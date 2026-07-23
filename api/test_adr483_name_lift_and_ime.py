#!/usr/bin/env python3
"""Gate: ADR-483 — the name is what the member typed; the IME owns Enter first.

Two defects, one root: the Studio showed a name the member never typed.

  D1  the crumb derived the name from the PATH alone. ADR-469 lifted the name
      into the artifact's <title> and taught `services/studio.py::artifact_name`
      to read it first — but the Studio workbench never migrated, so the crumb
      kept titleizing the meaning folder. That folder is an ASCII identity KEY
      (ADR-469: "it must be injective; it does not have to be readable"), so a
      non-Latin name is gone by the time the crumb reads it. `sdㄴ` → `Sd`.
  D2  the rename field acted on Enter DURING an IME composition. Typing Korean,
      the first Enter commits the SYLLABLE, not the field — `isComposing` is
      true and the buffer holds a half-formed jamo. The rename snatched that
      fragment and committed it as the name.

Compounded, they produced the operator's report: create a document, type a
Korean name, and the crumb reads "Sd" — the rename looking like it had done
nothing at all. It had done something; it had done the wrong thing, twice.

Receipts (workspace_file_versions, 2026-07-23 01:19:46):
    MoveFile: from operation/untitled-document-2/ → operation/sd/
    Studio: name → 'sdㄴ'
The rename WORKED. What it wrote was the fragment, and what it displayed was
the slug — which is why "nothing renders to input" was the honest report of a
surface where the input had in fact rendered.

NOT-the-fix, recorded so it is not relitigated: allowing non-Latin PATH slugs.
The path is a URL parameter, an agent-facing address (MCP recall/trace, ADR-448
`derived_from` edges), and the substrate's binding key (ADR-373/286/209). It is
opaque on purpose and nobody reads it. ADR-469 already solved the readability
problem in the right place — the title — and `disambiguate` already solved the
collision problem. The remaining bug was one unmigrated caller, not the rule.

D1 + D2 are validated EXECUTING, not grepped:
`web/scripts/gates/adr483_name_lift_and_ime.mjs` runs the real
`artifactNameOf`/`extractTitle` and the real crumb `onKeyDown` body (14/14),
each with a FALSIFIER that restores the pre-fix behaviour and asserts the
defect returns. This committed gate is the static regression guard + the
FE/BE parity check on the shared placeholder set.

Run: python3 test_adr483_name_lift_and_ime.py   (check()-style, NOT pytest)
"""

import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    root = pathlib.Path(__file__).resolve().parent.parent
    web = root / "web"
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    modal = (web / "components/studio/NewArtifactModal.tsx").read_text()
    toolbar = (web / "components/studio/StudioToolbar.tsx").read_text()
    route = (root / "api/routes/studio.py").read_text()

    # ── D1: the lift is the crumb's source, and the lossy one is not reachable
    _check(
        "D1: the surface derives the name through the LIFT (artifactNameOf)",
        "function artifactNameOf(" in surface,
    )
    _check(
        "D1: <title> extraction exists FE-side (mirrors extract_title)",
        "function extractTitle(" in surface,
    )
    # ONE derivation: every member-facing name reads the same memo. If a second
    # call site ever re-derives from the path, the Studio shows two names again.
    _check(
        "D1: the path-only fallback has exactly ONE caller (inside the lift)",
        surface.count("artifactNameFromPath(") == 2,  # the declaration + the lift
    )
    _check(
        "D1: no call site derives the displayed name from the path directly",
        "artifactName(artifactPath)" not in surface,
    )
    _check(
        "D1: the crumb, the rename field and the file verbs share one memo",
        surface.count("artifactDisplayName") >= 7,
    )

    # ── The placeholder guard is SERVED, never re-derived FE-side ────────────
    # A deck/page scaffold h1 is a thesis ("The headline promise."), not
    # "Untitled ‹label›" — so it is not derivable from the served labels, and a
    # FE re-derivation would drift from `_is_placeholder_title`.
    _check(
        "parity: the kernel serves the scaffold titles",
        '"placeholder_titles": sorted(_SCAFFOLD_TITLES)' in route,
    )
    _check(
        "parity: the FE vocabulary type carries them",
        "placeholder_titles: string[]" in toolbar,
    )
    _check(
        "parity: the lift consumes the SERVED set (no FE-side scaffold list)",
        "vocabulary?.placeholder_titles" in surface,
    )
    # In CODE — the prose in comments explains the placeholder (and quotes it,
    # which is why the naive substring test cannot answer this). Comments are
    # stripped first so the question asked is the real one: does any shipped
    # expression carry a scaffold title?
    surface_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", surface, flags=re.S))
    _check(
        "parity: no scaffold title appears in FE code (comments excluded)",
        not any(
            t in surface_code
            for t in ("Untitled document", "Untitled article", "The headline promise.")
        ),
    )

    # The served set must be exactly what the placeholder predicate tests.
    try:
        from services.studio import _SCAFFOLD_TITLES, _is_placeholder_title

        _check(
            "parity: every served title IS a placeholder by the server's predicate",
            all(_is_placeholder_title(t) for t in _SCAFFOLD_TITLES),
        )
        _check(
            "parity: a real name is NOT a placeholder (the predicate discriminates)",
            not _is_placeholder_title("sdㄴ") and not _is_placeholder_title("IR deck v3"),
        )
    except Exception as e:  # noqa: BLE001
        _check(f"parity: scaffold set importable ({e})", False)

    # ── The path rule is UNCHANGED — the decision this ADR records ──────────
    try:
        from services.naming import path_slug

        _check(
            "D3: the path stays an ASCII key — non-Latin still slugs away",
            path_slug("한글 문서") == "untitled" and path_slug("sdㄴ") == "sd",
        )
        _check(
            "D3: Latin naming is byte-identical (no behaviour change)",
            path_slug("IR deck v3") == "ir-deck-v3" and path_slug("café") == "cafe",
        )
    except Exception as e:  # noqa: BLE001
        _check(f"D3: naming importable ({e})", False)

    # ── D2: the IME guard, on BOTH inputs that name an artifact ─────────────
    _check(
        "D2: the crumb's rename field guards on isComposing",
        "if (e.nativeEvent.isComposing) return;" in surface,
    )
    _check(
        "D2: the named door's modal guards too (same bug, same fix)",
        "if (e.nativeEvent.isComposing) return;" in modal,
    )

    # ── The EXECUTING gate is the load-bearing one ──────────────────────────
    mjs = web / "scripts/gates/adr483_name_lift_and_ime.mjs"
    _check("executing gate present", mjs.exists())
    if mjs.exists():
        proc = subprocess.run(
            ["node", str(mjs)], cwd=str(root), capture_output=True, text=True
        )
        for line in proc.stdout.strip().splitlines():
            print(f"    {line}")
        _check("executing gate passes (runs the real handler + falsifiers)", proc.returncode == 0)

    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)
    print(f"\nADR-483: {passed}/{total} passed")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
