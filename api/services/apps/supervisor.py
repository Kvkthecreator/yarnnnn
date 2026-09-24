"""The Supervisor app (ADR-656 → ADR-658) — where a member manages the work that runs on its own.

The first COMPOSED kernel app: its surface's shape is DECLARED (sections over
the workspace) rather than mirrored from one substrate concern, which is the
register ADR-435 declined to name and ADR-653 D3.a promoted. Every other kernel
app is a bespoke React component over its own material; this one renders what
its declaration says.

WHAT LIVES HERE
- the app's REGISTRATION (ADR-562: residency declared where the app lives).
- ``build_supervisor_posture`` — the bound lane's JOB overlay (ADR-606 D3),
  re-derived by ADR-667 D5: the agent AUTHORS standing work, through the
  one door (`DeclareWork`), and performs none of it.

⚠️ THE APP IS NOT THE AGENT. The registration names `supervisor` as the
resident; the agent's CHARACTER (who it is) lives on its `AGENTS` row, and the
JOB (what this pane is for) lives here. That partition is agent-composition.md
§3.3: a sentence a reader would check against the app's registry is a job, one
true of the agent wherever it works is a character.

⚠️ NO AUTHORITY, AND NONE IS REPRESENTABLE. This app declares a resident and a
posture. It cannot grant, dispatch, wake, or name another being — the posture
below is written so that only *"this belongs to the place that owns it"* is
sayable, never *"Editor, do this"* (ADR-460 D3.a; the gate asserts the text).
"""

from __future__ import annotations

import logging
from typing import Any

from services.authoring import register_app

logger = logging.getLogger(__name__)

#: How many pieces of work the per-turn state block lists. A workspace with
#: more is told the count; the agent lists the folder for the rest.
_STATE_CAP = 12


def build_supervisor_posture(state: str = "") -> str:
    """The job overlay for the supervisor's bound lane (ADR-606 D3 → ADR-667 D5).

    The Supervisor is where a member sets up and keeps the work that keeps
    happening. Its agent AUTHORS that work — through `DeclareWork`, the one
    door the Supervisor's routes also call — and performs none of it: each
    piece runs under the executor its kept file's type derives (ADR-639 D3),
    in its own conversation (ADR-666 D4).

    `state` is the per-turn block `supervisor_state_block` reads: the roster
    and each piece's last run, so the agent answers from the ledger rather
    than from what it remembers saying.

    ⚠️ What this posture may NOT say, and the gate holds it: no other agent's
    name, and no verb that assigns. Who runs a piece of work is derived from
    what the work is, never chosen here (ADR-596 D1).
    """
    lines = [
        "## Your pane — the Supervisor app (the work that keeps happening)",
        "",
        "THE JOB:",
        "- The member tells you about work that keeps happening. You set it up"
        " as standing work — a kept file, a schedule, and CONTRACT.md saying"
        " what must be true when a run finishes — with DeclareWork. Ask what"
        " the file must stay true to before you ask how often.",
        "- Work on websites is set up by doing it once. When their browser is"
        " yours this turn, do the task now while they watch, then offer to"
        " keep doing it: declare it with the sites you actually used, the file"
        " you kept, and a contract written from the steps that worked. It"
        " then runs in their browser when they start it, and waits for them"
        " when it comes due — it never acts while they are away.",
        "- Work that reads files, connections or websites and acts on none"
        " runs on its own schedule. A chain is several pieces, each kept from"
        " the one before; never ask one file to do everything.",
        "- You run no piece of work here. Each runs in its own conversation,"
        " and the member starts it from the Supervisor.",
        "- When something failed, read its record (`{folder}/runs/`) and its"
        " contract before you explain it; change or pause it with"
        " DeclareWork, retire it by deleting its _standing.yaml.",
        "- Raise something only when it changes what the member would do"
        " next. Having nothing to raise is a complete answer.",
    ]
    if state:
        lines += ["", state]
    return "\n".join(lines)


def supervisor_state_block(client: Any, user_id: str) -> str:
    """The work now, for this turn: each piece of standing work in the acting
    workspace and its newest run. Read fresh (derived, never stored); empty
    when there is none or the read fails — a turn never fails on it."""
    try:
        from services.runs import list_runs
        from services.standing_work import discover_standing
        from services.workspace_context import effective_workspace_id

        ws = effective_workspace_id(user_id)
        decls = sorted(
            (d for group in discover_standing(client, workspace_id=ws).values() for d in group),
            key=lambda d: d.topic,
        )
        if not decls:
            return "THE WORK NOW: none set up yet."
        newest: dict[str, dict] = {}
        for r in list_runs(client, ws, topics=[d.topic for d in decls], limit=60) if ws else []:
            newest.setdefault(r.get("topic") or "", r)
        rows = []
        for d in decls[:_STATE_CAP]:
            kind = "browser, sites " + ", ".join((d.browser or {}).get("sites") or []) if d.browser else "on its own"
            status = (f"cannot run: {d.problem}" if d.problem
                      else "paused" if d.paused else f"schedule {d.schedule}")
            run = newest.get(d.topic)
            last = (f"last run {run.get('state')}"
                    + (f" ({run.get('outcome')})" if run.get("outcome") else "")
                    if run else "never run")
            rows.append(f"- {d.topic}/ keeps {d.target} · {kind} · {status} · {last}")
        more = len(decls) - _STATE_CAP
        if more > 0:
            rows.append(f"- …and {more} more")
        return "THE WORK NOW:\n" + "\n".join(rows)
    except Exception as exc:  # noqa: BLE001 — a turn never fails on its state
        logger.warning("[SUPERVISOR] state block unavailable: %s", exc)
        return ""


def supervisor_pane_posture(
    client: Any, user_id: str, artifact_path: str, artifact: str
) -> str:
    """The ADR-606 D3 builder shape. An app-bound lane (ADR-653 R3) has no
    artifact; what it reads per turn is the work (`supervisor_state_block`)."""
    return build_supervisor_posture(supervisor_state_block(client, user_id))


# ── ADR-562 D3: the registration, beside the code it configures ───────────
# The resident is IDENTITY only — the engine follows Supervisor's own row in
# `agents_registry.AGENTS`, never a caller-supplied model.
#
# ⚠️ NO `standing_executor`. The field exists (ADR-604 D2) and this app does
# not fill it. ADR-658 D3: this app is standing work's SURFACE — where a member
# creates, sees and manages it — and executes none of it. The executor stays
# derived per declaration from the kept file's type → its app (ADR-639 D3);
# an app that both surfaced and executed would re-merge the distinction
# ADR-639 drew between running work and showing it.
register_app("supervisor", resident="supervisor", posture=supervisor_pane_posture)
