"""Settings-door polish (2026-08-21) — the four operator-requested changes.

1. Connectors is the LANDING pane and LEADS the nav. The two must agree: the
   page derives its data-loading effects from its own fallback, so a
   disagreement loads one pane's data while rendering another's.
2. A connection's TARGET (where it points) is resolved SERVER-side, once, and
   shown on the list row — three "Connected" rows are otherwise identical
   until you drill into each.
3. The detail header gives the target its own line, not a mid-sentence clause
   between a status word and a date.
4. The workspace door's AI section says whose roster it is.

The target resolver is the load-bearing part: each provider names its target
with a DIFFERENT metadata key (prod 2026-08-21 — slack/notion write
`workspace_name`, github writes `login`; github has no `workspace_name` at
all). Reading one key renders a blank label for GitHub, which looks like a
broken connection rather than a different noun.

Run: python3 test_settings_polish_2026_08_21.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_passed = 0
_failed = 0


def record(name, ok, why=""):
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"PASS  {name}")
    else:
        _failed += 1
        print(f"FAIL  {name}  {why}")


def _src(rel):
    return open(os.path.join(REPO, rel)).read()


def _strip_comments(src: str) -> str:
    """Drop // and /* */ and {/* */} so an assertion cannot match the comment
    that EXPLAINS it — the failure mode that has bitten this repo repeatedly."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)
    return src


# -- 1. the resolver handles every REAL production metadata shape ------------
from services.connectors import connection_target  # noqa: E402

PROD_SHAPES = {
    # keys observed in prod on 2026-08-21
    "slack":  ({"scope": "x", "team_id": "T1", "team_name": "yarnnn",
                "workspace_name": "yarnnn"}, "yarnnn"),
    "notion": ({"owner": {}, "bot_id": "b", "workspace_id": "w",
                "workspace_name": "yarnnn"}, "yarnnn"),
    # github has NO workspace_name — this is the case a single-key read broke
    "github": ({"name": "Kevin Kim", "login": "Kvkthecreator", "scope": "",
                "avatar_url": "", "github_user_id": 1}, "Kvkthecreator"),
}
for platform, (md, expected) in PROD_SHAPES.items():
    record(
        f"connection_target resolves {platform} (real prod metadata shape)",
        connection_target(platform, md) == expected,
        f"got {connection_target(platform, md)!r}, want {expected!r}",
    )

record(
    "an unidentifiable connection yields None (render nothing, not an empty label)",
    connection_target("slack", {}) is None and connection_target("slack", None) is None,
)
record(
    "a whitespace-only name is not a name",
    connection_target("slack", {"workspace_name": "   "}) is None,
)

# -- 2. both endpoints emit it, from the SAME resolver -----------------------
routes = _src("api/routes/integrations.py")
record(
    "the LIST endpoint emits target",
    "target=connection_target(" in routes,
    "the list row cannot distinguish two connections of one provider",
)
record(
    "the DETAIL endpoint emits target from the same resolver",
    '"target": connection_target(' in routes,
    "two faces of one connection could name their target differently",
)

# -- 3. connectors leads AND lands (the two must agree) ---------------------
page = _strip_comments(_src("web/app/(authenticated)/settings/page.tsx"))
record(
    "the shell's default pane is connectors",
    'defaultPane="connectors"' in page,
)
record(
    "the page's own fallback agrees with it",
    ': "connectors";' in page,
    "the page would load one pane's data while the shell renders another",
)
# nav ORDER: Connections must appear before Account in PANE_GROUPS
groups = page[page.index("const PANE_GROUPS"): page.index("const ALL_PANES")]
record(
    "Connections leads the sidebar",
    groups.index('"Connections"') < groups.index('"Account"'),
    "the first nav item is not the pane that loads",
)

# -- 4. the target is rendered on the row and on its own line ---------------
section = _strip_comments(_src("web/components/settings/ConnectedIntegrationsSection.tsx"))
record(
    "the list row renders the target",
    "{target}" in section and "target={" in section,
)
manage = _strip_comments(_src("web/components/settings/ManageConnectionSubsurface.tsx"))
record(
    "the detail header no longer buries the target mid-sentence",
    "` · ${connection.workspace_name}`" not in manage,
    "still rendered between the status word and the date",
)
record(
    "the detail header gives the target its own emphasized line",
    "connection.target ?? connection.workspace_name" in manage
    and "font-medium text-foreground" in manage,
)

# -- 5. the AI section names its scope, per door ----------------------------
members = _strip_comments(_src("web/components/workspace-concepts/WorkspaceMembersCard.tsx"))
record(
    "the workspace door scopes the AI heading to this workspace",
    "'AI connections to this workspace'" in members,
)
record(
    "the account door keeps the unqualified heading (it is already 'yours')",
    "'AI connections'" in members and "scope === 'mine'" in members,
)

# -- 6. no confidently-wrong first frame ------------------------------------
# The roster fetch runs in a MOUNT EFFECT (post-paint). If the loading flag
# starts false, the first frame renders the loaded branch against an EMPTY
# status map: every connector reads as un-connected and falls into "New
# connection", offering platforms that are ALREADY connected. Observed in prod
# 2026-08-21 (Slack offered as new while active). There is no correct render
# before the roster arrives, so the initial state must be "loading".
raw_section = _src("web/components/settings/ConnectedIntegrationsSection.tsx")
m = re.search(r"isLoadingIntegrations,\s*set\w+\]\s*=\s*useState\((\w+)\)", raw_section)
record(
    "the connector roster starts in its loading state",
    bool(m) and m.group(1) == "true",
    f"useState({m.group(1) if m else '?'}) — first frame offers connected "
    "platforms as new",
)
# The drill-in makes the same shape of fetch; it already gets this right.
raw_manage = _src("web/components/settings/ManageConnectionSubsurface.tsx")
record(
    "the connection drill-in starts in its loading state too",
    re.search(r"\[loading,\s*setLoading\]\s*=\s*useState\(true\)", raw_manage)
    is not None,
)

print("=" * 62)
print(f"settings polish gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 62)
sys.exit(1 if _failed else 0)
