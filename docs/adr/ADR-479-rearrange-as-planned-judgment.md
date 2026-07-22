# ADR-479 — Re-arrange as planned judgment: the AI places, the mechanism applies

- **Status**: **Implemented** (2026-07-22) — operator-ratified in full before build. Gate `api/test_adr479_arrangement_plan.py` 19/19, behavioural (it drives `validate_plan`, it does not grep it) and falsified: disabling the total-coverage rule turns the content-destruction check red. Owed the human live-click smoke, like every FE ship in this arc.
- **Scope**: Studio · the arrangement act (deck slides + page sections)
- **Amends**: ADR-466 D5 (the role-aware slot ladder — superseded as the *decision* layer, preserved as the fallback) · ADR-462 D9 (the never-destroy-content invariant — strengthened from "refuse" to "account for every block") · ADR-477 D10 (a menu row that hints at nothing is a defect — one such row is deleted here)
- **Preserves**: ADR-443 R1 (the DOM is the model) · ADR-224 (the kernel names the category, never the instance) · ADR-307 (one gate on consequential acts) · ADR-396 (one meter) · ADR-209 (every write is one attributed revision)

## 1. The problem: a heuristic ladder standing in for a judgment

`applyArrangement` (artifactOps.ts) re-lays a page by carrying its content into a
new arrangement's slots. To decide *where each block goes*, it climbs a ladder:

1. a figure/gallery seeks a slot whose role is `media`;
2. else a block whose **source slot name** matches a target slot name lands there
   (`side` → `side`), unless that target is a media slot;
3. else everything falls into the first non-media, non-heading slot;
4. if the target arrangement has **no slot at all**, REFUSE.

Each rung is a proxy for a question none of them actually asks: *given this
content and this target layout, where does each piece belong?* The code's own
comment block is the confession — two silent content losses had already shipped
(5 arrangements carry no slot and `replaceWith` destroyed every block; 6 carry
more than one and `querySelector` collapsed a two-column slide into column one).
Both read to the operator as "re-arrange wiped my slide", because it did.

The current code fixed the *destruction*. It did not fix the *guessing*. The
operator's report after repeated use: re-arrange needs to preserve and
re-allocate with more intelligence than a name match can carry.

## 2. Decision

### D1 — The placement decision becomes a judgment; the write stays mechanism

Re-arrange becomes an **always-metered judgment call** that returns a *plan*,
never markup:

```json
{ "arrangement": "two-column",
  "placements": [ {"blockId": "h1", "slot": "heading"},
                  {"blockId": "p2", "slot": "main"},
                  {"blockId": "f3", "slot": "side"} ] }
```

The model reads the page's blocks (kind + text excerpt + current slot) and the
target arrangement's declared slots (name + role) — both already served by the
registry — and returns a placement per block. **It emits no HTML.** The
mechanism then applies the plan: materialize the fragment, move each block to
its named slot, land one CAS revision.

This is the ADR-475 shape (prompt → *named layer plan* → mechanical
composition), applied to the act that most needs it. It is why that arc worked
and why this one will: the model does the only part that requires understanding,
and touches nothing else.

**"Full AI" here means the placement decision is always a judgment — NOT that AI
authors the slide.** The write path stays 100% deterministic, which is precisely
what makes always-on safe.

### D2 — The plan is validated against the closed vocabulary before it writes

The arrangements are a **kernel-declared closed set** (11 deck, 6 page —
`STUDIO_ARRANGEMENTS`), each with named, role-typed slots. So a plan is
checkable, and an unchecked plan never reaches the document:

- every `slot` names a slot the target arrangement actually declares;
- every `blockId` names a block currently on the page;
- **total coverage** — every carried block appears exactly once, placed or
  explicitly overflowed. This is what retires the content-destruction class for
  good: ADR-462 D9's invariant strengthens from *refuse when unmappable* to
  *account for every block, always*.

A plan failing validation is **rejected, not rendered**. The mechanical ladder
(§1) remains as the fallback so a refusal, a cold engine, or an exhausted
balance still re-lays the page — degraded, never dead (ADR-468 D4: a composition
must never dead-end).

### D3 — Determinism, scale, and the future-proofing this buys

- **Deterministic**: the same plan always produces the same HTML. Non-determinism
  is quarantined in a *proposal* that must pass a total-coverage check against a
  closed vocabulary before it can touch substrate.
- **Scalable**: a 12th arrangement is a registry row. The model learns it from
  the served vocabulary — no new code, no prompt branch, no FE change. The kernel
  names the category; the instance is data (ADR-224).
- **Future-proof**: the plan is the contract. Swap the engine, change the model,
  add a slot role — the boundary holds, because nothing downstream of the plan
  knows or cares where the plan came from.

### D4 — Re-arrange lives on the toolbar button only; the menu row is deleted

The right-click menu is **block-scoped**: Copy/Paste/Duplicate/Delete, Turn
into…, Rewrite…, Check this…, Copy link to block, History — every row acts on
the block that was right-clicked. `Re-arrange…` acts on the **page containing
it**. That is a scope violation, and it is *why* the row was wired to
`menuOpenDesign` (`setRightTab('design')`) — the menu had no honest way to
express a page-level act, so it punted to "open the Design tab". Worse, the
gallery it punts at **was deleted 2026-07-21** (ADR-466 P12, as a duplicate of
the toolbar's). The row is a dangling pointer: an ADR-477 D10 defect — a menu
hint nothing listens for.

The toolbar is the correct and already-page-scoped home (`disabled={!hasPageAnchor}`,
"Select a slide first"). **The menu row is deleted.** The AI rows that stay
(`Rewrite…`, `Check this…`) prove the grammar rather than break it: they are
block-scoped AI, which is exactly what a right-click menu should carry.

### D5 — `Turn into…` is a separate defect, named not fixed

`Turn into…` shares the same dangling `menuOpenDesign` wiring. Unlike
Re-arrange it **is** genuinely block-scoped, so it belongs in the menu and
deserves a real implementation (the block-kind picker) rather than deletion.
Out of scope here; recorded so it is not mistaken for settled.

## 3. Cost, gating, consequence

One metered judgment per re-arrange, on the ADR-396 meter, through the ADR-307
gate like any consequential act — it mutates substrate. It is a **layout**
change over existing content, not authorship: no new content is invented, and
every block is conserved by D2. Cheap to undo (⌘Z is revert-as-write), which is
what makes always-on defensible where always-on generation would not be.

## 4. What this does NOT do

- Does not let the model emit HTML, CSS, or geometry.
- Does not invent, rewrite, or drop content — placement only, coverage enforced.
- Does not add an arrangement, a slot role, or a layout mode.
- Does not change the deck/page mode seam, the block grammar, or the write door.
- Does not touch `Turn into…` (D5).

## 5. The one-line statement

**Re-arrange asks a judgment where each block belongs and lets the mechanism put
it there — so the intelligence scales with the registry and the write stays
exactly as deterministic as it was.**
