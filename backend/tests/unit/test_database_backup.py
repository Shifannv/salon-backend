"""Backup export safety: routing, encryption boundaries and failed pipelines."""

import hashlib
import importlib.util
import io
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

SPEC = importlib.util.spec_from_file_location(
    "database_backup", Path(__file__).resolve().parents[2] / "scripts/backup_database.py",
)
backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup)
FINGERPRINT = "A" * 40


def test_git_gpg_paths_use_msys_drive_form():
    tool = "C:/Program Files/Git/usr/bin/gpg.exe"
    assert backup.gpg_path(tool, "C:\\Users\\Fixture\\keys") == "/c/Users/Fixture/keys"
    assert backup.gpg_path("/usr/bin/gpg", "/home/fixture/keys") == "/home/fixture/keys"
    assert backup.gpg_path("C:/Gpg4win/bin/gpg.exe", "C:\\keys") == "C:/keys"


@pytest.fixture
def source(tmp_path):
    cert = tmp_path / "ca.crt"
    cert.write_text("public fixture certificate")
    return {"PGHOST": "db.example.invalid", "PGDATABASE": "postgres", "PGUSER": "fixture",
            "PGPASSWORD": "synthetic-test-only", "PGSSLMODE": "verify-full", "PGSSLROOTCERT": str(cert)}


@pytest.mark.parametrize("change", [
    {"PGHOST": "different.example.invalid"}, {"PGSSLMODE": "require"}, {"PGSSLMODE": "disable"},
    {"PGPORT": "6543"}, {"PGSERVICE": "another-target"}, {"PGSERVICEFILE": "another-target"},
    {"PGDATABASE": ""}, {"PGUSER": ""}, {"PGSSLROOTCERT": "missing-certificate"},
])
def test_unsafe_source_cannot_start_any_export(source, change, monkeypatch):
    monkeypatch.setattr(backup.subprocess, "Popen", Mock(side_effect=AssertionError("No process expected")))
    with pytest.raises(ValueError):
        backup.export_backup(SimpleNamespace(expected_host="db.example.invalid"), {**source, **change})
    backup.subprocess.Popen.assert_not_called()


def test_private_keys_must_not_live_in_checkout(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "ROOT", tmp_path)
    keyring = tmp_path / "keys"
    keyring.mkdir()
    with pytest.raises(ValueError, match="outside the repository"):
        backup.validate_destination(tmp_path / "output", keyring, FINGERPRINT)


def test_unignored_checkout_destination_is_rejected(tmp_path, monkeypatch):
    checkout = tmp_path / "repo"
    checkout.mkdir()
    keyring = tmp_path / "keys"
    keyring.mkdir()
    monkeypatch.setattr(backup, "ROOT", checkout)
    monkeypatch.setattr(backup.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=1))
    with pytest.raises(ValueError, match="git-ignored"):
        backup.validate_destination(checkout / "unprotected", keyring, FINGERPRINT)


@pytest.mark.parametrize("failure", [None, "dump", "encryption", "missing_key", "timeout"])
def test_encrypted_pipeline_only_records_complete_exports(source, tmp_path, monkeypatch, failure):
    output, keyring = tmp_path / "output", tmp_path / "keys"
    keyring.mkdir()
    monkeypatch.setattr(backup, "ROOT", tmp_path / "unrelated-repo")
    monkeypatch.setattr(backup, "locate_tool", lambda name: name)
    dump = Mock(stdout=io.BytesIO(b"synthetic database archive"))
    dump.wait.return_value = 1 if failure == "dump" else 0
    dump.poll.return_value = None if failure == "timeout" else 0
    spawn = Mock(return_value=dump)
    monkeypatch.setattr(backup.subprocess, "Popen", spawn)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if "--list-keys" in command:
            return SimpleNamespace(returncode=0, stdout=(
                b"" if failure == "missing_key" else f"fpr:::::::::{FINGERPRINT}:\n".encode()
            ))
        assert kwargs["stdin"] is dump.stdout
        kwargs["stdout"].write(b"encrypted-fixture-bytes")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 660)
        return SimpleNamespace(returncode=1 if failure == "encryption" else 0)

    monkeypatch.setattr(backup.subprocess, "run", run)
    args = SimpleNamespace(expected_host=source["PGHOST"], output_dir=output,
                           gpg_home=keyring, recipient=FINGERPRINT)
    if failure:
        with pytest.raises((ValueError, RuntimeError, subprocess.TimeoutExpired)):
            backup.export_backup(args, {**source, "UNRELATED_SECRET": "never-forwarded"})
        assert not list(output.glob("*.json"))
        assert not list(output.glob("*.gpg"))
        if failure == "missing_key":
            spawn.assert_not_called()
        if failure == "timeout":
            dump.kill.assert_called_once()
    else:
        result = backup.export_backup(args, {**source, "UNRELATED_SECRET": "never-forwarded"})
        assert result["status"] == "encrypted_export_complete_restore_unverified"
        assert result["sha256"] == hashlib.sha256(b"encrypted-fixture-bytes").hexdigest()
        assert not result["plaintext_dump_written"]
        assert "synthetic-test-only" not in json.dumps(result)
        assert {p.suffix for p in output.iterdir()} == {".gpg", ".json"}
        assert "UNRELATED_SECRET" not in spawn.call_args.kwargs["env"]
        assert source["PGPASSWORD"] not in str(spawn.call_args.args[0])
        assert all("--no-auto-key-retrieve" in command for command in calls)
    assert dump.stdout.closed or failure == "missing_key"
