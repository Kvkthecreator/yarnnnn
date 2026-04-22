"""
RepurposeOutput Primitive — ADR-148 Phase 4

Adapts an existing task output for a different format or channel.

Two execution paths:
- Mechanical (backend): PDF, XLSX, DOCX, markdown — format conversion
- Editorial (agent): LinkedIn, slides, summary, Medium — content adaptation

The user sees one action ("Repurpose"). The system routes based on target.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Targets and their execution path
MECHANICAL_TARGETS = {"pdf", "xlsx", "docx", "markdown"}
EDITORIAL_TARGETS = {"linkedin", "slides", "summary", "medium", "twitter"}

# Editorial repurpose instructions per target
EDITORIAL_INSTRUCTIONS = {
    "linkedin": (
        "Adapt this output as a LinkedIn post. Write a compelling hook (first 2 lines are visible before 'see more'). "
        "150-250 words max. Professional but engaging tone. End with a question or call-to-action to drive engagement. "
        "Remove internal-only details. Reference data points that demonstrate expertise. No hashtag spam — 3 max."
    ),
    "slides": (
        "Restructure this output as a slide deck. Each ## heading becomes a slide. "
        "Slide titles are assertions ('Revenue grew 23%'), not topics ('Revenue'). "
        "3 bullets max per slide. Include a visual every other slide (mermaid diagram or data table). "
        "Title slide → Key Insight → 3-5 Content Slides → Summary → Next Steps. "
        "Total: 8-12 slides."
    ),
    "summary": (
        "Condense this output into a 3-paragraph executive summary. "
        "Paragraph 1: The headline finding (what happened and why it matters). "
        "Paragraph 2: Key evidence (2-3 data points that support the headline). "
        "Paragraph 3: Recommended action (what to do about it). "
        "Total: 150-250 words. No bullet points — flowing prose."
    ),
    "medium": (
        "Adapt this output as a Medium article for public consumption. "
        "Add a compelling headline (not the internal task title). "
        "Write an engaging introduction that hooks a general professional audience. "
        "Preserve data and analysis but remove company-specific internal context. "
        "Add a concluding 'takeaway' section. Target: 1000-1500 words."
    ),
    "twitter": (
        "Distill this output into a Twitter/X thread of 5-7 tweets. "
        "Tweet 1: The hook (the most surprising or important finding). "
        "Tweets 2-5: One key insight per tweet with a data point. "
        "Final tweet: The takeaway + what to watch for. "
        "Each tweet under 280 characters. Use thread numbering (1/7, 2/7...)."
    ),
}


REPURPOSE_OUTPUT_TOOL = {
    "name": "RepurposeOutput",
    "description": """Adapt a task output for a different format or channel.

Mechanical targets (instant): pdf, xlsx, docx, markdown
Editorial targets (agent adapts): linkedin, slides, summary, medium, twitter

Examples:
- RepurposeOutput(task_slug="competitive-intel-brief-demo", target="pdf")
- RepurposeOutput(task_slug="competitive-intel-brief-demo", target="linkedin")
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_slug": {
                "type": "string",
                "description": "The task whose output to repurpose",
            },
            "target": {
                "type": "string",
                "description": "Target format or channel: pdf, xlsx, docx, markdown, linkedin, slides, summary, medium, twitter",
                "enum": list(MECHANICAL_TARGETS | EDITORIAL_TARGETS),
            },
            "output_date": {
                "type": "string",
                "description": "Optional: specific output date folder (default: latest)",
            },
        },
        "required": ["task_slug", "target"],
    },
}


async def handle_repurpose_output(auth: Any, input: dict) -> dict:
    """Handle RepurposeOutput primitive."""
    task_slug = input.get("task_slug", "").strip()
    target = input.get("target", "").strip().lower()
    output_date = input.get("output_date", "").strip()

    if not task_slug:
        return {"success": False, "error": "missing_task_slug", "message": "task_slug is required"}
    if target not in (MECHANICAL_TARGETS | EDITORIAL_TARGETS):
        return {
            "success": False, "error": "invalid_target",
            "message": f"Unknown target '{target}'. Valid: {', '.join(sorted(MECHANICAL_TARGETS | EDITORIAL_TARGETS))}",
        }

    user_id = auth.user_id
    client = auth.client

    # Find the output
    from services.task_workspace import TaskWorkspace
    tw = TaskWorkspace(client, user_id, task_slug)

    if not output_date:
        # Find latest output
        result = (
            client.table("workspace_files")
            .select("path")
            .eq("user_id", user_id)
            .like("path", f"/tasks/{task_slug}/outputs/%/output.md")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return {"success": False, "error": "no_output", "message": f"No output found for task '{task_slug}'"}
        path = result.data[0]["path"]
        # Extract date folder: /tasks/{slug}/outputs/{date}/output.md
        parts = path.split("/")
        output_date = parts[-2]

    # Read the output
    output_md = await tw.read(f"outputs/{output_date}/output.md")
    output_html = await tw.read(f"outputs/{output_date}/output.html")

    if not output_md:
        return {"success": False, "error": "output_not_found", "message": f"No output.md at outputs/{output_date}/"}

    # Route: mechanical or editorial
    if target in MECHANICAL_TARGETS:
        return await _mechanical_repurpose(auth, task_slug, output_date, output_md, output_html, target)
    else:
        return await _editorial_repurpose(auth, task_slug, output_date, output_md, target)


async def _mechanical_repurpose(auth, task_slug, output_date, output_md, output_html, target):
    """Mechanical repurpose — format conversion via render service or direct."""
    import httpx

    RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")
    RENDER_SERVICE_SECRET = os.environ.get("RENDER_SERVICE_SECRET", "")

    if target == "markdown":
        return {
            "success": True,
            "target": "markdown",
            "content": output_md,
            "message": "Markdown content ready for download.",
        }

    # PDF / DOCX
    if target in ("pdf", "docx"):
        render_input = {"title": task_slug.replace("-", " ").title()}
        if output_html:
            render_input["html"] = output_html
        else:
            render_input["markdown"] = output_md

        try:
            headers = {"Content-Type": "application/json"}
            if RENDER_SERVICE_SECRET:
                headers["X-Render-Secret"] = RENDER_SERVICE_SECRET

            async with httpx.AsyncClient(timeout=60.0) as http:
                resp = await http.post(
                    f"{RENDER_SERVICE_URL}/render",
                    json={"type": "pdf", "input": render_input, "output_format": target, "user_id": auth.user_id},
                    headers=headers,
                )
                if resp.status_code != 200:
                    return {"success": False, "error": "render_failed", "message": f"Render service: {resp.status_code}"}
                data = resp.json()
                return {
                    "success": True,
                    "target": target,
                    "url": data.get("output_url"),
                    "message": f"{target.upper()} exported successfully.",
                }
        except Exception as e:
            return {"success": False, "error": "render_error", "message": str(e)}

    # XLSX — extract tables
    if target == "xlsx":
        import re
        tables = []
        table_pattern = re.compile(r'(\|[^\n]+\|\n\|[-:\| ]+\|\n(?:\|[^\n]+\|\n?)+)', re.MULTILINE)
        for match in table_pattern.finditer(output_md):
            lines = match.group(1).strip().split("\n")
            if len(lines) < 3:
                continue
            headers = [h.strip() for h in lines[0].strip("|").split("|")]
            rows = [[c.strip().strip("*") for c in line.strip("|").split("|")] for line in lines[2:]]
            tables.append({"name": f"Table {len(tables)+1}", "headers": headers, "rows": rows})

        if not tables:
            return {"success": False, "error": "no_tables", "message": "No tables found in output to export as XLSX"}

        try:
            headers = {"Content-Type": "application/json"}
            if RENDER_SERVICE_SECRET:
                headers["X-Render-Secret"] = RENDER_SERVICE_SECRET

            async with httpx.AsyncClient(timeout=60.0) as http:
                resp = await http.post(
                    f"{RENDER_SERVICE_URL}/render",
                    json={"type": "xlsx", "input": {"title": task_slug, "sheets": tables}, "output_format": "xlsx", "user_id": auth.user_id},
                    headers=headers,
                )
                if resp.status_code != 200:
                    return {"success": False, "error": "render_failed", "message": f"Render service: {resp.status_code}"}
                data = resp.json()
                return {"success": True, "target": "xlsx", "url": data.get("output_url"), "message": "XLSX exported."}
        except Exception as e:
            return {"success": False, "error": "render_error", "message": str(e)}

    return {"success": False, "error": "unsupported", "message": f"Mechanical target '{target}' not implemented"}


async def _editorial_repurpose(auth, task_slug, output_date, output_md, target):
    """Editorial repurpose — agent adapts content for target channel/format."""
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import get_tools_for_mode, create_headless_executor
    from services.task_workspace import TaskWorkspace

    user_id = auth.user_id
    client = auth.client
    instruction = EDITORIAL_INSTRUCTIONS.get(target, "Adapt this output for the requested format.")

    # Resolve which agent to use — the agent that produced the output
    tw = TaskWorkspace(client, user_id, task_slug)
    task_md = await tw.read("TASK.md")
    agent_slug = None
    if task_md:
        import re
        # Try to find agent from TASK.md process section
        match = re.search(r'\*\*(\w[\w-]+)\*\*\)', task_md)
        if not match:
            # Fallback: find agent slug from task_types process.
            # ADR-205: lazy-ensure infrastructure agents before lookup.
            type_match = re.search(r'\*\*Type:\*\*\s*(\S+)', task_md)
            if type_match:
                from services.task_types import get_task_type
                from services.agent_creation import classify_role, ensure_infrastructure_agent
                type_def = get_task_type(type_match.group(1))
                if type_def and type_def.get("process"):
                    agent_type = type_def["process"][-1]["agent_type"]  # last step agent
                    if classify_role(agent_type) != "user_authored":
                        ensured = await ensure_infrastructure_agent(client, user_id, agent_type)
                        if ensured:
                            agent_slug = ensured.get("slug")
                    if not agent_slug:
                        roster = client.table("agents").select("slug, role").eq("user_id", user_id).execute()
                        for a in (roster.data or []):
                            if a.get("role") == agent_type:
                                agent_slug = a["slug"]
                                break

    if not agent_slug:
        # Default to Writer for editorial repurpose (ADR-176).
        from services.agent_creation import ensure_infrastructure_agent
        ensured = await ensure_infrastructure_agent(client, user_id, "writer")
        if ensured:
            agent_slug = ensured.get("slug")

    if not agent_slug:
        return {"success": False, "error": "no_agent", "message": "No agent available for editorial repurpose"}

    # Build prompt
    system_prompt = (
        f"You are repurposing an existing output for a different format/channel.\n\n"
        f"## Target: {target}\n\n"
        f"## Instructions\n{instruction}\n\n"
        f"Produce ONLY the repurposed content — no meta-commentary, no preamble."
    )

    user_message = f"## Original Output\n\n{output_md}"

    # Generate via simple completion (no tools needed for repurpose).
    # Haiku is sufficient — editorial repurpose is format transformation
    # (restructure, condense, reframe), not open-ended reasoning.
    from services.anthropic import chat_completion
    _REPURPOSE_MODEL = "claude-haiku-4-5-20251001"

    response = await chat_completion(
        messages=[{"role": "user", "content": user_message}],
        system=system_prompt,
        model=_REPURPOSE_MODEL,
    )

    repurposed_content = response.text.strip() if response.text else ""
    if not repurposed_content:
        return {"success": False, "error": "empty_output", "message": "Agent produced no repurposed content"}

    # Compose the repurposed content
    # ADR-170: surface_type vocabulary (deck = discrete full-screen frames)
    surface = "deck" if target == "slides" else "report"
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'render'))
        from compose import compose_html
        repurposed_html = compose_html(repurposed_content, title=f"{task_slug} — {target}", surface_type=surface)
    except Exception:
        repurposed_html = None

    # Save to workspace under repurpose/ folder
    repurpose_folder = f"outputs/{output_date}/repurpose"
    await tw.write(f"{repurpose_folder}/{target}.md", repurposed_content, summary=f"Repurposed: {target}")
    if repurposed_html:
        await tw.write(f"{repurpose_folder}/{target}.html", repurposed_html, summary=f"Composed repurpose: {target}")

    logger.info(f"[REPURPOSE] {task_slug} → {target}: {len(repurposed_content)} chars")

    return {
        "success": True,
        "target": target,
        "content": repurposed_content,
        "html": repurposed_html is not None,
        "words": len(repurposed_content.split()),
        "message": f"Repurposed for {target} ({len(repurposed_content.split())} words).",
        "ui_action": {
            "type": "SHOW_REPURPOSE",
            "data": {"task_slug": task_slug, "target": target, "output_date": output_date},
        },
    }
