"""
Proactive Review Pass — ADR-092 Phase 4

Lightweight Haiku review for proactive and coordinator deliverables.
Called by the scheduler on each proactive_next_review_at tick.

The agent reads its domain (via headless tools) and returns one of:
  {"action": "generate"}            → orchestration proceeds to full generation
  {"action": "observe", "note": …}  → note appended to deliverable_memory, no version
  {"action": "sleep", "until": …}   → proactive_next_review_at set to specified time

This is a two-phase execution model for proactive/coordinator modes:
  Phase A (this module): lightweight Haiku review — decide whether to act
  Phase B (deliverable_execution.py): full generation if Phase A returns "generate"

The review pass is intentionally cheap. Most cycles produce "observe" or "sleep".
Full Opus/Sonnet generation only runs when warranted.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Review pass uses Haiku — lightweight, cost-efficient
REVIEW_MODEL = "claude-haiku-4-5-20251001"
REVIEW_MAX_TOKENS = 1024
REVIEW_MAX_TOOL_ROUNDS = 3  # Allow a few lookups before deciding


def _build_review_system_prompt(deliverable: dict) -> str:
    """
    Build the review pass system prompt.

    Instructs the agent to assess its domain and return a structured
    JSON decision — not to generate content.
    """
    title = deliverable.get("title", "Untitled")
    deliverable_type = deliverable.get("deliverable_type", "custom")
    instructions = (deliverable.get("deliverable_instructions") or "").strip()
    memory = deliverable.get("deliverable_memory") or {}
    mode = deliverable.get("mode", "proactive")

    prompt = f"""You are performing a domain review for a {mode} deliverable: "{title}" (type: {deliverable_type}).

Your job is NOT to generate a deliverable. Your job is to assess whether conditions in your domain
warrant generating one right now.

## Your Domain Instructions
{instructions if instructions else "No specific instructions set. Use your judgment based on deliverable type and available context."}

## How to Decide

Use your available tools (Search, Read, List, RefreshPlatformContent) to check the current state
of your domain. Then return a JSON decision:

**generate** — conditions warrant producing a new version now. Use this when:
- Something significant has changed or emerged in your domain
- Enough has accumulated since the last generation to be worth surfacing
- A time-sensitive event is approaching that needs preparation

**observe** — nothing warrants generation yet, but worth noting something. Use this when:
- You see a development worth tracking but not yet significant enough to act on
- You want to record a pattern you're monitoring for future reference

**sleep** — domain is quiet, nothing to note. Use this when:
- Nothing meaningful has changed
- You want to defer the next review to a specific future time

## Response Format

Respond with ONLY a JSON object — no prose before or after:

```json
{{"action": "generate"}}
```

```json
{{"action": "observe", "note": "Brief description of what you observed and why it matters."}}
```

```json
{{"action": "sleep", "until": "2026-03-05T09:00:00Z", "note": "Optional reason for deferring."}}
```

The `until` field in sleep must be an ISO 8601 UTC timestamp. Default to 24 hours from now if unsure."""

    # Coordinator mode: mention write primitives
    if mode == "coordinator":
        prompt += """

## Coordinator Write Primitives

As a coordinator, you also have access to:

**CreateDeliverable** — create a new child deliverable when you detect a condition that warrants it
(e.g. an upcoming meeting needing prep, a stalled project, an emerging issue).
Check deliverable_memory.created_deliverables before creating to avoid duplicates.

**AdvanceDeliverableSchedule** — advance an existing deliverable to run now when conditions warrant it.

Use List or Search to find existing deliverables before creating or advancing.
Your JSON decision still controls the overall outcome — use `generate` only if THIS coordinator
deliverable should itself produce a new version (rare). Use `observe` or `sleep` for most cycles,
creating/advancing child deliverables as needed via tools during the review pass."""

    # Inject memory context
    review_log = memory.get("review_log", [])
    observations = memory.get("observations", [])
    last_generated_at = memory.get("last_generated_at")

    memory_parts = []
    if last_generated_at:
        memory_parts.append(f"**Last generated:** {last_generated_at}")
    if review_log:
        memory_parts.append("**Recent review log (last 5):**")
        for entry in review_log[-5:]:
            date = entry.get("date", "")
            action = entry.get("action", "")
            note = entry.get("note", "")
            memory_parts.append(f"- {date} [{action}]: {note}")
    if observations:
        memory_parts.append("**Pending observations:**")
        for obs in observations[-5:]:
            memory_parts.append(f"- {obs.get('date', '')}: {obs.get('note', '')}")

    # Coordinator mode: inject created_deliverables dedup log
    if mode == "coordinator":
        created_deliverables = memory.get("created_deliverables", [])
        if created_deliverables:
            memory_parts.append("**Created deliverables (dedup log — last 10):**")
            for cd in created_deliverables[-10:]:
                memory_parts.append(
                    f"- [{cd.get('date', '')}] {cd.get('title', '')} "
                    f"(key: {cd.get('dedup_key', 'none')})"
                )

    if memory_parts:
        prompt += "\n\n## Your Accumulated Memory\n" + "\n".join(memory_parts)

    return prompt


def _parse_review_response(text: str) -> dict:
    """
    Parse the agent's JSON review decision from its text response.

    Returns a dict with at least {"action": "generate"|"observe"|"sleep"}.
    Falls back to {"action": "observe", "note": "..."} on parse failure.
    """
    if not text:
        return {"action": "observe", "note": "Review pass returned empty response."}

    # Strip markdown code fences if present
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        # Remove first and last fence lines
        inner = [l for l in lines if not l.startswith("```")]
        clean = "\n".join(inner).strip()

    # Find the JSON object
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1:
        return {"action": "observe", "note": f"Could not parse review response: {text[:200]}"}

    try:
        parsed = json.loads(clean[start:end + 1])
        action = parsed.get("action", "")
        if action not in ("generate", "observe", "sleep"):
            return {"action": "observe", "note": f"Unknown action '{action}' in review response."}
        return parsed
    except json.JSONDecodeError as e:
        return {"action": "observe", "note": f"JSON parse error in review response: {e}"}


async def run_proactive_review(
    client,
    user_id: str,
    deliverable: dict,
) -> dict:
    """
    Run the lightweight Haiku review pass for a proactive/coordinator deliverable.

    Args:
        client: Supabase service client
        user_id: User UUID
        deliverable: Full deliverable dict from DB

    Returns:
        Parsed decision dict: {"action": "generate"|"observe"|"sleep", "note": ..., "until": ...}
        Never raises — on failure returns {"action": "observe", "note": "Review error: ..."}
    """
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import get_tools_for_mode, create_headless_executor

    title = deliverable.get("title", "Untitled")
    deliverable_id = deliverable.get("id")

    logger.info(f"[PROACTIVE_REVIEW] Starting review: {title} ({deliverable_id})")

    try:
        system_prompt = _build_review_system_prompt(deliverable)

        # Review prompt: ask the agent to assess its domain and decide
        user_message = (
            f"Review your domain for deliverable: {title}\n\n"
            "Use your tools to check current conditions, then respond with your JSON decision."
        )

        headless_tools = get_tools_for_mode("headless")
        executor = create_headless_executor(
            client,
            user_id,
            deliverable_sources=deliverable.get("sources"),
            coordinator_deliverable_id=deliverable.get("id"),
        )

        # Tool-use loop — agent may look at sources before deciding
        messages = [{"role": "user", "content": user_message}]
        rounds = 0
        final_text = ""

        while rounds < REVIEW_MAX_TOOL_ROUNDS:
            rounds += 1
            response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=headless_tools,
                model=REVIEW_MODEL,
                max_tokens=REVIEW_MAX_TOKENS,
            )

            if response.text:
                final_text = response.text

            # If no tool use, agent has decided — parse and return
            if not response.tool_uses:
                break

            # Execute tool calls and continue loop
            tool_results = []
            for tu in response.tool_uses:
                result = await executor(tu.name, tu.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result),
                })

            # Append assistant turn + tool results to messages
            assistant_content = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
            for tu in response.tool_uses:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tu.id,
                    "name": tu.name,
                    "input": tu.input,
                })
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        decision = _parse_review_response(final_text)
        logger.info(f"[PROACTIVE_REVIEW] Decision for {title}: {decision.get('action')}")
        return decision

    except Exception as e:
        logger.error(f"[PROACTIVE_REVIEW] Review failed for {title}: {e}")
        return {"action": "observe", "note": f"Review error: {e}"}


def apply_review_decision(
    client,
    deliverable: dict,
    decision: dict,
) -> None:
    """
    Apply the review decision to deliverable_memory and proactive_next_review_at.

    Does NOT trigger generation — caller handles that based on action=="generate".

    Args:
        client: Supabase service client
        deliverable: Full deliverable dict
        decision: Parsed decision from run_proactive_review()
    """
    deliverable_id = deliverable.get("id")
    action = decision.get("action", "observe")
    note = decision.get("note", "")
    now = datetime.now(timezone.utc)

    # Build review log entry
    log_entry: dict = {
        "date": now.date().isoformat(),
        "action": action,
        "note": note,
    }

    # Compute next review time
    if action == "sleep" and decision.get("until"):
        try:
            next_review = datetime.fromisoformat(decision["until"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            next_review = now + timedelta(hours=24)
    elif action == "generate":
        # After generation, review again in 24h by default
        next_review = now + timedelta(hours=24)
    else:
        # observe: check again in 24h
        next_review = now + timedelta(hours=24)

    log_entry["next_review_at"] = next_review.isoformat()

    # Read fresh memory, append log entry, cap at 50
    try:
        fresh = (
            client.table("deliverables")
            .select("deliverable_memory")
            .eq("id", deliverable_id)
            .single()
            .execute()
        )
        current_memory = (fresh.data or {}).get("deliverable_memory") or {}
    except Exception:
        current_memory = {}

    review_log = current_memory.get("review_log", [])
    review_log.append(log_entry)
    if len(review_log) > 50:
        review_log = review_log[-50:]

    updated_memory = {**current_memory, "review_log": review_log}
    if action == "generate":
        updated_memory["last_generated_at"] = now.isoformat()

    client.table("deliverables").update({
        "deliverable_memory": updated_memory,
        "proactive_next_review_at": next_review.isoformat(),
    }).eq("id", deliverable_id).execute()
