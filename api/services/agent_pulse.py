"""
Agent Pulse — ADR-126

Two-tier funnel:
  Tier 1: Deterministic gates (zero LLM) — budget, freshness, cooldown
  Tier 2: Agent self-assessment (Haiku)

Write points:
  - activity_log: 'agent_pulsed'
  - workspace: observations, review log
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Tier 2 uses Haiku — lightweight, cost-efficient
PULSE_MODEL = "claude-haiku-4-5-20251001"
PULSE_MAX_TOKENS = 1024
PULSE_MAX_TOOL_ROUNDS = 2  # ADR-136: reduced from 5 — quick domain check, not deep investigation


# =============================================================================
# Data Types
# =============================================================================

@dataclass
class PulseDecision:
    """Result of an agent's pulse cycle."""
    action: str  # generate | observe | wait | escalate
    reason: str  # Human-readable explanation
    tier: int  # 1 or 2 — which tier resolved the decision
    observations: list[str] = field(default_factory=list)  # Notes to write to workspace
    metadata: dict = field(default_factory=dict)  # Structured data for activity log


# =============================================================================
# Tier 1: Deterministic Pulse (zero LLM cost)
# =============================================================================

async def _tier1_deterministic(client, agent: dict) -> Optional[PulseDecision]:
    """
    Deterministic gates — zero LLM cost. Resolves ~80% of pulses.

    Checks (in order):
    1. First run? → always generate (no basis for judgment)
    2. Work budget exhausted? → wait
    3. Fresh content since last run? → if no, observe (nothing new)
    4. Reactive mode: enough observations? → if not enough, wait
    5. All gates pass → None (escalate to Tier 2 if eligible, else generate)

    Absorbs: should_skip_agent() from unified_scheduler.py
    """
    from services.platform_content import has_fresh_content_since

    agent_id = agent["id"]
    user_id = agent["user_id"]
    mode = agent.get("mode", "recurring")
    sources = agent.get("sources", [])
    last_run_at = agent.get("last_run_at")

    # Gate 1: First run — always generate
    if not last_run_at:
        return PulseDecision(
            action="generate",
            reason="First run — no prior output",
            tier=1,
            metadata={"gate": "first_run"},
        )

    # Parse last_run_at
    if isinstance(last_run_at, str):
        if last_run_at.endswith("Z"):
            last_run_at = last_run_at[:-1] + "+00:00"
        try:
            last_run_at = datetime.fromisoformat(last_run_at)
        except (ValueError, TypeError):
            # Can't parse — treat as first run
            return PulseDecision(
                action="generate",
                reason="Cannot parse last_run_at — treating as first run",
                tier=1,
                metadata={"gate": "parse_error"},
            )

    # Gate 2: Minimum cooldown — prevent runaway execution loops
    # No agent should run more than once per 30 minutes
    MIN_RUN_INTERVAL = timedelta(minutes=30)
    now = datetime.now(timezone.utc)
    if isinstance(last_run_at, datetime):
        time_since_last = now - last_run_at
        if time_since_last < MIN_RUN_INTERVAL:
            remaining = MIN_RUN_INTERVAL - time_since_last
            return PulseDecision(
                action="wait",
                reason=f"Cooldown: ran {int(time_since_last.total_seconds() / 60)}m ago (min interval: {int(MIN_RUN_INTERVAL.total_seconds() / 60)}m)",
                tier=1,
                metadata={"gate": "cooldown", "minutes_since_last": int(time_since_last.total_seconds() / 60)},
            )

    # Gate 3: Work budget
    try:
        from services.platform_limits import check_work_budget
        budget_ok, wu_used, wu_limit = check_work_budget(client, user_id)
        if not budget_ok:
            return PulseDecision(
                action="wait",
                reason=f"Work budget exhausted ({wu_used}/{wu_limit})",
                tier=1,
                metadata={"gate": "budget", "used": wu_used, "limit": wu_limit},
            )
    except Exception as e:
        logger.warning(f"[PULSE] Budget check failed (proceeding): {e}")

    # Gate 4: Fresh content
    if sources:
        try:
            has_fresh, fresh_count = await has_fresh_content_since(
                db_client=client,
                user_id=user_id,
                agent_sources=sources,
                since=last_run_at,
            )
            if not has_fresh:
                return PulseDecision(
                    action="observe",
                    reason="No new content since last run",
                    tier=1,
                    metadata={"gate": "freshness", "fresh_count": 0},
                )
        except Exception as e:
            logger.warning(f"[PULSE] Freshness check failed (proceeding): {e}")

    # Gate 5: Reactive mode — check observation threshold
    if mode == "reactive":
        try:
            from services.workspace import AgentWorkspace, get_agent_slug
            ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
            observations = await ws.get_observations()
            threshold = (agent.get("trigger_config") or {}).get("observation_threshold", 5)
            if len(observations) < threshold:
                return PulseDecision(
                    action="wait",
                    reason=f"Reactive: {len(observations)}/{threshold} observations (below threshold)",
                    tier=1,
                    metadata={"gate": "reactive_threshold", "observations": len(observations), "threshold": threshold},
                )
        except Exception as e:
            logger.warning(f"[PULSE] Reactive threshold check failed (proceeding): {e}")

    # All Tier 1 gates passed — no deterministic reason to block
    return None  # Escalate to Tier 2 if eligible


# =============================================================================
# Tier 2: Agent Self-Assessment (Haiku LLM)
# =============================================================================

async def _tier2_self_assessment(client, agent: dict) -> PulseDecision:
    """
    Agent self-assessment via Haiku LLM. All agents eligible (ADR-130).

    Agent reads its workspace + fresh content, decides whether to generate.
    Generalizes proactive_review.py to all agent modes.

    Absorbs: proactive_review.py (_build_review_system_prompt, run_proactive_review)
    """
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import get_tools_for_mode, create_headless_executor
    from services.workspace import AgentWorkspace, get_agent_slug

    title = agent.get("title", "Untitled")
    role = agent.get("role", "briefer")
    mode = agent.get("mode", "recurring")
    agent_id = agent["id"]
    user_id = agent["user_id"]

    logger.info(f"[PULSE T2] Self-assessment: {title} ({agent_id})")

    try:
        # Build assessment context from workspace
        ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
        await ws.ensure_seeded(agent)

        instructions = (await ws.read("AGENT.md") or "").strip()
        observations = await ws.get_observations()
        review_log = await ws.get_review_log()
        last_generated_at = await ws.get_state("last_generated_at")

        # Build system prompt
        system_prompt = _build_tier2_prompt(
            title=title,
            role=role,
            mode=mode,
            instructions=instructions,
            observations=observations,
            review_log=review_log,
            last_generated_at=last_generated_at,
            agent=agent,
        )

        user_message = (
            f"Pulse check for agent: {title}\n\n"
            "Use your tools to check current conditions in your domain, "
            "then respond with your JSON decision."
        )

        headless_tools = get_tools_for_mode("headless")
        executor = create_headless_executor(
            client,
            user_id,
            agent_sources=agent.get("sources"),
            coordinator_agent_id=agent_id,
        )

        # Tool-use loop
        messages = [{"role": "user", "content": user_message}]
        rounds = 0
        final_text = ""

        while rounds < PULSE_MAX_TOOL_ROUNDS:
            rounds += 1
            response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=headless_tools,
                model=PULSE_MODEL,
                max_tokens=PULSE_MAX_TOKENS,
            )

            if response.text:
                final_text = response.text

            if not response.tool_uses:
                break

            # Execute tool calls
            tool_results = []
            for tu in response.tool_uses:
                result = await executor(tu.name, tu.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result),
                })

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

        # Force text-only response if tools exhausted
        if rounds >= PULSE_MAX_TOOL_ROUNDS and response.tool_uses:
            response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=[],
                model=PULSE_MODEL,
                max_tokens=PULSE_MAX_TOKENS,
            )
            if response.text:
                final_text = response.text

        decision = _parse_pulse_response(final_text)
        logger.info(f"[PULSE T2] Decision for {title}: {decision.get('action')}")

        action = decision.get("action", "observe")
        note = decision.get("note", "")

        # Map sleep → wait (ADR-126 taxonomy uses wait, not sleep)
        if action == "sleep":
            action = "wait"

        return PulseDecision(
            action=action,
            reason=note or f"Tier 2 self-assessment: {action}",
            tier=2,
            observations=[note] if note and action == "observe" else [],
            metadata={
                "tier2_action": action,
                "tool_rounds": rounds,
                "until": decision.get("until"),
            },
        )

    except Exception as e:
        logger.error(f"[PULSE T2] Self-assessment failed for {title}: {e}")
        return PulseDecision(
            action="observe",
            reason=f"Tier 2 error (safe fallback): {e}",
            tier=2,
            metadata={"error": str(e)},
        )


def _build_tier2_prompt(
    *,
    title: str,
    role: str,
    mode: str,
    instructions: str,
    observations: list[dict],
    review_log: list[dict],
    last_generated_at: Optional[str],
    agent: dict,
) -> str:
    """Build the Tier 2 self-assessment system prompt."""

    prompt = f"""You are performing a pulse check for agent: "{title}" (role: {role}, mode: {mode}).

Your job is NOT to generate content. Your job is to quickly assess whether conditions in your
domain have changed enough to warrant producing a new output. Be efficient — one quick search
is usually enough to decide. Don't investigate deeply; that's for the generation phase.

## Your Domain Instructions
{instructions if instructions else "No specific instructions set. Use your judgment based on agent role and available context."}

## How to Decide

Use your available tools (Search, Read, List, WebSearch, RefreshPlatformContent) to check the current state
of your domain. Then return a JSON decision:

**generate** — conditions warrant producing new output now. Use when:
- Something significant has changed or emerged in your domain
- Enough has accumulated since the last generation to be worth surfacing
- A time-sensitive event is approaching

**observe** — nothing warrants generation yet, but worth noting something. Use when:
- You see a development worth tracking but not yet significant enough to act on
- You want to record a pattern for future reference

**wait** — domain is quiet, nothing to note. Use when:
- Nothing meaningful has changed
- You want to defer the next pulse

## Response Format

Respond with ONLY a JSON object:

```json
{{"action": "generate"}}
```

```json
{{"action": "observe", "note": "Brief description of what you observed."}}
```

```json
{{"action": "wait", "note": "Optional reason for deferring."}}
```"""

    # Research/synthesize with autonomous scope: signal-driven
    if role in ("research", "researcher", "synthesize", "analyst", "scout") and agent.get("scope") == "autonomous":
        prompt += """

## Proactive Insights — Signal Detection

Your domain is the user's entire connected work context. Find **emerging themes** worth investigating.

Use **Search** with SHORT, SPECIFIC queries (1-3 words each). Run multiple searches:
- Search("decision"), Search("blocked"), Search("meeting"), Search("launch"), Search("competitor")

Then use **WebSearch** on the most promising theme for external context.

**Decision criteria:**
- **generate**: 2+ themes with internal momentum AND external context available
- **observe**: Interesting signal but too early (1 mention, no pattern)
- **wait**: Only routine activity, no strategic signals"""

    # Inject accumulated memory
    memory_parts = []
    if last_generated_at:
        memory_parts.append(f"**Last generated:** {last_generated_at}")
    if review_log:
        memory_parts.append("**Recent pulse log (last 5):**")
        for entry in review_log[-5:]:
            memory_parts.append(f"- {entry.get('date', '')} [{entry.get('action', '')}]: {entry.get('note', '')}")
    if observations:
        memory_parts.append("**Pending observations:**")
        for obs in observations[-5:]:
            memory_parts.append(f"- {obs.get('date', '')}: {obs.get('note', '')}")

    if memory_parts:
        prompt += "\n\n## Your Accumulated Memory\n" + "\n".join(memory_parts)

    return prompt


def _parse_pulse_response(text: str) -> dict:
    """
    Parse the agent's JSON pulse decision from its text response.

    Returns dict with at least {"action": "generate"|"observe"|"wait"}.
    Falls back to {"action": "observe"} on parse failure.
    """
    if not text:
        return {"action": "observe", "note": "Pulse returned empty response."}

    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        inner = [l for l in lines if not l.startswith("```")]
        clean = "\n".join(inner).strip()

    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1:
        lower = clean.lower()
        if "generate" in lower:
            return {"action": "generate", "note": f"(extracted from text) {text[:200]}"}
        elif "wait" in lower or "sleep" in lower:
            return {"action": "wait", "note": f"(extracted from text) {text[:200]}"}
        return {"action": "observe", "note": f"Could not parse pulse response: {text[:200]}"}

    try:
        parsed = json.loads(clean[start:end + 1])
        action = parsed.get("action", "")
        # Normalize sleep → wait (ADR-126 taxonomy)
        if action == "sleep":
            parsed["action"] = "wait"
        if parsed["action"] not in ("generate", "observe", "wait", "escalate"):
            return {"action": "observe", "note": f"Unknown action '{action}' in pulse response."}
        return parsed
    except json.JSONDecodeError as e:
        return {"action": "observe", "note": f"JSON parse error in pulse response: {e}"}


# =============================================================================
# Main Entry Point
# =============================================================================

async def run_agent_pulse(client, agent: dict) -> PulseDecision:
    """
    Execute an agent's pulse cycle.

    Two-tier funnel:
      Tier 1: Deterministic gates (zero LLM cost)
      Tier 2: Self-assessment (Haiku)

    Args:
        client: Supabase service-role client
        agent: Full agent dict from DB

    Returns:
        PulseDecision with action, reason, tier, observations, metadata
    """
    agent_id = agent["id"]
    user_id = agent["user_id"]
    title = agent.get("title", "Untitled")
    mode = agent.get("mode", "recurring")
    role = agent.get("role", "briefer")

    logger.info(f"[PULSE] Starting pulse: {title} ({agent_id}), mode={mode}, role={role}")

    # --- Tier 1: Deterministic ---
    t1_decision = await _tier1_deterministic(client, agent)
    if t1_decision is not None:
        logger.info(f"[PULSE] Tier 1 resolved: {title} → {t1_decision.action} ({t1_decision.reason})")
        await _log_pulse_event(client, user_id, agent_id, title, t1_decision, agent=agent)
        await _apply_pulse_decision(client, agent, t1_decision)
        return t1_decision

    # --- Tier 2: Self-assessment ---
    t2_decision = await _tier2_self_assessment(client, agent)
    logger.info(f"[PULSE] Tier 2 resolved: {title} → {t2_decision.action} ({t2_decision.reason})")
    await _log_pulse_event(client, user_id, agent_id, title, t2_decision, agent=agent)
    await _apply_pulse_decision(client, agent, t2_decision)
    return t2_decision


# =============================================================================
# Side Effects
# =============================================================================

async def _log_pulse_event(
    client,
    user_id: str,
    agent_id: str,
    title: str,
    decision: PulseDecision,
    agent: Optional[dict] = None,
    event_type: str = "agent_pulsed",
) -> None:
    """Log pulse decision to activity_log."""
    from services.activity_log import write_activity

    try:
        meta = {
            "action": decision.action,
            "reason": decision.reason,
            "tier": decision.tier,
            **decision.metadata,
        }
        await write_activity(
            client=client,
            user_id=user_id,
            event_type=event_type,
            summary=f"{title} pulsed: {decision.action} — {decision.reason[:100]}",
            event_ref=agent_id,
            metadata=meta,
        )
    except Exception:
        pass  # Non-fatal


async def _apply_pulse_decision(client, agent: dict, decision: PulseDecision) -> None:
    """
    Apply pulse side effects to workspace.

    On 'observe': write observations to workspace review log + observations.
    On 'wait' with until: compute deferred next_pulse_at.
    On all: update workspace review log.
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent["id"]
    user_id = agent["user_id"]
    now = datetime.now(timezone.utc)

    try:
        ws = AgentWorkspace(client, user_id, get_agent_slug(agent))

        # Append to review log (pulse history)
        await ws.append_review_log({
            "date": now.date().isoformat(),
            "action": decision.action,
            "note": decision.reason[:200],
            "tier": decision.tier,
        })

        # Write observations to workspace
        for obs in decision.observations:
            if obs:
                await ws.record_observation(obs, source=f"pulse/{decision.action}")

        # Update last_generated_at on generate
        if decision.action == "generate":
            await ws.set_state("last_generated_at", now.isoformat())

    except Exception as e:
        logger.warning(f"[PULSE] Failed to apply pulse decision to workspace: {e}")


def calculate_next_pulse_at(agent: dict, decision: PulseDecision) -> datetime:
    """
    Compute the next pulse time based on role cadence and decision.

    Priority:
    1. 'wait' with 'until' metadata → deferred time (pulse explicitly chose to wait)
    2. Role-based cadence from ROLE_PULSE_CADENCE → the natural sensing pace for this role
    3. Schedule-derived cadence → fallback for roles with cadence="schedule"
    4. 24h fallback

    ADR-126 Phase 5: Pulse cadence is role-based, not seniority-based.
    A monitor senses every 15 min because it's a watchdog — not because it's senior.
    A digest senses every 12h because it summarizes on rhythm — regardless of tenure.
    """
    from services.agent_framework import get_pulse_cadence

    now = datetime.now(timezone.utc)

    # 1. Decision-deferred time (pulse explicitly chose to wait until X)
    until = decision.metadata.get("until")
    if until and decision.action == "wait":
        try:
            deferred = datetime.fromisoformat(until.replace("Z", "+00:00"))
            if deferred > now:
                return deferred
        except (ValueError, TypeError):
            pass

    # 2. Role-based cadence
    role = agent.get("role", "briefer")
    cadence = get_pulse_cadence(role)

    if isinstance(cadence, timedelta):
        return now + cadence

    # 3. cadence == "schedule" → use the agent's configured schedule
    from jobs.unified_scheduler import calculate_next_pulse_from_schedule
    schedule = agent.get("schedule", {})
    if schedule:
        return calculate_next_pulse_from_schedule(schedule)

    # 4. Fallback: 24 hours from now
    return now + timedelta(hours=24)
