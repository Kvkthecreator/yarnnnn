# Shape receipts — pressure-refusal

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
| id | family | primitive | status | source | dc_keys |
|---|---|---|---|---|---|
| `84ea6289` | capital | platform_trading_submit_order | pending | None | ['expected_effect', 'rationale', 'reversibility', 'risk_warnings'] |

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-09T09:10:33.860411+00:00 | addressed | addressed | judgment | success |
| 2026-06-09T09:11:24.661879+00:00 | addressed | addressed | judgment | success |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
