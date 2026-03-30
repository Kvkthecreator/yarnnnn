"""
Task Pipeline — ADR-141 + ADR-145: Unified Execution Architecture

Mechanical generation pipeline triggered by scheduler. No decision-making — just execution.

Two execution paths:
  1. Single-step (existing): TASK.md has agent_slug, no type_key → direct generation
  2. Multi-step process (ADR-145): TASK.md has type_key → resolve process steps from registry
     → execute each step sequentially → pass output forward as explicit handoff

Single-step flow:
  Scheduler → Read TASK.md → Resolve agent → Gather context → Generate → Save → Deliver

Multi-step flow:
  Scheduler → Read TASK.md → Resolve type_key → Look up process steps
    → For each step: resolve agent by type → gather context + prior step output → generate
    → Final step output → compose HTML → deliver

Replaces: agent_pulse.py, trigger_dispatch.py, execution_strategies.py,
          agent_execution.py (execute_agent_generation).
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _total_input_tokens(usage: dict) -> int:
    """Sum all input token fields including prompt cache tokens."""
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )


# =============================================================================
# TASK.md Parsing
# =============================================================================

def parse_task_md(content: str) -> dict:
    """Parse TASK.md into structured dict.

    Expected format:
        # Title
        **Slug:** my-task
        **Agent:** research-agent
        **Schedule:** weekly
        **Delivery:** email@example.com

        ## Objective
        - **Deliverable:** ...
        - **Audience:** ...

        ## Success Criteria
        - criterion 1
        - criterion 2

        ## Output Spec
        - section 1
        - section 2
    """
    result = {
        "title": "",
        "agent_slug": "",
        "schedule": "",
        "delivery": "",
        "objective": {},
        "success_criteria": [],
        "output_spec": [],
    }

    lines = content.strip().splitlines()
    if not lines:
        return result

    # Title from first heading
    if lines[0].startswith("# "):
        result["title"] = lines[0][2:].strip()

    # Parse metadata fields
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("**Agent:**"):
            result["agent_slug"] = line_stripped.split("**Agent:**")[1].strip()
        elif line_stripped.startswith("**Slug:**"):
            result["slug"] = line_stripped.split("**Slug:**")[1].strip()
        elif line_stripped.startswith("**Type:**"):
            result["type_key"] = line_stripped.split("**Type:**")[1].strip()
        elif line_stripped.startswith("**Schedule:**"):
            result["schedule"] = line_stripped.split("**Schedule:**")[1].strip()
        elif line_stripped.startswith("**Delivery:**"):
            result["delivery"] = line_stripped.split("**Delivery:**")[1].strip()

    # Parse sections
    current_section = None
    for line in lines:
        line_stripped = line.strip()
        if line_stripped == "## Objective":
            current_section = "objective"
            continue
        elif line_stripped == "## Success Criteria":
            current_section = "criteria"
            continue
        elif line_stripped == "## Output Spec":
            current_section = "output_spec"
            continue
        elif line_stripped.startswith("## "):
            current_section = None
            continue

        if current_section == "objective" and line_stripped.startswith("- **"):
            match = re.match(r"- \*\*(\w+):\*\*\s*(.*)", line_stripped)
            if match:
                key = match.group(1).lower()
                result["objective"][key] = match.group(2).strip()
        elif current_section == "criteria" and line_stripped.startswith("- "):
            result["success_criteria"].append(line_stripped[2:])
        elif current_section == "output_spec" and line_stripped.startswith("- "):
            result["output_spec"].append(line_stripped[2:])

    return result


# =============================================================================
# Context Gathering (replaces execution_strategies.py)
# =============================================================================

async def gather_task_context(
    client,
    user_id: str,
    agent: dict,
    agent_slug: str,
    task_info: Optional[dict] = None,
) -> tuple[str, dict]:
    """Gather context for task execution.

    Reads from agent workspace (identity, memory, observations) and knowledge base.
    Knowledge base search is task-aware: uses task objective/title for relevance,
    not just agent title.

    Returns:
        (context_text, context_metadata)
    """
    from services.workspace import AgentWorkspace, KnowledgeBase, UserMemory

    ws = AgentWorkspace(client, user_id, agent_slug)
    await ws.ensure_seeded(agent)

    sections = []

    # 1. Agent workspace context (thesis, memory, observations)
    ws_context = await ws.load_context()
    if ws_context:
        sections.append(f"## Agent Context\n{ws_context}")

    # 2. Knowledge base — search using task context for relevance
    # Task-aware: objective/title drive search, not generic agent title
    role = agent.get("role", "custom")
    title = agent.get("title", "")

    # Build search query from task objective + title (task-aware context gathering)
    search_query = title  # fallback: agent title
    if task_info:
        task_title = task_info.get("title", "")
        objective = task_info.get("objective", {})
        objective_parts = [
            task_title,
            objective.get("deliverable", ""),
            objective.get("purpose", ""),
        ]
        query_parts = [p for p in objective_parts if p]
        if query_parts:
            search_query = " ".join(query_parts)[:200]  # cap length for embedding search

    kb = KnowledgeBase(client, user_id)
    try:
        kb_results = await kb.search(
            query=search_query,
            limit=10,
        )
        if kb_results:
            kb_text = "\n\n".join([
                f"### {getattr(r, 'path', 'unknown')}\n{getattr(r, 'content', '')[:2000]}"
                for r in kb_results
            ])
            sections.append(f"## Knowledge Base\n{kb_text}")
    except Exception as e:
        logger.warning(f"[TASK_EXEC] Knowledge search failed (non-fatal): {e}")

    # 3. User memories
    try:
        um = UserMemory(client, user_id)
        notes = await um.read("notes.md")
        if notes:
            sections.append(f"## User Notes\n{notes}")
    except Exception as e:
        logger.debug(f"[TASK_EXEC] User memory read failed: {e}")

    context_text = "\n\n".join(sections) if sections else "(No context available)"

    metadata = {
        "sections": len(sections),
        "platform_content_ids": [],  # platform content now accessed via knowledge base
        "scope": agent.get("scope", "cross_platform"),
    }

    return context_text, metadata


# =============================================================================
# Prompt Building
# =============================================================================

def build_task_execution_prompt(
    task_info: dict,
    agent: dict,
    agent_instructions: str,
    context: str,
    user_context: Optional[list] = None,
) -> tuple[str, str]:
    """Build system prompt and user message for task execution.

    ADR-143: Preferences/feedback now injected via gathered context (load_context()),
    not as a separate parameter.

    Returns:
        (system_prompt, user_message)
    """
    role = agent.get("role", "custom")
    title = task_info.get("title", "Untitled Task")

    # --- System prompt ---
    system = f"""You are an autonomous agent executing a scheduled task.

## Output Rules
- Follow the format and instructions below exactly.
- Be concise and professional — keep content tight and scannable.
- Do not invent information not present in the provided context or your research findings.
- Do not use emojis in headers or content unless preferences explicitly request them.
- Use plain markdown headers (##, ###) and bullet points for structure."""

    # User context (profile + preferences)
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
            system += "\n\n## User Context\n" + "\n".join(context_lines)

    # Agent instructions (from AGENT.md)
    if agent_instructions:
        system += f"\n\n## Agent Instructions\n{agent_instructions}"

    # Agent methodology — craft knowledge from type registry, injected at system level
    # so it shapes reasoning identity, not buried in gathered context.
    from services.agent_framework import get_type_playbook
    playbooks = get_type_playbook(role)
    if playbooks:
        system += "\n\n## Methodology"
        for filename, content in playbooks.items():
            system += f"\n\n{content}"

    # Tool usage guidance
    system += """

## Tool Usage (Headless Mode)
You have read-only investigation tools: Search, Read, List, WebSearch, GetSystemState.
- Use tools ONLY if the gathered context is clearly insufficient.
- Prefer generating from the provided context — most tasks have enough.
- NEVER narrate your tool usage in the final output.

## Visual Assets
Include visual elements inline — they are automatically rendered by the platform:
- **Data tables**: Use markdown tables with numeric data. Tables with numbers are automatically rendered as charts (bar, line, or pie depending on data shape).
- **Diagrams**: Use ```mermaid code blocks for competitive positioning, market maps, org charts, process flows. These are automatically rendered as SVG diagrams.
- Interleave visuals with prose — aim for a visual element every 2-3 paragraphs.
- Tables and mermaid blocks are kept in the output alongside their rendered versions.

## Empty Context Handling
If context says "(No context available)" or tools return no results:
- Still produce the output in the requested format.
- Note briefly that no recent activity was found.
- A short, properly formatted output is always better than meta-commentary."""

    # Assessment postamble (ADR-128 + success criteria eval)
    from services.agent_pipeline import _ASSESSMENT_POSTAMBLE, _CRITERIA_EVAL_SECTION
    criteria = task_info.get("success_criteria", [])
    if criteria:
        criteria_list = "\n".join(f"  - {c}" for c in criteria)
        criteria_eval = _CRITERIA_EVAL_SECTION.format(criteria_list=criteria_list)
    else:
        criteria_eval = ""
    system += _ASSESSMENT_POSTAMBLE.format(criteria_eval=criteria_eval)

    # --- User message ---
    user_parts = [f"# Task: {title}"]

    # Objective
    objective = task_info.get("objective", {})
    if objective:
        user_parts.append("\n## Objective")
        for key in ["deliverable", "audience", "purpose", "format"]:
            val = objective.get(key)
            if val:
                user_parts.append(f"- **{key.capitalize()}:** {val}")
        # Pipeline step instruction (ADR-145)
        step_instruction = objective.get("step_instruction")
        if step_instruction:
            user_parts.append(f"\n**Your specific role:** {step_instruction}")

    # Success criteria
    criteria = task_info.get("success_criteria", [])
    if criteria:
        user_parts.append("\n## Success Criteria")
        for c in criteria:
            user_parts.append(f"- {c}")

    # Output spec
    output_spec = task_info.get("output_spec", [])
    if output_spec:
        user_parts.append("\n## Output Format")
        for s in output_spec:
            user_parts.append(f"- {s}")

    # Gathered context
    user_parts.append(f"\n## Gathered Context\n{context}")

    user_message = "\n".join(user_parts)

    return system, user_message


# =============================================================================
# Cadence Calculation
# =============================================================================

def calculate_next_run_at(schedule, last_run_at: Optional[datetime] = None) -> Optional[datetime]:
    """Calculate next_run_at from schedule string or dict. Pure math, no LLM.

    ADR-138: schedule is stored as a simple string ('daily', 'weekly', 'monthly')
    or cron expression in the tasks table.
    """
    now = last_run_at or datetime.now(timezone.utc)

    # Handle string schedules (ADR-138 tasks table format)
    if isinstance(schedule, str):
        s = schedule.lower().strip()
        if s == "daily":
            return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        elif s == "weekly":
            days_ahead = 7 - now.weekday()
            if days_ahead == 0:
                days_ahead = 7
            return (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
        elif s == "monthly":
            if now.month == 12:
                return now.replace(year=now.year + 1, month=1, day=1, hour=9, minute=0, second=0, microsecond=0)
            return now.replace(month=now.month + 1, day=1, hour=9, minute=0, second=0, microsecond=0)
        else:
            # Unknown or cron — default to 24h
            return now + timedelta(hours=24)

    # Legacy dict format (from old agent scheduling)
    if isinstance(schedule, dict):
        try:
            from jobs.unified_scheduler import calculate_next_pulse_from_schedule
            return calculate_next_pulse_from_schedule(schedule, from_time=last_run_at)
        except Exception:
            return now + timedelta(hours=24)

    return None


# =============================================================================
# Main Pipeline
# =============================================================================

async def execute_task(
    client,
    user_id: str,
    task_slug: str,
) -> dict:
    """Execute a single task — the complete pipeline from TASK.md to delivery.

    ADR-141: Mechanical pipeline. No decision-making. Called by scheduler
    when task is due (next_run_at <= now).

    Args:
        client: Supabase service client
        user_id: User UUID
        task_slug: Task slug (matches /tasks/{slug}/TASK.md)

    Returns:
        Result dict with task_slug, status, message
    """
    from services.task_workspace import TaskWorkspace
    from services.workspace import AgentWorkspace, KnowledgeBase, UserMemory, get_agent_slug
    from services.agent_framework import has_asset_capabilities, has_capability

    started_at = datetime.now(timezone.utc)
    logger.info(f"[TASK_EXEC] Starting: {task_slug} for user {user_id[:8]}...")

    # =====================================================================
    # 0. Optimistic next_run_at bump — prevents scheduler re-pickup
    # The scheduler queries next_run_at <= now every 5 min. If execution
    # takes longer than 5 min, the task gets picked up again. Bump to
    # +2 hours as a sentinel; the real value is set at step 15.
    # =====================================================================
    try:
        sentinel = (started_at + timedelta(hours=2)).isoformat()
        client.table("tasks").update({
            "next_run_at": sentinel,
        }).eq("user_id", user_id).eq("slug", task_slug).execute()
    except Exception as e:
        logger.warning(f"[TASK_EXEC] Optimistic next_run_at bump failed: {e}")

    try:
        # =====================================================================
        # 1. Read TASK.md
        # =====================================================================
        tw = TaskWorkspace(client, user_id, task_slug)
        task_md_content = await tw.read_task()
        if not task_md_content:
            return _fail(task_slug, "TASK.md not found")

        task_info = parse_task_md(task_md_content)

        # =====================================================================
        # 1a. Check for multi-step process (ADR-145)
        # =====================================================================
        type_key = task_info.get("type_key", "").strip()
        if type_key:
            from services.task_types import get_task_type
            task_type_def = get_task_type(type_key)
            if task_type_def and len(task_type_def.get("process", [])) > 1:
                # Multi-step process — delegate to process executor
                result = await _execute_pipeline(
                    client, user_id, task_slug, tw, task_info, task_type_def, started_at,
                )
                return result

        # Single-step execution (existing flow)
        agent_slug = task_info.get("agent_slug", "").strip()

        # For single-step typed tasks, resolve agent from process definition
        if not agent_slug and type_key:
            from services.task_types import get_task_type
            _type_def = get_task_type(type_key)
            if _type_def and _type_def.get("process"):
                agent_type = _type_def["process"][0]["agent_type"]
                roster = client.table("agents").select("slug, role").eq("user_id", user_id).execute()
                for a in (roster.data or []):
                    if a.get("role") == agent_type:
                        agent_slug = a["slug"]
                        logger.info(f"[TASK_EXEC] Resolved agent {agent_slug} from type {type_key} process")
                        break

        if not agent_slug:
            return _fail(task_slug, "No agent assigned in TASK.md")

        # =====================================================================
        # 2. Resolve agent from DB
        # =====================================================================
        agent_result = (
            client.table("agents")
            .select("*")
            .eq("user_id", user_id)
            .eq("slug", agent_slug)
            .limit(1)
            .execute()
        )
        if not agent_result.data:
            return _fail(task_slug, f"Agent '{agent_slug}' not found")
        agent = agent_result.data[0]
        agent_id = agent["id"]
        role = agent.get("role", "custom")
        scope = agent.get("scope", "cross_platform")
        title = task_info.get("title") or agent.get("title", "Untitled")

        logger.info(f"[TASK_EXEC] Agent: {agent_slug} (role={role}, scope={scope})")

        # =====================================================================
        # 3. Check work credits
        # =====================================================================
        try:
            from services.platform_limits import check_credits
            credits_ok, credits_used, credits_limit = check_credits(client, user_id)
            if not credits_ok:
                logger.info(f"[TASK_EXEC] Work credits exhausted for user {user_id[:8]} ({credits_used}/{credits_limit})")
                return _fail(task_slug, "Work credits exhausted")
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Credits check failed (proceeding): {e}")

        # =====================================================================
        # 4. Create agent_runs record
        # =====================================================================
        from services.agent_execution import get_next_run_number, create_version_record
        next_version = await get_next_run_number(client, agent_id)
        version = await create_version_record(client, agent_id, next_version)
        version_id = version["id"]

        # =====================================================================
        # 5. Read agent workspace (AGENT.md, memory, preferences)
        # =====================================================================
        ws = AgentWorkspace(client, user_id, agent_slug)
        await ws.ensure_seeded(agent)

        ws_instructions = await ws.read("AGENT.md") or ""

        # ADR-143: feedback + methodology loaded via ws.load_context() in context gathering
        # User context (profile + preferences)
        user_context = _load_user_context(client, user_id)

        # =====================================================================
        # 6. Gather context
        # =====================================================================
        context_text, context_meta = await gather_task_context(
            client, user_id, agent, agent_slug, task_info=task_info,
        )

        # =====================================================================
        # 7. Build prompt and generate
        # =====================================================================
        system_prompt, user_message = build_task_execution_prompt(
            task_info=task_info,
            agent=agent,
            agent_instructions=ws_instructions,
            context=context_text,
            user_context=user_context,
        )

        # ADR-148: No SKILL.md injection, no RuntimeDispatch during headless generation.
        # Agent writes prose with inline data tables + mermaid blocks.
        # Post-generation render phase (render_inline_assets) handles chart/diagram rendering.

        # Generate via headless agent (multi-tool-round)
        draft, usage, pending_renders = await _generate(
            client, user_id, agent, system_prompt, user_message, scope,
        )

        # Strip contributor assessment before delivery (ADR-128)
        from services.agent_execution import _extract_contributor_assessment
        draft, contributor_assessment = _extract_contributor_assessment(draft)

        # =====================================================================
        # 7b. Render inline assets — ADR-148 Phase 2 (tables→charts, mermaid→SVG)
        # =====================================================================
        rendered_assets = []
        try:
            from services.render_assets import render_inline_assets
            draft, rendered_assets = await render_inline_assets(draft, user_id)
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Inline asset rendering failed (non-fatal): {e}")

        # =====================================================================
        # 8. Update agent_runs record with content
        # =====================================================================
        from services.agent_execution import update_version_for_delivery, SONNET_MODEL
        version_metadata = {
            "input_tokens": _total_input_tokens(usage),
            "output_tokens": usage.get("output_tokens", 0),
            "model": SONNET_MODEL,
            "task_slug": task_slug,
            "platform_content_ids": context_meta.get("platform_content_ids", []),
            "trigger_type": "scheduled",
        }
        await update_version_for_delivery(client, version_id, draft, metadata=version_metadata)

        # =====================================================================
        # 9. Mark consumed platform content as retained
        # =====================================================================
        pc_ids = context_meta.get("platform_content_ids", [])
        if pc_ids:
            try:
                from services.platform_content import mark_content_retained
                await mark_content_retained(client, pc_ids, reason="task_execution", ref=version_id)
            except Exception as e:
                logger.warning(f"[TASK_EXEC] Content retention failed: {e}")

        # =====================================================================
        # 10. Save output to task workspace
        # =====================================================================
        task_output_folder = await tw.save_output(
            content=draft,
            agent_slug=agent_slug,
            manifest_data={
                "version_id": str(version_id),
                "version_number": next_version,
                "tokens": usage,
            },
        )

        # Also save to agent workspace (for agent's output history)
        agent_output_folder = None
        try:
            agent_output_folder = await ws.save_output(
                content=draft,
                run_id=str(version_id),
                agent_id=str(agent_id),
                version_number=next_version,
                role=role,
                rendered_files=pending_renders if pending_renders else None,
            )
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Agent output folder write failed: {e}")

        # =====================================================================
        # 11. Write to knowledge base (accumulation)
        # =====================================================================
        try:
            kb = KnowledgeBase(client, user_id)
            knowledge_path = KnowledgeBase.get_knowledge_path(role, title)
            await kb.write(
                path=knowledge_path,
                content=draft,
                summary=f"{title} v{next_version}",
                metadata={
                    "agent_id": str(agent_id),
                    "task_slug": task_slug,
                    "run_id": str(version_id),
                    "role": role,
                    "version_number": next_version,
                },
                tags=[role],
            )
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Knowledge write failed: {e}")

        # =====================================================================
        # 12. Compose HTML (always — ADR-148 singular rendering path)
        # =====================================================================
        if agent_output_folder:
            try:
                from services.agent_execution import _compose_output_html
                _layout = "document"
                _type_key = task_info.get("type_key", "").strip()
                if _type_key:
                    from services.task_types import get_task_type
                    _tdef = get_task_type(_type_key)
                    if _tdef:
                        _layout = _tdef.get("layout_mode", "document")
                await _compose_output_html(
                    client, user_id, agent_slug, agent_output_folder,
                    title=title, pending_renders=pending_renders,
                    layout_mode=_layout,
                )
                agent_html = await ws.read(f"outputs/{agent_output_folder}/output.html")
                if agent_html and task_output_folder:
                    await tw.write(
                        f"outputs/{task_output_folder}/output.html",
                        agent_html,
                        summary=f"Composed HTML for {title}",
                        tags=["output", "html"],
                    )
            except Exception as e:
                logger.warning(f"[TASK_EXEC] Compose HTML failed (non-fatal): {e}")

        # =====================================================================
        # 13. Deliver
        # =====================================================================
        final_status = "delivered"
        delivery_error = None

        delivery_target = task_info.get("delivery", "").strip()
        if delivery_target and agent_output_folder:
            try:
                from services.agent_execution import (
                    get_user_email,
                    normalize_destination_for_delivery,
                )
                from services.delivery import deliver_from_output_folder
                from services.supabase import get_service_client

                # Build destination from TASK.md delivery field
                destination = _parse_delivery_target(delivery_target, client, user_id)

                if destination:
                    delivery_result = await deliver_from_output_folder(
                        client=client,
                        user_id=user_id,
                        agent=agent,
                        output_folder=agent_output_folder,
                        agent_slug=agent_slug,
                        version_id=str(version_id),
                        version_number=next_version,
                        destination=destination,
                        task_slug=task_slug,
                    )
                    if delivery_result.status.value == "success":
                        now = datetime.now(timezone.utc).isoformat()
                        client.table("agent_runs").update({
                            "status": "delivered",
                            "delivered_at": now,
                            "delivery_status": "delivered",
                        }).eq("id", version_id).execute()
                    else:
                        final_status = "failed"
                        delivery_error = delivery_result.error_message
                        client.table("agent_runs").update({
                            "status": "failed",
                            "delivery_status": "failed",
                            "delivery_error": delivery_error,
                        }).eq("id", version_id).execute()
            except Exception as e:
                logger.error(f"[TASK_EXEC] Delivery failed: {e}")
                final_status = "failed"
                delivery_error = str(e)
                client.table("agent_runs").update({
                    "status": "failed",
                    "delivery_status": "failed",
                    "delivery_error": delivery_error,
                }).eq("id", version_id).execute()
        else:
            # No delivery configured — mark as delivered (content generated)
            now = datetime.now(timezone.utc).isoformat()
            client.table("agent_runs").update({
                "status": "delivered",
                "delivered_at": now,
            }).eq("id", version_id).execute()

        # =====================================================================
        # 14. Post-generation side effects (all non-fatal)
        # =====================================================================

        # Append to task run log (with self-assessment if available)
        try:
            log_entry = f"v{next_version} {final_status}"
            if delivery_error:
                log_entry += f" — {delivery_error}"
            if contributor_assessment:
                confidence = contributor_assessment.get("output_confidence", "unknown")
                # Extract level from "high — reason" format
                level = confidence.split("—")[0].split("–")[0].strip().lower() if confidence else "unknown"
                log_entry += f" | confidence={level}"
                # Include criteria eval if present
                criteria_met = contributor_assessment.get("criteria_met")
                if criteria_met:
                    log_entry += f" | criteria: {criteria_met}"
            await tw.append_run_log(log_entry)
        except Exception:
            pass

        # Self-observation (ADR-117)
        if final_status == "delivered" and draft:
            try:
                from services.agent_execution import _extract_run_observation
                observation = _extract_run_observation(
                    draft, [], context_meta.get("sections", 0), role,
                )
                await ws.record_observation(observation, source="self")
            except Exception:
                pass

        # Self-assessment (ADR-128)
        if final_status == "delivered" and contributor_assessment:
            try:
                from services.agent_execution import _append_self_assessment
                await _append_self_assessment(ws, contributor_assessment)
            except Exception:
                pass

        # Agent card (ADR-116)
        if final_status == "delivered":
            try:
                from services.agent_execution import _generate_agent_card
                await _generate_agent_card(client, user_id, agent, next_version)
            except Exception:
                pass

        # =====================================================================
        # 15. Update scheduling
        # =====================================================================
        now = datetime.now(timezone.utc)
        try:
            # Read schedule from tasks table
            task_row = (
                client.table("tasks")
                .select("schedule")
                .eq("user_id", user_id)
                .eq("slug", task_slug)
                .limit(1)
                .execute()
            )
            schedule = (task_row.data[0]["schedule"] if task_row.data else None) or {}

            next_run = calculate_next_run_at(schedule, last_run_at=now) if schedule else None

            update_data = {"last_run_at": now.isoformat()}
            if next_run:
                update_data["next_run_at"] = next_run.isoformat()

            client.table("tasks").update(update_data).eq(
                "user_id", user_id
            ).eq("slug", task_slug).execute()
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Schedule update failed: {e}")

        # =====================================================================
        # 16. Activity log + work units
        # =====================================================================
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        try:
            from services.activity_log import write_activity
            await write_activity(
                client=client,
                user_id=user_id,
                event_type="task_executed",
                summary=f"{title} v{next_version} {final_status}",
                event_ref=version_id,
                metadata={
                    "task_slug": task_slug,
                    "agent_slug": agent_slug,
                    "agent_id": str(agent_id),
                    "version_number": next_version,
                    "role": role,
                    "scope": scope,
                    "final_status": final_status,
                    "delivery_error": delivery_error,
                    "duration_ms": duration_ms,
                    "input_tokens": _total_input_tokens(usage),
                    "output_tokens": usage.get("output_tokens", 0),
                },
            )
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Activity log write failed: {e}")

        if final_status == "delivered":
            try:
                from services.platform_limits import record_credits
                record_credits(client, user_id, "task_execution", agent_id=str(agent_id), metadata={"task_slug": task_slug})
            except Exception:
                pass

        logger.info(
            f"[TASK_EXEC] Complete: {task_slug} → {agent_slug} v{next_version} "
            f"{final_status} ({duration_ms}ms)"
        )

        return {
            "success": final_status == "delivered",
            "task_slug": task_slug,
            "agent_slug": agent_slug,
            "run_id": version_id,
            "version_number": next_version,
            "status": final_status,
            "duration_ms": duration_ms,
            "message": f"v{next_version} {final_status}" + (f": {delivery_error}" if delivery_error else ""),
        }

    except Exception as e:
        logger.error(f"[TASK_EXEC] Failed: {task_slug}: {e}")
        return _fail(task_slug, str(e))


# =============================================================================
# Multi-Step Process Execution (ADR-145 Gate 2)
# =============================================================================

async def _execute_pipeline(
    client,
    user_id: str,
    task_slug: str,
    tw,  # TaskWorkspace
    task_info: dict,
    task_type_def: dict,
    started_at,
) -> dict:
    """Execute a multi-step process — sequential agent execution with handoffs.

    Each process step:
    1. Resolve agent by type from user's roster
    2. Gather step-specific context (agent workspace + prior step output)
    3. Generate with step instruction merged into task objective
    4. Save step output to /tasks/{slug}/outputs/{date}/step-{N}/

    Final step's output becomes the task deliverable.
    """
    from services.task_workspace import TaskWorkspace
    from services.workspace import AgentWorkspace, KnowledgeBase
    from services.agent_framework import has_asset_capabilities, has_capability
    from services.agent_execution import (
        get_next_run_number, create_version_record,
        update_version_for_delivery, SONNET_MODEL,
        _extract_contributor_assessment, _compose_output_html,
    )
    from services.platform_limits import check_credits, record_credits

    steps = task_type_def["process"]
    title = task_info.get("title") or task_slug
    delivery_target = task_info.get("delivery", "").strip()

    logger.info(f"[PIPELINE] Starting {len(steps)}-step process for {task_slug} (type={task_info.get('type_key')})")

    # Write initial run status for frontend progress polling
    run_status = {
        "status": "running",
        "current_step": 0,
        "total_steps": len(steps),
        "completed_steps": [],
        "started_at": started_at.isoformat(),
    }
    try:
        await tw.write(
            f"outputs/{started_at.strftime('%Y-%m-%dT%H%M')}/status.json",
            json.dumps(run_status, indent=2),
            tags=["status"],
            lifecycle="ephemeral",
        )
    except Exception:
        pass  # Non-critical — progress is best-effort

    # Resolve all process agents upfront
    agents_result = (
        client.table("agents")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    all_agents = agents_result.data or []
    role_to_agent = {}
    for a in all_agents:
        r = a.get("role")
        if r and r not in role_to_agent:
            role_to_agent[r] = a

    # Check credits before starting
    try:
        credits_ok, credits_used, credits_limit = check_credits(client, user_id)
        if not credits_ok:
            return _fail(task_slug, "Work credits exhausted")
    except Exception as e:
        logger.warning(f"[PIPELINE] Credits check failed (proceeding): {e}")

    # Date folder for this run
    date_folder = started_at.strftime("%Y-%m-%dT%H%M")

    step_outputs: list[str] = []
    final_draft = ""
    final_agent = None
    final_agent_slug = ""
    final_role = ""
    total_usage = {"input_tokens": 0, "output_tokens": 0}
    all_renders: list = []

    for step_idx, step in enumerate(steps):
        step_num = step_idx + 1
        agent_type = step["agent_type"]
        step_name = step["step"]
        step_instruction = step["instruction"]

        agent = role_to_agent.get(agent_type)
        if not agent:
            logger.warning(f"[PIPELINE] Step {step_num} ({step_name}): no agent of type '{agent_type}' — skipping")
            step_outputs.append(f"(Step {step_num} skipped: no {agent_type} agent in roster)")
            continue

        agent_slug = agent.get("slug", "")
        agent_id = agent["id"]
        role = agent.get("role", "custom")
        scope = agent.get("scope", "cross_platform")

        logger.info(f"[PIPELINE] Step {step_num}/{len(steps)}: {step_name} → {agent_slug} ({agent_type})")

        # --- Gather context for this step ---
        ws = AgentWorkspace(client, user_id, agent_slug)
        await ws.ensure_seeded(agent)
        ws_instructions = await ws.read("AGENT.md") or ""
        user_context = _load_user_context(client, user_id)

        context_text, context_meta = await gather_task_context(
            client, user_id, agent, agent_slug, task_info=task_info,
        )

        # --- Build step-specific prompt ---
        # Merge step instruction into the task objective
        step_task_info = {**task_info}
        step_objective = dict(task_info.get("objective", {}))
        step_objective["step_instruction"] = step_instruction
        step_task_info["objective"] = step_objective

        system_prompt, user_message = build_task_execution_prompt(
            task_info=step_task_info,
            agent=agent,
            agent_instructions=ws_instructions,
            context=context_text,
            user_context=user_context,
        )

        # Inject step-specific preamble — BEFORE gathered context for visibility
        step_preamble = f"\n\n## Process Step {step_num}/{len(steps)}: {step_name.title()}\n"
        step_preamble += f"Your role in this process: {step_instruction}\n"
        if step_outputs:
            prior_output = step_outputs[-1]
            step_preamble += (
                f"\n## Prior Step Output (YOUR PRIMARY INPUT)\n"
                f"The following is the output from the previous step. "
                f"This is your primary source material — your job is to TRANSFORM this research "
                f"into the deliverable described above. Every finding, data point, and citation "
                f"from this input should appear in your output (restructured, not copy-pasted). "
                f"Do NOT conduct independent research that ignores this input. "
                f"Do NOT produce a shorter output than this input — you are adding structure, "
                f"formatting, and visual assets, not condensing.\n\n"
                f"{prior_output[:8000]}\n"
            )
        elif step_num == 1:
            step_preamble += (
                "\nYou are the first step in a multi-step process. "
                "Your output will be the primary input for the next agent. "
                "Be thorough — include all findings, data points, and sources. "
                "The next agent cannot research further, only format what you provide.\n"
            )

        # Append to user message (after gathered context)
        user_message += step_preamble

        # ADR-148: No SKILL.md / RuntimeDispatch in headless. Agent writes inline data + mermaid.

        # --- Generate ---
        draft, usage, pending_renders = await _generate(
            client, user_id, agent, system_prompt, user_message, scope,
        )

        # Strip assessment
        draft, _ = _extract_contributor_assessment(draft)

        total_usage["input_tokens"] += _total_input_tokens(usage)
        total_usage["output_tokens"] += usage.get("output_tokens", 0)
        all_renders.extend(pending_renders or [])

        step_outputs.append(draft)
        final_draft = draft
        final_agent = agent
        final_agent_slug = agent_slug
        final_role = role

        # Save step output
        try:
            step_path = f"outputs/{date_folder}/step-{step_num}/output.md"
            await tw.write(step_path, draft, summary=f"Step {step_num}: {step_name}", tags=["pipeline", "step"])
            step_manifest = {
                "step": step_num,
                "step_name": step_name,
                "agent_type": agent_type,
                "agent_slug": agent_slug,
                "tokens": usage,
            }
            await tw.write(
                f"outputs/{date_folder}/step-{step_num}/manifest.json",
                json.dumps(step_manifest, indent=2),
                tags=["pipeline", "manifest"],
            )
        except Exception as e:
            logger.warning(f"[PIPELINE] Step output save failed: {e}")

        # Record credit per step
        try:
            record_credits(client, user_id, "task_execution", agent_id=str(agent_id), metadata={
                "task_slug": task_slug, "step": step_num, "step_name": step_name,
            })
        except Exception:
            pass

        # Update run status for frontend progress polling
        run_status["current_step"] = step_num
        run_status["completed_steps"].append({
            "step": step_num,
            "step_name": step_name,
            "agent_type": agent_type,
            "agent_slug": agent_slug,
        })
        try:
            await tw.write(
                f"outputs/{date_folder}/status.json",
                json.dumps(run_status, indent=2),
                tags=["status"],
                lifecycle="ephemeral",
            )
        except Exception:
            pass

        logger.info(f"[PIPELINE] Step {step_num} complete ({usage.get('output_tokens', 0)} tokens)")

    # =====================================================================
    # Post-process: Save final output, compose, deliver
    # =====================================================================
    if not final_draft or not final_agent:
        return _fail(task_slug, "Process produced no output")

    # Render inline assets — ADR-148 Phase 2 (tables→charts, mermaid→SVG)
    rendered_assets = []
    try:
        from services.render_assets import render_inline_assets
        final_draft, rendered_assets = await render_inline_assets(final_draft, user_id)
    except Exception as e:
        logger.warning(f"[PIPELINE] Inline asset rendering failed (non-fatal): {e}")

    # Create agent_runs record for the final output
    agent_id = final_agent["id"]
    next_version = await get_next_run_number(client, agent_id)
    version = await create_version_record(client, agent_id, next_version)
    version_id = version["id"]

    version_metadata = {
        "input_tokens": total_usage["input_tokens"],
        "output_tokens": total_usage["output_tokens"],
        "model": SONNET_MODEL,
        "task_slug": task_slug,
        "type_key": task_info.get("type_key"),
        "process_steps": len(steps),
        "trigger_type": "scheduled",
    }
    await update_version_for_delivery(client, version_id, final_draft, metadata=version_metadata)

    # Mark run status as completed for frontend progress polling
    run_status["status"] = "completed"
    run_status["completed_at"] = datetime.now(timezone.utc).isoformat()
    try:
        await tw.write(
            f"outputs/{date_folder}/status.json",
            json.dumps(run_status, indent=2),
            tags=["status"],
            lifecycle="ephemeral",
        )
    except Exception:
        pass

    # Save final output to task workspace (same date_folder as step outputs)
    task_output_folder = await tw.save_output(
        content=final_draft,
        agent_slug=final_agent_slug,
        date_folder=date_folder,
        manifest_data={
            "version_id": str(version_id),
            "version_number": next_version,
            "type_key": task_info.get("type_key"),
            "process_steps": len(steps),
            "tokens": total_usage,
        },
    )

    # Save to agent workspace
    ws = AgentWorkspace(client, user_id, final_agent_slug)
    agent_output_folder = None
    try:
        agent_output_folder = await ws.save_output(
            content=final_draft,
            run_id=str(version_id),
            agent_id=str(agent_id),
            version_number=next_version,
            role=final_role,
            rendered_files=all_renders if all_renders else None,
        )
    except Exception as e:
        logger.warning(f"[PIPELINE] Agent output folder write failed: {e}")

    # Knowledge base accumulation
    try:
        kb = KnowledgeBase(client, user_id)
        knowledge_path = KnowledgeBase.get_knowledge_path(final_role, title)
        await kb.write(
            path=knowledge_path,
            content=final_draft,
            summary=f"{title} v{next_version}",
            metadata={"task_slug": task_slug, "type_key": task_info.get("type_key")},
            tags=[final_role],
        )
    except Exception:
        pass

    # Compose HTML (always — ADR-148 singular rendering path)
    if agent_output_folder:
        try:
            await _compose_output_html(
                client, user_id, final_agent_slug, agent_output_folder,
                title=title, pending_renders=all_renders,
                layout_mode=task_type_def.get("layout_mode", "document"),
            )
            # Sync composed HTML from agent workspace to task workspace
            agent_ws = AgentWorkspace(client, user_id, final_agent_slug)
            agent_html = await agent_ws.read(f"outputs/{agent_output_folder}/output.html")
            if agent_html:
                await tw.write(
                    f"outputs/{date_folder}/output.html",
                    agent_html,
                    summary=f"Composed HTML for {title}",
                    tags=["output", "html"],
                )
        except Exception as e:
            logger.warning(f"[PIPELINE] Compose HTML failed: {e}")

    # Deliver
    final_status = "delivered"
    delivery_error = None

    if delivery_target and agent_output_folder:
        try:
            from services.delivery import deliver_from_output_folder
            destination = _parse_delivery_target(delivery_target, client, user_id)
            if destination:
                delivery_result = await deliver_from_output_folder(
                    client=client, user_id=user_id, agent=final_agent,
                    output_folder=agent_output_folder, agent_slug=final_agent_slug,
                    version_id=str(version_id), version_number=next_version,
                    destination=destination, task_slug=task_slug,
                )
                if delivery_result.status.value == "success":
                    now = datetime.now(timezone.utc).isoformat()
                    client.table("agent_runs").update({
                        "status": "delivered", "delivered_at": now, "delivery_status": "delivered",
                    }).eq("id", version_id).execute()
                else:
                    final_status = "failed"
                    delivery_error = delivery_result.error_message
        except Exception as e:
            final_status = "failed"
            delivery_error = str(e)
    else:
        now = datetime.now(timezone.utc).isoformat()
        client.table("agent_runs").update({
            "status": "delivered", "delivered_at": now,
        }).eq("id", version_id).execute()

    if final_status == "failed":
        client.table("agent_runs").update({
            "status": "failed", "delivery_status": "failed", "delivery_error": delivery_error,
        }).eq("id", version_id).execute()

    # Run log
    try:
        process_summary = " → ".join(s["step"] for s in steps)
        log_entry = f"v{next_version} {final_status} ({process_summary})"
        if delivery_error:
            log_entry += f" — {delivery_error}"
        await tw.append_run_log(log_entry)
    except Exception:
        pass

    # Update scheduling
    now = datetime.now(timezone.utc)
    try:
        task_row = (
            client.table("tasks").select("schedule")
            .eq("user_id", user_id).eq("slug", task_slug).limit(1).execute()
        )
        schedule = (task_row.data[0]["schedule"] if task_row.data else None) or {}
        next_run = calculate_next_run_at(schedule, last_run_at=now) if schedule else None
        update_data = {"last_run_at": now.isoformat()}
        if next_run:
            update_data["next_run_at"] = next_run.isoformat()
        client.table("tasks").update(update_data).eq("user_id", user_id).eq("slug", task_slug).execute()
    except Exception as e:
        logger.warning(f"[PIPELINE] Schedule update failed: {e}")

    # Activity log
    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=client, user_id=user_id,
            event_type="task_executed",
            summary=f"{title} v{next_version} {final_status} ({len(steps)} steps)",
            event_ref=version_id,
            metadata={
                "task_slug": task_slug,
                "type_key": task_info.get("type_key"),
                "process_steps": len(steps),
                "agent_slugs": [s.get("agent_type") for s in steps],
                "step_details": [
                    {"step": i + 1, "step_name": s.get("step", f"step-{i+1}"), "agent_type": s.get("agent_type")}
                    for i, s in enumerate(steps)
                ],
                "final_status": final_status,
                "duration_ms": duration_ms,
                "input_tokens": total_usage["input_tokens"],
                "output_tokens": total_usage["output_tokens"],
            },
        )
    except Exception as e:
        logger.warning(f"[PIPELINE] Activity log write failed: {e}")

    logger.info(
        f"[PIPELINE] Complete: {task_slug} → {len(steps)} steps, v{next_version} "
        f"{final_status} ({duration_ms}ms, {total_usage['input_tokens']+total_usage['output_tokens']} tokens)"
    )

    return {
        "success": final_status == "delivered",
        "task_slug": task_slug,
        "type_key": task_info.get("type_key"),
        "process_steps": len(steps),
        "agent_slug": final_agent_slug,
        "run_id": version_id,
        "version_number": next_version,
        "status": final_status,
        "duration_ms": duration_ms,
        "message": f"v{next_version} {final_status} ({len(steps)} steps)",
    }


# =============================================================================
# Generation (reuses headless agent loop from agent_execution)
# =============================================================================

# Scope → max tool rounds
_TOOL_ROUNDS = {
    "platform": 3,
    "cross_platform": 5,
    "knowledge": 5,
    "research": 6,
    "autonomous": 8,
}


async def _generate(
    client,
    user_id: str,
    agent: dict,
    system_prompt: str,
    user_message: str,
    scope: str,
) -> tuple[str, dict, list]:
    """Run the headless generation loop. Returns (draft, usage, pending_renders)."""
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import get_tools_for_mode, create_headless_executor
    from services.agent_pipeline import validate_output
    from services.agent_execution import (
        SONNET_MODEL, _is_narration, _strip_tool_narration,
    )

    role = agent.get("role", "custom")
    max_tool_rounds = _TOOL_ROUNDS.get(scope, 5)

    # Agents with asset capabilities (chart, mermaid, image) need more rounds
    # for both research tool calls AND asset generation
    from services.agent_framework import has_asset_capabilities
    if has_asset_capabilities(role):
        max_tool_rounds = max(max_tool_rounds, 6)

    headless_tools = get_tools_for_mode("headless")
    executor = create_headless_executor(
        client, user_id,
        agent_sources=[],
        agent=agent,
    )

    messages = [{"role": "user", "content": user_message}]
    tools_used = []
    total_input_tokens = 0
    total_output_tokens = 0
    draft = ""

    for round_num in range(max_tool_rounds + 1):
        response = await chat_completion_with_tools(
            messages=messages,
            system=system_prompt,
            tools=headless_tools,
            model=SONNET_MODEL,
            max_tokens=4000,
        )

        if response.usage:
            total_input_tokens += _total_input_tokens(response.usage)
            total_output_tokens += response.usage.get("output_tokens", 0)

        # Agent finished
        if response.stop_reason in ("end_turn", "max_tokens") or not response.tool_uses:
            draft = response.text.strip()
            if round_num > 0:
                logger.info(f"[TASK_EXEC] Agent used {round_num} tool round(s): {', '.join(tools_used)}")
            break

        # Hit tool round limit
        if round_num >= max_tool_rounds:
            candidate = response.text.strip() if response.text else ""
            if candidate and not _is_narration(candidate):
                draft = candidate
                break

            # Force final synthesis
            messages.append({"role": "assistant", "content": response.text or ""})
            messages.append({"role": "user", "content": "You have reached the tool limit. Synthesize all gathered information and produce the final output now."})
            final_response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=[],
                model=SONNET_MODEL,
                max_tokens=4000,
            )
            if final_response.usage:
                total_input_tokens += _total_input_tokens(final_response.usage)
                total_output_tokens += final_response.usage.get("output_tokens", 0)
            draft = final_response.text.strip() if final_response.text else ""
            break

        # Execute tools
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

        tool_results = []
        for tu in response.tool_uses:
            tools_used.append(tu.name)
            logger.info(f"[TASK_EXEC] Tool: {tu.name}({str(tu.input)[:100]})")
            result = await executor(tu.name, tu.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(result) if isinstance(result, dict) else str(result),
            })
        messages.append({"role": "user", "content": tool_results})
    else:
        draft = ""

    if not draft:
        raise ValueError("Agent produced empty draft")

    draft = _strip_tool_narration(draft)
    if not draft:
        raise ValueError("Agent produced only tool-use narration")

    # Retry if critically short
    if len(draft.split()) < 20:
        messages.append({"role": "assistant", "content": draft})
        messages.append({"role": "user", "content": (
            "Your output was too short. Produce the full content in the requested format now."
        )})
        retry_response = await chat_completion_with_tools(
            messages=messages, system=system_prompt, tools=[], model=SONNET_MODEL, max_tokens=4000,
        )
        if retry_response.usage:
            total_input_tokens += _total_input_tokens(retry_response.usage)
            total_output_tokens += retry_response.usage.get("output_tokens", 0)
        retry_draft = (retry_response.text or "").strip()
        if len(retry_draft.split()) > len(draft.split()):
            draft = retry_draft

    usage = {"input_tokens": total_input_tokens, "output_tokens": total_output_tokens}

    # Collect rendered files from RuntimeDispatch
    pending_renders = getattr(executor, "auth", None)
    pending_renders = getattr(pending_renders, "pending_renders", []) if pending_renders else []

    return draft, usage, pending_renders


# =============================================================================
# Helpers
# =============================================================================

def _load_user_context(client, user_id: str) -> Optional[list]:
    """Load user context from workspace /memory/ files."""
    try:
        from services.workspace import UserMemory
        um = UserMemory(client, user_id)
        memory_files = um.read_all_sync()
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
        # ADR-143: Inject brand context
        brand = memory_files.get("BRAND.md", "").strip()
        if brand:
            user_context.append({"key": "brand", "value": brand})
        return user_context if user_context else None
    except Exception as e:
        logger.warning(f"[TASK_EXEC] User context load failed: {e}")
        return None


def _parse_delivery_target(delivery_str: str, client, user_id: str) -> Optional[dict]:
    """Parse TASK.md delivery field into destination dict.

    Supports:
    - Email: "user@example.com" → {"platform": "email", "target": "...", "format": "send"}
    - Slack: "slack:#channel" → {"platform": "slack", "target": "#channel", "format": "send"}
    - None/empty → email fallback
    """
    if not delivery_str:
        # Fall back to user email
        from services.agent_execution import get_user_email
        from services.supabase import get_service_client
        email = get_user_email(get_service_client(), user_id)
        if email:
            return {"platform": "email", "target": email, "format": "send"}
        return None

    if "@" in delivery_str and not delivery_str.startswith("slack:"):
        return {"platform": "email", "target": delivery_str, "format": "send"}

    if delivery_str.startswith("slack:"):
        target = delivery_str[6:]
        return {"platform": "slack", "target": target, "format": "send"}

    # Unknown format — try email fallback
    from services.agent_execution import get_user_email
    from services.supabase import get_service_client
    email = get_user_email(get_service_client(), user_id)
    if email:
        return {"platform": "email", "target": email, "format": "send"}
    return None


def _fail(task_slug: str, message: str) -> dict:
    """Build failure result."""
    logger.error(f"[TASK_EXEC] {task_slug}: {message}")
    return {
        "success": False,
        "task_slug": task_slug,
        "status": "failed",
        "message": message,
    }


# =============================================================================
# Agent-first entry point (for manual runs, MCP, Execute primitive)
# =============================================================================

async def execute_agent_run(
    client,
    user_id: str,
    agent: dict,
    trigger_context: Optional[dict] = None,
) -> dict:
    """Execute an agent run — finds the agent's task and routes through execute_task().

    This is the replacement for execute_agent_generation(). Callers that have
    an agent dict (manual run, MCP, Execute primitive, event triggers) use this.

    If the agent has an assigned task, routes through execute_task().
    If no task exists, runs a direct generation (taskless — agent identity only).

    Args:
        client: Supabase service client
        user_id: User UUID
        agent: Full agent dict from DB
        trigger_context: Optional trigger info

    Returns:
        Result dict compatible with execute_agent_generation() return shape
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    agent_slug = get_agent_slug(agent)

    # Look up task assigned to this agent
    try:
        task_result = (
            client.table("tasks")
            .select("slug")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )
        # Find task whose TASK.md references this agent
        assigned_task_slug = None
        if task_result.data:
            from services.task_workspace import TaskWorkspace
            for task_row in task_result.data:
                tw = TaskWorkspace(client, user_id, task_row["slug"])
                task_md = await tw.read_task()
                if task_md and f"**Agent:** {agent_slug}" in task_md:
                    assigned_task_slug = task_row["slug"]
                    break
    except Exception as e:
        logger.warning(f"[AGENT_RUN] Task lookup failed (falling back to direct): {e}")
        assigned_task_slug = None

    if assigned_task_slug:
        # Route through task pipeline
        logger.info(f"[AGENT_RUN] {agent_slug} → task '{assigned_task_slug}'")
        result = await execute_task(client, user_id, assigned_task_slug)
        # Map to legacy result shape
        return {
            "success": result.get("success", False),
            "run_id": result.get("run_id"),
            "version_number": result.get("version_number"),
            "status": result.get("status", "failed"),
            "message": result.get("message", ""),
        }

    # No task — direct generation (taskless agent run)
    logger.info(f"[AGENT_RUN] {agent_slug} has no task — direct generation")
    return await _execute_direct(client, user_id, agent, agent_slug, trigger_context)


async def _execute_direct(
    client,
    user_id: str,
    agent: dict,
    agent_slug: str,
    trigger_context: Optional[dict] = None,
) -> dict:
    """Direct agent generation without a task. For agents not yet assigned tasks.

    Minimal pipeline: gather context → generate → save output → activity log.
    No delivery, no scheduling update (no TASK.md to read config from).
    """
    from services.workspace import AgentWorkspace, KnowledgeBase, get_agent_slug
    from services.agent_framework import has_asset_capabilities, has_capability
    from services.agent_execution import (
        get_next_run_number, create_version_record, update_version_for_delivery,
        SONNET_MODEL, _extract_contributor_assessment,
    )

    started_at = datetime.now(timezone.utc)
    agent_id = agent["id"]
    role = agent.get("role", "custom")
    scope = agent.get("scope", "cross_platform")
    title = agent.get("title", "Untitled")

    try:
        # Create agent_runs record
        next_version = await get_next_run_number(client, agent_id)
        version = await create_version_record(client, agent_id, next_version)
        version_id = version["id"]

        # Read agent workspace
        ws = AgentWorkspace(client, user_id, agent_slug)
        await ws.ensure_seeded(agent)
        ws_instructions = await ws.read("AGENT.md") or ""
        user_context = _load_user_context(client, user_id)

        # Gather context (no task_info for legacy single-agent path)
        context_text, context_meta = await gather_task_context(
            client, user_id, agent, agent_slug,
        )

        # Build prompt (use agent title as task title)
        task_info = {"title": title, "objective": {}, "success_criteria": [], "output_spec": []}
        system_prompt, user_message = build_task_execution_prompt(
            task_info=task_info,
            agent=agent,
            agent_instructions=ws_instructions,
            context=context_text,
            user_context=user_context,
        )

        # Skill docs
        if has_asset_capabilities(role):
            try:
                from services.agent_execution import _fetch_skill_docs
                skill_docs = await _fetch_skill_docs()
                if skill_docs:
                    system_prompt += f"\n\n## Output Skill Documentation\n{skill_docs}"
            except Exception:
                pass

        # Generate
        draft, usage, pending_renders = await _generate(
            client, user_id, agent, system_prompt, user_message, scope,
        )

        draft, contributor_assessment = _extract_contributor_assessment(draft)

        # Save to agent_runs
        await update_version_for_delivery(client, version_id, draft, metadata={
            "input_tokens": _total_input_tokens(usage),
            "output_tokens": usage.get("output_tokens", 0),
            "model": SONNET_MODEL,
            "trigger_type": (trigger_context or {}).get("type", "manual"),
        })

        # Save output folder
        try:
            await ws.save_output(
                content=draft,
                run_id=str(version_id),
                agent_id=str(agent_id),
                version_number=next_version,
                role=role,
                rendered_files=pending_renders if pending_renders else None,
            )
        except Exception as e:
            logger.warning(f"[AGENT_RUN] Output folder write failed: {e}")

        # Write to knowledge base
        try:
            kb = KnowledgeBase(client, user_id)
            knowledge_path = KnowledgeBase.get_knowledge_path(role, title)
            await kb.write(
                path=knowledge_path, content=draft,
                summary=f"{title} v{next_version}",
                metadata={"agent_id": str(agent_id), "role": role, "version_number": next_version},
                tags=[role],
            )
        except Exception:
            pass

        # Mark as delivered (no external delivery for taskless runs)
        now = datetime.now(timezone.utc).isoformat()
        client.table("agent_runs").update({
            "status": "delivered",
            "delivered_at": now,
        }).eq("id", version_id).execute()

        # Activity log
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        try:
            from services.activity_log import write_activity
            await write_activity(
                client=client, user_id=user_id,
                event_type="task_executed",
                summary=f"{title} v{next_version} delivered (direct)",
                event_ref=version_id,
                metadata={
                    "agent_slug": agent_slug, "agent_id": str(agent_id),
                    "version_number": next_version, "role": role,
                    "final_status": "delivered", "duration_ms": duration_ms,
                    "trigger_type": (trigger_context or {}).get("type", "manual"),
                },
            )
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Activity log write failed: {e}")

        # Work credits
        try:
            from services.platform_limits import record_credits
            record_credits(client, user_id, "task_execution", agent_id=str(agent_id))
        except Exception:
            pass

        logger.info(f"[AGENT_RUN] Complete: {agent_slug} v{next_version} delivered ({duration_ms}ms)")

        return {
            "success": True,
            "run_id": version_id,
            "version_number": next_version,
            "status": "delivered",
            "message": f"Run {next_version} delivered",
        }

    except Exception as e:
        logger.error(f"[AGENT_RUN] Failed: {agent_slug}: {e}")
        return {
            "success": False,
            "run_id": None,
            "status": "failed",
            "message": str(e),
        }
