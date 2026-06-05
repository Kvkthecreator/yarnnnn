"""
ADR-238 regression gate — autonomy-mode FE consumption.

Asserts six invariants for the substrate-read primitive extracted in
ADR-238 (Round 1 of the ADR-236 frontend cockpit coherence pass).

**Amended by ADR-245 Phase 2 (2026-05-01)**: the parser module relocated
from `web/lib/autonomy.ts` to `web/lib/content-shapes/autonomy.ts` per
ADR-245 D3 content-shape registry. Path constants + import-string
assertions in this gate updated accordingly. The semantic invariants
(parser exports, MandateFace + ChatPanel imports the canonical parser,
no re-inlining) are unchanged — only the path moved.

The frontend has no JS test runner today; per ADR-238 §"Test gate" this
Python script is the test gate (consistent with the ADR-231 invariants
gate pattern). It reads the FE source files as text and asserts the
expected exports / imports / boundary conditions.

Run via:
    python -m pytest api/test_adr238_autonomy_substrate.py -v

Or as a standalone script:
    python api/test_adr238_autonomy_substrate.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WEB_LIB_AUTONOMY = REPO_ROOT / "web" / "lib" / "content-shapes" / "autonomy.ts"
API_WORKSPACE_INIT = REPO_ROOT / "api" / "services" / "workspace_init.py"
API_WORKSPACE_PATHS = REPO_ROOT / "api" / "services" / "workspace_paths.py"


def _read(p: Path) -> str:
    if not p.exists():
        raise AssertionError(f"Missing file: {p.relative_to(REPO_ROOT)}")
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test gate
# ---------------------------------------------------------------------------

def test_lib_autonomy_module_exists_and_exports_required_surface():
    """Assertion #1: the autonomy shape module exists and exports the
    documented surface — parseAutonomy, formatAutonomySummary,
    resolveEffectiveLevel, useAutonomy, AutonomyLevel, AutonomyMeta,
    AUTONOMY_PATH.

    **Amended by ADR-245 Phase 2**: module relocated to
    web/lib/content-shapes/autonomy.ts. **Amended by ADR-245 Phase 2**:
    `parse` is the canonical export; `parseAutonomy` is the back-compat
    alias (`export const parseAutonomy = parse;`)."""
    src = _read(WEB_LIB_AUTONOMY)
    # Path constants + types
    for ex in [
        "export const AUTONOMY_PATH",
        "export type AutonomyLevel",
        "export interface AutonomyMeta",
        "export function resolveEffectiveLevel",
        "export function formatAutonomySummary",
        "export function useAutonomy",
    ]:
        assert ex in src, f"autonomy shape module missing export: {ex}"
    # parseAutonomy may be either function-form or alias-const-form per
    # ADR-245 Phase 2 — both are valid public exports.
    assert (
        "export function parseAutonomy" in src
        or "export const parseAutonomy" in src
    ), "autonomy shape module missing export: parseAutonomy (function or const alias)"


# test_mandate_face_does_not_re_inline_parser — superseded: MandateFace.tsx deleted by ADR-228.
# test_mandate_face_imports_from_lib_autonomy — superseded: MandateFace.tsx deleted by ADR-228.
# test_chat_panel_imports_use_autonomy — superseded: ChatPanel.tsx deleted by ADR-259/ADR-312.


def test_workspace_init_scaffolds_governance_substrate():
    """Assertion #5 (amended ADR-286 + ADR-320): AUTONOMY.md is BUNDLE-owned
    (forked via fork_reference_workspace per ADR-286 single-writer), not
    kernel-scaffolded. The kernel-universal governance file workspace_init DOES
    scaffold is the token-budget ceiling (GOVERNANCE_TOKEN_BUDGET_PATH). This
    guards that the governance root stays wired into init."""
    src = _read(API_WORKSPACE_INIT)
    assert "GOVERNANCE_TOKEN_BUDGET_PATH" in src, (
        "workspace_init.py must reference GOVERNANCE_TOKEN_BUDGET_PATH — the "
        "kernel-universal governance ceiling scaffolded at signup (ADR-293 D7). "
        "AUTONOMY.md itself is bundle-forked per ADR-286 single-writer."
    )


def test_workspace_paths_exposes_shared_autonomy_path():
    """Assertion #6: workspace_paths.py exposes GOVERNANCE_AUTONOMY_PATH with
    the workspace-relative shape `governance/AUTONOMY.md`. Regression
    guard against path-constant drift on the Python side; FE drift is
    caught by assertion #1."""
    src = _read(API_WORKSPACE_PATHS)
    expected = 'GOVERNANCE_AUTONOMY_PATH = "governance/AUTONOMY.md"'
    assert expected in src, (
        f"workspace_paths.py must define {expected!r} (workspace-relative). "
        "ADR-238 assertion #6."
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_lib_autonomy_module_exists_and_exports_required_surface,
        test_workspace_init_scaffolds_governance_substrate,
        test_workspace_paths_exposes_shared_autonomy_path,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} ADR-238 assertions passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
