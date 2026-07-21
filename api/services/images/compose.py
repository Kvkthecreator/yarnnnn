"""The composition act — the four steps, run once (ADR-475, ADR-468 D3).

    decompose  →  route by kind  →  generate per object  →  compose

This module is the ORCHESTRATOR. It owns none of the four steps' logic
(`decompose.py` plans, `generate.py` rents + composes) — it owns the SEQUENCE,
and one architectural fact that is the whole reason the file exists:

    THE GENERATED LEAVES ARE FILES, AND THE COMPOSITION CITES THEM.

Each subject leaf lands as its own attributed binary revision in the commons
(ADR-427 Phase 2 — CAS + marker row) and the stage references it by path +
head revision (`data-ref`/`data-ref-rev`, ADR-440 D5). The stage never inlines
bytes. That is what makes an IMAGES composition text substrate the lane can
edit, `trace` can walk, and a member can revert one layer of.

── WHY N+1 REVISIONS AND NOT ONE ────────────────────────────────────────────
A composition with three generated leaves writes four revisions: three assets
plus the stage. This is deliberate. The alternative — one revision carrying
everything — would make "re-roll the hero" rewrite the whole composition and
lose per-object history, which is precisely the flat-image failure IMAGES
exists to refuse. Per-object provenance requires per-object revisions.

Canonical reference: docs/adr/ADR-475-decomposed-generation.md
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from services.images.generate import (
    GeneratedAsset,
    Layer,
    compose_layers,
    get_backend,
)

logger = logging.getLogger(__name__)

#: Where a composition's generated leaves live: beside the stage that cites
#: them, in an `assets/` folder. Meaning-placed (ADR-440 D6) — the leaves of
#: THIS ad belong with this ad, so moving or deleting the work moves or
#: deletes its parts, and a member reading the Finder sees why they exist.
ASSETS_DIR = "assets"


def asset_path(stage_path: str, role: str, index: int) -> str:
    """The path for one generated leaf, beside its stage.

    `operation/launch-ad/image.html` → `operation/launch-ad/assets/subject.png`

    Named by ROLE, not by hash: the member opening the Finder should see
    `subject.png` and `logo.png`, because the object's name is the thing they
    reasoned about. Collisions within one composition are disambiguated by
    index rather than by mangling the name.
    """
    base = stage_path.rsplit("/", 1)[0]
    slug = re.sub(r"[^a-z0-9]+", "-", (role or "leaf").lower()).strip("-") or "leaf"
    return f"{base}/{ASSETS_DIR}/{slug}-{index}.png"


def _stage_inner_size(layer: Layer, width: int, height: int) -> tuple[int, int]:
    """The pixel size to rent for a leaf, from its percent-of-frame width.

    A leaf is generated at the size it will OCCUPY, not at the stage's full
    size: renting a 1080×1080 image for an object that occupies 60% of the
    frame buys pixels that are then thrown away. The height follows the
    stage's aspect so the subject is not distorted before it is placed.
    """
    pct = int(layer.get("w") or 60)
    w = max(64, round(width * pct / 100))
    h = max(64, round(w * (height / width))) if width else w
    return w, h


def compose_stage(
    db_client: Any,
    *,
    user_id: str,
    stage_path: str,
    layers: list[Layer],
    width: int,
    height: int,
    authored_by: str,
    stage_html: str,
    principal_id: Optional[str] = None,
) -> dict:
    """Run generation for every raster leaf, then land the composition.

    Returns ``{"html", "assets": [paths], "layers": n, "generated": n}``.
    The caller owns the stage's own write — this function produces the markup
    and the citations it depends on, so the endpoint keeps ONE write path for
    the artifact (the `write_revision` call the create endpoint already makes).
    """
    from services.authored_substrate import write_revision

    backend = get_backend()
    assets: dict[str, tuple[str, str, GeneratedAsset]] = {}
    written: list[str] = []

    for i, layer in enumerate(layers):
        if layer.get("kind") != "subject":
            continue  # text is text; a CSS surface rents nothing (the routing rule)
        role = layer.get("role") or f"leaf-{i}"
        prompt = layer.get("prompt") or role
        w, h = _stage_inner_size(layer, width, height)

        try:
            asset = backend.generate(prompt=prompt, width=w, height=h, cutout=True)
        except Exception as exc:  # noqa: BLE001
            # One leaf failing must not lose the composition (ADR-468 D4).
            logger.warning("[IMAGES] generation failed for %r: %s", role, exc)
            continue

        # A rented call is a metered call (ADR-396 — one ledger, every $
        # attributed). One row PER LEAF, matching the per-object revision
        # grain: "re-roll the hero" costs and ledgers exactly one leaf. The
        # free stub records nothing (zero-cost rows are noise, not honesty).
        cost = float(asset.get("cost_usd") or 0)
        if cost > 0:
            try:
                from services.telemetry import record_execution_event

                record_execution_event(
                    db_client,
                    user_id=user_id,
                    # ADR-373/445: generation is real metered cost — attribute it
                    # to the principal who asked, so it lands in
                    # spend_by_principal and counts against their cap.
                    principal_id=principal_id or user_id,
                    slug="images-generate",
                    mode="mechanical",
                    trigger_type="manual",
                    status="success",
                    model=asset["model"],
                    cost_override_usd=cost,
                )
            except Exception:  # noqa: BLE001 — never lose a leaf over the ledger
                logger.warning("[IMAGES] could not ledger generation for %r", role)

        path = asset_path(stage_path, role, i + 1)
        try:
            revision_id = write_revision(
                db_client,
                user_id=user_id,
                path=path,
                content_bytes=asset["data"],
                authored_by=authored_by,
                message=f"generate {role}: {prompt[:120]}",
                content_type=asset["content_type"],
                lifecycle="active",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[IMAGES] could not write leaf %s: %s", path, exc)
            continue

        assets[role] = (path, revision_id, asset)
        written.append(path)

    inner = compose_layers(layers, assets)
    html = _place_into_stage(stage_html, inner)
    return {
        "html": html,
        "assets": written,
        "layers": len(layers),
        "generated": len(written),
    }


#: The stage's frame — the `.slide` section the scaffold ships. Composition
#: replaces its CONTENTS, never the frame itself: the frame carries the
#: arrangement and the shared object layer's grain boundary (ADR-472 D2), and
#: rewriting it would drop the stage's dimensions with it.
_SLIDE_RE = re.compile(
    r"(<section[^>]*class=\"slide\"[^>]*>)(.*?)(</section>)", re.DOTALL
)


def _place_into_stage(stage_html: str, inner: str) -> str:
    """Put the composed objects inside the stage's existing frame.

    A REPLACE, not an append: composing is authoring the stage's contents, and
    the scaffold's placeholder heading is exactly what the member asked to be
    replaced. The frame's own attributes (dimensions, arrangement) survive
    untouched, which is why this is a targeted substitution rather than a
    rebuild of the document.
    """
    match = _SLIDE_RE.search(stage_html)
    if not match:
        logger.warning("[IMAGES] no .slide frame found — composition appended to body")
        return stage_html.replace("</body>", f"  {inner}\n</body>", 1)
    return stage_html[: match.start()] + (
        f"{match.group(1)}\n  {inner}\n{match.group(3)}"
    ) + stage_html[match.end():]
