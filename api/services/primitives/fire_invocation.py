"""
FireInvocation Primitive — ADR-261 unified shape.

Manual fire of a recurrence — "run this once now." The operator (via
chat) or the Reviewer (mid-loop) calls FireInvocation with a slug; the
dispatcher invokes the Reviewer with that recurrence's prompt as the
addressed-equivalent envelope (per ADR-260 D1 + ADR-261 D3).

Per ADR-261 D1 there is no shape parameter — every recurrence has the
same shape. Per ADR-261 D2 there is one canonical file
(``/workspace/_recurrences.yaml``); the slug looks up the entry there.

Tool surface (chat + headless, both modes can fire invocations):

    FireInvocation(slug="signal-evaluation")
    FireInvocation(slug="weekly-brief", context="Focus on pricing changes only")

The optional ``context`` field carries one-shot steering for this
firing only — appended to the recurrence's prompt; does not mutate the
recurrence record.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


FIRE_INVOCATION_TOOL = {
    "name": "FireInvocation",
    "description": """Fire a recurrence — run it once now (ADR-261).

Use when the operator wants to manually trigger a recurring task immediately. The recurrence's prompt becomes the addressed-equivalent envelope handed to the Reviewer.

Optional `context` carries one-shot steering for this firing only — does not modify the recurrence. Useful when the operator wants the next run to focus on something specific without amending the prompt.

Examples:
  FireInvocation(slug="signal-evaluation")
  FireInvocation(slug="weekly-brief", context="Lead with pricing changes")

For chat-first operator-immediate work (where no recurrence exists yet), do NOT use FireInvocation — author the recurrence first via Schedule(action="create", ...), or do the work directly via the regular tool surface.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "slug": {
                "type": "string",
                "description": "Operator-legible nameplate of the recurrence in /workspace/_recurrences.yaml.",
            },
            "context": {
                "type": "string",
                "description": "Optional one-shot steering for this firing (does not modify the recurrence).",
            },
        },
        "required": ["slug"],
    },
}


async def handle_fire_invocation(auth: Any, input: dict) -> dict:
    """Fire an invocation against the named recurrence.

    Per ADR-261 D3 + ADR-260 D1: walks ``/workspace/_recurrences.yaml``,
    finds the entry, and dispatches via ``invocation_dispatcher.dispatch``
    with ``trigger="addressed"`` (operator-initiated) plus optional
    one-shot ``context`` steering.

    Returns ``{success, slug, trigger, message, ...}`` from the dispatcher.
    """
    from services.invocation_dispatcher import dispatch
    from services.recurrence import walk_workspace_recurrences

    user_id = getattr(auth, "user_id", None)
    db_client = getattr(auth, "client", None)
    if not user_id:
        return {"success": False, "error": "auth_required", "message": "user_id required"}

    input = input or {}
    slug = input.get("slug") or ""
    context = input.get("context")

    if not slug or not isinstance(slug, str):
        return {"success": False, "error": "missing_slug", "message": "slug is required"}

    recurrences = walk_workspace_recurrences(db_client, user_id)
    rec = next((r for r in recurrences if r.slug == slug), None)
    if rec is None:
        return {
            "success": False,
            "error": "not_found",
            "message": f"no recurrence with slug='{slug}' in /workspace/_recurrences.yaml",
            "retry_hint": (
                "Check the slug spelling. Use Schedule(action='create', ...) "
                "if you want to author a new recurrence."
            ),
        }

    if rec.paused:
        return {
            "success": False,
            "error": "paused",
            "message": (
                f"recurrence {slug} is paused. Use "
                f"Schedule(action='resume', slug='{slug}') before firing."
            ),
        }

    return await dispatch(
        client=db_client,
        user_id=user_id,
        recurrence=rec,
        trigger="addressed",
        context=context,
    )


__all__ = ["FIRE_INVOCATION_TOOL", "handle_fire_invocation"]
