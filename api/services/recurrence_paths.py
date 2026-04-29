"""
Recurrence Path Resolution — ADR-231 Phase 3.2.a.

Maps (RecurrenceDeclaration) → natural-home substrate paths per ADR-231 D2 / D9 / D10.

This is a pure-function module. No I/O, no side effects. Lives next to
`recurrence.py` (the YAML schema + walker) because both share the same
substrate-shape vocabulary; the dispatcher (3.2.b) and the data migration
script (3.5) both consume these resolvers.

ADR-231 D2 — Output substrate (post-cutover):

    DELIVERABLE   → /workspace/reports/{slug}/{date}/output.md
    ACCUMULATION  → /workspace/context/{domain}/   (entity files written by agent)
    ACTION        → no filesystem output (platform side-effect; narrative is the surface)
    MAINTENANCE   → /workspace/_shared/back-office-audit.md (append-only audit index)

ADR-231 D9 — Per-declaration working scratch:

    DELIVERABLE   → /workspace/reports/{slug}/working/
    ACCUMULATION  → /workspace/context/{domain}/working/{slug}/
    ACTION        → /workspace/operations/{slug}/working/
    MAINTENANCE   → /workspace/_shared/working/{slug}/

ADR-231 D10 — Run log discipline (declaration-scoped):

    DELIVERABLE   → /workspace/reports/{slug}/_run_log.md
    ACCUMULATION  → /workspace/context/{domain}/_run_log.md
    ACTION        → /workspace/operations/{slug}/_run_log.md
    MAINTENANCE   → /workspace/_shared/back-office-audit.md (the audit log IS the run log)

ADR-231 D2 — Feedback substrate (per declaration / per domain):

    DELIVERABLE   → /workspace/reports/{slug}/_feedback.md
    ACCUMULATION  → /workspace/context/{domain}/_feedback.md (per ADR-181 already canonical)
    ACTION        → no separate feedback file (outcomes ARE the feedback signal per ADR-195)
    MAINTENANCE   → no feedback file

Optional operator prose / one-shot steering:

    DELIVERABLE   → /workspace/reports/{slug}/_intent.md (optional)
    ACCUMULATION  → /workspace/context/{domain}/_intent.md (optional)
    ACTION        → /workspace/operations/{slug}/_intent.md (optional)
    MAINTENANCE   → (none — back-office is system-authored)

Rationale notes:

- ACCUMULATION outputs do NOT have a canonical "output file" per declaration.
  The recurrence's job is to update entity files in the domain (per ADR-151).
  `resolve_output_root` returns the domain root; the agent's WriteFile calls
  land entity files inside it.
- MAINTENANCE collapses per-task `outputs/{date}/` folders into a single
  shared audit log per ADR-231 D2 (`/workspace/_shared/back-office-audit.md`).
  Every back-office firing appends one entry. This is the substrate change
  that 3.2.b implements; the path resolver here ratifies the target.
- ACTION has no filesystem output substrate; the platform write IS the work,
  and the outcome reconciliation (ADR-195) writes to the relevant domain's
  `_performance.md`. `resolve_output_path` raises for ACTION to make the
  semantic explicit at the call site.

Date placeholder semantics:

  output paths for DELIVERABLE substitute `{date}` with the firing's
  ISO-8601 date-or-datetime tag at the call site. This module accepts an
  optional `started_at: datetime` parameter and renders the path; if
  None, the literal `{date}` placeholder is preserved (useful for
  declaration-time references and tests).

Date format: `%Y-%m-%dT%H%M` to match `task_workspace.save_output()` and
`task_pipeline.execute_task` step 9 — preserves cross-cutover continuity
of `outputs/{date}/` folder names so existing readers don't have to update.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from services.recurrence import RecurrenceDeclaration, RecurrenceShape

DATE_FOLDER_FORMAT = "%Y-%m-%dT%H%M"


# ---------------------------------------------------------------------------
# Substrate root — one per shape
# ---------------------------------------------------------------------------


def resolve_substrate_root(decl: RecurrenceDeclaration) -> str:
    """Return the directory that contains all per-declaration substrate.

    This is the parent of `working/`, `_run_log.md`, `_feedback.md`, and
    (for DELIVERABLE) the dated output folders. The dispatcher uses it as
    the prefix for every per-declaration write.

    For ACCUMULATION, the root is the *domain* directory — multiple
    declarations under the same domain share `_run_log.md` and `_feedback.md`
    but get sub-keyed `working/{slug}/` per ADR-231 D9.

    For MAINTENANCE, the root is `/workspace/_shared/`, again shared across
    all back-office declarations.
    """
    if decl.shape == RecurrenceShape.DELIVERABLE:
        return f"/workspace/reports/{decl.slug}"
    if decl.shape == RecurrenceShape.ACCUMULATION:
        domain = decl.domain
        if not domain:
            raise ValueError(
                f"ACCUMULATION declaration '{decl.slug}' missing domain "
                f"(declaration_path={decl.declaration_path}); cannot resolve substrate root"
            )
        return f"/workspace/context/{domain}"
    if decl.shape == RecurrenceShape.ACTION:
        return f"/workspace/operations/{decl.slug}"
    if decl.shape == RecurrenceShape.MAINTENANCE:
        return "/workspace/_shared"
    raise ValueError(f"unknown shape: {decl.shape}")


# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------


def resolve_output_path(
    decl: RecurrenceDeclaration,
    started_at: Optional[datetime] = None,
) -> str:
    """Return the canonical output write path for one firing.

    Behavior per shape:

    - DELIVERABLE: returns `<root>/{date}/output.md`. If declaration carries
      an explicit `output_path` field with a `{date}` placeholder, that wins
      over the default; this lets bundles override the canonical layout
      (e.g., `/workspace/reports/{slug}/{date}/brief.md` instead of `output.md`).
    - ACCUMULATION: raises ValueError. Accumulation has no per-firing output
      file; agents write entity files within the domain. Use
      `resolve_substrate_root(decl)` to get the domain root and let the
      agent place entity files inside it.
    - ACTION: raises ValueError. Action has no filesystem output (platform
      side-effect). Outcome reconciliation (ADR-195) is a separate substrate
      operation against the relevant domain's `_performance.md`.
    - MAINTENANCE: returns the shared audit log path
      `/workspace/_shared/back-office-audit.md`. Every back-office firing
      appends an entry; there are no per-task output folders post-cutover.

    Args:
        decl: parsed recurrence declaration
        started_at: timestamp for the firing; substituted into `{date}`
                    placeholder. If None, the literal `{date}` is preserved.

    Returns:
        Absolute workspace path string.

    Raises:
        ValueError: if the shape has no canonical output path.
    """
    if decl.shape == RecurrenceShape.DELIVERABLE:
        date_token = (
            started_at.strftime(DATE_FOLDER_FORMAT) if started_at is not None else "{date}"
        )
        # Bundle override
        if decl.output_path:
            template = decl.output_path
            if "{date}" in template:
                return template.replace("{date}", date_token)
            # Honor literal output_path if no placeholder — bundle author opted out of dating
            return template
        return f"/workspace/reports/{decl.slug}/{date_token}/output.md"

    if decl.shape == RecurrenceShape.ACCUMULATION:
        raise ValueError(
            f"ACCUMULATION declaration '{decl.slug}' has no canonical output path. "
            f"Use resolve_substrate_root(decl) for the domain root; entity files "
            f"are written by the agent inside it (per ADR-151)."
        )

    if decl.shape == RecurrenceShape.ACTION:
        raise ValueError(
            f"ACTION declaration '{decl.slug}' has no filesystem output. "
            f"The platform side-effect is the work; outcome reconciliation "
            f"writes to /workspace/context/{{domain}}/_performance.md "
            f"per ADR-195."
        )

    if decl.shape == RecurrenceShape.MAINTENANCE:
        return "/workspace/_shared/back-office-audit.md"

    raise ValueError(f"unknown shape: {decl.shape}")


def resolve_output_folder(
    decl: RecurrenceDeclaration,
    started_at: Optional[datetime] = None,
) -> str:
    """Return the directory that holds one firing's output bundle (DELIVERABLE only).

    The DELIVERABLE shape produces a folder containing `output.md`,
    `manifest.json`, section partials, and rendered assets. This helper
    returns the folder path; the dispatcher writes individual files into it.

    Raises ValueError for non-DELIVERABLE shapes — they don't have
    per-firing folders.
    """
    if decl.shape != RecurrenceShape.DELIVERABLE:
        raise ValueError(
            f"resolve_output_folder is DELIVERABLE-only; got {decl.shape.value} "
            f"for '{decl.slug}'"
        )
    output_path = resolve_output_path(decl, started_at=started_at)
    # Strip the trailing filename to get the folder
    if "/" in output_path:
        return output_path.rsplit("/", 1)[0]
    return output_path


# ---------------------------------------------------------------------------
# Per-declaration ancillary paths
# ---------------------------------------------------------------------------


def resolve_run_log_path(decl: RecurrenceDeclaration) -> str:
    """Return the path to the declaration's append-only run log per ADR-231 D10.

    DELIVERABLE / ACTION → per-declaration `_run_log.md`.
    ACCUMULATION → domain-level shared `_run_log.md` (multiple declarations under
    one domain share the log; entries identify themselves by slug).
    MAINTENANCE → the shared audit log doubles as the run log per D10.
    """
    if decl.shape == RecurrenceShape.MAINTENANCE:
        return "/workspace/_shared/back-office-audit.md"
    return f"{resolve_substrate_root(decl)}/_run_log.md"


def resolve_feedback_path(decl: RecurrenceDeclaration) -> Optional[str]:
    """Return the feedback file path per ADR-231 D2.

    DELIVERABLE → per-declaration `_feedback.md`.
    ACCUMULATION → per-domain `_feedback.md` (already canonical per ADR-181).
    ACTION → None (outcomes ARE the feedback signal per ADR-195).
    MAINTENANCE → None (back-office is system-authored, no operator feedback).
    """
    if decl.shape in (RecurrenceShape.DELIVERABLE, RecurrenceShape.ACCUMULATION):
        return f"{resolve_substrate_root(decl)}/_feedback.md"
    return None


def resolve_intent_path(decl: RecurrenceDeclaration) -> Optional[str]:
    """Return the optional `_intent.md` path for operator prose context.

    Always returns a path for non-MAINTENANCE shapes; the file may not exist
    on disk (it's optional). MAINTENANCE returns None — back-office is
    system-authored, no operator prose surface.
    """
    if decl.shape == RecurrenceShape.MAINTENANCE:
        return None
    return f"{resolve_substrate_root(decl)}/_intent.md"


def resolve_steering_path(decl: RecurrenceDeclaration) -> Optional[str]:
    """Return the YARNNN-authored `_steering.md` path.

    Mirrors `_intent.md` shape but is YARNNN-authored cycle-specific
    management notes per ADR-149. Same shape semantics — present for
    judgment-bearing shapes, absent for MAINTENANCE.
    """
    if decl.shape == RecurrenceShape.MAINTENANCE:
        return None
    return f"{resolve_substrate_root(decl)}/_steering.md"


def resolve_working_scratch_path(decl: RecurrenceDeclaration) -> str:
    """Return the per-declaration ephemeral scratch directory per ADR-231 D9.

    Scratch is invocation-scoped, NOT Agent-scoped — a researcher Agent
    assigned to two recurrences gets two scratch dirs. This isolates
    mid-invocation state across firings and across declarations.

    Trailing slash is included so callers can append filenames directly.
    """
    if decl.shape == RecurrenceShape.DELIVERABLE:
        return f"/workspace/reports/{decl.slug}/working/"
    if decl.shape == RecurrenceShape.ACCUMULATION:
        domain = decl.domain
        if not domain:
            raise ValueError(
                f"ACCUMULATION declaration '{decl.slug}' missing domain — "
                f"cannot resolve working scratch path"
            )
        # Sub-keyed by recurrence slug because multiple recurrences share the domain
        return f"/workspace/context/{domain}/working/{decl.slug}/"
    if decl.shape == RecurrenceShape.ACTION:
        return f"/workspace/operations/{decl.slug}/working/"
    if decl.shape == RecurrenceShape.MAINTENANCE:
        return f"/workspace/_shared/working/{decl.slug}/"
    raise ValueError(f"unknown shape: {decl.shape}")


# ---------------------------------------------------------------------------
# Convenience aggregate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedPaths:
    """Bundle of every path the dispatcher needs for one firing.

    Built once per dispatch entry. `output_path` and `output_folder` are
    None for shapes that don't have filesystem outputs (ACCUMULATION,
    ACTION). `feedback_path`, `intent_path`, `steering_path` are None for
    shapes that don't carry those affordances.
    """

    substrate_root: str
    output_path: Optional[str]
    output_folder: Optional[str]
    run_log_path: str
    feedback_path: Optional[str]
    intent_path: Optional[str]
    steering_path: Optional[str]
    working_scratch: str


def resolve_paths(
    decl: RecurrenceDeclaration,
    started_at: Optional[datetime] = None,
) -> ResolvedPaths:
    """Build a ResolvedPaths bundle for one firing.

    Single entry point the dispatcher uses to get all per-firing paths.
    Shape-aware: optional fields are None when the shape doesn't carry the
    affordance.
    """
    substrate_root = resolve_substrate_root(decl)

    if decl.shape == RecurrenceShape.DELIVERABLE:
        output_path: Optional[str] = resolve_output_path(decl, started_at=started_at)
        output_folder: Optional[str] = resolve_output_folder(decl, started_at=started_at)
    elif decl.shape == RecurrenceShape.MAINTENANCE:
        # MAINTENANCE has an output_path (the audit log) but no per-firing folder
        output_path = resolve_output_path(decl, started_at=started_at)
        output_folder = None
    else:
        # ACCUMULATION + ACTION: no output_path, no output_folder
        output_path = None
        output_folder = None

    return ResolvedPaths(
        substrate_root=substrate_root,
        output_path=output_path,
        output_folder=output_folder,
        run_log_path=resolve_run_log_path(decl),
        feedback_path=resolve_feedback_path(decl),
        intent_path=resolve_intent_path(decl),
        steering_path=resolve_steering_path(decl),
        working_scratch=resolve_working_scratch_path(decl),
    )


__all__ = [
    "DATE_FOLDER_FORMAT",
    "ResolvedPaths",
    "resolve_substrate_root",
    "resolve_output_path",
    "resolve_output_folder",
    "resolve_run_log_path",
    "resolve_feedback_path",
    "resolve_intent_path",
    "resolve_steering_path",
    "resolve_working_scratch_path",
    "resolve_paths",
]
