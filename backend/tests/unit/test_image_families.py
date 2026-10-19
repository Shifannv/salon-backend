"""Real image-family gateway/use-case flows against a stateful fake R2 client."""

import asyncio
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app.application.use_cases.account_erasure import AccountErasureService
from app.application.use_cases.media import UploadAvatar
from app.application.use_cases.media_cleanup import retire_unreferenced_media
from app.application.use_cases.media_publication import validate_media_reference
from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.infrastructure.media.pillow_processor import PillowImageProcessor
from app.infrastructure.r2.storage import R2StorageGateway
from tests.conftest import make_profile
from tests.unit.media_r2_fake import FakeR2Client
from tests.unit.test_image_processing import photo

BUCKET = "synthetic-images"
BASE = "https://media.example.test/"
NAMESPACE = "salon-images/salon-one/"


@pytest.fixture
def gateway():
    settings = Settings(
        _env_file=None, environment="test", r2_account_id="synthetic",
        r2_access_key_id="synthetic", r2_secret_access_key="synthetic-signing-key",
        r2_bucket=BUCKET, r2_public_url=BASE, public_api_base_url="https://api.example.test",
    )
    storage = R2StorageGateway(settings)
    storage._client = FakeR2Client()
    return storage


@pytest.fixture
def family():
    return PillowImageProcessor().process_family(photo((960, 640)), "image/jpeg", "gallery")


def key(url):
    assert url.startswith(BASE)
    return url[len(BASE):]


def references(*urls):
    refs = MagicMock()
    refs.lock_media_url = AsyncMock()
    refs.media_url_is_referenced = AsyncMock(side_effect=lambda url: url in urls)
    return refs


def age_objects(gateway):
    past = datetime.now(timezone.utc) - timedelta(days=2)
    for item in gateway._client.objects.values():
        item["LastModified"] = past


async def upload(gateway, family, alias="upload.jpg", namespace=NAMESPACE):
    return await gateway.upload_processed_family(BUCKET, namespace, family, alias=namespace + alias)


@pytest.mark.asyncio
async def test_distinct_grants_share_immutable_keys_but_accounts_do_not(gateway):
    data = photo((960, 640))
    tokens = []
    for account, name in [("salon-one", "one"), ("salon-one", "two"), ("salon-two", "one")]:
        url = await gateway.get_upload_url(BUCKET, f"salon-images/{account}/{name}.jpg", "image/jpeg")
        tokens.append(url.rsplit("/", 1)[1])
    first, second, other = [await gateway.accept_upload(token, data, "image/jpeg") for token in tokens]
    assert first["variants"] == second["variants"]
    assert first["public_url"] != second["public_url"]
    assert first["family_id"] != other["family_id"]
    assert {v["url"] for v in first["variants"].values()}.isdisjoint(
        v["url"] for v in other["variants"].values())
    for variant, metadata in first["variants"].items():
        assert f"/webp-v2/{first['family_id']}/{variant}-{metadata['sha256']}.webp" in metadata["url"]
    with pytest.raises(ValidationError, match="account"):
        await gateway.validate_media_reference(first["public_url"], "salon-images/salon-two/")


@pytest.mark.asyncio
async def test_duplicate_and_concurrent_uploads_reuse_identical_members(gateway, family):
    first, second = await asyncio.gather(upload(gateway, family, "one.jpg"), upload(gateway, family, "two.jpg"))
    assert first["variants"] == second["variants"]
    before = deepcopy(gateway._client.objects)
    assert await upload(gateway, family, "one.jpg") == first
    assert gateway._client.objects == before
    assert len(before) == 5  # Three immutable variants and two compatibility aliases.


@pytest.mark.asyncio
@pytest.mark.parametrize("failed_attempt", [1, 2, 3, 4])
async def test_partial_upload_cannot_publish_and_same_upload_retries(gateway, family, failed_attempt):
    gateway._client.fail_put_at.add(failed_attempt)
    with pytest.raises(ValidationError, match="family upload failed"):
        await upload(gateway, family)
    assert len(gateway._client.objects) == failed_attempt - 1
    alias = BASE + NAMESPACE + "upload.jpg"
    with pytest.raises(ValidationError):
        await validate_media_reference(references(), gateway, alias, NAMESPACE)
    result = await upload(gateway, family)
    await gateway.validate_media_reference(result["public_url"], NAMESPACE)
    assert len(gateway._client.objects) == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("lost_at", [1, 2, 3, 4])
async def test_lost_upload_response_is_recovered_only_by_verified_head(gateway, family, lost_at):
    gateway._client.lose_response_at.add(lost_at)
    result = await upload(gateway, family)
    assert len(gateway._client.objects) == 4
    await gateway.validate_media_reference(result["public_url"], NAMESPACE)


@pytest.mark.asyncio
@pytest.mark.parametrize("written_objects", [1, 2, 3, 4])
async def test_failure_to_verify_each_written_member_prevents_success(gateway, family, written_objects):
    original = gateway._client.head_object.side_effect
    failed_once = False

    def fail_verification(**kwargs):
        nonlocal failed_once
        if gateway._client.put_attempts == written_objects and not failed_once:
            failed_once = True
            raise TimeoutError("Synthetic post-upload verification failure")
        return original(**kwargs)

    gateway._client.head_object.side_effect = fail_verification
    with pytest.raises(ValidationError, match="family upload failed"):
        await upload(gateway, family)
    assert len(gateway._client.objects) == written_objects
    result = await upload(gateway, family)
    await gateway.validate_media_reference(result["public_url"], NAMESPACE)


@pytest.mark.asyncio
async def test_reused_capability_cannot_replace_immutable_alias(gateway, family):
    first = await upload(gateway, family)
    before = deepcopy(gateway._client.objects[key(first["public_url"])])
    different = PillowImageProcessor().process_family(photo((700, 900)), "image/jpeg", "gallery")
    with pytest.raises(ValidationError, match="family upload failed"):
        await upload(gateway, different)
    assert gateway._client.objects[key(first["public_url"])] == before
    await gateway.validate_media_reference(first["public_url"], NAMESPACE)


@pytest.mark.asyncio
async def test_bad_ack_requires_matching_head_not_an_unchecked_success(gateway, family):
    gateway._client.bad_response_at.add(2)
    result = await upload(gateway, family)
    assert len(result["variants"]) == 3
    assert gateway._client.head_object.call_count >= 8


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", [
    "unsigned", "signature", "width", "height", "variant", "mime", "family", "size",
    "sha256", "policy_version",
])
async def test_unsigned_or_invalid_signed_metadata_is_rejected(gateway, family, mutation):
    result = await upload(gateway, family)
    path = key(result["public_url"])
    stored = gateway._client.objects[path]
    metadata = stored["Metadata"]
    if mutation == "unsigned":
        stored["Metadata"] = {}
    elif mutation == "signature":
        metadata["processed-signature"] = "invalid"
    else:
        proof = json.loads(metadata["processed-image-v2"])
        if mutation == "width":
            proof["width"] = 999999
        elif mutation == "height":
            proof["height"] = 999999
        elif mutation == "variant":
            proof["variant"] = "unapproved"
        elif mutation == "mime":
            proof["mime"] = "image/png"
        elif mutation == "family":
            proof["family_id"] = "0" * 64
        elif mutation == "size":
            proof["size"] += 1
        elif mutation == "sha256":
            proof["sha256"] = "0" * 64
        elif mutation == "policy_version":
            proof["policy_version"] = "unapproved"
        stored["Metadata"] = gateway._family_metadata(proof)
    with pytest.raises(ValidationError):
        await gateway.validate_media_reference(result["public_url"], NAMESPACE)


@pytest.mark.asyncio
async def test_partial_family_cannot_be_published_through_a_valid_remaining_member(gateway, family):
    result = await upload(gateway, family)
    gateway._client.objects.pop(key(result["variants"]["card"]["url"]))
    with pytest.raises(ValidationError):
        await gateway.validate_media_reference(result["public_url"], NAMESPACE)
    with pytest.raises(ValidationError):
        await gateway.validate_media_reference(result["variants"]["detail"]["url"], NAMESPACE)


@pytest.mark.asyncio
@pytest.mark.parametrize("referenced", ["alias", "thumbnail", "card", "detail", "second_alias"])
async def test_any_reference_protects_entire_family(gateway, family, referenced):
    result = await upload(gateway, family)
    second = await upload(gateway, family, "second.jpg")
    age_objects(gateway)
    url = {"alias": result["public_url"], "second_alias": second["public_url"]}.get(referenced)
    if url is None:
        url = result["variants"][referenced]["url"]
    refs = references(url)
    before = deepcopy(gateway._client.objects)
    assert not await retire_unreferenced_media(refs, gateway, BUCKET, key(result["public_url"]))
    assert gateway._client.objects == before
    assert refs.lock_media_url.await_count == 3


@pytest.mark.asyncio
async def test_partial_family_cleanup_removes_remaining_members_and_preserves_unmarked(gateway, family):
    gateway._client.fail_put_at.add(3)
    with pytest.raises(ValidationError):
        await upload(gateway, family)
    first = next(iter(gateway._client.objects))
    gateway._client.put_object(Bucket=BUCKET, Key=NAMESPACE + "legacy.jpg", Body=b"legacy")
    age_objects(gateway)
    assert await retire_unreferenced_media(references(), gateway, BUCKET, first)
    assert set(gateway._client.objects) == {NAMESPACE + "legacy.jpg"}
    assert not await retire_unreferenced_media(references(), gateway, BUCKET, NAMESPACE + "legacy.jpg")


@pytest.mark.asyncio
async def test_fresh_alias_protects_deduplicated_old_family_during_attachment(gateway, family):
    old = await upload(gateway, family)
    age_objects(gateway)
    fresh = await upload(gateway, family, "fresh.jpg")
    assert fresh["variants"] == old["variants"]
    before = deepcopy(gateway._client.objects)
    assert not await retire_unreferenced_media(
        references(), gateway, BUCKET, key(old["variants"]["card"]["url"]),
    )
    assert gateway._client.objects == before
    age_objects(gateway)
    assert await retire_unreferenced_media(
        references(), gateway, BUCKET, key(old["variants"]["card"]["url"]),
    )
    assert not gateway._client.objects


@pytest.mark.asyncio
async def test_avatar_database_rollback_preserves_prior_reference_and_does_not_delete(gateway):
    actor = make_profile()
    old = "https://legacy.example.test/previous.jpg"

    class Repository:
        avatar_url = old
        lock_media_url = AsyncMock()

        async def update_profile(self, profile_id, values):
            # Model a transaction rejected before commit; no R2 rollback is allowed.
            raise RuntimeError("Synthetic database rollback")

    repository = Repository()
    use_case = UploadAvatar(repository, gateway, PillowImageProcessor())
    with pytest.raises(RuntimeError, match="rollback"):
        await use_case.execute_family(actor, photo((800, 600)), "image/jpeg", BUCKET)
    assert repository.avatar_url == old
    assert gateway._client.objects
    gateway._client.delete_object.assert_not_called()


def erasure_service(gateway, *referenced):
    service = AccountErasureService.__new__(AccountErasureService)
    service.storage = gateway
    service.bucket = BUCKET
    service.storage_required = True
    service.media_references = references(*referenced)
    service.release_media_lock = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_erasure_same_family_multiple_recorded_urls_and_retries_are_idempotent(gateway, family):
    first = await upload(gateway, family)
    second = await upload(gateway, family, "second.jpg")
    urls = [first["public_url"], second["public_url"], first["variants"]["card"]["url"]]
    service = erasure_service(gateway)
    await service._delete_media(urls)
    assert not gateway._client.objects
    await service._delete_media(urls)
    assert not gateway._client.objects


@pytest.mark.asyncio
async def test_erasure_keeps_anchor_for_midway_delete_failure_and_retry(gateway, family):
    result = await upload(gateway, family)
    anchor = key(result["public_url"])
    failed = key(result["variants"]["card"]["url"])
    gateway._client.fail_delete_keys.add(failed)
    service = erasure_service(gateway)
    with pytest.raises(ValidationError, match="delete"):
        await service._delete_media([result["public_url"]])
    assert anchor in gateway._client.objects
    assert key(result["variants"]["thumbnail"]["url"]) not in gateway._client.objects
    gateway._client.fail_delete_keys.clear()
    await service._delete_media([result["public_url"]])
    assert not gateway._client.objects
    assert service.release_media_lock.await_count == 2


@pytest.mark.asyncio
async def test_erasure_legacy_and_missing_404_are_idempotent(gateway):
    path = "avatars/user-one/legacy.jpg"
    gateway._client.put_object(Bucket=BUCKET, Key=path, Body=b"legacy")
    service = erasure_service(gateway)
    await service._delete_media([BASE + path, BASE + "avatars/user-one/missing.jpg"])
    assert not gateway._client.objects
    await service._delete_media([BASE + path])


@pytest.mark.asyncio
async def test_erasure_preserves_family_shared_by_another_reference(gateway, family):
    result = await upload(gateway, family)
    service = erasure_service(gateway, result["variants"]["thumbnail"]["url"])
    await service._delete_media([result["public_url"]])
    assert len(gateway._client.objects) == 4


@pytest.mark.asyncio
async def test_namespace_inventory_head_failure_stops_cleanup(gateway, family):
    result = await upload(gateway, family)
    original = gateway._client.head_object.side_effect

    def unavailable_alias(**kwargs):
        if kwargs["Key"] == key(result["public_url"]):
            raise TimeoutError("Synthetic inventory failure")
        return original(**kwargs)

    gateway._client.head_object.side_effect = unavailable_alias
    with pytest.raises(TimeoutError):
        await retire_unreferenced_media(references(), gateway, BUCKET, key(result["variants"]["card"]["url"]))
    gateway._client.delete_object.assert_not_called()


@pytest.mark.asyncio
async def test_signed_head_metadata_with_error_status_is_not_a_verified_object(gateway, family):
    result = await upload(gateway, family)
    original = gateway._client.head_object.side_effect

    def error_status(**kwargs):
        response = original(**kwargs)
        response["ResponseMetadata"]["HTTPStatusCode"] = 500
        return response

    gateway._client.head_object.side_effect = error_status
    with pytest.raises(ValidationError):
        await gateway.validate_media_reference(result["public_url"], NAMESPACE)


@pytest.fixture
def api_client(gateway, monkeypatch):
    from app.api.deps import get_authenticated_session, get_current_actor, get_storage_gateway
    from app.api.v1.routes import media
    from app.core.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "r2_bucket", BUCKET)
    repository = AsyncMock()
    monkeypatch.setattr(media, "PlatformRepository", lambda session: repository)
    app = create_app()
    app.dependency_overrides[get_current_actor] = lambda: make_profile()
    app.dependency_overrides[get_authenticated_session] = lambda: MagicMock()
    app.dependency_overrides[get_storage_gateway] = lambda: gateway
    # No context manager: lifespan deliberately never starts a DB/cache connection.
    client = TestClient(app)
    yield client, repository
    client.close()


def test_real_api_grant_put_204_and_result_preserve_legacy_public_url(api_client, gateway):
    client, repository = api_client
    grant_response = client.post("/v1/profiles/me/avatar-upload-url", json={
        "filename": "synthetic.jpg", "content_type": "image/jpeg",
    })
    assert grant_response.status_code == 200
    grant = grant_response.json()
    assert grant["result_url"] != grant["upload_url"]
    assert "/v1/media/results/" in grant["result_url"]
    assert grant["upload_url"].rsplit("/", 1)[-1] not in grant["result_url"]
    assert grant["expires_in"] == 300
    path = urlsplit(grant["upload_url"]).path
    result_path = urlsplit(grant["result_url"]).path
    assert client.get(result_path).status_code == 422  # A grant is not an uploaded family.
    assert client.get(path).status_code in {404, 405}  # Upload capability is not a read endpoint.
    response = client.put(path, content=photo((900, 600)), headers={"content-type": "image/jpeg"})
    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["link"] == f'<{grant["result_url"]}>; rel="describedby"'
    assert grant["upload_url"] not in response.headers["link"]
    result_response = client.get(result_path)
    assert result_response.status_code == 200
    result = result_response.json()
    assert result_response.headers["cache-control"] == "no-store"
    assert response.headers["x-image-family-id"] == result["family_id"]
    assert result["public_url"] == grant["public_url"]
    alias = gateway._client.objects[key(grant["public_url"])]
    assert alias["ContentType"] == "image/webp"
    assert alias["Body"][:4] == b"RIFF" and alias["Body"][8:12] == b"WEBP"
    assert set(result["variants"]) == {"avatar"}
    variant = result["variants"]["avatar"]
    assert variant["width"] == 512 and variant["height"] <= 512
    assert variant["mime"] == "image/webp"
    assert variant["size"] == len(gateway._client.objects[key(variant["url"])]["Body"])
    repository.update_profile.assert_not_awaited()


def test_result_token_is_read_only_and_upload_token_is_not_a_result_token(api_client, gateway):
    client, _ = api_client
    grant = client.post("/v1/profiles/me/avatar-upload-url", json={
        "filename": "synthetic.jpg", "content_type": "image/jpeg",
    }).json()
    upload_token = grant["upload_url"].rsplit("/", 1)[-1]
    result_token = grant["result_url"].rsplit("/", 1)[-1]
    put = client.put(f"/v1/media/uploads/{result_token}", content=photo((900, 600)),
                     headers={"content-type": "image/jpeg"})
    assert put.status_code == 422
    assert client.get(f"/v1/media/results/{upload_token}").status_code == 422
    assert not gateway._client.objects, "a rejected token must not create objects"


def test_result_url_expires_with_the_grant(api_client, gateway, monkeypatch):
    import time as _time

    client, _ = api_client
    grant = client.post("/v1/profiles/me/avatar-upload-url", json={
        "filename": "synthetic.jpg", "content_type": "image/jpeg",
    }).json()
    real = _time.time()
    monkeypatch.setattr("app.infrastructure.r2.storage.time.time", lambda: real + 301)
    assert client.get(urlsplit(grant["result_url"]).path).status_code == 422


class _Clock:
    """Controllable clock for the storage module only."""

    def __init__(self, monkeypatch):
        import time as _time
        from types import SimpleNamespace

        self.now = _time.time()
        monkeypatch.setattr("app.infrastructure.r2.storage.time", SimpleNamespace(time=lambda: self.now))


def _grant(client):
    return client.post("/v1/profiles/me/avatar-upload-url", json={
        "filename": "synthetic.jpg", "content_type": "image/jpeg",
    }).json()


def test_put_with_query_string_commits_and_returns_204_with_the_result_link(api_client, gateway):
    client, _ = api_client
    grant = _grant(client)
    path = urlsplit(grant["upload_url"]).path
    response = client.put(path + "?cache=1&x=2", content=photo((900, 600)),
                          headers={"content-type": "image/jpeg"})
    assert response.status_code == 204
    assert gateway._client.objects
    # Derived from the validated path token: identical to the grant's result URL.
    assert response.headers["link"] == f'<{grant["result_url"]}>; rel="describedby"'
    assert grant["upload_url"].rsplit("/", 1)[-1] not in response.headers["link"]
    assert client.get(urlsplit(grant["result_url"]).path).status_code == 200


def test_expiry_crossed_during_processing_stores_nothing_and_reports_the_failure(api_client, gateway, monkeypatch):
    from app.infrastructure.r2.storage import PillowImageProcessor as Processor

    client, _ = api_client
    clock = _Clock(monkeypatch)
    grant = _grant(client)
    original = Processor.process_family_async

    async def slow(self, *args, **kwargs):
        result = await original(self, *args, **kwargs)
        clock.now += 301
        return result

    monkeypatch.setattr(Processor, "process_family_async", slow)
    response = client.put(urlsplit(grant["upload_url"]).path, content=photo((900, 600)),
                          headers={"content-type": "image/jpeg"})
    assert response.status_code == 422
    assert not gateway._client.objects, "an expired capability must not store anything"
    assert "link" not in response.headers


def test_expiry_crossed_during_storage_still_returns_204_and_extends_nothing(api_client, gateway, monkeypatch):
    client, _ = api_client
    clock = _Clock(monkeypatch)
    grant = _grant(client)
    original = gateway.upload_processed_family

    async def slow_store(*args, **kwargs):
        result = await original(*args, **kwargs)
        clock.now += 301  # the grant expires after the final pre-storage check
        return result

    monkeypatch.setattr(gateway, "upload_processed_family", slow_store)
    path = urlsplit(grant["upload_url"]).path
    response = client.put(path, content=photo((900, 600)), headers={"content-type": "image/jpeg"})
    assert response.status_code == 204, "committed storage must not be reported as an error"
    assert gateway._client.objects
    assert response.headers["link"] == f'<{grant["result_url"]}>; rel="describedby"'
    stored = len(gateway._client.objects)
    # Nothing is extended: the same upload capability and the result link are now expired.
    assert client.get(urlsplit(grant["result_url"]).path).status_code == 422
    again = client.put(path, content=photo((900, 600)), headers={"content-type": "image/jpeg"})
    assert again.status_code == 422
    assert len(gateway._client.objects) == stored


def test_failure_to_derive_the_link_never_turns_a_stored_upload_into_an_error(api_client, gateway, monkeypatch):
    client, _ = api_client
    grant = _grant(client)

    def broken(_token):
        raise ValidationError("synthetic link failure")

    monkeypatch.setattr(gateway, "get_result_url", broken)
    response = client.put(urlsplit(grant["upload_url"]).path, content=photo((900, 600)),
                          headers={"content-type": "image/jpeg"})
    assert response.status_code == 204
    assert gateway._client.objects
    assert "link" not in response.headers


def test_token_purposes_stay_cryptographically_separate(gateway):
    import asyncio

    upload_url = asyncio.run(gateway.get_upload_url(BUCKET, f"{NAMESPACE}a.jpg", "image/jpeg"))
    upload_token = upload_url.rsplit("/", 1)[-1]
    result_token = gateway.get_result_url(upload_token).rsplit("/", 1)[-1]
    assert upload_token != result_token
    gateway.validate_upload_token(upload_token, "image/jpeg")
    with pytest.raises(ValidationError):
        gateway.validate_upload_token(result_token, "image/jpeg")
    gateway._result_claims(result_token)
    with pytest.raises(ValidationError):
        gateway._result_claims(upload_token)
    # A result token is bound to its own claims: it cannot be re-signed into an upload token.
    payload, signature = result_token.split(".")
    with pytest.raises(ValidationError):
        gateway._claims(f"{payload}.{signature}", "image/jpeg")


def test_real_api_multipart_returns_family_and_legacy_avatar_field(api_client, gateway):
    client, repository = api_client
    response = client.post("/v1/customer/profile/avatar", files={
        "image": ("synthetic.png", photo((900, 600), fmt="PNG", alpha=True), "image/png"),
    })
    assert response.status_code == 200
    result = response.json()
    assert result["policy_version"] == "webp-v2"
    assert len(result["family_id"]) == 64
    assert set(result["variants"]) == {"avatar"}
    assert result["avatar_url"] == result["variants"]["avatar"]["url"]
    assert set(result["variants"]["avatar"]) == {
        "variant", "url", "width", "height", "mime", "size", "sha256",
    }
    assert gateway._client.objects[key(result["avatar_url"])]["ContentType"] == "image/webp"
    repository.update_profile.assert_awaited_once_with(
        make_profile().id, {"avatar_url": result["avatar_url"]},
    )


def test_integrated_admission_rejects_oversized_multipart_before_parser(api_client, gateway, monkeypatch):
    from starlette.requests import Request

    client, repository = api_client
    parser = MagicMock(side_effect=AssertionError("Multipart parser must not run"))
    monkeypatch.setattr(Request, "form", parser)
    response = client.post("/v1/customer/profile/avatar", files={
        "image": ("oversized.jpg", b"x" * (5_242_880 + 65_536), "image/jpeg"),
    })
    assert response.status_code == 413
    parser.assert_not_called()
    gateway._client.put_object.assert_not_called()
    repository.update_profile.assert_not_awaited()


def test_integrated_multipart_rejects_multiple_files_before_processing(api_client, gateway):
    client, repository = api_client
    response = client.post("/v1/customer/profile/avatar", files=[
        ("image", ("one.jpg", photo((64, 64)), "image/jpeg")),
        ("image", ("two.jpg", photo((64, 64)), "image/jpeg")),
    ])
    assert response.status_code == 400
    gateway._client.put_object.assert_not_called()
    repository.update_profile.assert_not_awaited()


@pytest.mark.asyncio
async def test_concurrent_avatar_commit_failure_and_cleanup_keep_committed_family(gateway):
    """Transaction-lock model only; real PostgreSQL locking is tested separately."""
    state = {"avatar_url": "https://legacy.example.test/old.jpg"}
    locks = {}
    success_pending, failed_pending = asyncio.Event(), asyncio.Event()
    allow_success, allow_failure = asyncio.Event(), asyncio.Event()

    class Transaction:
        def __init__(self, fail=False):
            self.fail = fail
            self.held = []
            self.assigned = None

        async def lock_media_url(self, url):
            # Match the repository's shared family lock before member URL locks.
            family = url.rsplit("/", 1)[0] if "/webp-v2/" in url else url
            if family not in [name for name, _ in self.held]:
                lock = locks.setdefault(family, asyncio.Lock())
                await lock.acquire()
                self.held.append((family, lock))

        async def media_url_is_referenced(self, url):
            return state["avatar_url"] == url

        async def update_profile(self, profile_id, values):
            self.assigned = values["avatar_url"]
            (failed_pending if self.fail else success_pending).set()
            await (allow_failure if self.fail else allow_success).wait()
            if self.fail:
                raise RuntimeError("Synthetic rolled-back concurrent replacement")
            state.update(values)
            return dict(state)

        def release(self):
            for _, lock in reversed(self.held):
                lock.release()
            self.held.clear()

    success_tx, failure_tx = Transaction(), Transaction(fail=True)

    async def replace(transaction, size):
        try:
            return await UploadAvatar(transaction, gateway, PillowImageProcessor()).execute_family(
                make_profile(), photo(size), "image/jpeg", BUCKET,
            )
        finally:
            transaction.release()

    successful = asyncio.create_task(replace(success_tx, (900, 600)))
    failed = asyncio.create_task(replace(failure_tx, (600, 900)))
    await asyncio.wait_for(success_pending.wait(), 5)
    await asyncio.wait_for(failed_pending.wait(), 5)
    age_objects(gateway)
    cleanup_tx = Transaction()

    async def cleanup_committing_family():
        try:
            return await retire_unreferenced_media(
                cleanup_tx, gateway, BUCKET, key(success_tx.assigned),
            )
        finally:
            cleanup_tx.release()

    cleanup = asyncio.create_task(cleanup_committing_family())
    await asyncio.sleep(0)
    assert not cleanup.done()  # Publication still owns the family transaction lock.
    allow_success.set()
    result = await successful
    assert not await cleanup
    allow_failure.set()
    with pytest.raises(RuntimeError, match="rolled-back"):
        await failed
    assert state["avatar_url"] == result["public_url"]
    retired_tx = Transaction()
    try:
        assert await retire_unreferenced_media(
            retired_tx, gateway, BUCKET, key(failure_tx.assigned),
        )
    finally:
        retired_tx.release()
    assert key(failure_tx.assigned) not in gateway._client.objects
    await gateway.validate_media_reference(result["public_url"], f"avatars/{make_profile().id}/")
