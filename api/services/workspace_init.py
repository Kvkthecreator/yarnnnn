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
(meta-cognitive Agent) and the Reviewer seat (at /workspace/persona/).
Production roles (orchestration capability bundles — Researcher, Analyst,
Writer, Tracker, Designer, Reporting) are lazy-created on first dispatch
as agents-table rows for pipeline dispatch; they are NOT Agents in the
sharp sense. Platform integrations are connection-bound capability bundles,
not Agents. Substrate grows from work.

ADR-206: Further collapse — zero operational tasks at signup. `daily-update`
and `back-office-*` are no longer scaffolded; they materialize on trigger
conditions (proposals created, platform connected, agent threshold, etc.).
IDENTITY/BRAND/CONVENTIONS relocated under `constitution/ + governance/ + operation/ (ADR-320 split of legacy _shared/)`;
YARNNN working-memory files relocated under `/workspace/system/`.
The workspace is textually present + structurally empty.

Phases:
  1. YARNNN agent row (role=thinking_partner, origin=system_bootstrap)
  2. Kernel-seeded workspace skeleton files:
       Shared context: MANDATE, IDENTITY, BRAND, AUTONOMY, PRECEDENT
       YARNNN memory: awareness, _playbook, style, notes
       Reviewer substrate: IDENTITY, principles, OCCUPANT, handoffs, reflection
       (CONVENTIONS.md NOT seeded — program-scoped, bundles fork it)
  3. Workspace narrative chat_sessions row (ADR-219)
  4. Signup balance audit trail (ADR-172)
  5. Reference-workspace fork (ADR-226, optional, program-bound)
     — delegates to services.programs.fork_reference_workspace

After init, YARNNN customizes the workspace based on the user's work description
(ADR-188 + ADR-190):
  - Scaffolds domain-specific context directories on demand (ADR-188 Phase 2:
    `_domain.md`)
  - Creates custom tasks with domain-specific step instructions (ADR-188 Phase 1)
  - Identity/brand inference from rich input flows through `InferContext`
    (ADR-235 D1.a). The combined first-act-scaffold primitive `InferWorkspace`
    was removed per ADR-314 D4 (dissolved by Direction A — for a program
    workspace, the bundle fork drafts the constitution; there is no
    conversational `/init`).

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
    program_slug: str | None = None,
) -> dict:
    """Initialize a complete workspace for a new user.

    Idempotent — checks for existing workspace before creating.
    Called from `GET /api/workspace/state` on first login (lazy roster
    scaffolding). Also called from `routes/account.py` L2/L4 reinit paths
    after purge, optionally with `program_slug` per ADR-244 D4 to re-fork
    a previously-active bundle.

    Args:
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
        "session_bootstrapped": False,  # ADR-219: workspace narrative session created
    }

    # Check if already initialized. ADR-206: idempotency gated on presence
    # of /workspace/persona/IDENTITY.md (always scaffolded in Phase 2).
    from services.workspace import UserMemory
    from services.workspace_paths import PERSONA_IDENTITY_PATH
    um = UserMemory(client, user_id)
    existing_identity = await um.read(PERSONA_IDENTITY_PATH)
    if existing_identity:
        result["already_initialized"] = True
        # Still run idempotent steps in case of partial init
        logger.info(f"[WORKSPACE_INIT] Workspace already initialized for {user_id[:8]}")

    # =========================================================================
    # Phase 1: YARNNN agent row — sole infrastructure agent at signup (ADR-205)
    # =========================================================================
    # Specialists + Platform Bots are lazy-created. YARNNN is scaffolded here
    # because it is the persistent system identity that owns back-office tasks.
    # ADR-205: no pre-created directories — substrate grows from work.
    result["directories_scaffolded"] = []
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
    # Phase 2: Workspace skeleton files (ADR-206)
    # =========================================================================
    # Kernel-seeded files (not program-scoped):
    #   Authored shared context: MANDATE, IDENTITY, BRAND, AUTONOMY, PRECEDENT
    #   YARNNN working memory: awareness, _playbook, style, notes
    #   Reviewer substrate: IDENTITY, principles, OCCUPANT, handoffs, reflection
    # CONVENTIONS.md is NOT seeded here — program-scoped (bundles fork it).
    # See docs/architecture/workspace-init.md for the full canonical reference.
    try:
        # ADR-286 import set: kernel-universal defaults only. Bundle-owned
        # content (MANDATE, IDENTITY, BRAND, AUTONOMY, etc.) is written by
        # `fork_reference_workspace` in Phase 5 — never imported here.
        from services.orchestration import (
            TP_ORCHESTRATION_PLAYBOOK,
            DEFAULT_PRECEDENT_MD,
            DEFAULT_REVIEW_REFLECTION_MD,  # ADR-364: supersedes DEFAULT_REVIEW_CALIBRATION_MD
            DEFAULT_WORKSPACE_GUIDE_MD,  # kernel-default for no-program workspaces only (ADR-286 D2)
        )
        from services.workspace_paths import (
            CONSTITUTION_PRECEDENT_PATH,
            GOVERNANCE_BUDGET_PATH,  # ADR-327 spend-envelope governance file
            SYSTEM_PLAYBOOK_PATH,
            SYSTEM_STYLE_PATH, SYSTEM_NOTES_PATH,
            PERSONA_PRINCIPLES_YAML_PATH,  # machine-parsed thresholds — kernel default empty; bundle overrides
            PERSONA_OCCUPANT_PATH,
            PERSONA_HANDOFFS_PATH, PERSONA_REFLECTION_PATH,  # ADR-364
        )
        from services.budget import DEFAULT_BUDGET_YAML

        # ADR-286 (2026-05-17): Single-Writer Per Path. Kernel scaffolds ONLY
        # kernel-universal paths — paths that no bundle ships, present in every
        # workspace regardless of program activation. Bundle-owned paths
        # (MANDATE, IDENTITY, BRAND, AUTONOMY, _autonomy.yaml, awareness.md,
        # review/IDENTITY, review/principles, persona/_principles.yaml, etc.)
        # are written exclusively by `fork_reference_workspace` in Phase 5.
        # No-program workspaces have absent bundle-owned paths; the Reviewer
        # envelope renders empty-state hints (honest semantic — a no-program
        # workspace IS unconfigured). See ADR-286 D1 + D2.
        #
        # The legacy `bundle_owned_paths` skip mechanism (ADR-269 iter-4) is
        # dissolved — no kernel write to skip. The `is_skeleton_content`
        # kernel-default rescue patches in workspace_utils.py are dissolved
        # for the same reason (per ADR-286 D6).
        #
        # `identity_content` (with optional timezone normalization above) is
        # no longer written here — alpha-trader bundle ships its own IDENTITY.md.
        # When the operator declares their personal identity, it lives in
        # `persona/IDENTITY.md` either through bundle-default + edits
        # or future explicit personal-identity path (deferred). For no-program
        # workspaces, IDENTITY.md is absent and the operator authors via chat.
        workspace_files = {
            # Kernel-universal paths only (no bundle ships these):
            CONSTITUTION_PRECEDENT_PATH: (DEFAULT_PRECEDENT_MD, "Precedent substrate — durable boundary-case guidance"),
            SYSTEM_PLAYBOOK_PATH: (TP_ORCHESTRATION_PLAYBOOK, "YARNNN orchestration playbook"),
            SYSTEM_STYLE_PATH: ("# Style\n<!-- System-inferred from edit patterns. -->\n", "Style placeholder"),
            SYSTEM_NOTES_PATH: ("# Notes\n<!-- YARNNN-extracted facts and instructions. -->\n", "Notes placeholder"),
            PERSONA_PRINCIPLES_YAML_PATH: (
                "# _principles.yaml — machine-parsed review thresholds (ADR-254)\n"
                "# Read by review_policy.load_principles() via yaml.safe_load.\n"
                "# For the Reviewer's full reasoning framework, see principles.md.\n\n"
                "# Uncomment and set when you have a domain with outcome tracking:\n"
                "# trading:\n"
                "#   high_impact_threshold_cents: 50000  # $500 routes outcome to task feedback.md\n"
                "#   auto_approve_below_cents: 0         # set to enable AI auto-action\n",
                "Reviewer machine-parsed thresholds — kernel-universal default (overridden by bundle on activation)"
            ),
            PERSONA_REFLECTION_PATH: (DEFAULT_REVIEW_REFLECTION_MD, "Reviewer seat reflection — interpreted learning from the closed intent→outcome loop (Reviewer-authored, ADR-364)"),
            # ADR-327: the operation's spend envelope (one dollar budget over a
            # timeframe). Operator-only-authored; the Reviewer reads but cannot
            # raise its own ceiling. Kernel-universal — every workspace needs
            # cost governance regardless of program activation. Bundles MAY
            # override with program-tuned defaults via Phase 5 fork (alpha-trader
            # ships its own version). Collapses the retired _pace.yaml +
            # _token_budget.yaml.
            GOVERNANCE_BUDGET_PATH: (
                DEFAULT_BUDGET_YAML,
                "Budget governance — the operation's spend envelope (ADR-327)",
            ),
        }

        # `_workspace_guide.md` is dual-classifiable per ADR-286 D2: kernel-
        # universal for no-program workspaces (the kernel default explains
        # the workspace shape); bundle-owned for program-activated workspaces
        # (bundles ship richer program-shaped guides). Special-case here:
        # kernel scaffold writes the default ONLY when no program is
        # activating at signup. Bundle-fork in Phase 5 writes the bundle
        # version for program-activated workspaces.
        if not program_slug:
            workspace_files["_workspace_guide.md"] = (
                DEFAULT_WORKSPACE_GUIDE_MD,
                "Workspace guide — kernel default for no-program workspaces (ADR-286 D2)",
            )

        # Note: PERSONA_PRINCIPLES_YAML_PATH is in the kernel-universal set
        # above for backward compatibility — the alpha-trader bundle ALSO
        # ships persona/_principles.yaml with `auto_approve_below_cents` etc.
        # populated. The bundle's version overrides via Phase 5 fork. For
        # no-program workspaces, the kernel default empty-template stays.
        # If a future bundle audit confirms _principles.yaml should always
        # be bundle-owned, move it to the bundle-owned set per ADR-286 D3.

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
                    result["workspace_files_seeded"].append(PERSONA_OCCUPANT_PATH)
                    result["workspace_files_seeded"].append(PERSONA_HANDOFFS_PATH)
                    logger.info(
                        f"[WORKSPACE_INIT] Reviewer seat scaffolded: "
                        f"occupant=human:{user_id[:8]} (ADR-211 D4)"
                    )
        except Exception as exc:
            logger.warning(f"[WORKSPACE_INIT] Reviewer seat scaffold failed: {exc}")
    except Exception as e:
        logger.warning(f"[WORKSPACE_INIT] Workspace files failed: {e}")

    # =========================================================================
    # Phase 3: Workspace narrative session (ADR-219)
    # =========================================================================
    # Per FOUNDATIONS Axiom 9 + ADR-219, every invocation in the workspace
    # emits one narrative entry into a chat-shaped log. The autonomous
    # writers (task pipeline `write_narrative_entry`, reviewer verdicts,
    # back-office digests, MCP foreign-LLM entries) all resolve their
    # target via `find_active_workspace_session(client, user_id)` —
    # which returns None if no chat_sessions row exists yet.
    #
    # Pre-2026-04-28 the chat session was lazy-created when the operator
    # first opened /chat (`routes.feed.get_or_create_session`). That left
    # a coverage gap: workspaces where the operator's first action was
    # connecting a platform or running a task — autonomous writers had
    # nowhere to surface, and prior task-run narrative was permanently
    # lost (narrative is per-invocation, not historically reconstructable).
    # Surfaced by seulkim88@gmail.com production audit 2026-04-28.
    #
    # Singular implementation: workspace_init is now the sole creator of
    # the workspace's first chat_sessions row. `routes.feed.get_or_create_session`
    # remains the path for subsequent rotations (4h-inactivity windows
    # per ADR-067 / ADR-159) — it finds the bootstrapped row on first
    # invocation rather than creating one.
    #
    # Idempotent: skips when an active thinking_partner session (no
    # agent_id, no task_slug — workspace-scope) already exists.
    try:
        existing_session = (
            client.table("chat_sessions")
            .select("id")
            .eq("user_id", user_id)
            .eq("session_type", "thinking_partner")
            .eq("status", "active")
            .is_("agent_id", "null")
            .is_("task_slug", "null")
            .limit(1)
            .execute()
        )
        if not (existing_session.data or []):
            session_row = (
                client.table("chat_sessions")
                .insert({
                    "user_id": user_id,
                    "session_type": "thinking_partner",
                    "status": "active",
                })
                .execute()
            )
            if session_row.data:
                result["session_bootstrapped"] = True
                logger.info(
                    f"[WORKSPACE_INIT] Workspace narrative session created for "
                    f"{user_id[:8]} (id={session_row.data[0]['id'][:8]}) — ADR-219 coverage"
                )
            else:
                logger.error(
                    f"[WORKSPACE_INIT] Session bootstrap returned no row for "
                    f"{user_id[:8]} — autonomous narrative writes will silently no-op"
                )
        else:
            logger.info(
                f"[WORKSPACE_INIT] Workspace narrative session already exists "
                f"for {user_id[:8]}, skipping"
            )
    except Exception as e:
        # Best-effort: workspace init proceeds even if session bootstrap
        # fails. The next /chat open will lazy-create via the existing
        # routes.feed.get_or_create_session path. Log loud so the gap
        # is visible in production logs.
        logger.error(
            f"[WORKSPACE_INIT] Session bootstrap FAILED for {user_id[:8]}: {e} "
            f"— narrative coverage may be degraded until /chat is opened"
        )

    # No operational tasks at signup (ADR-206 + ADR-261 D6): daily-update +
    # back-office work are bundle-seeded entries in
    # /workspace/_recurrences.yaml when the operator activates a program;
    # operators without a bundle author them via Schedule(action='create', ...).

    # =========================================================================
    # Phase 4: Signup balance audit trail (ADR-172)
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
    # Phase 5: Reference-workspace fork (ADR-226) — optional, program-bound
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
            from services.programs import fork_reference_workspace
            fork_summary = await fork_reference_workspace(
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
    # NOTE (ADR-280 revised 2026-05-15): Phase 6 genesis-by-Reviewer wake
    # was deleted in the same commit chain. The workspace guide is now
    # bundle-shipped substrate, not Reviewer-authored at first wake:
    #   - Kernel-default _workspace_guide.md is seeded in Phase 2 above
    #     (DEFAULT_WORKSPACE_GUIDE_MD constant).
    #   - Bundle-shipped guides at docs/programs/{slug}/reference-workspace/
    #     _workspace_guide.md are forked by services.programs.fork_reference_workspace
    #     in Phase 5 above (overrides the kernel default for program workspaces).
    # The Reviewer reads the resulting guide at every wake (including first
    # wake) like any other operator-canon file. No genesis machinery needed.
    from services.workspace_paths import PERSONA_IDENTITY_PATH
    problems = []
    if len(result["agents_created"]) == 0 and not result["already_initialized"]:
        problems.append("zero agents created")
    if PERSONA_IDENTITY_PATH not in result["workspace_files_seeded"] and not result["already_initialized"]:
        problems.append(f"{PERSONA_IDENTITY_PATH} not seeded")
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


# materialize_back_office_task DELETED (ADR-261 D6 §4, Phase B.5). Lazy
# back-office task materialization is gone; back-office work lives as
# bundle-seeded entries in /workspace/_recurrences.yaml.


# =============================================================================
# Fork helper location reference
# =============================================================================
# fork_reference_workspace lives in services.programs.
# is_skeleton_content lives in services.workspace_utils.
# _strip_tier_frontmatter DELETED (ADR-261 D6 + ADR-262 D6, Phase D.2):
#   the three-tier frontmatter system dissolved; bundle files are
#   markdown the operator owns; ADR-209 attribution captures
#   bundle-fork vs operator-edit distinction.
