# ADR-580 — The medium regroup: Studio is the seed stack, and the vocabulary stops being a document

> **Status**: **Accepted** (2026-08-19); D2/D3 **Implemented** same day; D4/D5 phased.
> Operator-directed: *"my intent is that this system actually becomes the seed and
> infrastructure stack that will evolve for a splitting of APPs for Deck and currently
> articles… current NEW is geared towards many text orientations while almost nothing of
> the component and metric and tables like considerations… the current philosophy is
> still focused on the remnants of the now gutted out documents type… thus, we need to
> regroup as a whole."*
>
> **Preserves**: [ADR-466](ADR-466-the-mode-native-carve-one-grammar-n-native-editors.md)
> (one grammar, N native editors — the app split is that carve promoted one altitude) ·
> [ADR-579](ADR-579-three-verbs-that-write-one-act-that-doesnt.md) (the verb grammar —
> family ordering happens *inside* NEW; ADD/UPDATE/ASK untouched) ·
> [ADR-539](ADR-539-the-vocabulary-declares-behavior.md) D1 (classification derives from
> declared fields — family is a DERIVATION of `tier × cites`, never a new hand-kept
> column) · [ADR-506](ADR-506-the-insert-door.md) D3 (**per-type kind subsetting stays
> refused** — this ADR reorders and labels; every kind stays reachable from every door)
> · [ADR-528](ADR-528-a-range-is-not-a-block-the-continuous-document.md) D5 (the `apps` column — the split's
> eventual mechanism, already declared) · [ADR-574](ADR-574-the-prose-currency-leads-text-is-the-text-app-docs-pauses.md)
> (Text owns prose authoring — which is exactly why Studio's NEW no longer needs to
> read like a word processor).
>
> **Dimensional classification** (Axiom 0): **Channel** (which medium's door leads with
> which family) + **Substrate** (the kind registry gains a derived family facet).

---

## 1. Context — the vocabulary is a document wearing a deck costume

The registry matrix, measured 2026-08-19:

| Family (derived) | Kinds | Count |
|---|---|---|
| **prose** (`tier=text`) | heading · prose · callout · quote · checklist · list · numbered · toggle | 8 |
| **composed** (`tier=object, cites=none`) | button · component · metrics · divider | 4 |
| **cited** (`cites≠none`) | table · chart · figure · gallery | 4 |

Eight prose kinds against three genuinely composed ones (divider is furniture). The NEW
door on a **deck** opens onto a column of text orientations — the shape of the gutted
document era (ADR-574 paused Docs; Text owns the prose currency), not the shape of the
medium being hardened. The drift ledger already measured the sibling fact: the flow
layouts are ~5% distinct from each other, while *"the deck is the one coherent case
because it opted out of being a webpage."*

## 2. Decisions

### D1 — Studio is the seed stack; Deck and Articles are the destined apps

Named as direction, not built today: the Studio infrastructure (one kernel vocabulary,
one write path, the verb grammar, the design-system cascade) is the **seed** that will
split into medium apps — **Deck first (hardening now), Articles after** (the flow
layouts, deliberately under-invested until Deck is hard). The split's mechanism already
exists: the registry's `apps` column (ADR-528 D5) + `register_app` residency (ADR-562).
A split is an app offering a weighted roster over the ONE kernel vocabulary — never a
fork of the grammar, the write path, or the registry. ADR-466's rule, one altitude up:
one grammar, N native apps.

### D2 — Family is a derivation: prose · composed · cited — **Implemented**

Every kind's **family** derives from fields the registry already declares (ADR-539 D1's
discipline — a derivation cannot drift, a hand column can):

```
family(row) = 'cited'    if row.cites != 'none'
              'composed' if row.tier == 'object'
              'prose'    otherwise (tier == 'text')
```

No new registry column. `divider` lands composed by its own declared tier; if use
falsifies that, the fix is a tier question, not a family exception. The FE derivation
lives in the ONE grouping module (`blockRows.tsx`), beside the ADD/NEW partition it
extends.

### D3 — The medium orders the families; nothing is hidden — **Implemented**

Inside the NEW group, family order follows the medium:

- **paged (deck/web)**: **composed → prose** — the deck's native units lead.
- **flow (document/article)**: **prose → composed** — the caret's units lead.
- The ADD group is untouched (its own verb).

This is **ordering and labeling, never subsetting** — ADR-506 D3's refusal stands
untouched: every kind remains reachable from every door on every medium. The toolbar's
NEW menu (the discovery door) additionally renders the family subheaders (**Composed**
· **Text**) so the structure teaches; the slash palette and the right-click tiers stay
terse (the located fast path). All doors render the one grouping module's order, so
they cannot disagree.

### D4 — The composed family grows deck-native kinds (phase)

The regroup exposes the real gap: three composed kinds cannot carry a deck. The growth
set, to be designed as registry rows + semantic fragments + kernel CSS (every property
a role or a rung — ADR-487 §3; themed by cascade, never by insert-time styling):

- **stat** — one big number with label and delta (the single-fact slide unit).
- **comparison** — two labelled columns of claims (the versus unit).
- **timeline** — ordered milestones on a line (the roadmap unit).
- **person** — avatar/name/role card (the team unit); **logo-row** — a strip of cited
  marks (this one is `cites=picture` — it lands in ADD).

Each lands in the vocabulary once and appears in every door by construction. Shapes
with free geometry stay refused (the ADR-487/538 line); the composed family is the
Notion/Gamma bet, not the Figma bet — composed semantic objects, not drawn ones.

### D5 — What the split will take (phase, named so it is not re-derived)

When Deck becomes an app: `register_app("deck", …)` with its resident; the `apps`
column weights the roster; the surface roster/dock follows `kernel_surfaces` (the
ADR-574 pause machinery, in reverse). Articles follows the same door later. Nothing in
this ADR needs undoing at that point — that is what D1 means by seed.

## 3. Gates

`api/test_adr580_medium_regroup.py` (script-style): the derivation matrix executed
against the live registry (component→composed, heading→prose, table→cited,
divider→composed); the FE module orders by medium; the doors pass their medium; no
kind hidden (count parity across media).
