"""Stream a PostgreSQL custom archive into GPG; never write a plaintext dump.

Reads libpq settings from process environment, never application environment files.
Run --check-tools first. Export is opt-in and does not restore or change a database.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WINDOWS_TOOLS = {
    "pg_dump": Path("C:/Program Files/PostgreSQL/18/bin/pg_dump.exe"),
    "gpg": Path("C:/Program Files/Git/usr/bin/gpg.exe"),
}
PG_SETTINGS = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGPASSFILE", "PGSSLROOTCERT")


def locate_tool(name):
    found = shutil.which(name)
    fallback = WINDOWS_TOOLS[name]
    if found:
        return found
    return str(fallback) if fallback.is_file() else None


def gpg_path(tool, path):
    """Git's MSYS GPG expects Unix drive paths instead of native backslashes."""
    normalized = str(path).replace("\\", "/")
    if str(tool).replace("\\", "/").lower().endswith("/usr/bin/gpg.exe") and re.match(r"^[A-Za-z]:/", normalized):
        return "/" + normalized[0].lower() + normalized[2:]
    return normalized


def validate_source(environment, expected_host):
    """Reject ambiguous routing and require remote TLS without printing config."""
    if not expected_host or environment.get("PGHOST") != expected_host:
        raise ValueError("PGHOST must match --expected-host")
    if any(c in expected_host for c in "/:@, "):
        raise ValueError("Expected host must be one hostname, without credentials or overrides")
    if not environment.get("PGDATABASE") or not environment.get("PGUSER"):
        raise ValueError("PGDATABASE and PGUSER must be configured in the process environment")
    if environment.get("PGSERVICE") or environment.get("PGSERVICEFILE"):
        raise ValueError("Service-file routing is not accepted for this explicit backup")
    if environment.get("PGPORT", "5432") == "6543":
        raise ValueError("Use a direct or session-pooler connection, not transaction port 6543")
    if environment.get("PGSSLMODE") != "verify-full":
        raise ValueError("PGSSLMODE=verify-full is required")
    certificate = environment.get("PGSSLROOTCERT")
    if not certificate or not Path(certificate).is_file():
        raise ValueError("A trusted PGSSLROOTCERT file is required")


def validate_destination(output_directory, gpg_home, recipient):
    """Keep private keys outside the checkout and export files in an ignored path."""
    output = Path(output_directory).resolve()
    keyring = Path(gpg_home).resolve()
    if keyring.is_relative_to(ROOT) or not keyring.is_dir():
        raise ValueError("GPG home must already exist outside the repository")
    if output.is_relative_to(keyring) or keyring.is_relative_to(output):
        raise ValueError("Backup destination and keyring must be separate")
    if not re.fullmatch(r"[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64}", recipient):
        raise ValueError("Use the full public encryption-key fingerprint")
    if output.is_relative_to(ROOT):
        probe = output / "backup.dump.gpg"
        check = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "--quiet", "--", str(probe)],
            capture_output=True, check=False,
        )
        if check.returncode != 0:
            raise ValueError("Backup destination inside the repository must be git-ignored")
    return output, keyring


def export_backup(args, environment):
    validate_source(environment, args.expected_host)
    output, keyring = validate_destination(args.output_dir, args.gpg_home, args.recipient)
    pg_dump, gpg = locate_tool("pg_dump"), locate_tool("gpg")
    if not pg_dump or not gpg:
        raise ValueError("pg_dump and gpg must be installed before exporting")
    gpg_args = [gpg, "--no-options", "--homedir", gpg_path(gpg, keyring), "--batch", "--no-tty", "--no-auto-key-retrieve"]
    keys = subprocess.run(
        [*gpg_args, "--with-colons", "--fingerprint", "--list-keys", args.recipient],
        capture_output=True, check=False, timeout=20,
    )
    fingerprints = [line.split(":")[9].upper() for line in keys.stdout.decode(errors="replace").splitlines()
                    if line.startswith("fpr:") and len(line.split(":")) > 9]
    if keys.returncode or args.recipient.upper() not in fingerprints:
        raise ValueError("The exact recipient key is unavailable; no database export started")

    output.mkdir(parents=True, exist_ok=True)
    name = "postgres-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + ".dump.gpg"
    destination = output / name
    partial = destination.with_suffix(destination.suffix + ".partial")
    # Only allow libpq values needed for the selected source into the dump process.
    dump_env = {k: v for k, v in environment.items() if k.upper() in {
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC", "PATHEXT",
    }}
    dump_env.update({k: environment[k] for k in PG_SETTINGS if k in environment})
    dump_env.update(PGSSLMODE="verify-full", PGCONNECT_TIMEOUT="15",
                    PGOPTIONS="-c statement_timeout=600000 -c lock_timeout=5000")
    with tempfile.TemporaryFile() as dump_errors, tempfile.TemporaryFile() as encryption_errors, partial.open("xb") as archive:
        dump = subprocess.Popen(
            [pg_dump, "--format=custom", "--no-password", "--lock-wait-timeout=5s"],
            env=dump_env, stdout=subprocess.PIPE, stderr=dump_errors,
        )
        try:
            try:
                encrypted = subprocess.run(
                    [*gpg_args, "--trust-model", "always", "--recipient", args.recipient, "--encrypt"],
                    stdin=dump.stdout, stdout=archive, stderr=encryption_errors, check=False, timeout=660,
                )
            finally:
                dump.stdout.close()
            dumped = dump.wait(timeout=30)
            if dumped or encrypted.returncode:
                raise RuntimeError("Backup failed; incomplete .partial output must not be used")
        finally:
            if dump.poll() is None:
                dump.kill()
                dump.wait(timeout=10)
    if not partial.stat().st_size:
        raise RuntimeError("Encrypted backup was empty; no completed archive recorded")
    partial.rename(destination)
    with destination.open("rb") as archive:
        digest = hashlib.file_digest(archive, "sha256").hexdigest()
    manifest = {"status": "encrypted_export_complete_restore_unverified", "archive": destination.name,
                "sha256": digest, "bytes": destination.stat().st_size,
                "created_at": datetime.now(UTC).isoformat(), "format": "pg_dump custom + OpenPGP",
                "plaintext_dump_written": False, "scope": "database objects/data visible to the configured role",
                "not_included": ["R2/storage object contents", "cloud IAM/DNS", "provider settings", "runtime secrets"],
                "restore_rehearsal": "required_before_using_for_recovery"}
    destination.with_suffix(destination.suffix + ".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-tools", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expected-host")
    parser.add_argument("--output-dir")
    parser.add_argument("--gpg-home")
    parser.add_argument("--recipient")
    args = parser.parse_args()
    if args.check_tools:
        print(json.dumps({name: bool(locate_tool(name)) for name in WINDOWS_TOOLS}))
        return
    if not args.execute or not all((args.expected_host, args.output_dir, args.gpg_home, args.recipient)):
        parser.error("Export requires --execute, --expected-host, --output-dir, --gpg-home and --recipient")
    try:
        print(json.dumps(export_backup(args, os.environ)))
    except (ValueError, RuntimeError) as error:
        print(json.dumps({"status": "backup_not_complete", "reason": str(error)}))
        raise SystemExit(1) from None
    except (OSError, subprocess.SubprocessError):
        print(json.dumps({"status": "backup_not_complete", "reason": "Tool execution failed; raw diagnostics suppressed"}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
