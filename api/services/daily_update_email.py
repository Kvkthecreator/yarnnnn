"""Daily-Update Email Pointer Template — ADR-202 §1.

Daily-update email emits an **expository pointer** — headline summary +
deep-links into cockpit surfaces — not a full-content digest. The
agent-generated digest content lives at `/tasks/daily-update/outputs/
{date}/` and is consumed by the Overview surface (ADR-199). The email
is the notification that the cockpit has something to show; it is not
the UX.

Per ADR-202:
- §1: Daily-update shape = headline + pointer cluster + empty-state
- §4: External-Channel content discipline — headline + 1-2 line
  summary + deep-links, NO full rich content, NO action buttons

Headline is deterministic: counts of today's task runs, pending
proposals, and new reviewer decisions. No LLM call, no narrative
prose in the email body.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from services.deep_links import (
    context_path_url,
    overview_url,
    review_url,
)

logger = logging.getLogger(__name__)


async def compute_daily_headline_counts(
    client: Any,
    user_id: str,
    *,
    since: datetime | None = None,
) -> dict:
    """Deterministic counts since `since` (default: start of today UTC).

    Returns `{task_runs, pending_proposals, reviewer_decisions}`.
    Each count is independent; a failure in one zeroes that count but
    does not block the others.
    """
    if since is None:
        now = datetime.now(timezone.utc)
        since = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    since_iso = since.isoformat()

    task_runs = 0
    pending_proposals = 0
    reviewer_decisions = 0

    # 1. Task runs since `since` — agent_runs rows
    try:
        result = (
            client.table("agent_runs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", since_iso)
            .execute()
        )
        task_runs = int(getattr(result, "count", 0) or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[DAILY_UPDATE_EMAIL] task_runs count failed for user=%s: %s",
            user_id[:8], exc,
        )

    # 2. Pending proposals (status='pending', not expired)
    try:
        result = (
            client.table("action_proposals")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "pending")
            .execute()
        )
        pending_proposals = int(getattr(result, "count", 0) or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[DAILY_UPDATE_EMAIL] pending_proposals count failed for user=%s: %s",
            user_id[:8], exc,
        )

    # 3. Reviewer decisions since `since` — count approve/reject entries
    # in action_proposals with approved_at or status='rejected' in window.
    # (decisions.md is markdown; quicker to count via proposal status
    # changes.)
    try:
        approved = (
            client.table("action_proposals")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("approved_at", since_iso)
            .execute()
        )
        rejected = (
            client.table("action_proposals")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "rejected")
            .gte("created_at", since_iso)
            .execute()
        )
        reviewer_decisions = int(
            (getattr(approved, "count", 0) or 0)
            + (getattr(rejected, "count", 0) or 0)
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[DAILY_UPDATE_EMAIL] reviewer_decisions count failed for user=%s: %s",
            user_id[:8], exc,
        )

    return {
        "task_runs": task_runs,
        "pending_proposals": pending_proposals,
        "reviewer_decisions": reviewer_decisions,
    }


def build_headline(counts: dict) -> str:
    """Build the one-line headline from counts.

    Format (per ADR-202 §1 example):
      "3 task runs · 2 proposals pending · 1 reviewer decision"

    Uses singular/plural correctly. All-zero is an empty string — the
    caller uses it to pick the empty-state template.
    """
    t = int(counts.get("task_runs", 0) or 0)
    p = int(counts.get("pending_proposals", 0) or 0)
    r = int(counts.get("reviewer_decisions", 0) or 0)
    parts = [
        f"{t} task run{'s' if t != 1 else ''}",
        f"{p} proposal{'s' if p != 1 else ''} pending",
        f"{r} reviewer decision{'s' if r != 1 else ''}",
    ]
    return " · ".join(parts)


def build_pointer_html(counts: dict, schedule_label: str) -> str:
    """Populated daily-update email — expository pointer shape.

    Shows the counts headline and pointer cluster deep-linking into
    cockpit surfaces. Agent-generated digest content lives at the
    cockpit surface, not in this email.
    """
    headline = build_headline(counts)
    pointers = _build_pointer_cluster_html(counts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Your daily update — YARNNN</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 640px; margin: 32px auto; padding: 0 24px; color: #374151; line-height: 1.6;">
  <h1 style="color: #1a1a2e; font-size: 22px; margin-bottom: 4px;">Your daily update</h1>
  <p style="color: #6b7280; font-size: 14px; margin-top: 0; margin-bottom: 20px;">{headline}</p>
  <div style="margin: 24px 0;">
{pointers}
  </div>
  <hr style="margin: 32px 0; border: 0; border-top: 1px solid #e5e7eb;">
  <p style="color: #6b7280; font-size: 13px;">Daily update · {schedule_label} · <a href="{overview_url()}" style="color: #6b7280;">Open cockpit</a></p>
</body>
</html>"""


def build_pointer_markdown(counts: dict, schedule_label: str) -> str:
    """Markdown counterpart for the output.md file + text/plain email body."""
    headline = build_headline(counts)
    lines = [
        "# Your daily update",
        "",
        f"_{headline}_",
        "",
    ]
    lines.extend(_build_pointer_cluster_markdown(counts))
    lines.extend([
        "",
        "---",
        "",
        f"*Daily update · {schedule_label} · [Open cockpit]({overview_url()})*",
    ])
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# pointer cluster construction
# ---------------------------------------------------------------------------


def _build_pointer_cluster_html(counts: dict) -> str:
    """Emit 2-4 contextual deep-links based on what has content.

    Every pointer is a real cockpit surface. The operator clicks, lands
    in cockpit, operates there.
    """
    pending = int(counts.get("pending_proposals", 0) or 0)
    decisions = int(counts.get("reviewer_decisions", 0) or 0)
    task_runs = int(counts.get("task_runs", 0) or 0)

    lines: list[str] = []
    # Primary: overview
    lines.append(_pointer_line_html(
        label=f"See today's overview →",
        url=overview_url(),
    ))
    # Contextual: queue when there are pending proposals
    if pending > 0:
        label = (
            f"Review {pending} pending proposal →"
            if pending == 1
            else f"Review {pending} pending proposals →"
        )
        lines.append(_pointer_line_html(
            label=label,
            url=overview_url(focus="queue"),
        ))
    # Contextual: review stream when there are recent decisions
    if decisions > 0:
        label = (
            f"See {decisions} new reviewer decision →"
            if decisions == 1
            else f"See {decisions} new reviewer decisions →"
        )
        since_iso = _since_iso()
        lines.append(_pointer_line_html(
            label=label,
            url=review_url(since=since_iso),
        ))
    # Contextual: money-truth summary when task activity suggests outcomes
    if task_runs > 0:
        lines.append(_pointer_line_html(
            label="Open your book →",
            url=context_path_url("/workspace/context/_performance_summary.md"),
        ))
    return "\n".join(lines)


def _build_pointer_cluster_markdown(counts: dict) -> list[str]:
    pending = int(counts.get("pending_proposals", 0) or 0)
    decisions = int(counts.get("reviewer_decisions", 0) or 0)
    task_runs = int(counts.get("task_runs", 0) or 0)

    lines = [f"- [See today's overview →]({overview_url()})"]
    if pending > 0:
        label = (
            f"Review {pending} pending proposal →"
            if pending == 1
            else f"Review {pending} pending proposals →"
        )
        lines.append(f"- [{label}]({overview_url(focus='queue')})")
    if decisions > 0:
        label = (
            f"See {decisions} new reviewer decision →"
            if decisions == 1
            else f"See {decisions} new reviewer decisions →"
        )
        since_iso = _since_iso()
        lines.append(f"- [{label}]({review_url(since=since_iso)})")
    if task_runs > 0:
        lines.append(
            f"- [Open your book →]"
            f"({context_path_url('/workspace/context/_performance_summary.md')})"
        )
    return lines


def _pointer_line_html(*, label: str, url: str) -> str:
    return (
        f'    <p style="margin: 8px 0;">'
        f'<a href="{url}" style="color: #3b82f6; text-decoration: none; font-weight: 500;">{label}</a>'
        f'</p>'
    )


def _since_iso() -> str:
    """ISO timestamp for 'since yesterday UTC' filter in deep-links."""
    now = datetime.now(timezone.utc)
    yesterday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    return yesterday.isoformat()
