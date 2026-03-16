"""
Proactive Review Pass — TP's Per-Agent Supervisory Check

ADR-092 Phase 4, reframed by ADR-111 Phase 4 as TP's supervisory capability.

Lightweight Haiku review for proactive and coordinator agents.
Invoked by TP's Heartbeat (composer._run_supervisory_review) on each review cadence.

The agent reads its domain (via headless tools) and returns one of:
  {"action": "generate"}            → orchestration proceeds to full generation
  {"action": "observe", "note": …}  → note appended to workspace, no version
  {"action": "sleep", "until": …}   → proactive_next_review_at deferred

Conceptual ownership: TP (meta-cognitive layer) owns the decision to review
and the decision to act on the assessment. The agent provides domain expertise.

Two-phase execution:
  Phase A (this module): lightweight Haiku review — agent assesses domain
  Phase B (agent_execution.py): full generation if Phase A returns "generate"

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
REVIEW_MAX_TOOL_ROUNDS = 5  # Enough for broad scan + focused lookups + final decision


async def _build_review_system_prompt(agent: dict, client=None) -> str:
    """
    Build the review pass system prompt.

    ADR-106 Phase 2: Reads instructions and memory from workspace files
    (source of truth), not from agent DB columns.
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    title = agent.get("title", "Untitled")
    skill = agent.get("skill", "custom")
    mode = agent.get("mode", "proactive")

    # ADR-106: Load from workspace (source of truth)
    ws = AgentWorkspace(client, agent.get("user_id"), get_agent_slug(agent))
    await ws.ensure_seeded(agent)  # Lazy migration

    instructions = (await ws.read("AGENT.md") or "").strip()
    observations = await ws.get_observations()
    review_log = await ws.get_review_log()
    created_agents = await ws.get_created_agents()
    last_generated_at = await ws.get_state("last_generated_at")

    prompt = f"""You are performing a domain review for a {mode} agent: "{title}" (skill: {skill}).

Your job is NOT to generate an agent. Your job is to assess whether conditions in your domain
warrant generating one right now.

## Your Domain Instructions
{instructions if instructions else "No specific instructions set. Use your judgment based on agent skill and available context."}

## How to Decide

Use your available tools (Search, Read, List, WebSearch, RefreshPlatformContent) to check the current state
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

    # Research/synthesize skill with autonomous scope: signal-driven review
    if skill in ("research", "synthesize") and agent.get("scope") == "autonomous":
        prompt += """

## Proactive Insights — Signal Detection

Your domain is the user's entire connected work context. Your job is to find **emerging themes** worth investigating externally.

**How to scan:**
Use **Search** with SHORT, SPECIFIC queries (1-3 words each). Run multiple searches, one per topic:
- Search("decision") or Search("blocked") — what's being decided or stalled?
- Search("meeting") or Search("investor") — who's new, what's upcoming?
- Search("launch") or Search("release") — what's shipping?
- Search("competitor") or Search("market") — external awareness signals?
- Search("") with no query to get recent items across all platforms

DO NOT combine multiple topics into one long query — that returns nothing. One topic per Search call.

Then use **WebSearch** on the most promising theme to check: is there relevant external context?

**Signal vs noise:**
- STRATEGIC: competitor mentions, technology evaluations, market discussions, customer feedback patterns, hiring/org changes → worth investigating
- OPERATIONAL: routine standup summaries, infrastructure alerts, deploy notifications, calendar scheduling → skip unless unusually significant

**Decision criteria:**
- **generate**: You found 2+ themes with internal momentum AND at least one has meaningful external context. Include the themes in your note.
- **observe**: You see an interesting signal but it's too early (only 1 mention, no pattern yet). Note what you're tracking.
- **sleep**: Platforms are quiet or only showing routine activity. No strategic signals detected.

**Important:** Check your accumulated memory (review_log and observations below) to avoid re-reporting themes you already covered. Focus on what's NEW or CHANGED since your last review."""

    # Coordinator mode: mention write primitives
    if mode == "coordinator":
        prompt += """

## Coordinator Write Primitives

As a coordinator, you also have access to:

**CreateAgent** — create a new child agent when you detect a condition that warrants it
(e.g. an upcoming meeting needing prep, a stalled project, an emerging issue).
Check agent_memory.created_agents before creating to avoid duplicates.

**AdvanceAgentSchedule** — advance an existing agent to run now when conditions warrant it.

Use List or Search to find existing agents before creating or advancing.
Your JSON decision still controls the overall outcome — use `generate` only if THIS coordinator
agent should itself produce a new version (rare). Use `observe` or `sleep` for most cycles,
creating/advancing child agents as needed via tools during the review pass."""

    # ADR-106: Inject memory from workspace files (source of truth)
    memory_parts = []
    if last_generated_at:
        memory_parts.append(f"**Last generated:** {last_generated_at}")
    if review_log:
        memory_parts.append("**Recent review log (last 5):**")
        for entry in review_log[-5:]:
            memory_parts.append(f"- {entry.get('date', '')} [{entry.get('action', '')}]: {entry.get('note', '')}")
    if observations:
        memory_parts.append("**Pending observations:**")
        for obs in observations[-5:]:
            memory_parts.append(f"- {obs.get('date', '')}: {obs.get('note', '')}")

    # Coordinator mode: inject created_agents dedup log from workspace
    if mode == "coordinator" and created_agents:
        memory_parts.append("**Created agents (dedup log — last 10):**")
        for cd in created_agents[-10:]:
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
        # Fallback: extract action keyword from text
        lower = clean.lower()
        if "generate" in lower:
            return {"action": "generate", "note": f"(extracted from text) {text[:200]}"}
        elif "sleep" in lower:
            return {"action": "sleep", "note": f"(extracted from text) {text[:200]}"}
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
    agent: dict,
) -> dict:
    """
    Run the lightweight Haiku review pass for a proactive/coordinator agent.

    Args:
        client: Supabase service client
        user_id: User UUID
        agent: Full agent dict from DB

    Returns:
        Parsed decision dict: {"action": "generate"|"observe"|"sleep", "note": ..., "until": ...}
        Never raises — on failure returns {"action": "observe", "note": "Review error: ..."}
    """
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import get_tools_for_mode, create_headless_executor

    title = agent.get("title", "Untitled")
    agent_id = agent.get("id")

    logger.info(f"[PROACTIVE_REVIEW] Starting review: {title} ({agent_id})")

    try:
        system_prompt = await _build_review_system_prompt(agent, client=client)

        # Review prompt: ask the agent to assess its domain and decide
        user_message = (
            f"Review your domain for agent: {title}\n\n"
            "Use your tools to check current conditions, then respond with your JSON decision."
        )

        headless_tools = get_tools_for_mode("headless")
        executor = create_headless_executor(
            client,
            user_id,
            agent_sources=agent.get("sources"),
            coordinator_agent_id=agent.get("id"),
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

        # If loop exhausted all rounds (agent still calling tools), give it one
        # final turn WITHOUT tools to force a JSON decision
        if rounds >= REVIEW_MAX_TOOL_ROUNDS and response.tool_uses:
            response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=[],  # No tools — force text-only response
                model=REVIEW_MODEL,
                max_tokens=REVIEW_MAX_TOKENS,
            )
            if response.text:
                final_text = response.text

        decision = _parse_review_response(final_text)
        logger.info(f"[PROACTIVE_REVIEW] Decision for {title}: {decision.get('action')}")
        return decision

    except Exception as e:
        logger.error(f"[PROACTIVE_REVIEW] Review failed for {title}: {e}")
        return {"action": "observe", "note": f"Review error: {e}"}


async def apply_review_decision(
    client,
    agent: dict,
    decision: dict,
) -> None:
    """
    Apply the review decision to workspace files and scheduling.

    ADR-106 Phase 2: Writes to workspace (source of truth).
    Only updates proactive_next_review_at on the agents table (scheduling, not intelligence).
    Does NOT trigger generation — caller handles that based on action=="generate".
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    action = decision.get("action", "observe")
    note = decision.get("note", "")
    now = datetime.now(timezone.utc)

    # Compute next review time
    if action == "sleep" and decision.get("until"):
        try:
            next_review = datetime.fromisoformat(decision["until"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            next_review = now + timedelta(hours=24)
    elif action == "generate":
        next_review = now + timedelta(hours=24)
    else:
        next_review = now + timedelta(hours=24)

    # Write to workspace (source of truth)
    ws = AgentWorkspace(client, agent.get("user_id"), get_agent_slug(agent))

    # Append to review log
    await ws.append_review_log({
        "date": now.date().isoformat(),
        "action": action,
        "note": note,
        "next_review_at": next_review.isoformat(),
    })

    # Update operational state
    if action == "generate":
        await ws.set_state("last_generated_at", now.isoformat())

    # Record observation for context
    if note:
        await ws.record_observation(note, source=f"review/{action}")

    # Update scheduling on agents table (scheduling is DB, not workspace)
    client.table("agents").update({
        "proactive_next_review_at": next_review.isoformat(),
    }).eq("id", agent_id).execute()
