"""
Design systems — the Skin layer as a workspace convention (ADR-449).

A design system is an ORDINARY meaning-folder identified by a `_design.yaml`
manifest (name + ordered folder-relative CSS sources). Nothing is seeded
(ADR-414); the kernel ships the category, never an instance. An artifact wears
a design system as a second, MARKED style element:

    <style data-skin="true" data-ref="<manifest path>"> …composed css… </style>

- MARKED (`data-skin`) so the apply rule replaces exactly this element and a
  layout/arrangement switch — which replaces the UNMARKED layout style — never
  touches it (the ADR-449 D3 amendment to the ADR-443/444 switch rule).
- CITED (`data-ref` → the manifest) so the ADR-448 write-door lift records the
  reference edge on every artifact write: the manifest's dependents are the
  artifacts wearing it; Files warns before it is trashed; trace walks
  artifact → design system. The contract costs one attribute.

Every function here is pure or read-only. The bound lane consumes the contract
through its posture section (build_design_system_section, composed in
lane_runner); the future mechanical picker (ADR-447 D7 inspector) wires the
same functions. There is NO write path in this module — applies go through the
lane's file verbs or the one mechanical door, as ever.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: The manifest basename that makes a folder a design system (machine-parsed
#: per the §9 underscore-yaml discipline).
DESIGN_MANIFEST_BASENAME = "_design.yaml"

#: The marked skin element (ADR-449 D2). One regex owns both halves of the
#: apply rule: find-and-replace when present, insert-before-</head> when not.
_SKIN_ELEMENT_RX = re.compile(
    r"<style\s+[^>]*data-skin=\"true\"[^>]*>.*?</style>", re.DOTALL
)

#: Defensive bound on composed skin CSS (an artifact carries this inline).
_MAX_SKIN_CSS = 120_000


def parse_design_manifest(content: Optional[str]) -> Optional[dict]:
    """Parse a `_design.yaml` body → {name, css} or None if not a manifest.

    Tolerant (load_workspace_yaml never raises); strict on shape — a manifest
    without a non-empty `css` list is not a design system yet.
    """
    from services.review_policy import load_workspace_yaml

    data = load_workspace_yaml(content or "")
    if not isinstance(data, dict):
        return None
    css = data.get("css")
    if not isinstance(css, list):
        return None
    sources = [str(c).strip().lstrip("./") for c in css if str(c).strip()]
    if not sources:
        return None
    return {
        "name": str(data.get("name") or "").strip() or "Design system",
        "css": sources,
    }


def find_design_systems(client: Any, user_id: str) -> list[dict]:
    """Discover the workspace's design systems — the manifest search (D1/D5).

    Returns [{name, manifest_path, folder, css}] for every active
    `_design.yaml` whose body parses as a manifest. No registry row exists or
    is maintained; discovery IS the convention. Best-effort: failures return
    what was found.
    """
    from services.workspace_context import substrate_scope_filter

    out: list[dict] = []
    try:
        rows = (
            client.table("workspace_files")
            .select("path, content, lifecycle")
            .eq(*substrate_scope_filter(user_id))
            .like("path", f"%/{DESIGN_MANIFEST_BASENAME}")
            .order("updated_at", desc=True)
            .limit(20)
            .execute()
        ).data or []
        for r in rows:
            if r.get("lifecycle") == "archived":
                continue
            manifest = parse_design_manifest(r.get("content"))
            if not manifest:
                continue
            path = r["path"]
            out.append(
                {
                    "name": manifest["name"],
                    "manifest_path": path,
                    "folder": path.rsplit("/", 1)[0],
                    "css": manifest["css"],
                }
            )
    except Exception as exc:  # noqa: BLE001 — discovery is best-effort
        logger.debug("[DESIGN_SYSTEMS] discovery failed: %s", exc)
    return out


def resolve_design_system(client: Any, user_id: str, manifest_path: str) -> Optional[dict]:
    """Resolve one design system → {name, manifest_path, css_text, sources}.

    Reads the manifest, then its folder-relative CSS sources in manifest
    order, and concatenates them (a source that fails to read is skipped with
    a log — a partial skin beats none). Returns None if the manifest is
    missing or not a manifest.
    """
    from services.workspace_context import substrate_scope_filter

    abs_manifest = (
        manifest_path
        if manifest_path.startswith("/workspace/")
        else "/workspace/" + manifest_path.lstrip("/")
    )
    folder = abs_manifest.rsplit("/", 1)[0]

    def _read(path: str) -> Optional[str]:
        try:
            res = (
                client.table("workspace_files")
                .select("content")
                .eq(*substrate_scope_filter(user_id))
                .eq("path", path)
                .limit(1)
                .execute()
            )
            return (res.data or [{}])[0].get("content")
        except Exception as exc:  # noqa: BLE001
            logger.debug("[DESIGN_SYSTEMS] read failed for %s: %s", path, exc)
            return None

    manifest = parse_design_manifest(_read(abs_manifest))
    if not manifest:
        return None

    parts: list[str] = []
    sources: list[str] = []
    for rel in manifest["css"]:
        src_path = f"{folder}/{rel}"
        css = _read(src_path)
        if css is None:
            logger.warning("[DESIGN_SYSTEMS] css source missing: %s", src_path)
            continue
        sources.append(src_path)
        parts.append(f"/* {rel} */\n{css.strip()}")
    css_text = "\n\n".join(parts)[:_MAX_SKIN_CSS]
    return {
        "name": manifest["name"],
        "manifest_path": abs_manifest,
        "css_text": css_text,
        "sources": sources,
    }


def compose_skin_element(manifest_path: str, css_text: str, rev_id: Optional[str] = None) -> str:
    """Compose the marked skin element (D2): data-skin + data-ref (+ pin)."""
    abs_manifest = (
        manifest_path
        if manifest_path.startswith("/workspace/")
        else "/workspace/" + manifest_path.lstrip("/")
    )
    pin = f' data-ref-rev="{rev_id}"' if rev_id else ""
    return (
        f'<style data-skin="true" data-ref="{abs_manifest}"{pin}>\n'
        f"{css_text.strip()}\n"
        f"</style>"
    )


def apply_skin_to_html(artifact_html: str, skin_element: str) -> str:
    """The apply rule (D3) — executable spec, pure.

    Replace the artifact's existing marked skin element; if none exists,
    insert the element immediately before </head> (last in head — the
    workspace's identity overrides the layout skin by cascade order). The
    UNMARKED layout <style> is never touched. Returns the html unchanged if it
    has no </head> to anchor on (not an artifact).
    """
    if _SKIN_ELEMENT_RX.search(artifact_html):
        return _SKIN_ELEMENT_RX.sub(lambda _m: skin_element, artifact_html, count=1)
    idx = artifact_html.find("</head>")
    if idx < 0:
        return artifact_html
    return artifact_html[:idx] + skin_element + "\n" + artifact_html[idx:]


def remove_skin_from_html(artifact_html: str) -> str:
    """Remove the marked skin element (an ordinary edit — D3's inverse)."""
    return _SKIN_ELEMENT_RX.sub("", artifact_html, count=1)


def build_design_system_section(client: Any, user_id: str) -> str:
    """The bound lane's additive posture section (D4) — composed per turn.

    Present ONLY when the workspace has at least one design system (no design
    system → empty string → zero prompt cost, the envelope-dilution
    discipline). Teaches the D2/D3 contract in the lane's own verbs.
    """
    systems = find_design_systems(client, user_id)
    if not systems:
        return ""
    listing = "\n".join(
        f"- {s['name']} — manifest {s['manifest_path']} (css: {', '.join(s['css'])})"
        for s in systems[:5]
    )
    return f"""## Design system (the workspace's visual identity)
This workspace has a design system the member expects artifacts to follow:
{listing}

When the member asks you to apply/use/follow it (or asks for "our style"):
1. Read the manifest and its css sources (folder-relative paths) with ReadFile.
2. Compose ONE style element marked and cited exactly like this, placed LAST
   inside <head> (after the layout's own <style>):
   <style data-skin="true" data-ref="<manifest path>"> …the css sources, concatenated in manifest order… </style>
3. If a data-skin element already exists, replace THAT element only.
Rules: never edit the layout's own unmarked <style> to restyle — the marked
element is the workspace's layer and cascade order makes it win. When you
switch layouts, replace only the unmarked <style>; the data-skin element
SURVIVES the switch. The data-ref citation is how the workspace knows which
artifacts wear the design system — never strip it."""
