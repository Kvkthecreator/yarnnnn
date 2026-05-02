"""
ADR-244 regression gate — Frontend Kernel three-layer content rendering.

Phase 1 ratified the model. Phase 2 (this commit's extension) populates
the content-shape registry by migrating four existing parsers + adding
two new shape entries. Phases 3-5 add their own assertions as they land.

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
WEB_LIB_DIR = REPO_ROOT / "web" / "lib"

# Phase 2 — content-shape modules under web/lib/content-shapes/
PHASE_2_SHAPES = [
    "autonomy",
    "decisions",
    "inference-meta",
    "snapshot",
    "performance",
    "principles",
]

# Phase 2 — legacy parser paths that MUST be deleted (Singular Implementation)
PHASE_2_DELETED_LEGACY = [
    "autonomy.ts",
    "reviewer-decisions.ts",
    "inference-meta.ts",
    "snapshot-meta.ts",
]

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
# Phase 2 assertions
# ---------------------------------------------------------------------------

def test_phase_2_shape_modules_exist():
    """Assertion #9: every Phase 2 shape ships a TS module under
    web/lib/content-shapes/{shape}.ts. This is the registry directory's
    populated state."""
    missing = [
        s for s in PHASE_2_SHAPES
        if not (CONTENT_SHAPES_DIR / f"{s}.ts").exists()
    ]
    assert not missing, (
        f"Phase 2 must ship modules for {PHASE_2_SHAPES} per ADR-244 D3. "
        f"Missing: {missing}"
    )


def test_phase_2_shape_modules_declare_schema():
    """Assertion #10: every Phase 2 shape module exports the four required
    schema fields per ADR-244 D3 — SHAPE_KEY, PATH_GLOB, WRITE_CONTRACT,
    CANONICAL_L3 — plus a `parse()` function (or alias)."""
    for shape in PHASE_2_SHAPES:
        path = CONTENT_SHAPES_DIR / f"{shape}.ts"
        src = _read(path)
        for marker in ["SHAPE_KEY", "PATH_GLOB", "WRITE_CONTRACT", "CANONICAL_L3", "META"]:
            assert marker in src, (
                f"Shape module {shape}.ts must export {marker!r} per ADR-244 D3."
            )
        assert "export function parse" in src or "export const parse" in src, (
            f"Shape module {shape}.ts must export a `parse` function per ADR-244 D3."
        )


def test_phase_2_legacy_parsers_deleted():
    """Assertion #11: legacy parser files at web/lib/{*.ts} are DELETED
    per Singular Implementation rule 1. ADR-244 Phase 2 collapsed parser
    homes into web/lib/content-shapes/."""
    survivors = [
        legacy for legacy in PHASE_2_DELETED_LEGACY
        if (WEB_LIB_DIR / legacy).exists()
    ]
    assert not survivors, (
        f"Phase 2 must delete legacy parser files {PHASE_2_DELETED_LEGACY} "
        f"per Singular Implementation. Surviving: {survivors}"
    )


def test_phase_2_no_stale_imports():
    """Assertion #12: no FE source file imports from the legacy parser
    paths (`@/lib/autonomy`, `@/lib/reviewer-decisions`, etc.). All
    consumers must import from `@/lib/content-shapes/{shape}`."""
    web_root = REPO_ROOT / "web"
    if not web_root.is_dir():
        return
    legacy_paths = [
        "@/lib/autonomy",
        "@/lib/reviewer-decisions",
        "@/lib/inference-meta",
        "@/lib/snapshot-meta",
    ]
    offenders: list[str] = []
    for ts_file in web_root.rglob("*.ts*"):
        # Skip node_modules + build output if either gets vendored.
        parts = set(ts_file.parts)
        if "node_modules" in parts or ".next" in parts:
            continue
        try:
            txt = ts_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for legacy in legacy_paths:
            # Exact-token match — must end with closing quote, not be a prefix
            # of `content-shapes/...`.
            for q in ['"', "'"]:
                needle = f"{q}{legacy}{q}"
                if needle in txt:
                    offenders.append(f"{ts_file.relative_to(REPO_ROOT)} :: {legacy}")
    assert not offenders, (
        "Stale legacy parser imports found per ADR-244 Phase 2 D3 + Singular "
        f"Implementation:\n  " + "\n  ".join(offenders[:10])
    )


def test_phase_2_registry_populated():
    """Assertion #13: index.ts CONTENT_SHAPES registry imports + exports
    each Phase 2 shape's META. Empty stub from Phase 1 is no longer
    acceptable."""
    src = _read(CONTENT_SHAPES_INDEX)
    for shape in PHASE_2_SHAPES:
        # Each shape module has its META imported into index.ts
        assert f"from './{shape}'" in src, (
            f"index.ts must import META from ./{shape} per ADR-244 D3."
        )
    # Registry object must contain entries
    assert "CONTENT_SHAPES" in src and "Object.freeze" in src, (
        "index.ts CONTENT_SHAPES must be populated + frozen per Phase 2."
    )
    # Resolver must have non-stub body
    assert "globToRegExp" in src or "PATH_GLOB" in src, (
        "shapeForPath must use PATH_GLOB matching per ADR-244 D3."
    )


def test_phase_2_recurrence_shapes_finding_logged():
    """Assertion #14: ADR-244 records the Phase 2 implementation-time
    finding that recurrence-shapes.ts is NOT a content-shape parser
    (no parse() of file content, no PATH_GLOB) and remains at
    web/lib/recurrence-shapes.ts. Honors ADR-225 v2 / ADR-239 precedent
    of recording memo-vs-implementation drift in the ADR."""
    src = _read(ADR_FILE)
    assert "recurrence-shapes" in src and ("not a content-shape" in src or "implementation-time finding" in src), (
        "ADR-244 must log the Phase 2 finding about recurrence-shapes.ts. "
        "Honors ADR-225 v2 / ADR-239 drift-recording precedent."
    )


# ---------------------------------------------------------------------------
# Phase 3 assertions
# ---------------------------------------------------------------------------

WEB_MONEY_TRUTH_FACE = REPO_ROOT / "web" / "components" / "library" / "faces" / "MoneyTruthFace.tsx"
WEB_MANDATE_FACE = REPO_ROOT / "web" / "components" / "library" / "faces" / "MandateFace.tsx"
WEB_PERFORMANCE_FACE = REPO_ROOT / "web" / "components" / "library" / "faces" / "PerformanceFace.tsx"
WEB_DECISIONS_STREAM = REPO_ROOT / "web" / "components" / "work" / "details" / "DecisionsStream.tsx"


def test_phase_3_money_truth_imports_from_registry():
    """Assertion #15: MoneyTruthFace.tsx imports the performance parser
    from `@/lib/content-shapes/performance` per ADR-244 Phase 3 audit
    (the inline `parseFrontmatter` was the canonical violation flagged
    in §Implementation Phase 3 candidates)."""
    src = _read(WEB_MONEY_TRUTH_FACE)
    assert "@/lib/content-shapes/performance" in src, (
        "MoneyTruthFace.tsx must import from @/lib/content-shapes/performance "
        "per ADR-244 Phase 3 canonical-L3 audit."
    )


def test_phase_3_money_truth_no_inline_parser():
    """Assertion #16: MoneyTruthFace.tsx has no inline `parseFrontmatter`
    function and does not redeclare the `MoneyTruthMeta` interface — both
    moved into `content-shapes/performance.ts` per ADR-244 Phase 3.
    Singular Implementation rule 1: no parallel parsers."""
    src = _read(WEB_MONEY_TRUTH_FACE)
    assert "function parseFrontmatter" not in src, (
        "MoneyTruthFace.tsx must NOT redeclare inline parseFrontmatter "
        "(use `parse` from @/lib/content-shapes/performance) per ADR-244 Phase 3."
    )
    assert "interface MoneyTruthMeta" not in src, (
        "MoneyTruthFace.tsx must NOT redeclare MoneyTruthMeta interface "
        "(use `PerformanceMeta` from registry) per ADR-244 Phase 3."
    )


def test_phase_3_canonical_consumers_import_from_registry():
    """Assertion #17: every canonical L3 consumer of a registry-covered
    shape imports its parser from `@/lib/content-shapes/{shape}`.
    Verifies Phase 2 sed migration didn't miss anything and Phase 3
    canonical-L3 census is complete."""
    canonical_consumers = {
        WEB_MANDATE_FACE: "@/lib/content-shapes/autonomy",
        WEB_PERFORMANCE_FACE: "@/lib/content-shapes/decisions",
        WEB_DECISIONS_STREAM: "@/lib/content-shapes/decisions",
    }
    for path, expected_import in canonical_consumers.items():
        src = _read(path)
        assert expected_import in src, (
            f"{path.relative_to(REPO_ROOT)} must import from {expected_import} "
            "per ADR-244 Phase 3 canonical-L3 audit."
        )


def test_phase_3_bundle_specific_parsers_documented():
    """Assertion #18: ADR documents the Phase 3 finding that
    TraderSignalExpectancy.tsx parses a bundle-extended shape
    (`expectancy_by_signal` field on `_performance.md`) and stays out of
    the kernel registry per ADR-188 + ADR-244 D7 (bundle library
    extension loading deferred). Same demand-pull discipline as Phase 2's
    recurrence-shapes finding."""
    src = _read(ADR_FILE)
    assert "TraderSignalExpectancy" in src and "bundle" in src.lower(), (
        "ADR-244 must log the Phase 3 finding about TraderSignalExpectancy "
        "as a bundle-extended shape per ADR-188 + D7."
    )


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        # Phase 1
        test_adr_file_exists,
        test_adr_references_all_predecessors,
        test_adr_declares_three_layers,
        test_adr_declares_three_gap_closures,
        test_content_shapes_directory_exists,
        test_content_shapes_index_declares_schema_types,
        test_claude_md_registers_adr_244,
        test_design_archive_clean_until_phase_5,
        # Phase 2
        test_phase_2_shape_modules_exist,
        test_phase_2_shape_modules_declare_schema,
        test_phase_2_legacy_parsers_deleted,
        test_phase_2_no_stale_imports,
        test_phase_2_registry_populated,
        test_phase_2_recurrence_shapes_finding_logged,
        # Phase 3
        test_phase_3_money_truth_imports_from_registry,
        test_phase_3_money_truth_no_inline_parser,
        test_phase_3_canonical_consumers_import_from_registry,
        test_phase_3_bundle_specific_parsers_documented,
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
    print(f"\nADR-244 gate (Phase 1 + Phase 2 + Phase 3): {passed}/{total} passing")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
