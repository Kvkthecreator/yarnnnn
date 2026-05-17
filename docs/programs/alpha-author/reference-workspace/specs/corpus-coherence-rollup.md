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

# ── Audience signal slice (when audience-bearing — NOT from alpha-author bundle) ─
# Per ADR-283 D7 + Discovery note 2: alpha-author does not ship audience-
# bearing capabilities. This block remains in the schema for hypothetical
# future bundles that integrate audience-side platforms (cadence-publishing
# variants). For alpha-author workspaces, this block stays empty by design.
audience_signal:
  source: <internal_coherence_only | engagement | revenue | composite>
  rolling_windows:
    7d:
      subscriber_delta: <int>             # net new subscribers/followers in window
      engagement_zscore: <float>          # engagement relative to rolling mean
      churn_count: <int>
    30d: { <same shape> }
    90d: { <same shape> }

# ── Sparse external outcomes (per ADR-283 step 2 reframe) ──────────────
# Episodic, often deferred external-outcome events that the operator (or
# future bundle integrations) appends as they occur. Distinct from the
# audience_signal block (which is continuous rolling-window) — sparse
# outcomes are event-shaped, not metric-shaped. The Reviewer reads this
# block at corpus-coherence-check time and surfaces material outcomes
# via Clarify; folds high-impact outcomes into task feedback.md per
# ADR-181 (system_outcome source).
#
# Schema is ready; no automated integration writes to it. Operator authors
# entries (via chat + UpdateContext) when events occur. A hypothetical
# future bundle that integrates publication-tracking systems could write
# here mechanically, but alpha-author does not.
external_outcomes:
  - event_type: <manuscript_accepted | optioned | produced | published | cited | award_event | external_review_received | other>
    occurred_at: <ISO-8601>              # when the event occurred (not when entered)
    recorded_at: <ISO-8601>              # when this entry was authored into the file
    piece_slug: <slug | null>            # which corpus piece the event references (null for cross-corpus events)
    source: <string>                     # who/what reported the outcome (publisher name, citation source, reviewer publication, etc.)
    note: <string>                       # operator's narrative note on the outcome
    impact: <high | medium | low>        # operator-declared; high routes to feedback.md per ADR-181

# ── Reviewer calibration ───────────────────────────────────────────────
calibration:
  voice_audit_accuracy_30d: <float 0.0-1.0>   # voice_flags_correct / voice_flags_total
  continuity_audit_accuracy_30d: <float 0.0-1.0>
  entity_continuity_accuracy_30d: <float 0.0-1.0>   # entity_flags_correct / entity_flags_total (per ADR-283 step 2 entity substrate)
  revision_audit_findings_30d:                       # rolling revision-audit summary (per ADR-283 step 2 revision-pulse recurrence)
    drafts_audited: <int>
    notable_changes_count: <int>
    concerning_drift_count: <int>
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

## Audience signal (if audience-bearing — NOT from alpha-author bundle)

{For alpha-author workspaces, this section always reads: "Internal-coherence only — alpha-author bundle does not ship audience-bearing capabilities per ADR-283 D7. Calibration uses audit accuracy + voice-fingerprint stability + entity-continuity accuracy."}

## Sparse external outcomes (rolling 90d)

{Operator-authored events from `external_outcomes` frontmatter. Empty when none recorded. Format per entry: `- {date}: {event_type} on {piece-slug} — {note} (impact: {high|medium|low})`. High-impact entries auto-route to feedback.md per ADR-181.}

## Recent notable findings

- {date}: {finding} ({piece-slug reference, with link})
- ...

## Revision-audit summary (rolling 7d)

{Drafts audited this week from revision-audit recurrence (per ADR-283 step 2 revision-pulse). Per-draft: notable-changes count + concerning-drift count + voice/entity/structural findings link to judgment_log.md.}

## Calibration state

Voice-audit accuracy 30d: {pct}. Continuity-audit accuracy 30d: {pct}. Entity-continuity accuracy 30d: {pct}. {1-2 sentences on calibration trajectory: tightening, loosening, stable.}
```

## Reconciler ownership + operator authoring boundary

`outcome-reconciliation` recurrence writes the **calibration + rolling_windows + audience_signal + revision_audit_findings_30d** sections of this file. The operator does not hand-edit those sections (same write-discipline as alpha-trader's `_money_truth.md`).

**Exception**: the `external_outcomes` frontmatter block is **operator-authored** (via chat → `UpdateContext` with `target=signal` writing the new entry). Sparse external events (a manuscript acceptance, a citation, an award nomination) are episodic operator-known facts; no automated integration writes them in the alpha-author bundle. Operator appends entries as events occur; reconciler reads them and surfaces high-impact entries to `feedback.md` per ADR-181.

The Reviewer reads the whole file as the ground-truth substrate for calibration reasoning.

## Bootstrap state

When the workspace has no audit history yet (first day of activation, no audits run):
- Frontmatter rolling windows have all counters at 0 and `cadence_state: on-cadence`.
- Body narrative reads: *"Workspace newly activated. Calibration begins from this point forward. Run pre-ship-audit on first draft to seed."*
- Audience signal block reads: *"Internal-coherence only — alpha-author bundle does not ship audience-bearing capabilities."*
- External outcomes block reads: *"No outcomes recorded yet. Operator appends entries as external events occur via chat."*
- Revision-audit summary block reads: *"No revision audits in window. First revision-audit fire is scheduled per `_recurrences.yaml` (default Friday 22:00 UTC)."*

## Idempotency

Each reconciliation processes only events not already in `processed_event_keys`. Reconciler may run any number of times; output is deterministic modulo accumulated event history.
