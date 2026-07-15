"""W0 — the ADR-457 D8 falsifier read surface.

ADR-457 D8 declares three falsifiers for the Think·Make bet, to be evaluated
60–90 days after the chat waves ship. This module is the READ side: three
functions, one per falsifier, each returning a plain dict. No new storage, no
dashboard, no UI — a falsifier is read at evaluation time, not watched.

THE THREE DATA HOMES (the 2026-07-16 finding — D8's "all readable from
execution_events + session counts" is half right):

  1. chat-as-command-line-only  →  execution_events ⋈ chat_sessions
     BLOCKED until migration 216: every chat turn AND every Studio bound-lane
     turn writes slug="lane". The discriminator lives one table over
     (chat_sessions.context_metadata->'lane'->>'artifact_path' — ADR-440 D3:
     "a lane with a binding is a studio lane"), and `session_id` is the join
     key that reconnects them.

  2. settle unused              →  execution_events (the settle slug)
     Needs the verb to exist. Pre-settle this reports staged=False — the
     explicit "the verb does not exist yet" signal, so a zero can never be
     misread as rejection. An unbuilt verb reads null; null is not evidence
     of non-adoption.

  3. MCP ≫ desk                 →  workspace_file_versions.authored_by
     Works TODAY, no dependency on 216: `yarnnn:mcp:*` (the hum) vs
     `operator` + `member:*` (the desk) is exactly D8's cut, already recorded.

DISCIPLINE: every function reports its WINDOW and its UNCLASSIFIED/UNSTAGED
count alongside the number. A falsifier that cannot say what it did not see is
a vibe with a decimal point. Reading these is the 60–90d pass; this module
builds the instrument and passes no judgment on the bet.

Spec: docs/analysis/w0-falsifier-instrumentation-spec-2026-07-16.md
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: The surface classes falsifier 1 sorts turns into. DERIVED from the joined
#: session's lane binding at read time (DP29 derived-never-stored) — the
#: ledger stores WHICH SESSION, never WHICH SURFACE.
SURFACE_THINK = "think"            # a chat lane: no binding
SURFACE_MAKE = "make"              # a Studio bound lane (ADR-440 D3)
SURFACE_DERIVE = "derive"          # a derive-bound lane (ADR-450 D3)
SURFACE_STEWARD = "steward"        # the ambient rail (ADR-454)
SURFACE_UNCLASSIFIED = "unclassified"  # pre-W0 rows — NEVER folded into another


def _window_start(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def classify_surface(session_row: Optional[dict]) -> str:
    """Derive the surface class from a session row (ADR-460 §4 taxonomy).

    Pure. `None` (no joined session) → unclassified: a row recorded before
    migration 216, or a non-session invocation. Never guessed into a class —
    a metric that silently drops unknowns reads as coverage it does not have.
    """
    if not session_row:
        return SURFACE_UNCLASSIFIED
    if session_row.get("session_type") != "lane":
        # thinking_partner (the steward rail) and any future session type.
        return SURFACE_STEWARD
    lane = (session_row.get("context_metadata") or {}).get("lane") or {}
    # Order matters: a derive lane is bound to an artifact too (ADR-450 D3
    # composes with the ADR-440 binding), so derive is tested FIRST.
    if lane.get("derive_recipe"):
        return SURFACE_DERIVE
    if lane.get("artifact_path"):
        return SURFACE_MAKE
    return SURFACE_THINK


def falsifier_1_surface_mix(
    client: Any, workspace_id: str, days: int = 90
) -> dict:
    """D8 falsifier 1 — "sessions concentrate in Studio and chat is used only
    as a command line → Think was the wrong frame".

    FIRES WHEN: think-surface turns collapse toward zero while make holds.

    Honest asymmetry, documented not silently substituted: D8 says "sessions
    concentrate"; this measures TURNS. Turns are the better proxy — a session
    left open is not use — but it is not literally what D8 wrote.
    """
    since = _window_start(days)
    events = (
        client.table("execution_events")
        .select("id, session_id")
        .eq("workspace_id", workspace_id)
        .eq("slug", "lane")
        .gte("created_at", since)
        .execute()
    ).data or []

    session_ids = {e["session_id"] for e in events if e.get("session_id")}
    sessions: dict[str, dict] = {}
    if session_ids:
        rows = (
            client.table("chat_sessions")
            .select("id, session_type, context_metadata")
            .in_("id", list(session_ids))
            .execute()
        ).data or []
        sessions = {r["id"]: r for r in rows}

    counts = {
        SURFACE_THINK: 0, SURFACE_MAKE: 0, SURFACE_DERIVE: 0,
        SURFACE_STEWARD: 0, SURFACE_UNCLASSIFIED: 0,
    }
    for e in events:
        counts[classify_surface(sessions.get(e.get("session_id")))] += 1

    classified = sum(v for k, v in counts.items() if k != SURFACE_UNCLASSIFIED)
    return {
        "falsifier": 1,
        "question": "is chat used only as a command line?",
        "window_days": days,
        "turns_by_surface": counts,
        "classified_turns": classified,
        # The load-bearing honesty field: rows recorded before migration 216.
        # Shrinks to irrelevance on its own as post-W0 rows accumulate.
        "unclassified_turns": counts[SURFACE_UNCLASSIFIED],
        "note": "turns, not sessions (D8 says sessions; a session left open is not use)",
    }


def falsifier_2_settle_adoption(
    client: Any, workspace_id: str, days: int = 90, settle_slug: str = "settle"
) -> dict:
    """D8 falsifier 2 — "the settle verb goes unused after honest staging →
    the compounding moment is not felt; GTM must not lead with it".

    FIRES WHEN: staged is True and settles stay ~0 across the window.

    PRE-SETTLE this returns settles=0, staged=False. That distinction is the
    entire point of building this before the verb: an unbuilt verb reads zero,
    and zero would otherwise be indistinguishable from "shipped and ignored" —
    which is exactly what this falsifier fires on.
    """
    since = _window_start(days)

    settles = len((
        client.table("execution_events")
        .select("id")
        .eq("workspace_id", workspace_id)
        .eq("slug", settle_slug)
        .gte("created_at", since)
        .execute()
    ).data or [])

    # Has the verb EVER fired? (all-time, not windowed — "staged" is about
    # existence, not recent use.)
    ever = len((
        client.table("execution_events")
        .select("id")
        .eq("slug", settle_slug)
        .limit(1)
        .execute()
    ).data or [])

    mix = falsifier_1_surface_mix(client, workspace_id, days)
    think_turns = mix["turns_by_surface"][SURFACE_THINK]

    return {
        "falsifier": 2,
        "question": "is the settle verb used after honest staging?",
        "window_days": days,
        "staged": ever > 0,
        "settles": settles,
        "think_turns": think_turns,
        # The rate at which thinking becomes record — the compounding signal.
        "settles_per_think_turn": (settles / think_turns) if think_turns else None,
        "note": (
            "staged=False → the verb does not exist yet; a zero here is NOT "
            "evidence of non-adoption"
        ),
    }


def falsifier_3_hum_vs_desk(
    client: Any, workspace_id: str, days: int = 90
) -> dict:
    """D8 falsifier 3 — "MCP traffic dwarfs desk traffic among real users →
    the hum is the true wedge; investment priority flips back per D5".

    FIRES WHEN: hum_writes >> desk_writes.

    Works today with no dependency on migration 216: the revision ledger's
    attribution already carries the cut (`yarnnn:mcp:*` vs `operator`/`member:*`).
    Measures WRITES (attributed acts), which is the honest unit — a read leaves
    no attributed trace by design.
    """
    since = _window_start(days)
    rows = (
        client.table("workspace_file_versions")
        .select("authored_by")
        .eq("workspace_id", workspace_id)
        .gte("created_at", since)
        .execute()
    ).data or []

    hum = desk = system = 0
    for r in rows:
        a = r.get("authored_by") or ""
        if a.startswith("yarnnn:mcp"):
            hum += 1
        elif a == "operator" or a.startswith("operator") or a.startswith("member:"):
            desk += 1
        else:
            # freddie:/system:/agent:/specialist: — neither hum nor desk; the
            # operation's own machinery. Reported, never folded into either.
            system += 1

    return {
        "falsifier": 3,
        "question": "does MCP traffic dwarf desk traffic?",
        "window_days": days,
        "hum_writes": hum,
        "desk_writes": desk,
        "system_writes": system,
        "hum_to_desk_ratio": (hum / desk) if desk else None,
        "note": "writes, not reads (a read leaves no attributed trace by design)",
    }


def read_all(client: Any, workspace_id: str, days: int = 90) -> dict:
    """All three falsifiers, one call. The 60–90d evaluation entry point."""
    return {
        "workspace_id": workspace_id,
        "window_days": days,
        "read_at": datetime.now(timezone.utc).isoformat(),
        "falsifier_1": falsifier_1_surface_mix(client, workspace_id, days),
        "falsifier_2": falsifier_2_settle_adoption(client, workspace_id, days),
        "falsifier_3": falsifier_3_hum_vs_desk(client, workspace_id, days),
    }
