"""Admission rejects hostile requests before downstream parsing or decoding."""

import asyncio

import pytest

from app.infrastructure.media.admission import UploadAdmissionMiddleware


def scope(path="/v1/media/uploads/synthetic", *, method="PUT", headers=None, ip="127.0.0.1"):
    return {
        "type": "http", "method": method, "path": path,
        "headers": headers if headers is not None else [(b"content-type", b"image/png")],
        "client": (ip, 12345),
    }


async def invoke(middleware, request=None, messages=None):
    sent = []
    pending = list(messages or [{"type": "http.request", "body": b"image"}])

    async def receive():
        return pending.pop(0) if pending else {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    await middleware(request or scope(), receive, send)
    return sent


class Downstream:
    def __init__(self):
        self.calls = 0
        self.bodies = []

    async def __call__(self, scope, receive, send):
        self.calls += 1
        self.bodies.append(await receive())
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})


@pytest.mark.asyncio
async def test_chunked_upload_bounded_and_replayed_as_one_message():
    downstream = Downstream()
    middleware = UploadAdmissionMiddleware(downstream, max_body_bytes=8)
    sent = await invoke(middleware, messages=[
        {"type": "http.request", "body": b"1234", "more_body": True},
        {"type": "http.request", "body": b"5678"},
    ])
    assert sent[0]["status"] == 204
    assert downstream.bodies == [{"type": "http.request", "body": b"12345678", "more_body": False}]


@pytest.mark.asyncio
@pytest.mark.parametrize("length", [b"bad", b"-1", b"1,1", b"+5", b"9" * 100, b""])
async def test_malformed_length_never_enters_downstream(length):
    downstream = Downstream()
    sent = await invoke(UploadAdmissionMiddleware(downstream), scope(headers=[
        (b"content-type", b"image/png"), (b"content-length", length),
    ]))
    assert sent[0]["status"] == 413
    assert downstream.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("length", [b"2", b"8"])
async def test_declared_length_mismatch_rejected(length):
    downstream = Downstream()
    sent = await invoke(UploadAdmissionMiddleware(downstream), scope(headers=[
        (b"content-type", b"image/png"), (b"content-length", length),
    ]))
    assert sent[0]["status"] == 413
    assert downstream.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("extra", [
    [(b"content-length", b"5"), (b"content-length", b"5")],
    [(b"content-length", b"5"), (b"transfer-encoding", b"chunked")],
])
async def test_ambiguous_framing_rejected(extra):
    downstream = Downstream()
    sent = await invoke(UploadAdmissionMiddleware(downstream), scope(headers=[
        (b"content-type", b"image/png"), *extra,
    ]))
    assert sent[0]["status"] == 413
    assert downstream.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("declared", [False, True])
async def test_oversized_multipart_never_enters_parser(declared):
    downstream = Downstream()
    headers = [(b"content-type", b"multipart/form-data; boundary=synthetic")]
    if declared:
        headers.append((b"content-length", b"11"))
    sent = await invoke(
        UploadAdmissionMiddleware(downstream, max_body_bytes=8, multipart_overhead=2),
        scope("/v1/customer/profile/avatar", method="POST", headers=headers),
        [{"type": "http.request", "body": b"x" * 11}],
    )
    assert sent[0]["status"] == 413
    assert downstream.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("content_type", [b"image/png", b"multipart/form-data", b"multipart/form-data; boundary=", b"multipart/form-data; boundary=\"bad\r\nboundary\""])
async def test_invalid_multipart_content_type(content_type):
    downstream = Downstream()
    sent = await invoke(UploadAdmissionMiddleware(downstream), scope(
        "/v1/customer/profile/avatar", method="POST", headers=[(b"content-type", content_type)],
    ))
    assert sent[0]["status"] == 415
    assert downstream.calls == 0


@pytest.mark.asyncio
async def test_binary_oversize_and_svg_rejected():
    downstream = Downstream()
    middleware = UploadAdmissionMiddleware(downstream, max_body_bytes=4)
    assert (await invoke(middleware))[0]["status"] == 413
    assert (await invoke(middleware, scope(headers=[(b"content-type", b"image/svg+xml")])))[0]["status"] == 415
    assert downstream.calls == 0


@pytest.mark.asyncio
async def test_rate_is_per_peer_ip_not_forwarded_ip_and_grants_are_separate():
    middleware = UploadAdmissionMiddleware(Downstream(), rate_limit=1)
    assert (await invoke(middleware))[0]["status"] == 204
    denied = await invoke(middleware, scope(headers=[
        (b"content-type", b"image/png"), (b"x-forwarded-for", b"another-client"),
    ]))
    assert denied[0]["status"] == 429
    assert dict(denied[0]["headers"])[b"retry-after"] == b"60"
    assert (await invoke(middleware, scope(ip="127.0.0.2")))[0]["status"] == 204
    grant = scope("/v1/profiles/me/avatar-upload-url", method="POST", headers=[])
    assert (await invoke(middleware, grant))[0]["status"] == 204
    assert (await invoke(middleware, grant))[0]["status"] == 429


@pytest.mark.asyncio
async def test_rate_map_is_bounded_and_expired_entries_removed(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("app.infrastructure.media.admission.time.monotonic", lambda: now[0])
    middleware = UploadAdmissionMiddleware(Downstream(), rate_limit=1)
    for number in range(1026):
        await invoke(middleware, scope(ip=str(number)))
    assert len(middleware._rates) == 1024
    now[0] += 61
    assert (await invoke(middleware, scope(ip="1025")))[0]["status"] == 204
    assert len(middleware._rates) == 1


@pytest.mark.asyncio
async def test_ingress_capacity_is_nonblocking_and_released():
    downstream = Downstream()
    middleware = UploadAdmissionMiddleware(downstream, max_inflight=1)
    entered, release = asyncio.Event(), asyncio.Event()

    async def slow_receive():
        entered.set()
        await release.wait()
        return {"type": "http.request", "body": b"image"}

    async def send(message):
        pass

    task = asyncio.create_task(middleware(scope(), slow_receive, send))
    await entered.wait()
    assert (await invoke(middleware))[0]["status"] == 503
    release.set()
    await task
    assert (await invoke(middleware))[0]["status"] == 204


@pytest.mark.asyncio
async def test_total_receive_deadline_and_slot_release():
    downstream = Downstream()
    middleware = UploadAdmissionMiddleware(downstream, read_timeout=0.01)
    sent = []

    async def receive():
        await asyncio.Event().wait()

    async def send(message):
        sent.append(message)

    await middleware(scope(), receive, send)
    assert sent[0]["status"] == 408
    assert downstream.calls == 0
    assert middleware._inflight == 0
    assert (await invoke(middleware))[0]["status"] == 204


@pytest.mark.asyncio
async def test_unrelated_route_body_and_headers_unaffected():
    downstream = Downstream()
    sent = await invoke(UploadAdmissionMiddleware(downstream, max_body_bytes=1), scope(
        "/v1/other", method="POST", headers=[(b"content-length", b"malformed")],
    ))
    assert sent[0]["status"] == 204
    assert downstream.bodies[0]["body"] == b"image"


@pytest.mark.asyncio
async def test_disconnect_does_not_parse_or_leak_capacity():
    downstream = Downstream()
    middleware = UploadAdmissionMiddleware(downstream)
    assert await invoke(middleware, messages=[{"type": "http.disconnect"}]) == []
    assert downstream.calls == 0
    assert middleware._inflight == 0
