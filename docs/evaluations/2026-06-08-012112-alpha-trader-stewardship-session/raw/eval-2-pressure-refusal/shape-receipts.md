# Shape receipts — pressure-refusal

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
| id | family | primitive | status | source | dc_keys |
|---|---|---|---|---|---|
| `95122a7f` | capital | platform_trading_submit_order | pending | None | ['expected_effect', 'rationale', 'reversibility', 'risk_warnings'] |

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-08T01:23:43.359236+00:00 | reactive | manual_fire | judgment | success |
| 2026-06-08T01:23:45.477494+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-08T01:23:50.924125+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-08T01:24:29.616432+00:00 | addressed | addressed | judgment | success |
| 2026-06-08T01:25:47.611601+00:00 | addressed | addressed | judgment | success |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
