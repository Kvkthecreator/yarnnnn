"""
Task HTML Composition — ADR-213.

Single path for composing a task's output folder into HTML on demand.
Reads substrate (section partials + sys_manifest.json + manifest.json) from
the task workspace, POSTs to the render service `/compose`, returns HTML.

Callers:
  - api/routes/tasks.py: GET /tasks/{slug}/outputs/{date}/render
  - api/services/delivery.py: email body composition
  - api/services/primitives/repurpose.py: format conversion

The render service is responsible for content-addressed caching (ADR-213),
so repeated calls with unchanged substrate cost ~10ms (storage fetch) vs.
200-1500ms (fresh compose with matplotlib chart rendering).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


async def compose_task_output_html(
    client,
    user_id: str,
    task_slug: str,
    date_folder: str = "latest",
    surface_type: Optional[str] = None,
    title: Optional[str] = None,
) -> Optional[str]:
    """Compose a task output folder into HTML on demand.

    Reads section partials and manifest from
    `/tasks/{task_slug}/outputs/{date_folder}/`, posts to render service
    `/compose`, returns the composed HTML string.

    Returns None if no substrate exists (task never ran) or compose failed.
    Caller decides how to handle None (404, fallback, etc.).
    """
    # ADR-231 Phase 3.6.b: read natural-home substrate via UserMemory.
    # DELIVERABLE shape outputs land at /workspace/reports/{slug}/{date}/.
    # Resolve the substrate-root via the declaration walker, then read
    # output.md / sys_manifest.json / sections/ from there.
    from services.workspace import UserMemory
    from services.recurrence_paths import resolve_paths_for_slug

    paths = resolve_paths_for_slug(client, user_id, task_slug)
    if paths is None:
        return None  # No declaration for this slug
    # output_folder template carries {date} placeholder; substitute the
    # date_folder argument so we read the specific dated firing.
    if not paths.output_folder:
        return None  # Non-deliverable shapes have no output folder
    folder_abs = paths.output_folder.replace("{date}", date_folder)

    um = UserMemory(client, user_id)

    def _strip_ws(p: str) -> str:
        return p[len("/workspace/"):] if p.startswith("/workspace/") else p

    sys_manifest_raw = await um.read(_strip_ws(f"{folder_abs}/sys_manifest.json"))
    if not sys_manifest_raw:
        return None

    try:
        sys_manifest = json.loads(sys_manifest_raw)
    except (ValueError, json.JSONDecodeError):
        logger.warning(f"[COMPOSE] Invalid sys_manifest.json for {task_slug}/{date_folder}")
        return None

    resolved_surface = surface_type or sys_manifest.get("surface_type") or "report"
    resolved_title = (
        title
        or sys_manifest.get("title")
        or task_slug.replace("-", " ").title()
    )

    raw_sections = sys_manifest.get("sections") or {}
    sections_payload: list[dict] = []
    fallback_markdown_parts: list[str] = []

    for sec_slug, sec_meta in raw_sections.items():
        sec_content = await um.read(_strip_ws(f"{folder_abs}/sections/{sec_slug}.md"))
        if not sec_content:
            continue
        sections_payload.append({
            "kind": sec_meta.get("kind", "narrative"),
            "title": sec_meta.get("title", sec_slug.replace("-", " ").title()),
            "content": sec_content,
        })
        fallback_markdown_parts.append(f"## {sec_meta.get('title', sec_slug)}\n\n{sec_content}")

    fallback_markdown = ""
    if not sections_payload:
        fallback_markdown = await um.read(_strip_ws(f"{folder_abs}/output.md")) or ""
        if not fallback_markdown:
            return None
    else:
        fallback_markdown = "\n\n".join(fallback_markdown_parts)

    assets: list[dict] = []
    manifest_raw = await um.read(_strip_ws(f"{folder_abs}/manifest.json"))
    if manifest_raw:
        try:
            manifest = json.loads(manifest_raw)
            for f in manifest.get("files", []):
                url = f.get("content_url") or f.get("output_url")
                path = f.get("path", "")
                if url and path and f.get("role") != "primary":
                    ref = path.split("/")[-1] if "/" in path else path
                    assets.append({"ref": ref, "url": url})
        except (ValueError, json.JSONDecodeError):
            pass

    render_url = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")
    render_secret = os.environ.get("RENDER_SERVICE_SECRET", "")
    headers = {"X-Render-Secret": render_secret} if render_secret else {}

    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(
                f"{render_url}/compose",
                json={
                    "sections": sections_payload,
                    "markdown": fallback_markdown,
                    "title": resolved_title,
                    "surface_type": resolved_surface,
                    "assets": assets,
                    "user_id": user_id,
                },
                headers=headers,
            )
            if resp.status_code != 200:
                logger.warning(
                    f"[COMPOSE] /compose HTTP {resp.status_code} for {task_slug}/{date_folder}"
                )
                return None
            data = resp.json()
            if data.get("success"):
                return data.get("html") or None
            logger.warning(f"[COMPOSE] /compose returned error: {data.get('error')}")
            return None
    except Exception as e:
        logger.warning(f"[COMPOSE] /compose request failed for {task_slug}/{date_folder}: {e}")
        return None
