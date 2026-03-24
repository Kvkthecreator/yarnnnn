"""
Agent Pulse — ADR-126 + ADR-133

Three execution modes (ADR-133):
  1. Standalone agents (no project): independent pulse (Tier 1 + Tier 2)
  2. Project contributors: PM-dispatched (no independent pulse)
  3. PM agents: coordination pulse (Tier 1 + Tier 3)

Three-tier funnel:
  Tier 1: Deterministic gates (zero LLM) — budget, freshness, cooldown
  Tier 2: Agent self-assessment (Haiku) — standalone agents only
  Tier 3: PM coordination pulse (Haiku) — PM reads work plan, dispatches phases

Write points:
  - activity_log: 'agent_pulsed' for standalone agents
  - activity_log: 'pm_pulsed' for PM coordination pulse
  - activity_log: 'contributor_dispatched' when PM dispatches a contributor
  - activity_log: 'phase_advanced' when PM advances project to next phase
  - workspace: observations, review log, phase_state.json
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
PULSE_MAX_TOOL_ROUNDS = 5


# =============================================================================
# Data Types
# =============================================================================

@dataclass
class PulseDecision:
    """Result of an agent's pulse cycle."""
    action: str  # generate | observe | wait | escalate
    reason: str  # Human-readable explanation
    tier: int  # 1, 2, or 3 — which tier resolved the decision
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

    # Gate 3: Cadence enforcement (ADR-136) — has this project already delivered in the current window?
    tc = agent.get("type_config") or {}
    project_slug = tc.get("project_slug")
    if project_slug and isinstance(last_run_at, datetime):
        try:
            from services.workspace import ProjectWorkspace
            pw = ProjectWorkspace(client, user_id, project_slug)
            project = await pw.read_project()
            cadence = (project or {}).get("cadence", "")
            if cadence:
                # Calculate cadence window
                cadence_delta = {
                    "daily": timedelta(hours=20),    # Allow re-run after 20h
                    "weekly": timedelta(days=6),     # Allow re-run after 6 days
                    "biweekly": timedelta(days=13),
                    "monthly": timedelta(days=28),
                }.get(cadence.lower().strip())
                if cadence_delta and isinstance(last_run_at, datetime):
                    time_since = now - last_run_at
                    if time_since < cadence_delta:
                        return PulseDecision(
                            action="wait",
                            reason=f"Cadence: {cadence} — ran {time_since.days}d ago, next window in {(cadence_delta - time_since).days}d",
                            tier=1,
                            metadata={"gate": "cadence", "cadence": cadence, "days_since": time_since.days},
                        )
        except Exception as e:
            logger.warning(f"[PULSE] Cadence check failed (proceeding): {e}")

    # Gate 4: Work budget
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

    # Gate 3: Fresh content
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

    # Gate 4: Reactive mode — check observation threshold
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

Your job is NOT to generate content. Your job is to assess whether conditions in your domain
warrant generating content right now.

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
        if parsed["action"] not in ("generate", "observe", "wait", "escalate", "dispatch", "advance_phase"):
            return {"action": "observe", "note": f"Unknown action '{action}' in pulse response."}
        return parsed
    except json.JSONDecodeError as e:
        return {"action": "observe", "note": f"JSON parse error in pulse response: {e}"}


# =============================================================================
# Tier 3: PM Coordination Pulse (ADR-133)
# =============================================================================

async def _tier3_pm_coordination(client, agent: dict) -> PulseDecision:
    """
    PM coordination pulse — sense project state, decide next action.

    The PM reads: work plan phases, phase_state.json, contributor assessments.
    Decides: dispatch contributors, advance phase, steer, escalate, or wait.

    Actions the PM can take (returned in decision.metadata):
      - dispatch: set next_pulse_at on contributors to trigger their run
      - advance_phase: mark current phase complete, prepare next phase
      - steer: write updated contribution brief
      - escalate: flag for Composer attention
      - wait: project is healthy, no action needed
      - generate: PM itself should run (assembly, assessment)
    """
    from services.workspace import ProjectWorkspace, AgentWorkspace, get_agent_slug
    from services.activity_log import write_activity

    agent_id = agent["id"]
    user_id = agent["user_id"]
    title = agent.get("title", "Untitled")
    tc = agent.get("type_config") or {}
    project_slug = tc.get("project_slug")

    if not project_slug:
        # PM without a project — shouldn't happen, fall back to wait
        return PulseDecision(
            action="wait",
            reason="PM has no project_slug — cannot coordinate",
            tier=3,
        )

    pw = ProjectWorkspace(client, user_id, project_slug)

    # --- Gather project state ---
    # 1. Read phase state
    import json as _json
    phase_state_raw = await pw.read("memory/phase_state.json")
    phase_state = {}
    if phase_state_raw:
        try:
            phase_state = _json.loads(phase_state_raw)
        except _json.JSONDecodeError:
            pass

    # 2. Read work plan
    work_plan = await pw.read("memory/work_plan.md") or ""

    # 3. Read project objective
    project = await pw.read_project()
    objective = project.get("objective", {}) if project else {}

    # 4. Get contributor agents for this project
    try:
        contributors_result = (
            client.table("agents")
            .select("id, title, role, last_run_at, status, type_config, next_pulse_at")
            .eq("user_id", user_id)
            .eq("status", "active")
            .neq("role", "pm")
            .execute()
        )
        project_contributors = [
            a for a in (contributors_result.data or [])
            if (a.get("type_config") or {}).get("project_slug") == project_slug
        ]
    except Exception:
        project_contributors = []

    # 5. Read contributor assessments (latest from each)
    contributor_status = []
    for c in project_contributors:
        slug = get_agent_slug(c)
        cws = AgentWorkspace(client, user_id, slug)
        assessment = await cws.read("memory/self_assessment.md")
        last_output = c.get("last_run_at")
        contributor_status.append({
            "title": c.get("title", "?"),
            "role": c.get("role", "?"),
            "slug": slug,
            "agent_id": c["id"],
            "last_run_at": last_output,
            "has_assessment": bool(assessment and "Not yet assessed" not in assessment),
            "assessment_snippet": (assessment or "")[:300],
        })

    # ADR-135: Read PM decision log for continuity across contexts
    from services.pm_coordination import read_pm_log
    pm_log = await read_pm_log(client, user_id, project_slug, max_entries=5)

    # --- Build Tier 3 prompt ---
    now = datetime.now(timezone.utc)
    prompt = _build_tier3_prompt(
        title=title,
        project_slug=project_slug,
        objective=objective,
        work_plan=work_plan,
        phase_state=phase_state,
        contributor_status=contributor_status,
        now_iso=now.isoformat(),
        pm_log=pm_log,
    )

    # --- Call Haiku for PM coordination decision ---
    from services.anthropic import chat_completion

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": "Assess the project and decide what to do next."}],
            system=prompt,
            model=PULSE_MODEL,
            max_tokens=PULSE_MAX_TOKENS,
        )
        parsed = _parse_pulse_response(response)
    except Exception as e:
        logger.warning(f"[PULSE T3] PM coordination LLM failed: {e}")
        return PulseDecision(
            action="wait",
            reason=f"PM coordination failed: {e}",
            tier=3,
        )

    action = parsed.get("action", "wait")
    note = parsed.get("note", "")
    dispatch_targets = parsed.get("dispatch", [])  # list of contributor slugs to dispatch

    # --- ADR-135: Announce PM decisions to chat session ---
    from services.pm_coordination import pm_announce

    # --- Execute PM dispatch side effects ---
    if action == "dispatch" and dispatch_targets:
        phase_context = parsed.get("phase_context", note)
        await _write_phase_briefs(
            client, user_id, project_slug, project_contributors,
            dispatch_targets, phase_context, phase_state,
        )
        dispatched = await _dispatch_contributors(
            client, user_id, project_slug, project_contributors, dispatch_targets,
        )
        # Announce to chat
        dispatch_names = [c.get("title", s) for c in project_contributors for s in dispatched if get_agent_slug(c) == s]
        await pm_announce(client, user_id, project_slug, agent,
            f"Dispatching {', '.join(dispatch_names or dispatched)}. {note}",
            decision_type="dispatch")
        return PulseDecision(
            action="generate",
            reason=f"Dispatched {len(dispatched)} contributors: {', '.join(dispatched)}",
            tier=3,
            metadata={
                "pm_action": "dispatch",
                "dispatched": dispatched,
                "project_slug": project_slug,
            },
        )

    if action == "advance_phase":
        phase_name = parsed.get("phase", "")
        await _advance_phase_state(client, user_id, project_slug, phase_name, phase_state)
        await pm_announce(client, user_id, project_slug, agent,
            f"Phase complete: {phase_name}. {note}",
            decision_type="advance_phase")
        return PulseDecision(
            action="generate",
            reason=f"Advancing phase: {phase_name}. {note}",
            tier=3,
            metadata={"pm_action": "advance_phase", "phase": phase_name, "project_slug": project_slug},
        )

    if action == "escalate":
        await pm_announce(client, user_id, project_slug, agent,
            f"Need help: {note}",
            decision_type="escalate")
        return PulseDecision(
            action="escalate",
            reason=f"PM escalation: {note}",
            tier=3,
            metadata={"pm_action": "escalate", "project_slug": project_slug},
        )

    if action == "generate":
        await pm_announce(client, user_id, project_slug, agent,
            note or "Running project assessment.",
            decision_type="generate")
        return PulseDecision(
            action="generate",
            reason=f"PM coordination: {note}",
            tier=3,
            metadata={"pm_action": "generate", "project_slug": project_slug},
        )

    # Default: wait
    return PulseDecision(
        action="wait",
        reason=f"Project healthy: {note}" if note else "No coordination needed",
        tier=3,
        metadata={"pm_action": "wait", "project_slug": project_slug},
    )


async def _dispatch_contributors(
    client, user_id: str, project_slug: str,
    project_contributors: list[dict], dispatch_targets: list[str],
) -> list[str]:
    """Set next_pulse_at on target contributors to trigger their run.

    Returns list of slugs that were successfully dispatched.
    """
    from services.workspace import get_agent_slug
    from services.activity_log import write_activity

    now = datetime.now(timezone.utc)
    # Set next_pulse_at to now (or 1 min from now to let PM finish first)
    dispatch_time = now + timedelta(minutes=1)
    dispatched = []

    for contributor in project_contributors:
        slug = get_agent_slug(contributor)
        if slug in dispatch_targets:
            try:
                client.table("agents").update({
                    "next_pulse_at": dispatch_time.isoformat(),
                }).eq("id", contributor["id"]).execute()
                dispatched.append(slug)

                # Log dispatch event
                try:
                    await write_activity(
                        client=client,
                        user_id=user_id,
                        event_type="contributor_dispatched",
                        summary=f"PM dispatched {contributor.get('title', slug)} for project {project_slug}",
                        event_ref=contributor["id"],
                        metadata={
                            "project_slug": project_slug,
                            "contributor_slug": slug,
                            "dispatched_by": "pm_pulse",
                        },
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"[PULSE T3] Failed to dispatch {slug}: {e}")

    return dispatched


async def _write_phase_briefs(
    client, user_id: str, project_slug: str,
    project_contributors: list[dict], dispatch_targets: list[str],
    phase_context: str, phase_state: dict,
) -> None:
    """ADR-133 Phase 2: Write phase-aware briefs for dispatched contributors.

    Each dispatched contributor gets a brief that includes:
    1. What the PM wants them to do (from the coordination decision)
    2. Prior phase outputs (cross-phase context injection)
    """
    from services.workspace import ProjectWorkspace, AgentWorkspace, get_agent_slug

    pw = ProjectWorkspace(client, user_id, project_slug)

    # Gather prior phase outputs for context injection
    prior_outputs = []
    completed_phases = [
        name for name, state in (phase_state.get("phases", {})).items()
        if state.get("status") == "complete"
    ]
    for phase_name in completed_phases:
        phase_data = phase_state["phases"][phase_name]
        for output_path in phase_data.get("outputs", []):
            # Read the output.md from each prior phase contributor
            try:
                # output_path is like "market-researcher/outputs/2026-03-23T1200"
                parts = output_path.split("/")
                if len(parts) >= 3:
                    contributor_slug = parts[0]
                    cws = AgentWorkspace(client, user_id, contributor_slug)
                    content = await cws.read(f"outputs/{parts[-1]}/output.md")
                    if content:
                        prior_outputs.append({
                            "phase": phase_name,
                            "contributor": contributor_slug,
                            "content_preview": content[:500],
                            "full_path": output_path,
                        })
            except Exception:
                pass

    # Build phase context section
    phase_context_section = ""
    if prior_outputs:
        phase_context_section = "\n\n## Phase Context (from prior phases)\n\n"
        for po in prior_outputs:
            phase_context_section += f"### {po['contributor']} ({po['phase']})\n"
            phase_context_section += f"{po['content_preview']}\n\n"
            phase_context_section += f"_Full output: /agents/{po['full_path']}/output.md_\n\n"

    # Write brief for each dispatched contributor
    for contributor in project_contributors:
        slug = get_agent_slug(contributor)
        if slug in dispatch_targets:
            brief = f"## PM Directive\n\n{phase_context}\n"
            brief += phase_context_section
            try:
                await pw.write_brief(slug, brief)
                logger.info(f"[PULSE T3] Wrote phase brief for {slug} ({len(brief)} chars)")
            except Exception as e:
                logger.warning(f"[PULSE T3] Failed to write brief for {slug}: {e}")


async def _advance_phase_state(
    client, user_id: str, project_slug: str,
    phase_name: str, current_state: dict,
) -> None:
    """ADR-133 Phase 2: Update phase_state.json when PM advances a phase."""
    from services.workspace import ProjectWorkspace
    from services.activity_log import write_activity
    import json as _json

    pw = ProjectWorkspace(client, user_id, project_slug)
    now = datetime.now(timezone.utc)

    # Update the phase state
    phases = current_state.get("phases", {})
    if phase_name in phases:
        phases[phase_name]["status"] = "complete"
        phases[phase_name]["completed_at"] = now.isoformat()

    current_state["phases"] = phases
    current_state["last_advanced_at"] = now.isoformat()

    # Write updated phase state
    try:
        await pw.write(
            "memory/phase_state.json",
            _json.dumps(current_state, indent=2),
            summary=f"Phase advanced: {phase_name}",
        )
    except Exception as e:
        logger.warning(f"[PULSE T3] Failed to update phase_state.json: {e}")

    # Log phase_advanced event
    try:
        await write_activity(
            client=client,
            user_id=user_id,
            event_type="phase_advanced",
            summary=f"Project {project_slug}: advanced past {phase_name}",
            event_ref=project_slug,
            metadata={
                "project_slug": project_slug,
                "phase": phase_name,
            },
        )
    except Exception:
        pass


def _build_tier3_prompt(
    title: str,
    project_slug: str,
    objective: dict,
    work_plan: str,
    phase_state: dict,
    contributor_status: list[dict],
    now_iso: str,
    pm_log: str = "",
) -> str:
    """Build the PM Tier 3 coordination prompt."""

    from services.agent_framework import AGENT_TYPES, has_asset_capabilities

    contributors_text = ""
    for c in contributor_status:
        role = c['role']
        type_def = AGENT_TYPES.get(role, {})
        caps = type_def.get("capabilities", [])
        asset_caps = [cap for cap in caps if cap in ("chart", "mermaid", "image", "video_render")]
        cap_note = f" [assets: {', '.join(asset_caps)}]" if asset_caps else ""
        status = f"last_run: {c['last_run_at'] or 'never'}{cap_note}"
        if c["has_assessment"]:
            status += f"\n    assessment: {c['assessment_snippet']}"
        contributors_text += f"  - {c['title']} ({role}, slug: {c['slug']}): {status}\n"

    phase_state_text = json.dumps(phase_state, indent=2) if phase_state else "No phase state yet."

    objective_text = ""
    if objective:
        for k, v in objective.items():
            objective_text += f"  - {k}: {v}\n"
    else:
        objective_text = "  (not defined)"

    return f"""You are the Project Manager for "{title}" (project: {project_slug}).

Current time: {now_iso}

## Project Objective
{objective_text}

## Work Plan
{work_plan or "(No work plan defined yet. Consider creating one with structured phases.)"}

## Phase State
{phase_state_text}

## Contributors
{contributors_text or "  (no contributors)"}

## Your Recent Decisions
{pm_log or "(No prior decisions — this is your first assessment.)"}

## Available Agent Types (for escalation requests)
- briefer: summarizes platform activity (no assets)
- monitor: watches for changes and alerts (no assets)
- researcher: investigates topics (charts, mermaid, images)
- drafter: produces deliverables (charts, mermaid, images, video)
- analyst: tracks metrics and patterns (charts, mermaid)
- writer: crafts communications (images, video)
- planner: prepares plans and agendas (no assets)
- scout: tracks competitors and markets (charts, images)

## Your Task

Assess the project state and decide what to do:

1. **dispatch** — trigger specific contributors to run now. Return their slugs.
   Use this when: a phase has unfinished contributor work and context is ready.
2. **advance_phase** — declare current phase complete, prepare for next phase.
   Use this when: all contributors in the current phase have produced output.
3. **generate** — you (the PM) should run to write briefs, update assessments, etc.
   Use this when: project needs PM work (steering, assembly, work plan updates).
4. **escalate** — flag this project for Composer attention.
   Use this when: missing contributors, budget issues, or structural problems.
5. **wait** — project is healthy, nothing to do right now.
   Use this when: current phase is in progress and contributors are working.

IMPORTANT: Respond with ONLY a raw JSON object. No explanation, no markdown, no text before or after. Just the JSON.

{{"action": "dispatch|advance_phase|generate|escalate|wait", "note": "why", "dispatch": ["slug1", "slug2"], "phase": "phase name if advancing", "phase_context": "what prior phases found that this phase should build on (for dispatch only)"}}
"""


# =============================================================================
# Main Entry Point
# =============================================================================

def _is_project_contributor(agent: dict) -> bool:
    """Check if this agent is a project contributor (not standalone, not PM)."""
    role = agent.get("role", "")
    tc = agent.get("type_config") or {}
    project_slug = tc.get("project_slug")
    return bool(project_slug) and role != "pm"


def _is_pm(agent: dict) -> bool:
    """Check if this agent is a PM."""
    return agent.get("role") == "pm"


async def run_agent_pulse(client, agent: dict) -> PulseDecision:
    """
    Execute an agent's pulse cycle (ADR-133: three execution modes).

    Routing:
      - PM agent → Tier 1 + Tier 3 (coordination pulse)
      - Project contributor → skip (PM dispatches, return generate immediately)
      - Standalone agent → Tier 1 + Tier 2 (independent pulse)

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

    # --- ADR-133: Project contributors are PM-dispatched ---
    # When PM sets next_pulse_at on a contributor, the scheduler picks it up.
    # The contributor doesn't "decide" — it just generates. Tier 1 gates still
    # apply (budget, etc.) but no self-assessment.
    if _is_project_contributor(agent):
        logger.info(f"[PULSE] PM-dispatched contributor: {title} ({agent_id}) → generate")
        # Still run Tier 1 for budget/safety gates
        t1_decision = await _tier1_deterministic(client, agent)
        if t1_decision is not None:
            logger.info(f"[PULSE] Tier 1 blocked dispatched contributor: {title} → {t1_decision.action}")
            await _log_pulse_event(client, user_id, agent_id, title, t1_decision, agent=agent)
            await _apply_pulse_decision(client, agent, t1_decision)
            return t1_decision
        # Tier 1 passed → generate (PM dispatched this run)
        decision = PulseDecision(
            action="generate",
            reason="PM-dispatched contributor — generating",
            tier=1,
            metadata={"gate": "pm_dispatched"},
        )
        await _log_pulse_event(client, user_id, agent_id, title, decision, agent=agent)
        await _apply_pulse_decision(client, agent, decision)
        return decision

    logger.info(f"[PULSE] Starting pulse: {title} ({agent_id}), mode={mode}, role={role}")

    # --- Tier 1: Deterministic ---
    t1_decision = await _tier1_deterministic(client, agent)
    if t1_decision is not None:
        logger.info(f"[PULSE] Tier 1 resolved: {title} → {t1_decision.action} ({t1_decision.reason})")
        await _log_pulse_event(client, user_id, agent_id, title, t1_decision, agent=agent)
        await _apply_pulse_decision(client, agent, t1_decision)
        return t1_decision

    # --- PM agents: Tier 3 coordination pulse ---
    if _is_pm(agent):
        t3_decision = await _tier3_pm_coordination(client, agent)
        event_type = "pm_pulsed"
        logger.info(f"[PULSE] Tier 3 resolved: {title} → {t3_decision.action} ({t3_decision.reason})")
        await _log_pulse_event(client, user_id, agent_id, title, t3_decision, agent=agent, event_type=event_type)
        await _apply_pulse_decision(client, agent, t3_decision)
        return t3_decision

    # --- Standalone agents: Tier 2 self-assessment ---
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
    from services.activity_log import write_activity, resolve_agent_project_slug

    try:
        meta = {
            "action": decision.action,
            "reason": decision.reason,
            "tier": decision.tier,
            **decision.metadata,
        }
        # ADR-129: Enrich with project_slug for project-scoped activity
        if agent:
            slug = resolve_agent_project_slug(agent)
            if slug:
                meta["project_slug"] = slug
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
