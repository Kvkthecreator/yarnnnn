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


async def _gather_context_domains(
    client,
    user_id: str,
    context_reads: list[str],
    max_files_per_domain: int = 20,
    max_content_per_file: int = 3000,
) -> str:
    """Read accumulated context from workspace context domains.

    ADR-151: /workspace/context/{domain}/ files are the primary context source.
    Reads all files from each domain in context_reads, ordered by recency.

    Returns formatted context string with domain sections.
    """
    if not context_reads:
        return ""

    from services.directory_registry import get_domain_folder

    sections = []

    for domain_key in context_reads:
        folder = get_domain_folder(domain_key)
        if not folder:
            continue

        prefix = f"/workspace/{folder}"
        try:
            result = (
                client.table("workspace_files")
                .select("path, content, updated_at, tags")
                .eq("user_id", user_id)
                .like("path", f"{prefix}/%")
                .order("updated_at", desc=True)
                .limit(max_files_per_domain)
                .execute()
            )
            rows = result.data or []

            if not rows:
                continue

            domain_parts = []
            for row in rows:
                path = row.get("path", "")
                content = (row.get("content") or "")[:max_content_per_file]
                updated = row.get("updated_at", "")[:10]  # Date only

                # Make path relative to domain folder for readability
                rel_path = path.replace(prefix + "/", "")

                if content.strip():
                    domain_parts.append(
                        f"### {rel_path}" + (f" (updated {updated})" if updated else "") +
                        f"\n{content}"
                    )

            if domain_parts:
                sections.append(
                    f"## Accumulated Context: {domain_key}\n" +
                    "\n\n".join(domain_parts)
                )

        except Exception as e:
            logger.warning(f"[TASK_EXEC] Context domain read failed for {domain_key}: {e}")

    return "\n\n".join(sections) if sections else ""


async def _post_run_domain_scan(
    client,
    user_id: str,
    task_slug: str,
    task_info: dict,
    draft: str,
    version_number: int,
    run_time,
    tools_used: Optional[list] = None,
    agent_reflection: Optional[dict] = None,
    duration_s: float = 0,
    tool_rounds: int = 0,
) -> None:
    """Post-execution: scan domains, update trackers, update task awareness.

    ADR-154: Replaces _route_output_to_context_domains(). Three responsibilities:
    1. Signal log entry (preserved from old function)
    2. Scan entity-bearing domains → update _tracker.md (materialized view)
    3. Update task awareness.md with cycle state

    All deterministic — no LLM calls. Non-fatal — failures logged.
    """
    from services.directory_registry import (
        get_domain_folder, has_entity_tracker, build_tracker_md, get_tracker_path,
    )
    from services.workspace import UserMemory
    from services.task_workspace import TaskWorkspace

    context_writes = (task_info or {}).get("context_writes", [])
    context_reads = (task_info or {}).get("context_reads", [])
    title = (task_info or {}).get("title", task_slug)
    um = UserMemory(client, user_id)
    tw = TaskWorkspace(client, user_id, task_slug)
    date_str = run_time.strftime("%Y-%m-%d")

    # ── 1. Signal log entry (preserved) ──
    try:
        if "signals" in context_writes:
            signal_path = f"context/signals/{date_str}.md"
            existing = await um.read(signal_path) or f"# Signals — {date_str}\n"
            signal_entry = (
                f"\n## {title} v{version_number} ({run_time.strftime('%H:%M UTC')})\n"
                f"- Task: {task_slug}\n"
                f"- Output: {len(draft)} chars\n"
                f"- Summary: {draft[:200].replace(chr(10), ' ').strip()}...\n"
            )
            await um.write(signal_path, existing + signal_entry,
                          summary=f"Signal from {task_slug} v{version_number}")
    except Exception as e:
        logger.warning(f"[TASK_EXEC] Signal log write failed (non-fatal): {e}")

    # ── 2. Domain entity scan → _tracker.md ──
    # Scan all domains this task writes to (for context tasks)
    entities_touched: dict[str, list[str]] = {}  # domain → [entity slugs]
    all_domains = set(context_writes) | set(context_reads)

    for domain_key in all_domains:
        if not has_entity_tracker(domain_key):
            continue

        folder = get_domain_folder(domain_key)
        if not folder:
            continue

        try:
            tracker_path = get_tracker_path(domain_key)
            prefix = f"/workspace/{folder}/"

            # List all files in this domain
            result = (
                client.table("workspace_files")
                .select("path, updated_at")
                .eq("user_id", user_id)
                .like("path", f"{prefix}%")
                .order("updated_at", desc=True)
                .limit(200)
                .execute()
            )
            rows = result.data or []

            # Extract entity subfolders from paths
            # e.g., /workspace/context/competitors/acme-corp/profile.md → acme-corp
            entity_files: dict[str, dict] = {}  # slug → {last_updated, files}
            for row in rows:
                path = row.get("path", "")
                rel = path.replace(prefix, "")
                parts = rel.split("/")
                if len(parts) < 2:
                    continue  # Top-level files (_tracker.md, _landscape.md) — skip
                entity_slug = parts[0]
                if entity_slug.startswith("_"):
                    continue  # Synthesis/tracker files
                filename = parts[1].replace(".md", "")

                if entity_slug not in entity_files:
                    entity_files[entity_slug] = {
                        "slug": entity_slug,
                        "last_updated": row.get("updated_at", "")[:10],
                        "files": [],
                        "status": "active",
                    }
                if filename not in entity_files[entity_slug]["files"]:
                    entity_files[entity_slug]["files"].append(filename)

            # Calculate staleness based on task schedule
            schedule = task_info.get("schedule", "weekly")
            stale_days = {"daily": 3, "weekly": 10, "monthly": 45}.get(schedule, 14)
            from datetime import timedelta
            stale_cutoff = (run_time - timedelta(days=stale_days)).strftime("%Y-%m-%d")

            entities_list = []
            for slug, edata in sorted(entity_files.items()):
                if edata["last_updated"] and edata["last_updated"] < stale_cutoff:
                    edata["status"] = "stale"
                elif not edata["files"]:
                    edata["status"] = "discovered"
                entities_list.append(edata)

            # Track which entities were touched this cycle (updated today)
            touched = [e["slug"] for e in entities_list if e.get("last_updated") == date_str]
            if touched:
                entities_touched[domain_key] = touched

            # Write _tracker.md
            if tracker_path:
                tracker_content = build_tracker_md(domain_key, entities_list)
                await um.write(tracker_path, tracker_content,
                              summary=f"Entity tracker update: {domain_key}")

        except Exception as e:
            logger.warning(f"[TASK_EXEC] Domain scan failed for {domain_key} (non-fatal): {e}")

    # ── 3. Update task awareness.md ──
    try:
        awareness_lines = ["# Task Awareness\n"]

        # Last cycle section
        awareness_lines.append("## Last Cycle")
        awareness_lines.append(f"- **Run:** {run_time.strftime('%Y-%m-%d %H:%M UTC')} (v{version_number})")
        if duration_s:
            awareness_lines.append(f"- **Duration:** {duration_s:.0f}s, {tool_rounds} tool rounds")
        if entities_touched:
            for dk, slugs in entities_touched.items():
                awareness_lines.append(f"- **Entities touched ({dk}):** {', '.join(slugs)}")
        if tools_used:
            # Summarize tool usage
            from collections import Counter
            tool_counts = Counter(tools_used)
            tool_summary = ", ".join(f"{name} ({count})" for name, count in tool_counts.most_common())
            awareness_lines.append(f"- **Tools used:** {tool_summary}")
        if agent_reflection:
            confidence = agent_reflection.get("output_confidence", "unknown")
            level = confidence.split("—")[0].split("–")[0].strip() if confidence else "unknown"
            awareness_lines.append(f"- **Agent reflection:** confidence={level}")

        # Phase detection (ADR-154)
        type_key = (task_info or {}).get("type_key", "")
        task_phase = "steady"
        if type_key and context_writes:
            from services.task_types import get_bootstrap_criteria, evaluate_bootstrap_status
            bootstrap = get_bootstrap_criteria(type_key)
            if bootstrap:
                required_files = bootstrap.get("required_files", [])
                # Count entities that have all required files across all write domains
                total_qualified = 0
                total_entities = 0
                for dk in context_writes:
                    if dk == "signals" or not has_entity_tracker(dk):
                        continue
                    for slug, edata in entities_touched.get(dk, []) and [] or []:
                        pass  # entities_touched only has slugs
                # Use the tracker data we already built
                for dk in context_writes:
                    if dk == "signals" or dk not in entities_touched and dk not in all_domains:
                        continue
                    tracker_path_check = get_tracker_path(dk)
                    if not tracker_path_check:
                        continue
                    tracker_content_check = await um.read(tracker_path_check)
                    if not tracker_content_check:
                        continue
                    for line in tracker_content_check.split("\n"):
                        if line.startswith("|") and "Slug" not in line and "---" not in line:
                            parts = [p.strip() for p in line.split("|")]
                            if len(parts) >= 5:
                                total_entities += 1
                                files_str = parts[3] if len(parts) > 3 else ""
                                entity_files = [f.strip() for f in files_str.split(",") if f.strip() and f.strip() != "—"]
                                if all(rf in entity_files for rf in required_files):
                                    total_qualified += 1
                task_phase = evaluate_bootstrap_status(type_key, total_entities, total_qualified)

        # Domain state + phase section
        awareness_lines.append(f"\n## Phase: {task_phase}")
        if task_phase == "bootstrap":
            bootstrap_info = get_bootstrap_criteria(type_key) or {}
            min_e = bootstrap_info.get("min_entities", "?")
            awareness_lines.append(f"- Bootstrap in progress: {total_qualified}/{min_e} entities meet criteria")
            awareness_lines.append(f"- Total entities discovered: {total_entities}")
        else:
            awareness_lines.append("- Domain established. Normal cadence.")

        if context_writes:
            awareness_lines.append("\n## Domain State")
            for domain_key in context_writes:
                if domain_key == "signals":
                    continue
                if not has_entity_tracker(domain_key):
                    continue
                tracker_path = get_tracker_path(domain_key)
                if tracker_path:
                    tracker_content = await um.read(tracker_path)
                    if tracker_content:
                        health_start = tracker_content.find("## Domain Health")
                        if health_start >= 0:
                            awareness_lines.append(f"### {domain_key}")
                            awareness_lines.append(tracker_content[health_start:].strip())

        # Next cycle focus (derived from staleness + phase)
        stale_entities: list[str] = []
        for domain_key in (context_writes or context_reads):
            if not has_entity_tracker(domain_key) or domain_key == "signals":
                continue
            tracker_path = get_tracker_path(domain_key)
            if tracker_path:
                tracker_content = await um.read(tracker_path)
                if tracker_content:
                    for line in tracker_content.split("\n"):
                        if "| stale |" in line.lower():
                            parts = line.split("|")
                            if len(parts) >= 2:
                                slug = parts[1].strip()
                                if slug:
                                    stale_entities.append(f"{slug} ({domain_key})")

        awareness_lines.append(f"\n## Next Cycle Focus")
        if task_phase == "bootstrap":
            awareness_lines.append("- **BOOTSTRAP PRIORITY:** Discover and profile new entities to meet minimum criteria.")
            if stale_entities:
                for se in stale_entities:
                    awareness_lines.append(f"- {se}: stale — update alongside discovery")
        elif stale_entities:
            for se in stale_entities:
                awareness_lines.append(f"- {se}: stale — prioritize update")
        else:
            awareness_lines.append("- All entities current. Discover new entities or deepen existing profiles.")

        awareness_content = "\n".join(awareness_lines) + "\n"
        await tw.write("awareness.md", awareness_content,
                      summary=f"Task awareness update v{version_number}")

    except Exception as e:
        logger.warning(f"[TASK_EXEC] Awareness update failed (non-fatal): {e}")


def _extract_recent_feedback(feedback_md: str, max_entries: int = 3) -> str:
    """Extract the most recent N feedback entries from task feedback.md.

    ADR-149: feedback.md has entries like '## Feedback (date, source: ...)' or
    '## Evaluation (date, source: ...)'. Returns the last N entries as a string.
    """
    if not feedback_md or not feedback_md.strip():
        return ""
    entries = re.split(r"(?=^## )", feedback_md, flags=re.MULTILINE)
    entries = [e.strip() for e in entries if e.strip() and e.strip().startswith("## ")]
    if not entries:
        return ""
    recent = entries[:max_entries]  # Already newest-first (append-at-top convention)
    return "\n\n".join(recent)


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
        elif line_stripped.startswith("**Mode:**"):
            result["mode"] = line_stripped.split("**Mode:**")[1].strip()
        elif line_stripped.startswith("**Class:**"):
            result["task_class"] = line_stripped.split("**Class:**")[1].strip()
        elif line_stripped.startswith("**Schedule:**"):
            result["schedule"] = line_stripped.split("**Schedule:**")[1].strip()
        elif line_stripped.startswith("**Delivery:**"):
            result["delivery"] = line_stripped.split("**Delivery:**")[1].strip()
        elif line_stripped.startswith("**Context Reads:**"):
            raw = line_stripped.split("**Context Reads:**")[1].strip()
            result["context_reads"] = [d.strip() for d in raw.split(",") if d.strip() and d.strip() != "none"]
        elif line_stripped.startswith("**Context Writes:**"):
            raw = line_stripped.split("**Context Writes:**")[1].strip()
            result["context_writes"] = [d.strip() for d in raw.split(",") if d.strip() and d.strip() != "none"]
        elif line_stripped.startswith("**Output Category:**"):
            raw = line_stripped.split("**Output Category:**")[1].strip()
            result["output_category"] = raw if raw != "none" else ""

    # Parse sections
    current_section = None
    for line in lines:
        line_stripped = line.strip()
        if line_stripped == "## Objective":
            current_section = "objective"
        elif line_stripped == "## Process":
            current_section = "process"
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
        elif current_section == "process" and re.match(r"^\d+\.\s+\*\*", line_stripped):
            # Parse: "1. **Update-Context** (research-agent): instruction text"
            step_match = re.match(
                r"^\d+\.\s+\*\*(.+?)\*\*\s*\(([^)]+)\)(?::\s*(.*))?",
                line_stripped,
            )
            if step_match:
                step_name = step_match.group(1).strip().lower().replace(" ", "-")
                agent_ref = step_match.group(2).strip()
                instruction_text = (step_match.group(3) or "").strip()
                result.setdefault("process_steps", []).append({
                    "step": step_name,
                    "agent_ref": agent_ref,  # Could be agent_slug or agent_type
                    "instruction": instruction_text,
                })

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
    task_slug: Optional[str] = None,
) -> tuple[str, dict]:
    """Gather context for task execution.

    ADR-154: Context priority order (who/what/how):
    1. Task awareness (HOW) — cycle-to-cycle execution state
    2. Domain tracker (WHAT) — entity registry + freshness (context tasks)
    3. Accumulated context domains (WHAT) — /workspace/context/ files
    4. Agent identity (WHO) — AGENT.md only (no thesis, no working notes)
    5. User notes — workspace-level standing instructions

    Returns:
        (context_text, context_metadata)
    """
    from services.workspace import AgentWorkspace, UserMemory
    from services.task_workspace import TaskWorkspace

    ws = AgentWorkspace(client, user_id, agent_slug)
    await ws.ensure_seeded(agent)

    sections = []

    # 0. Task awareness — cycle-to-cycle state (ADR-154)
    if task_slug:
        try:
            tw = TaskWorkspace(client, user_id, task_slug)
            awareness = await tw.read("awareness.md")
            if awareness and "no prior cycles" not in awareness:
                sections.append(f"## Execution Awareness\n{awareness}")
        except Exception as e:
            logger.debug(f"[TASK_EXEC] Awareness read failed: {e}")

    # 1. Domain tracker — entity registry for context tasks (ADR-154)
    if task_info:
        context_writes = task_info.get("context_writes", [])
        if context_writes:
            from services.directory_registry import has_entity_tracker, get_tracker_path
            um_tracker = UserMemory(client, user_id)
            for domain_key in context_writes:
                if domain_key == "signals" or not has_entity_tracker(domain_key):
                    continue
                tracker_path = get_tracker_path(domain_key)
                if tracker_path:
                    try:
                        tracker_content = await um_tracker.read(tracker_path)
                        if tracker_content:
                            sections.append(f"## Entity Tracker: {domain_key}\n{tracker_content}")
                    except Exception:
                        pass

    # 2. Accumulated context domains — PRIMARY CONTEXT (ADR-151/152)
    context_domains_text = ""
    if task_info:
        context_reads = task_info.get("context_reads", [])
        if context_reads:
            context_domains_text = await _gather_context_domains(
                client, user_id, context_reads,
            )
    if context_domains_text:
        sections.append(context_domains_text)

    # 3. Agent identity — AGENT.md only (ADR-154: no thesis, no working notes)
    # load_context() still used for now — will be thinned in Phase 2b
    ws_context = await ws.load_context()
    if ws_context:
        sections.append(f"## Agent Context\n{ws_context}")

    # 4. User notes — workspace-level standing instructions
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
    deliverable_spec: str = "",
    steering_notes: str = "",
    task_feedback: str = "",
    task_mode: str = "recurring",
    prior_output: str = "",
    task_phase: str = "steady",
) -> tuple[str, str]:
    """Build system prompt and user message for task execution.

    ADR-154: Phase-aware. Bootstrap phase overrides step instructions.
    ADR-149: DELIVERABLE.md injected into system prompt.

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

    # ADR-149: DELIVERABLE.md — quality contract injection
    if deliverable_spec and deliverable_spec.strip():
        # Strip the header and comments, keep the spec sections
        spec_clean = deliverable_spec.strip()
        if spec_clean.startswith("# Deliverable Specification"):
            spec_clean = spec_clean.split("\n", 1)[-1].strip()
        # Remove HTML comments
        spec_clean = re.sub(r"<!--.*?-->", "", spec_clean, flags=re.DOTALL).strip()
        if spec_clean:
            system += f"\n\n## Deliverable Specification\nYour output MUST match this quality contract:\n{spec_clean}"

    # Reflection postamble (ADR-128/149 + success criteria eval)
    from services.agent_pipeline import _REFLECTION_POSTAMBLE, _CRITERIA_EVAL_SECTION
    criteria = task_info.get("success_criteria", [])
    if criteria:
        criteria_list = "\n".join(f"  - {c}" for c in criteria)
        criteria_eval = _CRITERIA_EVAL_SECTION.format(criteria_list=criteria_list)
    else:
        criteria_eval = ""
    system += _REFLECTION_POSTAMBLE.format(criteria_eval=criteria_eval)

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
        # ADR-154: Phase-aware step instruction
        step_instruction = objective.get("step_instruction")
        if task_phase == "bootstrap" and step_instruction:
            # Override with bootstrap-specific instruction if available
            from services.task_types import STEP_INSTRUCTIONS
            bootstrap_key = None
            for key in STEP_INSTRUCTIONS:
                if key.endswith(":bootstrap") and key.replace(":bootstrap", "") in (step_instruction[:30] or ""):
                    bootstrap_key = key
                    break
            # Simpler: check if update-context:bootstrap exists and step is update-context
            if "update-context:bootstrap" in STEP_INSTRUCTIONS:
                # Check if original instruction matches update-context
                if STEP_INSTRUCTIONS.get("update-context", "")[:50] in step_instruction[:50]:
                    step_instruction = STEP_INSTRUCTIONS["update-context:bootstrap"]
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

    # ADR-149: Goal mode — prior output as primary context
    if task_mode == "goal" and prior_output:
        user_parts.append(
            "\n## Prior Output (YOUR PRIMARY INPUT)\n"
            "You are revising this deliverable. Improve based on steering notes "
            "and feedback below. Build on what exists — do not start from scratch.\n\n"
            f"{prior_output[:8000]}"
        )

    # ADR-149: Steering notes — TP's cycle-specific guidance
    if steering_notes and steering_notes.strip():
        clean_steering = steering_notes.strip()
        # Strip file header/comments
        if clean_steering.startswith("# Steering Notes"):
            clean_steering = clean_steering.split("\n", 1)[-1].strip()
        clean_steering = re.sub(r"<!--.*?-->", "", clean_steering, flags=re.DOTALL).strip()
        if clean_steering:
            user_parts.append(f"\n## Steering Notes (from task manager)\n{clean_steering}")

    # ADR-149: Recent task feedback — user corrections + TP evaluations
    if task_feedback and task_feedback.strip():
        user_parts.append(f"\n## Recent Feedback\nIncorporate these corrections:\n{task_feedback}")

    # Gathered context
    user_parts.append(f"\n## Gathered Context\n{context}")

    user_message = "\n".join(user_parts)

    return system, user_message


# =============================================================================
# Cadence Calculation
# =============================================================================

def calculate_next_run_at(
    schedule,
    last_run_at: Optional[datetime] = None,
) -> Optional[datetime]:
    """Calculate next_run_at from schedule string. Pure math, no LLM.

    ADR-154: Schedule is just schedule — no phase override. Phase affects
    execution depth (tool rounds, prompt), not frequency. The journalist
    model: first run is deep research, subsequent runs are delta updates,
    but the check-in rhythm stays the same.
    """
    now = last_run_at or datetime.now(timezone.utc)

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
            return now + timedelta(hours=24)

    # Legacy dict format
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
    from services.workspace import AgentWorkspace, UserMemory, get_agent_slug
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
        # 1b. Read DELIVERABLE.md + task memory (ADR-149)
        # =====================================================================
        deliverable_spec = await tw.read("DELIVERABLE.md") or ""
        steering_notes = await tw.read("memory/steering.md") or ""
        task_feedback_raw = await tw.read("memory/feedback.md") or ""
        # Extract last 3 feedback entries for prompt injection (keep it concise)
        task_feedback = _extract_recent_feedback(task_feedback_raw, max_entries=3)

        # =====================================================================
        # 1c. Read mode from TASK.md (ADR-154 — single source of truth)
        # =====================================================================
        task_mode = task_info.get("mode", "recurring")

        # =====================================================================
        # 1d. Check for multi-step process (ADR-152: read from TASK.md, not registry)
        # =====================================================================
        process_steps = task_info.get("process_steps", [])
        if len(process_steps) > 1:
            # Multi-step process — delegate to process executor
            result = await _execute_pipeline(
                client, user_id, task_slug, tw, task_info, process_steps, started_at,
                deliverable_spec=deliverable_spec,
                steering_notes=steering_notes,
                task_feedback=task_feedback,
                task_mode=task_mode,
            )
            return result

        # Single-step execution (existing flow)
        agent_slug = task_info.get("agent_slug", "").strip()

        # ADR-152: For single-step tasks, resolve agent from TASK.md process_steps
        if not agent_slug and process_steps:
            agent_ref = process_steps[0].get("agent_ref") or process_steps[0].get("agent_type", "")
            if agent_ref:
                roster = client.table("agents").select("slug, role").eq("user_id", user_id).execute()
                for a in (roster.data or []):
                    if a.get("slug") == agent_ref or a.get("role") == agent_ref:
                        agent_slug = a["slug"]
                        logger.info(f"[TASK_EXEC] Resolved agent {agent_slug} from TASK.md process")
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
        # 6. Gather context (ADR-154: includes awareness + tracker)
        # =====================================================================
        context_text, context_meta = await gather_task_context(
            client, user_id, agent, agent_slug, task_info=task_info,
            task_slug=task_slug,
        )

        # =====================================================================
        # 6b. Goal mode: read prior output for revision context (ADR-149)
        # =====================================================================
        prior_output = ""
        if task_mode == "goal":
            prior_output = await tw.read("outputs/latest/output.md") or ""

        # =====================================================================
        # 6c. Detect phase from awareness.md (ADR-154)
        # =====================================================================
        task_phase = "steady"
        try:
            _awareness_check = await tw.read("awareness.md") or ""
            if "## Phase: bootstrap" in _awareness_check or "no prior cycles" in _awareness_check:
                task_phase = "bootstrap"
        except Exception:
            pass

        # =====================================================================
        # 7. Build prompt and generate
        # =====================================================================
        system_prompt, user_message = build_task_execution_prompt(
            task_info=task_info,
            agent=agent,
            agent_instructions=ws_instructions,
            context=context_text,
            user_context=user_context,
            deliverable_spec=deliverable_spec,
            steering_notes=steering_notes,
            task_feedback=task_feedback,
            task_mode=task_mode,
            prior_output=prior_output,
            task_phase=task_phase,
        )

        # ADR-148: No SKILL.md injection, no RuntimeDispatch during headless generation.
        # Agent writes prose with inline data tables + mermaid blocks.
        # Post-generation render phase (render_inline_assets) handles chart/diagram rendering.

        # Generate via headless agent (multi-tool-round)
        draft, usage, pending_renders, _tools_used, _tool_rounds = await _generate(
            client, user_id, agent, system_prompt, user_message, scope,
            task_phase=task_phase,
        )

        # Strip agent reflection before delivery (ADR-128/149)
        from services.agent_execution import _extract_agent_reflection
        draft, agent_reflection = _extract_agent_reflection(draft)

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
            "trigger_type": "scheduled",
        }
        await update_version_for_delivery(client, version_id, draft, metadata=version_metadata)

        # =====================================================================
        # 9. Save output to task workspace (mode-aware, ADR-149)
        # =====================================================================
        date_folder = started_at.strftime("%Y-%m-%dT%H%M")

        if task_mode == "goal":
            # Goal mode: archive prior output, write to latest/ (revision pattern)
            prior_latest = await tw.read("outputs/latest/output.md")
            if prior_latest:
                await tw.write(
                    f"outputs/{date_folder}/output.md", prior_latest,
                    summary=f"Archive prior version before revision",
                    tags=["output", "archive"],
                )
            await tw.write(
                "outputs/latest/output.md", draft,
                summary=f"Goal revision v{next_version}",
                tags=["output", "latest"],
            )
            task_output_folder = "latest"
        else:
            # Recurring + reactive: new dated folder + overwrite latest/
            task_output_folder = await tw.save_output(
                content=draft,
                agent_slug=agent_slug,
                manifest_data={
                    "version_id": str(version_id),
                    "version_number": next_version,
                    "tokens": usage,
                },
            )
            # Also write to latest/ for easy access
            try:
                await tw.write(
                    "outputs/latest/output.md", draft,
                    summary=f"Latest output v{next_version}",
                    tags=["output", "latest"],
                )
            except Exception:
                pass  # Non-critical

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
        # 11. Post-run domain scan + awareness update (ADR-154)
        # =====================================================================
        run_duration = (datetime.now(timezone.utc) - started_at).total_seconds()
        await _post_run_domain_scan(
            client, user_id, task_slug, task_info, draft, next_version, started_at,
            tools_used=_tools_used,
            agent_reflection=agent_reflection,
            duration_s=run_duration,
            tool_rounds=_tool_rounds,
        )

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

        # Append to task run log (with agent reflection if available)
        try:
            log_entry = f"v{next_version} {final_status}"
            if delivery_error:
                log_entry += f" — {delivery_error}"
            if agent_reflection:
                confidence = agent_reflection.get("output_confidence", "unknown")
                # Extract level from "high — reason" format
                level = confidence.split("—")[0].split("–")[0].strip().lower() if confidence else "unknown"
                log_entry += f" | confidence={level}"
                # Include criteria eval if present
                criteria_met = agent_reflection.get("criteria_met")
                if criteria_met:
                    log_entry += f" | criteria: {criteria_met}"
            await tw.append_run_log(log_entry)
        except Exception:
            pass

        # ADR-154: Agent self-observation and reflection REMOVED from agent workspace.
        # Reflections are now folded into task awareness.md by _post_run_domain_scan().

        # Agent card (ADR-116)
        if final_status == "delivered":
            try:
                from services.agent_execution import _generate_agent_card
                await _generate_agent_card(client, user_id, agent, next_version)
            except Exception:
                pass

        # =====================================================================
        # 15. Update scheduling (ADR-154: phase-aware)
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
            schedule = (task_row.data[0]["schedule"] if task_row.data else None) or None

            next_run = calculate_next_run_at(schedule, last_run_at=now) if schedule else None

            update_data = {
                "last_run_at": now.isoformat(),
                # Always set next_run_at — either to next scheduled time or None
                # to clear the optimistic sentinel. Without this, on-demand/reactive
                # tasks with no schedule get re-picked by the scheduler when the
                # +2h sentinel expires.
                "next_run_at": next_run.isoformat() if next_run else None,
            }

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
        # Clear the optimistic sentinel so failed reactive tasks don't re-run
        try:
            task_row = client.table("tasks").select("schedule").eq(
                "user_id", user_id
            ).eq("slug", task_slug).limit(1).execute()
            schedule = (task_row.data[0]["schedule"] if task_row.data else None) or None
            next_run = calculate_next_run_at(schedule, last_run_at=datetime.now(timezone.utc)) if schedule else None
            client.table("tasks").update({
                "next_run_at": next_run.isoformat() if next_run else None,
            }).eq("user_id", user_id).eq("slug", task_slug).execute()
        except Exception:
            pass  # Best-effort cleanup
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
    process_steps: list,  # ADR-152: from TASK.md, not registry
    started_at,
    deliverable_spec: str = "",
    steering_notes: str = "",
    task_feedback: str = "",
    task_mode: str = "recurring",
) -> dict:
    """Execute a multi-step process — sequential agent execution with handoffs.

    ADR-152: process_steps come from parsed TASK.md, not the task type registry.
    Each step has: {step, agent_ref, instruction}.

    Each process step:
    1. Resolve agent by slug or type from user's roster
    2. Gather step-specific context (agent workspace + prior step output)
    3. Generate with step instruction merged into task objective
    4. Save step output to /tasks/{slug}/outputs/{date}/step-{N}/

    ADR-149: Reads DELIVERABLE.md + steering + feedback. Mode-aware output write.
    Final step's output becomes the task deliverable.
    """
    from services.task_workspace import TaskWorkspace
    from services.workspace import AgentWorkspace
    from services.agent_framework import has_asset_capabilities, has_capability
    from services.agent_execution import (
        get_next_run_number, create_version_record,
        update_version_for_delivery, SONNET_MODEL,
        _extract_agent_reflection, _compose_output_html,
    )
    from services.platform_limits import check_credits, record_credits

    steps = process_steps  # ADR-152: from TASK.md, not registry
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
    slug_to_agent = {}
    for a in all_agents:
        r = a.get("role")
        s = a.get("slug")
        if r and r not in role_to_agent:
            role_to_agent[r] = a
        if s:
            slug_to_agent[s] = a

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
        # ADR-152: Steps from TASK.md have agent_ref; registry steps have agent_type
        agent_ref = step.get("agent_ref") or step.get("agent_type", "")
        step_name = step["step"]
        step_instruction = step.get("instruction", "")
        # If instruction is empty (TASK.md may truncate), use generic template
        if not step_instruction:
            from services.task_types import STEP_INSTRUCTIONS
            step_instruction = STEP_INSTRUCTIONS.get(step_name, "")

        # Resolve agent: try slug first, then role/type
        agent = slug_to_agent.get(agent_ref) if agent_ref in slug_to_agent else role_to_agent.get(agent_ref)
        if not agent:
            logger.warning(f"[PIPELINE] Step {step_num} ({step_name}): no agent '{agent_ref}' — skipping")
            step_outputs.append(f"(Step {step_num} skipped: no {agent_ref} agent)")
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
            task_slug=task_slug,
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
            deliverable_spec=deliverable_spec,
            steering_notes=steering_notes if step_num == len(steps) else "",  # Only last step gets steering
            task_feedback=task_feedback if step_num == len(steps) else "",    # Only last step gets feedback
            task_mode=task_mode,
        )

        # Inject step-specific preamble — BEFORE gathered context for visibility
        step_preamble = f"\n\n## Process Step {step_num}/{len(steps)}: {step_name.title()}\n"
        step_preamble += f"Your role in this process: {step_instruction}\n"

        # ADR-151: Determine prior step type for diff-aware handoff
        prior_step_name = steps[step_idx - 1]["step"] if step_idx > 0 else ""
        is_after_context_update = prior_step_name == "update-context"

        if step_outputs:
            prior_output = step_outputs[-1]
            if is_after_context_update:
                # ADR-151: Diff-aware handoff — prior step was update-context
                step_preamble += (
                    f"\n## Context Update Changelog (from prior step)\n"
                    f"The following describes what changed in the workspace context this cycle. "
                    f"Your primary context is the accumulated workspace context (injected above). "
                    f"Use this changelog to emphasize WHAT'S NEW in your output — the reader "
                    f"has seen prior reports. Lead with changes, not stable context.\n\n"
                    f"{prior_output[:8000]}\n"
                )
            else:
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
        draft, usage, pending_renders, _tools_used, _tool_rounds = await _generate(
            client, user_id, agent, system_prompt, user_message, scope,
        )

        # Strip assessment
        draft, _ = _extract_agent_reflection(draft)

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

    # Save final output to task workspace (mode-aware, ADR-149)
    if task_mode == "goal":
        # Goal: archive prior, write to latest/
        prior_latest = await tw.read("outputs/latest/output.md")
        if prior_latest:
            await tw.write(
                f"outputs/{date_folder}/output.md", prior_latest,
                summary="Archive prior version before revision",
                tags=["output", "archive"],
            )
        await tw.write(
            "outputs/latest/output.md", final_draft,
            summary=f"Goal revision v{next_version}",
            tags=["output", "latest"],
        )
        task_output_folder = date_folder
    else:
        # Recurring + reactive: new dated folder + overwrite latest/
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
        try:
            await tw.write(
                "outputs/latest/output.md", final_draft,
                summary=f"Latest output v{next_version}",
                tags=["output", "latest"],
            )
        except Exception:
            pass

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

    # Post-run domain scan + awareness update (ADR-154)
    pipeline_duration = (datetime.now(timezone.utc) - started_at).total_seconds()
    await _post_run_domain_scan(
        client, user_id, task_slug, task_info, final_draft, next_version, started_at,
        duration_s=pipeline_duration,
    )

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
        schedule = (task_row.data[0]["schedule"] if task_row.data else None) or None
        next_run = calculate_next_run_at(schedule, last_run_at=now) if schedule else None
        update_data = {
            "last_run_at": now.isoformat(),
            "next_run_at": next_run.isoformat() if next_run else None,
        }
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

# Scope → max tool rounds (steady state)
_TOOL_ROUNDS = {
    "platform": 5,
    "cross_platform": 8,
    "knowledge": 8,
    "research": 10,
    "autonomous": 12,
}

# ADR-154: Bootstrap multiplier — first run is deep research (journalist model).
# Phase affects depth (tool rounds), not frequency (schedule).
_BOOTSTRAP_ROUND_MULTIPLIER = 2  # 2x rounds during bootstrap


async def _generate(
    client,
    user_id: str,
    agent: dict,
    system_prompt: str,
    user_message: str,
    scope: str,
    task_phase: str = "steady",
) -> tuple[str, dict, list, list, int]:
    """Run the headless generation loop.

    Returns (draft, usage, pending_renders, tools_used, tool_rounds).
    ADR-154: tools_used and tool_rounds returned for awareness.md.
    """
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import get_tools_for_mode, create_headless_executor
    from services.agent_pipeline import validate_output
    from services.agent_execution import (
        SONNET_MODEL, _is_narration, _strip_tool_narration,
    )

    role = agent.get("role", "custom")
    max_tool_rounds = _TOOL_ROUNDS.get(scope, 5)

    # ADR-154: Bootstrap phase gets 2x tool rounds — deep research on first run
    if task_phase == "bootstrap":
        max_tool_rounds = max_tool_rounds * _BOOTSTRAP_ROUND_MULTIPLIER

    # Agents with asset capabilities (chart, mermaid, image) need more rounds
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

    return draft, usage, pending_renders, tools_used, round_num


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
    from services.workspace import AgentWorkspace, get_agent_slug
    from services.agent_framework import has_asset_capabilities, has_capability
    from services.agent_execution import (
        get_next_run_number, create_version_record, update_version_for_delivery,
        SONNET_MODEL, _extract_agent_reflection,
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
        draft, usage, pending_renders, _tools_used, _tool_rounds = await _generate(
            client, user_id, agent, system_prompt, user_message, scope,
        )

        draft, agent_reflection = _extract_agent_reflection(draft)

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

        # ADR-151: Signal routing for taskless agent runs
        try:
            from services.workspace import UserMemory
            um = UserMemory(client, user_id)
            from datetime import datetime, timezone
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            signal_path = f"context/signals/{date_str}.md"
            existing = await um.read(signal_path) or f"# Signals — {date_str}\n"
            signal_entry = (
                f"\n## {title} v{next_version} ({datetime.now(timezone.utc).strftime('%H:%M UTC')})\n"
                f"- Agent: {agent_slug}\n"
                f"- Output: {len(draft)} chars\n"
            )
            await um.write(signal_path, existing + signal_entry,
                          summary=f"Signal from {agent_slug} v{next_version}")
        except Exception as e:
            logger.warning(f"[AGENT_RUN] Context signal routing failed: {e}")

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
