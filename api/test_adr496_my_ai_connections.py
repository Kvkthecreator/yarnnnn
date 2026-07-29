"""
ADR-496 regression gate — the account door mirrors the member's OWN inbound AI
connections, and governance stays singular.

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
COMPONENT = os.path.join(REPO, "web", "components", "settings", "MyAiConnectionsSection.tsx")
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


comp = open(COMPONENT).read()
page = open(PAGE).read()
roster = open(ROSTER).read()
backend = open(BACKEND).read()

# --- 1. the mirror shows only the VIEWER's own connections ------------------

check(
    "the mirror filters on connected_by_is_you",
    "connected_by_is_you === true" in comp,
    "without this a member would see peers' connections on their personal door",
)
check(
    "the mirror filters to inbound AI roles only",
    "EXTERNAL_AI_ROLES" in comp and "foreign-llm" in comp,
)
check(
    "human roles are NOT rendered here (that is the roster's job)",
    '"owner"' not in comp and "'owner'" not in comp,
)

# --- 2. it is READ-ONLY — governance stays singular -------------------------

for verb, api_call in [
    ("narrow", "narrowMember"),
    ("revoke", "revokeMember"),
    ("invite", "inviteMember"),
    ("spend cap", "setSpendCap"),
]:
    check(
        f"the mirror carries no {verb} verb",
        api_call not in comp,
        f"{api_call} would make this a second governance surface",
    )

check(
    "the roster still owns the governance verbs",
    "revokeMember" in roster,
    "governance must not have MOVED — it stays singular in the roster",
)
check(
    "the mirror links ACROSS to the roster instead of duplicating it",
    "/workspace-settings?pane=members" in comp,
)

# --- 3. the backend still serves the attributed fact ------------------------

check(
    "GET /workspace/members serves connected_by_is_you (ADR-431 D3)",
    "connected_by_is_you" in backend,
    "the mirror's filter depends on this field",
)
check(
    "the member model still carries write_zones (ADR-424 operator zones)",
    "write_zones" in backend,
)

# --- 4. it is mounted on the account door, under the connectors pane --------

check(
    "the mirror is mounted in the settings (account) door",
    "MyAiConnectionsSection" in page,
)
check(
    "it is imported from the settings component home",
    "@/components/settings/MyAiConnectionsSection" in page,
)
check(
    "it is hidden during a connector drill-in",
    '{!accountParam.get("connector") && (\n            <div className="mt-8' in page,
    "the Manage subsurface must render alone",
)
check(
    "the pane subtitle names BOTH directions (outbound + inbound)",
    "platforms you reach out to, and AI assistants that reach in" in page,
    "the old subtitle described only the outbound half",
)

# --- 5. shared rendering primitives, so the two surfaces cannot drift -------

check(
    "the mirror reuses the shared provider brand icons",
    "@/lib/ai-providers/brand-icons" in comp and "@/lib/ai-providers/brand-icons" in roster,
    "two visual languages for one fact would drift",
)

print()
if _failures:
    print(f"FAILED {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("ADR-496 gate: all checks passed")
