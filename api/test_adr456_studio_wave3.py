"""ADR-456 Wave-3 regression gate — the builder look: cited backgrounds, the
page layout, and the theme contract.

Static/structural checks (no DB, no LLM):
  1. The background mechanism: data-ref-kind="background" is a PROJECTION
     concern (backgroundImage on the projected DOM; the source stays citation
     + tokens, never inline style); a background failure never touches the
     band's children; scrim/bg-pos are page-bg-gated tokens the kernel CSS
     interprets; the toned/scrimmed button inverts.
  2. THE SKIN-STOMP FIX: resolveOne must never resolve INTO a <style> element
     — the marked data-skin/data-kernel elements carry data-ref as an EDGE
     citation, and resolving them replaced the skin's CSS with the manifest's
     escaped text (latent since ADR-449).
  3. The page layout: fourth STUDIO_LAYOUTS row + its band family (hero ·
     content · feature-grid · testimonial · cta · footer); templates derive;
     the generic non-slide .cols makes multi-column bands real outside decks
     (the pre-existing document/article two-column gap).
  4. The theme contract: kernel chrome consumes --radius (with fallbacks);
     the design-system recipe names the five contract variables; the Design
     tab reads the applied skin's vars (read-only panel) and gates measure to
     document/article only.
  5. Kernel CSS v4 + the FE ops (setPageBackground/removePageBackground) +
     the Design tab's background picker.

Run:  cd api && python3 test_adr456_studio_wave3.py
Exit code is authoritative (0 = pass).
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    from services.derive_recipes import DERIVE_RECIPES
    from services.studio import (
        STUDIO_ARRANGEMENTS,
        STUDIO_KERNEL_CSS,
        STUDIO_KERNEL_CSS_VERSION,
        STUDIO_LAYOUTS,
        STUDIO_TEMPLATES,
        STUDIO_TOKENS,
        build_skeleton,
        build_studio_posture,
    )

    # ── 1. The background mechanism ──────────────────────────────────────
    _check("scrim + bg-pos: page-bg-gated tokens",
           STUDIO_TOKENS.get("scrim", {}).get("applies") == ["page-bg"]
           and STUDIO_TOKENS.get("bg-pos", {}).get("applies") == ["page-bg"])
    _check("kernel CSS interprets the background pair (cover, scrim, focus)",
           '[data-ref-kind="background"]' in STUDIO_KERNEL_CSS
           and '[data-scrim="dark"]::before' in STUDIO_KERNEL_CSS
           and '[data-bg-pos="top"]' in STUDIO_KERNEL_CSS)
    _check("band content sits above the scrim (position layering)",
           '[data-ref-kind="background"] > * { position: relative; }' in STUDIO_KERNEL_CSS)
    _check("the toned/scrimmed button inverts (stays visible on a filled band)",
           '[data-scrim="dark"] p[data-block="button"] a' in STUDIO_KERNEL_CSS)

    # ── 2. The skin-stomp fix + projection behavior (FE source) ──────────
    web = Path(__file__).resolve().parent.parent / "web"
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    _check("resolveOne never resolves INTO a style element (the skin-stomp fix)",
           "if (el.tagName === 'STYLE') return;" in proj)
    _check("background resolution sets backgroundImage on the PROJECTED DOM",
           "kind === 'background'" in proj
           and "style.backgroundImage" in proj)
    _check("a background failure never touches the band's children",
           "if (kind === 'background') return;" in proj)

    # ── 3. The page layout ───────────────────────────────────────────────
    _check("page is the fourth layout (templates derive)",
           "page" in STUDIO_LAYOUTS and "page" in STUDIO_TEMPLATES)
    _check("the page band family",
           set(STUDIO_ARRANGEMENTS.get("page", {}))
           == {"hero", "content", "feature-grid", "testimonial", "cta", "footer"})
    _check("the hero leads the page scaffold",
           'data-arrange="hero"' in build_skeleton("page")
           and 'data-template="page"' in build_skeleton("page"))
    _check("cta band rides the tone token (no new mechanism)",
           'data-tone="accent"' in STUDIO_ARRANGEMENTS["page"]["cta"]["fragment"])
    _check("feature-grid declares three flow slots",
           [s["role"] for s in STUDIO_ARRANGEMENTS["page"]["feature-grid"]["slots"]]
           == ["flow", "flow", "flow"])
    # The base rule later widened to all [data-arrange] (kernel evolution); the
    # deck exemption lives in the responsive STACKING rule, which is the part
    # that must stay non-slide (a deck slide is a fixed stage, never stacks).
    _check("the generic .cols is real + deck exempt from responsive stacking",
           "[data-arrange] .cols { display: flex" in STUDIO_KERNEL_CSS
           and "[data-arrange]:not(.slide) .cols { flex-direction: column; }" in STUDIO_KERNEL_CSS)

    # ── 4. The theme contract ────────────────────────────────────────────
    _check("kernel chrome consumes --radius (with fallbacks)",
           "var(--radius, 6px)" in STUDIO_KERNEL_CSS
           and "var(--radius, 4px)" in STUDIO_KERNEL_CSS)
    _check("the design-system recipe names the five contract variables",
           all(v in DERIVE_RECIPES["design-system"]["instructions"]
               for v in ("--ink", "--paper", "--muted", "--accent", "--radius")))
    design = (web / "components/studio/StudioDesignTab.tsx").read_text()
    _check("Design tab: the read-only theme panel parses the applied skin's vars",
           "skinVars" in design and "style[data-skin]" in design)
    _check("Design tab: measure gated to document/article only (page = full-width bands)",
           "layout === 'document' || layout === 'article'" in design)
    _check("Design tab: the background picker + page-bg token gate",
           "onSetPageBackground" in design and "page-bg" in design
           and "Set background…" in design)

    # ── 5. Version + ops + posture ───────────────────────────────────────
    # Pinned `== 4` when W3 shipped; the version kept moving (design systems v9,
    # the position layer v10) and this stale pin made the gate red since. What
    # W3 actually needs: the version is AT LEAST its own bump, and the skeleton
    # bakes whatever the current version is (the retrofit contract).
    _check("kernel CSS version >= 4 and the skeleton bakes the CURRENT version",
           STUDIO_KERNEL_CSS_VERSION >= 4
           and f'data-kernel-v="{STUDIO_KERNEL_CSS_VERSION}"' in build_skeleton("page"))
    ops = (web / "components/studio/artifactOps.ts").read_text()
    _check("setPageBackground/removePageBackground land through the one door",
           "export function setPageBackground" in ops
           and "export function removePageBackground" in ops
           and "'data-ref-kind', 'background'" in ops.replace('", "', "', '").replace('"', "'"))
    posture = build_studio_posture("/workspace/operation/x/p.html", build_skeleton("page"))
    _check("posture teaches the cited background (never inline style)",
           'data-ref-kind="background"' in posture and "data-scrim=" in posture)
    _check("posture lists the page bands (registry-derived)",
           "hero — " in posture and "feature-grid — " in posture)

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
