"""Design-system import — a real export becomes a conforming meaning-folder.

ADR-462 D11/D13. The mechanism ADR-449 D1 assumed ("drop the folder in, get a
manifest written") but never built: a design system arrived only by hand.

WHAT AN EXPORT ACTUALLY IS (measured, not assumed — the live YARNNN + Concorn
folders, 11 items each): mostly NOT skin. components/, ui_kits/, guidelines/, a
508KB `_ds_bundle.js`, a lint config, a vendor `_ds_manifest.json`. What the
ADR-449 contract consumes is ONE CSS string. So the import is a search for the
entry point plus a flatten — never an interpretation of the vendor's schema.
Parsing one schema per vendor is the road not taken; `_ds_manifest.json` is
EVIDENCE (we read one field from it) and never a second contract.

THE BINARIES (ADR-510, superseding this module's ADR-462 D13 bucket lane). A
design system's fonts and logos are cited by the skin's `@font-face` /
`url()`s. They land as ORDINARY BINARY REVISIONS through the one write door —
`write_revision(content_bytes=…)` routes bytes through the ADR-427 storage
seam (CAS), attributed and parent-pointered like any other substrate write,
and the serving URL is minted at read (ADR-427 D4), never stored. The
2026-07-16 shape (documents bucket + stored `content_url`) is DELETED: it
predated ADR-427 Phase 2 and left the substrate's own record of every binary
empty — bytes the revision chain could not see and an export could not carry
(the lane divergence the 2026-07-31 audit receipted).

This module PLANS and EXECUTES through the one write door; it never invents a
second. Every write is `write_revision` (ADR-209/444).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Text we carry into the workspace. Everything else in an export is the
#: vendor's business — it may be uploaded separately as ordinary substrate, but
#: the import does not pretend it is part of the skin.
_TEXT_SUFFIXES = (".css", ".md", ".yaml", ".yml", ".txt")

#: Font binaries the skin's @font-face can cite (ADR-462 D13).
_FONT_SUFFIXES = (".woff2", ".woff", ".ttf", ".otf")

#: Image binaries a design system ships (logos, brand marks).
_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif")


def classify(rel_path: str) -> str:
    """What is this file, for import purposes? — pure.

    `skin` (css the contract consumes) · `doc` (readme — carried for the
    member) · `font` / `image` (binaries the skin may cite) · `vendor`
    (everything else: bundles, components, lint configs, ui kits).
    """
    name = rel_path.split("/")[-1]
    if name.startswith(".") or "/." in rel_path:
        return "vendor"
    low = rel_path.lower()
    if low.endswith(".css"):
        return "skin"
    if low.endswith(_FONT_SUFFIXES):
        return "font"
    # An SVG is TEXT — the one "image" that is ordinary substrate. It lands as
    # content like any other file and the projection resolves it as it already
    # does for the cited SVGs in the live workspace.
    if low.endswith(".svg"):
        return "doc"
    if low.endswith(_IMAGE_SUFFIXES):
        return "image"
    # A readme at the root is FOR the member; a .md buried in components/ is
    # the vendor's own prose (prompt.md files, per-kit READMEs) and stays out.
    if low.endswith((".md", ".txt")) and "/" not in rel_path:
        return "doc"
    return "vendor"


def import_design_system(
    db_client: Any,
    *,
    user_id: str,
    folder: str,
    display_name: str,
    files: dict,
    service_client: Any = None,
) -> dict:
    """Write an export into the workspace as a conforming design system.

    `files` maps rel_path → bytes. Text lands as ordinary substrate through the
    one write door; fonts/images land through the SAME door as binary revisions
    (`content_bytes` → the ADR-427 CAS seam; type derived from the bytes,
    serving URL minted at read). Returns a receipt: what landed, what was
    skipped, and every warning produced — a binary that fails to land is
    NAMED in the receipt, never silently dropped.

    The manifest is written LAST and only if an entry point was found — a
    folder without one is not a design system, and half-writing one would make
    the picker offer something that cannot resolve.
    """
    from services.authored_substrate import write_revision
    from services.design_systems import (
        build_manifest_yaml,
        flatten_css,
        plan_import,
        seed_maps,
    )

    text: dict = {}
    for rel, data in files.items():
        if classify(rel) in ("skin", "doc"):
            try:
                text[rel] = data.decode("utf-8") if isinstance(data, bytes) else data
            except UnicodeDecodeError:
                logger.warning("[DS_IMPORT] not utf-8, skipping: %s", rel)

    plan = plan_import(text, folder_name=display_name)
    entry = plan["entry"]
    if not entry:
        return {
            "ok": False,
            "error": (
                "No CSS entry point found. A design system needs a stylesheet "
                "(styles.css, or one this folder names) for artifacts to wear."
            ),
            "css_seen": plan["css_all"],
        }

    written: list = []
    warnings: list = list()

    # 1. The CSS + docs — ordinary substrate, one door.
    for rel, content in text.items():
        path = f"{folder}/{rel}"
        write_revision(
            db_client, user_id=user_id, path=path, content=content,
            authored_by="operator", message=f"Import {display_name}: {rel}",
        )
        written.append(path)

    # 2. The binaries the skin may cite — the SAME door, binary lane (ADR-510).
    #    The CAS upload needs the service client (the workspace-cas bucket is
    #    seam-managed, like every uploaded binary — routes/documents does the
    #    same); attribution stays the operator's via authored_by + user_id.
    fonts: list = []
    for rel, data in files.items():
        kind = classify(rel)
        if kind not in ("font", "image") or not isinstance(data, bytes):
            continue
        path = f"{folder}/{rel}"
        try:
            write_revision(
                service_client or db_client, user_id=user_id, path=path,
                content_bytes=data,
                authored_by="operator",
                message=f"Import {display_name}: {rel} (binary)",
                revision_kind="observation",
            )
        except Exception as exc:  # noqa: BLE001 — NAMED in the receipt, never silent
            logger.warning("[DS_IMPORT] binary write failed for %s: %s", rel, exc)
            warnings.append(f"binary write failed: {rel} ({exc})")
            continue
        written.append(path)
        if kind == "font":
            fonts.append(rel)

    # 3. The manifest — LAST, and only now that its sources exist.
    def _read(abs_path: str) -> str | None:
        return text.get(abs_path[len(folder):].lstrip("/"))

    _css, sources, flat_warnings = flatten_css(entry, _read, folder)
    warnings.extend(flat_warnings)

    # Seed the synonym bridge (DESIGN-SYSTEMS.md §5, Move 2) from the flattened
    # skin's own token names — so a system whose accent is `--yarn-orange`
    # themes the kernel chrome without hand-authoring. EVIDENCE, not a decision:
    # the seed is written into the yaml where a human confirms it, and it is
    # surfaced in the receipt so a wrong bridge is visible, not silent.
    seeded_maps = seed_maps(_css)

    manifest_path = f"{folder}/_design.yaml"
    write_revision(
        db_client, user_id=user_id, path=manifest_path,
        content=build_manifest_yaml(display_name, [entry], maps=seeded_maps),
        authored_by="operator", message=f"Import {display_name}: the manifest",
    )
    written.append(manifest_path)

    return {
        "ok": True,
        "manifest_path": manifest_path,
        "name": display_name,
        "entry": entry,
        "written": written,
        "sources": sources,
        "fonts": fonts,
        "maps": seeded_maps,
        "skipped": sorted({r for r in files if classify(r) == "vendor"}),
        "warnings": warnings,
    }
