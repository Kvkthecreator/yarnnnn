"""
RuntimeDispatch Primitive — ADR-118 Phase B

Allows headless agents to dispatch rendering during generation.
Calls yarnnn-render service, uploads result to Supabase Storage,
writes workspace_files row with content_url.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")


RUNTIME_DISPATCH_TOOL = {
    "name": "RuntimeDispatch",
    "description": """Render structured output as a downloadable file (PDF, PPTX, XLSX, chart image).

Use this when the user's agent should produce a binary artifact alongside or instead of text.
The rendered file is uploaded to storage and delivered as an email attachment or download link.

type: document|presentation|spreadsheet|chart
output_format: pdf|docx|pptx|xlsx|png|svg

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
                "enum": ["document", "presentation", "spreadsheet", "chart"],
                "description": "Handler type",
            },
            "input": {
                "type": "object",
                "description": "Handler-specific input spec (see examples in description)",
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

    1. Calls yarnnn-render service via HTTP
    2. On success, writes workspace_files row with content_url
    3. Returns URL to agent for inclusion in output
    """
    render_type = input.get("type", "")
    render_input = input.get("input", {})
    output_format = input.get("output_format", "")
    filename = input.get("filename", "")

    if not render_type or not output_format:
        return {"success": False, "error": "missing_params", "message": "type and output_format are required"}

    # Call render service
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{RENDER_SERVICE_URL}/render",
                json={
                    "type": render_type,
                    "input": render_input,
                    "output_format": output_format,
                    "filename": filename or None,
                },
            )
            resp.raise_for_status()
            result = resp.json()
    except httpx.TimeoutException:
        return {"success": False, "error": "render_timeout", "message": "Render service timed out (60s)"}
    except Exception as e:
        logger.error(f"[RUNTIME_DISPATCH] Render service call failed: {e}")
        return {"success": False, "error": "render_failed", "message": str(e)}

    if not result.get("success"):
        return {"success": False, "error": "render_error", "message": result.get("error", "Unknown render error")}

    output_url = result.get("output_url", "")
    content_type = result.get("content_type", "")
    size_bytes = result.get("size_bytes", 0)

    # Write workspace_files row with content_url
    try:
        agent_slug = getattr(auth, "agent_slug", None) or "unknown"
        title = render_input.get("title", render_type)
        safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in title).strip().replace(" ", "-")[:50]
        ws_path = f"/agents/{agent_slug}/outputs/{safe_title}.{output_format}"

        auth.client.table("workspace_files").upsert(
            {
                "user_id": auth.user_id,
                "path": ws_path,
                "content": f"Rendered {render_type}: {title}",
                "content_type": content_type,
                "content_url": output_url,
                "metadata": {
                    "render_type": render_type,
                    "output_format": output_format,
                    "size_bytes": size_bytes,
                },
                "tags": ["rendered", render_type, output_format],
            },
            on_conflict="user_id,path",
        ).execute()
    except Exception as e:
        logger.warning(f"[RUNTIME_DISPATCH] Workspace write failed (non-fatal): {e}")

    return {
        "success": True,
        "output_url": output_url,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "message": f"Rendered {render_type} as {output_format} ({size_bytes} bytes). URL: {output_url}",
    }
