"""
RuntimeDispatch Primitive — ADR-118

Allows headless agents to dispatch skill execution on the output gateway.
Calls yarnnn-render service, uploads result to Supabase Storage,
writes workspace_files row with content_url.

Workspace write is FATAL — if the workspace row fails, the entire call fails.
No orphaned binaries (ADR-118 Resolved Decision #3).

ADR-118 D.2: Sends shared secret + user_id, checks render limits before dispatch.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")
RENDER_SERVICE_SECRET = os.environ.get("RENDER_SERVICE_SECRET", "")


RUNTIME_DISPATCH_TOOL = {
    "name": "RuntimeDispatch",
    "description": """Invoke an output gateway skill to produce a downloadable file (PDF, PPTX, XLSX, chart image).

Use this when the agent should produce a binary artifact alongside text output.
The rendered file is uploaded to storage and delivered as an email attachment or download link.

Available skills:
- document: Markdown → PDF or DOCX (via pandoc)
- presentation: Slide spec → PPTX (via python-pptx)
- spreadsheet: Table spec → XLSX (via openpyxl)
- chart: Data spec → PNG or SVG (via matplotlib)

Construct the input spec according to the skill's SKILL.md instructions (injected into your context when authorized).

Examples:
- RuntimeDispatch(type="document", input={"markdown": "# Report\\n...", "title": "Q1 Report"}, output_format="pdf")
- RuntimeDispatch(type="presentation", input={"title": "Weekly Update", "slides": [{"title": "Highlights", "content": "..."}]}, output_format="pptx")
- RuntimeDispatch(type="spreadsheet", input={"title": "Metrics", "headers": ["Week", "Users"], "rows": [["W1", 100]]}, output_format="xlsx")
- RuntimeDispatch(type="chart", input={"chart_type": "bar", "title": "Growth", "labels": ["Jan", "Feb"], "datasets": [{"label": "Users", "data": [100, 200]}]}, output_format="png")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "description": "Skill type to invoke (e.g., document, presentation, spreadsheet, chart). See SKILL.md docs in your context for available types.",
            },
            "input": {
                "type": "object",
                "description": "Skill-specific input spec (see SKILL.md instructions in your context)",
            },
            "output_format": {
                "type": "string",
                "description": "Desired output format: pdf, docx, pptx, xlsx, png, svg",
            },
            "filename": {
                "type": "string",
                "description": "Optional filename (without extension)",
            },
        },
        "required": ["type", "input", "output_format"],
    },
}


async def handle_runtime_dispatch(auth: Any, input: dict) -> dict:
    """
    Handle RuntimeDispatch primitive.

    1. Checks render limit (ADR-118 D.2 — hard reject if exceeded)
    2. Calls yarnnn-render output gateway via HTTP (with auth + user_id)
    3. On success, writes workspace_files row with content_url (FATAL on failure)
    4. Records render usage
    5. Returns URL to agent for inclusion in output
    """
    skill_type = input.get("type", "")
    skill_input = input.get("input", {})
    output_format = input.get("output_format", "")
    filename = input.get("filename", "")

    if not skill_type or not output_format:
        return {"success": False, "error": "missing_params", "message": "type and output_format are required"}

    # ADR-118 D.2: Check render limit before dispatching
    from services.platform_limits import check_render_limit
    allowed, renders_used, render_limit = check_render_limit(auth.client, auth.user_id)
    if not allowed:
        return {
            "success": False,
            "error": "render_limit_exceeded",
            "message": f"Monthly render limit reached ({renders_used}/{render_limit}). Upgrade for more renders.",
        }

    # Call output gateway with auth + user_id
    headers = {}
    if RENDER_SERVICE_SECRET:
        headers["X-Render-Secret"] = RENDER_SERVICE_SECRET
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{RENDER_SERVICE_URL}/render",
                json={
                    "type": skill_type,
                    "input": skill_input,
                    "output_format": output_format,
                    "filename": filename or None,
                    "user_id": auth.user_id,
                },
                headers=headers,
            )
            resp.raise_for_status()
            result = resp.json()
    except httpx.TimeoutException:
        return {"success": False, "error": "render_timeout", "message": "Output gateway timed out (60s)"}
    except Exception as e:
        logger.error(f"[RUNTIME_DISPATCH] Output gateway call failed: {e}")
        return {"success": False, "error": "render_failed", "message": str(e)}

    if not result.get("success"):
        return {"success": False, "error": "render_error", "message": result.get("error", "Unknown render error")}

    output_url = result.get("output_url", "")
    content_type = result.get("content_type", "")
    size_bytes = result.get("size_bytes", 0)

    # Write workspace_files row with content_url — FATAL on failure (ADR-118 Resolved Decision #3)
    agent_slug = getattr(auth, "agent_slug", None) or "unknown"
    title = skill_input.get("title", skill_type)
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in title).strip().replace(" ", "-")[:50]
    ws_path = f"/agents/{agent_slug}/outputs/{safe_title}.{output_format}"

    try:
        auth.client.table("workspace_files").upsert(
            {
                "user_id": auth.user_id,
                "path": ws_path,
                "content": f"Rendered {skill_type}: {title}",
                "content_type": content_type,
                "content_url": output_url,
                "metadata": {
                    "skill_type": skill_type,
                    "output_format": output_format,
                    "size_bytes": size_bytes,
                },
                "tags": ["rendered", skill_type, output_format],
            },
            on_conflict="user_id,path",
        ).execute()
    except Exception as e:
        logger.error(f"[RUNTIME_DISPATCH] Workspace write FAILED (fatal): {e}")
        return {
            "success": False,
            "error": "workspace_write_failed",
            "message": f"Rendered file uploaded to storage but workspace metadata write failed: {e}. "
                       f"Output URL (for manual reference): {output_url}",
        }

    # ADR-118 D.2: Record render usage for tier limit tracking
    from services.platform_limits import record_render_usage
    record_render_usage(auth.client, auth.user_id, skill_type, output_format, size_bytes)

    # ADR-118 D.3: Accumulate rendered file metadata for save_output() manifest
    rendered_file_info = {
        "path": f"{safe_title}.{output_format}",
        "content_type": content_type,
        "content_url": output_url,
        "size_bytes": size_bytes,
        "skill_type": skill_type,
        "role": "rendered",
    }
    if hasattr(auth, "pending_renders"):
        auth.pending_renders.append(rendered_file_info)

    return {
        "success": True,
        "output_url": output_url,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "message": f"Rendered {skill_type} as {output_format} ({size_bytes} bytes). URL: {output_url}",
    }
