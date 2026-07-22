"""IMAGES — the composition app (ADR-472), as a package.

The module became a package when generation arrived (ADR-475): the stage's
constants and the generation workflow are different concerns with different
dependencies (one is pure data, the other reaches a rented engine), and a
single 700-line module would have fused them.

    stage.py     — the stage: presets, real dimensions, scaffold, skin.
                   Pure data + pure functions. No I/O, no engine.
    generate.py  — decomposed generation (ADR-475): a prompt becomes a NAMED
                   LAYER PLAN, each leaf routed by kind, composed into the
                   layered stage. The engine is RENTED behind a seam.
    decompose.py — the plan: brief → named layer plan (resident or heuristic).
    compose.py   — the orchestrator: generate per leaf, land N+1 revisions.

(There is no render.py. Export to a flat PNG is CLIENT-SIDE — the browser
rasterizes the stage it already displays — a fast-follow, not a server concern;
the removed server rasterizer only ever 503'd in prod. See ADR-475 §13.)

Everything the pre-package module exported is re-exported here, so
``from services.images import STAGE_SLUG`` reads exactly as it did before the
split — the file moved, the import surface did not.

Canonical reference: docs/adr/ADR-472-images-as-a-first-class-app.md
                     docs/adr/ADR-475-decomposed-generation.md
"""

from __future__ import annotations

from services.images.stage import (  # noqa: F401
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
