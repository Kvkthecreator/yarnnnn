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

_MAX_ACTIVE_LANES = 8      # UX bound, not policy (ADR-408 D6)
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
    model: str
    # ADR-440 D3 — the Studio binding: a workspace path this lane authors.
    # A lane with a binding is a Studio lane; its turns carry the authoring
    # posture + token profile. Optional; plain chat lanes never set it.
    artifact_path: Optional[str] = None
    # ADR-450 D3 — the derive binding (the "Learn from" verb): a kernel recipe
    # slug + the workspace source path this lane derives from. Same lane_meta
    # mechanism as the Studio binding; turns compose the recipe section.
    derive_recipe: Optional[str] = None
    derive_source: Optional[str] = None


class LaneTurnRequest(BaseModel):
    content: str
    # Phase-A turn controls: edit-and-resend. When set, the transcript tail is
    # truncated from this USER message (inclusive) before the turn runs. The
    # no-rewind rule (three-axes discourse §3): truncation is transcript-only —
    # substrate writes from discarded turns stand on the ledger; undoing them
    # is its own revert-as-write act (ADR-406).
    replace_from_message_id: Optional[str] = None


class LanePatchRequest(BaseModel):
    # Phase-A conversation hygiene: rename + pin (lane_meta fields).
    name: Optional[str] = None
    pinned: Optional[bool] = None


def _acting_workspace(auth: UserClient) -> Optional[str]:
    return effective_workspace_id(auth.user_id)


def _lane_row_to_dict(row: dict) -> dict:
    lane_meta = (row.get("context_metadata") or {}).get("lane") or {}
    return {
        "id": row["id"],
        "name": lane_meta.get("name") or "Lane",
        "model": lane_meta.get("model") or "",
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
async def list_lanes(auth: UserClient) -> dict:
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
        lanes = [_lane_row_to_dict(r) for r in (q.execute().data or [])]

    from services.derive_recipes import list_recipes

    return {
        "enabled": enabled,
        "models": [
            {"id": mid, "label": meta["label"]}
            for mid, meta in LANE_MODELS.items()
        ],
        # ADR-450 D5: the Learn-from chooser payload — kernel recipes, served
        # on the capability envelope (no new endpoint, no FE duplication).
        "recipes": list_recipes(),
        "lanes": lanes,
    }


@router.post("/lanes")
async def create_lane(req: CreateLaneRequest, auth: UserClient) -> dict:
    from services.lane_runner import LANE_MODELS
    from services.model_router import model_router_enabled

    if not model_router_enabled():
        raise HTTPException(status_code=403, detail="Lanes are not enabled (router off)")
    if req.model not in LANE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown lane model: {req.model}")
    # Phase-A hygiene: a nameless lane is fine — it auto-names on first turn.
    name = (req.name or "").strip()[:_MAX_NAME_LEN] or _DEFAULT_LANE_NAME

    ws = _acting_workspace(auth)
    active = (
        auth.client.table("chat_sessions")
        .select("id", count="exact")
        .eq("user_id", auth.user_id)
        .eq("session_type", "lane")
        .eq("status", "active")
    )
    if ws:
        active = active.eq("workspace_id", ws)
    count = active.execute().count or 0
    if count >= _MAX_ACTIVE_LANES:
        raise HTTPException(
            status_code=409,
            detail=f"Lane limit reached ({_MAX_ACTIVE_LANES}) — archive one first",
        )

    lane_meta: dict = {"name": name, "model": req.model}
    artifact_path = (req.artifact_path or "").strip()
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
                user_message=content,
                member_label=getattr(auth, "email", None) or None,
                # ADR-440 D3 — a bound lane's turns carry the Studio posture.
                artifact_path=lane_meta.get("artifact_path"),
                # ADR-450 D3 — a derive-bound lane's turns carry the recipe.
                derive_recipe=lane_meta.get("derive_recipe"),
                derive_source=lane_meta.get("derive_source"),
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
    return _turn_stream_response(auth, lane, content, persist_user=True, renamed=renamed)


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
