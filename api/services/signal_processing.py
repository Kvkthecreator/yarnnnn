"""
Signal Processing Service — ADR-068

Single LLM call (Haiku) that reasons over a SignalSummary and decides what
the user's platform world warrants. Creates signal-emergent deliverables
and queues their execution.

This is Path B (orchestrator). TP is not involved.

Actions this service can take:
- create_signal_emergent: Create a deliverable (origin=signal_emergent,
  trigger_type=manual) and immediately queue execution
- trigger_existing: Advance the next_run of an existing deliverable
- no_action: Signal doesn't meet confidence threshold or is deduplicated

Signal-emergent deliverables start with governance=manual, so the generated
version lands as 'staged' for user review before delivery.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from services.signal_extraction import SignalSummary

logger = logging.getLogger(__name__)

# Minimum confidence to act on a signal
CONFIDENCE_THRESHOLD = 0.60

# Haiku for the reasoning pass — this is a routing/classification call
SIGNAL_REASONING_MODEL = "claude-haiku-4-20250514"

# Type config for the first signal-emergent type: meeting_prep
MEETING_PREP_TYPE_CLASSIFICATION = {
    "binding": "platform_bound",
    "primary_platform": "google",
    "temporal_pattern": "event_driven",
    "freshness_requirement_hours": 1,
}


@dataclass
class SignalAction:
    """A single action to take based on signal processing."""
    action_type: str              # create_signal_emergent | trigger_existing | no_action
    deliverable_type: str         # meeting_prep, gmail_inbox_brief, etc.
    title: str
    description: str
    confidence: float
    sources: list[dict] = field(default_factory=list)
    trigger_deliverable_id: Optional[str] = None  # For trigger_existing
    signal_context: dict = field(default_factory=dict)  # For logging/debugging


@dataclass
class SignalProcessingResult:
    """Result of the signal processing reasoning pass."""
    user_id: str
    processed_at: datetime
    actions: list[SignalAction] = field(default_factory=list)
    reasoning_summary: str = ""   # For logging only — not stored


async def process_signal(
    client,
    user_id: str,
    signal_summary: SignalSummary,
    user_context: list[dict],
    recent_activity: list[dict],
    existing_deliverables: list[dict],
) -> SignalProcessingResult:
    """
    Reason over the signal summary and decide what to create or trigger.

    Args:
        client: Supabase service-role client
        user_id: The user
        signal_summary: Output of extract_signal_summary()
        user_context: Rows from user_context table (memory)
        recent_activity: Recent rows from activity_log
        existing_deliverables: Active/paused deliverables for deduplication

    Returns:
        SignalProcessingResult with list of actions to execute
    """
    if not signal_summary.has_signals:
        logger.info(f"[SIGNAL_PROCESSING] No signals for {user_id}, skipping")
        return SignalProcessingResult(
            user_id=user_id,
            processed_at=datetime.now(timezone.utc),
        )

    # Build the reasoning prompt
    prompt = _build_reasoning_prompt(
        signal_summary=signal_summary,
        user_context=user_context,
        recent_activity=recent_activity,
        existing_deliverables=existing_deliverables,
    )

    # Single LLM call — Haiku for cost efficiency
    from services.anthropic import chat_completion

    try:
        raw_response = await chat_completion(
            messages=[{"role": "user", "content": prompt}],
            system=_REASONING_SYSTEM_PROMPT,
            model=SIGNAL_REASONING_MODEL,
            max_tokens=1000,
        )
    except Exception as e:
        logger.error(f"[SIGNAL_PROCESSING] LLM call failed for {user_id}: {e}")
        return SignalProcessingResult(
            user_id=user_id,
            processed_at=datetime.now(timezone.utc),
        )

    # Parse structured JSON response
    actions, reasoning = _parse_reasoning_response(raw_response, signal_summary)

    # Apply confidence filter and deduplication
    filtered_actions = _filter_actions(actions, existing_deliverables)

    result = SignalProcessingResult(
        user_id=user_id,
        processed_at=datetime.now(timezone.utc),
        actions=filtered_actions,
        reasoning_summary=reasoning,
    )

    logger.info(
        f"[SIGNAL_PROCESSING] user={user_id}: "
        f"{len(filtered_actions)} actions after filtering "
        f"(raw={len(actions)})"
    )

    return result


async def execute_signal_actions(
    client,
    user_id: str,
    result: SignalProcessingResult,
) -> int:
    """
    Execute the actions from signal processing.

    Creates signal-emergent deliverables and queues execution.
    Returns count of deliverables created.
    """
    created = 0

    for action in result.actions:
        if action.action_type == "create_signal_emergent":
            deliverable_id = await _create_signal_emergent_deliverable(
                client, user_id, action
            )
            if deliverable_id:
                await _queue_signal_emergent_execution(client, user_id, deliverable_id)
                created += 1

        elif action.action_type == "trigger_existing":
            if action.trigger_deliverable_id:
                await _advance_deliverable_run(client, action.trigger_deliverable_id)

    return created


async def _create_signal_emergent_deliverable(
    client,
    user_id: str,
    action: SignalAction,
) -> Optional[str]:
    """Create a signal-emergent deliverable row."""
    now = datetime.now(timezone.utc).isoformat()
    deliverable_id = str(uuid4())

    # Type classification — meeting_prep is the first supported type
    type_classification = MEETING_PREP_TYPE_CLASSIFICATION if (
        action.deliverable_type == "meeting_prep"
    ) else {
        "binding": "cross_platform",
        "temporal_pattern": "event_driven",
        "freshness_requirement_hours": 4,
    }

    try:
        client.table("deliverables").insert({
            "id": deliverable_id,
            "user_id": user_id,
            "title": action.title,
            "description": action.description,
            "deliverable_type": action.deliverable_type,
            "type_classification": type_classification,
            "type_config": {},
            "schedule": {},                  # No schedule — one-time
            "trigger_type": "manual",        # ADR-068: one-time, no recurring schedule
            "sources": action.sources,
            "governance": "manual",          # Always requires user review
            "origin": "signal_emergent",     # ADR-068
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }).execute()

        logger.info(
            f"[SIGNAL_PROCESSING] Created signal_emergent deliverable "
            f"{deliverable_id} ({action.deliverable_type}) for {user_id}: {action.title}"
        )
        return deliverable_id

    except Exception as e:
        logger.error(
            f"[SIGNAL_PROCESSING] Failed to create deliverable for {user_id}: {e}"
        )
        return None


async def _queue_signal_emergent_execution(client, user_id: str, deliverable_id: str) -> None:
    """
    Fetch the created deliverable and immediately execute it.

    Signal-emergent deliverables are created and executed in the same scheduler
    cycle — they don't wait for the next cron run.
    """
    try:
        result = (
            client.table("deliverables")
            .select("*")
            .eq("id", deliverable_id)
            .single()
            .execute()
        )
        if not result.data:
            logger.warning(f"[SIGNAL_PROCESSING] Deliverable {deliverable_id} not found after creation")
            return

        from services.deliverable_execution import execute_deliverable_generation
        await execute_deliverable_generation(
            client=client,
            user_id=user_id,
            deliverable=result.data,
            trigger_context={"type": "signal_emergent"},
        )

    except Exception as e:
        logger.error(
            f"[SIGNAL_PROCESSING] Execution failed for {deliverable_id}: {e}"
        )


async def _advance_deliverable_run(client, deliverable_id: str) -> None:
    """Advance an existing deliverable's next_run_at to now."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        client.table("deliverables").update({
            "next_run_at": now,
            "updated_at": now,
        }).eq("id", deliverable_id).execute()
        logger.info(f"[SIGNAL_PROCESSING] Advanced next_run for {deliverable_id}")
    except Exception as e:
        logger.warning(f"[SIGNAL_PROCESSING] Failed to advance run for {deliverable_id}: {e}")


def _build_reasoning_prompt(
    signal_summary: SignalSummary,
    user_context: list[dict],
    recent_activity: list[dict],
    existing_deliverables: list[dict],
) -> str:
    """Build the structured prompt for the reasoning pass."""

    # Format calendar signals
    calendar_text = ""
    if signal_summary.calendar_signals:
        items = []
        for sig in signal_summary.calendar_signals:
            attendees = ", ".join(sig.attendee_emails[:5]) if sig.attendee_emails else "no attendees listed"
            items.append(
                f"- \"{sig.title}\" in {sig.hours_until}h "
                f"(attendees: {attendees})"
            )
        calendar_text = "UPCOMING EVENTS (next 48h):\n" + "\n".join(items)
    else:
        calendar_text = "UPCOMING EVENTS: None in next 48h"

    # Format silence signals
    silence_text = ""
    if signal_summary.silence_signals:
        items = []
        for sig in signal_summary.silence_signals:
            items.append(
                f"- Thread \"{sig.thread_subject}\" with {sig.sender}: "
                f"quiet for {sig.days_silent} days"
            )
        silence_text = "QUIET THREADS (no recent activity):\n" + "\n".join(items)
    else:
        silence_text = "QUIET THREADS: None detected"

    # Format user context (memory)
    context_text = ""
    if user_context:
        lines = []
        for row in user_context[:15]:
            key = row.get("key", "")
            value = row.get("value", "")
            if key.startswith(("fact:", "preference:", "instruction:")):
                lines.append(f"- {value}")
        if lines:
            context_text = "USER CONTEXT:\n" + "\n".join(lines)

    # Format recent activity
    activity_text = ""
    if recent_activity:
        lines = []
        for event in recent_activity[:8]:
            lines.append(f"- {event.get('summary', '')}")
        activity_text = "RECENT SYSTEM ACTIVITY:\n" + "\n".join(lines)

    # Format existing deliverables for deduplication awareness
    deliverables_text = ""
    if existing_deliverables:
        lines = []
        for d in existing_deliverables[:10]:
            lines.append(
                f"- {d.get('title')} ({d.get('deliverable_type')}, "
                f"next run: {d.get('next_run_at', 'manual')})"
            )
        deliverables_text = "EXISTING DELIVERABLES:\n" + "\n".join(lines)
    else:
        deliverables_text = "EXISTING DELIVERABLES: None configured"

    return f"""{calendar_text}

{silence_text}

{context_text}

{activity_text}

{deliverables_text}

Based on the above, what does this user's world warrant right now?
Respond with JSON only."""


_REASONING_SYSTEM_PROMPT = """You are the signal processing component of a productivity system.
Your job is to look at a snapshot of a user's platform world and decide what proactive work, if any, is warranted.

You can suggest one of three action types:
- "create_signal_emergent": Create and immediately run a one-time deliverable
- "trigger_existing": Advance the schedule of an existing deliverable that already covers this signal
- "no_action": The signals don't warrant anything (too low confidence, already covered, or not meaningful)

For meeting_prep: suggest it if there's a calendar event in the next 48h with external attendees that doesn't already have a meeting_prep deliverable running for it.

Respond ONLY with valid JSON in this exact format:
{
  "actions": [
    {
      "action_type": "create_signal_emergent",
      "deliverable_type": "meeting_prep",
      "title": "Meeting Prep: <event title>",
      "description": "One-time brief for <event> with <attendees>",
      "confidence": 0.85,
      "sources": [{"type": "integration_import", "provider": "google", "source": "calendar"}],
      "signal_context": {"event_title": "...", "hours_until": 12, "attendees": ["..."]}
    }
  ],
  "reasoning": "Brief explanation of decisions made"
}

If no action is warranted, return: {"actions": [], "reasoning": "..."}
Confidence must be 0.0–1.0. Only suggest actions with confidence >= 0.60."""


def _parse_reasoning_response(raw_response: str, signal_summary: SignalSummary) -> tuple[list[SignalAction], str]:
    """Parse the LLM's JSON response into SignalAction objects."""
    try:
        # Strip markdown code fences if present
        text = raw_response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        data = json.loads(text)
        actions_raw = data.get("actions", [])
        reasoning = data.get("reasoning", "")

        actions = []
        for item in actions_raw:
            action_type = item.get("action_type", "no_action")
            if action_type not in ("create_signal_emergent", "trigger_existing", "no_action"):
                continue

            actions.append(SignalAction(
                action_type=action_type,
                deliverable_type=item.get("deliverable_type", "custom"),
                title=item.get("title", "Untitled"),
                description=item.get("description", ""),
                confidence=float(item.get("confidence", 0.0)),
                sources=item.get("sources", []),
                trigger_deliverable_id=item.get("trigger_deliverable_id"),
                signal_context=item.get("signal_context", {}),
            ))

        return actions, reasoning

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"[SIGNAL_PROCESSING] Failed to parse reasoning response: {e}")
        return [], ""


def _filter_actions(
    actions: list[SignalAction],
    existing_deliverables: list[dict],
) -> list[SignalAction]:
    """Apply confidence threshold and basic deduplication."""
    filtered = []
    seen_types: set[str] = set()

    # Index existing deliverables by type for deduplication
    existing_types = {d.get("deliverable_type") for d in existing_deliverables}

    for action in actions:
        # Confidence threshold
        if action.confidence < CONFIDENCE_THRESHOLD:
            logger.info(
                f"[SIGNAL_PROCESSING] Skipping {action.deliverable_type} "
                f"(confidence {action.confidence} < {CONFIDENCE_THRESHOLD})"
            )
            continue

        # Don't create a signal_emergent deliverable if a user-configured one of
        # the same type is already scheduled to run today
        if action.action_type == "create_signal_emergent":
            if action.deliverable_type in existing_types:
                logger.info(
                    f"[SIGNAL_PROCESSING] Skipping {action.deliverable_type} "
                    f"— existing deliverable of same type already configured"
                )
                continue

        # One action per deliverable type per cycle
        type_key = f"{action.action_type}:{action.deliverable_type}"
        if type_key in seen_types:
            continue
        seen_types.add(type_key)

        filtered.append(action)

    return filtered
