#!/usr/bin/env python3
"""Mint a clickable magic-link URL for a BROWSER click-pass session.

Why this exists (2026-07-31, the settings-surfaces sign-off): the existing
`alpha_ops._shared.mint_jwt` machinery exchanges the OTP server-side and hands
back a bare JWT — perfect for API probes, useless for a browser pass. A browser
principal needs a URL it can NAVIGATE to, so Supabase sets the session cookies
in the real browser. This mints exactly that and prints nothing else.

The two lanes it serves:
  1. Claude in Chrome (this repo's session, once the extension is paired).
  2. Claude desktop / the operator, driven from the operator packet
     (docs/evaluations/OPERATOR-PACKET-settings-click-pass.md) — the packet
     pastes the printed URL and never needs repo access.

SAFETY — this is a Hat-B developer instrument:
  - It refuses any email not on the DECLARED TEST ROSTER below. Minting a login
    link for a real external principal would be an account takeover, not a test.
    (personas.yaml is the probe-target roster and must never list a real user;
    the same rule binds here, enforced in code rather than by discipline.)
  - Links are single-use and short-lived (Supabase default ~1h).
  - Never paste a minted URL into a commit, an issue, or a chat log that leaves
    the operator's machine.

Usage:
    cd api && python3 -m scripts.operator.browser_login_link seulkim88@gmail.com
    cd api && python3 -m scripts.operator.browser_login_link kvkthecreator@gmail.com
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

_API_ROOT = Path(__file__).resolve().parents[2]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(_API_ROOT.parent / ".env")

#: The ONLY emails this script will mint a browser session for. Every entry is a
#: declared test principal (the owner/member instrument + the rigs). Adding a
#: real user here is the same category error as adding one to personas.yaml.
ALLOWED_EMAILS = {
    "kvkthecreator@gmail.com",   # owner of d5b9029b (the live workspace)
    "seulkim88@gmail.com",       # member of d5b9029b + owner of 4ca9c664
    "kvkthecreator@yarnnn.com",  # kvk-yarnnn rig (ws bf5b25a9)
    "testacct@yarnnn.com",       # unprovisioned rig
}

DEFAULT_SITE = os.environ.get("YARNNN_SITE_URL", "https://yarnnn.com")


def mint_browser_link(email: str, redirect_to: str) -> str:
    """Return a navigable magic-link URL that establishes a browser session."""
    if email not in ALLOWED_EMAILS:
        raise SystemExit(
            f"REFUSED: {email!r} is not on the declared test roster.\n"
            f"Allowed: {sorted(ALLOWED_EMAILS)}\n"
            "Minting a browser session for a non-test principal is an account "
            "takeover, not an evaluation."
        )
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not service_key:
        raise SystemExit(
            "SUPABASE_URL / SUPABASE_SERVICE_KEY not set — source the alpha-ops "
            "env (api/.env.alpha-ops) per docs/database/ACCESS.md."
        )

    with httpx.Client(timeout=20.0) as client:
        r = client.post(
            f"{supabase_url}/auth/v1/admin/generate_link",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
            json={
                "type": "magiclink",
                "email": email,
                # Where the browser lands AFTER the token is consumed.
                "options": {"redirect_to": redirect_to},
            },
        )
        if r.status_code >= 300:
            raise SystemExit(f"generate_link failed [{r.status_code}]: {r.text}")
        payload = r.json()
        props = payload.get("properties") or payload
        # `action_link` is the NAVIGABLE url (verify endpoint + token + redirect).
        link = props.get("action_link")
        if not link:
            token_hash = props.get("hashed_token") or props.get("token_hash")
            if not token_hash:
                raise SystemExit(f"no action_link or token_hash in response: {payload}")
            link = (
                f"{supabase_url}/auth/v1/verify?token={token_hash}"
                f"&type=magiclink&redirect_to={redirect_to}"
            )
        return link


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: python3 -m scripts.operator.browser_login_link "
            "<email> [redirect_path]\n"
            f"allowed emails: {sorted(ALLOWED_EMAILS)}"
        )
    email = sys.argv[1].strip()
    path = sys.argv[2] if len(sys.argv) > 2 else "/workspace-settings"
    redirect_to = path if path.startswith("http") else f"{DEFAULT_SITE}{path}"

    link = mint_browser_link(email, redirect_to)
    print(f"\n# browser session for: {email}")
    print(f"# lands on: {redirect_to}")
    print("# single-use, ~1h validity — do NOT paste into commits or shared logs\n")
    print(link)
    print()


if __name__ == "__main__":
    main()
