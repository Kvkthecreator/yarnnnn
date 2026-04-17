"""Back Office: Proposal Cleanup — ADR-193 Phase 5.

Sweeps `action_proposals` rows that are still `status='pending'` past
their `expires_at` and marks them `status='expired'`. Runs as a daily
back-office task owned by YARNNN (per ADR-164 pattern).

Zero LLM cost — deterministic SQL update only. Output is a markdown
report with counts.

The executor scopes by user_id so task runs don't touch other users'
proposals (parallel to workspace_cleanup pattern from ADR-164).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Mark pending proposals past expires_at as expired.

    Returns the standard back-office executor shape:
      {
          "content": "<markdown report>",
          "structured": {"expired_count": int, "errors": [str]},
      }
    """
    started_at = datetime.now(timezone.utc)
    now_iso = started_at.isoformat()

    expired_count = 0
    errors: list[str] = []

    try:
        # Select pending proposals that have expired for this user
        result = (
            client.table("action_proposals")
            .select("id, action_type, expires_at")
            .eq("user_id", user_id)
            .eq("status", "pending")
            .lt("expires_at", now_iso)
            .execute()
        )
        to_expire = result.data or []

        if to_expire:
            ids = [row["id"] for row in to_expire]
            update_result = (
                client.table("action_proposals")
                .update({"status": "expired"})
                .in_("id", ids)
                .execute()
            )
            expired_count = len(update_result.data or [])
            logger.info(
                f"[PROPOSAL_CLEANUP] user={user_id[:8]} expired {expired_count} "
                f"pending proposals past TTL"
            )
    except Exception as e:
        msg = f"proposal cleanup query/update failed: {e}"
        errors.append(msg)
        logger.warning(f"[PROPOSAL_CLEANUP] {msg}")

    finished_at = datetime.now(timezone.utc)
    duration_s = (finished_at - started_at).total_seconds()

    # Markdown report (delivered to task output folder)
    report_lines = [
        f"# Proposal Cleanup — {started_at.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"Expired {expired_count} pending proposal(s) past TTL.",
        f"Run duration: {duration_s:.2f}s",
    ]
    if errors:
        report_lines.append("")
        report_lines.append("## Errors")
        for err in errors:
            report_lines.append(f"- {err}")

    return {
        "content": "\n".join(report_lines) + "\n",
        "structured": {
            "expired_count": expired_count,
            "duration_seconds": duration_s,
            "errors": errors,
        },
    }
