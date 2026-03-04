"""
Trigger Dispatch — ADR-088

Single decision point for all background deliverable triggers.

Three callers:
  unified_scheduler.py → process_deliverable()   trigger_type='schedule', strength='high'
  event_triggers.py    → execute_event_triggers() trigger_type='event',    strength='medium'
  [future signal path]                            trigger_type='signal',   strength='medium'

The high path delegates unchanged to execute_deliverable_generation().
The medium path appends an observation to deliverable_memory without generating a version.
The low path logs only (zero LLM cost).

This module is backend-only. POST /chat (TP chat) does not go through dispatch.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


async def dispatch_trigger(
    client,
    deliverable: dict,
    trigger_type: str,
    trigger_context: dict,
    signal_strength: str,
) -> dict:
    """
    Route a background trigger to the appropriate action.

    Args:
        client: Supabase client (service role)
        deliverable: Full deliverable dict from database
        trigger_type: 'schedule' | 'event' | 'signal'
        trigger_context: Type-specific payload passed through to execution
        signal_strength: 'high' | 'medium' | 'low'

    Returns:
        Dict with 'action', 'success', and type-specific keys.
        Never raises — dispatch failure should not crash the caller.
    """
    deliverable_id = deliverable.get("id")
    title = deliverable.get("title", "Untitled")

    if signal_strength == "high":
        return await _dispatch_high(client, deliverable, trigger_type, trigger_context)

    elif signal_strength == "medium":
        # ADR-092: Reactive mode upgrades to high when observation threshold is met
        mode = deliverable.get("mode", "recurring")
        if mode == "reactive":
            return await _dispatch_medium_reactive(client, deliverable, trigger_type, trigger_context)
        return await _dispatch_medium(client, deliverable, trigger_type, trigger_context)

    else:  # low
        user_id = deliverable.get("user_id")
        return await _dispatch_low(client, deliverable_id, user_id, trigger_type)


# =============================================================================
# High — full generation
# =============================================================================

async def _dispatch_high(
    client,
    deliverable: dict,
    trigger_type: str,
    trigger_context: dict,
) -> dict:
    """Delegate to execute_deliverable_generation(), pass result through."""
    from services.deliverable_execution import execute_deliverable_generation

    deliverable_id = deliverable.get("id")
    user_id = deliverable.get("user_id")
    title = deliverable.get("title", "Untitled")

    logger.info(f"[DISPATCH] high → generate: {title} ({deliverable_id}), trigger={trigger_type}")

    try:
        result = await execute_deliverable_generation(
            client=client,
            user_id=user_id,
            deliverable=deliverable,
            trigger_context=trigger_context,
        )
        # Merge action key into result — callers still get success/version_id/etc.
        return {"action": "generated", **result}
    except Exception as e:
        logger.error(f"[DISPATCH] high failed for {title}: {e}")
        return {"action": "generated", "success": False, "error": str(e)}


# =============================================================================
# Medium — observation append to deliverable_memory
# =============================================================================

async def _dispatch_medium(
    client,
    deliverable: dict,
    trigger_type: str,
    trigger_context: dict,
) -> dict:
    """Append an observation to deliverable_memory without generating a version."""
    from services.activity_log import write_activity

    deliverable_id = deliverable.get("id")
    user_id = deliverable.get("user_id")
    title = deliverable.get("title", "Untitled")

    logger.info(f"[DISPATCH] medium → memory update: {title} ({deliverable_id}), trigger={trigger_type}")

    try:
        observation = _build_observation(trigger_type, trigger_context)

        # Fresh read — optimistic concurrency (safe at single-user scale)
        fresh = (
            client.table("deliverables")
            .select("deliverable_memory")
            .eq("id", deliverable_id)
            .single()
            .execute()
        )
        current_memory = (fresh.data or {}).get("deliverable_memory") or {}

        observations = current_memory.get("observations", [])
        observations.append({
            "date": datetime.now(timezone.utc).date().isoformat(),
            "source": trigger_type,
            "note": observation,
        })
        # Cap at 20, keep most recent
        if len(observations) > 20:
            observations = observations[-20:]

        updated_memory = {**current_memory, "observations": observations}

        client.table("deliverables").update(
            {"deliverable_memory": updated_memory}
        ).eq("id", deliverable_id).execute()

        try:
            await write_activity(
                client=client,
                user_id=user_id,
                event_type="memory_written",
                summary=f"Trigger observation: {title}",
                event_ref=deliverable_id,
                metadata={"trigger_type": trigger_type, "note": observation[:200]},
            )
        except Exception:
            pass  # Non-fatal

        logger.info(f"[DISPATCH] ✓ memory updated: {title}")
        return {"action": "memory_updated", "success": True, "deliverable_id": deliverable_id}

    except Exception as e:
        logger.error(f"[DISPATCH] medium failed for {title}: {e}")
        return {"action": "memory_updated", "success": False, "error": str(e)}


async def _dispatch_medium_reactive(
    client,
    deliverable: dict,
    trigger_type: str,
    trigger_context: dict,
) -> dict:
    """
    ADR-092: Reactive mode medium dispatch.

    Appends an observation to deliverable_memory.observations.
    When len(observations) >= threshold (default 5), upgrades to high — generates a
    version and clears the observation queue.
    """
    from services.activity_log import write_activity

    deliverable_id = deliverable.get("id")
    user_id = deliverable.get("user_id")
    title = deliverable.get("title", "Untitled")
    trigger_config = deliverable.get("trigger_config") or {}
    threshold = trigger_config.get("observation_threshold", 5)

    logger.info(f"[DISPATCH] reactive medium: {title} ({deliverable_id}), threshold={threshold}")

    try:
        observation = _build_observation(trigger_type, trigger_context)

        # Fresh read
        fresh = (
            client.table("deliverables")
            .select("deliverable_memory")
            .eq("id", deliverable_id)
            .single()
            .execute()
        )
        current_memory = (fresh.data or {}).get("deliverable_memory") or {}

        observations = current_memory.get("observations", [])
        observations.append({
            "date": datetime.now(timezone.utc).date().isoformat(),
            "source": trigger_type,
            "note": observation,
        })
        if len(observations) > 20:
            observations = observations[-20:]

        if len(observations) >= threshold:
            # Threshold met — upgrade to generation, clear queue
            logger.info(f"[DISPATCH] reactive threshold met ({len(observations)}/{threshold}) → generate: {title}")
            updated_memory = {
                **current_memory,
                "observations": [],  # cleared after generation
                "last_generated_at": datetime.now(timezone.utc).isoformat(),
            }
            client.table("deliverables").update(
                {"deliverable_memory": updated_memory}
            ).eq("id", deliverable_id).execute()

            result = await _dispatch_high(client, deliverable, trigger_type, trigger_context)
            result["reactive_threshold_met"] = True
            result["observations_cleared"] = len(observations)
            return result
        else:
            # Below threshold — accumulate and wait
            updated_memory = {**current_memory, "observations": observations}
            client.table("deliverables").update(
                {"deliverable_memory": updated_memory}
            ).eq("id", deliverable_id).execute()

            try:
                await write_activity(
                    client=client,
                    user_id=user_id,
                    event_type="memory_written",
                    summary=f"Reactive observation ({len(observations)}/{threshold}): {title}",
                    event_ref=deliverable_id,
                    metadata={
                        "trigger_type": trigger_type,
                        "note": observation[:200],
                        "observation_count": len(observations),
                        "threshold": threshold,
                    },
                )
            except Exception:
                pass  # Non-fatal

            logger.info(f"[DISPATCH] reactive observation {len(observations)}/{threshold}: {title}")
            return {
                "action": "memory_updated",
                "success": True,
                "deliverable_id": deliverable_id,
                "observation_count": len(observations),
                "threshold": threshold,
            }

    except Exception as e:
        logger.error(f"[DISPATCH] reactive medium failed for {title}: {e}")
        return {"action": "memory_updated", "success": False, "error": str(e)}


def _build_observation(trigger_type: str, trigger_context: dict) -> str:
    """Build a human-readable observation string from trigger context."""
    if trigger_type == "event":
        platform = trigger_context.get("platform", "platform")
        event_type = trigger_context.get("event_type", "event")
        resource_id = trigger_context.get("resource_id", "")
        preview = trigger_context.get("content_preview", "")
        base = f"{platform.capitalize()} {event_type} in {resource_id}"
        if preview:
            preview_trimmed = preview[:150].strip()
            return f"{base}: {preview_trimmed}"
        return base

    elif trigger_type == "signal":
        reasoning = trigger_context.get("signal_reasoning", "")
        signal_type = trigger_context.get("signal_type", "signal")
        if reasoning:
            return f"Signal ({signal_type}): {reasoning[:200]}"
        return f"Signal detected: {signal_type}"

    else:
        return f"Background trigger: {trigger_type}"


# =============================================================================
# Low — log only
# =============================================================================

async def _dispatch_low(
    client,
    deliverable_id: Optional[str],
    user_id: Optional[str],
    trigger_type: str,
) -> dict:
    """Log the trigger event with no LLM cost."""
    from services.activity_log import write_activity

    logger.debug(f"[DISPATCH] low → log only: {deliverable_id}, trigger={trigger_type}")

    if user_id:
        try:
            await write_activity(
                client=client,
                user_id=user_id,
                event_type="scheduler_heartbeat",
                summary=f"Low-signal trigger skipped: {trigger_type}",
                event_ref=deliverable_id,
                metadata={"trigger_type": trigger_type, "signal_strength": "low"},
            )
        except Exception:
            pass  # Non-fatal

    return {"action": "logged", "success": True}
