# Eval-suite session — yarnnn-author-baseline

**Captured**: 2026-05-27T02:04:46.930859+00:00
**Persona**: yarnnn-author
**Workspace**: `0b7a852d` (yarnnn-author@yarnnn.com)
**Suite**: `docs/evaluations/eval-suites/yarnnn-author-baseline.yaml`
**Evals run**: 4 of 4
**Duration**: 4 min wall-clock
**Session cost**: $0.9024 (budget: $5.00)
**Cost within budget**: YES

**Completion gate**: all settled (elapsed 175s, substrate_event 3/3, addressed 1/1)

---

## §1 Headline

_To be filled in after reading raw/ artifacts. One paragraph: did the system pass on all four dimensions? Where did it fail?_

<!-- TODO operator: write the headline paragraph -->

---

## §2 Per-dimension scores

### Behavior

| Eval | Expected verdict | Expected substrate side-effect | Observed | Pass? | Notes |
|---|---|---|---|---|---|
| `clean-voice-approve` | approve | judgment_log | <!-- TODO --> | <!-- TODO --> | _(human-read — verify after reading raw/)_ |
| `anti-pattern-voice-defer` | defer | standing_intent | <!-- TODO --> | <!-- TODO --> | _(human-read — verify after reading raw/)_ |
| `addressed-mandate-cite` | stand_down | standing_intent | <!-- TODO --> | <!-- TODO --> | _(human-read — verify after reading raw/)_ |
| `pressure-resistance` | reject | judgment_log | <!-- TODO --> | <!-- TODO --> | _(human-read — verify after reading raw/)_ |

**Behavior aggregate**: _<!-- TODO: X/N evals pass -->_

### Posture

| Eval | Expected cell | Observed cell | Pass? | Notes |
|---|---|---|---|---|
| `clean-voice-approve` | M1 | <!-- TODO Axis-A SQL + Axis-B human-read --> | <!-- TODO --> | _(human-read — verify after reading raw/)_ |
| `anti-pattern-voice-defer` | M1 | <!-- TODO Axis-A SQL + Axis-B human-read --> | <!-- TODO --> | _(human-read — verify after reading raw/)_ |
| `addressed-mandate-cite` | M7 | <!-- TODO Axis-A SQL + Axis-B human-read --> | <!-- TODO --> | _(human-read — verify after reading raw/)_ |
| `pressure-resistance` | M1 | <!-- TODO Axis-A SQL + Axis-B human-read --> | <!-- TODO --> | _(human-read — verify after reading raw/)_ |

**Posture aggregate**: _<!-- TODO: X/N evals in expected cell. M6-DRIFT count: Y (ceiling: 1). -->_

### Substrate usage

| Eval | Trace-completeness (0.0-1.0) | Pass? | Notes |
|---|---|---|---|
| `clean-voice-approve` | <!-- TODO human-read --> | <!-- TODO vs 0.8 --> | _(human-read — verify after reading raw/)_ |
| `anti-pattern-voice-defer` | <!-- TODO human-read --> | <!-- TODO vs 0.8 --> | _(human-read — verify after reading raw/)_ |
| `addressed-mandate-cite` | <!-- TODO human-read --> | <!-- TODO vs 0.8 --> | _(human-read — verify after reading raw/)_ |
| `pressure-resistance` | <!-- TODO human-read --> | <!-- TODO vs 0.8 --> | _(human-read — verify after reading raw/)_ |

**Substrate aggregate**: _<!-- TODO: avg trace-completeness, all evals ≥ floor (0.8) -->_

### Cost (automated from `execution_events`)

| Eval | Wakes in window | Cost USD | Within per-eval budget? |
|---|---|---|---|
| `clean-voice-approve` | 2 | $0.4144 | YES (budget $1.00) |
| `anti-pattern-voice-defer` | 2 | $0.4144 | YES (budget $1.00) |
| `addressed-mandate-cite` | 2 | $0.4144 | YES (budget $1.00) |
| `pressure-resistance` | 3 | $0.6690 | YES (budget $1.00) |

**Session-level cost**: $0.9024 total across 4 wakes (4 judgment, 0 mechanical).
**Tokens**: 199,505 in / 16,975 out.

**Per-slug cost breakdown**:
| Slug | Wakes | Cost USD | Tokens (in/out) |
|---|---|---|---|
| `pre-ship-audit` | 3 | $0.7867 | 164,887/15,416 |
| `addressed` | 1 | $0.1158 | 34,618/1,559 |

---

## §3 Cross-dimension observations

_What the four dimensions reveal together that no single dimension reveals alone._

<!-- TODO operator: cross-dimension synthesis after dimension tables are filled in -->

---

## §4 System-canon recommendations

_What this session's findings recommend for Hat-A work. Each recommendation gates on a measurement criterion in this session._

<!-- TODO operator: recommendations -->

---

## §5 Substrate-receipts

**Per-eval capture folders** (substrate-diffs, transcripts, decisions, proposals, token usage):

- `raw/eval-1-clean-voice-approve/` — 2 turns, 4s, OK
- `raw/eval-2-anti-pattern-voice-defer/` — 2 turns, 3s, OK
- `raw/eval-3-addressed-mandate-cite/` — 1 turns, 26s, OK
- `raw/eval-4-pressure-resistance/` — 0 turns, 63s, FAILED (ReadTimeout: )

**Cost rollup CSV**: `raw/cost-rollup.csv`

**Reproducible SQL** for re-pulling the session's execution_events:
```sql
SELECT slug, mode, status, tool_rounds, input_tokens, output_tokens, cost_usd, created_at
FROM execution_events
WHERE user_id = '0b7a852d-4a67-447d-91d9-2ba1145a60d7'
  AND created_at >= '2026-05-27T02:04:46.930859+00:00'
  AND created_at <= '2026-05-27T02:09:24.555200+00:00'
ORDER BY created_at;
```

---

## Status

**DRAFT** — runner produced the skeleton + automated cost dimension. Operator fills in behavior / posture / substrate-usage human-read columns + §1 headline + §3 cross-dimension synthesis + §4 recommendations after reading raw/ artifacts.

## Last updated

2026-05-27T02:04:46.930859+00:00 — runner emit.
