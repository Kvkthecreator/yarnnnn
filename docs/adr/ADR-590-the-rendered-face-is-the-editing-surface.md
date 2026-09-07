# ADR-590 — The rendered face is the editing surface

> **Status**: **Accepted** (2026-08-20, operator-ratified: *"yes, aligned in full … would like
> to delegate implementation details as we're aligned"*, on the audit's question *"when the caret
> is inside a rendered table, should the source ever be reachable?"* — answered **no**).

**Date**: 2026-08-20
**Dimension**: Channel (what the member sees and touches on the prose currency) + Mechanism
(decoration → editable widget, without a persisted block model)

**Extends**: ADR-571 (the Text app), ADR-572 D14/D15 (marks hidden always; the `<table>` widget),
ADR-574 (Text leads the prose currency), ADR-575 D8 (the block markers; a divider is an object).
**Preserves**: ADR-456 D1 (the markdown ruling — `.md` is a string, never block-grade),
ADR-406/286 (no CRDT; the revision is the atom), ADR-209 (every mutation attributed).
**Amends**: ADR-572 **D15.b** — *"Putting the caret inside reveals the source rows for editing"*
is **reversed**. That sentence is the defect this ADR closes.

---

## 1. Context — one rule, applied to nine of eleven things

The operator, driving the Text app on a real document:

> *"the rendering is right, but when clicked on its the raw style and i want to edit on the
> render style. this may mean upgrading the render approach itself. think from first principles
> and try to infer what i'm really asking for here (like notion user experience)."*

The screenshot shows a cited CSV table rendered as a proper grid, and the same table as raw
pipes the moment the caret enters it.

Text renders eleven things. Ten are decorations that hide or replace source; one is not rendered
at all. **The reveal rule is not uniform, and nobody decided that it should not be:**

| Rendered thing | On caret entry | Decided by |
|---|---|---|
| `#` heading marks | stays rendered | D14.a |
| `**` `*` `` ` `` `~~` inline marks | stays rendered | D14.a |
| `>` quote mark + the quote bar | stays rendered | D14.a / D9 |
| `-` `1.` list markers → bullets | stays rendered | D8 |
| `[ ]` `[x]` → checkboxes | stays rendered | D8 |
| `---` → divider object | stays rendered | D8.a/D8.c |
| link marks + URL | stays rendered | D14.a |
| **table** | **drops to raw source** | **D15.b** |
| ` ```mermaid ` fence | **never rendered** | — |
| ` ``` ` code fence | **never rendered** | — |

> **A twelfth row, found 2026-09-07 (D5):** `![alt](path)` — **never rendered.** The image door
> shipped one day after D8 (ADR-572 D17) and was gated against the reading face D8 had just
> demoted to thumbnail + print, so this census — written from what the canvas drew — could not
> see it. The line rendered as its alt text, underlined, with the link marks hidden.

ADR-572 D14.a settled this question once, against the Obsidian compromise D13 had shipped:

> *"The operator drove it and rejected it: **'i don't want the hashtags visible.'** On a surface
> being promoted to the primary writing app, a `##` appearing the moment you click into a heading
> is the source leaking through the document, which is exactly the thing the reading face exists
> to stop."*

D15 shipped the table widget five decisions later and did not carry that ruling into it. The
table's reveal-on-caret is not a considered exception to D14.a — it is **D13's reversed rule,
surviving in the one place D14.a did not reach**, because D15 was solving a different problem
(column alignment) and inherited the reveal from the attempt it replaced.

So the operator is not asking for a new behaviour. They are asking for the rule they already
ratified to apply to the two things it skipped.

## 2. What was really being asked (and what markdown can actually carry)

The audit's first-principles read: Notion's property is not *"it renders nicely."* It is that
**there is no source to fall back to** — you edit the rendered thing because the rendered thing
is the document. A table cell is a text field; you click it and type in it.

That is the gap, and it decomposes into two independent claims:

- **The face never breaks.** Rendered stays rendered, caret or no caret. (D1 below.)
- **The face is where you type.** The rendered cell accepts input and writes back. (D2 below.)

The second requires the first — you cannot type into a widget that vanishes when clicked.

**The correction this ADR must record.** `ProseCanvas.tsx` states, in `TableWidget`'s docstring,
that *"nothing maps a cell back to a source position for writing"* — true of the code as written,
but positioned as though ADR-456 D1 required it. **It does not.** D1's words are
*"textarea/CodeMirror-grade, never block-grade"*, and D1 constrains the document **MODEL**: a
persisted tree of identified blocks with stable ids, annotation-on-DOM machinery markdown cannot
carry. It says nothing about rendered appearance or about where keystrokes land.

This is the third time this exact misreading has been caught in this app's history. ADR-572 D13's
own commentary names the first two:

> *"ADR-572 D8 shipped the marks permanently VISIBLE and called it an 'honest limitation',
> claiming that hiding them needs the node↔offset map ADR-456 D1 bans. **That was wrong, and it is
> the same misreading D8 itself corrected.**"*

The test that actually separates a view from a block model is unchanged and is the one every
decoration here already passes: **delete the code and the file is unchanged.** An editable widget
passes it. The widget is built from the source each update, holds no id, is never serialized, and
the document stays the plain `.md` a connector reads and writes back. What an edit does is
`view.dispatch()` a change over a range the decoration *already knows* — the same direction of
travel as every other edit in this app, arriving through a different gesture.

## 3. Decisions

### D1 — Rendered stays rendered; the source is not reachable by caret

**No decoration in the Text canvas reverts to source because the caret entered it.** D14.a's rule
is the app's rule, applied without exception.

Concretely: the `editing` branch of `buildTableDecorations` — which swapped the whole `<table>`
for `cm-tableSource` lines whenever the selection intersected the table's range — is **deleted**,
along with the `cm-tableSource` theme rule it fed. Not flagged, not conditioned: deleted. A second
rendering path for the same construct, reachable by an ordinary gesture, is the dual-approach
shape the discipline forbids, and keeping it "just in case" is how the ambiguity this ADR closes
got here in the first place.

**What this costs, stated plainly.** Between D1 and D2 landing, a table is rendered and not
directly editable — the member edits it through the toolbar's CSV re-insert, or by deleting the
block. **D1 and D2 therefore ship together**; D1 alone is a regression, and this ADR does not
authorize shipping it alone.

### D2 — The cell is the text field

**A rendered table's cells are editable in place, and typing in one writes markdown back to that
cell's source range.**

The mechanism, which needs no new model:

- Each `<td>`/`<th>` carries `contenteditable`, plus its row/column index. The widget already
  holds the table's source (`src`) and the decoration already holds its range `[from, to)`.
- On commit (blur, `Enter`, `Tab`), the cell's text is escaped (`|` → `\|`, newlines stripped —
  a cell is one line by construction in GFM) and spliced into the row, and the **whole table
  range** is replaced via `view.dispatch`. Whole-range because a GFM table's rows are
  interdependent; a per-cell character diff would have to reason about the delimiter row.
- `Tab` / `Shift-Tab` move between cells, `Enter` commits and moves down, `Escape` reverts the
  cell to its source text. These keys are handled **in the widget**, because CodeMirror's keymap
  does not reach inside a widget's DOM.
- The delimiter row (`| --- | --- |`) is **never** editable — it is table machinery, not content.

**The document remains the source of truth.** The widget is still rebuilt from the document on
every update; an edit is not stored in the widget and then flushed, it is dispatched immediately
and comes back as a new render. There is no second copy of the table anywhere, at any instant.

**Undo.** Each committed cell is one transaction, so one `⌘Z` undoes one cell — the grain a member
expects, and the same grain the toolbar edits already have.

### D3 — Fences render; the source is reachable by an affordance, never by the caret

` ```mermaid ` and ` ``` ` fences render **as themselves** — a mermaid fence draws the diagram,
a code fence draws a highlighted block with its language shown. Neither is prose and neither
should read as prose, which is what they do today (the operator's screenshot shows the bare words
`mermaid` and `graph TD` sitting in serif body copy, because the canvas renders no fence at all
and the reading face styles what is left).

**A code fence's content IS its source** — editing the code and editing the source are the same
act, so a code fence is editable in place under D2's rule, with no reveal needed.

**A mermaid diagram is the one genuine exception in this ADR**, and it is an exception to *how*
the source is reached, never to D1: a diagram's source is a different language from its picture,
and no in-place gesture edits a rendered graph. So the diagram carries an **explicit affordance**
(an edit control on the widget) that toggles that block — and only that block — to its source.
**Caret entry still does nothing.** The distinction D1 draws is between an *incidental* gesture
(clicking where you meant to read) and a *declared* one (pressing edit), and only the first is
banned. An affordance the member chose is not the source leaking through.

### D4 — One reveal rule, stated where the code can be held to it

The rule this ADR settles is a property of the *canvas*, not of any one widget, and it has now
been re-derived three times by three decisions. It is stated once, in `ProseCanvas.tsx`'s header,
as the canvas's contract:

> Rendered is rendered. No decoration reverts to source because the caret arrived. Source is
> reached only by an affordance the member pressed, and only where the rendered form cannot carry
> the edit (D3's diagram is the only such case).

New widgets are held to it by gate, not by memory.

### D5 — An image renders as the picture, and a revealed block returns (2026-09-07)

The operator, driving the Text app: *"composition (now just referring) new sub files doesn't seem
to work at the moment."* Reproduced on production through CodeMirror's own input path: a
` ```mermaid ` fence rendered to an SVG, a CSV snapshot under its provenance line rendered as a
real table, and `![laptop](marketing/assets/…png)` rendered as the underlined word *laptop* — real
`<img>` count **0**.

**Why nobody saw it.** ADR-572 D8 (`f392323`, 2026-08-16) collapsed Text to this one canvas and
left `MarkdownRenderer` drawing only the landing thumbnail and Print/PDF. D17 (`8a195db`, the next
day) shipped Insert → Image and gated it with **17g: "the renderer RESOLVES a workspace image
path"** — asserting the component the member no longer types in. `ProseCanvas` had six widget
classes and no image; the lezer `Image` node fell through to the link rule. §1's census above
listed eleven rendered things and had no image row, so the omission was never a decision. Three
weeks under a green gate. *A gate that names a component proves the component, not the surface.*

**Decision — the image is a widget under D1's rule.** `![alt](path)` on its own line (the D17
insert) renders as a figure: the picture, its alt as a caption, and the same edit affordance the
diagram carries. An image inside a sentence renders inline at text height. Pure decoration by the
test every widget here passes — built from the source each update, no id, never serialized; delete
the class and the file is unchanged.

**One resolver, two faces.** The path→URL resolution D17 wrote inside `MarkdownRenderer` moves to
`lib/workspace/imageUrl.ts` and both faces call it. Two copies would be two chances to reproduce
the drift this decision corrects. The reading face's "Image not found: *path*" is the canvas's
too — the path named, never a broken glyph.

**The reveal returns.** D3 shipped `revealFence` and a `collapseFence` effect that nothing
dispatched: a diagram opened for editing stayed as source until reload — the source leaking
through the document, reached by a declared gesture and then never undone. Now opening a block
places the caret inside it, and the caret **leaving** the block folds the source back into its
rendering. One reveal mechanism, one return, both widgets. D4's contract stands unchanged.

**Refused here:** the pin. Markdown has nowhere to keep a revision id (D17's "deliberate loss"),
so a moved image still says "not found" and names the path. **Refused:** resolving `./relative`
paths — D17 cites by workspace path; a relative path fails the same way on both faces, which is
the honest asymmetry-free answer until it is asked for.

**Gate:** `test_adr571_text_app.py` §17g now asserts the ONE resolver is reached by both faces,
and §17h **mounts the canvas** and counts the rendered `<img>` — the surface, not the component.

## 4. Refusals (what this ADR does not open)

- **No block model, no ids, no `data-*` annotations, no serialization.** ADR-456 D1 stands
  entirely. The document is a string; every widget is derived and transient.
- **No database.** Column types, sort, filter, per-cell formatting, merged cells — GFM cannot
  carry any of it, and ADR-456 D2 already refuses databases outright, naming the CSV-citing table
  as the stronger primitive. The table in the operator's screenshot **is** that citation. Cells
  become editable; a table does not become a database.
- **No CRDT** (standing, ADR-406/286).
- **No second parser.** The canvas reads `@lezer/markdown`'s tree, as it does now; the reading
  face and print keep using the workspace's one `MarkdownRenderer` pipeline.
- **Editing a cell of a CITED table is still editing the `.md`, not the cited CSV.** The snapshot
  note above the table says what it is (`From … · snapshot <date>`). Writing back through a
  citation to its source file is a different act with different attribution, and it is not opened
  here.

## 5. Consequences

- The Text canvas has **one** rendering path per construct. `cm-tableSource` — a second path for
  tables, reachable by clicking — is gone, and with it the class of ambiguity where a member sees
  two different faces for one file and cannot tell which is the document.
- Text reaches the Notion property that matters for prose: **the rendered document is the thing
  you type into.**
- The ADR-456 D1 misreading is corrected in canon for the third and, by D4, last time — the rule
  now lives where the code is, not only in an ADR that the next widget's author may not read.

## 6. Gate

`api/test_adr590_rendered_face.py`, plus the D15.b assertions in
`api/test_adr571_text_app.py` that this ADR reverses — recorded as reversed in place rather than
deleted, the convention D15.b itself set for a superseded table behaviour.
