# ADR-542: A token declares WHERE and WHEN — `applies` splits into scope and grains

> **Status**: **Accepted** (2026-08-09) — operator-ratified ("proceed with
> phase 3-5 in full"); the third phase of the hierarchy/docs-app streamlining
> (ADR-539 → ADR-541 → this).
> **Date**: 2026-08-09
> **Dimension**: **Substrate** (what a token row declares) primary; a
> **Channel** consequence (how the pane and the lane read it).
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**: ADR-453 D1 (`applies` + one grammar for both hands), ADR-455
> (the phrase table), ADR-525 D4 (`block-flow` — the term the flat vocabulary
> forced into a hyphen), ADR-527 D3 / ADR-536 (align's grain odyssey — the
> defect class this closes), ADR-539 (the registry declares; consumers derive),
> ADR-541 D2 (one derivation home), AUTHORING.md "Carried follow-ons"
> (`applies` → `(scope, grain)` — the debt this pays).

---

## 1. Context — one field doing two fields' work

Every token and measure row carries `applies: [slug…]`, and every slug is a
compound: *where the control mounts* × *what admits it*. The registry's own
docstring confesses it: *"Every value reads as (object × condition)… The
hyphen is doing a second field's work."* The twelve slugs decompose exactly:

| slug | scope (WHERE) | grain (WHEN) |
|---|---|---|
| `block` | block | any |
| `block-staged` | block | staged |
| `block-flow` | block | flow |
| `block-callout` | block | callout |
| `media` | block | media |
| `page` | page | any |
| `page-deck` | page | deck |
| `page-multicol` | page | multicol |
| `page-bg` | page | bg |
| `document` | document | any |
| `document-flow` | document | flow |
| `document-deck` | document | deck |

The flat encoding has a receipted defect history. ADR-525 §1.5: *"A token
literally cannot declare 'flow blocks only'"* — because saying it required
minting a new compound slug, which nobody did until the leak shipped. ADR-536:
align/indent were *"computed and never mounted"* — the grain existed, the
scope existed, and no gate could state the invariant "a served (scope, grain)
pair must mount somewhere" because the pair was not a pair, it was a hyphen.
And the standing `test_adr453` red (`valid_applies` stale since ADR-525) is
the same shape one layer up: the gate enumerated the compound slugs and the
compound set drifted. Two real axes, each small and closed, were disguised as
one open-ended axis that grew by concatenation.

## 2. Decisions

### D1 — Rows declare `scope` and `grains`; `applies` is deleted

Every `STUDIO_TOKENS` and `STUDIO_MEASURES` row replaces `applies` with:

- **`scope`**: tuple of `block | page | document` — where in the pane it
  mounts. (Plural because `tone` genuinely mounts at two: block and page.)
- **`grains`**: tuple of `any | staged | flow | media | callout | deck |
  multicol | bg` — the predicates, ANY of which admits it at a listed scope.
  `("any",)` is unconditional.

Both axes are **closed enums**, gate-checked. A new WHERE is a new scope
value (there have been three since ADR-453); a new WHEN is a new grain with a
declared predicate — never a new compound.

### D2 — One admitting function on each side of the wire

The wire serves `scope` + `grains` verbatim. The FE gains ONE function —
`admits(token, scope, ctx)` — consumed by every pane memo (the ~15 inline
`applies.includes(...)` sites collapse onto it) and by the surface's
span-token check. The lane's posture composes its WHERE phrase from two
tables (`SCOPE_PHRASES` × `GRAIN_PHRASES`) replacing `APPLIES_TARGETS`. Same
rule as ADR-541 D2: deriving admittance anywhere else re-opens the leak.

### D3 — The completeness invariant becomes checkable

*Every grain the kernel serves is consumed by the FE's `admits`, and every
scope has a pane mount.* This is the ADR-536 defect ("computed and never
mounted") stated as a gate: a grain added to the registry without its FE
predicate now fails CI instead of shipping a control that never renders.

### D4 — `test_adr453`'s standing red is repaired here

The `valid_applies` failure (stale since ADR-525, deliberately left visible
by the ADR-538 lane rather than silently patched) is re-cut to the two closed
enums — the honest home the 538 handoff named for it.

### D5 — Dead chrome, swept in the same motion

- The mobile tab bar stops offering a nav tab on flow — its pane content has
  been `isPaged`-unmounted since ADR-520/526 (a dead "Outline" tab; the
  outline's home is the pane, per ADR-526 D2's operator ruling).
- `pathRow` and `contents` stop being computed on flow, where they are
  structurally always-empty (ADR-481 D1 flattened the scaffolds).
- The served `group` field stays served and stays display-only (noted at the
  route since ADR-539); no FE consumer is added.

## 3. What this amends

| Canon | Change |
|---|---|
| ADR-453 D1 | `applies` retired; the one-grammar-for-both-hands rule is unchanged and now carries WHERE and WHEN as separate facts. |
| ADR-455 | The phrase table splits along the same seam. |
| ADR-525 D4 | `block-flow` dissolves into `scope=(block), grains=(flow)` — the compound the flat vocabulary forced. |
| AUTHORING.md | The carried follow-on is paid; the registry section documents the two axes. |
| `test_adr453` | Re-cut to the closed enums (D4). |

## 4. Consequences

**Positive.** The two axes stop growing by concatenation; the ADR-536 defect
class gets a standing gate (D3); the pane's token memos read as one predicate
instead of fifteen membership tests; the lane's WHERE phrase is composed, not
enumerated.

**Costs, stated.** Every gate that pinned an `applies` spelling re-cuts in
this commit (enumerated in the gate; the battery measures the delta). The
wire shape changes (`applies` out, `scope`/`grains` in) — FE and BE move in
one commit, as the vocabulary always has.

## 5. Falsifiers

1. If a change needs a slug that is neither a scope nor a grain, D1's claim
   that the axes are closed is wrong — reopen this ADR, don't mint a
   compound.
2. If a served grain reaches the FE without an `admits` predicate and D3's
   gate stays green, the completeness invariant is mis-stated — fix the gate
   before the vocabulary.

## 6. The one-line statement

**A token says WHERE it mounts and WHEN it applies as two declared facts —
one admitting function reads them on each side of the wire, so a control can
no longer be computed and never mounted, and the axes stop growing by
concatenation.**
