# Pre-Ship Check Spec

Spec for the `pre-ship-audit` recurrence. The Reviewer reads this spec when auditing a draft marked `ready_for_review` before publication.

## Purpose

Apply the full audit chain to a draft before it ships:
1. Voice fingerprint check (per `/workspace/operation/specs/voice-audit.md`)
2. Continuity check (per `/workspace/operation/specs/continuity-audit.md`)
3. Anti-AI-slop check (subset of voice-audit; universal anti-pattern baseline)
4. Editorial principle match (per `_editorial.md` "what gets shipped" criteria)
5. Citation-verifiability check (per `principles.md::citation-verifiability`) — external factual references (ADR/file/URL claims) the Reviewer cannot verify from workspace substrate → defer to operator; internally-inconsistent or invented-path references → reject. "Architecture-grounded" is not satisfied by the mere presence of citations; it requires references the Reviewer can confirm or the operator confirms.
6. Cadence context (is this on declared cadence per `_preferences.yaml`)

## Trigger shape

Reactive (`schedule: null` in `_recurrences.yaml`). Fires when:
- Operator marks a draft `ready_for_review` in piece profile.md.
- Operator addresses the Reviewer in chat with explicit pre-ship audit intent.
- `FireInvocation(slug="pre-ship-audit", context={piece_slug: ...})` is called from another recurrence (rare).

## Inputs the Reviewer reads

- The draft: `/workspace/operation/authored/{piece-slug}/content.md` + `profile.md`.
- Voice fingerprint: `/workspace/operation/authored/_voice.md`.
- Editorial principles: `/workspace/operation/authored/_editorial.md`.
- Recent corpus: pieces in `/workspace/operation/authored/` where status is `published`, sorted by `published_at` desc, top 5-10.
- Cadence preferences: `/workspace/contract/_preferences.yaml`.
- Calibration state: `/workspace/operation/authored/_signal.md` rolling-window state (for audit-EV reasoning).

## Output target

**Two-channel verdict (ADR-303 P6 — channel-shape discipline).** A pre-ship audit produces a long, structured, rule-by-rule document. That document does NOT fit a short verdict-signal field — so it has its own channel:

1. **The full rule-by-rule audit → `/workspace/persona/judgment_log.md` via ONE `WriteFile` call (append-only, per ADR-281).** This is the verdict-of-record: the `## Pre-Ship Audit / ### Rule 1.../### Rule 2.../### Rule 8...` document covering EVERY rule, with specific evidence (paragraph locations, excerpts, prior-piece references). **Read all needed substrate first, compose the COMPLETE audit, write it ONCE** — do not write rule-by-rule across many WriteFile calls (that fragments the document and exhausts the round budget before the audit finishes — observed 2026-06-01, the audit budget-exhausted at round 20/20 mid-write). Always include the `content` parameter. Write this single call FIRST.
2. **The headline → `ReturnVerdict`.** After the single judgment_log write, close the turn with `ReturnVerdict(verdict=approve|defer|reject, reasoning='[one-sentence headline]', confidence=...)`. `reasoning` is the headline ONLY — do not restate the full audit there; the full audit is the judgment_log document. A verdict emitted as prose without a tool call does NOT close the turn.
3. The draft's `profile.md` updated with `pre_ship_audit_state: approved | deferred | rejected` and the latest audit timestamp.
4. When deferred: the structured defect description lives in the judgment_log document; surface a `Clarify` message to the operator with the specific operator-actionable defect.
5. When approved AND `_autonomy.yaml` permits auto-ship for this piece type: `ProposeAction(action_type="ship_piece", piece_slug=...)` emitted. Otherwise the approve is surfaced to operator Queue for click.

## Verdict criteria

**APPROVE** when all of:
- Voice-audit verdict `pass` (no operator-declared anti-patterns triggered; no universal anti-pattern baseline triggered, OR operator declared `voice_override: true` in profile.md).
- Continuity-audit verdict `pass` (no unacknowledged contradictions, OR bridge is present in draft, OR operator declared `continuity_override: true` with reasoning).
- Anti-slop check clean.
- Editorial principle match: draft satisfies the `_editorial.md` "what gets shipped" criteria.
- Citation-verifiability `pass`: zero unverifiable load-bearing external references (or all such references trace to workspace substrate the Reviewer confirmed).
- Cadence context: draft is on-cadence, ahead of cadence, or behind-cadence-with-operator-acknowledgment.

**DEFER** when one or more checks have specific operator-actionable defects:
- Single anti-pattern hit with specific location (operator can edit and resubmit).
- Continuity break with a clear suggested bridge (operator authors the bridge).
- Unverifiable load-bearing external references (ADR/file/URL claims the Reviewer cannot confirm from workspace substrate) — operator confirms each resolves to a real source matching the claim, or revises.
- Cadence behind but operator hasn't declared if this piece is on-thesis or off-cadence.

**REJECT** when one or more hard rejection rules fire (per `/workspace/persona/principles.md` "Hard rejection rules" section):
- Voice fingerprint drift beyond declared tolerance.
- ≥2 anti-slop signature hits without operator override.
- Unacknowledged continuity break with no clear bridge.
- Engagement-bait construction detected.
- Hot-take posture without thesis-advancement justification.
- Internally-inconsistent or invented-path external references (citation-verifiability fabrication tells — e.g. a count claim that contradicts its own list, or a URL path shape contradicting a declared convention).
- Missing voice fingerprint declaration (bootstrap exception per principles.md "Bootstrap clause").

## Quality criteria

- Audit verdict includes specific evidence (paragraph locations, excerpts, prior-piece references). No vague "feels off" language.
- Defer directives are operator-actionable — operator can fix the named defect and resubmit without further interpretation work.
- Reject reasoning cites the specific principles.md hard-rejection-rule by name.
- Audit verdict written to judgment_log.md within the same Reviewer wake (no orphan audits).
- When auto-ship fires (Phase 1+ bounded-autonomous), the ProposeAction includes the audit verdict reasoning in its `reasoning` field so the action proposals queue carries the audit trail.
