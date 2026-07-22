#!/usr/bin/env python3
"""ADR-479 gate — Re-arrange as planned judgment.

This gate EXECUTES the validator rather than grepping for it. That distinction
is the whole point of the file: three operator-found defects in this arc
(drag bound to the grip not the card, a context menu that could not hear iframe
clicks, a picker whose reset key churned) all passed grep-shaped gates while
being plainly broken in the browser. `validate_plan` is pure and importable, so
there is no excuse for asserting anything less than its behaviour.

The load-bearing claim (ADR-479 D2): a plan is admissible only if it names real
slots, names real blocks, and accounts for EVERY block exactly once. That last
clause is what retires the content-destruction class — ADR-462 D9 hardens from
"refuse when unmappable" to "account for every block, always". A block missing
from a plan is the destruction bug's exact signature, so it must be rejected.

Also gated structurally (these are wiring facts, not logic): the route exists
and meters once, and the right-click Re-arrange row is GONE (D4).
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "api"))
    web = root / "web"

    from services.studio_arrangement_plan import build_plan_request, validate_plan

    BLOCKS = [
        {"id": "h1", "kind": "heading", "text": "A leaner cost structure"},
        {"id": "p2", "kind": "paragraph", "text": "When you build in a down market…"},
        {"id": "f3", "kind": "figure", "text": ""},
    ]
    SLOTS = [
        {"name": "heading", "role": "heading"},
        {"name": "main", "role": "flow"},
        {"name": "side", "role": "flow"},
    ]
    GOOD = [
        {"block_id": "h1", "slot": "heading"},
        {"block_id": "p2", "slot": "main"},
        {"block_id": "f3", "slot": "side"},
    ]

    # ── 1. THE INVARIANT: total coverage (the content-destruction killer) ───
    ok = validate_plan(GOOD, BLOCKS, SLOTS)
    _check("a complete plan validates and returns its placements",
           ok is not None and len(ok) == 3)
    _check("⭐ a plan that DROPS a block is REJECTED (the destruction signature)",
           validate_plan(GOOD[:2], BLOCKS, SLOTS) is None)
    _check("a plan that places one block TWICE is rejected",
           validate_plan(GOOD + [{"block_id": "h1", "slot": "main"}], BLOCKS, SLOTS) is None)

    # ── 2. THE CLOSED VOCABULARY (D2) ──────────────────────────────────────
    _check("an INVENTED slot is rejected (only declared slots exist)",
           validate_plan(
               [{"block_id": "h1", "slot": "nowhere"}] + GOOD[1:], BLOCKS, SLOTS
           ) is None)
    _check("an INVENTED block id is rejected (no stale/hallucinated ids)",
           validate_plan(
               [{"block_id": "ghost", "slot": "main"}] + GOOD[1:], BLOCKS, SLOTS
           ) is None)
    _check("a malformed placement (not an object) is rejected",
           validate_plan(["nope"], BLOCKS, SLOTS) is None)  # type: ignore[list-item]

    # ── 3. THE HONEST EDGES ────────────────────────────────────────────────
    _check("no blocks to carry → a vacuously valid empty plan (not a refusal)",
           validate_plan([], [], SLOTS) == [])
    _check("content but NO slots → refusal (a layout with nowhere to put it)",
           validate_plan(GOOD, BLOCKS, []) is None)

    # ── 4. THE PROMPT PAYLOAD carries meaning, never markup ─────────────────
    req = build_plan_request(BLOCKS, SLOTS)
    _check("the plan request carries block ids, kinds, and text (judgment reads meaning)",
           "id=h1" in req and "kind=figure" in req and "down market" in req)
    _check("…and the declared slots with their roles",
           "name=side" in req and "role=media" not in req and "role=heading" in req)
    _check("the request contains NO markup (the model never sees or writes HTML)",
           "<" not in req)

    # ── 5. WIRING (structural — these are facts, not logic) ────────────────
    routes = (root / "api/routes/studio.py").read_text()
    _check("the plan route exists",
           '"/studio/arrangement/plan"' in routes)
    _check("it meters ONCE, as judgment, on the one ledger (ADR-396)",
           'slug="studio-arrangement-plan"' in routes
           and 'mode="judgment"' in routes
           and "record_execution_event" in routes)
    _check("the planner reports usage but never ledgers itself (no double-charge)",
           "record_execution_event" not in
           (root / "api/services/studio_arrangement_plan.py").read_text())

    # ── 6. D4 — Re-arrange left the right-click menu ────────────────────────
    menu = (web / "components/studio/StudioBlockMenu.tsx").read_text()
    _check("D4: the page-scoped Re-arrange row is GONE from the block menu",
           "Re-arrange…" not in menu and "onRearrange" not in menu)
    _check("…while the block-scoped AI rows stay (the grammar the menu carries)",
           "Rewrite…" in menu and "Check this…" in menu)

    # ── 7. The FE applies a plan, and still falls back (ADR-468 D4) ─────────
    ops = (web / "components/studio/artifactOps.ts").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    _check("applyArrangementPlan places by the PLAN's slot names",
           "export function applyArrangementPlan" in ops and "bySlotPlan" in ops)
    _check("blocksForPlan sends id/kind/text — never markup",
           "export function blocksForPlan" in ops and "textContent" in ops)
    _check("a refusal falls through to the MECHANICAL ladder (never dead-ends)",
           "planArrangement" in surface and "applyArrangement(html, a.fragment, anchor, slotRoles)" in surface)

    print()
    ok_all = all(c for _, c in _results)
    print(f"{'PASS' if ok_all else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok_all


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
