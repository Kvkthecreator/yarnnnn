"""Shared-artifact wedge routes — ADR-437 D4.

The cockpit origin of a share (the "Share" affordance) + the one accept surface
(`/s/{token}`). The MCP `share` verb (the second origin, ADR-437 D4.1) lands in
the MCP server as an additive follow-on; both origins mint the same share row
via `services.workspace_shares` and land here.

Kept OFF `routes/workspace.py` deliberately (that file is heavily co-edited);
a share is its own bounded concern with its own router.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from services.machine_projection import file_type_of, project_for_machine
from services.supabase import UserClient, principal_reaches_workspace, resolve_owner_workspace_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Models ───────────────────────────────────────────────────────────────────

class ShareCreateRequest(BaseModel):
    # The shared artifact (a workspace_files path). None = a bare workspace
    # share (invite-shaped, no artifact context).
    artifact_path: Optional[str] = None
    label: Optional[str] = None
    ttl_days: Optional[int] = None  # None = a durable link (never expires)
    # ADR-465 D3 — the grant shape: "member" (broad, default) | "viewer"
    # (birth-narrowed read-only grant; "just look at this" never over-grants).
    role: str = "member"


class ShareSummary(BaseModel):
    id: str
    artifact_path: Optional[str] = None
    label: Optional[str] = None
    role: str
    status: str
    created_at: str = ""
    expires_at: Optional[str] = None
    share_link: Optional[str] = None


class ShareListResponse(BaseModel):
    shares: list[ShareSummary]


class WalkEntry(BaseModel):
    """One step of the public attribution walk (ADR-513 D2) — metadata only:
    who, when, what-message. Never revision content, never diffs."""
    authored_by: Optional[str] = None
    when: Optional[str] = None
    change: Optional[str] = None


class SharePreviewResponse(BaseModel):
    workspace_name: Optional[str] = None
    artifact_path: Optional[str] = None
    label: Optional[str] = None
    role: str
    status: str
    # ADR-513: the public projection — the shared artifact + its walk. The
    # response model IS the boundary (D2): additions here are additions to
    # what an anonymous reader can see; keep deliberate.
    artifact_name: Optional[str] = None
    artifact_kind: Optional[str] = None      # "html" | "text"
    artifact_content: Optional[str] = None   # current content only, capped
    truncated: bool = False
    walk: list[WalkEntry] = []
    # ADR-530 D1/D3 — the file's MODEL-CONSUMABLE projection (DP34), beside the
    # raw content the browser renders in its locked iframe. Not a widening of
    # the ADR-513 D2 boundary: this is the same artifact, in the form a machine
    # can read. `artifact_note` carries the honest marker when a format has no
    # registered strategy yet (DP34's anti-silent-drop clause) — never a wall of
    # raw bytes, which is what this boundary used to emit.
    artifact_text: Optional[str] = None
    artifact_note: Optional[str] = None


class ShareAcceptResponse(BaseModel):
    success: bool
    workspace_id: str
    workspace_name: Optional[str] = None
    artifact_path: Optional[str] = None
    role: str


def _acting_workspace(auth: UserClient) -> str:
    """The workspace the caller is acting in (X-Workspace-Id → owner fallback).

    A member may share within a commons they hold a grant to; the owner shares
    their own. `principal_reaches_workspace` is the authority check.
    """
    ws = auth.workspace_id or resolve_owner_workspace_id(auth.user_id)
    if not ws:
        raise HTTPException(status_code=400, detail="No workspace resolved for this principal")
    if not principal_reaches_workspace(auth.user_id, ws):
        raise HTTPException(status_code=403, detail="You do not have a grant to this workspace")
    return ws


# ── Cockpit origin: create / list / revoke ───────────────────────────────────

@router.post("/workspace/shares", response_model=ShareSummary)
async def create_workspace_share(body: ShareCreateRequest, auth: UserClient) -> ShareSummary:
    """Mint a share link for an artifact (ADR-437 D4 — the cockpit origin).

    Minting a grant is governance (ADR-517 D3): write-holders mint, viewers
    never, and the workspace dial (`share_mint_policy`) can tighten to
    owner-only. The gate is `assert_may_mint_share` — the same one the MCP
    origin calls (species-blind, ADR-405).
    """
    from services.deep_links import app_url
    from services.workspace_shares import ShareError, assert_may_mint_share, create_share

    workspace_id = _acting_workspace(auth)
    try:
        assert_may_mint_share(auth.user_id, workspace_id)
        share = create_share(
            workspace_id=workspace_id,
            shared_by=auth.user_id,
            artifact_path=body.artifact_path,
            label=body.label,
            ttl_days=body.ttl_days,
            role=body.role,
        )
    except ShareError as e:
        raise HTTPException(status_code=403 if e.code == "mint_forbidden" else 400, detail=str(e))

    return ShareSummary(
        id=share["id"],
        artifact_path=share.get("artifact_path"),
        label=share.get("label"),
        role=share["role"],
        status=share["status"],
        created_at=str(share.get("created_at") or ""),
        expires_at=share.get("expires_at"),
        share_link=f"{app_url()}/s/{share['token']}",
    )


@router.get("/workspace/shares", response_model=ShareListResponse)
async def list_workspace_shares(auth: UserClient) -> ShareListResponse:
    from services.workspace_shares import list_shares

    workspace_id = _acting_workspace(auth)
    return ShareListResponse(shares=[
        ShareSummary(
            id=r["id"], artifact_path=r.get("artifact_path"), label=r.get("label"),
            role=r["role"], status=r["status"],
            created_at=str(r.get("created_at") or ""),
            expires_at=r.get("expires_at"),
        )
        for r in list_shares(workspace_id)
    ])


@router.post("/workspace/shares/{share_id}/revoke")
async def revoke_workspace_share(share_id: str, auth: UserClient) -> dict:
    """ADR-517 D4 — the owner revokes any link; the minter revokes their own."""
    from services.workspace_shares import ShareError, revoke_share

    workspace_id = _acting_workspace(auth)
    try:
        revoked = revoke_share(workspace_id, share_id, revoked_by=auth.user_id)
    except ShareError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not revoked:
        raise HTTPException(status_code=404, detail="No active share with that id")
    return {"success": True, "id": share_id}


# ── The one accept surface: preview / accept ──────────────────────────────────

#: ADR-513: the public content cap — generous for prose; a capability link is a
#: view, not an export lane (the git export is the egress door, ADR-510).
PUBLIC_CONTENT_CAP = 400_000
#: The walk is a demonstration, not an archive — the full chain is members-only.
PUBLIC_WALK_CAP = 12

#: ADR-513 D4 — a capability link is neither cacheable by intermediaries nor
#: indexable, on EVERY status. One constant so an added `raise` cannot silently
#: ship a bare error response (the 2026-08-03 live defect).
_CAPABILITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
}


def _render_markdown(out: SharePreviewResponse) -> str:
    """The ADR-513 D2 projection, serialized as markdown (ADR-529 D2).

    THE SAME PROJECTION, a different representation — this function receives the
    already-built `SharePreviewResponse` and never reads the database, so the
    two representations cannot drift and markdown can never carry a field JSON
    does not. That is precisely why ADR-529 amends ADR-513 **D3** (rendering)
    and not **D2** (the boundary): no new information crosses.

    The reader this exists for is a machine that cannot execute JavaScript — an
    LLM handed the link, a fetcher, a script. It gets prose, not a JSON blob it
    has to be taught to parse.
    """
    lines: list[str] = []
    name = out.artifact_name or out.label
    if name:
        lines.append(f"# {name}")
        lines.append("")
    ws = out.workspace_name or "a shared workspace"
    reach = "read-only" if out.role == "viewer" else "full access on joining"
    lines.append(f"*Shared from **{ws}** on yarnnn — {reach}.*")
    lines.append("")

    # ADR-530 D1: the machine lane serves the PROJECTION, never the raw
    # container. It previously fenced HTML verbatim, so an LLM asking for
    # markdown received `<!doctype html><style>:root{--ink:#1a1a1a}…` — safe,
    # and completely useless for the thing it was asked to do.
    if out.artifact_text:
        lines.append(out.artifact_text)
        lines.append("")
        if out.truncated:
            lines.append("*(Truncated — join the workspace to read the full document.)*")
            lines.append("")
    elif out.artifact_note:
        # DP34: legibly marked, never dropped and never fabricated.
        lines.append(f"*{out.artifact_note}*")
        lines.append("")

    if out.walk:
        lines.append("---")
        lines.append("")
        lines.append("**Every change, signed**")
        lines.append("")
        for w in out.walk:
            when = (w.when or "")[:10]
            who = w.authored_by or "unknown"
            change = f" — {w.change}" if w.change else ""
            lines.append(f"- `{when}` **{who}**{change}")
        lines.append("")

    return "\n".join(lines)


@router.get("/s/{token}.txt", response_class=PlainTextResponse)
async def preview_share_text(token: str, request: Request) -> PlainTextResponse:
    """The share link's MACHINE ADDRESS (ADR-530 D4).

    An ALIAS, not a second resource: same token, same capability, same
    revocation, same lifecycle — and a `Link: rel="canonical"` back to
    `/s/{token}` so no crawler, cache or agent treats it as separate content.

    Why it exists beside content negotiation, which is the native mechanism:
    **agents in the wild paste, they do not negotiate.** The live receipt
    (2026-08-06) is that ChatGPT fetched a share link with `Accept: text/html`
    and got what a browser gets. A representation nothing asks for is a
    representation that does not exist, so the `Accept:` lane keeps being the
    protocol and this is the pasteable affordance over it — the `llms.txt`
    lesson: guessable, linkable, handable to an agent on purpose.

    `.txt` and not `.md` because the derive-registry promises DP34's *text*
    strategy — a PDF's projection is not markdown, and naming it `.md` would
    claim a guarantee we do not make.

    MUST stay declared ABOVE `/s/{token}` — FastAPI matches in declaration
    order and the bare token pattern would otherwise swallow the suffix.
    """
    from services.deep_links import app_url

    result = await preview_share(token=token, response=Response(), request=request, format="md")
    body = result.body.decode("utf-8") if isinstance(result, PlainTextResponse) else ""
    headers = dict(_CAPABILITY_HEADERS)
    # The alias points home: one resource, one identity (ADR-530 D4).
    headers["Link"] = f'<{app_url()}/s/{token}>; rel="canonical"'
    return PlainTextResponse(body, media_type="text/plain; charset=utf-8", headers=headers)


@router.get("/s/{token}", response_model=SharePreviewResponse)
async def preview_share(
    token: str,
    response: Response,
    request: Request,
    format: Optional[str] = None,
) -> SharePreviewResponse | PlainTextResponse:
    """The PUBLIC artifact view (ADR-513) — no auth: the token is the capability.

    A stranger clicking a share link sees the artifact + its attribution walk
    (who · when · what-message) before any sign-up ask — the moat demonstrated
    on contact (ADR-437 D4, made literal). Accepting (becoming a principal)
    stays auth-gated on the POST below. Lifecycle is enforced here too (D4):
    a revoked or expired link goes dark — this closes the pre-existing hole
    where inactive shares still previewed.

    The anonymous reader is NOT a principal: service-client reads scoped by
    the share's own workspace, projected through the response model (D2 — the
    narrow boundary: no shared_by, no workspace_id, no revision content/diffs,
    no second file).

    ADR-529 D2 — ONE URL, TWO REPRESENTATIONS. A reader that cannot execute
    JavaScript (`Accept: text/markdown`, or `?format=md`) gets this same
    projection as markdown instead of JSON. Same token, same capability, same
    revocation, same fields — the serialization differs, the boundary does not.
    Deliberately NOT a second link: a sibling URL or an "AI link" would mint a
    second thing to revoke, explain, and drift.
    """
    from datetime import datetime, timezone

    from services.supabase import get_service_client
    from services.workspace_shares import get_share_by_token

    # Capability links must be neither cached by intermediaries nor indexed;
    # revocation must be the end of them (ADR-513 D4).
    #
    # Setting them on `response` covers the 200 ONLY. `raise HTTPException`
    # discards the injected Response — main.py's app-level handler builds a fresh
    # JSONResponse carrying just `exc.headers` — so every error exit must carry
    # them explicitly (found live 2026-08-03: the 404 and the 410 both shipped
    # bare). The REVOKED response is precisely the one that most needs no-store:
    # without it an intermediary may keep serving a cached copy of the
    # pre-revocation 200, and revocation stops being the end of the link.
    response.headers.update(_CAPABILITY_HEADERS)

    share = get_share_by_token(token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share link not found",
                            headers=dict(_CAPABILITY_HEADERS))
    if share["status"] != "active":
        raise HTTPException(status_code=410, detail=f"This share link is {share['status']}",
                            headers=dict(_CAPABILITY_HEADERS))
    expires = share.get("expires_at")
    if expires and datetime.fromisoformat(str(expires).replace("Z", "+00:00")) < datetime.now(timezone.utc):
        get_service_client().table("workspace_shares").update({"status": "expired"}).eq(
            "id", share["id"]
        ).execute()
        raise HTTPException(status_code=410, detail="This share link has expired",
                            headers=dict(_CAPABILITY_HEADERS))

    out = SharePreviewResponse(
        workspace_name=share.get("workspace_name"),
        artifact_path=share.get("artifact_path"),
        label=share.get("label"),
        role=share["role"],
        status=share["status"],
    )

    # ADR-517 D5: artifact_path is stored in the canonical absolute spelling
    # (normalized at create_share, backfilled by migration 234) — no reader-side
    # compensation.
    abs_path = share.get("artifact_path")
    if abs_path:
        svc = get_service_client()
        rows = (
            svc.table("workspace_files")
            .select("path, content")
            .eq("workspace_id", share["workspace_id"])
            .eq("path", abs_path)
            .limit(1)
            .execute()
        ).data or []
        if rows:
            content = rows[0].get("content") or ""
            out.truncated = len(content) > PUBLIC_CONTENT_CAP
            leaf = abs_path.rsplit("/", 1)[-1]
            out.artifact_name = share.get("label") or leaf

            # ADR-530 D1 — the kind comes from the ONE derive-registry dispatcher,
            # never from a call-site suffix test. The line this replaces was
            #     "html" if leaf.endswith((".html",".htm")) else "text"
            # which asserts everything not-HTML IS text, so a shared PDF/XLSX/ZIP
            # had its RAW BYTES emitted into a <pre> — DP34's diagnostic test
            # failing verbatim.
            projection = project_for_machine(path=abs_path, content=content)
            out.artifact_kind = "html" if file_type_of(abs_path) in ("html", "htm") else "text"

            if projection.is_readable:
                out.artifact_text = (projection.text or "")[:PUBLIC_CONTENT_CAP]
                # The browser renders the raw form (locked iframe for html —
                # ADR-513 D3, untouched); a machine reads `artifact_text`.
                out.artifact_content = content[:PUBLIC_CONTENT_CAP]
            else:
                # DP34's anti-silent-drop clause: a format with no strategy is a
                # KNOWN GAP, said out loud. No raw bytes cross for a container
                # nothing can read.
                out.artifact_note = projection.note
                out.artifact_content = None
                out.truncated = False
            walk_rows = (
                svc.table("workspace_file_versions")
                .select("authored_by, created_at, message")
                .eq("workspace_id", share["workspace_id"])
                .eq("path", abs_path)
                .order("created_at", desc=True)
                .limit(PUBLIC_WALK_CAP)
                .execute()
            ).data or []
            out.walk = [
                WalkEntry(
                    authored_by=r.get("authored_by"),
                    when=r.get("created_at"),
                    change=r.get("message"),
                )
                for r in walk_rows
            ]

    # ADR-529 D2 — negotiate the REPRESENTATION, having already built the one
    # projection. Explicit `?format=md` wins; otherwise honor an Accept header
    # that asks for markdown/plain over JSON. A browser sends `text/html,…`
    # and is unaffected; `*/*` (curl's default) stays JSON so no existing
    # machine caller changes shape underneath itself.
    accept = (request.headers.get("accept") or "").lower()
    wants_md = (format or "").lower() in {"md", "markdown", "text"} or (
        format is None
        and ("text/markdown" in accept or "text/plain" in accept)
        and "application/json" not in accept
    )
    if wants_md:
        return PlainTextResponse(
            _render_markdown(out),
            media_type="text/markdown; charset=utf-8",
            headers=dict(_CAPABILITY_HEADERS),
        )
    return out


@router.post("/s/{token}/accept", response_model=ShareAcceptResponse)
async def accept_workspace_share(token: str, auth: UserClient) -> ShareAcceptResponse:
    """Bind the acceptor to the commons via a share link (ADR-437 D4.2).

    Link-based — any authenticated principal may accept (the Figma default).
    Mints a BROAD member grant; the FE binds via X-Workspace-Id on success.
    """
    from services.workspace_shares import ShareError, accept_share

    try:
        result = accept_share(token=token, user_id=auth.user_id)
    except ShareError as e:
        status = {"not_found": 404, "expired": 410, "not_active": 409}.get(e.code, 400)
        raise HTTPException(status_code=status, detail=str(e))
    return ShareAcceptResponse(
        success=True,
        workspace_id=result["workspace_id"],
        workspace_name=result.get("workspace_name"),
        artifact_path=result.get("artifact_path"),
        role=result["role"],
    )
