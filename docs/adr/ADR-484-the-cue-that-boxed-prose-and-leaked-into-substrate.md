# ADR-484 — The cue that boxed prose, and leaked into the substrate

- **Status**: **Accepted** (2026-07-23, operator-reported — *"i thought the document is now one
  big flow, i still see outlined block selections for this newly created document"*)
- **Date**: 2026-07-23
- **Dimension**: Channel (primary — the flow surface's selection chrome) + **Substrate**
  (D2 — runtime chrome was being written into artifacts). No schema, no migration, no new
  primitive. One data repair (§4).
- **Amends**:
  - **ADR-482 D2** — the asymmetry it fixed was real; the direction it fixed it in was wrong
    for prose. The cue becomes OBJECT-ONLY on flow. D2's fix stands for objects.
- **Preserves**: ADR-480 D1 (the flow editing grain) · ADR-481 D2/D3 (no hover cue, no gutter
  on flow) · ADR-462 D5 (selection is neutral) · ADR-482 D8 (the UA focus ring stays
  suppressed) · ADR-209 (the repair lands through the one attributed write door) · **every
  `paged` surface in full**.

---

## 1. Why this ADR exists

An operator opened a freshly-created flow document and reported still seeing **outlined block
selections** — the per-block enclosure ADR-480 was supposed to have dissolved.

The outline was ours, and it was mine: **ADR-482 D2**. D2 observed a genuine asymmetry — on
flow, right-click applied the neutral `.yarnnn-pointed` cue and left-click did not — and
resolved it by making left-click match right-click:

```js
if (cur) cur.classList.add('yarnnn-pointed');   // ADR-482 D2, unconditional
```

That is the wrong direction on prose. On a continuous writing surface, **clicking into a
paragraph places a caret, and the caret IS the feedback.** A rule drawn around the paragraph
re-asserts exactly the enclosure ADR-480 dissolved — the "mouse fights me" complaint that
`FLOW_POINTER_CSS` was written to end.

The evidence that this was an oversight rather than a judgment: `FLOW_POINTER_CSS` had
**already drawn the correct boundary** for the hover cue, scoping it to object kinds
(`figure`, `table`, `chart`, `gallery`, `metrics`) and never to prose. D2 applied the
*selection* cue without honouring the line the *hover* cue already respected.

**Decision D1**: on flow, the selection cue applies to **objects only**. A figure/table/
chart/gallery/divider is still selected as a unit — there is no caret to stand in for the
cue, so it keeps it. Prose gets the caret and nothing else. Paged is untouched: there the
per-block outline is meaningful, because one block is live at a time.

---

## 2. The worse bug underneath

Reading the operator's actual document to confirm the diagnosis surfaced something the
report could not have named:

```html
<h2 data-block="heading" data-block-id="t3" class="yarnnn-pointed">First section</h2>
```

**The chrome class had been written into the saved artifact.**

`readSourceInner` — the ONE serializer both commit paths use (the flow root and the
per-block edit) — restores citation islands to their source form and strips nothing else. So
every commit serialized the DOM *as it stood*, and whichever block was selected at that
moment carried its selection cue into the file.

This is categorically worse than a live-session artifact:

- it renders the outline **for every future reader**, in every session, forever
- it sits in the substrate **attributed as the member's own authored content** (ADR-209),
  when the member never wrote it and could not see that they had
- it is invisible to the surface that caused it — no rule of ours draws an outline for a
  saved class; the class simply *is* the state now

**Decision D2**: `readSourceInner` strips runtime chrome before serializing. Done there
because it is the singular serializer, so chrome cannot leak from either commit path. The
strip is token-wise (`class="a yarnnn-pointed b"` → `class="a b"`), and an attribute left
with no tokens is dropped rather than left as `class=""`.

---

## 3. The generalization

ADR-482 §10 recorded: *an affordance a deletion leans on must be exercised in the mode that
inherits it.* This ADR adds the substrate-side twin:

> **Runtime chrome painted onto the live DOM must be stripped at the serialization boundary,
> not merely styled correctly.** A cue that is invisible in one mode is still *present* in
> the DOM, and any path that reads the DOM to persist it will write the cue into the
> artifact.

The class was correct as chrome and catastrophic as content. Nothing in the CSS layer could
have caught that — the styling was scoped fine; the *serializer* was the unguarded surface.
Every class the runtime adds is now a candidate for the same leak, which is why the strip
lives at the one door rather than in a per-class rule.

---

## 4. The data repair

The leak had already shipped. Three artifacts in the operator's live workspace carried it,
five occurrences total — including the operator's real `prd-for-yarnnn` document (3).

`api/scripts/oneshot/adr484_strip_leaked_chrome_class.py` repairs them **through
`write_revision`**, never a raw UPDATE, attributed `system:adr484-chrome-strip` — a
mechanical repair of runtime leakage, explicitly *not* an authored edit, because the member
neither wrote the class nor removed it.

Receipts (2026-07-23): 3 artifacts repaired, 3 attributed revisions written,
`select count(*) … where content like '%yarnnn-pointed%'` → **0**. Authored classes survived
(`class="lede"` intact, 3 occurrences in `prd-for-yarnnn`); no empty `class=""` remains.

A bug in the repair script itself was caught by its own test pass before it touched anything:
substring surgery turned `class="a yarnnn-pointed b"` into `class="ab"`, fusing two unrelated
classes into one that never existed. Rewritten token-wise. *Test the repair against the real
shapes before running it against the real data.*

---

## 5. Consequences

- Clicking prose on a flow document places a caret and draws nothing. The document reads as
  one continuous writing surface, which is what ADR-480 promised.
- Objects still select visibly, so the ADR-482 D2 asymmetry stays fixed where it mattered.
- No artifact can acquire runtime chrome as content again.
- Three already-damaged artifacts are clean, with the repair legible in the revision trail.

---

## 6. Validation

`web/scripts/gates/adr484_flow_chrome_leak.mjs` (**14/14**) — **executes** the real flow
click branch and the real `readSourceInner` body extracted from source, with a **falsifier per
defect**: restore D2's unconditional apply and assert prose boxes again; remove the strip and
assert the class serializes again. Prose/heading/quote/checklist draw nothing;
figure/table/chart/divider still do.

`api/test_adr482_flow_completion.py` amended (34/34) — the D2 assertion pinned the literal
unconditional-apply line this ADR replaces. The invariant it protects (left-click is not
silently inert) is preserved and narrowed to the correct scope.

Siblings green: ADR-480 30/30 · ADR-481 32/32 · ADR-482 slash-take 7/7 · ADR-483 17/17.
`next build` clean.

**Owed**: a human click-pass confirming prose no longer outlines and objects still do.
