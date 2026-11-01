"""Restore an encrypted PostgreSQL archive into an isolated Docker database.

The archive is decrypted directly into ``pg_restore``.  No plaintext dump is
written.  The target container must use Docker network mode ``none`` and must
have no published ports.  Raw tool diagnostics are intentionally suppressed
because connection and encryption failures may contain sensitive material.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", "C:/__missing_local_app_data__"))
WINDOWS_TOOLS = {
    "gpg": Path("C:/Program Files/Git/usr/bin/gpg.exe"),
    "docker": LOCAL_APP_DATA / "Programs/DockerDesktop/resources/bin/docker.exe",
}
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class RestoreError(RuntimeError):
    """A safe, non-secret restore failure."""


class _DataBlob(ctypes.Structure):
    _fields_ = [("size", ctypes.c_ulong), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def locate_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    fallback = WINDOWS_TOOLS[name]
    return str(fallback) if fallback.is_file() else None


def _gpg_path(tool: str, path: Path) -> str:
    normalized = str(path).replace("\\", "/")
    if tool.replace("\\", "/").lower().endswith("/usr/bin/gpg.exe") and re.match(
        r"^[A-Za-z]:/", normalized
    ):
        return "/" + normalized[0].lower() + normalized[2:]
    return normalized


def unprotect_dpapi(path: Path) -> bytearray:
    """Decrypt a current-user Windows DPAPI blob without exposing its value."""

    if os.name != "nt":
        raise RestoreError("DPAPI restore is available only on Windows")
    encrypted = path.read_bytes()
    if not encrypted:
        raise RestoreError("DPAPI passphrase file is empty")
    source = (ctypes.c_ubyte * len(encrypted)).from_buffer_copy(encrypted)
    incoming = _DataBlob(len(encrypted), source)
    outgoing = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = ctypes.c_bool
    if not crypt32.CryptUnprotectData(
        ctypes.byref(incoming), None, None, None, None, 0, ctypes.byref(outgoing)
    ):
        raise RestoreError("DPAPI passphrase decryption failed")
    try:
        return bytearray(ctypes.string_at(outgoing.data, outgoing.size))
    finally:
        if outgoing.data:
            kernel32.LocalFree(outgoing.data)


def inspect_isolated_container(docker: str, container: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", container):
        raise RestoreError("Invalid Docker container name")
    result = subprocess.run(
        [docker, "inspect", container],
        capture_output=True,
        check=False,
        timeout=20,
        creationflags=CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise RestoreError("Restore target container is unavailable")
    try:
        document = json.loads(result.stdout)[0]
        host = document["HostConfig"]
        networks = document["NetworkSettings"]["Networks"]
        state = document["State"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise RestoreError("Docker isolation metadata is invalid") from error
    if not state.get("Running"):
        raise RestoreError("Restore target container is not running")
    if host.get("NetworkMode") != "none" or host.get("PortBindings") not in (None, {}):
        raise RestoreError("Restore target must use network=none with no published ports")
    if any(
        details.get(field)
        for details in networks.values()
        for field in ("IPAddress", "GlobalIPv6Address", "Gateway", "IPv6Gateway")
    ):
        raise RestoreError("Restore target unexpectedly has network addressing")
    return {"network_mode": "none", "published_ports": 0}


def inspect_empty_database(
    docker: str, container: str, database_user: str, database: str
) -> dict[str, Any]:
    """Require a privileged, empty target before restoring managed Supabase schemas."""

    query = """
        select current_user, r.rolsuper::text, r.rolbypassrls::text,
               (select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
                where n.nspname not in ('pg_catalog','information_schema')
                  and n.nspname not like 'pg_toast%'
                  and c.relkind in ('r','p','v','m','S','f'))::text
        from pg_roles r where r.rolname=current_user
    """
    result = subprocess.run(
        [
            docker,
            "exec",
            container,
            "psql",
            "--username",
            database_user,
            "--dbname",
            database,
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            "--field-separator=|",
            "--command",
            query,
        ],
        capture_output=True,
        check=False,
        timeout=20,
        creationflags=CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise RestoreError("Restore database or role is unavailable")
    fields = result.stdout.decode(errors="replace").strip().split("|")
    if len(fields) != 4 or fields[0] != database_user:
        raise RestoreError("Restore database identity could not be verified")
    if fields[1:3] != ["true", "true"]:
        raise RestoreError("Full Supabase restore requires a superuser with RLS bypass")
    if fields[3] != "0":
        raise RestoreError("Restore database must be empty")
    return {"restore_role_superuser": True, "restore_database_empty": True}


def validate_inputs(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    archive = Path(args.archive).resolve()
    keyring = Path(args.gpg_home).resolve()
    passphrase_file = Path(args.passphrase_dpapi_file).resolve()
    if not archive.is_file() or archive.suffix.lower() != ".gpg":
        raise RestoreError("Encrypted archive is missing or has the wrong suffix")
    if archive.is_relative_to(ROOT):
        raise RestoreError("Recovery archives must remain outside the repository")
    if not keyring.is_dir() or keyring.is_relative_to(ROOT):
        raise RestoreError("GPG home must exist outside the repository")
    if not passphrase_file.is_file() or passphrase_file.is_relative_to(ROOT):
        raise RestoreError("DPAPI passphrase file must exist outside the repository")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,62}", args.database):
        raise RestoreError("Invalid isolated database name")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,62}", args.database_user):
        raise RestoreError("Invalid isolated database user")
    return archive, keyring, passphrase_file


def restore(args: argparse.Namespace) -> dict[str, Any]:
    archive, keyring, passphrase_file = validate_inputs(args)
    gpg, docker = locate_tool("gpg"), locate_tool("docker")
    if not gpg or not docker:
        raise RestoreError("GPG and Docker are required")
    isolation = inspect_isolated_container(docker, args.container)
    target = inspect_empty_database(
        docker, args.container, args.database_user, args.database
    )
    passphrase = unprotect_dpapi(passphrase_file)
    started = time.perf_counter()
    gpg_process = restore_process = None
    try:
        with tempfile.TemporaryFile() as gpg_errors, tempfile.TemporaryFile() as restore_errors:
            gpg_process = subprocess.Popen(
                [
                    gpg,
                    "--no-options",
                    "--homedir",
                    _gpg_path(gpg, keyring),
                    "--batch",
                    "--no-tty",
                    "--pinentry-mode",
                    "loopback",
                    "--passphrase-fd",
                    "0",
                    "--decrypt",
                    str(archive),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=gpg_errors,
                creationflags=CREATE_NO_WINDOW,
            )
            assert gpg_process.stdin is not None and gpg_process.stdout is not None
            restore_process = subprocess.Popen(
                [
                    docker,
                    "exec",
                    "-i",
                    args.container,
                    "pg_restore",
                    "--username",
                    args.database_user,
                    "--dbname",
                    args.database,
                    "--no-owner",
                    "--no-privileges",
                    "--exit-on-error",
                ],
                stdin=gpg_process.stdout,
                stdout=subprocess.DEVNULL,
                stderr=restore_errors,
                creationflags=CREATE_NO_WINDOW,
            )
            gpg_process.stdout.close()
            gpg_process.stdin.write(passphrase)
            gpg_process.stdin.write(b"\n")
            gpg_process.stdin.close()
            try:
                restore_process.wait(timeout=args.timeout_seconds)
                gpg_process.wait(timeout=30)
            except subprocess.TimeoutExpired as error:
                restore_process.kill()
                gpg_process.kill()
                restore_process.wait(timeout=10)
                gpg_process.wait(timeout=10)
                raise RestoreError("Encrypted restore timed out") from error
            if gpg_process.returncode or restore_process.returncode:
                failure = "gpg_failure" if gpg_process.returncode else "pg_restore_failure"
                raise RestoreError(f"Encrypted restore failed: {failure}")
    except (OSError, subprocess.SubprocessError) as error:
        raise RestoreError("Encrypted restore tool execution failed") from error
    finally:
        for index in range(len(passphrase)):
            passphrase[index] = 0
        if restore_process is not None and restore_process.poll() is None:
            restore_process.kill()
        if gpg_process is not None and gpg_process.poll() is None:
            gpg_process.kill()
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {
        "status": "isolated_restore_complete",
        "archive_sha256": digest,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "plaintext_dump_written": False,
        **isolation,
        **target,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-tools", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--archive")
    parser.add_argument("--gpg-home")
    parser.add_argument("--passphrase-dpapi-file")
    parser.add_argument("--container")
    parser.add_argument("--database")
    parser.add_argument("--database-user", default="postgres")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    if args.check_tools:
        print(json.dumps({name: bool(locate_tool(name)) for name in WINDOWS_TOOLS}))
        return
    required = (
        args.archive,
        args.gpg_home,
        args.passphrase_dpapi_file,
        args.container,
        args.database,
    )
    if not args.execute or not all(required):
        parser.error("Restore requires --execute and every target/encryption argument")
    try:
        print(json.dumps(restore(args)))
    except RestoreError as error:
        print(json.dumps({"status": "restore_not_complete", "reason": str(error)}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
