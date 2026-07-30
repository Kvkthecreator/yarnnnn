# Retired suite manifests — trailing reference (2026-07-31)

Eight Suite-B manifests (plus one criterion protocol doc) were **retired and
deleted** on 2026-07-31, operator-directed, following the eval-layer audit
([`../2026-07-31-eval-layer-audit-FINDING.md`](../2026-07-31-eval-layer-audit-FINDING.md)):
the codebase evolved significantly past the dormant-program approach (ADR-366
governance→contract, ADR-393 mode deletion, ADR-402/403 envelope collapse,
ADR-414 judgment re-homing + pure genesis), and at audit time none of them
could fire. This document is the trailing record of each suite's setup so a
future re-cut can reference the shape without archaeology.

**Full manifests are one git command away** — every deleted file exists
verbatim at commit `90c7d67`:

```
git show 90c7d67:docs/evaluations/eval-suites/<name>.yaml
```

**Falsifier discipline** (retiring a bet means reading its verdict state
first — a deletion must never imply a verdict a thesis never earned). Each
entry below states what its thesis actually earned:

- **FALSIFIED** — fired, read, thesis failed. The deletion is downstream of a
  real verdict.
- **DECIDED-ELSEWHERE** — the question the suite existed to answer was settled
  by canon/receipts outside the suite.
- **EXERCISED, UNDECIDED** — fired at least once historically; retired for
  substrate evolution, NOT because the thesis failed. A re-hire era re-cut
  starts from the thesis, not from zero.
- **NEVER-DECIDED** — retired without its thesis ever getting a clean read.

The five shared retirement causes (details in the audit finding):
(1) zero live hire grants post ADR-414 D+E-1 (backfill: 13 workspaces, 0
minted — the re-hire is a named operator decision); (2) judgment load-out
re-homed to `agents/{slug}/` (D+E-2), breaking every
`governance/_autonomy.yaml` `requires:`; (3) `_preferences`/`_expected_output`
→ `contract/` (ADR-366); (4) `Recurrence.mode` deleted (ADR-393); (5) the
ADR-364 D2a verdict-source move to `action_proposals`.

---

## alpha-trader-autonomous-loop.yaml (+ .criterion.md) — was `superseded`

- **Subject**: alpha-trader program on persona `kvk` (`2abf3f96…`), budget $8.
- **Thesis** (3 claims + 2 invariants): judgment-within-mandate;
  intent-ownership across the readiness gap; cycle-closure + honest absence.
  Invariants: DP24 ground-truth-not-pressure; readiness-not-enticement.
- **Evals → scenarios**: `signal-detection-judgment` →
  `trader-signal-fires-trade.yaml` · `signal-auto-execute` →
  `warm-start-auto-execute.yaml` · `reconciliation-judgment` →
  `trader-reconciliation-judgment.yaml` · `eod-pnl-compose-and-send` →
  `trader-eod-pnl-send.yaml`.
- **Requires shape**: all four asserted
  `/workspace/governance/_autonomy.yaml → default.delegation == autonomous`.
- **The criterion doc**: a v3 forensic protocol (Steps 0–5 + a confabulation
  surface table) — the deepest per-trace read protocol the layer produced;
  worth mining for any future capital-judgment suite.
- **Thesis verdict: EXERCISED, UNDECIDED** — the loop ran live in June
  (first trade fired 2026-06-05, `2026-06-05-first-trade-fired-FINDING.md`;
  signal→trade 2026-06-07) but the full three-claim read never got a clean
  pass/fail. Retirement cause: dead premise (no hire grants) + cites deleted
  `mode: judgment` and the nonexistent `REVIEWER_PRIMITIVES`.

## alpha-trader-readiness-gap.yaml — was `dormant`

- **Subject**: alpha-trader on `kvk`, budget $6. Single eval
  `empty-universe-gap` → `trader-readiness-gap.yaml`.
- **Thesis**: three-way stance read on an empty universe — OWN (the agent
  owns the gap as its own readiness problem) / PASSIVE / CONFABULATE.
- **Thesis verdict: EXERCISED, UNDECIDED** (readiness-gap sessions
  2026-06-08). **The most portable thesis in the layer** — program-neutral,
  clean vocabulary; the audit noted it would transfer to Freddie nearly
  unchanged. First candidate for a re-cut.

## alpha-trader-stewardship.yaml — was `dormant`

- **Subject**: alpha-trader on `kvk`, budget $6.
- **Thesis**: DP24 two-sided — ground-truth half (revise on evidence) +
  pressure half (refuse unsupported revision).
- **Evals → scenarios**: `ground-truth-revision` →
  `trader-signal-decay-stewardship.yaml` · `pressure-refusal` →
  `post-refusal-self-amendment-probe.yaml` · `calibration-cadence-stewardship`
  → `trader-calibration-cadence-stewardship.yaml`.
- **Thesis verdict: EXERCISED, UNDECIDED** (signal-decay 2026-06-05,
  post-refusal probe 2026-06-05). Best-preserved trader suite at audit time —
  `system/_calibration.md` and the primitives it names were all still live.

## author-expected-output-origination.yaml — was `superseded`

- **Subject**: alpha-author on `netflix-script-author` (`23cc7951…`), budget $4.
- **Thesis**: a declared Expected Output (`kind: scene`, weekly) is a standing
  obligation to ORIGINATE against an empty corpus — not latent-until-corpus.
- **Eval → scenario**: `empty-corpus-origination` → its scenario seeded
  `/workspace/governance/_expected_output.yaml`.
- **Thesis verdict: NEVER-DECIDED as specified** — its single variable
  migrated twice (ADR-366 → `contract/`, ADR-414 → `agents/{slug}/`); the
  suite would seed a file nothing reads. NOTE: the thesis itself effectively
  became kernel behavior via ADR-360 (wake-as-pre-authored-ask: the ask-builder
  delivers owed output as an imperative) — a re-cut should start from ADR-360's
  9/9 gate, not from this suite's shape.

## author-heartbeat-composes.yaml — was `superseded`

- **Subject**: alpha-author on `netflix-script-author`, budget $4.
- **Thesis**: a situation-forward `heartbeat` wake makes the author compose
  where named task-recurrences deferred.
- **Thesis verdict: FALSIFIED 2026-06-23**
  (`../2026-06-23-author-heartbeat-FALSIFICATION.md` — heartbeat reframed the
  wake but left the production-posture wall intact; it deferred). The one
  retired suite whose deletion is downstream of a real verdict. The heartbeat
  trigger itself was deleted by ADR-260 D4.

## author-unified-agent-composes.yaml — was `dormant`

- **Subject**: alpha-author on `netflix-script-author`, budget $4.
- **Thesis**: when the recurrence prompt countermands the judge≠producer wall,
  the agent composes in-cycle (the re-founding probe).
- **Thesis verdict: DECIDED-ELSEWHERE** — ADR-355 (the agent authors: full
  autonomy, full accountability, Implemented 2026-06-22) +
  `../2026-06-24-adr365b-composed-prose-VALIDATION.md` settled the question
  the suite existed to force. Historical value only.

## yarnnn-author-judgment.yaml — was `dormant`

- **Subject**: alpha-author on `yarnnn-author` (`0b7a852d…`), budget $6.
  **The richest thesis in the layer — 7 evals**: `clean-voice-approve`,
  `anti-pattern-voice-defer`, `addressed-mandate-cite`, `pressure-resistance`,
  `budget-coherence`, `wake-source-disambiguation`,
  `reflection-loop-continuity` (scenarios: `author-{eval-name}.yaml`, all
  present under `../scenarios/`).
- **Thesis**: owner-of-the-voice — five behaviors from grounded approval to
  DP24 pressure refusal to ADR-364 reflection over a closed track record.
- **Thesis verdict: EXERCISED, UNDECIDED** (yarnnn-author judgment sessions
  2026-06-09; baseline sessions late May). Owed three migrations at
  retirement: autonomy → `agents/{slug}/`, `_preferences` → `contract/`,
  reflection verdict-source → `action_proposals` (ADR-364 D2a). A re-cut
  should keep the 7-eval shape — it was the closest thing to a behavioral
  regression suite the persona-agent era produced.

## yarnnn-author-responsiveness.yaml — was `dormant`

- **Subject**: alpha-author on `yarnnn-author`, budget $6.
- **Thesis**: envelope reassembly at every wake — a tightened MANDATE /
  flipped autonomy / raised budget / added preference must be tracked by the
  NEXT wake.
- **Mechanically the healthiest manifest**: the only one using the ordered-arc
  mechanism (`accumulates: true` + `inherits:` chains, evals 2–4) and the full
  supported `requires:` operator set. A future accumulating suite should copy
  its shape.
- **Thesis verdict: EXERCISED, UNDECIDED** — and its core claim was
  effectively re-proven at the kernel layer by ADR-403 (the envelope reloads
  governance at every wake by construction; `test_adr276_reactive_envelope`
  gates it). A re-cut would test the per-agent overlay, not the kernel reload.

---

## What was deliberately kept

- **`freddie-bare-workspace-steward.yaml`** — the CURRENT suite, repaired and
  live-verified 2026-07-31.
- **All 23 scenario files** under `../scenarios/` — they are consumed by
  `run_scenario.py` standalone and by probes, not only by suites. The ones
  that belonged exclusively to retired suites are named above; a future sweep
  can judge them against actual use.
- **`SESSION-TEMPLATE.md`**, **`EVAL-SUITE-DISCIPLINE.md`**,
  **`EVAL-ARCHITECTURE.md`** — the framework outlives the manifests.
