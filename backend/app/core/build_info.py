"""Public source identity baked into an image, never supplied by runtime secrets."""
import re
from pathlib import Path

API_VERSION = "0.1.0"
COMMIT_FILE = Path(__file__).resolve().parents[2] / "build-commit"


def source_commit() -> str:
    try:
        value = COMMIT_FILE.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return "unknown"
    return value if re.fullmatch(r"[0-9a-f]{40}", value) else "unknown"
