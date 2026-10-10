"""Exercise actual gateway proof, ownership, retry and cleanup boundaries."""

import hashlib
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from app.application.ports.image_processor import ImagePolicy
from app.application.use_cases.admin import CatalogAdminUseCases
from app.application.use_cases.media import UploadAvatar
from app.application.use_cases.media_cleanup import retire_unreferenced_media
from app.application.use_cases.platform import CustomerUseCases, OwnerUseCases
from app.core.exceptions import ValidationError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.media.pillow_processor import PillowImageProcessor
from tests.conftest import make_owner, make_profile
from tests.unit.test_image_processing import gateway, photo, photo_data


def stored_head(gw, path, data=photo_data):
    return {"ContentType": "image/jpeg", "ContentLength": len(data),
            "Metadata": gw._processed_metadata(path, data, "image/jpeg")}


@pytest.mark.parametrize("path,namespace", [
    ("avatars/user-001/photo.jpg", "avatars/user-001/"),
    ("salon-images/salon/photo.jpg", "salon-images/salon/"),
    ("staff-photos/salon/staff/photo.jpg", "staff-photos/salon/staff/"),
])
async def test_owned_proven_image_can_be_saved(path, namespace):
    gw = gateway()
    gw._client.head_object.return_value = stored_head(gw, path)
    await gw.validate_media_reference(gw.get_public_url("images", path), namespace)


@pytest.mark.parametrize("defect", ["missing", "unsigned", "tampered", "mime", "size", "policy"])
async def test_r2_looking_url_is_not_proof_of_processing(defect):
    gw = gateway()
    path = "avatars/user-001/photo.jpg"
    head = stored_head(gw, path)
    if defect == "missing":
        gw._client.head_object.side_effect = RuntimeError("not found")
    elif defect == "unsigned":
        head["Metadata"] = {}
    elif defect == "tampered":
        head["Metadata"]["processed-image-v1"] += " "
    elif defect == "mime":
        head["ContentType"] = "image/png"
    elif defect == "size":
        head["ContentLength"] += 1
    else:
        gw.settings.image_avatar_dimension = 32
    gw._client.head_object.return_value = head
    with pytest.raises(ValidationError):
        await gw.validate_media_reference(gw.get_public_url("images", path), "avatars/user-001/")


@pytest.mark.parametrize("url", [
    "https://evil.test/photo.jpg", "https://cdn.example.test/avatars/other/photo.jpg",
    "https://cdn.example.test/avatars/user-001/%2e%2e/photo.jpg",
    "https://cdn.example.test/avatars/user-001/photo.jpg?fake=1",
])
async def test_foreign_and_noncanonical_media_urls_rejected_without_fetching(url):
    gw = gateway()
    with pytest.raises(ValidationError):
        await gw.validate_media_reference(url, "avatars/user-001/")
    gw._client.head_object.assert_not_called()


@pytest.mark.parametrize("feature", ["customer", "staff", "gallery", "service", "catalog"])
async def test_url_saving_calls_gateway_before_database_write(feature):
    repo, storage = AsyncMock(), AsyncMock()
    repo.get_owner_salon.return_value = {"id": "salon"}
    repo.get_profile.return_value = {"avatar_url": None}
    repo.list_owner_staff.return_value = [{"id": "staff", "photo_url": "https://legacy.test/old.jpg"}]
    storage.validate_media_reference.side_effect = ValidationError("Unprocessed image")
    owner = OwnerUseCases(repo, storage)
    with pytest.raises(ValidationError):
        if feature == "customer":
            await CustomerUseCases(repo, storage).update_profile(make_profile(), {"avatar_url": "https://cdn.test/new.jpg"})
        elif feature == "staff":
            await owner.update_staff(make_owner(), "staff", {"photo_url": "https://cdn.test/new.jpg"})
        elif feature == "gallery":
            await owner.create_image(make_owner(), {"url": "https://cdn.test/new.jpg"})
        elif feature == "service":
            await owner.create_service(make_owner(), {"photo_url": "https://cdn.test/new.jpg"})
        else:
            from app.domain.entities.profile import Role
            await CatalogAdminUseCases(repo, storage).create_category(
                make_profile(role=Role.super_admin), {"image_url": "https://cdn.test/new.jpg"})
    repo.update_profile.assert_not_awaited()
    repo.update_owner_staff.assert_not_awaited()
    repo.create_salon_image.assert_not_awaited()
    repo.create_owner_service.assert_not_awaited()
    repo.create_category.assert_not_awaited()
    assert repo.lock_media_url.await_count >= 1
    assert all(call.args == ("https://cdn.test/new.jpg",) for call in repo.lock_media_url.await_args_list)


async def test_identical_put_retry_succeeds_without_overwriting_or_deleting():
    gw = gateway()
    path = "avatars/user-001/photo.jpg"
    token = (await gw.get_upload_url("images", path, "image/jpeg")).rsplit("/", 1)[-1]
    await gw.accept_upload(token, photo_data, "image/jpeg")
    written = gw._client.put_object.call_args.kwargs
    gw._client.head_object.return_value = {"Metadata": written["Metadata"],
                                          "ContentType": "image/jpeg", "ContentLength": len(written["Body"])}
    gw._client.put_object.side_effect = RuntimeError("Already exists")
    await gw.accept_upload(token, photo_data, "image/jpeg")
    other = BytesIO()
    Image.new("RGB", (64, 64), "green").save(other, "JPEG")
    with pytest.raises(ValidationError):
        await gw.accept_upload(token, other.getvalue(), "image/jpeg")
    gw._client.delete_object.assert_not_called()


@pytest.mark.parametrize("referenced", [True, False])
async def test_cleanup_deletes_only_after_locked_committed_reference_check(referenced):
    gw, repo = gateway(), AsyncMock()
    path = "staff-photos/salon/staff/photo.jpg"
    gw._client.head_object.return_value = stored_head(gw, path)
    repo.media_url_is_referenced.return_value = referenced
    assert await retire_unreferenced_media(repo, gw, "images", path) is (not referenced)
    repo.lock_media_url.assert_awaited_once_with(gw.get_public_url("images", path))
    if referenced:
        gw._client.delete_object.assert_not_called()
    else:
        gw._client.delete_object.assert_called_once_with(Bucket="images", Key=path)


async def test_cleanup_preserves_legacy_objects_and_retries_storage_or_database_failure():
    gw, repo = gateway(), AsyncMock()
    path = "avatars/user-001/photo.jpg"
    gw._client.head_object.return_value = {"Metadata": {}}
    assert not await retire_unreferenced_media(repo, gw, "images", path)
    repo.media_url_is_referenced.assert_not_awaited()
    gw._client.head_object.return_value = stored_head(gw, path)
    repo.media_url_is_referenced.side_effect = RuntimeError("Database unavailable")
    with pytest.raises(RuntimeError):
        await retire_unreferenced_media(repo, gw, "images", path)
    gw._client.delete_object.assert_not_called()
    repo.media_url_is_referenced.side_effect = None
    repo.media_url_is_referenced.return_value = False
    gw._client.delete_object.side_effect = RuntimeError("R2 unavailable")
    with pytest.raises(ValidationError):
        await retire_unreferenced_media(repo, gw, "images", path)
    gw._client.delete_object.side_effect = None
    assert await retire_unreferenced_media(repo, gw, "images", path)


async def test_cleanup_lists_aged_objects_across_pages_only():
    gw = gateway()
    old = datetime.now(timezone.utc) - timedelta(days=2)
    gw._client.list_objects_v2.side_effect = [
        {"Contents": [{"Key": "avatars/u/old.jpg", "LastModified": old}],
         "IsTruncated": True, "NextContinuationToken": "next"},
        {"Contents": [{"Key": "avatars/u/recent.jpg", "LastModified": datetime.now(timezone.utc)}]},
        {"Contents": []}, {"Contents": []},
    ]
    assert [path async for path in gw.cleanup_candidates()] == ["avatars/u/old.jpg"]
    assert gw._client.list_objects_v2.call_args_list[1].kwargs["ContinuationToken"] == "next"


def test_only_exact_server_outputs_skip_reencoding_and_policies_still_apply():
    processor = PillowImageProcessor()
    policy = ImagePolicy(512, 512000)
    processed = processor.process(photo(orientation=6), "image/jpeg", policy)
    with patch.object(Image.Image, "save", side_effect=AssertionError("Unexpected re-encoding")):
        assert processor.process(processed, "image/jpeg", policy) == processed
    with pytest.raises(ValidationError):
        processor.process(processed, "image/png", policy)
    with pytest.raises(ValidationError):
        processor.process(processed + b"junk", "image/jpeg", ImagePolicy(512, 1))
    with pytest.raises(ValidationError):
        PillowImageProcessor(max_pixels=1).process(processed, "image/jpeg", policy)
    smaller = processor.process(processed, "image/jpeg", ImagePolicy(128, 512000))
    assert hashlib.sha256(smaller).digest() != hashlib.sha256(processed).digest()
    with Image.open(BytesIO(smaller)) as image:
        assert max(image.size) == 128


async def test_avatar_replacement_and_failed_replacement_never_eagerly_delete_shared_media():
    repo, storage = AsyncMock(), AsyncMock()
    storage.upload_bytes.return_value = "https://cdn.test/avatars/user-001/new.jpg"
    use_case = UploadAvatar(repo, storage, PillowImageProcessor())
    await use_case.execute(make_profile(), photo_data, "image/jpeg", "images")
    repo.update_profile.side_effect = RuntimeError("Commit outcome unknown")
    with pytest.raises(RuntimeError):
        await use_case.execute(make_profile(), photo_data, "image/jpeg", "images")
    storage.delete_object.assert_not_awaited()


async def test_reference_query_fails_closed_on_rls_and_checks_every_media_table():
    session = AsyncMock()
    session.execute.return_value.scalar_one = lambda: True
    assert await PlatformRepository(session).media_url_is_referenced("https://cdn.test/photo.jpg")
    assert str(session.execute.call_args_list[0].args[0]) == "set local row_security = off"
    query = str(session.execute.call_args_list[1].args[0])
    for table in ("profiles", "staff", "salon_images", "services", "service_categories", "service_subcategories", "salons"):
        assert f"from {table} " in query


@pytest.mark.parametrize("kind,edge", [("avatar", 512), ("gallery", 1600), ("staff", 1024)])
async def test_signed_workflow_processes_http_bytes_then_validates_saved_reference(kind, edge):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.deps import get_storage_gateway
    from app.api.v1.routes.media import router

    repo, gw = AsyncMock(), gateway()
    repo.get_owner_salon.return_value = {"id": "salon"}
    repo.list_owner_staff.return_value = [{"id": "staff", "photo_url": None}]
    actor = make_owner()
    repo.get_profile.return_value = {"avatar_url": None}
    owner = OwnerUseCases(repo, gw)
    if kind == "avatar":
        grant = await CustomerUseCases(repo, gw).get_avatar_upload_url(actor, "image/jpeg", "camera.jpg", "images")
    elif kind == "gallery":
        grant = await owner.get_image_upload_url(actor, "image/jpeg", "gallery.jpg", "images")
    else:
        grant = await owner.get_staff_photo_upload_url(actor, "staff", "image/jpeg", "camera.jpg", "images")
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.dependency_overrides[get_storage_gateway] = lambda: gw
    original = photo(orientation=6)
    with TestClient(app) as client:
        response = client.put(grant["upload_url"].replace("https://api.example.test", ""),
                              content=original, headers={"Content-Type": "image/jpeg"})
    assert response.status_code == 204
    written = gw._client.put_object.call_args.kwargs
    assert written["Body"] != original
    with Image.open(BytesIO(written["Body"])) as image:
        assert image.height == edge
        assert image.height > image.width
        assert not image.getexif()
    gw._client.head_object.return_value = {"Metadata": written["Metadata"],
                                          "ContentType": written["ContentType"], "ContentLength": len(written["Body"])}
    if kind == "avatar":
        await CustomerUseCases(repo, gw).update_profile(actor, {"avatar_url": grant["public_url"]})
    elif kind == "gallery":
        await owner.create_image(actor, {"url": grant["public_url"]})
    else:
        await owner.update_staff(actor, "staff", {"photo_url": grant["public_url"]})
    gw._client.head_object.assert_called_once_with(Bucket="images", Key=written["Key"])
    assert repo.lock_media_url.await_count >= 1
    assert all(call.args == (grant["public_url"],) for call in repo.lock_media_url.await_args_list)


async def test_multipart_http_customer_avatar_stores_processed_pixels_and_proof(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.deps import get_authenticated_session, get_current_actor, get_storage_gateway
    from app.api.v1.routes import media

    repo, gw = AsyncMock(), gateway()
    monkeypatch.setattr(media, "PlatformRepository", lambda session: repo)
    app = FastAPI()
    app.include_router(media.router, prefix="/v1")
    app.dependency_overrides[get_current_actor] = lambda: make_profile()
    app.dependency_overrides[get_authenticated_session] = lambda: None
    app.dependency_overrides[get_storage_gateway] = lambda: gw
    original = photo()
    with TestClient(app) as client:
        response = client.post("/v1/customer/profile/avatar", files={"image": ("gallery.jpg", original, "image/jpeg")})
    assert response.status_code == 200
    written = gw._client.put_object.call_args.kwargs
    assert written["Body"] != original
    with Image.open(BytesIO(written["Body"])) as image:
        assert image.size == (512, 288)
    assert "processed-image-v1" in written["Metadata"]
    repo.update_profile.assert_awaited_once_with("user-001", {"avatar_url": response.json()["avatar_url"]})


async def test_staff_replacement_preserves_shared_old_object_and_checks_new_namespace():
    repo, storage = AsyncMock(), AsyncMock()
    repo.get_owner_salon.return_value = {"id": "salon"}
    repo.list_owner_staff.return_value = [{"id": "staff", "photo_url": "https://legacy.test/shared.jpg"}]
    new_url = "https://cdn.test/staff-photos/salon/staff/new.jpg"
    use_case = OwnerUseCases(repo, storage)
    await use_case.update_staff(make_owner(), "staff", {"photo_url": new_url})
    storage.validate_media_reference.assert_awaited_once_with(new_url, "staff-photos/salon/staff/")
    repo.update_owner_staff.side_effect = RuntimeError("Save failed")
    with pytest.raises(RuntimeError):
        await use_case.update_staff(make_owner(), "staff", {"photo_url": new_url})
    storage.delete_object.assert_not_awaited()


async def test_stale_auth_avatar_snapshot_cannot_restore_deleted_or_unproven_media():
    from dataclasses import replace

    actor = replace(make_profile(), avatar_url="https://legacy.test/old.jpg")
    repo, storage = AsyncMock(), AsyncMock()
    repo.get_profile.return_value = {"avatar_url": "https://cdn.test/replacement.jpg"}
    storage.validate_media_reference.side_effect = ValidationError("Missing old object")
    with pytest.raises(ValidationError):
        await CustomerUseCases(repo, storage).update_profile(actor, {"avatar_url": actor.avatar_url})
    repo.update_profile.assert_not_awaited()
    storage.validate_media_reference.assert_awaited_once_with(actor.avatar_url, "avatars/user-001/")


async def test_staff_creation_cannot_reuse_a_gallery_photo_above_staff_dimensions():
    repo, gw = AsyncMock(), gateway()
    repo.get_owner_salon.return_value = {"id": "salon"}
    path = "salon-images/salon/photo.jpg"
    data = PillowImageProcessor().process(photo(), "image/jpeg", ImagePolicy(1600, 1048576))
    gw._client.head_object.return_value = stored_head(gw, path, data)
    with pytest.raises(ValidationError, match="media category"):
        await OwnerUseCases(repo, gw).create_staff(make_owner(), {"photo_url": gw.get_public_url("images", path)})
    repo.create_owner_staff.assert_not_awaited()


@pytest.mark.parametrize("method", ["create_category", "update_category", "create_subcategory", "update_subcategory"])
async def test_all_admin_catalog_image_writes_reject_unmarked_objects(method):
    from app.domain.entities.profile import Role

    repo, gw = AsyncMock(), gateway()
    repo.get_category.return_value = {"image_url": None}
    repo.get_subcategory.return_value = {"image_url": None}
    gw._client.head_object.return_value = {"Metadata": {}}
    use_case = CatalogAdminUseCases(repo, gw)
    values = {"image_url": gw.get_public_url("images", "salon-images/salon/photo.jpg")}
    args = (make_profile(role=Role.super_admin), values)
    if method.startswith("update"):
        args = (args[0], "catalog-id", values)
    with pytest.raises(ValidationError):
        await getattr(use_case, method)(*args)
    getattr(repo, method).assert_not_awaited()


async def test_gallery_url_replacement_checks_processing_proof_before_write():
    repo, gw = AsyncMock(), gateway()
    repo.get_owner_salon.return_value = {"id": "salon"}
    repo.list_salon_images.return_value = [{"id": "image", "url": "https://legacy.test/old.jpg"}]
    gw._client.head_object.return_value = {"Metadata": {}}
    with pytest.raises(ValidationError):
        await OwnerUseCases(repo, gw).update_image(make_owner(), "image", {
            "url": gw.get_public_url("images", "salon-images/salon/unprocessed.jpg"),
        })
    repo.update_salon_image.assert_not_awaited()


async def test_unchanged_legacy_avatar_is_compared_under_lock_before_save():
    from dataclasses import replace

    actor = replace(make_profile(), avatar_url="https://legacy.test/shared.jpg")
    repo, storage = AsyncMock(), AsyncMock()
    repo.get_profile.return_value = {"avatar_url": actor.avatar_url}
    calls = []

    async def lock(url):
        calls.append("lock")

    async def current(profile_id):
        calls.append("read")
        return {"avatar_url": actor.avatar_url}

    async def save(profile_id, values):
        calls.append("save")
        return values

    repo.lock_media_url.side_effect = lock
    repo.get_profile.side_effect = current
    repo.update_profile.side_effect = save
    await CustomerUseCases(repo, storage).update_profile(actor, {"avatar_url": actor.avatar_url})
    assert calls == ["lock", "read", "save"]
    storage.validate_media_reference.assert_not_awaited()


async def test_gallery_attach_retry_returns_existing_row_without_duplicate_insert():
    from unittest.mock import MagicMock

    session = AsyncMock()
    row = {"id": "image", "url": "https://cdn.test/salon-images/salon/photo.jpg"}
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = row
    session.execute.return_value = result
    repository = PlatformRepository(session)
    with patch.object(repository, "get_owner_salon", AsyncMock(return_value={"id": "salon"})):
        assert await repository.create_salon_image("owner", {"url": row["url"]}) == row
    assert session.execute.await_count == 1
    session.commit.assert_awaited_once()


async def test_scheduled_worker_continues_after_failed_cleanup_and_retries_next_sweep(monkeypatch):
    from unittest.mock import MagicMock

    from app.infrastructure.media import cleanup_worker

    gw = gateway()
    paths = ["avatars/user-001/first.jpg", "avatars/user-001/second.jpg"]

    async def candidates():
        for path in paths:
            yield path

    gw.cleanup_candidates = candidates
    session = AsyncMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    monkeypatch.setattr(cleanup_worker, "AsyncSessionLocal", session_factory)
    references = AsyncMock()
    references.media_reference_guards_installed.return_value = True
    monkeypatch.setattr(cleanup_worker, "PlatformRepository", lambda session: references)
    monkeypatch.setattr(cleanup_worker, "R2StorageGateway", lambda settings: gw)
    monkeypatch.setattr(cleanup_worker.settings, "r2_bucket", "images")
    retire = AsyncMock(side_effect=[RuntimeError("Transient failure"), True, True, False])
    monkeypatch.setattr(cleanup_worker, "retire_unreferenced_media", retire)
    assert await cleanup_worker.sweep_media() == 1
    assert await cleanup_worker.sweep_media() == 1
    assert retire.await_count == 4
    assert session.commit.await_count == 3


async def test_cleanup_worker_refuses_to_scan_before_database_guards_are_installed(monkeypatch):
    from unittest.mock import MagicMock

    from app.infrastructure.media import cleanup_worker

    gw, references = gateway(), AsyncMock()
    references.media_reference_guards_installed.return_value = False
    gw.cleanup_candidates = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock()
    monkeypatch.setattr(cleanup_worker, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(cleanup_worker, "PlatformRepository", lambda session: references)
    monkeypatch.setattr(cleanup_worker, "R2StorageGateway", lambda settings: gw)
    monkeypatch.setattr(cleanup_worker.settings, "r2_bucket", "images")
    with pytest.raises(RuntimeError, match="0020_media_reference_guards"):
        await cleanup_worker.sweep_media()
    gw.cleanup_candidates.assert_not_called()
    gw._client.delete_object.assert_not_called()
