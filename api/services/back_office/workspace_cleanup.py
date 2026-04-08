"""Back Office: Workspace Cleanup — ADR-164.

Migrated from the hourly ephemeral file cleanup block that used to live in
`unified_scheduler.run_unified_scheduler()` (ADR-119/127).

Two-tier TTL policy:
  - Tier 1: `/working/` scratch files — 24h TTL
  - Tier 2: `/user_shared/` staging files — 30 day TTL (ADR-127)

Runs daily (not hourly — per ADR-164 design constraint that back office
task cadences be set to what makes sense for observation, not just
technical efficiency). The 24h TTL guarantee is unchanged; files just
get cleaned up within 24h of becoming eligible instead of within 1h.

Zero LLM cost — deterministic SQL deletes only. Output is a markdown
report with the counts and any errors encountered.

IMPORTANT: this executor touches ALL users' workspace_files rows that
match the ephemeral lifecycle + path filter, BUT it is called from the
task pipeline which is per-user. The executor filters by user_id to
stay within the caller's workspace. Cross-user contamination is not
possible.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


# TTL windows. These match the pre-ADR-164 values in unified_scheduler.
# Changing them requires a follow-up — the ADR-127 and ADR-119 contracts
# are 24h for /working/ and 30d for /user_shared/.
WORKING_TTL_HOURS = 24
USER_SHARED_TTL_DAYS = 30


async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Execute ephemeral workspace cleanup for the given user.

    Deletes workspace_files rows where:
      - lifecycle = 'ephemeral'
      - user_id matches the caller
      - path is under /working/ and older than WORKING_TTL_HOURS, OR
      - path is under /user_shared/ and older than USER_SHARED_TTL_DAYS

    Returns the same shape as other back office executors.
    """
    started_at = datetime.now(timezone.utc)

    working_count = 0
    user_shared_count = 0
    errors: list[str] = []

    # Tier 1: /working/ scratch files — 24h TTL
    try:
        working_cutoff = (started_at - timedelta(hours=WORKING_TTL_HOURS)).isoformat()
        working_result = (
            client.table("workspace_files")
            .delete()
            .eq("user_id", user_id)
            .eq("lifecycle", "ephemeral")
            .like("path", "%/working/%")
            .lt("updated_at", working_cutoff)
            .execute()
        )
        working_count = len(working_result.data or [])
    except Exception as e:
        err = f"/working/ cleanup failed: {e}"
        logger.warning(f"[BACK_OFFICE:workspace_cleanup] {err}")
        errors.append(err)

    # Tier 2: /user_shared/ staging files — 30 day TTL (ADR-127)
    try:
        shared_cutoff = (started_at - timedelta(days=USER_SHARED_TTL_DAYS)).isoformat()
        shared_result = (
            client.table("workspace_files")
            .delete()
            .eq("user_id", user_id)
            .eq("lifecycle", "ephemeral")
            .like("path", "%/user_shared/%")
            .lt("updated_at", shared_cutoff)
            .execute()
        )
        user_shared_count = len(shared_result.data or [])
    except Exception as e:
        err = f"/user_shared/ cleanup failed: {e}"
        logger.warning(f"[BACK_OFFICE:workspace_cleanup] {err}")
        errors.append(err)

    total = working_count + user_shared_count
    summary = f"Cleaned {total} ephemeral files ({working_count} /working/, {user_shared_count} /user_shared/)."
    if errors:
        summary += f" {len(errors)} error(s) encountered."

    actions_taken = [
        {"action": "delete_ephemeral", "scope": "/working/", "count": working_count},
        {"action": "delete_ephemeral", "scope": "/user_shared/", "count": user_shared_count},
    ]

    output_markdown = _format_report(
        started_at, working_count, user_shared_count, errors
    )

    logger.info(f"[BACK_OFFICE:workspace_cleanup] {summary}")

    return {
        "summary": summary,
        "output_markdown": output_markdown,
        "actions_taken": actions_taken,
    }


def _format_report(
    started_at: datetime,
    working_count: int,
    user_shared_count: int,
    errors: list[str],
) -> str:
    date_str = started_at.strftime("%Y-%m-%d %H:%M UTC")
    total = working_count + user_shared_count

    lines = [
        f"# Workspace Cleanup — {date_str}",
        "",
        "## Summary",
        f"Cleaned **{total}** ephemeral files this cycle.",
        "",
        "## Policy",
        f"- Tier 1 — `/working/` scratch files: **{WORKING_TTL_HOURS}h** TTL (ADR-119)",
        f"- Tier 2 — `/user_shared/` staging files: **{USER_SHARED_TTL_DAYS}d** TTL (ADR-127)",
        "",
        "## Results",
        "",
        "| Tier | Path pattern | TTL | Files deleted |",
        "|---|---|---:|---:|",
        f"| 1 | `/working/` | {WORKING_TTL_HOURS}h | {working_count} |",
        f"| 2 | `/user_shared/` | {USER_SHARED_TTL_DAYS}d | {user_shared_count} |",
        "",
    ]

    if errors:
        lines.append("## Errors")
        lines.append("")
        for err in errors:
            lines.append(f"- {err}")
        lines.append("")

    lines.append(f"<!-- executor: services.back_office.workspace_cleanup · version: 1 -->")

    return "\n".join(lines) + "\n"
