"""
Narrative routes — ADR-219 Commit 4.

Per FOUNDATIONS Axiom 9 + invocation-and-narrative.md, `/work` is no longer
a parallel substrate of "tasks and their runs"; it is the narrative
filtered by task slug. This module exposes the filter-over-narrative
endpoint that the cockpit's WorkListSurface consumes for recent-activity
headlines.

Endpoint:
- GET /api/narrative/by-task — returns task-grouped narrative slices
  (last material entry + counts by weight) for every task slug surfaced
  in this user's `session_messages.metadata.task_slug`.

`agent_runs` is unchanged. It remains the audit ledger and continues to
back the per-task run-history view in WorkDetail (read by routes/tasks.py
GET /api/tasks/{slug}). This module is purely about the operator-facing
list-view headline source — replacing today's `task.last_run_at`
timestamp with "what actually shipped" headlines from the narrative.

Scoping note: session_messages doesn't carry user_id directly; we
resolve via chat_sessions.user_id. The user JWT's RLS gates this
naturally — we still scope the chat_sessions query to user_id for
explicit safety.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


# Default window for the "counts" buckets. Spec D7 doesn't pin a
# value — this matches the digest task's window (services.back_office.
# narrative_digest.DIGEST_WINDOW_HOURS) so the cockpit headlines and
# the daily digest agree on what "recent" means. Frontend can override
# via ?window_hours=N if a future surface needs a different scope.
DEFAULT_WINDOW_HOURS = 24

# Pull at most this many session_messages rows per request. The
# narrative will accumulate over time; this cap keeps the JSON
# payload bounded. We sort by created_at desc and take the most
# recent N — the "last material" headline per task only needs the
# most-recent material entry, and the counts are bounded to the
# 24h window, so pulling more than ~500 rows would be wasted work.
ROW_FETCH_CAP = 500


# =============================================================================
# Response models
# =============================================================================

class NarrativeMaterialEntry(BaseModel):
    """The most-recent material-weight narrative entry for a task slug.

    Used by the cockpit list view to render a headline like:
        "Researcher delivered competitor scan · 2h ago"
    instead of the previous timestamp-only "Last: 2h ago".
    """
    summary: str
    role: str
    pulse: str
    created_at: str
    invocation_id: Optional[str] = None


class NarrativeCounts(BaseModel):
    """Per-weight invocation counts in the rolling window.

    Frontend may surface these as small inline indicators on the row
    (Commit 5 territory). Today we expose them so the consumer doesn't
    have to re-fetch.
    """
    material: int = 0
    routine: int = 0
    housekeeping: int = 0


class NarrativeByTaskSlice(BaseModel):
    """One task's slice of the narrative."""
    task_slug: str
    last_material: Optional[NarrativeMaterialEntry] = None
    counts: NarrativeCounts = NarrativeCounts()
    most_recent_at: Optional[str] = None


class NarrativeByTaskResponse(BaseModel):
    """Top-level response — keyed-list of task slices.

    Empty `tasks` list means: no narrative entries with a task_slug in
    metadata exist for this user yet. Frontend should render the list
    with empty headlines (graceful) — narrative coverage builds up as
    invocations fire post-Commit-2.
    """
    window_hours: int
    tasks: list[NarrativeByTaskSlice]


# =============================================================================
# Endpoint
# =============================================================================

@router.get("/by-task", response_model=NarrativeByTaskResponse)
async def by_task(
    auth: UserClient,
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> NarrativeByTaskResponse:
    """Return narrative slices grouped by task_slug.

    For every task this user has invocations on, returns:
      - the most recent material-weight entry (the headline)
      - counts by weight in the rolling window
      - timestamp of the most recent any-weight entry (for sort)

    Narrative entries without a `metadata.task_slug` are inline
    actions (ADR-219 D6 — "operator asked X without a nameplate")
    and are NOT included in this response. They surface in /chat
    directly, not via the /work filter.
    """
    user_id = auth.user_id
    window_cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    # 1. Resolve this user's session ids. session_messages doesn't carry
    # user_id; the join lives in chat_sessions.
    sessions_result = (
        auth.client.table("chat_sessions")
        .select("id")
        .eq("user_id", user_id)
        .execute()
    )
    session_ids = [row["id"] for row in (sessions_result.data or [])]
    if not session_ids:
        return NarrativeByTaskResponse(window_hours=window_hours, tasks=[])

    # 2. Pull recent session_messages for this user. We over-fetch the
    # window-cutoff filter here (window_hours bounds counts; "last
    # material" can predate the window if no material happened today)
    # by ordering desc + capping at ROW_FETCH_CAP. The aggregation
    # below applies the window cutoff per-bucket.
    msgs_result = (
        auth.client.table("session_messages")
        .select("id, role, content, metadata, created_at")
        .in_("session_id", session_ids)
        .order("created_at", desc=True)
        .limit(ROW_FETCH_CAP)
        .execute()
    )
    rows = msgs_result.data or []

    # 3. Bucket by task_slug. Skip rows without one (inline actions).
    slices: dict[str, dict[str, Any]] = {}
    for row in rows:
        md = row.get("metadata") or {}
        slug = md.get("task_slug")
        if not slug:
            continue

        slot = slices.setdefault(
            slug,
            {
                "task_slug": slug,
                "last_material": None,
                "counts": {"material": 0, "routine": 0, "housekeeping": 0},
                "most_recent_at": None,
            },
        )

        created_at = row.get("created_at")
        if created_at and (
            slot["most_recent_at"] is None or created_at > slot["most_recent_at"]
        ):
            slot["most_recent_at"] = created_at

        # Counts apply only to the rolling window.
        weight = md.get("weight")
        if (
            weight in ("material", "routine", "housekeeping")
            and created_at
            and created_at >= window_cutoff.isoformat()
        ):
            slot["counts"][weight] = slot["counts"][weight] + 1

        # Track the most-recent material entry irrespective of window —
        # the headline is "what shipped last" not "what shipped today".
        # Rows arrive in created_at desc order, so the first material
        # row we see for a slug is the most recent.
        if weight == "material" and slot["last_material"] is None:
            summary = md.get("summary") or (row.get("content") or "").split("\n", 1)[0][:160]
            slot["last_material"] = {
                "summary": summary,
                "role": row.get("role") or "system",
                "pulse": md.get("pulse") or "addressed",
                "created_at": created_at or "",
                "invocation_id": md.get("invocation_id"),
            }

    # 4. Materialize the response. Sort by most_recent_at desc so the
    # frontend has a sensible default order if it doesn't re-sort.
    out: list[NarrativeByTaskSlice] = []
    for s in slices.values():
        last_mat = s["last_material"]
        out.append(
            NarrativeByTaskSlice(
                task_slug=s["task_slug"],
                last_material=NarrativeMaterialEntry(**last_mat) if last_mat else None,
                counts=NarrativeCounts(**s["counts"]),
                most_recent_at=s["most_recent_at"],
            )
        )
    out.sort(
        key=lambda x: x.most_recent_at or "",
        reverse=True,
    )

    return NarrativeByTaskResponse(window_hours=window_hours, tasks=out)
