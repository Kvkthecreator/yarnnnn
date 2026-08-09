"""ADR-472 — IMAGES as a first-class app: the carve's invariants.

Supersedes test_adr471_canvas.py (the canvas doc type left Studio; its
click-pass-earned posture assertions move here intact, now asserted against the
IMAGES stage). Covers:

  §1  the carve      — canvas is GONE from Studio; the stage lives in IMAGES
  §2  the kernel     — the object layer is SHARED, not forked (block-staged)
  §3  dimensions     — real W×H, presets, clamping, round-trip (D3)
  §4  the posture    — the ADR-471 click-pass assertions, on the stage
  §5  no dual path   — the aspect token is deleted, not ported (D7)

Run:  python3 api/test_adr472_images.py   (NOT pytest — check()-gate.)
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from services import images as im
    from services.studio import (
        MEASURE_GRAINS,
        STUDIO_LAYOUTS,
        STUDIO_MEASURES,
        STUDIO_TOKENS,
        build_skeleton,
        build_studio_posture,
        resolve_layout,
    )

    # ── §1 The carve (D1/D7) ─────────────────────────────────────────────
    _check("canvas is GONE from Studio's layouts", "canvas" not in STUDIO_LAYOUTS)
    _check(
        "the stage lives in IMAGES and resolves through the shared registry",
        im.STAGE_SLUG == "image"
        and im.STAGE_SLUG in im.IMAGES_LAYOUTS
        and resolve_layout("image") is im.STAGE,
    )
    _check(
        "Studio does not offer the stage as one of ITS templates",
        "image" not in STUDIO_LAYOUTS,
    )
    _check(
        "the stage is paged and labelled for the app, not the layout",
        im.STAGE["mode"] == "paged" and im.STAGE["label"] == "Image",
    )
    # The registry keeps first-registration-wins rather than raising (ADR-443
    # §6: no exceptions from services/studio.py), so DISJOINTNESS is asserted
    # here — this is where a slug collision between two apps is actually caught.
    _check(
        "the two apps' layout slug sets are DISJOINT (no silent shadowing)",
        not (set(STUDIO_LAYOUTS) & set(im.IMAGES_LAYOUTS)),
    )

    # ── §2 The shared object layer (D2) ──────────────────────────────────
    # The hazard the coupling audit found: the stage's ENTIRE positioning
    # capability rides a grain that used to be named `block-deck`. If the
    # rename or the sharing regressed, IMAGES gets artboards on which nothing
    # can be positioned — so these are the load-bearing checks.
    _check(
        "the staged grain is `staged` (ADR-542 grain slug; never the deck-shaped name)",
        "staged" in MEASURE_GRAINS and "block-deck" not in MEASURE_GRAINS,
    )
    _check(
        "position + stacking measures apply to the staged grain",
        STUDIO_MEASURES["x"]["grains"] == ("staged",)
        and STUDIO_MEASURES["y"]["grains"] == ("staged",)
        and STUDIO_MEASURES["z"]["grains"] == ("staged",),  # ADR-542: grain slugs
    )
    _check(
        "the stage inherits the frame class the object layer keys on",
        'class="slide"' in im.STAGE["scaffold"]
        and 'class="slide"' in im.IMAGES_ARRANGEMENTS["image"]["free"]["fragment"],
    )
    _check(
        "the stage's scaffold teaches everything-positioned",
        'data-x="8"' in im.STAGE["scaffold"] and "--yx:8%" in im.STAGE["scaffold"],
    )

    # ── §3 Dimensions-first (D3) ─────────────────────────────────────────
    _check(
        "presets carry REAL pixel dimensions",
        all(
            isinstance(p["width"], int) and isinstance(p["height"], int)
            for p in im.STAGE_PRESETS
        )
        and im.preset("square") is not None
        and im.preset("square")["width"] == 1080,
    )
    _check(
        "a named preset resolves to its box",
        im.resolve_dimensions(preset_slug="story") == (1080, 1920)
        and im.resolve_dimensions(preset_slug="ad") == (1200, 628),
    )
    _check(
        "custom dimensions win, and clamp to sane bounds",
        im.resolve_dimensions(width=800, height=600) == (800, 600)
        and im.resolve_dimensions(width=1, height=99999)
        == (im.MIN_DIMENSION, im.MAX_DIMENSION),
    )
    _check(
        "a stage is NEVER born dimensionless (the point of dimensions-first)",
        im.resolve_dimensions() == (1080, 1080),
    )
    attrs = im.stage_root_attrs(1200, 628)
    _check(
        "root attrs carry the marker AND the values (px + unitless for aspect-ratio)",
        'data-w="1200"' in attrs
        and 'data-h="628"' in attrs
        and "--stage-w:1200px" in attrs
        and "--stage-wn:1200" in attrs,
    )
    _check(
        "dimensions round-trip off the root; a legacy stage falls back to square",
        im.stage_dimensions(f"<html data-template='image' {attrs}>".replace("'", '"'))
        == (1200, 628)
        and im.stage_dimensions('<html data-template="image">') == (1080, 1080),
    )

    # ── §4 The posture — ADR-471's click-pass assertions, on the stage ────
    posture = build_studio_posture(
        "operation/x/visual.html", build_skeleton("image", "X")
    )
    _check(
        "the posture admits FIRST COMPOSITION via one complete WriteFile",
        "FIRST COMPOSITION" in posture and "send the FULL content" in posture,
    )
    _check(
        "…and the patch discipline resumes after it",
        "After the first composition, PATCH." in posture,
    )
    _check(
        "placeholders are replaceable; member-authored blocks never",
        "Scaffold PLACEHOLDER blocks" in posture
        and "never dropped and keep their data-block-id" in posture,
    )
    _check(
        "the MEASURES paragraph teaches staged frames + z (not deck-only)",
        "STAGED frame" in posture and "data-z with --yz" in posture,
    )
    _check(
        "the stage's flow prose composes in (everything-positioned, real dimensions)",
        "Position EVERY block" in posture and "data-w/data-h" in posture,
    )

    # ── §5 No dual path (D7) ─────────────────────────────────────────────
    _check(
        "the aspect slug token is DELETED, not ported to IMAGES",
        "aspect" not in STUDIO_TOKENS
        and "data-aspect" not in im.STAGE["skin"]
        and "--stage-aspect" not in im.STAGE["skin"],
    )
    _check(
        "no token anywhere still scopes to the retired document-canvas grain",
        not any(
            "canvas" in (t.get("grains") or ()) for t in STUDIO_TOKENS.values()
        ),
    )

    # ── §6 ADR-488 — the app is INTERNAL: hidden, not unplugged ─────────
    # Images left the user-facing tier pre-beta (unveil bar = polish parity,
    # the ADR-486 D7 registration-is-not-unveil pattern). The gate pins the
    # HIDDEN state so a stray edit can't half-unveil it: hiding is these
    # four facts together, and re-unveiling is a deliberate ADR-488 §5
    # decision that updates this block in the same commit.
    from services.kernel_surfaces import KERNEL_SURFACES

    images_row = next(s for s in KERNEL_SURFACES if s["slug"] == "images")
    _check(
        "registry: images is search-only (ADR-488 — hidden at rest)",
        images_row.get("launcher_tier") == "search-only",
    )
    _check(
        "registry: images is NOT default-pinned (ADR-488 — left the Dock)",
        images_row.get("default_pinned") is False,
    )
    _check(
        "registry: images stays ROUTABLE (unpromoted, not unplugged)",
        images_row.get("route") == "/images"
        and images_row.get("register") == "application",
    )
    prefs_src = (
        Path(__file__).resolve().parent.parent
        / "web/lib/shell/surface-preferences.ts"
    ).read_text()
    kept_block = prefs_src.split("DEFAULT_KEPT_SURFACES: string[] = [", 1)[1].split(
        "];", 1
    )[0]
    _check(
        "FE: 'images' is not in the default Dock (DEFAULT_KEPT_SURFACES)",
        "'images'" not in kept_block.replace("// 'images'", ""),
    )
    _check(
        "FE: the de-seed path exists — a reseed generation names the old "
        "images-bearing default, so seeded-but-uncurated Docks converge",
        "'images'," in prefs_src.split("DOCK_RESEED_GENERATIONS", 1)[1].split("];", 1)[0],
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
