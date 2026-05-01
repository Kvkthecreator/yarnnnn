"""
ADR-244 regression gate — Frontend Kernel three-layer content rendering.

Phase 1 assertions only (this commit ratifies the model). Phases 2-5 add
their own assertions to this file as they land.

Same Python-test-over-TS-source pattern as ADR-237 / ADR-238 / ADR-239 /
ADR-240 / ADR-241 / ADR-242 (no JS test runner today; see ADR-236 Rule 3).

Run via:
    python -m pytest api/test_adr244_three_layer_model.py -v

Or as a standalone script:
    python api/test_adr244_three_layer_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ADR_FILE = REPO_ROOT / "docs" / "adr" / "ADR-244-frontend-kernel-three-layer-content-rendering.md"
CONTENT_SHAPES_DIR = REPO_ROOT / "web" / "lib" / "content-shapes"
CONTENT_SHAPES_INDEX = CONTENT_SHAPES_DIR / "index.ts"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
DESIGN_ARCHIVE_DIR = REPO_ROOT / "docs" / "design" / "archive"

REQUIRED_PREDECESSORS = ["ADR-167", "ADR-225", "ADR-228", "ADR-237", "ADR-238", "ADR-239", "ADR-241", "ADR-242"]


def _read(p: Path) -> str:
    if not p.exists():
        raise AssertionError(f"Missing file: {p.relative_to(REPO_ROOT)}")
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 1 assertions
# ---------------------------------------------------------------------------

def test_adr_file_exists():
    """Assertion #1: ADR-244 doc exists at the canonical path."""
    assert ADR_FILE.exists(), f"ADR-244 missing at {ADR_FILE.relative_to(REPO_ROOT)}"


def test_adr_references_all_predecessors():
    """Assertion #2: ADR cites every predecessor that the dimensional
    mapping + descriptive census depends on. Per ADR-236 Rule 8 drafted-pair
    sequencing — predecessors must be Implemented before being cited."""
    src = _read(ADR_FILE)
    missing = [p for p in REQUIRED_PREDECESSORS if p not in src]
    assert not missing, (
        f"ADR-244 must reference predecessors {REQUIRED_PREDECESSORS} per ADR-236 Rule 8. "
        f"Missing: {missing}"
    )


def test_adr_declares_three_layers():
    """Assertion #3: ADR explicitly names L1 / L2 / L3 layers and their
    axiom mappings. Without these the axiomatic claim collapses."""
    src = _read(ADR_FILE)
    for marker in ["L1", "L2", "L3", "Axiom 1", "Axiom 5", "Axiom 6"]:
        assert marker in src, f"ADR-244 must declare {marker} per D1 dimensional mapping."


def test_adr_declares_three_gap_closures():
    """Assertion #4: ADR closes the three load-bearing gaps named in the
    design conversation: content-shape registry (D3), canonical-L3 +
    secondary consumers (D4), per-class write contracts (D5)."""
    src = _read(ADR_FILE)
    for d in ["### D3", "### D4", "### D5"]:
        assert d in src, f"ADR-244 must close gap section {d}."
    for keyword in ["registry", "Canonical L3", "Write Contract"]:
        assert keyword in src, f"ADR-244 must address {keyword!r} per gap closures."


def test_content_shapes_directory_exists():
    """Assertion #5: web/lib/content-shapes/ exists with stub index.ts.
    Phase 2 populates it with migrated parsers + new shapes."""
    assert CONTENT_SHAPES_DIR.is_dir(), (
        f"Phase 1 must create {CONTENT_SHAPES_DIR.relative_to(REPO_ROOT)} per ADR-244 D3."
    )
    assert CONTENT_SHAPES_INDEX.exists(), (
        f"Phase 1 must create {CONTENT_SHAPES_INDEX.relative_to(REPO_ROOT)} stub."
    )


def test_content_shapes_index_declares_schema_types():
    """Assertion #6: stub index.ts declares the WriteContract + ContentShape
    types + CONTENT_SHAPES registry + shapeForPath resolver. Phase 2
    populates entries; Phase 1 establishes the contract on disk."""
    src = _read(CONTENT_SHAPES_INDEX)
    for marker in [
        "WriteContract",
        "ContentShape",
        "CONTENT_SHAPES",
        "shapeForPath",
        "configuration",
        "declaration",
        "live_aggregate",
    ]:
        assert marker in src, (
            f"web/lib/content-shapes/index.ts must export {marker!r} per ADR-244 D3 + D5."
        )


def test_claude_md_registers_adr_244():
    """Assertion #7: CLAUDE.md ADR registry includes ADR-244 entry. Without
    this the ADR is invisible to future sessions per CLAUDE.md rule 3
    (CHECK ADRs FIRST)."""
    src = _read(CLAUDE_MD)
    assert "ADR-244" in src, "CLAUDE.md must register ADR-244 in the Key ADRs section."


def test_design_archive_clean_until_phase_5():
    """Assertion #8: docs/design/archive/ does not yet contain ADR-244
    supersede artifacts. Phase 5 lands the supersede pass; Phase 1 must not
    pre-archive anything."""
    if not DESIGN_ARCHIVE_DIR.is_dir():
        return
    archived = list(DESIGN_ARCHIVE_DIR.glob("*ADR-244*"))
    assert not archived, (
        f"Phase 1 must not pre-archive design docs. Found: {[p.name for p in archived]}. "
        "Move supersede pass to Phase 5."
    )


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        test_adr_file_exists,
        test_adr_references_all_predecessors,
        test_adr_declares_three_layers,
        test_adr_declares_three_gap_closures,
        test_content_shapes_directory_exists,
        test_content_shapes_index_declares_schema_types,
        test_claude_md_registers_adr_244,
        test_design_archive_clean_until_phase_5,
    ]
    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as exc:
            print(f"  FAIL  {fn.__name__}: {exc}")
            failed += 1
    total = passed + failed
    print(f"\nADR-244 Phase 1 gate: {passed}/{total} passing")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
