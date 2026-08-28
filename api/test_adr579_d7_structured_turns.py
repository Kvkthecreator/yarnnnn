"""ADR-579 D7 — the pane hosts structured turns (the seed-turn spine).

Defends:
  1. The wire + the stamp: `LaneTurnRequest.seed` (typed), stamped on the
     member's row (the ADR-605 mentions-stamp shape), threaded to the runner.
  2. The rendering: the gesture line composes at the ONE kernel site
     (ADR-606 D1), EXECUTED — with the binding-authority guard and the
     clip-honesty mark.
  3. The FE promotion: the three gesture doors pass a TYPED target — ids and
     excerpts no longer flatten into the member's composer prose; the pane
     holds the target as a chip, sends it once, clears it; the transcript
     renders the stamp back.

Run: python3 test_adr579_d7_structured_turns.py   (from api/)
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
WEB = ROOT.parent / "web"

# ── 1. The wire + the stamp ────────────────────────────────────────────────
lanes_src = (ROOT / "routes" / "lanes.py").read_text()
check("D7 LaneSeed model exists", "class LaneSeed(BaseModel)" in lanes_src)
check("D7 LaneTurnRequest accepts seed",
      re.search(r"class LaneTurnRequest.*?seed: Optional\[LaneSeed\]",
                lanes_src, re.S) is not None)
check("D7 the gesture is STAMPED on the member's row (the ADR-605 shape)",
      'meta["seed"] = seed.model_dump()' in lanes_src)
check("D7 the route threads the seed to the runner",
      "seed=seed.model_dump() if seed else None" in lanes_src)
tree = ast.parse(lanes_src)
_core = next(n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name == "_turn_stream_response")
check("D7 the turn core accepts seed as a parameter (threaded, not closed over)",
      "seed" in {a.arg for a in _core.args.args + _core.args.kwonlyargs})

runner_src = (ROOT / "services" / "lane_runner.py").read_text()
rtree = ast.parse(runner_src)
for fn in ("build_lane_conventions", "run_lane_turn", "run_lane_turn_stream"):
    node = next((n for n in ast.walk(rtree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == fn), None)
    check(f"D7 {fn} accepts seed",
          node is not None
          and "seed" in {a.arg for a in node.args.args + node.args.kwonlyargs})

# ── 2. The rendering — EXECUTED at the one kernel site ─────────────────────
from services.lane_runner import _compose_focus_section  # noqa: E402

_seed = {"verb": "rewrite", "path": "op/deck.html", "block_id": "b3",
         "label": "heading", "excerpt": "Q3 results", "page_index": 2}
out = _compose_focus_section("op/deck.html", "", None, _seed)
check("D7 the gesture line renders (verb, noun, id, excerpt)",
      "clicked Rewrite on the heading block (id b3)" in out
      and '"Q3 results"' in out, out)
check("D7 the gesture names itself as the turn's target",
      "this turn's target" in out)
check("D7 the binding is the authority — a foreign-path seed is silence",
      _compose_focus_section("op/deck.html", "", None,
                             {**_seed, "path": "op/other.md"}) == "")
check("D7 an unbound lane renders the gesture (no binding to guard)",
      "clicked Rewrite on" in _compose_focus_section(None, "", None, _seed))
check("D7 a clipped gesture excerpt says it is one",
      "…" in _compose_focus_section(None, "", None,
                                    {**_seed, "excerpt": "x" * 200}))
check("D7 no seed → byte-identical to focus-only composition",
      _compose_focus_section("op/a.md", "", None, None) == ""
      and _compose_focus_section(
          "op/a.md", '<html data-template="deck"></html>',
          {"scope": "page", "page_index": 0, "viewport_page_index": 0},
          None,
      ) == "\n- The member is viewing slide 1.\n")
check("D7 an unknown verb renders nothing (fail-closed copy)",
      _compose_focus_section(None, "", None, {**_seed, "verb": "delete"}) == "")

# ── 3. The FE promotion ────────────────────────────────────────────────────
studio = (WEB / "components" / "authoring" / "StudioSurface.tsx").read_text()
check("D7 ids no longer flatten into composer prose",
      "(id: ${" not in studio)
# PRE-EXISTING RED, found 2026-08-28 and fixed here rather than left. This
# pinned the ROSTER — three `ask` doors plus `rewrite` plus `check` — and
# ADR-613 then deleted Ask and Check from Slides while ADR-620 routed the
# survivors through ONE producer. So it required doors the product no longer
# has, and had been failing since 613 without anyone reading it as a signal.
#
# D7's claim is that a door passes a TYPED target rather than flattening ids
# into prose (the check above). That is what this now controls for: the seed
# producer exists and every door names its verb through it, whatever the
# roster happens to be.
check("D7 the doors pass typed targets (presence control for the absence above)",
      "const seedRewrite = useCallback(" in studio
      and re.search(r"verb: t\.verb \?\? '\w+'", studio) is not None
      and studio.count("seedComposer('', {") == 1)

lane_panel = (WEB / "components" / "chat-surface" / "LanePanel.tsx").read_text()
check("D7 the slot carries the typed target",
      "target?: SeedTarget" in lane_panel)
check("D7 the pane holds the gesture (pendingSeed armed from the slot)",
      re.search(r"setPendingSeed\(composerSeed\.target \?\? null\)", lane_panel)
      is not None)
check("D7 the gesture fires WITH the send and clears",
      "const seed = pendingSeed ?? undefined;" in lane_panel
      and "setPendingSeed(null);" in lane_panel)
check("D7 the send carries the wire form",
      "seed: opts.seed ? seedToWire(opts.seed) : undefined" in lane_panel)
check("D7 the chip is dismissible (✕ drops the target, wired)",
      re.search(r"onClick=\{\(\) => setPendingSeed\(null\)\}", lane_panel)
      is not None)
check("D7 the transcript renders the stamp back (typed turn, after the fact)",
      "m.role === 'user' && m.seed" in lane_panel
      and "seedFromMeta(m.metadata?.seed)" in lane_panel)

client = (WEB / "lib" / "api" / "client.ts").read_text()
check("D7 the client passes seed up the one wire",
      "...(opts?.seed ? { seed: opts.seed } : {})" in client)

if failures:
    print(f"ADR-579 D7 FAILED ({len(failures)}):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
print("ADR-579 D7 structured turns: all checks passed")
sys.exit(0)
