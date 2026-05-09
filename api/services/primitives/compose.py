"""
Compose Primitive — ADR-262 D4.

Compose is a callable primitive that takes a task's section partials +
manifest and produces composed HTML via the existing render engine
(`render/compose.py`, ADR-148/170/177/213 mechanical pipeline).

Per ADR-262 D4:
  - Compose survives as deterministic rendering; not collapsed.
  - Compose is callable as a primitive (this module) for explicit
    mid-session composition during the Reviewer's loop.
  - Compose is also opt-out structural default — when a session writes
    section partials matching the deliverable convention, the framework
    auto-runs Compose unless the recurrence's `options.skip_compose: true`.
    The auto-trigger is implemented at the session-close boundary (separate
    from this primitive's callable surface). Both share the same engine.

This primitive wraps `services.compose.task_html.compose_task_output_html`
which already encapsulates the substrate-read + render-service-POST flow.

Available in BOTH chat and headless modes (Reviewer may direct composition
during its real-time loop; specialists may compose interim drafts).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


COMPOSE_TOOL = {
    "name": "Compose",
    "description": """Compose section partials + manifest into final HTML output (ADR-262 D4).

Wraps the deterministic render-engine pipeline. Reads from the task's
output folder (`/tasks/{task_slug}/outputs/{date_folder}/`):
  - sys_manifest.json (composition manifest with section-kind metadata)
  - sections/*.md (section partials)
  - assets/* (charts, images, mermaid diagrams)

Posts to render service /compose. Returns the composed HTML.

Caller responsibility: write the result to the appropriate output path
(typically `/workspace/reports/{task_slug}/{date}/output.html` per
CONVENTIONS topology). The primitive returns the HTML string — it does
not write substrate itself.

Examples:
  Compose(task_slug="weekly-market-conditions")
  Compose(task_slug="weekly-market-conditions", date_folder="2026-05-08")
  Compose(task_slug="portfolio-review", surface_type="dashboard", title="Q2 Review")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_slug": {
                "type": "string",
                "description": "The task slug whose output folder to compose. Required.",
            },
            "date_folder": {
                "type": "string",
                "description": "Date folder name (e.g. '2026-05-08'). Defaults to 'latest' (the most recent firing).",
                "default": "latest",
            },
            "surface_type": {
                "type": "string",
                "enum": ["report", "dashboard", "deck"],
                "description": "Composition surface — report (default vertical doc), dashboard (live-bound panes), deck (slide-shaped). Falls back to sys_manifest.json::surface_type.",
            },
            "title": {
                "type": "string",
                "description": "Optional human-readable title. Falls back to sys_manifest.json::title.",
            },
        },
        "required": ["task_slug"],
    },
}


async def handle_compose(auth: Any, input: dict) -> dict:
    """Execute one Compose call.

    Returns:
        {
          "ok": True/False,
          "html": "<html string>",        # only on success
          "error": "...",                   # only on failure
        }
    """
    from services.compose.task_html import compose_task_output_html

    task_slug = (input or {}).get("task_slug") or ""
    if not task_slug:
        return {"ok": False, "error": "task_slug is required"}

    date_folder = (input or {}).get("date_folder") or "latest"
    surface_type = (input or {}).get("surface_type") or None
    title = (input or {}).get("title") or None

    user_id = getattr(auth, "user_id", None)
    if not user_id:
        return {"ok": False, "error": "authentication required"}
    client = getattr(auth, "client", None)
    if client is None:
        return {"ok": False, "error": "client unavailable"}

    try:
        html = await compose_task_output_html(
            client,
            user_id,
            task_slug=task_slug,
            date_folder=date_folder,
            surface_type=surface_type,
            title=title,
        )
    except Exception as exc:
        logger.exception("[COMPOSE] failed task=%s date=%s: %s", task_slug, date_folder, exc)
        return {"ok": False, "error": f"compose failed: {exc}"}

    if html is None:
        return {
            "ok": False,
            "error": (
                f"no substrate at /tasks/{task_slug}/outputs/{date_folder}/ — "
                "task may not have run yet, or the substrate's natural-home path "
                "is non-conventional and falls outside the auto-resolver."
            ),
        }

    return {
        "ok": True,
        "html": html,
        "task_slug": task_slug,
        "date_folder": date_folder,
        "html_bytes": len(html),
    }
