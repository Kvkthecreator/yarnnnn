"""
ADR-312 regression gate — Home as Composition.

Asserts the kernel home contract invariants:

  1. Surface rename — the kernel surface is `home` (slug + route + title),
     not `cockpit`. Singular Implementation: `cockpit` slug/route are gone.
  2. Register split — mandate/principles/identity carry register `intent`;
     autonomy/budget/connectors/program/settings/setup carry `os-config`; the
     `application` register is unchanged. (ADR-327: `pace` retired → `budget`.)
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
    # ADR-327: `pace` retired → `budget` is the canonical os-config governance
    # dial. `setup` (ADR-331) is also os-config (it configures the OS, not an
    # open file).
    for slug in ("autonomy", "budget", "connectors", "program", "settings", "setup"):
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
# 3b — D2 amendment (2026-06-04): kernel renders the three universal slots
# ---------------------------------------------------------------------------

def test_kernel_universal_slots_exist():
    """ADR-312 D2 amendment: the three kernel-universal Home slots (#3 decision
    queue, #5 recent artifacts, #6 judgment trail) are kernel-rendered — they
    exist as components under web/components/library/kernel-home/ and are NOT
    program-declared (no SURFACES.yaml). They render for every workspace."""
    kernel_home = LIBRARY_DIR / "kernel-home"
    for comp in ("KernelDecisionQueue", "KernelRecentArtifacts", "KernelJudgmentTrail"):
        assert (kernel_home / f"{comp}.tsx").exists(), (
            f"ADR-312 D2 amendment: kernel-universal slot {comp} must exist at "
            f"web/components/library/kernel-home/{comp}.tsx."
        )


def test_home_renderer_wires_universal_slots():
    """ADR-312 D2 amendment: HomeRenderer interleaves the three kernel-universal
    slots with program sections (not behind the program XOR). All three must be
    rendered by HomeRenderer directly."""
    src = _read(LIBRARY_DIR / "HomeRenderer.tsx")
    for comp in ("KernelDecisionQueue", "KernelRecentArtifacts", "KernelJudgmentTrail"):
        assert f"<{comp} />" in src, (
            f"ADR-312 D2 amendment: HomeRenderer must render {comp} directly "
            "(kernel-universal slot, not program-gated)."
        )


def test_decision_queue_reuses_proposals_api():
    """Singular implementation: the decision-queue slot reuses the existing
    proposals API (ADR-307), not a parallel reader."""
    src = _read(LIBRARY_DIR / "kernel-home" / "KernelDecisionQueue.tsx")
    # Match the chained call (`api.proposals\n  .list(...)`) — check both
    # tokens rather than the contiguous string so line-wrapping doesn't
    # false-negative.
    assert "api.proposals" in src and ".list(" in src, (
        "KernelDecisionQueue must reuse api.proposals.list (ADR-307 generic "
        "gated-action queue), not a parallel proposals reader."
    )


def test_judgment_trail_reuses_decisions_parser():
    """Singular implementation: the judgment-trail slot reuses the canonical
    content-shapes/decisions.ts parser, not a parallel decisions parser."""
    src = _read(LIBRARY_DIR / "kernel-home" / "KernelJudgmentTrail.tsx")
    assert "content-shapes/decisions" in src, (
        "KernelJudgmentTrail must reuse the canonical content-shapes/decisions.ts "
        "parser, not re-implement decisions.md parsing."
    )


# ---------------------------------------------------------------------------
# 3c — D2 amendment #2 (2026-06-04): a program declares exactly hero + entities
# ---------------------------------------------------------------------------

def test_program_declares_at_most_two_home_sections():
    """ADR-312 D2 amendment #2: a program declares EXACTLY two home slots —
    one ground-truth hero (#2) + one entity list (#4). No metric stack. We
    assert every program's SURFACES.yaml home.program_sections has <= 2
    entries."""
    import re
    programs_dir = REPO_ROOT / "docs" / "programs"
    offenders = []
    for surfaces in programs_dir.glob("*/SURFACES.yaml"):
        text = _read(surfaces)
        # Count `- kind:` entries inside the home.program_sections block.
        home_match = re.search(r"\n\s*home:\s*\n\s*program_sections:\s*\n(.*?)(?=\n\S|\Z)", text, re.DOTALL)
        if not home_match:
            continue
        kinds = re.findall(r"-\s*kind:", home_match.group(1))
        # alpha-trader is the known, documented exception pending reshape.
        if surfaces.parent.name == "alpha-trader":
            continue
        if len(kinds) > 2:
            offenders.append(f"{surfaces.parent.name}: {len(kinds)} sections")
    assert not offenders, (
        "ADR-312 D2 amendment #2: a program declares <= 2 home.program_sections "
        f"(one hero + one entity list). Offenders: {offenders}"
    )


def test_no_program_mandate_component_registered():
    """ADR-312 D2 amendment #2: a program may NOT re-render the mandate — the
    kernel HomeHeader (slot #1) owns it. No `*Mandate` program component may be
    registered in the library."""
    registry = _read(LIBRARY_DIR / "registry.tsx")
    import re
    # Registered component keys that end in "Mandate" (e.g. AuthorMandate).
    bad = re.findall(r"^\s*(\w*Mandate):\s*\(\)\s*=>", registry, re.MULTILINE)
    # MandateFace was the deleted four-face component; allow none.
    assert not bad, (
        "ADR-312 D2 amendment #2: no program may register a *Mandate component "
        f"(the kernel HomeHeader owns the mandate). Found: {bad}"
    )


def test_author_program_reshaped_to_hero_and_pieces():
    """ADR-312 D2 amendment #2: alpha-author's four overlapping cards collapsed
    to exactly AuthorHero (slot #2) + AuthorPieces (slot #4)."""
    author_dir = LIBRARY_DIR / "programs" / "alpha-author"
    assert (author_dir / "AuthorHero.tsx").exists(), "AuthorHero (slot #2) must exist."
    assert (author_dir / "AuthorPieces.tsx").exists(), "AuthorPieces (slot #4) must exist."
    for deleted in ("AuthorMandate", "AuthorCorpus", "AuthorVoice", "AuthorPipeline"):
        assert not (author_dir / f"{deleted}.tsx").exists(), (
            f"ADR-312 D2 amendment #2: {deleted} is superseded by AuthorHero/"
            "AuthorPieces and must be deleted (Singular Implementation)."
        )


def test_decision_queue_is_plain_language():
    """Plain-language pass: the decision queue maps primitives to operator verbs
    and drops the substrate/capital jargon word from the row.

    ADR-340 P4 F3 (2026-06-12): the inline PRIMITIVE_LABELS map was
    consolidated into the shared web/lib/proposal-labels.ts module
    (Singular Implementation). The plain-language guarantee now lives
    there; the slot imports proposalActionLabel. Assert the shared
    module carries the operator verbs + the slot uses it."""
    slot = _read(LIBRARY_DIR / "kernel-home" / "KernelDecisionQueue.tsx")
    labels = _read(WEB / "lib" / "proposal-labels.ts")
    assert "proposalActionLabel" in slot, (
        "KernelDecisionQueue must use the shared proposalActionLabel (ADR-340 P4 F3)."
    )
    assert "Save a workspace change" in labels and "Submit a trade order" in labels, (
        "lib/proposal-labels.ts must map primitives to plain operator verbs."
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
# 5 — cockpit-route fold (D9)
# ---------------------------------------------------------------------------

def test_cockpit_route_module_folded():
    """ADR-312 D9: api/routes/cockpit.py is folded — trader data → alpha_trader
    route, pace → kernel pace route. No cockpit route module survives."""
    assert not (REPO_ROOT / "api" / "routes" / "cockpit.py").exists(), (
        "ADR-312 D9: api/routes/cockpit.py must be folded into alpha_trader.py "
        "(trader data) + pace.py (kernel governance) — no cockpit route survives."
    )
    assert (REPO_ROOT / "api" / "routes" / "alpha_trader.py").exists(), (
        "ADR-312 D9: trader data routes live in api/routes/alpha_trader.py."
    )
    assert (REPO_ROOT / "api" / "routes" / "pace.py").exists(), (
        "ADR-312 D9: pace folds to the kernel route api/routes/pace.py."
    )


def test_no_api_cockpit_mount_in_main():
    """ADR-312 D9: main.py mounts alpha_trader at /api/programs/alpha-trader and
    pace at /api/pace — no /api/cockpit router mount survives."""
    main_src = _read(REPO_ROOT / "api" / "main.py")
    # No live router mount on /api/cockpit. (Explanatory comments naming the
    # old path are allowed; an include_router(... "/api/cockpit") is not.)
    for line in main_src.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert "/api/cockpit" not in stripped, (
            f"ADR-312 D9: no live /api/cockpit mount may survive (found: {stripped!r})"
        )
    assert "/api/programs/alpha-trader" in main_src, (
        "ADR-312 D9: alpha_trader router mounts at /api/programs/alpha-trader."
    )
    assert 'prefix="/api/pace"' in main_src, (
        "ADR-312 D9: pace router mounts at the kernel /api/pace."
    )


def test_no_api_cockpit_callers_in_frontend():
    """ADR-312 D9: the FE client + components call /api/programs/alpha-trader/*
    and /api/pace — no live api.cockpit caller survives."""
    import subprocess

    web = REPO_ROOT / "web"
    # Search for live `api.cockpit.` usages (the namespace was deleted).
    # -F so the dots are literal (else /api/cockpit/ in doc tables matches).
    result = subprocess.run(
        ["grep", "-rnF", "api.cockpit.", str(web / "components"), str(web / "lib"), str(web / "app")],
        capture_output=True,
        text=True,
    )
    hits = [
        ln for ln in result.stdout.splitlines()
        if "node_modules" not in ln and "/README.md:" not in ln
    ]
    assert not hits, (
        "ADR-312 D9: api.cockpit.* namespace deleted — callers use "
        f"api.programs.alphaTrader.* / api.pace(). Survivors: {hits}"
    )


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
        test_kernel_universal_slots_exist,
        test_home_renderer_wires_universal_slots,
        test_decision_queue_reuses_proposals_api,
        test_judgment_trail_reuses_decisions_parser,
        test_program_declares_at_most_two_home_sections,
        test_no_program_mandate_component_registered,
        test_author_program_reshaped_to_hero_and_pieces,
        test_decision_queue_is_plain_language,
        test_four_face_fallback_deleted,
        test_cockpit_route_module_folded,
        test_no_api_cockpit_mount_in_main,
        test_no_api_cockpit_callers_in_frontend,
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
