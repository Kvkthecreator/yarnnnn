#!/usr/bin/env python3
"""Gate: ADR-461 — geometry as intent, and the boundary that keeps it honest.

D1  the `size` token (Hug | Fill) — width as INTENT, enumerated.
D2  `bindGesture` — the ONE pointer-gesture primitive; gestures compose
    existing ops rather than becoming a second write path.
D3  the column divider — a snap handle stepping through the ratio token's
    STOPS. "never free pixels" (ADR-453 D7:176).
D4  bounded-continuous is deck + media only; continuous-everywhere is OPTED
    OUT. The line: a slide has a frame, a page has a viewport.

WHAT THIS GATE IS REALLY FOR: D1-D3 admit no continuous value, and that is the
whole reason they need no amendment to the token model. The moment a raw pixel
enters the artifact, ADR-461's boundary has been crossed without the argument
D4 requires. These checks are the tripwire.

Run: python3 api/test_adr461_geometry.py
"""

import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


def run() -> bool:
    sys.path.insert(0, str(ROOT / "api"))
    from services.studio import (
        STUDIO_KERNEL_CSS,
        STUDIO_LAYOUTS,
        STUDIO_TOKENS,
        compose_kernel_style_element,
    )

    proj = (WEB / "components/workspace/viewers/projection.ts").read_text()
    canvas = (WEB / "components/studio/StudioCanvas.tsx").read_text()
    surface = (WEB / "components/studio/StudioSurface.tsx").read_text()

    # ── D1: width as intent ────────────────────────────────────────────────
    print("\n-- D1: width as intent --")
    _check("the `size` token exists and applies to blocks", "size" in STUDIO_TOKENS)
    size = STUDIO_TOKENS.get("size", {})
    _check(
        "it offers Hug + Fill (the inspector's two ENUMERABLE widths)",
        {v["value"] for v in size.get("values", [])} == {"hug", "fill"},
    )
    _check(
        "`Fixed` is NOT a value here (a continuous value has no pre-declarable selector)",
        not any(v["value"] == "fixed" for v in size.get("values", [])),
    )
    _check(
        "the default is the ABSENCE of the attribute (the pad/valign/fit convention)",
        "absence" in size.get("description", ""),
    )
    for v in size.get("values", []):
        _check(
            f"'{v['value']}' actually renders",
            f'[data-size="{v["value"]}"]' in STUDIO_KERNEL_CSS,
        )

    # ── D2: one gesture primitive ──────────────────────────────────────────
    print("\n-- D2: gestures compose ops, never a second write path --")
    _check(
        "bindGesture is the ONE pointer-gesture primitive",
        "function bindGesture(handle, subject, opts)" in proj,
    )
    _check(
        "bindDrag is a CALLER of it (the extraction is proven, not asserted)",
        "bindGesture(handle, function () { return curBlock; }" in proj,
    )
    _check(
        "the divider is its SECOND caller (the primitive earns its keep)",
        "bindGesture(divider, function () { return dividerCols; }" in proj,
    )
    _check(
        "click-suppression is ONE flag with ONE setter (no per-gesture cross-talk)",
        proj.count("gestureSuppressClick = true") == 1
        and "draggedPastThreshold" not in proj,
    )
    # The gesture posts; the parent lands it through the existing door.
    _check(
        "the divider POSTS a message rather than writing (no second write path)",
        "type: 'yarnnn-ratio'" in proj,
    )
    _check(
        "the canvas forwards it",
        "d.type === 'yarnnn-ratio'" in canvas and "onRatio?.(" in canvas,
    )
    ratio_h = re.search(r"const handleRatio = useCallback\(([\s\S]*?)\n  \);", surface)
    ratio_body = ratio_h.group(1) if ratio_h else ""
    _check("the surface handler is findable", bool(ratio_h))
    _check(
        "it composes the EXISTING setToken op through applyOp (the one door)",
        "setToken(html" in ratio_body and "applyOp(" in ratio_body,
    )
    _check(
        "it carries its OWN anchor, not the selection's (a located gesture)",
        "anchor: { pageIndex }" in ratio_body,
    )

    # ── D3: stops, never pixels ────────────────────────────────────────────
    print("\n-- D3: the divider steps through STOPS, never free pixels --")
    stops = {v["value"] for v in STUDIO_TOKENS["ratio"]["values"]}
    _check("the ratio token's stops are 2-1 / 1-2", stops == {"2-1", "1-2"})
    _check(
        "1-1 is the ABSENCE (the even default), not a third value",
        "1-1" not in stops and "absence = even" in STUDIO_TOKENS["ratio"]["description"],
    )
    div = re.search(r"function ensureDivider\(\) \{([\s\S]*?)\n    return divider;", proj)
    div_body = div.group(1) if div else ""
    _check("the divider gesture is findable", bool(div))
    _check(
        "it snaps to a named stop or CLEARS (never a computed width)",
        "'1-2'" in div_body and "'2-1'" in div_body and "removeAttribute('data-ratio')" in div_body,
    )
    # THE TRIPWIRE. If any of these appear, a raw pixel is being authored and
    # ADR-461's boundary has been crossed without D4's argument.
    _check(
        "the divider writes NO px/%/width into the artifact",
        not re.search(r"setAttribute\('style'", div_body)
        and "style.width =" not in div_body
        and "+ 'px'" not in div_body.replace("divider.style", "CHROME"),
    )

    # ── D4: the boundary ───────────────────────────────────────────────────
    print("\n-- D4: a slide has a frame; a page has a viewport --")
    kernel = compose_kernel_style_element()
    _check(
        "a slide IS a containing block, unconditionally (D3's premise, in CSS)",
        "\n.slide { position: relative; }" in kernel,
    )
    _check(
        "the frame does not depend on an unrelated token (pagenum owns only its counter)",
        'html[data-pagenum="on"] .slide { counter-increment: slide; }' in kernel,
    )
    _check(
        "a slide keeps its responsive EXEMPTION (a fixed stage does not reflow)",
        '[data-arrange]:not(.slide) .cols { flex-direction: column; }' in kernel,
    )
    _check(
        "the deck is still a fixed 16:9 stage (what makes it boundable at all)",
        "aspect-ratio: 16 / 9" in STUDIO_LAYOUTS["deck"]["skin"]
        and "overflow: hidden" in STUDIO_LAYOUTS["deck"]["skin"],
    )
    # No continuous value has entered ANY token — D4's opt-out, mechanically.
    continuous = {
        k: t
        for k, t in STUDIO_TOKENS.items()
        if not all(re.fullmatch(r"[a-z0-9-]+", v["value"]) for v in t["values"])
    }
    _check(
        "every token value is still an enumerable slug (no continuous value has landed)",
        not continuous,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
