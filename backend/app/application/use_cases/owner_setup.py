"""Owner payout-account validation and setup-checklist helpers."""

from typing import Any

from app.core.exceptions import ValidationError

PAYOUT_FIELDS = ("account_holder_name", "upi_id", "bank_name", "bank_account_number", "ifsc")


def validate_payout_account(merged: dict[str, Any]) -> None:
    """Validate the merged payout row. Messages never contain submitted values."""

    if not merged.get("account_holder_name"):
        raise ValidationError("Account holder name is required")
    if merged.get("ifsc") and not merged.get("bank_account_number"):
        raise ValidationError("An IFSC code needs a bank account number")
    if merged.get("bank_name") and not merged.get("bank_account_number"):
        raise ValidationError("A bank name needs a bank account number")
    if merged.get("bank_account_number") and not merged.get("ifsc"):
        raise ValidationError("A bank account number needs an IFSC code")
    has_bank = bool(merged.get("bank_account_number")) and bool(merged.get("ifsc"))
    if not merged.get("upi_id") and not has_bank:
        raise ValidationError("Add a UPI ID, or both a bank account number and IFSC code")


def mask_payout_account(row: dict[str, Any] | None) -> dict[str, Any]:
    """Build the public response; only the last 4 digits of the account survive."""

    if row is None:
        return {
            "configured": False, "account_holder_name": None, "upi_id": None,
            "bank_name": None, "bank_account_last4": None, "ifsc": None,
            "has_upi": False, "has_bank": False, "updated_at": None,
        }
    # The repository already masks inside Postgres; ``bank_account_number`` is accepted
    # only so a caller holding a full row can never leak more than four digits.
    last4 = row.get("bank_account_last4")
    if last4 is None and row.get("bank_account_number"):
        last4 = row["bank_account_number"][-4:]
    return {
        "configured": True,
        "account_holder_name": row["account_holder_name"],
        "upi_id": row.get("upi_id"),
        "bank_name": row.get("bank_name"),
        "bank_account_last4": last4,
        "ifsc": row.get("ifsc"),
        "has_upi": bool(row.get("upi_id")),
        "has_bank": bool(last4) and bool(row.get("ifsc")),
        "updated_at": row.get("updated_at"),
    }


def _has_open_day(hours: Any) -> bool:
    if not isinstance(hours, dict):
        return False
    return any(isinstance(day, dict) and day.get("open") for day in hours.values())


def build_setup_status(facts: dict[str, Any]) -> dict[str, Any]:
    """Turn raw salon facts into the ordered setup checklist."""

    def present(key: str) -> bool:
        value = facts.get(key)
        return isinstance(value, str) and bool(value.strip())

    items = [
        ("profile_basics", "Business details",
         "Add your salon name, address and city.",
         all(present(k) for k in ("name", "address", "city")), "business_profile"),
        ("working_hours", "Working hours",
         "Choose the days and times you are open.",
         _has_open_day(facts.get("working_hours")), "working_hours"),
        ("photos", "Salon photos",
         "Add at least one photo of your salon.", bool(facts.get("has_photos")), "photos"),
        ("services", "Services",
         "Add at least one service customers can book.",
         bool(facts.get("has_services")), "services"),
        ("staff", "Staff",
         "Add at least one team member.", bool(facts.get("has_staff")), "staff"),
        ("payout", "Payout details",
         "Tell us where to send your customer payments.",
         bool(facts.get("has_payout")), "payout"),
    ]
    result = [
        {"key": key, "title": title, "description": desc, "done": done, "action": action}
        for key, title, desc, done, action in items
    ]
    completed = sum(1 for item in result if item["done"])
    return {
        "completed_count": completed,
        "total_count": len(result),
        "is_complete": completed == len(result),
        "items": result,
    }
