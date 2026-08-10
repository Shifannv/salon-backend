import pytest
from pydantic import ValidationError

from app.api.v1.schemas.platform import ProfileUpdateRequest


def test_profile_update_normalizes_indian_mobile() -> None:
    payload = ProfileUpdateRequest(phone="98765 43211")

    assert payload.phone == "+919876543211"


def test_profile_update_allows_repeated_digits_inside_valid_mobile() -> None:
    payload = ProfileUpdateRequest(phone="9876000012")

    assert payload.phone == "+919876000012"


@pytest.mark.parametrize(
    "phone",
    [
        "1234567890",
        "9876543210",
        "0000000000",
        "1111111111",
        "98765",
    ],
)
def test_profile_update_rejects_fake_or_invalid_mobile(phone: str) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest(phone=phone)
