"""
Task Pipeline — ADR-141: Unified Execution Architecture

Mechanical generation pipeline triggered by scheduler. No decision-making — just execution.

Flow:
  Scheduler finds due task (SQL)
    → Read TASK.md (objective, criteria, output spec, agent slug)
    → Resolve agent (DB lookup by slug)
    → Read AGENT.md (identity, expertise)
    → Read agent memory/ (accumulated knowledge)
    → Search /knowledge/ (relevant workspace context)
    → Build execution prompt (task objective + agent identity + context)
    → Generate output (Sonnet, multi-tool-round)
    → Save output to /tasks/{slug}/outputs/{date}/
    → Compose HTML (render service, non-fatal)
    → Append to memory/run_log.md
    → Write to /knowledge/ (accumulation)
    → Deliver per TASK.md config
    → Update tasks.last_run_at + calculate next_run_at
    → Write activity event

Replaces: agent_pulse.py, trigger_dispatch.py, execution_strategies.py,
          agent_execution.py (execute_agent_generation).
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


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
) -> tuple[str, dict]:
    """Gather context for task execution.

    Reads from agent workspace (identity, memory, observations) and knowledge base.
    Knowledge base includes platform content (synced to /knowledge/ by platform sync).
    Replaces the strategy pattern (PlatformBound/CrossPlatform/Analyst/Research).

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

    # 2. Knowledge base — search for relevant content
    # This includes platform content (Slack, Notion) synced to /knowledge/ paths
    role = agent.get("role", "custom")
    title = agent.get("title", "")
    kb = KnowledgeBase(client, user_id)
    try:
        kb_results = await kb.search(
            query=title,
            role=role,
            limit=10,
        )
        if kb_results:
            kb_text = "\n\n".join([
                f"### {r.get('path', 'unknown')}\n{r.get('content', '')[:2000]}"
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
    workspace_preferences: Optional[str] = None,
) -> tuple[str, str]:
    """Build system prompt and user message for task execution.

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

    # Learned preferences (from workspace memory/preferences.md)
    if workspace_preferences:
        system += f"""

## Learned Preferences (from user edit history)
{workspace_preferences}

Follow these preferences closely — they reflect what the user has consistently edited in past outputs."""

    # Tool usage guidance
    system += """

## Tool Usage (Headless Mode)
You have read-only investigation tools: Search, Read, List, WebSearch, GetSystemState.
- Use tools ONLY if the gathered context is clearly insufficient.
- Prefer generating from the provided context — most tasks have enough.
- NEVER narrate your tool usage in the final output.

## Empty Context Handling
If context says "(No context available)" or tools return no results:
- Still produce the output in the requested format.
- Note briefly that no recent activity was found.
- A short, properly formatted output is always better than meta-commentary."""

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

def calculate_next_run_at(schedule: dict, last_run_at: Optional[datetime] = None) -> datetime:
    """Calculate next_run_at from schedule config. Pure math, no LLM.

    Delegates to the existing scheduler utility.
    """
    from jobs.unified_scheduler import calculate_next_pulse_from_schedule
    return calculate_next_pulse_from_schedule(schedule, from_time=last_run_at)


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

    try:
        # =====================================================================
        # 1. Read TASK.md
        # =====================================================================
        tw = TaskWorkspace(client, user_id, task_slug)
        task_md_content = await tw.read_task()
        if not task_md_content:
            return _fail(task_slug, "TASK.md not found")

        task_info = parse_task_md(task_md_content)
        agent_slug = task_info.get("agent_slug", "").strip()
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
        # 3. Check work budget
        # =====================================================================
        try:
            from services.platform_limits import check_work_budget
            budget_ok = check_work_budget(client, user_id)
            if not budget_ok:
                logger.info(f"[TASK_EXEC] Work budget exhausted for user {user_id[:8]}")
                return _fail(task_slug, "Work budget exhausted")
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Budget check failed (proceeding): {e}")

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
        ws_preferences = await ws.read("memory/preferences.md") or ""

        # User context (profile + preferences)
        user_context = _load_user_context(client, user_id)

        # =====================================================================
        # 6. Gather context
        # =====================================================================
        context_text, context_meta = await gather_task_context(
            client, user_id, agent, agent_slug,
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
            workspace_preferences=ws_preferences,
        )

        # Skill docs for agents with asset capabilities
        skill_docs = None
        if has_asset_capabilities(role):
            try:
                from services.agent_execution import _fetch_skill_docs
                skill_docs = await _fetch_skill_docs()
                if skill_docs:
                    system_prompt += f"""

## Output Skill Documentation
You have access to RuntimeDispatch for producing binary artifacts.
Construct input specs according to these skill instructions:

{skill_docs}

When producing output that would benefit from a rendered artifact (PDF, PPTX, XLSX, chart),
use RuntimeDispatch with the spec format described above. Always produce a text version
alongside any binary — the text is the feedback surface for user edits."""
            except Exception as e:
                logger.warning(f"[TASK_EXEC] Skill docs fetch failed: {e}")

        # Generate via headless agent (multi-tool-round)
        draft, usage, pending_renders = await _generate(
            client, user_id, agent, system_prompt, user_message, scope,
        )

        # Strip contributor assessment before delivery (ADR-128)
        from services.agent_execution import _extract_contributor_assessment
        draft, contributor_assessment = _extract_contributor_assessment(draft)

        # =====================================================================
        # 8. Update agent_runs record with content
        # =====================================================================
        from services.agent_execution import update_version_for_delivery, SONNET_MODEL
        version_metadata = {
            "input_tokens": usage.get("input_tokens", 0),
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
        # 12. Compose HTML (non-fatal)
        # =====================================================================
        if agent_output_folder and has_capability(role, "compose_html"):
            try:
                from services.agent_execution import _compose_output_html
                await _compose_output_html(
                    client, user_id, agent_slug, agent_output_folder,
                    title=title, pending_renders=pending_renders,
                )
            except Exception as e:
                logger.warning(f"[TASK_EXEC] Compose HTML failed: {e}")

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

        # Append to task run log
        try:
            log_entry = f"v{next_version} {final_status}"
            if delivery_error:
                log_entry += f" — {delivery_error}"
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
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                },
            )
        except Exception:
            pass

        if final_status == "delivered":
            try:
                from services.platform_limits import record_work_units
                record_work_units(client, user_id, "task_execution", 1, agent_id=str(agent_id))
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
# Generation (reuses headless agent loop from agent_execution)
# =============================================================================

# Scope → max tool rounds
_TOOL_ROUNDS = {
    "platform": 2,
    "cross_platform": 3,
    "knowledge": 3,
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
    max_tool_rounds = _TOOL_ROUNDS.get(scope, 3)

    # Planner/prepare needs more rounds
    if role in ("prepare", "planner"):
        max_tool_rounds = max(max_tool_rounds, 5)

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
            total_input_tokens += response.usage.get("input_tokens", 0)
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
                total_input_tokens += final_response.usage.get("input_tokens", 0)
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
            total_input_tokens += retry_response.usage.get("input_tokens", 0)
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
        ws_preferences = await ws.read("memory/preferences.md") or ""
        user_context = _load_user_context(client, user_id)

        # Gather context
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
            workspace_preferences=ws_preferences,
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
            "input_tokens": usage.get("input_tokens", 0),
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
        except Exception:
            pass

        # Work units
        try:
            from services.platform_limits import record_work_units
            record_work_units(client, user_id, "agent_run", 1, agent_id=str(agent_id))
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
