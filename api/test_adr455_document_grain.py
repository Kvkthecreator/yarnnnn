"""ADR-455 regression gate — document-grain tokens · the file-verb completion
· the navigator that earns its place.

Static/structural checks (no DB, no LLM):
  1. The document-grain tokens: font (document, all layouts) + measure
     (document-flow — document/article only); kernel CSS v2 interprets them on
     the ROOT (html[data-font=…]); the retrofit version bumped.
  2. The posture names the root as a token carrier (registry-derived lines
     include the new families — one grammar, both hands).
  3. setToken targets the document grain (the artifact root).
  4. The Design tab's document scope: Ag-preview typography chips + the
     document tokens + the skin-override hint.
  5. The file-verb completion: Copy link + Duplicate ride the shared menu's
     extraItems extension point; Duplicate never overwrites an existing copy.
  6. The navigator: the outline is NAVIGATIONAL (entries carry the heading's
     block id; clicking scrolls via yarnnn-scroll-to-block) and the navigator
     COLLAPSES (desktop toggle).

Run:  cd api && python3 test_adr455_document_grain.py
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
        STUDIO_KERNEL_CSS,
        STUDIO_KERNEL_CSS_VERSION,
        STUDIO_TOKENS,
        build_skeleton,
        build_studio_posture,
    )

    # ── 1. The document-grain tokens ─────────────────────────────────────
    _check("font token: document grain, serif/sans/mono",
           STUDIO_TOKENS.get("font", {}).get("applies") == ["document"]
           and {v["value"] for v in STUDIO_TOKENS["font"]["values"]} == {"serif", "sans", "mono"})
    _check("measure token: document-flow grain (deck excluded), wide",
           STUDIO_TOKENS.get("measure", {}).get("applies") == ["document-flow"]
           and {v["value"] for v in STUDIO_TOKENS["measure"]["values"]} == {"wide"})
    _check("kernel CSS interprets the root grains (html[data-font/measure])",
           'html[data-font="serif"]' in STUDIO_KERNEL_CSS
           and 'html[data-font="sans"]' in STUDIO_KERNEL_CSS
           and 'html[data-font="mono"]' in STUDIO_KERNEL_CSS
           and 'html[data-measure="wide"]' in STUDIO_KERNEL_CSS)
    _check("kernel CSS version >= 2 (the retrofit carries the v2 rules; ADR-456 bumped to 3)",
           STUDIO_KERNEL_CSS_VERSION >= 2
           and f'data-kernel-v="{STUDIO_KERNEL_CSS_VERSION}"' in build_skeleton("document"))

    # ── 2. The posture (one grammar, both hands) ─────────────────────────
    posture = build_studio_posture("/workspace/operation/x/doc.html", build_skeleton("document"))
    _check("posture names the root as a token carrier",
           "artifact root" in posture.lower() and "<html> root element" in posture)
    _check("posture token lines include font + measure (registry-derived)",
           'data-font=' in posture and 'data-measure=' in posture)

    # ── 3–6. The FE half (read as text) ──────────────────────────────────
    web = Path(__file__).resolve().parent.parent / "web"
    ops = (web / "components/studio/artifactOps.ts").read_text()
    _check("setToken targets the document grain (the artifact root)",
           "'block' | 'page' | 'document'" in ops and "doc.documentElement" in ops)

    design_tab = (web / "components/studio/StudioDesignTab.tsx").read_text()
    _check("Design tab: Ag-preview typography chips (FontControl)",
           "FontControl" in design_tab and "Ag" in design_tab and "FONT_STACKS" in design_tab)
    _check("Design tab: document tokens gated by layout (measure = document/article only; "
           "ADR-456 W3 excluded page too)",
           "document-flow" in design_tab
           and "layout === 'document' || layout === 'article'" in design_tab)
    _check("Design tab: the skin-override hint (cascade stays honest)",
           "may override" in design_tab)

    menu = (web / "components/workspace/FileContextMenu.tsx").read_text()
    _check("shared menu: the extraItems extension point (additive, no fork)",
           "extraItems" in menu and "FileMenuExtraItem" in menu)

    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    _check("Copy link + Duplicate live on (re-homed to the Design tab by ADR-458)",
           "copyArtifactLink" in surface and "duplicateArtifact" in surface)
    _check("Duplicate never overwrites an existing copy (probe-then-create)",
           "-copy.html" in surface and "continue; // exists" in surface)

    nav = (web / "components/studio/StudioNavigator.tsx").read_text()
    _check("navigator: outline entries carry the heading block id",
           "blockId: h.getAttribute('data-block-id')" in nav)
    _check("navigator: outline entries are clickable (onSelectHeading)",
           "onSelectHeading" in nav and "onClick={() => onSelectHeading(h.blockId!)}" in nav)

    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    _check("runtime: yarnnn-scroll-to-block (the outline's scroll bridge)",
           "yarnnn-scroll-to-block" in proj)

    _check("surface: the navigator collapses (desktop toggle)",
           "navCollapsed" in surface and "md:hidden" in surface and "PanelLeft" in surface)

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
