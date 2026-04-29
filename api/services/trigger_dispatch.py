"""
Trigger Dispatch — ADR-088

Single decision point for all background agent triggers.

Three callers:
  unified_scheduler.py → process_agent()   trigger_type='schedule', strength='high'
  event_triggers.py    → execute_event_triggers() trigger_type='event',    strength='medium'
  [future signal path]                            trigger_type='signal',   strength='medium'

The high path delegates unchanged to execute_agent_generation().
The medium path appends an observation to agent_memory without generating a version.
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
    agent: dict,
    trigger_type: str,
    trigger_context: dict,
    signal_strength: str,
) -> dict:
    """
    Route a background trigger to the appropriate action.

    Args:
        client: Supabase client (service role)
        agent: Full agent dict from database
        trigger_type: 'schedule' | 'event' | 'signal'
        trigger_context: Type-specific payload passed through to execution
        signal_strength: 'high' | 'medium' | 'low'

    Returns:
        Dict with 'action', 'success', and type-specific keys.
        Never raises — dispatch failure should not crash the caller.
    """
    agent_id = agent.get("id")
    title = agent.get("title", "Untitled")

    if signal_strength == "high":
        return await _dispatch_high(client, agent, trigger_type, trigger_context)

    elif signal_strength == "medium":
        # ADR-092: Reactive mode upgrades to high when observation threshold is met
        mode = agent.get("_task_mode", "recurring")  # ADR-138: mode is on tasks
        if mode == "reactive":
            return await _dispatch_medium_reactive(client, agent, trigger_type, trigger_context)
        return await _dispatch_medium(client, agent, trigger_type, trigger_context)

    else:  # low
        user_id = agent.get("user_id")
        return await _dispatch_low(client, agent_id, user_id, trigger_type)


# =============================================================================
# High — full generation
# =============================================================================

async def _dispatch_high(
    client,
    agent: dict,
    trigger_type: str,
    trigger_context: dict,
) -> dict:
    """ADR-231 Phase 3.6.a.2: route through invocation_dispatcher.

    Resolves agent → recurrence declaration, then dispatch(decl). When no
    declaration assigns this agent, returns success=False with an
    explanatory message — the operator should author one via
    ManageRecurrence(action='create', ...).
    """
    from services.invocation_dispatcher import dispatch, find_declaration_for_agent
    from services.workspace import get_agent_slug

    agent_id = agent.get("id")
    user_id = agent.get("user_id")
    title = agent.get("title", "Untitled")
    agent_slug = get_agent_slug(agent)

    logger.info(f"[DISPATCH] high → generate: {title} ({agent_id}), trigger={trigger_type}")

    decl = find_declaration_for_agent(client, user_id, agent_slug)
    if decl is None:
        msg = (
            f"no recurrence declaration assigns agent '{agent_slug}'; "
            f"trigger ignored"
        )
        logger.warning(f"[DISPATCH] high skipped for {title}: {msg}")
        return {"action": "generated", "success": False, "error": msg}

    try:
        result = await dispatch(client, user_id, decl)
        return {"action": "generated", **result}
    except Exception as e:
        logger.error(f"[DISPATCH] high failed for {title}: {e}")
        return {"action": "generated", "success": False, "error": str(e)}


# =============================================================================
# Medium — observation append to workspace (ADR-106 Phase 2)
# =============================================================================

async def _dispatch_medium(
    client,
    agent: dict,
    trigger_type: str,
    trigger_context: dict,
) -> dict:
    """Append an observation to workspace without generating a version."""
    from services.activity_log import write_activity
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    user_id = agent.get("user_id")
    title = agent.get("title", "Untitled")

    logger.info(f"[DISPATCH] medium → workspace update: {title} ({agent_id}), trigger={trigger_type}")

    try:
        observation = _build_observation(trigger_type, trigger_context)

        # ADR-106: Write to workspace (source of truth)
        ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
        await ws.append_observation(observation, source=trigger_type)

        try:
            await write_activity(
                client=client,
                user_id=user_id,
                event_type="memory_written",
                summary=f"Trigger observation: {title}",
                event_ref=agent_id,
                metadata={"trigger_type": trigger_type, "note": observation[:200]},
            )
        except Exception:
            pass  # Non-fatal

        logger.info(f"[DISPATCH] ✓ workspace updated: {title}")
        return {"action": "memory_updated", "success": True, "agent_id": agent_id}

    except Exception as e:
        logger.error(f"[DISPATCH] medium failed for {title}: {e}")
        return {"action": "memory_updated", "success": False, "error": str(e)}


async def _dispatch_medium_reactive(
    client,
    agent: dict,
    trigger_type: str,
    trigger_context: dict,
) -> dict:
    """
    ADR-092: Reactive mode medium dispatch.
    ADR-106 Phase 2: Writes to workspace files (source of truth).

    Appends an observation to workspace memory/observations.md.
    When observation count >= threshold (default 5), upgrades to high — generates a
    version and clears the observation queue.
    """
    from services.activity_log import write_activity
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    user_id = agent.get("user_id")
    title = agent.get("title", "Untitled")
    # trigger_config column dropped (migration 129). Default threshold.
    threshold = 5

    logger.info(f"[DISPATCH] reactive medium: {title} ({agent_id}), threshold={threshold}")

    try:
        observation = _build_observation(trigger_type, trigger_context)

        # ADR-106: Write to workspace, get count for threshold
        ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
        count = await ws.append_observation(observation, source=trigger_type)

        if count >= threshold:
            # Threshold met — upgrade to generation, clear queue
            logger.info(f"[DISPATCH] reactive threshold met ({count}/{threshold}) → generate: {title}")
            await ws.clear_observations()
            await ws.set_state("last_generated_at", datetime.now(timezone.utc).isoformat())

            result = await _dispatch_high(client, agent, trigger_type, trigger_context)
            result["reactive_threshold_met"] = True
            result["observations_cleared"] = count
            return result
        else:
            # Below threshold — accumulate and wait
            try:
                await write_activity(
                    client=client,
                    user_id=user_id,
                    event_type="memory_written",
                    summary=f"Reactive observation ({count}/{threshold}): {title}",
                    event_ref=agent_id,
                    metadata={
                        "trigger_type": trigger_type,
                        "note": observation[:200],
                        "observation_count": count,
                        "threshold": threshold,
                    },
                )
            except Exception:
                pass  # Non-fatal

            logger.info(f"[DISPATCH] reactive observation {count}/{threshold}: {title}")
            return {
                "action": "memory_updated",
                "success": True,
                "agent_id": agent_id,
                "observation_count": count,
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
    agent_id: Optional[str],
    user_id: Optional[str],
    trigger_type: str,
) -> dict:
    """Log the trigger event with no LLM cost."""
    from services.activity_log import write_activity

    logger.debug(f"[DISPATCH] low → log only: {agent_id}, trigger={trigger_type}")

    if user_id:
        try:
            await write_activity(
                client=client,
                user_id=user_id,
                event_type="scheduler_heartbeat",
                summary=f"Low-signal trigger skipped: {trigger_type}",
                event_ref=agent_id,
                metadata={"trigger_type": trigger_type, "signal_strength": "low"},
            )
        except Exception:
            pass  # Non-fatal

    return {"action": "logged", "success": True}
