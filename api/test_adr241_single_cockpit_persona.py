"""
ADR-241 regression gate — single cockpit persona.

Asserts eight invariants for the Reviewer-into-TP collapse landed in
ADR-241 (Round 5 step of the ADR-236 frontend cockpit coherence pass).

**Amended by ADR-244 Phase 2 (2026-05-01)**: the canonical decisions
parser relocated from `web/lib/reviewer-decisions.ts` to
`web/lib/content-shapes/decisions.ts` per ADR-244 D3 content-shape
registry. Path constants + import-string assertions in this gate
updated accordingly. The semantic invariants (parser exports
parseDecisions + aggregateReviewerCalibration; DecisionsStream imports
the canonical parser) are unchanged — only the path moved.

Same Python-test-over-TS-source pattern as ADR-237 / ADR-238 / ADR-239 /
ADR-240 (no JS test runner today; see ADR-236 Rule 3).

Run via:
    python -m pytest api/test_adr241_single_cockpit_persona.py -v

Or as a standalone script:
    python api/test_adr241_single_cockpit_persona.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WEB_DECISIONS_STREAM = REPO_ROOT / "web" / "components" / "work" / "details" / "DecisionsStream.tsx"
WEB_REVIEWER_DIR = REPO_ROOT / "web" / "components" / "agents" / "reviewer"
WEB_AGENT_ROSTER = REPO_ROOT / "web" / "components" / "agents" / "AgentRosterSurface.tsx"
WEB_AGENTS_PAGE = REPO_ROOT / "web" / "app" / "(authenticated)" / "agents" / "page.tsx"
WEB_AGENT_CONTENT = REPO_ROOT / "web" / "components" / "agents" / "AgentContentView.tsx"
API_REVIEWER_AUDIT = REPO_ROOT / "api" / "services" / "reviewer_audit.py"
WEB_LIB_REVIEWER = REPO_ROOT / "web" / "lib" / "content-shapes" / "decisions.ts"


def _read(p: Path) -> str:
    if not p.exists():
        raise AssertionError(f"Missing file: {p.relative_to(REPO_ROOT)}")
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test gate
# ---------------------------------------------------------------------------

def test_decisions_stream_relocated_to_work():
    """Assertion #1: web/components/work/details/DecisionsStream.tsx
    exists and exports DecisionsStream (relocated from /agents/reviewer/
    per ADR-241 D3)."""
    src = _read(WEB_DECISIONS_STREAM)
    assert "export function DecisionsStream(" in src, (
        "DecisionsStream.tsx must export DecisionsStream per ADR-241 D3."
    )


def test_reviewer_directory_deleted():
    """Assertion #2: web/components/agents/reviewer/ directory does not
    exist. Regression guard against re-creation of the deleted Reviewer
    surface namespace per ADR-241 §"Files deleted"."""
    assert not WEB_REVIEWER_DIR.exists(), (
        f"web/components/agents/reviewer/ must NOT exist — deleted by "
        f"ADR-241. Surface collapsed into Thinking Partner detail view."
    )


def test_agent_roster_surface_deleted():
    """Assertion #3: web/components/agents/AgentRosterSurface.tsx does
    not exist. Regression guard — /agents redirects directly to TP detail
    per ADR-241 D1; the roster is dead UX."""
    assert not WEB_AGENT_ROSTER.exists(), (
        "AgentRosterSurface.tsx must NOT exist — deleted by ADR-241 D1. "
        "Singular Implementation: roster surface and direct-detail "
        "landing cannot coexist."
    )


def test_agents_page_redirects_to_thinking_partner():
    """Assertion #4: /agents (no query param) redirects to
    ?agent=thinking-partner per ADR-241 D1."""
    src = _read(WEB_AGENTS_PAGE)
    assert "/agents?agent=thinking-partner" in src, (
        "agents/page.tsx must redirect to ?agent=thinking-partner when "
        "no agent param is set per ADR-241 D1."
    )


def test_agent_content_view_no_reviewer_dispatch():
    """Assertion #5: AgentContentView.tsx no longer dispatches to
    ReviewerDetailView. The reviewer branch is now a redirect to
    TP's Principles tab per ADR-241 D3 + R1."""
    src = _read(WEB_AGENT_CONTENT)
    assert "ReviewerDetailView" not in src, (
        "AgentContentView.tsx must NOT reference ReviewerDetailView "
        "(dispatch component deleted by ADR-241). Reviewer branch is "
        "now a redirect to ?agent=thinking-partner&tab=principles."
    )
    # The redirect target must be present.
    assert "agent=thinking-partner&tab=principles" in src, (
        "AgentContentView.tsx reviewer branch must redirect to "
        "TP's Principles tab per ADR-241 D3 + R1."
    )


def test_reviewer_audit_substrate_preserved():
    """Assertion #6: services/reviewer_audit.py exists and continues
    to write to /workspace/review/decisions.md. Substrate preservation
    regression guard per ADR-241 §"Preserves" (ADR-194 v2 substrate
    paths unchanged)."""
    src = _read(API_REVIEWER_AUDIT)
    assert "review/decisions.md" in src, (
        "reviewer_audit.py must continue to reference "
        "/workspace/review/decisions.md per ADR-194 v2 substrate "
        "preservation. ADR-241 changes the surface, not the substrate."
    )


def test_canonical_parser_preserved():
    """Assertion #7: the canonical decisions shape module continues to
    export parseDecisions and aggregateReviewerCalibration.

    **Amended by ADR-244 Phase 2**: module relocated to
    `web/lib/content-shapes/decisions.ts`. `parse` is the canonical
    export; `parseDecisions` is the back-compat alias
    (`export const parseDecisions = parse;`). Both function-form and
    alias-const-form are valid public exports."""
    src = _read(WEB_LIB_REVIEWER)
    assert (
        "export function parseDecisions" in src
        or "export const parseDecisions" in src
    ), (
        "decisions shape module must continue to export parseDecisions "
        "(function or const alias) — ADR-239 D1 preserved by ADR-241."
    )
    assert "export function aggregateReviewerCalibration" in src, (
        "decisions shape module must continue to export "
        "aggregateReviewerCalibration (ADR-239 D2 preserved by ADR-241)."
    )


def test_decisions_stream_uses_canonical_parser():
    """Assertion #8: DecisionsStream.tsx imports parseDecisions from
    @/lib/content-shapes/decisions. Singular Implementation: one parser, one
    canonical home."""
    src = _read(WEB_DECISIONS_STREAM)
    assert "from '@/lib/content-shapes/decisions'" in src, (
        "DecisionsStream.tsx must import from @/lib/content-shapes/decisions "
        "per ADR-241 Singular Implementation discipline."
    )
    assert "parseDecisions" in src, (
        "DecisionsStream.tsx must use the canonical parseDecisions parser."
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_decisions_stream_relocated_to_work,
        test_reviewer_directory_deleted,
        test_agent_roster_surface_deleted,
        test_agents_page_redirects_to_thinking_partner,
        test_agent_content_view_no_reviewer_dispatch,
        test_reviewer_audit_substrate_preserved,
        test_canonical_parser_preserved,
        test_decisions_stream_uses_canonical_parser,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} ADR-241 assertions passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
