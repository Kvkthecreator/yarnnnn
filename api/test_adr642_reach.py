"""ADR-642 gate — the boundary has a door: Reach.

Run with:  cd api && venv/bin/python test_adr642_reach.py
(script-style — prints ✗ and exits 1 on failure; under pytest it reports a
false PASS like the other script gates.)

Every check is falsified by construction — remove the mechanism and it reds:

  D1  THE ROW + THE LOCKSTEP: `reach` is a PRIMARY kernel surface (pinned by
      derivation, the boundary glyph, the connectors hue), present in the
      four FE files the ADR-338 parity binds, in DEFAULT_KEPT_SURFACES, with
      a Dock reseed generation — and it has NO AppDescriptor (a kernel
      surface, not an app).
  D2  THE BOUNDARY LENS, DRIVEN: the timeline under `lens=boundary` keeps an
      observation and a publish receipt, drops a plain revision, an
      invocation, a substrate proposal and a pending one; the receipt rides
      the sidecar row (whitelisted keys), weighted material; without the
      lens nothing changes. The fake FILTERS on the PostgREST predicates it
      is handed, so an unfiltered query cannot pass.
  D3  THE GUARDS: the surface reaches no run/pause, no publish, no agents
      API; the lens selects no cost column; no receipt key is cost-shaped.
  D4  QUEUE IS ABSORBED: no roster row, gone from the four FE files, a
      `redirect()` stub into Reach's Leaving pane, hand-listed in middleware,
      retired from the Dock; the To-do escape hatch targets Reach; QueueBody
      takes `families` and Reach mounts the boundary families only.
  D5  WHAT A CONNECTION DOES derives from BOTH write paths: Slack names the
      click AND the gated proposal; WordPress the click alone; GitHub never;
      and `does` rides the integrations LIST.
"""

from __future__ import annotations

import asyncio
import fnmatch
import inspect
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
ROOT = API.parent
WEB = ROOT / "web"
sys.path.insert(0, str(API))

PASSED = 0
FAILED: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASSED
    if cond:
        PASSED += 1
        print(f"  ✓ {label}")
    else:
        FAILED.append(label)
        print(f"  ✗ {label}" + (f" — {detail}" if detail else ""))


def _read(rel: str) -> str:
    return (WEB / rel).read_text()


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


# ---------------------------------------------------------------------------
print("D1. the row + the lockstep")
from services.kernel_surfaces import KERNEL_SURFACES  # noqa: E402

by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
row = by_slug.get("reach")
check("reach is a kernel surface row", row is not None)
check("…PRIMARY, pinned by derivation, an application window",
      bool(row) and row.get("stage") == "primary" and row.get("launcher_tier") == "primary"
      and row.get("default_pinned") is True and row.get("register") == "application"
      and row.get("route") == "/reach", str(row))
check("…wearing the boundary glyph (a key the FE registry knows)",
      bool(row) and row.get("icon_key") == "arrow-left-right"
      and "'arrow-left-right':" in _read("lib/shell/surface-icons.tsx"))
check("…the connectors hue (ADR-641: accent keyed on the SLUG)",
      re.search(r"^\s*reach:\s*'text-cyan-500'", _read("lib/shell/surface-icons.tsx"), re.MULTILINE) is not None)

_surface_ts = _read("types/surface.ts")
# The union's members are the `| 'slug'` lines; comments in that block are
# prose (an older one carries a semicolon, so "up to the first semicolon"
# is not a safe cut). Read the ROWS, not a region.
_union = _surface_ts.split("export type KernelSurfaceSlug", 1)[1].split("export const KERNEL_SURFACE_SLUGS", 1)[0]
_union_slugs = set(re.findall(r"^\s*\|\s*'([a-z0-9-]+)'", _union, re.MULTILINE))
_arr = re.search(r"KERNEL_SURFACE_SLUGS.*?=\s*\[(.*?)\]\s*as const", _surface_ts, re.DOTALL)
_arr_slugs = set(re.findall(r"'([a-z0-9-]+)'", _strip_comments(_arr.group(1) if _arr else "")))
_reg = re.search(r"KERNEL_SURFACE_REGISTRY.*?=.*?\{(.*?)\n\};", _read("components/shell/SurfaceRegistry.tsx"), re.DOTALL)
_reg_keys = set(re.findall(r"^\s*'?([a-z0-9-]+)'?\s*:", _strip_comments(_reg.group(1) if _reg else ""), re.MULTILINE))
check("reach is in the FE slug union", "reach" in _union_slugs)
check("reach is in the FE allowlist", "reach" in _arr_slugs)
check("reach is in the FE component registry", "reach" in _reg_keys)
check("the route page exists", (WEB / "app/(authenticated)/reach/page.tsx").exists())

_prefs = _read("lib/shell/surface-preferences.ts")
_kept = re.search(r"export const DEFAULT_KEPT_SURFACES: string\[\] = \[(.*?)\];", _prefs, re.DOTALL)
_kept_slugs = re.findall(r"'([a-z0-9-]+)'", _strip_comments(_kept.group(1) if _kept else ""))
check("reach is in DEFAULT_KEPT_SURFACES (the hand-kept copy of the derivation)", "reach" in _kept_slugs)
check("…last: the record, its residents, its boundary", _kept_slugs[-3:] == ["files", "agents", "reach"], str(_kept_slugs))
check("a Dock reseed generation carries the add", "dock-reseed-2026-09-07-reach" in _prefs)
_apps = _read("lib/apps/registry.ts")
check("reach has NO AppDescriptor — a kernel surface, not an app (ADR-636/639)",
      "slug: 'reach'" not in _apps and 'slug: "reach"' not in _apps)

# ---------------------------------------------------------------------------
print("D2. the boundary lens, driven")


class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    """A dict-backed PostgREST query that FILTERS on every predicate it is
    handed — so an unfiltered route cannot pass (the fake carries the
    falsifier)."""

    def __init__(self, client, name, rows):
        self.client, self.name = client, name
        self.rows = [dict(r) for r in rows]

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) == val]
        return self

    def neq(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) != val]
        return self

    def in_(self, col, vals):
        vals = set(vals)
        self.rows = [r for r in self.rows if r.get(col) in vals]
        return self

    def lt(self, col, val):
        self.rows = [r for r in self.rows if (r.get(col) or "") < val]
        return self

    def or_(self, expr):
        clauses = [tuple(part.split(".", 2)) for part in expr.split(",")]

        def ok(r):
            for col, op, val in clauses:
                v = r.get(col)
                if op == "eq" and v == val:
                    return True
                if op == "like" and v is not None and fnmatch.fnmatchcase(str(v), val):
                    return True
            return False

        self.rows = [r for r in self.rows if ok(r)]
        return self

    def order(self, col, desc=False):
        self.rows.sort(key=lambda r: r.get(col) or "", reverse=desc)
        return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    def execute(self):
        self.client.executed.append(self.name)
        return _Res(self.rows)


class _Client:
    def __init__(self, tables):
        self.tables, self.executed = tables, []

    def table(self, name):
        return _Q(self, name, self.tables.get(name, []))


class _Auth:
    def __init__(self, client):
        self.user_id = "00000000-0000-0000-0000-0000000000a1"
        self.workspace_id = "ws1"
        self.client = client


_SIDECAR = "/workspace/operation/brief/_publish.yaml"
_TABLES = {
    "workspace_file_versions": [
        {"workspace_id": "ws1", "path": "/workspace/inbound/slack/general/2026-09-07T10.md",
         "authored_by": "system:capture-slack", "author_identity_uuid": None, "message": "captured",
         "revision_kind": "observation", "created_at": "2026-09-07T10:00:00+00:00"},
        {"workspace_id": "ws1", "path": _SIDECAR,
         "authored_by": "operator", "author_identity_uuid": "u", "message": "sent to Slack #general",
         "revision_kind": "derivation", "created_at": "2026-09-07T11:00:05+00:00"},
        {"workspace_id": "ws1", "path": "/workspace/operation/brief/brief.md",
         "authored_by": "member:u via x", "author_identity_uuid": "u", "message": "edit",
         "revision_kind": "authored", "created_at": "2026-09-07T09:00:00+00:00"},
        {"workspace_id": "OTHER", "path": "/workspace/inbound/slack/x/1.md",
         "authored_by": "system:capture-slack", "revision_kind": "observation",
         "created_at": "2026-09-07T12:00:00+00:00"},
    ],
    "execution_events": [
        {"workspace_id": "ws1", "slug": "standing:brief", "mode": "mechanical", "status": "success",
         "trigger_type": "cron", "principal_id": "u", "created_at": "2026-09-07T08:00:00+00:00"},
    ],
    "action_proposals": [
        {"workspace_id": "ws1", "id": "p-ext", "primitive": "platform_slack_send_to_channel",
         "family": "external-write", "status": "approved", "source": "agent:x",
         "approved_by": "u", "created_at": "2026-09-07T07:00:00+00:00", "approved_at": "2026-09-07T07:30:00+00:00"},
        {"workspace_id": "ws1", "id": "p-sub", "primitive": "write_file", "family": "substrate",
         "status": "approved", "source": "agent:x", "approved_by": "u",
         "created_at": "2026-09-07T06:00:00+00:00", "approved_at": "2026-09-07T06:30:00+00:00"},
        {"workspace_id": "ws1", "id": "p-pend", "primitive": "platform_slack_send_to_channel",
         "family": "external-write", "status": "pending", "source": "agent:x",
         "approved_by": None, "created_at": "2026-09-07T05:00:00+00:00", "approved_at": None},
    ],
    "workspace_files": [
        {"workspace_id": "ws1", "path": _SIDECAR, "content": (
            "- platform: wordpress\n  url: https://w.test/1\n  status: publish\n  at: '2026-09-01T10:00:00+00:00'\n"
            "- platform: slack\n  channel: '#general'\n  ts: '1'\n  url: https://slack.test/p1\n  status: posted\n"
            "  at: '2026-09-07T11:00:03+00:00'\n  read_back: matched\n  chars: 120\n  folded: false\n  composer_version: 1\n"
        )},
    ],
    "principal_grants": [],
}

import services.workspace_context as _wsc  # noqa: E402
import services.supabase as _sb  # noqa: E402
from routes.workspace import (  # noqa: E402
    BOUNDARY_PROPOSAL_FAMILIES, _RECEIPT_KEYS, get_workspace_timeline, receipt_for_revision,
)

check("the route takes a `lens`", "lens" in inspect.signature(get_workspace_timeline).parameters)
check("the boundary families are the two that cross", set(BOUNDARY_PROPOSAL_FAMILIES) == {"external-write", "capital"})

_orig_scope, _orig_eff, _orig_svc = _wsc.substrate_scope_filter, _wsc.effective_workspace_id, _sb.get_service_client
_wsc.substrate_scope_filter = lambda uid, wid=None: ("workspace_id", "ws1")
_wsc.effective_workspace_id = lambda uid, wid=None: "ws1"
try:
    client = _Client(_TABLES)
    _sb.get_service_client = lambda: client
    res = asyncio.run(get_workspace_timeline(_Auth(client), limit=40, before=None, lens="boundary"))
    kinds = {e.kind for e in res.entries}
    paths = {e.path for e in res.entries if e.kind == "revision"}
    pids = {e.proposal_id for e in res.entries if e.kind == "proposal"}
    check("under the lens only revisions + proposals appear", kinds <= {"revision", "proposal"}, str(kinds))
    check("an observation ARRIVED", "/workspace/inbound/slack/general/2026-09-07T10.md" in paths)
    check("a publish receipt LEFT", _SIDECAR in paths)
    check("a plain revision does not cross", "/workspace/operation/brief/brief.md" not in paths)
    check("another workspace's rows never appear", "/workspace/inbound/slack/x/1.md" not in paths)
    check("a decided boundary proposal LEFT", "p-ext" in pids)
    check("a substrate proposal never leaves; a pending one has not crossed", "p-sub" not in pids and "p-pend" not in pids, str(pids))
    check("the invocation ledger is not even queried under the lens", "execution_events" not in client.executed, str(client.executed))
    sidecar_row = next((e for e in res.entries if e.path == _SIDECAR), None)
    check("the receipt rides the sidecar row — the entry it APPENDED, not the older one",
          sidecar_row is not None and (sidecar_row.receipt or {}).get("platform") == "slack"
          and sidecar_row.receipt.get("read_back") == "matched", str(sidecar_row and sidecar_row.receipt))
    check("…whitelisted keys only (no `ts`, no composer internals)",
          sidecar_row is not None and set(sidecar_row.receipt or {}) <= set(_RECEIPT_KEYS)
          and "ts" not in (sidecar_row.receipt or {}))
    check("…and a receipt is MATERIAL at the boundary (never housekeeping)",
          sidecar_row is not None and sidecar_row.weight == "material")
    obs_row = next((e for e in res.entries if e.path and e.path.startswith("/workspace/inbound/")), None)
    check("an observation carries no receipt", obs_row is not None and obs_row.receipt is None)

    client2 = _Client(_TABLES)
    _sb.get_service_client = lambda: client2
    plain = asyncio.run(get_workspace_timeline(_Auth(client2), limit=40, before=None))
    ppaths = {e.path for e in plain.entries if e.kind == "revision"}
    check("without the lens the plain revision and the invocation are back",
          "/workspace/operation/brief/brief.md" in ppaths and any(e.kind == "invocation" for e in plain.entries))
    check("…and no row carries a receipt", all(e.receipt is None for e in plain.entries))
finally:
    _wsc.substrate_scope_filter, _wsc.effective_workspace_id, _sb.get_service_client = _orig_scope, _orig_eff, _orig_svc

check("receipt_for_revision picks the newest entry not after the revision (pure)",
      (receipt_for_revision(
          [{"at": "2026-09-01T10:00:00+00:00", "platform": "a"}, {"at": "2026-09-07T11:00:03+00:00", "platform": "b"},
           {"at": "2026-09-08T00:00:00+00:00", "platform": "c"}],
          "2026-09-07T11:00:05+00:00") or {}).get("platform") == "b")
check("…and falls to the last when nothing dates", (receipt_for_revision([{"platform": "z"}], "x") or {}).get("platform") == "z")

# ---------------------------------------------------------------------------
print("D3. the guards")
_reach_src = "\n".join(
    _read(p) for p in (
        "app/(authenticated)/reach/page.tsx",
        "components/reach/ReachConnected.tsx",
        "components/reach/BoundaryLedger.tsx",
    )
)
check("Reach reaches no run / pause switch (they stay in Notifications → Standing work)",
      "api.standing.run" not in _reach_src and "api.standing.update" not in _reach_src)
check("Reach carries no publish act (the act stays on the artifact's pane, ADR-628 D2)",
      "api.publish." not in _reach_src and "SendToSlack" not in _reach_src and "StudioPublish" not in _reach_src)
check("Reach presents no agent record (ADR-640)", "api.agents" not in _reach_src)
check("Reach doors to Settings → Connectors for consent, never connects itself",
      "navigateToSurface('connectors')" in _reach_src and "getAuthorizationUrl" not in _reach_src)
_ws_src = (API / "routes" / "workspace.py").read_text()
_tl = _ws_src.split("async def get_workspace_timeline", 1)[1]
check("the lens selects no cost column", "cost_usd" not in _tl and "input_tokens" not in _tl)
check("no receipt key is cost-shaped", not any("cost" in k or "token" in k for k in _RECEIPT_KEYS))
check("Crossed renders through the shared timeline-rows grammar (one narrative, Axiom 9)",
      "from '@/lib/workspace/timeline-rows'" in _read("components/reach/BoundaryLedger.tsx")
      and "lens: 'boundary'" not in _read("components/notifications/ActivityLedger.tsx"))

# ---------------------------------------------------------------------------
print("D4. queue is absorbed")
check("no `queue` roster row", "queue" not in by_slug)
check("queue left the FE union, allowlist and registry",
      "queue" not in _union_slugs and "queue" not in _arr_slugs and "queue" not in _reg_keys)
# Comments stripped first: the stub's own docblock says "never a client
# useEffect redirect", and a gate that greps its own documentation goes red
# on the sentence explaining the rule.
_stub = _strip_comments(_read("app/(authenticated)/queue/page.tsx"))
check("/queue is a server redirect() stub into Reach's Leaving pane (ADR-308)",
      "redirect('/reach?reach.pane=leaving')" in _stub and "'use client'" not in _stub and "useEffect" not in _stub)
_mw = _strip_comments(_read("lib/supabase/middleware.ts"))
check("\"/queue\" is hand-listed in middleware (the ADR-592 obligation)", '"/queue"' in _mw)
_retired = re.search(r"DOCK_RETIRED_SLUGS = new Set<string>\(\[(.*?)\]\)", _prefs, re.DOTALL)
check("queue is retired from the Dock (no ghost icon)", bool(_retired) and "'queue'" in _retired.group(1))
_notif = _read("app/(authenticated)/notifications/page.tsx")
check("the To-do escape hatch targets Reach, not the dead surface",
      'navigateToSurface("reach"' in _notif and 'navigateToSurface("queue")' not in _notif)
_qb = _read("components/queue/QueueBody.tsx")
check("QueueBody takes `families` (one body, three mounts — ADR-346)",
      "families?: readonly QueueFamily[]" in _qb and "families.includes(" in _qb)
check("Reach mounts the boundary families only; To do mounts everything",
      "<QueueBody families={['external-write', 'capital']} />" in _read("app/(authenticated)/reach/page.tsx")
      and "<QueueBody />" in _notif)

# ---------------------------------------------------------------------------
print("D5. what a connection does derives from BOTH write paths")
from services.connectors import connector_does  # noqa: E402

_slack = connector_does("slack") or {}
_wp = connector_does("wordpress") or {}
_gh = connector_does("github") or {}
check("Slack: the click AND the gated proposal are both named",
      "your click" in _slack.get("writes", "") and "proposal" in _slack.get("writes", ""), _slack.get("writes"))
check("…and the agents fact says where an agent's post goes", "proposal" in _slack.get("agents", ""), _slack.get("agents"))
check("WordPress: the click alone", "publish" in _wp.get("writes", "") and "proposal" not in _wp.get("writes", ""), _wp.get("writes"))
check("GitHub: never writes", "never writes" in _gh.get("writes", ""), _gh.get("writes"))
from routes.integrations import IntegrationResponse  # noqa: E402
check("`does` rides the integrations LIST", "does" in IntegrationResponse.model_fields)
check("…and the list handler fills it", "does=(None if attached else connector_does(platform))" in (API / "routes" / "integrations.py").read_text())

print()
if FAILED:
    print(f"ADR-642 gate RED — {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"    - {f}")
    sys.exit(1)
print(f"ALL PASS — {PASSED} checks — ADR-642 holds")
