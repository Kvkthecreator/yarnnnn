"""
Signal Processing Service — ADR-068 Phase 3+4

Two-phase model (hardened 2026-02-20):

PHASE 1: ORCHESTRATION (Ephemeral)
- Extract behavioral signals from live platform APIs (signal_extraction.py)
- Reason with LLM (Haiku): "What does this user's world warrant?"
- Produce action recommendations (ephemeral SignalAction objects)

PHASE 2: SELECTIVE ARTIFACT CREATION (Persistent)
- create_signal_emergent: Create deliverable row (origin=signal_emergent) for novel work
- trigger_existing: Advance next_run_at of existing deliverable (pure orchestration)
- no_action: Signal doesn't meet threshold or is deduplicated

This is Path B (orchestrator). TP is not involved.

Signal-emergent deliverables are:
- Normal deliverable rows with origin=signal_emergent (provenance)
- Initially one-time (trigger_type=manual, no schedule)
- Can be promoted to recurring (origin stays signal_emergent)
- Delivered immediately (ADR-066 delivery-first)
- Tracked in signal_history for per-signal deduplication

Key insight: Signals observe platforms, deliverables synthesize across them.
The system creates deliverable artifacts when it detects novel work not covered
by existing configurations.
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

# Model for the reasoning pass — routing/classification call, Haiku for cost efficiency
SIGNAL_REASONING_MODEL = "claude-haiku-4-5-20251001"


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

    # Content sufficiency check (cold-start graceful exit)
    total_items = (
        (signal_summary.calendar_content.items_count if signal_summary.calendar_content else 0) +
        (signal_summary.gmail_content.items_count if signal_summary.gmail_content else 0) +
        (signal_summary.slack_content.items_count if signal_summary.slack_content else 0) +
        (signal_summary.notion_content.items_count if signal_summary.notion_content else 0)
    )

    if total_items < 3:
        logger.info(
            f"[SIGNAL_PROCESSING] Insufficient content for {user_id} "
            f"({total_items} items total), returning no_action"
        )
        return SignalProcessingResult(
            user_id=user_id,
            processed_at=datetime.now(timezone.utc),
            reasoning_summary="Insufficient platform content for signal detection",
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
    Execute the actions from signal processing (Phase 2: Selective Artifact Creation).

    Two execution paths:
    1. create_signal_emergent: Creates NEW deliverable row (artifact creation)
    2. trigger_existing: Updates existing deliverable's next_run_at (pure orchestration)

    Returns count of NEW deliverables created (not count of all actions executed).
    """
    created = 0
    triggered_ids: list[str] = []
    action_types: list[str] = []
    content_retained_count = 0

    for action in result.actions:
        action_types.append(action.action_type)

        if action.action_type == "create_signal_emergent":
            # ADR-053: Check deliverable limit before creating signal-emergent deliverable
            from services.platform_limits import check_deliverable_limit
            allowed, limit_msg = check_deliverable_limit(client, user_id)
            if not allowed:
                logger.info(
                    f"[SIGNAL_PROCESSING] Skipping signal-emergent creation for {user_id}: {limit_msg}"
                )
                continue

            # Artifact creation: Create new deliverable row with origin=signal_emergent
            deliverable_id = await _create_signal_emergent_deliverable(
                client, user_id, action
            )
            if deliverable_id:
                # Immediate execution (doesn't wait for next cron cycle)
                # ADR-080: Forward signal reasoning to headless mode
                await _queue_signal_emergent_execution(
                    client, user_id, deliverable_id,
                    signal_reasoning=result.reasoning_summary,
                    signal_context=action.signal_context,
                )
                created += 1
                triggered_ids.append(deliverable_id)

        elif action.action_type == "trigger_existing":
            # Pure orchestration: Advance existing deliverable's schedule (no new row)
            if action.trigger_deliverable_id:
                await _advance_deliverable_run(client, action.trigger_deliverable_id)
                triggered_ids.append(action.trigger_deliverable_id)
                logger.info(
                    f"[SIGNAL_PROCESSING] Triggered existing deliverable "
                    f"{action.trigger_deliverable_id} for {user_id}"
                )

    # ADR-072: Write signal_processed event to activity_log
    await _write_signal_processed_event(
        client=client,
        user_id=user_id,
        result=result,
        actions_taken=action_types,
        deliverables_triggered=triggered_ids,
        content_retained_count=content_retained_count,
    )

    return created


async def _write_signal_processed_event(
    client,
    user_id: str,
    result: SignalProcessingResult,
    actions_taken: list[str],
    deliverables_triggered: list[str],
    content_retained_count: int,
) -> None:
    """
    Write signal_processed event to activity_log (ADR-072: System State Awareness).

    Called after signal processing reasoning pass completes.
    Non-fatal — failure doesn't block signal processing.
    """
    from services.activity_log import write_activity

    signals_evaluated = len(result.actions)
    created_count = len([a for a in actions_taken if a == "create_signal_emergent"])
    triggered_count = len([a for a in actions_taken if a == "trigger_existing"])

    # Build human-readable summary
    if created_count > 0 and triggered_count > 0:
        summary = f"Signal processing: {created_count} deliverable(s) created, {triggered_count} triggered"
    elif created_count > 0:
        summary = f"Signal processing: {created_count} deliverable(s) created"
    elif triggered_count > 0:
        summary = f"Signal processing: {triggered_count} deliverable(s) triggered"
    else:
        summary = "Signal processing: no actions taken"

    # Use service client — activity_log RLS blocks user-scoped inserts
    try:
        from services.supabase import get_service_client
        await write_activity(
            client=get_service_client(),
            user_id=user_id,
            event_type="signal_processed",
            summary=summary,
            metadata={
                "signals_evaluated": signals_evaluated,
                "actions_taken": actions_taken,
                "deliverables_triggered": deliverables_triggered,
                "content_retained_count": content_retained_count,
                "reasoning_summary": result.reasoning_summary[:500] if result.reasoning_summary else None,
            },
        )
    except Exception as e:
        logger.warning(f"[SIGNAL_PROCESSING] Failed to write activity log: {e}")


async def _create_signal_emergent_deliverable(
    client,
    user_id: str,
    action: SignalAction,
) -> Optional[str]:
    """
    Create a signal-emergent deliverable row with deduplication check.

    This is ARTIFACT CREATION (Phase 2). Creates a persistent deliverable row that:
    - Has origin=signal_emergent (immutable provenance)
    - Is initially one-time (trigger_type=manual, no schedule)
    - Can be promoted to recurring (origin stays signal_emergent)
    - Is tracked in signal_history for per-signal deduplication

    Returns deliverable_id if created, None if deduplicated.
    """
    # Check signal_history for recent trigger (ADR-068 Phase 4 deduplication)
    signal_ref = action.signal_context.get("event_id") or action.signal_context.get("thread_id", "")
    if signal_ref and not await _check_signal_eligible(client, user_id, action.deliverable_type, signal_ref):
        logger.info(
            f"[SIGNAL_PROCESSING] Skipping {action.deliverable_type} for {signal_ref} — "
            f"already triggered within deduplication window"
        )
        return None

    now = datetime.now(timezone.utc).isoformat()
    deliverable_id = str(uuid4())

    # ADR-082: Use canonical type classification (handles aliases too)
    from routes.deliverables import get_type_classification
    type_classification = get_type_classification(action.deliverable_type)

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
            "origin": "signal_emergent",     # ADR-068
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }).execute()

        logger.info(
            f"[SIGNAL_PROCESSING] Created signal_emergent deliverable "
            f"{deliverable_id} ({action.deliverable_type}) for {user_id}: {action.title}"
        )

        # Record signal trigger in deduplication history (ADR-068 Phase 4)
        if signal_ref:
            await _record_signal_trigger(
                client, user_id, action.deliverable_type, signal_ref, deliverable_id
            )

        return deliverable_id

    except Exception as e:
        logger.error(
            f"[SIGNAL_PROCESSING] Failed to create deliverable for {user_id}: {e}"
        )
        return None


async def _queue_signal_emergent_execution(
    client,
    user_id: str,
    deliverable_id: str,
    signal_reasoning: str = "",
    signal_context: Optional[dict] = None,
) -> None:
    """
    Fetch the created deliverable and immediately execute it.

    Signal-emergent deliverables are created and executed in the same scheduler
    cycle — they don't wait for the next cron run.

    ADR-080: Signal reasoning and context are forwarded to the generation step
    via trigger_context, so the agent in headless mode knows WHY this
    deliverable was created and can use that to guide investigation.
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

        # ADR-080: Forward signal intelligence to generation step
        trigger = {
            "type": "signal_emergent",
            "signal_reasoning": signal_reasoning[:1000] if signal_reasoning else "",
            "signal_context": signal_context or {},
        }

        from services.deliverable_execution import execute_deliverable_generation
        await execute_deliverable_generation(
            client=client,
            user_id=user_id,
            deliverable=result.data,
            trigger_context=trigger,
        )

    except Exception as e:
        logger.error(
            f"[SIGNAL_PROCESSING] Execution failed for {deliverable_id}: {e}"
        )


async def _advance_deliverable_run(client, deliverable_id: str) -> None:
    """
    Advance an existing deliverable's next_run_at to now.

    This is PURE ORCHESTRATION (no artifact creation). Updates an existing
    recurring deliverable to run early in response to a signal, rather than
    creating a new one-time deliverable.

    Example: User has weekly meeting_prep deliverable. Signal detects urgent
    meeting tomorrow. Instead of creating NEW signal_emergent deliverable,
    advance the existing recurring one to run now.
    """
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
    """
    Build the structured prompt for content-based reasoning.

    Reframed (2026-02-20): This prompt presents LIVE PLATFORM CONTENT, not absence/thresholds.
    The LLM reasons about what's significant in the actual content, aligned with strategic
    deliverable types (daily_strategy_reflection, intelligence_brief, deep_research).
    """

    # Format platform content (not signals/thresholds)
    platform_sections = []

    if signal_summary.calendar_content and signal_summary.calendar_content.items_count > 0:
        calendar = signal_summary.calendar_content
        platform_sections.append(
            f"CALENDAR (upcoming {(calendar.time_range_end - calendar.time_range_start).days} days, {calendar.items_count} events):\n"
            f"{calendar.content_summary}"
        )

    if signal_summary.gmail_content and signal_summary.gmail_content.items_count > 0:
        gmail = signal_summary.gmail_content
        platform_sections.append(
            f"GMAIL (last {(gmail.time_range_end - gmail.time_range_start).days} days, {gmail.items_count} messages):\n"
            f"{gmail.content_summary}"
        )

    if signal_summary.slack_content and signal_summary.slack_content.items_count > 0:
        slack = signal_summary.slack_content
        platform_sections.append(
            f"SLACK (last {(slack.time_range_end - slack.time_range_start).days} days, {slack.items_count} messages):\n"
            f"{slack.content_summary}"
        )

    if signal_summary.notion_content and signal_summary.notion_content.items_count > 0:
        notion = signal_summary.notion_content
        platform_sections.append(
            f"NOTION ({notion.items_count} items):\n{notion.content_summary}"
        )

    if not platform_sections:
        platform_content_text = "PLATFORM CONTENT: No recent activity across connected platforms"
    else:
        platform_content_text = "\n\n".join(platform_sections)

    # Format user context (memory) - unchanged
    context_text = ""
    if user_context:
        lines = []
        for row in user_context[:15]:
            key = row.get("key", "")
            value = row.get("value", "")
            if key.startswith(("fact:", "preference:", "instruction:")):
                lines.append(f"- {value}")
        if lines:
            context_text = "USER CONTEXT (Memory Layer):\n" + "\n".join(lines)

    # Format recent activity - unchanged
    activity_text = ""
    if recent_activity:
        lines = []
        for event in recent_activity[:8]:
            lines.append(f"- {event.get('summary', '')}")
        activity_text = "RECENT SYSTEM ACTIVITY:\n" + "\n".join(lines)

    # Format existing deliverables with Layer 4 content (ADR-069) - unchanged
    deliverables_text = ""
    if existing_deliverables:
        lines = []
        for d in existing_deliverables[:10]:
            title = d.get('title', '')
            dtype = d.get('deliverable_type', '')
            next_run = d.get('next_run_at', 'manual')

            # Add content preview if available
            content = d.get('recent_content')
            version_date = d.get('recent_version_date')
            content_preview = ""

            if content and version_date:
                # Extract first 400 chars as preview
                preview = content[:400].replace('\n', ' ').strip()
                if len(content) > 400:
                    preview += "..."

                # Format date for readability
                try:
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(version_date.replace('Z', '+00:00'))
                    days_ago = (datetime.now(date_obj.tzinfo) - date_obj).days
                    if days_ago == 0:
                        date_str = "today"
                    elif days_ago == 1:
                        date_str = "yesterday"
                    else:
                        date_str = f"{days_ago} days ago"
                except (ValueError, TypeError):
                    date_str = version_date[:10]  # Fallback to ISO date

                content_preview = f"\n    Last output ({date_str}): {preview}"

            did = d.get("id", "")
            lines.append(
                f"- [{did}] {title} ({dtype}, next run: {next_run}){content_preview}"
            )
        deliverables_text = "EXISTING DELIVERABLES:\n" + "\n".join(lines)
    else:
        deliverables_text = "EXISTING DELIVERABLES: None configured"

    return f"""{platform_content_text}

{context_text}

{activity_text}

{deliverables_text}

Given the above platform content, what is significant? What patterns are emerging?
What deliverable would add value right now?

Respond with JSON only."""


_REASONING_SYSTEM_PROMPT = """You are the signal processing component of a productivity system.

You read LIVE PLATFORM CONTENT (emails, calendar events, Slack messages, Notion pages) and determine
what's significant enough to warrant creating or triggering a deliverable.

ARCHITECTURAL REFRAME (2026-02-20):
This is NOT absence/threshold detection. You reason about CONTENT SIGNIFICANCE, not gaps.
The question is: "Given what's actually here across platforms, what patterns are emerging,
what decisions are pending, what topic warrants synthesis?"

THREE STRATEGIC DELIVERABLE TYPES DEFINE "SIGNIFICANT" (ADR-082 active types):

1. **status_report** — Cross-platform synthesis of strategic movements, decision points, pattern recognition
   - Look for: Developments affecting strategic landscape, gap between stated priorities and actual activity
   - Example: Email thread reveals decision point on pricing, Slack shows team alignment shifting
   - Creates: Cross-platform synthesis summarizing key developments and strategic movements

2. **research_brief** — Entity-specific or topic-specific developments requiring investigation
   - Look for: What changed about this entity/topic? New information with specific impact? Topics needing deeper synthesis
   - Example: Calendar shows upcoming meeting with contact X, Gmail has 3 new threads from X's company
   - Example: "AI regulation" in 3 Slack channels, 2 email threads, upcoming meeting agenda
   - Creates: Research brief combining platform context + external sources

3. **custom** — Novel deliverable that doesn't fit standard types
   - Look for: Unique cross-platform patterns that warrant a one-off synthesis
   - Example: Unusual convergence of events requiring a tailored deliverable format
   - Creates: Custom deliverable with user-specific description

ACTION TYPES:

1. "trigger_existing" — An existing deliverable already handles this content (advance its schedule)
2. "create_signal_emergent" — No suitable recurring deliverable exists (create new one-time deliverable)
3. "no_action" — Content doesn't warrant action (insufficient significance, already covered, too sparse)

DECISION PRIORITY:
- First check EXISTING DELIVERABLES: Does one already handle this content? If yes, prefer "trigger_existing"
- Only use "create_signal_emergent" when the work is novel and no suitable recurring deliverable exists
- Use LAYER 4 CONTENT (recent deliverable output) to assess if existing deliverable is still relevant or stale

CONTENT SUFFICIENCY:
- If platform content is too sparse (only 1-2 items total), default to "no_action"
- Significance requires substance: multiple data points, clear pattern, or high-impact single event
- Don't force signal detection when content doesn't warrant it

EXAMPLES:

Content: Calendar has 1 upcoming meeting "Weekly Team Sync", Gmail has 2 internal emails, no Slack activity
→ no_action (routine internal activity, insufficient significance)

Content: Calendar shows "Client Meeting with Acme Corp CEO", Gmail has 3 threads about Acme pricing concerns, Slack #sales mentions Acme 4 times
→ create_signal_emergent (research_brief type, entity=Acme Corp, significant multi-platform pattern)

Content: User has existing status_report deliverable (last run: 3 days ago), Gmail shows 5 decision-point emails today, Slack shows strategy discussion
→ trigger_existing (advance the status_report to run now, fresh strategic movements detected)

Respond ONLY with valid JSON in this exact format:

For triggering existing deliverable:
{
  "actions": [
    {
      "action_type": "trigger_existing",
      "deliverable_type": "<type from EXISTING DELIVERABLES list>",
      "trigger_deliverable_id": "<UUID from brackets in EXISTING DELIVERABLES list>",
      "confidence": 0.85,
      "reasoning": "Existing deliverable handles this content, advancing schedule"
    }
  ],
  "reasoning": "Explanation of what content patterns warranted this action"
}

For creating new deliverable:
{
  "actions": [
    {
      "action_type": "create_signal_emergent",
      "deliverable_type": "research_brief",
      "title": "Research Brief: Acme Corp Developments",
      "description": "Synthesis of recent Acme-related activity across platforms",
      "confidence": 0.85,
      "sources": [{"type": "integration_import", "provider": "google", "source": "calendar"}],
      "signal_context": {"entity": "Acme Corp", "platforms": ["calendar", "gmail", "slack"]}
    }
  ],
  "reasoning": "Cross-platform pattern indicates significant entity developments"
}

If no action is warranted, return: {"actions": [], "reasoning": "Insufficient content significance"}
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

            # Validate trigger_deliverable_id is a UUID (LLM sometimes returns title instead)
            trigger_id = item.get("trigger_deliverable_id")
            if trigger_id and action_type == "trigger_existing":
                import re
                if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', trigger_id, re.I):
                    logger.warning(f"[SIGNAL_PROCESSING] Invalid trigger_deliverable_id (not UUID): {trigger_id[:60]}")
                    trigger_id = None

            actions.append(SignalAction(
                action_type=action_type,
                deliverable_type=item.get("deliverable_type", "custom"),
                title=item.get("title", "Untitled"),
                description=item.get("description", ""),
                confidence=float(item.get("confidence", 0.0)),
                sources=item.get("sources", []),
                trigger_deliverable_id=trigger_id,
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


# =============================================================================
# ADR-068 Phase 4: Per-Signal Deduplication
# =============================================================================

# Deduplication windows (hours) per signal type
DEDUPLICATION_WINDOWS = {
    "meeting_prep": 24,          # Don't recreate for same event within 24h
    "silence_alert": 168,        # 7 days - don't nag about same thread weekly
    "contact_drift": 336,        # 14 days - longer window for drift signals
}


async def _check_signal_eligible(
    client, user_id: str, signal_type: str, signal_ref: str
) -> bool:
    """
    Check if a signal is eligible to create a new deliverable.

    Returns False if the signal was triggered recently (within deduplication window).
    """
    from datetime import timedelta

    window_hours = DEDUPLICATION_WINDOWS.get(signal_type, 24)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    try:
        result = (
            client.table("signal_history")
            .select("id, last_triggered_at")
            .eq("user_id", user_id)
            .eq("signal_type", signal_type)
            .eq("signal_ref", signal_ref)
            .gte("last_triggered_at", cutoff.isoformat())
            .execute()
        )

        if result.data:
            # Signal was triggered recently — not eligible
            return False

        return True

    except Exception as e:
        logger.warning(f"[SIGNAL_DEDUP] Failed to check eligibility: {e}")
        # On error, allow signal through (fail-open)
        return True


async def _record_signal_trigger(
    client, user_id: str, signal_type: str, signal_ref: str, deliverable_id: str
) -> None:
    """
    Record that a signal triggered a deliverable creation.

    Upserts into signal_history to update last_triggered_at timestamp.
    """
    try:
        client.table("signal_history").upsert({
            "user_id": user_id,
            "signal_type": signal_type,
            "signal_ref": signal_ref,
            "last_triggered_at": datetime.now(timezone.utc).isoformat(),
            "deliverable_id": deliverable_id,
        }, on_conflict="user_id,signal_type,signal_ref").execute()

        logger.info(
            f"[SIGNAL_DEDUP] Recorded {signal_type} trigger for {signal_ref}"
        )

    except Exception as e:
        logger.warning(f"[SIGNAL_DEDUP] Failed to record trigger: {e}")
        # Non-fatal — signal was already created, history is just metadata
