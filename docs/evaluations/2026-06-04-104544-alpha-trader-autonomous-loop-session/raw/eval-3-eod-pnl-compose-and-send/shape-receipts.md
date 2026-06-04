# Shape receipts — eod-pnl-compose-and-send

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
_(none)_

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-04T10:47:25.925011+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T10:47:32.005053+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T10:47:34.008378+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T10:47:48.123301+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T10:47:49.181135+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T10:48:29.413443+00:00 | reactive | manual_fire | judgment | success |
| 2026-06-04T10:48:31.892208+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T10:48:32.893256+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-04T10:48:33.254883+00:00 | reactive | manual_fire | judgment | skipped |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
