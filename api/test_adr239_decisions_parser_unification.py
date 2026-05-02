"""
ADR-239 regression gate — decisions parser unification.

Asserts six invariants for the parser consolidation landed in ADR-239
(Round 3 of the ADR-236 frontend cockpit coherence pass).

**Amended by ADR-245 Phase 2 (2026-05-01)**: the canonical decisions
parser relocated from `web/lib/reviewer-decisions.ts` to
`web/lib/content-shapes/decisions.ts` per ADR-245 D3 content-shape
registry. Path constants + import-string assertions in this gate
updated accordingly. The semantic invariants (parser exports
parseDecisions + aggregateReviewerCalibration; PerformanceFace +
DecisionsStream import the canonical parser; no inline re-implementation)
are unchanged — only the path moved.

Same Python-test-over-TS-source pattern as ADR-237 / ADR-238 (no JS test
runner today; see ADR-236 Rule 3).

Run via:
    python -m pytest api/test_adr239_decisions_parser_unification.py -v

Or as a standalone script:
    python api/test_adr239_decisions_parser_unification.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WEB_LIB_REVIEWER = REPO_ROOT / "web" / "lib" / "content-shapes" / "decisions.ts"
WEB_PERFORMANCE_FACE = REPO_ROOT / "web" / "components" / "library" / "faces" / "PerformanceFace.tsx"
# ADR-241 D3 (2026-04-30) relocated the Stream consumer from
# web/components/agents/reviewer/DecisionsStreamPane.tsx to
# web/components/work/details/DecisionsStream.tsx. The canonical parser
# preservation invariant (ADR-239's concern) is unchanged; only the
# consumer's path moves. ADR-239 + ADR-241 cross-amendment — see
# ADR-241 §"Preserves" for the explicit invariant carry-over.
WEB_DECISIONS_PANE = REPO_ROOT / "web" / "components" / "work" / "details" / "DecisionsStream.tsx"
WEB_FACES_DIR = REPO_ROOT / "web" / "components" / "library" / "faces"


def _read(p: Path) -> str:
    if not p.exists():
        raise AssertionError(f"Missing file: {p.relative_to(REPO_ROOT)}")
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test gate
# ---------------------------------------------------------------------------

def test_reviewer_decisions_lib_exposes_aggregator_and_calibration_type():
    """Assertion #1: the canonical decisions shape module exposes the
    parser, the aggregator, and the calibration interface.

    **Amended by ADR-245 Phase 2**: module relocated to
    `web/lib/content-shapes/decisions.ts`. `parseDecisions` may be
    function-form OR alias-const-form (`export const parseDecisions = parse`)
    — both are valid public exports."""
    src = _read(WEB_LIB_REVIEWER)
    assert (
        "export function parseDecisions" in src
        or "export const parseDecisions" in src
    ), "decisions shape module missing export: parseDecisions (function or const alias)"
    for ex in [
        "export function aggregateReviewerCalibration",
        "export interface ReviewerCalibration",
    ]:
        assert ex in src, f"decisions shape module missing export: {ex}"


def test_performance_face_no_inline_parse_decisions():
    """Assertion #2: PerformanceFace.tsx no longer contains an inline
    `function parseDecisions(`. Regression guard against re-inlining."""
    src = _read(WEB_PERFORMANCE_FACE)
    assert "function parseDecisions(" not in src, (
        "PerformanceFace.tsx contains an inline parseDecisions function — "
        "Singular Implementation violation per ADR-239 D1. Import from "
        "@/lib/content-shapes/decisions instead."
    )


def test_performance_face_no_inline_calibration_interface():
    """Assertion #3: PerformanceFace.tsx no longer contains an inline
    `interface ReviewerCalibration {`. The interface lives in
    @/lib/content-shapes/decisions per ADR-239 D2."""
    src = _read(WEB_PERFORMANCE_FACE)
    assert "interface ReviewerCalibration {" not in src, (
        "PerformanceFace.tsx contains an inline ReviewerCalibration "
        "interface — Singular Implementation violation per ADR-239 D2. "
        "Import the type from @/lib/content-shapes/decisions."
    )


def test_performance_face_imports_from_reviewer_decisions_lib():
    """Assertion #4: PerformanceFace.tsx imports the canonical parser,
    aggregator, and type from @/lib/content-shapes/decisions."""
    src = _read(WEB_PERFORMANCE_FACE)
    assert "from '@/lib/content-shapes/decisions'" in src, (
        "PerformanceFace.tsx must import from @/lib/content-shapes/decisions "
        "per ADR-239 D1+D2."
    )
    for name in ("parseDecisions", "aggregateReviewerCalibration", "ReviewerCalibration"):
        assert name in src, (
            f"PerformanceFace.tsx must reference {name!r} via the "
            f"@/lib/content-shapes/decisions import."
        )


def test_no_legacy_task_path_drift_in_faces():
    """Assertion #5: Q5 path audit regression guard. None of the cockpit
    faces reference the legacy `/tasks/{slug}/outputs/` substrate path.
    Post-ADR-231 those paths moved to natural-home `/workspace/reports/`
    and `/workspace/context/` locations. Catches future drift if a face
    accidentally references the legacy task path."""
    forbidden_substrings = [
        "/tasks/{",
        "tasks/${",
    ]
    for face_file in sorted(WEB_FACES_DIR.glob("*.tsx")):
        src = face_file.read_text(encoding="utf-8")
        for forbidden in forbidden_substrings:
            assert forbidden not in src, (
                f"{face_file.relative_to(REPO_ROOT)} contains legacy task "
                f"path substring {forbidden!r} — substrate drift per "
                "ADR-231 D2/D3. Path migration required."
            )


def test_decisions_stream_still_uses_canonical_parser():
    """Assertion #6: DecisionsStream consumer continues to import
    parseDecisions from @/lib/content-shapes/decisions. Path moved in
    ADR-241 D3 (web/components/agents/reviewer/DecisionsStreamPane.tsx
    → web/components/work/details/DecisionsStream.tsx); the canonical
    parser preservation invariant is unchanged."""
    src = _read(WEB_DECISIONS_PANE)
    assert "from '@/lib/content-shapes/decisions'" in src, (
        "DecisionsStream.tsx must import from @/lib/content-shapes/decisions "
        "(canonical parser per ADR-239 D1, path per ADR-241 D3)."
    )
    assert "parseDecisions" in src, (
        "DecisionsStream.tsx must call parseDecisions from the "
        "canonical module."
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_reviewer_decisions_lib_exposes_aggregator_and_calibration_type,
        test_performance_face_no_inline_parse_decisions,
        test_performance_face_no_inline_calibration_interface,
        test_performance_face_imports_from_reviewer_decisions_lib,
        test_no_legacy_task_path_drift_in_faces,
        test_decisions_stream_still_uses_canonical_parser,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} ADR-239 assertions passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
