"""ADR-644 gate — one reach status: the agent and the member read the same structure.

Run with:  cd api && venv/bin/python test_adr644_one_reach_status.py
(script-style — prints ✗ and exits 1 on failure.)

Every check is falsified by construction — remove the mechanism and it reds:

  D1  THE FACTS DERIVE from the enacting machinery: the capture binding's
      statement, the live read roster, the gate's family classifier, the
      publish seam's door roster. A write tool patched INTO the live surface
      flips `agent_writes` (and every renderer) at once; none composed → empty.
  D2  THREE RENDERERS, ONE STRUCTURE: the frame paragraph for all four reach
      states carries the row facts and ADR-535 D3's fragments; `describe`
      keeps the 585 / 628 / 582 anchors; the `list_integrations` handler and
      the integrations LIST route read the SAME rows through the SAME
      function (driven with one fake client, compared row for row).
  D3  NO RENDERER CARRIES A CONTROL: nothing under this ADR mutates a
      connection; the frame names Settings for consent, the agent page for
      scope, and never a dial.
  D4  THE DELETIONS HOLD: `connector_does` is gone; the lane frame has no
      hand prose branch for reach; there is ONE enumeration reader; the tool
      description names no retired connector; the door roster is mounted
      where it says (pane ↔ `app.slug`, the door's label in the component).
"""

from __future__ import annotations

import asyncio
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


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


import services.turn_reach as _tr  # noqa: E402
from services.connectors import CONNECTOR_CAPTURE_BINDINGS  # noqa: E402
from services.publish import PUBLISH_DOORS, PUBLISH_TARGETS  # noqa: E402
from services.reach_status import (  # noqa: E402
    connection_rows, describe, frame_paragraph, platform_reach, reach_status,
)

# ---------------------------------------------------------------------------
print("D1. the facts derive from the enacting machinery")
_slack = platform_reach("slack", reach_on=True)
_wp = platform_reach("wordpress", reach_on=True)
_gh = platform_reach("github", reach_on=True)
check("captures = the capture binding's own statement",
      _slack and _slack["captures"] == CONNECTOR_CAPTURE_BINDINGS["slack"]["reads"])
check("reads = the read roster a lane composes for the platform",
      _slack and set(_slack["reads"]) == set(_tr.turn_reach_tool_names(("slack",))) and _slack["reads"])
check("an outbound-only platform reads nothing and names its door",
      _wp and _wp["reads"] == [] and _wp["captures"] is None
      and _wp["member_doors"] and _wp["member_doors"][0]["door"] == "Publish")
check("no first-party platform has a live agent write path today (the registry row is a fossil)",
      all((platform_reach(p, reach_on=True) or {}).get("agent_writes") == []
          for p in ("slack", "notion", "github", "wordpress")))
check("an unbound platform derives NO facts", platform_reach("commerce", reach_on=True) is None
      and platform_reach("mcp:linear", reach_on=True) is None)
check("scope is the turn's: None = every granted; a tuple = exactly those; () = none",
      platform_reach("slack", reach_on=True)["in_scope"] is None
      and platform_reach("slack", reach_on=True, scoped_platforms=("slack",))["in_scope"] is True
      and platform_reach("slack", reach_on=True, scoped_platforms=("notion",))["in_scope"] is False
      and platform_reach("slack", reach_on=False, scoped_platforms=())["in_scope"] is False)

# The falsifier: a write tool composed into the LIVE surface flips the fact —
# and therefore every renderer — without anyone editing a sentence.
_orig_names = _tr.turn_reach_tool_names
_tr.turn_reach_tool_names = lambda platforms=None: tuple(_orig_names(platforms)) + ("platform_slack_send_to_channel",)
try:
    _flip = platform_reach("slack", reach_on=True)
    _flip_desc = describe(_flip)
    _flip_frame = frame_paragraph(
        reach_status([{"platform": "slack", "status": "active", "metadata": {"workspace_name": "acme"}}],
                     reach_on=True), "Kev", reach_on=True)
finally:
    _tr.turn_reach_tool_names = _orig_names
check("a write tool composed into the live surface → agent_writes names it, gated by PROPOSAL",
      _flip["agent_writes"] == [{"tool": "platform_slack_send_to_channel", "mode": "propose"}], str(_flip["agent_writes"]))
check("…and the member face says the proposal path", "proposal" in _flip_desc["writes"] and "proposal" in _flip_desc["agents"])
check("…and the agent face says it can post, by PROPOSAL", "you can post with platform_slack_send_to_channel" in _flip_frame and "PROPOSAL" in _flip_frame)
check("…and with none composed, neither face claims it",
      "proposal" not in describe(_slack)["writes"] and "you can post" not in frame_paragraph(
          reach_status([{"platform": "slack", "status": "active", "metadata": {}}], reach_on=True), "Kev", reach_on=True))

# ---------------------------------------------------------------------------
print("D2. three renderers, one structure")
_ROWS = [
    {"platform": "slack", "status": "active", "metadata": {"workspace_name": "acme"}, "created_at": "2026-09-01"},
    {"platform": "wordpress", "status": "active", "metadata": {"login": "kvk"}, "created_at": "2026-09-01"},
    {"platform": "github", "status": "expired", "metadata": {"login": "kvk"}, "created_at": "2026-09-01"},
    {"platform": "mcp:linear", "status": "active", "metadata": {"title": "Linear", "aperture": {"list_issues": "direct"}}, "created_at": "2026-09-01"},
]
_STATES = (
    ("darkened", (False, None), ("cannot read through", "paste it"), ("on your agent page",)),
    ("scoped-to-nothing", (False, ()), ("cannot read through", "scoped you to no connections", "widen your connections on your agent page"), ("connect in settings",)),
    ("unscoped", (True, None), ("read through",), ("cannot read through",)),
    ("scoped-to-slack", (True, ("slack",)), ("you can read through", "slack"), ("cannot read through",)),
)
for _label, (_on, _plats), _must, _must_not in _STATES:
    _status = reach_status(_ROWS, reach_on=_on, scoped_platforms=_plats)
    _para = frame_paragraph(_status, "Kev", reach_on=_on, scoped_platforms=_plats)
    _low = " ".join(_para.lower().split())
    check(f"[{_label}] names the inventory tool", "list_integrations" in _para)
    check(f"[{_label}] states its own edge (ADR-535 D3)", all(f in _low for f in _must) and not any(f in _low for f in _must_not),
          _low[:200])
    check(f"[{_label}] names every first-party row, never the attached one (ADR-635 renders those)",
          "slack (acme)" in _low and "wordpress" in _low and "github" in _low and "[expired]" in _low and "linear" not in _low)
    check(f"[{_label}] names the member's door where the agent cannot",
          "kev can, from the text pane (send to slack)" in _low and "kev can, from the blogger pane (publish)" in _low)
    check(f"[{_label}] never says 'no live'", "no live" not in _low)
_scoped = frame_paragraph(reach_status(_ROWS, reach_on=True, scoped_platforms=("slack",)), "Kev", reach_on=True, scoped_platforms=("slack",))
check("[scoped-to-slack] a platform outside the scope is said to be outside it, not 'cannot read through'",
      "github (kvk) [expired]: outside what kev scoped you to" in " ".join(_scoped.lower().split()))
check("[unscoped] a readable row names the tools it is read with",
      "you read it with platform_slack_list_channels, platform_slack_get_channel_history" in
      frame_paragraph(reach_status(_ROWS, reach_on=True), "Kev", reach_on=True))

_d = describe(_slack)
check("describe keeps the 585 disclosure (engine + pasting) when reach is on",
      "engine" in _d["chat"] and "you picked" in _d["chat"] and "pasting" in _d["chat"])
check("…and says 'cannot reach' when it is off",
      "cannot reach" in describe(platform_reach("slack", reach_on=False))["chat"])
check("describe keeps the 628 anchors for WordPress",
      "publish" in describe(_wp)["writes"] and "never captures" in describe(_wp)["reads"] and "your click" in describe(_wp)["agents"])
check("describe names the member's door on the agents row for a readable platform with a door",
      "cannot send a file there" in _d["agents"] and "Send to Slack" in _d["agents"])


class _Res:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, client, rows):
        self.client, self.rows = client, [dict(r) for r in rows]
        self.selected = None

    def select(self, cols, *_a, **_k):
        self.selected = cols
        return self

    def eq(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) == val]
        return self

    def order(self, *_a, **_k):
        return self

    def execute(self):
        self.client.selects.append(self.selected)
        return _Res(self.rows)


class _Client:
    def __init__(self, rows):
        self.rows, self.selects = rows, []

    def table(self, name):
        assert name in ("platform_connections", "sync_registry"), name
        return _Q(self, self.rows if name == "platform_connections" else [])


_user_rows = [dict(r, user_id="u1", id=f"c{i}", updated_at="2026-09-02") for i, r in enumerate(_ROWS)]
_client = _Client(_user_rows + [{"user_id": "OTHER", "platform": "notion", "status": "active", "metadata": {}}])
_rows = connection_rows(_client, "u1")
check("the ONE enumeration reader is account-scoped and metadata-only",
      [r["platform"] for r in _rows] == [r["platform"] for r in _user_rows]
      and all("credentials" not in (s or "") for s in _client.selects))


class _Auth:
    user_id = "u1"
    workspace_id = None
    client = _client


from services.primitives.registry import handle_list_integrations  # noqa: E402

_tool = asyncio.run(handle_list_integrations(_Auth(), {}))
_tool_rows = {i["platform"]: i for i in _tool["integrations"]}
_status_rows = {f["platform"]: f for f in reach_status(_rows, reach_on=_tr.is_turn_reach_enabled())}
check("the tool result carries the structure's facts, row for row",
      all(_tool_rows[p][k] == _status_rows[p][k]
          for p in ("slack", "wordpress", "github")
          for k in ("name", "target", "captures", "reads", "agent_writes", "member_doors")),
      str(_tool_rows.get("slack")))
check("…and the attached row keeps ADR-635's shape", _tool_rows["mcp:linear"].get("kind") == "attached"
      and _tool_rows["mcp:linear"].get("tools_exposed") == ["list_issues"])
check("…and does not claim scope (that is the frame's fact)", "in_scope" not in _tool_rows["slack"])

from routes.integrations import list_integrations  # noqa: E402

_list = asyncio.run(list_integrations(_Auth()))
_list_rows = {i.provider: i for i in _list.integrations}
check("the integrations LIST route serves the same structure + its rendering",
      all(_list_rows[p].reach[k] == _status_rows[p][k]
          for p in ("slack", "wordpress", "github")
          for k in ("name", "captures", "reads", "agent_writes", "member_doors"))
      and _list_rows["slack"].does == describe(_list_rows["slack"].reach)
      and _list_rows["mcp:linear"].reach is None and _list_rows["mcp:linear"].does is None)

# ---------------------------------------------------------------------------
print("D3. no renderer carries a control")
_rs = (API / "services" / "reach_status.py").read_text()
check("reach_status never writes (no update/upsert/insert/delete on any table)",
      not re.search(r"\.(update|upsert|insert|delete)\(", _rs))
_para = frame_paragraph(reach_status(_ROWS, reach_on=True), "Kev", reach_on=True)
check("the frame points consent to Settings and scope to the agent page, never to a dial here",
      "Connect in Settings" in _para and "dial" not in _para.lower())

# ---------------------------------------------------------------------------
print("D4. the deletions hold")
_conn_src = (API / "services" / "connectors.py").read_text()
check("connector_does is DELETED (the def, not the epitaph)",
      re.search(r"^def connector_does\(", _conn_src, re.MULTILINE) is None)
_lane = (API / "services" / "lane_runner.py").read_text()
check("the lane frame renders the reach section from the structure",
      "frame_paragraph(" in _lane and "reach_status(" in _lane)
check("…and carries no hand-written reach branch",
      not any(s in _lane for s in (
          "list_integrations tells you which platforms",
          "You have no platform reach in this workspace",
          "Seeing a connection is not having it",
          "You cannot send or publish anywhere",
      )))
check("…and the paragraph is composed into the frame (the section is not orphaned)",
      "{connector_reach_section}" in _lane)
_readers = []
for p in sorted((API / "services").rglob("*.py")):
    rel = str(p.relative_to(API))
    if "__pycache__" in rel:
        continue
    src = p.read_text(errors="ignore")
    if 'table("platform_connections")' in src and "id, platform, status, metadata" in src:
        _readers.append(rel)
check("ONE enumeration reader of the connection rows under services/ (the ADR-635 attached reader is its sibling)",
      sorted(_readers) == ["services/attached_connectors.py", "services/reach_status.py"], str(_readers))
from routes.integrations import list_integrations as _list_route  # noqa: E402

check("the two reach faces that enumerate — the tool handler and the LIST route — read through it, never the table",
      'table("platform_connections")' not in inspect.getsource(handle_list_integrations)
      and 'table("platform_connections")' not in inspect.getsource(_list_route)
      and "connection_rows(" in inspect.getsource(handle_list_integrations)
      and "connection_rows(" in inspect.getsource(_list_route))
from services.primitives.registry import LIST_INTEGRATIONS_TOOL  # noqa: E402

_desc = LIST_INTEGRATIONS_TOOL.get("description", "")
check("the tool description names no retired connector and names the doors",
      _desc and "commerce" not in _desc and "trading" not in _desc and "member_doors" in _desc)
_surface = (WEB / "components" / "authoring" / "StudioSurface.tsx").read_text()
for _plat, _door in PUBLISH_DOORS.items():
    _cond = f"app.slug === '{_door['pane'].lower()}' && artifactPath && ("
    _block = _surface.split(_cond, 1)[1].split(")}", 1)[0] if _cond in _surface else ""
    _m = re.search(r"<([A-Z]\w+)", _block)
    _comp = (WEB / "components" / "authoring" / f"{_m.group(1)}.tsx") if _m else None
    check(f"{_plat}: the door is mounted on the {_door['pane']} pane and the component names it",
          bool(_comp) and _comp.exists() and _door["door"] in _comp.read_text(), str(_block[:80]))
check("every publish target has a door", set(PUBLISH_DOORS) >= set(PUBLISH_TARGETS))

print()
if FAILED:
    print(f"ADR-644 gate RED — {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"    - {f}")
    sys.exit(1)
print(f"ALL PASS — {PASSED} checks — ADR-644 holds")
