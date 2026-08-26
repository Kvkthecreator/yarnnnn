# ADR-613 — The judged act leaves the menus: Slides joins the one gesture

**Status**: Implemented (2026-08-26)
**Completes**: [ADR-612](ADR-612-the-judged-act-is-one-gesture-at-the-selection.md) §6 — the Slides half it scoped and owed.
**Supersedes**: [ADR-462](ADR-462-the-block-context-menu-and-the-metered-badge.md) D4's *placement* (the metered line is no longer drawn in the block menu — it is drawn at the gesture) · [ADR-586](ADR-586-one-insert-door-categories-galleries-contextual-update.md) D6's second-menu route · [ADR-589](ADR-589-update-is-a-door-over-the-selection-matrix.md) D5's object-rung answer.
**Does NOT change**: ADR-589's selection LADDER, which keeps the mechanical acts — the two doors answer different questions (ADR-612 §1).

---

## 1. What was measured

Driven in production, the judged act cost **four hops in Slides** and **one in
Text**:

> `Update` → two-pane door → ladder rung → `Move, turn into, rewrite…` →
> block menu → `Rewrite…` → chat flips

versus `select → sparkle → chat`. Same intent, two vocabularies, four hops
apart.

## 2. Decisions

### D1 — The three judged verbs leave the block menu

`Rewrite…` and `Check this…` move to the ADR-612 gesture. **`Ask about this…`
is DELETED outright** (operator's ruling): it is rebuildable from the same seed
machinery if it is ever wanted back, and keeping one metered row stranded in a
menu whose two siblings left is the shape this ADR exists to remove.

**The `Ask` tier goes with them.** Every row in it was judged, so the tier, its
`askOpen` state (and six reset call-sites), its flyout and its hover handler
are vacuous — not shrunken, vacuous.

### D2 — The `meter` discriminator is DELETED, not left latent

With no metered row remaining, `meter` marks nothing. The prop, the amber `AI`
badge, the amber hover and icon classes, and the `!meter && shortcut` guard are
all removed.

**ADR-462 D4's free/metered LINE is not abandoned** — it is drawn where the
metered act now lives. What is removed is a discriminator with nothing to
discriminate, which is a second spelling waiting to happen (the ADR-592
six-spellings lesson, and the two `hidden` readers before it).

### D3 — Slides supplies the one thing it lacked: a selection RECT

`StudioSelection` carries identity and never geometry. Every iframe message
carried either a pointer POINT (`yarnnn-context-menu`, which ADR-612 D1
refuses) or no coordinates at all — `yarnnn-range` is even deduped by id-set,
so it would not re-fire when a selection's geometry changed within the same
blocks.

So the runtime now posts `yarnnn-selection-rect`: the selection's **visual
box**, for both grains (`showBox` for a block, the format bar's own
`selectionchange` rect for a text range), retracted when the subject is lost.

**It must NOT zoom-divide.** Dividing by `zf()` is correct only for
body-appended chrome inside the zoomed document (the format bar). A
parent-side door needs the raw visual rect; `StudioCanvas` maps it with
`+ iframeRect.left/top` and **no zoom multiply** — the mapping already proven
by the context-menu bridge, whose comment records that multiplying put the menu
at ~37% of the offset on a deck.

**The gesture renders parent-side, never in the iframe** — *chrome never enters
the artifact* (the standing rule at the context-menu mount). The in-iframe
format bar is the precedent for POSITIONING, not a host for our door.

### D4 — The chip's noun and the anchor are decided TOGETHER

Slides has a grain Text does not: a text RANGE inside a block and the BLOCK are
different targets. `gestureTarget` derives the noun *and* the seed label from
the grain the runtime reported, so they cannot drift. Without that, the member
thinks they are rewriting three words and the whole block comes back changed —
the ADR-373 D6 incorrect-success class, one layer up.

The range's address is still `block_id`: HTML has no source offsets, so that is
this medium's address (ADR-609 D2). The noun still says "the selection" because
that is what the member has, and the frame carries the excerpt to narrow it.

### D5 — The second-menu route is deleted whole

ADR-589's object rung was the only rung that mounted another MENU instead of
the pane, and its label named a verb that has now left (`rewrite`). Everything
it reached — turn into, move up/down, bring forward/backward — is already in
the object scope of the pane the adjacent row opens.

Deleted end to end: the row, `onBlockActs` (prop + wiring), `openBlockActs`,
`ctxInitialOpen` and its two resets, `initialOpen` on the menu, and the now-dead
`Sparkles` import in the door. The rung now reads like every other rung: **one
row → the dwell.** `StudioBlockMenu` reverts to right-click-only.

## 3. What this does NOT change

- **ADR-589's ladder.** It answers *which nested thing am I shaping* — real for
  mechanical acts where the target is ambiguous. The judged act needs no
  ladder because the selection already IS the target (ADR-612 §1).
- **ADR-462 D1.** No new write path: the gesture seeds the composer exactly as
  the deleted rows did.
- **The in-frame format bar.** Untouched; it now also reports its rect.

## 4. Verification

`api/test_adr612_judged_gesture.py` (extended). Defends the shared mount, the
rect reporting for both grains and its retraction, the **no-zoom-divide** rule,
the iframe-to-parent mapping, noun/anchor agreement, the collision guard, and
each deletion as an invariant rather than a count.

Falsified against real breaks: the reporter zoom-dividing · the grain no longer
picking the noun · the `meter` prop restored latent · the collision guard
removed.

**A falsifier that PASSED first, and the lesson repeated.** The zoom check
sliced the reporter with `split("}")[0]`, which stops at the first inner brace —
before the rect literal — so a real zoom-divide passed. Slicing to the
function's end fixed it. This is the second time in this arc that a
**slice-scoped assertion asserted the wrong region**; the rule is to bound a
slice by something that actually ends the construct.

Amended, not loosened, in the same pass: ADR-462 (the metered-badge group now
gates the DELETION), ADR-579 D5 (the Ask tier's absence; the ordering claim
became an absence claim), ADR-586 (the flyout count became an invariant — a
pinned count reads a deletion as a violation), ADR-589 D5 (the object rung
routes to the dwell).

Green: 612 · 609 · 589 26/26 · 586 35/35 · 579 17/17 · 606 · 522 · 571 · 562 ·
ratchets; `next build` exit 0. ADR-462's 4 remaining failures are **pre-existing
at HEAD** (arrangement carry + frame labels), measured before and after.

## 5. OWED

The browser click-pass of this half — the Text half's two defects (a spinner
claiming a turn that had not started, and a landing that never fired) were both
found by driving, not by gates.
