"""
ADR-231 Phase 3.5 — data migration script.

Migrates existing `tasks` rows + `/tasks/{slug}/TASK.md` files to YAML
recurrence declarations at natural-home locations per ADR-231 D2/D3.

Idempotent. Reversible (every write goes through ADR-209 write_revision
with full attribution and revision history).

Per-task flow:
  1. Read tasks row → derive (slug, schedule, status, paused).
  2. Read /tasks/{slug}/TASK.md via UserMemory.
  3. Parse via task_pipeline.parse_task_md (last legitimate use; the
     parser dies in Phase 3.7 alongside task_pipeline.py).
  4. Determine RecurrenceShape from parsed `**Output:**` field.
  5. Build YAML declaration at the natural-home path per
     services.recurrence.derive_declaration_path.
  6. Write YAML via authored_substrate.write_revision with
     authored_by="system:adr-231-migration".
  7. Update the tasks row to set declaration_path.
  8. (Optional with --archive-legacy) Mark /tasks/{slug}/TASK.md as
     archived; operators stop seeing the dual substrate.

Dry-run mode (--dry-run, default): prints the plan without writing.
Live mode (--apply): performs writes.

Usage:
  python -m scripts.migrate_to_recurrence_declarations \\
      --user-id <UUID> \\
      [--dry-run | --apply] \\
      [--archive-legacy]

Or process all users:
  python -m scripts.migrate_to_recurrence_declarations --all-users [--apply]

Operational sequence (per cutover plan):
  1. Land migration 164 (Phase 3.4) — ✅ done.
  2. Run this script in dry-run against kvk's workspace + each alpha persona;
     eyeball the planned YAML at natural-home paths.
  3. Run with --apply against the same workspaces, in order.
  4. Verify scheduler picks up the new declarations on its next tick.
  5. Phase 3.6 caller migrations begin.

Operational follow-up after apply:
  Run a `materialize_scheduling_index` sweep to populate declaration_path
  on every active row. The script does this automatically per user as a
  final step.
"""

from __future__ import annotations

import argparse
import asyncio
import json as _json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# Allow running as module from api/ root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.recurrence import (
    RecurrenceShape,
    derive_declaration_path,
)
from services.recurrence_paths import resolve_paths
from services.workspace import UserMemory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate-recurrences")


OUTPUT_KIND_TO_SHAPE = {
    "produces_deliverable": RecurrenceShape.DELIVERABLE,
    "accumulates_context": RecurrenceShape.ACCUMULATION,
    "external_action": RecurrenceShape.ACTION,
    "system_maintenance": RecurrenceShape.MAINTENANCE,
}


def _bootstrap_client():
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise SystemExit(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set "
            "(load from .env or environment)"
        )
    return create_client(url, key)


def _shape_for_task(task_info: dict) -> Optional[RecurrenceShape]:
    """Determine RecurrenceShape from parsed TASK.md output_kind."""
    output_kind = task_info.get("output_kind", "produces_deliverable")
    return OUTPUT_KIND_TO_SHAPE.get(output_kind)


def _domain_from_writes(task_info: dict) -> Optional[str]:
    """For ACCUMULATION shape: derive domain slug from context_writes."""
    writes = task_info.get("context_writes") or []
    if not writes:
        return None
    # Filter out 'signals' which is a shared/auxiliary domain — pick the primary
    primary = [w for w in writes if w != "signals"]
    return primary[0] if primary else writes[0]


def _build_yaml_for_deliverable(slug: str, task_info: dict, schedule: Optional[str], paused: bool) -> dict:
    """Build the YAML body for a DELIVERABLE recurrence."""
    body: dict = {"slug": slug}
    if task_info.get("title"):
        body["display_name"] = task_info["title"]
    if task_info.get("agent_slug"):
        body["agents"] = [task_info["agent_slug"]]
    elif task_info.get("process_steps"):
        agents = []
        for step in task_info["process_steps"]:
            ref = step.get("agent_ref") or step.get("agent_type")
            if ref and ref not in agents:
                agents.append(ref)
        if agents:
            body["agents"] = agents
    if task_info.get("context_reads"):
        body["context_reads"] = task_info["context_reads"]
    if task_info.get("context_writes"):
        body["context_writes"] = task_info["context_writes"]
    if task_info.get("required_capabilities"):
        body["required_capabilities"] = task_info["required_capabilities"]
    if task_info.get("delivery"):
        body["delivery"] = task_info["delivery"]
    if task_info.get("page_structure"):
        body["page_structure"] = task_info["page_structure"]
    if task_info.get("objective"):
        obj = task_info["objective"]
        if isinstance(obj, dict):
            deliverable_block = {}
            if obj.get("audience"):
                deliverable_block["audience"] = obj["audience"]
            if task_info.get("page_structure"):
                deliverable_block["page_structure"] = task_info["page_structure"]
            if obj.get("purpose"):
                deliverable_block["purpose"] = obj["purpose"]
            if deliverable_block:
                body["deliverable"] = deliverable_block
        elif isinstance(obj, str):
            body["objective"] = obj
    # Recurring sub-block
    if schedule:
        body["recurring"] = {"schedule": schedule, "paused": paused}
    elif paused:
        body["paused"] = True
    return {"report": body}


def _build_yaml_for_accumulation(slug: str, task_info: dict, schedule: Optional[str], paused: bool) -> dict:
    """Build a single-entry recurrence (will be wrapped in `recurrences:` list)."""
    entry: dict = {"slug": slug}
    if task_info.get("agent_slug"):
        entry["agent"] = task_info["agent_slug"]
    elif task_info.get("process_steps"):
        first = task_info["process_steps"][0] if task_info["process_steps"] else {}
        ref = first.get("agent_ref") or first.get("agent_type")
        if ref:
            entry["agent"] = ref
    if schedule:
        entry["schedule"] = schedule
    if paused:
        entry["paused"] = True
    if task_info.get("objective"):
        obj = task_info["objective"]
        if isinstance(obj, dict) and obj.get("purpose"):
            entry["objective"] = obj["purpose"]
        elif isinstance(obj, str):
            entry["objective"] = obj
    if task_info.get("context_reads"):
        entry["context_reads"] = task_info["context_reads"]
    if task_info.get("context_writes"):
        entry["context_writes"] = task_info["context_writes"]
    if task_info.get("required_capabilities"):
        entry["required_capabilities"] = task_info["required_capabilities"]
    return entry


def _build_yaml_for_action(slug: str, task_info: dict, schedule: Optional[str], paused: bool) -> dict:
    body: dict = {"slug": slug}
    if task_info.get("title"):
        body["display_name"] = task_info["title"]
    if task_info.get("agent_slug"):
        body["agents"] = [task_info["agent_slug"]]
    if task_info.get("required_capabilities"):
        body["required_capabilities"] = task_info["required_capabilities"]
        # Conventional first capability is the target_capability for ACTION
        body["target_capability"] = task_info["required_capabilities"][0]
    if task_info.get("context_reads"):
        body["context_reads"] = task_info["context_reads"]
    if task_info.get("context_writes"):
        body["context_writes"] = task_info["context_writes"]
    if schedule:
        body["recurring"] = {"schedule": schedule, "paused": paused}
    elif paused:
        body["paused"] = True
    return {"action": body}


def _build_back_office_entry(slug: str, task_info: dict, schedule: Optional[str], paused: bool) -> Optional[dict]:
    """Build an entry for the shared back-office.yaml index."""
    # Find executor: directive in process_steps
    executor = None
    process_steps = task_info.get("process_steps", [])
    import re as _re
    for step in process_steps:
        instruction = step.get("instruction", "") or ""
        match = _re.search(r"executor:\s*([\w.]+)", instruction)
        if match:
            executor = match.group(1)
            break
    if not executor:
        # Heuristic fallback: derive from slug (back-office-foo-bar → services.back_office.foo_bar)
        if slug.startswith("back-office-"):
            tail = slug[len("back-office-"):].replace("-", "_")
            executor = f"services.back_office.{tail}"
    if not executor:
        return None
    entry: dict = {
        "slug": slug,
        "executor": executor,
    }
    if schedule:
        entry["schedule"] = schedule
    if paused:
        entry["paused"] = True
    return entry


def _build_yaml_body(
    slug: str,
    shape: RecurrenceShape,
    task_info: dict,
    schedule: Optional[str],
    paused: bool,
) -> Optional[dict]:
    if shape == RecurrenceShape.DELIVERABLE:
        return _build_yaml_for_deliverable(slug, task_info, schedule, paused)
    if shape == RecurrenceShape.ACCUMULATION:
        return _build_yaml_for_accumulation(slug, task_info, schedule, paused)
    if shape == RecurrenceShape.ACTION:
        return _build_yaml_for_action(slug, task_info, schedule, paused)
    if shape == RecurrenceShape.MAINTENANCE:
        return _build_back_office_entry(slug, task_info, schedule, paused)
    return None


def _resolve_target_path(
    slug: str,
    shape: RecurrenceShape,
    task_info: dict,
) -> Optional[str]:
    """Compute the natural-home declaration path."""
    if shape == RecurrenceShape.ACCUMULATION:
        domain = _domain_from_writes(task_info)
        if not domain:
            return None
        return derive_declaration_path(shape, slug, domain=domain)
    return derive_declaration_path(shape, slug)


async def _migrate_user(
    client,
    user_id: str,
    *,
    apply: bool,
    archive_legacy: bool,
) -> dict:
    """Migrate one user's tasks to YAML declarations.

    Returns a stats dict.
    """
    import yaml as _yaml
    from services.task_pipeline import parse_task_md
    from services.authored_substrate import write_revision

    stats = {
        "user_id": user_id,
        "tasks_seen": 0,
        "tasks_migrated": 0,
        "tasks_skipped": 0,
        "tasks_errored": 0,
        "yaml_writes": 0,
        "legacy_archived": 0,
        "errors": [],
    }

    # 1. Read tasks rows
    rows = (
        client.table("tasks")
        .select("id, slug, schedule, status, paused, declaration_path")
        .eq("user_id", user_id)
        .execute()
    )
    rows_data = rows.data or []
    stats["tasks_seen"] = len(rows_data)

    # 2. Read TASK.md content per task in one query
    um = UserMemory(client, user_id)

    # 3. Group plan by target YAML file (multi-decl files need accumulation)
    # multi_decl_writes[abs_path] = list of entry dicts
    multi_decl_writes: dict[str, list[dict]] = {}
    single_decl_writes: dict[str, dict] = {}  # abs_path -> body dict
    slug_to_abs: dict[str, str] = {}  # slug -> abs_path

    for row in rows_data:
        slug = row["slug"]
        try:
            task_md_path = f"tasks/{slug}/TASK.md"  # UserMemory base is /workspace; prepend differently
            # TASK.md actually lives at /tasks/{slug}/TASK.md, NOT under /workspace/.
            # We need to read directly from workspace_files.
            res = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", f"/tasks/{slug}/TASK.md")
                .limit(1)
                .execute()
            )
            if not res.data:
                stats["tasks_skipped"] += 1
                logger.warning("no TASK.md for %s/%s; skipping", user_id[:8], slug)
                continue
            task_md = res.data[0]["content"]
            task_info = parse_task_md(task_md)
            shape = _shape_for_task(task_info)
            if shape is None:
                stats["tasks_skipped"] += 1
                logger.warning(
                    "could not infer shape for %s/%s (output_kind=%s); skipping",
                    user_id[:8], slug, task_info.get("output_kind"),
                )
                continue

            target_path = _resolve_target_path(slug, shape, task_info)
            if target_path is None:
                stats["tasks_skipped"] += 1
                logger.warning("could not resolve target path for %s/%s; skipping", user_id[:8], slug)
                continue

            schedule = row.get("schedule") or task_info.get("schedule") or None
            paused = bool(row.get("paused", False))

            body_or_entry = _build_yaml_body(slug, shape, task_info, schedule, paused)
            if body_or_entry is None:
                stats["tasks_errored"] += 1
                stats["errors"].append(f"could not build YAML for {slug}")
                continue

            slug_to_abs[slug] = target_path

            if shape in (RecurrenceShape.ACCUMULATION, RecurrenceShape.MAINTENANCE):
                multi_decl_writes.setdefault(target_path, []).append(body_or_entry)
            else:
                single_decl_writes[target_path] = body_or_entry

        except Exception as e:
            stats["tasks_errored"] += 1
            stats["errors"].append(f"{slug}: {e}")
            logger.exception("error processing %s/%s: %s", user_id[:8], slug, e)

    # 4. Plan summary
    logger.info(
        "[%s] plan: %d single-decl YAMLs, %d multi-decl YAMLs",
        user_id[:8],
        len(single_decl_writes),
        len(multi_decl_writes),
    )

    # 5. Apply writes
    for abs_path, body in single_decl_writes.items():
        relative = abs_path[len("/workspace/"):] if abs_path.startswith("/workspace/") else None
        if not relative:
            logger.warning("skipping non-/workspace/ path: %s", abs_path)
            continue
        yaml_text = _yaml.safe_dump(body, sort_keys=False, default_flow_style=False)
        if apply:
            try:
                await um.write(
                    relative,
                    yaml_text,
                    authored_by="system:adr-231-migration",
                    message=f"Migrated TASK.md to YAML declaration per ADR-231 D2/D3",
                )
                stats["yaml_writes"] += 1
                logger.info("[apply] wrote %s", abs_path)
            except Exception as e:
                stats["tasks_errored"] += 1
                stats["errors"].append(f"write {abs_path}: {e}")
        else:
            logger.info("[dry-run] would write %s:\n%s", abs_path, yaml_text)

    for abs_path, entries in multi_decl_writes.items():
        relative = abs_path[len("/workspace/"):] if abs_path.startswith("/workspace/") else None
        if not relative:
            logger.warning("skipping non-/workspace/ path: %s", abs_path)
            continue
        # back-office.yaml uses `back_office_jobs:` wrapper; domain _recurring uses `recurrences:`
        if abs_path.endswith("back-office.yaml"):
            wrapped = {"back_office_jobs": entries}
        else:
            wrapped = {"recurrences": entries}
        yaml_text = _yaml.safe_dump(wrapped, sort_keys=False, default_flow_style=False)
        if apply:
            try:
                await um.write(
                    relative,
                    yaml_text,
                    authored_by="system:adr-231-migration",
                    message=f"Migrated {len(entries)} TASK.md to multi-decl YAML per ADR-231 D2/D3",
                )
                stats["yaml_writes"] += 1
                logger.info("[apply] wrote %s (%d entries)", abs_path, len(entries))
            except Exception as e:
                stats["tasks_errored"] += 1
                stats["errors"].append(f"write {abs_path}: {e}")
        else:
            logger.info("[dry-run] would write %s (%d entries):\n%s", abs_path, len(entries), yaml_text)

    # 6. Update tasks rows with declaration_path + count migrated
    for row in rows_data:
        slug = row["slug"]
        target_path = slug_to_abs.get(slug)
        if not target_path:
            continue
        if apply:
            try:
                client.table("tasks").update({
                    "declaration_path": target_path,
                }).eq("id", row["id"]).execute()
                stats["tasks_migrated"] += 1
            except Exception as e:
                stats["tasks_errored"] += 1
                stats["errors"].append(f"update tasks row {slug}: {e}")
        else:
            stats["tasks_migrated"] += 1
            logger.info("[dry-run] would set tasks.declaration_path=%s for %s", target_path, slug)

    # 7. Optional: archive legacy TASK.md files
    if archive_legacy:
        for slug in slug_to_abs.keys():
            legacy_path = f"/tasks/{slug}/TASK.md"
            if apply:
                try:
                    # Mark legacy file as archived (lifecycle='archived' isn't valid post-159;
                    # the cleanest path is to write a final revision noting the migration,
                    # then DELETE the row — preserves the history in workspace_file_versions).
                    res = (
                        client.table("workspace_files")
                        .select("id")
                        .eq("user_id", user_id)
                        .eq("path", legacy_path)
                        .limit(1)
                        .execute()
                    )
                    if res.data:
                        # Final revision noting the migration
                        await write_revision(
                            client,
                            user_id=user_id,
                            path=legacy_path,
                            content=f"<!-- Migrated to {slug_to_abs[slug]} per ADR-231 D2 (2026-04-29) -->\n",
                            authored_by="system:adr-231-migration",
                            message=f"Archive — migrated to {slug_to_abs[slug]}",
                        )
                        # Delete the workspace_files row (history preserved in workspace_file_versions)
                        client.table("workspace_files").delete().eq("id", res.data[0]["id"]).execute()
                        stats["legacy_archived"] += 1
                except Exception as e:
                    stats["errors"].append(f"archive {legacy_path}: {e}")
            else:
                logger.info("[dry-run] would archive %s", legacy_path)

    # 8. Final: materialize_scheduling_index sweep so declaration_path populates
    if apply:
        try:
            from services.scheduling import materialize_scheduling_index
            touched = await materialize_scheduling_index(client, user_id)
            logger.info("[apply] materialize_scheduling_index touched %d rows", touched)
        except Exception as e:
            stats["errors"].append(f"materialize_scheduling_index: {e}")

    return stats


async def main():
    parser = argparse.ArgumentParser(description="ADR-231 Phase 3.5 data migration")
    parser.add_argument("--user-id", help="UUID of a single user to migrate")
    parser.add_argument("--all-users", action="store_true", help="Process all users with active tasks")
    parser.add_argument("--apply", action="store_true", help="Perform writes (default: dry-run)")
    parser.add_argument("--archive-legacy", action="store_true", help="After migration, archive /tasks/{slug}/TASK.md files")
    args = parser.parse_args()

    if not args.user_id and not args.all_users:
        parser.error("must pass --user-id <UUID> or --all-users")

    client = _bootstrap_client()

    if args.all_users:
        users_result = (
            client.table("tasks")
            .select("user_id")
            .execute()
        )
        user_ids = sorted(set(r["user_id"] for r in (users_result.data or [])))
    else:
        user_ids = [args.user_id]

    logger.info(
        "ADR-231 Phase 3.5 migration starting — %d user(s), mode=%s, archive_legacy=%s",
        len(user_ids),
        "APPLY" if args.apply else "DRY-RUN",
        args.archive_legacy,
    )

    overall = {
        "users": len(user_ids),
        "tasks_seen": 0,
        "tasks_migrated": 0,
        "tasks_skipped": 0,
        "tasks_errored": 0,
        "yaml_writes": 0,
        "legacy_archived": 0,
        "errors_per_user": {},
    }

    for uid in user_ids:
        logger.info("=" * 70)
        logger.info("processing user %s", uid)
        stats = await _migrate_user(
            client, uid,
            apply=args.apply,
            archive_legacy=args.archive_legacy,
        )
        overall["tasks_seen"] += stats["tasks_seen"]
        overall["tasks_migrated"] += stats["tasks_migrated"]
        overall["tasks_skipped"] += stats["tasks_skipped"]
        overall["tasks_errored"] += stats["tasks_errored"]
        overall["yaml_writes"] += stats["yaml_writes"]
        overall["legacy_archived"] += stats["legacy_archived"]
        if stats["errors"]:
            overall["errors_per_user"][uid] = stats["errors"]
        logger.info("user %s done: %s", uid[:8], _json.dumps({k: v for k, v in stats.items() if k != "errors"}, indent=2))

    logger.info("=" * 70)
    logger.info("OVERALL: %s", _json.dumps(overall, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
