"""
Workspace Initialization — ADR-152 + ADR-188 + ADR-189 + ADR-190: Workspace Bootstrap

Sets up a workspace from the three registries (ADR-188: template libraries).
Called once at signup. After initialization, the workspace is self-contained —
registries are templates that were applied, the workspace filesystem is the
sole source of truth.

Phases:
  1. Directory structure (from WORKSPACE_DIRECTORIES)
  2. Agent roster (from AGENT_TEMPLATES + DEFAULT_ROSTER) — infrastructure rows
     (YARNNN, Specialists, Platform Bots); user-authored Agents filter by
     origin='system_bootstrap' per ADR-189
  3. Workspace files (IDENTITY.md, BRAND.md, AWARENESS.md, CONVENTIONS.md as
     empty/minimal skeletons — ADR-190 strips pre-committed filler)
  4. Essential tasks (daily-update heartbeat + back office tasks)
  5. Signup balance audit trail (ADR-172)

After init, YARNNN customizes the workspace based on the user's work description
(ADR-188 + ADR-190):
  - Scaffolds domain-specific context directories on demand (ADR-188 Phase 2:
    `_domain.md`)
  - Creates custom tasks with domain-specific step instructions (ADR-188 Phase 1)
  - Rich first-act input triggers `UpdateContext(target="workspace")` which
    runs combined inference + writes IDENTITY/BRAND + scaffolds entity
    subfolders + proposes work intent (ADR-190)

ADR-190 deletions:
  - WORKSPACE.md manifest (was vestigial post-ADR-159 compact index)
  - DEFAULT_BRAND_MD filler (BRAND.md now empty skeleton; inference populates)
  - update_workspace_manifest() helper (no longer called from ManageTask etc.)

The registries are NEVER consulted at runtime — only at creation time.

Version: 2.0 (2026-04-17, ADR-190)
"""

import logging
from datetime import datetime, timezone
from typing import Any

from services.schedule_utils import calculate_next_run_at, get_user_timezone

logger = logging.getLogger(__name__)


async def initialize_workspace(client: Any, user_id: str, browser_tz: str | None = None) -> dict:
    """Initialize a complete workspace for a new user.

    Idempotent — checks for existing workspace before creating.
    Called from onboarding-state endpoint on first login.

    Args:
        browser_tz: IANA timezone string inferred from the browser (X-Timezone header).
                    Written into IDENTITY.md during Phase 3 so the daily-update task
                    fires at 09:00 local time on first run — no explicit user prompt needed.

    Returns dict with initialization summary.
    """
    result = {
        "agents_created": [],
        "directories_scaffolded": [],
        "workspace_files_seeded": [],
        "tasks_created": [],
        "already_initialized": False,
    }

    # Check if already initialized. ADR-190: WORKSPACE.md manifest deleted;
    # idempotency now gated on IDENTITY.md presence (always scaffolded at
    # Phase 3). Per-phase idempotency guards the rest.
    from services.workspace import UserMemory
    um = UserMemory(client, user_id)
    existing_identity = await um.read("IDENTITY.md")
    if existing_identity:
        result["already_initialized"] = True
        # Still run idempotent steps in case of partial init
        logger.info(f"[WORKSPACE_INIT] Workspace already initialized for {user_id[:8]}")

    # =========================================================================
    # Phase 1: Directory Structure (from WORKSPACE_DIRECTORIES)
    # =========================================================================
    try:
        from services.directory_registry import scaffold_all_directories
        scaffolded = await scaffold_all_directories(client, user_id)
        result["directories_scaffolded"] = scaffolded
        if scaffolded:
            logger.info(f"[WORKSPACE_INIT] Directories: {', '.join(scaffolded)}")
    except Exception as e:
        logger.warning(f"[WORKSPACE_INIT] Directory scaffold failed: {e}")

    # =========================================================================
    # Phase 2: Agent Roster (from AGENT_TYPES + DEFAULT_ROSTER)
    # =========================================================================
    try:
        from services.agent_framework import AGENT_TYPES, DEFAULT_ROSTER
        from services.agent_creation import create_agent_record

        for agent_def in DEFAULT_ROSTER:
            try:
                type_def = AGENT_TYPES.get(agent_def["role"], {})
                await create_agent_record(
                    client=client,
                    user_id=user_id,
                    title=agent_def["title"],
                    role=agent_def["role"],
                    origin="system_bootstrap",
                    agent_instructions=type_def.get("default_instructions", ""),
                )
                result["agents_created"].append(agent_def["title"])
                logger.info(f"[WORKSPACE_INIT] Agent: {agent_def['title']}")
            except Exception as e:
                logger.warning(f"[WORKSPACE_INIT] Agent {agent_def['title']} failed (may exist): {e}")
    except Exception as e:
        logger.error(f"[WORKSPACE_INIT] Agent roster FAILED — no agents created: {e}")

    # =========================================================================
    # Phase 3: Workspace Files (identity, brand, playbook, preferences)
    # =========================================================================
    try:
        from services.agent_framework import (
            TP_ORCHESTRATION_PLAYBOOK,
            DEFAULT_IDENTITY_MD,
            DEFAULT_BRAND_MD,
            DEFAULT_AWARENESS_MD,
            DEFAULT_CONVENTIONS_MD,
            DEFAULT_REVIEW_IDENTITY_MD,
            DEFAULT_REVIEW_PRINCIPLES_MD,
        )

        # Inject browser timezone so get_user_timezone() in Phase 5 resolves
        # correctly without asking the user.
        # _parse_memory_md reads plain "key: value" lines (not bold markdown),
        # so we write a separate plain-format IDENTITY.md when a timezone is
        # known, and fall back to the display template otherwise.
        identity_content = DEFAULT_IDENTITY_MD
        if browser_tz:
            from services.platform_limits import normalize_timezone_name
            from services.workspace import UserMemory
            validated_tz = normalize_timezone_name(browser_tz)
            if validated_tz and validated_tz != "UTC":
                identity_content = UserMemory._render_memory_md({"timezone": validated_tz})
                logger.info(f"[WORKSPACE_INIT] Timezone inferred from browser: {validated_tz}")

        workspace_files = {
            "IDENTITY.md": (identity_content, "User identity template"),
            "BRAND.md": (DEFAULT_BRAND_MD, "Default brand baseline"),
            "AWARENESS.md": (DEFAULT_AWARENESS_MD, "TP situational awareness"),
            "_playbook.md": (TP_ORCHESTRATION_PLAYBOOK, "TP orchestration playbook"),
            "style.md": ("# Style\n<!-- System-inferred from edit patterns. -->\n", "Style placeholder"),
            "notes.md": ("# Notes\n<!-- TP-extracted facts and instructions. -->\n", "Notes placeholder"),
            # ADR-174 Phase 1: workspace structural conventions — agent-readable, TP-extensible
            "CONVENTIONS.md": (DEFAULT_CONVENTIONS_MD, "Workspace filesystem conventions"),
            # ADR-194 v2 Phase 1: Reviewer substrate (fourth cognitive layer).
            # Lands at /workspace/review/. decisions.md is NOT scaffolded —
            # created on first Reviewer write in Phase 2+.
            "review/IDENTITY.md": (DEFAULT_REVIEW_IDENTITY_MD, "Reviewer identity"),
            "review/principles.md": (DEFAULT_REVIEW_PRINCIPLES_MD, "Reviewer declared framework (user-editable)"),
        }

        for filename, (content, summary) in workspace_files.items():
            existing = await um.read(filename)
            if not existing:
                await um.write(filename, content, summary=f"Workspace init: {summary}")
                result["workspace_files_seeded"].append(filename)
                logger.info(f"[WORKSPACE_INIT] File: {filename}")
    except Exception as e:
        logger.warning(f"[WORKSPACE_INIT] Workspace files failed: {e}")

    # =========================================================================
    # Phase 4 (was WORKSPACE.md manifest) DELETED per ADR-190. The manifest
    # was vestigial — ADR-159 compact index replaced it as the session-start
    # meta-awareness source. YARNNN queries DB for current state via working
    # memory; no static file needed. Phase numbering below preserved as 5/6
    # for commit diff readability.
    # =========================================================================

    # =========================================================================
    # Phase 5: Default Tasks — the heartbeat anchor (ADR-161)
    # =========================================================================
    user_timezone = get_user_timezone(client, user_id)

    # Every workspace gets exactly one default task: daily-update.
    # It is essential — cannot be deleted or auto-paused. It is the user-facing
    # manifestation of the system being alive, and runs daily at 09:00 local time.
    # Empty workspaces produce a deterministic "honest empty" template (zero
    # LLM cost). Populated workspaces produce a real operational digest.
    # ── Daily update (user-facing heartbeat, ADR-161) ──
    try:
        existing_task = (
            client.table("tasks")
            .select("id")
            .eq("user_id", user_id)
            .eq("slug", "daily-update")
            .execute()
        )
        if not (existing_task.data or []):
            await _create_essential_daily_update(client, user_id, user_timezone)
            result["tasks_created"].append("daily-update")
            logger.info(f"[WORKSPACE_INIT] Default task: daily-update (essential)")
        else:
            logger.info(f"[WORKSPACE_INIT] daily-update task already exists, skipping")
    except Exception as e:
        logger.error(f"[WORKSPACE_INIT] Default task (daily-update) FAILED — user has no heartbeat: {e}")

    # ── Back office tasks (ADR-164) ──
    # Scheduled maintenance owned by TP. Same substrate as user tasks; runs
    # through the same pipeline via the TP dispatch branch in execute_task().
    # Essential — users can pause but not archive.
    for type_key, slug, title in [
        ("back-office-agent-hygiene", "back-office-agent-hygiene", "Agent Hygiene"),
        ("back-office-workspace-cleanup", "back-office-workspace-cleanup", "Workspace Cleanup"),
        # ADR-193 Phase 5: sweep expired action_proposals
        ("back-office-proposal-cleanup", "back-office-proposal-cleanup", "Proposal Cleanup"),
        # ADR-195 Phase 2: reconcile platform events into action_outcomes
        ("back-office-outcome-reconciliation", "back-office-outcome-reconciliation", "Outcome Reconciliation"),
    ]:
        try:
            existing = (
                client.table("tasks")
                .select("id")
                .eq("user_id", user_id)
                .eq("slug", slug)
                .execute()
            )
            if not (existing.data or []):
                await _create_essential_back_office_task(
                    client,
                    user_id,
                    type_key,
                    slug,
                    title,
                    user_timezone,
                )
                result["tasks_created"].append(slug)
                logger.info(f"[WORKSPACE_INIT] Default task: {slug} (essential, TP-owned)")
            else:
                logger.info(f"[WORKSPACE_INIT] {slug} already exists, skipping")
        except Exception as e:
            logger.warning(f"[WORKSPACE_INIT] Back office task ({slug}) creation failed: {e}")

    # =========================================================================
    # Phase 6: Signup balance audit trail (ADR-172)
    # =========================================================================
    # The $3 signup balance is granted by schema DEFAULT on workspaces
    # (migration 144: balance_usd=3.0, free_balance_granted=true).
    # The trigger in migration 106 auto-creates the workspace row on
    # auth.users INSERT, so the balance exists before this code runs.
    #
    # This phase records the audit trail in balance_transactions.
    # Idempotent: only writes if no signup_grant row exists yet.
    if not result["already_initialized"]:
        try:
            ws_row = client.table("workspaces")\
                .select("id")\
                .eq("owner_id", user_id)\
                .limit(1)\
                .execute()
            if ws_row.data:
                workspace_id = ws_row.data[0]["id"]
                # Check if audit row already exists (idempotent)
                existing_tx = client.table("balance_transactions")\
                    .select("id")\
                    .eq("workspace_id", workspace_id)\
                    .eq("kind", "signup_grant")\
                    .limit(1)\
                    .execute()
                if not (existing_tx.data or []):
                    client.table("balance_transactions").insert({
                        "workspace_id": workspace_id,
                        "kind": "signup_grant",
                        "amount_usd": 3.0,
                        "metadata": {"note": "schema_default_grant_audit_trail"},
                    }).execute()
                    logger.info(f"[WORKSPACE_INIT] Signup balance audit: $3.00 for {user_id[:8]}")
            else:
                logger.error(f"[WORKSPACE_INIT] No workspace row for {user_id[:8]} — balance may be missing")
        except Exception as e:
            logger.warning(f"[WORKSPACE_INIT] Signup balance audit failed: {e}")

    # =========================================================================
    # Post-init validation — check critical invariants
    # =========================================================================
    problems = []
    if len(result["agents_created"]) == 0 and not result["already_initialized"]:
        problems.append("zero agents created")
    if "IDENTITY.md" not in result["workspace_files_seeded"] and not result["already_initialized"]:
        problems.append("IDENTITY.md not seeded")
    if "daily-update" not in result["tasks_created"] and not result["already_initialized"]:
        # Check if it existed already (idempotent case is fine)
        try:
            check = client.table("tasks").select("id").eq("user_id", user_id).eq("slug", "daily-update").execute()
            if not (check.data or []):
                problems.append("daily-update task missing")
        except Exception:
            problems.append("daily-update task check failed")

    if problems:
        logger.error(
            f"[WORKSPACE_INIT] INCOMPLETE for {user_id[:8]}: {', '.join(problems)}. "
            f"Created: {len(result['agents_created'])} agents, "
            f"{len(result['workspace_files_seeded'])} files, "
            f"{len(result['tasks_created'])} tasks"
        )
    else:
        logger.info(
            f"[WORKSPACE_INIT] Complete for {user_id[:8]}: "
            f"{len(result['agents_created'])} agents, "
            f"{len(result['directories_scaffolded'])} directories, "
            f"{len(result['workspace_files_seeded'])} files, "
            f"{len(result['tasks_created'])} tasks"
        )

    return result


async def _create_essential_daily_update(
    client: Any,
    user_id: str,
    user_timezone: str,
) -> None:
    """Create the essential daily-update task at workspace initialization.

    ADR-161: This is the heartbeat artifact. Every workspace gets one.
    The task runs at 09:00 in the user's local timezone. Empty workspaces produce a
    deterministic template; populated workspaces produce a real digest.

    The `essential=true` flag prevents archive and (future) auto-pause.
    Users can manually pause via ManageTask if they explicitly opt out.
    """
    from services.task_workspace import TaskWorkspace
    from services.task_types import build_task_md_from_type

    now = datetime.now(timezone.utc)
    next_run = calculate_next_run_at("daily", last_run_at=now, user_timezone=user_timezone)

    row = {
        "user_id": user_id,
        "slug": "daily-update",
        "mode": "recurring",
        "status": "active",
        "schedule": "daily",
        "next_run_at": next_run.isoformat() if next_run else now.isoformat(),
        "essential": True,
    }
    insert_result = client.table("tasks").insert(row).execute()
    if not insert_result.data:
        raise RuntimeError("Failed to insert daily-update task")

    # Write TASK.md so the pipeline has a charter to read
    task_md = build_task_md_from_type(
        type_key="daily-update",
        title="Daily Update",
        slug="daily-update",
        schedule="daily",
        delivery="email",
        agent_slugs=["reporting"],
    )
    tw = TaskWorkspace(client, user_id, "daily-update")
    await tw.write("TASK.md", task_md, summary="Essential task definition: Daily Update")

    # ADR-149: Scaffold DELIVERABLE.md from type registry
    from services.task_types import build_deliverable_md_from_type
    deliverable_md = build_deliverable_md_from_type("daily-update")
    if deliverable_md:
        await tw.write("DELIVERABLE.md", deliverable_md, summary="Quality contract: Daily Update")


async def _create_essential_back_office_task(
    client: Any,
    user_id: str,
    type_key: str,
    slug: str,
    title: str,
    user_timezone: str,
) -> None:
    """Create an essential back office task owned by TP (ADR-164).

    Back office tasks execute via the TP dispatch branch in the task pipeline.
    They scaffold with `essential=true` so users can't accidentally archive
    them. Same substrate as user tasks, executed through the same pipeline,
    producing the same output artifacts.
    """
    from services.task_workspace import TaskWorkspace
    from services.task_types import build_task_md_from_type

    now = datetime.now(timezone.utc)
    # Same local morning cadence as daily-update.
    next_run = calculate_next_run_at("daily", last_run_at=now, user_timezone=user_timezone)

    row = {
        "user_id": user_id,
        "slug": slug,
        "mode": "recurring",
        "status": "active",
        "schedule": "daily",
        "next_run_at": next_run.isoformat() if next_run else now.isoformat(),
        "essential": True,
    }
    insert_result = client.table("tasks").insert(row).execute()
    if not insert_result.data:
        raise RuntimeError(f"Failed to insert back office task: {slug}")

    # Write TASK.md. agent_slugs=["thinking-partner"] matches the slug that
    # get_agent_slug() derives from the "Thinking Partner" title.
    task_md = build_task_md_from_type(
        type_key=type_key,
        title=title,
        slug=slug,
        schedule="daily",
        delivery="none",  # Back office tasks don't deliver externally
        agent_slugs=["thinking-partner"],
    )
    tw = TaskWorkspace(client, user_id, slug)
    await tw.write("TASK.md", task_md, summary=f"Essential task definition: {title}")

    # ADR-149: Scaffold DELIVERABLE.md from type registry
    from services.task_types import build_deliverable_md_from_type
    deliverable_md = build_deliverable_md_from_type(type_key)
    if deliverable_md:
        await tw.write("DELIVERABLE.md", deliverable_md, summary=f"Quality contract: {title}")


# ADR-190: `update_workspace_manifest()` and `_build_workspace_manifest()`
# DELETED. The WORKSPACE.md manifest they wrote was vestigial — ADR-159
# compact index replaced it as the session-start meta-awareness source.
# YARNNN queries current workspace state from the DB via `build_working_memory`
# (agents, tasks, context domains); no static manifest file needed.
