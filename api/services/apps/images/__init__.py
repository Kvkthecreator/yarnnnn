"""IMAGES — the composition app (ADR-472), as a package.

    stage.py     — the stage: presets, real dimensions, scaffold, skin.
                   Pure data + pure functions. No I/O, no engine.
    generate.py  — the RASTER BACKENDS (ADR-475): the rented engine behind a
                   seam, resolved by `services/capabilities.py` for the lane's
                   `GenerateImage`.

`decompose.py` + `compose.py` are DELETED (2026-09-08). They planned a brief
into layers and wrote the stage's markup server-side, for a `POST
/api/images/compose` that had zero client callers its whole life — while
`decompose.py` itself said the judgment "belongs to an agent, not to a rule
table". It does: Designer composes a stage through the ORDINARY uniform lane
verbs, driven before deleting (three layers, each placed and depth-stamped,
the declared ground honoured, via `WriteFile`). Keeping both would have been
two implementations of one act.

(There is no render.py. Export to a flat PNG is CLIENT-SIDE — the browser
rasterizes the stage it already displays; the removed server rasterizer only
ever 503'd in prod. See ADR-475 §13.)

Canonical reference: docs/adr/ADR-472-images-as-a-first-class-app.md
                     docs/adr/ADR-475-decomposed-generation.md
"""

from __future__ import annotations

from services.apps.images.stage import (  # noqa: F401
    DEFAULT_PRESET,
    IMAGES_ARRANGEMENTS,
    IMAGES_LAYOUTS,
    MAX_DIMENSION,
    MIN_DIMENSION,
    STAGE,
    STAGE_PRESETS,
    STAGE_SLUG,
    preset,
    resolve_dimensions,
    stage_dimensions,
    stage_root_attrs,
)

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
