"""ADR-453 regression gate — the Studio property layer (tokens · the Design
tab · the grain-aligned verbs · the arrangement-as-interaction-contract).

Static/structural checks (no DB, no LLM):
  1. STUDIO_TOKENS: the six v1 families, valid shapes, valid `applies` values,
     absence-is-default (no token declares a written default).
  2. The kernel CSS + the marked element: every token family has an
     interpreting selector; compose_kernel_style_element is marked + versioned;
     build_skeleton bakes it (all three layouts); cascade order (unmarked
     layout style before data-kernel).
  3. The interaction contract: slot roles are the gate — the media role exists
     (picture-with-caption / lead-image), section-header ships the first token
     use (data-tone), fragments stay id-annotated.
  4. The posture: the Property-tokens section derives from the registry
     (one grammar — controls + lane never drift); the layout-switch rule
     protects BOTH marked elements.
  5. The served vocabulary route: tokens + media_kinds + kernel element +
     design_systems ride the one endpoint; the resolve endpoint exists.
  6. The FE half (read as text): artifactOps carries the verb completion
     (setToken/delete/duplicate/move at both grains + applySkin/removeSkin +
     the kernel upsert); the runtime carries slot hover + the grain ladder +
     the role-gated add-here payload; the Design tab + toolbar exist with the
     realigned verbs; the old mixed-grain menu is deleted.

Run:  cd api && python3 test_adr453_property_layer.py
Exit code is authoritative (0 = pass).
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    from services.studio import (
        MEDIA_BLOCK_KINDS,
        STUDIO_ARRANGEMENTS,
        STUDIO_KERNEL_CSS,
        STUDIO_KERNEL_CSS_VERSION,
        STUDIO_TOKENS,
        build_skeleton,
        build_studio_posture,
        compose_kernel_style_element,
    )

    # ── 1. The token registry (D1; document grain added by ADR-455) ──────
    _check(
        "the ADR-453 six + the ADR-455 document families",
        {"align", "tone", "height", "fit", "ratio", "valign", "font", "measure"}
        <= set(STUDIO_TOKENS),
    )
    valid_applies = {"block", "media", "page", "page-multicol", "page-deck", "document",
                     "document-flow", "document-deck",  # document-deck: ADR-456 W1
                     "page-bg"}  # page-bg: ADR-456 W3 (cited background present)
    _check(
        "token rows carry label/applies/values/description",
        all(
            t.get("label")
            and isinstance(t.get("applies"), list)
            and set(t["applies"]) <= valid_applies
            and t.get("values")
            and all(v.get("value") and v.get("label") for v in t["values"])
            and t.get("description")
            for t in STUDIO_TOKENS.values()
        ),
    )
    _check(
        "absence is the default (no family declares a written default value)",
        all("default" not in t for t in STUDIO_TOKENS.values()),
    )
    _check("media kinds = figure + chart (+ gallery, ADR-456 W1)",
           MEDIA_BLOCK_KINDS == {"figure", "chart", "gallery"})

    # ── 2. The kernel CSS + the marked element (D2) ──────────────────────
    _check(
        "every token family has an interpreting selector",
        all(f"[data-{key}=" in STUDIO_KERNEL_CSS for key in STUDIO_TOKENS),
    )
    # Per-VALUE coverage (ADR-461 B1, 2026-07-15). The family check above passes
    # if ONE value renders — which is how `align: start` survived: declared in
    # the registry, no `[data-align="start"]` rule anywhere, so picking "Left"
    # wrote an attribute that rendered nothing. Two UI states, one visual
    # result. A token the Design tab OFFERS must do something when picked; a
    # default belongs in the ABSENCE of the attribute (the pad/valign/fit
    # convention), never as a declared-but-inert value.
    unrendered = {
        key: [
            v["value"]
            for v in t["values"]
            if f'[data-{key}="{v["value"]}"]' not in STUDIO_KERNEL_CSS
        ]
        for key, t in STUDIO_TOKENS.items()
    }
    unrendered = {k: v for k, v in unrendered.items() if v}
    _check(
        "every OFFERED token value renders (no declared-but-inert values)",
        not unrendered,
    )
    if unrendered:
        print(f"       ↳ declared but never rendered: {unrendered}")
    _check(
        "tokens theme through custom properties, never raw-only color",
        "var(--accent" in STUDIO_KERNEL_CSS and "var(--ink" in STUDIO_KERNEL_CSS,
    )
    kel = compose_kernel_style_element()
    _check(
        "kernel element is marked + versioned",
        'data-kernel="true"' in kel and f'data-kernel-v="{STUDIO_KERNEL_CSS_VERSION}"' in kel,
    )
    for layout in ("document", "deck", "article"):
        sk = build_skeleton(layout)
        _check(
            f"skeleton bakes the kernel element after the layout style ({layout})",
            'data-kernel="true"' in sk and sk.index("<style>") < sk.index("data-kernel"),
        )

    # ── 3. The interaction contract (D5) ─────────────────────────────────
    deck = STUDIO_ARRANGEMENTS["deck"]
    # ADR-481 D1 (2026-07-22): article's `lead-image` retired with every other
    # flow arrangement. The media ROLE — what this check is actually about — is
    # unchanged, carried by the deck's two media rows (picture-with-caption +
    # the W1 full-bleed). Verified against the registry: `page`'s band family is
    # heading/flow only, so deck is where the role lives.
    _check(
        "the media role exists (picture-with-caption + full-bleed)",
        any(s["role"] == "media" for s in deck["picture-with-caption"]["slots"])
        and any(s["role"] == "media" for s in deck["full-bleed"]["slots"]),
    )
    _check(
        "section-header ships the first token use (data-tone)",
        'data-tone="inverse"' in deck["section-header"]["fragment"],
    )
    _check(
        "new fragments stay block-id annotated",
        'data-block-id' in deck["picture-with-caption"]["fragment"]
        and 'data-block-id' in deck["section-header"]["fragment"],
    )

    # ── 4. The posture (one grammar, both hands) ─────────────────────────
    posture = build_studio_posture("/workspace/operation/x/deck.html", build_skeleton("deck"))
    _check("posture carries the Property-tokens section", "## Property tokens" in posture)
    _check(
        "posture token lines derive from the registry",
        all(f"data-{key}=" in posture for key in STUDIO_TOKENS),
    )
    _check(
        "layout-switch rule protects BOTH marked elements",
        "UNMARKED" in posture
        and 'data-kernel="true"' in posture
        and 'data-skin="true"' in posture,
    )
    _check("posture forbids inline style for tokens", 'style=""' in posture)

    # ── 5. The served surface (routes) ───────────────────────────────────
    routes_src = Path("routes/studio.py").read_text()
    _check(
        "vocabulary serves tokens + media_kinds + kernel element + design systems",
        all(
            key in routes_src
            for key in ('"tokens"', '"media_kinds"', '"kernel_style_element"', '"design_systems"')
        ),
    )
    _check(
        "the resolve endpoint exists and composes, never writes",
        "/studio/design-systems/resolve" in routes_src
        and "compose_skin_element" in routes_src,
    )

    # ── 6. The FE half (read as text) ────────────────────────────────────
    web = Path(__file__).resolve().parent.parent / "web"
    ops = (web / "components/studio/artifactOps.ts").read_text()
    _check(
        "artifactOps: the verb completion",
        all(
            f"export function {fn}(" in ops
            for fn in (
                "setToken",
                "deleteBlock",
                "duplicateBlock",
                "moveBlock",
                "deletePage",
                "duplicatePage",
                "movePage",
                "applySkin",
                "removeSkin",
            )
        ),
    )
    _check(
        "artifactOps: the kernel upsert (versioned, cascade before data-skin)",
        "ensureKernelStyle" in ops and "data-kernel-v" in ops and "insertBefore" in ops,
    )
    _check(
        "artifactOps: page anchoring extends to pageIndex over the shared PAGE_SEL",
        "pageIndex" in ops and "'section.slide, [data-arrange]'" in ops,
    )

    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    _check(
        "runtime: slot hover outline + name label",
        "[data-slot]:hover" in proj and "content: attr(data-slot)" in proj,
    )
    _check(
        "runtime: the grain ladder (slot + page selection) + shared page index",
        "yarnnn-point" in proj and "pageIndexOf" in proj and "arrangeOf" in proj,
    )
    _check(
        "runtime: add-here carries arrange + pageIndex (the role gate's lookup key)",
        proj.count("yarnnn-add-here") >= 1 and "arrange:" in proj,
    )

    toolbar = (web / "components/studio/StudioToolbar.tsx").read_text()
    _check(
        # ADR-466 D5 amends ADR-453 D3: the toolbar pairs the page verbs —
        # New ‹noun› beside Layout (re-lay the CURRENT page), the PowerPoint
        # pair. The old single mixed-grain "Arrange ▾" menu stays deleted; the
        # Layout gallery is the same grammar as the Properties page scope
        # (arrangementCarryNote is the shared forewarning).
        "toolbar: the page-verb pair (New ‹noun› · Layout), carry-note shared (ADR-466 D5)",
        "New {pageNoun}" in toolbar
        and "onApplyArrangement" in toolbar
        and "arrangementCarryNote" in toolbar,
    )
    _check(
        "toolbar: the gallery renders derived wireframes",
        "ArrangementThumb" in toolbar,
    )
    _check(
        "the old StudioInsertMenu is deleted (Singular Implementation)",
        not (web / "components/studio/StudioInsertMenu.tsx").exists(),
    )

    design_tab = (web / "components/studio/StudioDesignTab.tsx").read_text()
    _check(
        "Design tab: scope-switching (document/page/slot/block)",
        all(f"'{s}'" in design_tab for s in ("document", "page", "slot", "block")),
    )
    _check(
        "Design tab: homes the design-system picker (ADR-449 D5)",
        "onApplyDesignSystem" in design_tab and "design_systems" in design_tab,
    )
    _check(
        "Design tab: tokens read from the SOURCE (derived, never stored)",
        "DOMParser" in design_tab and "getAttribute(`data-${t.key}`)" in design_tab,
    )

    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    _check(
        "surface: Chat | Design tabs, lane stays mounted under Design",
        "rightTab" in surface and "'chat' ? 'flex' : 'hidden'" in surface,
    )
    _check(
        "surface: role-gated add-here (media → the Design tab's picker)",
        "role === 'media'" in surface,
    )

    print()
    failed = [label for label, ok in _results if not ok]
    print(f"{len(_results) - len(failed)}/{len(_results)} checks passed")
    if failed:
        print("FAILED:")
        for f in failed:
            print(f"  - {f}")
    return not failed


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
