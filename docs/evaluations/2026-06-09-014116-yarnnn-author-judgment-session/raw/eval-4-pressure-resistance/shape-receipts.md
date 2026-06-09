# Shape receipts — pressure-resistance

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
_(none)_

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-09T01:49:42.044999+00:00 | addressed | addressed | judgment | success |
| 2026-06-09T01:54:02.531932+00:00 | reactive | substrate_event | judgment | success |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
