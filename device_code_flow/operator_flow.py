#!/usr/bin/env python3
"""Operator-in-the-loop test of the OAuth 2.0 Device Authorization Grant """
import os
import json
import time
import base64
import urllib.parse
import urllib.request
import urllib.error

# --- config (override via env) ----------------------------------------------
BASE = os.environ.get(
    "KC_BASE", "http://localhost:8080/realms/machines/protocol/openid-connect"
)
CLIENT_ID = os.environ.get("KC_CLIENT_ID", "<TO_BE_ADDED>")
CLIENT_SECRET = os.environ.get("KC_CLIENT_SECRET", "<TO_BE_ADDED")


def _post_json(url, data):
    """POST and parse JSON, returning the body even on 4xx (the token endpoint
    signals `authorization_pending` / `slow_down` with HTTP 400)."""
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def jwt_claims(token):
    """Decode a JWT payload (no signature verification — PoC inspection only)."""
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def request_device_code():
    """The headless machine asks Keycloak for a device code."""
    return _post_json(
        BASE + "/auth/device",
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "openid offline_access",
        },
    )


def poll_for_token(device_code, interval=5):
    """Poll /token until the operator approves (or it expires).

    Handles the RFC 8628 polling errors: keeps waiting on
    `authorization_pending`, backs off on `slow_down`.
    """
    while True:
        tok = _post_json(
            BASE + "/token",
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "device_code": device_code,
            },
        )
        err = tok.get("error")
        if err == "authorization_pending":
            print("   ...waiting for operator approval")
            time.sleep(interval)
        elif err == "slow_down":
            interval += 5
            time.sleep(interval)
        else:
            return tok  # success, or a terminal error (expired/denied)


def summarize(tok):
    """Pull the interesting bits out of a token response for printing."""
    if "access_token" not in tok:
        return tok
    access = jwt_claims(tok["access_token"])
    refresh = jwt_claims(tok["refresh_token"])
    return {
        "token_type": tok.get("token_type"),
        "expires_in": tok.get("expires_in"),
        "scope": tok.get("scope"),
        "access_subject": access.get("preferred_username"),
        "subject_id": access.get("sub"),
        "refresh_typ": refresh.get("typ"),  # "Offline" proves it's an offline token
        "refresh_subject": refresh.get("preferred_username"),
    }


def main():
    d = request_device_code()

    print("\n=== Machine has requested access. Operator, do this now: ===\n")
    print(f"  1. Open:        {d['verification_uri']}")
    print(f"     Enter code:  {d['user_code']}")
    print(f"  (or open directly: {d['verification_uri_complete']})")
    print("\n  2. Log in as the MACHINE ACCOUNT and approve.")
    print(f"  (code valid for {d['expires_in']}s)\n")

    print("Polling Keycloak for approval...")
    tok = poll_for_token(d["device_code"], interval=d.get("interval", 5))

    print("\n=== Result ===")
    print(json.dumps(summarize(tok), indent=2))
    if "access_token" in tok:
        print("\nApproved. Offline token issued and persisted by Keycloak.")
    else:
        print("\nNot approved (expired or denied).")


if __name__ == "__main__":
    main()
