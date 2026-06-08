# Shape receipts — ground-truth-revision

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
_(none)_

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-08T01:22:17.54118+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-08T01:22:18.466607+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-08T01:22:20.261217+00:00 | reactive | manual_fire | mechanical | success |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
