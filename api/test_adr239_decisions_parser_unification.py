"""
ADR-239 regression gate — decisions parser unification.

Asserts six invariants for the parser consolidation landed in ADR-239
(Round 3 of the ADR-236 frontend cockpit coherence pass).

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

WEB_LIB_REVIEWER = REPO_ROOT / "web" / "lib" / "reviewer-decisions.ts"
WEB_PERFORMANCE_FACE = REPO_ROOT / "web" / "components" / "library" / "faces" / "PerformanceFace.tsx"
WEB_DECISIONS_PANE = REPO_ROOT / "web" / "components" / "agents" / "reviewer" / "DecisionsStreamPane.tsx"
WEB_FACES_DIR = REPO_ROOT / "web" / "components" / "library" / "faces"


def _read(p: Path) -> str:
    if not p.exists():
        raise AssertionError(f"Missing file: {p.relative_to(REPO_ROOT)}")
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test gate
# ---------------------------------------------------------------------------

def test_reviewer_decisions_lib_exposes_aggregator_and_calibration_type():
    """Assertion #1: web/lib/reviewer-decisions.ts exposes the canonical
    parser, the new aggregator, and the calibration interface."""
    src = _read(WEB_LIB_REVIEWER)
    expected = [
        "export function parseDecisions",
        "export function aggregateReviewerCalibration",
        "export interface ReviewerCalibration",
    ]
    for ex in expected:
        assert ex in src, f"web/lib/reviewer-decisions.ts missing export: {ex}"


def test_performance_face_no_inline_parse_decisions():
    """Assertion #2: PerformanceFace.tsx no longer contains an inline
    `function parseDecisions(`. Regression guard against re-inlining."""
    src = _read(WEB_PERFORMANCE_FACE)
    assert "function parseDecisions(" not in src, (
        "PerformanceFace.tsx contains an inline parseDecisions function — "
        "Singular Implementation violation per ADR-239 D1. Import from "
        "@/lib/reviewer-decisions instead."
    )


def test_performance_face_no_inline_calibration_interface():
    """Assertion #3: PerformanceFace.tsx no longer contains an inline
    `interface ReviewerCalibration {`. The interface lives in
    @/lib/reviewer-decisions per ADR-239 D2."""
    src = _read(WEB_PERFORMANCE_FACE)
    assert "interface ReviewerCalibration {" not in src, (
        "PerformanceFace.tsx contains an inline ReviewerCalibration "
        "interface — Singular Implementation violation per ADR-239 D2. "
        "Import the type from @/lib/reviewer-decisions."
    )


def test_performance_face_imports_from_reviewer_decisions_lib():
    """Assertion #4: PerformanceFace.tsx imports the canonical parser,
    aggregator, and type from @/lib/reviewer-decisions."""
    src = _read(WEB_PERFORMANCE_FACE)
    assert "from '@/lib/reviewer-decisions'" in src, (
        "PerformanceFace.tsx must import from @/lib/reviewer-decisions "
        "per ADR-239 D1+D2."
    )
    for name in ("parseDecisions", "aggregateReviewerCalibration", "ReviewerCalibration"):
        assert name in src, (
            f"PerformanceFace.tsx must reference {name!r} via the "
            f"@/lib/reviewer-decisions import."
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


def test_decisions_stream_pane_still_uses_canonical_parser():
    """Assertion #6: DecisionsStreamPane.tsx (Reviewer detail view)
    continues to import parseDecisions from @/lib/reviewer-decisions.
    Regression guard against the canonical parser being moved or
    renamed without updating this consumer."""
    src = _read(WEB_DECISIONS_PANE)
    assert "from '@/lib/reviewer-decisions'" in src, (
        "DecisionsStreamPane.tsx must import from @/lib/reviewer-decisions "
        "(canonical parser per ADR-239 D1)."
    )
    assert "parseDecisions" in src, (
        "DecisionsStreamPane.tsx must call parseDecisions from the "
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
        test_decisions_stream_pane_still_uses_canonical_parser,
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
