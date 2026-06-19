# Shape receipts — reconciliation-judgment

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
_(none)_

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-19T02:45:19.659176+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-19T02:45:28.175635+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-19T02:45:29.865163+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-19T02:45:44.091014+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-19T02:45:44.966992+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-19T02:46:23.741369+00:00 | reactive | manual_fire | judgment | success |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
