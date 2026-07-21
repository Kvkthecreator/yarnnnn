"""
IMAGES — the composition app (ADR-472).

The second authoring app (ADR-468 D1), carved out of Studio by ADR-472. Its
artifact is a **rendered raster**: a marketing ad ends life as a 1080×1080 PNG,
not as the HTML that composed it. That single fact is why IMAGES is an app and
not a Studio layout —

    Studio:  the file IS the deliverable        (a deck, a doc)
    IMAGES:  the composition is the SOURCE,
             the raster is a DERIVATION          (ADR-472 D4)

and the derivation is a first-class attributed revision (ADR-427 binary
Category-1 + ADR-448 `derived_from`), which is a relationship Studio's model
structurally lacks (its export is Print/PDF — it LEAVES the system).

── WHAT THIS MODULE OWNS ────────────────────────────────────────────────────
The stage: its dimensions, its scaffold, its skin, its arrangement. Dimensions
are REAL (W×H in pixels, ADR-472 D3), not the enumerated aspect slugs ADR-471
had to use because a property token's values must be enumerable (ADR-461). A
stage is born at a size the way a Canva design is.

── WHAT THIS MODULE DOES *NOT* OWN ──────────────────────────────────────────
The OBJECT LAYER — position/size/stacking (`x`/`y`/`z`/`w`/`h` under the
`block-staged` grain), the `.slide` frame class, the kernel CSS measure rules,
the auto-fit. Those live in `services/studio.py` as the SHARED KERNEL and are
consumed by both apps (ADR-472 D2). IMAGES borrows nothing and forks nothing:
one implementation, two consumers. The frame class is the grain's boundary,
which is why an IMAGES stage carries `class="slide"` — a deliberate inheritance
(ADR-471 D-a), now honestly named.

Canonical reference: docs/adr/ADR-472-images-as-a-first-class-app.md
"""

from __future__ import annotations

from typing import Optional, TypedDict

# ---------------------------------------------------------------------------
# Stage presets (ADR-472 D3) — dimensions FIRST.
# ---------------------------------------------------------------------------
#
# Creation begins with the stage's size (the Canva/Fabric model), not with a
# heading that later acquires a ratio. These are REAL pixel dimensions: the
# render target (D4/D5) rasterizes at exactly this size, so "Square" is 1080×1080
# because that is what an Instagram post is — not because it is "1:1".
#
# A preset is a convenience, never a constraint: `custom` carries any W×H. The
# slug is opaque and stable (ADR-459 D3) — it names the INTENT, and the numbers
# may be corrected without breaking a stored stage, because the stage stores its
# resolved width/height, not its preset slug.


class StagePreset(TypedDict):
    slug: str
    label: str
    width: int
    height: int
    hint: str


STAGE_PRESETS: list[StagePreset] = [
    {"slug": "square", "label": "Square", "width": 1080, "height": 1080,
     "hint": "Instagram / LinkedIn post"},
    {"slug": "story", "label": "Story", "width": 1080, "height": 1920,
     "hint": "Instagram / TikTok story, 9:16"},
    {"slug": "wide", "label": "Wide", "width": 1600, "height": 900,
     "hint": "Presentation still, YouTube thumbnail, 16:9"},
    {"slug": "ad", "label": "Ad", "width": 1200, "height": 628,
     "hint": "Meta / LinkedIn link ad"},
    {"slug": "portrait", "label": "Portrait", "width": 1080, "height": 1350,
     "hint": "Instagram portrait, 4:5"},
    {"slug": "banner", "label": "Banner", "width": 1500, "height": 500,
     "hint": "X / site header"},
]

DEFAULT_PRESET = "square"

#: Bounds. A stage is a raster target, so the ceiling is what a renderer can
#: reasonably produce and a browser can hold — not an arbitrary design limit.
MIN_DIMENSION = 16
MAX_DIMENSION = 8192


def preset(slug: str) -> Optional[StagePreset]:
    """The preset row for a slug, or None."""
    return next((p for p in STAGE_PRESETS if p["slug"] == slug), None)


def resolve_dimensions(
    *,
    preset_slug: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> tuple[int, int]:
    """The stage's real W×H (ADR-472 D3).

    Explicit width/height win (the custom case); else the named preset; else the
    default. Always returns a clamped, integral pair — a stage is never born
    dimensionless, which is the whole point of dimensions-first.
    """
    if width is not None and height is not None:
        w, h = int(width), int(height)
    else:
        p = preset(preset_slug or DEFAULT_PRESET) or preset(DEFAULT_PRESET)
        assert p is not None  # DEFAULT_PRESET is always present
        w, h = p["width"], p["height"]
    clamp = lambda v: max(MIN_DIMENSION, min(MAX_DIMENSION, v))  # noqa: E731
    return clamp(w), clamp(h)


# ---------------------------------------------------------------------------
# The stage (the IMAGES document type) — moved from STUDIO_LAYOUTS["canvas"]
# by ADR-472 D1/D7, and reshaped by D3 (dimensions replace the aspect slug).
# ---------------------------------------------------------------------------
#
# Shape-compatible with a STUDIO_LAYOUTS row on purpose: the posture builder,
# the skeleton builder, and the kernel-CSS retrofit are shared machinery, and a
# divergent row shape would fork them. The app boundary is the MODULE and the
# surface, not a novel data shape.

STAGE = {
    # ADR-473 D2: the owning app. One declaration; the kernel derives from it
    # what this app may create, which artifacts are its own, and where the
    # Finder's open verb routes this type.
    "app": "images",
    "label": "Image",
    "mode": "paged",
    "description": "A composed visual — layered objects on a sized stage.",
    "flow": (
        "each stage is <section class=\"slide\" data-arrange=\"free\"> — a "
        "fixed-SIZE frame, not a prose page. Position EVERY block "
        "(data-x/data-y markers with style=\"--yx:N%;--yy:N%\") and size where "
        "it matters (data-w with --yw); overlapping blocks order with data-z "
        "(--yz, higher = in front). Text is real text (heading blocks); images "
        "are cited figures (data-ref / data-ref-rev), never inline bytes; "
        "shapes are inline <svg> inside a block. The stage's pixel size rides "
        "the root as data-w/data-h (ADR-472 D3) — it is a DIMENSION, not a "
        "ratio slug. One visual statement per stage — compose it like a "
        "poster, not a document."
    ),
    # The skin. Note what is ABSENT: no aspect-slug mapping. The stage's box
    # comes from its real dimensions, published by the FE as --stage-w/--stage-h
    # (ADR-472 D3) — a continuous value, which is exactly what a property token
    # could not express and why the aspect token is deleted rather than moved.
    "skin": """
    body { background: var(--deck-stage, #e8e4de); }
    /* The stage is a fixed-SIZE frame. Width/height ride the root as real
       pixels; aspect-ratio falls back to square only when a legacy stage
       carries no dimensions. Padding 0 so a positioned block's percent-of-frame
       is a percent of the visible stage. */
    /* Unitless siblings (--stage-wn/--stage-hn) feed aspect-ratio, which
       cannot consume a px length; the px pair sizes the box. Both are written
       inline at creation (services/images.py::stage_root_attrs) — a legacy
       stage with neither falls back to 1080 square rather than collapsing. */
    .slide {
      position: relative;
      width: var(--stage-w, 1080px);
      max-width: 100%;
      aspect-ratio: var(--stage-wn, 1080) / var(--stage-hn, 1080);
      margin: 0 auto;
      padding: 0;
      background: var(--page-bg, #fffdf9);
      overflow: hidden;
    }
    .slide .kicker { color: var(--accent); font-size: var(--text-sm, 0.85rem);
                     letter-spacing: 0.08em; text-transform: uppercase; }
    .slide [data-block="figure"] img { width: 100%; height: 100%;
                                       object-fit: contain; }
""".strip("\n"),
    "scaffold": """<section class="slide" data-arrange="free">
  <p class="kicker" data-block="heading" data-block-id="k1" data-x="8" data-y="8" style="--yx:8%;--yy:8%">Untitled image</p>
  <h1 data-block="heading" data-block-id="t1" data-x="8" data-y="16" data-w="70" style="--yx:8%;--yy:16%;--yw:70%">The visual statement.</h1>
</section>""",
}

#: The stage's slug — the document type IMAGES owns. Opaque + stable.
STAGE_SLUG = "image"

#: Layout table, shaped like STUDIO_LAYOUTS so shared machinery reads either.
IMAGES_LAYOUTS: dict[str, dict] = {STAGE_SLUG: STAGE}

#: The stage has ONE arrangement — the open stage. No slots: the stage IS the
#: arrangement, and blocks land positioned, not slotted. A future named
#: composition (thirds, hero+copy) is a new row here, generated by decomposed
#: generation (ADR-472 D6) rather than hand-authored.
IMAGES_ARRANGEMENTS: dict[str, dict] = {
    STAGE_SLUG: {
        "free": {
            "label": "Free",
            "description": "An open stage — position everything.",
            "grain": "page",
            "slots": [],
            "fragment": """<section class="slide" data-arrange="free">
  <h2 data-block="heading" data-block-id="t1" data-x="8" data-y="12" style="--yx:8%;--yy:12%">New stage</h2>
</section>""",
        },
    },
}


# IMAGES registers its stage with the shared machinery (ADR-472 D2). The
# builders (skeleton, posture, artifact-kind, arrangement grammar) are kernel
# code both apps consume — registration is how IMAGES reaches them without
# Studio importing an app or the builders being forked.
from services.studio import register_layouts  # noqa: E402  (registration side-effect)

register_layouts(IMAGES_LAYOUTS, IMAGES_ARRANGEMENTS)


def stage_root_attrs(width: int, height: int) -> str:
    """The root attributes + inline vars carrying a stage's dimensions (D3).

    Emitted onto <html> at creation. `data-w`/`data-h` are the MARKERS (what a
    reader, a migration, or the renderer keys on); the inline `--stage-w` /
    `--stage-h` are the VALUES the skin consumes — the same attribute/property
    split the ADR-461 measures use.

    The value rides inline rather than through a CSS rule because a dimension is
    CONTINUOUS: there is no enumerable set of rules to write, which is precisely
    why the ADR-471 aspect token could not express this and was deleted (D3).
    """
    w, h = int(width), int(height)
    return (
        f'data-w="{w}" data-h="{h}" '
        f'style="--stage-w:{w}px;--stage-h:{h}px;--stage-wn:{w};--stage-hn:{h}"'
    )


def stage_dimensions(html: str) -> tuple[int, int]:
    """Read a stage's real dimensions back off its root (ADR-472 D3).

    The inverse of `stage_root_attrs` — used by the renderer (D4/D5) to
    rasterize at exactly the authored size, and by any reader that needs the
    box. Falls back to the default preset for a stage authored before
    dimensions existed (an ADR-471 canvas), so a legacy artifact renders square
    rather than dimensionless.
    """
    import re as _re

    def _attr(name: str) -> Optional[int]:
        m = _re.search(rf'<html[^>]*\bdata-{name}="(\d+)"', html or "")
        return int(m.group(1)) if m else None

    default = preset(DEFAULT_PRESET)
    assert default is not None
    return (_attr("w") or default["width"], _attr("h") or default["height"])


__all__ = [
    "STAGE",
    "STAGE_SLUG",
    "STAGE_PRESETS",
    "DEFAULT_PRESET",
    "IMAGES_LAYOUTS",
    "IMAGES_ARRANGEMENTS",
    "MIN_DIMENSION",
    "MAX_DIMENSION",
    "preset",
    "resolve_dimensions",
    "stage_root_attrs",
    "stage_dimensions",
]
