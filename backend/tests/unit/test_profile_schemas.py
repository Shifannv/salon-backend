import pytest
from pydantic import ValidationError

from app.api.v1.schemas.platform import ProfileUpdateRequest


def test_profile_update_normalizes_indian_mobile() -> None:
    payload = ProfileUpdateRequest(phone="9090908080")

    assert payload.phone == "+919090908080"


def test_profile_update_accepts_plus_91_storage_format() -> None:
    payload = ProfileUpdateRequest(phone="+919876000012")

    assert payload.phone == "+919876000012"


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
        "1212121212",
        "111222333",
        "12345",
        "4321",
        "98765",
        "98765 43211",
        "90909abc80",
    ],
)
def test_profile_update_rejects_fake_or_invalid_mobile(phone: str) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest(phone=phone)


@pytest.mark.parametrize("reference", ["__char__char-1", "__char__char-15", "avatar:curly", "avatar:beard", "avatar:geek"])
def test_profile_update_preserves_bundled_avatar_references(reference):
    assert ProfileUpdateRequest(avatar_url=reference).avatar_url == reference


@pytest.mark.parametrize("reference", ["__char__char-16", "avatar:unknown", "data:image/png;base64,AAAA"])
def test_profile_update_rejects_unknown_or_inline_avatar_references(reference):
    with pytest.raises(ValidationError):
        ProfileUpdateRequest(avatar_url=reference)
