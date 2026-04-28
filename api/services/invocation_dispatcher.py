"""
Invocation Dispatcher — ADR-231 Phase 2 adapter.

The forthcoming canonical entry point for firing invocations against
recurrence declarations. Phase 2 (this commit): a thin adapter that
translates `RecurrenceDeclaration` inputs into the existing task pipeline
shape, then delegates to `task_pipeline.execute_task`.

Phase 3 atomic cutover replaces the adapter body with a YAML-native
pipeline (the `task_pipeline.py` internals migrate here, the slug-based
entry point disappears, and the `tasks` table queries are dropped).

Two reasons this file exists *now* rather than waiting for the cutover:

1. **Caller migration target**: any caller that wants to fire a recurrence
   can route through this dispatcher today. When the cutover lands, only
   *this* file's internals change — call sites stay stable. That's the
   Singular Implementation discipline applied at the call-site boundary:
   one place to dispatch, regardless of how the dispatch is implemented
   underneath.
2. **`FireInvocation` clean surface**: the primitive (added in commit
   4595657) currently calls `task_pipeline.execute_task` directly. With
   this dispatcher in place, the primitive routes through here instead,
   and the cutover doesn't have to touch the primitive itself.

Public surface:

  await dispatch(client, user_id, decl: RecurrenceDeclaration, *, context: str | None = None) -> dict

Returns a dict with at minimum `{success: bool, ...}`. Additional fields
mirror what `task_pipeline.execute_task` returns today; the cutover may
sharpen the return shape but `success` is the load-bearing contract.
"""

from __future__ import annotations

import logging
from typing import Optional

from services.recurrence import RecurrenceDeclaration, RecurrenceShape

logger = logging.getLogger(__name__)


async def dispatch(
    client,
    user_id: str,
    decl: RecurrenceDeclaration,
    *,
    context: Optional[str] = None,
) -> dict:
    """Fire one invocation against a recurrence declaration.

    Phase 2 adapter: routes through `task_pipeline.execute_task` by slug.
    Works during the migration window because every recurrence declaration
    has a corresponding `tasks` row.

    Phase 3 atomic cutover replaces this body with a direct YAML-native
    pipeline (no slug lookup; declaration is the canonical input).

    Args:
        client: Supabase service client
        user_id: User UUID
        decl: parsed RecurrenceDeclaration to fire
        context: optional one-shot steering for this firing (does NOT
                 mutate the declaration; informs only this invocation)

    Returns:
        Result dict from the underlying pipeline. Always contains
        `success: bool` plus pipeline-specific fields. Augmented with
        `shape`, `slug`, `declaration_path` for caller correlation.
    """
    if decl.paused:
        return {
            "success": False,
            "error": "paused",
            "message": (
                f"declaration '{decl.slug}' is paused; cannot dispatch. "
                f"Use UpdateContext(target='recurrence', action='resume', ...) to resume."
            ),
            "shape": decl.shape.value,
            "slug": decl.slug,
            "declaration_path": decl.declaration_path,
        }

    # Phase 2 dispatch shim — route through existing pipeline by slug.
    try:
        from services.task_pipeline import execute_task
    except ImportError as e:
        return {
            "success": False,
            "error": "pipeline_unavailable",
            "message": f"task pipeline unavailable: {e}",
            "shape": decl.shape.value,
            "slug": decl.slug,
            "declaration_path": decl.declaration_path,
        }

    try:
        result = await execute_task(
            client=client,
            user_id=user_id,
            task_slug=decl.slug,
            context=context,
        )
    except Exception as e:
        logger.exception(
            "[INVOCATION_DISPATCHER] dispatch failed for %s/%s: %s",
            decl.shape.value,
            decl.slug,
            e,
        )
        return {
            "success": False,
            "error": "dispatch_error",
            "message": str(e),
            "shape": decl.shape.value,
            "slug": decl.slug,
            "declaration_path": decl.declaration_path,
        }

    if not isinstance(result, dict):
        result = {"success": True, "raw": result}
    result.setdefault("success", True)
    result["shape"] = decl.shape.value
    result["slug"] = decl.slug
    result["declaration_path"] = decl.declaration_path
    return result


__all__ = ["dispatch"]
