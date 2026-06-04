# Shape receipts — eod-pnl-compose-and-send

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
_(none)_

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-04T11:51:29.073114+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T11:51:30.904031+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T11:52:12.915005+00:00 | reactive | manual_fire | judgment | success |
| 2026-06-04T11:52:14.270285+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T11:52:20.300717+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T11:52:22.578735+00:00 | reactive | manual_fire | mechanical | success |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
