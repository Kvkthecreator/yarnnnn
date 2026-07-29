"""
ADR-498 regression gate — the invite flow names the wrong-account state, and
transactional email has ONE house shell.

Run: `python3 api/test_adr498_invite_flow.py`

## The failure this defends against

Operator-observed 2026-07-29: opening an invite link produced
`Failed to load resource: 403` in the console and nothing actionable on screen.

The 403 was CORRECT — `accept_invite` binds an invite to its address, and the
link had been opened while signed in as a different user. The defect was that
the page discovered the mismatch only AFTER the click, then rendered the raw
server detail with no way forward. Both facts (who was invited, who is signed
in) were knowable BEFORE the click.

The rule: **when a gate's outcome is predictable from state the surface already
holds, surface the state — do not let the user discover it as a failure.**
"""

from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(REPO, "web", "app", "invite", "[token]", "page.tsx")
INVITES = os.path.join(REPO, "api", "services", "workspace_invites.py")
SHELL = os.path.join(REPO, "api", "services", "email_shell.py")

_failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"✓ {label}")
    else:
        print(f"✗ {label}" + (f" — {detail}" if detail else ""))
        _failures.append(label)


page = open(PAGE).read()
invites = open(INVITES).read()
shell = open(SHELL).read()

# --- 1. the mismatch is detected BEFORE the click ---------------------------

check(
    "the page reads the signed-in identity",
    "auth.getSession()" in page and "viewerEmail" in page,
    "without this the mismatch is only discoverable via a 403",
)
check(
    "a wrongAccount state is derived from invited vs signed-in",
    "const wrongAccount" in page,
)
check(
    "the comparison mirrors the server (trim + lowercase)",
    ".trim().toLowerCase()" in page,
    "the FE must not disagree with accept_invite about what matches",
)
check(
    "the wrong-account branch replaces the Accept button",
    "} : wrongAccount ? (" in page or ": wrongAccount ? (" in page,
    "offering a button that is guaranteed to 403 is the original defect",
)
check(
    "both addresses are named in the wrong-account copy",
    "you&apos;re signed in as" in page,
)

# --- 2. there is a way OUT, and it returns here -----------------------------

check(
    "a switch-account action exists",
    "switchAccount" in page and "auth.signOut()" in page,
)
check(
    "the redirect targets the REAL login route (/auth/login, not /login)",
    "/auth/login?next=" in page and '"/login?next=' not in page,
    "/login does not exist in this app and would 404",
)
check(
    "the invite link round-trips through login",
    "next=${encodeURIComponent(`/invite/${token}`)}" in page,
    "the member must land back on the accept, not the home page",
)

# --- 3. the server contract is UNCHANGED (the 403 was correct) -------------

check(
    "accept_invite still rejects a mismatched email",
    'raise InviteError(\n            "email_mismatch"' in invites
    or '"email_mismatch"' in invites,
    "the gate is correct — only its PRESENTATION changed",
)
check(
    "the route still maps email_mismatch → 403",
    '"email_mismatch": 403' in open(os.path.join(REPO, "api", "routes", "workspace.py")).read(),
)

# --- 4. ONE email shell, and the invite uses it ----------------------------

check(
    "the shared email shell exists",
    "def render_email(" in shell and "def paragraph(" in shell,
)
check(
    "the invite email renders through the shell",
    "from services.email_shell import" in invites and "render_email(" in invites,
    "a hand-rolled template would be a sixth private variant",
)
check(
    "the bare unstyled invite markup is gone",
    '<p><a href="{link}">Accept the invite</a>' not in invites,
)
check(
    "the invite names the bound address in the BODY",
    "This invite was sent to <strong>{email}</strong>" in invites,
    "the mail must not set up the dead end the app now catches",
)
check(
    "the email carries a preheader (inbox preview)",
    "preheader=" in invites and "preheader" in shell,
)
check(
    "a text/plain alternative is still sent",
    "text=(" in invites,
    "HTML-only mail is a deliverability and accessibility regression",
)

# --- 5. email-client constraints respected ---------------------------------

check(
    "layout is table-based (no flex/grid)",
    "role=\"presentation\"" in shell and "display:flex" not in shell,
)
check(
    "styles are inlined, not only in a <style> block",
    shell.count("style=\"") > 8,
)
check(
    "the dark-mode block is additive only (light stands alone)",
    "prefers-color-scheme: dark" in shell and "!important" in shell,
)
check(
    "no external stylesheet or web font is referenced",
    "<link" not in shell and "fonts.googleapis" not in shell,
)

print()
if _failures:
    print(f"FAILED {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("ADR-498 gate: all checks passed")
