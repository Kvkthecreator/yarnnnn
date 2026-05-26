"""
MirrorScheduleIndex Primitive — ADR-301

Projects the workspace's `tasks` scheduling index (slug + schedule + mode +
last_run_at + next_run_at + paused) into a compact substrate file the
Reviewer reads at every wake. Closes the schedule-hallucination class
documented in docs/evaluations/2026-05-24-045348-reviewer-schedule-self-
misdiagnosis/findings.md.

The Reviewer perceives time (ADR-274 Operating Context block) and standing
intent (ADR-284) but had no substrate basis for reasoning about its own
cadence pre-ADR-301. The persona frame instructs it to call ListRevisions +
GetSystemState mid-loop, but under bounded tool-round budgets the Reviewer
skipped the verification round and made up the schedule literal. ADR-301
puts the schedule literal + last_run_at + next_run_at in the envelope so
the Reviewer reasons from substrate, not memory.

Surface:
  MirrorScheduleIndex(diff_aware: bool = True)

Behavior:
  1. Query `tasks` for all rows belonging to the workspace (active +
     paused — paused recurrences are part of the cadence picture).
  2. Read each row's declaration_path content from workspace_files to
     extract the literal schedule string + mode. Without declaration_path
     the row's `schedule` column is the fallback.
  3. Compose a compact markdown summary with a table per recurrence.
  4. Diff-aware: skip the write when content unchanged (no revision noise).
  5. Otherwise write via `write_revision()` with
     `authored_by="system:mirror-schedule-index"` per ADR-209.

Returns:
  {success, paths_written, paths_skipped, recurrences_count, error?}

Dispatch surface:
  Kernel maintenance phase only (ADR-301 D4) — called per scheduler tick
  from `unified_scheduler.py` via `services.kernel_mirrors`. NOT in
  CHAT/HEADLESS/REVIEWER_PRIMITIVES per ADR-301 D6 (the Reviewer reads
  the mirrored file; it does not invoke the mirror).
"""

from __future__ import annotations

import logging
import re as _re
from datetime import datetime, timezone
from typing import Any

import yaml as _yaml

from services.workspace_paths import MEMORY_SCHEDULE_INDEX_PATH

logger = logging.getLogger(__name__)


def _extract_schedule_and_mode_from_declaration(
    declaration_content: str, slug: str
) -> tuple[str, str]:
    """Extract the literal schedule string + mode from a _recurrences.yaml
    body, by slug. Returns ("?", "judgment") on parse failure.

    The YAML shape is a top-level list of recurrence dicts; each dict has
    at minimum `slug`, `schedule`, optionally `mode`. We use yaml.safe_load
    when possible; on malformed input we fall back to regex on the raw
    text bounded to the slug's block.
    """
    try:
        parsed = _yaml.safe_load(declaration_content)
        if isinstance(parsed, list):
            for entry in parsed:
                if isinstance(entry, dict) and entry.get("slug") == slug:
                    schedule = entry.get("schedule")
                    mode = entry.get("mode", "judgment")
                    if isinstance(schedule, (list, tuple)):
                        # Multi-fire shapes like ["@market_open + 15min",
                        # "@market_open + 3h"] preserve as JSON-ish literal
                        schedule_str = "[" + ", ".join(
                            f"`{s}`" for s in schedule
                        ) + "]"
                    elif schedule is None:
                        schedule_str = "?"
                    else:
                        schedule_str = f"`{schedule}`"
                    return schedule_str, str(mode)
    except Exception:
        pass

    # Regex fallback — bounded to the slug's block
    slug_pattern = _re.compile(
        rf"-\s*slug:\s*{_re.escape(slug)}\b(.*?)(?=\n-\s*slug:|\Z)",
        _re.DOTALL,
    )
    m = slug_pattern.search(declaration_content)
    if m:
        block = m.group(1)
        sched_m = _re.search(r"schedule:\s*(.+?)$", block, _re.MULTILINE)
        mode_m = _re.search(r"mode:\s*(\w+)", block)
        schedule_str = (
            f"`{sched_m.group(1).strip()}`" if sched_m else "?"
        )
        mode_str = mode_m.group(1) if mode_m else "judgment"
        return schedule_str, mode_str
    return "?", "judgment"


def _format_timestamp(ts: Any) -> str:
    """Format a timestamp value (string from PostgREST) as 'YYYY-MM-DDTHH:MM:SSZ'
    or '—' when None/unparseable."""
    if not ts:
        return "—"
    if isinstance(ts, str):
        try:
            # PostgREST returns ISO-8601 strings with timezone offset
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return ts
    return str(ts)


async def handle_mirror_schedule_index(auth: Any, input: dict) -> dict:
    """Execute MirrorScheduleIndex primitive (ADR-301).

    Inputs:
      diff_aware: bool — default True; skip write when content unchanged

    Returns:
      {
        "success": bool,
        "paths_written": list[str],
        "paths_skipped": list[str],
        "recurrences_count": int,
        "error": str | None,
      }
    """
    diff_aware = input.get("diff_aware", True)

    client = getattr(auth, "client", None)
    user_id = getattr(auth, "user_id", None)
    if client is None or not user_id:
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "recurrences_count": 0,
            "error": "missing auth context (client or user_id)",
        }

    output_path = f"/workspace/{MEMORY_SCHEDULE_INDEX_PATH}"

    # --- Query tasks scheduling index ---
    try:
        tasks_res = (
            client.table("tasks")
            .select(
                "slug, status, schedule, next_run_at, last_run_at, "
                "paused, declaration_path"
            )
            .eq("user_id", user_id)
            .neq("status", "archived")
            .order("slug")
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "[MIRROR_SCHEDULE_INDEX] tasks query failed for user=%s: %s",
            user_id[:8], exc,
        )
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "recurrences_count": 0,
            "error": f"tasks query failed: {exc}",
        }

    task_rows = tasks_res.data or []

    # --- Read declaration files in one batch ---
    declaration_paths = sorted({
        row.get("declaration_path") for row in task_rows
        if row.get("declaration_path")
    })
    declarations: dict[str, str] = {}
    if declaration_paths:
        try:
            decl_res = (
                client.table("workspace_files")
                .select("path, content")
                .eq("user_id", user_id)
                .in_("path", list(declaration_paths))
                .execute()
            )
            for row in decl_res.data or []:
                declarations[row.get("path", "")] = row.get("content", "")
        except Exception as exc:
            logger.warning(
                "[MIRROR_SCHEDULE_INDEX] declaration read failed for user=%s: %s",
                user_id[:8], exc,
            )
            # Fall through — we'll use the tasks.schedule column as fallback

    # --- Compose the summary ---
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    frontmatter = (
        f"---\n"
        f"as_of: {now_iso}\n"
        f"recurrences_count: {len(task_rows)}\n"
        f"---\n\n"
    )

    if not task_rows:
        summary = (
            frontmatter
            + "# Schedule Index\n\n_(no recurrences declared in this workspace)_\n"
        )
    else:
        header = (
            "# Schedule Index\n\n"
            "| slug | schedule | mode | last_run_at | next_run_at | paused |\n"
            "|---|---|---|---|---|---|\n"
        )
        lines: list[str] = []
        for row in task_rows:
            slug = row.get("slug") or "?"
            decl_path = row.get("declaration_path")
            decl_content = declarations.get(decl_path or "", "")
            if decl_content:
                schedule_str, mode_str = (
                    _extract_schedule_and_mode_from_declaration(
                        decl_content, slug
                    )
                )
            else:
                # Fallback: use tasks.schedule column (cron string, no mode)
                fallback = row.get("schedule")
                schedule_str = f"`{fallback}`" if fallback else "?"
                mode_str = "judgment"  # Conservative default
            last_run = _format_timestamp(row.get("last_run_at"))
            next_run = _format_timestamp(row.get("next_run_at"))
            paused = "true" if row.get("paused") else "false"
            lines.append(
                f"| {slug} | {schedule_str} | {mode_str} | "
                f"{last_run} | {next_run} | {paused} |"
            )
        summary = frontmatter + header + "\n".join(lines) + "\n"

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
            # Diff-aware comparison: strip the frontmatter `as_of:` line so
            # an unchanged schedule index doesn't churn revisions every tick.
            def _strip_as_of(s: str) -> str:
                return _re.sub(r"^as_of:.*$", "as_of: <ts>", s, count=1, flags=_re.MULTILINE)
            if _strip_as_of(prior_content) == _strip_as_of(summary):
                return {
                    "success": True,
                    "paths_written": [],
                    "paths_skipped": [output_path],
                    "recurrences_count": len(task_rows),
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
            authored_by="system:mirror-schedule-index",
            message=f"mirrored {len(task_rows)} recurrence(s) → _schedule_index.md",
            summary="Schedule index substrate (ADR-301 — Reviewer pulse envelope)",
            tags=["pulse", "schedule-index", "adr-301"],
            lifecycle="active",
            content_type="text/markdown",
        )
        return {
            "success": True,
            "paths_written": [output_path],
            "paths_skipped": [],
            "recurrences_count": len(task_rows),
            "error": None,
        }
    except Exception as exc:
        logger.warning(
            "[MIRROR_SCHEDULE_INDEX] write failed for user=%s path=%s: %s",
            user_id[:8], output_path, exc,
        )
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "recurrences_count": len(task_rows),
            "error": f"write failed: {exc}",
        }
