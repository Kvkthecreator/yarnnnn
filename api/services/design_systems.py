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

#: `@import "…";` / `@import url(…);` — the entry-point convention every real
#: design-system export uses (ADR-462 D11). Media-query'd imports
#: (`@import "x.css" screen;`) are matched and their query DROPPED: the skin is
#: one inline element, so a media-scoped import cannot survive the flatten
#: honestly. Rare in a token file; named rather than silently mishandled.
_IMPORT_RX = re.compile(
    r"""@import\s+(?:url\(\s*)?['"]([^'"]+)['"]\s*\)?[^;]*;"""
    r"""|@import\s+url\(\s*([^'")\s]+)\s*\)[^;]*;""",
    re.IGNORECASE,
)

#: `/* … */` — stripped before parsing. Real entry points DESCRIBE themselves
#: in prose ("It is an @import manifest;" — the live YARNNN styles.css), and an
#: unstripped comment makes the parser import a file named `manifest;`. A CSS
#: comment is not code; the first test against the real export proved it.
_COMMENT_RX = re.compile(r"/\*.*?\*/", re.DOTALL)

#: `url(...)` inside a rule — @font-face src, background-image, mask, etc.
_URL_RX = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", re.IGNORECASE)

#: A url() we must never try to resolve as a workspace path.
_EXTERNAL_URL_PREFIXES = ("http://", "https://", "//", "data:")


def _norm_rel(base_dir: str, rel: str) -> str:
    """Resolve a folder-relative reference against base_dir (posix, no I/O).

    `posixpath.normpath` handles the `../assets/fonts/x.ttf` shape that every
    token file uses to reach its siblings.
    """
    import posixpath

    return posixpath.normpath(posixpath.join(base_dir, rel))


def flatten_css(
    entry_rel: str,
    read: Any,
    folder: str,
    *,
    _seen: Optional[set] = None,
) -> tuple[str, list[str], list[str]]:
    """Inline a CSS file's `@import` graph → (css_text, sources, warnings).

    WHY THIS EXISTS (ADR-462 D11): every real design-system export makes its
    entry point an @import manifest and nothing else. The live YARNNN export's
    `styles.css` is 11 lines, all @import; Concorn's is identical in shape. The
    ADR-449 v1 resolve concatenated the manifest's `css:` list verbatim into an
    inline <style> — where a relative @import cannot resolve. Naming styles.css
    would have produced a skin of five dead import lines: SILENTLY no styling,
    the worst failure shape, because it looks applied.

    Depth-first in source order (CSS cascade is order-dependent), cycle-safe,
    and it reports what it could not read rather than dropping it quietly.

    `read(abs_path) -> str|None` is the caller's reader — this stays pure.
    """
    seen = _seen if _seen is not None else set()
    abs_entry = _norm_rel(folder, entry_rel)
    if abs_entry in seen:
        return "", [], []  # a cycle: the first visit already contributed it
    seen.add(abs_entry)

    css = read(abs_entry)
    if css is None:
        return "", [], [f"missing: {abs_entry}"]

    sources = [abs_entry]
    warnings: list[str] = []
    base_dir = abs_entry.rsplit("/", 1)[0]
    out: list[str] = []
    pos = 0

    # Comments out FIRST (see _COMMENT_RX): a real entry point describes itself
    # in prose, and prose mentioning "@import" is not an import.
    css = _COMMENT_RX.sub("", css)

    # url()s are rewritten HERE, per file, against THIS file's directory —
    # never once over the merged blob. `tokens/fonts.css` reaches Pacifico as
    # `../assets/fonts/…`, which resolves correctly only against `tokens/`. The
    # first real run rewrote it against the ENTRY's dir and produced
    # `/design-system/assets/…` — one directory too high, silently wrong.
    css = rewrite_urls(css, abs_entry, warnings)

    for m in _IMPORT_RX.finditer(css):
        out.append(css[pos : m.start()])
        pos = m.end()
        target = m.group(1) or m.group(2)
        if target.startswith(_EXTERNAL_URL_PREFIXES):
            # An external @import cannot be inlined and must not silently
            # remain (it would be a live third-party dependency in a
            # "self-contained" artifact — ADR-456 D3).
            warnings.append(f"external @import dropped: {target}")
            continue
        sub_css, sub_sources, sub_warnings = flatten_css(
            target, read, base_dir, _seen=seen
        )
        out.append(f"\n/* ↳ {target} */\n{sub_css}\n")
        sources.extend(sub_sources)
        warnings.extend(sub_warnings)

    out.append(css[pos:])
    return "".join(out), sources, warnings


def rewrite_urls(css: str, css_abs_path: str, warn: list[str]) -> str:
    """Rewrite a flattened file's relative `url()`s → absolute workspace paths.

    A token file reaches its siblings relatively (`url("../assets/fonts/
    Pacifico-Regular.ttf")`). Once flattened into ONE inline element in an
    artifact that lives somewhere else entirely, every relative url() is
    broken. They become absolute workspace paths, which is what the projection
    already knows how to resolve for images.

    An EXTERNAL url is left in place and WARNED about, never rewritten: a
    jsDelivr @font-face (Concorn ships one) is a real third-party dependency,
    and the importer surfaces it rather than pretending it resolved.
    """
    base_dir = css_abs_path.rsplit("/", 1)[0]

    def _sub(m: "re.Match") -> str:
        target = m.group(1).strip()
        if target.startswith(_EXTERNAL_URL_PREFIXES):
            warn.append(f"external url() kept as-is: {target}")
            return m.group(0)
        return f'url("{_norm_rel(base_dir, target)}")'

    return _URL_RX.sub(_sub, css)


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
    warnings: list[str] = []
    seen: set = set()
    for rel in manifest["css"]:
        # ADR-462 D11: each declared source is FLATTENED, not read. Every real
        # export makes its entry an @import manifest (the live YARNNN
        # styles.css is 11 lines, all @import) — reading it verbatim would put
        # dead import lines in an inline <style> and style nothing, silently.
        # `seen` spans the loop so two entries sharing a token file inline it
        # once, in first-cascade position.
        css, srcs, warns = flatten_css(rel, _read, folder, _seen=seen)
        if not srcs:
            logger.warning("[DESIGN_SYSTEMS] css source missing: %s/%s", folder, rel)
            warnings.extend(warns)
            continue
        sources.extend(srcs)
        warnings.extend(warns)
        parts.append(f"/* {rel} */\n{css.strip()}")
    css_text = "\n\n".join(parts)[:_MAX_SKIN_CSS]
    for w in warnings:
        logger.warning("[DESIGN_SYSTEMS] %s: %s", abs_manifest, w)
    return {
        "name": manifest["name"],
        "manifest_path": abs_manifest,
        "css_text": css_text,
        "sources": sources,
        # Surfaced, not swallowed: an external font URL is a real third-party
        # dependency in a "self-contained" artifact (ADR-456 D3). The importer
        # and the picker both show these rather than pretend they resolved.
        "warnings": warnings,
    }


#: Files an import ignores outright — a design-system export ships a lot that
#: the SKIN contract does not consume (ADR-462 D11). The skin is one CSS
#: string; components/, ui_kits/, a 500KB _ds_bundle.js and a lint config are
#: the vendor's business, not the kernel's. They may still land as substrate
#: (they are ordinary files); they are simply never part of the composed skin.
_IMPORT_SKIP_SUFFIXES = (".DS_Store", ".d.ts", ".jsx", ".tsx", ".js", ".json", ".oxlintrc.json")

#: Where an import looks for the CSS entry point, in order of confidence. Every
#: export observed so far (YARNNN, Concorn) uses `styles.css` at the root as an
#: @import manifest — the convention is real, so honour it before guessing.
_ENTRY_CANDIDATES = ("styles.css", "style.css", "index.css", "main.css", "tokens.css")


def plan_import(files: dict, folder_name: Optional[str] = None) -> dict:
    """Plan a design-system import from a flat {rel_path: content} map.

    PURE — no I/O, no writes. Returns the plan the caller executes through the
    one write door (ADR-444/209): the entry point it found, the manifest it
    would write, and what it is skipping and why.

    The judgment this makes, and its evidence: a real export (the live YARNNN
    and Concorn folders, 11 items each) is mostly NOT skin — components/,
    ui_kits/, guidelines/, a 508KB _ds_bundle.js. What the ADR-449 contract
    consumes is ONE CSS string. So the import is a search for the entry point,
    not an interpretation of the vendor's schema: `_ds_manifest.json` is
    EVIDENCE an importer may read, never a second schema the kernel parses
    (that way lies one parser per vendor).
    """
    css_files = sorted(
        p for p in files
        if p.endswith(".css") and not p.split("/")[-1].startswith(".")
    )
    entry = next((c for c in _ENTRY_CANDIDATES if c in css_files), None)
    if entry is None:
        # No conventional entry: the caller lists every css file in path order
        # (tokens/ sorts before others, which is the right cascade by luck and
        # by convention). Named as a fallback so a weird export still lands.
        entry = None

    # The name a MEMBER would recognise. The folder they dropped in is the best
    # evidence there is: the live export's `_ds_manifest.json` carries only
    # `namespace: "YARNNNDesignSystem_36fab3"` — a machine id, with no name/
    # title/displayName field anywhere. The first probe run surfaced that
    # verbatim as the display name, which is exactly the kind of vendor
    # internal that should never reach a picker. Folder name first; the
    # namespace only as a last resort.
    name = (folder_name or "").strip() or None
    if not name:
        raw = files.get("_ds_manifest.json")
        if raw:
            try:
                import json

                name = (json.loads(raw) or {}).get("namespace") or None
            except Exception:  # noqa: BLE001
                name = None

    skipped = [
        p for p in files
        if p.endswith(_IMPORT_SKIP_SUFFIXES) or "/." in p or p.startswith(".")
    ]
    return {
        "entry": entry,
        "css_all": css_files,
        "name": name,
        "skipped": skipped,
        "assets": sorted(
            p for p in files
            if p.startswith("assets/") and not p.endswith(_IMPORT_SKIP_SUFFIXES)
        ),
    }


def build_manifest_yaml(name: str, css: list) -> str:
    """The `_design.yaml` an import writes (D1's contract, authored by us).

    Deliberately minimal and OURS: `{name, css[]}`. A vendor manifest
    (`_ds_manifest.json`, with namespace/components/themes/startingPoints/…)
    is richer, and adopting it would make the kernel parse one schema per
    vendor forever. We read it for evidence and write our own contract.
    """
    lines = [f"name: {name}", "css:"]
    lines.extend(f"  - {c}" for c in css)
    return "\n".join(lines) + "\n"


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
