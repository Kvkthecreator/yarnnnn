# ADR-612 — The judged act is ONE gesture, and it lives at the selection

**Status**: Implemented (Text half, 2026-08-26) · Slides half OWED and scoped in §6
**Builds on**: [ADR-609](ADR-609-the-selection-is-an-address.md) (the anchor — this ADR is its entrance) · [ADR-579](ADR-579-three-verbs-that-write-one-act-that-doesnt.md) D7 (the typed seed) · [ADR-522](ADR-522-the-focus-declaration-what-the-member-is-looking-at.md) §7 / lane-frame §6 (the pointer refusal — **amended here, not overturned**)
**Does NOT change**: [ADR-589](ADR-589-update-is-a-door-over-the-selection-matrix.md) — the MECHANICAL door keeps the selection ladder, which is what it was designed for.

---

## 1. The observation

The operator, comparing the two apps in production: *"is it possible to collapse
the slides update with text rewrite concept into one concept … I think the
current rewrite mechanism is closer to the fundamental interaction regardless of
document and app types."*

Driven, the divergence is a depth count. Same intent, two vocabularies:

| App | Path to the judged act |
|---|---|
| **Slides** | `Update` → two-pane door → rail rung (`Artifact › Slide 1 › heading › Heading › Text`) → `Move, turn into, rewrite…` → block menu → `Rewrite…` → chat flips |
| **Text** | select → sparkle → chat, chip loaded |

**Four hops versus one.** And the operator's reading of which is fundamental is
correct for a structural reason worth stating: **the Text path is
grain-agnostic.** "Rewrite what I have selected" needs no ladder because the
selection ALREADY IS the target. The ladder solves a different question —
*which of the nested things am I shaping* — and that question is real for
MECHANICAL acts (palette, tokens, arrangement, turn-into) where the target
genuinely is ambiguous and the act set is determined only once it is known.

So the two doors were never the same door wearing different clothes. One is a
**target-disambiguator**; the other is a **committed act on an unambiguous
target**. Fusing them would have made the judged act inherit a ladder it does
not need — which is exactly why it sits four hops deep today.

## 2. The decision, in one line

**The judged act (the sparkle) leaves the mechanical door and becomes one
selection-triggered affordance, identical in every app. The ADR-589 ladder
keeps the mechanical acts.**

This is not a new boundary — ADR-462 D4's meter badge is already the
mechanical-vs-metered seam. Today that seam is drawn INSIDE a menu; this
promotes it to the surface, where the member can see it.

## 3. Decisions

### D1 — One affordance, anchored to the SELECTION (not the pointer)

The judged act appears when a selection settles, positioned at the selection's
end, and dismisses when the selection clears. It is the same component and the
same words in every app.

**Why the selection and not the cursor** — and this is the ADR-522 §7 /
lane-frame §6 refusal, honoured rather than reopened:

The refusal is about **pointer telemetry as a focus signal** — inferring what
the member cares about from where the cursor sits, and SENDING that to the
model. Two reasons: at send time the pointer is on the composer (degenerate by
construction), and hover does not exist on touch.

**A floating button positioned near the selection is not that.** The pointer
never crosses the wire. What crosses is still the selection the member
deliberately made — the same commitment grain ADR-609 already carries. The
positioning is a RENDERING decision made entirely in the browser.

The distinction is load-bearing and the anchor choice preserves it: a selection
has a rect on touch, where a pointer has no position at all. **Anchoring to the
cursor would have been dead on touch and jittery on mouse — the exact two
failure modes the refusal was written about.** Anchoring to the selection is
immune to both. The refusal section is amended to say so, so a future session
does not read "no mouse-following" and re-refuse this feature.

**Revised after driving it (2026-08-26).** The first cut anchored to the
selection's END POINT. That reads wrong: a multi-line selection ends at the
LAST line's x — often far left and mid-paragraph — so the door landed on the
prose BELOW the selection, covering what the member was reading, and sat inside
the reading column where the eye is. It now hangs in the MARGIN beside the
selection (right, else left), level with the selection's end, falling back to
below-the-end only when there is no margin to hang in. **The selection is
already highlighted; the door does not need to point at it, it needs to not
cover it.**

**Corrected again after the click-pass (2026-08-27) — the rule was right and
its MEASUREMENT was wrong.** The margin test asked whether the door fits between
the selection and the VIEWPORT edge. A viewport is far wider than a reading
column, so that is true almost always — including when the space to the right is
the rest of the member's own sentence. A short MID-LINE selection ("rewrite
these three words", the commonest case) therefore placed the door *inside* the
content every time: driven in production it covered "italic and code." in Text
and the word "thesis" in Slides.

The margin is the space outside the **CONTENT**, so the caller declares it —
`contentLeft`/`contentRight` on the anchor, from the reading column (Text) and
the artifact's own box (Slides). **Absent bounds the door claims NO margin** and
goes below the selection: guessing is how it landed on the prose.

Note this is the SAME defect as the paragraph above, rotated 90°. That fix
corrected the selection's *box*; this one corrects what the box is *compared
against*. Their passing cases overlap on a full-column selection, which is why
the first read as complete. Detail:
[the click-pass finding](../evaluations/2026-08-27-judged-gesture-click-pass-FINDING.md).

### D2 — The chip names the grain, and the chip is the contract

A unified affordance must answer a question the two media answer differently:
in Text a selection is a text RANGE (offsets); in Slides, clicking a heading
selects a BLOCK, and text inside a block could mean either. ADR-541's `scopeOf`
already resolves this (`tier === 'text' ? 'range' : 'object'`) and ADR-609's
anchor carries either — the machinery exists.

What was missing is that the member could not SEE which one was about to be
acted on. **Whatever the chip names is what gets anchored.** Without that the
member thinks they are rewriting three words and the whole block comes back
changed — the ADR-373 D6 incorrect-success shape, one layer up.

### D3 — The header button is DELETED, not kept beside it

ADR-609's Text door shipped as a header-toolbar button. It is removed in the
same commit that adds the floating one. Two entrances to one act, one of them
far from the thing it acts on, is the duplication this codebase keeps paying
for (the six-spellings problem ADR-592 ended; the two `hidden` readers). A
door that is a second entrance to the SAME op is legitimate (ADR-462 D1); a
second SPELLING of the same door is not.

### D4 — `MarkdownToolbar` stays deterministic

The judged verb never joins it. That component is markdown verbs — bold,
heading, list — every one mechanical and free. Putting a metered act in that
row would blur the one boundary the member can currently trust by position.

### D4 — The act says it is working, and cannot get stuck saying so

Clicking Rewrite used to be the end of the visible story on the canvas: the
door vanished, the turn ran unseen, and the document later replaced itself. The
door now STAYS through the turn and reads "Rewriting…", disabled against a
second click. A turn that answers WITHOUT writing — a refusal, a question back,
an error — releases the state on a generous ceiling: it is a stuck-state
release, not a timeout on the turn, because expiring an in-flight turn early
would be the worse lie.

### D5 — When the write lands, the member is put back ON the work

The defect this closes is the one the operator named: *"the loading to refresh
is confusing because once the document is updated we should show clearly exact
location where we were working."* The lane's write triggered a full refetch, the
document silently replaced itself, and the member had to hunt for what changed.

The canvas already preserved the caret across an external write — by holding
its offset from the END of the document. That heuristic is **exactly wrong for
a rewrite that lands in the middle**: text above the caret shifts, so the
anchor drifts by the length delta.

So the landing re-finds the passage **by CONTENT, not by offset**: the
rewritten passage is a different length, so the old span no longer describes
it. The unchanged prefix pins the new start, the unchanged suffix pins the end,
and the range is selected and scrolled to the viewport's centre. It fires when
the reloaded text REACHES the canvas (a frame after the effect), not when the
write is announced — at announce time the document has not arrived yet.

Both ends are best-effort by construction. A rewrite that also restructured its
surroundings simply lands on the whole changed region — still the right
neighbourhood, and never a wrong claim about where the member's passage went.

## 4. Refused, and recorded

- **Merging Update and Rewrite into one door.** §1's structural reason: they
  answer different questions. The judged act would inherit a ladder it does not
  need.
- **Following the mouse cursor.** Not because it is telemetry (it is not, per
  D1) but because it is WORSE: dead on touch, jittery on mouse.
- **A hover-triggered affordance.** Hover is transit, not commitment — the
  original refusal's words, and they still hold at the render layer.

## 5. Verification

`api/test_adr612_judged_gesture.py`. Defends: one gesture producer in Text (the
header button is GONE, not duplicated), the affordance anchors to the selection
RECT and never to a pointer/hover event, the margin preference over covering
prose, the chip's grain matching the anchor that ships, the deterministic
toolbar carrying no metered verb, the pending state and its stuck-state
release, and the landing (by content, fired when the text arrives).

Falsified against real breaks: the header button restored · pointer tracking
re-entering the affordance · the anchor drifting off the selection · the label
diverging from the chip's noun · a metered verb in the deterministic toolbar ·
the margin preference removed · the landing firing before the document arrives ·
the stuck-state release removed.

The landing algorithm is separately driven over 10 cases — shorter/longer
middle rewrites, at-start, at-end, multi-paragraph, repeated surrounding text
(the ambiguity trap), and four degenerate ones (full restructure, an overreach
that changed more than asked, no change at all, an emptied document). None
produce an inverted or wrong span; the overreach case correctly lands on the
whole changed region, which is the honest answer.

## 6. OWED — the Slides half (DONE: [ADR-613](ADR-613-the-judged-act-leaves-the-menus.md), 2026-08-26)

Deliberately a separate commit, and the cleanup is the point. Pulling the
judged verbs out of `StudioBlockMenu` collapses the `Move, turn into,
rewrite…` row, and the open question is whether that submenu still earns its
place once the metered act leaves it. That is real deletion and wants its own
scope, not a tail on this one. The reusable piece — the positioned
selection-affordance — lands here so Slides adopts rather than re-invents it.

Also owed: the browser click-pass of this Text half. **DONE 2026-08-27** — it
confirmed D4 (the door claims no turn until Send) and D5 (the write lands only
on the selection) live, and found the D1 margin defect corrected above.
