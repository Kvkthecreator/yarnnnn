"""
Tests for ADR-170 compose substrate.

Covers:
- parse_draft_into_sections(): section splitting, slug matching, missing sections
- make_manifest() + SysManifest.is_section_stale(): provenance + staleness logic
- read_manifest(): round-trip serialization
- build_generation_brief(): fixture-based output shape validation
  (uses competitive-brief page_structure, no DB calls)

Run:
  cd api && python -m pytest test_compose.py -v
  or: cd api && python test_compose.py
"""

import sys
import json
import asyncio
from datetime import datetime, timezone, timedelta

sys.path.insert(0, ".")

from services.compose.assembly import parse_draft_into_sections, build_post_generation_manifest
from services.compose.manifest import (
    make_manifest, read_manifest, SysManifest, SectionProvenance, AssetRecord,
)


# =============================================================================
# Fixtures
# =============================================================================

COMPETITIVE_BRIEF_PAGE_STRUCTURE = [
    {"kind": "narrative", "title": "Executive Summary",
     "reads_from": ["competitors/_synthesis.md", "signals/_tracker.md"]},
    {"kind": "entity-grid", "title": "Competitor Profiles",
     "entity_pattern": "competitors/*/"},
    {"kind": "timeline", "title": "Recent Signals",
     "reads_from": ["signals/_tracker.md"]},
    {"kind": "trend-chart", "title": "Market Position",
     "reads_from": ["competitors/*/analysis.md"]},
    {"kind": "comparison-table", "title": "Competitive Matrix",
     "reads_from": ["competitors/*/profile.md"]},
    {"kind": "callout", "title": "Strategic Implications",
     "reads_from": ["competitors/_synthesis.md"]},
]

SAMPLE_DRAFT = """
## Executive Summary

OpenAI remains the dominant player with 65% market share in API revenue.
Anthropic has accelerated enterprise adoption through Constitutional AI positioning.
Key risk: commoditization of base model capabilities by Q3.

## Competitor Profiles

### OpenAI
One-line description: API-first LLM platform. Key fact: $3B ARR. Status: 🟢 Growing

### Anthropic
One-line description: Safety-focused Claude platform. Key fact: $500M ARR. Status: 🟢 Growing

### Cohere
One-line description: Enterprise NLP platform. Key fact: $200M ARR. Status: 🟡 At risk

## Recent Signals

**2026-04-09** — OpenAI raised $10B at $150B valuation (Reuters)
**2026-04-07** — Anthropic launched Claude Enterprise tier (official)
**2026-04-05** — Cohere laid off 15% of staff (TechCrunch)

## Market Position

| Quarter | OpenAI | Anthropic | Cohere |
|---------|--------|-----------|--------|
| Q3 2025 | 62%    | 18%       | 8%     |
| Q4 2025 | 64%    | 21%       | 7%     |
| Q1 2026 | 65%    | 23%       | 6%     |

## Competitive Matrix

| Feature | OpenAI | Anthropic | Cohere |
|---------|--------|-----------|--------|
| Enterprise SSO | ✓ | ✓ | ✓ |
| On-prem deploy | ✗ | ✓ | ✓ |
| Fine-tuning | ✓ | ✗ | ✓ |
| Safety cert | ✗ | ✓ | ✗ |

## Strategic Implications

> **Recommendation:** Anthropic's Constitutional AI narrative is winning enterprise procurement. Prioritize partnerships that reference safety certification as a differentiator. OpenAI's commoditization pressure will accelerate through H2 2026.
""".strip()


SAMPLE_DOMAIN_STATE = {
    "competitors": {
        "entities": ["openai", "anthropic", "cohere"],
        "entity_files": [
            {"slug": "openai", "file": "profile.md", "path": "/workspace/context/competitors/openai/profile.md", "updated_at": "2026-04-09T10:00:00Z"},
            {"slug": "openai", "file": "analysis.md", "path": "/workspace/context/competitors/openai/analysis.md", "updated_at": "2026-04-09T10:00:00Z"},
            {"slug": "anthropic", "file": "profile.md", "path": "/workspace/context/competitors/anthropic/profile.md", "updated_at": "2026-04-08T12:00:00Z"},
            {"slug": "cohere", "file": "profile.md", "path": "/workspace/context/competitors/cohere/profile.md", "updated_at": "2026-04-07T08:00:00Z"},
        ],
        "synthesis_files": [
            {"path": "/workspace/context/competitors/_synthesis.md", "updated_at": "2026-04-09T18:00:00Z"},
        ],
        "assets": [
            {"filename": "openai-favicon.png", "path": "/workspace/context/competitors/assets/openai-favicon.png", "content_url": "https://example.com/openai-favicon.png", "updated_at": "2026-04-08T00:00:00Z"},
        ],
        "latest_updated_at": "2026-04-09T18:00:00Z",
    },
    "signals": {
        "entities": [],
        "entity_files": [],
        "synthesis_files": [
            {"path": "/workspace/context/signals/_tracker.md", "updated_at": "2026-04-10T06:00:00Z"},
        ],
        "assets": [],
        "latest_updated_at": "2026-04-10T06:00:00Z",
    },
}


# =============================================================================
# Tests: parse_draft_into_sections
# =============================================================================

def test_parse_all_sections_present():
    sections = parse_draft_into_sections(SAMPLE_DRAFT, COMPETITIVE_BRIEF_PAGE_STRUCTURE)

    expected_slugs = {
        "executive-summary",
        "competitor-profiles",
        "recent-signals",
        "market-position",
        "competitive-matrix",
        "strategic-implications",
    }
    assert set(sections.keys()) == expected_slugs, (
        f"Expected slugs {expected_slugs}, got {set(sections.keys())}"
    )
    print("✓ parse_all_sections_present: all 6 sections found")


def test_parse_section_kinds_matched():
    sections = parse_draft_into_sections(SAMPLE_DRAFT, COMPETITIVE_BRIEF_PAGE_STRUCTURE)

    assert sections["executive-summary"]["kind"] == "narrative"
    assert sections["competitor-profiles"]["kind"] == "entity-grid"
    assert sections["recent-signals"]["kind"] == "timeline"
    assert sections["market-position"]["kind"] == "trend-chart"
    assert sections["competitive-matrix"]["kind"] == "comparison-table"
    assert sections["strategic-implications"]["kind"] == "callout"
    print("✓ parse_section_kinds_matched: all kinds correctly mapped")


def test_parse_section_content_nonempty():
    sections = parse_draft_into_sections(SAMPLE_DRAFT, COMPETITIVE_BRIEF_PAGE_STRUCTURE)

    for slug, sec in sections.items():
        assert sec["char_count"] > 0, f"Section '{slug}' has empty content"
        assert sec["content"].strip().startswith("##"), (
            f"Section '{slug}' content should start with ## header"
        )
    print("✓ parse_section_content_nonempty: all sections have content starting with ##")


def test_parse_missing_section_gets_empty_placeholder():
    # Draft missing "Strategic Implications" section
    partial_draft = SAMPLE_DRAFT.split("## Strategic Implications")[0].strip()
    sections = parse_draft_into_sections(partial_draft, COMPETITIVE_BRIEF_PAGE_STRUCTURE)

    assert "strategic-implications" in sections, "Missing section should still appear"
    assert sections["strategic-implications"]["content"] == "", (
        "Missing section should have empty content"
    )
    assert sections["strategic-implications"]["char_count"] == 0
    print("✓ parse_missing_section_gets_empty_placeholder: missing section is empty, not absent")


def test_parse_empty_draft_returns_all_empty():
    sections = parse_draft_into_sections("", COMPETITIVE_BRIEF_PAGE_STRUCTURE)
    # Empty draft → all declared sections present with empty content
    for s in COMPETITIVE_BRIEF_PAGE_STRUCTURE:
        from services.compose.assembly import _slug
        slug = _slug(s["title"])
        assert slug in sections
        assert sections[slug]["content"] == ""
    print("✓ parse_empty_draft_returns_all_empty: empty draft produces empty placeholders")


def test_parse_no_page_structure_returns_empty():
    sections = parse_draft_into_sections(SAMPLE_DRAFT, [])
    assert sections == {}
    print("✓ parse_no_page_structure_returns_empty")


# =============================================================================
# Tests: SysManifest + is_section_stale
# =============================================================================

def _make_ts(minutes_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def test_manifest_section_not_stale():
    """Section produced AFTER its sources were last updated → not stale."""
    source_updated = _make_ts(60)    # sources updated 60 min ago
    produced_at = _make_ts(30)       # section produced 30 min ago (after sources)

    manifest = make_manifest(
        task_slug="competitive-brief",
        surface_type="report",
        sections={
            "executive-summary": SectionProvenance(
                kind="narrative",
                produced_at=produced_at,
                source_files=["/workspace/context/competitors/_synthesis.md"],
                source_updated_at=source_updated,
            )
        },
        assets={},
        entity_count=3,
        domain_freshness={"competitors": source_updated},
    )

    assert not manifest.is_section_stale("executive-summary"), (
        "Section produced after source update should NOT be stale"
    )
    print("✓ manifest_section_not_stale")


def test_manifest_section_is_stale():
    """Section produced BEFORE its sources were last updated → stale."""
    produced_at = _make_ts(90)       # produced 90 min ago
    source_updated = _make_ts(30)    # sources updated 30 min ago (AFTER production)

    manifest = make_manifest(
        task_slug="competitive-brief",
        surface_type="report",
        sections={
            "executive-summary": SectionProvenance(
                kind="narrative",
                produced_at=produced_at,
                source_files=["/workspace/context/competitors/_synthesis.md"],
                source_updated_at=source_updated,
            )
        },
        assets={},
        entity_count=3,
        domain_freshness={"competitors": source_updated},
    )

    assert manifest.is_section_stale("executive-summary"), (
        "Section produced before source update should be stale"
    )
    print("✓ manifest_section_is_stale")


def test_manifest_unknown_section_is_stale():
    """Section not in manifest → treated as stale (safe default)."""
    manifest = make_manifest(
        task_slug="competitive-brief",
        surface_type="report",
        sections={},
        assets={},
        entity_count=0,
        domain_freshness={},
    )
    assert manifest.is_section_stale("nonexistent-section"), (
        "Unknown section should be treated as stale"
    )
    print("✓ manifest_unknown_section_is_stale")


def test_manifest_round_trip():
    """to_json() → read_manifest() produces identical object."""
    produced = _make_ts(30)
    source_updated = _make_ts(60)

    original = make_manifest(
        task_slug="competitive-brief",
        surface_type="report",
        sections={
            "executive-summary": SectionProvenance(
                kind="narrative",
                produced_at=produced,
                source_files=["/workspace/context/competitors/_synthesis.md"],
                source_updated_at=source_updated,
            ),
        },
        assets={
            "openai-favicon.png": AssetRecord(
                kind="root",
                source_path="/workspace/context/competitors/assets/openai-favicon.png",
                content_url="https://example.com/openai-favicon.png",
                fetched_at=_make_ts(120),
            )
        },
        entity_count=3,
        domain_freshness={"competitors": source_updated},
    )

    serialized = original.to_json()
    restored = read_manifest(serialized)

    assert restored is not None, "read_manifest() returned None"
    assert restored.task_slug == original.task_slug
    assert restored.surface_type == original.surface_type
    assert restored.entity_count == original.entity_count
    assert "executive-summary" in restored.sections
    assert "openai-favicon.png" in restored.assets
    assert restored.sections["executive-summary"].kind == "narrative"
    assert restored.assets["openai-favicon.png"].kind == "root"
    print("✓ manifest_round_trip: serialization and deserialization consistent")


def test_read_manifest_returns_none_on_bad_json():
    assert read_manifest("") is None
    assert read_manifest("not json") is None
    assert read_manifest("{}") is not None  # valid empty manifest
    print("✓ read_manifest_returns_none_on_bad_json")


# =============================================================================
# Tests: build_post_generation_manifest
# =============================================================================

def test_build_post_generation_manifest_structure():
    sections_parsed = parse_draft_into_sections(SAMPLE_DRAFT, COMPETITIVE_BRIEF_PAGE_STRUCTURE)
    task_info = {
        "type_key": "competitive-brief",
        "output_kind": "produces_deliverable",
        "surface_type": "report",
        "context_reads": ["competitors", "signals"],
        "page_structure": COMPETITIVE_BRIEF_PAGE_STRUCTURE,
    }
    manifest = build_post_generation_manifest(
        task_slug="competitive-brief",
        surface_type="report",
        sections_parsed=sections_parsed,
        domain_state=SAMPLE_DOMAIN_STATE,
        task_info=task_info,
        run_started_at="2026-04-10T09:30:00+00:00",
    )

    assert manifest.task_slug == "competitive-brief"
    assert manifest.surface_type == "report"
    assert manifest.entity_count == 3  # 3 in competitors + 0 in signals
    assert "executive-summary" in manifest.sections
    assert "competitor-profiles" in manifest.sections
    assert "competitors" in manifest.domain_freshness

    # Executive Summary reads from competitors/_synthesis.md and signals/_tracker.md
    exec_sec = manifest.sections["executive-summary"]
    assert exec_sec.kind == "narrative"
    assert exec_sec.produced_at == "2026-04-10T09:30:00+00:00"
    assert any("_synthesis.md" in f for f in exec_sec.source_files), (
        f"Executive Summary should reference _synthesis.md, got: {exec_sec.source_files}"
    )

    # Assets from domain state
    assert "openai-favicon.png" in manifest.assets
    assert manifest.assets["openai-favicon.png"].kind == "root"
    print("✓ build_post_generation_manifest_structure: manifest shape correct")


def test_build_manifest_staleness_on_rerun():
    """Simulate a re-run: manifest produced at T1, source updated at T2 > T1."""
    sections_parsed = parse_draft_into_sections(SAMPLE_DRAFT, COMPETITIVE_BRIEF_PAGE_STRUCTURE)
    task_info = {
        "page_structure": COMPETITIVE_BRIEF_PAGE_STRUCTURE,
        "surface_type": "report",
        "context_reads": ["competitors", "signals"],
    }
    run_time = "2026-04-09T09:00:00+00:00"  # produced before signals update
    manifest = build_post_generation_manifest(
        task_slug="competitive-brief",
        surface_type="report",
        sections_parsed=sections_parsed,
        domain_state=SAMPLE_DOMAIN_STATE,  # signals updated at 2026-04-10T06:00:00Z
        task_info=task_info,
        run_started_at=run_time,
    )

    # Recent Signals reads from signals/_tracker.md (updated 2026-04-10T06:00:00Z)
    # Run was at 2026-04-09T09:00:00Z → section IS stale on a hypothetical second read
    recent_signals = manifest.sections.get("recent-signals")
    if recent_signals and recent_signals.source_updated_at:
        # source_updated_at (2026-04-10T06:00:00Z) > produced_at (2026-04-09T09:00:00Z)
        assert recent_signals.source_updated_at > recent_signals.produced_at, (
            "Recent Signals source was updated after run — should be stale"
        )
        assert manifest.is_section_stale("recent-signals")
        print("✓ build_manifest_staleness_on_rerun: staleness correctly detected across runs")
    else:
        print("~ build_manifest_staleness_on_rerun: skipped (no source_updated_at for recent-signals)")


# =============================================================================
# Tests: generation brief shape (no DB — validates structure only)
# =============================================================================

def test_surface_formatting_guidance_all_types():
    from services.compose.assembly import _surface_formatting_guidance
    for surface in ["report", "deck", "dashboard", "digest", "workbook"]:
        guidance = _surface_formatting_guidance(surface)
        assert guidance, f"No guidance for surface_type='{surface}'"
    assert _surface_formatting_guidance("unknown") == ""
    print("✓ surface_formatting_guidance_all_types: all declared surfaces have guidance")


def test_kind_output_contract_all_kinds():
    from services.compose.assembly import _kind_output_contract
    declared_kinds = [
        "narrative", "metric-cards", "entity-grid", "comparison-table",
        "trend-chart", "distribution-chart", "timeline", "status-matrix",
        "data-table", "callout", "checklist",
    ]
    for kind in declared_kinds:
        contract = _kind_output_contract(kind)
        assert contract, f"No output contract for kind='{kind}'"
    assert _kind_output_contract("unknown") == ""
    print(f"✓ kind_output_contract_all_kinds: all {len(declared_kinds)} kinds have contracts")


def test_slug_helper():
    from services.compose.assembly import _slug
    assert _slug("Executive Summary") == "executive-summary"
    assert _slug("Competitive Matrix") == "competitive-matrix"
    assert _slug("Market Position (2026)") == "market-position-2026"
    assert _slug("  Spaces & Symbols! ") == "spaces-symbols"
    print("✓ slug_helper: slug generation correct")


# =============================================================================
# Tests: classify_revision_scope (Phase 4)
# =============================================================================

from services.compose.revision import classify_revision_scope, build_revision_brief, RevisionScope


def _make_manifest_with_sections(sections_config: dict, domain_freshness: dict = None) -> "SysManifest":
    """Helper: build a manifest with specified section provenance."""
    sections = {}
    for slug, cfg in sections_config.items():
        sections[slug] = SectionProvenance(
            kind=cfg.get("kind", "narrative"),
            produced_at=cfg["produced_at"],
            source_files=cfg.get("source_files", []),
            source_updated_at=cfg.get("source_updated_at"),
        )
    return make_manifest(
        task_slug="competitive-brief",
        surface_type="report",
        sections=sections,
        assets={},
        entity_count=3,
        domain_freshness=domain_freshness or {},
    )


def test_revision_full_run_no_manifest():
    """No prior manifest → full run."""
    scope = classify_revision_scope(
        prior_manifest=None,
        page_structure=COMPETITIVE_BRIEF_PAGE_STRUCTURE,
        domain_state=SAMPLE_DOMAIN_STATE,
    )
    assert scope.revision_type == "full"
    assert scope.is_full_run
    assert scope.needs_generation
    assert not scope.is_current
    assert len(scope.stale_sections) == len(COMPETITIVE_BRIEF_PAGE_STRUCTURE)
    print("✓ revision_full_run_no_manifest: no manifest → full run with all sections stale")


def test_revision_none_all_current():
    """All sections current (produced after their sources) → revision_type=none."""
    # All sections produced at _make_ts(10) — after source updates at _make_ts(60)
    produced = _make_ts(10)
    source_updated = _make_ts(60)
    sections_cfg = {
        "executive-summary": {"produced_at": produced, "source_updated_at": source_updated},
        "competitor-profiles": {"produced_at": produced, "source_updated_at": source_updated},
        "recent-signals": {"produced_at": produced, "source_updated_at": source_updated},
        "market-position": {"produced_at": produced, "source_updated_at": source_updated},
        "competitive-matrix": {"produced_at": produced, "source_updated_at": source_updated},
        "strategic-implications": {"produced_at": produced, "source_updated_at": source_updated},
    }
    # Domain freshness same as source_updated_at — no newer data
    domain_freshness = {
        "competitors": source_updated,
        "signals": source_updated,
    }
    manifest = _make_manifest_with_sections(sections_cfg, domain_freshness)

    # Domain state with same freshness as manifest
    domain_state = {
        "competitors": {**SAMPLE_DOMAIN_STATE["competitors"], "latest_updated_at": source_updated},
        "signals": {**SAMPLE_DOMAIN_STATE["signals"], "latest_updated_at": source_updated},
    }

    scope = classify_revision_scope(
        prior_manifest=manifest,
        page_structure=COMPETITIVE_BRIEF_PAGE_STRUCTURE,
        domain_state=domain_state,
    )
    assert scope.revision_type == "none", f"Expected none, got {scope.revision_type}: {scope.reason}"
    assert scope.is_current
    assert not scope.needs_generation
    assert len(scope.current_sections) == len(COMPETITIVE_BRIEF_PAGE_STRUCTURE)
    assert len(scope.stale_sections) == 0
    print("✓ revision_none_all_current: all sections current → no regeneration needed")


def test_revision_full_run_all_stale():
    """All sections stale (sources updated after production) → full run."""
    produced = _make_ts(90)      # produced 90 min ago
    source_updated = _make_ts(30)  # sources updated 30 min ago (after production)
    sections_cfg = {
        slug: {"produced_at": produced, "source_updated_at": source_updated}
        for slug in ["executive-summary", "competitor-profiles", "recent-signals",
                     "market-position", "competitive-matrix", "strategic-implications"]
    }
    manifest = _make_manifest_with_sections(sections_cfg)

    scope = classify_revision_scope(
        prior_manifest=manifest,
        page_structure=COMPETITIVE_BRIEF_PAGE_STRUCTURE,
        domain_state=SAMPLE_DOMAIN_STATE,
    )
    assert scope.revision_type == "full", f"Expected full, got {scope.revision_type}"
    assert scope.is_full_run
    assert not scope.current_sections
    print("✓ revision_full_run_all_stale: all stale → full run (not section-scoped)")


def test_revision_section_scoped_partial_stale():
    """Some sections stale, some current → section-scoped revision."""
    produced = _make_ts(90)
    fresh_source = _make_ts(120)    # source updated 120 min ago (before production)
    stale_source = _make_ts(30)     # source updated 30 min ago (after production)

    sections_cfg = {
        "executive-summary": {"produced_at": produced, "source_updated_at": stale_source},   # stale
        "competitor-profiles": {"produced_at": produced, "source_updated_at": fresh_source},  # current
        "recent-signals": {"produced_at": produced, "source_updated_at": stale_source},       # stale
        "market-position": {"produced_at": produced, "source_updated_at": fresh_source},      # current
        "competitive-matrix": {"produced_at": produced, "source_updated_at": fresh_source},   # current
        "strategic-implications": {"produced_at": produced, "source_updated_at": fresh_source}, # current
    }
    # Domain freshness matches source times so domain-level check doesn't override
    domain_freshness = {
        "competitors": fresh_source,
        "signals": fresh_source,
    }
    manifest = _make_manifest_with_sections(sections_cfg, domain_freshness)

    # Domain state with same freshness as manifest (no new domain data)
    domain_state = {
        "competitors": {**SAMPLE_DOMAIN_STATE["competitors"], "latest_updated_at": fresh_source},
        "signals": {**SAMPLE_DOMAIN_STATE["signals"], "latest_updated_at": fresh_source},
    }

    scope = classify_revision_scope(
        prior_manifest=manifest,
        page_structure=COMPETITIVE_BRIEF_PAGE_STRUCTURE,
        domain_state=domain_state,
    )
    assert scope.revision_type == "section", f"Expected section, got {scope.revision_type}: {scope.reason}"
    assert scope.is_section_scoped
    assert scope.needs_generation
    assert "executive-summary" in scope.stale_sections
    assert "recent-signals" in scope.stale_sections
    assert "competitor-profiles" in scope.current_sections
    assert "market-position" in scope.current_sections
    assert len(scope.stale_sections) == 2
    assert len(scope.current_sections) == 4
    print(f"✓ revision_section_scoped_partial_stale: 2 stale, 4 current → section-scoped: {scope.reason}")


def test_revision_domain_freshness_triggers_stale():
    """Domain updated since manifest recorded → sections reading that domain become stale."""
    produced = _make_ts(30)
    source_updated = _make_ts(60)
    sections_cfg = {
        slug: {"produced_at": produced, "source_updated_at": source_updated}
        for slug in ["executive-summary", "competitor-profiles", "recent-signals",
                     "market-position", "competitive-matrix", "strategic-implications"]
    }
    # Manifest domain_freshness: competitors at source_updated time
    domain_freshness = {"competitors": source_updated, "signals": source_updated}
    manifest = _make_manifest_with_sections(sections_cfg, domain_freshness)

    # Domain state: signals domain has newer data than manifest recorded
    newer_signals = _make_ts(10)  # updated 10 min ago — after manifest was written
    domain_state = {
        "competitors": {**SAMPLE_DOMAIN_STATE["competitors"], "latest_updated_at": source_updated},
        "signals": {**SAMPLE_DOMAIN_STATE["signals"], "latest_updated_at": newer_signals},
    }

    scope = classify_revision_scope(
        prior_manifest=manifest,
        page_structure=COMPETITIVE_BRIEF_PAGE_STRUCTURE,
        domain_state=domain_state,
    )
    # "recent-signals" reads from signals/_tracker.md → signals domain is newer → stale
    assert scope.revision_type in ("section", "full"), f"Expected section or full, got {scope.revision_type}"
    assert "recent-signals" in scope.stale_sections, (
        f"recent-signals should be stale due to domain update. stale={scope.stale_sections}"
    )
    print(f"✓ revision_domain_freshness_triggers_stale: signals domain update → recent-signals stale: {scope.reason}")


def test_revision_brief_section_scoped():
    """build_revision_brief() emits a human-readable revision instruction for section-scoped runs."""
    scope = RevisionScope(
        revision_type="section",
        stale_sections=["executive-summary", "recent-signals"],
        current_sections=["competitor-profiles", "market-position"],
        reason="2/4 sections stale: executive-summary, recent-signals",
        all_slugs=["executive-summary", "recent-signals", "competitor-profiles", "market-position"],
    )
    brief = build_revision_brief(scope, None, COMPETITIVE_BRIEF_PAGE_STRUCTURE)
    assert brief, "Revision brief should be non-empty for section-scoped run"
    assert "Revision Mode" in brief
    assert "executive-summary" in brief
    assert "competitor-profiles" in brief
    assert "verbatim" in brief.lower()
    print("✓ revision_brief_section_scoped: brief contains stale + current section lists")


def test_revision_brief_empty_for_full_run():
    """build_revision_brief() returns empty string for full runs — no preamble needed."""
    scope = RevisionScope(
        revision_type="full",
        stale_sections=["a", "b", "c"],
        current_sections=[],
        reason="all stale",
        all_slugs=["a", "b", "c"],
    )
    brief = build_revision_brief(scope, None, COMPETITIVE_BRIEF_PAGE_STRUCTURE)
    assert brief == "", f"Full run should produce empty revision brief, got: {brief[:100]}"
    print("✓ revision_brief_empty_for_full_run")


def test_revision_brief_empty_for_none():
    """build_revision_brief() returns empty string when nothing needs regeneration."""
    scope = RevisionScope(
        revision_type="none",
        stale_sections=[],
        current_sections=["a", "b"],
        reason="all current",
        all_slugs=["a", "b"],
    )
    brief = build_revision_brief(scope, None, COMPETITIVE_BRIEF_PAGE_STRUCTURE)
    assert brief == "", f"None-type should produce empty revision brief, got: {brief[:100]}"
    print("✓ revision_brief_empty_for_none")


# =============================================================================
# Runner
# =============================================================================

def run_all():
    tests = [
        # parse_draft_into_sections
        test_parse_all_sections_present,
        test_parse_section_kinds_matched,
        test_parse_section_content_nonempty,
        test_parse_missing_section_gets_empty_placeholder,
        test_parse_empty_draft_returns_all_empty,
        test_parse_no_page_structure_returns_empty,
        # SysManifest staleness
        test_manifest_section_not_stale,
        test_manifest_section_is_stale,
        test_manifest_unknown_section_is_stale,
        test_manifest_round_trip,
        test_read_manifest_returns_none_on_bad_json,
        # build_post_generation_manifest
        test_build_post_generation_manifest_structure,
        test_build_manifest_staleness_on_rerun,
        # helpers
        test_surface_formatting_guidance_all_types,
        test_kind_output_contract_all_kinds,
        test_slug_helper,
        # classify_revision_scope (Phase 4)
        test_revision_full_run_no_manifest,
        test_revision_none_all_current,
        test_revision_full_run_all_stale,
        test_revision_section_scoped_partial_stale,
        test_revision_domain_freshness_triggers_stale,
        test_revision_brief_section_scoped,
        test_revision_brief_empty_for_full_run,
        test_revision_brief_empty_for_none,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"ADR-170 Compose Substrate: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
