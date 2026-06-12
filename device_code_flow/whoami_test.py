#!/usr/bin/env python3
"""End-to-end test of client-credentials + token-exchange → /whoami.
  1. Client credentials → machine-worker service-account token → /whoami
     expected: service-account-machine-worker
  2. Token exchange requested_subject=tomohub → /whoami
     expected: tomohub
  3. Token exchange requested_subject=project-waffle → /whoami
     expected: project-waffle
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

KC_BASE = os.environ.get(
    "KC_BASE", "http://localhost:8080/realms/machines/protocol/openid-connect"
)
CLIENT_ID = os.environ.get("KC_CLIENT_ID", "machine-worker")
CLIENT_SECRET = os.environ.get("KC_CLIENT_SECRET", "FBASyxOyTjLqMOZppnx78NDwdB3UZHLW")
WHOAMI_URL = os.environ.get("WHOAMI_URL", "http://localhost:8000/whoami")


def _parse_error(e: urllib.error.HTTPError):
    raw = e.read().decode()
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        body = raw or f"HTTP {e.code} {e.reason}"
    raise RuntimeError(body) from e


def _post_form(url, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        _parse_error(e)


def _get_bearer(url, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        _parse_error(e)


def client_credentials() -> str:
    resp = _post_form(
        KC_BASE + "/token",
        {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    return resp["access_token"]


def token_exchange(subject_token: str, requested_subject: str) -> str:
    resp = _post_form(
        KC_BASE + "/token",
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "subject_token": subject_token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "requested_subject": requested_subject,
        },
    )
    return resp["access_token"]


def whoami(token: str) -> str:
    return _get_bearer(WHOAMI_URL, token)["sub"]


def run_step(label: str, token: str, expected: str):
    sub = whoami(token)
    status = "OK" if sub == expected else f"FAIL (expected {expected!r})"
    print(f"  {label}: {sub!r}  [{status}]")


def main():
    print("=== whoami integration test ===\n")

    print("Step 1 — client credentials")
    t1 = client_credentials()
    run_step("sub", t1, "service-account-machine-worker")

    print("\nStep 2 — token exchange → tomohub")
    t2 = token_exchange(t1, "tomohub")
    run_step("sub", t2, "tomohub")

    print("\nStep 3 — token exchange → project-waffle")
    t3 = token_exchange(t1, "project-waffle")
    run_step("sub", t3, "project-waffle")

    print()


if __name__ == "__main__":
    main()
