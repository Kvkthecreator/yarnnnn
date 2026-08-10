"""The widgets render the substrate the server actually sends (2026-08-10).

WHY THIS GATE EXISTS — a measured defect, not a speculative one. `compose_search`
has always returned `confidence` (ALWAYS present, even on a miss — the field was
added precisely so a host could tell "use this" from "ask which one"), and
`search-results/types.ts` declared it with the comment "always present". The
widget rendered it NOWHERE, and rendered `explanation` only on the EMPTY path —
so the `ambiguous` case, the one where the server explicitly writes "consider
asking the user which they mean", looked identical on screen to a confident hit.
Found by driving the live connector from ChatGPT (2026-08-10): the host asked the
user to disambiguate off the STRUCTURED payload while the card beside it showed a
flat ranked list. The signal survived to the model and died at the glass.

The shape of the fault is the one this project keeps meeting: a fact declared in
one place and dropped at the surface that was supposed to show it. So the gate
asserts the RENDER, not the declaration — a type that names a field proves
nothing about whether a reader ever sees it.

THE OTHER HALF — the two things the widgets could not say:
  - `derived_from` was accepted by `save`, parsed, and written to the ledger, but
    never RETURNED, so the provenance edge (the thing that separates an
    attributed commons from a folder of files) was invisible at the moment of
    writing. The server now echoes the POST-PARSE set — what was actually
    recorded — never the raw input, because a malformed citation is deliberately
    dropped rather than made fatal.
  - the conflict card told the reader to "save again" without naming the
    `base_revision` the retry must carry, though the server returns it on both
    conflict errors.

WHAT THIS GATE DOES NOT DO: it does not assert a widget for every verb. Text-only
is valid on every host (ADR-372 D1) and five verbs are text-only BY DECISION with
their reasons recorded (ADR-533 D4 / ADR-545). This gate covers only the fields a
declared widget already receives and failed to show.

Run: python3 test_mcp_widget_render_completeness.py
"""

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_WIDGETS = _ROOT / "mcp_server" / "widgets"
_SRC = _WIDGETS / "src"
_DIST = _WIDGETS / "dist"

_failures: list[str] = []


def _check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail if not ok else ''}")
    if not ok:
        _failures.append(label)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def main() -> int:
    search_tsx = _read(_SRC / "search-results" / "SearchResults.tsx")
    save_tsx = _read(_SRC / "save-receipt" / "SaveReceipt.tsx")
    styles = _read(_SRC / "shared" / "styles.ts")

    # ── 1. search renders the honest-state signal ────────────────────────────
    # Assert the BEHAVIOUR (the confidence value reaches a rendered element),
    # not a spelling: pinning a label string would read a copy edit as a
    # violation, which is the gate-craft error this project has hit repeatedly.
    _check(
        "1a search renders `confidence` (not merely typed)",
        "result.confidence" in search_tsx
        and re.search(r"<Confidence\s+level=", search_tsx) is not None,
        "confidence must reach a rendered component",
    )
    _check(
        "1b every confidence level the server can emit has a rendering",
        all(
            lvl in search_tsx
            for lvl in ("high", "ambiguous", "weak", "none")
        ),
        "the four levels compose_search returns must all map",
    )
    # The ambiguous/weak sentence is the one the server writes to say ASK.
    # Previously reachable only when results were EMPTY.
    _check(
        "1c `explanation` renders on the NON-empty path (the ambiguous case)",
        search_tsx.count("result.explanation") >= 2,
        "explanation must render beside results, not only on the miss",
    )

    # ── 2. save renders the provenance edge + the retry basis ────────────────
    _check(
        "2a save-receipt renders `derived_from` when present",
        "result.derived_from" in save_tsx,
        "the recorded citations must be visible on the receipt",
    )
    _check(
        "2b the conflict names the base_revision the retry needs",
        "head.revision_id" in save_tsx and "base_revision" in save_tsx,
        "a guard is only reassuring if you can see what it wants",
    )

    # ── 3. the server actually SENDS derived_from ────────────────────────────
    # The widget half is worthless if the payload never carries it. Assert the
    # echo is the POST-PARSE set (`cited`), not the caller's raw input.
    comp = _read(_ROOT / "services" / "mcp_composition.py")
    _check(
        "3a compose_save echoes the recorded citations",
        'out["derived_from"] = cited' in comp,
        "save must return what it recorded",
    )
    _check(
        "3b the echo is the parsed set, never the raw argument",
        'out["derived_from"] = derived_from' not in comp,
        "echoing raw input would report an edge that may not exist",
    )

    # ── 4. styles exist for every class the widgets emit ─────────────────────
    for cls in ("yz-confidence", "yz-conf-high", "yz-conf-ambiguous",
                "yz-explanation", "yz-derived", "yz-basis", "yz-rev"):
        _check(f"4 `{cls}` has a style rule", f".{cls}" in styles,
               "an unstyled class renders as unformatted text")

    # ── 5. THE BUILD IS THE MOUNT ────────────────────────────────────────────
    # A green source tree is not a shipped widget: the served resource reads the
    # BUNDLE off disk. This project has shipped a computed-but-never-mounted
    # token before, so assert the built artifact carries the render.
    search_dist = _read(_DIST / "search-results.html")
    save_dist = _read(_DIST / "save-receipt.html")
    _check(
        "5a the search bundle carries the confidence render",
        "yz-conf-" in search_dist and "Several matches" in search_dist,
        "rebuild: node build.mjs",
    )
    _check(
        "5b the save bundle carries derived_from + the retry basis",
        "Made from" in save_dist and "Save again with" in save_dist,
        "rebuild: node build.mjs",
    )

    # ── 6. the stylesheet is ONE template literal — no stray backticks ───────
    # This trap bit three times in the ADR-546 arc and once here: a backtick in
    # a CSS comment terminates the literal and the build dies with a parse error
    # far from the cause. Cheap standing guard.
    m = re.search(r"export const CSS = `(.*?)\n`;", styles, re.DOTALL)
    _check(
        "6 no backtick inside the CSS template literal",
        m is not None and "`" not in m.group(1),
        "a backtick in a CSS comment breaks the build",
    )

    print()
    total = 15
    if _failures:
        print(f"{len(_failures)} FAILED: {', '.join(_failures)}")
        return 1
    print(f"{total}/{total} widget-render assertions pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
