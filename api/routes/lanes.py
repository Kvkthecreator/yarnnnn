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

#: ADR-559 D3 — what a member is told when an engine is unavailable, per
#: reason. Written for the MEMBER, not the operator: "no provider key" is our
#: deployment's problem, so it must not read as something they did wrong or
#: could fix. The reason code still rides on the envelope for the operator.
_UNAVAILABLE_ENGINE_DETAIL = {
    "no_provider_key": "{label} isn't connected on this deployment yet.",
    "unpriced": "{label} has no billing rate configured and cannot run.",
    "upstream_refused": "{label} is unavailable right now — the provider declined the last request.",
}


class CreateLaneRequest(BaseModel):
    # Optional since Phase A: absent/blank → _DEFAULT_LANE_NAME + auto-name on
    # the first turn (conversation hygiene — the ChatGPT-bar naming behavior).
    name: Optional[str] = None
    # ADR-558 D1/D3 — CHAT IS THE ENGINE SURFACE. An unbound (chat) lane is
    # created with an ENGINE; it has no birth-persona. Who REPLIES is the cast's
    # answer (ADR-495), joined after creation, never chosen at the door.
    #
    # `agent` survives for BOUND lanes only — Studio/Docs/IMAGES pin a resident
    # (ADR-467 D1: an app has one job, so it pins one colleague). Passing
    # `agent` without a binding is now a 422: it was the creation-time scalar
    # ADR-495 D3 already retired into the cast, and keeping both authorities
    # produced a live bug (an Agent added via CastBar never replied — the cast
    # said yes, lane_meta said nobody). One authority per surface.
    model: Optional[str] = None
    # ADR-562 D3 — THE APP ASKS, THE SERVER ANSWERS WHO. A bound lane names the
    # APP creating it (`studio` | `docs` | `images`); the resident is resolved
    # server-side from that app's own registration
    # (`services/apps/*` → `register_app`). `agent` is no longer accepted from
    # the client at all: an app's resident is a fact ABOUT THE APP, not a
    # preference the browser states — and a client that could assert it could
    # also drift from it, which is exactly what happened (the panel rendered the
    # ENGINE where a resident had been pinned, because the client held the fact
    # and never read it back).
    app: Optional[str] = None

    # ADR-562 D3 — REFUSE an `agent` a stale client still sends, never ignore it.
    # Pydantic's default is to DROP an unknown field, which during a deploy
    # window (cached bundle → new API) would create a bound lane carrying NO
    # resident: the client believes it pinned Designer, the lane pins nobody,
    # and the panel silently falls back to the engine label — the exact defect
    # this ADR removes, reintroduced by a rollout gap. The ADR-460 strict-key
    # precedent: a dropped field reads as supported and becomes a bug report.
    model_config = {"extra": "forbid"}
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


class LaneFocus(BaseModel):
    """ADR-522 — what the member is looking at when they ask.

    Per-turn and transient: focus changes between turns and within one, so it
    is never persisted (the durable lane↔artifact binding lives on
    ``context_metadata.lane`` and answers a different question — WHICH file,
    not WHERE in it).

    ``scope`` is ADR-519 D1's four-grain hierarchy, not ADR-453's dissolved
    block→slot→page ladder. The shell declares it; the server renders one
    bullet from it and never parses ``path`` for authority (the lane binding
    is the authority on which artifact this lane may write).
    """

    app: str
    path: Optional[str] = None
    scope: str = "document"  # document | page | container | block
    id: Optional[str] = None
    page_index: Optional[int] = None
    label: Optional[str] = None
    excerpt: Optional[str] = None
    viewport_page_index: Optional[int] = None


class LaneTurnRequest(BaseModel):
    content: str
    # ADR-522 D2: the focus declaration for THIS turn. Optional throughout —
    # an app that declares nothing sends nothing, and the posture simply
    # carries no focus line.
    focus: Optional[LaneFocus] = None
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
    """The workspace this request is bound to.

    `auth.workspace_id` is passed EXPLICITLY (ADR-501, probe 2026-07-29):
    `get_user_client` already resolved the binding fail-closed from
    `X-Workspace-Id`, and it is the strongest signal — omitting it left the
    resolver to fall through to the contextvar/owner path, so a member acting
    in a granted workspace resolved their OWN and every conversation in the
    shared one 404'd with "not found in this workspace". The contextvar is set
    per request too, but passing the value we already hold removes the
    dependency on that ordering entirely.
    """
    return effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))


def _conversation_write_client(auth: UserClient):
    """The client conversation-level WRITES go through (migration 228).

    RENAMED + NARROWED from `_cast_read_client`. That helper existed because
    `chat_sessions` / `session_messages` RLS was `user_id = auth.uid()` — the row
    belonged to its CREATOR, a policy older than the cast (ADR-495) — so a member
    correctly cast in read nothing back and shared conversations were dead at
    N>1. Every READ was routed through the service client to get around it.

    **Migration 228 moved that answer into the database**, which is where
    migrations 221 and 227 already argued it belongs ("make the table tell the
    truth to any authorized reader"). `chat_sessions` SELECT is now cast
    membership ∩ workspace grant; `session_messages` SELECT additionally
    enforces the ADR-495 D2 visibility window. So every READ in this module uses
    `auth.client` and is checked by the table itself — the application gate is
    now defence in depth rather than the only defence.

    What legitimately remains service-side, and why the policies deliberately do
    NOT grant it to a participant:

    - **Session-row mutation by a non-creator** — auto-name, pin/rename, archive,
      the `updated_at` touch. A participant who did not create the conversation
      has no UPDATE policy on it (the creator owns the row), yet renaming on
      first turn and touching `updated_at` on every turn must work for ANY
      participant. These are system-mediated acts, gated in Python by
      `_get_lane` (cast membership + acting workspace) before they run.
    - **Transcript-tail delete** — participants have no DELETE on
      `session_messages` at all: a transcript is append-only (ADR-406's appender
      rule). Edit-and-resend truncates as a system act, gated by the author
      check in `lane_turn`.

    Keeping the name honest matters: the old one said "read" while the module
    used it for fifteen reads AND writes, which is how the workaround quietly
    became the architecture.
    """
    from services.supabase import get_service_client

    return get_service_client()


def app_for_lane(lane_meta: dict) -> str:
    """The app a lane belongs to — its stamp, else its artifact's layout.

    ADR-602 D7. The stamp (ADR-567 D4) is authoritative when present. Without
    one, a BOUND lane still belongs to an app: its artifact declares a layout
    and the layout registry declares that layout's owner. Deriving it means a
    pre-567 lane behaves like every other lane instead of reading as
    residentless.

    Path-shaped, deliberately: reading the artifact's CONTENT here would make
    a hot pure function do IO on every lane in a list. `.html` is Slides'
    currency and `.md` is Text's — a coarse but honest split, and a wrong
    guess is impossible for the two apps that have residents (both are
    unambiguous by extension). Anything else returns "" and the precedence
    continues exactly as before.
    """
    stamped = (lane_meta.get("app") or "").strip()
    if stamped:
        return stamped
    path = (lane_meta.get("artifact_path") or "").strip().lower()
    if path.endswith(".html"):
        return "slides"
    if path.endswith(".md"):
        return "text"
    return ""


def _lane_agent(lane_meta: dict) -> Optional[str]:
    """The lane's resident, DERIVED from the registration (ADR-597 D1). Pure-ish.

    A bound lane's resident is a fact about the APP, so it follows the app's
    own declaration at read time — the same rule that already governed the
    app's rename (`as_name`, ADR-562 D6) and the posture text (ADR-460 D4:
    a now-fact is derived, never stored). Persisting it was what stranded
    every live desk on yesterday's registration ("Claude Sonnet" in Studio).

    Precedence: the app's registration → the derive recipe's declaration →
    the legacy stored stamp (pre-597 rows; a registration that has since left
    the roster) → None. A lane with none of these shows its engine, which is
    honest — that IS what such a lane is.

    ⚠️ THE PRE-567 GAP (ADR-602 D7, operator-observed). A lane bound to an
    artifact but carrying NO `app` stamp — every lane created before ADR-567,
    ~35 of which ADR-597 D3 deliberately left alone — skipped straight to the
    legacy stamp, and an unstamped one derived None. The member then read
    "Message Claude Sonnet 4.6…" on a deck Editor was authoring: correct by
    the letter of the precedence, wrong in the room. `app_for_lane` closes it
    by asking the ARTIFACT what app owns its layout, which is the same
    question `build_studio_posture` already answers at turn time.
    """
    app = app_for_lane(lane_meta)
    if app:
        # The package import IS the registration — load-bearing, never prune.
        import services.apps  # noqa: F401  (registration side-effect)
        from services.authoring import resident_for_app

        derived = resident_for_app(app)
        if derived:
            return derived
    recipe = (lane_meta.get("derive_recipe") or "").strip()
    if recipe:
        from services.derive_recipes import resident_for_recipe

        derived = resident_for_recipe(recipe)
        if derived:
            return derived
    return lane_meta.get("agent") or None


def _lane_row_to_dict(row: dict) -> dict:
    lane_meta = (row.get("context_metadata") or {}).get("lane") or {}
    return {
        "id": row["id"],
        "name": lane_meta.get("name") or "Lane",
        "model": lane_meta.get("model") or "",
        # ADR-597 D1 — WHO this lane talks to, derived from the registration
        # at serve time (never the creation-time stamp). None only when
        # nothing derivable or stored remains; the FE then falls back to the
        # model label, which is honest rather than guessed.
        "agent": _lane_agent(lane_meta),
        # Phase-A hygiene: pinned lanes sort first in the workbench list.
        "pinned": bool(lane_meta.get("pinned")),
        # ADR-440 D3 — the Studio binding (None for plain chat lanes).
        "artifact_path": lane_meta.get("artifact_path"),
        # ADR-567 D4 — the binding app (None for plain chat + pre-567 lanes).
        "app": lane_meta.get("app"),
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
    """Load one conversation, authorizing by CAST MEMBERSHIP (ADR-495 D2).

    Membership IS read permission. The creator is a participant like any other
    (migration 226 backfilled one for every pre-existing conversation), so the
    single-owner case is the N=1 degenerate case of the general rule rather
    than a separate code path.

    No species check: `visibility_floor` answers the same question for every
    participant. The window itself is applied at the transcript read
    (`_fetch_history`, `lane_messages`) — this gate answers *may they read at
    all*, that one answers *from where*.
    """
    from services.conversation_cast import visibility_floor

    res = (
        auth.client.table("chat_sessions")
        .select("id, user_id, workspace_id, status, context_metadata, created_at, updated_at")
        .eq("id", lane_id)
        .eq("session_type", "lane")
        .limit(1)
        .execute()
    )
    row = (res.data or [None])[0]
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    # FAIL CLOSED (ADR-501 class, audited 2026-07-30). This read
    # `if ws and row.get("workspace_id") and …` — so a conversation whose
    # `workspace_id` is NULL passed the check in EVERY workspace, and
    # `visibility_floor` is workspace-blind, so it was openable by direct id
    # from any workspace the caller could reach while being INVISIBLE in the
    # list (whose queries `.eq("workspace_id", ws)` unconditionally). Openable
    # but unlistable is the tell that the two paths disagreed.
    #
    # Migration 203 backfilled the column and added a BEFORE INSERT trigger, so
    # a NULL is not expected — which is exactly why it must be refused rather
    # than waved through: an unbound conversation row is a substrate defect, and
    # serving it in whatever workspace happens to ask is the wrong answer to it.
    ws = _acting_workspace(auth)
    if ws and row.get("workspace_id") != ws:
        raise HTTPException(status_code=404, detail="Conversation not found in this workspace")

    floor = visibility_floor(lane_id, auth.user_id)
    if floor is None:
        # Not in the cast. The creator fallback covers conversations whose
        # participant row is missing (a failed backfill or a race at create):
        # the creator is always a participant, so heal rather than lock out.
        if row.get("user_id") != auth.user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        from services.conversation_cast import add_participant
        add_participant(
            lane_id,
            workspace_id=row.get("workspace_id"), member_kind="human",
            principal_id=auth.user_id, invited_by=auth.user_id,
            visible_from_sequence=0,
        )
        floor = 0
    row["_visible_from_sequence"] = floor
    return row


def _apps_payload() -> list[dict]:
    """The app registry, FE-shaped (ADR-562 D6).

    `{slug, resident, name}` per registered app — `name` is the app's own label
    for its resident ("Writer" in Docs), empty when the app did not rename one.
    Served rather than mirrored in TypeScript: a parallel table is the second
    home ADR-562 deleted, and it drifts the moment one side is edited.

    EXPOSED apps only (audited 2026-08-24): `stage: internal` means "absent
    from the served roster" (ADR-592), and this envelope is served to every
    member — an internal app (Supervisor at birth, ADR-603 D4) must not leak
    here. Filtered at the surface row, the same declaration
    `kernel_surface_entries()` honours; an app with NO surface row is not
    visitable and is likewise withheld (fail closed).
    """
    import services.apps  # noqa: F401  (registration side-effect)
    from services.app_stage import is_exposed
    from services.authoring import all_apps
    from services.kernel_surfaces import KERNEL_SURFACES

    rows = {e.get("slug"): e for e in KERNEL_SURFACES}
    return [
        {"slug": a["slug"], "resident": a["resident"], "name": a["name"]}
        for a in all_apps().values()
        if a["slug"] in rows and is_exposed(rows[a["slug"]])
    ]


def _beings_payload() -> list[dict]:
    """Every being, FE-shaped, with provenance and the desks it serves.

    `agents` above is the ROSTER — who a member may INVITE (`offered`). This is
    the fuller answer to "who exists": a housed being is real and answers in
    its app every day, so a surface that lists only the offered ones tells the
    member they have nobody while Designer is mid-conversation with them.

    ADR-601 D4 — two facts are SERVED rather than inferred:
      `kernel` — yarnnn authored this being (so the pane can say so from the
                 FIELD, never from absence-from-a-list, which would have the
                 surface asserting something the API never said).
      `homes`  — a LIST: many-to-one is ordinary since ADR-601 D1, and a being
                 serving no desk gets an empty array. Resolved from the same
                 `register_app` declarations the prompt reads.
    """
    import services.apps  # noqa: F401  (registration side-effect)
    from services.agents_registry import AGENTS, homes_for_agent, is_promoted

    # ADR-602 D3 — a being whose only desk is unpromoted waits with it. Filtered
    # SERVER-side: the pane asks "who works here", and a being the member cannot
    # reach is not an answer to that. Derived from the app's own stage, so
    # promoting the app promotes its voice with no second edit.
    return [
        {
            "slug": r["slug"],
            "name": r["name"],
            "blurb": r["blurb"],
            "icon": r["icon"],
            "offered": bool(r.get("offered")),
            "kernel": bool(r.get("kernel")),
            "homes": homes_for_agent(r["slug"]),
            # ADR-602 D6 — the engine, so a being's page can SAY what runs it
            # rather than implying it. Already public on the lane envelope
            # (`model_names`); no new disclosure.
            "model": r.get("model") or "",
        }
        for r in AGENTS.values()
        if is_promoted(r["slug"])
    ]


def _lane_envelope(auth: UserClient, enabled: bool, lanes: list[dict]) -> dict:
    """The capability envelope around the conversation list. Extracted so the
    empty-cast early return serves the identical shape (one envelope, one
    definition — the FE must never see two payload shapes for one endpoint)."""
    from services.agents_registry import list_agents
    from services.derive_recipes import list_recipes
    from services.lane_runner import (
        LANE_MODELS,
        lane_model_availability,
        offered_lane_models,
    )

    return {
        "enabled": enabled,
        # ADR-558 D1 — `models` IS THE CHAT CHOOSER now. Starting a conversation
        # is picking an ENGINE; the door asks which one. (ADR-460's "the member
        # picks WHO" is preserved where it belongs — `/agents` and app residents
        # — but it was answering the wrong door here: a member who came to use
        # GPT-5 was handed a persona.)
        #
        # ADR-559 D2/D3: the door offers the CURRENT roster (retired engines
        # keep running their own lanes but leave the chooser), and every row
        # carries its availability. Unavailable engines are SERVED, not
        # filtered — the FE greys them with the reason. A member who expects
        # DeepSeek and sees nothing files a bug; one who sees "DeepSeek —
        # unavailable" understands.
        "models": [
            {
                "id": mid,
                "label": meta["label"],
                "vision": bool(meta.get("vision", True)),
                "available": (_avail := lane_model_availability(mid))[0],
                "unavailable_reason": _avail[1],
            }
            for mid, meta in offered_lane_models().items()
        ],
        # ⭐ THE SECOND AUDIENCE — the NAMING table (2026-08-21).
        #
        # `models` above is the CHOOSER, and it is correctly the OFFERED roster.
        # But the FE also used it to NAME an engine (`modelLabel`, the lane
        # header, the filter facet), and those are different questions: a lane's
        # engine is persisted at creation and is a HISTORICAL FACT (ADR-460 D4),
        # so a lane pinned to a RETIRED engine had no row here and fell through
        # to rendering its RAW ID — `anthropic/claude-sonnet-4-6` as a filter
        # chip, provider prefix and all. Not hypothetical: at the ADR-559
        # refresh every live lane was pinned to that engine.
        #
        # `model_names` is the FULL `LANE_MODELS`, id → label, for naming only.
        # This is the same "one dict, two audiences" split `offered_lane_models`
        # already makes (ADR-559 D2) — it was just never carried to the
        # envelope. Deliberately NOT merged into `models`: putting retired rows
        # there would leak them back into the chooser, which D2 forbids.
        "model_names": {mid: meta["label"] for mid, meta in LANE_MODELS.items()},
        # `agents` STAYS, but as the CAST's roster, not the creation chooser:
        # who a member may ADD to a conversation (ADR-495 — a colleague is
        # joined, never chosen at the door). Personas are configured in
        # `/agents`; this is the list of who is available to invite.
        "agents": list_agents(),
        # ADR-562 D6 — the app registry, served so the FE resolves an app's name for
        # its resident from the SAME declaration the prompt uses. Serving it
        # beats a parallel TS table: that is precisely the second home ADR-562
        # deleted, and it would drift the moment one side was edited.
        "apps": _apps_payload(),
        # ADR-600 D6 — every being, with its desk. `agents` is who may be
        # INVITED; this is who EXISTS, so the /agents surface can show a
        # housed being where it lives instead of claiming the member has
        # nobody.
        "beings": _beings_payload(),
        # ADR-450 D5: the Learn-from chooser payload — kernel recipes, served
        # on the capability envelope (no new endpoint, no FE duplication).
        "recipes": list_recipes(),
        "lanes": lanes,
    }


@router.get("/lanes")
async def list_lanes(auth: UserClient, include_bound: bool = False) -> dict:
    """The lane list + capability envelope. `enabled` gates the FE strip —
    lanes exist only where the ADR-408 D4 router is live."""
    from services.lane_runner import LANE_MODELS
    from services.model_router import lanes_enabled

    enabled = lanes_enabled()
    lanes: list[dict] = []
    if enabled:
        # ADR-495 D2 — the list is CAST-SCOPED, not owner-scoped: a
        # conversation you were invited to is yours to see. `user_id` stays on
        # the row as the creator fact; it is no longer the read gate.
        from services.conversation_cast import _svc as _cast_svc

        member_rows = (
            _cast_svc().table("conversation_members")
            .select("conversation_id")
            .eq("principal_id", auth.user_id)
            .eq("member_kind", "human")
            .execute()
        ).data or []
        my_conversations = [m["conversation_id"] for m in member_rows]
        if not my_conversations:
            return _lane_envelope(auth, enabled, [])
        q = (
            auth.client.table("chat_sessions")
            .select("id, user_id, workspace_id, status, context_metadata, created_at, updated_at, summary")
            .in_("id", my_conversations)
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
        # ADR-495 D1 — the cast rides on every row: the list shows WHO is in
        # each conversation, which is the whole object model made visible.
        # One batched read, not N.
        if lanes:
            casts = (
                _cast_svc().table("conversation_members")
                .select("conversation_id, member_kind, principal_id, agent_slug, visible_from_sequence")
                .in_("conversation_id", [ln["id"] for ln in lanes])
                .execute()
            ).data or []
            by_conv: dict[str, list[dict]] = {}
            for c in casts:
                by_conv.setdefault(c["conversation_id"], []).append(c)
            for ln in lanes:
                ln["participants"] = by_conv.get(ln["id"], [])

    return _lane_envelope(auth, enabled, lanes)


@router.post("/lanes")
async def create_lane(req: CreateLaneRequest, auth: UserClient) -> dict:
    from services.agents_registry import resolve_agent
    from services.lane_runner import LANE_MODELS, lane_model_availability
    from services.model_router import lanes_enabled

    if not lanes_enabled():
        raise HTTPException(status_code=403, detail="Lanes are not enabled (router off)")

    # ADR-558 D1/D3 — the door asks WHICH ENGINE. A resident resolves to its
    # model here, server-side; the model stays authoritative on the lane
    # (ADR-460 spec §6: the model is the fact, and the fact is what actually
    # ran — deriving it at turn time would let a registry edit retroactively
    # lie about a past lane's engine).
    model = (req.model or "").strip()
    app_slug = (req.app or "").strip()
    # A BINDING is what makes a lane an app's, and only an app pins a colleague.
    is_bound = bool(
        (req.artifact_path or "").strip()
        or (req.derive_recipe or "").strip()
        or (req.derive_source or "").strip()
    )
    if app_slug and not is_bound:
        # THE ADR-558 D3 LINE, unchanged in substance: a chat lane has no
        # birth-persona: who replies is the cast's answer, joined after
        # creation. Refused loudly rather than ignored — a silently-dropped
        # residency would read as supported and become a bug report (the
        # ADR-460 strict-key precedent).
        raise HTTPException(
            status_code=422,
            detail=(
                "A chat conversation is created with an engine, not a colleague "
                "(ADR-558). Create it with `model`, then add the colleague to "
                "the cast."
            ),
        )
    # ADR-562 D3 — the resident is DERIVED from the app's own declaration, never
    # taken from the client. An unregistered app is a caller bug (the ADR-450
    # precedent: an unknown recipe is a caller bug, not a lane), and refusing
    # beats a plausible default — ADR-548's lesson, that a fallback degrading to
    # a plausible value is worse than one that fails.
    agent_slug = ""
    if app_slug:
        # The package import IS the registration (services/apps/__init__.py) —
        # load-bearing, never prune it as unused. Without it this resolution
        # would depend on whether some OTHER router happened to be imported
        # first, and a valid app would 422 on import order alone.
        import services.apps  # noqa: F401  (registration side-effect)
        from services.authoring import resident_for_app

        agent_slug = resident_for_app(app_slug) or ""
        if not agent_slug:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Unknown app: {app_slug}. An app declares its resident in "
                    "its own module (services/apps/*, ADR-562)."
                ),
            )
    elif (req.derive_recipe or "").strip():
        # ADR-562 D4 — a canvas-less derive lane (it lands in /chat, so no app
        # speaks for it) takes the RECIPE's declared colleague. The app wins
        # when both apply: a derive INTO a canvas is that app's lane, and the
        # recipe is the job it does there (the lane_runner's character-then-job
        # order, resolved one layer up).
        from services.derive_recipes import resident_for_recipe

        agent_slug = resident_for_recipe(req.derive_recipe) or ""
    if agent_slug:
        # Member-first: their named colleagues, then the kernel set.
        agent = resolve_agent(agent_slug)
        if not agent:
            # The ADR-450 precedent: an unknown recipe is a caller bug, not a lane.
            raise HTTPException(status_code=422, detail=f"Unknown agent: {agent_slug}")
        model = agent["model"]
    if not model:
        raise HTTPException(status_code=422, detail="model is required")
    if model not in LANE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown lane model: {model}")
    # ADR-559 D2/D3 — refuse at the DOOR, not mid-turn. A conversation created
    # on a retired or unavailable engine looks fine until the first message,
    # then fails with a stack-shaped error against an empty transcript. Both
    # checks apply to NEW conversations only: an existing lane on a retired
    # engine keeps running (LANE_MODELS is the turn-time whitelist), and a
    # bound app lane resolves its engine from its resident.
    _meta = LANE_MODELS[model]
    if _meta.get("retired"):
        raise HTTPException(
            status_code=422,
            detail=(
                f"{_meta['label']} has been superseded and is no longer offered "
                "for new conversations. Existing conversations on it keep working."
            ),
        )
    _ok, _why = lane_model_availability(model)
    if not _ok:
        raise HTTPException(
            status_code=422,
            detail=_UNAVAILABLE_ENGINE_DETAIL.get(
                _why, f"{_meta['label']} is not available right now."
            ).format(label=_meta["label"]),
        )
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
    # ADR-597 D1 — the resident is NOT stamped. It is a fact about the app,
    # derived from the registration at every read (`_lane_agent`); persisting
    # it here was what stranded live desks on yesterday's declaration. What
    # creation legitimately records: the MODEL (a historical fact — what the
    # lane ran on, ADR-460 spec §6) below, and the CAST row (a membership
    # event — who was invited) further down. `agent_slug` remains resolved
    # above because both of those need it at creation time.
    # ADR-567 D4 — a bound lane carries its BINDING APP. The runner keys the
    # job overlay on it (radar → the desk posture, not Studio's): the agent
    # slug cannot name the app (Docs and Studio share designer), and radar's
    # artifact is plain markdown, so the document-derived resolution
    # (data-template) has nothing to read. Selects the JOB only — the resident
    # was resolved above, the engine rides the resident.
    if app_slug and is_bound:
        lane_meta["app"] = app_slug
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
    # The cast rows take the workspace THE ROW ACTUALLY GOT, not the local `ws`
    # (which is None when the acting binding didn't resolve). Migration 203's
    # BEFORE INSERT trigger fills it from the owner, so the stored value is
    # authoritative and always present — and since migration 228 the cast's
    # `workspace_id` is NOT NULL, so guessing here would be a constraint error.
    ws = created.get("workspace_id") or ws
    # ADR-495 D1 — the cast is born with the conversation: the creator, always.
    # Window 0 (they see everything from turn one — nothing prior to withhold).
    #
    # ADR-558 D3: a CHAT lane's cast is born with ONE member — the creator. No
    # agent, because a chat conversation has no birth-persona; the member adds
    # a colleague when they want one. `agent_slug` here is only ever an app's
    # resident (bound lanes), which IS invited, because the app's job is that
    # colleague's job.
    from services.conversation_cast import add_participant

    add_participant(
        created["id"], workspace_id=ws, member_kind="human",
        principal_id=auth.user_id, invited_by=auth.user_id, visible_from_sequence=0,
    )
    if agent_slug:
        add_participant(
            created["id"], workspace_id=ws, member_kind="agent",
            agent_slug=agent_slug, invited_by=auth.user_id, visible_from_sequence=0,
        )
    logger.info("[LANE] created lane=%s model=%s ws=%s", created["id"][:8], model, (ws or "-")[:8])
    return _lane_row_to_dict(created)


@router.get("/lanes/{lane_id}/messages")
async def lane_messages(lane_id: str, auth: UserClient) -> dict:
    lane = _get_lane(auth, lane_id)
    # ADR-495 D2 — the visibility window, enforced at the read. `_get_lane`
    # answered "may they read at all"; this answers "from where". A window of
    # 0 (every pre-existing participant) is a no-op filter.
    floor = int(lane.get("_visible_from_sequence") or 0)
    res = (
        auth.client.table("session_messages")
        .select("id, role, content, metadata, created_at")
        .eq("session_id", lane_id)
        .gte("sequence_number", floor)
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


def _cast_roster(auth: UserClient, slugs: list[str]) -> dict[str, dict]:
    """slug → character, for the Agents in this cast.

    Addressing matches on the DISPLAY NAME as well as the slug, because the
    member reads "Lisa" and never sees `lisa` — and for kernel rows the two
    differ outright (`sonnet` is displayed "Thinker"). Best-effort: a roster
    that fails to load degrades to slug-only matching, never a failed turn.
    """
    if not slugs:
        return {}
    try:
        from services.agents_registry import resolve_agent

        out: dict[str, dict] = {}
        for s in slugs:
            character = resolve_agent(s)
            if character:
                out[s] = character
        return out
    except Exception:  # noqa: BLE001 — degrade to slugs, never fail the turn
        logger.warning("[ADDRESSING] roster unavailable; matching on slug only")
        return {}


def _last_responder(auth: UserClient, lane_id: str, cast_agents: list[str]) -> Optional[str]:
    """The Agent that answered most recently in this conversation, if it is
    still in the cast.

    Continuity: with several Agents present and no mention, the conversation
    continues with whoever you were just talking to. Requiring a mention on
    every turn would make addressing a per-turn picker — the thing ADR-492 D3
    explicitly refuses.

    Reads the `agent_slug` this route now writes onto assistant rows. Rows
    written before that (every row predating this change) carry no slug and
    simply yield None — the ladder then falls to join order, i.e. exactly
    today's behavior. No backfill needed.
    """
    if len(cast_agents) < 2:
        return None  # the sole-agent and no-agent rungs don't need this read
    try:
        res = (
            auth.client
            .table("session_messages")
            .select("metadata")
            .eq("session_id", lane_id)
            .eq("role", "assistant")
            .order("sequence_number", desc=True)
            .limit(12)
            .execute()
        )
        for row in res.data or []:
            slug = ((row.get("metadata") or {}).get("agent_slug") or "").strip()
            if slug and slug in cast_agents:
                return slug
    except Exception:  # noqa: BLE001 — continuity is a nicety, never a blocker
        logger.warning("[ADDRESSING] last-responder read failed for %s", lane_id)
    return None


def _fetch_history(
    auth: UserClient, lane_id: str, *, before_sequence: Optional[int] = None,
    visible_from: int = 0,
) -> list[dict]:
    """History window: user/assistant text only — tool traffic is per-turn
    working state, never persisted (the transcript is not shared memory,
    and it is not the tool ledger either; writes live in revisions).

    `visible_from` (ADR-495 D2) clamps the history to what the ACTING
    participant may read. Without it, a participant joined at "from now" could
    address an Agent and receive an answer conditioned on turns they cannot
    see — the window would be cosmetic. 0 is a no-op.
    """
    q = (
        auth.client.table("session_messages")
        .select("role, content, sequence_number")
        .eq("session_id", lane_id)
        .gte("sequence_number", visible_from)
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
        # SERVICE CLIENT, deliberately: migration 228 gives participants no
        # DELETE policy on `session_messages` — a transcript is append-only
        # (ADR-406's appender rule). Truncation is a system-mediated act, gated
        # by the author check in `lane_turn` before it runs. With `auth.client`
        # this silently deletes NOTHING and edit-and-resend duplicates the tail.
        _conversation_write_client(auth).table("session_messages")
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
        # The binding is PASSED, not inferred (ADR-501, commit 2a8c1d7). Dropping
        # the second arg left `effective_workspace_id` to fall through to the
        # contextvar/owner path — so a member attaching an image in a GRANTED
        # workspace resolved their OWN and got "Attachment not found".
        .eq(*substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None)))
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
            # PASSED, not inferred — see `_resolve_blob_storage_path` above.
            .eq(*substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None)))
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
        _conversation_write_client(auth).table("chat_sessions").update(
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
    # ADR-522 D2 — WHERE the member is standing, this turn. Transient: it is
    # read off the request and threaded in, never off `lane_meta` (durable).
    # A regenerate passes None — focus is per-turn and never persisted, so
    # there is nothing to replay.
    focus: Optional[LaneFocus] = None,
) -> StreamingResponse:
    """The one streaming turn core — serves POST messages AND regenerate.

    SSE grammar mirrors the steward (`data: {json}\\n\\n`, frames keyed by
    their JSON discriminator):
      - {"speaker": {"agent_slug", "reason"}}
                                       — WHO is answering, sent BEFORE the
                                         first delta so the in-flight bubble is
                                         attributed the moment it appears.
                                         Added 2026-08-14 with addressing: the
                                         server always knew the responder and
                                         never put it on the wire, so a live
                                         reply from Lisa rendered under the
                                         lane's engine label. Absent for a
                                         direct (agent-less) conversation.
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

    # WHO IS IN THIS CONVERSATION decides both questions below: whether anyone
    # auto-replies, and WHICH Agent does (ADR-495 D1/D3 — the cast IS the
    # conversation; ADR-408 A2 — the engine is the member's hands, never an
    # uninvited participant).
    #
    # Read ONCE, here. This used to be a `member_kind` count feeding a single
    # boolean, while the REPLIER came from `lane_meta["agent"]` — the
    # creation-time scalar ADR-495 D3 retired into the cast. The split meant an
    # Agent added via CastBar after creation never replied (the cast said yes,
    # lane_meta said nobody), and two Agents in a cast was unrepresentable.
    # One read, one source of truth.
    from services.conversation_cast import agent_slugs, list_participants

    lane_id = lane["id"]
    lane_meta = (lane.get("context_metadata") or {}).get("lane") or {}
    # ADR-597 D1 — the lane's resident, derived from the registration (see
    # _lane_agent). Used as the responder fallback and as the pin-comparison
    # baseline below, so a registration change reaches a live desk's TURN,
    # not just its label.
    lane_agent = _lane_agent(lane_meta)

    try:
        cast = list_participants(lane_id)
    except Exception:  # noqa: BLE001 — cast unreadable → the lane's own Agent
        cast = []
    # ADR-605 — human cast rows gain their display label here, so the same
    # addressing grammar that routes an @agent to a turn can resolve an
    # @person for the ATTENTION stamp below. Best-effort: unlabelled rows
    # just leave those mentions unresolved.
    from services.mentions import (
        enrich_cast_labels, fire_and_forget, mentioned_humans, notify_mentioned,
    )

    cast = enrich_cast_labels(cast)
    humans = sum(1 for c in cast if c.get("member_kind") == "human")
    cast_agents = agent_slugs(cast)
    # ADR-492 D3 / ADR-495 D3, finally built: ADDRESSING selects who answers.
    # This was `cast_agents[0]` — join order, unconditionally — so the
    # first-invited Agent answered every turn forever and every other face in
    # the cast was structurally unreachable. The observed failure: a member
    # typed "@lisa can you hear me" and Thinker replied that no such agent
    # exists (correctly, from inside its own prompt — see the cast frame in
    # `lane_runner.build_lane_conventions`).
    #
    # The lane's creation-time Agent is still the FALLBACK for pre-cast lanes
    # (Studio/derive bind a model with no participant rows) and an unreadable
    # cast. When the cast has Agents, the cast wins. `_last_responder` keeps a
    # conversation with the SAME Agent going without re-addressing every turn —
    # the picker ADR-492 D3 refused.
    from services.addressing import select_responder

    cast_roster = _cast_roster(auth, cast_agents)
    responder, responder_reason = select_responder(
        content,
        cast,
        roster=cast_roster,
        fallback=_last_responder(auth, lane_id, cast_agents) or lane_agent,
    )
    # Nobody replies when the conversation holds people and no Agent. A solo
    # cast keeps today's behavior (the engine IS that conversation). Add an
    # Agent and replies begin; remove it and they stop — stateless and
    # retroactive, so existing person-conversations became DMs with no
    # migration. Zero-cost path: no model call, so it runs BEFORE the draw gate.
    direct = humans >= 2 and not cast_agents

    if persist_user:
        # ONE user-row write for every conversation shape (the fix for the
        # group cell, audited 2026-07-30). This lived on the direct branch
        # ALONE, so a conversation with 2+ humans AND an Agent — the ordinary
        # group chat — wrote its user rows with `authored_by="operator"` and NO
        # `author_principal_id`. The FE aligns own-vs-other on that field, so
        # every participant's message rendered right-aligned as the viewer's
        # own and the transcript was unreadable. The old comment here said
        # "attribution matters in a multi-human transcript" — true on both
        # branches, implemented on one.
        #
        # `member:{user_id}` is the ADR-209 member form and is correct at every
        # cast size: a turn is authored by the human who typed it, whatever else
        # is in the room. There is no longer an "operator" spelling of a lane
        # user row.
        meta: dict = {"author_principal_id": auth.user_id}
        if attachments_meta:
            meta["attachments"] = attachments_meta
        # ADR-605 — the mention STAMP: addressing metadata parsed once and
        # stored with the content it derives from (the ADR-492 D3 split: the
        # @token stays verbatim in the text; the attention consequence is the
        # kernel's, derived per viewer from this stamp). The author is
        # excluded at stamp time — they are present (ADR-405 D4).
        user_mentions = mentioned_humans(content, cast, exclude=auth.user_id)
        if user_mentions:
            meta["mentions"] = user_mentions
        write_narrative_entry(
            auth.client, lane_id,
            role="user",
            summary=content,
            pulse="addressed",
            authored_by=f"member:{auth.user_id}",
            extra_metadata=meta,
        )
        if user_mentions:
            # The email consequence, off the turn's critical path — the one
            # chokepoint gates by each recipient's dial and fails closed.
            fire_and_forget(notify_mentioned(
                auth.client,
                workspace_id=lane.get("workspace_id"),
                conversation_id=lane_id,
                conversation_name=lane_meta.get("name") or "a conversation",
                mentioned=user_mentions,
                author_label=(getattr(auth, "email", None) or "A teammate").split("@")[0],
            ))

    if direct:
        async def dm_stream():
            # `direct: true` tells the FE this was a broadcast, not a turn —
            # drop the reply placeholder instead of marking "[no reply]".
            done: dict = {
                "done": True, "direct": True,
                "rounds": 0, "tools_called": [], "artifacts": [],
            }
            if renamed:
                done["lane_name"] = renamed
            yield f"data: {json.dumps(done)}\n\n"

        return StreamingResponse(dm_stream(), media_type="text/event-stream")

    # THE draw gate (ADR-445 §9 closed / ADR-491 Phase 3) — a lane turn is a
    # costed, member-attributed draw of the shared pool; gate BEFORE the stream
    # starts (this runs in the handler body, so a block is a clean 402, not a
    # mid-stream error). Covers both entries (turn + regenerate) — they both
    # come through this core.
    from services.platform_limits import check_draw
    draw_ok, draw_reason, draw_detail = check_draw(
        auth.client,
        auth.user_id,
        workspace_id=getattr(auth, "workspace_id", None),
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

    # `lane_id` + `lane_meta` are resolved above, before the cast read.
    model = lane_meta.get("model") or ""
    # The RESPONDER's own engine, when the cast named someone other than the
    # lane's own resident (i.e. an Agent invited later). ADR-460's rule
    # that a lane's model is pinned is about not letting a registry edit
    # retroactively relabel PAST turns — it is not a rule that a newly invited
    # colleague must run on the previous one's engine. The pin still holds for
    # the lane's own resident: `responder == lane_agent` (ADR-597: derived,
    # never the creation-time stamp) resolves to the same stored model and
    # nothing changes.
    if responder and responder != lane_agent:
        from services.agents_registry import resolve_agent

        try:
            _resolved = resolve_agent(responder)
        except Exception:  # noqa: BLE001 — registry read is best-effort
            _resolved = None
        if _resolved and _resolved.get("model"):
            model = _resolved["model"]

    # ADR-495 D2 — the acting participant's window clamps the model's context,
    # so an answer is never conditioned on turns the asker cannot see.
    history = _fetch_history(
        auth, lane_id,
        before_sequence=history_before_sequence,
        visible_from=int(lane.get("_visible_from_sequence") or 0),
    )

    # The member's message was persisted above — ONE write for every cast
    # shape. The second `write_narrative_entry` that used to live here (with
    # `authored_by="operator"` and no `author_principal_id`) is DELETED, not
    # kept alongside: two spellings of the same row is exactly the ambiguity
    # that made the group cell unreadable.

    async def event_stream():
        def sse(obj: dict) -> str:
            return f"data: {json.dumps(obj)}\n\n"

        accumulated: list[str] = []
        tools_called: list[str] = []
        artifacts: list[str] = []
        rounds = 0
        errored: Optional[str] = None
        persisted = False
        spoke = False  # the speaker frame is sent once, before the first delta

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
            # WHO spoke, and WHY they were the one. Before this, `responder`
            # was computed and thrown away: the row recorded only the ENGINE
            # (`member:{id} via {model}`), so a transcript could never say
            # which cast member answered — and with addressing live, two
            # Agents' replies would render identically on reload. The reason
            # rides along so "why did Lisa answer?" is a record lookup rather
            # than a re-derivation from the text months later.
            if responder:
                extra["agent_slug"] = responder
                extra["responder_reason"] = responder_reason
            # ADR-605 — an agent's turn mentions people the same way a
            # member's does (the derivation never asks who authored the
            # mentioning turn). The acting member is excluded at stamp time:
            # they are watching this reply arrive.
            reply_mentions = mentioned_humans(reply, cast, exclude=auth.user_id)
            if reply_mentions:
                extra["mentions"] = reply_mentions
            write_narrative_entry(
                auth.client, lane_id,
                role="assistant",
                summary=reply or "[no reply]",
                pulse="addressed",
                authored_by=lane_caller_identity(auth.user_id, model),
                extra_metadata=extra,
            )
            if reply_mentions:
                fire_and_forget(notify_mentioned(
                    auth.client,
                    workspace_id=lane.get("workspace_id"),
                    conversation_id=lane_id,
                    conversation_name=lane_meta.get("name") or "a conversation",
                    mentioned=reply_mentions,
                    author_label=(
                        (cast_roster.get(responder) or {}).get("name") or responder or "An agent"
                    ),
                ))
            try:
                _conversation_write_client(auth).table("chat_sessions").update(
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
                # ADR-440 D3 — a bound lane's turns carry the Studio posture;
                # ADR-567 D4 — unless its binding app declares another job
                # (radar → the desk posture).
                artifact_path=lane_meta.get("artifact_path"),
                app=lane_meta.get("app"),
                # ADR-450 D3 — a derive-bound lane's turns carry the recipe.
                derive_recipe=lane_meta.get("derive_recipe"),
                derive_source=lane_meta.get("derive_source"),
                # ADR-522 — WHERE the member is standing, this turn. Read off
                # the request (transient), never off `lane_meta` (durable):
                # the binding says WHICH artifact, the focus says where in it.
                focus=focus.model_dump() if focus else None,
                # ADR-460 D4 — WHO the member is talking to: the Agent's
                # posture composes at turn time from this slug. ADR-495 D3: the
                # slug comes from the CAST (`responder`, resolved above), so an
                # Agent invited after creation actually answers; `lane_meta` is
                # only the fallback for pre-cast (Studio/derive) lanes.
                agent=responder,
                # ADR-495 D3 — the room, so the frame can name who else is in
                # it. Without this the Agent believes the conversation is a
                # dyad and denies that a cast-mate exists.
                cast=cast,
                responder_reason=responder_reason,
                # W0 / ADR-457 D8 — the falsifier join key: this turn's cost
                # row carries the session it served, so the surface that asked
                # (think / make / derive) is derivable at read time.
                session_id=lane_id,
            ):
                if not spoke and responder:
                    # WHO, before WHAT. The bubble must never render an
                    # anonymous spinner while a named colleague is answering —
                    # that is the shape that read "Gemini Flash is working…"
                    # in a conversation with Lisa.
                    spoke = True
                    yield sse({"speaker": {
                        "agent_slug": responder, "reason": responder_reason,
                    }})
                if kind == "delta":
                    accumulated.append(payload)
                    yield sse({"text_delta": payload})
                elif kind == "tool":
                    tools_called.append(payload["name"])
                    # The step frame is an OBJECT (name + optional subject).
                    # `tool` stays a bare string for the older readers that
                    # match on `typeof evt.tool === "string"`; the object rides
                    # beside it as `tool_step`, so a client deployed before this
                    # change keeps working and one deployed after gets the
                    # subject. (A commit is not a deploy — the two halves of
                    # this seam ship independently.)
                    yield sse({
                        "tool": payload["name"],
                        "tool_step": {
                            "name": payload["name"],
                            "subject": payload.get("subject"),
                        },
                    })
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
            # `exception()` not `warning()`: this is a catch-all, so it swallows
            # our OWN bugs (NameError/AttributeError) alongside provider faults.
            # Stringifying without the frame is how `name 'req' is not defined`
            # reached an operator's chat surface with nothing to locate it by.
            logger.exception("[LANE stream] turn failed (lane=%s)", lane_id[:8])
            errored = str(exc)
            yield sse({"error": errored})

        persist_reply(stopped=False)

        done: dict = {
            "done": True,
            "rounds": rounds,
            "tools_called": tools_called,
            "artifacts": artifacts,
        }
        if responder:
            # Also on the terminal frame, not only the pre-delta one: a
            # tool-only turn yields no delta, and a client that reconnects
            # mid-stream would otherwise finalize an unattributed bubble.
            done["agent_slug"] = responder
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
            .select("id, role, sequence_number, metadata")
            .eq("session_id", lane_id)
            .eq("id", req.replace_from_message_id)
            # ADR-495 D2 — a member may only edit-and-resend from a turn INSIDE
            # their window. The author check below is necessary but not
            # sufficient: without this, a participant joined at "from now" could
            # name a pre-window message id and truncate the transcript from a
            # point they were never shown (the tail delete that follows is
            # unclamped by design).
            .gte("sequence_number", int(lane.get("_visible_from_sequence") or 0))
            .limit(1)
            .execute()
        )
        row = (row_res.data or [None])[0]
        if not row:
            raise HTTPException(status_code=404, detail="Message not found in this lane")
        if row.get("role") != "user":
            raise HTTPException(status_code=422, detail="Only your own messages can be edited")
        # Multi-human conversations: "your own" means AUTHORED BY YOU, not any
        # user row — edit-and-resend truncates the tail, which must never
        # reach another participant's words. Rows without the stamp predate
        # multi-human casts (solo lanes) and are the editor's own.
        _author = ((row.get("metadata") or {}).get("author_principal_id"))
        if _author and _author != auth.user_id:
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
        focus=req.focus,
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
        # ADR-495 D2 — regenerate reruns the last user turn THIS participant can
        # see. Unclamped, a member joined at "from now" on a quiet conversation
        # would regenerate off a pre-window message — reading it back in the
        # process, which is the disclosure the window exists to prevent.
        .gte("sequence_number", int(lane.get("_visible_from_sequence") or 0))
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


# The member-agent CRUD (`POST/PATCH /lane-agents`, the "make your own" door)
# is DELETED by ADR-599 D2 with the rest of the member-agent machinery. If
# member agents return, they return app-paired, built against the ADR-596
# scaffold — not resurrected from this file's history.


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
        _conversation_write_client(auth).table("chat_sessions").update(
            {"context_metadata": merged}
        ).eq("id", lane_id).execute()
        lane = {**lane, "context_metadata": merged}
    return _lane_row_to_dict(lane)


@router.get("/lanes/search")
async def search_lanes(q: str, auth: UserClient) -> dict:
    """Phase-A hygiene: search across the conversations the viewer PARTICIPATES
    in, in the acting workspace — transcript content match (ILIKE), first
    snippet per conversation. Cast-scoped per ADR-495 D2 (membership is read
    permission), and window-clamped so search never surfaces a turn the viewer
    cannot open."""
    query = (q or "").strip()
    if len(query) < 2:
        return {"matches": []}

    from services.conversation_cast import _svc as _cast_svc

    member_rows = (
        _cast_svc().table("conversation_members")
        .select("conversation_id, visible_from_sequence")
        .eq("principal_id", auth.user_id)
        .eq("member_kind", "human")
        .execute()
    ).data or []
    if not member_rows:
        return {"matches": []}
    floors = {m["conversation_id"]: int(m.get("visible_from_sequence") or 0) for m in member_rows}

    lq = (
        auth.client.table("chat_sessions")
        .select("id")
        .in_("id", list(floors.keys()))
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
        .select("session_id, content, created_at, sequence_number")
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
        # ADR-495 D2 — never surface a turn below the viewer's window.
        if int(r.get("sequence_number") or 0) < floors.get(sid, 0):
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
    lane = _get_lane(auth, lane_id)
    # ADR-495 D2 — the archiver summarizes only what THEY may read. The
    # unclamped-read defect this guards was first audited on the retired
    # `settle` verb (2026-07-30, ADR-507): the summary is durable and shown to
    # the cast, so distilling pre-window turns into it would leak them.
    floor = int(lane.get("_visible_from_sequence") or 0)

    # Best-effort summary — never block archive on it.
    summary: Optional[str] = None
    try:
        from datetime import date as _date
        from services.session_continuity import generate_session_summary

        msgs = (
            auth.client.table("session_messages")
            .select("role, content, sequence_number")
            .eq("session_id", lane_id)
            .gte("sequence_number", floor)
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
    _conversation_write_client(auth).table("chat_sessions").update(update).eq("id", lane_id).execute()
    return {"success": True, "summary": summary}


# ---------------------------------------------------------------------------
# The cast — ADR-495 D1/D3. ONE species-blind invite.
#
# There is no "invite a person" endpoint and no "invite an agent" endpoint:
# there is `POST /lanes/{id}/participants`, which takes a participant. The
# class routes the row to the right column and pre-selects a default window;
# it never decides whether the invite is allowed or what the invite MEANS.
# ---------------------------------------------------------------------------

class ParticipantRequest(BaseModel):
    kind: str                                    # 'human' | 'agent'
    principal_id: Optional[str] = None
    agent_slug: Optional[str] = None
    # ADR-495 D2 — the visibility window, chosen by the inviter at invite time.
    # Omitted → the class default (agent: full history; human: from now).
    # `0` is an explicit "share full history" and is honored as given.
    visible_from_sequence: Optional[int] = None


def _workspace_humans(auth: UserClient, workspace_id: Optional[str]) -> dict[str, str]:
    """Active human grant-holders: principal_id → role. The commons boundary
    (ADR-408 D1) — a workspace grant is the prerequisite for being invited to
    a conversation inside it."""
    if not workspace_id:
        return {auth.user_id: "owner"}
    from services.supabase import get_service_client

    rows = (
        get_service_client()
        .table("principal_grants")
        .select("principal_id, role, status")
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .execute()
    ).data or []
    return {r["principal_id"]: r["role"] for r in rows if r.get("role") in ("owner", "member")}


@router.get("/lanes/{lane_id}/participants")
async def list_conversation_participants(lane_id: str, auth: UserClient) -> dict:
    """The cast. One list — humans and Agents, in join order."""
    from services.conversation_cast import list_participants

    _get_lane(auth, lane_id)
    return {"participants": list_participants(lane_id)}


@router.post("/lanes/{lane_id}/participants")
async def add_conversation_participant(
    lane_id: str, req: ParticipantRequest, auth: UserClient
) -> dict:
    """Add a participant — human or Agent, one mechanism (ADR-495 D3).

    Adding a participant grants them read access from their window forward.
    That is the whole act: no scope flip, no fork, no metered distillation, no
    second conversation.
    """
    from services.conversation_cast import add_participant, list_participants

    lane = _get_lane(auth, lane_id)
    # THE CONVERSATION'S workspace, never the inviter's acting one. This read
    # `lane.get("workspace_id") or _acting_workspace(auth)`, so inviting into a
    # workspace-less conversation stamped the participant row with whatever
    # workspace the INVITER happened to be acting in — a cast row that disagreed
    # with its own parent. Harmless while the column was never read; migration
    # 228 makes it load-bearing (NOT NULL + FK, and the workspace bound in the
    # RLS policy), so the fallback is removed rather than left as a trap.
    #
    # `_get_lane` has already refused a conversation whose workspace doesn't
    # match the acting one (and, since 228, one with no workspace at all cannot
    # exist: every live row is bound, migration 203's trigger fills it on
    # insert). So the parent's value is both correct and always present.
    ws = lane.get("workspace_id")
    if not ws:
        raise HTTPException(
            status_code=409,
            detail="This conversation isn't bound to a workspace — reopen it and try again.",
        )

    kind = (req.kind or "").strip().lower()
    if kind == "human":
        if not req.principal_id:
            raise HTTPException(status_code=422, detail="A person needs principal_id")
        if req.principal_id not in _workspace_humans(auth, ws):
            raise HTTPException(
                status_code=422,
                detail="That person isn't in this workspace — invite them to the workspace first.",
            )
    elif kind == "agent":
        if not req.agent_slug:
            raise HTTPException(status_code=422, detail="An agent needs agent_slug")
        # ADR-600 D3 — the door asks the FIELD, not mere resolvability. Before
        # this, it gated on `resolve_agent`, which resolves EVERY being: a
        # desk's resident was accepted into any chat lane's cast while the
        # roster offered nobody, so the API contradicted its own surface (the
        # ADR-373 D6 incorrect-success class). `offered` is the same question
        # `list_agents` answers, asked at the door.
        from services.agents_registry import resolve_agent

        _being = resolve_agent(req.agent_slug)
        if _being is None:
            raise HTTPException(status_code=422, detail=f"No agent called '{req.agent_slug}'")
        if not _being.get("offered"):
            # Refused with the REASON — a resident is not missing, it is
            # housed. The generic "no agent called…" would read as a typo and
            # send the member looking for a different spelling.
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{_being.get('name') or req.agent_slug} works at a desk — "
                    "you meet them in their app, not by inviting them to a "
                    "conversation."
                ),
            )
    else:
        raise HTTPException(status_code=422, detail=f"Unknown participant kind: {req.kind}")

    result = add_participant(
        lane_id,
        workspace_id=ws, member_kind=kind, invited_by=auth.user_id,
        principal_id=req.principal_id if kind == "human" else None,
        agent_slug=req.agent_slug if kind == "agent" else None,
        visible_from_sequence=req.visible_from_sequence,
    )
    return {
        "added": result["added"],
        "participant": result["participant"],
        "participants": list_participants(lane_id),
    }


@router.delete("/lanes/{lane_id}/participants")
async def remove_conversation_participant(
    lane_id: str,
    auth: UserClient,
    principal_id: Optional[str] = None,
    agent_slug: Optional[str] = None,
) -> dict:
    """Remove a participant. Ends FUTURE read access; it does not un-read what
    was already seen (ADR-495 D6 — an honest limit, stated not implied).

    The last human may not be removed: a conversation with no human participant
    would be unreachable by anyone, which is deletion wearing another name.
    """
    from services.conversation_cast import human_ids, list_participants, remove_participant

    _get_lane(auth, lane_id)
    if bool(principal_id) == bool(agent_slug):
        raise HTTPException(
            status_code=422, detail="Pass exactly one of principal_id / agent_slug"
        )
    if principal_id:
        humans = human_ids(list_participants(lane_id))
        if humans == [principal_id]:
            raise HTTPException(
                status_code=422,
                detail="That's the last person in this conversation — archive it instead.",
            )
    removed = remove_participant(
        lane_id, principal_id=principal_id, agent_slug=agent_slug
    )
    return {"removed": removed, "participants": list_participants(lane_id)}
