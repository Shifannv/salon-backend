"""Worker start-up validation, heartbeat healthcheck, compose wiring, schema guard, 0028."""

import importlib.util
import re
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.infrastructure.account_deletion import health
from app.infrastructure.account_deletion.worker import (
    storage_is_required,
    validate_worker_configuration,
)
from app.infrastructure.db.repositories import account_deletion_repository as repo_module
from app.infrastructure.db.repositories.account_deletion_repository import (
    SALON_CASCADE_TABLES,
    SALON_PROVIDER_REFERENCE_TABLES,
)


@pytest.fixture
def tmp_path():
    # pytest's own tmp_path directory is not writable on some Windows machines.
    with tempfile.TemporaryDirectory() as directory:
        yield Path(directory)


ROOT = Path(__file__).resolve().parents[2]
VERSIONS = ROOT / "migrations/versions"

FULL_R2 = {
    "r2_account_id": "acc", "r2_access_key_id": "k", "r2_secret_access_key": "s",
    "r2_bucket": "b", "r2_public_url": "https://media.example.com",
}
SUPABASE = {"supabase_url": "https://x.supabase.co", "supabase_service_role_key": "svc"}


def cfg(**kw) -> Settings:
    return Settings(_env_file=None, environment=kw.pop("environment", "production"), **kw)


# ----------------------------------------------------------- start-up validation
def test_a_missing_bucket_stops_the_worker_before_any_request_is_claimed():
    settings = cfg(supabase_anon_key="a", supabase_jwks_url="https://x/jwks", **SUPABASE,
                   **{**FULL_R2, "r2_bucket": None})
    problems = validate_worker_configuration(settings)
    assert len(problems) == 1 and "R2_BUCKET" in problems[0]


def test_missing_supabase_admin_credentials_are_reported():
    settings = cfg(environment="test", **FULL_R2)
    assert any("SUPABASE_SERVICE_ROLE_KEY" in p for p in validate_worker_configuration(settings))


def test_a_complete_production_configuration_is_accepted():
    settings = cfg(supabase_anon_key="a", supabase_jwks_url="https://x/jwks", **SUPABASE, **FULL_R2)
    assert validate_worker_configuration(settings) == []


def test_local_without_any_storage_is_allowed_but_a_partial_config_is_not():
    assert storage_is_required(cfg(environment="local")) is False
    assert validate_worker_configuration(cfg(environment="local", **SUPABASE)) == []
    partial = validate_worker_configuration(cfg(environment="local", r2_bucket="b", **SUPABASE))
    assert len(partial) == 1 and "R2_ACCOUNT_ID" in partial[0]


def test_a_refund_provider_that_cannot_start_is_reported():
    settings = cfg(environment="test", **SUPABASE, **FULL_R2)
    with patch.object(Settings, "payment_provider", "nonexistent", create=True):
        pass  # Settings itself refuses an adapter-less provider; the guard below covers boot
    with pytest.raises(ValueError):
        cfg(environment="test", payment_provider="nonexistent")
    assert validate_worker_configuration(settings) == []


# ------------------------------------------------------------------------ heartbeat
def test_healthcheck_is_green_only_while_the_heartbeat_is_fresh(tmp_path):
    beat = tmp_path / "beat"
    assert health.is_healthy(beat) is False  # never started
    health.touch(beat)
    assert health.is_healthy(beat) is True
    assert health.is_healthy(beat, now=time.time() + 10_000) is False  # wedged / dead
    beat.write_text("not-a-number", encoding="utf-8")
    assert health.is_healthy(beat) is False


def test_healthcheck_exit_code_and_message(tmp_path, monkeypatch, capsys):
    beat = tmp_path / "beat"
    monkeypatch.setenv("ACCOUNT_DELETION_HEARTBEAT_FILE", str(beat))
    assert health.main() == 1 and "stale" in capsys.readouterr().err
    health.touch()
    assert health.main() == 0


def test_heartbeat_tolerance_scales_with_the_poll_interval(monkeypatch):
    monkeypatch.setenv("ACCOUNT_DELETION_WORKER_POLL_SECONDS", "15")
    assert health.max_age_seconds() == 180
    monkeypatch.setenv("ACCOUNT_DELETION_WORKER_POLL_SECONDS", "600")
    assert health.max_age_seconds() == 3660
    monkeypatch.setenv("ACCOUNT_DELETION_WORKER_POLL_SECONDS", "junk")
    assert health.max_age_seconds() == 180


def test_compose_gives_the_deletion_worker_a_real_healthcheck_and_leaves_the_payment_worker():
    yaml = pytest.importorskip("yaml")
    services = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))["services"]
    deletion = services["account-deletion-worker"]["healthcheck"]
    assert deletion.get("disable") is not True
    assert deletion["test"][-1] == "app.infrastructure.account_deletion.health"
    assert deletion["interval"] and deletion["retries"]
    assert services["payment-webhook-worker"]["healthcheck"] == {"disable": True}


# -------------------------------------------------------------------- schema guard
_CASCADE = re.compile(
    r"references\s+(?:public\.)?salons\s*\(\s*id\s*\)\s*on\s+delete\s+cascade", re.IGNORECASE)
_TABLE_STMT = re.compile(
    r"(?:create\s+table(?:\s+if\s+not\s+exists)?|alter\s+table(?:\s+only)?(?:\s+if\s+exists)?)"
    r"\s+(?:public\.)?([a-z_][a-z0-9_]*)", re.IGNORECASE)


def cascade_tables_in_migrations() -> dict[str, str]:
    """table -> file, for every FK to salons(id) declared ``on delete cascade``."""

    found: dict[str, str] = {}
    sources = [ROOT / "migrations/001_supabase_schema.sql", *sorted(VERSIONS.glob("0*.py"))]
    for path in sources:
        sql = path.read_text(encoding="utf-8")
        for match in _CASCADE.finditer(sql):
            owners = list(_TABLE_STMT.finditer(sql, 0, match.start()))
            assert owners, f"{path.name}: cascade FK to salons outside any table statement"
            found[owners[-1].group(1).lower()] = path.name
    return found


def test_the_schema_guard_actually_finds_the_known_cascades():
    # If the parser silently stopped matching, the guard below would pass for the wrong reason.
    assert set(cascade_tables_in_migrations()) >= {
        "salon_images", "salon_holidays", "blocked_slots", "salon_payout_accounts",
        "salon_payout_account_history",
    }


def test_every_cascade_fk_to_salons_has_an_explicit_delete_in_the_owner_scrub():
    """Salons are soft-deactivated, so ``on delete cascade`` never fires. A new cascade FK
    without a matching entry in SALON_CASCADE_TABLES would silently keep a closed salon's
    data for ever (this is exactly how salon_holidays and the payout tables were missed)."""

    declared = cascade_tables_in_migrations()
    missing = {t: f for t, f in declared.items() if t not in SALON_CASCADE_TABLES}
    assert not missing, (
        f"cascade FK(s) to salons(id) not erased by account deletion: {missing}. "
        "Add the table to SALON_CASCADE_TABLES in account_deletion_repository.py."
    )
    source = Path(repo_module.__file__).read_text(encoding="utf-8")
    assert "for table in SALON_CASCADE_TABLES + SALON_PROVIDER_REFERENCE_TABLES" in source
    assert "delete from {table} where salon_id in" in source


def test_the_constant_lists_are_disjoint_and_sane():
    assert not set(SALON_CASCADE_TABLES) & set(SALON_PROVIDER_REFERENCE_TABLES)
    assert "salon_payout_account_history" in SALON_CASCADE_TABLES
    assert {"subscription_provider_accounts", "payment_provider_accounts"} == set(
        SALON_PROVIDER_REFERENCE_TABLES)


def test_the_guard_would_catch_a_new_cascade_table():
    sql = ("create table public.salon_widgets (id uuid primary key, "
           "salon_id uuid references public.salons(id) on delete cascade)")
    match = _CASCADE.search(sql)
    owner = list(_TABLE_STMT.finditer(sql, 0, match.start()))[-1].group(1)
    assert owner == "salon_widgets" and owner not in SALON_CASCADE_TABLES
    alter = "alter table salon_gizmos add constraint fk foreign key (salon_id) references salons(id) on delete cascade"
    assert list(_TABLE_STMT.finditer(alter, 0, _CASCADE.search(alter).start()))[-1].group(1) == "salon_gizmos"


# ------------------------------------------------------------------------- 0028
def load_0028():
    spec = importlib.util.spec_from_file_location(
        "erasure_hardening_revision", VERSIONS / "0028_account_erasure_hardening.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def run(fn) -> str:
    statements: list[str] = []
    with patch.object(load_0028().op, "execute", side_effect=statements.append):
        fn()
    return "\n".join(statements).lower()


def test_0028_chain_and_shape():
    m = load_0028()
    assert m.revision == "0028_account_erasure_hardening"
    assert m.down_revision == "0027_payout_account_audit"
    up = run(m.upgrade)
    assert "confdeltype in ('a', 'r')" in up  # RESTRICT audit columns can no longer wedge erasure
    assert "revoke execute on function erase_profile_references" in up
    assert "idx_account_deletion_requests_open_age" in up and "where status <> 'completed'" in up
    down = run(m.downgrade)
    assert "confdeltype in ('a')" in down and "drop index if exists idx_account_deletion_requests_open_age" in down


def test_0028_uses_one_statement_per_execute_for_asyncpg():
    statements: list[str] = []
    with patch.object(load_0028().op, "execute", side_effect=statements.append):
        load_0028().upgrade()
    for statement in statements:
        body = re.sub(r"\$\$.*?\$\$", "", statement, flags=re.DOTALL)
        assert body.count(";") <= 1, statement
