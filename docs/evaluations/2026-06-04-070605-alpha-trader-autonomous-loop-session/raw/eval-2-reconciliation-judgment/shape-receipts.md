# Shape receipts — reconciliation-judgment

_Architecture-shape evidence (not just outcome). Per the ADR-307 lesson: check the action landed in the architecturally-correct shape — family, status, source, self-wake count._

## action_proposals in window
| id | family | primitive | status | source | dc_keys |
|---|---|---|---|---|---|
| `9af4377a` | capital | platform_trading_submit_order | rejected | None | ['expected_effect', 'rationale', 'reversibility', 'risk_warnings'] |

## execution_events in window
| created_at | trigger | wake_source | mode | status |
|---|---|---|---|---|
| 2026-06-04T07:08:51.278691+00:00 | addressed | manual_fire | mechanical | success |
| 2026-06-04T07:08:52.292475+00:00 | addressed | manual_fire | mechanical | success |
| 2026-06-04T07:08:54.056773+00:00 | addressed | manual_fire | judgment | success |
| 2026-06-04T07:08:55.793197+00:00 | addressed | manual_fire | mechanical | success |
| 2026-06-04T07:08:56.806011+00:00 | addressed | manual_fire | mechanical | success |
| 2026-06-04T07:08:57.779121+00:00 | addressed | manual_fire | judgment | success |

## Self-wake count (Reviewer re-waking on its own queued write)
**0** — should be 0 (ADR-307 source-skip guard).
