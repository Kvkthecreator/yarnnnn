"""Runs — one row per run, shared with the workspace, live (ADR-666).

A RUN is one occurrence of work: a standing declaration's toolless derive, a
browser run of declared work, or the browser acts of a chat turn. It is an ACT
LEDGER row (`public.runs`, migration 262) — what happened, never workspace
state: what a run MADE is files (Axiom 1), and a declared browser run leaves a
record file beside its work (D3).

THIS MODULE IS THE ONE WRITER of `runs` and of run records. Callers:

    standing_work.run_standing_sweep   — every standing run opens and finishes one
    standing_work (due browser work)   — `raise_due`: a run WAITING on its member
    routes/standing_work (Run now)     — `start_browser_run`: queued, in the work's
                                          conversation
    routes/lanes (the turn)            — `TurnRun`: a browser act opens or joins a
                                          run; receipts are its steps
    routes/runs (stop)                 — `stop_run`

Writes go through the SERVICE client: a run is written by the kernel on behalf
of whoever it runs as, the way `execution_events` is. Reads go through the
caller's client, so RLS ("Members read workspace runs") is the membership test.

⚠️ A run is NOT a task (ADR-231). The kernel creates it when something runs; it
has no schedule, no folder of its own, and means nothing beyond this occurrence.
The declaration stays the only thing a member creates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)

STATES = ("queued", "running", "waiting", "done", "failed", "stopped")
LIVE_STATES = ("queued", "running", "waiting")
ENDED_STATES = ("done", "failed", "stopped")

#: The folder a declared browser run's record lands in, beside its work (D3).
RECORDS_FOLDER = "runs"

#: The columns a reader is served — one select, every reader.
_COLUMNS = (
    "id, workspace_id, user_id, topic, lane_id, kind, trigger, state, waiting_on, "
    "outcome, steps, revision_id, record_path, cost_usd, started_at, updated_at, ended_at"
)


def _svc():
    from services.supabase import get_service_client

    return get_service_client()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _workspace_for(user_id: str, workspace_id: Optional[str]) -> Optional[str]:
    if workspace_id:
        return workspace_id
    from services.workspace_context import effective_workspace_id

    return effective_workspace_id(user_id)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def open_run(
    *, user_id: str, workspace_id: Optional[str], kind: str, trigger: str,
    topic: Optional[str] = None, lane_id: Optional[str] = None,
    state: str = "running", waiting_on: Optional[dict] = None,
) -> Optional[str]:
    """Open a run. Returns its id, or None when it could not be written — a run
    that cannot be recorded never stops the work it records (the ledger rule
    `record_execution_event` follows)."""
    ws = _workspace_for(user_id, workspace_id)
    if not ws:
        logger.warning("[RUNS] no workspace for %s — run not recorded", user_id[:8])
        return None
    row = {
        "workspace_id": ws, "user_id": user_id, "kind": kind, "trigger": trigger,
        "topic": topic, "lane_id": lane_id, "state": state, "waiting_on": waiting_on,
    }
    try:
        res = _svc().table("runs").insert(row).execute()
        return ((res.data or [None])[0] or {}).get("id")
    except Exception as e:  # noqa: BLE001
        logger.warning("[RUNS] open failed (%s %s): %s", kind, topic or "chat", e)
        return None


def _update(run_id: Optional[str], fields: dict) -> None:
    if not run_id:
        return
    try:
        _svc().table("runs").update(fields).eq("id", run_id).execute()
    except Exception as e:  # noqa: BLE001
        logger.warning("[RUNS] update failed for %s: %s", run_id[:8], e)


def set_steps(run_id: Optional[str], steps: list[dict]) -> None:
    """The run's steps, whole. The turn holds the list and writes it after each
    receipt — no read-modify-write, one writer per run."""
    _update(run_id, {"steps": steps})


def mark_running(run_id: Optional[str], *, lane_id: Optional[str] = None) -> None:
    fields: dict = {"state": "running", "waiting_on": None}
    if lane_id:
        fields["lane_id"] = lane_id
    _update(run_id, fields)


def _cost_of(ledger_ids: Iterable[str]) -> Optional[float]:
    ids = [i for i in ledger_ids if i]
    if not ids:
        return None
    try:
        rows = (
            _svc().table("execution_events").select("cost_usd").in_("id", ids).execute()
        ).data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("[RUNS] cost read failed: %s", e)
        return None
    return round(sum(float(r.get("cost_usd") or 0) for r in rows), 6)


def finish_run(
    run_id: Optional[str], *, state: str, outcome: Optional[str] = None,
    revision_id: Optional[str] = None, record_path: Optional[str] = None,
    ledger_ids: Iterable[str] = (), steps: Optional[list[dict]] = None,
) -> None:
    """End a run. A run someone STOPPED stays stopped: the turn that was
    stopped finishes after the stop landed, and must not overwrite it."""
    if not run_id:
        return
    if state not in ENDED_STATES:
        raise ValueError(f"finish_run: {state!r} is not an ended state")
    current = get_run(_svc(), run_id)
    if current and current.get("state") == "stopped":
        # Stopped from outside (its Stop): the turn then ended normally and
        # would have derived a done-style outcome. A stopped run has none.
        state, outcome, revision_id = "stopped", None, None
    fields: dict = {"state": state, "outcome": outcome, "ended_at": _now(), "waiting_on": None}
    if revision_id:
        fields["revision_id"] = revision_id
    if record_path:
        fields["record_path"] = record_path
    if steps is not None:
        fields["steps"] = [{**st, "at": st.get("at") or _now()} for st in steps]
    cost = _cost_of(ledger_ids)
    if cost is not None:
        fields["cost_usd"] = cost
    _update(run_id, fields)


def raise_due(decl: Any) -> dict:
    """ADR-666 D4 — browser work that comes due never acts: it opens a run
    WAITING on its member. One per declaration — the unique index
    `runs_one_waiting_per_topic` refuses a second, which reads as "already
    waiting", not as a failure. The drain records the tick either way."""
    if getattr(decl, "problem", None) is not None:
        # ADR-667 D3 — a declaration that cannot run raises nothing, and one
        # naming a browser outside the workspace would wait on nobody forever.
        return {"success": False, "slug": decl.slug, "error_reason": decl.problem}
    member = (decl.browser or {}).get("member")
    existing = live_for_topic(_svc(), decl.workspace_id, decl.topic)
    if existing:
        return {"success": True, "slug": decl.slug, "waiting": True, "run_id": existing["id"],
                "detail": "already waiting"}
    run_id = open_run(
        user_id=member, workspace_id=decl.workspace_id, kind="browser",
        trigger="scheduled", topic=decl.topic, state="waiting",
        waiting_on={"kind": "member"},
    )
    return {"success": True, "slug": decl.slug, "waiting": True, "run_id": run_id}


def start_browser_run(decl: Any, *, lane_id: str) -> Optional[str]:
    """Run now on browser work (ADR-666 D4): a waiting run is taken up, else a
    queued one opens. The turn marks it running when it begins."""
    existing = live_for_topic(_svc(), decl.workspace_id, decl.topic)
    if existing and existing.get("state") == "waiting":
        # ADR-667 D7 — the trigger stays `scheduled`: the schedule raised it,
        # its member performs it, and the row says both (`lane_id` set).
        _update(existing["id"], {"state": "queued", "waiting_on": None, "lane_id": lane_id})
        return existing["id"]
    if existing:
        return existing["id"]
    return open_run(
        user_id=(decl.browser or {}).get("member"), workspace_id=decl.workspace_id,
        kind="browser", trigger="manual", topic=decl.topic, lane_id=lane_id, state="queued",
    )


def stop_run(run: dict) -> str:
    """Stop a run (ADR-666 D6). A running run's turn ends at its next act; a
    queued or waiting run is dismissed. Returns the state it ended in."""
    from services import client_tools

    if run.get("state") in ENDED_STATES:
        return run["state"]
    if run.get("state") == "running":
        client_tools.stop_run(run["id"])
    _update(run["id"], {"state": "stopped", "ended_at": _now(), "waiting_on": None})
    return "stopped"


# ---------------------------------------------------------------------------
# Reading — through the caller's client; RLS is the membership test
# ---------------------------------------------------------------------------


def get_run(client: Any, run_id: str) -> Optional[dict]:
    try:
        rows = client.table("runs").select(_COLUMNS).eq("id", run_id).limit(1).execute().data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("[RUNS] read failed for %s: %s", run_id[:8], e)
        return None
    return rows[0] if rows else None


def live_for_topic(client: Any, workspace_id: Optional[str], topic: str) -> Optional[dict]:
    if not workspace_id:
        return None
    try:
        rows = (
            client.table("runs").select(_COLUMNS)
            .eq("workspace_id", workspace_id).eq("topic", topic)
            .in_("state", list(LIVE_STATES))
            .order("started_at", desc=True).limit(1).execute()
        ).data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("[RUNS] live read failed for %s: %s", topic, e)
        return None
    return rows[0] if rows else None


def list_runs(
    client: Any, workspace_id: str, *, live: Optional[bool] = None,
    topic: Optional[str] = None, topics: Optional[list[str]] = None, limit: int = 30,
) -> list[dict]:
    """Runs in one workspace, newest first. `live=True` → queued · running ·
    waiting; `live=False` → ended. Never raises — an unreadable ledger is an
    empty list, and every surface that reads it degrades on its own."""
    try:
        q = client.table("runs").select(_COLUMNS).eq("workspace_id", workspace_id)
        if live is True:
            q = q.in_("state", list(LIVE_STATES))
        elif live is False:
            q = q.in_("state", list(ENDED_STATES))
        if topic:
            q = q.eq("topic", topic)
        if topics is not None:
            if not topics:
                return []
            q = q.in_("topic", topics)
        return q.order("started_at", desc=True).limit(limit).execute().data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("[RUNS] list failed: %s", e)
        return []


def hydrate_receipts(client: Any, rows: list[dict]) -> None:
    """ADR-666 D5 — a reply row carries `run_id`; its steps live on the run.
    Put them back under `metadata.receipts` for the transcript reader, in ONE
    query. Mutates `rows`."""
    ids = {
        str((r.get("metadata") or {}).get("run_id"))
        for r in rows if (r.get("metadata") or {}).get("run_id")
    }
    if not ids:
        return
    try:
        found = (
            client.table("runs").select("id, steps").in_("id", list(ids)).execute()
        ).data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("[RUNS] receipt hydration failed: %s", e)
        return
    steps = {r["id"]: r.get("steps") or [] for r in found}
    for r in rows:
        meta = r.get("metadata") or {}
        rid = meta.get("run_id")
        if rid and rid in steps:
            r["metadata"] = {**meta, "receipts": steps[rid]}


# ---------------------------------------------------------------------------
# The record file (D3) — declared browser runs only
# ---------------------------------------------------------------------------

_STATE_WORDS = {"done": "Finished", "failed": "Failed", "stopped": "Stopped"}
_TRIGGER_WORDS = {"manual": "run now", "scheduled": "on its schedule", "chat": "in a conversation"}


def render_record(run: dict, *, topic: str, target: str, member_name: str) -> str:
    """The record's prose. Plain, dated, one line per step — the receipt's own
    sentence (`text`), which is what the agent was told happened."""
    started = str(run.get("started_at") or "")[:16].replace("T", " ")
    lines = [
        f"# {topic} — run of {started} UTC",
        "",
        f"- Ran in {member_name}'s browser, started {_TRIGGER_WORDS.get(run.get('trigger') or '', '')}.",
        f"- {_STATE_WORDS.get(run.get('state') or '', run.get('state') or '')}"
        + (f": {run['outcome']}" if run.get("outcome") else "") + ".",
    ]
    if run.get("revision_id"):
        lines.append(f"- Wrote {target} (revision {str(run['revision_id'])[:8]}).")
    else:
        lines.append(f"- Did not change {target}.")
    steps = run.get("steps") or []
    lines += ["", "## Steps", ""]
    if steps:
        for i, s in enumerate(steps, 1):
            mark = "" if s.get("ok", True) else " (failed)"
            lines.append(f"{i}. {str(s.get('text') or s.get('name') or '').strip()}{mark}")
    else:
        lines.append("No steps were taken.")
    return "\n".join(lines) + "\n"


def write_record(decl: Any, run_id: str) -> Optional[str]:
    """Write `{topic}/runs/{YYYY-MM-DD-HHMM}.md` for a finished declared browser
    run. `system:standing` — machinery, no face. Returns the path, or None."""
    from services.authored_substrate import write_revision
    from services.principal_display import resolve_member_names

    svc = _svc()
    run = get_run(svc, run_id)
    if not run or run.get("state") not in ENDED_STATES:
        return None
    try:
        stamp = datetime.fromisoformat(str(run["started_at"]).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        stamp = datetime.now(timezone.utc)
    path = f"{decl.root}/{RECORDS_FOLDER}/{stamp.astimezone(timezone.utc):%Y-%m-%d-%H%M}.md"
    member = str(run.get("user_id") or "")
    name = resolve_member_names(svc, [member]).get(member) or "a member"
    try:
        write_revision(
            svc,
            user_id=decl.user_id,
            path=path,
            content=render_record(run, topic=decl.topic, target=decl.target, member_name=name),
            authored_by="system:standing",
            message=f"record of a run of '{decl.topic}'",
            workspace_id=decl.workspace_id,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("[RUNS] record write failed for %s: %s", decl.topic, e)
        return None
    _update(run_id, {"record_path": path})
    return path


def head_revision(user_id: str, path: str) -> Optional[str]:
    """The kept file's newest revision id — what a browser run wrote, read once
    at its end (the turn's own writes land before it finishes)."""
    try:
        from services.authored_substrate import list_revisions

        revs = list_revisions(_svc(), user_id=user_id, path=path, limit=1)
    except Exception as e:  # noqa: BLE001
        logger.warning("[RUNS] head revision read failed for %s: %s", path, e)
        return None
    return (revs[0] or {}).get("id") if revs else None


# ---------------------------------------------------------------------------
# The turn's run (D5) — used by routes/lanes
# ---------------------------------------------------------------------------


class TurnRun:
    """The run a lane turn belongs to. A turn started for declared work arrives
    with its run (`run` + `decl`); any other turn opens one lazily at its first
    browser act (`trigger: chat`). Every receipt is a step. `finish` closes it
    however the turn ended; for declared work it also stores what the turn
    wrote to the kept file and writes the record."""

    def __init__(self, *, user_id: str, workspace_id: Optional[str], lane_id: str,
                 run: Optional[dict] = None, decl: Any = None) -> None:
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.lane_id = lane_id
        self.run_id: Optional[str] = (run or {}).get("id")
        self.decl = decl
        self.steps: list[dict] = []
        self.finished = False
        if self.run_id:
            mark_running(self.run_id, lane_id=lane_id)

    def on_act(self, nonce: Optional[str]) -> None:
        from services import client_tools

        if not self.run_id:
            self.run_id = open_run(
                user_id=self.user_id, workspace_id=self.workspace_id, kind="browser",
                trigger="chat", lane_id=self.lane_id, state="running",
            )
        if self.run_id and nonce:
            client_tools.bind_run(nonce, self.run_id)

    def on_receipt(self, receipt: dict) -> None:
        self.steps.append({**receipt, "at": _now()})
        set_steps(self.run_id, self.steps)

    def finish(self, *, stopped: bool, errored: bool, artifacts: Iterable[str] = (),
               ledger_ids: Iterable[str] = ()) -> None:
        if self.finished or not self.run_id:
            return
        self.finished = True
        state = "stopped" if stopped else ("failed" if errored else "done")
        revision_id = None
        outcome = "turn_failed" if errored else None
        if self.decl is not None and not stopped:
            if self.decl.target_path in set(artifacts):
                revision_id = head_revision(self.decl.user_id, self.decl.target_path)
            if state == "done":
                outcome = "wrote" if revision_id else "no_change"
        finish_run(self.run_id, state=state, outcome=outcome, revision_id=revision_id,
                   ledger_ids=ledger_ids)
        if self.decl is not None:
            write_record(self.decl, self.run_id)


__all__ = [
    "STATES", "LIVE_STATES", "ENDED_STATES", "RECORDS_FOLDER",
    "open_run", "set_steps", "mark_running", "finish_run", "raise_due",
    "start_browser_run", "stop_run", "get_run", "live_for_topic", "list_runs",
    "hydrate_receipts", "render_record", "write_record", "head_revision", "TurnRun",
]
