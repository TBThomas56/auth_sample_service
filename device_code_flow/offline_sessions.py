#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = ["psycopg[binary]"]
# ///
"""Query Keycloak's offline sessions for the `machines` realm."""

import os

import psycopg

REALM = os.environ.get("KC_REALM", "machines")

CONN = dict(
    host=os.environ.get("PGHOST", "localhost"),
    port=int(os.environ.get("PGPORT", "5432")),
    dbname=os.environ.get("PGDATABASE", "keycloak"),
    user=os.environ.get("PGUSER", "postgres"),
    password=os.environ.get("PGPASSWORD", "postgres"),
)

QUERY = """
SELECT u.username,
       u.id               AS subject_id,
       c.client_id        AS client,
       ous.offline_flag   AS offline
FROM offline_user_session ous
JOIN realm r                  ON r.id = ous.realm_id
JOIN user_entity u            ON u.id = ous.user_id
JOIN offline_client_session ocs ON ocs.user_session_id = ous.user_session_id
JOIN client c                 ON c.id = ocs.client_id
WHERE r.name = %s
ORDER BY u.username;
"""


def main():
    with psycopg.connect(**CONN) as conn:
        rows = conn.execute(QUERY, (REALM,)).fetchall()

    if not rows:
        print(f"No offline sessions found in realm '{REALM}'.")
        return

    headers = ("username", "subject_id", "client", "offline")
    widths = [
        max(len(h), *(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)
    ]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)

    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))
    for r in rows:
        print(fmt.format(*(str(c) for c in r)))
    print(f"\n{len(rows)} row(s).")


if __name__ == "__main__":
    main()
