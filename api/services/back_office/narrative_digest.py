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

    # ADR-221 Commit C: collect material non-conversation entries grouped by
    # role for the recent.md narrative-side rollup. The rollup chat card
    # (above) is for the operator's chat surface; recent.md is for YARNNN's
    # prompt-time on-demand reasoning ("what happened while I was away?").
    # Grouped by role: reviewer / agent / external / system.
    recent_by_role: dict[str, list[dict]] = {
        "reviewer": [],
        "agent": [],
        "external": [],
        "system": [],
    }

    if session_ids:
        # session_messages query — pull rows from this user's sessions in
        # the window. Limit defensive (1000) — at alpha scale a workspace
        # produces well under 100/day, but capping prevents pathological
        # blow-up if something goes haywire upstream.
        msgs_result = (
            client.table("session_messages")
            .select("id, role, metadata, created_at")
            .in_("session_id", session_ids)
            .gte("created_at", window_cutoff.isoformat())
            .order("created_at", desc=False)
            .limit(1000)
            .execute()
        )
        for row in (msgs_result.data or []):
            md = row.get("metadata") or {}
            weight = md.get("weight") or "untagged"
            row_role = row.get("role") or ""
            if weight not in counts:
                counts["untagged"] += 1
                continue
            counts[weight] += 1
            if weight == "housekeeping":
                summary = md.get("summary") or "(no summary)"
                housekeeping_summaries.append(summary)
                rolled_up_ids.append(row["id"])
            # ADR-221 Commit C: material non-conversation entries feed recent.md.
            # User/assistant rows are conversation turns — they belong in
            # the message window (Layer 3), not the narrative-side rollup.
            if (
                weight == "material"
                and row_role in recent_by_role
            ):
                recent_by_role[row_role].append({
                    "summary": md.get("summary") or "(no summary)",
                    "created_at": row.get("created_at"),
                    "task_slug": md.get("task_slug"),
                    "invocation_id": md.get("invocation_id"),
                })

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

    # ADR-221 Commit C: write /workspace/memory/recent.md as the narrative-side
    # rollup of material non-conversation entries. This is the prompt-time
    # on-demand answer to "what happened while I was away?" — YARNNN's compact
    # index points at recent.md (working_memory.format_compact_index); YARNNN
    # reads it via ReadFile when the operator asks. Counterpart to ADR-209's
    # substrate-authorship one-liner (file mutations); two complementary axes.
    total_recent = sum(len(v) for v in recent_by_role.values())
    recent_written = False
    if total_recent > 0:
        try:
            from services.authored_substrate import write_revision

            recent_md = _format_recent_md(started_at, recent_by_role)
            write_revision(
                client,
                user_id=user_id,
                path="/workspace/memory/recent.md",
                content=recent_md,
                authored_by="system:narrative-digest",
                message=(
                    f"recent.md rollup: {total_recent} material non-conversation entries "
                    f"in last {DIGEST_WINDOW_HOURS}h"
                ),
                tags=["memory", "narrative", "recent"],
            )
            recent_written = True
            actions_taken.append({
                "action": "wrote_recent_md",
                "total_recent": total_recent,
                "by_role": {k: len(v) for k, v in recent_by_role.items()},
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[BACK_OFFICE:narrative_digest] recent.md write failed for user=%s: %s",
                user_id[:8] if user_id else "?",
                exc,
            )
            actions_taken.append(
                {"action": "wrote_recent_md_failed", "error": str(exc)}
            )

    summary = (
        f"Scanned {sum(counts.values())} narrative entries in last "
        f"{DIGEST_WINDOW_HOURS}h "
        f"({counts['material']} material, {counts['routine']} routine, "
        f"{total_housekeeping} housekeeping). "
        + (f"Rolled up {total_housekeeping}." if digest_entry else "Nothing to roll up.")
        + (f" Wrote recent.md ({total_recent} entries)." if recent_written else "")
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


# =============================================================================
# ADR-221 Commit C: recent.md formatter (narrative-side rollup for prompt-time
# on-demand reading).
# =============================================================================


def _humanize_age(created_at: str | None, now: datetime) -> str:
    """Render a created_at ISO timestamp as a human-friendly relative-age
    string ("2h ago", "1d ago"). Returns empty string on parse failure."""
    if not created_at:
        return ""
    try:
        # session_messages.created_at is ISO with timezone; tolerate Z suffix.
        ts_str = created_at.replace("Z", "+00:00")
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = now - ts
        secs = int(delta.total_seconds())
        if secs < 60:
            return "just now"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        return f"{secs // 86400}d ago"
    except Exception:  # noqa: BLE001
        return ""


def _format_recent_md(
    started_at: datetime,
    recent_by_role: dict[str, list[dict]],
) -> str:
    """Render /workspace/memory/recent.md.

    Per ADR-221 D4, recent.md is the narrative-side rollup of material
    non-conversation entries. YARNNN reads this on demand via ReadFile when
    the operator asks "what happened?" — most turns won't need it.

    Grouped by role (reviewer / agent / external / system) for scannability.
    Entries within a role are most-recent-first. Bounded display: 10 entries
    per role to keep the file under ~1500 tokens. Counts beyond that surface
    as a "+N more" line.
    """
    timestamp = started_at.strftime("%Y-%m-%d %H:%M UTC")
    total = sum(len(v) for v in recent_by_role.values())

    lines = [
        "# Recent workspace events",
        f"Last updated: {timestamp} · {DIGEST_WINDOW_HOURS}h window · {total} material entries",
        "",
        "_Material non-conversation invocations rolled up by `back-office-narrative-digest`. "
        "User and assistant chat turns are not included — they live in `session_messages` "
        "and are visible via the message window. Per ADR-221 this is YARNNN's prompt-time "
        "on-demand answer to 'what happened while I was away?' Counterpart to the "
        "ADR-209 substrate-authorship signal in the compact index._",
        "",
    ]

    # Display order: operator-facing first (reviewer, agent), then ambient
    # (external, system).
    display_order = [
        ("reviewer", "Reviewer verdicts"),
        ("agent", "Agent task completions"),
        ("external", "External (MCP) writes"),
        ("system", "System events"),
    ]

    for role, header in display_order:
        entries = recent_by_role.get(role, [])
        if not entries:
            continue
        # Most-recent first within role.
        entries_sorted = sorted(
            entries,
            key=lambda e: e.get("created_at") or "",
            reverse=True,
        )
        lines.append(f"## {header} ({len(entries_sorted)})")
        lines.append("")
        for e in entries_sorted[:10]:
            age = _humanize_age(e.get("created_at"), started_at)
            summary = e.get("summary") or "(no summary)"
            slug = e.get("task_slug")
            slug_str = f" — task: `{slug}`" if slug else ""
            age_str = f"{age} — " if age else ""
            lines.append(f"- {age_str}{summary}{slug_str}")
        if len(entries_sorted) > 10:
            lines.append(f"- _… plus {len(entries_sorted) - 10} more in window._")
        lines.append("")

    lines.append(
        "<!-- author: system:narrative-digest · ADR-221 · "
        "use ListRevisions/ReadRevision/DiffRevisions for substrate-authorship axis -->"
    )
    return "\n".join(lines) + "\n"
