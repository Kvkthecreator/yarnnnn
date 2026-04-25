"""Back Office: Narrative Digest — ADR-219 Commit 3.

Per FOUNDATIONS Axiom 9 + ADR-219 D5: every invocation emits exactly one
narrative entry, but rendering weight (material / routine / housekeeping)
varies. Housekeeping entries — back-office cleanup runs that found
nothing, heartbeat empty-states, etc. — would clutter the operator's
chat timeline if rendered individually. The digest folds the day's
housekeeping entries into ONE material-weight rolled-up narrative entry
that the operator can scroll past or expand.

Closes Axiom 9 Clause B: "every invocation logged, weight determines
visibility." The log layer remains complete (every housekeeping entry
stays in `session_messages`); the rollup is purely additive — a new
material entry that *summarizes* the housekeeping cluster, with
`metadata.rolled_up_count` + `metadata.rolled_up_window` so the frontend
(Commit 5) can render it as expandable.

Trigger: this task is materialized on the first time `write_narrative_entry`
emits a housekeeping-weight entry for the workspace. Once running, it
fires daily.

Scope: looks at the past 24h of session_messages owned by the user
across all chat_sessions (joined via chat_sessions.user_id), counts
entries by metadata.weight, and emits one material rollup if there were
any housekeeping entries in the window.

Zero LLM cost — deterministic SQL plus narrative.write_narrative_entry.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


# 24-hour rollup window. Matches the daily cadence — operator sees one
# digest per day. If we shift to weekly (open question 2 in
# invocation-and-narrative.md §7), this constant changes; the executor
# logic is unaffected.
DIGEST_WINDOW_HOURS = 24


async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Execute the daily narrative digest for the given user.

    Reads the past 24h of session_messages owned by user_id, groups by
    metadata.weight, and writes one rolled-up material narrative entry
    summarizing the housekeeping cluster. If there are zero housekeeping
    entries in the window, writes nothing — the digest is a *response* to
    accumulated noise, not a heartbeat in its own right.

    Returns the standard back-office executor shape (summary,
    output_markdown, actions_taken).
    """
    started_at = datetime.now(timezone.utc)
    window_cutoff = started_at - timedelta(hours=DIGEST_WINDOW_HOURS)

    # 1. Pull session_messages for this user in the window. We need the
    # join through chat_sessions because session_messages doesn't carry
    # user_id directly.
    sessions_result = (
        client.table("chat_sessions")
        .select("id")
        .eq("user_id", user_id)
        .execute()
    )
    session_ids = [row["id"] for row in (sessions_result.data or [])]

    counts = {"material": 0, "routine": 0, "housekeeping": 0, "untagged": 0}
    housekeeping_summaries: list[str] = []
    rolled_up_ids: list[str] = []

    if session_ids:
        # session_messages query — pull rows from this user's sessions in
        # the window. Limit defensive (1000) — at alpha scale a workspace
        # produces well under 100/day, but capping prevents pathological
        # blow-up if something goes haywire upstream.
        msgs_result = (
            client.table("session_messages")
            .select("id, metadata, created_at")
            .in_("session_id", session_ids)
            .gte("created_at", window_cutoff.isoformat())
            .order("created_at", desc=False)
            .limit(1000)
            .execute()
        )
        for row in (msgs_result.data or []):
            md = row.get("metadata") or {}
            weight = md.get("weight") or "untagged"
            if weight not in counts:
                counts["untagged"] += 1
                continue
            counts[weight] += 1
            if weight == "housekeeping":
                summary = md.get("summary") or "(no summary)"
                housekeeping_summaries.append(summary)
                rolled_up_ids.append(row["id"])

    total_housekeeping = counts["housekeeping"]

    actions_taken: list[dict] = [
        {"action": "scan_window", "hours": DIGEST_WINDOW_HOURS, "counts": counts},
    ]

    digest_entry = None
    if total_housekeeping > 0:
        # 2. Find the active workspace session — same target as Reviewer
        # surfacing. If none, the digest still produces an output.md but
        # no narrative entry (graceful degradation; the operator will
        # see the digest in /work next time they look).
        from services.narrative import (
            find_active_workspace_session,
            write_narrative_entry,
        )

        session_id = find_active_workspace_session(client, user_id)
        if session_id:
            digest_summary = (
                f"{total_housekeeping} housekeeping invocations rolled up — all clean"
            )
            digest_body = _format_digest_body(
                started_at, counts, housekeeping_summaries
            )
            try:
                digest_entry = write_narrative_entry(
                    client,
                    session_id,
                    role="system",
                    summary=digest_summary,
                    body=digest_body,
                    pulse="periodic",
                    weight="material",
                    task_slug=task_slug,
                    extra_metadata={
                        "system_card": "narrative_digest",
                        "rolled_up_count": total_housekeeping,
                        "rolled_up_window_hours": DIGEST_WINDOW_HOURS,
                        "rolled_up_ids": rolled_up_ids[:200],  # bounded
                        "counts": counts,
                        "authored_by": "system:back-office-narrative-digest",
                    },
                )
                actions_taken.append(
                    {
                        "action": "emit_rollup",
                        "rolled_up_count": total_housekeeping,
                        "session_id": session_id,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[BACK_OFFICE:narrative_digest] rollup write failed for user=%s: %s",
                    user_id[:8] if user_id else "?",
                    exc,
                )
                actions_taken.append(
                    {"action": "emit_rollup_failed", "error": str(exc)}
                )
        else:
            actions_taken.append(
                {"action": "emit_rollup_skipped", "reason": "no_active_session"}
            )

    summary = (
        f"Scanned {sum(counts.values())} narrative entries in last "
        f"{DIGEST_WINDOW_HOURS}h "
        f"({counts['material']} material, {counts['routine']} routine, "
        f"{total_housekeeping} housekeeping). "
        + (f"Rolled up {total_housekeeping}." if digest_entry else "Nothing to roll up.")
    )

    output_markdown = _format_report(
        started_at, counts, housekeeping_summaries, digest_entry is not None
    )

    logger.info(f"[BACK_OFFICE:narrative_digest] {summary}")

    return {
        "summary": summary,
        "output_markdown": output_markdown,
        "actions_taken": actions_taken,
    }


def _format_digest_body(
    started_at: datetime,
    counts: dict[str, int],
    housekeeping_summaries: list[str],
) -> str:
    """Render the rolled-up narrative entry's body (the operator sees this
    when they expand the digest card on /chat)."""
    date_str = started_at.strftime("%Y-%m-%d")
    lines = [
        f"**Housekeeping rollup — {date_str}**",
        "",
        f"{counts['housekeeping']} housekeeping invocations in the last "
        f"{DIGEST_WINDOW_HOURS}h. Click to expand the list:",
        "",
    ]
    # Show up to 25 summaries inline; the rest are accessible via
    # rolled_up_ids in metadata if a follow-up surface wants them.
    for s in housekeeping_summaries[:25]:
        lines.append(f"- {s}")
    if len(housekeeping_summaries) > 25:
        lines.append(f"- … plus {len(housekeeping_summaries) - 25} more.")
    return "\n".join(lines)


def _format_report(
    started_at: datetime,
    counts: dict[str, int],
    housekeeping_summaries: list[str],
    rolled_up: bool,
) -> str:
    """Render the back-office task's output.md (the persisted run record
    in /tasks/back-office-narrative-digest/outputs/{date}/output.md)."""
    date_str = started_at.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Narrative Digest — {date_str}",
        "",
        "## Window",
        f"Last **{DIGEST_WINDOW_HOURS}h**.",
        "",
        "## Counts",
        "",
        "| Weight | Count |",
        "|---|---:|",
        f"| material | {counts['material']} |",
        f"| routine | {counts['routine']} |",
        f"| housekeeping | {counts['housekeeping']} |",
        f"| untagged | {counts['untagged']} |",
        "",
    ]
    if counts["housekeeping"] > 0:
        lines.append("## Housekeeping summaries")
        lines.append("")
        for s in housekeeping_summaries[:50]:
            lines.append(f"- {s}")
        if len(housekeeping_summaries) > 50:
            lines.append(f"- … plus {len(housekeeping_summaries) - 50} more.")
        lines.append("")
    lines.append("## Rollup status")
    lines.append("")
    if rolled_up:
        lines.append("Emitted one rolled-up narrative entry to the operator's chat session.")
    elif counts["housekeeping"] == 0:
        lines.append("No housekeeping entries in window — nothing to roll up.")
    else:
        lines.append("Rollup skipped (no active chat session). Counts logged only.")
    lines.append("")
    lines.append(
        "<!-- executor: services.back_office.narrative_digest · version: 1 · ADR-219 Commit 3 -->"
    )
    return "\n".join(lines) + "\n"
