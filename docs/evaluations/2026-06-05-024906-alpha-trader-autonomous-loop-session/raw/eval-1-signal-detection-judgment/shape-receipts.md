# Shape receipts — signal-detection-judgment

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
| id | family | primitive | status | source | dc_keys |
|---|---|---|---|---|---|
| `edaba1bd` | capital | platform_trading_submit_bracket_order | pending | None | ['expected_effect', 'rationale', 'reversibility', 'risk_warnings'] |
| `423684ef` | capital | platform_trading_submit_order | pending | None | ['expected_effect', 'rationale', 'reversibility', 'risk_warnings'] |

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-05T02:49:20.644655+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-05T02:49:22.448494+00:00 | reactive | manual_fire | mechanical | success |
| 2026-06-05T02:49:56.272995+00:00 | addressed | addressed | judgment | success |
| 2026-06-05T02:50:04.111334+00:00 | reactive | manual_fire | judgment | success |
| 2026-06-05T02:50:05.493272+00:00 | reactive | manual_fire | mechanical | success |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
