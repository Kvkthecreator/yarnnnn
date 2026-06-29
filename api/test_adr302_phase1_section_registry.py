"""ADR-302 Phase 1 — Contract test for the typed section registry.

Verifies the structural foundation laid by `api/agents/freddie_agent_sections.py`:
- PersonaFrameSection dataclass is frozen + correctly typed
- persona_frame_section defaults to cached
- DANGEROUS_uncached_persona_frame_section produces volatile sections
- resolve_persona_frame_sections enforces singular-implementation (no
  duplicate section names) and concatenates with double-newline separator
- Empty/None compute results are skipped (contributes nothing to prompt)

These are unit-level contract tests. The post-implementation evaluation
re-run (per docs/evaluations/2026-05-26-163000-posture-criterion-declaration/)
measures behavioral effect against substrate.
"""

from __future__ import annotations

import pytest

from agents.freddie_agent_sections import (
    PersonaFrameSection,
    persona_frame_section,
    DANGEROUS_uncached_persona_frame_section,
    resolve_persona_frame_sections,
)


# ---------------------------------------------------------------------------
# T1: dataclass shape + immutability
# ---------------------------------------------------------------------------

def test_persona_frame_section_is_frozen():
    """Sections are structural artifacts — mutation would invalidate
    the 'one canonical place per concern' discipline."""
    s = persona_frame_section("test", lambda: "body")
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError depending on dataclass version
        s.name = "renamed"  # type: ignore[misc]


def test_persona_frame_section_carries_name_compute_cache_break():
    """All three fields are part of the canonical contract."""
    fn = lambda: "the body"
    s = persona_frame_section("identity", fn)
    assert s.name == "identity"
    assert s.compute is fn
    assert s.cache_break is False


# ---------------------------------------------------------------------------
# T2: cached default + DANGEROUS variant
# ---------------------------------------------------------------------------

def test_persona_frame_section_defaults_to_cached():
    """Cached is the default — cache_break=False unless explicitly volatile."""
    s = persona_frame_section("cached", lambda: "stable across wakes")
    assert s.cache_break is False


def test_DANGEROUS_uncached_variant_produces_volatile_section():
    """DANGEROUS_ variant produces cache_break=True."""
    s = DANGEROUS_uncached_persona_frame_section(
        "operating_context",
        lambda: "now: 2026-05-26T16:30Z",
        reason="ADR-274: per-wake now/timezone/market-state",
    )
    assert s.cache_break is True


def test_DANGEROUS_uncached_requires_reason_argument():
    """The reason argument is structurally required — TypeError on
    omission. This is the friction the discipline depends on."""
    with pytest.raises(TypeError):
        DANGEROUS_uncached_persona_frame_section(  # type: ignore[call-arg]
            "missing_reason",
            lambda: "body",
        )


# ---------------------------------------------------------------------------
# T3: resolver — concatenation + ordering + skip-empty
# ---------------------------------------------------------------------------

def test_resolver_concatenates_with_double_newline():
    sections = [
        persona_frame_section("a", lambda: "first"),
        persona_frame_section("b", lambda: "second"),
    ]
    result = resolve_persona_frame_sections(sections)
    assert result == "first\n\nsecond"


def test_resolver_preserves_section_order():
    sections = [
        persona_frame_section("alpha", lambda: "A"),
        persona_frame_section("beta", lambda: "B"),
        persona_frame_section("gamma", lambda: "C"),
    ]
    result = resolve_persona_frame_sections(sections)
    assert result.index("A") < result.index("B") < result.index("C")


def test_resolver_skips_empty_section_bodies():
    """Sections that compute to empty contribute nothing to the prompt.
    Used for conditionally-empty sections (e.g., a section that returns
    PRECEDENT content only when PRECEDENT.md is non-empty)."""
    sections = [
        persona_frame_section("a", lambda: "real content"),
        persona_frame_section("empty", lambda: ""),
        persona_frame_section("c", lambda: "more content"),
    ]
    result = resolve_persona_frame_sections(sections)
    assert result == "real content\n\nmore content"


# ---------------------------------------------------------------------------
# T4: duplicate-name enforcement (ADR-302 D1 at runtime)
# ---------------------------------------------------------------------------

def test_resolver_rejects_duplicate_section_names():
    """Duplicate names raise ValueError — singular-implementation
    discipline enforced at runtime. The error message cites the
    discipline (ADR-302 D1) to make the violation actionable."""
    sections = [
        persona_frame_section("identity", lambda: "first identity claim"),
        persona_frame_section("identity", lambda: "contradictory second claim"),
    ]
    with pytest.raises(ValueError) as excinfo:
        resolve_persona_frame_sections(sections)
    assert "Duplicate" in str(excinfo.value)
    assert "identity" in str(excinfo.value)
    assert "ADR-302" in str(excinfo.value)


# ---------------------------------------------------------------------------
# T5: cache_break is metadata only — resolver treats both equally
# ---------------------------------------------------------------------------

def test_resolver_treats_cached_and_uncached_uniformly():
    """The cache_break flag is metadata for the consumer (the system_prompt
    builder uses it to decide cache_control). The resolver itself doesn't
    differentiate — both kinds of sections contribute their body identically."""
    sections = [
        persona_frame_section("static", lambda: "stable"),
        DANGEROUS_uncached_persona_frame_section(
            "volatile",
            lambda: "per-wake",
            reason="test",
        ),
    ]
    result = resolve_persona_frame_sections(sections)
    assert "stable" in result
    assert "per-wake" in result
