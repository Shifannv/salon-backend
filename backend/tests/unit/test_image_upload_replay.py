"""Publication safety checks against actual upload use cases and R2 calls."""
from dataclasses import replace
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from app.application.use_cases.platform import CustomerUseCases, OwnerUseCases
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.r2.storage import R2StorageGateway
from tests.conftest import make_owner, make_profile


def gateway():
    result = R2StorageGateway(Settings(_env_file=None, r2_account_id="test",
        r2_access_key_id="test", r2_secret_access_key="test", r2_bucket="images",
        r2_public_url="https://cdn.test", public_api_base_url="https://api.test"))
    result._client = MagicMock()
    return result


async def test_upload_capability_cannot_overwrite_a_published_object():
    gw = gateway()
    token = (await gw.get_upload_url("images", "avatars/u/photo.jpg", "image/jpeg")).rsplit("/", 1)[-1]
    data = BytesIO()
    Image.new("RGB", (80, 40), "red").save(data, "JPEG")
    await gw.accept_upload(token, data.getvalue(), "image/jpeg")
    assert gw._client.put_object.call_args.kwargs["IfNoneMatch"] == "*"
    gw._client.put_object.side_effect = RuntimeError("precondition failed")
    with pytest.raises(ValidationError):
        await gw.accept_upload(token, data.getvalue(), "image/jpeg")
    gw._client.delete_object.assert_not_called()


async def test_avatar_grants_have_distinct_keys():
    gw = gateway()
    uc = CustomerUseCases(AsyncMock(), gw)
    first = await uc.get_avatar_upload_url(make_profile(), "image/jpeg", "a.jpg", "images")
    second = await uc.get_avatar_upload_url(make_profile(), "image/jpeg", "a.jpg", "images")
    assert first["public_url"] != second["public_url"]


async def test_staff_grant_requires_owned_staff_before_storage():
    repo, storage = AsyncMock(), AsyncMock()
    repo.get_owner_salon.return_value = {"id": "salon"}
    repo.list_owner_staff.return_value = [{"id": "ours"}]
    with pytest.raises(NotFoundError):
        await OwnerUseCases(repo, storage).get_staff_photo_upload_url(
            make_owner(), "foreign", "image/jpeg", "a.jpg", "images")
    storage.get_upload_url.assert_not_awaited()


async def test_profile_write_failure_preserves_previous_image():
    repo, storage = AsyncMock(), AsyncMock()
    repo.update_profile.side_effect = RuntimeError("write failed")
    actor = replace(make_profile(), avatar_url="https://cdn.test/avatars/u/old.jpg")
    repo.get_profile.return_value = {"avatar_url": actor.avatar_url}
    with pytest.raises(RuntimeError):
        await CustomerUseCases(repo, storage).update_profile(actor,
            {"avatar_url": "https://cdn.test/avatars/u/new.jpg"}, bucket="images", r2_public_base="https://cdn.test")
    storage.delete_object.assert_not_awaited()




@pytest.mark.parametrize("schema,values", [
    ("ProfileUpdateRequest", {"avatar_url": "data:image/png;base64,AAAA"}),
    ("StaffCreateRequest", {"full_name": "Staff", "photo_url": "data:image/png;base64,AAAA"}),
    ("StaffUpdateRequest", {"photo_url": "file:///photo.png"}),
    ("SalonImageCreateRequest", {"url": "data:image/jpeg;base64,AAAA"}),
    ("SalonImageUpdateRequest", {"url": "blob:original"}),
])
def test_inline_images_cannot_enter_media_records_or_cached_responses(schema, values):
    from pydantic import ValidationError as SchemaError

    from app.api.v1.schemas import platform
    with pytest.raises(SchemaError):
        getattr(platform, schema)(**values)


def test_existing_hosted_media_urls_and_clearing_remain_supported():
    from app.api.v1.schemas.platform import ProfileUpdateRequest, StaffUpdateRequest
    assert ProfileUpdateRequest(avatar_url="https://cdn.test/old.png").avatar_url == "https://cdn.test/old.png"
    assert ProfileUpdateRequest(avatar_url=None).avatar_url is None
    assert StaffUpdateRequest(photo_url="http://localhost/photo.png").photo_url == "http://localhost/photo.png"
