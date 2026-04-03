"""
Agent Execution Service - ADR-042 Simplified Flow + ADR-066 Delivery-First

Single Execute call for agent generation with immediate delivery (no approval gate).

Flow:
  Execute(action="agent.generate", target="agent:uuid")
    → check_agent_freshness() (ADR-049)
    → strategy.gather_context() (ADR-045 + ADR-073)
    → generate_draft_inline()
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
- Role-specific prompts (ROLE_PROMPTS, build_role_prompt)
- Output validation (validate_output)
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import httpx


def _total_input_tokens(usage: dict) -> int:
    """Sum all input token fields including prompt cache tokens."""
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )

logger = logging.getLogger(__name__)

RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")

# ADR-130: Type-scoped capability check replaces role-based SKILL_ENABLED_ROLES
from services.agent_framework import has_asset_capabilities

async def _fetch_skill_docs() -> Optional[str]:
    """Fetch SKILL.md content from the output gateway for all available skills.

    ADR-118 D.4: Dynamically discovers available skills from render service
    instead of hard-coded type→folder mapping. Falls back gracefully.
    Called during headless system prompt assembly (ADR-118 D.1).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # ADR-118 D.4: Discover skills dynamically from render service
            type_to_folder = {}
            try:
                resp = await client.get(f"{RENDER_SERVICE_URL}/skills")
                if resp.status_code == 200:
                    data = resp.json()
                    type_to_folder = data.get("type_to_folder", {})
            except Exception:
                pass

            if not type_to_folder:
                # Fallback: known skill folders (graceful degradation)
                for folder in ["pdf", "pptx", "xlsx", "chart"]:
                    type_to_folder[folder] = folder

            # Fetch SKILL.md for each discovered skill
            skill_sections = []
            for skill_type, folder in type_to_folder.items():
                try:
                    resp = await client.get(f"{RENDER_SERVICE_URL}/skills/{folder}/SKILL.md")
                    if resp.status_code == 200:
                        skill_sections.append(resp.text)
                except Exception:
                    continue

            if skill_sections:
                return "\n\n---\n\n".join(skill_sections)
    except Exception as e:
        logger.warning(f"[GENERATE] Failed to fetch skill docs from output gateway: {e}")
    return None

async def _compose_output_html(
    client, user_id: str, agent_slug: str, output_folder: str,
    title: str = "Output", pending_renders: list = None,
    layout_mode: str = "document",
) -> Optional[str]:
    """ADR-130 Phase 2: Post-generation compose step.

    Calls /compose on the render service to convert output.md + asset URLs
    into styled HTML. Layout mode determines composition strategy
    (document/presentation/dashboard/data).
    Non-fatal — agent run succeeds even if compose fails.
    """
    from services.workspace import AgentWorkspace

    ws = AgentWorkspace(client, user_id, agent_slug)

    # Read the output.md from the output folder
    output_md_path = f"outputs/{output_folder}/output.md"
    md_content = await ws.read(output_md_path)
    if not md_content:
        logger.warning(f"[COMPOSE] No output.md at {output_md_path}")
        return None

    # Build asset references from pending_renders
    assets = []
    for r in (pending_renders or []):
        url = r.get("output_url") or r.get("content_url")
        path = r.get("path", "")
        if url and path:
            # Extract filename from path for ref matching
            ref = path.split("/")[-1] if "/" in path else path
            assets.append({"ref": ref, "url": url})

    # Call /compose endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            headers = {}
            render_secret = os.environ.get("RENDER_SERVICE_SECRET", "")
            if render_secret:
                headers["X-Render-Secret"] = render_secret

            resp = await http.post(
                f"{RENDER_SERVICE_URL}/compose",
                json={
                    "markdown": md_content,
                    "title": title,
                    "layout_mode": layout_mode,
                    "assets": assets,
                    "user_id": user_id,
                },
                headers=headers,
            )

            if resp.status_code != 200:
                logger.warning(f"[COMPOSE] HTTP {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json()
            if not data.get("success"):
                logger.warning(f"[COMPOSE] Failed: {data.get('error')}")
                return None

            html = data.get("html", "")
            if not html:
                return None

            # Write output.html to workspace
            html_path = f"outputs/{output_folder}/output.html"
            await ws.write(html_path, html, summary="Composed HTML output")

            return html

    except Exception as e:
        logger.warning(f"[COMPOSE] Request failed: {e}")
        return None


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
    # No destination at all - use email delivery via Resend
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
    "let me read",
    "let me find",
    "let me see what",
    "let me review",
    "let me examine",
    "let me query",
    "let me fetch",
    "now let me",
    "i'll search",
    "i'll check",
    "i'll look",
    "i'll read",
    "i'll review",
    "i will search",
    "i will check",
    "i will read",
    "checking the",
    "searching for",
    "looking for platform content",
    "now i need to",
    "first, i'll",
    "first, let me",
    "i should read",
    "i should check",
    "i need to read",
    "i need to check",
]


def _is_narration(text: str) -> bool:
    """Check if text is tool-use narration rather than substantive content."""
    text_lower = text.lower().strip()
    return any(text_lower.startswith(p) or f"\n{p}" in text_lower for p in _NARRATION_PATTERNS)


def _strip_tool_narration(draft: str) -> str:
    """
    Strip tool-use narration from draft if the output is just narration.

    Catches both short narration (1-3 lines) and longer narration that starts
    with investigation language but never transitions to real content.

    Returns cleaned draft, or empty string if draft was purely narration.
    """
    lines = [line.strip() for line in draft.strip().splitlines() if line.strip()]
    if not lines:
        return ""

    draft_lower = draft.lower()

    # Short narration: 1-3 lines under 30 words
    if len(lines) <= 3 and len(draft.split()) < 30:
        if any(pattern in draft_lower for pattern in _NARRATION_PATTERNS):
            logger.warning(f"[GENERATE] Stripped short tool narration: {draft[:100]}")
            return ""

    # Longer narration: starts with narration pattern AND has no markdown structure
    # (real content has headers, lists, bold text; narration is plain prose about tool use)
    has_structure = any(
        line.startswith("#") or line.startswith("- ") or line.startswith("* ")
        or line.startswith("**") or line.startswith("| ")
        for line in lines
    )
    if not has_structure and _is_narration(draft):
        logger.warning(f"[GENERATE] Stripped unstructured tool narration: {draft[:100]}")
        return ""

    return draft


def _build_headless_system_prompt(
    role: str,
    trigger_context: Optional[dict] = None,
    research_directive: Optional[str] = None,
    agent: Optional[dict] = None,
    user_context: Optional[list] = None,
    skill_docs: Optional[str] = None,
) -> str:
    """
    Build system prompt for headless mode generation (ADR-080/081/087/101/109/117/118/143).

    Args:
        role: The agent role (digest, prepare, synthesize, etc.)
        trigger_context: Optional trigger info with signal reasoning
        research_directive: Optional research instruction for research-scope agents
        agent: Optional agent dict with agent_instructions and agent_memory
        user_context: Optional list of user_memory rows (profile + preferences)
        skill_docs: Optional SKILL.md content for authorized output skills (ADR-118 D.1)

    Returns:
        Complete system prompt string
    """
    prompt = f"""You are generating a {role} agent.

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

    # ADR-143: Preferences/feedback now loaded via load_context() as memory files.
    # No separate injection needed — feedback.md and methodology-*.md auto-load.

    # ADR-118 D.1: Inject SKILL.md content for authorized output skills.
    # Agents read skill docs to learn how to construct high-quality specs
    # for RuntimeDispatch (same model as Claude Code reading SKILL.md).
    if skill_docs:
        prompt += f"""

## Output Skill Documentation
You have access to RuntimeDispatch for producing binary artifacts.
Construct input specs according to these skill instructions:

{skill_docs}

When producing output that would benefit from a rendered artifact (PDF, PPTX, XLSX, chart),
use RuntimeDispatch with the spec format described above. Always produce a text version
alongside any binary — the text is the feedback surface for user edits."""

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

        # Pulse generate: forward the pulse decision context to generation (ADR-126)
        if trigger_type in ("pulse_generate", "proactive_review"):
            # pulse_generate: tier info in trigger_context
            pulse_tier = trigger_context.get("tier", "")
            review_decision = trigger_context.get("review_decision", {})
            review_note = review_decision.get("note", "")
            if review_note:
                prompt += f"\n\n## Pulse Context\nThis agent was triggered by a pulse (tier {pulse_tier}) that found:\n{review_note}\n\nUse this as your starting point — focus on synthesizing insights from the gathered context above rather than re-investigating."

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


# =============================================================================
# ADR-128/149: Agent Reflection — mandate context + self-reflection
# Terminology (ADR-149): "reflection" = agent self-awareness (agent scope),
#   "evaluation" = TP task quality judgment (task scope).
# =============================================================================

async def _build_mandate_context(ws, agent: dict) -> str:
    """ADR-154: Dissolved. Reflections now live on task awareness.md, not agent workspace."""
    return ""


_REFLECTION_BLOCK_RE = re.compile(
    r"\n---\s*\n*## Agent Reflection.*",
    re.DOTALL,
)

_REFLECTION_FIELDS_RE = re.compile(
    r"\*\*Mandate\*\*:\s*(.+?)(?:\n|$)"
    r".*?\*\*Domain Fitness\*\*:\s*(.+?)(?:\n|$)"
    r".*?\*\*Context Currency\*\*:\s*(.+?)(?:\n|$)"
    r".*?\*\*Output Confidence\*\*:\s*(.+?)(?:\n|$)",
    re.DOTALL,
)

# Legacy regex for old format — handles outputs from before ADR-149 rename
_LEGACY_ASSESSMENT_BLOCK_RE = re.compile(
    r"\n---\s*\n*## Contributor Assessment.*",
    re.DOTALL,
)


def _extract_agent_reflection(draft: str) -> tuple[str, Optional[dict]]:
    """
    Extract and strip the ## Agent Reflection block from draft (ADR-128/149).

    Returns (clean_draft, reflection_dict_or_None).
    Handles both new "Agent Reflection" and legacy "Contributor Assessment" headers.
    """
    match = _REFLECTION_BLOCK_RE.search(draft)
    if not match:
        # Try without the --- separator (some models omit it)
        alt_match = re.search(r"\n## Agent Reflection\b.*", draft, re.DOTALL)
        if alt_match:
            match = alt_match

    # Fallback: legacy "Contributor Assessment" header
    if not match:
        match = _LEGACY_ASSESSMENT_BLOCK_RE.search(draft)
    if not match:
        alt_match = re.search(r"\n## Contributor Assessment\b.*", draft, re.DOTALL)
        if alt_match:
            match = alt_match

    if not match:
        return draft, None

    reflection_text = match.group(0)
    clean_draft = draft[:match.start()].rstrip()

    # Parse the 4 fields
    fields_match = _REFLECTION_FIELDS_RE.search(reflection_text)
    if not fields_match:
        return clean_draft, None

    result = {
        "mandate": fields_match.group(1).strip(),
        "domain_fitness": fields_match.group(2).strip(),
        "context_currency": fields_match.group(3).strip(),
        "output_confidence": fields_match.group(4).strip(),
    }

    # Extract criteria eval if present (ADR-138: success criteria)
    criteria_match = re.search(r"\*\*Criteria Met\*\*:\s*(.+?)(?:\n\n|\n---|\Z)", reflection_text, re.DOTALL)
    if criteria_match:
        result["criteria_met"] = criteria_match.group(1).strip()

    # Extract Next Cycle Directive if present (self-improving execution loop)
    directive_match = re.search(
        r"## Next Cycle Directive\s*\n(.+?)(?:\n## |\Z)",
        reflection_text, re.DOTALL,
    )
    if not directive_match:
        # Might be in the portion after the reflection block was cut
        directive_match = re.search(
            r"## Next Cycle Directive\s*\n(.+?)(?:\n## |\Z)",
            draft[match.start():], re.DOTALL,
        )
    if directive_match:
        result["next_cycle_directive"] = directive_match.group(1).strip()

    return clean_draft, result


async def _append_agent_reflection(ws, reflection: dict) -> None:
    """ADR-154: Dissolved. Reflections now folded into task awareness.md by _post_run_domain_scan()."""
    pass


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
    effective_role: Optional[str] = None,
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
        get_headless_tools_for_agent,
        create_headless_executor,
    )
    from services.agent_pipeline import (
        build_role_prompt,
        validate_output,
    )

    agent_id = agent.get("id")
    role = effective_role or agent.get("role", "custom")  # ADR-117 Phase 3: duty override
    scope = agent.get("scope", "cross_platform")
    type_config = agent.get("type_config", {})
    recipient_context = {}  # Column dropped — recipient_context no longer on agents table

    # Format recipient context
    recipient_str = ""
    if recipient_context:
        name = recipient_context.get("name", "")
        recipient_role = recipient_context.get("role", "")
        priorities = recipient_context.get("priorities", [])
        if name or recipient_role:
            recipient_str = f"RECIPIENT: {name}"
            if recipient_role:
                recipient_str += f" ({recipient_role})"
            if priorities:
                recipient_str += f"\nPRIORITIES: {', '.join(priorities)}"

    # ADR-106/143: Load intelligence from workspace (source of truth)
    # Feedback + methodology loaded via load_context() automatically.
    from services.workspace import AgentWorkspace, get_agent_slug
    ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
    await ws.ensure_seeded(agent)  # Lazy migration from DB columns

    # ADR-143: Read workspace-based intelligence (simplified — feedback.md + methodology via load_context)
    ws_instructions = await ws.read("AGENT.md") or ""
    ws_goal = await ws.get_goal()

    # ADR-117 Phase 3: Load duty-specific context if running a non-seed duty
    duty_name = trigger_context.get("duty") if trigger_context else None
    if duty_name:
        duty_context = await ws.read_duty(duty_name)
        if duty_context:
            ws_instructions = ws_instructions + f"\n\n## Active Duty: {duty_name}\n{duty_context}"

    # Build workspace-sourced agent dict for prompt building
    workspace_agent = {
        **agent,
        "agent_instructions": ws_instructions,
        "agent_memory": {
            **({"goal": ws_goal} if ws_goal else {}),
        },
    }

    # ADR-128 Phase 1: Build mandate_context for contributor agents
    mandate_context = await _build_mandate_context(ws, agent)
    type_config = {**type_config, "mandate_context": mandate_context}

    # Build role-specific prompt (user message)
    prompt = build_role_prompt(
        role=role,
        config=type_config,
        agent=workspace_agent,
        gathered_context=gathered_context,
        recipient_text=recipient_str,
    )

    # ADR-108: Read user context from /memory/ files instead of user_memory table
    user_context = None
    try:
        from services.workspace import UserMemory
        um = UserMemory(client, user_id)
        memory_files = um.read_all_sync()
        # Build key-value list matching the shape _build_headless_system_prompt expects
        user_context = []
        profile = UserMemory._parse_memory_md(memory_files.get("IDENTITY.md"))
        for k, v in profile.items():
            if v:
                user_context.append({"key": k, "value": v})
        prefs = UserMemory._parse_preferences_md(memory_files.get("style.md"))
        for platform, settings in prefs.items():
            if settings.get("tone"):
                user_context.append({"key": f"tone_{platform}", "value": settings["tone"]})
            if settings.get("verbosity"):
                user_context.append({"key": f"verbosity_{platform}", "value": settings["verbosity"]})
        notes = UserMemory._parse_notes_md(memory_files.get("notes.md"))
        for note in notes[:5]:
            user_context.append({"key": f"preference:{note['content'][:40]}", "value": note["content"]})
        # ADR-143: Inject brand context for visual consistency
        brand = memory_files.get("BRAND.md", "").strip()
        if brand:
            user_context.append({"key": "brand", "value": brand})
    except Exception as e:
        logger.warning(f"[GENERATE] Failed to fetch user context: {e}")

    # ADR-130: Fetch SKILL.md for agents with asset capabilities (type-scoped)
    skill_docs = None
    if has_asset_capabilities(role):
        try:
            skill_docs = await _fetch_skill_docs()
        except Exception as e:
            logger.warning(f"[GENERATE] Skill docs fetch failed (non-fatal): {e}")

    # ADR-109/143: Headless system prompt with workspace-sourced intelligence
    system_prompt = _build_headless_system_prompt(
        role, trigger_context, research_directive, workspace_agent, user_context,
        skill_docs=skill_docs,
    )

    # ADR-109: Tool round limit based on scope
    max_tool_rounds = HEADLESS_TOOL_ROUNDS.get(scope, 3)

    # Planner/prepare needs more rounds for per-attendee research + WebSearch
    if role in ("prepare", "planner"):
        max_tool_rounds = max(max_tool_rounds, 5)

    # ADR-080: Mode-gated tools and executor
    # ADR-106: Pass agent dict so workspace primitives have agent context
    headless_tools = await get_headless_tools_for_agent(
        client, user_id, agent=agent, agent_sources=[],
    )
    executor = create_headless_executor(
        client, user_id,
        agent_sources=[],  # Column dropped — sources no longer on agents table
        agent=agent,
        dynamic_tools=headless_tools,
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

            # ADR-101: Track tokens from each round (including prompt cache)
            if response.usage:
                total_input_tokens += _total_input_tokens(response.usage)
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
                # If agent has substantive text (not narration) alongside tool calls, use it
                candidate = response.text.strip() if response.text else ""
                if candidate and not _is_narration(candidate):
                    draft = candidate
                    break

                # Force a final synthesis call with no tools available
                logger.info("[GENERATE] Forcing final synthesis call (no tools)")
                messages.append({"role": "assistant", "content": response.text or ""})
                messages.append({"role": "user", "content": "You have reached the tool limit. Please synthesize all the information gathered so far and produce the final output now. Do not request any more tools — produce the deliverable in its full format."})
                final_response = await chat_completion_with_tools(
                    messages=messages,
                    system=system_prompt,
                    tools=[],  # No tools — force text output
                    model=SONNET_MODEL,
                    max_tokens=4000,
                )
                # ADR-101: Track tokens from synthesis call (including prompt cache)
                if final_response.usage:
                    total_input_tokens += _total_input_tokens(final_response.usage)
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
        validation = validate_output(role, draft, type_config)
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
                total_input_tokens += _total_input_tokens(retry_response.usage)
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

        # ADR-118 D.3: Collect rendered files accumulated by RuntimeDispatch during generation
        pending_renders = getattr(executor, "auth", None)
        pending_renders = getattr(pending_renders, "pending_renders", []) if pending_renders else []

        return draft, usage, pending_renders

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
# ADR-118 D.3: Delivery helpers for workspace-based delivery path
# =============================================================================


def _log_export_standalone(client, version_id: str, user_id: str, destination: dict, result) -> None:
    """Log export to export_log table (standalone — not via DeliveryService)."""
    try:
        from integrations.core.types import ExportStatus
        client.table("export_log").insert({
            "agent_run_id": version_id,
            "user_id": user_id,
            "provider": destination.get("platform", "unknown"),
            "destination": destination,
            "status": result.status.value,
            "external_id": result.external_id,
            "external_url": result.external_url,
            "error_message": result.error_message,
            "completed_at": datetime.now(timezone.utc).isoformat() if result.status == ExportStatus.SUCCESS else None,
        }).execute()
    except Exception as e:
        logger.warning(f"[EXEC] Failed to log export: {e}")


async def _notify_delivery(client, user_id: str, agent: dict, destination: dict, result) -> None:
    """Send delivery success notification (ADR-040)."""
    try:
        from services.notifications import notify_agent_delivered
        platform = destination.get("platform", "unknown")
        target = destination.get("target")
        dest_str = platform
        if target:
            dest_str += f" ({target})"
        await notify_agent_delivered(
            db_client=client,
            user_id=user_id,
            agent_id=str(agent.get("id", "")),
            agent_title=agent.get("title", "Agent"),
            destination=dest_str,
            external_url=result.external_url,
            delivery_platform=platform,
        )
    except Exception as e:
        logger.warning(f"[EXEC] Delivery notification failed: {e}")


async def _notify_delivery_failed(client, user_id: str, agent: dict, error: str) -> None:
    """Send delivery failure notification (ADR-040)."""
    try:
        from services.notifications import notify_agent_failed
        await notify_agent_failed(
            db_client=client,
            user_id=user_id,
            agent_id=str(agent.get("id", "")),
            agent_title=agent.get("title", "Agent"),
            error=error,
        )
    except Exception as e:
        logger.warning(f"[EXEC] Failure notification failed: {e}")


# =============================================================================
# ADR-116 Phase 4: Agent Card Auto-Generation
# =============================================================================

def _extract_run_observation(
    draft: str,
    sources_used: list[str],
    items_fetched: int,
    role: str,
) -> str:
    """
    Extract a lightweight observation from a completed run — ADR-117 Phase 2.

    Rule-based, no LLM call. Captures:
    - Topics covered (from markdown headers)
    - Source coverage (which platforms contributed, data volume)
    - Role-specific signals
    """
    parts = []

    # Topic extraction from headers
    headers = re.findall(r"^#+\s+(.+)$", draft, re.MULTILINE)
    if headers:
        # Take up to 5 topic headers, skip generic ones
        topics = [h.strip() for h in headers if len(h.strip()) > 3][:5]
        if topics:
            parts.append(f"Topics: {', '.join(topics)}")

    # Source coverage
    if sources_used:
        parts.append(f"Sources: {', '.join(sources_used)} ({items_fetched} items)")
    else:
        parts.append("No platform sources used")

    # Data volume signal
    word_count = len(draft.split())
    if word_count < 100:
        parts.append("Thin output — limited source data")
    elif word_count > 2000:
        parts.append(f"Dense output ({word_count} words)")

    # Role-specific signals
    if role in ("digest", "briefer") and items_fetched < 5:
        parts.append("Low activity period — few items to brief on")
    elif role in ("synthesize", "analyst") and len(sources_used) < 2:
        parts.append("Cross-platform analysis with limited platform coverage")

    return "; ".join(parts) if parts else f"{role} run completed"


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
        "role": agent.get("role"),
        "scope": agent.get("scope"),
        "description": description,
        "thesis_summary": thesis[:300] if thesis else None,
        "sources": [],  # Column dropped
        "schedule": None,  # Column dropped
        "maturity": {
            "total_runs": run_count,
            "knowledge_files_produced": knowledge_files_count,
            "latest_version": version_number,
        },
        "last_run_at": None,  # Column dropped
        "interop": {
            "mcp_resource": f"workspace://agents/{slug}/",
            "input_format": "workspace_context",
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
    role = agent.get("role", "custom")
    scope = agent.get("scope", "cross_platform")
    title = agent.get("title", "Untitled")
    trigger_type = trigger_context.get("type", "manual") if trigger_context else "manual"

    # ADR-117 Phase 3: Resolve duty from trigger_context → effective_role
    # When running a non-seed duty (e.g., monitor on a digest agent), the duty's
    # role determines prompt selection and SKILL.md injection.
    duty_name = trigger_context.get("duty") if trigger_context else None
    effective_role = role  # default: seed role
    if duty_name and duty_name != role:
        # Duty role overrides for prompt + skill injection
        effective_role = duty_name

    logger.info(
        f"[EXEC] Starting: {title} ({agent_id}), "
        f"trigger={trigger_type}, scope={scope}, role={role}"
        + (f", duty={duty_name}" if duty_name else "")
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

        # ADR-117 Phase 3: Tag run with duty name for attribution
        if duty_name:
            try:
                client.table("agent_runs").update(
                    {"duty_name": duty_name}
                ).eq("id", version_id).execute()
            except Exception as e:
                logger.warning(f"[EXEC] duty_name tag failed (non-fatal): {e}")

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
        # ADR-117 Phase 3: effective_role overrides prompt + skill injection for non-seed duties
        research_directive = context_summary.get("research_directive")
        draft, usage, pending_renders = await generate_draft_inline(
            client, user_id, agent, gathered_context,
            trigger_context, research_directive,
            effective_role=effective_role,
        )

        # ADR-128/149: Extract and strip agent reflection before delivery
        agent_reflection = None
        draft, agent_reflection = _extract_agent_reflection(draft)
        if agent_reflection:
            logger.info(f"[EXEC] Agent reflection extracted (confidence: {agent_reflection.get('output_confidence', '?')})")

        # 4b. ADR-148 Phase 2: Render inline assets (tables→charts, mermaid→SVG)
        try:
            from services.render_assets import render_inline_assets
            draft, rendered_assets = await render_inline_assets(draft, user_id)
            if rendered_assets:
                logger.info(f"[EXEC] ADR-148: Rendered {len(rendered_assets)} inline assets")
        except Exception as e:
            logger.warning(f"[EXEC] ADR-148: Inline asset rendering failed (non-fatal): {e}")

        # 5. ADR-066: Prepare version for delivery (no staged status)
        # ADR-101: Store execution metadata (tokens, model) on version
        # ADR-049 evolution: Include context provenance for traceability
        version_metadata = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "model": SONNET_MODEL,
            "items_fetched": gathered_result.items_fetched,
            "sources_used": gathered_result.sources_used,
            "strategy": context_summary.get("strategy", "unknown"),
            # Persist trigger provenance so runs can be attributed to scheduler/manual/event paths.
            "trigger_type": trigger_type,
        }
        await update_version_for_delivery(client, version_id, draft, metadata=version_metadata)

        # ADR-049: Record source snapshots for audit trail
        # sources_used is a list of strings like "platform:slack", "other:document"
        # Build snapshot from the agent's source configs
        sources_for_snapshot = []  # Column dropped — sources no longer on agents table
        await record_source_snapshots(
            client, version_id, sources_for_snapshot,
        )

        # 6. last_run_at column dropped — no-op (was: update agent last_run_at)

        # 7. Resolve destination — agent destination → email fallback
        from services.supabase import get_service_client as _get_svc
        user_email = get_user_email(_get_svc(), user_id)
        destination = None  # Column dropped — destination no longer on agents table

        # Final fallback: email-first (ADR-066)
        destination = normalize_destination_for_delivery(destination, user_email)

        # 8. ADR-118 D.3: Save output folder BEFORE delivery (with rendered files from RuntimeDispatch)
        # Output folder is the single delivery source. Fatal if this fails.
        from services.workspace import AgentWorkspace, get_agent_slug
        from services.supabase import get_service_client as _get_svc3
        slug = get_agent_slug(agent)
        svc_client = _get_svc3()
        ws = AgentWorkspace(svc_client, user_id, slug)
        output_folder = None

        try:
            output_folder = await ws.save_output(
                content=draft,
                run_id=str(version_id),
                agent_id=str(agent_id),
                version_number=next_version,
                role=role,
                rendered_files=pending_renders if pending_renders else None,
            )
            if output_folder:
                logger.info(
                    f"[EXEC] ADR-118 D.3: Saved output folder at /agents/{slug}/{output_folder}/ "
                    f"({len(pending_renders)} rendered files)"
                )
            else:
                logger.error(f"[EXEC] ADR-118 D.3: save_output returned None — fatal")
        except Exception as e:
            logger.error(f"[EXEC] ADR-118 D.3: Output folder write FAILED (fatal): {e}")
            output_folder = None

        # 9. ADR-151: Signal routing to /workspace/context/signals/ (replaces legacy /knowledge/ writes)
        try:
            from services.workspace import UserMemory
            from datetime import datetime as _dt, timezone as _tz
            um = UserMemory(svc_client, user_id)
            date_str = _dt.now(_tz.utc).strftime("%Y-%m-%d")
            signal_path = f"context/signals/{date_str}.md"
            existing = await um.read(signal_path) or f"# Signals — {date_str}\n"
            signal_entry = (
                f"\n## {title} v{next_version} ({_dt.now(_tz.utc).strftime('%H:%M UTC')})\n"
                f"- Agent: {agent_slug}\n"
                f"- Role: {role}\n"
                f"- Output: {len(draft)} chars\n"
            )
            await um.write(signal_path, existing + signal_entry,
                          summary=f"Signal from {agent_slug} v{next_version}")
        except Exception as e:
            logger.warning(f"[EXEC] Context signal routing failed: {e}")

        # 9b. ADR-130 Phase 2: Compose HTML from output.md + assets (non-fatal)
        from services.agent_framework import has_capability
        if output_folder and has_capability(role, "compose_html"):
            try:
                composed_html = await _compose_output_html(
                    svc_client, user_id, slug, output_folder,
                    title=title, pending_renders=pending_renders,
                )
                if composed_html:
                    logger.info(f"[EXEC] ADR-130: Composed HTML ({len(composed_html)} chars) for {output_folder}")
            except Exception as e:
                logger.warning(f"[EXEC] ADR-130: Compose failed (non-fatal): {e}")

        # 10. ADR-118 D.3: Deliver from output folder (unified output substrate)
        final_status = "delivered"
        delivery_result = None
        delivery_error = None

        if destination and output_folder:
            logger.info(f"[EXEC] ADR-118 D.3: Delivering from output folder={output_folder}")
            try:
                from services.delivery import deliver_from_output_folder
                delivery_result = await deliver_from_output_folder(
                    client=svc_client,
                    user_id=user_id,
                    agent=agent,
                    output_folder=output_folder,
                    agent_slug=slug,
                    version_id=str(version_id),
                    version_number=next_version,
                    destination=destination,
                )
                if delivery_result.status.value == "success":
                    final_status = "delivered"
                    now = datetime.now(timezone.utc).isoformat()
                    client.table("agent_runs").update({
                        "status": "delivered",
                        "delivered_at": now,
                        "delivery_status": "delivered",
                    }).eq("id", version_id).execute()
                    # Log export + notify (parity with DeliveryService)
                    _log_export_standalone(svc_client, version_id, user_id, destination, delivery_result)
                    await _notify_delivery(svc_client, user_id, agent, destination, delivery_result)
                else:
                    final_status = "failed"
                    delivery_error = delivery_result.error_message
                    client.table("agent_runs").update({
                        "status": "failed",
                        "delivery_status": "failed",
                        "delivery_error": delivery_error,
                    }).eq("id", version_id).execute()
                    await _notify_delivery_failed(svc_client, user_id, agent, delivery_error or "Unknown error")
                logger.info(f"[EXEC] Delivery: {delivery_result.status.value}")
            except Exception as e:
                logger.error(f"[EXEC] Delivery failed: {e}")
                final_status = "failed"
                delivery_error = str(e)
                client.table("agent_runs").update({
                    "status": "failed",
                    "delivery_status": "failed",
                    "delivery_error": delivery_error,
                }).eq("id", version_id).execute()
                await _notify_delivery_failed(svc_client, user_id, agent, delivery_error)
        elif destination and not output_folder:
            # ADR-118 D.3 fallback: output folder failed, deliver from agent_runs (legacy path)
            logger.warning(f"[EXEC] ADR-118 D.3: Output folder unavailable, falling back to agent_runs delivery")
            try:
                from services.delivery import get_delivery_service
                delivery_service = get_delivery_service(client)
                delivery_result = await delivery_service.deliver_version(
                    version_id=version_id,
                    user_id=user_id,
                )
                if delivery_result.status.value == "success":
                    final_status = "delivered"
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
                logger.info(f"[EXEC] Fallback delivery: {delivery_result.status.value}")
            except Exception as e:
                logger.error(f"[EXEC] Fallback delivery failed: {e}")
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

        # ADR-117 Phase 2: Post-generation self-reflection for all skills
        if final_status == "delivered" and draft:
            try:
                observation = _extract_run_observation(
                    draft, gathered_result.sources_used,
                    gathered_result.items_fetched, role,
                )
                await ws.record_observation(observation, source="self")
                logger.info(f"[EXEC] ADR-117: Recorded self-observation for {title}")
            except Exception as e:
                logger.warning(f"[EXEC] ADR-117: Self-observation failed: {e}")
                # Non-fatal — don't block delivery

        # ADR-128/149: Append agent reflection to rolling history
        if final_status == "delivered" and agent_reflection:
            try:
                await _append_agent_reflection(ws, agent_reflection)
                logger.info(f"[EXEC] Agent reflection appended for {title}")
            except Exception as e:
                logger.warning(f"[EXEC] Agent reflection write failed: {e}")
                # Non-fatal

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
            _run_meta = {
                "agent_id": str(agent_id),
                "version_number": next_version,
                "role": role,  # ADR-109: For pattern detection
                "scope": scope,
                "strategy": strategy.strategy_name,
                "final_status": final_status,
                "delivery_error": delivery_error,
                "input_tokens": usage.get("input_tokens", 0),  # ADR-101
                "output_tokens": usage.get("output_tokens", 0),  # ADR-101
            }
            await write_activity(
                client=_get_svc2(),
                user_id=user_id,
                event_type="agent_run",
                summary=f"{title} v{next_version} {final_status}",
                event_ref=version_id,
                metadata=_run_meta,
            )
        except Exception:
            pass  # Non-fatal — never block execution

        # Record work credits for delivered agent runs
        if final_status == "delivered":
            try:
                from services.platform_limits import record_credits
                record_credits(svc_client, user_id, "task_execution", agent_id=str(agent_id))
            except Exception:
                pass  # Non-fatal

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
