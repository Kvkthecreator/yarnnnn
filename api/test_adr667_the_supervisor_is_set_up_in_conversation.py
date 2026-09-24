"""ADR-667 gate — the Supervisor is set up in conversation, and the browser is its prerequisite.

Run: cd api && python3 test_adr667_the_supervisor_is_set_up_in_conversation.py

Behavior is DRIVEN where it can be (the door, the tool, the write refusal, the
kernel stamp, the trigger) through the real functions with their I/O patched;
the client arms anchor on the guarded EXPRESSION, never a whole-file substring.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

API = Path(__file__).resolve().parent
ROOT = API.parent
WEB = ROOT / "web"
sys.path.insert(0, str(API))

_results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, bool(ok), detail))
    print(f"  {'✓' if ok else '✗'} {name}" + (f" — {detail}" if detail and not ok else ""))


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def code_only_ts(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", src)


MEMBER = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"

# ═══════════════════════════════════════════════════════════════════════════
print("D2. one door, two callers")
# ═══════════════════════════════════════════════════════════════════════════
import services.standing_door as door  # noqa: E402
from services.standing_door import DoorRefusal  # noqa: E402

_routes = read("api/routes/standing_work.py")
check("the composer lives in the door, and only there",
      "def compose_standing_yaml" in read("api/services/standing_door.py")
      and "def compose_standing_yaml" not in _routes and "safe_dump" not in _routes)
check("POST /standing calls door.declare", re.search(r"async def create_standing\(.*?await door\.declare\(", _routes, re.S) is not None)
check("PATCH /standing calls door.revise", re.search(r"async def update_standing\(.*?await door\.revise\(", _routes, re.S) is not None)

# Drive door.declare with its I/O patched: the stamp is the ACTING member.
_written: list[dict] = []


def _patch_door_io():
    from services import authored_substrate
    from services.standing_work import parse_standing_yaml

    door.acting_owner = lambda auth: auth.user_id
    door.read_declaration = lambda client, user_id, topic: None
    door.guard_sources = lambda auth, user_id, decl: None
    door.write_access = lambda auth, path: None

    async def _no_materialize(client, user_id):
        return None

    door.materialize = _no_materialize
    door.parse = lambda content, topic, user_id: parse_standing_yaml(
        content, topic=topic, declaration_path=door.decl_path(topic), user_id=user_id, workspace_id=None)
    authored_substrate.write_revision = lambda client, **kw: _written.append(kw) or "rev"


_patch_door_io()
_auth = SimpleNamespace(user_id=MEMBER, client=None, workspace_id=None,
                        caller_identity=f"member:{MEMBER} via anthropic/claude-sonnet-5")
_decl = asyncio.run(door.declare(_auth, folder="shop/prices", target="prices.md", schedule="0 9 * * 1",
                                 contract="Keep the prices current.", browser_sites=["shop.example.com"]))
_yaml_rev = next((w for w in _written if w["path"].endswith("_standing.yaml")), {})
check("declare stamps the acting member as the browser's member",
      _decl.browser == {"member": MEMBER, "sites": ["shop.example.com"]}
      and f"member: {MEMBER}" in (_yaml_rev.get("content") or ""))
try:
    asyncio.run(door.declare(_auth, folder="x", target="a.md", schedule="0 9 * * *", contract="  "))
    _refused = None
except DoorRefusal as e:
    _refused = e.problem
check("a blank contract is refused by name", _refused == "missing_contract")

# revise: another member may pause, never re-aim, someone's browser work.
_existing = door.compose_standing_yaml(target="prices.md", schedule="0 9 * * 1", paused=False, sources=[],
                                       browser={"member": OTHER, "sites": ["shop.example.com"]})
door.read_declaration = lambda client, user_id, topic: _existing
try:
    asyncio.run(door.revise(_auth, "shop/prices", browser_sites=["evil.example"]))
    _reaimed = None
except DoorRefusal as e:
    _reaimed = e.problem
check("revise refuses re-aiming another member's browser", _reaimed == "browser_not_yours")
_written.clear()
asyncio.run(door.revise(_auth, "shop/prices", paused=True))
check("…and still lets them pause it", any("paused: true" in (w.get("content") or "") for w in _written))

# The tool: registered, takes no member, and passes the caller's attribution.
from services.lane_runner import LANE_ARTIFACT_VERBS, lane_tool_names  # noqa: E402
from services.primitives.declare_work import DECLARE_WORK_TOOL, handle_declare_work  # noqa: E402
from services.primitives.registry import HANDLERS  # noqa: E402

check("DeclareWork is on every lane and dispatchable",
      "DeclareWork" in lane_tool_names() and HANDLERS.get("DeclareWork") is handle_declare_work)
check("its card is what it wrote (an artifact verb)", "DeclareWork" in LANE_ARTIFACT_VERBS)
check("its schema names no member", not any("member" in k for k in DECLARE_WORK_TOOL["input_schema"]["properties"]))

_seen: dict = {}


async def _fake_declare(auth, **kw):
    _seen.update(kw)
    return SimpleNamespace(browser={"member": auth.user_id, "sites": kw["browser_sites"]},
                           target_path="/workspace/shop/p/p.md")

door.read_declaration = lambda client, user_id, topic: None
_real_declare, door.declare = door.declare, _fake_declare
_out = asyncio.run(handle_declare_work(_auth, {"folder": "shop/p", "target": "p.md", "contract": "c",
                                               "sites": ["a.example"], "member": OTHER}))
door.declare = _real_declare
check("DeclareWork goes through door.declare with the caller's attribution",
      _seen.get("authored_by") == _auth.caller_identity and _seen.get("browser_sites") == ["a.example"]
      and "member" not in _seen and _out.get("success") is True)
check("…and its card is the CONTRACT.md it wrote", _out.get("path") == "/workspace/shop/p/CONTRACT.md")

# ═══════════════════════════════════════════════════════════════════════════
print("D2. one way to declare — the write verbs refuse _standing.yaml")
# ═══════════════════════════════════════════════════════════════════════════
from services.primitives.workspace import handle_edit_file, handle_write_file  # noqa: E402

_w = asyncio.run(handle_write_file(_auth, {"path": "shop/prices/_standing.yaml", "content": "target: a.md\n"}))
_e = asyncio.run(handle_edit_file(_auth, {"path": "/workspace/shop/prices/_standing.yaml",
                                          "old_string": "a", "new_string": "b"}))
check("WriteFile refuses _standing.yaml, naming DeclareWork",
      _w.get("error") == "declaration_via_door" and "DeclareWork" in _w.get("message", ""))
check("EditFile refuses it too", _e.get("error") == "declaration_via_door")

# ═══════════════════════════════════════════════════════════════════════════
print("D3. the member stamp holds at the kernel")
# ═══════════════════════════════════════════════════════════════════════════
import services.supabase as _sb  # noqa: E402
from services import runs as _runs  # noqa: E402
from services.standing_work import mark_browser_members, parse_standing_yaml  # noqa: E402


def _browser_decl(member: str):
    body = door.compose_standing_yaml(target="p.md", schedule="0 9 * * 1", paused=False, sources=[],
                                      browser={"member": member, "sites": ["a.example"]})
    return parse_standing_yaml(body, topic="w", declaration_path="/workspace/w/_standing.yaml",
                               user_id=MEMBER, workspace_id="ws-1")


_disc = read("api/services/standing_work.py").split("def discover_standing(")[1].split("\ndef ")[0]
check("discovery runs the stamp check over every declaration it finds",
      "mark_browser_members(d for decls in by_user.values() for d in decls)" in _disc)
_real_reach = _sb.principal_reaches_workspace
_sb.principal_reaches_workspace = lambda uid, ws: uid == MEMBER
_ok, _stranger = _browser_decl(MEMBER), _browser_decl(OTHER)
mark_browser_members([_ok, _stranger])
check("a member who reaches the workspace stays healthy", _ok.problem is None)
check("one who does not is browser_member_unknown", _stranger.problem == "browser_member_unknown")


def _undecidable(uid, ws):
    raise _sb.ReachUndecidable("socket")


_sb.principal_reaches_workspace = _undecidable
_unknown = _browser_decl(OTHER)
mark_browser_members([_unknown])
check("an undecidable check leaves the declaration as it was", _unknown.problem is None)
_sb.principal_reaches_workspace = _real_reach

_touched: list = []
_real_live = _runs.live_for_topic
_runs.live_for_topic = lambda *a, **k: _touched.append(a) or None
_raised = _runs.raise_due(_stranger)
check("raise_due opens no run for a declaration that cannot run",
      _raised.get("success") is False and _raised.get("error_reason") == "browser_member_unknown" and not _touched)

# ═══════════════════════════════════════════════════════════════════════════
print("D7. a run keeps its trigger")
# ═══════════════════════════════════════════════════════════════════════════
_updates: list[dict] = []
_runs.live_for_topic = lambda *a, **k: {"id": "run-1", "state": "waiting"}
_real_update, _runs._update = _runs._update, lambda run_id, fields: _updates.append(fields)
_runs._svc = lambda: None
_rid = _runs.start_browser_run(_ok, lane_id="lane-1")
_runs._update, _runs.live_for_topic = _real_update, _real_live
check("taking up a waiting run keeps trigger: scheduled",
      _rid == "run-1" and _updates and "trigger" not in _updates[0]
      and _updates[0].get("state") == "queued" and _updates[0].get("lane_id") == "lane-1")

# ═══════════════════════════════════════════════════════════════════════════
print("D5. the agent's job, re-derived")
# ═══════════════════════════════════════════════════════════════════════════
from services.agents_registry import AGENTS  # noqa: E402
from services.apps.supervisor import build_supervisor_posture  # noqa: E402

_job = build_supervisor_posture()
check("the job names standing work, DeclareWork and the browser",
      all(w in _job for w in ("standing work", "DeclareWork", "browser", "runs")))
check("the job no longer names a supervisor/ folder or threads",
      "supervisor/" not in _job and "thread" not in _job.lower())
check("the job names no other agent", not re.search(r"\b(Editor|Writer|Researcher|Designer)\b", _job))
check("the character no longer forbids doing work here",
      "work of no thread" not in AGENTS["supervisor"]["posture"])
_skill = read("api/services/skills/declaring-standing-work/SKILL.md")
check("the skill declares through DeclareWork and names the browser",
      "Call DeclareWork" in _skill and "sites:" in _skill and "never by hand" in _skill)

# ═══════════════════════════════════════════════════════════════════════════
print("D1/D4/D6. the pane")
# ═══════════════════════════════════════════════════════════════════════════
_surface = code_only_ts(read("web/components/supervisor/SupervisorSurface.tsx"))
check("the pane mounts the Supervisor's own conversation inside the browser gate",
      re.search(r"<BrowserGate>\s*<Conversation\s+app=\"supervisor\"", _surface) is not None)
# ⭐ DRIVEN 2026-09-24: work retired in the conversation stayed on the roster
# beside it until a reload. The roster re-reads when the agent's turn settles.
_lp = read("web/components/chat-surface/LanePanel.tsx")
check("the cockpit re-reads the roster when the conversation's turn settles",
      re.search(r"onTurnSettled=\{\(\) => \{ void loadRoster\(\); void refreshRuns\(\); \}\}", _surface) is not None
      and re.search(r"\} finally \{.*?onTurnSettled\?\.\(\);", _lp, re.S) is not None)
for gone in ("StartPicker", "NewStandingWorkModal", "StartMark", "WorkConversation"):
    check(f"deleted: {gone}", not (WEB / f"components/supervisor/{gone}.tsx").exists()
          and gone not in _surface)
_client = read("web/lib/api/client.ts")
check("the client no longer creates standing work outside the conversation",
      "StandingCreateRequest" not in _client)
_gate = code_only_ts(read("web/components/supervisor/BrowserGate.tsx"))
# ADR-664 am.1 — the store-link rule lives in the one install action.
check("the install step offers Add to Chrome only with a store listing",
      re.search(r"<AddToChrome\s+fallback", _gate) is not None and "storeUrl" not in _gate)
check("…switch-on only when installed and answering",
      "hands.executor !== null && hands.connected && !hands.on" in _gate)
_sec = code_only_ts(read("web/components/supervisor/SupervisorSection.tsx"))
check("needs-you lists a waiting run only for its own member",
      "r.state === 'waiting' && r.user_id === viewerId" in _sec
      and "runsNeedingYou(band.runs, band.viewerId)" in _sec)
_band = code_only_ts(read("web/components/supervisor/MinderBand.tsx"))
check("the band names whose browser a browser run is in",
      re.search(r"running\?\.kind === 'browser'\s*\?\s*t\('workingBrowser'", _band) is not None)
check("the band raises a run due on the viewer first",
      _band.find("r.state === 'waiting' && r.topic && r.user_id === viewerId") < _band.find("r.problem != null"))
_en = json.loads(read("web/messages/en.json"))
check("working no longer claims the Supervisor does the work",
      "Supervisor" not in _en["supervisor"]["minderBand"]["working"])

# ═══════════════════════════════════════════════════════════════════════════
failed = [n for n, ok, _ in _results if not ok]
print("\n" + "=" * 70)
print(f"  {len(_results) - len(failed)} passed, {len(failed)} failed")
print("=" * 70)
if failed:
    print("✗ ADR-667 gate RED")
    sys.exit(1)
print("✓ all ADR-667 checks passed")
