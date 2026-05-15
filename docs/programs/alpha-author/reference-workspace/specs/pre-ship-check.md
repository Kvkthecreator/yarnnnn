# Pre-Ship Check Spec

Spec for the `pre-ship-audit` recurrence. The Reviewer reads this spec when auditing a draft marked `ready_for_review` before publication.

## Purpose

Apply the full audit chain to a draft before it ships:
1. Voice fingerprint check (per `/workspace/specs/voice-audit.md`)
2. Continuity check (per `/workspace/specs/continuity-audit.md`)
3. Anti-AI-slop check (subset of voice-audit; universal anti-pattern baseline)
4. Editorial principle match (per `_editorial.md` "what gets shipped" criteria)
5. Cadence context (is this on declared cadence per `_preferences.yaml`)

## Trigger shape

Reactive (`schedule: null` in `_recurrences.yaml`). Fires when:
- Operator marks a draft `ready_for_review` in piece profile.md.
- Operator addresses the Reviewer in chat with explicit pre-ship audit intent.
- `FireInvocation(slug="pre-ship-audit", context={piece_slug: ...})` is called from another recurrence (rare).

## Inputs the Reviewer reads

- The draft: `/workspace/context/authored/{piece-slug}/content.md` + `profile.md`.
- Voice fingerprint: `/workspace/context/authored/_voice.md`.
- Editorial principles: `/workspace/context/authored/_editorial.md`.
- Recent corpus: pieces in `/workspace/context/authored/` where status is `published`, sorted by `published_at` desc, top 5-10.
- Cadence preferences: `/workspace/context/_shared/_preferences.yaml`.
- Calibration state: `/workspace/context/authored/_signal.md` rolling-window state (for audit-EV reasoning).

## Output target

The Reviewer's verdict + reasoning lands at:
1. `/workspace/review/judgment_log.md` (append-only) per ADR-281.
2. The draft's `profile.md` updated with `pre_ship_audit_state: approved | deferred | rejected` and the latest audit timestamp.
3. When deferred: structured defect description in judgment_log.md AND a `Clarify` message surfaced to operator with the specific operator-actionable defect.
4. When approved AND `_autonomy.yaml` permits auto-ship for this piece type: `ProposeAction(action_type="ship_piece", piece_slug=...)` emitted. Otherwise the approve is surfaced to operator Queue for click.

## Verdict criteria

**APPROVE** when all of:
- Voice-audit verdict `pass` (no operator-declared anti-patterns triggered; no universal anti-pattern baseline triggered, OR operator declared `voice_override: true` in profile.md).
- Continuity-audit verdict `pass` (no unacknowledged contradictions, OR bridge is present in draft, OR operator declared `continuity_override: true` with reasoning).
- Anti-slop check clean.
- Editorial principle match: draft satisfies the `_editorial.md` "what gets shipped" criteria.
- Cadence context: draft is on-cadence, ahead of cadence, or behind-cadence-with-operator-acknowledgment.

**DEFER** when one or more checks have specific operator-actionable defects:
- Single anti-pattern hit with specific location (operator can edit and resubmit).
- Continuity break with a clear suggested bridge (operator authors the bridge).
- Cadence behind but operator hasn't declared if this piece is on-thesis or off-cadence.

**REJECT** when one or more hard rejection rules fire (per `/workspace/review/principles.md` "Hard rejection rules" section):
- Voice fingerprint drift beyond declared tolerance.
- ≥2 anti-slop signature hits without operator override.
- Unacknowledged continuity break with no clear bridge.
- Engagement-bait construction detected.
- Hot-take posture without thesis-advancement justification.
- Missing voice fingerprint declaration (bootstrap exception per principles.md "Bootstrap clause").

## Quality criteria

- Audit verdict includes specific evidence (paragraph locations, excerpts, prior-piece references). No vague "feels off" language.
- Defer directives are operator-actionable — operator can fix the named defect and resubmit without further interpretation work.
- Reject reasoning cites the specific principles.md hard-rejection-rule by name.
- Audit verdict written to judgment_log.md within the same Reviewer wake (no orphan audits).
- When auto-ship fires (Phase 1+ bounded-autonomous), the ProposeAction includes the audit verdict reasoning in its `reasoning` field so the action proposals queue carries the audit trail.
