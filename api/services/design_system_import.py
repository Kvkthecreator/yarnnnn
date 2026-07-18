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

THE FONT (ADR-462 D13). A design system's `@font-face` is a CITATION, not an
inline: Pacifico is 411KB base64 against a 120KB skin ceiling — arithmetic, not
taste. But `workspace_blobs.content` is TEXT (ADR-427 Phase 1; Phase 2/3's
object-store driver is reserved, not built), so a TTF cannot go down the
ordinary substrate path at all. It rides the lane images already use: the
ADR-395 `documents` bucket, with `workspace_files.content_url` pointing at the
stable blob endpoint. One binary lane, two callers.

This module PLANS and EXECUTES through the one write door; it never invents a
second. Every write is `write_revision` (ADR-209/444).
"""

from __future__ import annotations

import logging
import posixpath
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: Text we carry into the workspace. Everything else in an export is the
#: vendor's business — it may be uploaded separately as ordinary substrate, but
#: the import does not pretend it is part of the skin.
_TEXT_SUFFIXES = (".css", ".md", ".yaml", ".yml", ".txt")

#: Font binaries the skin's @font-face can cite (ADR-462 D13).
_FONT_SUFFIXES = (".woff2", ".woff", ".ttf", ".otf")

#: Image binaries a design system ships (logos, brand marks).
_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif")

_FONT_MIME = {
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
}

_IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}


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
    # An SVG is TEXT — the one "image" that is ordinary substrate. It needs no
    # bucket (and the bucket rejects image/svg+xml anyway, verified live), so
    # it lands as content like any other file and the projection resolves it as
    # it already does for the cited SVGs in the live workspace.
    if low.endswith(".svg"):
        return "doc"
    if low.endswith(_IMAGE_SUFFIXES):
        return "image"
    # A readme at the root is FOR the member; a .md buried in components/ is
    # the vendor's own prose (prompt.md files, per-kit READMEs) and stays out.
    if low.endswith((".md", ".txt")) and "/" not in rel_path:
        return "doc"
    return "vendor"


def binary_mime(rel_path: str) -> str:
    """The content-type a binary is uploaded with.

    Load-bearing, not cosmetic: the `documents` bucket enforces an
    allowed_mime_types list, so a wrong type is a 415 rather than a bad
    header. The first real import sent `application/octet-stream` for every
    PNG (a font-only lookup with an octet-stream default) and the bucket
    rejected all five logos.
    """
    low = rel_path.lower()
    for suf, mime in {**_FONT_MIME, **_IMAGE_MIME}.items():
        if low.endswith(suf):
            return mime
    return "application/octet-stream"


#: The `documents` bucket accepts font types (operator added font/woff2, woff,
#: ttf, otf on 2026-07-16; verified live — 12 types, the original 8 intact).
#: Kept as a named constant rather than deleted: it is the one line that says
#: whether the binary lane is open, and if the bucket policy ever narrows the
#: import must go back to warning instead of half-landing a design system whose
#: @font-face points at nothing (ADR-462 D13).
FONT_UPLOAD_SUPPORTED = True


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
    one write door; fonts/images land in the ADR-395 bucket with a
    `content_url` row (the binary lane images already use). Returns a receipt:
    what landed, what was skipped, and every warning the flatten produced.

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

    # 2. The binaries the skin may cite — the ADR-395 lane (D13).
    fonts: list = []
    fonts_deferred: list = []
    for rel, data in files.items():
        kind = classify(rel)
        if kind not in ("font", "image") or not isinstance(data, bytes):
            continue
        if kind == "font" and not FONT_UPLOAD_SUPPORTED:
            # NAMED, not swallowed: the skin's @font-face will cite a path with
            # no bytes, so the face falls back to the stack beside it. The
            # member is told; the import still lands (a design system is its
            # tokens far more than its wordmark).
            fonts_deferred.append(rel)
            warnings.append(
                f"font not uploaded ({rel}): the storage bucket allows no font "
                f"types. The @font-face will fall back until the bucket's "
                f"allowed_mime_types gains font/woff2|woff|ttf|otf."
            )
            continue
        url = _put_binary(
            service_client or db_client, user_id=user_id, rel=rel, data=data,
            folder=folder, display_name=display_name, db_client=db_client,
        )
        if url:
            written.append(f"{folder}/{rel}")
            if kind == "font":
                fonts.append(rel)
        else:
            warnings.append(f"binary upload failed: {rel}")

    # 3. The manifest — LAST, and only now that its sources exist.
    def _read(abs_path: str) -> Optional[str]:
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
        "fonts_deferred": fonts_deferred,
        "maps": seeded_maps,
        "skipped": sorted({r for r in files if classify(r) == "vendor"}),
        "warnings": warnings,
    }


def _put_binary(
    service: Any, *, user_id: str, rel: str, data: bytes,
    folder: str, display_name: str, db_client: Any,
) -> Optional[str]:
    """A font/image into the ADR-395 bucket + its workspace_files row.

    NOT workspace_blobs: `content` is TEXT there (ADR-427 Phase 1) and a TTF is
    not utf-8. The `documents` bucket is the binary lane that already exists —
    the same one an uploaded image rides, so the projection's content_url
    resolution works on this for free.
    """
    from services.documents import blob_content_url

    path = f"{folder}/{rel}"
    storage_path = f"{user_id}/design-system/{posixpath.basename(folder)}/{rel}"
    try:
        service.storage.from_("documents").upload(
            path=storage_path,
            file=data,
            file_options={"content-type": binary_mime(rel), "upsert": "true"},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[DS_IMPORT] storage upload failed for %s: %s", rel, exc)
        return None

    url = blob_content_url(storage_path)
    from services.authored_substrate import write_revision

    # The row carries the ADDRESS, not the bytes — content stays empty, which
    # is exactly the ADR-395 raw-upload shape.
    write_revision(
        db_client, user_id=user_id, path=path, content="",
        authored_by="operator", message=f"Import {display_name}: {rel} (binary)",
        content_url=url, content_type=binary_mime(rel),
        revision_kind="observation",
    )
    return url
