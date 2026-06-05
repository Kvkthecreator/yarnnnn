"""
MirrorRecentExecution Primitive — ADR-301 (ratifies ADR-285 D3)

Projects the workspace's recent `execution_events` rows (last 24h window)
into a compact substrate file the Reviewer reads at every wake. Pair with
MirrorScheduleIndex: together they give the Reviewer substrate basis for
reasoning about its own pulse — what is supposed to fire and when (schedule
index) + what actually fired recently and with what outcome (recent
execution lineage).

The pre-ADR-301 gap: the Reviewer perceived time (Operating Context) but
not what the system had been doing in time. Persona-frame instructions
named GetSystemState / ListRevisions for runtime querying — under bounded
tool-round budgets the Reviewer skipped the verification round and made up
the recent-activity picture. ADR-301 puts the activity rollup in the
envelope so the Reviewer reasons from substrate.

Surface:
  MirrorRecentExecution(window_hours: int = 24, diff_aware: bool = True)

Behavior:
  1. Query `execution_events` for rows in the last N hours belonging to
     the workspace.
  2. Compose a compact markdown summary: line-per-fire (sorted newest →
     oldest) + per-mode counts.
  3. Diff-aware: skip write when content unchanged (excluding the
     `as_of:` frontmatter timestamp).
  4. Write via `write_revision()` with
     `authored_by="system:mirror-recent-execution"` per ADR-209.

Returns:
  {success, paths_written, paths_skipped, events_processed, error?}

Dispatch surface:
  Kernel maintenance phase only (ADR-301 D4) — called per scheduler tick
  from `unified_scheduler.py` via `services.kernel_mirrors`. NOT in
  CHAT/HEADLESS/REVIEWER_PRIMITIVES per ADR-301 D6.
"""

from __future__ import annotations

import logging
import re as _re
from datetime import datetime, timedelta, timezone
from typing import Any

from services.workspace_paths import SYSTEM_RECENT_EXECUTION_PATH

logger = logging.getLogger(__name__)


def _format_event_line(row: dict) -> str:
    """Format one execution_events row as a one-line substrate entry."""
    created_at = row.get("created_at") or ""
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            ts = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            ts = created_at
    else:
        ts = "?"
    slug = row.get("slug") or "?"
    mode = row.get("mode") or "?"
    status = row.get("status") or "?"
    wake_source = row.get("wake_source") or ""
    funnel = row.get("funnel_decision") or ""
    cost = row.get("cost_usd")
    duration_ms = row.get("duration_ms")
    duration_str = (
        f"{duration_ms / 1000:.1f}s" if isinstance(duration_ms, (int, float))
        else "—"
    )
    cost_str = f"${cost:.3f}" if isinstance(cost, (int, float)) else "$0"
    src_str = (
        f" · {wake_source}" if wake_source else ""
    ) + (
        f"/{funnel}" if wake_source and funnel else ""
    )
    return (
        f"- {ts} · {slug} · {mode} · {status}{src_str} · "
        f"{duration_str} · {cost_str}"
    )


async def handle_mirror_recent_execution(auth: Any, input: dict) -> dict:
    """Execute MirrorRecentExecution primitive (ADR-301).

    Inputs:
      window_hours: int — default 24; lookback window
      diff_aware: bool — default True; skip write when content unchanged

    Returns:
      {
        "success": bool,
        "paths_written": list[str],
        "paths_skipped": list[str],
        "events_processed": int,
        "error": str | None,
      }
    """
    window_hours = input.get("window_hours", 24)
    if not isinstance(window_hours, int) or window_hours < 1:
        window_hours = 24
    diff_aware = input.get("diff_aware", True)

    client = getattr(auth, "client", None)
    user_id = getattr(auth, "user_id", None)
    if client is None or not user_id:
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "events_processed": 0,
            "error": "missing auth context (client or user_id)",
        }

    output_path = f"/workspace/{SYSTEM_RECENT_EXECUTION_PATH}"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- Query execution_events ---
    try:
        res = (
            client.table("execution_events")
            .select(
                "created_at, slug, mode, status, trigger_type, "
                "wake_source, funnel_decision, cost_usd, duration_ms, "
                "input_tokens, output_tokens, error_reason"
            )
            .eq("user_id", user_id)
            .gte("created_at", cutoff_iso)
            .order("created_at", desc=True)
            .limit(200)  # Defensive bound; typical workspace produces <30/day
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "[MIRROR_RECENT_EXECUTION] query failed for user=%s: %s",
            user_id[:8], exc,
        )
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "events_processed": 0,
            "error": f"query failed: {exc}",
        }

    rows = res.data or []

    # --- Compose summary ---
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    frontmatter = (
        f"---\n"
        f"as_of: {now_iso}\n"
        f"window: {window_hours}h\n"
        f"fire_count: {len(rows)}\n"
        f"---\n\n"
    )

    if not rows:
        summary = (
            frontmatter
            + f"# Recent Execution Lineage\n\n"
            + f"_(no execution_events in the last {window_hours}h)_\n"
        )
    else:
        # Per-mode counts (deterministic — no pattern detection in Phase 1)
        judgment_count = sum(1 for r in rows if r.get("mode") == "judgment")
        mechanical_count = sum(1 for r in rows if r.get("mode") == "mechanical")
        judgment_failures = sum(
            1 for r in rows
            if r.get("mode") == "judgment" and r.get("status") != "success"
        )
        mechanical_failures = sum(
            1 for r in rows
            if r.get("mode") == "mechanical" and r.get("status") != "success"
        )
        judgment_cost = sum(
            float(r.get("cost_usd") or 0)
            for r in rows if r.get("mode") == "judgment"
        )

        # Per-wake-source counts
        wake_source_counts: dict[str, int] = {}
        for r in rows:
            ws = r.get("wake_source")
            if ws:
                wake_source_counts[ws] = wake_source_counts.get(ws, 0) + 1

        body_lines = [
            "# Recent Execution Lineage",
            "",
            f"## Last {window_hours}h ({len(rows)} fires)",
            "",
        ]
        body_lines.extend(_format_event_line(r) for r in rows[:50])  # Cap at 50 for envelope sanity
        if len(rows) > 50:
            body_lines.append(f"- _(+{len(rows) - 50} older events truncated)_")
        body_lines.extend([
            "",
            "## Counts",
            "",
            f"- judgment fires: {judgment_count} · "
            f"{judgment_failures} failure(s) · ${judgment_cost:.3f} total",
            f"- mechanical fires: {mechanical_count} · "
            f"{mechanical_failures} failure(s) · $0 total",
        ])
        if wake_source_counts:
            body_lines.append("")
            body_lines.append("## Wake sources")
            body_lines.append("")
            for src in sorted(wake_source_counts):
                body_lines.append(f"- {src}: {wake_source_counts[src]} fire(s)")
        summary = frontmatter + "\n".join(body_lines) + "\n"

    # --- Diff-aware skip ---
    if diff_aware:
        try:
            existing = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", output_path)
                .limit(1)
                .execute()
            )
            prior_content = (existing.data or [{}])[0].get("content") or ""
            # Strip the volatile `as_of:` line for diff comparison
            def _strip_as_of(s: str) -> str:
                return _re.sub(
                    r"^as_of:.*$", "as_of: <ts>",
                    s, count=1, flags=_re.MULTILINE,
                )
            if _strip_as_of(prior_content) == _strip_as_of(summary):
                return {
                    "success": True,
                    "paths_written": [],
                    "paths_skipped": [output_path],
                    "events_processed": len(rows),
                    "error": None,
                }
        except Exception:
            pass

    # --- Write via Authored Substrate (ADR-209) ---
    try:
        from services.authored_substrate import write_revision

        write_revision(
            client,
            user_id=user_id,
            path=output_path,
            content=summary,
            authored_by="system:mirror-recent-execution",
            message=f"mirrored {len(rows)} event(s) → _recent_execution.md",
            summary="Recent execution lineage substrate (ADR-301 — Reviewer pulse envelope)",
            tags=["pulse", "recent-execution", "adr-301"],
            lifecycle="active",
            content_type="text/markdown",
        )
        return {
            "success": True,
            "paths_written": [output_path],
            "paths_skipped": [],
            "events_processed": len(rows),
            "error": None,
        }
    except Exception as exc:
        logger.warning(
            "[MIRROR_RECENT_EXECUTION] write failed for user=%s path=%s: %s",
            user_id[:8], output_path, exc,
        )
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "events_processed": len(rows),
            "error": f"write failed: {exc}",
        }
