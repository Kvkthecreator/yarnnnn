# Corpus Coherence Rollup Spec

Schema for `_signal.md` — alpha-author's instance of the ground-truth substrate per FOUNDATIONS Axiom 8 + ADR-282 + ADR-283 D4.

## File location

Per-domain at `/workspace/context/authored/_signal.md` and (when audience-bearing) `/workspace/context/audience/_signal.md`. Cross-domain rollup at `/workspace/context/_signal_summary.md`.

## File format

YAML frontmatter (machine-parsed rolling windows + processed-event-keys for idempotency) + human-readable body (narrative of recent activity, drift signals, calibration state).

## Frontmatter schema

```yaml
---
last_reconciled: 2026-05-15T05:00:00Z   # ISO-8601 with timezone
processed_event_keys:                   # idempotency — reconciler skips events already processed
  - decisions:2026-05-15:audit-piece-foo
  - decisions:2026-05-14:audit-piece-bar

# ── Rolling windows (computed each reconciliation) ─────────────────────
rolling_windows:
  7d:
    audits_total: <int>
    audits_approved: <int>
    audits_deferred: <int>
    audits_rejected: <int>
    pieces_shipped: <int>
    voice_flags_total: <int>
    voice_flags_correct: <int>           # operator agreed with flag
    voice_flags_false_positive: <int>    # operator overrode flag
    continuity_flags_total: <int>
    continuity_flags_correct: <int>
    continuity_flags_false_positive: <int>
    cadence_state: on-cadence | behind | ahead
  30d:
    <same shape as 7d>
  90d:
    <same shape as 7d>

# ── By piece type (when relevant) ───────────────────────────────────────
by_piece_type:
  newsletter:
    <same shape as rolling_windows.7d for this piece type only>
  essay:
    <same shape>
  post:
    <same shape>

# ── Audience signal slice (when audience-bearing) ───────────────────────
# Only populated when audience-bearing capabilities (LinkedIn/X/newsletter)
# are connected per ADR-283 step 2. Pre-step-2 workspaces have this block
# empty.
audience_signal:
  source: <internal_coherence_only | engagement | revenue | composite>
  rolling_windows:
    7d:
      subscriber_delta: <int>             # net new subscribers/followers in window
      engagement_zscore: <float>          # engagement relative to rolling mean
      churn_count: <int>
    30d: { <same shape> }
    90d: { <same shape> }

# ── Reviewer calibration ───────────────────────────────────────────────
calibration:
  voice_audit_accuracy_30d: <float 0.0-1.0>   # voice_flags_correct / voice_flags_total
  continuity_audit_accuracy_30d: <float 0.0-1.0>
  last_calibration_run: 2026-05-15T05:00:00Z
---
```

## Body shape (narrative)

```markdown
# Corpus Signal — {workspace-name}

## Headline (rolling 30d)

{2-3 sentence narrative: recent audit accuracy, voice fingerprint stability, ship cadence state, key drift signals if any.}

## By piece type

### Newsletter
- Pieces shipped (30d): {n}
- Voice-flag rate: {pct} ({flagged} of {total} drafts)
- Notable: {top voice-drift pattern from 30d, or "no drift signals"}

### Essay
{same shape}

### Post
{same shape}

## Audience signal (if audience-bearing)

{Subscriber/engagement state per platform. When pre-audience (internal coherence only), this section reads: "Internal-coherence only — no audience capabilities connected. Calibration uses audit accuracy + voice-fingerprint stability."}

## Recent notable findings

- {date}: {finding} ({piece-slug reference, with link})
- ...

## Calibration state

Voice-audit accuracy 30d: {pct}. Continuity-audit accuracy 30d: {pct}. {1-2 sentences on calibration trajectory: tightening, loosening, stable.}
```

## Reconciler ownership

`outcome-reconciliation` recurrence writes this file. The operator does not hand-edit it (same write-discipline as alpha-trader's `_money_truth.md`). The Reviewer reads it as the ground-truth substrate for calibration reasoning.

## Bootstrap state

When the workspace has no audit history yet (first day of activation, no audits run):
- Frontmatter rolling windows have all counters at 0 and `cadence_state: on-cadence`.
- Body narrative reads: *"Workspace newly activated. Calibration begins from this point forward. Run pre-ship-audit on first draft to seed."*
- Audience signal block (if audience-bearing) reads: *"No audience signal yet — first reconciliation cycle pending."*

## Idempotency

Each reconciliation processes only events not already in `processed_event_keys`. Reconciler may run any number of times; output is deterministic modulo accumulated event history.
