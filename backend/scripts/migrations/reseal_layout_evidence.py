"""Re-seal Mumbai evidence after the migrations folder restructure.

Offline and read-only apart from rewriting two JSON evidence files. No network,
environment loading, database connection or SQL execution.

For each sealed path it records the CURRENT path and SHA-256, and keeps the old
path/hash under ``layout_restructure.superseded``. It also proves that SQL content
is unchanged and that each touched revision differs from its sealed original only
by the inserted ``/ "sql" /`` path segment.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REVIEWS = ROOT / "backend/migrations/reviews"
FILES = REVIEWS / "migration-mumbai-forward-files-2026-10-15.json"
BASELINE = REVIEWS / "migration-mumbai-forward-baseline-2026-10-15.json"
SQL_SEGMENT = b' / "sql" / '


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def current_path(old: str) -> str:
    """Map a pre-restructure repository path to where the file lives now."""
    if old.startswith("backend/migrations/") and old.endswith(".sql") and "/" not in old[len("backend/migrations/"):]:
        return "backend/migrations/sql/" + old.rsplit("/", 1)[1]
    return old


def reseal(entries: dict[str, str]) -> tuple[dict[str, str], dict[str, dict]]:
    sealed, superseded = {}, {}
    for old, old_hash in entries.items():
        new = current_path(old)
        data = (ROOT / new).read_bytes()
        now = digest(data)
        if new.endswith(".sql") and "/migrations/" in new:
            if now != old_hash:
                raise SystemExit(f"SQL content changed, refusing to reseal: {old}")
            note = "sql content hash unchanged; path moved"
        elif now == old_hash:
            note = "unchanged"
        elif digest(data.replace(SQL_SEGMENT, b" / ")) == old_hash:
            note = "only change: sidecar path segment '/ \"sql\" /' in the revision/test"
        else:
            raise SystemExit(f"Unexplained content change, refusing to reseal: {old}")
        sealed[new] = now
        if new != old or now != old_hash:
            superseded[old] = {"sha256": old_hash, "now": new, "reason": note}
    return sealed, superseded


def rewrite(path: Path, key_path: tuple[str, ...]) -> dict:
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    doc = json.loads(raw)
    target = doc
    for key in key_path[:-1]:
        target = target[key]
    sealed, superseded = reseal(target[key_path[-1]])
    target[key_path[-1]] = sealed
    doc["layout_restructure"] = {
        "reason": "migrations/ split into versions/, sql/ and reviews/; SQL content not edited",
        "superseded": superseded,
    }
    text = json.dumps(doc, indent=2) + "\n"
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return {path.name: {"entries": len(sealed), "superseded": len(superseded)}}


def main() -> None:
    print(json.dumps([rewrite(FILES, ("files_sha256",)), rewrite(BASELINE, ("baseline_hashes",))], indent=2))


if __name__ == "__main__":
    main()
