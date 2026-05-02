"""
FireInvocation Primitive — ADR-231 D5

Manual fire of a recurrence declaration. Replaces `ManageTask(action="trigger")`
under the invocation-first canon: invocations are the atom, recurrence
declarations are the legibility wrapper, and FireInvocation is the operator's
"run this once now" affordance.

Phase 2 implementation (this commit): thin adapter. Reads the recurrence
declaration via the new YAML schema, then routes through the existing
`task_pipeline.execute_task` by looking up the corresponding `tasks` row by
slug. This works for any declaration whose slug matches an existing task —
which is the migration state during Phase 2.

Phase 3 atomic cutover: this primitive's body is replaced with a direct
call to `invocation_dispatcher.execute_invocation(decl)`, the `tasks` row
lookup disappears, and FireInvocation becomes the singular dispatch primitive.

Tool surface (chat + headless parity, both modes can fire invocations):

    FireInvocation(shape="deliverable", slug="market-weekly")
    FireInvocation(shape="accumulation", slug="competitors-weekly-scan",
                   domain="competitors")
    FireInvocation(shape="action", slug="slack-standup")
    FireInvocation(shape="maintenance", slug="back-office-narrative-digest")
    FireInvocation(shape="deliverable", slug="weekly-brief",
                   context="Focus on pricing changes only")

The optional `context` field carries one-shot steering for this firing —
parallel to the existing `ManageTask(action="trigger", context=...)` shape.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


FIRE_INVOCATION_TOOL = {
    "name": "FireInvocation",
    "description": """Fire an invocation against a recurrence declaration — run it once now (ADR-231 D5).

Use when the operator wants to manually trigger a recurring task / report / action / maintenance job. Replaces the older `ManageTask(action="trigger")` shape.

Identifies the declaration via shape + slug (+ domain for accumulation):
  - shape="deliverable": runs a recurring report (e.g., weekly market brief)
  - shape="accumulation": runs a domain-tracking entry (e.g., competitor scan)
  - shape="action": runs an external-action declaration (e.g., scheduled Slack post)
  - shape="maintenance": runs a back-office job (e.g., workspace-cleanup)

Optional `context` carries one-shot steering for this firing only — does not modify the declaration. Useful when the operator wants the next run to focus on something specific without amending the recurrence config.

Examples:
  FireInvocation(shape="deliverable", slug="market-weekly")
  FireInvocation(shape="accumulation", slug="competitors-weekly-scan", domain="competitors")
  FireInvocation(shape="deliverable", slug="weekly-brief", context="Lead with pricing changes")

For chat-first operator-immediate work (where no recurrence exists yet), do NOT use FireInvocation — fire an invocation directly via the regular tool surface (gather context, produce output, write to filesystem). FireInvocation is for graduated recurrences only.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "shape": {
                "type": "string",
                "enum": ["deliverable", "accumulation", "action", "maintenance"],
                "description": "The recurrence shape — drives natural-home path resolution to find the declaration.",
            },
            "slug": {
                "type": "string",
                "description": "The operator-legible nameplate of the recurrence to fire.",
            },
            "domain": {
                "type": "string",
                "description": "Required when shape='accumulation' (the context domain — e.g., 'competitors'). Multi-decl files are per-domain.",
            },
            "context": {
                "type": "string",
                "description": "Optional one-shot steering for this firing (does not modify the declaration). Used when the operator wants the run to focus on something specific.",
            },
        },
        "required": ["shape", "slug"],
    },
}


async def handle_fire_invocation(auth: Any, input: dict) -> dict:
    """Fire an invocation against a recurrence declaration.

    Phase 2 implementation: locates the declaration via the recurrence YAML
    parser, then routes through `task_pipeline.execute_task` using the slug
    as the corresponding `tasks` row identifier.

    The Phase 3 atomic cutover replaces this body with a direct call to
    `invocation_dispatcher.execute_invocation(decl)` and drops the
    `tasks` row lookup entirely.

    Returns the same shape as `ManageTask(action="trigger")` for caller
    parity: `{success, message, agent_run_id?, run_at?, error?}`.
    """
    from services.recurrence import (
        RecurrenceShape,
        derive_declaration_path,
        parse_recurrence_yaml,
    )
    from services.workspace import UserMemory

    shape = input.get("shape")
    slug = input.get("slug")
    domain = input.get("domain")
    context = input.get("context")

    # ---- Validate inputs ----
    if shape not in {"deliverable", "accumulation", "action", "maintenance"}:
        return {
            "success": False,
            "error": "invalid_shape",
            "message": "shape must be one of: deliverable, accumulation, action, maintenance",
        }
    if not slug:
        return {"success": False, "error": "missing_slug", "message": "slug is required"}
    if shape == "accumulation" and not domain:
        return {
            "success": False,
            "error": "missing_domain",
            "message": "domain is required when shape='accumulation'",
        }

    # ---- Locate the declaration ----
    try:
        abs_path = derive_declaration_path(
            RecurrenceShape(shape), slug, domain=domain
        )
    except ValueError as e:
        return {"success": False, "error": "invalid_path", "message": str(e)}

    rel_path = abs_path[len("/workspace/"):] if abs_path.startswith("/workspace/") else abs_path
    um = UserMemory(auth.client, auth.user_id)
    content = await um.read(rel_path)
    if not content:
        return {
            "success": False,
            "error": "declaration_not_found",
            "message": f"no recurrence declaration at {abs_path}",
            "retry_hint": (
                "Verify the shape/slug/domain combination. For deliverables, "
                "the declaration lives at /workspace/reports/{slug}/_spec.yaml. "
                "For accumulation, /workspace/context/{domain}/_recurring.yaml "
                "with an entry slug. For actions, /workspace/operations/{slug}/_action.yaml. "
                "For maintenance, /workspace/_shared/back-office.yaml."
            ),
        }

    decls = parse_recurrence_yaml(content, abs_path, user_id=auth.user_id)
    target_decl = next((d for d in decls if d.slug == slug), None)
    if target_decl is None:
        return {
            "success": False,
            "error": "slug_not_found",
            "message": f"no entry with slug='{slug}' in {abs_path}",
        }

    if target_decl.paused:
        return {
            "success": False,
            "error": "paused",
            "message": (
                f"declaration {slug} is paused. Use ManageRecurrence("
                f"action='resume', shape='{shape}', slug='{slug}') to resume before firing."
            ),
        }

    # ---- Route through invocation_dispatcher ----
    # The dispatcher is the canonical Phase 2+ entry point for firing
    # recurrences. It currently adapts to task_pipeline.execute_task internally;
    # the Phase 3 atomic cutover replaces its body without touching this call
    # site. Singular Implementation discipline: one dispatch surface.
    from services.invocation_dispatcher import dispatch as _dispatch

    return await _dispatch(
        client=auth.client,
        user_id=auth.user_id,
        decl=target_decl,
        context=context,
    )
