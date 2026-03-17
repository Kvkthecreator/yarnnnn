"""
Agent Execution Service - ADR-042 Simplified Flow + ADR-066 Delivery-First

Single Execute call for agent generation with immediate delivery (no approval gate).

Flow:
  Execute(action="agent.generate", target="agent:uuid")
    → check_agent_freshness() (ADR-049)
    → strategy.gather_context() (ADR-045 + ADR-073)
    → generate_draft_inline()
    → mark_content_retained() (ADR-073)
    → record_source_snapshots() (ADR-049)
    → deliver immediately (ADR-066)
    → write activity_log (ADR-090 Phase 3)

ADR-049 Integration:
- Freshness check before generation
- Targeted sync of stale sources
- Source snapshots recorded for audit trail

ADR-066 Integration:
- No governance/approval gate - agents deliver immediately
- Version status: generating → delivered | failed
- Governance field ignored (backwards compatibility)

This module replaces:
- execute_agent_pipeline() - 3-step orchestrator
- execute_gather_step() - separate gather work_ticket
- execute_synthesize_step() - separate synthesize work_ticket
- execute_stage_step() - validation/staging step

Preserves from agent_pipeline.py:
- Skill-specific prompts (SKILL_PROMPTS, build_skill_prompt)
- Output validation (validate_output)
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Model constants
SONNET_MODEL = "claude-sonnet-4-20250514"


def get_user_email(client, user_id: str) -> Optional[str]:
    """Get user's email from auth.users for email-first delivery."""
    try:
        # Query auth.users via Supabase admin API
        result = client.auth.admin.get_user_by_id(user_id)
        if result and result.user and result.user.email:
            return result.user.email
    except Exception as e:
        logger.warning(f"[EXEC] Failed to get user email: {e}")
    return None


def normalize_destination_for_delivery(
    destination: Optional[dict],
    user_email: Optional[str],
) -> Optional[dict]:
    """
    Normalize destination for delivery, defaulting to user's email.

    ADR-066 email-first: If destination is incomplete or missing target,
    fall back to sending to user's registered email address.

    Args:
        destination: The agent's destination config
        user_email: User's email address

    Returns:
        Normalized destination dict, or None if no valid destination
    """
    # No destination at all - use email (aliased to gmail exporter)
    if not destination:
        if user_email:
            logger.info(f"[EXEC] No destination - defaulting to email: {user_email}")
            return {
                "platform": "email",
                "target": user_email,
                "format": "send",
            }
        return None

    platform = destination.get("platform")
    target = destination.get("target")

    # Destination has valid target - use as-is
    if target and target not in ("", "dm"):  # "dm" was a placeholder
        return destination

    # Missing or incomplete target - fall back to email
    if user_email:
        logger.info(
            f"[EXEC] Incomplete destination (platform={platform}, target={target}) "
            f"- defaulting to email: {user_email}"
        )
        return {
            "platform": "email",
            "target": user_email,
            "format": "send",
        }

    # No fallback available
    logger.warning(f"[EXEC] Incomplete destination and no user email available")
    return destination


async def get_next_run_number(client, agent_id: str) -> int:
    """Get the next version number for an agent."""
    result = (
        client.table("agent_runs")
        .select("version_number")
        .eq("agent_id", agent_id)
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]["version_number"] + 1
    return 1


async def create_version_record(
    client,
    agent_id: str,
    version_number: int,
) -> dict:
    """Create a new version record in 'generating' status."""
    version_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    result = (
        client.table("agent_runs")
        .insert({
            "id": version_id,
            "agent_id": agent_id,
            "version_number": version_number,
            "status": "generating",
            "created_at": now,
            # ADR-042: Leave these NULL - grow into schema
            # edit_diff, edit_categories, edit_distance_score,
            # context_snapshot_id, pipeline_run_id
        })
        .execute()
    )

    return result.data[0] if result.data else {"id": version_id}


# Patterns that indicate the model narrated its tool usage instead of producing content
_NARRATION_PATTERNS = [
    "let me check",
    "let me search",
    "let me look",
    "i'll search",
    "i'll check",
    "i'll look",
    "i will search",
    "i will check",
    "let me see what",
    "checking the",
    "searching for",
    "looking for platform content",
    "let me find",
]


def _strip_tool_narration(draft: str) -> str:
    """
    Strip tool-use narration from draft if the entire output is just narration.

    Returns cleaned draft, or empty string if draft was purely narration.
    """
    lines = [line.strip() for line in draft.strip().splitlines() if line.strip()]
    if not lines:
        return ""

    # If the entire draft is 1-3 short lines that match narration patterns, reject it
    if len(lines) <= 3 and len(draft.split()) < 30:
        draft_lower = draft.lower()
        if any(pattern in draft_lower for pattern in _NARRATION_PATTERNS):
            logger.warning(f"[GENERATE] Stripped tool narration from draft: {draft[:100]}")
            return ""

    return draft


def _build_headless_system_prompt(
    skill: str,
    trigger_context: Optional[dict] = None,
    research_directive: Optional[str] = None,
    agent: Optional[dict] = None,
    user_context: Optional[list] = None,
) -> str:
    """
    Build system prompt for headless mode generation (ADR-080/081/087/101/109).

    Args:
        skill: The agent skill (digest, prepare, synthesize, etc.)
        trigger_context: Optional trigger info with signal reasoning
        research_directive: Optional research instruction for research-scope agents
        agent: Optional agent dict with agent_instructions and agent_memory
        user_context: Optional list of user_memory rows (profile + preferences)

    Returns:
        Complete system prompt string

    Note: Feedback/learned preferences are in workspace memory/preferences.md,
    loaded by strategies via load_context() into gathered context (ADR-117).
    """
    prompt = f"""You are generating a {skill} agent.

## Output Rules
- Follow the format and instructions in the user message exactly.
- Be concise and professional — keep content tight and scannable.
- Do not invent information not present in the provided context or your research findings.
- Do not use emojis in headers or content unless the user's preferences explicitly request them.
- Use plain markdown headers (##, ###) and bullet points for structure.
- If the user's context mentions a preference for conciseness, prioritize brevity over completeness."""

    # Inject user context (profile + preferences) for personalized output
    if user_context:
        context_lines = []
        for row in user_context:
            key = row.get("key", "")
            value = row.get("value", "")
            if key in ("name", "role", "company", "timezone"):
                context_lines.append(f"- {key.title()}: {value}")
            elif key.startswith("tone_") or key.startswith("verbosity_"):
                context_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
            elif key.startswith("preference:"):
                context_lines.append(f"- Prefers: {value}")
        if context_lines:
            prompt += "\n\n## User Context\n" + "\n".join(context_lines)

    # ADR-087: Inject agent-scoped instructions and memory
    if agent:
        instructions = (agent.get("agent_instructions") or "").strip()
        if instructions:
            prompt += f"""

## Agent Instructions
The user has set these behavioral directives for this agent:
{instructions}"""

        memory = agent.get("agent_memory") or {}
        memory_parts = []

        # Goal (for goal-mode agents)
        goal = memory.get("goal")
        if goal:
            desc = goal.get("description", "")
            status = goal.get("status", "")
            if desc:
                memory_parts.append(f"**Goal:** {desc}")
                if status:
                    memory_parts.append(f"Goal status: {status}")

        observations = memory.get("observations", [])
        if observations:
            memory_parts.append("**Recent observations:**")
            for obs in observations[-5:]:
                memory_parts.append(f"- {obs.get('date', '')}: {obs.get('note', '')}")

        # Review log (last 3 entries)
        review_log = memory.get("review_log", [])
        if review_log:
            memory_parts.append("**Review history:**")
            for entry in review_log[-3:]:
                memory_parts.append(f"- {entry.get('date', '')}: {entry.get('note', '')}")

        if memory_parts:
            prompt += "\n\n## Agent Memory\n" + "\n".join(memory_parts)

    # ADR-117: Learned preferences now in workspace memory/preferences.md,
    # loaded by all strategies via load_context(). No system prompt injection needed.

    # ADR-081: Research directive overrides default tool guidance
    if research_directive:
        prompt += f"""

## Research Directive
{research_directive}

## Tool Usage
You have investigation tools available: Search, Read, List, WebSearch, GetSystemState.
- Use **WebSearch** to conduct web research as described above.
- Use **Search** or **Read** to cross-reference with the user's platform data if provided.
- Conduct 2-4 targeted searches, then synthesize findings into the agent format.
- After researching, generate the agent in a single pass — do not search further."""
    else:
        prompt += """

## Tool Usage (Headless Mode)
You have read-only investigation tools available: Search, Read, List, WebSearch, GetSystemState.
- Use tools ONLY if the gathered context in the user message is clearly insufficient to produce the agent.
- Prefer generating from the provided context — most agents have enough.
- If you do use a tool, do so in the first turn, then generate in the next.
- NEVER use tools to stall — if context is adequate, generate immediately.
- NEVER narrate your tool usage in the final output. Do not write things like "Let me check..." or "I'll search for..." — your output must be the finished agent content only.

## Empty Context Handling
If the gathered context says "(No context available)" or tools return no results:
- Still produce the agent in the requested format and structure.
- Note briefly that no recent activity was found for the period.
- Do NOT output investigation narration or meta-commentary about missing data.
- A short, properly formatted "no activity" output is always better than a tool-use narrative."""

    # Inject trigger context when available
    if trigger_context:
        trigger_type = trigger_context.get("type", "")

        # Proactive review: forward the review decision note to generation
        if trigger_type == "proactive_review":
            review_decision = trigger_context.get("review_decision", {})
            review_note = review_decision.get("note", "")
            if review_note:
                prompt += f"\n\n## Review Context\nThis agent was triggered by a proactive review pass that found:\n{review_note}\n\nUse this as your starting point. The review pass already identified these themes — focus on synthesizing insights from the gathered context above rather than re-investigating."

        # Signal processing: forward signal reasoning
        signal_reasoning = trigger_context.get("signal_reasoning", "")
        signal_ctx = trigger_context.get("signal_context", {})
        if signal_reasoning:
            prompt += f"\n\n## Signal Context\nThis agent was triggered by signal processing because:\n{signal_reasoning}"
        if signal_ctx:
            entity = signal_ctx.get("entity", "")
            platforms = signal_ctx.get("platforms", [])
            if entity:
                prompt += f"\nFocus entity: {entity}"
            if platforms:
                prompt += f"\nRelevant platforms: {', '.join(platforms)}"

    return prompt


# ADR-109: Scope-aware tool round limits
HEADLESS_TOOL_ROUNDS = {
    "platform":        2,   # Rarely needs tools — context is pre-gathered
    "cross_platform":  3,   # Occasionally useful for cross-referencing
    "knowledge":       3,   # Workspace-driven queries
    "research":        6,   # Needs room for web search + follow-up
    "autonomous":      8,   # Full investigation: workspace + knowledge base + web
}


async def generate_draft_inline(
    client,
    user_id: str,
    agent: dict,
    gathered_context: str,
    trigger_context: Optional[dict] = None,
    research_directive: Optional[str] = None,
) -> str:
    """
    Generate draft content via agent in headless mode (ADR-080/081).

    The agent has read-only tools (Search, Read, List, WebSearch,
    GetSystemState) available for investigation when gathered context
    is insufficient. Most agents generate in a single turn
    without tool use.

    ADR-042: Replaces execute_synthesize_step(). No separate work_ticket.
    ADR-080: Unified agent in headless mode — chat_completion_with_tools
    with mode-gated primitives.
    ADR-081: Binding-aware tool rounds. Research/hybrid types get higher
    limits and a research_directive so the agent does its own web research.
    """
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import (
        get_tools_for_mode,
        create_headless_executor,
    )
    from services.agent_pipeline import (
        build_skill_prompt,
        validate_output,
    )

    agent_id = agent.get("id")
    skill = agent.get("skill", "custom")
    scope = agent.get("scope", "cross_platform")
    type_config = agent.get("type_config", {})
    recipient_context = agent.get("recipient_context", {})

    # Format recipient context
    recipient_str = ""
    if recipient_context:
        name = recipient_context.get("name", "")
        role = recipient_context.get("role", "")
        priorities = recipient_context.get("priorities", [])
        if name or role:
            recipient_str = f"RECIPIENT: {name}"
            if role:
                recipient_str += f" ({role})"
            if priorities:
                recipient_str += f"\nPRIORITIES: {', '.join(priorities)}"

    # ADR-117: Feedback preferences now in workspace memory/preferences.md,
    # loaded by strategies via load_context(). No separate injection needed.

    # ADR-106 Phase 2: Load intelligence from workspace (source of truth)
    from services.workspace import AgentWorkspace, get_agent_slug
    ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
    await ws.ensure_seeded(agent)  # Lazy migration from DB columns

    # Read workspace-based intelligence
    ws_instructions = await ws.read("AGENT.md") or ""
    ws_observations = await ws.get_observations()
    ws_review_log = await ws.get_review_log()
    ws_goal = await ws.get_goal()

    # Build workspace-sourced agent dict for prompt building
    # (replaces reading from agent["agent_instructions"] / agent["agent_memory"])
    workspace_agent = {
        **agent,
        "agent_instructions": ws_instructions,
        "agent_memory": {
            "observations": ws_observations,
            "review_log": ws_review_log,
            **({"goal": ws_goal} if ws_goal else {}),
        },
    }

    # Build skill-specific prompt (user message)
    # ADR-101: past_versions moved to system prompt as learned_preferences
    prompt = build_skill_prompt(
        skill=skill,
        config=type_config,
        agent=workspace_agent,
        gathered_context=gathered_context,
        recipient_text=recipient_str,
        past_versions="",
    )

    # ADR-108: Read user context from /memory/ files instead of user_memory table
    user_context = None
    try:
        from services.workspace import UserMemory
        um = UserMemory(client, user_id)
        memory_files = um.read_all_sync()
        # Build key-value list matching the shape _build_headless_system_prompt expects
        user_context = []
        profile = UserMemory._parse_memory_md(memory_files.get("MEMORY.md"))
        for k, v in profile.items():
            if v:
                user_context.append({"key": k, "value": v})
        prefs = UserMemory._parse_preferences_md(memory_files.get("preferences.md"))
        for platform, settings in prefs.items():
            if settings.get("tone"):
                user_context.append({"key": f"tone_{platform}", "value": settings["tone"]})
            if settings.get("verbosity"):
                user_context.append({"key": f"verbosity_{platform}", "value": settings["verbosity"]})
        notes = UserMemory._parse_notes_md(memory_files.get("notes.md"))
        for note in notes[:5]:
            user_context.append({"key": f"preference:{note['content'][:40]}", "value": note["content"]})
    except Exception as e:
        logger.warning(f"[GENERATE] Failed to fetch user context: {e}")

    # ADR-109: Headless system prompt with workspace-sourced intelligence
    system_prompt = _build_headless_system_prompt(
        skill, trigger_context, research_directive, workspace_agent, user_context,
    )

    # ADR-109: Tool round limit based on scope
    max_tool_rounds = HEADLESS_TOOL_ROUNDS.get(scope, 3)

    # Prepare (meeting prep) needs more rounds for per-attendee research + WebSearch
    if skill == "prepare":
        max_tool_rounds = max(max_tool_rounds, 5)

    # ADR-080: Mode-gated tools and executor
    # ADR-092: Pass agent sources so headless RefreshPlatformContent can scope to them
    # ADR-106: Pass agent dict so workspace primitives have agent context
    headless_tools = get_tools_for_mode("headless")
    executor = create_headless_executor(
        client, user_id,
        agent_sources=agent.get("sources"),
        agent=agent,
    )

    import json

    try:
        # ADR-080: Agentic loop — agent can use read-only tools if needed
        messages = [{"role": "user", "content": prompt}]
        tools_used = []  # Track tool names for observability

        # ADR-101: Accumulate token usage across all tool rounds
        total_input_tokens = 0
        total_output_tokens = 0

        for round_num in range(max_tool_rounds + 1):
            response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=headless_tools,
                model=SONNET_MODEL,
                max_tokens=4000,
            )

            # ADR-101: Track tokens from each round
            if response.usage:
                total_input_tokens += response.usage.get("input_tokens", 0)
                total_output_tokens += response.usage.get("output_tokens", 0)

            # Agent finished or hit token limit — take whatever text exists
            if response.stop_reason in ("end_turn", "max_tokens") or not response.tool_uses:
                draft = response.text.strip()
                if response.stop_reason == "max_tokens":
                    logger.warning("[GENERATE] Headless agent hit max_tokens — draft may be truncated")
                if round_num > 0:
                    logger.info(
                        f"[GENERATE] Headless agent used {round_num} tool round(s): "
                        f"{', '.join(tools_used)}"
                    )
                break

            # Agent wants to use tools — check round limit
            if round_num >= max_tool_rounds:
                logger.warning(
                    f"[GENERATE] Headless agent hit max tool rounds ({max_tool_rounds}), "
                    f"tools used: {', '.join(tools_used)}"
                )
                # If agent has text alongside tool calls, use it
                if response.text and response.text.strip():
                    draft = response.text.strip()
                    break

                # Force a final synthesis call with no tools available
                logger.info("[GENERATE] Forcing final synthesis call (no tools)")
                messages.append({"role": "assistant", "content": response.text or ""})
                messages.append({"role": "user", "content": "You have reached the tool limit. Please synthesize all the information gathered so far and produce the final agent now. Do not request any more tools."})
                final_response = await chat_completion_with_tools(
                    messages=messages,
                    system=system_prompt,
                    tools=[],  # No tools — force text output
                    model=SONNET_MODEL,
                    max_tokens=4000,
                )
                # ADR-101: Track tokens from synthesis call
                if final_response.usage:
                    total_input_tokens += final_response.usage.get("input_tokens", 0)
                    total_output_tokens += final_response.usage.get("output_tokens", 0)
                draft = final_response.text.strip() if final_response.text else ""
                break

            # Build assistant message with tool use blocks
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

            # Execute tools and collect results
            tool_results = []
            for tu in response.tool_uses:
                tools_used.append(tu.name)
                logger.info(f"[GENERATE] Headless tool: {tu.name}({str(tu.input)[:100]})")
                result = await executor(tu.name, tu.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result) if isinstance(result, dict) else str(result),
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            # for/else: loop completed without break — safety net
            draft = ""

        if not draft:
            raise ValueError("Agent produced empty draft")

        # Detect critically bad output: tool-use narration leaked into draft
        draft = _strip_tool_narration(draft)

        if not draft:
            raise ValueError("Agent produced only tool-use narration, no actual content")

        # Validate output (non-blocking for soft issues, blocking for critical)
        validation = validate_output(skill, draft, type_config)
        if not validation.get("valid"):
            logger.warning(f"[GENERATE] Validation warnings: {validation.get('issues', [])}")

        # Block critically short output and force a retry synthesis
        word_count = len(draft.split())
        if word_count < 20:
            logger.warning(f"[GENERATE] Draft critically short ({word_count} words), forcing synthesis retry")
            messages.append({"role": "assistant", "content": draft})
            messages.append({"role": "user", "content": (
                "Your output was too short and incomplete. You MUST produce the full agent content "
                "in the requested format now. If no platform activity was found, still produce a "
                "properly structured output noting the lack of activity. Do not narrate — just write the content."
            )})
            retry_response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=[],
                model=SONNET_MODEL,
                max_tokens=4000,
            )
            if retry_response.usage:
                total_input_tokens += retry_response.usage.get("input_tokens", 0)
                total_output_tokens += retry_response.usage.get("output_tokens", 0)
            retry_draft = (retry_response.text or "").strip()
            if len(retry_draft.split()) > word_count:
                draft = retry_draft
                logger.info(f"[GENERATE] Synthesis retry produced {len(draft.split())} words")

        # ADR-101: Return draft + token usage for per-agent cost tracking
        usage = {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
        }
        logger.info(f"[GENERATE] Token usage: {total_input_tokens} in / {total_output_tokens} out")
        return draft, usage

    except Exception as e:
        logger.error(f"[GENERATE] LLM call failed: {e}")
        raise


async def update_version_for_delivery(
    client,
    version_id: str,
    draft_content: str,
    metadata: Optional[dict] = None,
):
    """
    Prepare version for delivery by storing content.

    ADR-066: Versions go directly to delivery, no staged status.
    Status remains 'generating' until delivery completes.
    ADR-101: Optional metadata (tokens, model) stored for cost tracking.
    """
    update = {
        "draft_content": draft_content,
        "final_content": draft_content,  # ADR-066: No editing step, content is final
    }
    if metadata:
        update["metadata"] = metadata
    client.table("agent_runs").update(update).eq("id", version_id).execute()


# =============================================================================
# ADR-116 Phase 4: Agent Card Auto-Generation
# =============================================================================

async def _generate_agent_card(client, user_id: str, agent: dict, version_number: int):
    """
    Auto-generate agent-card.json in the agent's workspace after each run.

    The card is a structured, machine-readable identity derived from workspace
    files + database metadata. Consumed by DiscoverAgents, MCP tools, and
    external agents (Claude Desktop, ChatGPT).
    """
    import json
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    slug = get_agent_slug(agent)
    ws = AgentWorkspace(client, user_id, slug)

    # Read identity files for card generation
    agent_md = await ws.read("AGENT.md")
    thesis = await ws.read("thesis.md")

    # Extract first paragraph of AGENT.md as description
    description = None
    if agent_md:
        paragraphs = agent_md.strip().split("\n\n")
        # Skip frontmatter/headers, find first real paragraph
        for p in paragraphs:
            stripped = p.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                description = stripped[:300]
                break

    # Compute maturity signals
    run_count = 0
    try:
        run_result = (
            client.table("agent_runs")
            .select("id", count="exact")
            .eq("agent_id", agent_id)
            .execute()
        )
        run_count = run_result.count or 0
    except Exception:
        pass

    # Count knowledge files produced by this agent via metadata RPC
    knowledge_files_count = 0
    try:
        kf_result = client.rpc("search_knowledge_by_metadata", {
            "p_user_id": user_id,
            "p_agent_id": str(agent_id),
            "p_limit": 100,
        }).execute()
        knowledge_files_count = len(kf_result.data or [])
    except Exception:
        pass

    card = {
        "schema_version": "1",
        "agent_id": str(agent_id),
        "title": agent.get("title"),
        "slug": slug,
        "skill": agent.get("skill"),
        "scope": agent.get("scope"),
        "description": description,
        "thesis_summary": thesis[:300] if thesis else None,
        "sources": agent.get("sources", []),
        "schedule": agent.get("schedule"),
        "maturity": {
            "total_runs": run_count,
            "knowledge_files_produced": knowledge_files_count,
            "latest_version": version_number,
        },
        "last_run_at": agent.get("last_run_at"),
        "interop": {
            "mcp_resource": f"workspace://agents/{slug}/",
            "input_format": "platform_content",
            "output_format": "markdown",
        },
    }

    await ws.write(
        "agent-card.json",
        json.dumps(card, indent=2, default=str),
        summary=f"Agent card for {agent.get('title')} (auto-generated)",
    )
    logger.info(f"[EXEC] ADR-116: Agent card generated for {slug}")


# =============================================================================
# Main Entry Point - ADR-042, ADR-045, ADR-066 Delivery-First
# =============================================================================

async def execute_agent_generation(
    client,
    user_id: str,
    agent: dict,
    trigger_context: Optional[dict] = None,
) -> dict:
    """
    Execute agent generation with immediate delivery (no approval gate).

    ADR-042: Simplified single-call flow
    ADR-109: Strategy selection based on scope
    ADR-049: Context freshness checks and source snapshots
    ADR-066: Delivery-first, no governance - always attempt delivery

    Args:
        client: Supabase client
        user_id: User UUID
        agent: Full agent dict (from database)
        trigger_context: Optional trigger info (schedule, event, manual)

    Returns:
        Result dict with run_id, status, message
        Status is 'delivered' or 'failed' (no 'staged' per ADR-066)
    """
    from services.execution_strategies import get_execution_strategy
    from services.freshness import (
        check_agent_freshness,
        record_source_snapshots,
    )

    agent_id = agent.get("id")
    skill = agent.get("skill", "custom")
    scope = agent.get("scope", "cross_platform")
    title = agent.get("title", "Untitled")
    trigger_type = trigger_context.get("type", "manual") if trigger_context else "manual"

    logger.info(
        f"[EXEC] Starting: {title} ({agent_id}), "
        f"trigger={trigger_type}, scope={scope}, skill={skill}"
    )

    version = None
    freshness_result = None

    try:
        # ADR-049: Check source freshness before generation
        freshness_result = await check_agent_freshness(client, user_id, agent)
        if not freshness_result["all_fresh"]:
            stale_count = len(freshness_result["stale_sources"])
            never_synced_count = len(freshness_result["never_synced"])
            logger.info(
                f"[EXEC] Freshness: {stale_count} stale, {never_synced_count} never synced"
            )
            # Note: We proceed with generation using available data
            # Targeted sync is handled separately if user requests it

        # 1. Get next version number
        next_version = await get_next_run_number(client, agent_id)

        # 2. Create version record (generating)
        version = await create_version_record(client, agent_id, next_version)
        version_id = version["id"]

        # 3. ADR-045: Select and execute strategy for context gathering
        strategy = get_execution_strategy(agent)
        gathered_result = await strategy.gather_context(client, user_id, agent)

        # Convert strategy result to legacy format for compatibility
        gathered_context = gathered_result.content
        context_summary = gathered_result.summary
        context_summary["sources_used"] = gathered_result.sources_used
        context_summary["total_items_fetched"] = gathered_result.items_fetched
        # ADR-049: Include freshness info in summary
        context_summary["freshness"] = {
            "all_fresh": freshness_result["all_fresh"] if freshness_result else True,
            "stale_sources": len(freshness_result["stale_sources"]) if freshness_result else 0,
        }

        # 4. Generate draft inline (ADR-080/081: pass trigger_context + research_directive)
        research_directive = context_summary.get("research_directive")
        draft, usage = await generate_draft_inline(
            client, user_id, agent, gathered_context,
            trigger_context, research_directive,
        )

        # 5. ADR-066: Prepare version for delivery (no staged status)
        # ADR-101: Store execution metadata (tokens, model) on version
        # ADR-049 evolution: Include context provenance for traceability
        version_metadata = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "model": SONNET_MODEL,
            "platform_content_ids": gathered_result.platform_content_ids,
            "items_fetched": gathered_result.items_fetched,
            "sources_used": gathered_result.sources_used,
            "strategy": context_summary.get("strategy", "unknown"),
            # Persist trigger provenance so runs can be attributed to scheduler/manual/event paths.
            "trigger_type": trigger_type,
        }
        await update_version_for_delivery(client, version_id, draft, metadata=version_metadata)

        # ADR-073: Mark consumed platform content as retained
        if gathered_result.platform_content_ids:
            try:
                from services.platform_content import mark_content_retained
                await mark_content_retained(
                    client,
                    gathered_result.platform_content_ids,
                    reason="agent_execution",
                    ref=version_id,
                )
            except Exception as e:
                logger.warning(f"[EXEC] Failed to mark content retained: {e}")

        # ADR-049: Record source snapshots for audit trail
        # sources_used is a list of strings like "platform:slack", "other:document"
        # Build snapshot from the agent's source configs
        sources_for_snapshot = []
        for source in agent.get("sources", []):
            if source.get("type") == "integration_import":
                sources_for_snapshot.append({
                    "platform": source.get("provider"),
                    "resource_id": source.get("resource_id"),
                    "resource_name": source.get("resource_name"),
                    "user_id": user_id,
                })
        await record_source_snapshots(
            client, version_id, sources_for_snapshot,
            content_ids=gathered_result.platform_content_ids,
        )

        # 6. Update agent last_run_at
        client.table("agents").update({
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", agent_id).execute()

        # 7. ADR-066: Always attempt delivery (no governance check)
        # Email-first: normalize/fallback to user's email if destination incomplete
        # get_user_email requires service role (auth.admin API)
        from services.supabase import get_service_client as _get_svc
        user_email = get_user_email(_get_svc(), user_id)
        raw_destination = agent.get("destination")
        destination = normalize_destination_for_delivery(raw_destination, user_email)

        # Update agent with normalized destination if it changed
        if destination and destination != raw_destination:
            try:
                client.table("agents").update({
                    "destination": destination,
                }).eq("id", agent_id).execute()
                logger.info(f"[EXEC] Updated agent destination to email-first default")
            except Exception:
                pass  # Non-fatal

        final_status = "delivered"
        delivery_result = None
        delivery_error = None

        if destination:
            logger.info(f"[EXEC] ADR-066 delivery-first: delivering version={version_id}")

            try:
                from services.delivery import get_delivery_service
                delivery_service = get_delivery_service(client)
                delivery_result = await delivery_service.deliver_version(
                    version_id=version_id,
                    user_id=user_id,
                )
                if delivery_result.status.value == "success":
                    final_status = "delivered"
                    # Update version status to delivered
                    now = datetime.now(timezone.utc).isoformat()
                    client.table("agent_runs").update({
                        "status": "delivered",
                        "delivered_at": now,
                    }).eq("id", version_id).execute()
                else:
                    final_status = "failed"
                    delivery_error = delivery_result.error_message
                    client.table("agent_runs").update({
                        "status": "failed",
                        "delivery_error": delivery_error,
                    }).eq("id", version_id).execute()
                logger.info(f"[EXEC] Delivery: {delivery_result.status.value}")
            except Exception as e:
                logger.error(f"[EXEC] Delivery failed: {e}")
                final_status = "failed"
                delivery_error = str(e)
                client.table("agent_runs").update({
                    "status": "failed",
                    "delivery_error": delivery_error,
                }).eq("id", version_id).execute()
        else:
            # No destination configured - mark as delivered (content generated successfully)
            now = datetime.now(timezone.utc).isoformat()
            client.table("agent_runs").update({
                "status": "delivered",
                "delivered_at": now,
            }).eq("id", version_id).execute()
            logger.info(f"[EXEC] No destination - content ready (version={version_id})")

        # ADR-107: Write agent output to /knowledge/ filesystem
        # Closes the accumulation loop — agent outputs become searchable knowledge
        if final_status == "delivered" and draft:
            try:
                from services.workspace import KnowledgeBase
                from services.supabase import get_service_client as _get_svc3
                kb = KnowledgeBase(_get_svc3(), user_id)
                knowledge_path = KnowledgeBase.get_knowledge_path(skill, title)
                await kb.write(
                    path=knowledge_path,
                    content=draft,
                    summary=f"{title} v{next_version}",
                    metadata={
                        "agent_id": str(agent_id),
                        "run_id": str(version_id),
                        "content_class": KnowledgeBase.CONTENT_CLASS_MAP.get(skill, "analyses"),
                        "skill": skill,
                        "scope": scope,
                        "version_number": next_version,
                    },
                    tags=[skill, agent.get("mode", "recurring")],
                )
                logger.info(f"[EXEC] ADR-107: Stored knowledge at {knowledge_path}")
            except Exception as e:
                logger.warning(f"[EXEC] ADR-107: Failed to store knowledge: {e}")
                # Non-fatal — don't block delivery

        # ADR-116 Phase 4: Auto-generate agent card after successful run
        if final_status == "delivered":
            try:
                await _generate_agent_card(client, user_id, agent, next_version)
            except Exception as e:
                logger.warning(f"[EXEC] ADR-116: Agent card generation failed: {e}")
                # Non-fatal

        logger.info(
            f"[EXEC] Complete: {title}, version={next_version}, "
            f"status={final_status}, strategy={strategy.strategy_name}"
        )

        # Activity log: record this agent run (ADR-063)
        # Requires service role — activity_log has no user INSERT policy
        try:
            from services.activity_log import write_activity
            from services.supabase import get_service_client as _get_svc2
            await write_activity(
                client=_get_svc2(),
                user_id=user_id,
                event_type="agent_run",
                summary=f"{title} v{next_version} {final_status}",
                event_ref=version_id,
                metadata={
                    "agent_id": str(agent_id),
                    "version_number": next_version,
                    "skill": skill,  # ADR-109: For pattern detection
                    "scope": scope,
                    "strategy": strategy.strategy_name,
                    "final_status": final_status,
                    "delivery_error": delivery_error,
                    "input_tokens": usage.get("input_tokens", 0),  # ADR-101
                    "output_tokens": usage.get("output_tokens", 0),  # ADR-101
                },
            )
        except Exception:
            pass  # Non-fatal — never block execution

        # ADR-114: Event-driven Composer heartbeat on delivered runs
        if final_status == "delivered":
            try:
                from services.composer import maybe_trigger_heartbeat
                await maybe_trigger_heartbeat(client, user_id, "agent_run_delivered", {
                    "agent_id": str(agent_id), "skill": skill,
                })
            except Exception as e:
                logger.warning(f"[EXEC] Event heartbeat trigger failed: {e}")

        return {
            "success": final_status == "delivered",
            "run_id": version_id,
            "version_number": next_version,
            "status": final_status,
            "message": f"Run {next_version} {final_status}" + (f": {delivery_error}" if delivery_error else ""),
            "delivery": delivery_result.model_dump() if delivery_result else None,
            "strategy": strategy.strategy_name,  # ADR-045: Track which strategy was used
        }

    except Exception as e:
        logger.error(f"[EXEC] Error: {e}")

        # ADR-066: Mark version as failed (not rejected)
        if version:
            try:
                client.table("agent_runs").update({
                    "status": "failed",
                    "delivery_error": str(e),
                }).eq("id", version["id"]).execute()
            except Exception as e2:
                logger.error(f"Failed to mark version {version['id']} as failed: {e2}")

        return {
            "success": False,
            "run_id": version["id"] if version else None,
            "status": "failed",
            "message": str(e),
        }
