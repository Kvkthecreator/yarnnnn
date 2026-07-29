"""
ADR-496 regression gate — the account door reuses the ROSTER COMPONENT for the
member's own inbound AI connections, and governance stays singular.

Run: `python3 api/test_adr496_my_ai_connections.py`

## What this defends

ADR-431 §2 made an MCP connection a MEMBER's connection (`connected_by`), not
the workspace's. But the only surface rendering it was Workspace Settings →
Members — a governance roster whose job is governing OTHER people. So the
ordinary question "what have I connected?" required opening a workspace surface
and visually filtering.

ADR-496 mirrors the viewer's own rows onto the account door, beside the outbound
platform credentials ADR-425 already homed there. The danger of any mirror is
that it grows into a SECOND governance surface and the two drift. These checks
hold the mirror to being a mirror:

  1. It filters on `connected_by_is_you` — a member never sees a peer's
     connection on their personal door.
  2. It carries NO governance verbs (narrow / revoke / invite / cap).
  3. It links ACROSS to the roster rather than duplicating it.
  4. The backend still serves the attributed fact the filter depends on.
"""

from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(REPO, "web", "app", "(authenticated)", "settings", "page.tsx")
ROSTER = os.path.join(
    REPO, "web", "components", "workspace-concepts", "WorkspaceMembersCard.tsx"
)
BACKEND = os.path.join(REPO, "api", "routes", "workspace.py")

_failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"✓ {label}")
    else:
        print(f"✗ {label}" + (f" — {detail}" if detail else ""))
        _failures.append(label)


page = open(PAGE).read()
roster = open(ROSTER).read()
backend = open(BACKEND).read()

# --- 1. ONE component, not a look-alike (the operator's correction) ----------

check(
    "the account door renders the REAL roster component, not a twin",
    "WorkspaceMembersCard" in page
    and "@/components/workspace-concepts/WorkspaceMembersCard" in page,
    "a second component would drift from the workspace view",
)
check(
    "the look-alike twin is deleted",
    not os.path.exists(
        os.path.join(REPO, "web", "components", "settings", "MyAiConnectionsSection.tsx")
    ),
    "two components for one display is the dual-approach this repo forbids",
)
check(
    "the roster exposes a scope axis",
    "WorkspaceMembersScope" in roster and "scope = 'workspace'" in roster,
)

# --- 2. `mine` shows only the VIEWER's own connections ----------------------

check(
    "the `mine` scope filters on connected_by_is_you",
    "m.connected_by_is_you === true" in roster,
    "without this a member would see peers' connections on their personal door",
)
check(
    "the scope filter runs on the ONE fetch (no second request)",
    "scope === 'mine'" in roster and roster.count("api.workspace.getMembers()") <= 2,
)
check(
    "under `mine` the People section is omitted",
    "scope === 'workspace' && (" in roster,
    "who else is in the workspace is a commons question, not an account one",
)
check(
    "the account door passes scope=\"mine\"",
    'scope="mine"' in page,
)

# --- 3. READ-ONLY — governance stays singular on the workspace door ---------

check(
    "the roster supports readOnly (drops narrow/revoke)",
    "readOnly = false" in roster and "!readOnly && m.role !== 'owner'" in roster,
)
check(
    "the account door passes readOnly",
    "readOnly" in page,
)
check(
    "the roster still owns the governance verbs for the workspace door",
    "revokeMember" in roster,
    "governance must not have MOVED — it stays on the workspace door",
)
check(
    "the account door links ACROSS instead of duplicating governance",
    "/workspace-settings?pane=members" in page,
)

# --- 4. the backend still serves the attributed fact ------------------------

check(
    "GET /workspace/members serves connected_by_is_you (ADR-431 D3)",
    "connected_by_is_you" in backend,
    "the scope filter depends on this field",
)
check(
    "the member model still carries write_zones (ADR-424 operator zones)",
    "write_zones" in backend,
)

# --- 5. mounting ------------------------------------------------------------

check(
    "it is hidden during a connector drill-in",
    '{!accountParam.get("connector") && (' in page,
    "the Manage subsurface must render alone",
)
check(
    "the pane subtitle names BOTH directions (outbound + inbound)",
    "platforms you reach out to, and AI assistants that reach in" in page,
)

print()
if _failures:
    print(f"FAILED {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("ADR-496 gate: all checks passed")
