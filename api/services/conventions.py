"""
Workspace Filesystem Conventions — ADR-262 D1.

Slug-templated path interpolation. Replaces the deleted
`recurrence_paths.py` per-shape dispatch with a flat conventions
surface every caller can use directly.

Conventions live as **operator-readable markdown** in
`/workspace/_shared/CONVENTIONS.md` (per ADR-262 D1). This Python
module is the call-site mirror of that markdown — both must be kept
in sync. When CONVENTIONS.md changes, this module changes too.

The convention shapes (per ADR-262 D1):

    Reports (DELIVERABLE-shaped output, replacive per firing):
      output:        /workspace/operation/reports/{slug}/{date}/output.md
      output html:   /workspace/operation/reports/{slug}/{date}/output.html
      sections:      /workspace/operation/reports/{slug}/{date}/sections/
      manifest:      /workspace/operation/reports/{slug}/{date}/manifest.json
      latest:        /workspace/operation/reports/{slug}/latest/
      feedback:      /workspace/operation/reports/{slug}/_feedback.md
      run log:       /workspace/operation/reports/{slug}/_run_log.md
      working:       /workspace/operation/reports/{slug}/working/

    Authored pieces (the published artifact — operator-canonical prose +
    on-demand composition substrate, per ADR-333 + ADR-283):
      piece root:    /workspace/operation/authored/{slug}/
      prose source:  /workspace/operation/authored/{slug}/content.md  (operator-canonical)
      profile:       /workspace/operation/authored/{slug}/profile.md
      composition:   /workspace/operation/authored/{slug}/{date}/sections/
      section map:   /workspace/operation/authored/{slug}/{date}/sys_manifest.json
      asset manifest:/workspace/operation/authored/{slug}/{date}/manifest.json
      (The composed HTML is a lazy projection pulled at consumption — never
      persisted as a file. content.md is the source; sections/ + assets are
      the produced composition substrate; HTML is the view. ADR-333.)

    Context (ACCUMULATION-shaped, additive entity files):
      domain root:    /workspace/operation/{domain}/
      entity (md):    /workspace/operation/{domain}/{entity}.md
      entity (yml):   /workspace/operation/{domain}/{entity}.yaml
      synthesis:      /workspace/operation/{domain}/_<name>.md
      feedback:       /workspace/operation/{domain}/_feedback.md
      ground-truth:   /workspace/operation/{domain}/_<ground-truth-instance>.md
                      (bundle-instance-named; alpha-trader: `_money_truth.md`)
      run log:        /workspace/operation/{domain}/_run_log.md

    Operations (ACTION-shaped, no filesystem output — outcomes flow into
    the relevant domain's ground-truth substrate per FOUNDATIONS Axiom 8):
      ops root:      /workspace/operation/operations/{slug}/
      run log:       /workspace/operation/operations/{slug}/_run_log.md
      working:       /workspace/operation/operations/{slug}/working/

    Recurrences (canonical declarations file per ADR-261 D2):
      single file:   /workspace/_recurrences.yaml

    Reviewer substrate (ADR-194 v2; ADR-256 unified reflection outputs
    into the judgment log; ADR-281 §5 renamed decisions.md → judgment_log.md):
      identity:       /workspace/persona/IDENTITY.md
      principles:     /workspace/persona/principles.md (prose)
      principles:     /workspace/persona/_principles.yaml (machine-parsed thresholds)
      judgment_log:   /workspace/persona/judgment_log.md (system-rendered append-only)

    Operator-authored shared substrate (ADR-206 + ADR-217 relocated
    `_shared/` to `constitution/ + governance/ + operation/ (ADR-320 split of legacy _shared/)`): see
    ``services.workspace_paths.CONSTITUTION_FILES`` — that module is
    the sole source of truth for kernel-seeded path constants. This
    module deliberately does not duplicate them; importing both would
    create two sources of truth.

    Specs (operator-authored output specs cited by recurrence prompts,
    ADR-262 D2 Pattern (ii)):
      spec:          /workspace/operation/specs/{name}.md

ADR-262 §D1 sub-clause: conventional paths are slug-templated
structurally. The slug, the date, the entity, the domain are
substrate-level data — never free-form Reviewer output. This
module enforces that by accepting only structured arguments.

Date format: ``%Y-%m-%dT%H%M`` to preserve cross-cutover continuity
of dated output folders. Same as the legacy ``DATE_FOLDER_FORMAT``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

DATE_FOLDER_FORMAT = "%Y-%m-%dT%H%M"

# Canonical recurrences file (ADR-261 D2) — the AGENT's judgment scheduling.
# A recurrence is a judgment prompt served by the wake funnel (services.wake).
RECURRENCES_PATH = "/workspace/_recurrences.yaml"

# Canonical captures file (ADR-393) — deterministic intake declarations
# (connector captures, ground-truth state mirrors, perception watches,
# substrate mirrors). Run by the capture lane (services.capture), OUTSIDE the
# wake funnel. Sibling to _recurrences.yaml; the two are cleanly separated —
# _recurrences.yaml is judgment cadence, _captures.yaml is mechanical intake.
CAPTURES_PATH = "/workspace/_captures.yaml"


# ---------------------------------------------------------------------------
# Date helper
# ---------------------------------------------------------------------------


def _date_token(when: Optional[datetime]) -> str:
    """Render a datetime as the dated-folder token, or the literal ``{date}``
    placeholder when ``when`` is None (useful for declaration-time references
    and tests).
    """
    return when.strftime(DATE_FOLDER_FORMAT) if when is not None else "{date}"


# ---------------------------------------------------------------------------
# Reports — DELIVERABLE-shaped substrate
# ---------------------------------------------------------------------------


def report_root(slug: str) -> str:
    """Per-report root directory (parent of dated folders + ancillary files)."""
    return f"/workspace/operation/reports/{slug}"


def report_dated_folder(slug: str, when: Optional[datetime] = None) -> str:
    """The folder holding one firing's output bundle: ``output.md``,
    ``output.html``, ``sections/``, ``manifest.json``."""
    return f"/workspace/operation/reports/{slug}/{_date_token(when)}"


def report_output_path(slug: str, when: Optional[datetime] = None) -> str:
    """The canonical markdown output for one firing."""
    return f"{report_dated_folder(slug, when)}/output.md"


def report_output_html_path(slug: str, when: Optional[datetime] = None) -> str:
    """The composed-HTML output for one firing (when Compose has run)."""
    return f"{report_dated_folder(slug, when)}/output.html"


def report_sections_dir(slug: str, when: Optional[datetime] = None) -> str:
    """Directory holding section partials. Presence of ``sections/*.md``
    triggers Compose by default per ADR-262 D4."""
    return f"{report_dated_folder(slug, when)}/sections"


def report_manifest_path(slug: str, when: Optional[datetime] = None) -> str:
    """Per-firing manifest: sections, assets, compose engine version,
    attribution."""
    return f"{report_dated_folder(slug, when)}/manifest.json"


def report_latest_dir(slug: str) -> str:
    """The 'latest' pointer folder (ADR-262 D1; symlink-equivalent)."""
    return f"/workspace/operation/reports/{slug}/latest"


def report_feedback_path(slug: str) -> str:
    """Per-report feedback file (ADR-181)."""
    return f"/workspace/operation/reports/{slug}/_feedback.md"


def report_run_log_path(slug: str) -> str:
    """Per-report append-only run log."""
    return f"/workspace/operation/reports/{slug}/_run_log.md"


def report_working_dir(slug: str) -> str:
    """Per-report ephemeral scratch directory."""
    return f"/workspace/operation/reports/{slug}/working"


# ---------------------------------------------------------------------------
# Authored pieces — the published artifact (ADR-333 + ADR-283)
#
# An authored piece is the operator's canonical prose (content.md) plus
# on-demand composition substrate (sections/ + manifests) produced when the
# Reviewer authors structure natively (ADR-333 D5). The composed HTML is a
# lazy projection pulled at the consumption boundary — never persisted here.
# The shape mirrors the report family so the root-agnostic composer
# (compose_task_output_html) serves both with one code path.
# ---------------------------------------------------------------------------


def authored_root(slug: str) -> str:
    """Per-piece root directory (parent of content.md, profile.md, and the
    dated composition folders)."""
    return f"/workspace/operation/authored/{slug}"


def authored_content_path(slug: str) -> str:
    """The operator-canonical prose source (ADR-283 — never a projection)."""
    return f"/workspace/operation/authored/{slug}/content.md"


def authored_profile_path(slug: str) -> str:
    """Per-piece profile (status, voice ref, cadence ref, audit state)."""
    return f"/workspace/operation/authored/{slug}/profile.md"


def authored_dated_folder(slug: str, when: Optional[datetime] = None) -> str:
    """The folder holding one composition's substrate bundle: ``sections/``,
    ``sys_manifest.json``, ``manifest.json``. No ``output.html`` — the HTML
    is pulled, never persisted (ADR-333)."""
    return f"/workspace/operation/authored/{slug}/{_date_token(when)}"


def authored_sections_dir(slug: str, when: Optional[datetime] = None) -> str:
    """Directory holding ``kind:``-tagged section partials the Reviewer wrote
    while authoring structure natively (ADR-333 D5)."""
    return f"{authored_dated_folder(slug, when)}/sections"


def authored_sys_manifest_path(slug: str, when: Optional[datetime] = None) -> str:
    """Per-composition section→kind map consumed by the composer."""
    return f"{authored_dated_folder(slug, when)}/sys_manifest.json"


def authored_manifest_path(slug: str, when: Optional[datetime] = None) -> str:
    """Per-composition asset manifest (designer-rendered chart/mermaid/image
    URLs with role tags)."""
    return f"{authored_dated_folder(slug, when)}/manifest.json"


# ---------------------------------------------------------------------------
# Context domains — ACCUMULATION-shaped substrate
# ---------------------------------------------------------------------------


def domain_root(domain: str) -> str:
    """Per-domain context root."""
    return f"/workspace/operation/{domain}"


def domain_entity_path(domain: str, entity: str, ext: str = "md") -> str:
    """Per-entity file inside a domain.

    ``ext`` defaults to ``md`` (prose) but should be ``yaml`` for
    structured records per the file-format discipline (CLAUDE.md item 9).
    """
    return f"/workspace/operation/{domain}/{entity}.{ext}"


def domain_synthesis_path(domain: str, name: str) -> str:
    """Cross-entity synthesis file (underscore-prefixed)."""
    return f"/workspace/operation/{domain}/_{name}.md"


def domain_feedback_path(domain: str) -> str:
    """Per-domain feedback file (ADR-181, ADR-151)."""
    return f"/workspace/operation/{domain}/_feedback.md"


def domain_run_log_path(domain: str) -> str:
    """Per-domain shared run log (multiple recurrences in one domain
    write to the same log; entries identify by slug)."""
    return f"/workspace/operation/{domain}/_run_log.md"


# ---------------------------------------------------------------------------
# Operations — ACTION-shaped substrate
# ---------------------------------------------------------------------------


def operation_root(slug: str) -> str:
    """Per-operation root. Action recurrences have no filesystem output —
    the platform side-effect IS the work, with outcomes flowing into the
    relevant domain's ground-truth substrate per FOUNDATIONS Axiom 8
    (alpha-trader instance: ``_money_truth.md`` per ADR-195 v2)."""
    return f"/workspace/operation/operations/{slug}"


def operation_run_log_path(slug: str) -> str:
    return f"/workspace/operation/operations/{slug}/_run_log.md"


def operation_working_dir(slug: str) -> str:
    return f"/workspace/operation/operations/{slug}/working"


# ---------------------------------------------------------------------------
# Reviewer substrate (ADR-194 v2)
#
# Note: ADR-256 unified reflection outputs into the judgment log. There is
# no separate reflections.md substrate. ADR-281 §5 renamed decisions.md →
# judgment_log.md; the canonical path constant lives in
# `services.workspace_paths.PERSONA_JUDGMENT_LOG_PATH` — this module's
# REVIEW_DECISIONS_PATH (parallel definition, zero importers) was deleted
# 2026-05-15 per Singular Implementation. Other REVIEW_* constants here
# remain as legacy /workspace/-prefixed convenience strings — if a future
# caller emerges these should be consolidated to workspace_paths.py too.
# ---------------------------------------------------------------------------

# ADR-320: the duplicate persona-path constants that lived here (zero importers)
# are DELETED. workspace_paths.py is the singular source for persona/* paths
# (PERSONA_IDENTITY_PATH, PERSONA_PRINCIPLES_PATH, PERSONA_PRINCIPLES_YAML_PATH).
# Import from there, never redefine here.


# ---------------------------------------------------------------------------
# Operator-authored shared substrate
#
# Source of truth: ``services.workspace_paths.CONSTITUTION_FILES``.
# This module deliberately does not duplicate those constants — the
# stale SHARED_*_PATH constants that pointed at /workspace/_shared/
# (pre-ADR-206 location) were deleted 2026-05-12. The MEMORY_*_PATH
# constants were also removed (zero importers; callers reference the
# paths directly).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Specs (operator-authored output specs, ADR-262 D2 Pattern (ii))
# ---------------------------------------------------------------------------


def spec_path(name: str) -> str:
    """Operator-authored spec doc cited by recurrence prompts."""
    return f"/workspace/operation/specs/{name}.md"


__all__ = [
    "DATE_FOLDER_FORMAT",
    "RECURRENCES_PATH",
    "CAPTURES_PATH",
    # Reports
    "report_root",
    "report_dated_folder",
    "report_output_path",
    "report_output_html_path",
    "report_sections_dir",
    "report_manifest_path",
    "report_latest_dir",
    "report_feedback_path",
    "report_run_log_path",
    "report_working_dir",
    # Authored pieces (ADR-333)
    "authored_root",
    "authored_content_path",
    "authored_profile_path",
    "authored_dated_folder",
    "authored_sections_dir",
    "authored_sys_manifest_path",
    "authored_manifest_path",
    # Context
    "domain_root",
    "domain_entity_path",
    "domain_synthesis_path",
    "domain_feedback_path",
    "domain_run_log_path",
    # Operations
    "operation_root",
    "operation_run_log_path",
    "operation_working_dir",
    # Specs
    "spec_path",
]
