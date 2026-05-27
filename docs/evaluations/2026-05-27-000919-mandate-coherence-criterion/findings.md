# Mandate-Coherence Criterion Declaration + Pre-Measurement Baseline

**Captured**: 2026-05-27T00:09Z. Hat-B evaluation.

**Shape**: criterion-declaration only. No measurement yet — post-deploy substrate population is too sparse (24h post-ADR-303 deploy, 7 successful judgment wakes total — see [`../2026-05-26-163000-posture-criterion-declaration/findings.md` §4](../2026-05-26-163000-posture-criterion-declaration/findings.md) for the immediate post-deploy snapshot). This folder establishes the second criterion that will measure the post-deploy population once it accumulates.

**Why this folder, why now**: the immediate-prior evaluation declared the **visibility-compliance criterion** (every judgment wake produces SOME operator-readable substrate, per ADR-303 D1/D2 posture cells; target: 95%+ operator-visibility ratio). That criterion measures whether the system honors its substrate-write contracts.

A second, distinct question goes unmeasured under the visibility criterion: **is the Reviewer's substrate-write actually about the operation's mandate?** A `standing_intent.md` that says *"scheduler silence detected, awaiting clarification"* satisfies the visibility-compliance criterion (it's a reviewer-attributed write within the wake window), but says nothing about the trading mandate. The visibility criterion would score it as adherent; the operator reading it learns the system noticed itself but learns nothing about whether the system is advancing the operation.

The companion criterion this evaluation declares — **mandate-coherence** — measures the second question. It does not replace the visibility criterion; the two compose. A wake can be visibility-compliant AND mandate-coherent (P1 ideal), visibility-compliant AND mandate-incoherent (substrate-write happened but said nothing mandate-relevant), or visibility-non-compliant entirely (the silent-wake class ADR-303 addresses structurally).

The motivating operator observation (2026-05-27 morning session): *"full autonomy is not yet fully stable and functional in full. we're getting hints of it working on and off, but collectively with qualitative substrate writes (not just standing intent and/or simply wakes), its not really working with awareness to a mandate and 'really working'."* This evaluation formalizes that observation into a measurable criterion.

---

## §1 Criterion declaration

### §1.1 Canon clause being measured against

Primary: **persona-frame `_compute_standing_intent_contract` lines 559-572** (per `api/agents/reviewer_agent.py` at commit `bc40aff`) — the MANDATE-citation discipline clause:

> When MANDATE.md content is load-bearing in your reasoning, cite it by name. The operator's MANDATE declares the operation's primary action + success criteria; when your "What I'm watching for" or "What would change my next move" derives from a MANDATE clause (a declared success criterion, a boundary condition, an edge hypothesis, a rule of operation), name `MANDATE.md` in the entry alongside the substrate-evidence files you cite. This makes the mandate→reasoning chain auditable: the operator reading standing_intent.md can trace your forward-looking judgment back to the declaration that authorized it. Generic "watching for drift" without a mandate-clause anchor — when one would apply — leaves the judgment ungrounded.

Secondary: **THESIS Commitment 1** (operator-authored mandate as the operation's standing intent) + **FOUNDATIONS Derived Principle 21 final clause** ("driven by operator-authored mandate"). The visibility criterion validates that the Reviewer writes; the mandate-coherence criterion validates that what it writes serves the operator's declared operation.

Tertiary (negative bound): **persona-frame `_compute_judgment_log_contract`** (whichever section enumerates judgment_log.md schema) — judgment_log entries enumerate decisions; mandate-coherence asks whether those decisions reference the MANDATE.md frame they're decided against.

**This criterion is NOT a duplicate of visibility-compliance.** The visibility criterion asks *did substrate get written?* The mandate-coherence criterion asks *is the substrate that got written about the operation the operator declared?*

### §1.2 Operationalization — how mandate-coherence maps to substrate signals

A judgment-wake cycle's substrate output (standing_intent.md revision + judgment_log.md revision + any directly-authored workspace edits within the wake window) is classified along two orthogonal axes:

**Axis A — Mandate reference presence:**
- **A1 (explicit)**: substrate text contains `MANDATE.md` as a named cited file OR quotes/paraphrases a specific MANDATE clause (Primary Action statement, declared success criterion, boundary condition, rule of operation).
- **A2 (implicit-via-substrate)**: substrate text cites a downstream substrate file (`_money_truth.md`, `_voice.md`, `_risk.md`, `principles.md`, `_universe.yaml`, etc.) which by canon derives from the MANDATE's framing. Substrate-chain reasoning, mandate-ungrounded surface text.
- **A3 (ungrounded)**: substrate text contains no MANDATE reference and no substrate-file reference. Generic reasoning ("watching for drift", "monitoring conditions", "scheduler silence detected") with no mandate-chain.

**Axis B — Operational advancement:**
- **B1 (advances)**: substrate text identifies a specific forward action, condition, or framework refinement that — if executed — would advance one of the MANDATE's declared success criteria. Example for alpha-trader: *"watching for signal-3 to fire on NVDA when RSI returns to 60 — current edge hypothesis from MANDATE.md is mean-reversion on oversold growth names"* is B1. Example for alpha-author: *"watching for the IR-narrative thread to mature past 3 weekly entries before pre-shipping — MANDATE declares 'distillation depth over rate-of-publication'"* is B1.
- **B2 (housekeeps)**: substrate text reports system-state observation, scheduler diagnostics, calibration notes, or session-continuity material with no forward-action implication for the mandate. Example: *"scheduler silence detected, 4-day gap, awaiting operator clarification"* is B2 — accurate, visibility-compliant, useful for system maintenance, but does not advance the trading mandate.
- **B3 (declines-with-reasoning)**: substrate text explicitly chooses not to act, citing the MANDATE's frame for why. Example: *"no actionable signal-evaluation today — MANDATE.md's declared risk-envelope (max 5 positions, 3% per position) is already at 4/5 and current candidates fall outside the framework's edge thresholds. Standing down."* B3 is mandate-coherent inaction.

**Cell partition** (A × B):

| | A1 (explicit) | A2 (implicit) | A3 (ungrounded) |
|---|---|---|---|
| **B1 (advances)** | M1-IDEAL | M2 | M3 |
| **B2 (housekeeps)** | M4 | M5 | **M6-DRIFT** |
| **B3 (declines)** | M7-IDEAL | M8 | M9 |

**Key shape:** M1 and M7 are the two mandate-coherent ideal cells. M6 is the drift class — substrate writes that are visibility-compliant but mandate-blind. M3/M5/M9 are weak cells — substrate is doing some work but doesn't ground itself in the operator's frame. M2/M4/M8 are acceptable middle cells.

**Detection rule (deterministic, classifiable post-hoc):**

```sql
-- Pseudo-query shape (full SQL in §3.1 when measurement runs)
WITH judgment_wake_substrate AS (
  SELECT
    e.id AS wake_id,
    e.user_id, e.slug, e.created_at,
    string_agg(v.content, E'\n---\n') AS substrate_text
  FROM execution_events e
  JOIN workspace_file_versions v
    ON v.user_id = e.user_id
    AND v.authored_by LIKE 'reviewer:%'
    AND v.created_at BETWEEN e.created_at - interval '15 min' AND e.created_at + interval '1 min'
  WHERE e.mode = 'judgment' AND e.status = 'success'
  GROUP BY e.id, e.user_id, e.slug, e.created_at
)
SELECT
  wake_id, user_id, slug,
  CASE
    WHEN substrate_text ~ '\\bMANDATE\\.md\\b' THEN 'A1'
    WHEN substrate_text ~ '\\b(_money_truth|_voice|_risk|principles|_universe|_account|_regime|_editorial)' THEN 'A2'
    ELSE 'A3'
  END AS axis_a,
  -- Axis B requires qualitative read; tag manually
  ...
FROM judgment_wake_substrate;
```

Axis A is fully automatable. Axis B requires a human read (or a separate LLM-judge pass, deferred — not introduced as system canon, would live in `api/eval/` if added). The two-axis classification is enough to produce a cell-distribution; full automation is a v2 question.

### §1.3 Expected posture per cell

The visibility criterion targets 95%+ on operator-visible substrate. The mandate-coherence criterion targets a different distribution:

| Cell | Expected fraction | Interpretation |
|---|---|---|
| **M1-IDEAL** (explicit mandate cite, advances) | **40-60%** of P1 wakes | The Reviewer is reasoning against the mandate and identifying forward action. Highest-value cell for autonomy validation. |
| **M7-IDEAL** (explicit mandate cite, declines) | **15-25%** of P2 wakes | Mandate-coherent inaction. The Reviewer cites the MANDATE frame to explain why no action warrants. Equally valuable as M1. |
| **M2 / M4** (explicit cite, weaker B-axis) | **10-15%** combined | Substrate cite present but action-implication soft. Acceptable middle. |
| **M5 / M8** (implicit-via-substrate, weaker B) | **10-15%** combined | Substrate-chain reasoning. Operationally fine but suggests persona-frame could tighten the explicit-cite muscle. |
| **M3 / M9** (ungrounded, claims advance/decline) | **<10%** combined | Forward-action language without grounding. Operator can't audit the mandate→reasoning chain. Weak. |
| **M6-DRIFT** (ungrounded, housekeeps) | **<5%** target | The thesis-driven class. Visibility-compliant but mandate-blind. Persistent M6 = full autonomy is structurally working but mandate-coherently broken. This cell is the load-bearing one to drive to near-zero. |

**Aggregate target**: M1 + M7 ≥ 55% of all judgment wakes producing reviewer-attributed substrate. M6 ≤ 5%. Total mandate-coherent (any A1 cell) ≥ 65%.

**Composition with visibility criterion**:
- Visibility 95% × Mandate-coherent 65% = autonomous loop functioning at both layers (~60% of all judgment wakes).
- Visibility 95% × Mandate-coherent 25% = autonomous loop is **shape-correct but content-hollow**. The substrate accumulates but doesn't advance the operation. This is the failure mode the operator's thesis predicts.
- Visibility 55% × Mandate-coherent 95% (of the 55%) = pre-ADR-303 baseline — when the Reviewer wrote, it wrote about the mandate, but it wrote too rarely.

### §1.4 Pre-flight criterion audit

**Q1**: Does the criterion cover all legitimate behaviors?

Yes — the 3×3 A×B cell partition is exhaustive over substrate-write outcomes. Every reviewer-attributed substrate write falls into exactly one cell.

**Q2**: Does it over-broadly conflate distinct postures?

One known concern: **back-office substrate-maintenance wakes are legitimately B2 (housekeep)**. `outcome-reconciliation` and `track-account`-style recurrences fold platform fills into `_money_truth.md` — they're maintenance by design, not mandate-advancement. The criterion should be applied to judgment-mode wakes only (filter: `e.mode = 'judgment'`), and within judgment-mode wakes, M6 should be near-zero. If applied to mechanical-mode wakes, M6 inflates artificially.

Second concern: **persona difference matters**. alpha-trader's MANDATE has crisp Primary Action (submit pair-trade orders) + explicit success criteria (expectancy R, win rate). alpha-author's MANDATE has softer success criteria (corpus coherence, IR-narrative distillation). The 40-60% M1 target may be too aggressive for alpha-author where housekeep-shaped wakes are more legitimate. Per-persona baselines may diverge; the criterion is the same but the target ratios may need persona-specific tuning after first measurement.

**Q3**: Are there cases where canon doesn't yet have a clear expected behavior?

YES, three cases worth naming:

- **Substrate-chain reasoning (A2) vs explicit cite (A1) — which is "better"?** Persona-frame lines 559-572 say "name MANDATE.md alongside the substrate-evidence files you cite" — suggesting both should appear. But operators may find pure-substrate-chain reasoning (A2) more useful when MANDATE is the unspoken backdrop of every substrate file. The criterion currently treats A1 as the gold standard; if operator feedback says A2-rich reasoning is preferable for some slugs, the criterion needs revision.

- **The B3 (declines-with-reasoning) cell**: ADR-303 D1 names P2 as "decided-nothing-material" — a legitimate posture, not failure. Mandate-coherent P2 = B3 cell with A1 grounding = M7. The criterion treats M7 as ideal alongside M1. But the persona-frame doesn't yet have explicit prescription for "when standing down, cite the MANDATE frame for why" — that's an implication of the broader mandate-citation discipline but not stated as a separate contract. **If M7 underperforms in first measurement, the right move is to extend the persona-frame standing-intent template to call out mandate-cited declines explicitly.**

- **What about wakes whose substrate cites OCCUPANT.md, IDENTITY.md, AUTONOMY.md, or principles.md but not MANDATE.md?** These are governance/identity-layer cites, not mandate cites. The criterion treats them as A2 (implicit-via-substrate) because principles derive from MANDATE per ADR-295. But if a Reviewer reasons primarily against principles.md (its own framework) without ever referencing the MANDATE that authorized those principles, that's a subtle drift — the Reviewer is reasoning against its own captured frame, not the operator's. Worth watching across measurements.

**Q4**: Are the criterion's load-bearing claims grounded in canon citations rather than vibes?

Yes — every cell maps to specific text in persona-frame `_compute_standing_intent_contract` (lines 559-572) or to FOUNDATIONS Derived Principle 21. The MANDATE-citation discipline is named persona-frame canon; the cell partition operationalizes it. The expected-fraction percentages are starting-point heuristics derived from the canon-stated intent ("the operator should be able to trace the mandate→reasoning chain"), not measurements — they will be calibrated against first real measurement and may need revision.

**Verdict on criterion well-formedness**: Sound enough to measure against, with three forward-evolution questions tracked. The criterion is **complementary** to the visibility criterion, not a replacement. Both run on the same wake population; their joint distribution is the autonomy-quality signal.

---

## §2 What this evaluation does NOT do

Five explicit non-claims:

1. **Does NOT measure adherence yet.** Post-deploy substrate population (24h since `bc40aff` deploy) is too sparse for either criterion to produce statistically meaningful measurement. First measurement waits ≥1 week per the visibility criterion's §4 plan.

2. **Does NOT replace the visibility-compliance criterion.** The two criteria measure orthogonal properties of the same substrate writes. The visibility criterion asks "did the wake produce ANY operator-readable artifact?" The mandate-coherence criterion asks "is the produced artifact about the operation?" Both must pass for autonomy to be working as canon claims.

3. **Does NOT validate that the persona-frame's mandate-citation discipline is sufficient.** If first measurement shows M6 drift at materially-higher-than-target fractions, the diagnosis is "persona-frame text under-specifies the citation discipline" or "the model isn't internalizing the MANDATE.md-cite muscle" or "the wake envelope's MANDATE.md preamble is too distant from the standing_intent.md-write moment." Resolution would be a separate Hat-A ADR amending the persona-frame.

4. **Does NOT introduce a system-side concept.** Mandate-coherence is a developer-side measurement criterion. The system already has the mandate-citation discipline in persona-frame canon. This evaluation measures whether that discipline produces the predicted behavior — it does not invent a new in-system entity.

5. **Does NOT specify pass/fail thresholds with finality.** Expected fractions in §1.3 are starting-point heuristics. First measurement will calibrate them against persona-specific reality. The criterion's discipline is the cell partition + measurement protocol; the exact percentages may evolve through observation, like the visibility criterion's denylist evolution.

---

## §3 Pre-measurement baseline — substrate inventory

No measurement yet (per §2.1). What this section provides instead: an inventory of the substrate population the first measurement will run against, so the post-measurement findings have a clean anchor.

### §3.1 Active workspace state (post-carve, 2026-05-27)

Two active workspaces, both clean post-deploy:

| User | Email | Program | Active recurrences | Mandate version |
|---|---|---|---|---|
| `2abf3f96` | kvkthecreator@gmail.com | alpha-trader | 3 judgment-mode (pre-market-brief, signal-evaluation, weekly-performance-review) | v2026-05-20.1 (bundle-versioned) |
| `0b7a852d` | yarnnn-author@yarnnn.com | alpha-author | 5 judgment-mode (outcome-reconciliation, corpus-coherence-check, revision-audit, weekly-corpus-review, quarterly-voice-audit) | v2026-05-20.1 (bundle-versioned) |

Six workspaces paused (substrate preserved, recurrences not firing) — see `docs/evaluations/sessions/` for cross-session continuity threads if revisiting later.

### §3.2 Predicted weekly judgment-wake population

Conservative estimate (based on the schedule + market-day distribution):
- **kvkthecreator/alpha-trader**: ~10 weekly judgment wakes (2 daily × 5 trading days = 10, plus weekly-performance-review = 11/week)
- **yarnnn-author**: ~8 weekly judgment wakes (daily outcome-reconciliation = 7, plus weekly + biweekly recurrences = ~10/week)
- **Total combined**: ~20 judgment wakes/week.

After ~10 days of accumulation, the population should reach n ≥ ~30 — comfortable for cell-distribution reading per the visibility criterion's stated n ≥ 27 baseline.

### §3.3 Substrate baseline at criterion-declaration time

```sql
-- Run at 2026-05-27T00:09Z (this folder's capture time)
SELECT
  u.email,
  COUNT(*) FILTER (WHERE wfv.authored_by LIKE 'reviewer:%' AND wfv.created_at >= '2026-05-26 05:22:00 UTC') AS post_deploy_reviewer_writes,
  COUNT(*) FILTER (WHERE wfv.authored_by LIKE 'dispatcher:%' AND wfv.created_at >= '2026-05-26 05:22:00 UTC') AS post_deploy_dispatcher_writes,
  COUNT(*) FILTER (WHERE wfv.authored_by LIKE 'reviewer:%') AS lifetime_reviewer_writes
FROM auth.users u
LEFT JOIN workspace_file_versions wfv ON wfv.user_id = u.id
WHERE u.email IN ('kvkthecreator@gmail.com', 'yarnnn-author@yarnnn.com')
GROUP BY u.email;
```

Result at capture: kvkthecreator 2 post-deploy reviewer writes (judgment_log + per-section writes from 13:01 UTC cycle); yarnnn-author 0 post-deploy reviewer writes (recurrences haven't fired since deploy). Zero dispatcher writes either workspace — Phase 3 helpers have not been exercised by a real silent-exit yet.

---

## §4 What the first measurement will measure

After ≥1 week of substrate accumulation (target: ~2026-06-03+), the first measurement runs the Axis-A SQL query above on the post-deploy population, then a human reads the substrate text and tags Axis B per cycle. Outputs:

**Per-workspace cell distribution**:
- M1/M2/M3/M4/M5/M6/M7/M8/M9 wakes count per workspace
- Percentage to target distribution (§1.3 table)
- M6-DRIFT count specifically called out

**Composite-with-visibility readout**:
- Visibility-compliance rate (from co-running visibility criterion's §4 plan re-measurement)
- Mandate-coherence rate (M1+M7 / total wakes)
- Joint distribution (visibility × mandate-coherence cells)

**Per-slug breakdown**:
- Does mandate-coherence vary by slug? Are some slugs (e.g., `pre-market-brief`) more naturally A1-eliciting than others (e.g., `outcome-reconciliation`)?

**Per-program comparison**:
- alpha-trader vs alpha-author: same persona-frame, different MANDATEs, different program-shaped substrate. Is mandate-coherence persona-portable, or does the trader's crisp Primary Action elicit different reasoning shape than the author's distillation-depth criteria?

**Drift remediation hypotheses**:
- If M6 high: persona-frame mandate-citation muscle insufficient → propose Hat-A amendment (tighter prescription, in-cycle reminder, etc.).
- If M3 high but M6 low: Reviewer reasons toward action but doesn't ground in mandate → propose stricter judgment_log.md schema requiring mandate-cite.
- If A2-heavy with low A1: substrate-chain reasoning dominates, MANDATE-direct cite is rare → may indicate the wake envelope's MANDATE preamble is structurally distant from the substrate text-generation moment; consider re-positioning.

---

## §5 Discipline notes — what this evaluation is for

This folder establishes the **second of two co-running criteria** for the post-deploy autonomy-quality measurement:

1. **Visibility-compliance** (declared `2026-05-26-163000`): does the autonomous loop produce operator-visible substrate? Measures the structural pipeline.
2. **Mandate-coherence** (this folder): does the produced substrate advance the operator's declared operation? Measures the substantive content.

Both criteria are read together. A system that scores 95% on visibility but 25% on mandate-coherence is autonomous-in-shape, not autonomous-in-substance. A system that scores 65% on visibility but 95% on mandate-coherence (within the 65%) is content-rich but pipeline-sparse — pre-ADR-303 was this. The target post-deploy state is 95% visibility AND 65%+ mandate-coherence simultaneously.

This folder also enacts the discipline (per `docs/evaluations/README.md` §"The criterion-declaration discipline") of declaring a criterion before measurement when the criterion itself is non-trivial. The visibility criterion was structurally implied by ADR-303; the mandate-coherence criterion is implied by FOUNDATIONS Derived Principle 21's "driven by operator-authored mandate" clause but had no operationalization until this folder.

If first measurement reveals the criterion is mis-formed (e.g., per-persona targets diverge by more than 30 percentage points), the right move is amendment of THIS criterion (cell partition adjustment, per-persona target tables) before re-running. Criterion-revision is itself a Hat-B activity; only canon changes derived from criterion findings flow to Hat-A.

---

## §6 Cross-references

- Companion criterion (visibility-compliance): [`../2026-05-26-163000-posture-criterion-declaration/findings.md`](../2026-05-26-163000-posture-criterion-declaration/) — the two criteria are siblings and compose.
- Persona-frame canon clause being measured: `api/agents/reviewer_agent.py` `_compute_standing_intent_contract` lines 559-572 (MANDATE-citation discipline) at commit `bc40aff`.
- FOUNDATIONS Derived Principle 21 final clause: "driven by operator-authored mandate" — the canonical claim this criterion validates.
- Driving operator observation: 2026-05-27 session — *"with qualitative substrate writes... its not really working with awareness to a mandate and 'really working'."*
- Workspace carve enabling clean measurement: same-session DB changes — 35 recurrences paused across 4 workspaces, 8 cold accounts purged, 8 trader recurrences paused on kvk to slow pacing, leaving 2 active workspaces with 8 combined active judgment-mode recurrences.

---

## Status

**OPEN** as the canonical mandate-coherence criterion. Lock at "Implemented" only after first measurement against ≥1 week of post-deploy substrate accumulation (estimated ~2026-06-03 earliest). The lock criterion is "measurement happened and §1.3 fractions calibrated against reality," not "system passed."

## Last updated

2026-05-27T00:09Z — initial criterion declaration. No measurement yet (sparse population).
