"""Check the review bundle's explicit privilege boundary without executing SQL."""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "backend/migrations/reviews/migration-mumbai-review-2026-10-15"


def validate():
    sql = {name: (BUNDLE / name).read_text(encoding="utf-8") for name in (
        "01-schema-only.sql", "02-security-grants.sql", "03-signup-trigger.sql",
    )}
    snapshot = json.loads((ROOT / "backend/migrations/reviews/migration-mumbai-least-privilege-snapshot-2026-10-15.json").read_text())
    for source in sql.values():
        code = re.sub(r"--[^\n]*", "", source)
        assert not re.search(r"ALTER\s+DEFAULT\s+PRIVILEGES|alembic\s+stamp", code, re.IGNORECASE)
        assert not re.search(r"^\s*(?:DROP|TRUNCATE|INSERT\s+INTO|DELETE\s+FROM)\b", code, re.IGNORECASE | re.MULTILINE)
        assert not re.search(r"\bUPDATE\s+public\.", code, re.IGNORECASE)
        assert not re.search(r"GRANT\s+.*\bTO\s+(?:PUBLIC|anon|authenticated)\b", code, re.IGNORECASE)
        assert not re.search(r"GRANT\s+.*ALL\s+(?:FUNCTIONS|TABLES)|WITH\s+GRANT\s+OPTION", code, re.IGNORECASE)
        assert source.count("BEGIN;\n") == 1 and source.endswith("COMMIT;\n")
    security = sql["02-security-grants.sql"]
    grants = re.findall(r"^GRANT (.+);$", security, re.MULTILINE)
    assert grants == [
        "EXECUTE ON FUNCTION public.create_booking(uuid,uuid,uuid[],timestamp with time zone,text,text,public.booking_source,text) TO service_role",
        "EXECUTE ON FUNCTION public.get_available_slots(uuid,date,integer) TO service_role",
    ]
    table_revokes = re.findall(r"^REVOKE ALL PRIVILEGES ON TABLE public\.([a-z_]+) FROM PUBLIC, anon, authenticated RESTRICT;$", security, re.MULTILINE)
    assert set(table_revokes) == {t["name"] for t in snapshot["tables"]}
    assert len(table_revokes) == 44
    function_revokes = re.findall(r"^REVOKE EXECUTE ON FUNCTION (.+) FROM PUBLIC, anon, authenticated RESTRICT;$", security, re.MULTILINE)
    assert len(function_revokes) == 52 and len(set(function_revokes)) == 52
    with (BUNDLE / "privilege-matrix.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1214
    assert all(r["existing_objects_only"] == "yes" and r["future_objects_receive_privilege"] == "no" for r in rows)
    assert len([r for r in rows if r["operation"] == "GRANT"]) == 2
    assert {r["object"] for r in rows if r["privilege"] == "EXECUTE" and r["operation"] == "REVOKE"} == set(function_revokes)
    assert "CREATE OR REPLACE" not in sql["03-signup-trigger.sql"]
    assert "t_on_auth_user_created" in sql["03-signup-trigger.sql"]
    print("PASS: explicit-object/role boundary, 1,214-row matrix, no defaults/client grants/destructive DML/history writes; no SQL executed")


if __name__ == "__main__":
    validate()
