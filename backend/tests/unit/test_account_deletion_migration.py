"""Static checks on revision 0021 without contacting a database."""

import importlib.util
import re
from pathlib import Path
from unittest.mock import patch

VERSIONS = Path(__file__).resolve().parents[2] / "migrations/versions"


def load():
    spec = importlib.util.spec_from_file_location("account_deletion_revision", VERSIONS / "0021_account_deletion.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def run(fn):
    statements: list[str] = []
    with patch.object(load().op, "execute", side_effect=statements.append):
        fn()
    return statements


def test_revision_chain_is_linear_after_media_guards():
    migration = load()
    assert migration.revision == "0021_account_deletion"
    assert migration.down_revision == "0020_media_reference_guards"
    heads = [p.stem for p in VERSIONS.glob("0*.py")]
    assert "0021_account_deletion" in heads and len(heads) == len(set(heads))


def test_upgrade_creates_bound_challenges_and_a_pii_free_ledger():
    sql = "\n".join(run(load().upgrade)).lower()
    assert "create table account_deletion_challenges" in sql
    assert "references profiles(id) on delete cascade" in sql
    assert "check (purpose = 'account_deletion')" in sql
    assert "contact_hash text not null" in sql
    assert "uq_account_deletion_challenge_live" in sql and "where status in ('sent', 'verified')" in sql
    ledger = sql.split("create table account_deletion_requests")[1].split("alter table")[0]
    assert "user_id uuid," in ledger and "references profiles" not in ledger
    assert "uq_account_deletion_request_open" in sql
    columns = set(re.findall(r"^\s*(\w+)\s+(?:uuid|text|integer|jsonb|timestamptz)\b", ledger, re.MULTILINE))
    assert {"id", "user_id", "role", "status", "media_keys", "last_error_code"} <= columns
    for forbidden in ("email", "phone", "full_name", "otp", "code", "contact_hash"):
        assert forbidden not in columns
    assert "enable row level security" in sql


def test_upgrade_relaxes_only_the_not_null_columns_erasure_must_clear():
    sql = "\n".join(run(load().upgrade)).lower()
    assert "alter table salons alter column owner_id drop not null" in sql
    assert "alter table booking_action_requests alter column requested_by drop not null" in sql


def test_audit_trigger_escape_hatch_and_erasure_helper():
    sql = "\n".join(run(load().upgrade)).lower()
    assert "current_setting('app.account_erasure', true)" in sql
    assert "create function erase_profile_references" in sql
    assert "security invoker" in sql and "set_config('app.account_erasure', 'on', true)" in sql
    assert "confdeltype = 'a'" in sql  # only no-action FKs; cascades are left alone


def test_downgrade_restores_baseline_audit_trigger_and_drops_everything():
    sql = "\n".join(run(load().downgrade)).lower()
    assert "app.account_erasure" not in sql
    assert "drop function if exists erase_profile_references" in sql
    assert "drop table if exists account_deletion_requests" in sql
    assert "drop table if exists account_deletion_challenges" in sql
    assert "new.created_by := old.created_by" in sql
