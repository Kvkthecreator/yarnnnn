# Operator packet — ADR-527 click-pass (the emphasis tier)

> **Why this is human-only.** The flow runtime lives in an opaque-origin iframe
> (`sandbox="allow-scripts"`). CDP cannot select text inside it or read the resulting DOM,
> and every claim below is about what happens to a *selection*. Same constraint as
> ADR-521/522/523/525/526.
>
> **Shipped**: `77851c8` (ADR) · `54d6130` (implementation) · this commit (canon).
> **Gates green**: ADR-527 40/40 · ADR-526 35/35 · ADR-525 34/34 · ADR-521 35/35 ·
> ADR-484 19/19 · ADR-519 16/16 · ADR-520 23/23 · `next build` exit 0 / 169 pages.

---

## What changed

A heading selection used to offer three controls. The pane now carries a **Text** section
with the writer's set — read off the Google Slides format bar, control by control. Colour
ships as design-system roles rather than a picker. Align comes back (an over-cut in
ADR-525 that this ADR names and corrects), and indent joins it.

---

## Setup

A Docs artifact with a heading, a few paragraphs, and — for step 7 — a figure or table.
A deck artifact for step 8.

---

## The pass

### 1. The Text section appears — and only for text

Select a few words inside a **paragraph**.

- ✅ **PASS**: the pane shows a **Text** section between Identity and Typography, with
  **B · I · U · S · <> · Clear**, a **Colour** swatch row, and a **Highlight** row.
- ❌ **FAIL**: no Text section, or it appears in the wrong spine position.

Now click a **figure** (or table).

- ✅ **PASS**: **no** Text section (there is no range to emphasise on an object).
- ❌ **FAIL**: it renders.

### 2. Underline and strikethrough

Select a phrase spanning **two paragraphs**. Press **U**, then **S**.

- ✅ **PASS**: both apply across the whole range, in both paragraphs. Pressing again removes.
- ❌ **FAIL**: only the first paragraph changes, or the formatting silently reverts after a
  moment (that reversion is the ADR-521 D3 trap and would mean the segmentation was
  bypassed).

Select a range that includes a **heading and a paragraph**, press **U**.

- ✅ **PASS**: both underline.
- ❌ **FAIL**: the heading loses its weight, or nothing happens.

### 3. Colour and highlight are the system's

Select a phrase. Click the **Accent** dot under Colour, then the **Warning** dot under
Highlight.

- ✅ **PASS**: the text takes the system's accent colour; the highlight is a soft tint of
  the warning colour, not a flat block.
- ❌ **FAIL**: nothing, a wrong colour, or a colour that does not match the design system.

Then click the **slashed (Default)** dot in each row.

- ✅ **PASS**: colour and highlight clear.
- ❌ **FAIL**: they persist, or the text is deleted.

Apply **two different colours in sequence** to the same phrase.

- ✅ **PASS**: it ends in the second colour — not a stack of nested spans.

### 4. Clear keeps structure — the important one

Take a **heading**, make part of it bold and coloured, then select it all and press
**Clear**.

- ✅ **PASS**: the emphasis goes; **it is still a heading** (same size, still in the
  outline).
- ❌ **FAIL**: it becomes body text, or the outline entry disappears. That would mean
  Clear reached structure, which it must never do.

### 5. The pane acts on the selection it can see

Select a phrase, then **click somewhere in the pane's empty space** (not a button), then
press **B** in the Text section.

- ✅ **PASS**: the phrase you selected goes bold — the runtime restored the range.
- ❌ **FAIL**: nothing happens (acceptable-ish), or **the wrong text is formatted** (a real
  defect — report it).

Now click into a paragraph so you have a **caret and no selection**, and press **U**.

- ✅ **PASS**: nothing happens. A caret is not a range, and the pane must never format
  what you cannot see selected.
- ❌ **FAIL**: something formats.

### 6. Align and indent are back

Put the caret in a paragraph. In the pane, find **Align** and pick Center, then Right.

- ✅ **PASS**: the paragraph moves; picking the absent/default value returns it left.
- ❌ **FAIL**: no Align row (it should be there now — ADR-525 had withdrawn it), or it
  does nothing.

Same for **Indent** (1 / 2 / 3).

- ✅ **PASS**: the paragraph steps in from the left; clearing returns it flush.

**Also confirm what should NOT be there**: no Width Hug|Fill, no W/H fields, **no point
size, no line spacing**. Those are refused (§4) and their absence is the design-system
commitment, not a gap.

### 7. Cut/paste keeps the colour

Colour a phrase, select the whole paragraph, ⌘X, click elsewhere, ⌘V.

- ✅ **PASS**: the colour survives the move.
- ❌ **FAIL**: it arrives plain. (This is the ADR-526 D4 seam, extended to the new marks.)

Then paste something **from an outside web page**.

- ✅ **PASS**: it arrives as clean text — no foreign colours, styles or classes.
- ❌ **FAIL**: foreign styling survives. **Report immediately** — the foreign path must be
  untouched.

### 8. Studio is unchanged — the regression half

Open a **deck**. Select a text block.

- ✅ **PASS**: the pane is exactly as before — verb row, Position, Layout with Hug|Fill and
  W/H, Typography, Colour. **No Text section** (it is flow-only).
- ❌ **FAIL**: anything missing or added.

---

## If something fails

Step 4 (clear reaching structure) and step 5 (formatting the wrong text) are the two worth
stopping for. Steps 1–3 failing together points at the pane→runtime channel; step 3 alone
points at the palette roles.

## Recording the result

On a clean pass: `.claude/hooks/mark-validated.sh web` (criteria in
`docs/evaluations/VERIFICATION.md`). Three Docs packets are now outstanding on the same
surface — ADR-525, ADR-526 and this one. Running them in one session is the efficient
path, and this packet's step 8 covers the Studio-regression half for all three.
