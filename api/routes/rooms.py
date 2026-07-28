"""Room routes — ADR-492 (rooms: the shared Conversation object).

A room is a shared-scope Conversation (workspace CONTENT, DP35 — migration
225): part of the commons, attributed, readable by grant-holders. Private
lanes stay in `chat_sessions` (member experience); scope is set at birth and
never flips (ADR-492 D6.b).

- `GET  /api/rooms`                 — active rooms in the acting workspace
- `POST /api/rooms`                 — create a room (members composed at birth)
- `GET  /api/rooms/{id}`            — room + members + recent messages
- `POST /api/rooms/{id}/messages`   — one human turn; addressing an Agent
                                      member fires that Agent's reply
- `POST /api/rooms/{id}/invite`     — add a member (human or Agent), attributed
- `PATCH /api/rooms/{id}`           — rename
- `POST /api/rooms/{id}/archive`    — archive

Invariants (ADR-492 D2/D3, enforced here):
- NEVER-AMBIENT: a model turn fires only on a human act — a plain message
  fires nothing; an engine reply fires only when the sender ADDRESSES an
  Agent member (`address` field or an `@slug` mention in the text).
- Attribution verbatim: human turns as the member; engine turns as
  `member:{id} via {model}` (the room shows the Agent's face; the ledger
  says the member's hands — ADR-460).
- Coworking commons (ADR-408 D1): any active-grant holder may read and
  speak; speaking joins you to the room (attributed). Invite is the explicit
  membership act. There is no owner-review lane.
- Rooms never send notifications (ADR-492 D3) — acts land on the ledgers;
  the OS routes attention. (The timeline/To-do derivation wiring is the
  declared fast-follow; nothing here writes to `notifications`.)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient, get_service_client
from services.workspace_context import effective_workspace_id

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_TITLE_LEN = 60
_MAX_MESSAGE_LEN = 32_000
_HISTORY_WINDOW = 30      # messages composed into an addressed engine turn
_PAGE = 200               # messages returned by GET (newest window)
_DEFAULT_TITLE = "New room"

_MENTION_RE = re.compile(r"@([a-z0-9][a-z0-9-]{0,40})", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Pydantic shapes
# ---------------------------------------------------------------------------

class RoomMemberSpec(BaseModel):
    kind: str                       # 'human' | 'agent'
    principal_id: Optional[str] = None
    agent_slug: Optional[str] = None


class CreateRoomRequest(BaseModel):
    title: Optional[str] = None
    members: list[RoomMemberSpec] = []


class RoomMessageRequest(BaseModel):
    content: str
    # ADR-492 D3 — addressing IS selection: name the Agent member who should
    # answer. Optional; an @slug mention in the text works too. Absent both,
    # the message is a plain human turn and NOTHING answers (never-ambient).
    address: Optional[str] = None


class InviteRequest(BaseModel):
    kind: str                       # 'human' | 'agent'
    principal_id: Optional[str] = None
    agent_slug: Optional[str] = None


class RoomPatchRequest(BaseModel):
    title: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _acting_workspace(auth: UserClient) -> str:
    ws = effective_workspace_id(auth.user_id)
    if not ws:
        raise HTTPException(status_code=409, detail="No acting workspace")
    return ws


def _grant_holders(workspace_id: str) -> dict[str, str]:
    """Active HUMAN grant-holders of the workspace: principal_id → role."""
    svc = get_service_client()
    rows = (
        svc.table("principal_grants")
        .select("principal_id, role, status")
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .execute()
    ).data or []
    return {r["principal_id"]: r["role"] for r in rows if r.get("role") in ("owner", "member")}


def _require_grant(auth: UserClient, workspace_id: str) -> None:
    """The commons boundary (ADR-408 D1): a grant is the only gate."""
    if auth.user_id not in _grant_holders(workspace_id):
        raise HTTPException(status_code=403, detail="No active grant on this workspace")


def _get_room(workspace_id: str, room_id: str) -> dict:
    svc = get_service_client()
    row = (
        svc.table("conversations")
        .select("*")
        .eq("id", room_id)
        .eq("workspace_id", workspace_id)
        .limit(1)
        .execute()
    ).data
    if not row:
        raise HTTPException(status_code=404, detail="Room not found")
    return row[0]


def _room_members(room_id: str) -> list[dict]:
    svc = get_service_client()
    return (
        svc.table("conversation_members")
        .select("member_kind, principal_id, agent_slug, invited_by, created_at")
        .eq("conversation_id", room_id)
        .order("created_at")
        .execute()
    ).data or []


def _resolve_registry_agent(auth: UserClient, slug: str) -> Optional[dict]:
    """A named hand — kernel or member-authored (ADR-460). None if unknown."""
    from services.agents_registry import find_member_agents, resolve_agent
    try:
        member_agents = find_member_agents(auth.client, auth.user_id)
    except Exception:  # noqa: BLE001 — registry read is best-effort here
        member_agents = []
    return resolve_agent(slug, member_agents)


def _ensure_member(room_id: str, workspace_id: str, *, kind: str,
                   principal_id: Optional[str] = None,
                   agent_slug: Optional[str] = None,
                   invited_by: str) -> bool:
    """Idempotent membership insert. Returns True if a row was added."""
    svc = get_service_client()
    q = (
        svc.table("conversation_members")
        .select("id")
        .eq("conversation_id", room_id)
        .eq("member_kind", kind)
    )
    q = q.eq("principal_id", principal_id) if kind == "human" else q.eq("agent_slug", agent_slug)
    if (q.limit(1).execute()).data:
        return False
    svc.table("conversation_members").insert({
        "conversation_id": room_id,
        "workspace_id": workspace_id,
        "member_kind": kind,
        "principal_id": principal_id,
        "agent_slug": agent_slug,
        "invited_by": invited_by,
    }).execute()
    return True


def _member_labels(auth: UserClient, principal_ids: set[str]) -> dict[str, str]:
    """Best-effort email labels (the workspace-members pattern)."""
    labels: dict[str, str] = {}
    svc = get_service_client()
    for pid in principal_ids:
        if pid == auth.user_id and getattr(auth, "email", None):
            labels[pid] = auth.email
            continue
        try:
            u = svc.auth.admin.get_user_by_id(pid)
            if u and getattr(u, "user", None) and u.user.email:
                labels[pid] = u.user.email
        except Exception:  # noqa: BLE001 — humanization is best-effort
            labels[pid] = f"member-{pid[:8]}"
    return labels


def _serialize_message(m: dict) -> dict:
    return {
        "id": m["id"],
        "author_principal_id": m["author_principal_id"],
        "via_model": m.get("via_model"),
        "agent_slug": m.get("agent_slug"),
        "content": m.get("content") or "",
        "mentions": m.get("mentions"),
        "created_at": m.get("created_at"),
    }


def _compose_history(messages: list[dict], *, answering_slug: str,
                     labels: dict[str, str]) -> list[dict]:
    """Room transcript → OpenAI-shape history for the addressed Agent.

    The answering Agent's own prior engine turns are `assistant`; every other
    voice (humans, other Agents) is a labeled `user` turn — the standard
    multi-party mapping onto a two-role protocol, with attribution kept
    visible so the model knows who said what.
    """
    history: list[dict] = []
    for m in messages:
        content = m.get("content") or ""
        if m.get("via_model") and m.get("agent_slug") == answering_slug:
            history.append({"role": "assistant", "content": content})
        else:
            if m.get("via_model"):
                speaker = f"{m.get('agent_slug') or 'agent'} (via {m['via_model']})"
            else:
                speaker = labels.get(m["author_principal_id"], "member")
            history.append({"role": "user", "content": f"[{speaker}]: {content}"})
    return history


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/rooms")
async def list_rooms(auth: UserClient) -> dict:
    ws = _acting_workspace(auth)
    _require_grant(auth, ws)
    svc = get_service_client()
    rows = (
        svc.table("conversations")
        .select("id, title, status, created_by, created_at, updated_at")
        .eq("workspace_id", ws)
        .eq("status", "active")
        .order("updated_at", desc=True)
        .execute()
    ).data or []
    rooms = []
    for r in rows:
        rooms.append({**r, "members": _room_members(r["id"])})
    return {"rooms": rooms}


@router.post("/rooms")
async def create_room(req: CreateRoomRequest, auth: UserClient) -> dict:
    """Create a room — born shared, members composed at birth (ADR-492 D6.a)."""
    ws = _acting_workspace(auth)
    _require_grant(auth, ws)
    holders = _grant_holders(ws)

    # Validate the birth cast BEFORE creating anything.
    human_ids: list[str] = []
    agent_slugs: list[str] = []
    for m in req.members:
        if m.kind == "human":
            if not m.principal_id:
                raise HTTPException(status_code=422, detail="human member needs principal_id")
            if m.principal_id not in holders:
                raise HTTPException(
                    status_code=422,
                    detail="That person does not hold a grant on this workspace — invite them to the workspace first.",
                )
            if m.principal_id != auth.user_id:
                human_ids.append(m.principal_id)
        elif m.kind == "agent":
            if not m.agent_slug:
                raise HTTPException(status_code=422, detail="agent member needs agent_slug")
            if _resolve_registry_agent(auth, m.agent_slug) is None:
                raise HTTPException(status_code=422, detail=f"No agent called '{m.agent_slug}'")
            agent_slugs.append(m.agent_slug)
        else:
            raise HTTPException(status_code=422, detail=f"Unknown member kind: {m.kind}")

    title = (req.title or "").strip()[:_MAX_TITLE_LEN] or _DEFAULT_TITLE
    svc = get_service_client()
    created = (
        svc.table("conversations")
        .insert({"workspace_id": ws, "title": title, "created_by": auth.user_id})
        .execute()
    ).data[0]
    room_id = created["id"]

    # The founder is always a member; then the composed cast.
    _ensure_member(room_id, ws, kind="human", principal_id=auth.user_id, invited_by=auth.user_id)
    for pid in human_ids:
        _ensure_member(room_id, ws, kind="human", principal_id=pid, invited_by=auth.user_id)
    for slug in dict.fromkeys(agent_slugs):
        _ensure_member(room_id, ws, kind="agent", agent_slug=slug, invited_by=auth.user_id)

    logger.info("[ROOM] created room=%s ws=%s humans=%d agents=%d",
                room_id[:8], ws[:8], 1 + len(human_ids), len(agent_slugs))
    return {"room": {**created, "members": _room_members(room_id)}}


@router.get("/rooms/{room_id}")
async def get_room(room_id: str, auth: UserClient) -> dict:
    ws = _acting_workspace(auth)
    _require_grant(auth, ws)
    room = _get_room(ws, room_id)
    members = _room_members(room_id)
    svc = get_service_client()
    msgs = (
        svc.table("conversation_messages")
        .select("*")
        .eq("conversation_id", room_id)
        .order("created_at", desc=True)
        .limit(_PAGE)
        .execute()
    ).data or []
    msgs.reverse()
    return {
        "room": {**room, "members": members},
        "messages": [_serialize_message(m) for m in msgs],
    }


@router.post("/rooms/{room_id}/invite")
async def invite_member(room_id: str, req: InviteRequest, auth: UserClient) -> dict:
    """The explicit membership act — attributed (invited_by)."""
    ws = _acting_workspace(auth)
    _require_grant(auth, ws)
    _get_room(ws, room_id)

    if req.kind == "human":
        if not req.principal_id:
            raise HTTPException(status_code=422, detail="human member needs principal_id")
        if req.principal_id not in _grant_holders(ws):
            raise HTTPException(
                status_code=422,
                detail="That person does not hold a grant on this workspace — invite them to the workspace first.",
            )
        added = _ensure_member(room_id, ws, kind="human",
                               principal_id=req.principal_id, invited_by=auth.user_id)
    elif req.kind == "agent":
        if not req.agent_slug:
            raise HTTPException(status_code=422, detail="agent member needs agent_slug")
        if _resolve_registry_agent(auth, req.agent_slug) is None:
            raise HTTPException(status_code=422, detail=f"No agent called '{req.agent_slug}'")
        added = _ensure_member(room_id, ws, kind="agent",
                               agent_slug=req.agent_slug, invited_by=auth.user_id)
    else:
        raise HTTPException(status_code=422, detail=f"Unknown member kind: {req.kind}")

    return {"added": added, "members": _room_members(room_id)}


@router.post("/rooms/{room_id}/messages")
async def post_room_message(room_id: str, req: RoomMessageRequest, auth: UserClient) -> dict:
    """One human turn; an addressed Agent member answers (never-ambient)."""
    ws = _acting_workspace(auth)
    _require_grant(auth, ws)
    _get_room(ws, room_id)

    content = (req.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message cannot be empty")
    if len(content) > _MAX_MESSAGE_LEN:
        raise HTTPException(status_code=422, detail="Message too long")

    members = _room_members(room_id)
    agent_members = {m["agent_slug"] for m in members if m["member_kind"] == "agent"}

    # Speaking joins you (coworking commons — attributed, idempotent).
    _ensure_member(room_id, ws, kind="human", principal_id=auth.user_id, invited_by=auth.user_id)

    # Addressing: the explicit field wins; else the first @slug that names an
    # Agent member. Mentions of agent members are recorded as addressing
    # metadata (D3 — content fact; the attention consequence is OS-side).
    mentioned = [s.lower() for s in _MENTION_RE.findall(content)]
    agent_mentions = [s for s in mentioned if s in agent_members]
    address = (req.address or "").strip().lower() or (agent_mentions[0] if agent_mentions else None)
    if address and address not in agent_members:
        if _resolve_registry_agent(auth, address) is not None:
            raise HTTPException(
                status_code=422,
                detail=f"'{address}' isn't in this room yet — invite them first.",
            )
        raise HTTPException(status_code=422, detail=f"No agent called '{address}'")

    mentions_meta = [{"kind": "agent", "id": s} for s in dict.fromkeys(agent_mentions)] or None

    svc = get_service_client()
    human_row = (
        svc.table("conversation_messages")
        .insert({
            "conversation_id": room_id,
            "workspace_id": ws,
            "author_principal_id": auth.user_id,
            "content": content,
            "mentions": mentions_meta,
        })
        .execute()
    ).data[0]
    svc.table("conversations").update({"updated_at": "now()"}).eq("id", room_id).execute()

    out: dict[str, Any] = {"messages": [_serialize_message(human_row)]}
    if not address:
        return out  # a plain human turn — nothing answers (never-ambient)

    # --- the addressed Agent's reply: the member's hands, metered, gated ---
    agent = _resolve_registry_agent(auth, address)
    model = (agent or {}).get("model") or ""

    from services.lane_runner import LANE_MODELS, run_lane_turn, unpriced_lane_model
    from services.model_router import model_router_enabled

    if not model_router_enabled():
        raise HTTPException(status_code=503, detail="the model router is not enabled")
    if model not in LANE_MODELS:
        raise HTTPException(status_code=422, detail=f"agent model not routable: {model}")
    if unpriced_lane_model(model):
        raise HTTPException(
            status_code=422,
            detail="this model has no billing rate configured and cannot run (ADR-439 §4)",
        )

    # THE draw gate (ADR-445 §9 / ADR-491 P3) — before any billable call.
    from services.platform_limits import check_draw
    draw_ok, draw_reason, _detail = check_draw(
        auth.client,
        auth.user_id,
        workspace_id=ws,
        principal_id=getattr(auth, "principal_id", None) or auth.user_id,
    )
    if not draw_ok:
        raise HTTPException(
            status_code=402,
            detail=(
                "This workspace's balance is exhausted — top up to continue."
                if draw_reason == "balance_exhausted"
                else "You've reached your spend cap on this workspace — ask the owner to raise it."
            ),
        )

    prior = (
        svc.table("conversation_messages")
        .select("*")
        .eq("conversation_id", room_id)
        .order("created_at", desc=True)
        .limit(_HISTORY_WINDOW)
        .execute()
    ).data or []
    prior.reverse()
    human_ids = {m["author_principal_id"] for m in prior}
    labels = _member_labels(auth, human_ids)
    # History excludes the just-posted message (it is this turn's user_message).
    history = _compose_history(
        [m for m in prior if m["id"] != human_row["id"]],
        answering_slug=address, labels=labels,
    )
    speaker = labels.get(auth.user_id, "member")

    result = await run_lane_turn(
        auth,
        model=model,
        history=history,
        user_message=f"[{speaker}]: {content}",
        member_label=speaker,
        agent=address,
        session_id=room_id,
        ledger_slug="room",
    )
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("message") or "The agent's turn failed")

    engine_row = (
        svc.table("conversation_messages")
        .insert({
            "conversation_id": room_id,
            "workspace_id": ws,
            "author_principal_id": auth.user_id,   # the addressing member's hands
            "via_model": model,
            "agent_slug": address,
            "content": result.get("text") or "",
        })
        .execute()
    ).data[0]
    svc.table("conversations").update({"updated_at": "now()"}).eq("id", room_id).execute()

    out["messages"].append(_serialize_message(engine_row))
    out["artifacts"] = result.get("artifacts") or []
    return out


@router.patch("/rooms/{room_id}")
async def patch_room(room_id: str, req: RoomPatchRequest, auth: UserClient) -> dict:
    ws = _acting_workspace(auth)
    _require_grant(auth, ws)
    _get_room(ws, room_id)
    if req.title is not None:
        title = req.title.strip()[:_MAX_TITLE_LEN]
        if not title:
            raise HTTPException(status_code=422, detail="Room title cannot be empty")
        get_service_client().table("conversations").update(
            {"title": title, "updated_at": "now()"}
        ).eq("id", room_id).execute()
    return {"room": {**_get_room(ws, room_id), "members": _room_members(room_id)}}


@router.post("/rooms/{room_id}/archive")
async def archive_room(room_id: str, auth: UserClient) -> dict:
    ws = _acting_workspace(auth)
    _require_grant(auth, ws)
    _get_room(ws, room_id)
    get_service_client().table("conversations").update(
        {"status": "archived", "updated_at": "now()"}
    ).eq("id", room_id).execute()
    return {"archived": True}
