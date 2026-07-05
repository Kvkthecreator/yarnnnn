"""
Authored-piece routes — read + consumption-pull composition surface over
`/workspace/operation/authored/{slug}/` (ADR-333 + ADR-283).

An authored piece is the operator's canonical prose (`content.md`) plus
on-demand composition substrate (`{date}/sections/` + manifests) the Reviewer
wrote while authoring structure natively (ADR-333 D5). The composed HTML is a
**lazy projection** — pulled here when a surface consumes the piece, never
persisted as a file (ADR-333 D1/D6). This route is the authored-deliverable
analog of the report pull surfaces in `routes/recurrences.py`.

The HTTP surface lives at `/api/authored/*`. It is a KERNEL route — authored
pieces are a kernel deliverable kind (conventions in `services/conventions.py`),
not bundle-specific program data. Per ADR-333 D8 only the author program needs
it now; the surface generalizes to any non-report deliverable on demand.

Endpoints:
- GET /authored/{slug}                  piece detail (canonical prose + status)
- GET /authored/{slug}/render           composed HTML (lazy pull; latest composition)
- GET /authored/{slug}/render/{date}    composed HTML for a specific composition
- GET /authored/{slug}/export           export composed piece (PDF/XLSX/etc.)

Auth boundary: derives user from `auth.user_id`. No cross-user reads.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.conventions import authored_content_path, authored_root
from services.workspace_context import substrate_scope_filter
from services.supabase import UserClient
from services.workspace import UserMemory

logger = logging.getLogger(__name__)

router = APIRouter()


def _strip_ws_prefix(p: str) -> str:
    return p[len("/workspace/"):] if p.startswith("/workspace/") else p


class AuthoredPiece(BaseModel):
    slug: str
    content: Optional[str] = None  # canonical prose (content.md)
    profile: Optional[str] = None  # profile.md (status, voice ref, audit state)
    latest_composition: Optional[str] = None  # date folder of newest sections/, if any


def _latest_composition_date(client, user_id: str, slug: str) -> Optional[str]:
    """Newest dated composition folder (by sys_manifest update), or None."""
    root = authored_root(slug)
    rows = (
        client.table("workspace_files")
        .select("path, updated_at")
        .eq(*substrate_scope_filter(user_id))
        .like("path", f"{root}/%/sys_manifest.json")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        return None
    rel = rows[0]["path"][len(root) + 1:]
    return rel.split("/")[0]


@router.get("/{slug}")
async def get_authored_piece(slug: str, auth: UserClient) -> AuthoredPiece:
    """Piece detail — canonical prose + profile + latest composition pointer."""
    um = UserMemory(auth.client, auth.user_id)
    content = await um.read(_strip_ws_prefix(authored_content_path(slug)))
    profile = await um.read(_strip_ws_prefix(f"{authored_root(slug)}/profile.md"))
    latest = _latest_composition_date(auth.client, auth.user_id, slug)
    return AuthoredPiece(
        slug=slug,
        content=content,
        profile=profile,
        latest_composition=latest,
    )


@router.get("/{slug}/render")
async def render_authored_piece(slug: str, auth: UserClient):
    """Composed HTML for the latest composition — pulled lazily (ADR-333 D6).

    The render fires here, on consumption, against the render service; the
    content-addressed cache (ADR-213) memoizes repeated pulls of unchanged
    substrate. Returns 404 when no composition substrate exists yet (the
    Reviewer hasn't authored kind-tagged sections for this piece).
    """
    date_folder = _latest_composition_date(auth.client, auth.user_id, slug)
    if not date_folder:
        raise HTTPException(status_code=404, detail="No composition substrate for this piece")

    from services.compose.task_html import compose_task_output_html
    html = await compose_task_output_html(
        auth.client, auth.user_id, slug, date_folder, artifact_kind="authored",
    )
    if not html:
        raise HTTPException(status_code=404, detail="No composed output for this piece")
    return StreamingResponse(iter([html.encode("utf-8")]), media_type="text/html")


@router.get("/{slug}/render/{date_folder}")
async def render_authored_piece_by_date(slug: str, date_folder: str, auth: UserClient):
    """Composed HTML for a specific composition date (lazy pull)."""
    from services.compose.task_html import compose_task_output_html
    html = await compose_task_output_html(
        auth.client, auth.user_id, slug, date_folder, artifact_kind="authored",
    )
    if not html:
        raise HTTPException(status_code=404, detail="No composed output for this composition")
    return StreamingResponse(iter([html.encode("utf-8")]), media_type="text/html")


@router.get("/{slug}/export")
async def export_authored_piece(
    slug: str,
    format: str,
    auth: UserClient,
    date_folder: Optional[str] = None,
):
    """Export the composed piece as PDF/XLSX/etc. via the render service.

    Mirrors the report export path (`routes/recurrences.py::export_recurrence_output`)
    but pulls authored-kind composition. The HTML is composed lazily here,
    then handed to the render `/export` endpoint."""
    if not date_folder:
        date_folder = _latest_composition_date(auth.client, auth.user_id, slug)
        if not date_folder:
            raise HTTPException(status_code=404, detail="No composition substrate to export")

    from services.compose.task_html import compose_task_output_html
    html_content = await compose_task_output_html(
        auth.client, auth.user_id, slug, date_folder, artifact_kind="authored",
    )
    if not html_content:
        raise HTTPException(status_code=404, detail="No composed output to export")

    render_url = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")
    render_secret = os.environ.get("RENDER_SERVICE_SECRET", "")
    headers = {"X-Render-Secret": render_secret} if render_secret else {}

    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(
            f"{render_url}/export",
            json={"html": html_content, "format": format, "user_id": auth.user_id},
            headers=headers,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Render export failed: {resp.status_code}")
    return StreamingResponse(
        iter([resp.content]),
        media_type=resp.headers.get("content-type", "application/octet-stream"),
    )
