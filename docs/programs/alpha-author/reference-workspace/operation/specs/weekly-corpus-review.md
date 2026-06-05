# Weekly Corpus Review Spec

Spec for the weekly `weekly-corpus-review` deliverable. Operator declares cadence in `_preferences.yaml` (default Sunday 18:00 UTC); the Reviewer authors the actual Schedule call per ADR-275.

## Purpose

Sunday-night synthesis surface for the operator. Compute voice-fingerprint stability, corpus continuity state, cadence health, and audience response (when audience-bearing); flag any drift signals; surface candidates for the quarterly voice audit.

## Output target

`/workspace/operation/reports/weekly-corpus-review/{date}/output.md`

## Required sections (in order)

### 1. `## Corpus State`
- Pieces shipped this week (count + slugs with links).
- Pieces in draft (count + slugs).
- Pieces deferred at pre-ship-audit this week (count + slugs + brief defer reason).
- Pieces rejected at pre-ship-audit this week (count + slugs + brief reject reason).

### 2. `## Voice Fingerprint Stability`
- Voice-audit accuracy (rolling 30d) from `_signal.md` calibration block.
- Top 3 anti-pattern hits this week with locations + excerpts.
- Voice-flag false-positive rate (operator-overridden flags) — if elevated, propose `_voice.md` revision.
- Comparison to prior week's voice-fingerprint stability metric.

### 3. `## Continuity Threads`
- Active threads this week (pieces that extended a prior corpus thread).
- Continuity breaks detected (with bridge status: bridged | unbridged-acknowledged | unbridged-flagged).
- Cross-piece tensions surfaced post-hoc (pieces published 4+ weeks ago now in tension with this week's pieces).

### 4. `## Cadence Health`
- Operator's declared cadence per `_preferences.yaml` (e.g., "newsletter weekly Sunday").
- Actual ship cadence this week + rolling 30d.
- Cadence state: on-cadence | ahead | behind. When behind, list missed cadence intervals.

### 5. `## Audience Response` (when audience-bearing)
- Subscriber/follower deltas per platform.
- Top engagement signals (per `_signal.md` audience block) with attribution to specific pieces.
- Churn events flagged for follow-up.
- When pre-audience (internal coherence only), this section reads: *"Internal-coherence only — no audience capabilities connected. Continue to Phase 1 substrate accumulation."*

### 6. `## Quarterly-Audit Flags`
- Signals deserving discussion at the next quarterly voice audit (whether for `_voice.md` revision, `_editorial.md` revision, or just close monitoring).
- One bullet per flag: `**Pattern N**: {description} ({metric vs baseline})`.

## Quality criteria

- Per-section quantitative AND narrative — numbers cite source (audit accuracy from `_signal.md`, ship counts from revision lineage, audience deltas from audience mechanical-mirrors when present).
- Anti-patterns flagged this week listed in BOTH section 2 (per-pattern detail) AND section 6 (quarterly-audit-flags) when persistent.
- Reference `/workspace/operation/authored/_signal.md` as the single numerical source. Do not recompute from raw audit logs.
- Length: ~800-1500 words.
- Section partials in `/workspace/operation/reports/weekly-corpus-review/{date}/sections/`:
  `1-corpus-state.md`, `2-voice-stability.md`, `3-continuity-threads.md`, `4-cadence-health.md`, `5-audience-response.md`, `6-quarterly-audit-flags.md`.
