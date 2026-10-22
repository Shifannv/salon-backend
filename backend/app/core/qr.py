"""QR code generation utilities for walk-in salon booking.

Each salon has a unique ``qr_token`` stored in the database.  These helpers
encode the walk-in URL for that token and return the QR as raw PNG bytes or
an SVG string using the *segno* library (pure Python, no Pillow required).

The URL baked into every QR code follows the pattern::

    <walkin_base_url>/<qr_token>

For example::

    https://book.yoursalon.com/s/abc123xyz

When a customer scans the QR the phone browser opens the walk-in web app
directly at that salon's service selection screen.  The web app then calls
``GET /v1/walkin/{qr_token}`` to load salon info, services, and staff.
"""

from __future__ import annotations

import io
import re

# Tokens are issued by the database (``encode(gen_random_bytes(16), 'hex')``): 32 lowercase hex characters.
# The check below is deliberately wider (URL-safe characters, 3-128 long) so a malformed value is rejected
# before any database or cache work, without rejecting a legacy token. It is not a secret check.
QR_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{3,128}")


def is_valid_qr_token_format(value: str) -> bool:
    """True when ``value`` can be a QR token (format only; existence is checked in Postgres)."""

    return QR_TOKEN_PATTERN.fullmatch(value) is not None


def _build_walkin_url(qr_token: str, base_url: str) -> str:
    """Return the URL encoded into the QR code for the given ``qr_token``."""
    base = base_url.rstrip("/")
    return f"{base}/{qr_token}"


def make_qr_png(
    qr_token: str,
    base_url: str,
    *,
    scale: int = 10,
    border: int = 4,
) -> bytes:
    """Return PNG bytes for the salon walk-in QR code.

    Parameters
    ----------
    qr_token:
        The salon's unique QR token (from ``salons.qr_token``).
    base_url:
        Walk-in web site base URL (``settings.walkin_base_url``).
    scale:
        Module size in pixels.  10 means each dark/light square is 10 × 10 px.
        Increase for higher-resolution output (e.g. scale=20 for print quality).
    border:
        Quiet-zone modules around the code.  QR spec requires ≥ 4.
    """
    import segno  # on first QR request, to keep it out of cold start

    url = _build_walkin_url(qr_token, base_url)
    qr = segno.make_qr(url, error="M")

    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=scale, border=border, dark="#111827", light="#FFFFFF")
    return buf.getvalue()


def make_qr_svg(
    qr_token: str,
    base_url: str,
    *,
    scale: int = 10,
    border: int = 4,
) -> str:
    """Return an SVG string for the salon walk-in QR code.

    SVG output is resolution-independent — ideal for web embedding and print.

    Parameters
    ----------
    qr_token:
        The salon's unique QR token (from ``salons.qr_token``).
    base_url:
        Walk-in web site base URL (``settings.walkin_base_url``).
    scale:
        Module size in user units (SVG viewBox units per module).
    border:
        Quiet-zone modules around the code.  QR spec requires ≥ 4.
    """
    import segno  # on first QR request, to keep it out of cold start

    url = _build_walkin_url(qr_token, base_url)
    qr = segno.make_qr(url, error="M")

    # segno writes SVG as bytes even to a StringIO — use BytesIO and decode.
    buf = io.BytesIO()
    qr.save(buf, kind="svg", scale=scale, border=border, dark="#111827", light="#FFFFFF")
    return buf.getvalue().decode("utf-8")
