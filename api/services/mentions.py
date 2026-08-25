"""Mentions — the attention half of the @ gesture (ADR-605; ADR-492 D3 built).

A mention is TWO facts split across the app/OS line (ADR-492 D3):

- **Addressing metadata** — authored content inside the Conversation grammar,
  species-blind: you address a person or a named hand with the same gesture.
  Owned by Chat (`services/addressing.py` parses it; nothing is rewritten).
- **The attention consequence** — the kernel's. An @agent routes a TURN (the
  mention IS the human act that fires it — never-ambient holds); an @human
  routes ATTENTION: the mention lands in that person's To-do derivation and,
  dial permitting, an email rides the ONE chokepoint
  (`send_notification(kind="mentions")`).

STORAGE MODEL (the DP29 line this module holds):

- The mention FACT is stamped on the message row at write time
  (`session_messages.metadata.mentions = [principal_id, ...]`) — parsed-once
  addressing metadata living WITH the content it derives from, exactly like
  `agent_slug`/`responder_reason` already do. It is not a second store: the
  message IS the substrate.
- The attention surface is DERIVED per viewer at read time. No mention inbox
  table, no per-mention read flags (ADR-492 D3). Two facts stay distinct
  (ADR-492 §7): the BADGE keys on the attention cursor ("unseen"); TO-DO
  MEMBERSHIP keys on RESOLUTION — a mention never silently clears by
  scroll-by. Resolution is derivable (the viewer spoke in that conversation
  after the mention) or explicit (a "Done" act advancing the per-conversation
  resolution cursor in `member_state['mention_resolutions']` — viewer
  presentation state, the ADR-407 cursor precedent, never authorization).

WHO IS STAMPED: mentioned humans in the CAST, minus the acting member (they
are present — being told what they just did or just watched violates ADR-405
D4). Cast membership already scopes disclosure: you can only meaningfully
mention someone who can read the conversation, and mentioning a non-member
resolves to `unresolved` — it never invites (adding a participant is an
explicit disclosure decision with a visibility window, ADR-495 D2; a mention
must not perform it as a side effect).

SPECIES-AGNOSTIC BY CONSTRUCTION: the derivation never asks who AUTHORED the
mentioning turn — a teammate's @you and an agent's @you land identically.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)

#: member_state key holding {conversation_id: resolved_up_to_sequence} — the
#: viewer's explicit "dealt with it" floor, per (workspace, principal).
MENTION_RESOLUTIONS_KEY = "mention_resolutions"

#: At most one mention email per (recipient, conversation) per this window —
#: derived from the transport ledger itself (the `notifications` rows), never
#: a new store. An active back-and-forth must not become an email per turn;
#: the in-app derivation stays complete regardless.
EMAIL_SUPPRESSION_MINUTES = 60

_EXCERPT_CHARS = 140
_SCAN_LIMIT = 200


def _svc():
    from services.supabase import get_service_client

    return get_service_client()


# ---------------------------------------------------------------------------
# Write-time half: labels, extraction, stamping
# ---------------------------------------------------------------------------

def enrich_cast_labels(cast: list[dict]) -> list[dict]:
    """Attach `display_name` to human cast rows so the addressing grammar can
    match people server-side.

    `conversation_members` stores no label (identity is the principal id);
    handles come from THE ONE resolver (`principal_display.resolve_member_names`
    — full name first, then the email local-part), the same source the FE
    roster renders, so the menu and the parser agree on what a person's
    handle is. Best-effort: an admin-API failure leaves rows unlabelled and
    those mentions simply unresolved — never an error on the turn path.
    """
    human_ids = [
        p.get("principal_id")
        for p in cast or []
        if p.get("member_kind") == "human" and p.get("principal_id")
    ]
    if not human_ids:
        return cast
    try:
        from services.principal_display import resolve_member_names

        names = resolve_member_names(_svc(), human_ids)
    except Exception as exc:  # noqa: BLE001 — labels are best-effort
        logger.warning("[MENTIONS] cast label resolution failed: %s", exc)
        names = {}
    out: list[dict] = []
    for p in cast:
        pid = p.get("principal_id")
        if p.get("member_kind") == "human" and pid in names and not p.get("display_name"):
            q = dict(p)
            q["display_name"] = names[pid]
            out.append(q)
        else:
            out.append(p)
    return out


def mentioned_humans(
    content: str, cast: list[dict], *, exclude: Optional[str] = None
) -> list[str]:
    """The humans this text mentions, as principal ids — the stamp value.

    `exclude` is the acting member: they are present at authoring time, and a
    mention of the present is not an attention event (ADR-405 D4). The @token
    itself stays verbatim in the content — this is metadata, not a rewrite.
    """
    from services.addressing import resolve_address

    resolved = resolve_address(content or "", cast)
    return [h for h in resolved["humans"] if h and h != exclude]


# ---------------------------------------------------------------------------
# Outbound half: the email consequence (through the ONE chokepoint)
# ---------------------------------------------------------------------------

_BACKGROUND_TASKS: set = set()


def fire_and_forget(coro) -> None:
    """Run an outbound consequence off the turn's critical path.

    A member's turn must not wait on Resend latency; a failed email is a
    degradation the log records, never a failed turn. Task refs are held so
    the loop cannot garbage-collect a running send.
    """
    try:
        task = asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        # No running loop (sync caller / tests) — the in-app derivation is
        # complete without the email; skip rather than block.
        return
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


def _recent_mention_email_exists(
    db_client, user_id: str, conversation_id: str
) -> bool:
    """Suppression, derived from the transport ledger (no new state).

    `db_client` must be the SERVICE client — a user-scoped client's RLS view
    of `notifications` is "own rows only", which for the AUTHOR is always
    empty over the RECIPIENT's rows, i.e. suppression that never suppresses.
    """
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=EMAIL_SUPPRESSION_MINUTES)
    ).isoformat()
    try:
        rows = (
            db_client.table("notifications")
            .select("id")
            .eq("user_id", user_id)
            .eq("source_type", "mention")
            .eq("source_id", conversation_id)
            .gte("created_at", cutoff)
            .limit(1)
            .execute()
        ).data
        return bool(rows)
    except Exception as exc:  # noqa: BLE001 — an unreadable ledger must not double-email
        logger.warning("[MENTIONS] suppression read failed — suppressing: %s", exc)
        return True


async def notify_mentioned(
    *,
    workspace_id: Optional[str],
    conversation_id: str,
    conversation_name: str,
    mentioned: Iterable[str],
    author_label: str,
) -> int:
    """Email each mentioned human, dial permitting — one recipient at a time
    through `send_notification(kind="mentions")` (ADR-593 D3: gate → record →
    send; fails closed on an unreadable pref store). Returns sends attempted.

    Pointer-only (ADR-202): the email says who and where, never the content.

    NO client parameter — the seam resolves the SERVICE client itself (the
    `conversation_cast._svc` rule: taking the client as a parameter makes the
    wrong client expressible). This consequence acts on the RECIPIENT — their
    prefs (`member_state` is service-role-only RLS), their address
    (`auth.admin`), their transport rows — none of which the AUTHOR's
    user-scoped client can read. The first prod drive proved it: the author's
    client resolved "No email for user" on a recipient with a real address.
    """
    from services.notifications import send_notification

    svc = _svc()
    sent = 0
    for user_id in dict.fromkeys(mentioned):  # ordered dedupe
        try:
            if _recent_mention_email_exists(svc, user_id, conversation_id):
                continue
            result = await send_notification(
                svc,
                user_id,
                f"{author_label} mentioned you in “{conversation_name}”",
                kind="mentions",
                urgency="normal",
                context={"conversation_id": conversation_id},
                source_type="mention",
                source_id=conversation_id,
                workspace_id=workspace_id,
            )
            if result.status in ("sent", "pending"):
                sent += 1
        except Exception as exc:  # noqa: BLE001 — one recipient's failure never blocks the next
            logger.warning("[MENTIONS] notify failed for %s: %s", str(user_id)[:8], exc)
    return sent


# ---------------------------------------------------------------------------
# Read-time half: the per-viewer derivation
# ---------------------------------------------------------------------------

def unresolved_from(
    rows: list[dict],
    *,
    floors: dict,
    reply_floors: dict,
    resolutions: dict,
) -> list[dict]:
    """PURE core: which mention rows still want the viewer.

    A mention is resolved when the viewer SPOKE in that conversation after it
    (a reply is dealing with it) or explicitly marked it done (the resolution
    cursor). It is invisible when it predates the viewer's visibility window
    (ADR-495 D2 — the window is the read floor, asked of every participant).
    """
    out: list[dict] = []
    for r in rows:
        conv = r.get("session_id")
        seq = r.get("sequence_number")
        if conv is None or seq is None:
            continue
        seq = int(seq)
        floor = floors.get(conv)
        if floor is None or seq < int(floor):
            continue  # not in the cast, or before their window
        if seq <= int(reply_floors.get(conv, -1)):
            continue  # they spoke after it
        if seq <= int(resolutions.get(conv, -1)):
            continue  # they marked it done
        out.append(r)
    return out


def _author_label(meta: dict) -> str:
    """Who mentioned the viewer — display form, species kept honest.

    An assistant row carries `agent_slug` (the cast member that spoke); a
    member row carries `author_principal_id`. Both resolve through the
    existing label sources; the degrade is never a UUID.
    """
    meta = meta or {}
    slug = meta.get("agent_slug")
    if slug:
        try:
            from services.agents_registry import AGENTS

            row = AGENTS.get(slug)
            if row and row.get("name"):
                return str(row["name"])
        except Exception:  # noqa: BLE001
            pass
        return str(slug)
    pid = meta.get("author_principal_id")
    if pid:
        try:
            from services.principal_display import resolve_member_names

            names = resolve_member_names(_svc(), [pid])
            if names.get(pid):
                return names[pid]
        except Exception:  # noqa: BLE001
            pass
    from services.principal_display import UNRESOLVED_MEMBER

    return UNRESOLVED_MEMBER


def list_mentions(workspace_id: str, viewer_id: str, *, limit: int = 20) -> list[dict]:
    """The viewer's unresolved mentions in this workspace, newest first.

    Derived, never stored: cast membership (+ visibility window) scopes what
    may be read; the stamp finds the rows; reply/resolution floors decide
    what still wants them. Service-role reads — authorization is the cast
    join itself, the `routes/lanes.py` / migration-228 pattern.
    """
    svc = _svc()

    member_rows = (
        svc.table("conversation_members")
        .select("conversation_id, visible_from_sequence")
        .eq("workspace_id", workspace_id)
        .eq("principal_id", viewer_id)
        .eq("member_kind", "human")
        .execute()
    ).data or []
    floors = {
        r["conversation_id"]: int(r.get("visible_from_sequence") or 0)
        for r in member_rows
    }
    if not floors:
        return []
    conv_ids = list(floors.keys())

    rows = (
        svc.table("session_messages")
        .select("session_id, sequence_number, content, created_at, metadata")
        .in_("session_id", conv_ids)
        .contains("metadata", {"mentions": [viewer_id]})
        .order("created_at", desc=True)
        .limit(_SCAN_LIMIT)
        .execute()
    ).data or []
    if not rows:
        return []

    candidate_convs = sorted({r["session_id"] for r in rows})
    reply_rows = (
        svc.table("session_messages")
        .select("session_id, sequence_number")
        .in_("session_id", candidate_convs)
        .eq("metadata->>author_principal_id", viewer_id)
        .order("sequence_number", desc=True)
        .limit(_SCAN_LIMIT)
        .execute()
    ).data or []
    reply_floors: dict = {}
    for r in reply_rows:
        conv = r["session_id"]
        if conv not in reply_floors:
            reply_floors[conv] = int(r["sequence_number"])

    resolutions = load_resolutions(workspace_id, viewer_id)

    live = unresolved_from(
        rows, floors=floors, reply_floors=reply_floors, resolutions=resolutions
    )[: max(1, int(limit))]
    if not live:
        return []

    name_rows = (
        svc.table("chat_sessions")
        .select("id, context_metadata")
        .in_("id", sorted({r["session_id"] for r in live}))
        .execute()
    ).data or []
    names = {
        r["id"]: ((r.get("context_metadata") or {}).get("lane") or {}).get("name")
        for r in name_rows
    }

    out: list[dict] = []
    for r in live:
        conv = r["session_id"]
        content = (r.get("content") or "").strip()
        out.append({
            "conversation_id": conv,
            "conversation_name": names.get(conv) or "a conversation",
            "sequence": int(r["sequence_number"]),
            "at": r.get("created_at"),
            "excerpt": content[:_EXCERPT_CHARS],
            "author": _author_label(r.get("metadata") or {}),
        })
    return out


def load_resolutions(workspace_id: str, viewer_id: str) -> dict:
    """The viewer's {conversation_id: resolved_up_to_sequence} map."""
    try:
        rows = (
            _svc().table("member_state")
            .select("value")
            .eq("workspace_id", workspace_id)
            .eq("principal_id", viewer_id)
            .eq("key", MENTION_RESOLUTIONS_KEY)
            .limit(1)
            .execute()
        ).data or []
        value = rows[0]["value"] if rows else None
        return value if isinstance(value, dict) else {}
    except Exception as exc:  # noqa: BLE001 — unreadable state reads as "nothing resolved"
        logger.warning("[MENTIONS] resolutions read failed: %s", exc)
        return {}


def resolve_mentions_up_to(
    workspace_id: str, viewer_id: str, conversation_id: str, sequence: int
) -> dict:
    """Advance the viewer's resolution cursor for one conversation.

    Monotonic (max-merge): resolving an older mention never un-resolves a
    newer explicit act. Server-side read-modify-write so the FE never owns
    the merge. Returns the stored map.
    """
    current = load_resolutions(workspace_id, viewer_id)
    merged = dict(current)
    merged[conversation_id] = max(int(current.get(conversation_id, -1)), int(sequence))
    _svc().table("member_state").upsert(
        {
            "workspace_id": workspace_id,
            "principal_id": viewer_id,
            "key": MENTION_RESOLUTIONS_KEY,
            "value": merged,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="workspace_id,principal_id,key",
    ).execute()
    return merged


__all__ = [
    "MENTION_RESOLUTIONS_KEY",
    "EMAIL_SUPPRESSION_MINUTES",
    "enrich_cast_labels",
    "mentioned_humans",
    "fire_and_forget",
    "notify_mentioned",
    "unresolved_from",
    "list_mentions",
    "load_resolutions",
    "resolve_mentions_up_to",
]
