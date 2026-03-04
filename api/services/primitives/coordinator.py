"""
Coordinator Primitives — ADR-092 Phase 5

Headless-only write primitives for coordinator deliverables.

  CreateDeliverable         — creates a child deliverable with origin=coordinator_created
  AdvanceDeliverableSchedule — sets next_run_at=now on an existing deliverable

These replace signal processing's create_signal_emergent and trigger_existing actions.
Deduplication is the coordinator's responsibility via deliverable_memory.created_deliverables.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# CreateDeliverable
# =============================================================================

CREATE_DELIVERABLE_TOOL = {
    "name": "CreateDeliverable",
    "description": """Create a new deliverable on behalf of the user.

Use when your coordinator instructions tell you to create a specific piece of work
in response to a detected condition (e.g. an upcoming meeting, a flagged email thread,
a stalled project).

Before creating, check your deliverable_memory.created_deliverables to avoid
duplicating a deliverable for the same underlying event (use dedup_key for this).

The created deliverable will run once immediately (trigger_type=manual) unless
you specify a schedule. It appears in the user's deliverables list with
origin=coordinator_created, attributed to this coordinator.

Required: title, deliverable_type
Optional: deliverable_instructions, sources (inherits coordinator's if omitted),
          trigger_context (passed to the generation run), dedup_key (for deduplication)""",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title for the new deliverable"
            },
            "deliverable_type": {
                "type": "string",
                "description": "Type of deliverable (e.g. brief, status, digest, watch, deep_research, coordinator, custom)"
            },
            "deliverable_instructions": {
                "type": "string",
                "description": "Specific instructions for the child deliverable's generation"
            },
            "sources": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Data sources for the deliverable. Inherits coordinator sources if omitted."
            },
            "trigger_context": {
                "type": "object",
                "description": "Context passed to the generation run (e.g. meeting details, thread summary)"
            },
            "dedup_key": {
                "type": "string",
                "description": "Unique key for this event (e.g. 'brief:calendar_event_id_xyz'). Used to prevent duplicate creation."
            }
        },
        "required": ["title", "deliverable_type"]
    }
}


async def handle_create_deliverable(auth: Any, input: dict) -> dict:
    """
    Handle CreateDeliverable primitive.

    Creates a child deliverable with origin=coordinator_created.
    The coordinator_deliverable_id from auth context links it back.

    Returns {success, deliverable_id, title, message}
    """
    title = input.get("title", "").strip()
    deliverable_type = input.get("deliverable_type", "custom")
    deliverable_instructions = input.get("deliverable_instructions", "")
    sources = input.get("sources")
    trigger_context = input.get("trigger_context", {})
    dedup_key = input.get("dedup_key", "")

    if not title:
        return {"success": False, "error": "missing_title", "message": "title is required"}

    user_id = auth.user_id
    coordinator_id = getattr(auth, "coordinator_deliverable_id", None)

    # Inherit sources from coordinator if not specified
    if sources is None:
        sources = getattr(auth, "deliverable_sources", []) or []

    now = datetime.now(timezone.utc)

    try:
        deliverable_data = {
            "user_id": user_id,
            "title": title,
            "deliverable_type": deliverable_type,
            "mode": "recurring",  # child deliverables run once (manual trigger)
            "trigger_type": "manual",
            "origin": "coordinator_created",
            "status": "active",
            "sources": sources,
            "schedule": {"frequency": "once"},
            "next_run_at": now.isoformat(),  # run immediately
            "deliverable_instructions": deliverable_instructions,
        }

        result = (
            auth.client.table("deliverables")
            .insert(deliverable_data)
            .execute()
        )

        if not result.data:
            return {"success": False, "error": "insert_failed", "message": "Failed to create deliverable"}

        new_id = result.data[0]["id"]

        logger.info(f"[COORDINATOR] Created deliverable: {title} ({new_id}), coordinator={coordinator_id}")

        # Write activity log
        try:
            from services.activity_log import write_activity
            await write_activity(
                client=auth.client,
                user_id=user_id,
                event_type="deliverable_scheduled",
                summary=f"Coordinator created: {title}",
                event_ref=new_id,
                metadata={
                    "coordinator_id": coordinator_id,
                    "deliverable_type": deliverable_type,
                    "dedup_key": dedup_key,
                    "trigger_context": trigger_context,
                },
            )
        except Exception:
            pass  # Non-fatal

        # Append to coordinator's created_deliverables dedup log
        if coordinator_id:
            try:
                fresh = (
                    auth.client.table("deliverables")
                    .select("deliverable_memory")
                    .eq("id", coordinator_id)
                    .single()
                    .execute()
                )
                coord_memory = (fresh.data or {}).get("deliverable_memory") or {}
                created_log = coord_memory.get("created_deliverables", [])
                created_log.append({
                    "date": now.date().isoformat(),
                    "title": title,
                    "deliverable_id": new_id,
                    "dedup_key": dedup_key,
                })
                if len(created_log) > 100:
                    created_log = created_log[-100:]
                auth.client.table("deliverables").update({
                    "deliverable_memory": {**coord_memory, "created_deliverables": created_log},
                }).eq("id", coordinator_id).execute()
            except Exception:
                pass  # Non-fatal

        return {
            "success": True,
            "deliverable_id": new_id,
            "title": title,
            "dedup_key": dedup_key,
            "message": f"Created deliverable '{title}' — queued for immediate generation.",
        }

    except Exception as e:
        logger.error(f"[COORDINATOR] CreateDeliverable failed: {e}")
        return {"success": False, "error": "creation_failed", "message": str(e)}


# =============================================================================
# AdvanceDeliverableSchedule
# =============================================================================

ADVANCE_DELIVERABLE_SCHEDULE_TOOL = {
    "name": "AdvanceDeliverableSchedule",
    "description": """Advance an existing deliverable's schedule to run now.

Use when you detect that a condition warrants running an existing deliverable
immediately, rather than waiting for its next scheduled run.

This sets next_run_at to now — the scheduler will pick it up on the next 5-minute tick.
The deliverable's schedule is preserved; this is a one-time advancement.

Requires the deliverable_id of the target deliverable. Use Search or List
to find the right deliverable by title or type before calling this.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "deliverable_id": {
                "type": "string",
                "description": "UUID of the deliverable to advance"
            },
            "reason": {
                "type": "string",
                "description": "Brief reason for advancing (logged to activity log)"
            }
        },
        "required": ["deliverable_id"]
    }
}


async def handle_advance_deliverable_schedule(auth: Any, input: dict) -> dict:
    """
    Handle AdvanceDeliverableSchedule primitive.

    Sets next_run_at=now so the scheduler picks it up immediately.
    Preserves the deliverable's existing schedule config.

    Returns {success, deliverable_id, message}
    """
    deliverable_id = input.get("deliverable_id", "").strip()
    reason = input.get("reason", "Coordinator-initiated advancement")

    if not deliverable_id:
        return {"success": False, "error": "missing_id", "message": "deliverable_id is required"}

    user_id = auth.user_id
    now = datetime.now(timezone.utc)

    try:
        # Verify the deliverable belongs to this user and is active
        check = (
            auth.client.table("deliverables")
            .select("id, title, status, user_id")
            .eq("id", deliverable_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )

        if not check or not check.data:
            return {
                "success": False,
                "error": "not_found",
                "message": f"Deliverable {deliverable_id} not found or not owned by this user",
            }

        d = check.data
        if d.get("status") not in ("active",):
            return {
                "success": False,
                "error": "not_active",
                "message": f"Deliverable '{d.get('title')}' is {d.get('status')} — cannot advance",
            }

        auth.client.table("deliverables").update({
            "next_run_at": now.isoformat(),
        }).eq("id", deliverable_id).execute()

        logger.info(f"[COORDINATOR] Advanced schedule: {d.get('title')} ({deliverable_id}), reason={reason}")

        try:
            from services.activity_log import write_activity
            await write_activity(
                client=auth.client,
                user_id=user_id,
                event_type="deliverable_scheduled",
                summary=f"Coordinator advanced: {d.get('title')}",
                event_ref=deliverable_id,
                metadata={
                    "coordinator_id": getattr(auth, "coordinator_deliverable_id", None),
                    "reason": reason,
                    "advanced_at": now.isoformat(),
                },
            )
        except Exception:
            pass  # Non-fatal

        return {
            "success": True,
            "deliverable_id": deliverable_id,
            "title": d.get("title"),
            "message": f"Advanced '{d.get('title')}' — will run on next scheduler tick.",
        }

    except Exception as e:
        logger.error(f"[COORDINATOR] AdvanceDeliverableSchedule failed: {e}")
        return {"success": False, "error": "advance_failed", "message": str(e)}
