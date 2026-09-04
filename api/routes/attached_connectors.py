"""Attached connectors — the directory, the attach seam, the aperture
(ADR-635). Mounted at /api/connectors.

    GET  /connectors/directory?q=        search the consumed directory
    GET  /connectors/categories          the seed's category vocabulary
    POST /connectors/attach              {url, title?, key?, category?,
                                          header_name?, header_value?,
                                          redirect_to?} → {slug, attached,
                                          authorization_url}
    GET  /connectors/attach/callback     the OAuth return (public; the signed
                                          state carries the member)
    GET  /connectors/{slug}              the row's public view (tools + aperture)
    PUT  /connectors/{slug}/aperture     {aperture: {tool: "direct"|"propose"}}
    POST /connectors/{slug}/refresh      re-list the server's tools

Disconnect rides the existing DELETE /api/integrations/{provider} with the
`mcp:{slug}` key — one lifecycle verb for every connection (ADR-494).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from services.supabase import UserClient, get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()


class AttachRequest(BaseModel):
    url: str
    title: Optional[str] = None
    key: Optional[str] = None
    category: Optional[str] = None
    header_name: Optional[str] = None
    header_value: Optional[str] = None
    # ADR-635 — optional, for a server with no dynamic registration where the
    # member registered yarnnn as an app themselves. Absent, the attach is
    # attempted with an unregistered client and the provider gets to answer.
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_to: Optional[str] = None


class ApertureRequest(BaseModel):
    aperture: dict[str, str]


@router.get("/connectors/directory")
async def directory(q: str = Query("", max_length=120), limit: int = Query(30, ge=1, le=50)) -> dict:
    from services.connector_directory import search

    return {"query": q, "results": search(q, limit=limit)}


@router.get("/connectors/categories")
async def category_vocabulary() -> dict:
    from services.connector_directory import categories

    return {"categories": categories()}


@router.post("/connectors/attach")
async def attach(req: AttachRequest, auth: UserClient) -> dict:
    from services import attached_connectors as ac
    from services.connector_directory import seed_entry_for_url

    seed = seed_entry_for_url(req.url)
    try:
        return await ac.begin_attach(
            auth, req.url,
            title=req.title or (seed or {}).get("title"),
            slug=req.key or (seed or {}).get("key"),
            category=req.category or (seed or {}).get("category"),
            header_name=req.header_name, header_value=req.header_value,
            client_id=req.client_id, client_secret=req.client_secret,
            redirect_to=req.redirect_to,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ATTACH] begin failed for %s: %s", req.url, exc)
        raise HTTPException(status_code=502, detail=f"could not reach the server: {exc}")


@router.get("/connectors/attach/callback")
async def attach_callback(
    code: Optional[str] = Query(None),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
) -> RedirectResponse:
    """The server sends the member back here. No session: the signed state
    names the member, and the exchange runs on the service client — the same
    posture as the integrations callback (ADR-531 outcomes on the redirect)."""
    from integrations.core.oauth import OAuthStateError, get_frontend_redirect_url
    from services import attached_connectors as ac

    provider = "connector"
    try:
        from integrations.core.oauth import validate_oauth_state

        _, platform, redirect_to = validate_oauth_state(state)
        provider = platform
    except OAuthStateError as exc:
        return RedirectResponse(url=get_frontend_redirect_url(
            False, provider, str(exc), error_reason=exc.args[0] if exc.args else "malformed"))
    if error or not code:
        return RedirectResponse(url=get_frontend_redirect_url(
            False, provider, error_description or error or "no code",
            error_reason="provider_denied"))
    try:
        done = await ac.complete_attach(get_service_client(), code, state)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ATTACH] callback failed: %s", exc)
        return RedirectResponse(url=get_frontend_redirect_url(
            False, provider, str(exc)[:200], error_reason="unexpected"))
    back = done.get("redirect_to") or "/settings?settings.pane=connectors"
    sep = "&" if "?" in back else "?"
    return RedirectResponse(url=get_frontend_redirect_url(
        True, ac.platform_key(done["slug"]), redirect_to=f"{back}{sep}settings.connector={ac.platform_key(done['slug'])}"))


@router.get("/connectors/{slug}")
async def get_attached(slug: str, auth: UserClient) -> dict:
    from services import attached_connectors as ac

    row = ac.load_row(auth.client, auth.user_id, slug)
    if not row:
        raise HTTPException(status_code=404, detail=f"not attached: {slug}")
    return ac.public_view(row)


@router.put("/connectors/{slug}/aperture")
async def put_aperture(slug: str, req: ApertureRequest, auth: UserClient) -> dict:
    from services import attached_connectors as ac

    try:
        aperture = ac.set_aperture(auth, slug, req.aperture)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    row = ac.load_row(auth.client, auth.user_id, slug)
    return {"aperture": aperture, "connector": ac.public_view(row) if row else None}


@router.post("/connectors/{slug}/refresh")
async def refresh_attached(slug: str, auth: UserClient) -> dict:
    from services import attached_connectors as ac

    try:
        tools = await ac.refresh_tools(auth, slug)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"could not list tools: {exc}")
    row = ac.load_row(auth.client, auth.user_id, slug)
    return {"tools": len(tools), "connector": ac.public_view(row) if row else None}
