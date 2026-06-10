# ADR-330 — Ground-Truth Intake: Generalizing the Consequence Pipe Beyond Platform Providers

**Status:** **Proposed** (2026-06-10) — drafted for operator ratification; no code landed
**Date:** 2026-06-10
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon — real-operator-facing)

> **Discourse base:** [`reality-in-current-standing-and-setup-as-rendering-2026-06-10.md`](../analysis/reality-in-current-standing-and-setup-as-rendering-2026-06-10.md) §1–§3 (the four-flow audit + the attestation taxonomy), succeeding [`author-blindness-and-invariant-capabilities-2026-06-10.md`](../analysis/author-blindness-and-invariant-capabilities-2026-06-10.md) §3. Every receipt below was re-verified against live `api/` on 2026-06-10 (discourse capture §0). **Post-pause addendum (same day):** [`four-flow-completeness-and-program-floor-2026-06-10.md`](../analysis/four-flow-completeness-and-program-floor-2026-06-10.md) names this ADR's territory as **flow 3 — the coupling term** (the world's verdict on the operation's own acts) of the four-flow completeness model, and frames D4's conformance gate as the first instance of flow-completeness-as-bundle-conformance (the arc-3 proposal).

**Amends:**
- [ADR-195 v2](ADR-195-outcome-attribution-substrate.md) — extends the `OutcomeProvider` contract with two non-platform intake paths (operator-attested CSV, retrospective) and adds an `attestation` field to `OutcomeCandidate`. The ABC, the ledger, the reconciler, and the two platform providers (Alpaca, Lemon Squeezy) are unchanged in shape; this ADR adds providers and one field, deletes nothing.
- [ADR-282](ADR-282-axiom-8-ground-truth-rename.md) — adopts "ground-truth intake / consequence pipe" as the Axiom-8 vocabulary for what was code-named `OutcomeProvider` (Decision 5). FOUNDATIONS/GLOSSARY touch is vocabulary-only.
- [ADR-287](ADR-287-bundle-conformance-discipline.md) — alpha-author's `substrate_abi.ground_truth` declaration extends the bundle-conformance gate (Decision 4).
- [ADR-327](ADR-327-budget-and-the-self-improving-loop.md) — the calibration mirror (`mirror_calibration.py`) lights up for the second active program once alpha-author declares ground-truth; no change to the mirror code, only to what it reads.

**Preserves:** FOUNDATIONS Axioms 0–9 · Axiom 8 (Money-Truth / Ground-Truth) · [ADR-153](ADR-153-platform-content-sunset.md) (continuous-sync-into-unattributed-shadow-table stays dead — this ADR adds bounded, attributed intake, the opposite shape) · [ADR-209](ADR-209-authored-substrate.md) Authored Substrate (every row attributed) · ADR-195 v2 reconciler + ledger + filesystem money-truth persistence · the two platform providers.

---

## 1. Problem statement

YARNNN's operation runs a four-flow loop: **context in** (perception) → **work out** (acts) → **outcomes in** (reality's verdict) → **the loop** (calibration of judgment against outcomes). Flow 3 — outcomes in — is the moat: *judgment calibrated against ground truth the agent cannot author.* It is also the most thinly built.

**Receipts (live, 2026-06-10):**

- `api/services/outcomes/reconciler.py::DEFAULT_PROVIDERS` registers exactly **two** providers: `TradingOutcomeProvider()` (Alpaca) and `CommerceOutcomeProvider()` (Lemon Squeezy). There is **no manual, CSV, operator, or agent intake of any kind**.
- `api/services/outcomes/base.py::OutcomeCandidate` (TypedDict) carries no field recording **who vouched for** the outcome. Every row is implicitly platform-attested because the only two producers are platform APIs.
- `docs/programs/alpha-author/MANIFEST.yaml` (`status: active`) declares **no** `substrate_abi.ground_truth` — even though its oracle profile (`shape: multi_signal_coherence`) is fully specified and its ground-truth file `operation/authored/_signal.md` **already exists and already accumulates** (declared in `path_zones[*].accumulating_files`, written by coherence-check + reconciliation, surfaced in the wake envelope as `corpus_signal_md`). Because the `substrate_abi.ground_truth` *declaration* is the one missing piece, `api/services/bundle_reader.py::get_ground_truth_for_workspace` returns `None` for alpha-author, so `api/services/primitives/mirror_calibration.py` omits its entire "Ground truth" section — **the second active program's self-improving loop is structurally dark** (cadence-history-only, no outcome basis) despite the substrate being present. This is a one-line declaration gap, not a missing-machinery gap.

Two consequences:

**Problem A — the loop only exists for two verticals.** Any operator whose ground truth isn't an Alpaca or Lemon Squeezy API has no door into flow 3. The universal fallback (the operator hands the system their own records) does not exist. This blocks cold-start calibration for every horizontal user and for alpha-author specifically.

**Problem B — generalizing flow 3 silently dilutes the moat unless attestation is explicit.** The moat claim is "ground truth the agent cannot author." The moment intake admits operator-imported CSVs and agent-asserted numbers, that claim splinters into three strengths (§3). Without a per-row attestation stamp, calibration would treat an agent-scraped newsletter stat with the same authority as an Alpaca fill — and the calibrated thing would be participating in producing its own evidence. The honest version of the moat requires every outcome row to carry **who attested it**.

---

## 2. Decision summary

| # | Decision | Shape |
|---|---|---|
| **D1** | **One intake pipe, two new producers.** Add a manual/operator CSV-import provider and a retrospective-import provider — both emit `OutcomeCandidate` through the existing reconciler + ledger. No parallel ingestion path; no new persistence. | Backend |
| **D2** | **`attestation` field on every `OutcomeCandidate`**, enum `platform \| operator \| agent`. **Label-first** (calibration records and surfaces the level; weighting is a follow-on when evidence demands). | Backend + canon |
| **D3** | **Retrospective mode** is the same intake with `executed_at` in the past + `retrospective: true`. Historical rows enter the domain's ground-truth file (`_money_truth.md` for trading, `_signal.md` for authored — the per-domain ground-truth substrate) segmented, not silently blended, so the calibration mirror can distinguish backfilled history from live outcomes. | Backend |
| **D4** | **alpha-author declares `substrate_abi.ground_truth`** = `operation/authored/_signal.md` (the file already exists and already accumulates — only the declaration is missing). Extends `api/test_adr287_bundle_conformance.py` same commit. | Bundle |
| **D5** | **Vocabulary rename to "ground-truth intake / consequence pipe"** at the canon layer (FOUNDATIONS Axiom 8 / GLOSSARY / docstrings). The Python class names keep `OutcomeProvider`/`OutcomeCandidate` (renaming the class is churn with no behavioral payoff; the *concept* misled, not the symbol). Singular implementation — no alias layer either way. | Canon (+ docstrings) |

**Anti-goals (binding, stated so future sessions don't re-open them):**

- **No continuous-sync revival.** ADR-153 stands. CSV/manual/retrospective intake is a *bounded invocation* — addressed trigger, attributed write, no background poller, no shadow content table.
- **No per-vertical API connectors yet.** CSV/manual is the **universal fallback**. Connectors (a Stripe outcome provider, a Substack stats provider) are bundle-side follow-ons, each its own small ADR — not this one.
- **No coverage/freshness tracking state.** The substrate is the record (discourse capture §3 bright line). What's been brought in = the rows that exist in `_money_truth.md`, attributed and dated. No `_intake_tracker.md`, no `sync_registry` rebirth.

---

## 3. Attestation — who vouches for an outcome row (D2)

Generalizing flow 3 requires naming, per row, the strength of the vouch:

| Level (`attestation`) | Voucher | Strength | Moat status | Example |
|---|---|---|---|---|
| `platform` | External API independent of operator **and** agent | **Gold** | Fully supports "judged against reality" | Alpaca fill, Lemon Squeezy order |
| `operator` | The operator's own import (CSV, manual entry, operator-proxy) | **Strong** | Agent still can't fake it. Operator can (incl. unconsciously — cherry-picked rows). Supports "judged against **your own records**." | Trade-log CSV, deal-history import |
| `agent` | An agent read/asserted the number | **Weak** | The calibrated thing participates in producing the evidence. Needs corroboration; labeled as such. | Agent scrapes a newsletter stats page |

**How each level preserves or qualifies the moat (the honest accounting D2 requires):**

- `platform` — the moat claim is unqualified. Neither the operator nor the agent authored the number; an independent system did.
- `operator` — the moat claim narrows from "judged against reality" to "judged against **your own records**." The *agent* still cannot author it (that's preserved — the agent is calibrated, not vouching). The operator can bias it. This is a real and acceptable qualification: an operator who lies to their own calibration loop only fools themselves, and the system never claimed to police the operator.
- `agent` — the moat claim is **conditional**. An agent-asserted outcome is admissible only as labeled, corroboration-seeking evidence. Calibration must never let an `agent`-attested row silently raise a recurrence's confidence the way a `platform` row does. Label-first (D2) makes this visible immediately; weighting (deferred) makes it enforced.

**Decision: label-first, not weight-first.** The mirror records and surfaces `attestation` on every row; the Reviewer reads it as part of its judgment context. Calibration *weighting* by attestation (e.g., agent-attested rows contribute fractional confidence) is a **follow-on** — added when evidence shows label-only is insufficient, not pre-built. This keeps the loop honest now (the strength is never hidden) without prematurely encoding a weighting curve we can't yet calibrate.

**Spec requirement:** every producer stamps `attestation` on every `OutcomeCandidate`. The two platform providers stamp `platform`. The CSV/manual provider stamps `operator` (or `operator-proxy` when fired through ADR-294's proxy — carried as a sub-label, not a fourth enum value). Any future agent-harvest-of-outcomes provider stamps `agent`.

---

## 4. D1 — One intake pipe, two new producers

### 4.1 Manual / operator CSV-import provider

A new `OperatorOutcomeProvider` (working name) implementing the existing `OutcomeProvider` ABC. It does **not** poll a platform; it reads a one-shot, operator-supplied structured import (CSV or equivalent) staged via the upload path (ADR-249 single-file → `/workspace/uploads/`), parses rows into `OutcomeCandidate` dicts, and returns them. The reconciler folds them through `ledger.fold_outcome_candidates` exactly as it does platform candidates — **same ledger, same idempotency, same money-truth file.**

- **Idempotency:** each row's `outcome_metadata` carries an operator-supplied or derived key (`import_batch_id` + row-hash, or an operator-provided external id). The ledger's existing `(user_id, action_type, metadata_key)` dedup applies unchanged — re-importing the same CSV is a no-op, not a double-count.
- **`proposal_id` linking (optional):** if a CSV row names a YARNNN `proposal_id` (the operator reconciling a past proposal against its real outcome), the provider sets it, elevating `reconciliation_confidence` to `high` per the existing ABC contract. Most operator imports will have no proposal link (pre-YARNNN history) and that's fine.
- **`attestation`:** `operator`.
- **Trigger shape:** addressed invocation — the operator fires "reconcile this import," the provider runs once, narrative entry + appended substrate are its only trace. **Not** a registered always-on provider in `DEFAULT_PROVIDERS` (that list stays platform-only for the daily back-office reconciliation); the operator provider is invoked on demand against a named import. *(Implementation note: whether this is a `providers=[OperatorOutcomeProvider(import_path=…)]` call into the existing `reconcile_user(providers=…)` override or a thin dedicated entrypoint is a Phase-1 code decision; both route through the same ledger — no parallel path either way.)*

### 4.2 The single pipe (why this is not a parallel ingestion path)

`reconcile_user(client, user_id, providers=…)` already accepts a `providers` override (ABC contract, base.py). The operator and retrospective providers are **additional implementers of the same ABC**, folded by the **same** `fold_outcome_candidates`, persisted to the **same** `_money_truth.md`. There is exactly one intake pipe; D1 widens its set of producers. No new table, no new persistence helper, no second reconciler.

---

## 5. D3 — Retrospective mode

The same intake, pointed at the past. The cold-start / calibration-backfill answer (the ADR-320 seam: a new operator arrives with a history of decisions + outcomes that predate YARNNN).

- **Distinguishing historical rows:** `executed_at` is in the past (already a candidate field) **plus** a `retrospective: bool` flag on `OutcomeCandidate` (new, defaults `False`). The flag is explicit because "old `executed_at`" alone is ambiguous (a platform reconciliation can legitimately surface a fill from last week); `retrospective: true` declares *operator intent to backfill history*, which the mirror treats differently.
- **Entry into `_money_truth.md`:** retrospective rows are **segmented**, not blended. The ledger writes them under a distinct frontmatter bucket (e.g., a `retrospective: true` marker on the row, or a dedicated `## Backfilled history` section) so the calibration mirror's head-read can present *"live outcomes since activation"* separately from *"backfilled pre-YARNNN history."* Segmenting protects the live loop from being swamped by (and the operator from misreading) a large historical dump as if it were recent performance.
- **Calibration consumption:** the mirror surfaces both segments but labels them. **Decision: retrospective rows are segmented + labeled, not weighted differently at first** (same label-first posture as attestation). Whether the Reviewer's cadence judgment should discount historical rows is a calibration question to answer with evidence, not pre-encode.

Retrospective rows are almost always `attestation: operator` (the operator is importing their own history); a retrospective import of platform-verifiable history could be `platform` if pulled through a platform provider against a historical window. The two flags are orthogonal — `attestation` says *who vouched*, `retrospective` says *is this backfill*.

---

## 6. D4 — alpha-author ground truth

alpha-author is `status: active` and its loop is dark. The audit (§1) found the substrate is **already present** — `operation/authored/_signal.md` is declared in the MANIFEST's `path_zones[*].accumulating_files`, written by coherence-check + reconciliation, and surfaced in the wake envelope as `corpus_signal_md`. The oracle profile is fully specified (`oracle.shape: multi_signal_coherence`, `oracle.source: corpus_coherence + audience_engagement + commerce_revenue`). **The one missing piece is the `substrate_abi.ground_truth` pointer.** So D4 is a one-line declaration, plus a gate:

1. **Declare `substrate_abi.ground_truth`** in `docs/programs/alpha-author/MANIFEST.yaml`:
   ```yaml
   substrate_abi:
     ground_truth: operation/authored/_signal.md
   ```
   `_signal.md` (not `_money_truth.md`) is the canonical filename per the MANIFEST's own comment + ADR-282/ADR-283 D4: the kernel-level concept is "ground-truth substrate" (Axiom 8); the alpha-author instance-level filename is `_signal.md` because its ground truth is multi-signal coherence, not a single P&L number. (alpha-trader's instance filename `_money_truth.md` is the trading-specific name for the same kernel slot.) The file lives under the already-declared `operation/authored` path zone. Once declared, `get_ground_truth_for_workspace` returns it and `mirror_calibration.py` surfaces it — **no mirror code change, no new recurrence, no new writer.** The accumulation recurrence already exists.

   **Attestation for alpha-author's ground truth is mixed and must be honest:** audience-platform-pulled numbers (when an audience platform is connected) are `platform`; operator-imported newsletter stats are `operator`; agent-asserted reads are `agent`. The recurrence(s) feeding `_signal.md` stamp accordingly. This is exactly why D2 is load-bearing for the non-trading verticals — alpha-author's ground truth is *inherently* multi-attestation in a way trading's clean Alpaca fills are not. *(The signal-mix weighting — corpus coherence vs audience vs revenue — already lives in the accumulation recurrence; this ADR does not re-specify it, only points `ground_truth` at the file it already writes.)*

2. **Bundle-conformance gate.** Extend `api/test_adr287_bundle_conformance.py` in the same commit to assert alpha-author declares a `ground_truth` path and that the path falls within a declared path zone (per ADR-287 discipline). No new test file — extend the existing gate.

   *(Caveat the implementation must respect: `bundles_active_for_workspace` additionally requires a connected bundle capability for cockpit-chrome purposes. `get_ground_truth_for_workspace` iterates the same active-bundle list, so alpha-author's ground truth surfaces in the calibration mirror only for workspaces where alpha-author is active-for-workspace. This is correct — a workspace not running alpha-author shouldn't get its ground-truth declaration. The declaration is necessary and the right scope; activation is the operator's, per ADR-331.)*

---

## 7. D5 — Naming

"OutcomeProvider" misled its own architect, who read it as pipeline-**out** (work leaving) rather than reality's-verdict-**in**. The fix is at the **canon/vocabulary** layer, not the symbol layer — and it builds directly on ADR-282, which already did the substrate-noun work (established `ground-truth` as the kernel-level Axiom-8 concept, `money-truth`/`_signal.md` as instance vocabulary) and **already explicitly preserved the `OutcomeProvider` ABC class name unchanged.** ADR-330 extends that same discipline to the *flow/mechanism* nouns:

- **Canon:** FOUNDATIONS Axiom 8 + GLOSSARY gain **"ground-truth intake"** (the flow — flow 3 of the four-flow loop) and **"consequence pipe"** (the mechanism — the reconciler + providers that turn reality's verdict into substrate) as operator/architect vocabulary. This is additive to ADR-282's kernel/instance ground-truth distinction, not a re-do of it — ADR-282 named the *substrate*; ADR-330 names the *flow that fills it*. Docstrings in `outcomes/*.py` are reworded to lead with "ground-truth intake / consequence pipe" and explain the `OutcomeProvider` class name as the code-level implementer of one intake source.
- **Code:** the class names `OutcomeProvider` / `OutcomeCandidate` / `reconcile_user` **stay** — consistent with ADR-282's explicit preservation of the same symbols. Renaming touches every provider, the reconciler, the ledger, and the back-office task for zero behavioral gain and real merge-churn risk against concurrent lanes. The misleading was conceptual (the operator lacked the Axiom-8 framing), not lexical. Fixing the framing fixes the misleading.
- **Singular implementation:** no alias module, no `GroundTruthProvider = OutcomeProvider` shim. One name in code, one vocabulary in canon, an explicit docstring bridge between them.

**Same-commit docstring fix (noted in discourse capture §0):** `outcomes/base.py` docstrings still reference the dropped `action_outcomes` SQL table (ADR-195 v2 moved persistence to filesystem `_money_truth.md`). Correct the stale prose in the same commit that rewords for D5 — the TypedDict and contract are right, only the prose lags.

---

## 8. What this ADR explicitly does NOT do

- Does not revive continuous sync (ADR-153 stands).
- Does not add per-vertical API outcome connectors (CSV/manual is the universal fallback; connectors are bundle-side follow-on ADRs).
- Does not add coverage/freshness/intake-progress tracking state (the substrate is the record).
- Does not implement attestation *weighting* (label-first; weighting is a follow-on).
- Does not implement retrospective *discounting* in calibration (segment + label first).
- Does not rename the Python classes (canon vocabulary only).
- Does not build the harvest invocation or `/setup` surface — those are [ADR-331](ADR-331-setup-as-rendering.md) (the companion ADR). ADR-330 is flow 3 (outcomes in); ADR-331 is flow 1 (context in) + its rendering.

---

## 9. Render-service parity

The new providers run inside the **reconciler**, which is invoked by the daily back-office task on the **Unified Scheduler** (cron) and on demand from the **API**. No new env vars. The operator-import path reads a staged upload (existing `/workspace/uploads/` substrate) — no new storage, no new secret. **All four Render services unaffected beyond the API + Scheduler already running the reconciler.** *(Confirm at implementation: the daily `DEFAULT_PROVIDERS` reconciliation stays platform-only on the Scheduler; operator/retrospective intake is API-addressed, so the Scheduler's behavior is unchanged.)*

---

## 10. Phased implementation (for ratification — no code landed yet)

1. **Phase 1 — `attestation` field + segmenting (D2, D3 substrate).** Add `attestation: Literal["platform","operator","agent"]` and `retrospective: bool` to `OutcomeCandidate`; the two platform providers stamp `platform`; `fold_outcome_candidates` writes the fields + segments retrospective rows in `_money_truth.md`. Mirror surfaces `attestation` + segment labels. *(Backward-compatible: existing rows read as `platform`, non-retrospective.)*
2. **Phase 2 — operator CSV provider (D1).** `OperatorOutcomeProvider` + the addressed-invocation entrypoint + idempotency. Reuses the upload path for staging.
3. **Phase 3 — retrospective mode wiring (D3).** Retrospective flag honored end-to-end; mirror presents segments.
4. **Phase 4 — alpha-author ground truth (D4).** MANIFEST declaration + accumulation recurrence + ADR-287 gate extension. **This is the proof the generalization works** — the second program's loop lights up.
5. **Phase 5 — vocabulary + docstrings (D5).** FOUNDATIONS/GLOSSARY + docstring rewording + `action_outcomes` stale-prose fix.

Each phase lands green (`api/test_adr287_bundle_conformance.py` for Phase 4; a new `api/test_adr330_ground_truth_intake.py` regression gate covering the `attestation`/`retrospective` fields + operator provider + idempotency).

---

## 11. Open questions (carried, not resolved)

1. **Attestation weighting** — does calibration eventually weight by `attestation`, and with what curve? (Deferred: label-first; weight when evidence demands — §3.)
2. **Retrospective discounting** — should the Reviewer's cadence judgment discount backfilled history? (Deferred: segment + label first — §5.)
3. **Bare-kernel default program** — ~~carried open~~ **RESOLVED post-pause** (2026-06-10) by [`four-flow-completeness-and-program-floor-2026-06-10.md`](../analysis/four-flow-completeness-and-program-floor-2026-06-10.md) §3: Direction A (program-activation is the product floor, ratified 2026-06-01) is reaffirmed with its positive account — **a program IS a flow-declaration set**; a "default program" would be a declaration set with no operation behind it. No default program. A no-program workspace gets a ground-truth declaration the only way anything gets one: by activating a program that declares it.
4. **Operator-proxy attestation sub-label** — `operator-proxy:` (ADR-294) outcomes: distinct enum value or `operator` + sub-label? (Leaning sub-label to keep the enum at three; finalize at Phase 2.)
