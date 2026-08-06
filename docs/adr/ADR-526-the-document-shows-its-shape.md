# ADR-526: The document shows its shape — the outline the member never got

> **Status**: **Accepted + Implemented** (2026-08-06). All nine sites in §5 shipped.
> Gates: new `adr526_docs_structure.mjs` **35/35** — the outline walk, the paste-provenance
> test and the sanitizer's attribute carve all EXECUTE the real extracted bodies, with a
> falsifier on the id guard; ADR-525 33/33 · ADR-484 19/19 · ADR-521 **35/35, and it earned
> its keep**: it caught three backticks in comments added inside the runtime template
> literal, which would have broken the build; ADR-519 16/16 · ADR-520 23/23 · ADR-522 all.
> `next build` **exit 0**, 169/169 pages, from an isolated worktree.
> Two operator decisions were taken at ratification: the outline lives **in the pane**
> (not a rail), and ⌥↑/⌥↓ ships as a **structure-tier act** (D3's argued reversal).
> **The operator click-pass is the one open item** — human-driven by necessity (the flow
> runtime lives in an opaque-origin iframe that synthesized keys cannot drive).
> Derived from the operator's directive to
> cross-compare Studio's Figma-benchmarked hierarchy work against Docs and *"re-apply
> features that pertain to the work flow type processing for docs app"* — technically
> different, equivalent in end-user experience. The audit that followed found the gap is
> not a missing feature but a **missing consumer**: the document's structure is already
> derived, twice, and routed exclusively to the AI.
> **Date**: 2026-08-06
> **Dimension**: **Channel** (what the surface shows the member about where they are).
> Nothing at the Substrate dimension changes — no new file, no new write door, no new op,
> no revision semantics, and **no `<section>` wrapper** (§4). The outline is derived at
> render from the artifact the pane already parses.
> **Relates to**: ADR-519 (the Studio counterpart this ADR answers — its D1 excluded Docs,
> and this is what the exclusion owed), ADR-520 D4 ("the pane is the structure's home" —
> the housing precedent this ADR follows), ADR-522 D4 (the heading convention + the
> `<section>` deferral this ADR upholds and scopes), ADR-481 D4 (the outline this ADR
> restores, approved there and deleted without a reversing decision), ADR-521 D4 (the
> keyboard-entrance precedent D3 rides), ADR-525 (the tier this ADR composes against),
> ADR-518 (the Docs/Studio split — one component, two grammars).

---

## 1. Context — the structure is computed twice and shown to nobody

### 1.1 The asymmetry

| | The AI receives | The member receives |
|---|---|---|
| The document's outline | a 24-entry indented table of contents, **every turn** | nothing |
| The current section | *"The member is writing under the heading 'Pricing'."* | nothing |
| Any structural view | both of the above | font sizes |

Both halves already ship:

- **`extract_outline`** (`api/services/studio.py:1920-1930`) walks `<h1>/<h2>` in document
  order, indents h2, caps at 24. Its only consumer is `:2019-2035` — the **lane posture**.
- **`headingAboveOf`** (`projection.ts:550-564`) resolves the nearest heading at-or-above
  any block by `compareDocumentPosition`, and stamps `headingId` + `headingText` on every
  `yarnnn-point` payload (`:653-660`). It reaches React state (`StudioSurface.tsx:609-610`)
  and is read at exactly one site (`:781-789`) — the ADR-522 focus memo, which sends it to
  the server. `build_focus_line`'s own docstring says the rest: *"a server-rendered line in
  the system posture, once per turn, **which the member never sees**"* (`studio.py:1945`).

ADR-522 was right to route it there — it was avoiding ADR-446 D5's composer-spam failure.
But *AI-only* was never a decision; it is simply where the derivation stopped.

### 1.2 The member's actual inventory

Every structural affordance in Docs, enumerated:

- **No rail** — `{isPaged && <PagedNavigator …>}` (`StudioSurface.tsx:2685`), and the
  toggle is paged-gated too (`:2734`).
- **No breadcrumb** — `{isPaged && selection && <SelectionBreadcrumb …>}` (`:2963`), and
  the component would return `null` on flow anyway (it needs `STRUCTURAL_PAGE_SEL`).
- **No path row in the pane** — `pathRow` is gated on `pageOfSelection != null`
  (`StudioDesignTab.tsx:952`), which resolves through `PAGE_SEL`; ADR-481 D1 flattened flow
  scaffolds, so no `<section>` ancestor exists and it is **always null**. (STUDIO.md
  claimed "✅ path" for `block (text)` from 2026-08-05 until `a862438` corrected it.)
- **No Contents** — gated `scope === 'page' | 'container'` (`:947-950`); flow has neither.
- **No Esc-walk depth** — `projection.ts:848-858` looks for `CONTAINER_SEL` then
  `PAGE_SEL`; on a flat document both miss, so Esc goes straight to clear. One rung.
- **`scrollToBlock` is fully built and completely unreachable** — the plumbing exists
  (`StudioSurface.tsx:2466`, `StudioCanvas.tsx:520-522`, `yarnnn-scroll-to-block`), and
  all three of its entry points are paged-gated.

The only structure a Docs member perceives is that an h1 renders larger than an h2.

Compare Studio at the same commit: the page grain has **five** routes to selection (click
margin · Esc-walk · breadcrumb · pane path · navigator), the container grain **four**. Docs
has **one** — click — for its only grain.

### 1.3 The outline was approved in canon, then deleted as hygiene

This is the part that makes the decision easy. **ADR-481 D4 explicitly kept it**:

> "`extractOutline` (`StudioNavigator.tsx`) walks `h1, h2` … a heading outline is exactly
> the Word/Docs nav-pane contract. … the navigator was already mode-native. No work."

It was removed in `c3f2a1e` (the ADR-518 polish pass, 2026-08-05), framed as dead-code
hygiene: *"the carve left the flow-outline renderer dead behind an `isPaged` flag …
Deleted, not dual-run … `extractOutline`/`onSelectHeading` gone."*

The framing at `StudioSurface.tsx:2681-2684` — *"a derived table of contents wearing a
navigator's clothes"* — is a **housing** argument, and a correct one: a slide filmstrip is
the wrong home for an outline. It is not a refusal of outlines. **No ADR reversed D4's
approval.** The capability was approved, built, mis-housed, and then removed for being
mis-housed.

And the member-facing documentation never caught up: `docs/gitbook/apps/docs.md` described
*"The outline on the left"* for a rail that had not existed since 2026-08-05 (corrected in
`a862438`, in anticipation of this ADR).

---

## 2. What transfers from the Figma benchmark, and what does not

ADR-519 §1 is explicit that the import was **"the *panel grammar*, not the node types."**
That is precisely the part that survives a change of medium.

| Figma → Studio (ADR-519/520) | Docs equivalent | Transfers? |
|---|---|---|
| One ordered spine; scopes differ only by **which rows render** | already true post-ADR-525 (the text tier renders fewer rows) | ✅ shipped |
| **Group dissolved**, not added — "a container without declared layout" | **the section is dissolved, not added** — it *is* "this heading to the next" (D1) | ✅ this ADR |
| Structure reachable via **Contents in the pane**; the rail is the sequence | the outline lives in the pane, not a rail (D2) | ✅ this ADR |
| Ancestor **path row** in Identity | the **enclosing heading**, from `headingId` (D2) | ✅ this ADR |
| Alignment glyph rows · W/H fields · Position | — no boxes, no coordinate space | 🚫 correctly absent |
| Page/container grains | — flow has neither by derivation (ADR-481 D1) | 🚫 correctly absent |

The second row is the load-bearing one, and it is the whole design. ADR-519 D2 refused to
add a Group node type because a group **is** a `<div>` without declared layout — *"the
honest CSS truth Figma itself hides."* The same move applies here: a section **is** the
span from a heading to the next heading, and `headingAboveOf` already computes it by
document position. Adding a `<section>` wrapper to make the outline work would be exactly
the shadow node ADR-519 D2 refused.

---

## 3. Decisions

### D1 — The section is a derived span, not a node

> **Docs' structural grain is the HEADING, and a "section" is the span from one heading to
> the next. It is derived at read, never authored, never wrapped.**

ADR-522 D4 already named this convention and its cost honestly (*"Docs has NO section
unit … a reading convention stated rather than papered over"*). This ADR **upholds it** and
makes it the basis of the affordances below, rather than treating it as a stopgap.

Consequence: the outline is a *projection* of the document, not a second structure. It
cannot drift from the prose, because it has no independent existence. Write a heading and
it appears; delete one and it goes. There is nothing to maintain, and nothing to sync.

### D2 — The outline and the enclosing heading are shown to the member

Two consumers are added to derivations that already exist:

- **The outline** renders in the **pane at document scope** (nothing selected) — the
  ADR-520 D4 housing rule (*"the pane is the structure's home"*), which is the same reading
  that deleted Studio's navigator tree. Rows are `h1/h2/h3` in document order, indented by
  level, click-to-select-and-scroll through the **existing** `scrollToBlock` reach
  (`selectNodeFromNavigator`) — a new reach, never a new op (STUDIO.md rule 7).
- **The enclosing heading** renders in the pane's **Identity** at block scope, replacing
  the `pathRow` that is structurally always-null on flow (§1.2). It is the flow analogue of
  Studio's ancestor path: *"‹heading› › this block"*, one rung deep because the document is
  one rung deep. Sourced from `selection.headingId`/`headingText`, already on every payload.

**Derived client-side.** The pane already parses the artifact (`StudioDesignTab.tsx:819-821`,
`DOMParser`), and every heading carries `data-block-id` from `normalizeStructure`. So the
outline is a DOM walk over the parsed document — **no server change, and no id backfill**.
This resolves ADR-522 §182's observation that `extract_outline` returns bare strings with
no ids: the server function is for the *lane posture* and stays exactly as it is; the FE
never calls it. Two consumers, two derivations, each in the register its reader needs —
never one shared function bent to serve both.

### D3 — ⌥↑ / ⌥↓ move the block, as a structure-tier act

> **Reordering a block on flow is a keyboard act on the structure tier, not an enclosure
> verb and not a drag.**

This is a **deliberate, argued reversal** of a standing position, so it states its case:

- **What is upheld.** ADR-521 D7's *"no drag handles / positional anything on flow"* stands
  unchanged. ADR-525 D3's withdrawal of Move up/down from the pane and menu stands — and
  `a862438` extended it to objects on flow, where the pane had kept it.
- **What changes.** Those refusals are about **presentation**: a drag handle asserts a box,
  and a pane/menu verb row presents the block as an enclosure with a position in a list.
  A keyboard chord asserts neither. It says "take this block and put it before the previous
  one" — which is exactly what `moveBlock` already does, medium-agnostically
  (`StudioSurface.tsx:1608`).
- **The precedent is exact.** ADR-521 D4 landed Tab/⇧Tab list indent and superseded the
  flow runtime's own written refusal, on this reasoning: *"a keyboard entrance to a
  structural op has exactly slash's legitimacy — the key is not the op, it is a door to
  it."* ⌥↑/⌥↓ is the same shape, on the same tier, for the same reason.
- **Why it is needed.** After ADR-525 the only way to move a paragraph is select · ⌘X ·
  place caret · ⌘V. `projection.ts:3019` prices this as *"the browser's own, priced and
  accepted"* — but that pricing was set when the gutter was deleted, before the pane and
  menu verbs were also withdrawn. The price rose and was never re-checked.
- **The convention.** ⌥↑/⌥↓ is Notion's and Google Docs' chord for exactly this.

Scoped like every other flow key: it never fires while a text *range* is selected (that is
the browser's), and it routes through the same `applyOp` door — one revision, structural,
so ADR-523 D1's reload rule applies unchanged.

### D4 — The cut/paste attribute round-trip is a bug, and it is fixed

Independent of D3, and true for any member who reorders by cut/paste: the ADR-521 D5 paste
allowlist strips **every attribute except `href`**. That is correct for *foreign* HTML — it
is a security gate. It is wrong for a member cutting and pasting **within their own
document**, where it silently discards `data-ref` citations and `data-tone` tokens on the
moved content.

The fix is narrow: an internal paste (the clipboard payload originated in this artifact,
identified at cut time) preserves the substrate attributes the grammar already speaks —
`data-block`, `data-block-id`, `data-ref`, and the declared token attributes — while every
other attribute stays stripped and the foreign-paste path is **untouched**. Ids are
re-minted on paste, never duplicated (`normalizeStructure` already owns that rule).

---

## 4. What this ADR refuses

- **No `<section>` wrapper.** ADR-522 D4 deferred it *"on evidence that the heading
  convention is insufficient"*. This audit is that evidence, and it says the convention is
  **sufficient** for the outline, the enclosing-heading crumb, and jump-to-heading — all of
  which D2 ships without it. It is insufficient for exactly two things, which is what would
  reopen the question (§6).
- **No rail.** The outline lives in the pane (D2), on ADR-520 D4's precedent. A second
  structural view is the *"second structure tree"* ADR-520 D5 refused in Studio; Docs
  inherits that refusal rather than re-litigating it.
- **No block-set selection mode.** ADR-521 D7 stands — the browser range IS flow's
  selection. The outline selects *one* heading; it is a reach, not a selection mode.
- **No drag handles, no positional anything on flow.** ADR-521 D7 / ADR-481 D2 unchanged.
- **No outline-drag-to-reorder-sections.** It would need the `<section>` wrapper this ADR
  refuses, and it is the exact affordance §6 lists as reopening evidence.
- **No collapsible headings.** Structurally blocked without the wrapper; see §6.
- **No new op, no new primitive, no schema change.** Every act above composes an existing
  door.

---

## 5. Implementation scope

| # | Site | Change |
|---|---|---|
| 1 | `StudioDesignTab.tsx` | `walkOutline(doc)` — headings in document order with level + id (client-side, from the already-parsed doc) |
| 2 | `StudioDesignTab.tsx` document scope | the **Outline** section, rows click-to-select via the existing `onSelectNode` |
| 3 | `StudioDesignTab.tsx` block scope Identity | the enclosing-heading crumb, from `selection.headingId`/`headingText` |
| 4 | `StudioSurface.tsx` | pass the flow reach: `onSelectNode` already exists — verify it is wired for flow (its callers were all paged-gated) |
| 5 | `projection.ts` | ⌥↑/⌥↓ → `yarnnn-key-verb move`, structure-tier scoped (D3) |
| 6 | `StudioSurface.tsx` | route the move verb to the existing `moveBlock` op |
| 7 | `projection.ts` | the internal-paste attribute carve (D4) |
| 8 | `docs/design/AUTHORING.md` | the Docs column gains its structural rows; rule 12 |
| 9 | `docs/gitbook/apps/docs.md` | the outline sentence (already corrected in `a862438`) |

New gate: `adr526_docs_structure.mjs` — executes the real outline derivation, the real
⌥↑/⌥↓ scoping, and the real paste carve, with a falsifier per claim.

---

## 6. What would reopen the `<section>` question

Stated so the next reader does not have to re-derive it. The heading convention is
insufficient for exactly two affordances:

1. **Collapsible headings** — folding everything under an h2 requires a element to fold.
2. **Move / duplicate a whole section** — including outline-drag-to-reorder.

If either becomes a real workload, `<section data-block>` wrappers emitted at
`normalizeStructure` (migration-by-use, the ADR-511 annotation pattern — no fleet sweep) is
the truer model, and it earns its own ADR. **Neither is speculative-blocked**; they are
simply not yet evidenced, and D2's affordances are the thing most likely to generate the
evidence one way or the other.

---

## 7. Consequences

**The member sees what the AI sees.** The asymmetry in §1.1 closes: the outline and the
current section stop being privileged information.

**Docs gets a second and third reach to its one grain** — outline click and heading crumb —
where it had only the click. Not parity with Studio's five routes, and it should not be:
flow is one rung deep, and the affordances are sized to the medium.

**Accepted cost**: the outline is h1/h2/h3 only. A document whose structure lives in bold
paragraphs shows an empty outline — correctly, because it has no structure the system can
honestly name. The empty state says so rather than inventing one.

**Accepted cost**: D3 adds a second reorder path (⌥↑/⌥↓ alongside cut/paste). This is not
a dual implementation — both land through `moveBlock`/the browser respectively, and D4
makes the cut/paste path correct rather than leaving two half-working routes.
