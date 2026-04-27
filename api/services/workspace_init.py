"""
Workspace Initialization — ADR-152 + ADR-188 + ADR-189 + ADR-190 + ADR-205 + ADR-206 + ADR-226: Workspace Bootstrap

Note: ``from __future__ import annotations`` below defers PEP 604 union evaluation
(``str | None``) until typing is queried. Without it, Python 3.9 (the prod venv
runtime) raises ``TypeError: unsupported operand type(s) for |: 'type' and
'NoneType'`` at signature-evaluation time the first time an annotated function
is referenced. Surfaced by the alpha-trader E2E proposal-cleanup materialization
path; see docs/alpha/observations/2026-04-26-trader-e2e-paper-loop.md §A4.

Sets up a workspace from the three registries (ADR-188: template libraries).
Called once at signup. After initialization, the workspace is self-contained —
registries are templates that were applied, the workspace filesystem is the
sole source of truth.

ADR-205 + ADR-212: Two systemic Agents are scaffolded at signup — YARNNN
(meta-cognitive Agent) and the Reviewer seat (at /workspace/review/).
Production roles (orchestration capability bundles — Researcher, Analyst,
Writer, Tracker, Designer, Reporting) are lazy-created on first dispatch
as agents-table rows for pipeline dispatch; they are NOT Agents in the
sharp sense. Platform integrations are connection-bound capability bundles,
not Agents. Substrate grows from work.

ADR-206: Further collapse — zero operational tasks at signup. `daily-update`
and `back-office-*` are no longer scaffolded; they materialize on trigger
conditions (proposals created, platform connected, agent threshold, etc.).
IDENTITY/BRAND/CONVENTIONS relocated under `/workspace/context/_shared/`;
YARNNN working-memory files relocated under `/workspace/memory/`.
The workspace is textually present + structurally empty.

Phases:
  1. YARNNN agent row (role=thinking_partner, origin=system_bootstrap)
     — sole infrastructure row at signup per ADR-205
  2. Authored shared context skeletons under `/workspace/context/_shared/`
     (IDENTITY, BRAND, CONVENTIONS) + YARNNN memory skeletons under
     `/workspace/memory/` + Reviewer substrate under `/workspace/review/`
  3. Signup balance audit trail (ADR-172)

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

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from services.schedule_utils import calculate_next_run_at, get_user_timezone

logger = logging.getLogger(__name__)


async def initialize_workspace(
    client: Any,
    user_id: str,
    browser_tz: str | None = None,
    program_slug: str | None = None,
) -> dict:
    """Initialize a complete workspace for a new user.

    Idempotent — checks for existing workspace before creating.
    Called from onboarding-state endpoint on first login.

    Args:
        browser_tz: IANA timezone string inferred from the browser (X-Timezone header).
                    Written into IDENTITY.md during Phase 3 so the daily-update task
                    fires at 09:00 local time on first run — no explicit user prompt needed.
        program_slug: Optional program selection (ADR-226). When provided, the
                    bundle's `reference-workspace/` is forked into the operator's
                    `/workspace/` honoring three-tier file categorization
                    (canon/authored/placeholder per ADR-223 §5). When None, the
                    workspace is generic per ADR-205/206 — no bundle chrome,
                    no program-shaped substrate.

    Returns dict with initialization summary.
    """
    result = {
        "agents_created": [],
        "directories_scaffolded": [],
        "workspace_files_seeded": [],
        "tasks_created": [],
        "already_initialized": False,
        "activated_program": None,  # ADR-226: bundle slug forked, or None
        "fork_files_written": [],  # ADR-226: paths written during the fork phase
    }

    # Check if already initialized. ADR-206: idempotency gated on presence
    # of /workspace/context/_shared/IDENTITY.md (always scaffolded in Phase 2).
    from services.workspace import UserMemory
    from services.workspace_paths import SHARED_IDENTITY_PATH
    um = UserMemory(client, user_id)
    existing_identity = await um.read(SHARED_IDENTITY_PATH)
    if existing_identity:
        result["already_initialized"] = True
        # Still run idempotent steps in case of partial init
        logger.info(f"[WORKSPACE_INIT] Workspace already initialized for {user_id[:8]}")

    # =========================================================================
    # Phase 1: Directory Structure — DELETED (ADR-205)
    # =========================================================================
    # ADR-205: Substrate grows from work. Context domain directories (incl.
    # signals) materialize on first agent write via UserMemory (virtual
    # filesystem — a write to a path creates the containing directory
    # implicitly). Signup no longer pre-creates anything under /workspace/context/.
    # Platform-bound domains (customers/revenue, trading/portfolio, slack/notion/github)
    # are still scaffolded at OAuth connect via scaffold_context_domain() — that's
    # connection-bound, not signup-bound, and matches ADR-158/183/187 platform
    # ownership semantics.
    result["directories_scaffolded"] = []

    # =========================================================================
    # Phase 2: YARNNN — sole infrastructure agent scaffolded at signup (ADR-205)
    # =========================================================================
    # Specialists + Platform Bots are lazy-created. YARNNN is scaffolded here
    # because it owns back-office tasks (ADR-164) which run on the workspace
    # heartbeat from day one. Idempotent — skips if already present.
    try:
        from services.orchestration import ALL_ROLES
        from services.agent_creation import create_agent_record

        yarnnn_existing = (
            client.table("agents")
            .select("id")
            .eq("user_id", user_id)
            .eq("role", "thinking_partner")
            .eq("origin", "system_bootstrap")
            .limit(1)
            .execute()
        )
        if not (yarnnn_existing.data or []):
            yarnnn_template = ALL_ROLES.get("thinking_partner", {})
            await create_agent_record(
                client=client,
                user_id=user_id,
                title=yarnnn_template.get("display_name", "Thinking Partner"),
                role="thinking_partner",
                origin="system_bootstrap",
                agent_instructions=yarnnn_template.get("default_instructions", ""),
            )
            result["agents_created"].append("Thinking Partner")
            logger.info(f"[WORKSPACE_INIT] Agent: YARNNN (thinking_partner) — sole signup scaffold (ADR-205)")
        else:
            logger.info(f"[WORKSPACE_INIT] YARNNN already exists, skipping")
    except Exception as e:
        logger.error(f"[WORKSPACE_INIT] YARNNN scaffold FAILED — workspace has no heartbeat: {e}")

    # =========================================================================
    # Phase 2: Workspace skeletons (ADR-206 relocations)
    # =========================================================================
    # Shared authored context under /workspace/context/_shared/,
    # YARNNN working memory under /workspace/memory/,
    # Reviewer substrate under /workspace/review/ (ADR-194).
    try:
        from services.orchestration import (
            TP_ORCHESTRATION_PLAYBOOK,
            DEFAULT_IDENTITY_MD,
            DEFAULT_BRAND_MD,
            DEFAULT_AWARENESS_MD,
            DEFAULT_CONVENTIONS_MD,
            DEFAULT_PRECEDENT_MD,
            DEFAULT_REVIEW_IDENTITY_MD,
            DEFAULT_REVIEW_PRINCIPLES_MD,
            # DEFAULT_REVIEW_OCCUPANT_MD + DEFAULT_REVIEW_HANDOFFS_MD deleted
            # per ADR-211 D4 singular-implementation — rotate_occupant() is
            # the single write path for both files (see below).
            # DEFAULT_REVIEW_MODES_MD deleted per ADR-217 — autonomy moved to
            # workspace-scoped AUTONOMY.md under /workspace/context/_shared/.
            DEFAULT_AUTONOMY_MD,
            DEFAULT_REVIEW_CALIBRATION_MD,
        )
        from services.workspace_paths import (
            SHARED_MANDATE_PATH, SHARED_IDENTITY_PATH, SHARED_BRAND_PATH,
            SHARED_CONVENTIONS_PATH, SHARED_AUTONOMY_PATH,
            SHARED_PRECEDENT_PATH,
            MEMORY_AWARENESS_PATH, MEMORY_PLAYBOOK_PATH,
            MEMORY_STYLE_PATH, MEMORY_NOTES_PATH,
            REVIEW_IDENTITY_PATH, REVIEW_PRINCIPLES_PATH,
            REVIEW_OCCUPANT_PATH,
            REVIEW_HANDOFFS_PATH, REVIEW_CALIBRATION_PATH,
        )

        identity_content = DEFAULT_IDENTITY_MD
        if browser_tz:
            from services.platform_limits import normalize_timezone_name
            from services.workspace import UserMemory
            validated_tz = normalize_timezone_name(browser_tz)
            if validated_tz and validated_tz != "UTC":
                identity_content = UserMemory._render_memory_md({"timezone": validated_tz})
                logger.info(f"[WORKSPACE_INIT] Timezone inferred from browser: {validated_tz}")

        # ADR-207 D2: empty Mandate skeleton. Operator authors via
        # UpdateContext(target="mandate") in first-turn elicitation.
        # Hard gate in ManageTask._handle_create blocks task scaffolding
        # until Mandate is non-empty.
        DEFAULT_MANDATE_MD = (
            "# Mandate\n\n"
            "<!-- This file declares what this workspace is running.\n"
            "     Authored via YARNNN conversation at first use; revised when\n"
            "     the operator decides. No forced revision cadence. -->\n\n"
            "## Primary Action\n"
            "_<not yet declared — talk to YARNNN to author your mandate>_\n\n"
            "## Success Criteria\n\n"
            "## Boundary Conditions\n"
        )

        # Static workspace files (not occupancy-dependent). OCCUPANT.md and
        # handoffs.md are seeded via the rotation primitive below — single
        # write path per ADR-211 D4 (rotation is a substrate write).
        workspace_files = {
            # Authored shared context (operator-scoped declarations + precedent).
            SHARED_MANDATE_PATH: (DEFAULT_MANDATE_MD, "Mandate skeleton — workspace north star"),
            SHARED_IDENTITY_PATH: (identity_content, "User identity template"),
            SHARED_BRAND_PATH: (DEFAULT_BRAND_MD, "Default brand baseline"),
            SHARED_CONVENTIONS_PATH: (DEFAULT_CONVENTIONS_MD, "Workspace filesystem conventions"),
            SHARED_AUTONOMY_PATH: (DEFAULT_AUTONOMY_MD, "Autonomy delegation — default manual, operator-authored (ADR-217)"),
            SHARED_PRECEDENT_PATH: (DEFAULT_PRECEDENT_MD, "Precedent substrate — durable boundary-case guidance"),
            # YARNNN working memory (ADR-206)
            MEMORY_AWARENESS_PATH: (DEFAULT_AWARENESS_MD, "YARNNN situational awareness"),
            MEMORY_PLAYBOOK_PATH: (TP_ORCHESTRATION_PLAYBOOK, "YARNNN orchestration playbook"),
            MEMORY_STYLE_PATH: ("# Style\n<!-- System-inferred from edit patterns. -->\n", "Style placeholder"),
            MEMORY_NOTES_PATH: ("# Notes\n<!-- YARNNN-extracted facts and instructions. -->\n", "Notes placeholder"),
            # Reviewer substrate Phase 1-3 (ADR-194 v2) — static at signup
            REVIEW_IDENTITY_PATH: (DEFAULT_REVIEW_IDENTITY_MD, "Reviewer seat identity (role-level, static)"),
            REVIEW_PRINCIPLES_PATH: (DEFAULT_REVIEW_PRINCIPLES_MD, "Reviewer declared framework (user-editable)"),
            # Reviewer substrate Phase 4 (ADR-211) minus modes.md (ADR-217 moved autonomy to _shared/):
            # OCCUPANT.md + handoffs.md are seeded below via the rotation primitive.
            REVIEW_CALIBRATION_PATH: (DEFAULT_REVIEW_CALIBRATION_MD, "Reviewer seat calibration trail (auto-generated by back-office task)"),
        }

        for path, (content, summary) in workspace_files.items():
            existing = await um.read(path)
            if not existing:
                await um.write(path, content, summary=f"Workspace init: {summary}")
                result["workspace_files_seeded"].append(path)
                logger.info(f"[WORKSPACE_INIT] File: {path}")

        # Reviewer seat signup-scaffold: single write path through the
        # rotation primitive (ADR-211 D4). Seeds both OCCUPANT.md and
        # handoffs.md atomically. Idempotent — rotate_occupant() short-
        # circuits if the seat is already filled by the target occupant.
        try:
            from services.review_rotation import rotate_occupant, read_current_occupant
            current = await read_current_occupant(um)
            if not current["occupant"]:
                rotation = await rotate_occupant(
                    um,
                    f"human:{user_id}",
                    authorized_by="system",
                    trigger="signup",
                    reason="Workspace scaffold — operator is default Reviewer seat occupant",
                )
                if rotation["rotated"]:
                    result["workspace_files_seeded"].append(REVIEW_OCCUPANT_PATH)
                    result["workspace_files_seeded"].append(REVIEW_HANDOFFS_PATH)
                    logger.info(
                        f"[WORKSPACE_INIT] Reviewer seat scaffolded: "
                        f"occupant=human:{user_id[:8]} (ADR-211 D4)"
                    )
        except Exception as exc:
            logger.warning(f"[WORKSPACE_INIT] Reviewer seat scaffold failed: {exc}")
    except Exception as e:
        logger.warning(f"[WORKSPACE_INIT] Workspace files failed: {e}")

    # =========================================================================
    # Operational tasks — NOT scaffolded at signup (ADR-206)
    # =========================================================================
    # ADR-206: the workspace is textually present, structurally empty. No
    # daily-update, no back-office tasks, no maintain-overview at signup.
    # Back-office tasks materialize on trigger (first proposal, platform
    # connect, agent threshold). daily-update is opt-in offered by YARNNN
    # once the operator's declared operation is running.

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
    # Phase 7: Reference-workspace fork (ADR-226) — optional, program-bound
    # =========================================================================
    # When the operator selected a program at signup (or activates one later),
    # this phase forks the bundle's reference-workspace/ into /workspace/
    # honoring three-tier file categorization (ADR-223 §5):
    #   - canon: program-shipped opinion, copied verbatim
    #   - authored: templates with prompts; operator MUST overwrite via YARNNN
    #   - placeholder: empty/skeleton, accumulates from work over time
    # Frontmatter (tier:, prompt:, note:, optional:) is bundle-only — stripped
    # before the file is written to operator's /workspace/.
    # Idempotent: re-running re-applies canon, preserves operator-authored.
    if program_slug:
        try:
            fork_summary = await _fork_reference_workspace(
                client, user_id, program_slug
            )
            result["activated_program"] = program_slug
            result["fork_files_written"] = fork_summary.get("files_written", [])
            logger.info(
                f"[WORKSPACE_INIT] Reference fork complete for {user_id[:8]}: "
                f"program={program_slug}, files={len(result['fork_files_written'])}"
            )
        except Exception as exc:
            logger.error(
                f"[WORKSPACE_INIT] Reference fork FAILED for {user_id[:8]} "
                f"(program={program_slug}): {exc}"
            )
            result["fork_error"] = str(exc)

    # =========================================================================
    # Post-init validation — check critical invariants
    # =========================================================================
    from services.workspace_paths import SHARED_IDENTITY_PATH
    problems = []
    if len(result["agents_created"]) == 0 and not result["already_initialized"]:
        problems.append("zero agents created")
    if SHARED_IDENTITY_PATH not in result["workspace_files_seeded"] and not result["already_initialized"]:
        problems.append(f"{SHARED_IDENTITY_PATH} not seeded")
    # ADR-206: daily-update is no longer an essential signup task — removed from validation.

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


async def materialize_back_office_task(
    client: Any,
    user_id: str,
    type_key: str,
    slug: str,
    title: str,
    user_timezone: str | None = None,
) -> None:
    """Materialize a back-office task on trigger (ADR-206).

    ADR-206: back-office tasks are no longer scaffolded at signup. This helper
    is called by trigger-site hooks (first proposal created, platform connected,
    agent-threshold probe) to materialize the task at the moment it becomes
    meaningful. Idempotent — no-op if the task already exists for this user.

    Tasks created here are `essential=true` so they can't be accidentally
    archived; they are still plumbing the workspace needs.
    """
    from services.task_workspace import TaskWorkspace
    from services.task_types import build_task_md_from_type, build_deliverable_md_from_type
    from services.schedule_utils import get_user_timezone as _get_user_timezone

    if user_timezone is None:
        user_timezone = _get_user_timezone(client, user_id)

    # Idempotency
    existing = (
        client.table("tasks")
        .select("id")
        .eq("user_id", user_id)
        .eq("slug", slug)
        .execute()
    )
    if existing.data:
        return

    now = datetime.now(timezone.utc)
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
        raise RuntimeError(f"Failed to materialize back office task: {slug}")

    task_md = build_task_md_from_type(
        type_key=type_key,
        title=title,
        slug=slug,
        schedule="daily",
        delivery="none",
        agent_slugs=["thinking-partner"],
    )
    tw = TaskWorkspace(client, user_id, slug)
    await tw.write("TASK.md", task_md, summary=f"Materialized back-office task: {title}")

    deliverable_md = build_deliverable_md_from_type(type_key)
    if deliverable_md:
        await tw.write("DELIVERABLE.md", deliverable_md, summary=f"Quality contract: {title}")

    logger.info(f"[MATERIALIZE] Back-office task created on trigger: {slug} for {user_id[:8]}")


# ADR-190: `update_workspace_manifest()` and `_build_workspace_manifest()`
# DELETED. The WORKSPACE.md manifest they wrote was vestigial — ADR-159
# compact index replaced it as the session-start meta-awareness source.
# YARNNN queries current workspace state from the DB via `build_working_memory`
# (agents, tasks, context domains); no static manifest file needed.


# =============================================================================
# ADR-226: Reference-workspace fork (Phase 7)
# =============================================================================


def _strip_tier_frontmatter(text: str) -> tuple[str, dict[str, Any]]:
    """Parse YAML frontmatter (if present) from a reference-workspace file
    and return (body, metadata).

    Per ADR-223 §5 amendment + ADR-226 §4: tier metadata
    (tier:, prompt:, note:, optional:) is bundle-only — must be stripped
    before the file is written to operator's /workspace/. Operator's
    workspace files are clean markdown.

    Returns:
        body: the markdown content with frontmatter removed
        metadata: parsed frontmatter as dict ({} if absent)

    The parser is intentionally minimal — handles the documented
    bundle frontmatter shape (`---\\n<keys>\\n---\\n`). Doesn't attempt
    full YAML 1.2 parsing; the bundle author writes simple key:value
    pairs per the schema.
    """
    if not text.startswith("---\n"):
        return text, {}
    end_marker = text.find("\n---\n", 4)
    if end_marker < 0:
        # Malformed frontmatter — return as-is to avoid data loss
        return text, {}
    fm_text = text[4:end_marker]
    body = text[end_marker + 5 :]  # skip the closing '\n---\n'
    metadata: dict[str, Any] = {}
    try:
        import yaml as _yaml
        parsed = _yaml.safe_load(fm_text)
        if isinstance(parsed, dict):
            metadata = parsed
    except Exception:
        # If YAML parsing fails, treat as no metadata; body is still stripped
        pass
    # Strip leading newline from body if present (artifact of '---\n' close)
    if body.startswith("\n"):
        body = body[1:]
    return body, metadata


def _is_skeleton_content(operator_content: str, bundle_body: str) -> bool:
    """Determine whether the operator's current file content is still
    skeleton (matches the bundle's body, the kernel-default skeleton,
    or browser-timezone-inflated kernel default) vs operator-authored.

    Used by re-fork idempotency per ADR-226 §4: re-running fork preserves
    operator-authored content; only re-applies the bundle if the operator
    hasn't filled it in.

    Detection patterns:
      - Empty / whitespace-only → skeleton.
      - Exact match to bundle body → skeleton (operator hasn't deviated).
      - Contains kernel-default placeholder phrases ("not yet declared",
        "not yet provided", "<!-- ... not yet ... -->") → skeleton.
      - Very short content (< 200 chars after strip) AND lacks operator-
        authored signal markers → skeleton. This catches kernel-default
        IDENTITY.md after browser-timezone inflation
        ("# About Me\\n\\ntimezone: Asia/Seoul\\n") — short, no operator
        signal, gets overwritten by the bundle's IDENTITY template.

    Operator-authored signal markers: any prose section beyond a single
    H1 + simple metadata. The "very short content" rule fires only when
    the file has NO sections beyond H1 and is genuinely sparse.
    """
    if not operator_content or not operator_content.strip():
        return True
    op_normalized = operator_content.strip()
    bundle_normalized = bundle_body.strip()
    if op_normalized == bundle_normalized:
        return True

    op_lower = op_normalized.lower()

    # Kernel-default placeholder phrases — workspace_init Phase 2 writes
    # these before fork runs. Treat as skeleton so bundle template wins.
    placeholder_phrases = (
        "not yet declared",
        "not yet provided",
        "<!-- identity not yet",
        "<!-- brand not yet",
        "<!-- mandate not yet",
        "<!-- awareness",  # YARNNN awareness placeholder
    )
    if any(phrase in op_lower for phrase in placeholder_phrases) and len(op_normalized) < 800:
        return True

    # Kernel-default Reviewer principles signature — Phase 2 writes a
    # generic framework that's longer than typical skeletons but still
    # represents pre-activation state. Bundle's program-specific principles
    # template should win at activation time.
    kernel_principles_signature = "this is the declared review framework for this workspace"
    if kernel_principles_signature in op_lower:
        return True

    # Very-short-and-sparse rule: kernel defaults inflated by Phase 2
    # (e.g. browser_tz appended to IDENTITY) are short and have no
    # H2 section — operator hasn't authored anything substantive yet.
    # Bundle templates always have H2 sections (## Status, ## Steps, etc.)
    if len(op_normalized) < 200:
        # Count H2 sections (## ...). Operator-authored content typically
        # has at least one H2 even when sparse.
        h2_count = sum(1 for line in op_normalized.split("\n") if line.startswith("## "))
        if h2_count == 0:
            return True

    return False


def _bundle_root_dir(program_slug: str):
    """Resolve docs/programs/{slug}/reference-workspace/ relative to this
    file. Singular implementation: same root logic as bundle_reader uses
    for MANIFEST.yaml; kept consistent across services."""
    from pathlib import Path
    return (
        Path(__file__).resolve().parent.parent.parent
        / "docs"
        / "programs"
        / program_slug
        / "reference-workspace"
    )


async def _fork_reference_workspace(
    client: Any, user_id: str, program_slug: str
) -> dict[str, Any]:
    """Per ADR-226: copy bundle's reference-workspace/ into operator's
    /workspace/, honoring ADR-223 §5 three-tier categorization.

    Each file written goes through services.workspace.UserMemory.write
    (which routes through services.authored_substrate.write_revision
    per ADR-209) with authored_by="system:bundle-fork" and a message
    identifying the source bundle + tier.

    Idempotency:
      - canon tier: re-applied on re-run. Operator edits are preserved
        as prior revisions in the chain (ADR-209).
      - authored tier: only re-applied if operator's file is still
        skeleton. Operator-authored content is preserved.
      - placeholder tier: only written on first fork (no overwrite).

    Returns a summary dict with:
      - files_written: list of paths the fork touched
      - files_skipped: list of paths skipped (operator already authored
        the authored-tier file, or placeholder already exists)
    """
    from services.workspace import UserMemory

    bundle_root = _bundle_root_dir(program_slug)
    if not bundle_root.is_dir():
        raise ValueError(
            f"Bundle reference-workspace not found: {bundle_root}. "
            f"Bundle '{program_slug}' may not exist or may not have a "
            f"reference-workspace/ directory."
        )

    # Validate the bundle's MANIFEST allows activation per ADR-226 §2.
    # Fail closed on bundles that aren't activatable (status not in
    # active|deferred). The UI should not allow non-activatable selection
    # but if it slips through we reject.
    from services.bundle_reader import _load_manifest
    manifest = _load_manifest(program_slug)
    if not manifest:
        raise ValueError(f"Bundle '{program_slug}' has no MANIFEST.yaml.")
    if manifest.get("status") not in ("active", "deferred"):
        raise ValueError(
            f"Bundle '{program_slug}' has status='{manifest.get('status')}'; "
            f"only active or deferred bundles can be forked."
        )

    um = UserMemory(client, user_id)
    files_written: list[str] = []
    files_skipped: list[str] = []

    # Walk bundle's reference-workspace/ recursively, skipping the
    # bundle-meta README.md (it's documentation about the bundle, not
    # a workspace file the operator inherits).
    for src_path in sorted(bundle_root.rglob("*.md")):
        if src_path.name == "README.md" and src_path.parent == bundle_root:
            continue

        # Relative path from reference-workspace root → workspace path.
        # UserMemory expects paths relative to /workspace/ (no leading slash).
        relative = src_path.relative_to(bundle_root).as_posix()
        target_path = relative  # e.g., "context/_shared/MANDATE.md"

        try:
            raw = src_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning(f"[FORK] Failed to read {src_path}: {exc}")
            continue

        body, metadata = _strip_tier_frontmatter(raw)
        tier = (metadata.get("tier") or "placeholder").lower()
        if tier not in ("canon", "authored", "placeholder"):
            logger.warning(
                f"[FORK] Unknown tier '{tier}' for {src_path}; "
                f"defaulting to placeholder"
            )
            tier = "placeholder"

        # Idempotency check: read operator's current content, decide whether
        # to write based on tier rules.
        existing = await um.read(target_path)
        should_write = False
        if existing is None:
            # First-fork case — always write
            should_write = True
        elif tier == "canon":
            # Re-fork case for canon: re-apply (operator edits preserved
            # as prior revisions per ADR-209).
            # Skip if content already matches to avoid no-op revisions.
            should_write = existing.strip() != body.strip()
        elif tier == "authored":
            # Re-fork case for authored: only re-apply if operator hasn't
            # authored real content yet AND current content differs from
            # the bundle body (avoid no-op rewrites that pollute the
            # revision chain).
            should_write = (
                _is_skeleton_content(existing, body)
                and existing.strip() != body.strip()
            )
        elif tier == "placeholder":
            # Re-fork case for placeholder: never overwrite. Substrate
            # accumulates from work; activation does not touch placeholders
            # after first fork.
            should_write = False

        if should_write:
            await um.write(
                target_path,
                body,
                summary=f"Forked from {program_slug} bundle (tier={tier})",
                authored_by="system:bundle-fork",
                message=(
                    f"ADR-226: forked {src_path.name} from "
                    f"docs/programs/{program_slug}/reference-workspace/ "
                    f"(tier={tier})"
                ),
            )
            files_written.append(target_path)
            logger.info(
                f"[FORK] {target_path} (tier={tier}) "
                f"← {program_slug}/reference-workspace/{relative}"
            )
        else:
            files_skipped.append(target_path)
            logger.info(
                f"[FORK] {target_path} (tier={tier}) — skipped "
                f"(operator-authored or no-op)"
            )

    return {
        "files_written": files_written,
        "files_skipped": files_skipped,
        "program_slug": program_slug,
    }
