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

CHOOSING THE PAIR (the lesson that reshaped the first click-pass):
  Prefer a DISPOSABLE RIG pair over live principals. A live workspace with a
  standing member forces every mutating step into attempt-and-restore, and makes
  the whole JOINING half untestable — that member's grant already exists and may
  never be revoked, so `becoming` a member (the first thing a real operator does,
  and the most likely to be broken) cannot be exercised at all. On a rig the same
  suite runs the real lifecycle: invite -> accept -> member -> narrow -> revoke.

  A COLD principal — owns nothing, never signed in — is a distinct instrument:
  it is the shape a real invitee arrives in. That state is CONSUMED on first use,
  so verify it (0 grant rows anywhere) before the run.

  Full method: docs/evaluations/BROWSER-CLICK-PASS-PLAYBOOK.md

BROWSER SESSION NUANCE:
  Use ONE ISOLATED BROWSER CONTEXT PER PRINCIPAL. Contexts share cookies, so
  logging in as a second principal in the same context silently overwrites the
  first — every later "member" observation is really the owner, and the pass
  looks perfectly plausible while proving nothing.

Usage:
    cd api && python3 -m scripts.operator.browser_login_link testacct@yarnnn.com
    cd api && python3 -m scripts.operator.browser_login_link kvkthecreator@yarnnn.com
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

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
    # --- the click-pass pair (rig-only, fully disposable) ---------------
    "kvkthecreator@yarnnn.com",  # OWNER principal — kvk-yarnnn rig, ws bf5b25a9
    "testacct@yarnnn.com",       # GUEST principal — owns NO workspace, never signed in
    # --- other rig principals (persona workspaces) ---------------------
    "alpha-trader-2@yarnnn.com",
    "yarnnn-author@yarnnn.com",
    "netflix-script-author@yarnnn.com",
    "korea-thriller-shorts@yarnnn.com",
    "bare-kernel@yarnnn.com",
    "anr-scout@yarnnn.com",
    # --- live-workspace principals -------------------------------------
    # Retained for read-mostly passes on d5b9029b. PREFER the rig pair above:
    # rigs are disposable, so mutating steps can run for real instead of being
    # attempted-and-restored against live substrate.
    "kvkthecreator@gmail.com",   # owner of d5b9029b
    "seulkim88@gmail.com",       # member of d5b9029b + owner of 4ca9c664
}

#: The canonical origin. MUST match the origin the app actually serves on —
#: Supabase redirects to it verbatim, and a bare-apex value gets 301'd to the
#: www host, which drops the URL FRAGMENT carrying the access token.
DEFAULT_SITE = os.environ.get("YARNNN_SITE_URL", "https://www.yarnnn.com")

#: Magic-link tokens arrive in the URL *fragment*, which only a page that mounts
#: the Supabase client can consume. Landing on the marketing root leaves the
#: fragment unread and the session unestablished (observed 2026-07-31 during the
#: settings click-pass: localStorage empty, immediate bounce to /auth/login).
#: /auth/callback is the route that exchanges the fragment and then honors
#: `next`, so every minted link is routed through it.
CALLBACK_PATH = "/auth/callback"


def _service_key_origin() -> str:
    """Which env file supplied the SUPABASE_SERVICE_KEY now in os.environ.

    Diagnostic only. `load_dotenv` is first-wins, so the value in play may come
    from a file the operator is not looking at — and a stale key's 401 gives no
    hint which one. Returns a human-readable origin, never raises.
    """
    live = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not live:
        return "unset"
    candidates = (
        ("api/.env.alpha-ops", _API_ROOT / ".env.alpha-ops"),
        ("<repo>/.env", _API_ROOT.parent / ".env"),
        ("api/.env", _API_ROOT / ".env"),
    )
    for label, path in candidates:
        try:
            if not path.exists():
                continue
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line.startswith("SUPABASE_SERVICE_KEY="):
                    continue
                if line.split("=", 1)[1].strip().strip('"').strip("'") == live:
                    return label
        except OSError:
            continue
    return "the shell environment (or an unmatched file)"


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
            # A 401 here is almost never "the request was wrong" — it is a
            # STALE SERVICE KEY, and the raw Supabase text ("Unregistered API
            # key") does not say WHICH of the three env files supplied it.
            # `load_dotenv` does not override, so the FIRST file that defines
            # the var wins: .env.alpha-ops, then repo .env, then api/.env.
            # That precedence cost ~15 minutes on 2026-08-25 (the stream-steps
            # click-pass) — two files carried a rotated-out key while api/.env
            # carried the live one, and the failure read as a bug in this
            # script. Name the file and the remedy instead.
            if r.status_code == 401:
                raise SystemExit(
                    f"generate_link REFUSED [401]: {r.text}\n\n"
                    f"This is a stale SUPABASE_SERVICE_KEY, not a bad request.\n"
                    f"  key in use : {service_key[:16]}… (from {_service_key_origin()})\n"
                    f"  precedence : load_dotenv does NOT override — the FIRST\n"
                    f"               file defining the var wins, in this order:\n"
                    f"                 1. api/.env.alpha-ops\n"
                    f"                 2. <repo>/.env\n"
                    f"                 3. api/.env\n"
                    f"  remedy     : rotate the key in the file named above to\n"
                    f"               the live one (see docs/database/ACCESS.md),\n"
                    f"               rather than overriding it per-invocation."
                )
            raise SystemExit(f"generate_link failed [{r.status_code}]: {r.text}")
        payload = r.json()
        props = payload.get("properties") or payload
        token_hash = props.get("hashed_token") or props.get("token_hash")
        if not token_hash:
            raise SystemExit(f"no hashed_token in response: {payload}")

        # Deliberately NOT the returned `action_link`. Supabase rewrites its
        # `redirect_to` to the project Site URL whenever the requested URL is
        # absent from the Redirect-URLs allow-list — silently, with a 200. That
        # lands the token on the marketing root, which mounts no Supabase client
        # and therefore never consumes it.
        #
        # Instead hand the token straight to /auth/callback, which consumes a
        # `token_hash` via verifyOtp() and then forwards to `next`. That keeps
        # this instrument independent of dashboard allow-list config.
        return f"{redirect_to}&token_hash={token_hash}&type=magiclink"


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: python3 -m scripts.operator.browser_login_link "
            "<email> [redirect_path]\n"
            f"allowed emails: {sorted(ALLOWED_EMAILS)}"
        )
    email = sys.argv[1].strip()
    path = sys.argv[2] if len(sys.argv) > 2 else "/workspace-settings"
    # Route through /auth/callback (which consumes the fragment) and let it
    # forward to the requested in-app destination via `next`.
    if path.startswith("http"):
        next_path = urlparse(path).path or "/"
    else:
        next_path = path
    redirect_to = f"{DEFAULT_SITE}{CALLBACK_PATH}?next={quote(next_path, safe='')}"
    # NOTE: mint_browser_link appends `&token_hash=...&type=magiclink`.

    link = mint_browser_link(email, redirect_to)
    print(f"\n# browser session for: {email}")
    print(f"# lands on: {redirect_to}")
    print("# single-use, ~1h validity — do NOT paste into commits or shared logs\n")
    print(link)
    print()


if __name__ == "__main__":
    main()
