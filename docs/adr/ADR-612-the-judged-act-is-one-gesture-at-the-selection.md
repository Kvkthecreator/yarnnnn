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
rect and never to a pointer/hover event, the chip's grain matches the anchor
that ships, and the deterministic toolbar carries no metered verb.

## 6. OWED — the Slides half

Deliberately a separate commit, and the cleanup is the point. Pulling the
judged verbs out of `StudioBlockMenu` collapses the `Move, turn into,
rewrite…` row, and the open question is whether that submenu still earns its
place once the metered act leaves it. That is real deletion and wants its own
scope, not a tail on this one. The reusable piece — the positioned
selection-affordance — lands here so Slides adopts rather than re-invents it.

Also owed: the browser click-pass of this Text half.
