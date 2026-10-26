"""Literal, scoped patterns for known profile data in retained support text."""

import re
from urllib.parse import quote


def quoted_text_pattern(value: str) -> str:
    """Match a known original message literally, never as executable regex syntax."""
    before = "(?<![[:alnum:]_])" if value[0].isalnum() else ""
    after = "(?![[:alnum:]_])" if value[-1].isalnum() else ""
    return before + re.escape(value) + after


def authored_quote_pattern(literals: list[str]) -> str:
    """Require explicit quotation context; preserve the attribution in group one."""
    prefix = r'((?:(?<![[:alnum:]_])(?:quoted|wrote|said|copied):[[:space:]]*|(?:^|\n)[[:space:]]*>[[:space:]]*|["“]))'
    return prefix + "(?:" + "|".join(literals) + ")"


def personal_text_pattern(profile: dict) -> str | None:
    """Build PostgreSQL ARE alternatives; profile strings never become regex code."""
    patterns = set()
    for key in ("id", "full_name", "email", "phone", "avatar_url"):
        value = str(profile.get(key) or "").strip()
        if not value:
            continue
        for literal in {value, quote(value, safe="")}:
            patterns.add(quoted_text_pattern(literal))
    phone = re.sub(r"\D", "", str(profile.get("phone") or ""))
    if len(phone) >= 7:
        country = ""
        if len(phone) == 12 and phone.startswith("91"):
            country, phone = r"(?:\+?91[[:space:]().-]*)?", phone[2:]
        patterns.add("(?<![[:digit:]])" + country
                     + "[[:space:]().-]*".join(phone) + "(?![[:digit:]])")
    return "(?:" + "|".join(sorted(patterns, key=lambda value: (-len(value), value))) + ")" if patterns else None
