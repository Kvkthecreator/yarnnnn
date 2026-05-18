"""
ADR-283 step 6 — Provision a new auth user for an alpha persona.

One-off bootstrapping harness for personas whose `user_id` in
docs/alpha/personas.yaml is still the all-zeros placeholder. Calls the
Supabase Auth admin API (service-key bearer) to create the user with
`email_confirm=true` so no email confirmation step is needed.

Idempotent: if the email already exists, prints the existing user_id and
exits 0 — re-running is safe.

Usage:
    set -a; source api/.env.alpha-ops; set +a
    api/venv/bin/python api/scripts/alpha_ops/provision_persona_auth.py \
        --email yarnnn-author@yarnnn.com [--password <pw>]

Prints the resulting user.id to stdout (single line, machine-readable).

ADR-283 D7: alpha-author personas use `platform.kind: none` — no
external platform creds needed at provision time. The provisioning
output (user_id) is hand-edited into personas.yaml via
the operator's separate commit before running activate_persona.py.
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid

import httpx


SUPABASE_URL_DEFAULT = "https://noxgqcwynkzqabljjyon.supabase.co"


def _require_env(var: str) -> str:
    val = os.environ.get(var)
    if not val:
        raise SystemExit(f"{var} not set. `set -a; source api/.env.alpha-ops; set +a`")
    return val


def _find_user_by_email(client: httpx.Client, base: str, service_key: str, email: str) -> str | None:
    """Search the admin user list for an existing email. Returns user.id or None."""
    # Paginate defensively — Supabase admin/users list endpoint paginates.
    page = 1
    while True:
        r = client.get(
            f"{base}/auth/v1/admin/users",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
            },
            params={"page": page, "per_page": 200},
        )
        if r.status_code >= 300:
            raise SystemExit(f"admin/users list failed [{r.status_code}]: {r.text}")
        body = r.json()
        users = body.get("users", []) if isinstance(body, dict) else []
        for u in users:
            if (u.get("email") or "").lower() == email.lower():
                return u.get("id")
        # Stop when fewer than per_page were returned.
        if len(users) < 200:
            return None
        page += 1


def _create_user(client: httpx.Client, base: str, service_key: str, email: str, password: str) -> str:
    """Create a new auth user with email_confirm=true. Returns user.id."""
    r = client.post(
        f"{base}/auth/v1/admin/users",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        },
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
        },
    )
    if r.status_code >= 300:
        raise SystemExit(f"admin/users create failed [{r.status_code}]: {r.text}")
    body = r.json()
    # Supabase returns the user object directly (no envelope) on this endpoint.
    user_id = body.get("id") if isinstance(body, dict) else None
    if not user_id:
        raise SystemExit(f"admin/users create: no id in response: {body}")
    return user_id


def main() -> int:
    ap = argparse.ArgumentParser(description="Provision a new auth user for a persona")
    ap.add_argument("--email", required=True, help="Email for the new auth user")
    ap.add_argument(
        "--password",
        default=None,
        help="Password to set. Defaults to a fresh uuid4 (the persona's access is via service-key JWT minting, not password login)",
    )
    args = ap.parse_args()

    service_key = _require_env("SUPABASE_SERVICE_KEY")
    base = os.environ.get("SUPABASE_URL") or SUPABASE_URL_DEFAULT
    base = base.rstrip("/")

    password = args.password or uuid.uuid4().hex
    password_was_generated = args.password is None

    with httpx.Client(timeout=30.0) as client:
        existing = _find_user_by_email(client, base, service_key, args.email)
        if existing:
            print(f"EXISTS  {args.email}  user_id={existing}", file=sys.stderr)
            print(existing)
            return 0

        user_id = _create_user(client, base, service_key, args.email, password)

    print(f"CREATED {args.email}  user_id={user_id}", file=sys.stderr)
    if password_was_generated:
        print(f"        password={password}  (capture in api/.env.alpha-ops if desired)", file=sys.stderr)
    print(user_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
