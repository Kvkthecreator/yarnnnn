"""
Continuous Substrate Re-Apply — ADR-292.

Closes the gap between docs/ canon and live operator workspaces. When kernel
skeleton constants improve (e.g., tightened safety language in
`DEFAULT_REVIEW_PRINCIPLES_MD`) or bundle templates evolve in
`docs/programs/{slug}/reference-workspace/`, this service propagates the
updates to all live workspaces — gated by the existing operator-authorship
detection so customized files are never touched.

Mechanism (intentionally thin — Singular Implementation discipline):

  1. **Bundle layer**: call existing `programs.fork_reference_workspace(...)`.
     Already idempotent + uses `is_skeleton_content` to skip operator-
     customized files. Zero new logic — re-running the existing fork IS
     the bundle re-apply.

  2. **Kernel layer**: walk the kernel-universal seed paths from
     `workspace_init.py` Phase 2, compare current workspace content
     against current kernel default content. If the workspace copy is
     still skeleton-shaped (per `is_skeleton_content`), re-apply the
     current kernel default. Otherwise, skip.

  3. **Audit log**: append one structured entry per run to
     `/workspace/_shared/substrate-reapply-log.md` via `write_revision()`
     with `authored_by="system:substrate-reapply"` per ADR-209.

Dispatch surfaces:
  - **Mechanical primitive**: registered as `ReapplyPlatformSubstrate` in
    `services/primitives/registry.py::HANDLERS`. Invoked by mechanical-mode
    recurrence `back-office-substrate-reapply` via
    `@primitive: ReapplyPlatformSubstrate()` directive (ADR-263 D5 + ADR-264).
  - **Manual one-shot**: `api/scripts/alpha_ops/reapply_persona.py` for
    operators to force a re-apply without waiting for the daily cycle.

What this does NOT do (explicit non-goals per ADR-292 D4):
  - No bundle versioning, no schema columns, no drift-findings table.
  - No operator accept/reject affordance.
  - No prompt version pinning.
  - No canary rollout.

These remain out of scope until a concrete production failure makes them
acute.

Canonical references:
  - docs/adr/ADR-292-continuous-substrate-reapply.md
  - docs/architecture/propagation-discipline.md
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Audit log path
# ---------------------------------------------------------------------------
REAPPLY_AUDIT_LOG_PATH = "_shared/substrate-reapply-log.md"

# ADR-292 attribution actor — kept distinct from `system:bundle-fork` (which is
# the one-shot activation actor) and `system:reapply` was the original ADR-292
# spec. Final landed name: `system:substrate-reapply` — names the recurrence
# slug + the actor in one string per ADR-288 D1.
REAPPLY_AUTHORED_BY = "system:substrate-reapply"


# ---------------------------------------------------------------------------
# Result shape (returned to caller, appended to audit log)
# ---------------------------------------------------------------------------

@dataclass
class ReapplyAction:
    """One file re-applied during a re-apply run."""
    path: str
    layer: str  # "kernel" | "bundle"
    change_summary: str


@dataclass
class ReapplyReport:
    """Structured result of one re-apply run."""
    user_id: str
    source: str  # "scheduled" | "manual"
    ran_at: str  # ISO 8601 UTC
    program_slug: Optional[str]
    actions: list[ReapplyAction] = field(default_factory=list)
    skipped_operator_authored: int = 0
    skipped_aligned: int = 0
    error: Optional[str] = None

    def to_log_markdown(self) -> str:
        """Render as a markdown append-block for the audit log."""
        lines = [
            f"## Re-apply run — {self.ran_at}",
            "",
            f"- **Source**: `{self.source}`",
            f"- **Program**: `{self.program_slug or 'none'}`",
            f"- **Actions taken**: {len(self.actions)}",
            f"- **Skipped (operator-authored)**: {self.skipped_operator_authored}",
            f"- **Skipped (aligned with canon)**: {self.skipped_aligned}",
        ]
        if self.error:
            lines.append(f"- **Error**: `{self.error}`")
        if self.actions:
            lines.append("")
            lines.append("### Actions")
            lines.append("")
            for action in self.actions:
                lines.append(
                    f"- `{action.path}` ({action.layer}) — {action.change_summary}"
                )
        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Kernel-layer re-apply
# ---------------------------------------------------------------------------

def _build_kernel_canonical_set() -> dict[str, tuple[str, str]]:
    """Return the canonical kernel-universal seed set.

    Mirrors `workspace_init.initialize_workspace` Phase 2's `workspace_files`
    dict but inverts the gate — instead of "write if missing", we want
    "the canonical content for these paths". The caller compares current
    workspace content against these and re-applies where they're still
    skeleton-shaped per `is_skeleton_content`.

    Per ADR-286, kernel writes ONLY kernel-universal paths (paths no bundle
    ships). Bundle-owned paths (MANDATE, IDENTITY, BRAND, AUTONOMY, etc.)
    are handled by the bundle re-apply layer below.
    """
    from services.orchestration import (
        TP_ORCHESTRATION_PLAYBOOK,
        DEFAULT_PRECEDENT_MD,
        DEFAULT_REVIEW_CALIBRATION_MD,
    )
    from services.workspace_paths import (
        SHARED_PRECEDENT_PATH,
        MEMORY_PLAYBOOK_PATH,
        MEMORY_STYLE_PATH,
        MEMORY_NOTES_PATH,
        REVIEW_PRINCIPLES_YAML_PATH,
        REVIEW_CALIBRATION_PATH,
    )

    review_principles_yaml_default = (
        "# _principles.yaml — machine-parsed review thresholds (ADR-254)\n"
        "# Read by review_policy.load_principles() via yaml.safe_load.\n"
        "# For the Reviewer's full reasoning framework, see principles.md.\n\n"
        "# Uncomment and set when you have a domain with outcome tracking:\n"
        "# trading:\n"
        "#   high_impact_threshold_cents: 50000  # $500 routes outcome to task feedback.md\n"
        "#   auto_approve_below_cents: 0         # set to enable AI auto-action\n"
    )

    return {
        SHARED_PRECEDENT_PATH: (
            DEFAULT_PRECEDENT_MD,
            "Precedent substrate — durable boundary-case guidance",
        ),
        MEMORY_PLAYBOOK_PATH: (
            TP_ORCHESTRATION_PLAYBOOK,
            "YARNNN orchestration playbook",
        ),
        MEMORY_STYLE_PATH: (
            "# Style\n<!-- System-inferred from edit patterns. -->\n",
            "Style placeholder",
        ),
        MEMORY_NOTES_PATH: (
            "# Notes\n<!-- YARNNN-extracted facts and instructions. -->\n",
            "Notes placeholder",
        ),
        REVIEW_PRINCIPLES_YAML_PATH: (
            review_principles_yaml_default,
            "Reviewer machine-parsed thresholds — kernel-universal default",
        ),
        REVIEW_CALIBRATION_PATH: (
            DEFAULT_REVIEW_CALIBRATION_MD,
            "Reviewer seat calibration trail (auto-generated by back-office task)",
        ),
    }


async def _reapply_kernel_layer(
    client: Any,
    user_id: str,
    report: ReapplyReport,
) -> None:
    """Walk kernel-universal paths; re-apply where skeleton-shaped.

    Gate: a path is re-applicable iff its current workspace content is
    still detected as skeleton via `is_skeleton_content` AND the canonical
    content differs from current content. Otherwise skip.
    """
    from services.workspace import UserMemory
    from services.workspace_utils import is_skeleton_content

    um = UserMemory(client, user_id)
    canonical = _build_kernel_canonical_set()

    for path, (canonical_content, change_summary) in canonical.items():
        existing = await um.read(path)

        # No file yet → kernel skeleton missing entirely. workspace_init
        # would have caught this on signup; re-apply makes the recovery
        # path explicit for workspaces predating a path addition.
        if existing is None:
            await um.write(
                path,
                canonical_content,
                summary=f"Substrate re-apply: {change_summary}",
                authored_by=REAPPLY_AUTHORED_BY,
                message=f"re-applied kernel skeleton (was missing): {path}",
            )
            report.actions.append(ReapplyAction(
                path=path,
                layer="kernel",
                change_summary=f"created (was missing): {change_summary}",
            ))
            continue

        # Already aligned with canon → nothing to do.
        if existing == canonical_content:
            report.skipped_aligned += 1
            continue

        # Operator has customized → never touch.
        if not is_skeleton_content(existing, bundle_body=canonical_content):
            report.skipped_operator_authored += 1
            continue

        # Skeleton-shaped but content drifted from canon (kernel default
        # changed since the workspace's last seed). Re-apply.
        await um.write(
            path,
            canonical_content,
            summary=f"Substrate re-apply: {change_summary}",
            authored_by=REAPPLY_AUTHORED_BY,
            message=f"re-applied kernel skeleton (canon updated): {path}",
        )
        report.actions.append(ReapplyAction(
            path=path,
            layer="kernel",
            change_summary=f"updated to current canon: {change_summary}",
        ))


# ---------------------------------------------------------------------------
# Bundle-layer re-apply
# ---------------------------------------------------------------------------

async def _reapply_bundle_layer(
    client: Any,
    user_id: str,
    program_slug: str,
    report: ReapplyReport,
) -> None:
    """Re-run the existing `fork_reference_workspace` for the activated bundle.

    `fork_reference_workspace` already implements the exact mechanism
    ADR-292 needs at the bundle layer: idempotent re-application, gated
    by `is_skeleton_content`, attributed via ADR-209. Re-running it IS
    the bundle re-apply.

    Singular Implementation: we do NOT introduce a second per-file walker
    here. One fork primitive, two trigger sites (one-shot activation +
    continuous re-apply).
    """
    from services.programs import fork_reference_workspace

    fork_result = await fork_reference_workspace(client, user_id, program_slug)

    # fork_reference_workspace returns files_written + files_skipped.
    # We classify them into the re-apply report's vocabulary.
    for path in fork_result.get("files_written", []):
        # OCCUPANT.md is always rewritten by fork_reference_workspace's
        # `_populate_occupant_for_runtime` step — filter it out so re-apply
        # reports don't show a spurious "OCCUPANT.md was updated" line on
        # every cycle.
        if path == "review/OCCUPANT.md":
            report.skipped_aligned += 1
            continue
        report.actions.append(ReapplyAction(
            path=path,
            layer="bundle",
            change_summary=f"re-forked from {program_slug} bundle",
        ))

    # files_skipped in fork's vocabulary = "operator has customized" (the
    # is_skeleton_content gate said no). Count as operator-authored skip.
    skipped = fork_result.get("files_skipped", [])
    report.skipped_operator_authored += len(skipped)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

async def _append_audit_log(client: Any, user_id: str, report: ReapplyReport) -> None:
    """Append one re-apply run to the workspace audit log.

    The log is system-authored substrate — operator-readable for audit,
    not operator-actionable (re-apply runs daily on its own; the log
    surfaces what happened, not what to decide).
    """
    from services.workspace import UserMemory

    um = UserMemory(client, user_id)
    existing = await um.read(REAPPLY_AUDIT_LOG_PATH) or (
        "# Substrate re-apply log\n\n"
        "Append-only audit trail of `back-office-substrate-reapply` runs.\n"
        "System-authored per ADR-292. Each block records one re-apply cycle:\n"
        "actions taken, files skipped because operator customized them, files\n"
        "skipped because they were already aligned with current canon.\n\n"
        "---\n\n"
    )

    new_content = existing + report.to_log_markdown()

    await um.write(
        REAPPLY_AUDIT_LOG_PATH,
        new_content,
        summary="Substrate re-apply audit log",
        authored_by=REAPPLY_AUTHORED_BY,
        message=f"appended re-apply run ({len(report.actions)} actions)",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def reapply_platform_substrate(
    client: Any,
    user_id: str,
    *,
    source: str = "scheduled",
) -> ReapplyReport:
    """Run one continuous substrate re-apply cycle for a workspace.

    Args:
        client: Supabase client (service-key — same shape every back-office
            primitive uses).
        user_id: Workspace owner.
        source: "scheduled" (daily back-office), "manual" (operator-triggered
            script), or "deploy" (post-deploy hook). Only affects the
            audit-log attribution; behavior identical.

    Returns the ReapplyReport with action list + skip counts. Always
    appends to the audit log, even on no-op runs (the log entry with empty
    actions is the proof that the cycle ran).
    """
    from services.programs import parse_active_program_slug
    from services.workspace import UserMemory
    from services.workspace_paths import SHARED_MANDATE_PATH

    ran_at = datetime.now(timezone.utc).isoformat()

    # Resolve active program (if any) before doing the work, so the report
    # carries it even on error paths.
    um = UserMemory(client, user_id)
    mandate_content = await um.read(SHARED_MANDATE_PATH)
    program_slug = parse_active_program_slug(mandate_content)

    report = ReapplyReport(
        user_id=user_id,
        source=source,
        ran_at=ran_at,
        program_slug=program_slug,
    )

    try:
        await _reapply_kernel_layer(client, user_id, report)
    except Exception as e:
        logger.exception(
            "[SUBSTRATE_REAPPLY] kernel layer failed for %s: %s", user_id[:8], e
        )
        report.error = f"kernel_layer: {e}"

    if program_slug:
        try:
            await _reapply_bundle_layer(client, user_id, program_slug, report)
        except Exception as e:
            logger.exception(
                "[SUBSTRATE_REAPPLY] bundle layer failed for %s/%s: %s",
                user_id[:8], program_slug, e,
            )
            # Preserve any prior error; report multiple via concat.
            bundle_err = f"bundle_layer: {e}"
            report.error = (
                f"{report.error}; {bundle_err}" if report.error else bundle_err
            )

    try:
        await _append_audit_log(client, user_id, report)
    except Exception as e:
        logger.exception(
            "[SUBSTRATE_REAPPLY] audit log append failed for %s: %s", user_id[:8], e
        )
        # Audit-log failure is not fatal — the actions already landed.
        # Log loudly but return the report so the caller knows what happened.

    logger.info(
        "[SUBSTRATE_REAPPLY] %s/%s: %d actions, %d skipped-operator, %d skipped-aligned",
        user_id[:8],
        program_slug or "no-program",
        len(report.actions),
        report.skipped_operator_authored,
        report.skipped_aligned,
    )
    return report


# ---------------------------------------------------------------------------
# Mechanical primitive handler
# ---------------------------------------------------------------------------
# Per ADR-263 D5 + ADR-264 D2: a mechanical-mode recurrence's prompt names a
# primitive invocation via `@primitive: <Name>(<args>)`. The dispatcher calls
# the handler registered in HANDLERS. The handler takes (auth, args) and
# returns a result dict.

REAPPLY_PLATFORM_SUBSTRATE_TOOL = {
    "name": "ReapplyPlatformSubstrate",
    "description": (
        "Continuous substrate re-apply (ADR-292). Walks kernel-universal "
        "paths + the activated program bundle's reference-workspace, "
        "re-writes platform-managed files where the operator has not "
        "taken authorship. Audit log at /workspace/_shared/"
        "substrate-reapply-log.md.\n\n"
        "Mechanical-mode primitive — invoked via @primitive: "
        "ReapplyPlatformSubstrate() directive from "
        "`back-office-substrate-reapply` recurrence. No args."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


async def handle_reapply_platform_substrate(auth: Any, input: dict) -> dict:
    """Execute ReapplyPlatformSubstrate (ADR-292).

    Returns:
      {
        "success": bool,
        "actions_taken": int,
        "skipped_operator_authored": int,
        "skipped_aligned": int,
        "program_slug": str | None,
        "error": str | None,
      }
    """
    user_id = getattr(auth, "user_id", None)
    db_client = getattr(auth, "client", None)
    if not user_id or not db_client:
        return {
            "success": False,
            "error": "auth_required",
            "actions_taken": 0,
            "skipped_operator_authored": 0,
            "skipped_aligned": 0,
            "program_slug": None,
        }

    report = await reapply_platform_substrate(db_client, user_id, source="scheduled")
    return {
        "success": report.error is None,
        "actions_taken": len(report.actions),
        "skipped_operator_authored": report.skipped_operator_authored,
        "skipped_aligned": report.skipped_aligned,
        "program_slug": report.program_slug,
        "error": report.error,
    }
