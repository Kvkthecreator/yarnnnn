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
m_container = re.search(r"\{scope === 'container' && \(", tab)
m_block = re.search(r"\{scope === 'block' && \(", tab)
m_page = re.search(r"\{scope === 'page' && \(", tab)
_check("the three selection scopes render (container/block/page regions found)",
       bool(m_container and m_block and m_page))
if not (m_container and m_block and m_page):
    print("FAILED: cannot extract scope regions — every assertion below is void")
    sys.exit(1)

page_r = tab[m_page.start():m_container.start()]
container_r = tab[m_container.start():m_block.start()]
block_r = tab[m_block.start():]


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

# BLOCK: Identity → Position → Layout → Style (Typography → Colour → cue) →
# Content (Turn into).
ordered(block_r, "block scope spine: Identity → Position → Layout → Style → Content",
        "VerbRow noun={selection?.label ?? 'block'} onVerb={onElementVerb}",
        ">Position</p>",
        ">Layout</p>",
        'label="Typography"',
        "ColorTokenSwatches",
        "AppliedSystemCue",
        ">Turn into</p>")

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
       re.search(r"posMeasures = useMemo\(\(\) => \{\s*\n\s*if \(scope !== 'block' \|\| "
                 r"!selectedEl\?\.closest\('\.slide'\)\) return \[\];", tab) is not None
       and "(m.key === 'x' || m.key === 'y') && m.applies.includes('block-staged')" in tab)
_check("the readback renders only in the POSITIONED state (flow shows no coordinates)",
       "positioned && posMeasures.length > 0 && (" in block_r)
# ADR-520 D3 re-cut: numeric ENTRY landed (the two-clamp MeasureField) —
# X/Y fields commit through onSetMeasure; "In flow" stays the only x/y clear.
_check("ADR-520 D3: X/Y entry rides MeasureField through onSetMeasure",
       "onCommit={(v) => onSetMeasure(m.key as 'x' | 'y', v)}" in block_r
       and re.search(r"onSetMeasure:\s*\(key: 'w' \| 'h' \| 'x' \| 'y', value: number\)", tab)
       is not None)

# ── Singular implementation (no duplicate mounts after the moves) ──────────
_check("ONE Position section (the tail mount is deleted, not shadowed)",
       block_r.count(">Position</p>") == 1 and tab.count(">Position</p>") == 1)
# ADR-520 D2 re-cut: the size fields mount at BOTH sizing grains (block Layout
# + staged-container Layout) — exactly two, and never a third Size section.
_check("size fields at exactly the two sizing grains; no Size section revival",
       tab.count("sizeMeasures.map") == 2 and ">Size</p>" not in tab
       and container_r.count("sizeMeasures.map") == 1
       and block_r.count("sizeMeasures.map") == 1)
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
