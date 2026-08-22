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

# -- 2b. the SUMMARY endpoint EXECUTES with a connected row ------------------
# The two checks above pin a SPELLING, and the spelling stayed green while
# production 500'd on every summary call (2026-08-21→22): `connection_target`
# was imported function-locally in the LIST handler only, and the summary's
# copy of the call named `platform` — a variable that scope does not have.
# Both defects are invisible at import time and to any source grep; the only
# detector is RUNNING the handler with a connection row present, because the
# broken line lives inside `_to_summary`, which executes only for connected
# platforms. The FE consequence was total: loadIntegrations() Promise.all's
# the list and the summary, so the 500 blanked the whole Connectors pane —
# every OAuth reconnect succeeded server-side and rendered as "no update".
import asyncio  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from routes.integrations import get_integrations_summary  # noqa: E402


class _Result:
    def __init__(self, data=None, count=0):
        self.data = data or []
        self.count = count


class _Query:
    def __init__(self, result):
        self._result = result

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def neq(self, *a, **k):
        return self

    def execute(self):
        return self._result


class _StubClient:
    def table(self, name):
        if name == "platform_connections":
            return _Query(_Result(data=[{
                "id": "conn-1",
                "platform": "slack",
                "status": "active",
                "metadata": {"workspace_name": "yarnnn"},
                "landscape": {"resources": [{"id": "C1", "name": "#general"}]},
                "created_at": "2026-08-22T00:00:00Z",
            }]))
        return _Query(_Result(data=[], count=0))


class _StubAuth:
    user_id = "00000000-0000-0000-0000-000000000000"
    client = _StubClient()


try:
    _summary = asyncio.run(get_integrations_summary(_StubAuth()))
    _slack = [p for p in _summary.platforms if p.provider == "slack"]
    record(
        "the SUMMARY endpoint executes end-to-end with a connected row",
        len(_slack) == 1,
        "the connected platform was dropped from the summary",
    )
    record(
        "…and the summary row carries the resolved target",
        bool(_slack) and _slack[0].target == "yarnnn",
        f"target={_slack[0].target!r}" if _slack else "no slack row emitted",
    )
except HTTPException as e:
    record(
        "the SUMMARY endpoint executes end-to-end with a connected row",
        False,
        f"handler raised {e.status_code}: {e.detail} — the prod-blanking shape",
    )
    record("…and the summary row carries the resolved target", False,
           "handler raised before emitting any row")

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

# -- 7. destructive-act treatment: shown-and-disabled, typed where final ----
# Refusal treatment must be CONSISTENT across one pane. The clear cards render
# greyed with "Only the workspace owner can clear shared content"; the delete
# card used to `return null` on 403, so the HEAVIER act was the one that
# vanished — a member could not tell whether deletion was unavailable to them
# or absent from the product. Enforcement is server-side either way
# (_assert_delete_authority / _require_workspace_clear_authority); this is
# legibility.
delete_card = _src("web/components/workspace-concepts/WorkspaceDeleteCard.tsx")
record(
    "a refused delete card is SHOWN with a reason, not hidden",
    "if (forbidden) return null;" not in _strip_comments(delete_card)
    and "Only the workspace owner can delete this workspace." in delete_card,
    "returning null makes the heaviest act invisible to a member",
)
danger = _src("web/components/workspace-concepts/WorkspaceDangerZone.tsx")
record(
    "a refused clear card keeps its stated reason",
    "Only the workspace owner can clear shared content." in danger,
)

# Typed confirmation guards the IRREVERSIBLE acts only.
record(
    "L2 (clear workspace, no undo) requires typing the workspace name",
    "typeToConfirm={activeWorkspaceLabel}" in danger,
)
record(
    "L1 (clear history) does NOT — friction on the lighter act trains "
    "people to type through the heavier one",
    danger.count("typeToConfirm={") == 1,
    f"typeToConfirm wired {danger.count('typeToConfirm={')} times",
)
record(
    "the Confirm button is actually gated on the typed value",
    "disabled={!confirmSatisfied}" in danger,
    "an input nobody checks is theatre",
)
record(
    "purge (destroys history, no undo) requires typing the name too",
    "purgeTyped.trim().toLowerCase() !== preview.name.trim().toLowerCase()"
    in delete_card,
)
record(
    "delete (reversible — Restore sits beside it) stays a two-click act",
    "purgeTyped" in delete_card and "deleteTyped" not in delete_card,
)

print("=" * 62)
print(f"settings polish gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 62)
sys.exit(1 if _failed else 0)
