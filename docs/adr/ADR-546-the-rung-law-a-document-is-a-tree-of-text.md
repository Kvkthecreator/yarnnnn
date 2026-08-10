# ADR-546: The rung law — a document is a tree of text, and the law forks from Studio's

> **Status**: **Proposed** (2026-08-10) — drafted from the operator's Docs audit
> directive and the two reframings taken during it (§2.1, §2.2). The audit that
> produced §1 is receipted in full; **no code has landed**.
> **Date**: 2026-08-10
> **Dimension**: **Substrate** (what a document's structure IS) primary, with
> **Channel** consequences (what Tab means, what a span's subjects are, what the
> chrome may say) that are the reason the substrate claim is worth making.
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**:
> - **ADR-544** (the containment law) — the **peer**, not the parent. This ADR is
>   what ADR-544 is for the paged media, done for flow, and it deliberately
>   imports none of ADR-544's answers (§2.3).
> - **ADR-526 D1** (a document's structure is the heading tree, derived and never
>   authored; no `<section>` wrapper) — **extended, not re-cut**. D1 named the
>   heading as the structural grain; this ADR names the *general* fact the heading
>   is one instance of (§D1), and upholds the `<section>` refusal (§4.2).
> - **ADR-528 rule 14** (a range is not a block; the flow scope set is
>   `document | range | object`) — **upheld and completed**: D3 gives the range
>   the rung-awareness its subject derivation lacked.
> - **ADR-539 D3/D4/D5** (`HEADING_RUNGS` is ONE kernel constant) — **generalized**.
>   The constant is right; it was one of three rung systems and the only one with
>   readers.
> - **ADR-521 D4** (Tab indents in a list) — **amended**. The gesture is right;
>   what it writes is not addressable (§1.3).
> - **ADR-536 D1/D2** (`list` is a kind; align + indent come home) — extended.
>   `list` became a kind; its *interior* stayed unnamed.
> - **ADR-518 D2** (the split is HOUSING; no forked machinery per app) — **upheld,
>   and the reason this is a fork of the LAW and not of the code** (§2.3).
> - **ADR-511 D3** (the selection floor is the attribution floor) — the floor is
>   confirmed per-medium rather than global (§D2).
> - **ADR-254** (file-format discipline) — unchanged; no new file, no new format.

---

## 1. Context — three rung systems, one gesture, no shared law

The 2026-08-10 audit drove the Docs canon against the Docs implementation, at the
operator's direction, looking for a Docs analogue of the ADR-544 fault. **The
analogue exists and it is the inverse.** ADR-544 found two substrate concepts
wearing one word. Docs has one concept — *depth* — wearing **three unrelated
spellings**, one of which nothing can address.

All findings below were made against a **22/22 green FE gate battery**. Four
arcs for four, this layer's defects are invisible to gates.

### 1.1 Depth is spelled three ways, all shipped, all depth-3

| system | spelling | declared where | who reads it |
|---|---|---|---|
| **heading** | `h1`/`h2`/`h3` | `HEADING_RUNGS = (1,2,3)`, `authoring.py:352` | outline, crumb, ramp, turn-into, AI posture, intake clamp |
| **indent** | `data-indent="1..3"` | a served token, `grains: ("flow",)`, `authoring.py` | the pane's one Text-section row |
| **list nesting** | `ul ul ul` / `ol ol ol` | kernel CSS, `authoring.py:1345-1348` | **nobody** |

The cardinality is the tell: all three are **three deep**. `authoring.py:1488-1490`
declares `[data-indent="1"]`→`2rem`, `"2"`→`4rem`, `"3"`→`6rem`; the list CSS
nests `disc → circle → square` and `decimal → lower-alpha → lower-roman`. Three
independent declarations of the same idea, at the same depth, that have never
been named as one.

### 1.2 The third has no reader at all

`normalizeStructure` (`artifactOps.ts:348-441`) is the identity floor. Its
subject set is `'[data-block], [data-block-id]'`, plus divs holding blocks, plus
pages. **`LI` appears in no pass.** So a nested list item carries no
`data-block-id`, is not a selection subject, has no label, no tier, cannot be a
range subject, and is invisible to `walkOutline` and `walkContents`.

Meanwhile the kernel renders it three levels deep. **The member authors, with
Tab, a hierarchy the surface has no word for and no way to select.**

### 1.3 One gesture, two meanings, arbitrated by tag

`projection.ts:2100-2114`:

```js
root.addEventListener('keydown', function (e) {
  if (e.key !== 'Tab') return;
  e.preventDefault();
  var li = el && el.closest ? el.closest('li') : null;
  if (li && root.contains(li)) {
    document.execCommand(e.shiftKey ? 'outdent' : 'indent');
    return;
  }
  if (e.shiftKey) return;
  if (document.queryCommandSupported && document.queryCommandSupported('insertText')) {
    document.execCommand('insertText', false, String.fromCharCode(9));
  }
});
```

Tab is *the* rung gesture, and it means two unrelated things:

- **in an `<li>`** → `execCommand('indent')`, writing `ul ul` that nothing can address;
- **in prose** → a literal tab **character**, which is not structure at all,

while `data-indent` — the one *addressable* prose rung, served, three-valued —
has **no keyboard entrance whatsoever** and is reachable only by clicking a pane
row. The member's most natural depth gesture reaches the unaddressable spelling
in a list and the wrong thing entirely in prose.

### 1.4 A span's subjects are flat, so the rung relation is discarded

`formatSegments` (`projection.ts:2233-2267`) is the one derivation of "what does
this range act on." It is flat by construction:

```js
// Top-level blocks only — a nested annotated element rides its parent's
// segment; citation islands are never format subjects (ADR-446 D3).
if (b.parentElement && b.parentElement.closest('[data-block]')) continue;
```

A range covering a heading and the six paragraphs beneath it yields **seven peer
subjects**. The fact that six of them are *subordinate to* the first — which the
document states structurally, and which `walkOutline` already computes — is
discarded at the one place a span's subjects are derived. This is why
"select multiple blocks" has no good answer today: the selection knows a count,
never a shape.

### 1.5 Why these are one fault

Each is the same shape, and it is ADR-544 §1.4's shape read in a mirror: **a
model coherent one layer above where the member's finger lands.** §1.1 makes
depth unstateable (three names for it), §1.2 makes one spelling unaddressable,
§1.3 makes the gesture ambiguous, §1.4 makes a multi-block selection shapeless.
Fixing any one alone leaves the others producing the same confusion through a
different door.

### 1.6 The vocabulary already leaks Studio's words

Separately from the rung fault, and load-bearing for §D5:

- `structureLabels.ts:99-102` — `if (tag === 'SECTION') return 'Slide'` and a
  terminal `return 'Group'`. `labelFor` is called from the **ungated** flow click
  handler (`projection.ts:828`), the Esc-walk (`:1080`) and the edit-runtime Esc
  path. `Group` is a word ADR-544 D7 spent a commit removing from the deck crumb.
- `StudioDesignTab.tsx:2512-2513` — the pane header falls back to
  `selection?.blockKind`, the raw attribute ADR-544 D4 closed for decks.
- `projection.ts:824, 831, 1071, 1083, 3352, 3369` — the flow selection payload
  carries `slot` and `arrange`, computed by `closest('[data-area], [data-slot]')`
  and `closest('[data-arrange]')` — **grains flow's own projection deletes one
  pass earlier** (`:4543-4557`). Post-544 that `slot` key reads `data-area`
  first, so **ADR-544's Area grain is now named in flow's selection payload.**

**ADR-544 F2 forbids `slot`/`col`/`cols`/`container` "for deck structure."
Nothing forbids a deck word on flow.** The falsifier is one-directional, which
is the whole reason this ADR exists as a law and not as a patch.

---

## 2. The two reframings that decide this ADR

### 2.1 A core format interprets the rungs for itself (the operator's)

> *"my understanding was that any core format, meaning, especially with text now,
> it needs to potentially have its own interpretation of the rungs."*

This dissolves the question the audit had asked. The audit asked *"is `<li>`
addressable — yes or no?"*, as though there were one global addressing floor.
There is not, and the system already knows it: `tier` is per-medium (ADR-525),
the block roster is `app`-scoped (ADR-528 D5), the mode gates the grain
(ADR-482 D3). **The floor is a per-medium interpretation, and depth is the fact
each medium interprets.**

- On **paged**, depth is *containment*: which Area holds this block (ADR-544).
- On **flow**, depth is *the rung*: how subordinate is this text to the text
  before it.

And on flow, `h1/h2/h3` and list nesting are **the same kind of statement** —
"this is subordinate to that" — differing only in spelling. That is why §1.1's
three systems all landed on depth 3 independently: they are one concept.

### 2.2 The nesting and multi-select questions are the same question

They resolve together, and neither resolves alone:

- **Nesting** is not "should `<li>` be selectable?" It is *"is list depth a rung?"*
  If yes, it needs no new grain — it needs the rung law to admit its spelling.
- **Multi-select** on flow is not "N subjects." A range covering a heading and
  its body is **one span at a rung** — a subtree. `formatSegments` discards
  exactly the relation that would make it describable.

One law about depth answers both. This is why they are one ADR.

### 2.3 Why the LAW forks and the MACHINERY does not

The operator raised a hard fork of the Docs app. **Refused, with the measurement
stated**, because the two questions come apart:

*Are the models different?* Yes — more so after ADR-544 than before.
*Is the machinery shared?* Also yes, and the sharing is load-bearing: one write
door (ADR-518 D2 names a second as **the** refused shape), one normalize seam,
one registry, one `HEADING_RUNGS`, one `tokenGrammar.admits`, one
`selection.ts` algebra (ADR-541 D2 built it *specifically* so surfaces cannot
disagree), one undo lineage, one paste allowlist.

The decisive evidence is §1 itself. **Not one of the seven findings is "shared
machinery forced Docs into a Studio shape."** Every one is the opposite — shared
machinery that **failed to branch** (§1.6's ungated ladder), or a Studio-scoped
fix written one-directionally (§1.6's payload, the one-directional F2). A fork
fixes none of them and **duplicates** all of them: two label ladders (one pair
already kept in step by a comment, the `d8c528b` defect), two tier derivations,
two normalize seams. ADR-544's own headline rule is *move the derivation, never
add a second*; a fork is the largest available "add a second."

`AUTHORING.md:9-20` already records this refusal for the doc, with numbers:
Docs-specific content is ~16% of the file, and ~44% of the `document` column is
`—`/`🚫` cells **that carry meaning only by contrast** — a cell reading "flow has
no containers by derivation" is a statement *about the difference*, and a fork
leaves it nowhere to live. Rule 11 is the recorded incident of one contract
derived in two places.

**So: the law forks (this ADR, symmetric gates, Docs' own four grains); the
machinery stays one implementation with N consumers.** What the operator
correctly felt was not shared code — it was ADR-544's law being gated in one
direction only.

### 2.4 The word "rung", and what was refused

**"Rung" is adopted** because the system already uses it for exactly this
(`HEADING_RUNGS`, `heading_rungs`, `DEEPEST_RUNG`, "the deepest declared rung"),
and generalizing a word already in the code beats minting one.

Refused, each for a receipt:

- **"Level"** — unmarked and already overloaded (heading level, indent level,
  nesting level are the three things being unified; using the word for the union
  would leave the parts unnameable).
- **"Section"** — a standing refusal (ADR-526 D1, upheld by ADR-544 §2.1). A
  section is the *span* a rung opens, and remains so (§D1).
- **"Outline"** — that is the *projection* of the rung tree (`walkOutline`), not
  the tree. Naming both one thing repeats §1.1's fault.
- **"Depth"** — kept as the *quantity* a rung carries, not as the grain's name.

---

## 3. Decisions

### D0 — The four grains of a document, named once

```
Document   the file — one continuous writing surface, one measure   (no coordinate space)
  Rung     a step of subordination: h1/h2/h3, or a nesting step     (the structural grain)
    Block  a paragraph, list, quote, table, figure                  (the addressing floor)
      Range  what the member has selected: a span across blocks     (the selection unit)
```

Every operator-facing surface — pane header, crumb, outline, menus, and the
LLM-facing grammar — uses these four words and no others for document structure.
**`Slide`, `Layout`, `Area`, `slot`, `col`, `cols`, `container`, `page` and every
raw `data-block` value never appear in operator-facing text on flow** (D5).

Note what is *absent by derivation*, and say so rather than leaving it to look
accidental: **there is no container grain and no page grain on a document.**
`docs.py:69` states the reason and this ADR promotes it to law — *"a capture
surface that asks 'where on the page' has stopped being a capture surface."*
The Docs analogue of an Area is **nothing**, deliberately.

### D1 — A rung is one concept with two spellings, and the set is ONE constant

Subordination on flow is **one fact**. It is spelled two ways, both legal:

- **the heading rung** — `h1`/`h2`/`h3`, subordinating everything until the next
  heading of equal-or-shallower rung (ADR-526 D1's span, unchanged);
- **the nesting rung** — a list item's depth within its list.

`HEADING_RUNGS = (1,2,3)` generalizes to **`FLOW_RUNGS`, the one declared depth
set for the document medium**, and both spellings clamp to it. The
already-matching cardinality of §1.1 makes this a naming of what is, not a new
bound: intake clamps `h4`–`h6` to `h3` today (ADR-539 D4), and nesting deeper
than three clamps the same way, migration-by-use, never a sweep.

**`data-indent` is absorbed, not preserved beside them.** It is a third spelling
of the same fact with no distinct meaning — a *presentational* left-margin whose
values are exactly `1|2|3`. It becomes the **rendering** of a prose rung, not a
token the member sets independently. One concept, one control.

### D2 — The addressing floor is per-medium, and on flow it stays the BLOCK

An `<li>` **does not become a block, and does not carry `data-block-id`.**
`normalizeStructure` is unchanged; ADR-511 D3's floor holds, interpreted for this
medium per §2.1.

A rung is therefore **a property of a block, not a grain that holds blocks.** A
list is one block; its interior depth is a rung the block carries, the same way a
heading's level is. This is the Google Docs contract (a list item is not a
separately selectable object) and it costs nothing the audit found a member
wanting.

**What changes is that the rung becomes READABLE.** Today list depth is
`ul ul` and nothing can see it; under D2 a block's rung is a derived, addressable
*fact about that block* — available to the outline, the crumb, the pane, the
range algebra and the lane, with no new identity and no new node.

> **The refusal this preserves**: a nested-item grain would be the Notion model,
> and it would move the attribution floor — which ADR-528 §2 measured as
> whole-FILE. That is a separate and much larger bet. Named here so its absence
> is a decision; §5 carries the evidence that would reopen it.

### D3 — A range's subjects carry their rung; a span is a SHAPE, not a count

`formatSegments` (§1.4) keeps its flat block list — text-tier ops legitimately
act per-block — but the **range's reported subjects gain their rung**, so every
consumer can see the shape instead of a count.

Consequences:

- **`rangeBlockIds` is not the whole answer.** The span reports its blocks *and*
  their rungs, so a surface can say *"Pricing and the 6 blocks under it"* instead
  of *"7 blocks selected"* (`StudioDesignTab.tsx:2512`).
- **A heading-led span is a subtree**, and that is the honest description of the
  commonest multi-block selection a document produces.
- **The derivation home is `selection.ts`** (ADR-541 D2 — the one home), never a
  second walk in the pane or the runtime.

This completes ADR-528 rule 14 rather than amending it: a range is still not a
block, and now it is not a shapeless bag either.

### D4 — Tab is the rung gesture, and it means ONE thing

Tab / ⇧Tab **step the rung**, everywhere in a document:

- **in a list** — nest / un-nest (ADR-521 D4's behavior, retained, now writing an
  addressable rung per D2);
- **in prose** — step the prose rung (what `data-indent` did without a keyboard
  entrance), clamped to `FLOW_RUNGS`.

**The literal-tab-character branch is DELETED.** It is not structure, it was
reachable only in prose, and it is the one branch that made the system's most
natural depth gesture mean something other than depth. A member who wants
whitespace has the measure and the rung; a literal tab in a continuous document
is a typewriter artifact.

`Tab never ends the writing session` (ADR-521 D4) is unchanged and remains the
reason the handler exists at all.

### D5 — The chrome says the four words, and never Studio's

The label derivation (`structureLabels.ts`) becomes **mode-aware**, at the one
site, never by a second ladder:

- `SECTION` → **never `'Slide'`** on flow;
- the terminal fallback → **never `'Group'`** on flow;
- the pane header's `?? selection.blockKind` fallback (`StudioDesignTab.tsx:2513`)
  is **deleted** — a block labels from the served registry's `label` or it says
  nothing, exactly as ADR-544 D4 ruled for decks;
- the flow selection payload **omits** `slot` and `arrange` (§1.6) rather than
  null-filling them: a medium does not name grains its own projection deletes.

**ADR-544 F2 becomes symmetric** (§6 F5): no operator-facing string renders a
*deck* grain on flow, and none renders a raw attribute value on either medium.
One law, two media, gated both ways.

### D6 — `pathRow`'s always-null premise is made true, not assumed

`StudioDesignTab.tsx:1407-1411` asserts pathRow is *"structurally ALWAYS NULL on
a document … ADR-481 D1 flattened flow scaffolds so no `<section>` ancestor
exists."* One of its two premises is false: the flow flatten targets **only
`[data-arrange]`** (`projection.ts:4543-4557`), while `STRUCTURAL_PAGE_SEL` is
`'section.slide, :is(body, main, article) > section'` — and **Docs' own kernel
skin declares `section[data-block]`** (`docs.py:47-48`).

The gate becomes **mode-explicit** rather than resting on an assumed absence.
Flattening more substrate to defend a comment is the wrong direction: ADR-526's
`<section>`-wrapper refusal is about **authoring** one, and the read path must be
gated by mode, not by a premise that a skin contradicts.

`PASTE_ALLOW` excludes `SECTION` and `PROMOTE_KIND` has no `SECTION` entry, so
paste is not a route — the reachable routes are legacy substrate and the skin's
own declared shape.

### D7 — Existing documents are read honestly, not migrated

**No heal, and this is a deliberate difference from ADR-544 D7.** A deck needed
one because containment was newly *total* and un-homed blocks had nowhere legal
to be. Nothing here makes existing markup illegal: a `ul ul` is a rung the moment
the rung is readable, and a `data-indent` is a prose rung already. Existing
documents are correct under this law without being rewritten.

Where a document carries markup this law reads differently (a legacy
`data-indent`, a deep nesting), it converges **on its next authored write** —
migration-by-use (ADR-209), attributed to whoever typed. A fleet sweep would
manufacture revisions nobody authored.

---

## 4. What this costs, stated

### 4.1 The literal tab is gone

D4 deletes it. A member who typed Tab in prose for whitespace loses that. This is
accepted: it is the branch that made the rung gesture ambiguous, and the audit
found no evidence anyone wants a tab character in a continuous document. **This
is the one member-visible removal in this ADR** and the falsifier that would
reverse it is named in §6 F6.

### 4.2 The `<section>` question is NOT reopened

D6 gates a read path; it does not admit a wrapper. ADR-526 D1/§6's standing
refusal, and the two affordances that would reopen it (collapsible headings,
move-a-whole-section), are untouched and unscheduled. **A reader of this ADR
should not conclude that rungs make a section node necessary** — the rung tree is
derived from document position, exactly as ADR-526's span is.

### 4.3 `data-indent` loses its independent life

D1 absorbs it. Any workspace that set `data-indent` for a *presentational*
reason unrelated to subordination now has that read as a rung. Mitigation: the
values are identical (`1|2|3` → the same margins), so nothing renders
differently; only the *word* for it changes, and the pane's control consolidates.

### 4.4 Amendment cost

ADR-539 D3's constant generalizes; ADR-521 D4's Tab ruling narrows; ADR-536 D2's
indent row consolidates; ADR-544 F2 becomes symmetric; `AUTHORING.md`'s matrix
rows for `document` (keyboard/list-indent, the pane's Text section, the label
rule) all move. Canon lands **in the same commit** as the code, per the project's
doc-first discipline.

### 4.5 What is NOT forked

Per §2.3: the write door, `normalizeStructure`, the registry, `selection.ts`,
`tokenGrammar.admits`, the undo lineage, the paste allowlist, the projection
runtime. A future ADR that forks any of them owes the measurement §2.3 states.

---

## 5. Not decided here

- **Whether a list item becomes addressable** (the Notion model). D2 refuses it
  for now; the reopening evidence is a member gesture that genuinely needs to
  *select* one nested item — a per-item citation, a per-item move, or a per-item
  attribution. If per-block attribution ever lands (ADR-528 §2's separate bet),
  this question reopens with it.
- **Whether a heading-led span becomes a MOVE subject** ("move this section") —
  that is one of ADR-526 §6's two named `<section>`-reopening affordances, and
  D3 makes it *describable* without making it movable. Still awaiting evidence.
- **Collapsible headings** — unchanged, ADR-526 §6.
- **The final `FLOW_RUNGS` cardinality.** Three is what all three systems
  independently chose (§1.1); this ADR fixes the mechanism, not the enumeration.
- **Studio's media and paged rungs** — this ADR is flow-scoped. ADR-544 governs
  paged and is untouched.

---

## 6. Falsifiers

1. **If any operator-facing string renders `Slide`, `Group`, `Area`, `slot`,
   `col`, `cols`, `container` or a raw `data-block` value on a flow document**,
   D5 failed as a chokepoint — move the derivation, never add a second.
2. **If the flow selection payload names a grain flow's own projection deletes**
   (`slot`, `arrange`), D5's payload rule failed.
3. **If depth is declared in more than one place** — a second rung constant, a
   surviving independent `data-indent` control, or a nesting bound that is not
   `FLOW_RUNGS` — D1 failed and §1.1 has re-opened.
4. **If Tab means anything other than "step the rung" in a document**, D4 failed.
5. **If a gate pins a Studio grain to a flow surface, or a flow grain to a paged
   one**, the symmetry D5 establishes is not gated — an asymmetric falsifier is
   what let §1.6 ship.
6. **If a member is observed wanting a literal tab character in prose**, D4's
   deletion (§4.1) needs an explicit carve-out — an amendment to record, never a
   silent restoration.
7. **If a range over a heading and its body cannot be described as a subtree**,
   D3 failed and a multi-block selection is still a count.
8. **If `<li>` acquires `data-block-id`**, D2 was widened without the §5 evidence
   — that is an amendment, not an implementation detail.

---

## 7. Implementation phases

Sequenced so each phase is independently verifiable, substrate before surface,
and **each is gated by falsification before the next begins**:

1. **The rung, declared once** (D1) — `FLOW_RUNGS`; `data-indent` absorbed; both
   spellings clamp. Gate: F3.
2. **The rung, readable** (D2) — a block's rung derived without new identity;
   `normalizeStructure` provably unchanged. Gate: F8 (an `<li>` must NOT gain an
   id — a falsifier that must go red when one does).
3. **The span's shape** (D3) — rung-aware range subjects, derived in
   `selection.ts` only. Gate: F7.
4. **The gesture** (D4) — Tab steps the rung; the literal-tab branch deleted.
   Gate: F4.
5. **The vocabulary, symmetric** (D5 + D6) — the mode-aware label derivation, the
   payload omissions, the pathRow gate. Gates: F1, F2, F5.

**A browser click-pass gates this arc, not the gate battery.** Every §1 finding
was made against 22/22 green, and the specific pass this arc owes is: **Tab-nest
a bullet three deep in a real document, then select across a heading and its body
and read what the pane calls it.** The audit's own recommendation was that this
drive precede ratification of D2 — the "one opaque block" reasoning is from the
code, not from the gesture.
