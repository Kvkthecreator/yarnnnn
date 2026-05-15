# ADR-282: Axiom 8 — Propagate the Kernel/Instance Distinction for `money-truth`

**Status**: Proposed
**Date**: 2026-05-15
**Companion docs**: `docs/analysis/alpha-author-discourse-2026-05-15.md`, `docs/adr/ADR-283-alpha-author-bundle.md` (prerequisite-of)
**Amends**: FOUNDATIONS.md (Axiom 8 heading + body + version history), GLOSSARY.md (new axiom-level entry + sharpened instance entries), THESIS.md (targeted line edits where `money-truth` is doing kernel-level work), SERVICE-MODEL.md (version-history axiom name), README.md (one-liner axiom gloss), invocation-and-narrative.md (axiom gloss)
**Preserves**: alpha-trader instance-level vocabulary — `_money_truth.md`, `_money_truth_summary.md`, `services/outcomes/*.py`, `OutcomeProvider` ABC, `back-office-outcome-reconciliation` task, `TraderMoneyTruth` component, `MoneyTruthMeta` / `MoneyTruthData` types, `web/lib/content-shapes/money-truth.ts`, the `cockpit.money_truth` SURFACES binding key, `/api/cockpit/money-truth` route, blog posts with `money-truth` in title or body, every ADR-195 / ADR-211 / ADR-228 / ADR-267 reference to alpha-trader's substrate

## Context

Axiom 8 in FOUNDATIONS.md is currently named *"Money-Truth — Substrate Must Carry Reconciled Capital Reality."* The axiom's *architectural content* is correct — the workspace must touch a substrate carrying reconciled ground-truth that the operator personally bears the consequences of. But the *name* of the axiom, and `money-truth` as it appears throughout canonical docs, conflates two distinct things:

- **Kernel-level concept**: the axiomatic property — substrate-grounded, consequence-bearing, calibratable ground-truth must flow into the workspace
- **Alpha-trader instance**: the specific instantiation — Alpaca P&L flowing into `/workspace/context/{domain}/_money_truth.md` via `services/outcomes/`

Two pressures expose the conflation:

**Pressure 1 — THESIS already softens universality at the kernel level but FOUNDATIONS hasn't caught up.** THESIS commitment 3 (`docs/architecture/THESIS.md:90`) uses `ground-truth` as the kernel-level concept and `money-truth` as the instance, explicitly: *"Ground-truth evaluation — money-truth as the spine, universality not claimed."* That clarity exists in THESIS but doesn't propagate. THESIS L24 then says *"ground-truth evaluation (money-truth)"* — same line treats them as synonyms. THESIS L102 cites *"FOUNDATIONS Axiom 8 (Money-Truth)"* — same parenthetical conflation. The conflation is internal to THESIS, not just between THESIS and FOUNDATIONS.

**Pressure 2 — ADR-283 (alpha-author bundle) has a workspace where the conflation breaks.** The Netflix-screenplay workspace authoring a screenplay has zero external monetary signal for months. Axiom 8 must still hold for that workspace; its instance-level ground-truth is *internal substrate coherence* (Reviewer-detected corpus contradictions, voice drift) until external signal arrives. If `money-truth` is the axiom name, that workspace is treated as outside the axiom — which is architecturally wrong. The axiom holds; the noun overfit.

A 2026-05-15 codebase audit (`docs/analysis/alpha-author-discourse-2026-05-15.md` companion + grep across `docs/architecture/`, `docs/adr/`, `docs/design/`, `docs/features/`, `api/`, `web/`, `render/`, `supabase/migrations/`, `scripts/`, `CLAUDE.md`) verified:

- **Zero code-level kernel references.** No Python class, TypeScript type, database column, or service module uses `money-truth` as if it were the axiom-level concept. Axiom citations only live in canonical docs.
- **~330 instance-level code + doc references** are alpha-trader-scoped and must be preserved unchanged.
- **6 historical ADRs** cite Axiom 8 by its old name; preserved as artifacts per the ADR-259 chat-surface → feed-surface precedent.
- **8 canonical doc locations** currently conflate kernel and instance and need targeted edits (corrected from an earlier audit that listed 3).

## Decision

### D1. Reframe the problem

This ADR is not "rename Axiom 8." This ADR is **"propagate the kernel-concept-vs-alpha-trader-instance distinction across canon, atomically."**

The rename of Axiom 8's heading is one of several edits. The deeper move is establishing a discipline rule — `money-truth` is alpha-trader's instance-level term, *never* used as if it were the kernel-level concept — and propagating it through every canonical doc that currently violates it.

### D2. The discipline rule

> **`money-truth` is alpha-trader's instance-level term for FOUNDATIONS Axiom 8 (Ground-Truth Substrate). It must not be used in canonical docs as if it were the kernel-level concept.**
>
> When a doc means *"the axiomatic property that substrate must carry reconciled consequence-bearing reality"* — say **ground-truth substrate** and cite Axiom 8.
> When a doc means *"alpha-trader's `/workspace/context/{domain}/_money_truth.md` substrate, written by `services/outcomes/`, reconciled from Alpaca P&L"* — say **money-truth** and cite the alpha-trader bundle.
>
> A sentence that mentions both legitimately (e.g., *"alpha-trader's money-truth is the cleanest instance of ground-truth substrate per FOUNDATIONS Axiom 8"*) is *not* a conflation — it's instance-of relationship and is preferred.

This rule applies to all docs in `docs/architecture/`, `docs/design/`, `docs/features/`, `CLAUDE.md`, and any new ADRs from this point forward. Historical ADRs are exempt per D8.

### D3. Axiom 8 rename in FOUNDATIONS

`Axiom 8: Money-Truth — Substrate Must Carry Reconciled Capital Reality`
→
`Axiom 8: Ground-Truth Substrate — Substrate Must Carry Reconciled Consequence-Bearing Reality`

### D4. Generalize the axiom body in FOUNDATIONS

The current axiom body (FOUNDATIONS L476–502) mixes the kernel-level architectural property with alpha-trader instance-level vocabulary (`revenue`, `P&L`, `capital`, `commerce`). The rewrite separates them, mirroring how Axiom 1 separates the kernel substrate property from per-instance illustrations:

- **Kernel-level body** describes the architectural property in instance-agnostic terms. Three load-bearing properties: (a) consequence-bearing — the operator winces when it moves the wrong way; (b) substrate-grounded — flows back into the workspace as readable substrate, not living only in the operator's head; (c) calibratable — the Reviewer can read it and adjust judgment over time.
- **Three-instance illustration** points at concrete instantiations: alpha-trader (money-truth → P&L reconciliation), alpha-commerce (revenue-truth → subscription events + refunds), alpha-author (multi-signal: corpus-coherence + audience signal + revenue when present).

This is the same pattern Axiom 1 uses (kernel property + Authored Substrate clause + per-instance illustration).

### D5. THESIS amendments (this ADR's biggest correction vs an earlier draft)

An earlier draft of this ADR claimed THESIS needed no edit. **That was wrong.** THESIS uses `money-truth` in 9 places. The commitment-3 heading at L90 is already correct (`Ground-truth evaluation — money-truth as the spine, universality not claimed`) but the surrounding body conflates. Targeted edits:

- **L24** — *"ground-truth evaluation (money-truth)"* → *"ground-truth evaluation"* (drop the parenthetical synonym; the commitment-3 heading at L90 already defines money-truth as alpha-trader's instance)
- **L78** — *"the reviewer's judgment is evaluated against ground truth (money-truth)"* → *"the reviewer's judgment is evaluated against ground-truth substrate"* (kernel-level claim, instance synonym out)
- **L80** — *"Independence means the Reviewer's judgment is evaluated against ground truth (money-truth)"* → *"...against ground-truth substrate"* (same)
- **L94** — *"money-truth is the cleanest available ground-truth signal"* — **preserve unchanged**. This sentence is correctly pointing at alpha-trader's instance ("money-truth") as one example of the kernel concept ("ground-truth signal"). Exemplary instance-of phrasing per D2.
- **L102** — *"FOUNDATIONS Axiom 8 (Money-Truth)"* → *"FOUNDATIONS Axiom 8 (Ground-Truth Substrate)"* (axiom-name citation, must track the rename)
- **L196, L210, L229** — *"in domains with clean money-truth"* / *"the thesis is proven first in domains with clean money-truth"* / *"in domains where money-truth is clean"* — **preserve unchanged**. These claims correctly use `money-truth` to mean "alpha-trader-shaped instances" (clean monetary attribution). Replacing with `ground-truth substrate` would over-generalize the claim — THESIS legitimately asserts the *first* dogfood happens in money-truth-clean domains specifically.

The pattern that emerges: THESIS's commitment-3 heading at L90 already had the right framing. The ADR's job is propagating that framing through THESIS's body, *not* erasing instance-level claims that legitimately point at alpha-trader.

### D6. GLOSSARY amendments

- **Add new entry**: `Ground-truth substrate` — the kernel-level concept named by Axiom 8. Definition: *"The axiomatic property that the workspace must touch a substrate carrying reconciled consequence-bearing reality the operator personally bears the outcome of. Substrate-grounded, calibratable, regenerable. Per-domain instantiations include alpha-trader's `_money_truth.md`, alpha-commerce's revenue-truth, alpha-author's multi-signal corpus-coherence + audience + revenue substrate."*
- **Sharpen existing entries** — `Outcome`, `_money_truth.md`, `Money-Truth` (if a glossary entry by that name exists). Each gains a single-sentence pointer to the new axiom-level entry: *"alpha-trader's instance of [[ground-truth substrate]] (FOUNDATIONS Axiom 8)."* Existing definitions are preserved otherwise.
- **Loop entry (L163)** — *"money-truth reconciles"* phrase preserved (legitimately referencing alpha-trader's reconciler in operator-facing Loop description).
- **Substrate-canonical world entry (L171)** — *"ADR-195 (money-truth substrate)"* preserved (instance-pointer in historical citation).

### D7. Lower-priority canonical doc updates

Single-line substitutions where `money-truth` is currently doing kernel-level work:

- **`docs/architecture/SERVICE-MODEL.md` L483** — *"money-truth: Ax7→Ax8"* in version history. Either leave (historical artifact about renumbering) or update parenthetical to *"ground-truth substrate (formerly money-truth): Ax7→Ax8"*. Author's call at cascade-commit time.
- **`docs/architecture/README.md` L16** — FOUNDATIONS one-liner mentions *"money-truth"* in the list of axiom topics. Update to *"ground-truth substrate"* for axiom-level coherence.
- **`docs/architecture/invocation-and-narrative.md` L206** — *"FOUNDATIONS Axioms 1 / 2 / 3 / 5 / 7 / 8 — substrate, identity, purpose, mechanism, recursion, money-truth are unchanged"* — update the gloss to *"...recursion, ground-truth substrate are unchanged."*
- **`docs/architecture/persona-reflection.md` L271** — *"the continuous outcome loop (money-truth reconciliation)"* — preserve. Legitimately pointing at alpha-trader's reconciler as the canonical example.
- **`docs/architecture/reviewer-substrate.md` L116, L234** — references to *"the money-truth → future-judgment loop"* and *"ADR-195 v2 (money-truth substrate)"* — preserve. Instance-of references.
- **`docs/architecture/DOMAIN-STRESS-MATRIX.md` L368** — version-history line referencing old Axiom 7 numbering — preserve as historical artifact.
- **`docs/architecture/WORKSPACE.md` L94, L413, L419** — references to `_money_truth_summary.md` filename — preserve (instance filenames, never renamed).

The pattern: **rename where kernel-level, preserve where instance-level.** Most occurrences are instance-level and preserved.

### D8. Historical ADRs not edited

Historical ADRs that cite Axiom 8 by its old name (`ADR-194`, `ADR-195`, `ADR-205`, `ADR-207`, `ADR-228`, `ADR-231`, `ADR-267`) are not edited. They were correct artifacts at the time written. New ADRs from this point forward cite Axiom 8 (Ground-Truth Substrate). Same precedent as ADR-259 (chat-surface → feed-surface) where historical banners stayed.

### D9. No code rename necessary

The 2026-05-15 audit verified:

- **No Python classes** named `MoneyTruth*` at kernel level (`MoneyTruthFace` was deleted in ADR-273 Phase 2; `TraderMoneyTruth` is alpha-trader instance code)
- **No TypeScript types** named `MoneyTruth*` at kernel level (`MoneyTruthMeta`, `MoneyTruthData` are alpha-trader L2/L3 content-shape code per ADR-245)
- **No database columns** named `money_truth*` (verified across `supabase/migrations/`)
- **No service module** at kernel level uses `money-truth` (`services/outcomes/` is alpha-trader instance code)
- **No system prompt** at kernel level names the axiom by its old noun (axioms aren't cited by code; they're design constraints in canonical docs)

The cascade is **docs-only**. Zero code touches, zero migrations, zero test impact.

### D10. SURFACES.yaml + design-doc binding keys preserved

`cockpit.money_truth` as a binding key in `docs/programs/alpha-trader/SURFACES.yaml` and `docs/design/WORKSPACE.md` is **alpha-trader instance vocabulary** and preserved unchanged. The cockpit face component is named `TraderMoneyTruth.tsx`. The frontend route `/api/cockpit/money-truth` stays. These are instance-level operational identifiers, not axiom-level concept names.

When future bundles (alpha-author, alpha-commerce) declare their own ground-truth substrate faces, they pick instance-appropriate binding keys (e.g., `cockpit.corpus_signal` for alpha-author, `cockpit.revenue_truth` for alpha-commerce). The kernel doesn't normalize across instances — that would be a different ADR with worse architectural payoff.

## Cascade plan (single atomic commit)

Eight canonical-doc edits, no code, no migration. Single commit. Branch off main, land on main.

| File | Edit type | Lines |
|---|---|---|
| `docs/architecture/FOUNDATIONS.md` | Axiom 8 heading rewrite (D3) + body restructure (D4) + version-history append | 476, 486, 492, 615, 621, append to version table |
| `docs/architecture/GLOSSARY.md` | Add `Ground-truth substrate` entry; sharpen existing `Outcome` / `_money_truth.md` / `Money-Truth` entries with instance-pointer (D6) | 156 + new entry block |
| `docs/architecture/THESIS.md` | Targeted edits per D5 — L24, L78, L80, L102 rewrite; L90, L94, L196, L210, L229 preserve | L24, L78, L80, L102 |
| `docs/architecture/SERVICE-MODEL.md` | Version-history parenthetical update (D7) | L483 |
| `docs/architecture/README.md` | One-liner axiom gloss (D7) | L16 |
| `docs/architecture/invocation-and-narrative.md` | Axiom gloss (D7) | L206 |
| `docs/adr/ADR-282-axiom-8-ground-truth-rename.md` | This file | — |
| `docs/adr/ADR-283-alpha-author-bundle.md` | Citation already correct (already references ADR-282); no edit needed | — |

Optional / author's judgment at cascade-commit time:
- `docs/architecture/DOMAIN-STRESS-MATRIX.md` L368 — historical artifact, leave or note as historical
- `docs/architecture/reviewer-substrate.md`, `persona-reflection.md` — instance-pointers, all preserve per D7

## Grep gate (post-cascade verification)

The earlier ADR draft listed an incomplete grep gate. The corrected gate covers all phrasings observed in the audit:

```bash
# Must return zero results in canonical docs (excluding historical ADRs):
grep -rn "Axiom 8 (Money-Truth)" docs/architecture/ docs/design/ docs/features/ CLAUDE.md
grep -rn "Axiom 8 — Money-Truth\|Axiom 8: Money-Truth\|Axiom 8 Money-Truth" docs/architecture/ docs/design/ docs/features/ CLAUDE.md

# Must return only instance-level references (alpha-trader bundle scope) in canonical docs:
grep -rn "money-truth\|money_truth\|Money-Truth" docs/architecture/ docs/design/ docs/features/ CLAUDE.md

# Each remaining hit must be classifiable as alpha-trader instance vocabulary —
# pointing at _money_truth.md, services/outcomes/, TraderMoneyTruth component,
# the cockpit.money_truth binding key, or an instance-of relationship to ground-truth substrate.

# Must return positive results (new axiom-level vocabulary used):
grep -rn "Ground-Truth Substrate\|ground-truth substrate" docs/architecture/

# Must remain unchanged (alpha-trader instance code):
grep -rln "money-truth\|money_truth" api/services/outcomes/ web/lib/content-shapes/money-truth.ts web/components/library/programs/alpha-trader/
```

If any hit in the second-block grep can't be classified as alpha-trader instance vocabulary, that hit is a missed kernel-level reference and the cascade is incomplete. The grep gate is the singular implementation of D2 (the discipline rule) — it verifies the conflation has been propagated out.

## What this ADR enables

1. **ADR-283 (alpha-author bundle) can land clean.** alpha-author's multi-signal ground-truth shape is now axiomatically legitimate (Axiom 8 covers it explicitly via the three-instance illustration), not a special case bolted onto an alpha-trader-locked axiom.

2. **Future bundles inherit the corrected framing natively.** Each new bundle declares its own ground-truth instance shape; the kernel doesn't presume monetary signal.

3. **THESIS and FOUNDATIONS stop drifting.** Both use `ground-truth substrate` as the kernel-level concept and `money-truth` as alpha-trader's instance. Cross-doc vocabulary coherence.

4. **The discipline rule (D2) is enforceable.** Anyone writing a future canonical doc has a single rule to follow and a grep gate to verify against. Conflation becomes detectable, not endemic.

## What this ADR explicitly does not do

- Does not rename `_money_truth.md`, `_money_truth_summary.md`, or any other filename
- Does not rename `services/outcomes/`, the OutcomeProvider ABC, or any Python module
- Does not rename `TraderMoneyTruth.tsx`, `MoneyTruthMeta`, `MoneyTruthData`, `web/lib/content-shapes/money-truth.ts`, or any TypeScript identifier
- Does not rename SURFACES.yaml binding keys (`cockpit.money_truth`) or the `/api/cockpit/money-truth` route
- Does not edit historical ADRs (ADR-194 / ADR-195 / ADR-205 / ADR-207 / ADR-228 / ADR-231 / ADR-267)
- Does not edit blog posts in `content/posts/` that use `money-truth` (they're operator-facing content about alpha-trader's substrate, instance-scoped)
- Does not introduce new substrate shapes (alpha-author's ground-truth substrate is designed in ADR-283)
- Does not change ADR-195 v2 or its implementation
- Does not impact `_performance.md` (reviewer-seat calibration substrate, distinct concept, name preserved)

## Discovery note

This ADR was rewritten on 2026-05-15 after an audit of the codebase against the original draft surfaced two structural mistakes:

- The original draft claimed THESIS needed no edit. The audit showed THESIS uses `money-truth` in 9 places and conflates kernel and instance in 4 of them. The corrected ADR addresses each occurrence individually (D5).
- The original draft listed a 3-doc cascade (FOUNDATIONS + GLOSSARY + LAYER-MAPPING). The audit showed the actual radius is 6–8 canonical docs across `docs/architecture/`, and that LAYER-MAPPING is not impacted (no explicit Axiom 8 citation). The corrected ADR lists the actual radius (D7).

The deeper correction: the original draft framed the ADR as "rename Axiom 8." The audit showed the real architectural payoff is "propagate the kernel-concept-vs-alpha-trader-instance distinction across canon" — same direction, larger and more honest scope. The discipline rule (D2) is the load-bearing addition that the rename was only one consequence of.

This rewrite supersedes the original ADR-282 text in place per Singular Implementation. No v1/v2; the corrected text is the ADR.

## Status check

- **Implementation effort**: ~1.5 hours of focused doc edits + grep gate verification (slightly larger than the original ADR's 1-hour estimate because the radius is wider)
- **Risk**: low. Docs-only, no code, no migration, no test impact. The grep gate provides post-cascade verification.
- **Blocks**: ADR-283 (alpha-author bundle) implementation depends on this cascade landing first
- **Cascade**: 6 canonical doc files (8 if optional version-history updates included) + 1 new ADR. Single commit.
