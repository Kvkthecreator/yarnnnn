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

print("\nD6 — phase 3 (the Supervisor onto the frame; supervisor_state deleted)")
# Phase 3's arms land with phase 3. Nothing is asserted here yet.

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

print("\n" + "=" * 70)
print(f"  {PASS} passed, {FAIL} failed")
print("=" * 70)
if FAIL:
    print("✗ ADR-670 gate RED")
    sys.exit(1)
print("✓ all ADR-670 checks passed")
