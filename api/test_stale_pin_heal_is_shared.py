"""The stale-pin self-heal reaches EVERY transport that sends the pin (ADR-499).

`client.ts::request()` has healed a stale `X-Workspace-Id` since ADR-499. The
chat/SSE transport hand-builds its headers, SENDS the pin, and returns a raw
`Response` — so it never consulted that heal: a stale-pin 403 surfaced as an
ordinary chat error with no clear, no retry and no reload. The member stayed
pinned to an unreachable workspace, on the one surface where they would sit and
retry, while every `request()` caller around them healed.

What this guards:
  1. BOTH transports test the SAME predicate (`isStaleWorkspacePin`) — a second
     transport spelling the 403 signature itself is how the two drift.
  2. The reload guard is SHARED and module-scoped, so a heal in either place
     still produces exactly ONE navigation.
  3. The chat path reads the detail from a CLONE — consuming the body would
     break the caller, which parses its own error detail and streams on success.

Run: python3 test_stale_pin_heal_is_shared.py   (from api/)
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "web")

failures: list = []
checks = 0


def check(label: str, cond: bool) -> None:
    global checks
    checks += 1
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond:
        failures.append(label)


def strip_ts(src: str) -> str:
    """Block comments non-greedily, THEN line comments without DOTALL.

    Combining the two under re.S makes `//.*` run to end-of-file and eat the
    module — the trap that failed a sibling gate against correct code.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//.*", "", src)


client = open(os.path.join(WEB, "lib", "api", "client.ts")).read()
chat = open(os.path.join(WEB, "lib", "api", "chatTransport.ts")).read()
cbody, chbody = strip_ts(client), strip_ts(chat)

print("\n[1] The predicate is shared, not re-spelled")
check("1a. client.ts EXPORTS isStaleWorkspacePin", "export function isStaleWorkspacePin" in cbody)
check("1b. client.ts EXPORTS healStaleWorkspacePin", "export function healStaleWorkspacePin" in cbody)
check("1c. chatTransport IMPORTS both from client",
      "isStaleWorkspacePin" in chbody.split("\n")[0] or
      bool(re.search(r"import\s*\{[^}]*isStaleWorkspacePin[^}]*healStaleWorkspacePin|import\s*\{[^}]*healStaleWorkspacePin[^}]*isStaleWorkspacePin", chbody)))
# The signature must live in ONE place. Count literal occurrences of the server
# string outside the predicate — a second one means a transport re-spelled it.
sig = "No active grant into workspace"
check(
    "1d. the 403 signature string appears ONCE in client.ts (inside the predicate)",
    cbody.count(sig) == 1,
)
check("1e. chatTransport does NOT re-spell the signature", chbody.count(sig) == 0)

print("\n[2] The chat transport actually heals")
check("2a. it calls the shared predicate", "isStaleWorkspacePin(" in chbody)
check("2b. it calls the shared healer", "healStaleWorkspacePin(" in chbody)
check(
    "2c. it only inspects 403s (a 200 stream is never touched)",
    re.search(r"if\s*\(\s*response\.status\s*===\s*403\s*\)", chbody) is not None,
)

print("\n[3] The body survives for the caller")
check(
    "3a. the detail is read from a CLONE, never the response itself",
    "response.clone().json()" in chbody,
)
check(
    "3b. the original response is still returned",
    re.search(r"return\s+response\s*;", chbody) is not None,
)
# NarrativeContext parses its own detail off the same response.
narr = open(os.path.join(WEB, "contexts", "NarrativeContext.tsx")).read()
check(
    "3c. the caller still parses the response body (so it must be unconsumed)",
    "await response.json()" in strip_ts(narr),
)

print("\n[4] One reload, not two")
check(
    "4a. reloadScheduled stays module-scoped in client.ts (shared by both paths)",
    re.search(r"^let reloadScheduled = false;", cbody, re.M) is not None,
)
check(
    "4b. chatTransport does NOT declare its own reload guard",
    "reloadScheduled" not in chbody,
)
check(
    "4c. chatTransport does not call window.location.reload directly "
    "(it must go through the guarded healer)",
    "location.reload" not in chbody,
)

print("\n[5] The pin is still SENT (the ADR-373 invariant this transport exists for)")
check("5a. chatTransport sets X-Workspace-Id", '"X-Workspace-Id"' in chbody)

print(f"\n{'='*66}")
if failures:
    print(f"FAILED {len(failures)}/{checks}")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"PASSED {checks}/{checks}")
