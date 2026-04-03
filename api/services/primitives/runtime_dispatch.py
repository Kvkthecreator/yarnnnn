"""
RuntimeDispatch Primitive — ADR-118

Allows headless agents to dispatch skill execution on the output gateway.
Calls yarnnn-output-gateway service, uploads result to Supabase Storage,
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
    "description": """Invoke an output gateway skill to produce a visual or media asset.

Use this when the agent should produce a visual artifact alongside text output.
The rendered file is uploaded to storage and embedded in the output.

Available skills:
- chart: Data spec → PNG or SVG data visualization (via matplotlib)
- mermaid: Mermaid syntax → PNG or SVG diagram (via mermaid-cli)
- image: Image processing → PNG (via pillow)
- video: Scene spec → MP4 short-form video clip (via Remotion, max 30s)
- fetch-asset: Fetch external visual asset (favicon, logo) → PNG (ADR-157)

Construct the input spec according to the skill's SKILL.md instructions (injected into your context when authorized).

Examples:
- RuntimeDispatch(type="chart", input={"chart_type": "bar", "title": "Growth", "labels": ["Jan", "Feb"], "datasets": [{"label": "Users", "data": [100, 200]}]}, output_format="png")
- RuntimeDispatch(type="mermaid", input={"diagram": "graph TD; A-->B; B-->C"}, output_format="svg")
- RuntimeDispatch(type="video", input={"title": "Metrics", "scenes": [{"type": "metric", "label": "Users", "value": "12K", "duration": 5}], "duration_seconds": 15}, output_format="mp4")
- RuntimeDispatch(type="fetch-asset", input={"url": "anthropic.com", "asset_type": "favicon", "size": 128}, output_format="png")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "description": "Skill type to invoke (chart, mermaid, image, video, fetch-asset). See SKILL.md docs in your context.",
            },
            "input": {
                "type": "object",
                "description": "Skill-specific input spec (see SKILL.md instructions in your context)",
            },
            "output_format": {
                "type": "string",
                "description": "Desired output format: png, svg, mp4",
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
    2. Calls yarnnn-output-gateway via HTTP (with auth + user_id)
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

    # Check work credits before dispatching
    from services.platform_limits import check_credits
    credits_ok, credits_used, credits_limit = check_credits(auth.client, auth.user_id)
    if not credits_ok:
        return {
            "success": False,
            "error": "credits_exceeded",
            "message": f"Monthly work credits exhausted ({credits_used}/{credits_limit}). Upgrade for more capacity.",
        }

    # Call output gateway with auth + user_id
    headers = {}
    if RENDER_SERVICE_SECRET:
        headers["X-Render-Secret"] = RENDER_SERVICE_SECRET
    # Video renders need extended timeout (up to 180s for Remotion)
    request_timeout = 180.0 if skill_type == "video" else 60.0
    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
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
        return {"success": False, "error": "render_timeout", "message": f"Output gateway timed out ({request_timeout:.0f}s)"}
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

    # ADR-157: fetch-asset writes to caller-specified workspace_path (context domain)
    # Other skills write to agent outputs
    workspace_path_override = skill_input.get("workspace_path")
    if workspace_path_override:
        ws_path = workspace_path_override
    else:
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

    # Record work credits for render
    from services.platform_limits import record_credits
    record_credits(auth.client, auth.user_id, "render", metadata={"skill_type": skill_type, "output_format": output_format})

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
