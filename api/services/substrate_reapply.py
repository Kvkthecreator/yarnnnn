"""
Operator-Initiated Substrate Update — ADR-292.

Closes the gap between docs/ canon and live operator workspaces. When kernel
skeleton constants improve (e.g., tightened safety language in
`DEFAULT_REVIEW_PRINCIPLES_MD`) or bundle templates evolve in
`docs/programs/{slug}/reference-workspace/`, this service propagates the
updates to a live workspace — when the operator chooses to take them.

Shape (ADR-292):

  The model is **Claude Code's `claude --update`**, not a daily cron:
    - Platform versions substrate (KERNEL_VERSION + MANIFEST.yaml `version:`)
    - Detection compares platform-version vs workspace-recorded version
    - Operator sees "Update available" notification on Settings → Workspace
    - Operator clicks "Update" → this function runs → workspace advances

  Substrate-native version record: MANDATE.md frontmatter carries
  `activated_bundle_version` + `activated_kernel_version`. ADR-209
  attribution captures the update event in the revision chain. No schema
  bifurcation.

Public surface:

  - `bundle_update_available(client, user_id) -> Optional[BundleUpdateInfo]`
    Read-only detection helper. Cockpit surface consults this.
  - `kernel_update_available(client, user_id) -> Optional[KernelUpdateInfo]`
    Read-only detection helper.
  - `apply_substrate_update(client, user_id, *, scope, source) -> UpdateReport`
    Operator-initiated update. `scope` = "kernel" | "bundle" | "both".
    `source` is recorded in the audit log.

NOT a mechanical primitive (no @primitive: ReapplyPlatformSubstrate
directive). NOT a daily back-office recurrence. Operator decides when.

Audit log: `/workspace/system/substrate-update-log.md` (ADR-320: relocated
from the dissolved _shared/ root), system-authored, append-only. Each entry
records one update event with attribution.

Canonical references:
  - docs/adr/ADR-292-continuous-substrate-reapply.md
  - docs/architecture/propagation-discipline.md
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# ADR-320: relocated from the dissolved _shared/ root to system/ (the
# orchestration-runtime root). Substrate-update bookkeeping is system-authored
# runtime state, same character as system/_playbook.md / _schedule_index.md.
UPDATE_AUDIT_LOG_PATH = "system/substrate-update-log.md"

# Attribution actor for ADR-292 update events. Distinct from
# `system:bundle-fork` (one-shot activation actor) — names the operator-
# initiated update actor per ADR-288 D1 caller_identity contract.
UPDATE_AUTHORED_BY = "system:substrate-update"

# Frontmatter keys we read/write on MANDATE.md.
FRONTMATTER_BUNDLE_KEY = "activated_bundle_version"
FRONTMATTER_KERNEL_KEY = "activated_kernel_version"

# ADR-292 v3 D9: bundle files divided by architectural role. CONFIG_PATHS
# are operationally load-bearing — the kernel scheduler + wake architecture
# read them as source of truth for what the workspace does. Operator-edits
# express intent but the bundle ships shape constraints (which slugs exist;
# which sub-shapes are valid; what prompts are runtime-coupled). When the
# bundle moves shape, operator-edits on the old shape may be functionally
# inert or broken under the new code. Discipline: auto-overwrite the bundle's
# new content into the live path; back up the operator's prior content to
# `/workspace/system/conflict-backups/{ran_at}/{relative_path}` for manual
# inspection. Closed-set today — adding a third config file requires an ADR
# amendment naming it and updating this constant in the same commit.
CONFIG_PATHS: frozenset[str] = frozenset({
    "_recurrences.yaml",
    "_hooks.yaml",
})

# Per ADR-292 v3 D10: backup destination convention for operator-edited
# config files that get overwritten by a bundle update. Operator-readable;
# the audit log entry surfaces the backup path so manual re-application of
# the prior edits is a known affordance.
CONFLICT_BACKUP_PREFIX = "system/conflict-backups"

UpdateScope = Literal["kernel", "bundle", "both"]
UpdateSource = Literal["operator", "harness", "test"]


# ---------------------------------------------------------------------------
# Detection result shapes
# ---------------------------------------------------------------------------

@dataclass
class BundleUpdateInfo:
    """Result of `bundle_update_available()` when an update IS available."""
    program_slug: str
    workspace_version: Optional[str]   # None if never recorded
    available_version: str
    diff_summary: str  # short human-readable e.g. "2026-05-18.1 → 2026-05-25.1"


@dataclass
class KernelUpdateInfo:
    """Result of `kernel_update_available()` when an update IS available."""
    workspace_version: Optional[str]   # None if never recorded
    available_version: str
    diff_summary: str


# ---------------------------------------------------------------------------
# Update report (returned by apply_substrate_update, appended to audit log)
# ---------------------------------------------------------------------------

@dataclass
class UpdateAction:
    """One file updated during an update event."""
    path: str
    layer: str  # "kernel" | "bundle"
    change_summary: str


@dataclass
class ConflictedFile:
    """One CONFIG_PATHS file that was auto-overwritten with backup.

    Per ADR-292 v3 D9 + D10. Bundle-config files (`_recurrences.yaml`,
    `_hooks.yaml`) that were operator-edited get auto-overwritten with the
    bundle's new content; the operator's prior content lives at backup_path
    for manual inspection / selective re-application.

    The audit log renders these distinctly from `actions` (which are normal
    re-fork writes) and from `skipped_operator_authored` (operator-edited
    prose preserved as-is). A ConflictedFile entry means "we did write the
    bundle's content; your prior edits are at the backup path."
    """
    path: str           # relative workspace path that was overwritten
    backup_path: str    # relative workspace path where operator edits were saved
    bundle_version: str # bundle version that was re-applied


@dataclass
class UpdateReport:
    """Structured result of one operator-initiated update event."""
    user_id: str
    source: str
    ran_at: str  # ISO 8601 UTC
    scope: str   # "kernel" | "bundle" | "both"
    program_slug: Optional[str]
    kernel_from: Optional[str]
    kernel_to: Optional[str]
    bundle_from: Optional[str]
    bundle_to: Optional[str]
    actions: list[UpdateAction] = field(default_factory=list)
    skipped_operator_authored: int = 0
    skipped_aligned: int = 0
    config_conflicts: list[ConflictedFile] = field(default_factory=list)  # ADR-292 v3
    error: Optional[str] = None

    def to_log_markdown(self) -> str:
        """Render as a markdown append-block for the audit log."""
        lines = [
            f"## Substrate update — {self.ran_at}",
            "",
            f"- **Source**: `{self.source}`",
            f"- **Scope**: `{self.scope}`",
            f"- **Program**: `{self.program_slug or 'none'}`",
        ]
        if self.kernel_from or self.kernel_to:
            lines.append(
                f"- **Kernel version**: `{self.kernel_from or 'none'}` → `{self.kernel_to or 'unchanged'}`"
            )
        if self.bundle_from or self.bundle_to:
            lines.append(
                f"- **Bundle version**: `{self.bundle_from or 'none'}` → `{self.bundle_to or 'unchanged'}`"
            )
        lines.extend([
            f"- **Actions taken**: {len(self.actions)}",
            f"- **Skipped (operator-authored prose)**: {self.skipped_operator_authored}",
            f"- **Skipped (aligned with canon)**: {self.skipped_aligned}",
        ])
        if self.config_conflicts:
            lines.append(
                f"- **Config conflicts auto-resolved**: {len(self.config_conflicts)}"
            )
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
        if self.config_conflicts:
            # Per ADR-292 v3 D10: surface backup paths so operator knows
            # where to inspect prior edits.
            lines.append("")
            lines.append("### Config conflicts (operator-edits backed up, bundle re-applied)")
            lines.append("")
            for conflict in self.config_conflicts:
                lines.append(
                    f"- `{conflict.path}` → backup at `{conflict.backup_path}` "
                    f"(bundle version `{conflict.bundle_version}`). "
                    f"Operator may inspect the backup to re-apply edits selectively."
                )
        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# MANDATE.md frontmatter read/write
# ---------------------------------------------------------------------------
#
# We use a minimal hand-rolled YAML frontmatter parser to avoid coupling
# MANDATE.md reads to a generic frontmatter library. The shape is:
#
#   ---
#   activated_bundle_version: 2026-05-18.1
#   activated_kernel_version: 2026-05-18.1
#   ---
#   # Mandate — alpha-trader (template)
#   ...
#
# Frontmatter is optional. Absence is the legitimate "no version recorded
# yet" state (e.g., workspaces that activated before ADR-292 shipped).

_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<body>.*?)\n---\s*\n(?P<rest>.*)\Z",
    re.DOTALL,
)


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a markdown file.

    Returns (frontmatter_dict, body_without_frontmatter). If no frontmatter
    block is present, returns ({}, content_unchanged).

    Tolerant: malformed YAML returns ({}, content_unchanged) — we never
    raise on operator content.
    """
    if not content:
        return {}, content or ""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    body = match.group("body")
    rest = match.group("rest")
    fm: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip()
    return fm, rest


def _render_frontmatter(fm: dict[str, str], body: str) -> str:
    """Render frontmatter + body as a single string.

    If `fm` is empty, returns body unchanged. Otherwise emits a `---`-
    delimited YAML block followed by body.
    """
    if not fm:
        return body
    lines = ["---"]
    for key in sorted(fm):  # stable key order
        lines.append(f"{key}: {fm[key]}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body


def _read_workspace_versions(mandate_content: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Extract (bundle_version, kernel_version) from MANDATE.md frontmatter.

    Returns (None, None) if frontmatter absent or keys missing.
    """
    if not mandate_content:
        return None, None
    fm, _ = _parse_frontmatter(mandate_content)
    return (
        fm.get(FRONTMATTER_BUNDLE_KEY),
        fm.get(FRONTMATTER_KERNEL_KEY),
    )


def _write_workspace_versions(
    mandate_content: str,
    *,
    bundle_version: Optional[str] = None,
    kernel_version: Optional[str] = None,
) -> str:
    """Return MANDATE.md content with frontmatter version keys updated.

    Only the supplied keys are modified — pass None for keys to leave
    untouched. Other frontmatter keys (if any future ones exist) are
    preserved unchanged.
    """
    fm, body = _parse_frontmatter(mandate_content)
    if bundle_version is not None:
        fm[FRONTMATTER_BUNDLE_KEY] = bundle_version
    if kernel_version is not None:
        fm[FRONTMATTER_KERNEL_KEY] = kernel_version
    return _render_frontmatter(fm, body)


# ---------------------------------------------------------------------------
# Detection helpers (read-only)
# ---------------------------------------------------------------------------

async def bundle_update_available(
    client: Any, user_id: str
) -> Optional[BundleUpdateInfo]:
    """Return BundleUpdateInfo if the workspace's bundle version is behind canon.

    Returns None when:
      - workspace has no program activated
      - workspace's recorded bundle version equals current MANIFEST.yaml version
      - bundle has no `version:` field declared (caller treats as no-update)

    Caller (cockpit Settings → Workspace surface) renders the update
    affordance only when this returns non-None.
    """
    from services.bundle_reader import get_bundle_version
    from services.programs import parse_active_program_slug
    from services.workspace import UserMemory
    from services.workspace_paths import CONSTITUTION_MANDATE_PATH

    um = UserMemory(client, user_id)
    mandate_content = await um.read(CONSTITUTION_MANDATE_PATH)
    program_slug = parse_active_program_slug(mandate_content)
    if not program_slug:
        return None

    available = get_bundle_version(program_slug)
    if not available:
        return None  # bundle hasn't declared a version yet

    workspace_version, _ = _read_workspace_versions(mandate_content)
    if workspace_version == available:
        return None  # already up-to-date

    return BundleUpdateInfo(
        program_slug=program_slug,
        workspace_version=workspace_version,
        available_version=available,
        diff_summary=f"{workspace_version or 'unversioned'} → {available}",
    )


async def kernel_update_available(
    client: Any, user_id: str
) -> Optional[KernelUpdateInfo]:
    """Return KernelUpdateInfo if the workspace's kernel version is behind canon.

    Returns None when the workspace's recorded kernel version equals
    current `services.orchestration.KERNEL_VERSION`.
    """
    from services.orchestration import KERNEL_VERSION
    from services.workspace import UserMemory
    from services.workspace_paths import CONSTITUTION_MANDATE_PATH

    um = UserMemory(client, user_id)
    mandate_content = await um.read(CONSTITUTION_MANDATE_PATH)
    _, workspace_version = _read_workspace_versions(mandate_content)
    if workspace_version == KERNEL_VERSION:
        return None

    return KernelUpdateInfo(
        workspace_version=workspace_version,
        available_version=KERNEL_VERSION,
        diff_summary=f"{workspace_version or 'unversioned'} → {KERNEL_VERSION}",
    )


# ---------------------------------------------------------------------------
# Update workers
# ---------------------------------------------------------------------------

def _build_kernel_canonical_set() -> dict[str, tuple[str, str]]:
    """Return the canonical kernel-universal seed set.

    Mirrors `workspace_init.initialize_workspace` Phase 2's `workspace_files`
    dict but inverts the gate — instead of "write if missing", we want
    "the canonical content for these paths" so the update worker can
    re-apply on operator request.

    Per ADR-286, kernel writes ONLY kernel-universal paths (paths no bundle
    ships). Bundle-owned paths are handled by the bundle update layer.
    """
    from services.orchestration import (
        TP_ORCHESTRATION_PLAYBOOK,
        DEFAULT_PRECEDENT_MD,
        DEFAULT_REVIEW_REFLECTION_MD,  # ADR-364: supersedes DEFAULT_REVIEW_CALIBRATION_MD
    )
    from services.workspace_paths import (
        CONSTITUTION_PRECEDENT_PATH,
        SYSTEM_PLAYBOOK_PATH,
        SYSTEM_STYLE_PATH,
        SYSTEM_NOTES_PATH,
        PERSONA_PRINCIPLES_YAML_PATH,
        PERSONA_REFLECTION_PATH,  # ADR-364
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
        CONSTITUTION_PRECEDENT_PATH: (
            DEFAULT_PRECEDENT_MD,
            "Precedent substrate — durable boundary-case guidance",
        ),
        SYSTEM_PLAYBOOK_PATH: (
            TP_ORCHESTRATION_PLAYBOOK,
            "YARNNN orchestration playbook",
        ),
        SYSTEM_STYLE_PATH: (
            "# Style\n<!-- System-inferred from edit patterns. -->\n",
            "Style placeholder",
        ),
        SYSTEM_NOTES_PATH: (
            "# Notes\n<!-- YARNNN-extracted facts and instructions. -->\n",
            "Notes placeholder",
        ),
        PERSONA_PRINCIPLES_YAML_PATH: (
            review_principles_yaml_default,
            "Reviewer machine-parsed thresholds — kernel-universal default",
        ),
        PERSONA_REFLECTION_PATH: (
            DEFAULT_REVIEW_REFLECTION_MD,
            "Reviewer seat reflection — interpreted learning from the closed intent→outcome loop (ADR-364)",
        ),
    }


async def _update_kernel_layer(
    client: Any,
    user_id: str,
    report: UpdateReport,
) -> None:
    """Apply kernel-universal seed updates.

    Gate: a path is updatable iff its current workspace content is still
    detected as skeleton via `is_skeleton_content` AND the canonical
    content differs from current. Otherwise skip.
    """
    from services.workspace import UserMemory
    from services.workspace_utils import is_skeleton_content

    um = UserMemory(client, user_id)
    canonical = _build_kernel_canonical_set()

    for path, (canonical_content, change_summary) in canonical.items():
        existing = await um.read(path)

        if existing is None:
            await um.write(
                path,
                canonical_content,
                summary=f"Substrate update: {change_summary}",
                authored_by=UPDATE_AUTHORED_BY,
                message=f"applied kernel update (was missing): {path}",
            )
            report.actions.append(UpdateAction(
                path=path,
                layer="kernel",
                change_summary=f"created (was missing): {change_summary}",
            ))
            continue

        if existing == canonical_content:
            report.skipped_aligned += 1
            continue

        if not is_skeleton_content(existing, bundle_body=canonical_content):
            report.skipped_operator_authored += 1
            continue

        await um.write(
            path,
            canonical_content,
            summary=f"Substrate update: {change_summary}",
            authored_by=UPDATE_AUTHORED_BY,
            message=f"applied kernel update: {path}",
        )
        report.actions.append(UpdateAction(
            path=path,
            layer="kernel",
            change_summary=f"updated to current canon: {change_summary}",
        ))


async def _update_bundle_layer(
    client: Any,
    user_id: str,
    program_slug: str,
    report: UpdateReport,
) -> None:
    """Apply bundle template updates via existing `fork_reference_workspace`.

    `fork_reference_workspace` already implements the exact gate ADR-292
    needs at the bundle layer: idempotent re-application, content-gated by
    `is_skeleton_content`, attributed via ADR-209. Per ADR-292 v3 D10, the
    fork worker also handles config-vs-prose taxonomy + conflict backups
    internally — this function maps its return shape into UpdateReport.

    Singular Implementation: one fork primitive, two trigger sites
    (one-shot activation + operator-initiated update).
    """
    from services.programs import fork_reference_workspace

    fork_result = await fork_reference_workspace(client, user_id, program_slug)

    # Surface config conflicts first so the report renders them distinctly
    # from normal re-fork writes (per ADR-292 v3 D10).
    conflict_paths = set()
    for conflict in fork_result.get("config_conflicts", []) or []:
        report.config_conflicts.append(ConflictedFile(
            path=conflict["path"],
            backup_path=conflict["backup_path"],
            bundle_version=conflict["bundle_version"],
        ))
        conflict_paths.add(conflict["path"])

    for path in fork_result.get("files_written", []):
        # OCCUPANT.md is rewritten on every fork by `_populate_occupant_for_runtime`.
        # Filter it from the update report so it doesn't surface as a
        # spurious update action on every cycle.
        if path == "persona/OCCUPANT.md":
            report.skipped_aligned += 1
            continue
        # Config conflicts already surfaced above — don't double-count.
        if path in conflict_paths:
            continue
        # Also skip backup-path writes (system-authored, not operator-facing actions).
        if path.startswith(CONFLICT_BACKUP_PREFIX + "/"):
            continue
        report.actions.append(UpdateAction(
            path=path,
            layer="bundle",
            change_summary=f"re-forked from {program_slug} bundle",
        ))

    skipped = fork_result.get("files_skipped", [])
    report.skipped_operator_authored += len(skipped)


# ---------------------------------------------------------------------------
# MANDATE.md version-stamp write
# ---------------------------------------------------------------------------

async def _advance_workspace_version_stamps(
    client: Any,
    user_id: str,
    *,
    bundle_version: Optional[str],
    kernel_version: Optional[str],
) -> None:
    """Write updated `activated_*_version` keys into MANDATE.md frontmatter.

    Idempotent: if both versions match existing frontmatter, no write happens.
    """
    from services.workspace import UserMemory
    from services.workspace_paths import CONSTITUTION_MANDATE_PATH

    um = UserMemory(client, user_id)
    mandate_content = await um.read(CONSTITUTION_MANDATE_PATH) or ""

    existing_bundle, existing_kernel = _read_workspace_versions(mandate_content)
    needs_write = False
    if bundle_version is not None and bundle_version != existing_bundle:
        needs_write = True
    if kernel_version is not None and kernel_version != existing_kernel:
        needs_write = True
    if not needs_write:
        return

    new_content = _write_workspace_versions(
        mandate_content,
        bundle_version=bundle_version,
        kernel_version=kernel_version,
    )

    parts = []
    if bundle_version is not None:
        parts.append(f"bundle={bundle_version}")
    if kernel_version is not None:
        parts.append(f"kernel={kernel_version}")

    await um.write(
        CONSTITUTION_MANDATE_PATH,
        new_content,
        summary="Substrate update: advance version stamps",
        authored_by=UPDATE_AUTHORED_BY,
        message=f"advance MANDATE.md version stamps ({', '.join(parts)})",
    )


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

async def _append_audit_log(client: Any, user_id: str, report: UpdateReport) -> None:
    """Append one update event to the workspace audit log."""
    from services.workspace import UserMemory

    um = UserMemory(client, user_id)
    existing = await um.read(UPDATE_AUDIT_LOG_PATH) or (
        "# Substrate update log\n\n"
        "Append-only audit trail of ADR-292 operator-initiated substrate\n"
        "updates. Each block records one update event: scope, source, before/\n"
        "after versions, files touched, skip counters.\n\n"
        "Operator-readable; not operator-actionable (each entry already\n"
        "represents an applied decision).\n\n"
        "---\n\n"
    )

    new_content = existing + report.to_log_markdown()

    await um.write(
        UPDATE_AUDIT_LOG_PATH,
        new_content,
        summary="Substrate update audit log",
        authored_by=UPDATE_AUTHORED_BY,
        message=f"appended update event ({len(report.actions)} actions, scope={report.scope})",
    )


# ---------------------------------------------------------------------------
# Public entry point — operator-initiated update
# ---------------------------------------------------------------------------

async def apply_substrate_update(
    client: Any,
    user_id: str,
    *,
    scope: UpdateScope = "both",
    source: UpdateSource = "operator",
) -> UpdateReport:
    """Run one operator-initiated substrate update.

    Args:
        client: Supabase client (service-key shape for back-office work).
        user_id: Workspace owner.
        scope: Which layer to update. "kernel" | "bundle" | "both".
        source: Audit-log attribution. Default "operator" — the cockpit
            Settings → Workspace button calls this with source="operator".
            Harness scripts may call with source="harness"; tests with
            source="test".

    Returns the UpdateReport. Always appends to the audit log, even on
    no-op runs (the entry with empty `actions` is the proof the
    update was attempted).

    Behavior:
      1. Read active program slug from MANDATE.md (if any).
      2. Resolve "to" versions: kernel = orchestration.KERNEL_VERSION,
         bundle = bundle_reader.get_bundle_version(slug) or None.
      3. Read "from" versions from MANDATE.md frontmatter.
      4. If scope includes "kernel": run kernel-layer update worker.
      5. If scope includes "bundle" AND program activated: run bundle worker.
      6. Advance MANDATE.md frontmatter version stamps to the "to" versions.
      7. Append UpdateReport to audit log.
    """
    from services.bundle_reader import get_bundle_version
    from services.orchestration import KERNEL_VERSION
    from services.programs import parse_active_program_slug
    from services.workspace import UserMemory
    from services.workspace_paths import CONSTITUTION_MANDATE_PATH

    ran_at = datetime.now(timezone.utc).isoformat()

    um = UserMemory(client, user_id)
    mandate_content = await um.read(CONSTITUTION_MANDATE_PATH)
    program_slug = parse_active_program_slug(mandate_content)
    bundle_from, kernel_from = _read_workspace_versions(mandate_content)

    bundle_to: Optional[str] = None
    if program_slug:
        bundle_to = get_bundle_version(program_slug)
    kernel_to: Optional[str] = KERNEL_VERSION

    report = UpdateReport(
        user_id=user_id,
        source=source,
        ran_at=ran_at,
        scope=scope,
        program_slug=program_slug,
        kernel_from=kernel_from,
        kernel_to=kernel_to if scope in ("kernel", "both") else None,
        bundle_from=bundle_from,
        bundle_to=bundle_to if scope in ("bundle", "both") else None,
    )

    if scope in ("kernel", "both"):
        try:
            await _update_kernel_layer(client, user_id, report)
        except Exception as e:
            logger.exception(
                "[SUBSTRATE_UPDATE] kernel layer failed for %s: %s", user_id[:8], e
            )
            report.error = f"kernel_layer: {e}"

    if scope in ("bundle", "both") and program_slug:
        try:
            await _update_bundle_layer(client, user_id, program_slug, report)
        except Exception as e:
            logger.exception(
                "[SUBSTRATE_UPDATE] bundle layer failed for %s/%s: %s",
                user_id[:8], program_slug, e,
            )
            bundle_err = f"bundle_layer: {e}"
            report.error = (
                f"{report.error}; {bundle_err}" if report.error else bundle_err
            )

    # Advance version stamps only on success of the layer that updated. We
    # write whichever stamps the scope covered, regardless of how many
    # actions were taken — the stamp records "operator approved this
    # version," not "files actually changed."
    if not report.error:
        try:
            await _advance_workspace_version_stamps(
                client,
                user_id,
                bundle_version=bundle_to if scope in ("bundle", "both") else None,
                kernel_version=kernel_to if scope in ("kernel", "both") else None,
            )
        except Exception as e:
            logger.exception(
                "[SUBSTRATE_UPDATE] version-stamp write failed for %s: %s",
                user_id[:8], e,
            )
            report.error = f"version_stamp: {e}"

    try:
        await _append_audit_log(client, user_id, report)
    except Exception as e:
        logger.exception(
            "[SUBSTRATE_UPDATE] audit log append failed for %s: %s", user_id[:8], e
        )
        # Audit-log failure is not fatal — actions already landed.

    logger.info(
        "[SUBSTRATE_UPDATE] %s scope=%s program=%s: %d actions, %d skipped-operator, %d skipped-aligned",
        user_id[:8], scope, program_slug or "no-program",
        len(report.actions),
        report.skipped_operator_authored,
        report.skipped_aligned,
    )
    return report
