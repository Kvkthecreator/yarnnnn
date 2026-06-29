"""
Phase B.2 — Live Data Migration to /workspace/_recurrences.yaml.

ADR-261 D2 cutover. For each user with legacy per-shape declaration
files, projects them into the canonical /workspace/_recurrences.yaml
with the unified {slug, schedule, prompt} schema, then deletes the
legacy files.

Forward-only per the operator's singular-implementation directive
(2026-05-10): no backup, no dual-write window. ADR-209 revision chain
preserves the legacy YAML content as parent revisions of the new
_recurrences.yaml writes (and as parent revisions of the deletion
writes for the legacy files).

The projection rules ratified at planning time:

  back-office.yaml entry  →  one _recurrences.yaml entry
                              schedule = entry.schedule
                              prompt   = constructed from executor name
                              The deterministic Python executor is gone
                              per ADR-261 D6 §4 — the prompt now directs
                              the Reviewer to do the maintenance work.

  context/{domain}/_recurring.yaml[*]  →  one entry per recurrences[i]
                              schedule = entry.schedule
                              prompt   = constructed from agent + domain
                                         + objective + context_writes

  operations/{slug}/_action.yaml  →  one entry
                              schedule = action.recurring.schedule (often null)
                              prompt   = constructed from action body

  reports/{slug}/_spec.yaml  →  one entry
                              schedule = report.recurring.schedule
                              prompt   = constructed from report body

The migration is idempotent — re-running on a workspace with an existing
_recurrences.yaml merges (any slug already present in _recurrences.yaml
is preserved; any not-present slug from a legacy file is appended).

Usage (against the live Supabase instance — be deliberate):

    cd api
    python -m scripts.oneshot.phaseB_unify_recurrences --user-id <UUID>
    python -m scripts.oneshot.phaseB_unify_recurrences --all-users  # CAUTION

The script uses the SUPABASE_SERVICE_KEY env var (via services.supabase.
get_service_client) and writes via authored_substrate.write_revision
with authored_by="system:phaseB-migration" and a descriptive message.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("phaseB_migration")


# Path patterns for the legacy declaration files
_BACK_OFFICE_PATH = "/workspace/_shared/back-office.yaml"


# ---------------------------------------------------------------------------
# Per-shape projection helpers
# ---------------------------------------------------------------------------


def _project_back_office_entry(entry: dict) -> Optional[dict]:
    """Project one back_office_jobs[*] entry to a unified recurrence dict."""
    import yaml  # noqa: F401 — used by callers

    executor = entry.get("executor") or ""
    slug = entry.get("slug") or ""
    if not slug and executor:
        # Fallback: derive slug from dotted executor path
        last = executor.rsplit(".", 1)[-1].replace("_", "-")
        slug = last if "back-office" in last else f"back-office-{last}"
    if not slug:
        return None

    display_name = entry.get("display_name") or slug.replace("-", " ").title()
    schedule = entry.get("schedule")

    # Construct a prompt that asks the Reviewer to perform the work the
    # legacy executor did. Each known executor maps to a known maintenance
    # intent — for unknown executors we emit a generic "perform the
    # maintenance work named {slug}" prompt so nothing silently dies.
    prompt = _maintenance_prompt_for(slug, executor)
    return {
        "slug": slug,
        "schedule": schedule,
        "prompt": prompt,
        "paused": bool(entry.get("paused", False)),
        "display_name": display_name,
    }


def _maintenance_prompt_for(slug: str, executor: str) -> str:
    """Map a legacy back-office slug to a Reviewer-driven prompt."""
    table = {
        "back-office-narrative-digest": (
            "Roll up non-conversation narrative events from the last 24h "
            "(reviewer verdicts, agent runs, system events) into "
            "/workspace/system/recent.md. Group by Identity (reviewer / "
            "agent / external / system) and summarize material entries "
            "first. Feeds the compact index per ADR-159 + ADR-221."
        ),
        "back-office-proposal-cleanup": (
            "Archive action_proposals rows pending review for >7 days "
            "without operator action. Use UpdateContext target='proposal' "
            "to mark them archived (revision log preserves history per "
            "ADR-209). For each archived proposal, append one line to "
            "/workspace/persona/judgment_log.md noting the auto-archive."
        ),
        "back-office-outcome-reconciliation": (
            "Reconcile yesterday's executed proposals against platform "
            "events. Pull executed orders + fills since last reconciliation. "
            "Compute realized P&L per fill and append rolling-window "
            "updates to /workspace/context/{domain}/_money_truth.md per "
            "the schema in /workspace/operation/specs/performance-rollup.md."
        ),
        "back-office-reviewer-calibration": (
            "Calibrate against money-truth. Read "
            "/workspace/operation/trading/_money_truth.md for the last "
            "7d/30d/90d windows. Compare realized expectancy to your "
            "declared edge. If realized P&L diverges materially, append "
            "a calibration concern to /workspace/persona/judgment_log.md."
        ),
        "back-office-freddie-reflection": (
            "Reflect on yesterday's decisions against your principles. "
            "Read /workspace/persona/judgment_log.md (last 7d) and "
            "/workspace/persona/principles.md. If a pattern warrants a "
            "principles adjustment, ProposeAction with full revised file "
            "content. Always append a reflections.md entry."
        ),
        "track-universe": (
            "Refresh fundamentals for tickers in "
            "/workspace/operation/trading/_universe.yaml. For each ticker, "
            "fetch fresh Alpaca bars and compute SMA/RSI/ATR/volume. "
            "Write a current snapshot to "
            "/workspace/operation/trading/{ticker}.yaml."
        ),
        "signal-evaluation": (
            "Evaluate the universe against signals on the latest bars. "
            "When any signal fires, FireInvocation(slug='trade-proposal') "
            "to hand the signal to the Reviewer for capital judgment."
        ),
    }
    if slug in table:
        return table[slug]
    return (
        f"Perform the maintenance work previously named {slug!r} "
        f"(legacy executor: {executor!r}). Reviewer judgment required — "
        "this prompt was auto-projected during the Phase B unification "
        "and may need operator refinement."
    )


def _project_domain_recurring_entry(entry: dict, domain: str) -> Optional[dict]:
    """Project one /workspace/context/{domain}/_recurring.yaml entry."""
    slug = entry.get("slug") or ""
    if not slug:
        return None

    schedule = entry.get("schedule")
    paused = bool(entry.get("paused", False))
    display_name = entry.get("display_name") or slug.replace("-", " ").title()

    # Build the prompt from the legacy fields
    agent = entry.get("agent") or ""
    if not agent:
        agents_list = entry.get("agents") or []
        agent = agents_list[0] if agents_list else "researcher"

    objective = entry.get("objective") or ""
    if isinstance(objective, dict):
        # Common legacy shape: {deliverable, audience, purpose, format}
        purpose = objective.get("purpose") or ""
        objective = purpose

    context_writes = entry.get("context_writes") or [domain]
    context_reads = entry.get("context_reads") or []

    parts = [
        f"Accumulate context for the '{domain}' domain.",
    ]
    if objective:
        parts.append(f"Objective: {objective}")
    if context_reads:
        parts.append(f"Read from: {', '.join(context_reads)}.")
    parts.append(
        f"Write entity files into /workspace/context/{domain}/ "
        f"(per ADR-262 CONVENTIONS topology). Dispatch the {agent} "
        f"specialist via DispatchSpecialist if focused production work "
        f"is needed."
    )
    prompt = "\n".join(parts)

    return {
        "slug": slug,
        "schedule": schedule,
        "prompt": prompt,
        "paused": paused,
        "display_name": display_name,
    }


def _project_action_yaml(body: dict) -> Optional[dict]:
    """Project a /workspace/operation/operations/{slug}/_action.yaml body."""
    slug = body.get("slug") or ""
    if not slug:
        return None

    recurring = body.get("recurring") or {}
    schedule = recurring.get("schedule")
    paused = bool(recurring.get("paused", False))
    display_name = body.get("display_name") or slug.replace("-", " ").title()

    deliverable = body.get("deliverable") or {}
    purpose = deliverable.get("purpose") if isinstance(deliverable, dict) else ""
    audience = deliverable.get("audience") if isinstance(deliverable, dict) else ""
    fmt = deliverable.get("format") if isinstance(deliverable, dict) else ""

    success_criteria = body.get("success_criteria") or []
    emits_proposal = bool(body.get("emits_proposal", False))

    parts = [
        f"Reactive action: {display_name}.",
    ]
    if purpose:
        parts.append(f"Purpose: {purpose}")
    if audience:
        parts.append(f"Audience: {audience}")
    if fmt:
        parts.append(f"Format: {fmt}")
    if success_criteria:
        parts.append("Success criteria:")
        for c in success_criteria:
            parts.append(f"  - {c}")
    if emits_proposal:
        parts.append(
            "Emit a ProposeAction at the end (Reviewer-gated capital "
            "judgment). Stand down with reasoning if conditions don't "
            "warrant."
        )
    prompt = "\n".join(parts)

    return {
        "slug": slug,
        "schedule": schedule,
        "prompt": prompt,
        "paused": paused,
        "display_name": display_name,
    }


def _project_report_yaml(body: dict) -> Optional[dict]:
    """Project a /workspace/operation/reports/{slug}/_spec.yaml body."""
    slug = body.get("slug") or ""
    if not slug:
        return None

    recurring = body.get("recurring") or {}
    schedule = recurring.get("schedule")
    paused = bool(recurring.get("paused", False))
    display_name = body.get("display_name") or slug.replace("-", " ").title()
    output_path = body.get("output_path") or f"/workspace/operation/reports/{slug}/{{date}}/output.md"

    deliverable = body.get("deliverable") or {}
    if not isinstance(deliverable, dict):
        deliverable = {}
    purpose = deliverable.get("purpose") or ""
    audience = deliverable.get("audience") or ""
    fmt = deliverable.get("format") or ""

    success_criteria = body.get("success_criteria") or []
    context_reads = body.get("context_reads") or []

    parts = [
        f"Produce the {display_name} report. Save to {output_path}.",
    ]
    if purpose:
        parts.append(f"Purpose: {purpose}")
    if audience:
        parts.append(f"Audience: {audience}")
    if fmt:
        parts.append(f"Format: {fmt}")
    if context_reads:
        parts.append(f"Read context from: {', '.join(context_reads)}.")
    if success_criteria:
        parts.append("Success criteria:")
        for c in success_criteria:
            parts.append(f"  - {c}")
    parts.append(
        "Compose to HTML automatically when section partials exist "
        "(ADR-262 D4)."
    )
    prompt = "\n".join(parts)

    return {
        "slug": slug,
        "schedule": schedule,
        "prompt": prompt,
        "paused": paused,
        "display_name": display_name,
    }


# ---------------------------------------------------------------------------
# Workspace-walker
# ---------------------------------------------------------------------------


def _tolerant_parse_back_office(content: str) -> list[dict]:
    """Parse a back-office.yaml that may have mixed indentation.

    Strict yaml.safe_load() fails when the operator-edited file has some
    entries at column 0 and others indented under back_office_jobs:. We
    fall back to a regex-based extraction that finds every `- slug: ...`
    block and gathers its sibling key-value pairs.
    """
    import re
    import yaml

    # First try strict parse — the common case
    try:
        parsed = yaml.safe_load(content)
        if isinstance(parsed, dict):
            entries = parsed.get("back_office_jobs") or []
            if isinstance(entries, list):
                return [e for e in entries if isinstance(e, dict)]
        if isinstance(parsed, list):
            return [e for e in parsed if isinstance(e, dict)]
    except yaml.YAMLError as e:
        logger.warning(
            "back-office.yaml strict parse failed (%s); falling back to tolerant extraction",
            str(e).split("\n")[0],
        )

    # Tolerant fallback — find every `- slug:` block via regex and parse
    # each block as standalone YAML. This handles mixed indentation.
    blocks: list[dict] = []
    # Match `- slug: value` (any indent), capture the indent so we know
    # where the entry ends (next entry at same-or-lower indent).
    pattern = re.compile(
        r"^([ \t]*)-\s*slug\s*:\s*(.+?)$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(content))
    for i, m in enumerate(matches):
        indent_len = len(m.group(1))
        slug = m.group(2).strip().strip("\"'")
        block_start = m.end()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[block_start:block_end]
        # Body lines look like `  executor: services.back_office.foo`
        # Strip the common leading indent (entry-content indent = indent_len + 2)
        entry: dict = {"slug": slug}
        body_indent = indent_len + 2
        for line in body.split("\n"):
            stripped = line[body_indent:] if line.startswith(" " * body_indent) else line.strip()
            stripped = stripped.rstrip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" in stripped and not stripped.startswith(" "):
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key and value:
                    if value.lower() in {"true", "false"}:
                        entry[key] = value.lower() == "true"
                    else:
                        entry[key] = value
        if entry.get("slug"):
            blocks.append(entry)

    if blocks:
        logger.info(
            "tolerant extraction recovered %d back-office entries", len(blocks)
        )
    return blocks


def _gather_legacy_entries(client, user_id: str) -> tuple[list[dict], list[str]]:
    """Walk a user's workspace_files for legacy declaration files.

    Returns (projected_entries, legacy_paths) — legacy_paths to delete
    after _recurrences.yaml is written.
    """
    import yaml

    projected: list[dict] = []
    legacy_paths: list[str] = []

    rows = (
        client.table("workspace_files")
        .select("path,content")
        .eq("user_id", user_id)
        .or_(
            "path.eq./workspace/_shared/back-office.yaml,"
            "path.like./workspace/context/%/_recurring.yaml,"
            "path.like./workspace/operation/operations/%/_action.yaml,"
            "path.like./workspace/operation/reports/%/_spec.yaml"
        )
        .execute()
    ).data or []

    for row in rows:
        path = row.get("path") or ""
        content = row.get("content") or ""
        if not path or not content.strip():
            continue

        if path == _BACK_OFFICE_PATH:
            entries = _tolerant_parse_back_office(content)
            for entry in entries:
                rec = _project_back_office_entry(entry)
                if rec:
                    projected.append(rec)
            legacy_paths.append(path)
            continue

        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as e:
            logger.warning("YAML parse failed for %s: %s — skipping", path, e)
            continue
        if not isinstance(parsed, dict):
            continue

        elif path.startswith("/workspace/context/") and path.endswith("/_recurring.yaml"):
            domain = path[len("/workspace/context/"):].split("/")[0]
            entries = parsed.get("recurrences") or []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                rec = _project_domain_recurring_entry(entry, domain)
                if rec:
                    projected.append(rec)
            legacy_paths.append(path)

        elif path.startswith("/workspace/operation/operations/") and path.endswith("/_action.yaml"):
            body = parsed.get("action") if "action" in parsed else parsed
            if isinstance(body, dict):
                rec = _project_action_yaml(body)
                if rec:
                    projected.append(rec)
            legacy_paths.append(path)

        elif path.startswith("/workspace/operation/reports/") and path.endswith("/_spec.yaml"):
            body = parsed.get("report") if "report" in parsed else parsed
            if isinstance(body, dict):
                rec = _project_report_yaml(body)
                if rec:
                    projected.append(rec)
            legacy_paths.append(path)

    return projected, legacy_paths


# ---------------------------------------------------------------------------
# Main migration
# ---------------------------------------------------------------------------


async def migrate_user(client, user_id: str, *, dry_run: bool = False) -> dict:
    """Migrate one user's recurrence substrate. Returns a summary dict."""
    import yaml

    projected, legacy_paths = _gather_legacy_entries(client, user_id)
    logger.info(
        "[%s] gathered %d legacy entries from %d files",
        user_id[:8], len(projected), len(legacy_paths),
    )

    if not projected:
        return {
            "user_id": user_id,
            "projected": 0,
            "legacy_files": 0,
            "merged": 0,
            "skipped": True,
            "reason": "no legacy declarations",
        }

    # Read existing _recurrences.yaml (idempotency)
    existing_rows = (
        client.table("workspace_files")
        .select("content")
        .eq("user_id", user_id)
        .eq("path", "/workspace/_recurrences.yaml")
        .limit(1)
        .execute()
    ).data or []

    existing_entries: list[dict] = []
    if existing_rows:
        existing_content = existing_rows[0].get("content") or ""
        try:
            parsed = yaml.safe_load(existing_content)
            if isinstance(parsed, list):
                existing_entries = parsed
            elif isinstance(parsed, dict):
                existing_entries = parsed.get("recurrences") or []
        except yaml.YAMLError:
            existing_entries = []

    # Idempotent merge: keep existing entries; append projected ones whose slug
    # isn't already present.
    existing_slugs = {e.get("slug") for e in existing_entries if isinstance(e, dict)}
    new_entries = [r for r in projected if r["slug"] not in existing_slugs]
    merged = list(existing_entries) + new_entries

    # Serialize to canonical _recurrences.yaml shape (top-level list).
    yaml_text = yaml.safe_dump(
        merged,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=80,
    )

    if dry_run:
        logger.info(
            "[%s] DRY RUN — would write %d entries (%d new) to "
            "/workspace/_recurrences.yaml; would delete %d legacy files",
            user_id[:8], len(merged), len(new_entries), len(legacy_paths),
        )
        return {
            "user_id": user_id,
            "projected": len(projected),
            "legacy_files": len(legacy_paths),
            "merged": len(new_entries),
            "dry_run": True,
        }

    from services.authored_substrate import write_revision

    # 1. Write the merged _recurrences.yaml
    write_revision(
        client,
        user_id=user_id,
        path="/workspace/_recurrences.yaml",
        content=yaml_text,
        authored_by="system:phaseB-migration",
        message=(
            f"Phase B unification: project {len(projected)} legacy "
            f"declarations into canonical _recurrences.yaml "
            f"(merged {len(new_entries)} new entries with "
            f"{len(existing_entries)} existing)"
        ),
    )

    # 2. Delete legacy declaration files. workspace_files.delete is the
    # ADR-209-compliant deletion path for content removal (see
    # authored_substrate.py docstring lines 27-31).
    for path in legacy_paths:
        try:
            client.table("workspace_files").delete().eq(
                "user_id", user_id
            ).eq("path", path).execute()
            logger.info("[%s] deleted legacy file %s", user_id[:8], path)
        except Exception as e:
            logger.warning("[%s] delete failed for %s: %s", user_id[:8], path, e)

    return {
        "user_id": user_id,
        "projected": len(projected),
        "legacy_files": len(legacy_paths),
        "merged": len(new_entries),
        "dry_run": False,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", help="Migrate one user (UUID)")
    parser.add_argument("--all-users", action="store_true",
                        help="Migrate every user with at least one legacy file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute projection but don't write")
    args = parser.parse_args()

    if not args.user_id and not args.all_users:
        parser.error("provide either --user-id or --all-users")

    # Lazy import — keeps module loadable for inspection without env
    from services.supabase import get_service_client
    client = get_service_client()

    user_ids: list[str] = []
    if args.user_id:
        user_ids = [args.user_id]
    else:
        # Find all users with at least one legacy file
        rows = (
            client.table("workspace_files")
            .select("user_id")
            .or_(
                "path.eq./workspace/_shared/back-office.yaml,"
                "path.like./workspace/context/%/_recurring.yaml,"
                "path.like./workspace/operation/operations/%/_action.yaml,"
                "path.like./workspace/operation/reports/%/_spec.yaml"
            )
            .execute()
        ).data or []
        user_ids = sorted({r["user_id"] for r in rows})
        logger.info("Found %d users with legacy declarations", len(user_ids))

    summaries = []
    for uid in user_ids:
        try:
            summary = await migrate_user(client, uid, dry_run=args.dry_run)
            summaries.append(summary)
        except Exception as e:
            logger.exception("[%s] migration FAILED: %s", uid[:8], e)
            summaries.append({"user_id": uid, "error": str(e)})

    print()
    print("=" * 60)
    print("Migration summary")
    print("=" * 60)
    for s in summaries:
        print(s)


if __name__ == "__main__":
    asyncio.run(main())
