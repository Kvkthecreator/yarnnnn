"""
ADR-312 regression gate — Home as Composition.

Asserts the kernel home contract invariants:

  1. Surface rename — the kernel surface is `home` (slug + route + title),
     not `cockpit`. Singular Implementation: `cockpit` slug/route are gone.
  2. Register split — mandate/principles/identity carry register `intent`;
     autonomy/pace/connectors/program/settings carry `os-config`; the
     `application` register is unchanged.
  3. No trader-noun leak in the kernel — slot #2 (ground-truth hero) names a
     GENERIC contract, not a trader component. `money_truth` content-shape's
     CANONICAL_L3 must not be a `Trader*` component (it is the alpha-trader
     binding, declared in SURFACES.yaml, not the kernel default). Slot #4
     (live entities) must not hardcode a trader noun ("Positions") anywhere
     in the kernel library.
  4. The four-face fallback (ADR-228) stays deleted — no MoneyTruthFace /
     PerformanceFace / TrackingFace / MandateFace in the library.
  5. The cockpit-route fold (D9) — no `/api/cockpit/*` route survives;
     trader data routes live under `/api/programs/alpha-trader/*`; pace is a
     kernel governance dial under `/api/pace`.

Same Python-test-over-source pattern as ADR-237/238/239/240/241 per
ADR-236 Rule 3.

Run via:
    python -m pytest api/test_adr312_home_as_composition.py -v

Or as a standalone script:
    python api/test_adr312_home_as_composition.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / "web"
LIBRARY_DIR = WEB / "components" / "library"
CONTENT_SHAPES_DIR = WEB / "lib" / "content-shapes"

sys.path.insert(0, str(REPO_ROOT / "api"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1 + 2 — surface rename + register split (backend declaration)
# ---------------------------------------------------------------------------

def test_kernel_surface_is_home_not_cockpit():
    from services.kernel_surfaces import kernel_surface_slugs

    slugs = kernel_surface_slugs()
    assert "home" in slugs, "ADR-312 D1: the home kernel surface must exist."
    assert "cockpit" not in slugs, (
        "ADR-312 D1: the `cockpit` slug is renamed → `home`, not aliased."
    )


def test_home_surface_route_and_title():
    from services.kernel_surfaces import KERNEL_SURFACES

    home = next(s for s in KERNEL_SURFACES if s["slug"] == "home")
    assert home["route"] == "/home", "ADR-312 D1: home route is /home."
    assert home["title"] == "Home", "ADR-312 D1: home title is Home."
    # Summary must not lead with a trader noun — it's the generic home.
    assert "Position" not in home["summary"], (
        "ADR-312 D3/D4: the kernel home summary must not name a trader noun."
    )


def test_register_split_intent_vs_os_config():
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {s["slug"]: s for s in KERNEL_SURFACES if "register" in s}
    # `intent` register — the constitution (operation's authored intent).
    for slug in ("mandate", "principles", "identity"):
        assert by_slug[slug]["register"] == "intent", (
            f"ADR-312 D5: '{slug}' belongs to the `intent` register."
        )
    # `os-config` register — the OS configuring itself.
    for slug in ("autonomy", "pace", "connectors", "program", "settings"):
        assert by_slug[slug]["register"] == "os-config", (
            f"ADR-312 D5: '{slug}' belongs to the `os-config` register."
        )
    # `application` register — unchanged.
    assert by_slug["home"]["register"] == "application"
    assert by_slug["feed"]["register"] == "application"


# ---------------------------------------------------------------------------
# 3 — no trader-noun leak in the kernel
# ---------------------------------------------------------------------------

def test_ground_truth_hero_is_generic_not_trader():
    """ADR-312 D3: the kernel money_truth content-shape's CANONICAL_L3 names
    a generic ground-truth hero contract, NOT a Trader* component. The trader
    binding is declared in the alpha-trader SURFACES.yaml, not the kernel."""
    src = _read(CONTENT_SHAPES_DIR / "money-truth.ts")
    # Find the CANONICAL_L3 declaration line.
    decl = next(
        (ln for ln in src.splitlines() if ln.strip().startswith("export const CANONICAL_L3")),
        None,
    )
    assert decl is not None, "money-truth.ts must declare CANONICAL_L3."
    assert "Trader" not in decl, (
        "ADR-312 D3: the kernel CANONICAL_L3 must not bind a Trader* component "
        f"(found: {decl.strip()!r}). The trader component is a program binding."
    )
    assert "GroundTruthHero" in decl, (
        "ADR-312 D3: the kernel hero contract should be named generically "
        "(GroundTruthHero)."
    )


def test_no_kernel_hardcoded_positions_label():
    """ADR-312 D4/F2: slot #4 (live entities) is program-labeled. No kernel
    library component or compositor module may hardcode the trader noun
    'Positions' — that label lives only inside Trader* program components."""
    offenders = []
    for path in list(LIBRARY_DIR.glob("*.tsx")) + list((WEB / "lib" / "compositor").glob("*.ts")):
        if path.name.startswith("Trader"):
            continue  # program component — allowed to name its own entities
        text = _read(path)
        if '"Positions"' in text or ">Positions<" in text:
            offenders.append(path.name)
    assert not offenders, (
        "ADR-312 D4: kernel surfaces must not hardcode the trader noun "
        f"'Positions' in the live-entities slot. Offenders: {offenders}"
    )


# ---------------------------------------------------------------------------
# 4 — four-face fallback stays deleted (ADR-228 → ADR-273 → confirmed ADR-312)
# ---------------------------------------------------------------------------

def test_four_face_fallback_deleted():
    faces_dir = LIBRARY_DIR / "faces"
    for face in ("MoneyTruthFace", "PerformanceFace", "TrackingFace", "MandateFace"):
        assert not (faces_dir / f"{face}.tsx").exists(), (
            f"ADR-273/312: the four-face fallback ({face}) stays deleted — the "
            "cold-start home is the constitution-band CTA, not a de-activated "
            "trader dashboard."
        )


# ---------------------------------------------------------------------------
# 5 — cockpit-route fold (D9) — ADDED IN P5
# ---------------------------------------------------------------------------
#
# The route-fold assertions (no /api/cockpit/* survives; trader data under
# /api/programs/alpha-trader/*; pace under kernel /api/pace) are added in
# Phase 5 when the fold lands. They are intentionally absent here so P4
# lands green before the route work.


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def _run():
    tests = [
        test_kernel_surface_is_home_not_cockpit,
        test_home_surface_route_and_title,
        test_register_split_intent_vs_os_config,
        test_ground_truth_hero_is_generic_not_trader,
        test_no_kernel_hardcoded_positions_label,
        test_four_face_fallback_deleted,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print("=" * 60)
    print(f"ADR-312 home-as-composition gate: {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run() else 1)
