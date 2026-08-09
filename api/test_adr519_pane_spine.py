#!/usr/bin/env python3
"""Gate: ADR-519 Phase A — the pane speaks one spine.

The Design tab's four scopes each composed their rows ad-hoc (page led with
verbs, container with a media picker, block with typography; Layout sat at a
different position in each; container had no verb row at all). ADR-519 D3
fixes the grammar: **Identity → Position → Layout → Style → Content**, at
every scope — a scope renders only the sections its grain has, and never
re-orders them. Phase A also lands container/block verb-row parity (the same
id-addressed handler the right-click menu uses — ADR-511 D5 made the ops work
on containers with zero op-side change) and the X/Y position readback (the
drag's numeric receipt; numeric ENTRY is Phase C).

Static-source gate: per-site ordering assertions over the scope regions
(never a bare count — the counting-gate lesson). The click-pass owns what a
grep cannot see (the rendered panel).

RE-CUT 2026-08-06 for ADR-528 D2 (its §8's list, intent preserved). `block`
ceased to be a scope: on flow the set is `document | range | object`. Every
claim this gate made about `block` is a claim about a thing with a BOX, so it
moves to `object` unchanged; `range` gets the inverse assertions — the sections
it must NOT compose — because ADR-528's finding was that the old `block (text)`
column was defined by absence, and a column of withdrawals is a scope never
meant to be entered.

The extraction itself was the defect: it hard-coded page→container→block and
sliced regions by that assumed order, so ADR-528's rename left all 16
assertions VOID (they printed one failure and exited, which is the honest
failure mode — but a gate that stops defending its ADR is still a gate that
stopped). Regions are now derived from the source order, and the order is
itself asserted.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

_pass = 0
_fail = 0


def _check(label: str, cond: bool) -> None:
    global _pass, _fail
    print(("[PASS] " if cond else "[FAIL] ") + label)
    if cond:
        _pass += 1
    else:
        _fail += 1


tab = (WEB / "components/studio/StudioDesignTab.tsx").read_text()
surface = (WEB / "components/studio/StudioSurface.tsx").read_text()

# ── The scope regions (extraction must succeed or every ordering claim is void) ──
#
# ADR-528 D2 re-cut (2026-08-06), intent preserved per its §8: `block` is no
# longer a scope. On flow the scope set became `document | range | object`, so
# the pane now renders FIVE regions. Every assertion this gate made about the
# old `block` scope is an assertion about an OBJECT — a thing with a box — and
# moves to `object` verbatim; `range` (a text selection, no box, no single
# subject) inherits none of the spine claims, because it composes none of those
# sections. That is ADR-528's whole point and this gate must not re-assert the
# collapsed grammar.
#
# Regions are sliced by SOURCE ORDER, so the order is derived and asserted
# rather than assumed: a reordered render would otherwise slice regions that
# silently contain each other's sections. The old code hard-coded
# page→container→block; it broke the moment a scope was inserted between them.
_scopes = ["document", "page", "container", "range", "object"]
_marks = {s: re.search(r"\{scope === '%s' && \(" % s, tab) for s in _scopes}
_missing = [s for s, m in _marks.items() if m is None]

# This check runs BEFORE the extraction bail-out, on purpose. Re-collapsing the
# grammar (`object` → `block`) also breaks extraction, and a gate that reports
# only "cannot extract" names the symptom while the CAUSE — the collapsed
# grammar ADR-528 removed — goes unstated. Order the diagnosis before the exit.
_check("ADR-528 D2: no `block` scope region survives (the grammar is not re-collapsed)",
       re.search(r"\{scope === 'block' && \(", tab) is None)

_check("all five ADR-528 scope regions render (document/page/container/range/object)",
       not _missing)
if _missing:
    print(f"FAILED: cannot extract scope regions {_missing} — every assertion below is void")
    sys.exit(1)

_ordered_scopes = sorted(_scopes, key=lambda s: _marks[s].start())
_check("the render order is document → page → container → range → object",
       _ordered_scopes == _scopes)

_bounds = [(s, _marks[s].start()) for s in _ordered_scopes]


def _region(name: str) -> str:
    """The source between this scope's mount and the next scope's mount."""
    i = [n for n, _ in _bounds].index(name)
    start = _bounds[i][1]
    end = _bounds[i + 1][1] if i + 1 < len(_bounds) else len(tab)
    return tab[start:end]


page_r = _region("page")
container_r = _region("container")
# The old `block` region's claims are the OBJECT tier's claims (ADR-528 D2).
object_r = _region("object")
range_r = _region("range")


def ordered(region: str, label: str, *needles: str) -> None:
    """Assert every needle is present AND in strictly increasing position."""
    idx = []
    missing = []
    for n in needles:
        i = region.find(n)
        if i < 0:
            missing.append(n)
        idx.append(i)
    if missing:
        _check(f"{label} — MISSING: {missing[0][:60]!r}", False)
        return
    _check(label, all(a < b for a, b in zip(idx, idx[1:])))


# ── D3: the spine per scope ────────────────────────────────────────────────
# PAGE: Identity (verb row) → Layout → Style (tokens) → Content (background).
ordered(page_r, "page scope spine: Identity(verbs) → Layout → Style → Content(background)",
        "VerbRow noun={pageNoun}",
        ">Layout</p>",
        "applicable.map",
        ">Background</p>")

# CONTAINER: Identity (label + verb row) → Layout → Content (media picker).
ordered(container_r, "container scope spine: Identity(label+verbs) → Layout → Content(image)",
        "selection?.label ?? 'group'}</p>",
        "VerbRow noun={selection?.label ?? 'group'} onVerb={onElementVerb}",
        ">Layout</p>",
        "slotRole === 'media' && (")
_check("container Content: the media picker survives the move (onInsertImageInSlot in region)",
       "onInsertImageInSlot(img.path, selection!.blockId!)" in container_r)

# OBJECT (the old `block` scope — ADR-528 D2 renamed the scope, not the spine):
# Identity → Position → Layout → Style (Typography → Colour → cue) → Content.
#
# Typography and Turn into are asserted by their MOUNTS, not their labels: both
# were lifted out of the render into consts (`rampSection`, `turnIntoSection`)
# so `range` can compose the same section without a forked copy (ADR-528, the
# no-forked-machinery rule). The label literal now sits at the definition site,
# far above every scope region — pinning it here would assert the definition's
# position, not the section's place in this spine.
ordered(object_r, "object scope spine: Identity → Position → Layout → Style → Content",
        # The Identity anchor is the VerbRow's MOUNT, not its argument spelling:
        # the props went multi-line when `reorder` landed (ADR-525 follow-up,
        # 2026-08-06) and a one-line pin failed on a row that still renders.
        # Pin what the assertion is ABOUT (Identity precedes Position), never a
        # formatting accident — the "don't pin a spelling" discipline.
        "<VerbRow",
        ">Position</p>",
        ">Layout</p>",
        "rampSection",
        "ColorTokenSwatches",
        "AppliedSystemCue",
        "turnIntoSection")

# ADR-528 D2 — what `range` must NOT compose. The old `block (text)` column was
# defined almost entirely by ABSENCE, and that column of withdrawals is what
# ADR-528 diagnosed as a scope never meant to be entered. These are now
# non-composition, not suppression: the sections are absent, not gated off.
_check("ADR-528 D2: range composes NO verb row (a range has no box, no subject)",
       "<VerbRow" not in range_r)
_check("ADR-528 D2: range composes NO Position/geometry section",
       ">Position</p>" not in range_r and "sizeMeasures.map" not in range_r)
_check("ADR-528 D2: range composes NO container Layout rows (Hug|Fill, W/H)",
       ">Layout</p>" not in range_r)
# …and the one section that SURVIVES a span, because it acts on the selection
# rather than on a subject (ADR-527 D4, promoted to range's primary section).
_check("ADR-528: the Text (emphasis) section is range's, and acts on the selection",
       "TextSection" in range_r and "onFormat" in range_r)

# ── Verb-row parity (D3/D4 seam): one handler, three entrances ─────────────
_check("the pane declares onElementVerb (StructVerb) in its props",
       re.search(r"onElementVerb:\s*\(verb:\s*StructVerb\)\s*=>\s*void", tab) is not None)
_check("the surface passes the SAME id-addressed handler the menu uses",
       "onElementVerb={handleBlockVerb}" in surface)
_check("handleBlockVerb stays id-addressed (selection?.blockId — containers ride free, ADR-511 D5)",
       re.search(r"handleBlockVerb = useCallback\(\s*\(verb: StructVerb\) => \{\s*"
                 r"const id = selection\?\.blockId;", surface) is not None)

# ── X/Y readback (Phase A: readback, never entry) ──────────────────────────
_check("posMeasures derives x/y from the served measures, block-staged only",
       re.search(r"posMeasures = useMemo\(\(\) => \{\s*\n\s*if \(scope !== 'object' \|\| "
                 r"!selectedEl\?\.closest\('\.slide'\)\) return \[\];", tab) is not None
       and "(m.key === 'x' || m.key === 'y') && admits(m, 'block', { staged: true })" in tab)
_check("the readback renders only in the POSITIONED state (flow shows no coordinates)",
       "positioned && posMeasures.length > 0 && (" in object_r)
# ADR-520 D3 re-cut: numeric ENTRY landed (the two-clamp MeasureField) —
# X/Y fields commit through onSetMeasure; "In flow" stays the only x/y clear.
_check("ADR-520 D3: X/Y entry rides MeasureField through onSetMeasure",
       "onCommit={(v) => onSetMeasure(m.key as 'x' | 'y', v)}" in object_r
       and re.search(r"onSetMeasure:\s*\(key: 'w' \| 'h' \| 'x' \| 'y', value: number\)", tab)
       is not None)

# ── Singular implementation (no duplicate mounts after the moves) ──────────
_check("ONE Position section (the tail mount is deleted, not shadowed)",
       object_r.count(">Position</p>") == 1 and tab.count(">Position</p>") == 1)
# ADR-520 D2 re-cut: the size fields mount at BOTH sizing grains (block Layout
# + staged-container Layout) — exactly two, and never a third Size section.
_check("size fields at exactly the two sizing grains; no Size section revival",
       tab.count("sizeMeasures.map") == 2 and ">Size</p>" not in tab
       and container_r.count("sizeMeasures.map") == 1
       and object_r.count("sizeMeasures.map") == 1)
_check("ONE Turn into mount (moved to Content, not copied)",
       tab.count(">Turn into</p>") == 1)
_check("ONE media-picker mount (moved to container Content, not copied)",
       tab.count("onInsertImageInSlot(img.path") == 1)
_check("nonColorTokens renders exactly once (inside block Layout)",
       tab.count("nonColorTokens.map") == 1)

print()
print(f"{_pass}/{_pass + _fail} checks passed")
if _fail:
    print("FAILED")
    sys.exit(1)
