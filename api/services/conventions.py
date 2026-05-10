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
      output:        /workspace/reports/{slug}/{date}/output.md
      output html:   /workspace/reports/{slug}/{date}/output.html
      sections:      /workspace/reports/{slug}/{date}/sections/
      manifest:      /workspace/reports/{slug}/{date}/manifest.json
      latest:        /workspace/reports/{slug}/latest/
      feedback:      /workspace/reports/{slug}/_feedback.md
      run log:       /workspace/reports/{slug}/_run_log.md
      working:       /workspace/reports/{slug}/working/

    Context (ACCUMULATION-shaped, additive entity files):
      domain root:   /workspace/context/{domain}/
      entity (md):   /workspace/context/{domain}/{entity}.md
      entity (yml):  /workspace/context/{domain}/{entity}.yaml
      synthesis:     /workspace/context/{domain}/_<name>.md
      feedback:      /workspace/context/{domain}/_feedback.md
      performance:   /workspace/context/{domain}/_performance.md
      run log:       /workspace/context/{domain}/_run_log.md

    Operations (ACTION-shaped, no filesystem output — outcomes via
    domain _performance.md):
      ops root:      /workspace/operations/{slug}/
      run log:       /workspace/operations/{slug}/_run_log.md
      working:       /workspace/operations/{slug}/working/

    Recurrences (canonical declarations file per ADR-261 D2):
      single file:   /workspace/_recurrences.yaml

    Reviewer substrate:
      identity:      /workspace/review/IDENTITY.md
      principles:    /workspace/review/principles.md (prose)
      principles:    /workspace/review/_principles.yaml (machine-parsed thresholds)
      decisions:     /workspace/review/decisions.md (append-only)
      reflections:   /workspace/review/reflections.md (append-only)

    Operator authored shared substrate:
      mandate:       /workspace/_shared/MANDATE.md
      identity:      /workspace/_shared/IDENTITY.md
      brand:         /workspace/_shared/BRAND.md
      autonomy:      /workspace/_shared/AUTONOMY.md (prose)
      autonomy:      /workspace/_shared/_autonomy.yaml (machine-parsed)
      conventions:   /workspace/_shared/CONVENTIONS.md
      precedent:     /workspace/_shared/PRECEDENT.md

    Memory (YARNNN-authored, in-session, ADR-156):
      notes:         /workspace/memory/notes.md
      conversation:  /workspace/memory/conversation.md
      recent:        /workspace/memory/recent.md  (back-office narrative digest)

    Specs (operator-authored output specs cited by recurrence prompts,
    ADR-262 D2 Pattern (ii)):
      spec:          /workspace/specs/{name}.md

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

# Canonical recurrences file (ADR-261 D2)
RECURRENCES_PATH = "/workspace/_recurrences.yaml"


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
    return f"/workspace/reports/{slug}"


def report_dated_folder(slug: str, when: Optional[datetime] = None) -> str:
    """The folder holding one firing's output bundle: ``output.md``,
    ``output.html``, ``sections/``, ``manifest.json``."""
    return f"/workspace/reports/{slug}/{_date_token(when)}"


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
    return f"/workspace/reports/{slug}/latest"


def report_feedback_path(slug: str) -> str:
    """Per-report feedback file (ADR-181)."""
    return f"/workspace/reports/{slug}/_feedback.md"


def report_run_log_path(slug: str) -> str:
    """Per-report append-only run log."""
    return f"/workspace/reports/{slug}/_run_log.md"


def report_working_dir(slug: str) -> str:
    """Per-report ephemeral scratch directory."""
    return f"/workspace/reports/{slug}/working"


# ---------------------------------------------------------------------------
# Context domains — ACCUMULATION-shaped substrate
# ---------------------------------------------------------------------------


def domain_root(domain: str) -> str:
    """Per-domain context root."""
    return f"/workspace/context/{domain}"


def domain_entity_path(domain: str, entity: str, ext: str = "md") -> str:
    """Per-entity file inside a domain.

    ``ext`` defaults to ``md`` (prose) but should be ``yaml`` for
    structured records per the file-format discipline (CLAUDE.md item 9).
    """
    return f"/workspace/context/{domain}/{entity}.{ext}"


def domain_synthesis_path(domain: str, name: str) -> str:
    """Cross-entity synthesis file (underscore-prefixed)."""
    return f"/workspace/context/{domain}/_{name}.md"


def domain_feedback_path(domain: str) -> str:
    """Per-domain feedback file (ADR-181, ADR-151)."""
    return f"/workspace/context/{domain}/_feedback.md"


def domain_performance_path(domain: str) -> str:
    """Per-domain money-truth substrate (ADR-195 v2)."""
    return f"/workspace/context/{domain}/_performance.md"


def domain_run_log_path(domain: str) -> str:
    """Per-domain shared run log (multiple recurrences in one domain
    write to the same log; entries identify by slug)."""
    return f"/workspace/context/{domain}/_run_log.md"


# ---------------------------------------------------------------------------
# Operations — ACTION-shaped substrate
# ---------------------------------------------------------------------------


def operation_root(slug: str) -> str:
    """Per-operation root. Action recurrences have no filesystem output —
    the platform side-effect IS the work, with outcomes flowing into the
    relevant domain's ``_performance.md`` per ADR-195."""
    return f"/workspace/operations/{slug}"


def operation_run_log_path(slug: str) -> str:
    return f"/workspace/operations/{slug}/_run_log.md"


def operation_working_dir(slug: str) -> str:
    return f"/workspace/operations/{slug}/working"


# ---------------------------------------------------------------------------
# Reviewer substrate (ADR-194 v2)
# ---------------------------------------------------------------------------

REVIEW_IDENTITY_PATH = "/workspace/review/IDENTITY.md"
REVIEW_PRINCIPLES_PROSE_PATH = "/workspace/review/principles.md"
REVIEW_PRINCIPLES_YAML_PATH = "/workspace/review/_principles.yaml"
REVIEW_DECISIONS_PATH = "/workspace/review/decisions.md"
REVIEW_REFLECTIONS_PATH = "/workspace/review/reflections.md"


# ---------------------------------------------------------------------------
# Operator-authored shared substrate
# ---------------------------------------------------------------------------

SHARED_MANDATE_PATH = "/workspace/_shared/MANDATE.md"
SHARED_IDENTITY_PATH = "/workspace/_shared/IDENTITY.md"
SHARED_BRAND_PATH = "/workspace/_shared/BRAND.md"
SHARED_AUTONOMY_PROSE_PATH = "/workspace/_shared/AUTONOMY.md"
SHARED_AUTONOMY_YAML_PATH = "/workspace/_shared/_autonomy.yaml"
SHARED_CONVENTIONS_PATH = "/workspace/_shared/CONVENTIONS.md"
SHARED_PRECEDENT_PATH = "/workspace/_shared/PRECEDENT.md"


# ---------------------------------------------------------------------------
# Memory (YARNNN-authored, in-session, ADR-156 + ADR-159)
# ---------------------------------------------------------------------------

MEMORY_NOTES_PATH = "/workspace/memory/notes.md"
MEMORY_CONVERSATION_PATH = "/workspace/memory/conversation.md"
MEMORY_RECENT_PATH = "/workspace/memory/recent.md"


# ---------------------------------------------------------------------------
# Specs (operator-authored output specs, ADR-262 D2 Pattern (ii))
# ---------------------------------------------------------------------------


def spec_path(name: str) -> str:
    """Operator-authored spec doc cited by recurrence prompts."""
    return f"/workspace/specs/{name}.md"


__all__ = [
    "DATE_FOLDER_FORMAT",
    "RECURRENCES_PATH",
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
    # Context
    "domain_root",
    "domain_entity_path",
    "domain_synthesis_path",
    "domain_feedback_path",
    "domain_performance_path",
    "domain_run_log_path",
    # Operations
    "operation_root",
    "operation_run_log_path",
    "operation_working_dir",
    # Reviewer substrate
    "REVIEW_IDENTITY_PATH",
    "REVIEW_PRINCIPLES_PROSE_PATH",
    "REVIEW_PRINCIPLES_YAML_PATH",
    "REVIEW_DECISIONS_PATH",
    "REVIEW_REFLECTIONS_PATH",
    # Operator-authored shared substrate
    "SHARED_MANDATE_PATH",
    "SHARED_IDENTITY_PATH",
    "SHARED_BRAND_PATH",
    "SHARED_AUTONOMY_PROSE_PATH",
    "SHARED_AUTONOMY_YAML_PATH",
    "SHARED_CONVENTIONS_PATH",
    "SHARED_PRECEDENT_PATH",
    # Memory
    "MEMORY_NOTES_PATH",
    "MEMORY_CONVERSATION_PATH",
    "MEMORY_RECENT_PATH",
    # Specs
    "spec_path",
]
