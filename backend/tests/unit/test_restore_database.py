"""Safety tests for the encrypted isolated database restore helper."""

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts import restore_database as restore


def arguments(tmp_path: Path, **overrides) -> argparse.Namespace:
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    archive = outside / "backup.dump.gpg"
    archive.write_bytes(b"encrypted")
    keyring = outside / "keys"
    keyring.mkdir(exist_ok=True)
    passphrase = outside / "passphrase.dpapi"
    passphrase.write_bytes(b"protected")
    values = {
        "archive": str(archive),
        "gpg_home": str(keyring),
        "passphrase_dpapi_file": str(passphrase),
        "container": "gate-a-test",
        "database": "salon_restore",
        "database_user": "postgres",
        "timeout_seconds": 30,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def inspection(*, network="none", ports=None, address="", running=True):
    return json.dumps(
        [
            {
                "HostConfig": {"NetworkMode": network, "PortBindings": ports},
                "NetworkSettings": {
                    "Networks": {
                        "none": {
                            "IPAddress": address,
                            "GlobalIPv6Address": "",
                            "Gateway": "",
                            "IPv6Gateway": "",
                        }
                    }
                },
                "State": {"Running": running},
            }
        ]
    ).encode()


def test_isolated_container_is_accepted():
    completed = MagicMock(returncode=0, stdout=inspection())
    with patch.object(restore.subprocess, "run", return_value=completed):
        assert restore.inspect_isolated_container("docker", "gate-a-test") == {
            "network_mode": "none",
            "published_ports": 0,
        }


def test_empty_supabase_restore_database_is_accepted():
    completed = MagicMock(returncode=0, stdout=b"supabase_admin|true|true|0\n")
    with patch.object(restore.subprocess, "run", return_value=completed):
        assert restore.inspect_empty_database(
            "docker", "gate-a-test", "supabase_admin", "salon_restore"
        ) == {"restore_role_superuser": True, "restore_database_empty": True}


@pytest.mark.parametrize(
    ("output", "message"),
    [
        (b"supabase_admin|false|false|0\n", "superuser"),
        (b"supabase_admin|true|true|1\n", "must be empty"),
        (b"wrong|true|true|0\n", "identity"),
    ],
)
def test_unprivileged_or_nonempty_restore_database_is_refused(output, message):
    completed = MagicMock(returncode=0, stdout=output)
    with (
        patch.object(restore.subprocess, "run", return_value=completed),
        pytest.raises(restore.RestoreError, match=message),
    ):
        restore.inspect_empty_database(
            "docker", "gate-a-test", "supabase_admin", "salon_restore"
        )


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (inspection(network="bridge"), "network=none"),
        (inspection(ports={"5432/tcp": [{"HostPort": "5432"}]}), "network=none"),
        (inspection(address="172.17.0.2"), "network addressing"),
        (inspection(running=False), "not running"),
    ],
)
def test_nonisolated_container_is_refused(document, message):
    completed = MagicMock(returncode=0, stdout=document)
    with (
        patch.object(restore.subprocess, "run", return_value=completed),
        pytest.raises(restore.RestoreError, match=message),
    ):
        restore.inspect_isolated_container("docker", "gate-a-test")


def test_archive_inside_repository_is_refused(tmp_path):
    archive = restore.ROOT / "backend" / ".artifacts" / "unsafe.dump.gpg"
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(b"encrypted")
    args = arguments(tmp_path, archive=str(archive))
    try:
        with pytest.raises(restore.RestoreError, match="outside the repository"):
            restore.validate_inputs(args)
    finally:
        archive.unlink()


def test_invalid_database_and_container_names_are_refused(tmp_path):
    with pytest.raises(restore.RestoreError, match="database name"):
        restore.validate_inputs(arguments(tmp_path, database="postgres;drop"))
    with pytest.raises(restore.RestoreError, match="container name"):
        restore.inspect_isolated_container("docker", "bad container")


def test_passphrase_is_zeroed_after_restore(tmp_path):
    args = arguments(tmp_path)
    secret = bytearray(b"synthetic-passphrase")
    inspect = MagicMock(return_value={"network_mode": "none", "published_ports": 0})
    gpg = MagicMock()
    gpg.stdin = MagicMock()
    gpg.stdout = MagicMock()
    gpg.returncode = 0
    gpg.poll.return_value = 0
    restore_process = MagicMock()
    restore_process.returncode = 0
    restore_process.poll.return_value = 0
    with (
        patch.object(restore, "locate_tool", side_effect=lambda name: name),
        patch.object(restore, "inspect_isolated_container", inspect),
        patch.object(
            restore,
            "inspect_empty_database",
            return_value={"restore_role_superuser": True, "restore_database_empty": True},
        ),
        patch.object(restore, "unprotect_dpapi", return_value=secret),
        patch.object(restore.subprocess, "Popen", side_effect=[gpg, restore_process]),
    ):
        result = restore.restore(args)
    assert result["status"] == "isolated_restore_complete"
    assert result["plaintext_dump_written"] is False
    assert secret == bytearray(len(secret))
    assert gpg.stdin.write.call_count == 2
    assert "passphrase" not in result


def test_raw_tool_errors_are_not_in_restore_error(tmp_path):
    args = arguments(tmp_path)
    secret = bytearray(b"synthetic")
    gpg = MagicMock()
    gpg.stdin = MagicMock()
    gpg.stdout = MagicMock()
    gpg.returncode = 2
    gpg.poll.return_value = 2
    restore_process = MagicMock()
    restore_process.returncode = 1
    restore_process.poll.return_value = 1
    with (
        patch.object(restore, "locate_tool", side_effect=lambda name: name),
        patch.object(
            restore,
            "inspect_isolated_container",
            return_value={"network_mode": "none", "published_ports": 0},
        ),
        patch.object(
            restore,
            "inspect_empty_database",
            return_value={"restore_role_superuser": True, "restore_database_empty": True},
        ),
        patch.object(restore, "unprotect_dpapi", return_value=secret),
        patch.object(restore.subprocess, "Popen", side_effect=[gpg, restore_process]),
        pytest.raises(restore.RestoreError, match="gpg_failure") as failure,
    ):
        restore.restore(args)
    assert "synthetic" not in str(failure.value)
