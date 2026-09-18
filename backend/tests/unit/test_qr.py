"""Permanent walk-in QR identity and rendering."""

from app.core.qr import _build_walkin_url, make_qr_png, make_qr_svg


def test_build_walkin_url_appends_token_to_route_prefix() -> None:
    url = _build_walkin_url(
        "abc123",
        "https://salon-customer-qr-webpage.vercel.app/s/",
    )

    assert url == "https://salon-customer-qr-webpage.vercel.app/s/abc123"


def test_qr_render_is_deterministic_for_permanent_salon_identity() -> None:
    """The same stored token and frontend base always produce the same QR image."""

    token = "0123456789abcdef0123456789abcdef"
    base_url = "https://walkin.example.test/s"

    first_png = make_qr_png(token, base_url)
    second_png = make_qr_png(token, base_url)
    first_svg = make_qr_svg(token, base_url)
    second_svg = make_qr_svg(token, base_url)

    assert first_png == second_png
    assert first_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert first_svg == second_svg
    assert "<svg" in first_svg


def test_different_salon_tokens_produce_different_qr_images() -> None:
    """Two salon identities must never render as the same QR code."""

    base_url = "https://walkin.example.test/s"

    first = make_qr_png("salon-token-one", base_url)
    second = make_qr_png("salon-token-two", base_url)

    assert first != second
