"""
ADR-499 regression gate — a stale workspace pin self-heals instead of locking
the member out of their own account.

Run: `python3 api/test_adr499_stale_workspace_pin.py`

## The lockout this defends against

`X-Workspace-Id` is a localStorage pin written on invite/share accept. The
server validates it **fail-closed** (`supabase.py` → 403 "No active grant into
workspace …"), which is correct: never silently serve a different workspace than
the client addressed.

But the pin is a client-side CACHE of a server-side fact, and nothing cleared it
when the fact changed. Observed 2026-07-29: a member's invite grant was revoked
while their browser still held the pin. Every subsequent request 403'd — account
stats, notification prefs, surfaces — so the account looked workspace-less,
even though their OWN owner-workspace was reachable the instant the header went
away.

Receipt from the live DB at diagnosis time:

    owner-resolution (post-heal)          → 4ca9c664…  (their own workspace)
    pinned d5b9029b reachable? (pre-heal) → NO, revoked → 403 on every request

This is the "remembered state with no clearing path" smell — the same shape as
the ADR-491 stale settings pane and the ADR-494 D5 restore-class fix, one layer
lower.

## The rule

**A client-side cache of a server-side fact must clear when the server says the
fact is gone.** The fix belongs at the ONE choke point every request passes
through — not at each call site, which would be N places to forget.
"""

from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.join(REPO, "web", "lib", "api", "client.ts")
SUPABASE = os.path.join(REPO, "api", "services", "supabase.py")

_failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"✓ {label}")
    else:
        print(f"✗ {label}" + (f" — {detail}" if detail else ""))
        _failures.append(label)


client = open(CLIENT).read()
supa = open(SUPABASE).read()

# --- 1. the server contract is UNCHANGED (fail-closed is correct) ----------

check(
    "the server still rejects an unreachable pinned workspace with 403",
    "No active grant into workspace" in supa and "status_code=403" in supa,
    "fail-closed must survive — the fix is client-side cache hygiene",
)
check(
    "the server still falls back to the owner workspace when unpinned",
    "resolve_owner_workspace_id(user_id)" in supa,
    "this is what the self-heal retry lands on",
)
check(
    "a principal with no owned workspace falls back to their newest grant",
    "Fresh-invitee fallback" in supa,
)

# --- 2. the client self-heals at the ONE choke point -----------------------

check(
    "the pin is readable (to distinguish stale-pin from ordinary 403)",
    "export function getActiveWorkspaceId()" in client,
)
check(
    "the self-heal lives in request() — the single choke point",
    "staleWorkspacePin" in client,
    "per-call-site handling would be N places to forget",
)
check(
    "it matches the server's own detail string",
    'startsWith("No active grant into workspace")' in client,
    "a broad 403 catch would swallow ordinary authorization failures",
)
check(
    "it only fires when a pin is actually set",
    "!!getActiveWorkspaceId()" in client,
)

# --- 2b. THE WIRE SHAPE the detail actually arrives in ---------------------
# The server RAISES `detail=`, but main.py's envelope handler normalizes EVERY
# HTTPException to {"error": {"code", "message", "hint"}} — so `data.detail` is
# absent on the wire and a reader that knows only that shape never fires.
# Observed 2026-08-26 in production: a re-invited member could not accept,
# because the invite preview 403'd on their own stale pin and the heal was
# reading a field the envelope had removed. Asserting the string matches the
# server is NOT enough — it must be extracted from the shape it ARRIVES in.

check(
    "the client extracts the detail from BOTH wire shapes",
    "export function errorDetailFrom" in client
    and "error?.message" in client.replace(" ", ""),
    "envelope responses carry error.message, not detail",
)
check(
    "the stale-pin check reads through that extractor, not a raw .detail",
    "isStaleWorkspacePin(\n      response.status,\n      errorDetailFrom(data),\n    )" in client
    or ("errorDetailFrom(data)" in client and "?.detail,\n    );" not in client),
    "a second spelling of the extraction is how the shapes drift",
)
check(
    "the SSE transport uses the same extractor (it hand-builds its headers)",
    "errorDetailFrom(await response.clone().json())"
    in open(os.path.join(REPO, "web", "lib", "api", "chatTransport.ts")).read(),
    "the third transport had the identical blind spot",
)
check(
    "it clears the pin before retrying",
    "clearActiveWorkspace();" in client,
)
check(
    "it retries exactly ONCE (no loop)",
    "__retriedWithoutWorkspace: true" in client
    and "!options.__retriedWithoutWorkspace" in client,
    "an unguarded retry on a persistent 403 would spin forever",
)
check(
    "the retry marker is internal-only (not part of the public surface)",
    "Internal-only" in client and "RequestOptions" in client,
)

# --- 3. an ordinary 403 is NOT swallowed ----------------------------------

check(
    "owner-only verbs can still surface their 403",
    "staleWorkspacePin &&" in client
    and "throw new APIError(response.status" in client,
    "narrow-scoped: a non-matching 403 still throws",
)

print()
if _failures:
    print(f"FAILED {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("ADR-499 gate: all checks passed")
