# Shape receipts — reconciliation-judgment

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
_(none)_

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-07T09:34:24.019881+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-07T09:34:29.594206+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-07T09:34:31.372542+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-07T09:35:05.701314+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-07T09:35:06.705658+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-07T09:35:55.375142+00:00 | reactive | manual_fire | judgment | success |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
