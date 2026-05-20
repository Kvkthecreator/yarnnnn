"""
services/wake_sources/ — Source-side entry surface for the wake funnel.

Per ADR-296 v2 D1, five wake sources contribute proposals to the singular
evaluation funnel:

  - cron_tick         scheduler walks due recurrences (cron_tick.py)
  - addressed         operator chat → SSE-streaming (addressed.py)
  - proposal_arrival  action_proposals INSERT (proposal_arrival.py)
  - substrate_event   /workspace/_hooks.yaml match (substrate_event.py)
  - manual_fire       FireInvocation in chat (manual_fire.py)

Every module exposes a thin, source-shaped entry function that builds
the wake-source-specific payload and calls
`services.wake.submit_wake_proposal()` (or
`services.wake.stream_addressed_wake()` for the streaming case).

This is the source-side discipline that makes the wake-source taxonomy
load-bearing in code — every site that wakes the Reviewer goes through
one of these modules. Singular Implementation per ADR-296 v2 D1.
"""

__all__ = []
