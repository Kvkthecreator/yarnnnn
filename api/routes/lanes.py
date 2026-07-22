"""Lane routes — ADR-411 (implements ADR-408 D6 chat lanes).

A lane is a member's model-pinned helper thread over the shared workspace:
- `GET  /api/lanes`                — enabled flag + model registry + the
                                     member's lanes in the acting workspace
- `POST /api/lanes`                — create a lane (name + model)
- `GET  /api/lanes/{id}/messages`  — lane history (user/assistant text)
- `POST /api/lanes/{id}/messages`  — one turn, STREAMING SSE (ADR-412 D2)
- `POST /api/lanes/{id}/archive`   — archive (the lane list hides it)

Scope: (workspace, principal) like every session post ADR-407 Phase 4 —
a lane is member-experience, never shared. The steward thread is not a
lane and never appears here (ADR-408 D6: no multi-chat at Altitude 1).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.supabase import UserClient
from services.workspace_context import effective_workspace_id

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_ACTIVE_LANES = 20     # UX bound, not policy (ADR-408 D6)
_MAX_NAME_LEN = 60
_HISTORY_WINDOW = 20       # messages sent to the model per turn
_MAX_MESSAGE_LEN = 32_000
# Phase-A chassis (ADR-457 D6 as amended): a lane created without a name gets
# this placeholder and is auto-named from the first message's head.
_DEFAULT_LANE_NAME = "New chat"


class CreateLaneRequest(BaseModel):
    # Optional since Phase A: absent/blank → _DEFAULT_LANE_NAME + auto-name on
    # the first turn (conversation hygiene — the ChatGPT-bar naming behavior).
    name: Optional[str] = None
    # ADR-460 D4: `agent` is the member-facing choice (a name, not an engine);
    # `model` is the engine. Pass EITHER — an agent resolves to its model
    # server-side and BOTH land on the lane. `model` stays optional-but-live
    # because the Studio/derive paths bind a model directly and never pick a
    # character (a bound lane's job is the artifact, not the colleague).
    agent: Optional[str] = None
    model: Optional[str] = None
    # ADR-440 D3 — the Studio binding: a workspace path this lane authors.
    # A lane with a binding is a Studio lane; its turns carry the authoring
    # posture + token profile. Optional; plain chat lanes never set it.
    artifact_path: Optional[str] = None
    # ADR-450 D3 — the derive binding (the "Learn from" verb): a kernel recipe
    # slug + the workspace source path this lane derives from. Same lane_meta
    # mechanism as the Studio binding; turns compose the recipe section.
    derive_recipe: Optional[str] = None
    derive_source: Optional[str] = None


class LaneAttachment(BaseModel):
    # Phase-A attachments: a raw upload this turn references. `path` is the
    # workspace raw path the upload route returned; `kind` decides consumption
    # (image → vision content part via signed URL; file → the model reads the
    # text projection with ReadFile).
    path: str
    kind: str  # "image" | "file"
    name: Optional[str] = None


class LaneTurnRequest(BaseModel):
    content: str
    # Phase-A turn controls: edit-and-resend. When set, the transcript tail is
    # truncated from this USER message (inclusive) before the turn runs. The
    # no-rewind rule (three-axes discourse §3): truncation is transcript-only —
    # substrate writes from discarded turns stand on the ledger; undoing them
    # is its own revert-as-write act (ADR-406).
    replace_from_message_id: Optional[str] = None
    # Phase-A attachments (v1 scope: this turn only — history stays text, so
    # a later turn or a regenerate does not re-see the image bytes).
    attachments: Optional[list[LaneAttachment]] = None


class LanePatchRequest(BaseModel):
    # Phase-A conversation hygiene: rename + pin (lane_meta fields).
    # (`pinned` here = sorts-first in the list. NOT the Agent binding — see the
    # note below, which uses "bound" for that to keep the two words apart.)
    name: Optional[str] = None
    pinned: Optional[bool] = None
    # ⚠️ `agent` is deliberately ABSENT and must stay absent (2026-07-16).
    # A lane's Agent is chosen at creation and never changes: it is WHO this
    # conversation has been with, and every turn already on the transcript was
    # theirs. Re-pointing a lane mid-thread would retroactively misattribute a
    # history that is on the ledger (the ADR-406 no-rewind rule, one object
    # over) — you start a new conversation with someone else instead.
    #
    # This is also what "Studio's lane is pinned to Designer" MEANS in code:
    # `StudioSurface` creates with `agent: 'designer'` and no door exists to
    # change it. The pin is the absence of this field, not a lock on top of one.
    # A future session adding `agent` here unpins Studio without touching
    # Studio — `test_agent_registry.py` gates it.


def _acting_workspace(auth: UserClient) -> Optional[str]:
    return effective_workspace_id(auth.user_id)


def _lane_row_to_dict(row: dict) -> dict:
    lane_meta = (row.get("context_metadata") or {}).get("lane") or {}
    return {
        "id": row["id"],
        "name": lane_meta.get("name") or "Lane",
        "model": lane_meta.get("model") or "",
        # ADR-460 D4 — WHO this lane talks to. None for every pre-registry lane
        # and every Studio/derive lane: the FE falls back to the model label,
        # which is honest (that IS what those lanes are) rather than guessed.
        "agent": lane_meta.get("agent"),
        # Phase-A hygiene: pinned lanes sort first in the workbench list.
        "pinned": bool(lane_meta.get("pinned")),
        # ADR-440 D3 — the Studio binding (None for plain chat lanes).
        "artifact_path": lane_meta.get("artifact_path"),
        # ADR-450 D3 — the derive binding (None for plain chat lanes).
        "derive_recipe": lane_meta.get("derive_recipe"),
        "derive_source": lane_meta.get("derive_source"),
        "status": row.get("status"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        # Session legibility (ADR-412 D2): the prose summary captured on
        # archive (chat_sessions.summary). Null for active lanes.
        "summary": row.get("summary"),
    }


def _get_lane(auth: UserClient, lane_id: str) -> dict:
    """Load one lane row, enforcing (workspace, principal) ownership."""
    res = (
        auth.client.table("chat_sessions")
        .select("id, user_id, workspace_id, status, context_metadata, created_at, updated_at")
        .eq("id", lane_id)
        .eq("session_type", "lane")
        .limit(1)
        .execute()
    )
    row = (res.data or [None])[0]
    if not row or row.get("user_id") != auth.user_id:
        raise HTTPException(status_code=404, detail="Lane not found")
    ws = _acting_workspace(auth)
    if ws and row.get("workspace_id") and row["workspace_id"] != ws:
        raise HTTPException(status_code=404, detail="Lane not found in this workspace")
    return row


@router.get("/lanes")
async def list_lanes(auth: UserClient, include_bound: bool = False) -> dict:
    """The lane list + capability envelope. `enabled` gates the FE strip —
    lanes exist only where the ADR-408 D4 router is live."""
    from services.lane_runner import LANE_MODELS
    from services.model_router import model_router_enabled

    enabled = model_router_enabled()
    lanes: list[dict] = []
    if enabled:
        q = (
            auth.client.table("chat_sessions")
            .select("id, user_id, workspace_id, status, context_metadata, created_at, updated_at, summary")
            .eq("user_id", auth.user_id)
            .eq("session_type", "lane")
            .eq("status", "active")
            .order("created_at")
        )
        ws = _acting_workspace(auth)
        if ws:
            q = q.eq("workspace_id", ws)
        rows = q.execute().data or []
        # The seam-contract's plank 3, RULED 2026-07-16: a BOUND lane leaves
        # the /chat list. /chat is Think; a lane bound to an artifact is
        # Make-work with a text interface, and it lives where the artifact
        # does (Studio opens it by artifact_path). Live receipt for why: all 7
        # active lanes were bound, so the Think surface was a list of six
        # deck.html/page.html rows and one actual conversation. Grouping them
        # under a header would be the seam leak wearing a hat.
        # `?include_bound=1` serves Studio's own reads unchanged.
        if not include_bound:
            rows = [
                r for r in rows
                if not ((r.get("context_metadata") or {}).get("lane") or {}).get("artifact_path")
            ]
        lanes = [_lane_row_to_dict(r) for r in rows]

    from services.derive_recipes import list_recipes

    from services.agents_registry import find_member_agents, list_agents

    return {
        "enabled": enabled,
        # ADR-460 D4 — the chooser: named colleagues, not a spec sheet. The
        # member picks WHO; the engine rides behind the name. The member's own
        # Agents (their `_agent.yaml` folders) come first — they named them.
        "agents": list_agents(find_member_agents(auth.client, auth.user_id)),
        # `models` STAYS: every LANE_MODELS row is still routable (the Studio +
        # derive paths bind a model directly, and the lane list's model filter
        # facet reads it). The registry changes what the CHOOSER asks, not what
        # the system can run.
        "models": [
            {"id": mid, "label": meta["label"], "vision": bool(meta.get("vision", True))}
            for mid, meta in LANE_MODELS.items()
        ],
        # ADR-450 D5: the Learn-from chooser payload — kernel recipes, served
        # on the capability envelope (no new endpoint, no FE duplication).
        "recipes": list_recipes(),
        "lanes": lanes,
    }


@router.post("/lanes")
async def create_lane(req: CreateLaneRequest, auth: UserClient) -> dict:
    from services.agents_registry import find_member_agents, resolve_agent
    from services.lane_runner import LANE_MODELS
    from services.model_router import model_router_enabled

    if not model_router_enabled():
        raise HTTPException(status_code=403, detail="Lanes are not enabled (router off)")

    # ADR-460 D4 — the member picks WHO, not which engine. An agent resolves to
    # its model here, server-side; the model stays authoritative on the lane
    # (spec §6: the slug is the face, the model is the fact, and the fact is
    # what actually ran — deriving it at turn time would let a registry edit
    # retroactively lie about a past lane's engine).
    agent_slug = (req.agent or "").strip()
    model = (req.model or "").strip()
    if agent_slug:
        # Member-first: their named colleagues, then the kernel set.
        agent = resolve_agent(agent_slug, find_member_agents(auth.client, auth.user_id))
        if not agent:
            # The ADR-450 precedent: an unknown recipe is a caller bug, not a lane.
            raise HTTPException(status_code=422, detail=f"Unknown agent: {agent_slug}")
        model = agent["model"]
    if not model:
        raise HTTPException(status_code=422, detail="agent or model is required")
    if model not in LANE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown lane model: {model}")
    # Phase-A hygiene: a nameless lane is fine — it auto-names on first turn.
    name = (req.name or "").strip()[:_MAX_NAME_LEN] or _DEFAULT_LANE_NAME

    ws = _acting_workspace(auth)
    artifact_path_req = (req.artifact_path or "").strip()
    # The cap counts CHAT lanes only — a bound (Studio) lane is not one of the
    # member's conversations, it is an artifact's authoring thread, and Studio
    # opens one PER ARTIFACT without asking. Counting them here was a live bug
    # (2026-07-16): 7 bound + 1 chat = 8 = the cap, so "New chat" 409'd while
    # the list showed ONE lane — the member is told to "archive one first" with
    # nothing visible to archive. The same ruling as the list itself (a bound
    # lane isn't in the Think surface, so it isn't Think's budget either); the
    # cap is a UX bound on the member's own conversations (ADR-408 D6), never a
    # ceiling on how many artifacts they may author.
    active = (
        auth.client.table("chat_sessions")
        .select("id, context_metadata")
        .eq("user_id", auth.user_id)
        .eq("session_type", "lane")
        .eq("status", "active")
    )
    if ws:
        active = active.eq("workspace_id", ws)
    chat_lanes = [
        r for r in (active.execute().data or [])
        if not ((r.get("context_metadata") or {}).get("lane") or {}).get("artifact_path")
    ]
    # A bound lane is exempt from the cap in BOTH directions: it does not count
    # against it, and creating one is never refused by it.
    if not artifact_path_req and len(chat_lanes) >= _MAX_ACTIVE_LANES:
        raise HTTPException(
            status_code=409,
            detail=f"Lane limit reached ({_MAX_ACTIVE_LANES}) — archive one first",
        )

    lane_meta: dict = {"name": name, "model": model}
    # ADR-460 D4 — the face, beside the fact. Absent on Studio/derive lanes and
    # on every lane created before this registry: they resolve by `model`
    # exactly as before and simply render an engine label. No backfill, no
    # guessing (the W0 lesson: an unclassifiable row says so).
    if agent_slug:
        lane_meta["agent"] = agent_slug
    artifact_path = artifact_path_req  # parsed once, above (the cap exempts it)
    if artifact_path:
        lane_meta["artifact_path"] = artifact_path

    # ADR-450 D3 — the derive binding: validated against the kernel registry
    # (an unknown recipe is a caller bug, not a lane), source normalized to
    # the absolute form the posture + citations use.
    derive_recipe = (req.derive_recipe or "").strip()
    derive_source = (req.derive_source or "").strip()
    if derive_recipe or derive_source:
        from services.derive_recipes import get_recipe

        if not (derive_recipe and derive_source):
            raise HTTPException(
                status_code=422,
                detail="derive_recipe and derive_source must be passed together",
            )
        if not get_recipe(derive_recipe):
            raise HTTPException(status_code=422, detail=f"Unknown derive recipe: {derive_recipe}")
        if not derive_source.startswith("/workspace/"):
            derive_source = "/workspace/" + derive_source.lstrip("/")
        lane_meta["derive_recipe"] = derive_recipe
        lane_meta["derive_source"] = derive_source

    row = {
        "user_id": auth.user_id,
        "session_type": "lane",
        "status": "active",
        "context_metadata": {"lane": lane_meta},
    }
    if ws:
        row["workspace_id"] = ws
    res = auth.client.table("chat_sessions").insert(row).execute()
    created = (res.data or [None])[0]
    if not created:
        raise HTTPException(status_code=500, detail="Lane creation failed")
    logger.info("[LANE] created lane=%s model=%s ws=%s", created["id"][:8], req.model, (ws or "-")[:8])
    return _lane_row_to_dict(created)


@router.get("/lanes/{lane_id}/messages")
async def lane_messages(lane_id: str, auth: UserClient) -> dict:
    _get_lane(auth, lane_id)
    res = (
        auth.client.table("session_messages")
        .select("id, role, content, metadata, created_at")
        .eq("session_id", lane_id)
        .order("sequence_number")
        .limit(200)
        .execute()
    )
    return {
        "messages": [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
                "metadata": r.get("metadata") or {},
            }
            for r in (res.data or [])
            if r.get("role") in ("user", "assistant")
        ]
    }


def _fetch_history(
    auth: UserClient, lane_id: str, *, before_sequence: Optional[int] = None
) -> list[dict]:
    """History window: user/assistant text only — tool traffic is per-turn
    working state, never persisted (the transcript is not shared memory,
    and it is not the tool ledger either; writes live in revisions)."""
    q = (
        auth.client.table("session_messages")
        .select("role, content, sequence_number")
        .eq("session_id", lane_id)
        .order("sequence_number", desc=True)
        .limit(_HISTORY_WINDOW)
    )
    if before_sequence is not None:
        q = q.lt("sequence_number", before_sequence)
    hist_res = q.execute()
    return [
        {"role": r["role"], "content": r["content"] or ""}
        for r in reversed(hist_res.data or [])
        if r.get("role") in ("user", "assistant") and (r.get("content") or "").strip()
    ]


def _delete_transcript_tail(auth: UserClient, lane_id: str, from_sequence: int) -> None:
    """Truncate the transcript from `from_sequence` (inclusive). Transcript
    only — the no-rewind rule: substrate writes from discarded turns stand on
    the ledger (the transcript is episodic; the ledger is truth)."""
    (
        auth.client.table("session_messages")
        .delete()
        .eq("session_id", lane_id)
        .gte("sequence_number", from_sequence)
        .execute()
    )


def _resolve_blob_storage_path(auth: UserClient, path: str) -> Optional[str]:
    """A raw upload's private-bucket key, from its stable content_url
    (`/api/documents/blob?storage_path=…`, ADR-395 Piece A)."""
    from urllib.parse import parse_qs, urlparse

    from services.workspace_context import substrate_scope_filter

    res = (
        auth.client.table("workspace_files")
        .select("content_url")
        .eq(*substrate_scope_filter(auth.user_id))
        .eq("path", path)
        .limit(1)
        .execute()
    )
    row = (res.data or [None])[0]
    url = (row or {}).get("content_url") or ""
    vals = parse_qs(urlparse(url).query).get("storage_path")
    return vals[0] if vals else None


def _mint_cas_url_for_path(auth: UserClient, path: str) -> Optional[str]:
    """Mint a serving URL for a CAS-backed binary file (ADR-427 Phase 3).

    Resolves the file's head revision → blob sha → the seam's minted, TTL'd
    signed URL (D4 — capability minted per-request, never stored). Returns
    None when the path has no binary head (the caller 404s)."""
    from services.storage_backend import get_storage_backend
    from services.supabase import get_service_client
    from services.workspace_context import substrate_scope_filter

    try:
        row = (
            auth.client.table("workspace_files")
            .select("head_version_id")
            .eq(*substrate_scope_filter(auth.user_id))
            .eq("path", path)
            .limit(1)
            .execute()
        ).data
        head_id = (row or [{}])[0].get("head_version_id")
        if not head_id:
            return None
        head = (
            auth.client.table("workspace_file_versions")
            .select("blob_sha")
            .eq("id", head_id)
            .limit(1)
            .execute()
        ).data
        if not head:
            return None
        return get_storage_backend(get_service_client()).mint_serving_url(
            head[0]["blob_sha"], expires_in=3600
        )
    except Exception as exc:  # noqa: BLE001 — the caller surfaces a 404
        logger.warning("[LANE] CAS mint failed for %s: %s", path, exc)
        return None


def _build_turn_message(
    auth: UserClient,
    content: str,
    attachments: list[LaneAttachment],
    model: str,
):
    """Phase-A attachments → the model-facing message.

    Images become OpenAI vision content parts (fresh signed URL — the raw
    stays in the private bucket, DP32-retained); files become a pointer note
    (the lane reads the text projection with its own ReadFile — the
    substrate-native move, no content injection). Returns
    (model_message, attachments_meta) — the persisted user row keeps the
    plain text + metadata, never the parts array.
    """
    from services.documents import (
        create_signed_url_for_storage_path,
        upload_projection_path,
    )
    from services.lane_runner import LANE_MODELS
    from services.supabase import get_service_client

    image_parts: list[dict] = []
    notes: list[str] = []
    meta: list[dict] = []
    for att in attachments:
        kind = "image" if att.kind == "image" else "file"
        meta.append({"path": att.path, "kind": kind, "name": att.name or att.path.split("/")[-1]})
        if kind == "image":
            if not LANE_MODELS.get(model, {}).get("vision", True):
                raise HTTPException(
                    status_code=422,
                    detail=f"{LANE_MODELS.get(model, {}).get('label', model)} cannot see images — pick a vision-capable lane",
                )
            # Legacy raw lane: content_url → documents-bucket signed URL.
            # ADR-427 Phase 3 lane: the image is a CAS binary revision — mint
            # the serving URL from the head blob through the storage seam.
            storage_path = _resolve_blob_storage_path(auth, att.path)
            signed = (
                create_signed_url_for_storage_path(get_service_client(), storage_path)
                if storage_path
                else _mint_cas_url_for_path(auth, att.path)
            )
            if not signed:
                raise HTTPException(status_code=404, detail=f"Attachment not found: {att.path}")
            image_parts.append({"type": "image_url", "image_url": {"url": signed}})
        else:
            notes.append(
                f"[Attached file: {att.path} — text projection at "
                f"{upload_projection_path(att.path)}; read it with ReadFile]"
            )

    model_text = content + ("\n\n" + "\n".join(notes) if notes else "")
    if image_parts:
        return [{"type": "text", "text": model_text}, *image_parts], meta
    return model_text, meta


def _maybe_autoname(auth: UserClient, lane: dict, content: str) -> Optional[str]:
    """Phase-A hygiene: name a default-named lane from its first message's
    head (mechanical, zero-LLM — a metered naming call is not worth a title).
    Returns the new name when renamed, else None."""
    meta_all = lane.get("context_metadata") or {}
    lane_meta = dict(meta_all.get("lane") or {})
    current = (lane_meta.get("name") or "").strip()
    if current and current != _DEFAULT_LANE_NAME:
        return None
    head = " ".join(content.split())[:48].strip()
    if not head:
        return None
    if len(head) == 48:
        head = head.rsplit(" ", 1)[0] if " " in head else head
    lane_meta["name"] = head
    try:
        auth.client.table("chat_sessions").update(
            {"context_metadata": {**meta_all, "lane": lane_meta}}
        ).eq("id", lane["id"]).execute()
    except Exception as exc:
        logger.warning("[LANE] auto-name failed (non-fatal): %s", exc)
        return None
    return head


def _turn_stream_response(
    auth: UserClient,
    lane: dict,
    content: str,
    *,
    persist_user: bool,
    history_before_sequence: Optional[int] = None,
    renamed: Optional[str] = None,
    # Phase-A attachments: what the MODEL sees this turn (content-parts list
    # when images ride along; defaults to `content`). The persisted user row
    # always keeps the plain text + attachments metadata.
    model_message=None,
    attachments_meta: Optional[list[dict]] = None,
) -> StreamingResponse:
    """The one streaming turn core — serves POST messages AND regenerate.

    SSE grammar mirrors the steward (`data: {json}\\n\\n`, frames keyed by
    their JSON discriminator):
      - {"text_delta": str}            — a streamed text fragment
      - {"tool": str}                  — a tool the turn called
      - {"artifact": {"path", "verb"}} — a WriteFile/EditFile landed; the FE
                                         opens the file inline (artifact card)
      - {"done": true, "rounds", "tools_called", "artifacts", "lane_name"?}
                                       — terminal (lane_name when auto-named)
      - {"error": str}                 — a fatal turn error

    The two-write invariant (ADR-219): user row persisted up front (the turn
    is real even if the provider errors); ONE assistant row at stream close
    from the accumulated text + tools_called + artifacts.

    STOP (Phase-A turn controls): the member aborting the stream cancels this
    generator (CancelledError/GeneratorExit). The partial reply persists with
    `stopped: true` so the reloaded transcript matches what the member saw.
    Round-boundary discipline lives in the runner (a started write completes,
    asyncio.shield); the no-rewind rule means a stopped transcript may omit a
    write that landed — the ledger is truth.

    `artifacts` is persisted on the assistant row's metadata so a RELOADED
    lane still renders its cards — the transcript stays private (ADR-411), but
    a POINTER to the shared file is exactly what the lane contract promises.
    """
    from services.lane_runner import lane_caller_identity, run_lane_turn_stream
    from services.narrative import write_narrative_entry

    lane_id = lane["id"]
    lane_meta = (lane.get("context_metadata") or {}).get("lane") or {}
    model = lane_meta.get("model") or ""

    history = _fetch_history(auth, lane_id, before_sequence=history_before_sequence)

    if persist_user:
        # Persist the member's message before the LLM call (the turn is real
        # even if the provider errors — same posture as the steward thread).
        write_narrative_entry(
            auth.client, lane_id,
            role="user",
            summary=content,
            pulse="addressed",
            authored_by="operator",
            extra_metadata=(
                {"attachments": attachments_meta} if attachments_meta else None
            ),
        )

    async def event_stream():
        def sse(obj: dict) -> str:
            return f"data: {json.dumps(obj)}\n\n"

        accumulated: list[str] = []
        tools_called: list[str] = []
        artifacts: list[str] = []
        rounds = 0
        errored: Optional[str] = None
        persisted = False

        def persist_reply(*, stopped: bool) -> None:
            """ONE assistant row at close — shared by the clean path and the
            abort path (idempotent; sync client, safe in cancel cleanup)."""
            nonlocal persisted
            if persisted:
                return
            reply = "".join(accumulated)
            # Nothing to record when the turn produced no text AND ended
            # abnormally (error/stop) — only the user row remains.
            if not reply and (errored or stopped):
                return
            persisted = True
            extra: dict = {
                "lane_model": model,
                "tools_called": tools_called,
                "artifacts": artifacts,
            }
            if stopped:
                extra["stopped"] = True
            write_narrative_entry(
                auth.client, lane_id,
                role="assistant",
                summary=reply or "[no reply]",
                pulse="addressed",
                authored_by=lane_caller_identity(auth.user_id, model),
                extra_metadata=extra,
            )
            try:
                auth.client.table("chat_sessions").update(
                    {"updated_at": "now()"}
                ).eq("id", lane_id).execute()
            except Exception:
                pass

        try:
            async for kind, payload in run_lane_turn_stream(
                auth,
                model=model,
                history=history,
                user_message=model_message if model_message is not None else content,
                member_label=getattr(auth, "email", None) or None,
                # ADR-440 D3 — a bound lane's turns carry the Studio posture.
                artifact_path=lane_meta.get("artifact_path"),
                # ADR-450 D3 — a derive-bound lane's turns carry the recipe.
                derive_recipe=lane_meta.get("derive_recipe"),
                derive_source=lane_meta.get("derive_source"),
                # ADR-460 D4 — WHO the member is talking to: the Agent's
                # posture composes at turn time from this slug.
                agent=lane_meta.get("agent"),
                # W0 / ADR-457 D8 — the falsifier join key: this turn's cost
                # row carries the session it served, so the surface that asked
                # (think / make / derive) is derivable at read time.
                session_id=lane_id,
            ):
                if kind == "delta":
                    accumulated.append(payload)
                    yield sse({"text_delta": payload})
                elif kind == "tool":
                    tools_called.append(payload["name"])
                    yield sse({"tool": payload["name"]})
                elif kind == "artifact":
                    artifacts.append(payload["path"])
                    yield sse({"artifact": payload})
                elif kind == "error":
                    errored = f"{payload.get('error')}: {payload.get('message')}"
                    yield sse({"error": errored})
                elif kind == "done":
                    rounds = payload.get("rounds") or 0
                    # the terminal result is authoritative for both ledgers
                    tools_called = payload.get("tools_called") or tools_called
                    artifacts = payload.get("artifacts") or artifacts
        except (asyncio.CancelledError, GeneratorExit):
            # STOP: the member aborted / the client disconnected. Persist the
            # partial so the reloaded transcript matches what they saw, then
            # let the cancellation proceed.
            logger.info("[LANE stream] turn stopped by member (lane=%s)", lane_id[:8])
            persist_reply(stopped=True)
            raise
        except Exception as exc:  # provider/transport failure mid-stream
            logger.warning("[LANE stream] turn failed: %s", exc)
            errored = str(exc)
            yield sse({"error": errored})

        persist_reply(stopped=False)

        done: dict = {
            "done": True,
            "rounds": rounds,
            "tools_called": tools_called,
            "artifacts": artifacts,
        }
        if renamed:
            done["lane_name"] = renamed
        yield sse(done)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/lanes/{lane_id}/messages")
async def lane_turn(lane_id: str, req: LaneTurnRequest, auth: UserClient):
    """One lane turn — STREAMING (ADR-412 D2). See `_turn_stream_response`
    for the SSE grammar + invariants. Phase-A additions: edit-and-resend
    (`replace_from_message_id` truncates the transcript tail first) and
    auto-naming (a default-named lane takes its first message's head)."""
    content = (req.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message content required")
    if len(content) > _MAX_MESSAGE_LEN:
        raise HTTPException(status_code=422, detail="Message too long")

    lane = _get_lane(auth, lane_id)
    if lane.get("status") != "active":
        raise HTTPException(status_code=409, detail="Lane is archived")

    # Phase-A attachments: build the model-facing message (vision parts /
    # projection pointers) + the metadata the user row persists.
    model_message = None
    attachments_meta: Optional[list[dict]] = None
    if req.attachments:
        lane_meta = (lane.get("context_metadata") or {}).get("lane") or {}
        model_message, attachments_meta = _build_turn_message(
            auth, content, req.attachments, lane_meta.get("model") or ""
        )

    # Edit-and-resend: truncate the tail from the edited USER message, then
    # run an ordinary turn with the edited content.
    if req.replace_from_message_id:
        row_res = (
            auth.client.table("session_messages")
            .select("id, role, sequence_number")
            .eq("session_id", lane_id)
            .eq("id", req.replace_from_message_id)
            .limit(1)
            .execute()
        )
        row = (row_res.data or [None])[0]
        if not row:
            raise HTTPException(status_code=404, detail="Message not found in this lane")
        if row.get("role") != "user":
            raise HTTPException(status_code=422, detail="Only your own messages can be edited")
        _delete_transcript_tail(auth, lane_id, int(row["sequence_number"]))

    renamed = _maybe_autoname(auth, lane, content)
    return _turn_stream_response(
        auth,
        lane,
        content,
        persist_user=True,
        renamed=renamed,
        model_message=model_message,
        attachments_meta=attachments_meta,
    )


@router.post("/lanes/{lane_id}/regenerate")
async def regenerate_lane_turn(lane_id: str, auth: UserClient):
    """Phase-A turn controls: regenerate — drop the transcript tail after the
    last USER message and run its turn again (no new user row). Also serves
    retry-after-error (a trailing user row with no reply regenerates cleanly).
    The no-rewind rule applies: substrate writes from the discarded reply
    stand on the ledger."""
    lane = _get_lane(auth, lane_id)
    if lane.get("status") != "active":
        raise HTTPException(status_code=409, detail="Lane is archived")

    rows_res = (
        auth.client.table("session_messages")
        .select("id, role, content, sequence_number")
        .eq("session_id", lane_id)
        .order("sequence_number", desc=True)
        .limit(_HISTORY_WINDOW)
        .execute()
    )
    last_user = next(
        (r for r in (rows_res.data or []) if r.get("role") == "user"), None
    )
    if not last_user or not (last_user.get("content") or "").strip():
        raise HTTPException(status_code=409, detail="Nothing to regenerate yet")

    seq = int(last_user["sequence_number"])
    _delete_transcript_tail(auth, lane_id, seq + 1)
    return _turn_stream_response(
        auth,
        lane,
        last_user["content"],
        persist_user=False,
        # History must end BEFORE the user message we re-run — it is passed
        # as the turn's user_message, not repeated from history.
        history_before_sequence=seq,
    )


class CreateAgentRequest(BaseModel):
    """The "make your own" form (personified-agents spec §7).

    Deliberately NO tools/authority field — not omitted from the model, but
    absent from the vocabulary: an Agent a member names is a member-named HAND,
    not a seat (ADR-460 D3.a). The manifest parser refuses them too, on the
    other side of the door.
    """
    name: str
    based_on: str                      # the kernel capability this wears
    tone: Optional[str] = None         # their manner, in their words
    model: Optional[str] = None        # the engine override (§4: available, never asked)
    color: Optional[str] = None
    avatar: Optional[str] = None       # a workspace image path (the ADR-395 bucket lane)


@router.post("/lane-agents")
async def create_member_agent(req: CreateAgentRequest, auth: UserClient) -> dict:
    """Make an Agent of your own — "Lisa", not "Sonnet".

    The UI is a DOOR, not a database: this validates and writes
    `/workspace/agents/{slug}/_agent.yaml` through the ordinary authored-write
    path, attributed like any member act. The FILE stays the source of truth —
    inspectable in Files, versioned on the ledger, revertible. (The ADR-449
    posture: no write path in the registry module; applies go through the
    ordinary doors.)
    """
    return await _write_member_agent(req, auth, slug=None, verb="made")


async def _write_member_agent(
    req: "CreateAgentRequest", auth: UserClient, *, slug: Optional[str], verb: str
) -> dict:
    """The one write body for make + edit (Singular Implementation).

    `slug=None` mints one from the name (create); a slug edits that folder.
    Every validation below holds on BOTH doors — an edit must not be a way to
    reach what a create refuses.
    """
    import re as _re

    from services.agents_registry import (
        AGENT_MANIFEST_BASENAME,
        _kernel_character,
        find_member_agents,
    )
    from services.authored_substrate import write_revision
    from services.lane_runner import LANE_MODELS, unpriced_lane_model

    name = (req.name or "").strip()[:_MAX_NAME_LEN]
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    based_on = (req.based_on or "").strip()
    # EVERY kernel character is hireable — a base agent (Designer, "my designer
    # is Maya") OR a posture (Critic, "my critic is Lisa"). (A one-commit
    # `bound_only` block lived here on 2026-07-16 and was removed the same day:
    # it made Designer a different KIND of Agent, which is the taxonomy ADR-460
    # D1 dissolved.)
    if _kernel_character(based_on) is None:
        raise HTTPException(status_code=422, detail=f"Unknown based_on: {based_on}")

    # The engine override — available, never asked (spec §4). A member's file
    # may not route an unpriced engine: the ADR-439 §4 rule holds on this side
    # of the door too.
    model = (req.model or "").strip()
    if model:
        if model not in LANE_MODELS:
            raise HTTPException(status_code=422, detail=f"Unknown model: {model}")
        if unpriced_lane_model(model):
            raise HTTPException(
                status_code=422,
                detail="this model has no billing rate configured and cannot run (ADR-439 §4)",
            )

    if slug is None:
        slug = _re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "agent"
        if _kernel_character(slug) is not None:
            # A member folder may not shadow a kernel slug — base agent OR
            # posture. "critic" must not mean two things by workspace.
            raise HTTPException(
                status_code=409, detail=f"'{slug}' is a built-in agent's name — pick another"
            )
        if any(a["slug"] == slug for a in find_member_agents(auth.client, auth.user_id)):
            raise HTTPException(
                status_code=409, detail=f"You already have an agent called '{name}'"
            )

    lines = [f"based_on: {based_on}", f"name: {name}"]
    tone = (req.tone or "").strip()
    if tone:
        # Block scalar — a member's tone is prose and may carry any punctuation.
        lines.append("tone: |")
        lines.extend(f"  {ln}" for ln in tone.splitlines())
    if model:
        lines.append(f"model: {model}")
    color = (req.color or "").strip()
    if color:
        lines.append(f"color: {color}")
    avatar = (req.avatar or "").strip()
    if avatar:
        lines.append(f"avatar: {avatar}")

    path = f"/workspace/agents/{slug}/{AGENT_MANIFEST_BASENAME}"
    write_revision(
        auth.client,
        user_id=auth.user_id,
        path=path,
        content="\n".join(lines) + "\n",
        authored_by="operator",
        message=f"{verb} an agent: {name}",
        workspace_id=_acting_workspace(auth),
    )
    return {"slug": slug, "name": name, "based_on": based_on, "path": path}


@router.patch("/lane-agents/{slug}")
async def patch_member_agent(slug: str, req: CreateAgentRequest, auth: UserClient) -> dict:
    """Edit one of your Agents — the same card, over an existing folder.

    A second revision on the ledger, not an overwrite of history: the file
    stays the source of truth, versioned and revertible (ADR-449's posture —
    the UI is a door, not a database). A kernel Agent cannot be edited: it is
    the capability, not a colleague you named. To change what Lisa IS, hire
    someone else — which is what making another Agent is.
    """
    from services.agents_registry import _kernel_character, find_member_agents

    if _kernel_character(slug) is not None:
        raise HTTPException(
            status_code=409,
            detail=f"'{slug}' is built in — make your own agent to change it",
        )
    mine = find_member_agents(auth.client, auth.user_id)
    if not any(a["slug"] == slug for a in mine):
        raise HTTPException(status_code=404, detail=f"No agent called '{slug}'")
    return await _write_member_agent(req, auth, slug=slug, verb="updated")


@router.post("/lanes/{lane_id}/settle")
async def settle_lane_route(lane_id: str, auth: UserClient) -> dict:
    """"Keep this" — turn this conversation into record (ADR-457 D3).

    The member's gesture, NOT a model capability: it fires only on this call
    (the never-ambient invariant), and the lane's model is the transport, not
    the actor. Deliberately not a primitive — in CHAT_PRIMITIVES a model could
    settle its own conversation unasked.

    One bounded turn distills; the KERNEL places (ADR-457 D4), cites
    (ADR-448/423), embeds (the retrieval fix), and meters (falsifier 2's
    instrument). Returns the landed note so the FE can show the moment.
    """
    lane = _get_lane(auth, lane_id)
    lane_meta = (lane.get("context_metadata") or {}).get("lane") or {}

    from services.lane_runner import LANE_MODELS, unpriced_lane_model
    from services.model_router import model_router_enabled
    from services.settle import settle_lane

    if not model_router_enabled():
        raise HTTPException(status_code=503, detail="the model router is not enabled")
    model = lane_meta.get("model") or ""
    if model not in LANE_MODELS:
        raise HTTPException(status_code=422, detail=f"lane model not routable: {model}")
    # ADR-439 §4 — the PRE-CALL check: an unpriced model never routes in prod.
    if unpriced_lane_model(model):
        raise HTTPException(
            status_code=422,
            detail="this model has no billing rate configured and cannot run (ADR-439 §4)",
        )

    # The full conversation, oldest-first — a settle reads the whole thing,
    # not the turn window (_fetch_history caps at _HISTORY_WINDOW for cost;
    # settling half a conversation would distill half an understanding).
    msgs = (
        auth.client.table("session_messages")
        .select("role, content, sequence_number")
        .eq("session_id", lane_id)
        .order("sequence_number")
        .execute()
    ).data or []

    try:
        result = await settle_lane(
            auth,
            lane_id=lane_id,
            lane_meta=lane_meta,
            messages=[{"role": m["role"], "content": m.get("content") or ""} for m in msgs],
            member_label=getattr(auth, "email", None) or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return result


@router.patch("/lanes/{lane_id}")
async def patch_lane(lane_id: str, req: LanePatchRequest, auth: UserClient) -> dict:
    """Phase-A hygiene: rename + pin. lane_meta-only writes."""
    lane = _get_lane(auth, lane_id)
    meta_all = lane.get("context_metadata") or {}
    lane_meta = dict(meta_all.get("lane") or {})
    changed = False
    if req.name is not None:
        name = req.name.strip()[:_MAX_NAME_LEN]
        if not name:
            raise HTTPException(status_code=422, detail="Lane name cannot be empty")
        lane_meta["name"] = name
        changed = True
    if req.pinned is not None:
        lane_meta["pinned"] = bool(req.pinned)
        changed = True
    if changed:
        merged = {**meta_all, "lane": lane_meta}
        auth.client.table("chat_sessions").update(
            {"context_metadata": merged}
        ).eq("id", lane_id).execute()
        lane = {**lane, "context_metadata": merged}
    return _lane_row_to_dict(lane)


@router.get("/lanes/search")
async def search_lanes(q: str, auth: UserClient) -> dict:
    """Phase-A hygiene: search across the member's active lanes in the acting
    workspace — transcript content match (ILIKE), first snippet per lane.
    Member-experience scope (ADR-407): only the viewer's own lanes."""
    query = (q or "").strip()
    if len(query) < 2:
        return {"matches": []}

    lq = (
        auth.client.table("chat_sessions")
        .select("id")
        .eq("user_id", auth.user_id)
        .eq("session_type", "lane")
        .eq("status", "active")
    )
    ws = _acting_workspace(auth)
    if ws:
        lq = lq.eq("workspace_id", ws)
    lane_ids = [r["id"] for r in (lq.execute().data or [])]
    if not lane_ids:
        return {"matches": []}

    res = (
        auth.client.table("session_messages")
        .select("session_id, content, created_at")
        .in_("session_id", lane_ids)
        .ilike("content", f"%{query}%")
        .order("created_at", desc=True)
        .limit(40)
        .execute()
    )
    matches: dict[str, str] = {}
    for r in res.data or []:
        sid = r["session_id"]
        if sid in matches:
            continue
        content = r.get("content") or ""
        idx = content.lower().find(query.lower())
        start = max(0, idx - 40)
        snippet = content[start : idx + len(query) + 60].strip()
        matches[sid] = ("…" if start > 0 else "") + snippet
    return {"matches": [{"lane_id": k, "snippet": v} for k, v in matches.items()]}


@router.post("/lanes/{lane_id}/archive")
async def archive_lane(lane_id: str, auth: UserClient) -> dict:
    """Archive a lane. Session legibility (ADR-412 D2): capture a prose
    summary on the way out (reusing the steward's session-summary machinery)
    so the lane's work is legible after it leaves the active list."""
    _get_lane(auth, lane_id)

    # Best-effort summary — never block archive on it.
    summary: Optional[str] = None
    try:
        from datetime import date as _date
        from services.session_continuity import generate_session_summary

        msgs = (
            auth.client.table("session_messages")
            .select("role, content, sequence_number")
            .eq("session_id", lane_id)
            .order("sequence_number")
            .limit(200)
            .execute()
        )
        conv = [
            {"role": r["role"], "content": r["content"] or ""}
            for r in (msgs.data or [])
            if r.get("role") in ("user", "assistant")
        ]
        summary = await generate_session_summary(
            conv,
            _date.today().isoformat(),
            user_id=auth.user_id,
            principal_id=getattr(auth, "principal_id", None) or auth.user_id,
        )
    except Exception as exc:
        logger.warning("[LANE] archive summary failed (non-fatal): %s", exc)

    update: dict = {"status": "archived"}
    if summary:
        update["summary"] = summary
    auth.client.table("chat_sessions").update(update).eq("id", lane_id).execute()
    return {"success": True, "summary": summary}
