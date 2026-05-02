"""
ADR-238 regression gate — autonomy-mode FE consumption.

Asserts six invariants for the substrate-read primitive extracted in
ADR-238 (Round 1 of the ADR-236 frontend cockpit coherence pass).

**Amended by ADR-244 Phase 2 (2026-05-01)**: the parser module relocated
from `web/lib/autonomy.ts` to `web/lib/content-shapes/autonomy.ts` per
ADR-244 D3 content-shape registry. Path constants + import-string
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
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WEB_LIB_AUTONOMY = REPO_ROOT / "web" / "lib" / "content-shapes" / "autonomy.ts"
WEB_MANDATE_FACE = REPO_ROOT / "web" / "components" / "library" / "faces" / "MandateFace.tsx"
WEB_CHAT_PANEL = REPO_ROOT / "web" / "components" / "tp" / "ChatPanel.tsx"
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

    **Amended by ADR-244 Phase 2**: module relocated to
    web/lib/content-shapes/autonomy.ts. **Amended by ADR-244 Phase 2**:
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
    # ADR-244 Phase 2 — both are valid public exports.
    assert (
        "export function parseAutonomy" in src
        or "export const parseAutonomy" in src
    ), "autonomy shape module missing export: parseAutonomy (function or const alias)"


def test_mandate_face_does_not_re_inline_parser():
    """Assertion #2: regression guard — MandateFace.tsx no longer contains
    the strings `function parseAutonomy(` or `function formatAutonomySummary(`.
    A future drift that re-inlines the parser would fail this assertion."""
    src = _read(WEB_MANDATE_FACE)
    assert "function parseAutonomy(" not in src, (
        "MandateFace.tsx re-inlined parseAutonomy — Singular Implementation "
        "violation per ADR-238 D1/D3. Import from @/lib/content-shapes/autonomy instead."
    )
    assert "function formatAutonomySummary(" not in src, (
        "MandateFace.tsx re-inlined formatAutonomySummary — Singular "
        "Implementation violation per ADR-238 D1/D3. Import from "
        "@/lib/content-shapes/autonomy instead."
    )


def test_mandate_face_imports_from_lib_autonomy():
    """Assertion #3: MandateFace.tsx imports from @/lib/content-shapes/autonomy.

    **Amended by ADR-244 Phase 4**: MandateFace replaced the static
    `autonomyLine` text with the AutonomyToggle subcomponent (canonical
    L3 for the autonomy shape per ADR-244 D4). The previously-required
    `formatAutonomySummary` import was dropped because the toggle owns
    its own rendering. The post-Phase-4 surface MandateFace consumes is
    AUTONOMY_PATH + parseAutonomy + the new round-trip + serialize."""
    src = _read(WEB_MANDATE_FACE)
    assert "from '@/lib/content-shapes/autonomy'" in src, (
        "MandateFace.tsx must import autonomy helpers from @/lib/content-shapes/autonomy "
        "per ADR-238 D3."
    )
    # Verify the post-Phase-4 names MandateFace consumes.
    for name in ("AUTONOMY_PATH", "parseAutonomy"):
        pattern = re.compile(
            rf"from\s+'@/lib/content-shapes/autonomy'|import\s*\{{[^}}]*\b{name}\b[^}}]*\}}",
            re.DOTALL,
        )
        assert name in src and "@/lib/content-shapes/autonomy" in src, (
            f"MandateFace.tsx must import `{name}` from @/lib/content-shapes/autonomy."
        )


def test_chat_panel_imports_use_autonomy():
    """Assertion #4: ChatPanel.tsx imports useAutonomy from @/lib/content-shapes/autonomy
    and renders the chip."""
    src = _read(WEB_CHAT_PANEL)
    assert "useAutonomy" in src, (
        "ChatPanel.tsx must import useAutonomy from @/lib/content-shapes/autonomy "
        "per ADR-238 D4."
    )
    assert "@/lib/content-shapes/autonomy" in src, (
        "ChatPanel.tsx must import from @/lib/content-shapes/autonomy."
    )
    # The chip is gated on a non-manual effective level.
    assert "showAutonomyChip" in src, (
        "ChatPanel.tsx must compute showAutonomyChip per ADR-238 D4."
    )


def test_workspace_init_scaffolds_shared_autonomy_path():
    """Assertion #5: workspace_init.py continues to scaffold
    SHARED_AUTONOMY_PATH at signup. Regression guard against a substrate
    sunset that would orphan ADR-238."""
    src = _read(API_WORKSPACE_INIT)
    assert "SHARED_AUTONOMY_PATH" in src, (
        "workspace_init.py must reference SHARED_AUTONOMY_PATH to scaffold "
        "the autonomy substrate per ADR-217 / ADR-238 R4."
    )


def test_workspace_paths_exposes_shared_autonomy_path():
    """Assertion #6: workspace_paths.py exposes SHARED_AUTONOMY_PATH with
    the workspace-relative shape `context/_shared/AUTONOMY.md`. Regression
    guard against path-constant drift on the Python side; FE drift is
    caught by assertion #1."""
    src = _read(API_WORKSPACE_PATHS)
    expected = 'SHARED_AUTONOMY_PATH = "context/_shared/AUTONOMY.md"'
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
        test_mandate_face_does_not_re_inline_parser,
        test_mandate_face_imports_from_lib_autonomy,
        test_chat_panel_imports_use_autonomy,
        test_workspace_init_scaffolds_shared_autonomy_path,
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
