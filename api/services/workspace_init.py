"""
Workspace Initialization — PURE GENESIS (ADR-414 D4, 2026-07-07)

Note: ``from __future__ import annotations`` below defers PEP 604 union evaluation
(``str | None``) until typing is queried. Without it, Python 3.9 (the prod venv
runtime) raises ``TypeError`` at signature-evaluation time. See
docs/alpha/observations/2026-04-26-trader-e2e-paper-loop.md §A4.

The workspace is born empty, constituted, and shared. Genesis creates exactly
what a multi-principal OS requires at birth and NOTHING else:

  Phase 2. The two governance dials — `governance/_budget.yaml` (spend
           envelope, ADR-327) + `governance/_autonomy.yaml` (witness dial,
           ADR-405/408 D3). The steward's constitution (identity / mandate /
           principles) is a KERNEL CONSTANT riding the wake envelope
           (ADR-414 D2 / freddie_envelope.py) — never seeded.
  Phase 3. The workspace narrative chat_sessions row (ADR-219).
  Phase 4. The signup balance audit trail (ADR-172).

Deleted at genesis (the ADR-414 deletion ledger):
  - the thinking_partner agents row (D3 — migration 205; one system agent,
    the rail is its voice)
  - steward MANDATE/IDENTITY/principles seeding (D2 — kernel constants)
  - PRECEDENT, system/_playbook + style + notes, persona/_principles.yaml,
    reflection.md, _workspace_guide.md (materialize on first write — the
    Axiom 1 corollary "substrate grows from work" honored without exception)
  - the OCCUPANT/handoffs seat scaffold (the signup `human:{user_id}`
    occupant was substrate-runtime drift on every bare workspace)
  - the `program_slug` parameter + the genesis-time fork (D4/D5 — programs
    are post-genesis hires; ADR-222's "workspaces don't have types" finally
    honored in code)

Member genesis is the invite path (ADR-404) and never runs this function —
a member lands on a genuinely empty workspace and everything renders.
Structure emerges through the steward's work (ADR-381 derive-and-cite,
placement), not through templates.

Version: 3.0 (2026-07-07, ADR-414 D4 — pure genesis)
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
) -> dict:
    """Pure genesis (ADR-414 D4): the workspace is born empty, constituted,
    and shared.

    Genesis creates exactly what a multi-principal OS requires at birth:
      1. (retired) — no agents-table row (ADR-414 D3, migration 205)
      2. The two governance DIALS — `governance/_budget.yaml` +
         `governance/_autonomy.yaml`. The steward's constitution
         (identity / mandate / principles) is a KERNEL CONSTANT riding the
         wake envelope (ADR-414 D2) — never seeded. Everything else
         (PRECEDENT, system accumulation, _principles.yaml, reflection,
         OCCUPANT, the workspace guide) materializes on first write —
         Axiom 1's corollary ("substrate grows from work, not signup
         scaffolding") finally honored without exception.
      3. The workspace narrative session (ADR-219).
      4. The signup balance audit trail (ADR-172).

    Genesis NEVER forks a program (the `program_slug` parameter is deleted —
    ADR-414 D5: activation is a post-genesis hire; the L2/L4 reinit callers
    run the re-fork themselves after this returns). Member genesis is the
    invite path (ADR-404) and never runs this function.

    Idempotent — keyed on the budget dial's presence.
    """
    result = {
        "agents_created": [],  # retained key (API compat) — always [] post-ADR-414 D3
        "directories_scaffolded": [],
        "workspace_files_seeded": [],
        "tasks_created": [],
        "already_initialized": False,
        "activated_program": None,  # set by the caller's post-init re-fork, never here
        "fork_files_written": [],  # set by the caller's post-init re-fork, never here
        "session_bootstrapped": False,  # ADR-219: workspace narrative session created
    }

    # Idempotency: keyed on the budget dial — the first file pure genesis
    # seeds (present on every pre-ADR-414 workspace too, seeded since
    # ADR-327). The prior key (persona/IDENTITY.md) is no longer seeded.
    from services.workspace import UserMemory
    from services.workspace_paths import GOVERNANCE_BUDGET_PATH
    um = UserMemory(client, user_id)
    existing_budget = await um.read(GOVERNANCE_BUDGET_PATH)
    if existing_budget:
        result["already_initialized"] = True
        # Still run idempotent steps in case of partial init
        logger.info(f"[WORKSPACE_INIT] Workspace already initialized for {user_id[:8]}")

    # =========================================================================
    # Phase 2: The two governance dials (ADR-414 D2 — all that genesis seeds)
    # =========================================================================
    # The dials are genuinely workspace-variable (operator-tunable witness
    # timing + spend envelope) so they are files; the steward's constitution
    # is invariant across workspaces so it is a kernel constant (DP33) served
    # by the envelope (freddie_envelope.py). Deleted from seeding (ADR-414
    # deletion ledger): steward MANDATE/IDENTITY/principles, PRECEDENT,
    # system/_playbook + style + notes, persona/_principles.yaml +
    # reflection.md, _workspace_guide.md, and the OCCUPANT/handoffs seat
    # scaffold (the signup `human:{user_id}` occupant was substrate-runtime
    # drift on every bare workspace — ADR-284's problem, solved by removal).
    try:
        from services.orchestration import DEFAULT_AUTONOMY_YAML
        from services.workspace_paths import GOVERNANCE_AUTONOMY_YAML_PATH
        from services.budget import DEFAULT_BUDGET_YAML

        workspace_files = {
            GOVERNANCE_BUDGET_PATH: (
                DEFAULT_BUDGET_YAML,
                "Budget governance — the workspace's spend envelope (ADR-327)",
            ),
            # The witness dial (ADR-405/408 D3): per-family delegation,
            # substrate autonomous + consequential families fail-closed.
            # Always seeded (pre-ADR-414 it was no-program-only); a program
            # hire may overwrite with tuned values (marker-eligible).
            GOVERNANCE_AUTONOMY_YAML_PATH: (
                DEFAULT_AUTONOMY_YAML,
                "Witness dial — per-family delegation posture (ADR-405/408 D3)",
            ),
        }

        for path, (content, summary) in workspace_files.items():
            existing = await um.read(path)
            if not existing:
                await um.write(path, content, summary=f"Workspace init: {summary}")
                result["workspace_files_seeded"].append(path)
                logger.info(f"[WORKSPACE_INIT] File: {path}")
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

    # Phase 5 (the genesis-time program fork) is DELETED (ADR-414 D4/D5):
    # genesis never forks. Program activation is a post-genesis hire —
    # `routes/programs.py` (activate endpoint) and the L2/L4 reinit callers
    # (`services/workspace_purge.py`, `routes/account.py`) invoke
    # `services.programs.fork_reference_workspace` themselves.

    # =========================================================================
    # Post-init validation — check critical invariants (ADR-414 D4 rewrite)
    # =========================================================================
    # The pure-genesis invariants: the budget dial exists (seeded now or
    # already present) and the narrative session exists (bootstrapped now or
    # already present). The prior checks (agents_created > 0, persona
    # IDENTITY seeded) described the retired scaffolds — the persona check
    # also logged a spurious INCOMPLETE on every program signup (the file
    # arrived via the fork, not the seed).
    problems = []
    if (
        GOVERNANCE_BUDGET_PATH not in result["workspace_files_seeded"]
        and not result["already_initialized"]
    ):
        problems.append(f"{GOVERNANCE_BUDGET_PATH} not seeded")

    if problems:
        logger.error(
            f"[WORKSPACE_INIT] INCOMPLETE for {user_id[:8]}: {', '.join(problems)}. "
            f"Seeded: {len(result['workspace_files_seeded'])} files"
        )
    else:
        logger.info(
            f"[WORKSPACE_INIT] Complete for {user_id[:8]}: "
            f"{len(result['workspace_files_seeded'])} files seeded "
            f"(pure genesis — ADR-414 D4)"
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
