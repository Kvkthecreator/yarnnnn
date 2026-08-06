# Operator packet — ADR-526 click-pass (the document shows its shape)

> **Why this is human-only.** The flow runtime lives in an opaque-origin iframe
> (`sandbox="allow-scripts"`). CDP cannot synthesize keys into it or read the resulting
> DOM, so ⌥↑/⌥↓ and the paste behaviour can only be confirmed by a person. Same constraint
> as ADR-521/522/523/525.
>
> **Shipped**: `ce3fdd1` (ADR) · `a609cad` (implementation) · `53ec1c9` (canon).
> Preceded by `a862438`, the ADR-525 follow-up this arc found.
> **Gates green**: ADR-526 35/35 · ADR-525 33/33 · ADR-484 19/19 · ADR-521 35/35 ·
> ADR-519 16/16 · ADR-520 23/23 · `next build` exit 0 / 169 pages.

---

## What changed

Docs could not show you your own document's shape. The system was computing it — the
outline every turn, the enclosing heading on every click — and giving both **only to the
AI**. Now the member sees them, reordering a paragraph has a gesture again, and cutting
and pasting one no longer drops its citations.

---

## Setup

A Docs artifact with **at least three headings** (ideally an h1 and two h2s), some prose
under each, and — for step 6 — one figure or table. A deck artifact for step 7.

---

## The pass

### 1. The outline appears

Open the document and click empty space so **nothing is selected** (the pane shows
document scope). Look at the right-hand pane.

- ✅ **PASS**: an **Outline** section listing your headings in document order, h2s indented
  under h1s.
- ❌ **FAIL**: no Outline section, or headings in the wrong order, or missing ones.

### 2. The outline is a jump

Click a heading row in the outline.

- ✅ **PASS**: the canvas scrolls to that heading and it becomes the selection; the pane
  switches to block scope and shows **Typography** (it is a heading, so the ramp appears).
- ❌ **FAIL**: nothing happens, the wrong block is selected, or the pane shows enclosure
  chrome (a Layout section, a Duplicate/Up/Down/Delete row — see ADR-525).

### 3. The empty state is honest

Open (or make) a document with **no headings at all**.

- ✅ **PASS**: *"No headings yet — add one and it appears here."* Then type a heading and
  confirm it appears in the outline.
- ❌ **FAIL**: the section is missing entirely, or shows invented rows.

### 4. The enclosing heading shows where you are

Put the caret in a **paragraph** somewhere under an h2.

- ✅ **PASS**: the pane's Identity shows **‹that heading› › prose**. Clicking the heading
  part selects the heading.
- ❌ **FAIL**: no crumb, the wrong heading, or a crumb on a document with no headings.

> This is the same fact the AI has been receiving as *"the member is writing under
> 'Pricing'"* since ADR-522 — now shown to you.

### 5. ⌥↑ / ⌥↓ move a paragraph

Put the caret in a paragraph with paragraphs above and below it. Press **⌥↓**, then **⌥↑**.

- ✅ **PASS**: the paragraph swaps places with its neighbour; the caret stays with it; ⌘Z
  undoes it as one step.
- ❌ **FAIL**: nothing moves, the wrong block moves, the caret is lost, **or the block is
  deleted** (that is the fallthrough the gate pins — report it immediately).

Then: **select a range across two paragraphs** and press ⌥↑.

- ✅ **PASS**: yarnnn does nothing — the key belongs to the platform when a range is live.
- ❌ **FAIL**: a block moves.

### 6. Cut/paste keeps citations

Find (or insert) a paragraph containing a **citation** — text carrying a `data-ref`, e.g.
inserted through the citable picker — or a block with a **tone** set. Select it, ⌘X, click
elsewhere, ⌘V.

- ✅ **PASS**: the citation still renders as a live reference (not flattened to plain
  text); a toned block keeps its tone.
- ❌ **FAIL**: the citation becomes plain text, or the tone is lost.

Then the security half — **paste from outside** (copy a paragraph from any web page):

- ✅ **PASS**: it arrives as clean text with formatting but no foreign styling, ids or
  classes.
- ❌ **FAIL**: foreign markup, colours or attributes survive. **Report immediately** — the
  foreign path must be untouched.

### 7. Studio is unchanged — the regression half

Open a **deck**.

- ✅ **PASS**: the navigator filmstrip, the breadcrumb, the pane's path + Contents, the
  verb row with Move up/down, Layout, Position — **all exactly as before**. No Outline
  section (that is flow-only).
- ❌ **FAIL**: anything missing or added.

### 8. The figure fix (from `a862438`, this arc's first finding)

In the **Docs** artifact, select a **figure or table**.

- ✅ **PASS**: the pane shows Duplicate and Delete but **no Move up / Move down** — matching
  the right-click menu, which always refused them on flow.
- ❌ **FAIL**: Move up/down appear in the pane. (Before this arc they did, while the menu
  on the same block refused them.)

---

## If something fails

Note the step and whether the artifact is Docs or a deck. Step 5's delete failure is the
most serious — stop and report it. Steps 1–4 failing together suggests the outline
derivation; step 4 alone suggests the `headingId` plumb.

## Recording the result

On a clean pass: `.claude/hooks/mark-validated.sh web` (criteria in
`docs/evaluations/VERIFICATION.md`). This is also the pass that clears the **web** lane for
ADR-525, whose click-pass is still owed —
`OPERATOR-PACKET-adr525-selection-tier-click-pass.md` — since both touch the same surface;
run that packet's seven steps in the same session if you can.
