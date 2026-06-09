# Shape receipts — ground-truth-revision

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
_(none)_

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-09T09:08:18.038113+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-09T09:08:18.997327+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-09T09:08:20.825448+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-09T09:09:28.837676+00:00 | reactive | manual_fire | judgment | success |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
