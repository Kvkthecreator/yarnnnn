"""
One-shot: repair the flow (document/article) artifacts damaged before ADR-482
D11 shipped.

Context (2026-07-28): pre-D11, pressing Enter on a flow root's contenteditable
inserted a native <div>/<p> with no data-block, and normalizeBlockIds only ever
touched already-annotated elements — so those lines saved un-addressable and
un-selectable. Pressing '/' on exactly those element-node lines dead-ended, so
the sentinel landed as literal text. D11 fixed both going forward (the runtime
promotes bare lines + resolves the '/' text node from an element-node caret);
this brings the ALREADY-damaged substrate up to the same contract, as an
attributed, revertible revision (ADR-209 — never a raw SQL mutation).

Two repairs, matching the operator's chosen scope (structural + lone-slash):

  1. PROMOTE — a bare block-level element (a <div>/<p> with content but no
     data-block, no data-ref) that is a DIRECT CHILD of the flow root is named
     `prose` and minted a fresh id. Direct-child scope is exactly the shipped
     FE contract (normalizeBlockIds walks region.children): those are the lines
     native Enter creates as siblings of the real blocks. A bare <p> nested
     INSIDE an existing prose section is prose CONTENT, not a standalone block,
     and a `data-slot` div is a layout region — both are left alone. A promoted
     element keeps its children verbatim; only its annotation changes.

  2. STRIP LONE SLASH — an element whose ENTIRE trimmed text is exactly '/' (a
     failed slash gesture, e.g. <div>/</div>) is removed. A '/' embedded in
     other text is NEVER touched (URLs, "and/or", the operator's own prose) —
     only a line that is nothing but the sentinel.

Emptiness / <br>-only lines are left alone (they carry no content to promote and
no lone slash to strip). Citation islands (data-ref) and already-annotated
blocks are never promoted or stripped.

Attribution: `system:adr482-flow-repair` — a mechanical structural repair, not
an authored content edit. The text the operator wrote is preserved byte-for-byte
except the removal of lone-slash lines they explicitly asked to clear.

Usage:
    cd api
    python -m scripts.oneshot.adr482_repair_flow_documents            # dry run
    python -m scripts.oneshot.adr482_repair_flow_documents --execute  # apply
"""

from __future__ import annotations

import argparse
import logging
import random
import re
import string

logging.basicConfig(level=logging.WARNING)

USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"  # kvkthecreator@gmail.com

REPAIR_AUTHOR = "system:adr482-flow-repair"
REPAIR_MESSAGE = (
    "ADR-482 D11 flow repair: name the bare block-level lines native Enter "
    "created so they are addressable prose blocks, and remove lone-slash lines "
    "(failed '/' gestures). Structural only — authored text is preserved."
)

#: Only flow-mode templates carry the damage (paged blocks are per-block editable
#: and never produced bare root divs). Read from the served registry so a new
#: flow layout is covered without editing this list.
_FLOW_ROOT_TAGS = ("main", "article")
_PROMOTABLE = ("div", "p")


def _fresh_id(used: set[str]) -> str:
    for _ in range(10_000):
        cand = "b" + "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        if cand not in used:
            used.add(cand)
            return cand
    cand = "b" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    used.add(cand)
    return cand


def repair_html(content: str) -> tuple[str, int, int]:
    """Return (new_html, promoted_count, stripped_count). new_html == content
    when nothing changed (so the caller writes no revision)."""
    from lxml import html as lxml_html

    # Flow-only. A paged artifact (deck/page/canvas) never carries this damage,
    # and its blocks are enclosures we must not restructure.
    tpl = re.search(r'data-template="([a-z-]+)"', content or "")
    slug = tpl.group(1) if tpl else "document"

    # Resolve mode from the served registry (never hardcode the slug set).
    from services.authoring import STUDIO_LAYOUTS

    layout = STUDIO_LAYOUTS.get(slug)
    if not layout or layout.get("mode") != "flow":
        return content, 0, 0

    doc = lxml_html.fromstring(content)
    root = None
    for tag in _FLOW_ROOT_TAGS:
        found = doc.find(f".//{tag}")
        if found is not None:
            root = found
            break
    if root is None:
        return content, 0, 0

    used_ids = {
        el.get("data-block-id")
        for el in doc.iter()
        if el.get("data-block-id")
    }

    stripped = 0
    promoted = 0

    # ── 2. Strip lone-slash lines (every depth) ──────────────────────────
    # An element whose entire trimmed text is exactly '/', carrying no citation
    # and no child blocks, is a failed gesture. Remove it (with its tail text
    # preserved onto the previous node so surrounding prose is not disturbed).
    for el in list(root.iter()):
        if el is root:
            continue
        if el.get("data-ref") is not None:
            continue
        # Only leaf-ish lines: no nested annotated block, no media child.
        if el.find(".//*[@data-ref]") is not None:
            continue
        if el.find(".//*[@data-block]") is not None:
            continue
        text = (el.text_content() or "").strip()
        if text == "/":
            parent = el.getparent()
            if parent is None:
                continue
            # Preserve any tail whitespace/text so we don't merge words.
            if el.tail:
                prev = el.getprevious()
                if prev is not None:
                    prev.tail = (prev.tail or "") + el.tail
                else:
                    parent.text = (parent.text or "") + el.tail
            parent.remove(el)
            stripped += 1

    # ── 1. Promote bare block-level DIRECT CHILDREN of the flow root ─────
    # Direct-child scope mirrors the shipped FE fix (normalizeBlockIds walks
    # region.children): those are the lines native Enter creates as siblings of
    # the real blocks. A bare <p> nested inside a prose section is content, and
    # a data-slot container is a layout region — neither is a root child, so
    # neither is touched.
    for el in list(root):
        if el.tag not in _PROMOTABLE:
            continue
        if el.get("data-block") is not None or el.get("data-ref") is not None:
            continue
        if el.get("data-slot") is not None:
            continue  # a layout region, never content
        if (el.text_content() or "").strip() == "":
            continue  # a <br>-only / empty line
        el.set("data-block", "prose")
        el.set("data-block-id", _fresh_id(used_ids))
        promoted += 1

    if not promoted and not stripped:
        return content, 0, 0

    # Serialize back. lxml preserves the doctype only if we re-attach it; the
    # kernel's write door does not depend on the doctype line, and the FE
    # projection re-parses regardless — but keep it for fidelity with the
    # existing files (all start with <!doctype html>).
    new_html = lxml_html.tostring(doc, encoding="unicode", doctype="<!doctype html>")
    return new_html, promoted, stripped


def main(execute: bool) -> int:
    from services.authored_substrate import write_revision
    from services.supabase import get_service_client

    client = get_service_client()
    rows = (
        client.table("workspace_files")
        .select("id, path, content")
        .eq("user_id", USER_ID)
        .like("path", "%.html")
        .execute()
    ).data or []

    print(f"scanning {len(rows)} artifact(s) for flow damage\n")
    total_promoted = total_stripped = touched = 0

    for row in sorted(rows, key=lambda r: r["path"]):
        content = row.get("content") or ""
        new_html, promoted, stripped = repair_html(content)
        if promoted == 0 and stripped == 0:
            continue
        touched += 1
        total_promoted += promoted
        total_stripped += stripped
        verb = "REPAIR" if execute else "DRY RUN"
        print(f"  {verb}  {row['path']}  promote={promoted} strip={stripped}")
        if not execute:
            continue
        rev = write_revision(
            client,
            user_id=USER_ID,
            path=row["path"],
            content=new_html,
            authored_by=REPAIR_AUTHOR,
            message=REPAIR_MESSAGE,
            summary=(
                f"Flow repair: {promoted} bare line(s) named prose, "
                f"{stripped} lone-slash line(s) removed"
            ),
        )
        print(f"           rev={rev}")

    print(
        f"\n{touched} document(s) {'repaired' if execute else 'would be repaired'}; "
        f"{total_promoted} promoted, {total_stripped} lone-slash removed."
    )
    if not execute:
        print("dry run — re-run with --execute to apply.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    raise SystemExit(main(args.execute))
