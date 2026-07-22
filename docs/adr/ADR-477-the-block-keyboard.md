# ADR-477 — The block keyboard: an empty block closes, a selected block acts

> **Status**: **Implemented** 2026-07-21. Ratified by KVK; shipped `da450c0` (the block keyboard). Gate 13/13.
> **Decides**: Backspace on an emptied block removes it; the verb-key guard is
> re-cut from "is anything editing" to "does the caret have a CLAIM on this
> key"; the mode-native keyboard grammar is named, and its unbuilt half is
> named as unbuilt.
> **Amends**: ADR-462 D10 (the guard it shipped was correct under an invariant
> ADR-466 P11 later removed) · ADR-466 P11 (names the fallout it left).
> **Preserves**: ADR-443 R1 (the DOM is the model) · ADR-462 D1 (a key composes
> an existing verb, never a new op) · ADR-462 falsifiers 11 + 12 · ADR-466 D1
> (three native editors over one grammar) · ADR-461 D4 (a page has a viewport —
> no spatial keys on flow layouts).
> **⚠️ SCOPED BY [ADR-480](ADR-480-the-editing-grain-a-document-is-one-writing-surface.md)
> (2026-07-22)**: §1a's rule — *an empty block closes itself* — becomes **`paged`-only**.
> It is not deleted; it is scoped to where blocks are still ENCLOSURES (deck · page ·
> canvas), and there it stands exactly as shipped. On `flow` layouts (document · article)
> `contenteditable` moves to the document root, so the browser owns emptying, merging and
> splitting natively — the gap this ADR patched cannot occur there, because its cause
> ("`contenteditable` has no concept of the block") no longer applies when the editable
> field *is* the document. §1b (the verb-key guard asking whether the CARET has a claim)
> is untouched and still governs both modes.

---

## 1. The finding

Two defects, reported by the operator in one sentence: *"when I click delete on
a text, the block (empty) remains; if I select a block and press delete it
doesn't work."* They look like one bug. They are two, with different causes,
and the second is the more interesting.

### 1a. An emptied block survived its own emptying

The caret-Backspace handler is a **merge**: it carries this block's content
into the previous one. It is gated on finding a previous **TEXT-kind** block
(`adjacentTextBlock('up')`), and falls through to native otherwise.

Native `contenteditable` has no concept of a block. So when the merge declined,
Backspace deleted characters until there were none and then did nothing at all
— leaving an empty block wearing a selection box. There was **no rule anywhere
that an empty block closes**. The gap was invisible while every block had a
text predecessor; it surfaced at the top of a document and after any
figure/table/divider.

The worst variant was not "nothing happens." An empty block alone in a deck
slot *did* merge optimistically in-frame, but the parent op refused on the
cross-parent guard — so no revision landed and **the block reappeared on the
next reload**. Vanished, then came back.

### 1b. The verb keys were dead — a guard that outlived its invariant

`Delete` on a selected block was wired end to end and correct: the runtime
posts `yarnnn-key-verb`, the canvas forwards it, the surface runs the same
`deleteBlock` the menu row runs. ADR-462 D10 shipped it precisely so the menu
would stop advertising keys nothing listened for.

It was killed by its own guard:

```js
if (window.__yarnnnEditingId && window.__yarnnnEditingId() != null) return null;
```

**That guard was correct when it was written.** SELECTED and EDITING were
mutually exclusive states; "something is editing" therefore meant "the member
is not on the object layer."

**ADR-466 P10/P11 removed that exclusivity** — deliberately, and rightly. P11
made the selection box *persist through editing* (border dashed, all eight
handles live) because the operator observed that PowerPoint keeps its handles
up while you type. P10's staged click ladder enters text on a block that stays
selected. After P11, a block routinely looks selected — box drawn, handles up —
while `editingId` is non-null.

So the guard kept returning `null`, and **every verb key silently did nothing**.
Delete worked only if the member first pressed `Esc`, which nothing advertises.

This is the same failure mode P11 itself diagnosed in P8's hidden-box rule, in
the same words: *it outlived its cause*. A ratified change moved an invariant;
a guard written against the old invariant became a dead end without a single
line of it changing.

---

## 2. Decision

### D1 — An empty block closes itself

Backspace at the start of an **empty** block is a *delete*, not a merge. There
is nothing to carry, so the merge path's previous-TEXT-block requirement does
not apply and must not be reached.

- **Emptiness is judged on text**, and a block holding a citation island or an
  image is never empty — a `data-ref` is content the member did not type.
- **The member stays located.** The caret moves to the end of the previous
  block when that block can hold one; a non-text predecessor (figure, divider)
  takes the **selection** instead. Landing on the object layer in front of an
  object is honest; landing nowhere is not.
- **The sole or first block falls through to native.** With nothing to fall
  back to, removing it would leave the member in an empty document with no
  caret.
- **The detach is silent.** A commit here would re-assert the block and race
  the delete on one head — the one-gesture-two-ops trap the merge path already
  documents.
- **It posts the existing verb.** No second delete implementation enters the
  runtime (ADR-462 D1).

### D2 — The guard's seam is the caret's CLAIM, not edit-mode

The question a verb key must ask is not *"is anything editing?"* but **"does
the caret own this key right now?"**

The caret owns it when it is live **in this block** and there is **text for the
key to act on**. Both clauses are load-bearing:

- *in this block* — after P11 the member can have a caret in one block while
  another is the selection's subject. The subject wins.
- *has text* — an empty block gives the caret nothing to bite on; D1 owns that
  case.

**Text keys are stricter.** `⌘C`/`⌘V` return to the editor whenever a caret
exists at all, empty block or not: `⌘V` in an empty block means *paste text
here*, never *paste a block after this one*. The pre-existing rule that `⌘C`
over a highlighted phrase copies the phrase is preserved and generalized.

### D3 — The mode-native grammar is named; its unbuilt half is named as unbuilt

There was **no keyboard canon before this ADR** — ADR-462 D10 is a bug-fix
record for four keys, not a grammar; STUDIO.md has no shortcut table. The
grammar below follows ADR-466 D1's three native editors. It is **named here and
shipped incrementally**, because of falsifier 11.

**Universal**

| Key | Act | State |
|---|---|---|
| `⌫` / `Delete` | remove the selected block | **shipped** (D1 + D2) |
| `⌘C` / `⌘V` / `⌘D` | copy / paste-after / duplicate | **shipped** (ADR-462 D10) |
| `Esc` | caret → block-select → deselect | caret lift shipped; **deselect owed** |
| `Enter` | selected → edit | owed |
| `↑` / `↓` | move selection between blocks | owed |
| `Tab` / `⇧Tab` | cycle | owed |

**Deck / canvas (object-first)** — arrows nudge position, `⇧arrows` coarse,
`⌥arrows` resize, `⌘]`/`⌘[` z-order (the `nudgeZ` verbs already exist), `Tab`
cycles objects within the slide. All are position acts, so all are confined to
`block-staged` — ADR-466 D2's scope guard stands.

**Flow (document / article, caret-first)** — Notion semantics unchanged. Add
`⌘B`/`⌘I` (today mouse-only via the format bar) and `Tab` indent/outdent in
lists. **No positional keys**: ADR-461 D4's refusal of spatial freedom on flow
layouts is not relaxed by a keyboard.

**Page (band-first)** — `↑`/`↓` between bands, `⌘⇧↑`/`⌘⇧↓` to reorder. No
positional keys, same reason.

### D4 — `⌘Z` is not advertised until History exists

Undo is fully ratified as mechanism (ADR-453 D7: revert-as-write over ADR-209
D7) and **unbuilt as affordance**. Binding `⌘Z` before the History panel ships
would reproduce the exact defect ADR-462 D10 was written to fix — *"shortcut
labels are a promise; these were decoration."*

Deletion is safe without it: every delete is one attributed revision, the prior
content stays on the chain, and revert-as-write is the recovery path. There is
no destructive delete to protect against — only an unbuilt convenience.

---

## 3. Why the keyboard lives in the runtime

Not a preference. The canvas is a **sandboxed iframe**, so keys land in its
document or nowhere; the parent has no global keyboard and cannot have one.
Every key therefore composes an existing verb and posts it out — the same shape
as every other gesture (ADR-462 D1).

This also means new capture-phase handlers must be positioned deliberately in
the existing chain. The slash palette already relies on
`stopImmediatePropagation` to beat the Enter-split handler registered on the
same node in the same phase.

---

## 4. Falsifiers

1. Backspace on an emptied block removes it — at the top of a document, and
   after a figure, table, or divider.
2. No block is ever optimistically removed in-frame and resurrected by a
   reload.
3. A block holding only a citation or an image is never treated as empty.
4. `Delete` acts on a selected block whose box is up, **including while its
   border is dashed** (the P11 editing overlap).
5. `⌘V` with a live caret inserts text, never a block.
6. Every shortcut the context menu renders has a handler (ADR-462 falsifier 11,
   re-asserted by this gate against the menu's actual rendered rows).
7. A verb key and its menu row run the same function (ADR-462 falsifier 12).
8. No `⌘Z` is advertised anywhere while History is unbuilt.

Gate: `api/test_adr477_block_keyboard.py` (13 checks). Verified by **removing
each fix and confirming the gate goes red** — D2's revert drops it to 12/13,
D1's to 9/13.

---

## 5. What this ADR does not do

- It does not revisit the block model. ADR-466 P12's reaffirmation stands:
  blocks are the attribution grain and the `trace` join key.
- It does not ship the owed half of D3's grammar. Each row lands with its
  handler, or it is not advertised.
- It does not build Undo/History. D4 names why.
- It leaves ADR-462 D8's inspector question open.

---

## 6. One line

**A guard that asks "is anything editing" answers the wrong question once the
box can persist through editing; the right question is whether the caret has a
claim on this particular key — and an emptied block should close itself, because
nothing else in the stack knows what a block is.**
