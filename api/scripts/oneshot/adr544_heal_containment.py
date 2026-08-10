"""
One-shot: bring paged artifacts authored before ADR-544 up to the containment law.

Context (2026-08-10): pre-544 the arrangement registry disagreed with itself
about where a block lives — `title` put its heading inside a region while
`content`/`two-column` left a bare `<h2>` as a direct child of the slide, and a
`.col` sometimes wrapped a region rather than being one. On top of that, a drag
wrote `data-x`/`data-y` and the block LEFT the layout entirely ("a positioned
block exits the slot contract" — the ADR-461 honest remainder). ADR-544 D1 makes
containment total: every block lives in exactly one Area. This brings the
ALREADY-authored substrate up to that contract, as an attributed, revertible
revision (ADR-209 — never a raw SQL mutation).

Three repairs (ADR-544 D7):

  1. RENAME — `data-slot="x"` becomes `data-area="x"` with its role stamped
     inline (`data-area-role`), resolved from the served registry by the page's
     own `data-arrange`. An unknown region defaults to `body`, which is the
     honest answer: it holds content and is not a heading or a picture.

  2. RE-HOME — a block that is a DIRECT CHILD of a page (a slide or a band),
     sitting in no region at all, is wrapped into an Area. A heading block goes
     to a heading-role Area; anything else goes to the page's primary body Area.
     Per D7 a block whose Area cannot be inferred lands in the primary body Area
     — never dropped, never left un-homed.

  3. CLEAR POSITION — on a DECK slide, `data-x`/`data-y`/`data-z` and their
     `--yx/--yy/--yz` declarations are removed, returning the block to its
     Area's flow (D3). Other style declarations are preserved byte-for-byte.

SCOPE. Deck and web only. An IMAGES stage is NEVER touched: free position is
that app's whole point (ADR-544 §4.3), its arrangement declares no Areas by
design, and `services/images/stage.py` seeds `data-x`/`data-y` deliberately. The
template gate below is what enforces that, and it reads the served registry
rather than a hardcoded slug list.

Attribution: `system:adr544-containment-heal` — a mechanical structural repair,
not an authored content edit. Every block keeps its `data-block-id` and its
inner HTML byte-for-byte; only its ENCLOSURE and its position measures change.

Usage:
    cd api
    python -m scripts.oneshot.adr544_heal_containment            # dry run
    python -m scripts.oneshot.adr544_heal_containment --execute  # apply
"""

from __future__ import annotations

import argparse
import logging
import re

logging.basicConfig(level=logging.WARNING)

USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"  # kvkthecreator@gmail.com

HEAL_AUTHOR = "system:adr544-containment-heal"
HEAL_MESSAGE = (
    "ADR-544 containment heal: every block now lives in exactly one Area. "
    "Regions renamed to data-area with their role stamped; blocks that sat "
    "directly on a slide re-homed into an Area; deck free-position measures "
    "cleared so a block holds a place in the hierarchy rather than a "
    "coordinate. Structural only — authored content is preserved."
)

#: The position measures ADR-544 D3 retires for decks. IMAGES keeps them.
_POSITION_ATTRS = ("data-x", "data-y", "data-z")
_POSITION_VARS = ("--yx", "--yy", "--yz")


def _role_for(area_name: str, roles: dict[str, str]) -> str:
    """The Area's role, from the served registry. An unknown region defaults to
    `body` — the honest answer for a region that holds content and is neither a
    heading nor a picture. Never invents a role outside the closed set."""
    role = roles.get(area_name)
    return role if role in ("heading", "body", "media", "aside") else "body"


def heal_html(content: str) -> tuple[str, int, int, int]:
    """Return (new_html, renamed, rehomed, cleared). new_html == content when
    nothing changed (so the caller writes no revision)."""
    from lxml import html as lxml_html

    from services.authoring import STUDIO_ARRANGEMENTS, STUDIO_LAYOUTS

    tpl = re.search(r'data-template="([a-z-]+)"', content or "")
    slug = tpl.group(1) if tpl else ""
    layout = STUDIO_LAYOUTS.get(slug)
    # Studio's paged media only. An IMAGES stage resolves through a different
    # registry and must keep its free composition (§4.3); a flow document has
    # no page grain to contain anything into (ADR-481 D1).
    if not layout or layout.get("mode") != "paged":
        return content, 0, 0, 0
    is_deck = slug == "deck"

    doc = lxml_html.fromstring(content)
    arrangements = STUDIO_ARRANGEMENTS.get(slug, {})

    renamed = rehomed = cleared = 0

    # Pages: a deck slide or a web band. Addressed by data-arrange, which is
    # what carries the arrangement identity the roles are resolved from.
    pages = doc.xpath("//*[@data-arrange]")
    for page in pages:
        arrange = page.get("data-arrange") or ""
        row = arrangements.get(arrange, {})
        roles = {a["name"]: a["role"] for a in row.get("areas", [])}
        places = {a["name"]: a.get("place") for a in row.get("areas", [])}

        # ── 1. RENAME: data-slot → data-area + inline role ────────────────
        for el in page.xpath(".//*[@data-slot]"):
            name = el.get("data-slot") or ""
            el.attrib.pop("data-slot", None)
            el.set("data-area", name)
            el.set("data-area-role", _role_for(name, roles))
            if places.get(name):
                el.set("data-area-place", places[name])
            renamed += 1

        # ── 2. RE-HOME: a block sitting directly on the page ──────────────
        # Direct children only: a block nested deeper is already inside some
        # region (or inside another block, which rides its parent).
        loose = [
            el
            for el in page.getchildren()
            if el.get("data-block") is not None
        ]
        if loose:
            heading_area = None
            body_area = None
            for el in page.xpath(".//*[@data-area]"):
                r = el.get("data-area-role")
                if r == "heading" and heading_area is None:
                    heading_area = el
                if r == "body" and body_area is None:
                    body_area = el
            for el in loose:
                is_heading = el.get("data-block") == "heading"
                target = heading_area if is_heading else body_area
                if target is None:
                    # No Area of that role exists yet — mint one in place, so a
                    # block is never dropped and never left un-homed (D7).
                    target = lxml_html.Element("div")
                    name = "heading" if is_heading else "main"
                    target.set("data-area", name)
                    target.set("data-area-role", "heading" if is_heading else "body")
                    el.addprevious(target)
                    if is_heading:
                        heading_area = target
                    else:
                        body_area = target
                # The tail text rides the element; move it with the element so
                # whitespace does not migrate out of the page.
                target.append(el)
                rehomed += 1

        # ── 3. CLEAR POSITION (deck only, D3) ─────────────────────────────
        if is_deck:
            for el in page.xpath(".//*[@data-x or @data-y or @data-z]"):
                touched = False
                for attr in _POSITION_ATTRS:
                    if el.get(attr) is not None:
                        el.attrib.pop(attr, None)
                        touched = True
                style = el.get("style") or ""
                if style:
                    keep = [
                        d.strip()
                        for d in style.split(";")
                        if d.strip()
                        and not any(d.strip().startswith(v + ":") for v in _POSITION_VARS)
                    ]
                    # Preserve every declaration that is not ours (the setMeasure
                    # convention: an artifact's own style is not ours to stomp).
                    if keep:
                        el.set("style", "; ".join(keep))
                    else:
                        el.attrib.pop("style", None)
                if touched:
                    cleared += 1

    if not (renamed or rehomed or cleared):
        return content, 0, 0, 0

    new_html = lxml_html.tostring(doc, encoding="unicode", doctype="<!doctype html>")
    return new_html, renamed, rehomed, cleared


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

    print(f"scanning {len(rows)} artifact(s) for pre-ADR-544 structure\n")
    total_renamed = total_rehomed = total_cleared = touched = 0

    for row in sorted(rows, key=lambda r: r["path"]):
        content = row.get("content") or ""
        new_html, renamed, rehomed, cleared = heal_html(content)
        if not (renamed or rehomed or cleared):
            continue
        touched += 1
        total_renamed += renamed
        total_rehomed += rehomed
        total_cleared += cleared
        verb = "HEAL" if execute else "DRY RUN"
        print(
            f"  {verb}  {row['path']}  "
            f"areas={renamed} rehomed={rehomed} position-cleared={cleared}"
        )
        if not execute:
            continue
        rev = write_revision(
            client,
            user_id=USER_ID,
            path=row["path"],
            content=new_html,
            authored_by=HEAL_AUTHOR,
            message=HEAL_MESSAGE,
            summary=(
                f"Containment heal: {renamed} region(s) named as Areas, "
                f"{rehomed} block(s) re-homed, {cleared} free position(s) cleared"
            ),
        )
        print(f"         rev={rev}")

    print(
        f"\n{touched} artifact(s) {'healed' if execute else 'would be healed'}; "
        f"{total_renamed} areas named, {total_rehomed} blocks re-homed, "
        f"{total_cleared} positions cleared."
    )
    if not execute:
        print("dry run — re-run with --execute to apply.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    raise SystemExit(main(args.execute))
