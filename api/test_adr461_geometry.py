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
    # No continuous value has entered any TOKEN — a continuous value belongs to
    # a MEASURE (below), which is a different mechanism with a different bound.
    # A token smuggling `761px` is the boundary crossed without D4's argument.
    continuous = {
        k: t
        for k, t in STUDIO_TOKENS.items()
        if not all(re.fullmatch(r"[a-z0-9-]+", v["value"]) for v in t["values"])
    }
    _check(
        "every token value is still an enumerable slug (continuous belongs to a measure)",
        not continuous,
    )

    # ── D4: the measure — mechanism enumerable, value not ───────────────────
    print("\n-- D4: the one continuous property, bounded by a frame --")
    from services.studio import MEASURE_GRAINS, STUDIO_MEASURES

    _check("the measures registry exists", bool(STUDIO_MEASURES))
    for k, m in STUDIO_MEASURES.items():
        # THE INVARIANT D4 PRESERVES IN SUBSTANCE: the kernel still pre-declares
        # every selector it matches. It cannot pre-declare `[data-w="761"]` —
        # which is why `Fixed` failed as a token — but it CAN pre-declare one
        # rule reading a custom property. Mechanism enumerable, value not.
        _check(
            f"measure '{k}': its MECHANISM is pre-declared (var({m['css_var']}))",
            f"var({m['css_var']}," in kernel,
        )
        _check(
            f"measure '{k}': the var has a FALLBACK (garbage degrades to natural, never zero)",
            f"var({m['css_var']}, auto)" in kernel,
        )
        _check(
            f"measure '{k}': it is BOUNDED (free within its frame, never unbounded)",
            isinstance(m["min"], int) and isinstance(m["max"], int) and m["min"] < m["max"],
        )
        # THE BOUNDARY. deck + media only. A page reflows and has no frame; a
        # measure there would have no answer at 40rem, with per-breakpoint
        # editing refused (ADR-456 D3). This check IS ADR-461 D4.
        _check(
            f"measure '{k}': applies ONLY where a frame bounds it (deck + media)",
            set(m["applies"]) <= MEASURE_GRAINS and set(m["applies"]),
        )
        _check(
            f"measure '{k}': no document/article/page grain has leaked in",
            not any(g in str(m["applies"]) for g in ("document", "article", "page")),
        )
    _check(
        "the kernel scopes measures to the frame (.slide / media blocks only)",
        ".slide [data-w]" in kernel and '[data-block="figure"][data-w]' in kernel,
    )
    _check(
        "the vocabulary serves measures WITH their bound (the FE invents nothing)",
        '"measures"' in (ROOT / "api/routes/studio.py").read_text(),
    )

    # The op: writes both halves into the ONE source file, clamped.
    ops = (WEB / "components/studio/artifactOps.ts").read_text()
    sm = re.search(r"export function setMeasure\(([\s\S]*?)\n\}", ops)
    sm_body = sm.group(1) if sm else ""
    _check("setMeasure exists", bool(sm))
    _check(
        "it CLAMPS to the kernel's bound (a bad message cannot author unbounded)",
        "Math.max(spec.min, Math.min(spec.max," in sm_body,
    )
    _check(
        "it preserves the artifact's own style declarations (never stomps)",
        "!d.startsWith(`${spec.cssVar}:`)" in sm_body,
    )
    _check(
        "a byte-identical write produces NO revision (the setToken convention)",
        "if (el.outerHTML === before) return null;" in sm_body,
    )
    _check(
        "clearing removes BOTH halves (absence = the natural layout)",
        "el.removeAttribute(attr)" in sm_body and "el.removeAttribute('style')" in sm_body,
    )
    # The gesture: third bindGesture caller, posts a PERCENT of the frame.
    _check(
        # ADR-466 P8: the lone grip grew into the bounding box — body drag +
        # corner handles, every one riding the SAME gesture primitive.
        "the bounding box rides the ONE gesture primitive (body + handles)",
        "bindGesture(box, function () { return selBlock && positionable(selBlock) ? selBlock : null; }" in proj
        and "bindGesture(h, function () { return selBlock; }" in proj,
    )
    _check(
        "it reports a PERCENT OF THE FRAME, not a pixel (the bound is structural)",
        "br.width / (fr.width || 1)) * 100" in proj,
    )
    _check(
        "an UNFRAMED block gets no box (the boundary is felt, not just documented)",
        "function isMeasurable(block)" in proj
        and "if (editing == null && sel && sel.isConnected && isMeasurable(sel)) showBox(sel);" in proj,
    )
    # The handle follows the SELECTION, not the pointer: it draws at the block's
    # corner, so a hover-scoped handle vanishes exactly as it is reached for.
    # Selection is READ from the pointer runtime (one selection, never two).
    _check(
        "the handle follows the selection, not the pointer (a grip outlives the reach)",
        "window.__yarnnnSelected = function () { return cur; };" in proj
        and "window.__yarnnnSelected ? window.__yarnnnSelected() : null" in proj,
    )
    # The SAME gate decides both affordances, so a block can never show both:
    # framed -> handles, flowing -> gutter. The gutter's own row hit-test skips
    # any framed block (a placed thing has no row to be inserted between).
    _check(
        "a framed block gets no gutter (one gate, two affordances, never both)",
        "if (isMeasurable(b)) continue;" in proj,
    )
    # The preview must speak the COMMIT's units, or the block jumps on release.
    # The two questions are separate functions on purpose: "is this measurable?"
    # (responsive obligation — the D4 gate) vs "which rectangle is it a percent
    # OF?". Conflating them made every deck block measure against the SLIDE even
    # when a half-width column laid it out.
    _check(
        "the GATE and the RECTANGLE are different questions (isMeasurable vs "
        "measurableFrame) — conflating them was the frame bug",
        "function isMeasurable(block)" in proj and "function measurableFrame(block)" in proj
        and "if (!isMeasurable(block)) return null;" in proj,
    )
    _check(
        "the frame is the NEAREST layout parent, not always the slide",
        "block.closest('.col, [data-slot]')" in proj,
    )
    _check(
        "the resize preview is a percent, not a pixel (no jump at the drop)",
        "block.style.width = pct + '%';" in proj,
    )
    _check(
        "the surface clamps from the SERVED registry, never a hardcoded bound",
        "vocabulary?.measures?.find" in surface and "min: s.min" in surface,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
