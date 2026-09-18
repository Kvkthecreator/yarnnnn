"""The Supervisor app (ADR-656) — the member's view of what is underway.

The first COMPOSED kernel app: its surface's shape is DECLARED (sections over
the workspace) rather than mirrored from one substrate concern, which is the
register ADR-435 declined to name and ADR-653 D3.a promoted. Every other kernel
app is a bespoke React component over its own material; this one renders what
its declaration says.

WHAT LIVES HERE
- the app's REGISTRATION (ADR-562: residency declared where the app lives).
- ``build_supervisor_posture`` — the bound lane's JOB overlay (ADR-606 D3).

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

from typing import Any

from services.authoring import register_app

#: The app's own folder — its work, and the shared memory of this concern.
#: ADR-411 is the ruling underneath: *lanes are isolated conversations; the
#: workspace is the shared memory*. So there is no memory store to build here;
#: what the supervisor and its threads know in common is this folder, already
#: versioned and attributed.
SUPERVISOR_HOME = "supervisor/"


def build_supervisor_posture() -> str:
    """The job overlay for the supervisor's bound lane (ADR-606 D3).

    Pure and argument-free — deliberately. Every other app's posture is built
    from an ARTIFACT because every other app is bound to a document. This one
    is bound to the APP itself (ADR-653 R3, the third binding kind), so there
    is no head to read and nothing per-turn to interpolate.

    ⚠️ What this posture may NOT say, and the gate holds it: no other agent's
    name, and no verb that assigns. Routing is *where work goes*, which is a
    fact about a lane; *who does it* derives from the app that owns the work
    (ADR-597 D1) and is never chosen here.
    """
    return "\n".join([
        "## Your pane — the Supervisor app (what is underway)",
        "",
        "THE JOB:",
        "- The member briefs you about work. Your job is to know the SHAPE of"
        " it: which pieces are moving, which are waiting on them, and where"
        " each one belongs. Answer from what the workspace says, not from"
        " what you remember saying.",
        "- When several things arrive at once, say how they SPLIT and why —"
        " two asks about the same file are one piece of work; two asks about"
        " unrelated things are two. Name the split in plain words before"
        " anything else happens.",
        "- You do the work of no thread. When a piece belongs somewhere,"
        " say where and hand it over; when the member asks you to do it here,"
        " say plainly that it belongs elsewhere and why. Doing it here is how"
        " a keeper becomes a bottleneck.",
        f"- This app's own folder is `{SUPERVISOR_HOME}` — notes, decisions"
        " and briefs about the work as a whole live there. The work itself"
        " lives where it belongs in the workspace, never copied here.",
        "- Raise something only when it changes what the member would do"
        " next. What merely happened is already on their timeline, and a"
        " keeper who reports to prove it is awake teaches them to stop"
        " reading. Having nothing to raise is a complete answer.",
        "- Read before you claim. Your own summary is not evidence for"
        " itself: if you are about to say a thing is done, blocked or"
        " waiting, check the file that would show it.",
    ])


def supervisor_pane_posture(
    client: Any, user_id: str, artifact_path: str, artifact: str
) -> str:
    """The ADR-606 D3 builder shape over the pure posture.

    All four arguments are part of the shared contract and deliberately
    unused: an app-bound lane (ADR-653 R3) has no artifact, and this app reads
    nothing per-turn that the lane frame has not already read.
    """
    return build_supervisor_posture()


# ── ADR-562 D3: the registration, beside the code it configures ───────────
# The resident is IDENTITY only — the engine follows Supervisor's own row in
# `agents_registry.AGENTS`, never a caller-supplied model.
#
# ⚠️ NO `standing_executor`. The field exists (ADR-604 D2) and this app does
# not fill it: the supervisor's subject is ATTENDED work — what the member is
# doing now — and standing work is a kernel lane with its own executor derived
# from the kept file's type (ADR-639). An app that claimed both would re-merge
# the distinction ADR-639 drew.
register_app("supervisor", resident="supervisor", posture=supervisor_pane_posture)
