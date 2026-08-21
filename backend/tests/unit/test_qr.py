"""Walk-in QR URL construction."""

from app.core.qr import _build_walkin_url


def test_build_walkin_url_appends_token_to_route_prefix() -> None:
    url = _build_walkin_url(
        "abc123",
        "https://salon-customer-qr-webpage.vercel.app/s/",
    )

    assert url == "https://salon-customer-qr-webpage.vercel.app/s/abc123"
