# ADR-282: Axiom 8 — Rename "Money-Truth" to "Ground-Truth Substrate"

**Status**: Proposed
**Date**: 2026-05-15
**Companion docs**: `docs/analysis/alpha-author-discourse-2026-05-15.md`, `docs/adr/ADR-283-alpha-author-bundle.md` (next)
**Amends**: FOUNDATIONS.md Axiom 8 (heading + wording), GLOSSARY.md (axiom-level vocabulary entry), LAYER-MAPPING.md (axiom citation), THESIS.md (already correct — no edit, just citation strengthening)
**Preserves**: alpha-trader instance-level vocabulary (`money-truth`, `_money_truth.md`, `services/outcomes/*.py`), all existing reconciliation code, ADR-195 v2's substrate semantics

## Context

Axiom 8 in FOUNDATIONS.md is currently named *"Money-Truth — Substrate Must Carry Reconciled Capital Reality."* The axiom text correctly describes a load-bearing architectural property — that the workspace must touch a substrate carrying reconciled ground-truth that the operator personally bears the consequences of — but the *name* of the axiom and the noun used throughout its body (`money-truth`) implies the property only applies in monetary-capital domains.

This was historically accurate. The axiom was first articulated when alpha-trader was the only consequential dogfood, and Alpaca P&L flowing into `_money_truth.md` was the canonical instance. The naming worked because the kernel had exactly one instantiation.

The framing is no longer accurate. Two pressures expose it:

1. **THESIS.md already softens the universality** of money-truth at commitment 3 (`docs/architecture/THESIS.md:90-94`): *"in the domains where it applies, money-truth is the cleanest available ground-truth signal."* THESIS uses *"ground-truth"* as the kernel-level concept and *"money-truth"* as a domain-specific instance. FOUNDATIONS Axiom 8 doesn't yet reflect this distinction.

2. **The alpha-author discourse (2026-05-15)** identified a concrete disconfirming case: an alpha-author workspace authoring a Netflix screenplay has zero external monetary signal for months. Axiom 8 must still hold for that workspace. The ground-truth signal there is *internal substrate coherence* (corpus contradictions, voice drift, continuity breaks), eventually augmented by external signal (producer interest, reads, sales) when the artifact ships. This is a multi-signal, multi-timescale instantiation of the same axiomatic property. The current axiom name accommodates it awkwardly at best.

The fix is a rename, not a re-derivation. The axiom's content is correct. The noun overfit.

## Decision

### D1. Rename the axiom

`Axiom 8: Money-Truth — Substrate Must Carry Reconciled Capital Reality`
→
`Axiom 8: Ground-Truth Substrate — Substrate Must Carry Reconciled Consequence-Bearing Reality`

### D2. Generalize the axiom body

The axiom body currently mixes two registers — the kernel-level architectural property and the alpha-trader instance-level vocabulary (`revenue`, `P&L`, `capital`, `commerce`). Separate them:

- **Kernel-level body** describes the architectural property in instance-agnostic terms: *the workspace must touch a substrate that (a) is consequence-bearing — the operator winces when it moves the wrong way; (b) is substrate-grounded — flows back into the workspace as readable substrate, not living only in the operator's head; (c) is calibratable — the Reviewer can read it and adjust judgment over time.*
- **Three-instance illustration** points at concrete instantiations: alpha-trader (P&L), alpha-commerce (subscription events + refunds), alpha-author (multi-signal: corpus coherence + audience signal + revenue when present).

This is the same pattern Axiom 1 uses (kernel property + Authored Substrate clause + per-instance illustration).

### D3. Preserve `money-truth` as alpha-trader's instance-level vocabulary

`money-truth` survives unchanged as alpha-trader's instance-level term throughout:

- `_money_truth.md` filename — unchanged
- `services/outcomes/*.py` module — unchanged
- `OutcomeProvider` ABC — unchanged
- `back-office-outcome-reconciliation` task — unchanged
- alpha-trader MANIFEST + reference-workspace references — unchanged
- ADR-195 v2 + all its referenced code — unchanged

The kernel-level concept is `ground-truth substrate`. alpha-trader's instance of that concept is `money-truth`. Both terms remain useful; the relationship between them is clean (instance-of). The kernel narrative ("substrate must carry reconciled consequence-bearing reality") and the alpha-trader narrative ("money-truth is the cleanest available signal in trading") compose correctly under this naming.

### D4. No code rename necessary

The grep audit on `money-truth` and `_money_truth.md` confirms: every code reference is alpha-trader-instance-scoped (`services/outcomes/`, `back-office` reconciler, `_money_truth.md` writers). There are no kernel-level Python references to "money-truth" as an axiom-level concept — the axiom-level concept only lives in canonical docs. Rename is a docs-only operation.

### D5. GLOSSARY.md cascade

The GLOSSARY entries `Outcome`, `_money_truth.md`, and `Money-Truth` describe alpha-trader's instance-level vocabulary. They remain accurate as instance entries — they were always about alpha-trader's substrate, not about the axiom-level concept.

Add a new axiom-level entry: **Ground-truth substrate** (the kernel-level concept named by Axiom 8) with a pointer to the per-domain instances.

The existing entries gain a single-sentence pointer: *"alpha-trader's instance of [[ground-truth substrate]] (FOUNDATIONS Axiom 8)."*

### D6. THESIS.md does not need edit

THESIS.md commitment 3 already uses `ground-truth` correctly:

> *"in the domains where it applies, money-truth is the cleanest available ground-truth signal, and the architecture is instrumented to close the loop on it."*

> *"the reviewer's judgment is evaluated against ground truth (money-truth), not against internal agreement with producers."*

The rename ADR cites this as supporting evidence that THESIS already holds the distinction. After ADR-282 lands, FOUNDATIONS catches up to THESIS rather than vice versa.

### D7. LAYER-MAPPING.md cascade

Any reference to "Axiom 8 (Money-Truth)" becomes "Axiom 8 (Ground-Truth Substrate)" by literal substitution. Same axiom number, same content, new noun.

### D8. ADR backward references

Historical ADRs that cite "Axiom 8 (Money-Truth)" are *not* edited — they are historical artifacts and the citation was correct when written. New ADRs from this point forward cite "Axiom 8 (Ground-Truth Substrate)". Same pattern as the `chat-surface` → `feed-surface` rename (ADR-259), where historical ADR banners stayed and only new authorship inherited the new vocabulary.

## Three-instance illustration (replaces the current "Three asymmetric bets" section)

The axiom body's current "Three asymmetric bets money-truth substrate enables" subsection is alpha-trader-locked. Replace with a three-instance illustration that shows the kernel concept holding across domains:

### Instance 1 — alpha-trader (money-truth)

- **Ground-truth signal**: reconciled order fills + position state from Alpaca
- **Substrate home**: `/workspace/context/{domain}/_money_truth.md`
- **Latency**: minutes to hours
- **Attribution**: clean per-trade
- **Operator wince signal**: P&L decline
- **Reviewer calibration**: capital-EV reasoning on every proposal

### Instance 2 — alpha-commerce (revenue-truth)

- **Ground-truth signal**: subscription events, refunds, payment confirmations from Lemon Squeezy
- **Substrate home**: `/workspace/context/revenue/_money_truth.md` (per ADR-183 + ADR-184)
- **Latency**: minutes (event) to weeks (cohort retention)
- **Attribution**: per-product, weaker per-action
- **Operator wince signal**: MRR decline, churn spike
- **Reviewer calibration**: product-decision EV reasoning

### Instance 3 — alpha-author (multi-signal ground-truth)

- **Ground-truth signal**: composite of (a) internal substrate coherence — Reviewer-detected corpus contradictions, voice drift; (b) audience signal when present — engagement deltas, subscriber cohort behavior; (c) revenue signal when present — MRR, churn
- **Substrate home**: TBD in ADR-283. Multi-signal substrate, likely `/workspace/context/{domain}/_signal.md` or compound per-signal files
- **Latency**: continuous (coherence) to weeks (audience) to months (revenue)
- **Attribution**: cohort-level for audience, sparse-attribution for revenue, per-revision for coherence
- **Operator wince signal**: voice-drift detection, audience defection, revenue decline, scene-12-contradicts-scene-5
- **Reviewer calibration**: editorial-discipline reasoning across corpus

The illustration shows: **the axiom holds. The signal shape varies by domain. The architectural property is invariant.**

## Cascade plan (single commit)

This is a docs-only rename. Single commit, no migration, no code change, no schema impact.

1. **`docs/architecture/FOUNDATIONS.md`** — Axiom 8 heading rewrite, body restructure (kernel property + three-instance illustration replacing alpha-trader-locked subsections), version-history entry appended.
2. **`docs/architecture/GLOSSARY.md`** — add `Ground-truth substrate` axiom-level entry; existing `Outcome` / `_money_truth.md` / `Money-Truth` entries gain instance-pointer sentence.
3. **`docs/architecture/LAYER-MAPPING.md`** — literal substitution `Money-Truth` → `Ground-Truth Substrate` in axiom citations.
4. **`docs/adr/ADR-282-axiom-8-ground-truth-rename.md`** — this file.

Five-step grep gate before commit:

```
grep -rn "Axiom 8 (Money-Truth)" docs/architecture/   # should match in legacy only
grep -rn "Axiom 8 (Money-Truth)" docs/adr/             # historical only — do not edit
grep -rn "Axiom 8 (Ground-Truth Substrate)" docs/      # new vocabulary, used in new ADRs
grep -rn "money-truth" docs/architecture/FOUNDATIONS.md # instance-level mentions only
grep -rn "_money_truth.md" api/services/               # unchanged
```

The first three searches verify the cascade. The fourth verifies FOUNDATIONS no longer treats `money-truth` as kernel-level vocabulary (only as alpha-trader instance pointer). The fifth verifies no code rename occurred.

## What this enables

1. **ADR-283 (alpha-author bundle)** can be authored against a clean axiom without inheriting alpha-trader-locked framing. The multi-signal ground-truth shape alpha-author needs is now axiomatically legitimate, not a special case.
2. **Future bundles** (alpha-investor, alpha-advisor, alpha-recruiter, alpha-seller if any of these ever ship) inherit the corrected framing natively. Each declares its own ground-truth instance shape; the kernel doesn't presume monetary signal.
3. **THESIS commitment 3 + FOUNDATIONS Axiom 8 stop drifting.** Both now use `ground-truth` as the kernel-level concept and `money-truth` as alpha-trader's instance. Cross-doc vocabulary coherence.

## What this explicitly does not do

- Does not rename `_money_truth.md`. The file is alpha-trader's substrate file. Renaming would be performative without architectural benefit and would trigger code churn for no semantic gain.
- Does not rename `services/outcomes/`. The outcomes service is alpha-trader-instance code (Trading + Commerce OutcomeProviders).
- Does not amend ADR-195 v2 or its phased plan. Money-truth substrate as alpha-trader's instantiation is unchanged.
- Does not introduce new substrate shapes. alpha-author's ground-truth substrate is designed in ADR-283, not here.
- Does not impact the `_performance.md` substrate (which is reviewer-seat-level calibration, distinct from per-domain `_money_truth.md` — both names survive unchanged).

## Status check

- **Implementation effort**: ~1 hour of doc edits + grep gate verification.
- **Risk**: low. Docs-only, no code, no migration, no test impact.
- **Cascade**: 3 canonical doc files + 1 new ADR. No code, no schema, no test gate beyond grep verification.
- **Unblocks**: ADR-283 (alpha-author bundle authoring).
