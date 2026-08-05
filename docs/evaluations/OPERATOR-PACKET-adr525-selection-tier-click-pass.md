# Operator packet — ADR-525 click-pass (the selection's tier)

> **Why this is human-only.** The flow runtime lives in an opaque-origin iframe
> (`sandbox="allow-scripts"`, no same-origin). CDP cannot reach into it to synthesize
> clicks or read the resulting DOM, so every claim below is about what the *member* sees
> and must be confirmed by a person. This is the same constraint ADR-521 found and ADR-522
> and ADR-523 re-confirmed.
>
> **Shipped**: `adde347` (ADR) · `ad1abbd` (implementation) · `bc00be3` (canon).
> **Gates already green**: ADR-525 29/29 · ADR-484 19/19 (chokepoint + completeness) ·
> ADR-521 35/35 · ADR-519 16/16 · ADR-520 23/23 · `next build` exit 0 / 169 pages.
> The gates prove the *derivation* and the *composition*. They cannot prove what renders.

---

## What changed, in one line

A block in Docs and a block in Studio were the same shape in code. Now the runtime declares
which kind of thing the selection is (`text` / `object` / `structure`) and the pane, the
right-click menu and the keyboard all read that one field instead of each guessing.

---

## Setup

Any Docs artifact with prose, at least one heading, and — for step 4 — one figure or table.
The operator's own reproducer works: `/desktop?docs.file=operation/hello/document-copy.html`

A deck artifact for the regression half (step 6).

---

## The pass

### 1. The box is gone from prose — the originating report

Click into a **heading** in the flowing document.

- ✅ **PASS**: a caret appears. **No black outline** around the line.
- ❌ **FAIL**: an outline is drawn around the heading (the ADR-484 symptom, the exact thing
  reported on 2026-08-05).

Repeat on an ordinary **paragraph**, a **quote**, and a **checklist** item. Same expectation.

### 2. The pane stops answering enclosure questions

With the caret still in that heading, read the right-hand Design pane top to bottom.

- ✅ **PASS**: **File → ‹heading› → Typography → Tone → Turn into**.
  - **No** `Duplicate · Up · Down · Delete` row.
  - **No** `LAYOUT` section — no `WIDTH: Auto | Hug | Fill`, no `ALIGN: Auto | Center | Right`.
- ❌ **FAIL**: any of the above appear.

> This is the one to look at hardest — it is ADR-521 D1's *"no layout surface"* finally
> being true at the surface rather than only in the doc.

### 3. The pane and the menu now agree

Right-click the same heading.

- ✅ **PASS**: **no Duplicate, no Delete**, no Move up/down. Turn into IS present. The AI
  rows (Rewrite / Check / Ask) are present.
- ❌ **FAIL**: Duplicate or Delete appear.

> Before this ADR the pane offered Move up/down here while this menu refused it — one op,
> two contradictory answers, on one block. Both now read the same declared field, so the
> check is really *"do these two surfaces still disagree about anything?"*

### 4. Objects on flow are UNCHANGED — the half that must not regress

Click a **figure** (or table / chart) in the same document.

- ✅ **PASS**: a neutral outline IS drawn; the pane DOES show the verb row and the Layout
  section (Width / Align are legitimate here — a figure is a box).
- ❌ **FAIL**: the figure draws no box, or its verbs/Layout went missing.

> If step 1 passed and step 4 failed, the tier is collapsing everything on flow to `text`.

### 5. The selection is still REAL — only the enclosure chrome went

With the caret in a paragraph, confirm the pane's Identity row still names the block and
**Turn into** still converts it (try turning a paragraph into a callout, then undo with ⌘Z).

- ✅ **PASS**: the conversion lands; the block was addressable the whole time.
- ❌ **FAIL**: Turn into is missing or does nothing.

> ADR-525 withdrew the enclosure *affordances*, never the selection (ADR-480: the block
> stays addressable). This step is the guard against over-cutting.

### 6. Studio is byte-identical — the regression half

Open a **deck**. Click any block, including a text block.

- ✅ **PASS**: the bounding box, the eight handles, the move band, the verb row, Position
  (X/Y), Layout (W/H, Width, Align) — **all exactly as before**.
- ❌ **FAIL**: anything is missing.

> On a paged medium every block is an enclosure (ADR-480 D1) and prose is no exception.
> ADR-525 changed nothing here; if it did, the medium term is inverted.

### 7. The route that caused the regression

This is the specific path that re-opened the defect on 2026-08-04 (`678f579`), so it is
worth exercising directly.

In Docs, click a paragraph, then press **Esc**. Then click a paragraph and use the pane's
Contents/path row to select a different block.

- ✅ **PASS**: no box appears on prose at any point.
- ❌ **FAIL**: a box appears after Esc, or after a pane-driven selection.

> These reach `__yarnnnSelect` rather than the click handler. Before D2 they were
> unguarded, which is how a gate at 14/14 coexisted with the operator's report.

---

## If something fails

Note **which step**, and whether the artifact is Docs or a deck. The most diagnostic pair
is (1, 4): both passing means the tier is being derived correctly; step 1 failing alone
points at the chokepoint; step 4 failing alone points at the kind list.

## Recording the result

On a clean pass, mark the lane validated:
`.claude/hooks/mark-validated.sh web` — criteria in `docs/evaluations/VERIFICATION.md`.

This pass also **subsumes ADR-484 §6's owed click-pass** (*"a human click-pass confirming
prose no longer outlines and objects still do"*), which was never run — the reason the
regression went unseen for a day.
