"""
services/wake_sources/addressed.py — Addressed wake source (ADR-296 v2 D1).

The operator addressed the Reviewer via chat. This is the SSE-streaming
wake path; the Reviewer's progress events yield as they fire.

Per ADR-296 v2 §C2, addressed wakes pass the funnel by default — operator
presence is itself a wake-warrant. Tier 1 always returns `escalate`. The
SSE generator yields events as the Reviewer runs.

Caller: `routes/feed.py` (chat endpoint). The route handler consumes the
async generator and formats events as SSE for the operator's HTTP response.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Optional

from services.wake import stream_addressed_wake

logger = logging.getLogger(__name__)


async def stream(
    client,
    user_id: str,
    *,
    session_id: str,
    invocation_id: str,
    user_message: str,
    conversation_window: str,
    operator_focus: Optional[dict] = None,
) -> AsyncGenerator[dict, None]:
    """Stream the addressed Reviewer cycle as a sequence of SSE-shaped events.

    Per ADR-296 v2 D1: addressed wakes auto-escalate (operator presence is
    wake-warrant); the funnel's Tier 1 returns `escalate` deterministically.
    The Reviewer's tool-use loop runs concurrently with event yielding.

    Args:
        client: Supabase service client
        user_id: Workspace owner UUID
        session_id: chat session UUID (for narrative writes downstream)
        invocation_id: pre-generated execution_events.id for the cycle
        user_message: operator's input
        conversation_window: rolling N-message context window
        operator_focus: ADR-607 — where the operator is standing, as the
            typed ADR-522 focus shape (dict of the StewardFocus wire model);
            rendered into the ask by the one steward site, never persisted

    Yields:
        Event dicts per services.wake.stream_addressed_wake() contract.
        See the parent docstring for shapes.
    """
    async for event in stream_addressed_wake(
        client, user_id,
        session_id=session_id,
        invocation_id=invocation_id,
        user_message=user_message,
        conversation_window=conversation_window,
        operator_focus=operator_focus,
    ):
        yield event


__all__ = ["stream"]
