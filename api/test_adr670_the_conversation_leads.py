"""ADR-670 — the conversation leads: an index, the object, and its supervision.

Run: python3 api/test_adr670_the_conversation_leads.py   (from the repo root,
or `cd api && python3 test_adr670_the_conversation_leads.py`)

Script-shaped (the house form): prints each check, a count, exits 1 on any
failure. It reads the code, not the product. Every arm anchors on the guarded
EXPRESSION or the one module that must hold it — a whole-file substring cannot
say which caller holds a name, and a bare substring is satisfied by a name that
merely EXTENDS it (`useNeedsYouRENAMED`), so names are matched on word
boundaries. Each arm was proven RED by falsifying the code it guards.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {('— ' + detail) if detail else ''}")


def read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


_SKIP = ("node_modules", ".next", "out", "dist")


def web_sources(exts=(".ts", ".tsx", ".js", ".mjs", ".jsx")) -> list[Path]:
    """Every source file under web/, build output and dependencies excluded."""
    return [
        p for p in WEB.rglob("*")
        if p.is_file() and p.suffix in exts
        and not any(part in _SKIP for part in p.relative_to(WEB).parts)
    ]


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def calls(src: str, name: str) -> bool:
    """`name(` as a whole identifier — never a longer name that extends it."""
    return re.search(rf"(?<![\w$.]){re.escape(name)}\(", src) is not None


WEB_SRC = {rel(p): p.read_text(encoding="utf-8", errors="replace") for p in web_sources()}

PREFS = read("web/lib/shell/useSurfacePreferences.tsx")
ROUTE_SYNC = read("web/lib/shell/route-sync.ts")
STORE = read("web/lib/attention/useNeedsYou.ts")
BELL = read("web/components/shell/AttentionCenter.tsx")
MENTION_Q = read("web/components/notifications/MentionQueue.tsx")
QUEUE_BODY = read("web/components/queue/QueueBody.tsx")
RUN_Q = read("web/components/notifications/WaitingRunQueue.tsx")
NOTIF_PAGE = read("web/app/(authenticated)/notifications/page.tsx")
CHAT = read("web/components/chat-surface/ChatSurface.tsx")
SIDE = read("web/components/chat-surface/ChatSupervision.tsx")
STRIPS = read("web/components/chat-surface/ChatIndexStrips.tsx")
LANE = read("web/components/chat-surface/LanePanel.tsx")
PANES = read("docs/design/PANES.md")

# ═════════════════════════════════════════════════════════════════════════════
print("D1 — boot: nothing to restore opens Chat")
# ═════════════════════════════════════════════════════════════════════════════
# The decision itself is EXECUTED by the ADR-297 gate
# (test_adr297_pathname_follows_foreground.py, group 6); this arm holds only
# that the boot effect calls it and that the executed arm still exists.
check("route-sync exports the one boot decision",
      re.search(r"\bexport function resolveBootSurface\(", ROUTE_SYNC) is not None)
check("the boot effect calls it with the pathname, the home route and the open set",
      re.search(r"(?<![\w$.])resolveBootSurface\(\s*pathname\s*,\s*HOME_ROUTE\s*,\s*open\s*\)", PREFS)
      is not None)
_g297 = read("api/test_adr297_pathname_follows_foreground.py")
check("the ADR-297 gate executes resolveBootSurface on an empty home restore",
      "def test_the_boot_opens_chat" in _g297
      and "resolveBootSurface(p, '/desktop', open)" in _g297
      and 'out["empty_home"] == "chat"' in _g297)
_first = [f for f, s in WEB_SRC.items() if re.search(r"\buseIsFirstTime\b", s)]
check("useIsFirstTime is gone from web/", not _first, ", ".join(_first))

# ═════════════════════════════════════════════════════════════════════════════
print("\nD8 — the drawer's last remains are deleted")
# ═════════════════════════════════════════════════════════════════════════════
_drawer_re = re.compile(r"(?<![\w-])(main-rail|chat-drawer)(?![\w-])")
_web_hits = [f for f, s in WEB_SRC.items() if _drawer_re.search(s)]
check("`main-rail` / `chat-drawer` are absent from web/ source", not _web_hits, ", ".join(_web_hits))
_api_hits = [
    rel(p) for p in (ROOT / "api" / "services").rglob("*.py")
    if _drawer_re.search(p.read_text(encoding="utf-8", errors="replace"))
]
check("`main-rail` / `chat-drawer` are absent from api/services", not _api_hits, ", ".join(_api_hits))

# ═════════════════════════════════════════════════════════════════════════════
print("\nD5 — one needs-you derivation")
# ═════════════════════════════════════════════════════════════════════════════
# The ONE module allowed to read the two sources. A future mount with a
# genuinely different read is named here WITH its reason — never silently.
READERS_ALLOWED = {
    "web/lib/attention/useNeedsYou.ts": "the one client reader (ADR-670 D5)",
}
_CLIENT = "web/lib/api/client.ts"  # defines the methods; calls neither
_readers = sorted(
    f for f, s in WEB_SRC.items()
    if f != _CLIENT and (calls(s, "api.mentions.list") or calls(s, "api.proposals.list"))
)
_rogue = [f for f in _readers if f not in READERS_ALLOWED]
check("useNeedsYou is the only module that calls api.mentions.list / api.proposals.list",
      not _rogue, "also: " + ", ".join(_rogue))
check("…and it does call both (the arm is not vacuous)",
      calls(STORE, "api.mentions.list") and calls(STORE, "api.proposals.list"))
check("waiting runs come from useRuns — no second runs fetch in the store",
      calls(STORE, "useRuns") and not calls(STORE, "api.runs.list"))
check("a run waits on the viewer when it is waiting and runs as the viewer",
      re.search(r"run\.state === 'waiting'", STORE) is not None
      and re.search(r"run\.user_id === viewerId", STORE) is not None)
check("the store carries the bell's freshness: a poll floor and realtime invalidation",
      re.search(r"setInterval\(", STORE) is not None
      and "table: 'session_messages'" in STORE
      and STORE.find("setAuth(") < STORE.find(".subscribe()"))
for _name, _src in (
    ("the bell (AttentionCenter)", BELL),
    ("Notifications → mentions (MentionQueue)", MENTION_Q),
    ("Notifications → decisions (QueueBody)", QUEUE_BODY),
    ("Notifications → runs due (WaitingRunQueue)", RUN_Q),
    ("Chat's index (ChatIndexStrips)", STRIPS),
):
    check(f"{_name} reads useNeedsYou()", calls(_src, "useNeedsYou"))
check("Notifications → To do mounts the runs-due section",
      re.search(r"<WaitingRunQueue\s*/>", NOTIF_PAGE) is not None)
check("the bell's To do renders waiting runs",
      re.search(r"waitingRuns\.slice\(0,\s*MAX_ROWS_PER_SECTION\)\.map", BELL) is not None)
# ADR-637 — the lane read IS the visit; the store must follow it.
_load = re.search(r"api\.lanes\s*\.messages\(laneId\)\s*\.then\(\(res\) => \{(.*?)\}\)", LANE, re.S)
check("the lane read (the visit) refreshes the needs-you store",
      _load is not None and calls(_load.group(1), "refreshNeedsYou"))

# ═════════════════════════════════════════════════════════════════════════════
print("\nD6 — the Supervisor onto the frame; one drill grammar; supervisor_state deleted")
# ═════════════════════════════════════════════════════════════════════════════
SUP_DIR = WEB / "components" / "supervisor"
SUP = read("web/components/supervisor/SupervisorSurface.tsx")
SUP_SEC = read("web/components/supervisor/SupervisorSection.tsx")
DETAIL = read("web/components/supervisor/StandingDetail.tsx")
TRACE = read("web/components/supervisor/RunTrace.tsx")
OPEN_RUN = read("web/lib/runs/openRun.ts")
_api_py = {
    rel(p): p.read_text(encoding="utf-8", errors="replace")
    for p in (ROOT / "api").rglob("*.py")
    if not p.name.startswith("test_") and "node_modules" not in p.parts
}
# `supervisor_state_block` (the Supervisor's per-turn prompt block) is a
# different, live name — the word boundary is what keeps it out of this arm.
_ss_hits = [f for f, src in _api_py.items() if re.search(r"\bsupervisor_state\b", src)]
check("supervisor_state is gone from api/ (module, route, every import)",
      not (ROOT / "api/services/supervisor_state.py").exists() and not _ss_hits, ", ".join(_ss_hits))
check("the route is gone and not mounted",
      not (ROOT / "api/routes/supervisor.py").exists()
      and re.search(r"include_router\(\s*supervisor\.router", read("api/main.py")) is None)
_state_web = [f for f, src in WEB_SRC.items()
              if re.search(r"(?<![\w$])api\.supervisor\s*\.state\b|/api/supervisor/state", src)]
check("the client method and its type are gone (api.supervisor.state)", not _state_web, ", ".join(_state_web))
_nys = [f for f, src in WEB_SRC.items() if re.search(r"\b(NeedsYouSection|runsNeedingYou)\b", src)]
check("the Supervisor's own NeedsYouSection (and its private derivation) is gone", not _nys, ", ".join(_nys))
check("the Supervisor's index mounts the one needs-you strip",
      re.search(r"<NeedsYouStrip\b", SUP) is not None)

_sup_files = {rel(p): p.read_text(encoding="utf-8") for p in SUP_DIR.glob("*.tsx")}
_sup_bp = [f for f, src in _sup_files.items()
           if re.search(r"(?<![\w-])(sm|md|lg|xl):[\w\[\-]", src)]
check("no viewport breakpoint classes in the Supervisor (PANES §11)",
      bool(_sup_files) and not _sup_bp, ", ".join(_sup_bp))
check("the Supervisor measures its own container (usePaneLadder)",
      re.search(r"\[setPaneNode, wb\] = usePaneLadder\(\)", SUP) is not None
      and re.search(r"ref=\{setPaneNode\}", SUP) is not None)
for _slot in ("rail", "side"):
    check(f"the Supervisor composes its {_slot} through the one pane contract",
          re.search(rf"usePaneSlot\(\s*'supervisor'\s*,\s*'{_slot}'", SUP) is not None)
check("single-pane is a bottom tab bar of the three levels' panes",
      re.search(r"\{single && \(\s*<nav\b", SUP) is not None
      and re.search(r"\['index', t\('frame\.tabIndex'\)\]", SUP) is not None)

# The drill grammar: Index → Object (`work`) → Trace (`run`).
check("?supervisor.run= is read as the Trace level",
      re.search(r"const runId = param\.get\('run'\)", SUP) is not None)
check("the Trace renders the run in the canvas through the one RunView",
      re.search(r"runId \? \(\s*<RunTrace runId=\{runId\}", SUP) is not None
      and re.search(r"<RunView\b", TRACE) is not None)
check("each level sets its crumb; the root returns to the index",
      re.search(r"useWindowCrumb\('supervisor',", SUP) is not None
      and re.search(r"const toIndex = \(\) => param\.set\(\{ work: null, run: null", SUP) is not None
      and re.search(r"\[\{ label: t\('frame\.run'\), onClick: toIndex \}\]", SUP) is not None)
check("the Trace param is a momentary look — never replayed on a launch",
      re.search(r"supervisor: \['run', 'start'\]", read("web/lib/shell/surface-preferences.ts")) is not None)

# ONE way to open a run. The four callers the ADR names (the bell, Chat's
# index, To do's runs due, Chat's supervision side) plus the run tray and the
# Supervisor itself all call it; none spells a Supervisor navigation of its own.
check("the one helper exists and opens the Trace (the run id, and its work)",
      re.search(r"\bexport function useOpenRun\(", OPEN_RUN) is not None
      and re.search(r"return \{ work: run\.topic \?\? '', run: run\.id, start: '' \};", OPEN_RUN) is not None)
for _name, _path in (
    ("the bell (AttentionCenter)", "web/components/shell/AttentionCenter.tsx"),
    ("Chat's index (ChatIndexStrips)", "web/components/chat-surface/ChatIndexStrips.tsx"),
    ("To do's runs due (WaitingRunQueue)", "web/components/notifications/WaitingRunQueue.tsx"),
    ("Chat's supervision side (ChatSupervision)", "web/components/chat-surface/ChatSupervision.tsx"),
    ("the run tray (RunTray)", "web/components/runs/RunTray.tsx"),
    ("the Supervisor", "web/components/supervisor/SupervisorSurface.tsx"),
):
    check(f"{_name} opens a run through useOpenRun()", calls(read(_path), "useOpenRun"))
_spelled = [f for f, src in WEB_SRC.items()
            if f != "web/lib/runs/openRun.ts"
            and re.search(r"navigateToSurface\(\s*'supervisor'\s*,", src)]
check("no other spelling of where a run opens (no param-bearing Supervisor navigation elsewhere)",
      not _spelled, ", ".join(_spelled))
check("RunView offers open for ANY run (a Trace needs no work behind it)",
      re.search(r"\{onOpen \? \(", read("web/components/runs/RunView.tsx")) is not None)

# StandingDetail is split between the canvas and the side — never a second
# whole-pane rendering, and no back bar (the crumb replaced it).
check("StandingDetail is not a whole-pane component any more",
      re.search(r"\bexport function StandingDetail\(", DETAIL) is None
      and not [f for f, src in WEB_SRC.items() if re.search(r"<StandingDetail(?![\w])", src)])
check("its two halves mount in the canvas and the side, over one state",
      re.search(r"<StandingDetailCanvas work=\{work\}", SUP) is not None
      and re.search(r"<StandingDetailSide work=\{work\}", SUP) is not None
      and re.search(r"const work = useStandingDetail\(\{", SUP) is not None)
check("no per-surface back bar in the opened work",
      re.search(r"\bonBack\b|detail\.back|\bArrowLeft\b", DETAIL) is None)
check("a declared section lands in the slot its KIND names (no layout prop)",
      re.search(r"export function sectionSlot\(kind: string\)", SUP_SEC) is not None
      and all(re.search(rf"SECTIONS\.filter\(\(s\) => sectionSlot\(s\.kind\) === '{_s}'\)", SUP)
              for _s in ("rail", "side")))
check("the run open in the canvas is left out of every list beside it (one rendering per run)",
      re.search(r"r\.id !== band\.exceptRunId", SUP_SEC) is not None
      and re.search(r"r\.id !== exceptRunId", DETAIL) is not None)
check("PANES §6 names the Supervisor's slots",
      re.search(r"^\| \*\*Supervisor\*\* \|", PANES, re.M) is not None)
check("APP-BUILDER-UX §2.2 says band 3 is composed by the frame",
      "band 3 is composed by the frame" in read("docs/design/APP-BUILDER-UX.md"))
check("compositor.md names `?{slug}.run=` as the Trace level",
      "`?{slug}.run=<id>`" in read("docs/architecture/compositor.md"))

# ═════════════════════════════════════════════════════════════════════════════
print("\nD3 — Chat's supervision side: made here · runs")
# ═════════════════════════════════════════════════════════════════════════════
check("Chat composes a side through the one pane contract",
      re.search(r"usePaneSlot\(\s*'chat'\s*,\s*'side'", CHAT) is not None)
check("the side mounts the supervision", re.search(r"<ChatSupervision\b", CHAT) is not None)
check("the side reads useRuns", calls(SIDE, "useRuns"))
check("its runs are this conversation's and never a chat turn's (ADR-666 D7)",
      re.search(r"r\.lane_id === laneId && r\.trigger !== 'chat'", SIDE) is not None)
check("the side reads no store of its own (no api call)",
      re.search(r"(?<![\w$.])api\.", SIDE) is None)
check("Made here is lifted from the panel — no second read",
      re.search(r"onArtifactsChange=\{setMadeHere\}", CHAT) is not None
      and re.search(r"files=\{madeHere\}", CHAT) is not None
      and re.search(r"onArtifactsChange\?: \(files: MadeHereFile\[\]\) => void", LANE) is not None)
check("the panel reports landed writes only (a pending write may never land)",
      re.search(r"if \(a\.pending \|\| seen\.has\(a\.path\)\) continue;", LANE) is not None)
_bp = re.compile(r"(?<![\w-])(sm|md|lg|xl):[\w\[\-]")
_bp_hits = [n for n, s in (("ChatSurface", CHAT), ("ChatSupervision", SIDE), ("ChatIndexStrips", STRIPS))
            if _bp.search(s)]
check("no viewport breakpoint classes in Chat's panes (PANES §11)", not _bp_hits, ", ".join(_bp_hits))
check("PANES §6 names Chat's side, and §1 no longer says Chat composes none",
      "supervision: made here · runs" in PANES and "Chat composes no side" not in PANES)

# ═════════════════════════════════════════════════════════════════════════════
print("\nD4 — the index: needs you · who · the list")
# ═════════════════════════════════════════════════════════════════════════════
check("the Who faces come from the roster the lane list already carries",
      re.search(r"const whoFaces = useMemo\(\s*\(\)\s*=>\s*\(data\?\.agents \?\? \[\]\)", CHAT) is not None)
check("no second roster read in Chat (one lane-list read, no agents read)",
      len(re.findall(r"(?<![\w$.])api\.lanes\s*\.list\(", CHAT)) == 1
      and re.search(r"(?<![\w$.])api\.(agents|members|workspace)\.", CHAT + STRIPS) is None)
check("a face drives the ONE who-filter state",
      re.search(r"selected=\{whoFilter\}", CHAT) is not None
      and re.search(r"setWhoFilter\(\(cur\) => \(cur === slug \? null : slug\)\)", CHAT) is not None)
check("the retired chip facet is gone (one control for one state)",
      re.search(r"\bpresentWho\b", CHAT) is None)
check("a face with no chat yet starts one through the one create path",
      re.search(r"createLane\(\{ agent: slug \}\)", CHAT) is not None)
check("Chat's rail mounts the needs-you strip",
      re.search(r"<NeedsYouStrip\b", CHAT) is not None)

# ═════════════════════════════════════════════════════════════════════════════
print("\nD7 — the authoring apps: Properties rests, a working turn shows")
# ═════════════════════════════════════════════════════════════════════════════
STUDIO = read("web/components/authoring/StudioSurface.tsx")
TEXT = read("web/components/text/TextEditor.tsx")
check("LanePanel declares the busy slot",
      re.search(r"onBusyChange\?: \(busy: boolean\) => void;", LANE) is not None)
_fire = re.search(r"useEffect\(\(\) => \{\s*if \(reportedBusy\.current === sending\) return;"
                  r"\s*reportedBusy\.current = sending;\s*onBusyChangeRef\.current\?\.\(sending\);\s*\}, \[sending\]\);", LANE)
check("…and fires it from its own `sending`, only when it changes", _fire is not None)


def lane_element(src: str) -> str:
    """The props of the one `<LanePanel …/>` element in a surface."""
    m = re.search(r"<LanePanel\b(.*?)/>\s*\)", src, re.S)
    return m.group(1) if m else ""


for _name, _src, _side_guard, _bar_guard in (
    ("Studio", STUDIO, r"tab === 'chat' && laneBusy && rightTab !== 'chat' && chatLiveMark",
     r"pane === 'chat' && laneBusy && !chatActive && chatLiveMark"),
    ("Text", TEXT, r"tab === 'chat' && laneBusy && railTab !== 'chat' && chatLiveMark",
     r"pane === 'chat' && laneBusy && activePane !== 'chat' && chatLiveMark"),
):
    check(f"{_name} reads the bound lane's busy state (no second store)",
          re.search(r"\bonBusyChange=\{setLaneBusy\}", lane_element(_src)) is not None)
    check(f"{_name}'s Chat tab carries the live mark only while busy and not showing",
          re.search(re.escape(_side_guard), _src) is not None)
    check(f"{_name}'s single-pane bar marks its Chat tab the same way",
          re.search(re.escape(_bar_guard), _src) is not None)
    check(f"{_name}'s mark is the run tray's live dot (one idiom)",
          re.search(r"const chatLiveMark = \(.*?bg-emerald-500 animate-pulse", _src, re.S) is not None)
check("Properties stays the resting tab in both",
      "useState<'chat' | 'design'>('design')" in STUDIO
      and "useState<'properties' | 'chat'>('properties')" in TEXT)

print("\n" + "=" * 70)
print(f"  {PASS} passed, {FAIL} failed")
print("=" * 70)
if FAIL:
    print("✗ ADR-670 gate RED")
    sys.exit(1)
print("✓ all ADR-670 checks passed")
