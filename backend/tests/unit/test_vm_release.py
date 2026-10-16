"""Exercise deployment failure boundaries with a fake Docker CLI, without a VM."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
BASH = (
    "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")
)
pytestmark = pytest.mark.skipif(not BASH or not Path(BASH).exists(), reason="Requires Bash")


@pytest.fixture
def release(tmp_path):
    root = tmp_path / "salon-backend"
    target = root / "releases" / "test-release"
    (target / "scripts").mkdir(parents=True)
    (root / "backend").mkdir()
    (root / "backend" / ".env").write_text("ENVIRONMENT=production\n")
    for script in ("gcp-vm-release.sh", "gcp-vm-release-compose.sh", "gcp-vm-deploy.sh"):
        shutil.copyfile(SCRIPTS / script, target / "scripts" / script)
    (target / "image.tar.gz").touch()
    (target / "image-ref").write_text("salon-platform-api:sha-" + "a" * 40 + "-1-1\n")
    (target / "image-id").write_text("sha256:test-image\n")
    (target / "docker-compose.yml").write_text("services: {}\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(
        """#!/usr/bin/env bash
set -eu
printf '%s|%s|%s|%s\\n' "$*" "${COMPOSE_PROJECT_NAME:-}" "${COMPOSE_ENV_FILE:-}" "${SALON_API_IMAGE:-}" >> "$DEPLOY_TEST_LOG"
if [[ "$*" == 'image inspect --format'* ]]; then
  if [[ "${FAIL_STAGE:-}" == image ]]; then echo sha256:wrong; else echo "${TEST_IMAGE_ID:-sha256:test-image}"; fi
fi
case "${FAIL_STAGE:-}" in
  load) [[ "$1" != load ]] || exit 1 ;;
  migrate) [[ "$*" != *'upgrade 0037_customer_processing_charge'* ]] || exit 1 ;;
  up) [[ "$*" != *' up -d '* ]] || exit 1 ;;
  health) [[ "$*" != *' exec -T api '* ]] || exit 1 ;;
esac
""",
        newline="\n",
    )
    docker.chmod(0o755)
    # Lock behavior is provided by the VM's util-linux; this harness tests ordering.
    lock = bin_dir / "flock"
    lock.write_text("#!/usr/bin/env bash\nexit 0\n", newline="\n")
    lock.chmod(0o755)
    env = dict(
        os.environ,
        SALON_DEPLOY_ROOT=root.as_posix(),
        DEPLOY_TEST_LOG=(tmp_path / "docker.log").as_posix(),
        PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
        SALON_MIGRATION_POLICY="portable-ci",
        SALON_MIGRATION_REVISION="0037_customer_processing_charge",
        SALON_MIGRATION_APPROVAL_ID="synthetic-test-approval",
    )
    return root, target, env


def run_release(release, fail_stage=""):
    root, target, env = release
    result = subprocess.run(
        [BASH, "scripts/gcp-vm-release.sh"],
        cwd=target,
        env=dict(env, FAIL_STAGE=fail_stage),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    path = Path(env["DEPLOY_TEST_LOG"])
    log = path.read_text() if path.exists() else ""
    return result, log, root / "releases" / "current"


@pytest.mark.parametrize("stage", ["load", "image", "migrate"])
def test_pre_deploy_failure_never_replaces_services(release, stage):
    result, log, current = run_release(release, stage)
    assert result.returncode != 0
    assert " up -d " not in log
    assert not current.exists()


@pytest.mark.parametrize("stage", ["up", "health"])
def test_failed_readiness_does_not_promote_release(release, stage):
    result, log, current = run_release(release, stage)
    assert result.returncode != 0
    assert "upgrade 0037_customer_processing_charge" in log
    assert " up -d " in log
    assert not current.exists()


def test_migration_failure_preserves_previous_release_record(release):
    root, _, _ = release
    current = root / "releases" / "current"
    current.write_text("previous successful release")
    result, _, _ = run_release(release, "migrate")
    assert result.returncode != 0
    assert current.read_text() == "previous successful release"


def test_missing_runtime_env_stops_before_migrations(release):
    root, _, _ = release
    (root / "backend" / ".env").unlink()
    result, log, current = run_release(release)
    assert result.returncode != 0
    assert "alembic upgrade" not in log
    assert not current.exists()


def test_containerd_manifest_id_is_accepted_from_verified_allowlist(release):
    _, target, env = release
    (target / "image-id").write_text("sha256:test-image\nsha256:manifest\n")
    env["TEST_IMAGE_ID"] = "sha256:manifest"
    result, _, current = run_release(release)
    assert result.returncode == 0, result.stderr
    assert current.exists()


def test_success_migrates_exact_image_then_promotes_healthy_release(release):
    result, log, current = run_release(release)
    assert result.returncode == 0, result.stderr
    assert log.index("upgrade 0037_customer_processing_charge") < log.index(" up -d ")
    assert log.count(" exec -T api ") == 3
    assert " build " not in log
    assert " pull redis" in log
    assert current.exists()
    for line in log.splitlines():
        if line.startswith("compose "):
            assert "|backend|" in line
            assert "/backend/.env|salon-platform-api:sha-" in line


@pytest.mark.parametrize("missing", ["SALON_MIGRATION_POLICY", "SALON_MIGRATION_REVISION", "SALON_MIGRATION_APPROVAL_ID"])
def test_release_requires_explicit_migration_selection_and_approval(release, missing):
    release[2].pop(missing)
    result, log, current = run_release(release)
    assert result.returncode != 0
    assert not log and not current.exists()


def test_release_rejects_implicit_head_before_any_docker_operation(release):
    release[2]["SALON_MIGRATION_REVISION"] = "head"
    result, log, current = run_release(release)
    assert result.returncode != 0 and "head is refused" in result.stderr
    assert not log and not current.exists()
