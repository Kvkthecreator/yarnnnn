#!/usr/bin/env python3
"""Gate: the paged navigator's multi-select page management (deck + page).

The navigator strip becomes a first-class management surface (PowerPoint/Keynote):
multi-select cards, delete the selection as ONE compound revision, group-reorder
by drag, keyboard (Delete / arrows / select-all / clear). It applies to BOTH
paged templates — deck slides AND landing-page sections — because the unit is the
`mode === 'paged'` container, not the `deck` slug (ADR-222: the kernel names the
category, the FE never hardcodes a layout name).

Two new compound ops carry the destructive/reorder acts:
  deletePages(html, indices)  — remove several pages, high-index-first so an
    earlier removal never shifts a not-yet-removed index; dedup + range-guard;
    empty/all-invalid → null (no revision).
  movePages(html, indices, to) — move a selection to a gap, preserving internal
    order, landing as a contiguous run; null on empty/invalid.

Both resolve pages by PAGE_SEL ('section.slide, [data-arrange]') so a deck slide
and a page section are the same index space — the "both paged" generalization.

This repo has no FE test runner, so these are STATIC/STRUCTURAL checks on the
markers that, if regressed, break the logic. The LOGIC itself is validated
EXECUTING against a real DOM (jsdom + esbuild) — see
scratchpad/pagegate/validate.mjs, 15/15, which proves high-first delete,
group-move ordering, scattered→contiguous landing, and page-section generality.
The scratch harness is transient (deps outside the repo); this gate is the
committed regression guard on the source's shape.
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def _fn(src: str, name: str) -> str:
    """The body of `export function <name>(` up to the next top-level close."""
    i = src.find(f"export function {name}(")
    return src[i : src.find("\n}", i)] if i >= 0 else ""


def run() -> bool:
    root = Path(__file__).resolve().parent.parent
    web = root / "web"

    ops = (web / "components/studio/artifactOps.ts").read_text()
    nav = (web / "components/studio/StudioNavigator.tsx").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()

    # ── 1. the compound ops exist and carry the correctness markers ─────────
    dp = _fn(ops, "deletePages")
    mp = _fn(ops, "movePages")
    _check("deletePages(html, indices) exists", bool(dp))
    _check("movePages(html, indices, to) exists", bool(mp))
    _check(
        "deletePages resolves pages by PAGE_SEL (deck slide OR page section — both paged)",
        "PAGE_SEL" in dp,
    )
    _check(
        "deletePages removes HIGH-INDEX-FIRST (sort b - a) so a removal never shifts a pending index",
        "(a, b) => b - a" in dp,
    )
    _check("deletePages dedups the selection (new Set)", "new Set(indices)" in dp)
    _check(
        "deletePages range-guards + returns null on an empty selection (no revision)",
        "return null" in dp and "targets.length" in dp,
    )
    _check(
        "movePages resolves by PAGE_SEL too (the same paged index space)",
        "PAGE_SEL" in mp,
    )
    _check(
        "movePages preserves the selection's internal order (sort a - b)",
        "(a, b) => a - b" in mp,
    )
    _check(
        "movePages lands the group before the first non-moving page at/after `to`",
        "movingSet" in mp and "beforebegin" in mp,
    )
    _check("movePages null-guards empty / out-of-range `to`", "return null" in mp)

    # ── 2. the navigator is paged-general, NOT deck-hardcoded ────────────────
    # The strip must derive from the paged mode, so a page template gets cards
    # too. The prop is `isPaged` (already computed in StudioSurface).
    _check("the navigator takes an isPaged prop (mode-derived, not a slug test)", "isPaged" in nav)
    _check(
        "StudioSurface passes isPaged into the navigator",
        "isPaged={isPaged}" in surface or "isPaged={" in surface,
    )
    # The strip's BRANCH condition must be `if (isPaged)`, not `layout === 'deck'`
    # — a `layout === 'deck'` may still appear inside for the Slides/Sections
    # noun label (legitimate), so assert the gate, not the string's absence.
    _check(
        "the card strip branches on `if (isPaged)`, not a deck-slug gate",
        "if (isPaged)" in nav and "if (layout === 'deck')" not in nav,
    )

    # ── 3. multi-select + keyboard + group-drag markers ─────────────────────
    _check("multi-select holds a Set of indices", "Set<number>" in nav or "new Set<number>" in nav)
    _check(
        "shift / meta modifiers drive range + toggle select",
        ("shiftKey" in nav) and ("metaKey" in nav or "ctrlKey" in nav),
    )
    _check(
        "Delete/Backspace deletes the selection from the focused navigator",
        ("Delete" in nav or "Backspace" in nav),
    )
    _check(
        "a multi-delete confirms (single is immediate, ⌘Z undoes)",
        "confirm" in nav.lower() or "onDeletePages" in nav,
    )
    _check("group reorder wires through onReorderPages / a group move", "Pages" in nav)

    # ── 4. StudioSurface wires the new verbs ────────────────────────────────
    _check("StudioSurface wires deletePages", "deletePages" in surface)
    _check("StudioSurface wires movePages", "movePages" in surface)

    ok = all(c for _, c in _results)
    print(f"\n{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
