"""ADR-302 D5 + D6 — Typed section registry for the Reviewer persona-frame.

The persona-frame at `api/agents/reviewer_agent.py::_PERSONA_FRAME` is the
single most-read LLM-facing artifact in YARNNN canon. Drift in it compounds
at every Reviewer wake.

Pre-ADR-302, the persona-frame was a single ~500-line Python string. Adding
new canon over time produced stratigraphic guidance — three generations of
contradictory claims stacked on top of each other about whether the Reviewer
can write to operator-substrate files. The model read all three and had to
guess the most recent layer. See `docs/evaluations/2026-05-26-152500-failed-
action-substrate-blindspot/findings.md` for the failed-WriteFile pattern that
surfaced this drift.

This module is the **structural enforcement mechanism** for "one canonical
place per concern" — ADR-302 D5. The typing + naming + DANGEROUS_ prefix
discipline are inspired by Claude Code's `constants/systemPromptSections.ts`
(snapshot at `docs/analysis/src_claudeCC/`) but derived for YARNNN's
substrate model. See `docs/analysis/claude-code-prompt-discipline-comparison-
2026-05-26.md` for first-principles justification.

Three core elements per ADR-302 D5/D6:

1. `PersonaFrameSection` — named, computed, cache-tagged. Sections are
   registered objects, not string positions. Adding a second section with
   the same name surfaces in the registry rather than hiding in 500 lines
   of prose.

2. `persona_frame_section(name, compute)` — the cached default. Computed
   once at module load, stable across wakes. Use this for static content:
   axiom citations, write-authority declaration, anti-patterns, identity.

3. `DANGEROUS_uncached_persona_frame_section(name, compute, reason)` — the
   volatile variant. Required `reason` argument documents the justification
   for cache-busting in code. Use this ONLY for content that legitimately
   varies per wake (operating-context block per ADR-274; future analogous
   per-wake content). The DANGEROUS_ prefix is intentional friction.

Plus `resolve_persona_frame_sections(sections)` — assembly helper used by
`reviewer_agent.py::_build_system_prompt()` to render the registry into
the final prompt body.

What this module does NOT do (deliberate scope):
- Does not export the prompt itself. `_PERSONA_FRAME_SECTIONS` lives in
  `reviewer_agent.py` where the per-section compute functions are defined.
- Does not implement runtime cache invalidation. Sections are resolved
  once at module load; deploy triggers re-load. Same as the existing
  `_SYSTEM_PROMPT_CACHE` pattern in `reviewer_agent.py`.
- Does not enforce boundary marker ordering at runtime. The discipline is
  declarative — comments in the registry + reviewer judgment at PR time.
  Same pattern as Claude Code's `=== BOUNDARY MARKER ===` comment in
  `constants/prompts.ts:572`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


# ---------------------------------------------------------------------------
# Core types (ADR-302 D5)
# ---------------------------------------------------------------------------

#: A section's compute function takes no arguments and returns the section's
#: text body. Sections that need runtime data (e.g., operating-context with
#: live timestamps) close over the data source in their compute closure.
ComputeFn = Callable[[], str]


@dataclass(frozen=True)
class PersonaFrameSection:
    """A named, cache-tagged unit of persona-frame content.

    Frozen because sections are declared once at module load and are
    structural artifacts — mutation would invalidate the "one canonical
    place per concern" discipline. To change a section, replace it in the
    registry; don't mutate it in place.

    Fields:
        name: canonical identifier. One per concern. Adding a second
            section with the same name is the drift signal the discipline
            exists to surface.
        compute: produces the section's text body. Called at registry
            resolution time. May close over module-level constants
            (e.g., DEFAULT_REVIEWER_WRITE_LOCKS per ADR-302 D2) so the
            section content templates from canon rather than paraphrasing.
        cache_break: True for volatile sections that must recompute per
            wake. False for cached defaults (the vast majority). When True,
            the section bypasses any prompt cache the consumer maintains.
    """

    name: str
    compute: ComputeFn
    cache_break: bool


def persona_frame_section(name: str, compute: ComputeFn) -> PersonaFrameSection:
    """Construct a cached section. The default — use this unless you have
    a documented reason for per-wake recomputation.

    Cached sections are computed once at module load and reused across all
    Reviewer wakes within a deploy. This is the right default because
    canon evolves at deploy boundaries, not within a wake.
    """
    return PersonaFrameSection(name=name, compute=compute, cache_break=False)


def DANGEROUS_uncached_persona_frame_section(
    name: str,
    compute: ComputeFn,
    reason: str,
) -> PersonaFrameSection:
    """Construct a volatile section that recomputes every wake.

    The DANGEROUS_ prefix is intentional friction. An author who wants
    per-wake recomputation has to consciously type the prefix AND supply
    a `reason` argument documenting why cache-break is necessary. The
    `reason` lives in code so future reviewers can audit whether the
    cache-break is still warranted.

    Use ONLY when the section's content MUST reflect per-wake state that
    didn't exist at module-load time. Current legitimate use:
    - operating-context block per ADR-274 (now/timezone/market-state)

    Reject for everything else. Per-wake recomputation costs prompt cache
    hits and adds re-billing across every Reviewer loop round.

    The `reason` is captured but NOT used at runtime — it's pure
    documentation for the next reader.
    """
    # `reason` is structurally required to force conscious cache-break
    # decisions. It is not currently stored on PersonaFrameSection because
    # the dataclass is frozen + the reason is documented at the call site;
    # if future tooling needs runtime access (e.g., a logging audit of
    # which sections cache-break), add a `reason` field then.
    _ = reason  # explicit: argument captured, not stored
    return PersonaFrameSection(name=name, compute=compute, cache_break=True)


# ---------------------------------------------------------------------------
# Registry resolution (ADR-302 D5 assembly helper)
# ---------------------------------------------------------------------------

def resolve_persona_frame_sections(
    sections: list[PersonaFrameSection],
) -> str:
    """Resolve a registry of sections into the final prompt body.

    Iterates in order, calls each section's `compute()`, joins with the
    standard double-newline separator. Empty/None section content is
    skipped (a section that computes to "" or None contributes nothing
    to the prompt — useful for conditionally-empty sections).

    Duplicate section names raise ValueError — the singular-implementation
    discipline enforced at runtime. If you genuinely need two sections
    that contribute related content, name them distinctly
    (`anti_patterns_substrate` and `anti_patterns_discipline`, not two
    `anti_patterns` entries).

    The boundary marker discipline (ADR-302 D6) is NOT enforced at
    runtime — section ordering is the caller's responsibility, surfaced
    through the registry's declarative ordering + the
    `=== BOUNDARY MARKER ===` comment convention at the call site.
    """
    seen_names: set[str] = set()
    parts: list[str] = []
    for section in sections:
        if section.name in seen_names:
            raise ValueError(
                f"Duplicate persona-frame section name: {section.name!r}. "
                "One canonical place per concern (ADR-302 D1) — rename "
                "one or merge."
            )
        seen_names.add(section.name)
        body = section.compute()
        if body:
            parts.append(body)
    return "\n\n".join(parts)
