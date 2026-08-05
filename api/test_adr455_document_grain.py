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
    # ADR-487 D9 re-pin: the `font` token keeps its Ag preview and its resolved
    # face stacks, but the CHIP ROW is gone — it is a StyleSelect now
    # (FaceTokenSelect), the same shape block scope uses, because one word
    # ("Typography") rendering two ways in one panel was the drift. The
    # CAPABILITY asserted here is unchanged: an Ag preview per face, painted
    # with what the face resolves to.
    _check("Design tab: Ag-preview face select (ADR-487 D9 — one select shape, was FontControl chips)",
           "FaceTokenSelect" in design_tab
           and "Ag" in design_tab
           and "FONT_STACKS" in design_tab
           and "FontControl" not in design_tab)
    # ADR-487 D9 re-pin: the flow gate is DERIVED from the served `mode`
    # (ADR-466), not re-enumerated as a slug list. The old spelling was exactly
    # the flow set written longhand, so a new flow layout would have silently
    # lost its width token here.
    _check("Design tab: document tokens gated by served MODE, not a slug list "
           "(measure = flow layouts only; ADR-456 W3 excluded page too)",
           "document-flow" in design_tab
           and "mode === 'flow'" in design_tab
           and "layout === 'document' || layout === 'article'" not in design_tab)
    _check("Design tab: the skin-override hint (cascade stays honest)",
           "may override" in design_tab)
    # ADR-487 D9 — THE INVARIANT: inside an artifact the system is WORN, never
    # listed. The artifact-side var-list is deleted (it showed the
    # member-INVISIBLE slots the painted controls don't carry, parsed from this
    # artifact's stale copy rather than the resolved system). The var-list parse
    # belongs to the manage panel alone; the tab keeps only the PAINT map.
    _check("Design tab: no var-list — the system is worn, not listed (ADR-487 D9)",
           "parseSkinVars" not in design_tab
           and "isColorValue" not in design_tab
           and "skinVarMap" in design_tab)
    # ADR-487 D9 — and the cue that replaces it NAMES the system and is the
    # ROUTE to it (block scope was a dead end: painted in the system's values,
    # with no way to reach the system).
    _check("Design tab: the applied-system cue names + routes (one component, two scopes)",
           "AppliedSystemCue" in design_tab
           and design_tab.count("<AppliedSystemCue") == 2
           and "onOpenSystem" in design_tab)
    surface_src = (web / "components/studio/StudioSurface.tsx").read_text()
    _check("surface: the manage panel is the SOLE var-list mount (the object register)",
           "parseSkinVars" in surface_src)

    menu = (web / "components/workspace/FileContextMenu.tsx").read_text()
    _check("shared menu: the extraItems extension point (additive, no fork)",
           "extraItems" in menu and "FileMenuExtraItem" in menu)

    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    _check("Copy link + Duplicate live on (re-homed to the Design tab by ADR-458)",
           "copyArtifactLink" in surface and "duplicateArtifact" in surface)
    # ADR-514 D1 re-cut: the FE probe-then-create loop is gone — duplicate is
    # the kernel derivation (DuplicateFile), reached through the ONE shared
    # organize-verbs path.
    _check("Duplicate rides the kernel derivation (organizeVerbs.onDuplicate)",
           "organizeVerbs.onDuplicate" in surface)

    # ADR-518 follow-through: the flow outline died with the mode split — the
    # navigator is the paged strip; block picks ride the structure tree
    # (onSelectNode) and the same scroll bridge below.
    nav = (web / "components/studio/PagedNavigator.tsx").read_text()
    _check("navigator: structure-tree picks are clickable (onSelectNode)",
           "onClick={() => onSelectNode?.(n)}" in nav)

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
