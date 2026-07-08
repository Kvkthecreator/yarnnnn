"""
Deliverable HTML Composition — ADR-213 + ADR-333.

Single, root-agnostic path for composing a deliverable's output folder into
HTML on demand. Reads substrate (section partials + sys_manifest.json +
manifest.json) from the deliverable's dated folder — `report_root` for audit
reports, `authored_root` for published pieces — and composes HTML via the
in-API `compose.engine` library (ADR-417 retired the render service; compose
is a pure-Python, deterministic call now, no HTTP).

The composer is a **lazy projection** (ADR-333): it is pulled when a surface
actually consumes the artifact, never pushed eagerly. The substrate (sections
+ asset URLs) is canonical; the HTML it returns is a view. One code path
serves both deliverable kinds — `artifact_kind` selects the root resolver
(Singular Implementation: no parallel author-composer).

Callers:
  - api/routes/recurrences.py: report export (artifact_kind="report")
  - api/routes/authored.py: authored-piece composition (artifact_kind="authored")
  - api/services/delivery.py: email body composition
  - api/services/primitives/repurpose.py: format conversion
  (No eager session-close caller — ADR-333 D2 retired the push.)

ADR-417: content-addressed caching (ADR-213) went with the render service. The
in-API compose is fast enough that a per-pull recompute is acceptable; a
`workspace_blobs`-keyed memoization is a demand-gated follow-on if a hot path
proves it necessary.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


async def compose_task_output_html(
    client,
    user_id: str,
    task_slug: str,
    date_folder: str = "latest",
    surface_type: Optional[str] = None,
    title: Optional[str] = None,
    artifact_kind: str = "report",
) -> Optional[str]:
    """Compose a deliverable's output folder into HTML on demand.

    Reads section partials and manifest from the deliverable's dated folder,
    composes via the in-API `compose.engine` library (ADR-417), returns the
    composed HTML string.
    The root is selected by ``artifact_kind`` (ADR-333):
      - ``"report"`` (default) → `/workspace/operation/reports/{slug}/{date}/`
        (audit reports — canonical per ADR-231 D2 / ADR-262 D1)
      - ``"authored"`` → `/workspace/operation/authored/{slug}/{date}/`
        (published pieces — ADR-333 + ADR-283)

    We do not validate that a recurrence/piece exists for the slug —
    composition reads what's actually on disk.

    Returns None if no substrate exists (never composed) or compose failed.
    Caller decides how to handle None (404, fallback, etc.).
    """
    from services.conventions import authored_root, report_root
    from services.workspace import UserMemory

    if artifact_kind == "authored":
        root = authored_root(task_slug)
        # authored pieces render as a flowing article — which IS the compose
        # engine's `report` surface (vertically-stacked section-kind dispatch,
        # compose/engine.py default). We do not invent a separate surface type
        # ("article" is not in the engine's vocabulary); `report` already
        # produces the article form. (ADR-333 — Singular Implementation.)
        default_surface = "report"
    else:
        root = report_root(task_slug)
        default_surface = "report"

    folder_abs = f"{root}/{date_folder}"

    um = UserMemory(client, user_id)

    def _strip_ws(p: str) -> str:
        return p[len("/workspace/"):] if p.startswith("/workspace/") else p

    sys_manifest_raw = await um.read(_strip_ws(f"{folder_abs}/sys_manifest.json"))
    if not sys_manifest_raw:
        return None

    try:
        sys_manifest = json.loads(sys_manifest_raw)
    except (ValueError, json.JSONDecodeError):
        logger.warning(f"[COMPOSE] Invalid sys_manifest.json for {task_slug}/{date_folder}")
        return None

    resolved_surface = surface_type or sys_manifest.get("surface_type") or default_surface
    # "article" is the operator/spec vocabulary for a flowing piece; the render
    # engine implements that as `report` (its default vertically-stacked
    # section-kind layout). Map the synonym at the boundary so a manifest that
    # declares surface_type: article still renders. (ADR-333.)
    if resolved_surface == "article":
        resolved_surface = "report"
    resolved_title = (
        title
        or sys_manifest.get("title")
        or task_slug.replace("-", " ").title()
    )

    # Normalize the `sections` shape at the input boundary. The report path
    # (ADR-170) writes an object keyed by slug; the Reviewer authoring an
    # authored piece reliably writes an ordered list of {slug, kind, title}.
    # Both are valid representations of the same thing — accept either, reduce
    # to one internal list of (slug, meta) in order. ONE tolerant boundary, not
    # a dual render path (same discipline as ADR-166's legacy `**Class:**` remap).
    raw_sections = sys_manifest.get("sections") or {}
    normalized: list[tuple[str, dict]] = []
    if isinstance(raw_sections, dict):
        # object-keyed-by-slug, rendered in declaration order (Python dicts
        # preserve insertion order)
        normalized = [(slug, meta or {}) for slug, meta in raw_sections.items()]
    elif isinstance(raw_sections, list):
        # ordered list of section objects; the slug is the `slug` field
        for entry in raw_sections:
            if not isinstance(entry, dict):
                continue
            slug = entry.get("slug") or entry.get("file") or ""
            # strip a trailing .md and any leading NN- prefix from a file ref
            slug = slug.rsplit("/", 1)[-1]
            if slug.endswith(".md"):
                slug = slug[:-3]
            normalized.append((slug, entry))

    # Resolve each section's partial file. The Reviewer names partials with a
    # numeric prefix (`{NN}-{slug}.md`); the manifest slug is the bare slug.
    # Try the explicit `file` field first, then the bare slug, then a
    # prefix-globbed match — meeting the on-disk convention without forcing the
    # LLM to echo the exact filename in the manifest.
    # Glob the actual section partial files so we can resolve the manifest slug
    # against the on-disk `{NN}-{slug}.md` convention (the Reviewer numbers
    # partials for ordering but the manifest slug is the bare slug).
    sections_dir_abs = f"{folder_abs}/sections/"
    file_by_slug: dict[str, str] = {}
    try:
        rows = (
            client.table("workspace_files")
            .select("path")
            .eq("user_id", user_id)
            .like("path", f"{sections_dir_abs}%.md")
            .execute()
        ).data or []
    except Exception:
        rows = []
    for row in rows:
        fname = (row.get("path") or "").rsplit("/", 1)[-1]
        if not fname.endswith(".md"):
            continue
        base = fname[:-3]
        # strip a leading numeric ordering prefix (one or more digits + "-",
        # e.g. "1-architectures" or "01-architectures" → "architectures")
        bare = re.sub(r"^\d+-", "", base)
        file_by_slug[bare] = fname

    sections_payload: list[dict] = []
    fallback_markdown_parts: list[str] = []

    for sec_slug, sec_meta in normalized:
        # file resolution: explicit field → globbed prefix match → bare slug
        explicit = (sec_meta.get("file") or "").rsplit("/", 1)[-1]
        fname = explicit or file_by_slug.get(sec_slug) or f"{sec_slug}.md"
        sec_content = await um.read(_strip_ws(f"{folder_abs}/sections/{fname}"))
        if not sec_content:
            continue
        sections_payload.append({
            "kind": sec_meta.get("kind", "narrative"),
            "title": sec_meta.get("title", sec_slug.replace("-", " ").title()),
            "content": sec_content,
        })
        fallback_markdown_parts.append(f"## {sec_meta.get('title', sec_slug)}\n\n{sec_content}")

    fallback_markdown = ""
    if not sections_payload:
        fallback_markdown = await um.read(_strip_ws(f"{folder_abs}/output.md")) or ""
        if not fallback_markdown:
            return None
    else:
        fallback_markdown = "\n\n".join(fallback_markdown_parts)

    assets: list[dict] = []
    manifest_raw = await um.read(_strip_ws(f"{folder_abs}/manifest.json"))
    if manifest_raw:
        try:
            manifest = json.loads(manifest_raw)
            for f in manifest.get("files", []):
                url = f.get("content_url") or f.get("output_url")
                path = f.get("path", "")
                if url and path and f.get("role") != "primary":
                    ref = path.split("/")[-1] if "/" in path else path
                    assets.append({"ref": ref, "url": url})
        except (ValueError, json.JSONDecodeError):
            pass

    # ADR-417: compose is an in-API library call now (the render service is
    # retired). Pure-Python, deterministic templating — no HTTP, no cache
    # round-trip; ADR-333's lazy-projection contract is unchanged (pulled at
    # consumption). SectionContent's shape is exactly the sections_payload dicts.
    try:
        from services.compose.engine import compose_html, SectionContent

        section_objs = [SectionContent(**s) for s in sections_payload] if sections_payload else None
        html = compose_html(
            fallback_markdown,
            title=resolved_title,
            surface_type=resolved_surface,
            assets=assets,
            sections=section_objs,
        )
        return html or None
    except Exception as e:
        logger.warning(f"[COMPOSE] in-API compose failed for {task_slug}/{date_folder}: {e}")
        return None
