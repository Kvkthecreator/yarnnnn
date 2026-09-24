"""Runs routes — ADR-666 (the run: work that acts, seen while it happens).

    GET  /runs                 — the acting workspace's runs, newest first:
                                 `?live=true` queued · running · waiting,
                                 `?live=false` ended; `?topic=` one declaration's
    GET  /runs/{id}            — one run, with its steps
    POST /runs/{id}/stop       — stop it: a running run ends its turn at the next
                                 act; a queued or waiting one is dismissed

Every member of the workspace reads every run (D6): the conversation a run
happened in stays private, the run does not. Reads go through the member's own
client, so the `runs` RLS policy is the membership test. Stopping is the run's
own member's act, or the workspace owner's.

`RunOut` is THE served shape of a run — the standing routes serve it too, so a
run reads the same in the roster, the detail, the cockpit and the tray.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()

_LIST_CAP = 50


class RunOut(BaseModel):
    id: str
    topic: Optional[str] = None
    lane_id: Optional[str] = None
    kind: str
    trigger: str
    state: str
    waiting_on: Optional[dict] = None
    outcome: Optional[str] = None
    #: The acts, each the ADR-662 D3 receipt `{name, text, ok, record}` + `at`.
    steps: list[dict] = []
    revision_id: Optional[str] = None
    record_path: Optional[str] = None
    cost_usd: Optional[float] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    #: Who it runs as, and their name for the viewer.
    user_id: str
    member_name: Optional[str] = None
    #: May THIS viewer stop it — its own member, or the workspace owner.
    can_stop: bool = False


def _acting_workspace(auth) -> Optional[str]:
    from services.workspace_context import effective_workspace_id

    return effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))


def _acting_owner(auth) -> str:
    from services.workspace_context import acting_workspace_owner

    return acting_workspace_owner(auth.client, auth.user_id, getattr(auth, "workspace_id", None))


def serve_runs(auth, rows: list[dict]) -> list[RunOut]:
    """Rows → the served shape, with each member's name resolved in ONE batch
    and `can_stop` decided for this viewer."""
    from services.principal_display import resolve_member_names
    from services.runs import ENDED_STATES
    from services.supabase import get_service_client

    if not rows:
        return []
    names = resolve_member_names(get_service_client(), [str(r.get("user_id") or "") for r in rows])
    owner = _acting_owner(auth)
    out: list[RunOut] = []
    for r in rows:
        uid = str(r.get("user_id") or "")
        cost = r.get("cost_usd")
        out.append(RunOut(
            id=str(r["id"]),
            topic=r.get("topic"),
            lane_id=(str(r["lane_id"]) if r.get("lane_id") else None),
            kind=r.get("kind") or "derive",
            trigger=r.get("trigger") or "manual",
            state=r.get("state") or "done",
            waiting_on=r.get("waiting_on"),
            outcome=r.get("outcome"),
            steps=[s for s in (r.get("steps") or []) if isinstance(s, dict)],
            revision_id=(str(r["revision_id"]) if r.get("revision_id") else None),
            record_path=r.get("record_path"),
            cost_usd=(float(cost) if cost is not None else None),
            started_at=r.get("started_at"),
            ended_at=r.get("ended_at"),
            user_id=uid,
            member_name=names.get(uid),
            can_stop=(r.get("state") not in ENDED_STATES
                      and auth.user_id in (uid, owner)),
        ))
    return out


def _one(auth, run_id: str) -> dict:
    from services.runs import get_run

    ws = _acting_workspace(auth)
    run = get_run(auth.client, run_id)
    # A run in another workspace reads as absent, never as forbidden.
    if not run or (ws and str(run.get("workspace_id")) != str(ws)):
        raise HTTPException(status_code=404, detail="No such run")
    return run


@router.get("/runs")
async def list_runs_route(
    auth: UserClient, live: Optional[bool] = None, topic: Optional[str] = None,
    limit: int = 30,
) -> list[RunOut]:
    from services.runs import list_runs

    ws = _acting_workspace(auth)
    if not ws:
        return []
    rows = list_runs(auth.client, ws, live=live, topic=(topic or None),
                     limit=max(1, min(int(limit), _LIST_CAP)))
    return serve_runs(auth, rows)


@router.get("/runs/{run_id}")
async def get_run_route(run_id: str, auth: UserClient) -> RunOut:
    return serve_runs(auth, [_one(auth, run_id)])[0]


@router.post("/runs/{run_id}/stop")
async def stop_run_route(run_id: str, auth: UserClient) -> RunOut:
    from services.runs import get_run, stop_run
    from services.supabase import get_service_client

    run = _one(auth, run_id)
    if auth.user_id not in (str(run.get("user_id") or ""), _acting_owner(auth)):
        raise HTTPException(
            status_code=403,
            detail="Only the member it runs as, or the workspace's owner, can stop this run.",
        )
    stop_run(run)
    return serve_runs(auth, [get_run(get_service_client(), run_id) or run])[0]


def run_out(auth, row: Optional[dict]) -> Optional[RunOut]:
    """One row, served — for the standing routes. None stays None."""
    return serve_runs(auth, [row])[0] if row else None


__all__ = ["router", "RunOut", "serve_runs", "run_out"]
