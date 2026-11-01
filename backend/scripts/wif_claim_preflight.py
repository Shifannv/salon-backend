"""Verify the exact non-secret GitHub OIDC claims expected by production WIF.

The request token and returned JWT stay in memory and are never printed or written.
Only the selected identity claims used by the provider condition are logged.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

AUDIENCE = "salon-cloud-run-wif-claim-preflight"
EXPECTED = {
    "repository_id": "1422493480",
    "repository_owner_id": "172572480",
    "repository": "Shifannv/salon-backend",
    "actor_id": "172572480",
    "ref": "refs/heads/main",
    "sub": "repo:Shifannv@172572480/salon-backend@1422493480:environment:production",
    "event_name": "push",
    "workflow_ref": "Shifannv/salon-backend/.github/workflows/cloud-run-auto.yml@refs/heads/main",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def decode_claims(token: str) -> dict:
    parts = token.split(".")
    require(len(parts) == 3, "GitHub OIDC response was not a JWT")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload).decode())
    except (ValueError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("GitHub OIDC claim payload was invalid") from error
    require(isinstance(claims, dict), "GitHub OIDC claim payload was not an object")
    return claims


def request_claims() -> dict:
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "")
    request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "")
    require(url.startswith("https://") and bool(request_token), "GitHub OIDC request context is unavailable")
    separator = "&" if "?" in url else "?"
    oidc_request = urllib.request.Request(
        url + separator + urllib.parse.urlencode({"audience": AUDIENCE}),
        headers={"Authorization": "Bearer " + request_token},
    )
    try:
        with urllib.request.urlopen(oidc_request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub OIDC request failed (HTTP {error.code}); response suppressed") from None
    except (OSError, ValueError) as error:
        raise RuntimeError(f"GitHub OIDC request failed ({type(error).__name__}); response suppressed") from None
    token = payload.get("value") if isinstance(payload, dict) else None
    require(isinstance(token, str) and bool(token), "GitHub OIDC response omitted the token")
    return decode_claims(token)


def verify(claims: dict) -> dict[str, str | None]:
    observed = {key: claims.get(key) for key in EXPECTED}
    # These selected GitHub identity values are non-secret. Never log the JWT,
    # request token, audience, timestamps, nonce or token identifier.
    print("WIF claim preflight observed: " + json.dumps(observed, sort_keys=True))
    mismatched = [key for key, expected in EXPECTED.items() if observed[key] != expected]
    require(not mismatched, "WIF claim preflight mismatch: " + ",".join(mismatched))
    print("WIF claim preflight: PASS")
    return observed


def main() -> None:
    verify(request_claims())


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
