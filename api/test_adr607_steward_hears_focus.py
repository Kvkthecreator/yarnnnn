"""ADR-607 — the steward hears the typed focus; the operator locator is superseded.

Defends:
  1. The wire: ChatRequest carries typed `focus` (StewardFocus); the ADR-398 D2
     `locator` string is DELETED (absence with presence controls).
  2. The threading: feed → addressed source → wake context, as `operator_focus`.
  3. The rendering: ONE steward site — the addressed ask composes the place
     line + the grain line through the SAME renderer the lanes use, actor
     "The operator". EXECUTED, not grepped.
  4. The renderer: `actor` parameterization leaves the lane copy byte-stable;
     the declared page noun survives without a template (the steward has no
     artifact to derive one from).
  5. The FE: ChatDrawer composes from useCurrentFocus (the declaration), never
     from a URL scrape.

Run: python3 test_adr607_steward_hears_focus.py   (from api/)
"""

import ast
import re
import sys
from pathlib import Path

failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{label}{(': ' + detail) if detail else ''}")


ROOT = Path(__file__).resolve().parent

# ── 1. The wire ─────────────────────────────────────────────────────────────
feed_src = (ROOT / "routes" / "feed.py").read_text()
check("D1 ChatRequest carries typed focus",
      "class StewardFocus(BaseModel)" in feed_src
      and re.search(r"class ChatRequest.*?focus: Optional\[StewardFocus\]",
                    feed_src, re.S) is not None)
check("D1 the locator field is DELETED from the request",
      re.search(r"locator: Optional\[str\]", feed_src) is None)
check("D1 no [:200] locator truncation survives",
      "request.locator" not in feed_src)
check("D1 the route threads the typed focus",
      "operator_focus=request.focus.model_dump()" in feed_src)

# ── 2. The threading ────────────────────────────────────────────────────────
for rel, fn_name in (("services/wake_sources/addressed.py", "stream"),
                     ("services/wake.py", "stream_addressed_wake")):
    src = (ROOT / rel).read_text()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == fn_name), None)
    check(f"D1 {rel}::{fn_name} exists", fn is not None)
    if fn:
        args = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
        check(f"D1 {rel} accepts operator_focus", "operator_focus" in args)
        check(f"D1 {rel} carries no locator parameter",
              "operator_locator" not in args)
wake_src = (ROOT / "services" / "wake.py").read_text()
check("D1 the wake context bag carries operator_focus",
      '"operator_focus": operator_focus' in wake_src)
check("D1 …and no operator_locator key", '"operator_locator"' not in wake_src)

# ── 3. The rendering — EXECUTED ─────────────────────────────────────────────
from agents.freddie_agent import _ask_for_trigger  # noqa: E402

_ctx = {
    "user_message": "tidy this up",
    "conversation_window": "",
    "operator_focus": {
        "app": "slides", "path": "operation/q3/deck.html", "scope": "page",
        "page_index": 3, "viewport_page_index": 3, "label": "slide",
        "id": None, "excerpt": None,
    },
}
ask = _ask_for_trigger("addressed", _ctx)
check("D2 the place line renders from the typed focus",
      "The operator is writing from: slides — operation/q3/deck.html" in ask, ask)
check("D2 the grain line renders through the shared renderer, actor swapped",
      "The operator is viewing slide 4." in ask, ask)
check("D2 no focus → no place lines (silence is honest)",
      "writing from" not in _ask_for_trigger(
          "addressed", {"user_message": "hi", "conversation_window": ""}))
freddie_src = (ROOT / "agents" / "freddie_agent.py").read_text()
check("D2 the locator read is DELETED", "operator_locator" not in freddie_src)

# ── 4. The renderer's actor parameterization ────────────────────────────────
from services.authoring import build_focus_line  # noqa: E402

check("D2 lane copy is byte-stable (default actor)",
      build_focus_line({"scope": "block", "label": "heading",
                        "excerpt": "Pricing"}, "document")
      == '- The member is writing under the heading "Pricing".')
check("D2 the steward actor swaps the subject word only",
      build_focus_line({"scope": "block", "label": "heading",
                        "excerpt": "Pricing"}, "document",
                       actor="The operator")
      == '- The operator is writing under the heading "Pricing".')
check("D2 the declared page noun survives without a template",
      "slide 4" in build_focus_line(
          {"scope": "page", "page_index": 3, "viewport_page_index": 3,
           "label": "slide"}, "document", actor="The operator"))

# ── 5. The FE ───────────────────────────────────────────────────────────────
WEB = ROOT.parent / "web"
drawer = (WEB / "components" / "shell" / "chrome" / "ChatDrawer.tsx").read_text()
check("D1 the URL scrape is DELETED from ChatDrawer",
      "useSearchParams" not in drawer and "k.startsWith(prefix)" not in drawer)
check("D1 ChatDrawer composes from the declaration",
      "useCurrentFocus()" in drawer and "focusToWire(" in drawer)
narrative = (WEB / "contexts" / "NarrativeContext.tsx").read_text()
check("D1 the body carries focus, not locator",
      "body.focus = context.focus" in narrative
      and "body.locator" not in narrative)
panel = (WEB / "components" / "tp" / "ConversationPanel.tsx").read_text()
check("D1 ConversationPanel threads the typed focus",
      "focus?: FocusWire" in panel and "locator" not in panel)

if failures:
    print(f"ADR-607 FAILED ({len(failures)}):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
print("ADR-607 steward-hears-focus: all checks passed")
sys.exit(0)
