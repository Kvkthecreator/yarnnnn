"""ADR-664 gate — the member's browser is reach.

    D1  the browser is stated where reach is stated (`reach_status`), and nowhere else
    D2  held, it reaches any website and nothing in the reach section denies it
    D3  absent, it is still named — with how the member gets it
    D4  the frame's tools section claims no reach of its own
    D5  `list_integrations` names websites and no longer refuses
    D6  Reach shows the browser, served from the one structure, in both branches

Script-shaped: run it and READ THE COUNT.

    cd api && python3 test_adr664_the_browser_is_reach.py

Each arm was proven RED by breaking the guarded thing in place and restoring it.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
REPO = API.parent
sys.path.insert(0, str(API))
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "x")

PASS = FAIL = 0


def check(name: str, cond, note: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {note}" if note else ""))


def read(rel: str) -> str:
    p = REPO / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


from services import lane_runner as lr  # noqa: E402
from services.reach_status import browser_does, frame_paragraph  # noqa: E402

print("\nD1–D3 the reach section carries the browser")
_held = frame_paragraph([], "M", reach_on=True, browser_held=True)
_plain = frame_paragraph([], "M", reach_on=True, browser_held=False)
check(
    "held: it reaches any website, a website task goes to it first, and nothing denies it",
    "reaches ANY website" in _held and "goes to the browser first" in _held
    and "cannot send or publish anywhere" not in _held and "Never type a password yourself" in _held,
    _held[-300:],
)
check(
    "held: a connection still never sends",
    "Through a connection you cannot send or publish yourself" in _held,
)
check(
    "absent: the browser is named, with how to get it",
    "yarnnn extension to Chrome" in _plain and "cannot send or publish anywhere" in _plain,
)
runner = read("api/services/lane_runner.py")
check(
    "the frame tells the reach section whether the turn holds the browser",
    'browser_held=any(t["name"] == "BrowserOpen" for t in client_tools)' in runner,
)

print("\nD4 the tools section claims no reach")
check(
    "no reach sentence in the frame outside the reach section",
    "write out to external platforms" not in lr._CONVENTIONS_FRAME
    and "write only to the commons" not in lr._CONVENTIONS_FRAME
    and "BROWSER_FRAME" not in runner and "tools_edge" not in runner,
)
check(
    "no browser reach sentence lives with the tool definitions",
    "BROWSER_FRAME" not in read("api/services/primitives/browser.py"),
)

print("\nD5 list_integrations names websites")
reg = read("api/services/primitives/registry.py")
check(
    "its result says a website needs no connection, and its description no longer refuses",
    '"websites": (' in reg and "Asked to send or publish somewhere, you cannot" not in reg
    and "A WEBSITE needs no connection" in reg,
)

print("\nD6 Reach shows the browser")
_does = browser_does()
check(
    "the member face has the connections' shape",
    {"name", "reads", "writes", "agents"} <= set(_does) and "never allowed" in _does["writes"],
)
route = read("api/routes/integrations.py")
check(
    "GET /integrations serves it from the one structure",
    "browser=browser_does()" in route and "browser: Optional[dict] = None" in route,
)
pane = read("web/components/reach/ReachConnected.tsx")
check(
    "Reach renders the row with connections and without any",
    pane.count("<ReachBrowser does={browserDoes} Fact={Fact} />") == 2,
)
row = read("web/components/reach/ReachBrowser.tsx")
_jsx_text = re.findall(r">\s*([A-Za-z][^<>{}]{3,})\s*<", row)
check(
    "the row writes no reach sentence of its own — served facts and catalog keys only",
    not _jsx_text and "does.reads" in row and "does.writes" in row and "does.agents" in row,
    f"literal text in the row: {_jsx_text}",
)

print(f"\n  {PASS} passed, {FAIL} failed\n")
if FAIL:
    print("✗ ADR-664 checks FAILED")
    sys.exit(1)
print("✓ all ADR-664 checks passed")
