"""
Revision Routing — ADR-170 Phase 4.

Revision is composition with diff (RD-3):
  First run: compose from scratch.
  Subsequent runs: compose with prior manifest → detect stale sections →
  regenerate only what changed.

Four revision types (from narrowest to broadest scope):

  presentation  → reorder/restyle index.html. No regeneration, no re-render.
                  (Not yet wired — future Phase 6 concern)

  section       → one or more section partials stale (source files updated
                  after the section was produced). Regenerate stale sections
                  only, preserve current ones.

  asset         → derivative asset's source data updated. Re-render the asset.
                  Root asset fetched anew. No section regeneration.
                  (Tracked in manifest; full re-fetch deferred to Phase 5)

  full          → no prior manifest, or all sections stale, or first run.
                  Treat as a fresh compose — regenerate everything.

ADR-170 RD-3: "Revision and composition are the same operation with different
inputs." This module classifies WHICH input differs and scopes the work.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Revision scope dataclass
# =============================================================================

@dataclass
class RevisionScope:
    """What needs to be (re)generated on this run.

    stale_sections: section slugs that need regeneration (subset of all sections)
    current_sections: section slugs that are current — their partials can be reused
    revision_type: "full" | "section" | "asset" | "none"
    reason: human-readable explanation (logged, surfaced in manifest)
    """
    revision_type: str                    # "full" | "section" | "asset" | "none"
    stale_sections: list[str]             # slugs of sections that need regeneration
    current_sections: list[str]           # slugs of sections that are current
    reason: str                           # e.g. "2/5 sections stale: executive-summary, recent-signals"
    all_slugs: list[str] = field(default_factory=list)        # all declared section slugs (stale + current)
    forced_sections: list[str] = field(default_factory=list)  # slugs forced stale by steering

    @property
    def needs_generation(self) -> bool:
        """True if any prose regeneration is needed."""
        return self.revision_type in ("full", "section")

    @property
    def is_full_run(self) -> bool:
        return self.revision_type == "full"

    @property
    def is_section_scoped(self) -> bool:
        return self.revision_type == "section"

    @property
    def is_current(self) -> bool:
        """True if nothing needs regeneration (all sections up to date)."""
        return self.revision_type == "none"


# =============================================================================
# Revision classifier
# =============================================================================

def classify_revision_scope(
    prior_manifest,          # SysManifest | None
    page_structure: list[dict],
    domain_state: dict,
    forced_sections: Optional[list[str]] = None,
) -> RevisionScope:
    """Classify what needs regeneration given the prior manifest and current domain state.

    Args:
        prior_manifest: SysManifest from prior run, or None for first run
        page_structure: Task type page_structure (list of section defs)
        domain_state: Current domain state from _query_domain_state()
        forced_sections: Optional list of section slugs to force stale, regardless of
            manifest or domain freshness. Set when TP uses ManageTask(action="steer",
            target_section=...) — ADR-170 Gap 1.

    Returns:
        RevisionScope describing what to regenerate and why.

    Logic:
    - No prior manifest → full run (first run or manifest lost)
    - All sections stale → full run (avoids partial generation overhead)
    - No sections stale → none (skip generation, reuse prior output)
    - Some sections stale → section-scoped (regenerate stale only)
    - forced_sections → those slugs are always stale (section or full depending on overlap)
    """
    from services.compose.assembly import _slug, _domain_from_path, _path_matches_pattern

    # ADR-170 Gap 1: TP section-level steering override.
    # forced_sections are always stale regardless of manifest or domain state.
    forced_set = set(forced_sections or [])

    if not prior_manifest:
        all_slugs = [_slug(s["title"]) for s in page_structure]
        return RevisionScope(
            revision_type="full",
            stale_sections=all_slugs,
            current_sections=[],
            reason="No prior manifest — first run or manifest unavailable",
            all_slugs=all_slugs,
            forced_sections=list(forced_set),
        )

    if not page_structure:
        return RevisionScope(
            revision_type="full",
            stale_sections=[],
            current_sections=[],
            reason="No page_structure declared — full run",
            all_slugs=[],
            forced_sections=list(forced_set),
        )

    stale = []
    current = []

    for section_def in page_structure:
        title = section_def.get("title", "")
        slug = _slug(title)

        # ADR-170 Gap 1: TP-forced sections are always stale.
        if slug in forced_set:
            stale.append(slug)
            continue

        # Check manifest staleness (source files updated after section produced)
        if prior_manifest.is_section_stale(slug):
            stale.append(slug)
        else:
            # Also check if domain state has newer data than manifest domain_freshness
            reads_from = section_def.get("reads_from", [])
            entity_pattern = section_def.get("entity_pattern")
            domain_keys = set()

            for path_pattern in reads_from:
                dk = _domain_from_path(path_pattern)
                if dk:
                    domain_keys.add(dk)
            if entity_pattern:
                dk = _domain_from_path(entity_pattern)
                if dk:
                    domain_keys.add(dk)

            # Compare domain latest_updated_at vs manifest domain_freshness
            domain_stale = False
            for dk in domain_keys:
                current_freshness = domain_state.get(dk, {}).get("latest_updated_at", "")
                manifest_freshness = prior_manifest.domain_freshness.get(dk, "")
                if current_freshness and manifest_freshness and current_freshness > manifest_freshness:
                    domain_stale = True
                    break

            if domain_stale:
                stale.append(slug)
            else:
                current.append(slug)

    all_slugs = stale + current

    if not stale:
        return RevisionScope(
            revision_type="none",
            stale_sections=[],
            current_sections=current,
            reason="All sections current — no domain changes since last run",
            all_slugs=all_slugs,
            forced_sections=list(forced_set),
        )

    if not current:
        return RevisionScope(
            revision_type="full",
            stale_sections=stale,
            current_sections=[],
            reason=f"All {len(stale)} sections stale — full regeneration",
            all_slugs=all_slugs,
            forced_sections=list(forced_set),
        )

    forced_note = f" ({len(forced_set)} TP-forced)" if forced_set else ""
    return RevisionScope(
        revision_type="section",
        stale_sections=stale,
        current_sections=current,
        reason=(
            f"{len(stale)}/{len(all_slugs)} sections stale{forced_note}: "
            + ", ".join(stale)
        ),
        all_slugs=all_slugs,
        forced_sections=list(forced_set),
    )


def build_revision_brief(
    revision_scope: RevisionScope,
    prior_manifest,
    page_structure: list[dict],
) -> str:
    """Build a revision-aware preamble to prepend to the generation brief.

    Only called when revision_type == "section" (partial regeneration).
    Tells the LLM which sections to rewrite and which to leave verbatim.

    The current sections are listed explicitly so the LLM can output them
    unchanged (copied from the prior run's section partial content).

    Returns an empty string for full runs (no preamble needed — generate fresh).
    """
    if not revision_scope.is_section_scoped:
        return ""

    lines = [
        "## Revision Mode",
        f"**{revision_scope.reason}**",
        "",
        "This is a targeted revision, not a full regeneration. Instructions:",
        "",
    ]

    if revision_scope.stale_sections:
        lines.append(
            f"**Rewrite these sections** (source data has changed): "
            + ", ".join(f"`{s}`" for s in revision_scope.stale_sections)
        )

    if revision_scope.current_sections:
        lines.append(
            f"**Preserve these sections verbatim** (no source changes): "
            + ", ".join(f"`{s}`" for s in revision_scope.current_sections)
        )

    lines += [
        "",
        "For preserved sections: output the section header and content exactly as before. "
        "Do not paraphrase, summarize, or improve. Exact reproduction only.",
        "For rewritten sections: apply full analysis and generation as usual.",
    ]

    return "\n".join(lines)


def get_prior_section_content(
    section_slug: str,
    prior_sections_parsed: dict,
) -> str:
    """Retrieve prior section content for injection into preserved sections.

    Used when revision_type == "section" to inject prior partial content
    into the LLM context so it can reproduce it verbatim.

    Args:
        section_slug: Slug of the section to retrieve
        prior_sections_parsed: Dict from parse_draft_into_sections() on prior output

    Returns:
        Section content string, or empty string if not found.
    """
    sec = prior_sections_parsed.get(section_slug, {})
    return sec.get("content", "")
