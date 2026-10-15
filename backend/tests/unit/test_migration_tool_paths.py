"""Offline tool relocation checks: no credentials, network or sealed writes."""

import hashlib
import importlib
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "backend/scripts/migrations"
REVIEW = ROOT / "backend/migrations/reviews/migration-mumbai-review-2026-10-15"
RUNNERS = sorted(TOOLS.glob("migration_mumbai_*_20261015.py")) + sorted(
    (TOOLS / "evidence").glob("migration_mumbai_*_20261015.py")
)


@pytest.fixture
def offline_tools(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))

    def denied(*args, **kwargs):
        raise AssertionError("Tool path checks must not connect to a network")

    monkeypatch.setattr(socket.socket, "connect", denied)
    original_read = Path.read_text

    def guarded_read(path, *args, **kwargs):
        assert not path.name.startswith(".env"), "Tool imports must not load credentials"
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read)


@pytest.mark.parametrize("runner", RUNNERS, ids=lambda path: path.stem)
def test_runner_imports_without_network_or_credentials(offline_tools, runner):
    module = importlib.import_module(".".join(runner.relative_to(ROOT).with_suffix("").parts))
    if hasattr(module, "ROOT"):
        assert module.ROOT == ROOT


def test_runner_distribution():
    assert len(list(TOOLS.glob("migration_mumbai_*_20261015.py"))) == 7
    assert len(list((TOOLS / "evidence").glob("migration_mumbai_*_20261015.py"))) == 6


def test_offline_bundle_matches_sealed_files(offline_tools, tmp_path, monkeypatch):
    module = importlib.import_module(
        "backend.scripts.migrations.migration_mumbai_review_bundle_20261015"
    )
    monkeypatch.setattr(module, "OUT", tmp_path)
    module.build()
    for generated in tmp_path.iterdir():
        expected = REVIEW / generated.name
        assert expected.is_file()
        assert hashlib.sha256(generated.read_bytes()).digest() == hashlib.sha256(
            expected.read_bytes()
        ).digest(), generated.name


def test_read_only_bundle_validation(offline_tools):
    module = importlib.import_module(
        "backend.scripts.migrations.migration_mumbai_review_validate_20261015"
    )
    module.validate()


def test_revision_review_preserves_sealed_evidence(offline_tools, tmp_path, monkeypatch):
    module = importlib.import_module(
        "backend.scripts.migrations.migration_mumbai_revision_runtime_review_20261015"
    )
    target = ROOT / "backend/migrations/reviews/migration-mumbai-runtime-revision-review-2026-10-15.json"
    before = target.read_bytes()
    original_write = Path.write_text

    def redirected_write(path, content, *args, **kwargs):
        assert path == target
        return original_write(tmp_path / path.name, content, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", redirected_write)
    module.main()
    assert target.read_bytes() == before
    assert (tmp_path / target.name).read_bytes() == before
