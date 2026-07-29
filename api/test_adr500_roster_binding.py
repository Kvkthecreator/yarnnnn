"""
ADR-500 regression gate — the roster cache follows the acting workspace, and a
failed two-call act leaves no orphan.

Run: `python3 api/test_adr500_roster_binding.py`

## The two defects this defends against

Both observed 2026-07-29, by an invited member whose acting workspace had just
been rebound by the ADR-499 self-heal.

**(1) A cache that outlived its binding.** `useWorkspaceMembers` memoizes the
roster in a module-level promise, on the documented assumption that "the
workspace switcher hard-reloads on bind change" (ADR-407 D9). ADR-499's
self-heal rebinds MID-SESSION with no reload, breaking that proviso. The chat
picker then offered a person from the PREVIOUS workspace; the server correctly
422'd ("that person isn't in this workspace") on a choice the FE should never
have presented.

Receipt: seulkim's workspace `4ca9c664` has exactly one human grant (themself),
yet the picker listed `kvkthecreator@gmail.com`, whose grant is in `d5b9029b`.

**(2) A two-call act with no rollback.** Starting a conversation *with someone*
is `create` then `addParticipant`. When the second failed, the first had already
landed — so the member got an error AND an empty conversation they never asked
for. Receipt: lane `d59090d6…`, created 02:02:09 and orphaned by the 422.

## The rules

- **A cache keyed on nothing is keyed on the assumption that nothing changes.**
  When the fact it mirrors can change mid-session, key it to that fact.
- **A multi-call act must not leave partial state behind on failure.**
"""

from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEWER = os.path.join(REPO, "web", "lib", "workspace", "viewer.ts")
CHAT = os.path.join(REPO, "web", "components", "chat-surface", "ChatSurface.tsx")
LANES = os.path.join(REPO, "api", "routes", "lanes.py")

_failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"✓ {label}")
    else:
        print(f"✗ {label}" + (f" — {detail}" if detail else ""))
        _failures.append(label)


viewer = open(VIEWER).read()
chat = open(CHAT).read()
lanes = open(LANES).read()

# --- 1. the roster cache is keyed to the acting workspace ------------------

check(
    "the cache tracks the binding it was fetched under",
    "cacheBinding" in viewer,
)
check(
    "a binding change drops BOTH caches",
    "membersPromise = null" in viewer and "membershipsPromise = null" in viewer,
    "a stale membership list has the same failure mode as a stale roster",
)
check(
    "the binding is read from the active pin",
    "getActiveWorkspaceId()" in viewer,
)
check(
    "both hooks sync before reading the cache",
    viewer.count("syncCacheBinding();") >= 2,
    "one unsynced hook is enough to serve a stale roster",
)
check(
    "the ADR-407 D9 hard-reload assumption is documented as no longer sufficient",
    "ADR-499" in viewer,
    "the next reader must know WHY the key exists",
)

# --- 2. the two-call act rolls back --------------------------------------

check(
    "the created lane is tracked before the second call",
    "let created:" in chat,
)
check(
    "a failed participant-add archives the lane",
    "api.lanes.archive(created.id)" in chat,
)
check(
    "cleanup failure never masks the original error",
    ".catch(() => {})" in chat,
    "the member must see WHY the act failed, not why the cleanup failed",
)
check(
    "the original error is still thrown",
    "throw e instanceof Error ? e : new Error('Could not start this chat')" in chat,
)

# --- 3. the SERVER contract is unchanged (both 422s were correct) ---------

check(
    "the server still rejects a non-member participant",
    "That person isn't in this workspace" in lanes,
    "the gate is correct — the FE simply must not offer the choice",
)
check(
    "the commons boundary is still grant-derived",
    "_workspace_humans" in lanes and 'role") in ("owner", "member")' in lanes,
)

print()
if _failures:
    print(f"FAILED {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("ADR-500 gate: all checks passed")
