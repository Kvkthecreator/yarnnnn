"""The Studio — kernel constants + posture for the first authoring app.

ADR-440 (the app) + ADR-443 (the axiomatic model: blocks, layouts, seven
operations). This module is the Studio's PROGRAM half, housed as code per
ADR-440 D6 ("apps bring program, not substrate" — ADR-414 D2 precedent):

- ``STUDIO_BLOCKS``  — the ONE component vocabulary (ADR-443 R4): unifies the
  compose section-kinds (ADR-177) + the L3 affordance ancestry (ADR-245) +
  the reference model (ADR-440 D5) into a kernel-seeded grammar. It TEACHES
  (posture + palette) and never VALIDATES — grammar, not schema.
- ``STUDIO_LAYOUTS`` — layouts as first-class kernel data (ADR-443 D5):
  skin (CSS) + flow (grammar prose) + scaffold (annotated starter blocks).
  A template = layout × starter blocks; ``build_skeleton`` assembles it.
- ``build_studio_posture`` — the bound lane's authoring overlay, composed at
  turn time (ADR-440 D3). Pure: the runner does the I/O.

Nothing here is ever seeded into a workspace as a file; the only substrate
the Studio produces is the artifacts members author.

Consumers: ``routes/studio.py`` (templates + vocabulary + creation),
``services/lane_runner.py`` (posture via the conventions projection).

Prompt-change protocol: the posture text below is LLM-facing — changes MUST
be logged in ``api/prompts/CHANGELOG.md``.
"""

from __future__ import annotations

import re
from html import escape as html_escape, unescape as html_unescape
from typing import Optional

# Authoring turns rewrite/patch real documents — the chat-sized 2048 ceiling
# starves them. Applied by the lane runner when a lane is bound (ADR-440 D3).
STUDIO_LANE_MAX_TOKENS = 8192

# Paths a Studio artifact may be created at (ADR-440 D6: meaning-placed under
# the member write region — never an app-named root; the Studio owns no
# namespace, so this is a REGION constraint, not a ``studio/`` directory).
STUDIO_ARTIFACT_REGION = "/workspace/operation/"


# ---------------------------------------------------------------------------
# The block vocabulary (ADR-443 D4) — one grammar, kernel-seeded.
# `markup` is the teaching example the posture shows the lane; `label` is
# the operator word the palette shows the member (ADR-443 D3).
#
# ADR-528 D5 — `apps` is the per-app dimension this registry lacked while
# STUDIO_LAYOUTS has carried `app` since ADR-473 D2. That asymmetry is what
# made "drop callout and toggle from Docs" read as a menu-filtering question:
# there was nowhere to SAY a kind belongs to one app, so the only reachable
# lever was subsetting the menu — which AUTHORING.md refuses ("both doors
# offer every kind; what differs is which door, never what's in it"). The
# refusal is about a MEDIUM subsetting a shared roster at the door. Declaring
# ownership in the registry is the other thing entirely: the roster itself is
# app-scoped, and every door of every app still offers all of ITS roster.
#
# Absent `apps` = every app (the default). This is a grammar dimension, never
# a schema gate: an artifact holding a kind its app no longer offers still
# renders and still edits — the kind becomes an INERT NAME (ADR-511 D8), which
# is exactly what D5 specifies for the callout and toggle already in members'
# documents.
#
# ADR-539 D1 — a row DECLARES ITS BEHAVIOR. Four fields, every row, no
# defaults (explicit beats implicit at a kernel seam):
#   tier        — "text" (a click on flow is a caret) | "object" (a box,
#                 everywhere). ADR-525 D1's taxonomy; `structure` is a property
#                 of containers/pages, never of a kind.
#   elements    — the lowercase DOM tags recognized AS this kind at the intake
#                 seams (promotion, paste). Informational when promote=False.
#   promote     — may a bare tag be GUESSED into this kind? The FE promotion
#                 map is a pinned projection of {elements × promote=True};
#                 promote=True tags must therefore be unique across rows.
#                 `checklist` is the argued False (ADR-536: promotion is a
#                 guess from a TAG, and the checkbox list is the marked case).
#   convertible — does the member's Turn-into offer it?
#   cites       — "none" | "source" | "picture" (ADR-538 D1's rule as a FIELD).
#                 `group` is DERIVED from this (see GROUP_BY_CITES below), so
#                 a kind's group and its citation structurally cannot disagree.
# ---------------------------------------------------------------------------

STUDIO_BLOCKS: dict[str, dict[str, str]] = {
    # ADR-487 D1 — the type ramp made playable. Every scaffold already uses
    # heading blocks (they anchor pages); this registry row makes the insert
    # and turn-into surfaces offer what the scaffolds always used. The TAG
    # carries the rung (h1/h2/h3 — the FE's level targets swap the tag, same
    # kind); the kernel sizes each level from the type scale, so headings are
    # design-system-fed by construction. The re-arrange protection ("heading
    # blocks anchor the page and are not swept") is untouched — it never
    # required headings to be unauthorable.
    "heading": {
        "label": "Heading",
        "tier": "text",
        "cites": "none",
        "convertible": True,
        "elements": ("h1", "h2", "h3"),
        "promote": True,
        "description": "A heading on the type ramp — the tag (h1/h2/h3) carries the level.",
        "markup": '<h2 data-block="heading" data-block-id="b13">Heading</h2>',
    },
    "prose": {
        "label": "Text",
        "tier": "text",
        "cites": "none",
        "convertible": True,
        "elements": ("p", "div", "pre"),
        "promote": True,
        "description": "A heading + flowing paragraphs — the default content unit.",
        "markup": '<section data-block="prose" data-block-id="b1"><h2>Heading</h2><p>…</p></section>',
    },
    # ADR-528 D5 — NOT offered by Docs. A callout is prose in a container
    # (<aside>) with its own caret, and Google Docs has no equivalent; it sits
    # in TEXT_BLOCK_KINDS while BEING a container, which is one of the two
    # rows that most muddied the text/object line the ADR carves. Studio keeps
    # it: a deck or a landing page is a composed surface where an offset aside
    # is an authored object, and ADR-487 D2's variant system (note/success/
    # warning) plus the `block-callout` token grain are built on it there.
    "callout": {
        "label": "Callout",
        "tier": "text",
        "cites": "none",
        "convertible": True,
        "elements": ("aside",),
        "promote": False,
        "apps": ("studio",),
        "description": "A visually offset aside that highlights one point.",
        "markup": '<aside data-block="callout" data-block-id="b2"><p>…</p></aside>',
    },
    "quote": {
        "label": "Quote",
        "tier": "text",
        "cites": "none",
        "convertible": True,
        "elements": ("blockquote",),
        "promote": True,
        "description": "A pull quote with optional attribution.",
        "markup": '<blockquote data-block="quote" data-block-id="b3"><p>…</p><cite>…</cite></blockquote>',
    },
    "checklist": {
        "label": "Checklist",
        "tier": "text",
        "cites": "none",
        "convertible": True,
        "elements": ("ul",),
        "promote": False,
        "description": "A list of discrete items or steps.",
        "markup": '<ul data-block="checklist" data-block-id="b4"><li>…</li></ul>',
    },
    # ADR-536 D1 — the two list kinds the registry never had. `checklist` was
    # the ONLY list row, and it is a checkbox list (list-style:none + a ☐
    # pseudo-element), so a member wanting an ordinary bullet or a numbered
    # list had nothing to pick and nothing to Turn into. Meanwhile the paste
    # allowlist admits UL/OL and ADR-521 D4 shipped Tab/⇧Tab nesting "in a
    # list" — so the runtime could nest and render a container the vocabulary
    # could not NAME. These rows close that gap; the mechanism is entirely
    # existing (rows, not machinery — the ADR-456 W1 `divider` precedent).
    #
    # Both are `<ul>`/`<ol>` with plain list-style, i.e. what the kernel's own
    # element defaults already draw. They are TEXT kinds: prose inside list
    # items, which is why they join TEXT_BLOCK_KINDS and the turn-into set.
    "list": {
        "label": "Bulleted list",
        "tier": "text",
        "cites": "none",
        "convertible": True,
        "elements": ("ul",),
        "promote": True,
        "description": "A bulleted list — unordered items.",
        "markup": '<ul data-block="list" data-block-id="b14"><li>…</li></ul>',
    },
    "numbered": {
        "label": "Numbered list",
        "tier": "text",
        "cites": "none",
        "convertible": True,
        "elements": ("ol",),
        "promote": True,
        "description": "A numbered list — ordered steps or ranked items.",
        "markup": '<ol data-block="numbered" data-block-id="b15"><li>…</li></ol>',
    },
    # ADR-456 Wave 1 — the builder/Notion registry growth (rows, not mechanisms).
    "divider": {
        "label": "Divider",
        "tier": "object",
        "cites": "none",
        "convertible": False,
        "elements": ("hr",),
        "promote": False,
        "description": "A horizontal rule between sections of content.",
        "markup": '<hr data-block="divider" data-block-id="b9">',
    },
    # ADR-528 D5 — NOT offered by Docs, same reasoning as callout: prose in a
    # container (<details>), a caret inside it, no Google Docs equivalent.
    # It is also the kind ADR-526 §6 names as what a COLLAPSIBLE HEADING would
    # need — and that affordance is explicitly awaiting evidence, so offering
    # a collapsible container in the meantime answers the question by accident.
    "toggle": {
        "label": "Toggle",
        "tier": "text",
        "cites": "none",
        "convertible": True,
        "elements": ("details",),
        "promote": False,
        "apps": ("studio",),
        "description": "A collapsible section — a summary line that expands.",
        "markup": '<details data-block="toggle" data-block-id="b10"><summary>Summary line</summary><p>…</p></details>',
    },
    "button": {
        "label": "Button",
        "tier": "object",
        "cites": "none",
        "convertible": False,
        "elements": ("p",),
        "promote": False,
        "description": "A call-to-action link, styled by the palette.",
        "markup": '<p data-block="button" data-block-id="b11"><a href="https://…">Call to action</a></p>',
    },
    # ADR-538 D3 — the composite component. The landing-page-style card the
    # operator pointed at (a labelled container holding icon/name/phrase/pill
    # rows) is STYLED HTML: it cites nothing, so by D1 it is `content`, and the
    # kernel draws it. No new machinery — this is the `metrics` shape one
    # composition deeper, and it is why the answer to "can we scope these kinds
    # of components in" is a registry row rather than an engine.
    #
    # `apps: ("studio",)` for the ADR-528 D5 reason that governs callout and
    # toggle: a composed card is an authored object on a deck or a landing
    # page, and Docs is the flow/caret medium where it has no equivalent.
    #
    # Motion is NOT in the markup — it is kernel CSS (D4), under a
    # prefers-reduced-motion guard. A component is legible with motion disabled
    # by construction, which is what makes the guard safe to honour.
    "component": {
        "label": "Component",
        "tier": "object",
        "cites": "none",
        "convertible": False,
        "elements": ("div",),
        "promote": False,
        "apps": ("studio",),
        "description": "A composed card — a labelled container of icon/name/value rows.",
        "markup": (
            '<div data-block="component" data-block-id="b16">'
            "<header><span>Label</span></header>"
            '<div class="row"><span class="name">Name</span>'
            '<span class="value">Value</span>'
            '<span class="pill">tag</span></div>'
            "<footer>Footnote</footer>"
            "</div>"
        ),
    },
    "table": {
        "label": "Table",
        "tier": "object",
        "cites": "source",
        "convertible": False,
        "elements": ("table",),
        "promote": True,
        "description": "A live table CITED from a workspace CSV (never pasted).",
        "markup": '<div data-block="table" data-block-id="b5" data-ref="operation/…/data.csv" data-ref-kind="table"></div>',
    },
    # ADR-538 D1 — re-filed `data` → `content`. It cites nothing: the numbers
    # are typed into the markup (`<strong>42%</strong>`), so by the rule (a
    # `data` kind cites a SOURCE and is projected) it was never data. The
    # mis-filing was the same class as chart's and is corrected in the same
    # motion; the group is a served display label with no code branching on it,
    # so this moves a palette heading and nothing else.
    #
    # Making a metric CITE — a headline number that is a defensible, attributed
    # claim — is the genuinely valuable version and is NOT delivered here: it
    # needs sub-file (cell) addressing, which the substrate does not have (the
    # ADR-528 finding). Named as the open question, not smuggled in.
    "metrics": {
        "label": "Metrics",
        "tier": "object",
        "cites": "none",
        "convertible": False,
        "elements": ("div",),
        "promote": False,
        "description": "A row of headline numbers with labels.",
        "markup": '<div data-block="metrics" data-block-id="b6"><div class="metric"><strong>42%</strong><span>label</span></div></div>',
    },
    # ADR-538 D2 — the chart cites its DATA, not a picture of it. Before this
    # ADR the row was filed `data` while citing `./assets/chart.svg`, and sat
    # in MEDIA_BLOCK_KINDS beside figure/gallery — the registry's own
    # confession that it was media wearing a data label. The consequence was
    # exact: change the numbers and NOTHING happened, because the citation
    # pointed at a rendering. (The two live instances carried their data only
    # in `alt` prose, with an EMPTY data-ref-rev — an unpinned photograph.)
    #
    # Now it is a sibling of `table`: same citation machinery, same pinned
    # fallback, drawn by `csvToChartHtml` beside `csvToTableHtml`. The visual
    # intent rides as attributes (data-chart = bar|line|donut), because a
    # chart kind is an enumerated value the kernel can pre-declare, not
    # continuous geometry.
    #
    # NOT an ADR-417 reversal: 417 retired an owned GENERATION engine; this
    # projects the workspace's own cited substrate, which the projection has
    # done for CSVs since ADR-440 D5. It rents nothing and owns no engine.
    "chart": {
        "label": "Chart",
        "tier": "object",
        "cites": "source",
        "convertible": False,
        "elements": ("figure",),
        "promote": False,
        "description": "A chart PROJECTED from a cited workspace CSV (never a pasted picture).",
        "markup": '<figure data-block="chart" data-block-id="b7" data-chart="bar"><div data-ref="operation/…/data.csv" data-ref-kind="chart" data-ref-rev="<head-rev-id>"></div><figcaption>…</figcaption></figure>',
    },
    "figure": {
        "label": "Image",
        "tier": "object",
        "cites": "picture",
        "convertible": False,
        "elements": ("figure",),
        "promote": True,
        "description": "A workspace image CITED by reference, with a caption.",
        "markup": '<figure data-block="figure" data-block-id="b8"><img data-ref="operation/…/img.png" data-ref-rev="<head-rev-id>" alt="…"><figcaption>…</figcaption></figure>',
    },
    "gallery": {
        "label": "Gallery",
        "tier": "object",
        "cites": "picture",
        "convertible": False,
        "elements": ("div",),
        "promote": False,
        "description": "A grid of workspace images, each CITED by reference.",
        "markup": '<div data-block="gallery" data-block-id="b12"><figure><img data-ref="operation/…/img.png" data-ref-rev="<head-rev-id>" alt=""><figcaption></figcaption></figure></div>',
    },
}

# ADR-539 D1 — `group` is a DERIVATION of `cites`, never a field. ADR-538
# found `chart` and `metrics` mis-filed because group and citation could
# disagree; deriving makes the disagreement unrepresentable. The wire shape is
# unchanged: the vocabulary route still serves `group`, computed here.
GROUP_BY_CITES = {"none": "content", "source": "data", "picture": "media"}


def block_group(row: dict) -> str:
    """The served display group, derived from what the kind cites (ADR-539 D1)."""
    return GROUP_BY_CITES[row["cites"]]


# ADR-539 D3 — the heading rung set, declared ONCE. At audit (2026-08-09) the
# system gave four different answers to "which heading levels exist" across
# eight sites (outline h1–h3, AI outline h1–h2, crumb h1–h2, promotion h1–h6,
# turn-into harvest h1–h4) — which is why an h4 was named "Heading" by the
# pane and invisible to the outline, the crumb, and the lane in the same
# instant. Every consumer now reads this constant: `extract_outline` below,
# the served vocabulary (`heading_rungs`), and — via the ADR-539 parity gate —
# the FE's outline walk, ramp rows, promotion map, and the runtime's
# `headingAboveOf`. Intake CLAMPS to this set (D4): h4–h6 arrive as h3.
HEADING_RUNGS: tuple[int, ...] = (1, 2, 3)


# ADR-546 D1 — THE RUNG, declared once for the flow medium.
#
# Subordination on a document is ONE fact with two spellings: the HEADING rung
# (h1/h2/h3, subordinating everything to the next heading of equal-or-shallower
# rung — ADR-526 D1's span) and the NESTING rung (a list item's depth, or a
# prose block's step in from the measure).
#
# At the 2026-08-10 audit depth was declared THREE times and the three
# declarations did not know about each other:
#
#   - HEADING_RUNGS = (1, 2, 3)        — read by six consumers
#   - the `indent` token's values 1..3 — read by ONE pane row, no keyboard door
#   - `ul ul ul` in the kernel CSS     — read by NOBODY, while rendering three
#                                        levels deep, so a member could author
#                                        with Tab a hierarchy nothing could name
#
# All three independently landed on depth 3, which is what proves they are one
# concept rather than three coincidences. `FLOW_RUNGS` is that concept, and the
# indent token's values + the nesting CSS are both GENERATED from it below —
# so a fourth interpretation of depth cannot ship by editing one list.
#
# Paged depth is NOT this: on a slide, depth is containment (which Area holds
# the block — ADR-544 D1/D2). A rung is a flow fact, which is why the `indent`
# token declares `grains: ("flow",)`.
FLOW_RUNGS: tuple[int, ...] = HEADING_RUNGS

#: The deepest rung the medium speaks. Intake clamps to it (ADR-539 D4 for
#: headings; ADR-546 D1 extends the same migration-by-use rule to nesting).
DEEPEST_FLOW_RUNG: int = max(FLOW_RUNGS)


# ---------------------------------------------------------------------------
# Layouts (ADR-443 D5) — skin + flow + scaffold. A template = layout ×
# starter blocks; the three ADR-440 hardcoded skeletons are DELETED and
# assembled from these rows (Singular Implementation).
# ---------------------------------------------------------------------------

_SHARED_CSS = """
    :root { --ink: #1a1a1a; --muted: #6b6b6b; --accent: #b4540a; --paper: #fdfcfa; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Georgia, 'Times New Roman', serif; color: var(--ink);
           background: var(--paper); line-height: 1.6; }
    h1, h2, h3 { font-weight: 600; line-height: 1.2; }
    img { max-width: 100%; height: auto; }
    figure { margin: 1.5rem 0; }
    figcaption { font-size: var(--text-sm, 0.85rem); color: var(--muted); margin-top: 0.5rem; }
    table { border-collapse: collapse; width: 100%; font-size: var(--text-sm, 0.9rem); }
    th, td { border: 1px solid var(--ink-10, #ddd); padding: 0.4rem 0.6rem; text-align: left; }
    aside[data-block="callout"] { border-left: 3px solid var(--accent);
        background: rgba(180,84,10,0.06); padding: 0.75rem 1rem; margin: 1.25rem 0; }
    blockquote[data-block="quote"] { border-left: 3px solid var(--ink-10, #ddd); padding: 0.5rem 1rem;
        margin: 1.25rem 0; font-style: italic; }
    blockquote[data-block="quote"] cite { display: block; margin-top: 0.5rem;
        font-size: var(--text-sm, 0.85rem); color: var(--muted); font-style: normal; }
    ul[data-block="checklist"] { list-style: none; margin: 1rem 0; }
    ul[data-block="checklist"] li { padding-left: 1.5rem; position: relative; margin: 0.35rem 0; }
    ul[data-block="checklist"] li::before { content: "☐"; position: absolute; left: 0; }
    div[data-block="metrics"] { display: flex; gap: 1.5rem; flex-wrap: wrap; margin: 1.25rem 0; }
    div[data-block="metrics"] .metric strong { display: block; font-size: var(--text-2xl, 1.6rem); }
    div[data-block="metrics"] .metric span { font-size: var(--text-xs, 0.8rem); color: var(--muted); }
""".strip("\n")

#: A layout's **mode** — the composition seam (2026-07-15; re-cut by ADR-505).
#:
#:   paged (deck, web) — the CONTAINER is the unit. A slide IS a page; a web
#:     band IS a section. "New slide/band" is a primary authoring act, and a
#:     navigator strip is real navigation (PowerPoint/Keynote/Wix).
#:
#:   flow  (document) — BLOCKS are the unit and they flow. There is no section
#:     to insert; the outline is a derived table of contents, not structure
#:     (Notion/Docs).
#:
#: MODE IS NOT THE GEOMETRY SEAM (ADR-505 D3). `paged` answers only *does this
#: type have page units*. Whether a coordinate space exists is a SEPARATE axis,
#: derived from `.slide` ancestry via the `block-staged` predicate — which is why
#: deck has x/y/z and `web` does not, while both are `paged`. The two questions
#: were conflated under one word; naming them apart is what let `web` merge
#: article+page without inheriting the deck object grammar. A slide has a FRAME
#: (16:9, always — a percentage is stable); a web page has a VIEWPORT (390px to
#: 2560px — a percentage means something different at every width, and pinning it
#: is the per-breakpoint-editing refusal in another costume). ADR-461 D4 stands.
#:
#: Arrangements are `paged`-ONLY (ADR-481 D1, hardened by ADR-505 D1): a flowing
#: document has no page-grain unit. Two columns inside a document would be a
#: BLOCK kind, not an arrangement.
#:
#: NB: distinct from each layout's `flow` KEY below, which is prose describing
#: the layout's markup shape to the lane. `mode` is the machine seam; `flow` is
#: pedagogy.
STUDIO_LAYOUT_MODES = ("flow", "paged")

#: THE MEDIA ARE THREE (ADR-505 D1) — `document` · `deck` · `web`, one type per
#: medium the member actually works in — and THE HOUSINGS ARE TWO (ADR-518 D1):
#:
#:   document — CAPTURE. Notes, drafts, working docs. Continuous, internal,
#:              revised forever. Notion-class, never Word-class (no pagination,
#:              ADR-480 D6). The workspace's centre of gravity. OWNED BY DOCS —
#:              the row lives in `services/docs.py::DOCS_LAYOUTS` (the app
#:              boundary is the MODULE, ADR-473 D2) and registers below.
#:   deck     — PRESENT. A framed stage, spoken over. PowerPoint-class: the only
#:              type with a coordinate space, because the only one with a frame.
#:   web      — PUBLISH. A banded page read by someone OUTSIDE the workspace.
#:              Medium/Wix-class: band sequence + typography, no placement.
#:
#: This table therefore carries STUDIO'S OWN TWO — the paged/layout media. The
#: type SET is unchanged by the split (no fourth type, ADR-505 stands); only
#: the housing moved, exactly as `canvas` once did.
#:
#: Four types (document · deck · article · page) implied four coordinate systems
#: where there were only ever three media, and `article` was the tell — a
#: publishing shape wearing an internal-document chrome, never once used for real
#: work. ADR-505 D2 merged it into `web`.
#:
#: `canvas` IS NOT A STUDIO TYPE. It left for the IMAGES app as `image`
#: (ADR-472 D1/D7, migrated by `scripts/oneshot/adr472_migrate_canvas_to_image`)
#: and lives in `services/images/stage.py::STAGE`. It is absent from this table,
#: absent from RETIRED_LAYOUT_SLUGS (a Studio alias would re-claim it), and
#: `app_for_kind("canvas")` returns None on purpose — a stale `canvas` artifact
#: opens in the generic viewer and belongs to no app's recents. Do not add a row
#: for it here; the app boundary is the MODULE (ADR-473 D2).
STUDIO_LAYOUTS: dict[str, dict[str, str]] = {
    "deck": {
        "app": "studio",
        "label": "Deck",
        "mode": "paged",
        "description": "A slide deck — one idea per slide, spoken over.",
        "flow": (
            "each slide is <section class=\"slide\"> (a flow container, not a "
            "block); blocks live INSIDE slides. The first slide is the title "
            "slide (kicker + h1 thesis); every other slide is one idea led by an "
            "<h2>. A slide's title, kicker, and framing lines ARE heading blocks "
            "(data-block=\"heading\") so the member can edit them in place — keep "
            "them annotated. Keep slide text sparse — a deck is spoken over, not read."
        ),
        "skin": """
    body { background: var(--deck-stage, #e8e4de); }
    /* A deck slide is LANDSCAPE 16:9 — a fixed-aspect page, centered, one per
       screen, in the canvas AND in a scaled thumbnail (the navigator renders
       the same markup).

       The slide's BOX is not declared here — it is kernel-owned
       (`html[data-template="deck"] .slide` in STUDIO_KERNEL_CSS), because a
       layout skin is baked once at creation and could never reach the decks
       that already exist. This skin owns the slide's LOOK; the kernel owns the
       frame. What used to sit here was `width: min(100%, 62rem)`, which read
       the container and made a deck's geometry depend on the screen. */
    .slide { margin: 1.5rem auto;
             padding: 3.5rem 4rem; display: flex; flex-direction: column;
             justify-content: center; background: var(--paper);
             box-shadow: 0 1px 6px rgba(0,0,0,0.08); overflow: hidden;
             page-break-after: always; }
    .slide h1 { font-size: var(--text-4xl, 2.4rem); max-width: 34rem; }
    .slide h2 { font-size: var(--text-2xl, 1.7rem); margin-bottom: 1rem; }
    .slide .kicker { color: var(--accent); font-size: var(--text-sm, 0.85rem);
                     letter-spacing: 0.08em; text-transform: uppercase;
                     margin-bottom: 1rem; }
    .slide p { max-width: 36rem; }
    .slide .cols { display: flex; gap: 2.5rem; align-items: flex-start; }
    .slide .col { flex: 1; min-width: 0; }
""".strip("\n"),
        "scaffold": """<section class="slide" data-arrange="title">
  <div data-area="heading" data-area-role="heading">
    <p class="kicker" data-block="heading" data-block-id="k1">Untitled deck</p>
    <h1 data-block="heading" data-block-id="t1">The one-line thesis goes here.</h1>
    <p data-block="heading" data-block-id="f1">Subtitle or framing sentence.</p>
  </div>
</section>
<section class="slide" data-arrange="content">
  <div data-area="heading" data-area-role="heading">
    <h2 data-block="heading" data-block-id="t2">First point</h2>
  </div>
  <div data-area="main" data-area-role="body">
    <div data-block="prose" data-block-id="b1">
      <p>One idea per slide.</p>
    </div>
  </div>
</section>""",
    },
    # ADR-505 D2: the OUTWARD type — `article` and `page` merged. Both answered
    # one question ("HTML for someone outside the workspace"); the split asked
    # the member to pre-classify an essay against a landing page before writing
    # a word, and neither was ever used for real work (2 articles + 1 page at
    # the cut, all `test-*`). The band stack serves both: a `prose-header` band
    # opens a blog post, `hero`/`cta` open a landing page, and the difference is
    # which bands you stack — a composition choice, not a type.
    #
    # BAND-FIRST, NEVER OBJECT-FIRST (ADR-505 D3). No x/y/z here, ever: a web
    # page has a VIEWPORT, not a frame (ADR-461 D4), so a percentage position
    # means something different at every width and pinning it is per-breakpoint
    # editing. The reference class agrees — Medium, Substack, Ghost ship zero
    # positional control; the tools that do (Framer/Webflow) pay with a
    # breakpoint editor we refuse. Geometry is unreachable here STRUCTURALLY:
    # `block-staged` tests `.slide` ancestry and a web band is not a slide.
    "web": {
        "app": "studio",
        "label": "Web",
        "mode": "paged",
        "description": "A published page — blog post, essay, landing page.",
        "flow": (
            "one <main> of full-width section BANDS, each <section data-arrange=…> "
            "stacked vertically. A blog post or essay opens with a `prose-header` "
            "band (kicker/h1/standfirst/byline) and continues in `content` bands; "
            "a landing page opens with a `hero` (kicker + h1 promise + tagline + "
            "button), stacks feature/testimonial bands, and closes on a "
            "call-to-action. Band content centers itself in a reading column; a "
            "band may wear a cited background image (data-ref + "
            "data-ref-kind=\"background\" on the section) with a data-scrim for "
            "legibility. Written to be read by someone OUTSIDE the workspace — "
            "never position blocks (a page has a viewport, not a frame)."
        ),
        "skin": """
    section[data-arrange] { padding: 4rem 1.5rem; }
    section[data-arrange] > * { max-width: 56rem; margin-left: auto; margin-right: auto; }
    section[data-arrange="hero"] { padding: 6rem 1.5rem; text-align: center; }
    h1 { font-size: var(--text-4xl, 2.6rem); margin-bottom: 0.75rem; }
    .kicker { color: var(--accent); font-size: var(--text-sm, 0.85rem); letter-spacing: 0.08em;
              text-transform: uppercase; margin-bottom: 1rem; }
    .tagline { font-size: var(--text-lg, 1.2rem); color: var(--muted); }
    section[data-arrange] h2 { font-size: var(--text-2xl, 1.8rem); margin-bottom: 1rem; }
    /* The long-form band: a narrower reading column than a landing band, and a
       byline. This is the article shape, expressed as a band. */
    section[data-arrange="prose-header"] { padding: 5rem 1.5rem 2rem; }
    section[data-arrange="prose-header"] > *,
    section[data-arrange="prose"] > * { max-width: 42rem; }
    section[data-arrange="prose-header"] .standfirst { font-size: var(--text-lg, 1.15rem);
              color: var(--muted); }
    section[data-arrange="prose-header"] .byline { font-size: var(--text-sm, 0.85rem);
              color: var(--muted); margin-top: 1rem; letter-spacing: 0.02em; }
    section[data-arrange="prose"] { padding: 1rem 1.5rem; }
    section[data-arrange="prose"] [data-block="prose"] p { margin: 1rem 0; }
""".strip("\n"),
        "scaffold": """<main>
  <section data-arrange="hero">
    <div data-area="main" data-area-role="body">
      <p class="kicker" data-block="heading" data-block-id="k1">Untitled page</p>
      <h1 data-block="heading" data-block-id="t1">The headline promise.</h1>
      <p class="tagline" data-block="heading" data-block-id="s1">One sentence expanding on it.</p>
      <p data-block="button" data-block-id="c1"><a href="https://…">Call to action</a></p>
    </div>
  </section>
  <section data-arrange="content">
    <div data-area="heading" data-area-role="heading">
      <h2 data-block="heading" data-block-id="t2">First section</h2>
    </div>
    <div data-area="main" data-area-role="body">
      <div data-block="prose" data-block-id="b1"><p>Start here.</p></div>
    </div>
  </section>
</main>""",
    },
}


# ---------------------------------------------------------------------------
# Arrangements (ADR-447) — the composition layer, PROMOTED from ADR-444's
# deck-only "slide masters" to a first-class, per-document-type grammar.
# An arrangement says WHERE content goes on a page/section: grids, AREAS,
# overlays, sizings. It is orthogonal to the block (what content is) and the
# skin (how it looks). v1 is page-grain (whole page/slide); section-band
# nesting is phase 2.
#
# ADR-544 — THE CONTAINMENT LAW. The four grains are Slide → Layout → Area →
# Block, and **every block lives in exactly one Area**: no block is a direct
# child of a slide. The pre-544 registry disagreed with itself — `title` put its
# heading in a slot while `content`/`two-column` left a bare `<h2>` as a slide
# child, and `comparison` nested a slot inside a slot-less `.col`. Three
# structural stories for one hierarchy is what made the surface unable to speak
# it (ADR-544 §1.1). One story now: an Area IS the region element, so a `.col`
# that holds blocks carries the Area markers itself and `.cols` is the parent's
# declared LAYOUT, never a rung of its own (D2).
#
# Each row: label + description (operator words) · grain ('page' in v1) ·
# areas (each {name, role, place?}: role from the closed set
# heading|body|media|aside — `body` accepts blocks on a reflow, `heading`
# anchors; `place` disambiguates same-role siblings) · fragment (the
# deterministic insertion payload — data-arrange names the arrangement;
# data-area/data-area-role/data-area-place mark the regions; the FE stamps
# fresh block ids and writes through the mechanical door). Grammar not schema
# (R4): an un-arranged artifact stays valid.
#
# The role is the Area's IDENTITY, not a hint: the chrome labels from it
# (D4 — a raw `data-area` name is never a display word) and `applyArrangement`
# maps Area→Area by it on a re-lay (D6).
# ---------------------------------------------------------------------------

STUDIO_ARRANGEMENTS: dict[str, dict[str, dict]] = {
    "deck": {
        "title": {
            "label": "Title slide",
            "description": "Kicker, thesis headline, framing line.",
            "grain": "page",
            "areas": [{"name": "heading", "role": "heading"}],
            "fragment": """<section class="slide" data-arrange="title">
  <div data-area="heading" data-area-role="heading">
    <p class="kicker" data-block="heading" data-block-id="k1">Kicker</p>
    <h1 data-block="heading" data-block-id="t1">The headline goes here.</h1>
    <p data-block="heading" data-block-id="f1">Framing sentence.</p>
  </div>
</section>""",
        },
        "content": {
            "label": "Content",
            "description": "A heading with content below.",
            "grain": "page",
            "areas": [
                {"name": "heading", "role": "heading"},
                {"name": "main", "role": "body"},
            ],
            "fragment": """<section class="slide" data-arrange="content">
  <div data-area="heading" data-area-role="heading">
    <h2 data-block="heading" data-block-id="t1">Slide title</h2>
  </div>
  <div data-area="main" data-area-role="body"></div>
</section>""",
        },
        "two-column": {
            "label": "Two column",
            "description": "A heading over two side-by-side regions.",
            "grain": "page",
            "areas": [
                {"name": "heading", "role": "heading"},
                {"name": "main", "role": "body", "place": "left"},
                {"name": "side", "role": "body", "place": "right"},
            ],
            "fragment": """<section class="slide" data-arrange="two-column">
  <div data-area="heading" data-area-role="heading">
    <h2 data-block="heading" data-block-id="t1">Slide title</h2>
  </div>
  <div class="cols">
    <div class="col" data-area="main" data-area-role="body" data-area-place="left"></div>
    <div class="col" data-area="side" data-area-role="body" data-area-place="right"><div data-block="prose" data-block-id="b1"><p>Second column.</p></div></div>
  </div>
</section>""",
        },
        "comparison": {
            "label": "Comparison",
            "description": "Two headed columns, side by side.",
            "grain": "page",
            "areas": [
                {"name": "heading", "role": "heading"},
                {"name": "left", "role": "body", "place": "left"},
                {"name": "right", "role": "body", "place": "right"},
            ],
            "fragment": """<section class="slide" data-arrange="comparison">
  <div data-area="heading" data-area-role="heading">
    <h2 data-block="heading" data-block-id="t1">Slide title</h2>
  </div>
  <div class="cols">
    <div class="col" data-area="left" data-area-role="body" data-area-place="left"><h3 data-block="heading" data-block-id="l1">Option A</h3></div>
    <div class="col" data-area="right" data-area-role="body" data-area-place="right"><h3 data-block="heading" data-block-id="r1">Option B</h3></div>
  </div>
</section>""",
        },
        "quote": {
            "label": "Quote",
            "description": "One centered pull quote.",
            "grain": "page",
            "areas": [{"name": "main", "role": "body"}],
            "fragment": """<section class="slide" data-arrange="quote">
  <div data-area="main" data-area-role="body">
    <blockquote data-block="quote" data-block-id="b1"><p>The quote.</p><cite>Attribution</cite></blockquote>
  </div>
</section>""",
        },
        # ADR-453: the two deck rows that make the media role + tone token real.
        "picture-with-caption": {
            "label": "Picture with caption",
            "description": "A big cited image beside its commentary.",
            "grain": "page",
            "areas": [
                {"name": "heading", "role": "heading"},
                {"name": "media", "role": "media", "place": "left"},
                {"name": "caption", "role": "aside", "place": "right"},
            ],
            "fragment": """<section class="slide" data-arrange="picture-with-caption">
  <div data-area="heading" data-area-role="heading">
    <h2 data-block="heading" data-block-id="t1">Slide title</h2>
  </div>
  <div class="cols">
    <div class="col" data-area="media" data-area-role="media" data-area-place="left"></div>
    <div class="col" data-area="caption" data-area-role="aside" data-area-place="right"><div data-block="prose" data-block-id="b1"><p>What this picture shows, and why it matters.</p></div></div>
  </div>
</section>""",
        },
        "section-header": {
            "label": "Section header",
            "description": "A full-tone divider slide that names the next part.",
            "grain": "page",
            "areas": [{"name": "heading", "role": "heading"}],
            "fragment": """<section class="slide" data-arrange="section-header" data-tone="inverse">
  <div data-area="heading" data-area-role="heading">
    <p class="kicker" data-block="heading" data-block-id="k1">Part</p>
    <h1 data-block="heading" data-block-id="t1">Section title</h1>
  </div>
</section>""",
        },
        # ADR-456 Wave 1 — the builder-class deck rows. Their CSS lives in the
        # KERNEL stylesheet (not the layout skin) so they retrofit into
        # existing decks via the versioned upsert.
        "agenda": {
            "label": "Agenda",
            "description": "A heading over the run of topics.",
            "grain": "page",
            "areas": [
                {"name": "heading", "role": "heading"},
                {"name": "main", "role": "body"},
            ],
            "fragment": """<section class="slide" data-arrange="agenda">
  <div data-area="heading" data-area-role="heading">
    <h2 data-block="heading" data-block-id="t1">Agenda</h2>
  </div>
  <div data-area="main" data-area-role="body">
    <ul data-block="checklist" data-block-id="b1"><li>First topic</li><li>Second topic</li><li>Third topic</li></ul>
  </div>
</section>""",
        },
        "big-number": {
            "label": "Big number",
            "description": "One headline metric, front and center.",
            "grain": "page",
            "areas": [
                {"name": "heading", "role": "heading"},
                {"name": "main", "role": "body"},
            ],
            "fragment": """<section class="slide" data-arrange="big-number">
  <div data-area="heading" data-area-role="heading">
    <p class="kicker" data-block="heading" data-block-id="k1">The headline number</p>
  </div>
  <div data-area="main" data-area-role="body">
    <div data-block="metrics" data-block-id="b1"><div class="metric"><strong>42%</strong><span>what it measures</span></div></div>
  </div>
</section>""",
        },
        "full-bleed": {
            "label": "Full-bleed image",
            "description": "One cited image filling the whole slide.",
            "grain": "page",
            "areas": [{"name": "media", "role": "media"}],
            "fragment": """<section class="slide" data-arrange="full-bleed">
  <div data-area="media" data-area-role="media"></div>
</section>""",
        },
        "closing": {
            "label": "Closing",
            "description": "A full-tone thank-you slide with the next step.",
            "grain": "page",
            "areas": [{"name": "heading", "role": "heading"}],
            "fragment": """<section class="slide" data-arrange="closing" data-tone="inverse">
  <div data-area="heading" data-area-role="heading">
    <p class="kicker" data-block="heading" data-block-id="k1">Thank you</p>
    <h1 data-block="heading" data-block-id="t1">The closing line.</h1>
    <p data-block="heading" data-block-id="f1">Contact · next step</p>
  </div>
</section>""",
        },
    },
    # ADR-456 D4 (Wave 3): the web layout's band family — the builder-class
    # section stack (hero · content · features · testimonial · CTA · footer),
    # widened by ADR-505 D2 with the two LONG-FORM bands that carry what the
    # `article` layout used to be (prose-header · prose). The registry key is
    # `web`; the `grain: page` field is unrelated — that is the page-GRAIN of the
    # arrangement (whole-page vs section-band), untouched by the rename.
    "web": {
        "prose-header": {
            "label": "Article header",
            "description": "The long-form opening — kicker, title, standfirst, byline.",
            "grain": "page",
            # `main`/body, not `heading`: the byline sits alongside the headings
            # and the role ladder routes body content PAST a heading-role Area.
            "areas": [{"name": "main", "role": "body"}],
            "fragment": """<section data-arrange="prose-header">
  <div data-area="main" data-area-role="body">
    <p class="kicker" data-block="heading" data-block-id="k1">Kicker</p>
    <h1 data-block="heading" data-block-id="t1">The title of the piece.</h1>
    <p class="standfirst" data-block="heading" data-block-id="s1">The one-sentence promise to the reader.</p>
    <p class="byline" data-block="heading" data-block-id="y1">Byline · Date</p>
  </div>
</section>""",
        },
        "prose": {
            "label": "Prose",
            "description": "A narrow reading column — the body of a post or essay.",
            "grain": "page",
            "areas": [{"name": "main", "role": "body"}],
            "fragment": """<section data-arrange="prose">
  <div data-area="main" data-area-role="body">
    <div data-block="prose" data-block-id="b1"><p>Start writing.</p></div>
  </div>
</section>""",
        },
        "hero": {
            "label": "Hero",
            "description": "The headline band — kicker, promise, tagline, button.",
            "grain": "page",
            # `main`/body, not `heading`: this band carries a button alongside
            # its headings, and the role ladder routes body content PAST a
            # heading-role Area — a hero declared `heading` would take content
            # only via the last-resort fallback. The name describes what the
            # region actually holds.
            "areas": [{"name": "main", "role": "body"}],
            "fragment": """<section data-arrange="hero">
  <div data-area="main" data-area-role="body">
    <p class="kicker" data-block="heading" data-block-id="k1">Kicker</p>
    <h1 data-block="heading" data-block-id="t1">The headline promise.</h1>
    <p class="tagline" data-block="heading" data-block-id="s1">One sentence expanding on it.</p>
    <p data-block="button" data-block-id="c1"><a href="https://…">Call to action</a></p>
  </div>
</section>""",
        },
        "content": {
            "label": "Content",
            "description": "A heading with content below.",
            "grain": "page",
            "areas": [
                {"name": "heading", "role": "heading"},
                {"name": "main", "role": "body"},
            ],
            "fragment": """<section data-arrange="content">
  <div data-area="heading" data-area-role="heading">
    <h2 data-block="heading" data-block-id="t1">Section title</h2>
  </div>
  <div data-area="main" data-area-role="body"></div>
</section>""",
        },
        "feature-grid": {
            "label": "Feature grid",
            "description": "A heading over three side-by-side features.",
            "grain": "page",
            "areas": [
                {"name": "heading", "role": "heading"},
                {"name": "a", "role": "body", "place": "left"},
                {"name": "b", "role": "body", "place": "center"},
                {"name": "c", "role": "body", "place": "right"},
            ],
            "fragment": """<section data-arrange="feature-grid">
  <div data-area="heading" data-area-role="heading">
    <h2 data-block="heading" data-block-id="t1">Section title</h2>
  </div>
  <div class="cols">
    <div class="col" data-area="a" data-area-role="body" data-area-place="left"><div data-block="prose" data-block-id="b1"><h3>Feature</h3><p>One sentence on it.</p></div></div>
    <div class="col" data-area="b" data-area-role="body" data-area-place="center"><div data-block="prose" data-block-id="b2"><h3>Feature</h3><p>One sentence on it.</p></div></div>
    <div class="col" data-area="c" data-area-role="body" data-area-place="right"><div data-block="prose" data-block-id="b3"><h3>Feature</h3><p>One sentence on it.</p></div></div>
  </div>
</section>""",
        },
        "testimonial": {
            "label": "Testimonial",
            "description": "One centered quote with attribution.",
            "grain": "page",
            "areas": [{"name": "main", "role": "body"}],
            "fragment": """<section data-arrange="testimonial">
  <div data-area="main" data-area-role="body">
    <blockquote data-block="quote" data-block-id="q1"><p>What a customer said.</p><cite>Name, role</cite></blockquote>
  </div>
</section>""",
        },
        "cta": {
            "label": "Call to action",
            "description": "A closing ask — heading and button, centered.",
            "grain": "page",
            # `main`/flow for the same reason as `hero` — the band holds a
            # button, not headings alone.
            "areas": [{"name": "main", "role": "body"}],
            "fragment": """<section data-arrange="cta" data-tone="accent">
  <div data-area="main" data-area-role="body">
    <h2 data-block="heading" data-block-id="t1">The closing ask.</h2>
    <p data-block="button" data-block-id="c1"><a href="https://…">Call to action</a></p>
  </div>
</section>""",
        },
        "footer": {
            "label": "Footer",
            "description": "A quiet closing band — fine print, contact.",
            "grain": "page",
            "areas": [{"name": "main", "role": "body"}],
            "fragment": """<section data-arrange="footer">
  <div data-area="main" data-area-role="body">
    <div data-block="prose" data-block-id="b1"><p>Fine print · contact · attribution.</p></div>
  </div>
</section>""",
        },
    },
}


# ---------------------------------------------------------------------------
# Property tokens (ADR-453 D1) — the third annotation family. Tokens, not
# pixels: a token is a `data-*` attribute whose values are a small named set,
# interpreted by the kernel CSS below and THEMED by the design system's custom
# properties (ADR-449) — never raw geometry, never raw color. Absence is the
# default (clearing a token removes the attribute; un-tokened artifacts stay
# valid — grammar, not schema). One registry serves the Design tab's segmented
# controls AND the lane's posture (R4: one grammar for both hands).
#
# ADR-542 D1 — a row declares WHERE and WHEN as two closed axes (the old
# compound `applies` slugs are dissolved; the old docstring's own reading —
# "every value reads as (object × condition); the hyphen is doing a second
# field's work" — is now the schema):
#   scope   — block | page | document (WHERE the pane mounts the control)
#   grains  — any | staged | flow | media | callout | deck | multicol | bg
#             (WHEN a scope admits it — ANY listed grain's predicate suffices;
#              ("any",) is unconditional)
# Predicates, FE-side (one admitting function, ADR-542 D2):
#   staged   — `.slide` ancestry (a deck slide or an images artboard)
#   artboard — an IMAGES artboard ONLY (ADR-544 D3: decks have no free position)
#   flow     — the layout's mode is `flow`
#   media    — the kind cites a picture (MEDIA_BLOCK_KINDS)
#   callout  — the kind is `callout` (ADR-487 D2 variants)
#   deck     — the deck layout (slides; slide numbers ADR-456)
#   multicol — the page's arrangement has ≥2 body-role Areas
#   bg       — the page carries a cited background (data-ref-kind="background")
# ---------------------------------------------------------------------------

#: The two axes as DATA — one short phrase per value, composed into the WHERE
#: half of the lane's grammar line (`_where_phrase`). This exists because the
#: FE and the lane were not being told the same thing (ADR-455): the Design
#: tab GATES its controls by scope × grains, and one registry must teach both
#: hands the same containment (ADR-453 R4).
# ADR-542 D1 — the compound `applies` slugs are SPLIT along the seam the old
# docstring itself named ("the hyphen is doing a second field's work"): a row
# declares `scope` (WHERE the pane mounts it: block | page | document) and
# `grains` (WHEN a scope admits it — ANY listed predicate; ("any",) is
# unconditional). Both axes are CLOSED enums, gate-checked; a new WHERE is a
# new scope value and a new WHEN is a new grain with a declared predicate,
# never a new compound. The lane's WHERE phrase composes from the two tables.
TOKEN_SCOPES: tuple[str, ...] = ("block", "page", "document")
TOKEN_GRAINS: tuple[str, ...] = (
    "any", "staged", "artboard", "flow", "media", "callout", "deck", "multicol", "bg",
)

SCOPE_PHRASES: dict[str, str] = {
    "block": "a block",
    "page": "a page/slide element",
    "document": "the artifact root (<html>)",
}

GRAIN_PHRASES: dict[str, str] = {
    "any": "",  # unconditional — the scope phrase stands alone
    # ADR-525 D4's lesson carried forward: the grain names the MEDIUM/condition
    # explicitly so the AI hand is never told a paragraph has a width.
    "staged": "on a staged frame (a deck slide or a canvas artboard)",
    # ADR-544 D3 — free POSITION is an IMAGES-only capability now. `staged`
    # still means either frame (SIZE is legitimate on both); `artboard` is the
    # narrower predicate the position measures moved to, so a deck block can no
    # longer be placed at a coordinate and leave its Area.
    "artboard": "on a canvas artboard (IMAGES — never a deck slide)",
    "flow": "in a flowing document (never a staged frame)",
    "media": "that is a media block (figure/gallery)",
    "callout": "that is a callout",
    "deck": "on a deck only",
    "multicol": "whose arrangement has 2+ body Areas",
    "bg": "carrying a cited background image",
}

#: Block kinds the media-grain tokens (height/fit) apply to.
#: ADR-538 D2 — `chart` LEFT this set. The media tokens are about how a picture
#: fills its box (`fit`: cover/contain) and how tall the picture stands; a
#: chart is no longer a picture but a projection of cited data, so `fit` has
#: nothing to act on. `size` still reaches it as a staged object.
#: ADR-539 D2 — DERIVED from the registry's `cites` field (a media kind IS a
#: kind that cites a picture); hand-maintaining this set beside the rows is
#: how it diverged from the FE's picker set in the first place.
MEDIA_BLOCK_KINDS = {k for k, r in STUDIO_BLOCKS.items() if r["cites"] == "picture"}

STUDIO_TOKENS: dict[str, dict] = {
    # ADR-461 D1 — the block's width, as INTENT. The Claude Design inspector's
    # Hug | Fixed | Fill, minus Fixed: Hug and Fill are enumerated values (one
    # kernel rule each) and land here for free; `Fixed: 761px` is a CONTINUOUS
    # value the kernel cannot pre-declare a selector for, and is D3's bounded
    # exception (deck + media only), not this row's business.
    # Absence = the flow's natural width — the pad/valign/fit convention.
    # ADR-525 D4 — re-keyed from the widest grain ("block") to what it always
    # MEANT. The description below has said so in its own words since the token
    # shipped ("absence = the flow's natural width"): this is a box's width, and
    # on flow a text block has no box. Now: a block on a staged frame, or a
    # media object anywhere (a figure on flow IS a box and keeps the row).
    # The measure half of this registry was narrowed correctly long ago
    # (x/y/w/h are all `block-staged`); the token half was missed, which is why
    # a Docs paragraph rendered WIDTH: Auto | Hug | Fill.
    "size": {
        "label": "Width",
        "scope": ("block",),
        "grains": ("staged", "media"),
        "values": [
            {"value": "hug", "label": "Hug"},
            {"value": "fill", "label": "Fill"},
        ],
        "description": "how wide the block sits (absence = the flow's own width)",
    },
    # ADR-527 D3 AMENDS ADR-525 D4 on this row. The 525 reasoning ("alignment
    # within the block's region presupposes a region") was written for `size`
    # and applied to `align` by adjacency — but the kernel rule right above is
    # `text-align`, i.e. arrangement of PROSE inside its own measure, which a
    # flow block has. Every benchmark (Notion included) offers it on a
    # paragraph. `block-flow` is the grain ADR-525 D4 added to the vocabulary
    # and, until this row, nothing used.
    "align": {
        "label": "Align",
        "scope": ("block",),
        "grains": ("staged", "media", "flow"),
        # `start` is GONE (ADR-461 B1, 2026-07-15): it was declared here but no
        # `[data-align="start"]` rule ever existed in the kernel, so picking
        # "Left" wrote an attribute that rendered nothing — two UI states, one
        # visual result, indistinguishable from Auto. Every sibling token
        # expresses its default by OMISSION + an "absence = …" description
        # (pad, valign, fit, ratio, measure…); align alone declared it. The
        # convention is the siblings'. This matters beyond the bug: ADR-461 D1's
        # `Position: Inline` IS an absence-default (position: static), so this
        # row is the pattern it would have copied.
        "values": [
            {"value": "center", "label": "Center"},
            {"value": "end", "label": "Right"},
        ],
        "description": "content alignment within the block's region (absence = left)",
    },
    # ADR-527 D3 — the bar's ⇤/⇥ at block grain. Enumerable steps, so a TOKEN
    # (one kernel selector per value) and never a measure. Flow only: on a
    # staged frame a block is positioned, and indenting it would compete with
    # the coordinate space.
    "indent": {
        "label": "Indent",
        "scope": ("block",),
        "grains": ("flow",),
        # ADR-546 D1 — DERIVED from FLOW_RUNGS, never a hand-list. This row was
        # the second of three independent declarations of depth; it is now the
        # rung's own value set, so a fourth cannot ship by editing one literal.
        "values": [{"value": str(r), "label": str(r)} for r in FLOW_RUNGS],
        "description": "steps the block in from the measure's edge (absence = flush left)",
    },
    "tone": {
        "label": "Tone",
        "scope": ("block", "page"),
        "grains": ("any",),
        "values": [
            {"value": "accent", "label": "Accent"},
            {"value": "muted", "label": "Muted"},
            {"value": "inverse", "label": "Inverse"},
        ],
        "description": "emphasis via the palette variables — never raw color",
    },
    # ADR-487 D2 — the semantic trio wired. The §5 contract named
    # --fresh/--danger/--warn with the honest note "no selector yet"; the
    # selectors arrive WITH the member affordance that justifies them (a
    # callout's semantic register), never as speculative chrome. Absence =
    # the accent default the callout has always worn. --danger stays a
    # reserved slot (a fourth value is one row when a block demands it).
    "variant": {
        "label": "Variant",
        "scope": ("block",),
        "grains": ("callout",),
        "values": [
            {"value": "note", "label": "Note"},
            {"value": "success", "label": "Success"},
            {"value": "warning", "label": "Warning"},
        ],
        "description": "the callout's semantic register via the semantic slots — never raw color (absence = the accent default)",
    },
    "height": {
        "label": "Height",
        "scope": ("block",),
        "grains": ("media",),
        "values": [
            {"value": "s", "label": "Small"},
            {"value": "m", "label": "Medium"},
            {"value": "l", "label": "Large"},
        ],
        "description": "image height preset on a figure/gallery block",
    },
    "fit": {
        "label": "Fit",
        "scope": ("block",),
        "grains": ("media",),
        "values": [
            {"value": "cover", "label": "Fill"},
            {"value": "contain", "label": "Fit"},
        ],
        "description": "how the image fills its box",
    },
    "ratio": {
        "label": "Columns",
        "scope": ("page",),
        "grains": ("multicol",),
        "values": [
            {"value": "2-1", "label": "Wide left"},
            {"value": "1-2", "label": "Wide right"},
        ],
        "description": "column weighting on a multi-column page (absence = even)",
    },
    # ADR-516 D2 — `valign` and `pad` are DELETED from this registry. They were
    # the page grain's two LAYOUT tokens; layout now writes bounded inline-CSS
    # presets through the one op (the page is a container — ADR-516 D1), so a
    # private synonym for `justify-content`/`padding` was prompt tax under
    # ADR-306. Their kernel rules below REMAIN (ADR-511 D8: inert names on
    # legacy artifacts); a layout write strips the attribute from the element
    # it touches (convergence-by-use). Meaning-tokens (tone/variant/scrim/…)
    # are NOT layout and stay.
    # ADR-456 W3: the cited-background pair — a page/section wearing a
    # data-ref-kind="background" citation styles it with these, never inline.
    "scrim": {
        "label": "Scrim",
        "scope": ("page",),
        "grains": ("bg",),
        "values": [
            {"value": "dark", "label": "Dark"},
            {"value": "light", "label": "Light"},
        ],
        "description": "a legibility overlay on the page's cited background image",
    },
    "bg-pos": {
        "label": "Focus",
        "scope": ("page",),
        "grains": ("bg",),
        "values": [
            {"value": "top", "label": "Top"},
            {"value": "bottom", "label": "Bottom"},
        ],
        "description": "which part of the background image stays in view (absence = center)",
    },
    # ADR-455: document-grain tokens — set on the artifact ROOT. The Notion
    # page-menu affordances (typography, width) as tokens, never raw style.
    "font": {
        "label": "Typography",
        "scope": ("document",),
        "grains": ("any",),
        "values": [
            {"value": "serif", "label": "Serif"},
            {"value": "sans", "label": "Sans"},
            {"value": "mono", "label": "Mono"},
        ],
        "description": "the artifact's typeface family (absence = the layout/design-system default)",
    },
    "measure": {
        "label": "Width",
        "scope": ("document",),
        "grains": ("flow",),
        "values": [
            {"value": "wide", "label": "Wide"},
        ],
        "description": "the content column width on a document (absence = the layout default)",
    },
    # ADR-472 D3: the `aspect` token (wide/portrait/story slugs, scoped
    # `document-canvas`) is DELETED, not moved to IMAGES. It only ever existed
    # as slugs because ADR-461's gate requires every token value be enumerable,
    # and a stage's size is a CONTINUOUS value. IMAGES stages carry real W×H
    # pixels as data (services/images/stage.py::STAGE_PRESETS + resolve_dimensions),
    # which is what a design tool actually needs. Deleting rather than porting
    # is the Singular Implementation discipline — the ADR-453 gate was already
    # failing on this token as "declared but never rendered", which is what a
    # value with no interpreting selector looks like.
    # ADR-456 Wave 1: slide numbers — CSS counters, script-free, opt-in.
    "pagenum": {
        "label": "Slide numbers",
        "scope": ("document",),
        "grains": ("deck",),
        "values": [
            {"value": "on", "label": "On"},
        ],
        "description": "slide numbers in the corner of every slide (deck; absence = off)",
    },
}

#: The kernel CSS that interprets tokens — carried by every artifact in the
#: MARKED, VERSIONED kernel style element (D2). Themed through the same
#: custom properties the layouts declare and a design system may override
# ---------------------------------------------------------------------------
# MEASURES (ADR-461 D3/D4) — the one axis the token model gains.
#
# A token is `data-<key>="<one-of-an-enumerated-set>"`, and the kernel
# pre-declares a selector per value. That is why Hug and Fill were free (D1)
# and `Fixed: 761px` was not: a continuous value has no pre-declarable
# selector — `[data-w="761"]` cannot be written in advance.
#
# A MEASURE is the answer: a property whose MECHANISM is enumerable but whose
# VALUE is not. The kernel pre-declares ONE rule reading a custom property; the
# element carries the value. `data-ref` already has this shape — the kernel
# declares the mechanism, the element carries the referent — so this is a new
# INSTANCE of an existing pattern, not a new pattern.
#
# The bound is the whole ruling (ADR-461 D4): a measure is admitted only where
# a FRAME bounds it. A slide has one (16:9, overflow:hidden, no responsive
# obligation — the kernel says so). A page has only a viewport to guess at, and
# per-breakpoint editing is refused (ADR-456 D3), so a positioned hero on a
# page has no answer at 40rem. Hence `applies` here is deck + media ONLY.
#
# Continuous-everywhere is OPTED OUT, not refused — see ADR-461 D4 for the
# three conditions that would legitimately re-open it. The pressure will arrive
# as "why can a deck do this and a page can't?"; the answer is that a slide has
# a frame and a page has a viewport.
#
# `unit` + `min`/`max` are the kernel's bound on the value: a measure is
# free WITHIN its frame, never unbounded. The FE clamps; the kernel's `var()`
# fallback means a missing/garbage value degrades to the natural layout rather
# than to zero.
# ---------------------------------------------------------------------------

STUDIO_MEASURES: dict[str, dict] = {
    "w": {
        "label": "Width",
        # Deck + media only. NOT document or web — they reflow.
        "scope": ("block",),
        "grains": ("staged", "media"),
        "unit": "%",
        "min": 10,
        "max": 100,
        "css_var": "--yw",
        "description": "the block's width inside its frame (absence = the flow's own width)",
    },
    "h": {
        "label": "Height",
        "scope": ("block",),
        "grains": ("staged", "media"),
        "unit": "%",
        # The height axis floors at 1%, NOT 10% like width (ADR-475 §12). The
        # axes honestly differ: a 1%-tall rule is a legitimate block (a hairline
        # divider, a thin accent bar, a pill badge — the first live ad had two),
        # where a 1%-wide column is not. The first IMAGES ad exposed the copied
        # 10% floor inflating a hairline to a 63px slab on a 628px stage. This is
        # the KERNEL floor, so it governs Studio decks too — which is correct: a
        # thin horizontal rule is as legitimate on a slide as on a stage. Both
        # the FE geometry clamp (artifactOps.setGeometry, clamps from the SERVED
        # spec) and the IMAGES `_coerce` bound read this one value.
        "min": 1,
        "max": 100,
        "css_var": "--yh",
        "description": "the block's height inside its frame (absence = the content's own height)",
    },
    # Bounded POSITION (ADR-466 D2, enacting ADR-461 D3's remaining half): x/y
    # place a block at a point IN ITS FRAME — `left`/`top` as a percent of the
    # frame's box.
    #
    # ADR-544 D3 — THE GRAIN NARROWED FROM `staged` TO `artboard`: free position
    # is an IMAGES capability, and a deck slide no longer has one. The old grain
    # admitted both frames, and on a deck the consequence was stated in this very
    # comment: "a positioned block EXITS the slot contract (the ADR-461 honest
    # remainder)". That remainder is what the operator met as "I move a header
    # and it just ends up floating anywhere, overlapping" — a drag was not a move
    # within the layout but an ESCAPE from it, leaving a block that belongs to no
    # Area and that no later AI revision can reason about. Containment (D1) is
    # what makes a slide re-describable across a human edit and an AI pass, and
    # that determinism is worth more on a deck than arbitrary placement.
    #
    # IMAGES KEEPS THIS IN FULL (ADR-544 §4.3) — its stage is a composition
    # surface where overlap is the point, and `services/images/stage.py` seeds
    # data-x/data-y on its own scaffolds. The measures are NOT deleted; they are
    # re-grained. A sweep that removes them breaks IMAGES and is the predictable
    # over-reach of ADR-544.
    #
    # A media block in a FLOW layout must never exit the flow (it has an
    # intrinsic-ratio frame for SIZE, but position needs the fixed stage). The
    # presence of BOTH measures is the positioned state; absence = in flow.
    "x": {
        "label": "X",
        "scope": ("block",),
        "grains": ("artboard",),
        "unit": "%",
        "min": 0,
        "max": 95,
        "css_var": "--yx",
        "description": "the block's left edge as a percent of its frame (with y, positions the block; absence = in flow)",
    },
    "y": {
        "label": "Y",
        "scope": ("block",),
        "grains": ("artboard",),
        "unit": "%",
        "min": 0,
        "max": 95,
        "css_var": "--yy",
        "description": "the block's top edge as a percent of its frame (with x, positions the block; absence = in flow)",
    },
    # Stacking (ADR-471 D-d): z earned its token when composed visuals made
    # blocks OVERLAP on purpose. Integer index, not a percent — order among
    # positioned siblings; absence = document order (the pre-471 behavior,
    # unchanged). On a non-positioned block z-index is inert by CSS — the
    # fallback philosophy (a garbage measure degrades to natural behavior).
    # StudioBlockMenu's Bring forward/backward verbs write this token.
    "z": {
        "label": "Z",
        "scope": ("block",),
        "grains": ("artboard",),
        "unit": "",
        "min": 0,
        "max": 20,
        "css_var": "--yz",
        "description": "stacking order among positioned blocks (higher = in front; absence = document order)",
    },
}

#: Measure grains (ADR-542: grain slugs, post-split). `staged` is a block on a
#: STAGED frame — the `.slide` class, carried by a deck slide and by an IMAGES
#: stage; the frame class is the grain's boundary (ADR-472 D2). `media` is a
#: media block anywhere (an image has an intrinsic ratio, which is its own
#: frame — ADR-461 D4).
# ADR-544 D3 — `artboard` joins the frame-bounded set. The boundary this
# allowlist enforces is unchanged (a measure is admitted ONLY where a FRAME
# bounds it — never on a reflowing page, ADR-461 D4); what changed is that the
# POSITION measures narrowed from `staged` (either frame) to `artboard`
# (IMAGES only), because a deck block now holds a place in the hierarchy rather
# than a coordinate. SIZE still admits `staged`: a block sized within its Area
# is legitimate on both frames.
MEASURE_GRAINS = {"staged", "artboard", "media"}


#: (cascade: unmarked layout style < data-kernel < data-skin).
STUDIO_KERNEL_CSS = """
/* Block-kind + arrangement CSS (ADR-456 W1) — lives in the KERNEL element,
   not the layout skin, so new kinds/arrangements retrofit into existing
   artifacts via the versioned upsert. Token rules come LAST in this sheet so
   a token wins at equal specificity. */
hr[data-block="divider"] { border: 0; border-top: 1px solid var(--ink-10, #ddd); margin: 2.25rem 0; }
/* ADR-536 D1 — the two ordinary list kinds. Declared EXPLICITLY rather than
   left to the UA default because _SHARED_CSS's reset zeroes every margin and
   padding (`* { margin: 0; padding: 0 }`), which collapses a bare <ul> onto
   its markers. `checklist` next door already had to opt out of that reset the
   same way; these rows are its ordinary siblings. Nested lists step down the
   marker the way every writing surface does. */
ul[data-block="list"], ol[data-block="numbered"] { margin: 1rem 0; padding-inline-start: 1.5rem; }
ul[data-block="list"] { list-style: disc; }
ol[data-block="numbered"] { list-style: decimal; }
ul[data-block="list"] li, ol[data-block="numbered"] li { margin: 0.35rem 0; }
/* ADR-546 D1 — THE NESTING RUNG, generated from FLOW_RUNGS (__NEST_CSS__,
   substituted at module load). Was four hand-written selectors nesting to
   depth 3 — the audit's THIRD independent declaration of depth, and the one
   with NO reader: it rendered a hierarchy `normalizeStructure` could not
   address, so Tab authored structure nothing could name (ADR-546 §1.2). */
__NEST_CSS__
details[data-block="toggle"] { margin: 1rem 0; border: 1px solid var(--ink-10, #ddd);
  border-radius: var(--radius-md, var(--radius, 6px)); padding: 0.5rem 0.9rem; }
details[data-block="toggle"] summary { cursor: pointer; font-weight: 600; }
details[data-block="toggle"][open] summary { margin-bottom: 0.5rem; }
p[data-block="button"] { margin: 1.5rem 0; }
p[data-block="button"] a { display: inline-block; background: var(--accent, #b4540a);
  color: var(--paper, #fdfcfa); padding: 0.55rem 1.2rem;
  border-radius: var(--radius-pill, var(--radius, 6px)); text-decoration: none; font-weight: 600; }
div[data-block="gallery"] { display: grid; gap: 0.75rem; margin: 1.5rem 0;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); }
div[data-block="gallery"] figure { margin: 0; }
div[data-block="gallery"] img { width: 100%; aspect-ratio: 4 / 3;
  object-fit: cover; border-radius: var(--radius-sm, var(--radius, 4px)); }
div[data-block="gallery"] figcaption { font-size: var(--text-xs, 0.75rem); }
/* ADR-538 D3 — the composite component. Same construction as `metrics` one
   composition deeper: a labelled container of rows, drawn entirely from
   design-system slots so a skin themes it for free. It cites nothing (D1 →
   `content`), so there is no projection involved and it renders identically
   in every mount. */
div[data-block="component"] { border: 1px solid var(--rule, rgba(26,26,26,0.1));
  border-radius: var(--radius-lg, var(--radius, 10px)); padding: 1rem 1.15rem;
  margin: 1.5rem 0; background: var(--paper, #fff); }
div[data-block="component"] > header { font-size: var(--text-xs, 0.72rem);
  letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted);
  margin-bottom: 0.75rem; }
div[data-block="component"] .row { display: flex; align-items: center;
  gap: 0.6rem; padding: 0.5rem 0.65rem; border-radius: var(--radius, 6px);
  border: 1px solid transparent; }
div[data-block="component"] .row + .row { margin-top: 0.3rem; }
div[data-block="component"] .row .name { font-weight: 600; }
div[data-block="component"] .row .value { color: var(--muted); flex: 1;
  min-width: 0; }
div[data-block="component"] .row .pill { font-size: var(--text-xs, 0.72rem);
  padding: 0.15rem 0.55rem; border-radius: var(--radius-pill, 999px);
  background: var(--rule, rgba(26,26,26,0.06)); color: var(--muted); }
div[data-block="component"] > footer { margin-top: 0.75rem;
  font-size: var(--text-xs, 0.72rem); color: var(--muted); }
/* ADR-538 D2 — the projected chart. The projection emits this markup from the
   cited CSV (`csvToChartHtml`); the kernel styles it, so a chart is themed by
   the design system like every other block and needs no inline geometry. */
figure[data-block="chart"] { margin: 1.5rem 0; }
.yc-bar-chart ul { list-style: none; margin: 0; padding: 0; }
.yc-bar-chart li { display: flex; align-items: center; gap: 0.75rem;
  margin: 0.35rem 0; font-size: var(--text-sm, 0.9rem); }
.yc-bar-chart .yc-l { flex: 0 0 32%; min-width: 0; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; color: var(--muted); }
.yc-bar-chart .yc-track { flex: 1; background: var(--rule, rgba(26,26,26,0.07));
  border-radius: var(--radius-pill, 999px); overflow: hidden; }
.yc-bar-chart .yc-bar { display: block; height: 0.7rem;
  background: var(--accent, #b4540a); border-radius: var(--radius-pill, 999px); }
.yc-bar-chart .yc-v { flex: 0 0 auto; font-variant-numeric: tabular-nums;
  font-weight: 600; }
.yc-donut { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
.yc-donut svg { width: 9rem; height: 9rem; flex: 0 0 auto;
  color: var(--accent, #b4540a); transform: rotate(-90deg); }
.yc-legend { list-style: none; margin: 0; padding: 0;
  font-size: var(--text-sm, 0.9rem); }
.yc-legend li { display: flex; align-items: center; gap: 0.5rem;
  margin: 0.25rem 0; }
.yc-legend .swatch { width: 0.7rem; height: 0.7rem; border-radius: 2px;
  background: var(--accent, #b4540a); display: inline-block; }
/* ADR-538 D4 — the kernel's FIRST motion, and the whole of it. Declarative
   only: @keyframes + transition + :hover. Measured (ADR-538 §2) to run inside
   the bare `sandbox=""` the Web Viewer and every share link use, where script
   does NOT run — so a component stays alive where a reader actually meets it.
   `data-motion` is opt-in: absence is stillness, which keeps every existing
   artifact byte-identical in behaviour after the retrofit. */
@keyframes yarnnn-pulse { 0%, 100% { opacity: 0.35; transform: scale(0.82); }
  50% { opacity: 1; transform: scale(1); } }
@keyframes yarnnn-rise { from { opacity: 0; transform: translateY(0.5rem); }
  to { opacity: 1; transform: none; } }
[data-motion="pulse"] { animation: yarnnn-pulse 1.8s ease-in-out infinite; }
[data-motion="rise"] { animation: yarnnn-rise 0.5s ease-out both; }
div[data-block="component"] .row { transition: border-color 0.18s ease,
  background 0.18s ease; }
div[data-block="component"] .row:hover { border-color: var(--rule, rgba(26,26,26,0.12));
  background: var(--rule-soft, rgba(26,26,26,0.03)); }
/* Motion that cannot be turned off is an accessibility defect, and the kernel
   is the ONLY place this can be guaranteed once for every artifact and every
   future motion rule (ADR-538 D4 — a permanent obligation, not a nicety). */
@media (prefers-reduced-motion: reduce) {
  [data-motion] { animation: none !important; }
  div[data-block="component"] .row { transition: none !important; }
}
/* The multi-column band — kernel-owned for EVERY layout, slides included.
   It used to carve out `:not(.slide)` on the reasoning that "decks keep their
   own .slide .cols rules". That was true of the deck skin as of ADR-444 — and
   false of every deck created BEFORE it, because the layout skin is baked once
   at build_skeleton and never retrofitted (only style[data-kernel] is versioned
   + upserted). Those decks match neither rule, fall back to display:block, and
   silently stack their columns — exactly the silent-defect class the retrofit
   comment in artifactOps.ts predicts ("a version CHANGES or REMOVES a rule an
   old artifact depends on... nothing errors").
   The kernel may not depend on skin state it cannot retrofit. It owns .cols.
   The deck skin's identical rule is harmless duplication (same declarations,
   later in the cascade); the gap is what mattered. */
[data-arrange] .cols { display: flex; gap: 2rem; align-items: flex-start; }
[data-arrange] .col { flex: 1; min-width: 0; }
/* The deck's own gap is wider (a slide breathes) — restored here so retiring
   the carve-out doesn't quietly re-space every existing slide. */
.slide .cols { gap: 2.5rem; }
/* The cited page background (ADR-456 W3) — the SOURCE carries only the
   citation (data-ref + data-ref-kind="background") and tokens; the projection
   materializes background-image; these rules do the rest. */
[data-ref-kind="background"] { position: relative; background-size: cover;
  background-position: center; }
[data-ref-kind="background"] > * { position: relative; }
[data-bg-pos="top"] { background-position: top center; }
[data-bg-pos="bottom"] { background-position: bottom center; }
[data-scrim] { position: relative; }
[data-scrim]::before { content: ""; position: absolute; inset: 0; pointer-events: none; }
[data-scrim="dark"]::before { background: rgba(0,0,0,0.5); }
[data-scrim="light"]::before { background: rgba(253,252,250,0.65); }
[data-scrim="dark"] { color: var(--paper, #fdfcfa); }
/* Page-band arrangement accents (kernel-owned so they retrofit). */
[data-arrange="cta"], [data-arrange="testimonial"] { text-align: center; }
[data-arrange="testimonial"] blockquote[data-block="quote"] { border-left: 0;
  font-style: italic; font-size: var(--text-xl, 1.3rem); }
[data-arrange="footer"] { font-size: 0.85rem; color: var(--muted, #6b6b6b); }
.slide[data-arrange="full-bleed"] { padding: 0; }
.slide[data-arrange="full-bleed"] [data-area-role="media"] { flex: 1; display: flex; min-height: 0; }
.slide[data-arrange="full-bleed"] figure { flex: 1; margin: 0; min-width: 0; }
.slide[data-arrange="full-bleed"] img { width: 100%; height: 100%;
  object-fit: cover; max-height: none; }
[data-arrange="big-number"] div[data-block="metrics"] { justify-content: center;
  text-align: center; }
[data-arrange="big-number"] div[data-block="metrics"] .metric strong {
  font-size: var(--text-5xl, 4rem); line-height: 1.1; }
[data-arrange="big-number"] div[data-block="metrics"] .metric span { font-size: var(--text-base, 1rem); }
/* Property tokens (ADR-453) — interpreted here, themed by custom properties. */
[data-align="center"] { text-align: center; }
[data-align="center"] img { margin-inline: auto; }
[data-align="end"] { text-align: right; }
[data-align="end"] img { margin-inline-start: auto; }
/* ADR-546 D1 — THE PROSE RUNG, generated from FLOW_RUNGS (see __RUNG_CSS__
   below; this marker is substituted at module load). Was three hand-written
   `[data-indent]` rules — the second of the audit's three independent
   declarations of depth. A token, not a measure (ADR-461 D4's line: enumerable
   values get a pre-declared selector each). ADR-527 D3's ⇤/⇥ at BLOCK grain,
   and since ADR-546 D4 also what Tab/⇧Tab writes in prose. */
__RUNG_CSS__
/* ADR-527 D2 — the PALETTE MARKS: colour as a role, never a value. One rule per
   role, so a design-system swap re-themes every document that used them — the
   entire reason the picker is refused (ADR-449, "never raw color"). The span
   carries a role NAME; no inline color:/background: is ever written. */
span[data-mark="muted"] { color: var(--muted, #6b6b6b); }
span[data-mark="accent"] { color: var(--accent, #b4540a); }
span[data-mark="fresh"] { color: var(--fresh, #2e7d32); }
span[data-mark="warn"] { color: var(--warn, #b45309); }
span[data-mark="danger"] { color: var(--danger, #b3261e); }
/* Highlight tints the SAME roles — the callout-variant precedent (ADR-487 D2),
   reused rather than re-invented, so a skin needs no new variables. */
span[data-highlight="accent"] { background: color-mix(in srgb, var(--accent, #b4540a) 15%, transparent); }
span[data-highlight="fresh"] { background: color-mix(in srgb, var(--fresh, #2e7d32) 15%, transparent); }
span[data-highlight="warn"] { background: color-mix(in srgb, var(--warn, #b45309) 15%, transparent); }
span[data-highlight="danger"] { background: color-mix(in srgb, var(--danger, #b3261e) 15%, transparent); }
/* Width as intent (ADR-461 D1) — the inspector's Hug | Fill, enumerated.
   `Fixed: 761px` is NOT here: a continuous value has no pre-declarable
   selector, which is the whole reason it is D3's bounded exception rather
   than a fourth value on this row. Absence = the flow's own width. */
[data-size="hug"] { width: fit-content; max-width: 100%; }
[data-size="fill"] { width: 100%; }
/* Fill has to BEAT the grain's reading measure, or it is not a width at all.
   The deck skin caps prose for legibility (`.slide h1 { max-width: 34rem }`,
   `.slide p { max-width: 36rem }`) — specificity (0,1,1), which outranks the
   (0,1,0) row above. So `width: 100%` computed, then max-width clamped it
   straight back to 34rem: on the two most common blocks in a deck, Fill and
   Auto rendered the SAME BOX. Two inspector states, one visual result — the
   exact bug ADR-461 B1 removed from `align`, in the row next door.
   Measured (992px slide, 64px pad, inner 864): h1 auto 544 / fill 544 → 864.
   Scoped `.slide` (0,2,0) so it wins where the cap is set, and stays out of
   a document, whose measure is the whole point of the grain. */
.slide [data-size="fill"] { max-width: none; }
/* A hugged box is only as wide as its text, so `text-align` — which aligns the
   text INSIDE the box — has nothing left to move. Aligning it is a margin act.
   Without this, Hug + Center sat flush left (measured l=64, the bare padding),
   which reads as "align is broken" when it is width and align meeting. */
[data-size="hug"][data-align="center"] { margin-inline: auto; }
[data-size="hug"][data-align="end"] { margin-inline-start: auto; }
/* MEASURES (ADR-461 D4) — the one axis the token model gains: a property whose
   MECHANISM is pre-declared here but whose VALUE rides in the element. Two
   rules, any value — which is exactly why this preserves the invariant that
   killed `Fixed: 761px` as a token ([data-w="761"] can never be pre-written,
   but this can).

   The `var()` FALLBACK is load-bearing: a missing or garbage value degrades to
   the natural layout (auto), never to zero. An artifact whose measure was
   dropped by a bad write still renders as itself.

   Bounded by the FRAME, per D4: a slide has one (fixed-aspect,
   overflow:hidden, no responsive obligation), and a media block's intrinsic
   ratio is its own. The `.slide` scope is not decoration — it IS the boundary,
   and it is what a deck slide and an IMAGES stage share (ADR-472 D2 — the
   shared object layer, consumed by both apps).
   Nothing here applies to document or web, which reflow and would have
   no answer at 40rem. */
.slide [data-w], [data-block="figure"][data-w], [data-block="chart"][data-w],
[data-block="gallery"][data-w] { width: var(--yw, auto); max-width: 100%; }
.slide [data-h], [data-block="figure"][data-h], [data-block="chart"][data-h],
[data-block="gallery"][data-h] { height: var(--yh, auto); }
/* Bounded POSITION (ADR-466 D2) — x/y measures place a deck block at a point
   in its frame. The frame is the positioning context (the slide, a column, a
   slot); presence of BOTH measures is the positioned state, and the `auto`
   fallback means a missing/garbage value degrades to the natural layout,
   never to zero (the ADR-461 fallback rule). A positioned block exits the
   slot's flow (the honest remainder) — margin drops so the point is exact. */
section.slide, .slide .col, .slide [data-area] { position: relative; }
.slide [data-block][data-x][data-y] { position: absolute;
  left: var(--yx, auto); top: var(--yy, auto); margin: 0; max-width: 100%; }
/* Stacking (ADR-471 D-d) — z orders positioned blocks; on a static block
   z-index is inert by CSS, which is the fallback rule doing its job. */
.slide [data-block][data-z] { z-index: var(--yz, auto); }
/* Callout variants (ADR-487 D2) — the semantic trio wired. The base callout
   look (accent border + tint) lives in the baked layout skin; a variant
   overrides border + tint through the SEMANTIC slots, in the kernel so it
   retrofits. color-mix derives the tint from the same slot, so a themed
   trio tints as itself. Higher specificity (two attrs) beats the base. */
aside[data-block="callout"][data-variant="note"] { border-color: var(--ink-10, #ddd);
  background: color-mix(in srgb, var(--ink, #1a1a1a) 5%, transparent); }
aside[data-block="callout"][data-variant="success"] { border-color: var(--fresh, #2e7d32);
  background: color-mix(in srgb, var(--fresh, #2e7d32) 7%, transparent); }
aside[data-block="callout"][data-variant="warning"] { border-color: var(--warn, #b45309);
  background: color-mix(in srgb, var(--warn, #b45309) 8%, transparent); }
[data-tone="accent"] { color: var(--accent, #b4540a); }
[data-tone="muted"] { color: var(--muted, #6b6b6b); }
[data-block][data-tone="inverse"] { background: var(--ink, #1a1a1a);
  color: var(--paper, #fdfcfa); padding: 1rem 1.25rem; border-radius: var(--radius-md, 6px); }
.slide[data-tone="accent"], [data-arrange][data-tone="accent"] {
  background: var(--accent, #b4540a); color: var(--paper, #fdfcfa); }
.slide[data-tone="inverse"], [data-arrange][data-tone="inverse"] {
  background: var(--ink, #1a1a1a); color: var(--paper, #fdfcfa); }
.slide[data-tone] .kicker { color: inherit; opacity: 0.75; }
/* On a toned band (or a dark-scrimmed background) the button inverts so it
   stays visible against the band's own accent/ink fill. */
[data-arrange][data-tone] p[data-block="button"] a,
[data-scrim="dark"] p[data-block="button"] a {
  background: var(--paper, #fdfcfa); color: var(--ink, #1a1a1a); }
[data-height="s"] img { max-height: 10rem; }
[data-height="m"] img { max-height: 16rem; }
[data-height="l"] img { max-height: 28rem; }
[data-fit="cover"] img { width: 100%; object-fit: cover; }
[data-fit="contain"] img { object-fit: contain; }
[data-ratio="2-1"] .cols .col:first-child { flex: 2; }
[data-ratio="1-2"] .cols .col:last-child { flex: 2; }
/* LEGACY INERT NAMES (ADR-516 D2, per the ADR-511 D8 ruling): valign/pad left
   the token registry — layout writes are inline-CSS presets now — but the
   attributes live on in artifacts written before the cut, so these rules keep
   honoring them. Nothing writes them; a layout write strips them per-element. */
.slide[data-valign="start"] { justify-content: flex-start; }
.slide[data-valign="end"] { justify-content: flex-end; }
.slide[data-pad="s"] { padding: 2rem 2.5rem; }
.slide[data-pad="l"] { padding: 4.5rem 5.5rem; }
[data-arrange][data-pad="s"]:not(.slide) { padding-block: 0.25rem; }
[data-arrange][data-pad="l"]:not(.slide) { padding-block: 2.5rem; }
/* Document-grain tokens (ADR-455) — on the artifact root. */
/* ADR-487 D4 — the face slots. The member's choice stays the closed
   three-family vocabulary (categories, ADR-222); the design system supplies
   what each family IS (--font-serif: 'Tiempos', …). Fallbacks are the exact
   prior stacks, so a system that ships no faces changes nothing. */
html[data-font="serif"] body { font-family: var(--font-serif, Georgia, 'Times New Roman', serif); }
html[data-font="sans"] body { font-family: var(--font-sans, system-ui, -apple-system, 'Segoe UI', sans-serif); }
html[data-font="mono"] body { font-family: var(--font-mono, ui-monospace, 'SF Mono', Menlo, monospace); }
/* The `article` selector serves LEGACY artifacts only — ADR-505 D2 merged the
   `article` layout into `web`, and no scaffold emits an <article> root now. It
   stays because a pre-cut artifact still carries one and its measure must keep
   working (the ADR-481 D5 discipline: legacy renders, never migrates). */
html[data-measure="wide"] main, html[data-measure="wide"] article { max-width: 64rem; }
/* The slide IS the frame (ADR-461 D3/D4). `position: relative` makes it the
   containing block, so anything positioned inside a slide resolves against the
   16:9 stage rather than the viewport. Unconditional and kernel-owned:
   `html[data-pagenum="on"] .slide` below used to be the ONLY rule that made a
   slide positioned, which meant the frame existed only when slide numbers were
   switched on — a silent, state-dependent difference, the exact class of the
   `:not(.slide)` bug (8bc5384). ADR-461's premise is "a slide has a frame"; in
   CSS that is this line, and it must not be conditional on an unrelated token. */
.slide { position: relative; }
/* The frame's BOX, for the same reason the line above exists — and it must be
   KERNEL, not skin. A layout skin is baked once at creation, so a rule that
   lives only there fixes new decks and leaves every existing one broken; the
   kernel is the layer that retrofits (it is re-stamped on version bump).

   What this replaces: the deck skin sized the slide with
   `width: min(100%, 62rem)`, which reads the CONTAINER. So one deck had two
   geometries — the Studio canvas pinned it to 992px (projection.ts, `pointer`
   mode ONLY), while share, export and thumbnail let the container size it. In a
   narrow container the 16:9 box shrank until the unshrinking `3.5rem 4rem`
   padding overflowed `overflow:hidden` and the slide clipped to visual
   emptiness — the ADR-447 D7.7 defect, fixed in the canvas and nowhere else.

   A deck's arrangement must not change with the screen it is read on, so the
   box is a property of the FILE: the px pair sizes it, the unitless siblings
   feed aspect-ratio (which cannot consume a px length). Declared as vars so an
   authored stage size can override them per-artifact (the IMAGES-stage pattern
   in services/images/stage.py, which already carries dimensions this way).

   The kernel cascades AFTER the unmarked layout skin, so this wins over a
   legacy deck's baked width without `!important`. No max-width: a stage that
   shrinks with its container is the reflow this removes. Fitting belongs to the
   VIEWER and it SCALES (StudioCanvas fitScale → body.style.zoom), never
   resizes. `:not([data-template="image"] *)` is unnecessary — an IMAGES stage
   declares its own --stage-w inline on the root, which wins on specificity. */
html[data-template="deck"] .slide {
  --stage-w: 992px; --stage-h: 558px; --stage-wn: 16; --stage-hn: 9;
  width: var(--stage-w);
  height: var(--stage-h);
  aspect-ratio: var(--stage-wn) / var(--stage-hn);
}
/* Slide numbers (ADR-456 W1) — CSS counters, opt-in on the deck root. */
html[data-pagenum="on"] body { counter-reset: slide; }
html[data-pagenum="on"] .slide { counter-increment: slide; }
html[data-pagenum="on"] .slide::after { content: counter(slide); position: absolute;
  right: 1.25rem; bottom: 0.9rem; font-size: var(--text-xs, 0.7rem); color: var(--muted, #6b6b6b); }
/* Responsive stacking (ADR-456 W1): web multi-column bands stack
   on narrow screens; a deck slide is a fixed 16:9 stage, exempt.
   This `:not(.slide)` STAYS — unlike the one retired above, it does not depend
   on skin state. It encodes a real difference in kind: a slide has no
   responsive obligation (fixed stage, overflow:hidden), a page does. The other
   carve-out was an assumption about CSS that might not be there; this one is a
   statement about what a slide IS. */
@media (max-width: 40rem) {
  [data-arrange]:not(.slide) .cols { flex-direction: column; }
  div[data-block="gallery"] { grid-template-columns: repeat(2, 1fr); }
}
""".strip("\n")

# ── ADR-546 D1: the rung's CSS is GENERATED, so depth is declared once ──────
#
# Both spellings of the rung render from FLOW_RUNGS. Before this, depth lived in
# three hand-written lists that had drifted apart in READERSHIP (six consumers /
# one / none) while agreeing by luck on the number 3. Generating them means a
# change to FLOW_RUNGS reaches the stylesheet, the served token values and the
# intake clamp together — there is no list to forget.
#
# The nesting ladder alternates its marker per level the way every word
# processor does (disc→circle→square, decimal→lower-alpha→lower-roman), and runs
# to len(FLOW_RUNGS) levels: the top level is the block's own list, so a rung
# set of N produces N-1 nested selectors.
_PROSE_RUNG_STEP_REM = 2

_UL_MARKERS = ("disc", "circle", "square")
_OL_MARKERS = ("decimal", "lower-alpha", "lower-roman")


def _rung_css() -> str:
    """The prose rung: one pre-declared selector per step (ADR-461 D4's rule for
    enumerable values)."""
    return "\n".join(
        f'[data-indent="{r}"] {{ margin-inline-start: {r * _PROSE_RUNG_STEP_REM}rem; }}'
        for r in FLOW_RUNGS
    )


def _nest_css() -> str:
    """The nesting rung: the marker ladder, one selector per level below the
    block's own list. `depth` counts nesting steps, so FLOW_RUNGS=(1,2,3) yields
    `ul ul` and `ul ul ul`."""
    lines: list[str] = []
    for tag, block, markers in (
        ("ul", "list", _UL_MARKERS),
        ("ol", "numbered", _OL_MARKERS),
    ):
        for depth in range(1, len(FLOW_RUNGS)):
            sel = f'{tag}[data-block="{block}"]' + f" {tag}" * depth
            marker = markers[min(depth, len(markers) - 1)]
            extra = " margin: 0.35rem 0; padding-inline-start: 1.25rem;" if depth == 1 else ""
            lines.append(f"{sel} {{ list-style: {marker};{extra} }}")
    return "\n".join(lines)


STUDIO_KERNEL_CSS = STUDIO_KERNEL_CSS.replace("__RUNG_CSS__", _rung_css()).replace(
    "__NEST_CSS__", _nest_css()
)

#: Bump when STUDIO_KERNEL_CSS changes shape — the FE upserts any artifact
#: carrying an older data-kernel-v on its next mechanical op (the retrofit).
# v14 (2026-08-07): the deck STAGE became kernel-owned. The slide's box was
# sized by the layout skin with `width: min(100%, 62rem)` — a CONTAINER read —
# so a deck's geometry changed with the screen it was opened on, and the canvas
# masked it by pinning 992px in `pointer` mode only. Share, export and thumbnail
# got the reflowing box, which in a narrow container clipped slides to visual
# emptiness (the ADR-447 D7.7 defect, fixed in one consumer). It lives HERE and
# not in the skin precisely because a skin is baked once: only the kernel
# retrofits into decks that already exist. A slide's arrangement is a property
# of the file, and the viewer may scale it but never resize it.
#: v2: document-grain font/measure rules (ADR-455).
#: v3: Wave-1 block/arrangement rules + pad/pagenum tokens + responsive
#:     stacking (ADR-456) — block/arrangement CSS lives HERE, not the layout
#:     skin, precisely so this retrofit carries it into existing artifacts.
#: v4: Wave-3 (ADR-456) — cited page backgrounds (data-ref-kind="background"
#:     + scrim/bg-pos), the generic non-slide .cols (web
#:     two-column made real), page-band accents, --radius adoption.
# v9 (2026-07-16, DESIGN-SYSTEMS.md §5): the WIDENED theme contract. The
# coverage probe measured that the five point-vars (--ink/--paper/--muted/
# --accent/--radius) paint ~3% of a real design system and miss the GEOMETRY —
# hairlines, pill radii, the type scale. This bump gives every hard literal a
# themable slot with its EXACT current value as the fallback, so a skin-less
# artifact is byte-identical and a skin that ships the slot themes it:
#   ink RAMP    --ink-10 (fallback #ddd) — the hairline the brand's built on
#   RADIUS scale --radius-sm|md|pill (fallbacks 4px/6px/6px) — the pill bites now
#   TYPE scale  --text-xs…5xl (fallbacks are the 15 literals, mapped to steps)
#   deck stage  --deck-stage (fallback #e8e4de)
# The kernel names CATEGORIES (a radius scale, a type scale), never instances
# (--radius-pill: 9999px is the SKIN's value). Semantic --fresh/--danger/--warn
# are named in the contract (derive recipe) but wire no selector yet — no kernel
# chrome reads status color, and inventing one would be behavior, not a widen.
# Retrofit is byte-identical on a skin-less artifact (every var() falls back),
# so this bump never manufactures a visible change on its own.
#
# v8 (2026-07-15, ADR-461 D4): MEASURES — two rules reading a custom property,
# so a continuous value can ride in the element while the kernel still
# pre-declares every selector it matches. Deck + media only: a slide has a
# frame, a page has a viewport.
#
# v12 (2026-07-24, ADR-461 D1 follow-on): Fill actually fills, and a hugged
# block can be aligned. `[data-size="fill"]` set width:100% but the deck skin's
# reading measure (`.slide h1 { max-width: 34rem }`) has HIGHER specificity, so
# the clamp won and Fill rendered identically to Auto on headings and prose —
# the two most common blocks on a slide. Scoped `.slide [data-size="fill"]
# { max-width: none }` beats it where the cap lives, without touching the
# document grain, where the measure is the feature. Second half: `text-align`
# can't move a box that hugs its own text, so Hug + Center sat flush left;
# `margin-inline: auto` is the box-level act that token was always asking for.
# The bump is what carries both to decks already built.
#
# v11 (2026-07-20, ADR-471 D-d): the `z` stacking rule —
# `.slide [data-block][data-z] { z-index: var(--yz, auto) }`. The bump is what
# lights stacking up in every existing deck's positioned blocks, not only new
# canvases (the retrofit is the mechanism, as ever).
#
# v7 (2026-07-15, ADR-461 D1): the `size` token (Hug | Fill) — the block's
# width as intent. Enumerated, so it needs no new mechanism.
#
# v6 (2026-07-15, ADR-461): `.slide { position: relative }` unconditionally —
# the slide becomes the containing block, so ADR-461's premise ("a slide has a
# frame") is true in CSS and not merely in prose. It was previously positioned
# ONLY under html[data-pagenum="on"], i.e. the frame existed only when slide
# numbers happened to be on.
#
# v5: the .cols carve-out retired — the kernel owns the column band for every
# layout. A pre-ADR-444 deck's baked skin has no `.slide .cols`, and the
# kernel's `:not(.slide)` rule excluded it, so its two-column slides stacked
# silently. Bumping the version is what makes the retrofit reach them.
# v13 (2026-07-25, ADR-487 D2+D4): the design system reaches the grammar.
# (D2) callout `variant` token — note/success/warning selectors reading the
# semantic slots (--fresh/--warn wired at last; §5's "no selector yet" note
# resolved WITH the member affordance, not as speculative chrome). (D4) the
# three font-family rules gain FACE slots (--font-serif/sans/mono) with the
# exact prior stacks as fallbacks — ADR-455's "a skin supplies faces; the
# token selects among them" completed. Byte-identical on a skin-less
# artifact; the bump retrofits both into every existing artifact.
# v15 (2026-08-07, ADR-536 D1): the two ordinary list kinds (bulleted +
# numbered) gain kernel rules. Additive — no existing rule changed or removed,
# so the retrofit cannot alter an artifact that holds neither kind.
#
# The rules select on `data-block`, so they reach a list only once the
# recognizer has NAMED it. Lists already in members' documents arrived by paste
# and were promoted to `prose` (UL/OL mapped there because no list kind
# existed); ADR-536 re-points that promotion at the new kinds, and promotion is
# migration-by-use — an existing list is re-named on the artifact's next write,
# not by a sweep. So the bump and the recognizer change land TOGETHER: the CSS
# alone would retrofit nothing, and the promotion alone would name a kind the
# kernel could not draw.
# v16 (2026-08-09, ADR-538 D3+D4): the composite `component` kind gains kernel
# rules, and the kernel gains its FIRST motion — two @keyframes, one transition,
# one :hover, all opt-in behind `data-motion` (absence = stillness), plus the
# prefers-reduced-motion guard that disables every one of them. Additive: no
# existing rule changed or removed, and an artifact holding neither the kind nor
# a data-motion attribute is behaviourally byte-identical after the retrofit.
#
# The motion is DECLARATIVE by ruling, not by preference: §2 of the ADR measured
# a real browser and found CSS animation alive — and <script> dead — inside the
# bare sandbox="" that the Web Viewer, the paged navigator and the public share
# link all use. Script-driven motion would render only for its own author.
# v17 (ADR-544 D2) — the region selectors follow the Area grain:
# `[data-slot="media"]` → `[data-area-role="media"]` (role, not authored name)
# and the relative-position rule reads `[data-area]`. The BUMP is the point: the
# CSS changed in the kernel, so without it `ensure_kernel_style_in_html` sees a
# same-or-newer version and returns byte-identical — every already-authored deck
# would keep the stale rule forever and its full-bleed media would not flex.
# A kernel CSS edit without a version bump is a change that never mounts.
STUDIO_KERNEL_CSS_VERSION = 17


def compose_kernel_style_element() -> str:
    """The marked kernel style element (ADR-453 D2) — baked into skeletons,
    upserted by the FE ops. Like data-skin (ADR-449): marked so switches
    replace only the UNMARKED layout style; versioned so old artifacts
    retrofit on first touch."""
    return (
        f'<style data-kernel="true" data-kernel-v="{STUDIO_KERNEL_CSS_VERSION}">\n'
        f"{STUDIO_KERNEL_CSS}\n"
        f"</style>"
    )


#: The marked kernel style, for find-replace (mirror of design_systems'
#: `_SKIN_ELEMENT_RX`). Matched regardless of version so a stale one is replaced.
_KERNEL_ELEMENT_RX = re.compile(
    r'<style\s+[^>]*data-kernel="true"[^>]*>.*?</style>', re.DOTALL
)
#: The version currently ON a kernel element, for the retrofit's version gate.
_KERNEL_VERSION_RX = re.compile(r'data-kernel="true"[^>]*data-kernel-v="(\d+)"')


def ensure_kernel_style_in_html(artifact_html: str) -> str:
    """Retrofit the marked kernel style into an artifact — the SERVER mirror of
    the FE `ensureKernelStyle`/`retrofitKernel` (artifactOps.ts).

    ADR-453 D2 promises the kernel element "retrofits on first touch" so a new
    block kind / arrangement / token lights up in an OLD artifact. The FE
    mechanical door does this on every member write — but an artifact authored
    or rewritten ENTIRELY through the chat lane (a WriteFile that rebuilds the
    whole document) never passes through that door, so it could ship with NO
    marked kernel style and its property tokens (align / width / size) would be
    inert. This closes that path: the lane write retrofits too.

    Version-gated and marked-style-aware, like `apply_skin_to_html`:
      · no `</head>` (not a full-document artifact) → unchanged.
      · an existing kernel element at an OLDER version → replaced in place.
      · at the SAME-or-newer version → unchanged (byte-identical, no revision).
      · none present → inserted before the marked skin element if there is one
        (cascade: layout < kernel < skin), else before </head>.
    """
    if "</head>" not in artifact_html:
        return artifact_html  # not a full-document artifact — leave it alone
    fresh = compose_kernel_style_element()
    existing = _KERNEL_ELEMENT_RX.search(artifact_html)
    if existing:
        m = _KERNEL_VERSION_RX.search(existing.group(0))
        cur_v = int(m.group(1)) if m else 0
        if cur_v >= STUDIO_KERNEL_CSS_VERSION:
            return artifact_html  # already current — no churn
        return _KERNEL_ELEMENT_RX.sub(lambda _m: fresh, artifact_html, count=1)
    # None present — insert before the skin element (kernel < skin), else </head>.
    skin = re.search(r'<style\s+[^>]*data-skin="true"', artifact_html)
    anchor = skin.start() if skin else artifact_html.find("</head>")
    return artifact_html[:anchor] + fresh + "\n" + artifact_html[anchor:]


#: Every layout's scaffolded h1 text — the ONLY strings `set_artifact_title`
#: may overwrite. DERIVED from the registry, so editing a scaffold can never
#: silently orphan this list and start overwriting a member's authored title.
#: Every registered layout's scaffolded h1 placeholder — maintained by
#: `register_layouts` as each app's table arrives (ADR-518 D3), so the set
#: covers Docs' document and IMAGES' stage as well as Studio's own rows.
#: (The prior frozen derivation read STUDIO_LAYOUTS only, which silently
#: missed the IMAGES scaffold and would have lost `document` at the carve.)
_SCAFFOLD_TITLES: set[str] = set()


def _scaffold_title(lay: dict) -> str | None:
    """The h1 placeholder a layout's scaffold ships, tags stripped."""
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", lay.get("scaffold", ""), re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None


def set_artifact_title(html: str, title: str, *, set_h1: bool = True) -> str:
    """Retitle an artifact: the ``<title>`` AND the ``<h1>`` title block.

    The name is ONE fact wearing two hats — the file's name and the artifact's
    own title (2026-07-15). They used to drift: creation named the FILE from
    what the member typed and left the h1 at "Untitled document", so the
    artifact told you one thing and the substrate another, and only the
    filename was real.

    TWO guards, because an h1 is not always a title:

    1. Only a `flow` layout's h1 IS the artifact's title. A `paged` layout's h1
       is the title SLIDE's thesis / the landing page's headline — authored
       content that a FILENAME has no business dictating. So `set_h1` is False
       for paged layouts: the file is named, the thesis is left alone.
    2. Even in `flow`, only the untouched scaffold placeholder is replaced.
       Once the member has authored a title, their words win.

    The `<title>` element is always set — it is metadata, never authored.

    String-level on purpose: the kernel has no DOM, and the skeleton's shape is
    ours (the `t1` title block is scaffolded by every layout). A member's
    authored html is never reshaped here — only the placeholder is replaced.
    """
    safe = html_escape(title.strip()) if title and title.strip() else ""
    if not safe:
        return html
    out = re.sub(r"<title>[^<]*</title>", f"<title>{safe}</title>", html, count=1)
    if not set_h1:
        return out  # paged: the h1 is a thesis/headline, not a title (guard 1)
    # Only the scaffolded placeholder gets rewritten — never authored words.
    def _h1(m: re.Match) -> str:
        inner = m.group(2)
        if not _is_placeholder_title(inner):
            return m.group(0)
        return f"{m.group(1)}{safe}{m.group(3)}"

    out = re.sub(r'(<h1\b[^>]*data-block-id="t1"[^>]*>)(.*?)(</h1>)', _h1, out, count=1, flags=re.S)
    return out


def _is_placeholder_title(inner: str) -> bool:
    """Is this h1 still the kernel's scaffolded placeholder (never authored)?"""
    text = re.sub(r"<[^>]+>", "", inner).strip()
    return text in _SCAFFOLD_TITLES


# ---------------------------------------------------------------------------
# The layout resolver (ADR-472 D2) — the shared machinery's one lookup.
# ---------------------------------------------------------------------------
#
# `build_skeleton`, `build_studio_posture`, `describe_artifact_kind` and the
# arrangement grammar are SHARED by Studio and IMAGES: a stage is composed,
# postured, and named by the same code that composes a deck. Rather than fork
# them per app (the dual-approach smell) or have Studio import IMAGES (a kernel
# depending on an app), each app REGISTERS its layouts here and the shared
# machinery resolves through one door.
#
# Studio registers its own table at import; IMAGES registers at import of
# `services/images/`. Registration is idempotent and slug-keyed — a collision
# is a programming error, not a silent override.

_LAYOUT_REGISTRY: dict[str, dict] = {}
_ARRANGEMENT_REGISTRY: dict[str, dict] = {}


def register_layouts(layouts: dict[str, dict], arrangements: dict[str, dict] | None = None) -> None:
    """Register an app's document types with the shared machinery (ADR-472 D2).

    Also maintains `_SCAFFOLD_TITLES` (ADR-518 D3): the placeholder-title set
    must cover every app's scaffolds, and registration is the one door they
    all arrive through.
    """
    for slug, row in layouts.items():
        title = _scaffold_title(row)
        if title:
            _SCAFFOLD_TITLES.add(title)
        existing = _LAYOUT_REGISTRY.get(slug)
        if existing is not None and existing is not row:
            # Grammar, not schema (ADR-443 §6 — no exceptions from this
            # module; it stays a pure program). FIRST
            # REGISTRATION WINS: a second app claiming a live slug is a
            # programming error, but silently keeping the incumbent beats
            # crashing an import chain at boot. The ADR-472 gate asserts the
            # two apps' slug sets are disjoint, which is where a collision is
            # actually caught.
            continue
        _LAYOUT_REGISTRY[slug] = row
    for slug, rows in (arrangements or {}).items():
        _ARRANGEMENT_REGISTRY[slug] = rows


#: Retired layout slugs → their successor (ADR-505 D2). A pre-cut artifact
#: carries `data-template="article"` in its own bytes, and ADR-209 forbids
#: manufacturing a revision to fix a naming decision — so the slug resolves at
#: READ time and the source is never rewritten (the ADR-481 D5 discipline:
#: legacy renders, never migrates; it converges when the member next edits).
#:
#: This is an alias, NOT a dual implementation: there is one `web` row and one
#: `web` arrangement roster. Nothing may be ADDED here — a new retirement earns
#: a row, and a slug that never shipped is simply unknown.
RETIRED_LAYOUT_SLUGS: dict[str, str] = {
    "article": "web",
    "page": "web",
}


def canonical_layout_slug(slug: str) -> str:
    """A retired layout slug mapped to its live successor; any other slug as-is.

    The one place a legacy `data-template` value is reinterpreted. `canvas` is
    deliberately ABSENT — it belongs to the IMAGES app (ADR-472 D1), never to
    Studio, so it must resolve through the IMAGES registration or not at all.
    """
    return RETIRED_LAYOUT_SLUGS.get(slug, slug)


def resolve_layout(slug: str) -> dict | None:
    """The layout row for a slug, from ANY registered app. None if unknown.

    Retired Studio slugs resolve to their successor (ADR-505 D2) so a pre-cut
    artifact keeps rendering with the right mode, skin and chrome.
    """
    return _LAYOUT_REGISTRY.get(canonical_layout_slug(slug))


def blocks_for_app(app: str | None) -> dict[str, dict]:
    """The block vocabulary an APP offers (ADR-528 D5).

    A row without ``apps`` belongs to every app — the default, and what all but
    two rows carry. A row naming ``apps`` is offered only by those apps.

    Derived from the row, never from a slug list: a new app registering a
    layout inherits the whole shared roster without editing this function, and
    a kind changes hands by moving one tuple. `app=None` (an unresolvable or
    unregistered template) yields the full roster — the tolerant default, since
    the vocabulary TEACHES and never validates (ADR-443 R4).

    This is a grammar filter, not a schema gate. An artifact already holding a
    kind its app no longer offers renders and edits exactly as before; the kind
    is simply not offered again (an INERT NAME — ADR-511 D8).
    """
    if not app:
        return dict(STUDIO_BLOCKS)
    return {
        kind: b
        for kind, b in STUDIO_BLOCKS.items()
        if app in b.get("apps", ())  # named → this app must be in the list
        or "apps" not in b  # unnamed → every app
    }


def app_for_layout(slug: str | None) -> str | None:
    """Which app owns a layout slug (ADR-473 D2's `app`, read back). None if
    the slug is unknown — callers treat that as "no filtering"."""
    if not slug:
        return None
    row = resolve_layout(slug)
    return row.get("app") if row else None


def all_layouts() -> dict[str, dict]:
    """Every registered layout across apps (the vocabulary surface reads this).

    Live types only — a retired slug is resolvable (``resolve_layout``) but never
    OFFERED, so the create picker shows three Studio types and not five.
    """
    return dict(_LAYOUT_REGISTRY)


def resolve_arrangements(slug: str) -> dict:
    """The arrangement roster for a layout, from any registered app."""
    return _ARRANGEMENT_REGISTRY.get(canonical_layout_slug(slug), {})


# Studio registers its document types with the shared resolver (ADR-472 D2).
register_layouts(STUDIO_LAYOUTS, STUDIO_ARRANGEMENTS)


def build_skeleton(layout: str, title: str | None = None) -> str:
    """Assemble a new artifact's first revision: layout × starter blocks.

    The skeleton is self-describing (``data-template`` on the root; blocks
    annotated ``data-block`` + ``data-block-id``) and script-free (the canvas
    strips executables anyway — defense in depth).

    `title` (the name the member typed at creation) titles the artifact as well
    as the file — see `set_artifact_title`. Absent, the placeholder stands.
    """
    # Grammar, not schema (ADR-443 §6 — no exceptions from this module): an
    # unknown layout falls back to `document` the way every other resolution
    # site does, rather than gating creation. Resolved through the REGISTRY
    # (ADR-518 D3 — `document` is Docs' row, and the kernel never imports an
    # app); the last-resort clause covers import-time callers that run before
    # every app has registered.
    lay = (
        resolve_layout(layout)
        or resolve_layout("document")
        or next(iter(_LAYOUT_REGISTRY.values()))
    )
    placeholder = f"Untitled {lay['label'].lower()}"
    html = f"""<!doctype html>
<html data-template="{layout}">
<head>
<meta charset="utf-8">
<title>{placeholder}</title>
<style>
{_SHARED_CSS}
{lay['skin']}
</style>
{compose_kernel_style_element()}
</head>
<body>
{lay['scaffold']}
</body>
</html>
"""
    return set_artifact_title(html, title) if title else html


#: The creation-time registry (API surface of routes/studio.py — shape kept
#: stable from ADR-440). Derived: a template IS a layout + its starters.
DEFAULT_APP = "studio"


def app_for_kind(kind: Optional[str]) -> Optional[str]:
    """Which app OWNS a document type (ADR-473 D2) — the LaunchServices answer.

    The artifact declares its type in its own content (`data-template`, lifted
    by `artifact_kind`); the layout row declares which app owns that type. This
    resolves one to the other.

    Returns None for an unowned type — a bundle-shipped layout, a hand-authored
    file, an artifact from an app that isn't installed. That is a FALLBACK, not
    a failure (D6): the file still opens in the generic viewer and still appears
    in Files; it simply belongs to no app's recents.
    """
    if not kind:
        return None
    row = resolve_layout(kind)
    if not row:
        return None
    return row.get("app") or DEFAULT_APP


def kinds_for_app(app: str) -> set:
    """Every document type an app owns (ADR-473 D2) — the inverse lookup.

    Used to scope an app's creation palette and its artifact list. Derived from
    the same single declaration, never restated.
    """
    return {
        slug
        for slug, row in all_layouts().items()
        if (row.get("app") or DEFAULT_APP) == app
    }


def all_templates() -> dict[str, dict[str, str]]:
    """Every registered app's templates (ADR-472 D1) — layout × starter blocks.

    STUDIO_TEMPLATES stays Studio's own (ADR-443 §derivation asserts it equals
    STUDIO_LAYOUTS exactly); this is the cross-app view the creation surface
    and the vocabulary endpoint read, so an IMAGES stage is creatable without
    Studio's table growing a row it does not own.
    """
    return {
        slug: {
            "label": lay["label"],
            "description": lay["description"],
            "skeleton": build_skeleton(slug),
            "app": lay.get("app") or DEFAULT_APP,  # ADR-473 D2
        }
        for slug, lay in all_layouts().items()
    }


STUDIO_TEMPLATES: dict[str, dict[str, str]] = {
    slug: {
        "label": lay["label"],
        "description": lay["description"],
        "skeleton": build_skeleton(slug),
    }
    for slug, lay in STUDIO_LAYOUTS.items()
}


# ---------------------------------------------------------------------------
# Posture (ADR-440 D3 + ADR-443 D4/D5/D6) — the bound lane's authoring
# overlay, composed at turn time. PURE: caller supplies the artifact content.
# ---------------------------------------------------------------------------

def _blocks_grammar(app: str | None = None) -> str:
    """The kind roster the lane is taught (ADR-443 R4 — grammar, not schema).

    ADR-528 D5: scoped to the APP that owns the artifact's layout. The lane
    reads this grammar to decide what to author, so an unscoped roster is how
    the AI hand keeps offering a Docs member a callout the app does not offer —
    the same fault ADR-525 D4 fixed for tokens ("the lane reads this grammar
    too, so without D4 the AI hand keeps being told a paragraph has a width").
    """
    return "\n".join(
        f"  - {kind} — {b['description']}\n    e.g. {b['markup']}"
        for kind, b in blocks_for_app(app).items()
    )


def _arrangements_grammar(template: str) -> str:
    """The arrangement roster for a layout — the composition options the lane
    can author or re-lay to (ADR-447). Grammar, not schema."""
    rows = resolve_arrangements(template)
    if not rows:
        return "  (no named arrangements for this layout — a single flow.)"
    return "\n".join(
        f"  - {slug} — {a['description']} (areas: "
        + ", ".join(f"{s['name']}[{s['role']}]" for s in a["areas"])
        + ")"
        for slug, a in rows.items()
    )


def _where_phrase(scope: tuple, grains: tuple) -> str:
    """Render a row's (scope, grains) as the WHERE half of its grammar line
    (ADR-542 D2 — composed from the two tables, never enumerated per compound).

    An unknown value degrades to itself rather than vanishing: a new grain
    without a matching phrase still teaches the lane something, and the gate
    catches the omission."""
    scopes = " / ".join(SCOPE_PHRASES.get(s, s) for s in scope)
    conds = [GRAIN_PHRASES.get(g, g) for g in grains if g != "any"]
    return scopes if not conds else f"{scopes} {' / '.join(c for c in conds if c)}"


def _tokens_grammar() -> str:
    """The property-token roster (ADR-453) — one line per family, derived from
    the registry so the posture and the Design tab never drift.

    Each line carries WHERE the token may sit (its scope × grains, ADR-542),
    because the Design tab gates on exactly that and the lane previously
    wasn't told it — the two hands got one grammar but only one got the
    relation."""
    return "\n".join(
        f'  - data-{key}="'
        + "|".join(v["value"] for v in t["values"])
        + f'" [on {_where_phrase(t["scope"], t["grains"])}] — {t["description"]}'
        for key, t in STUDIO_TOKENS.items()
    )


_POSTURE_FRAME = """
## Studio: you are authoring one artifact
This lane is bound to `{path}` (layout: {template}). Your job is to author
and revise THAT artifact; the member sees it re-render beside this chat after
every write.
{outline_section}
- PATCH, don't rewrite: prefer EditFile with exact old/new fragments for
  changes; reserve WriteFile (full replace) for re-drafts the member
  explicitly asks for — and for FIRST COMPOSITION onto a fresh scaffold,
  where one WriteFile carrying the complete document is honest (a compose is
  a re-draft of placeholder content; send the FULL content in that same
  call). After the first composition, PATCH. Small patches keep the revision
  history legible.
- Scaffold PLACEHOLDER blocks (the skeleton's starter content) may be
  replaced or dropped when you compose; blocks the member or a prior turn
  authored are never dropped and keep their data-block-id.
- The member also edits DIRECTLY on the canvas — typing block text in place,
  and inserting blocks and slides (operator-authored revisions land between
  your turns): always re-read before editing, treat the current content as
  truth, and never renumber or remove existing data-block-id values you didn't
  create. A member's in-place text edit changes only a block's inner content,
  never its id or its cited objects — so when they ask you to build on an edit,
  read the block fresh rather than assuming your last version.
- The artifact is self-contained HTML: inline CSS only, no <script> and no
  external URLs — the canvas renders it fully sandboxed (scripts never run),
  and everything it shows must come from the workspace.

## Blocks (the component grammar)
Compose content as BLOCKS: each top-level content unit carries
data-block="<kind>" plus a short unique data-block-id (e.g. "b7") that you
stamp when creating a block and PRESERVE when editing it. Patch WITHIN block
boundaries — one block per edit where possible — and address blocks by their
id when the member selects one. Content that fits no kind may stay
unannotated; the grammar teaches, it never rejects.
Titles, headings, kickers, subtitles, and framing lines are also blocks —
data-block="heading" — so the member can select and edit them in place; keep
them annotated with a stable id when you author or restructure a header or a
slide title. Kinds:
{blocks_grammar}
  - heading — a title/kicker/subtitle/framing line (structural, not
    palette-inserted); e.g. <h1 data-block="heading" data-block-id="t1">Title</h1>

## Layout
This artifact's layout is {template}: {flow}
When the member asks to change the layout: preserve every block and its
data-block-id, replace the UNMARKED <style> skin and the flow structure per
the target layout's grammar, and update data-template on the root. The MARKED
style elements — <style data-kernel="true"> (kernel token CSS) and
<style data-skin="true"> (the workspace's design system) — are not the layout
skin: never edit or remove them; they survive every switch. A layout change is
an ordinary edit — versioned and revertible like any other.

## Arrangements and AREAS (where content goes on a page/section)
The structure is four grains: SLIDE (or band) → LAYOUT → AREA → BLOCK.
Each page or section carries an ARRANGEMENT — data-arrange="<slug>" on the
page element (a deck slide, or a web <section> band) — which declares AREAS:
data-area="<name>" data-area-role="<role>" regions that hold blocks, with an
optional data-area-place="<left|center|right>" to tell same-role siblings
apart. Roles are a closed set: heading · body · media · aside.

THE CONTAINMENT LAW: every block lives in exactly one Area. NEVER author a
block as a direct child of a slide or band — a bare <h2> under a slide is a
defect, not a shortcut. A slide's title goes in its heading-role Area.

The arrangement is the composition (grids, columns, areas); the block is the
content; keep them distinct. When you author a new page/section, annotate it
with data-arrange and give every content region data-area + data-area-role.
When you re-lay a page to a different arrangement, move existing blocks INTACT
(ids preserved) into the new arrangement's Areas, matching BY ROLE
(heading→heading, body→body, media→media) — heading blocks anchor the page and
are not swept. The member also re-arranges directly with the toolbar; treat the
current arrangement as truth and re-read before editing. Arrangements for this
layout:
{arrangements_grammar}

## Property tokens (placement + emphasis — tokens, never raw style)
The artifact root, blocks, and pages may carry property TOKENS — data-*
attributes with small named value sets, styled by the marked
<style data-kernel="true"> element and themed by the design system's custom
properties. Absence is the default: set a token by adding the attribute, clear
it by removing the attribute. Never use inline style="" or raw colors for
placement/emphasis — the token IS the edit. Document-grain tokens (font,
measure, pagenum) live on the <html> root element (ADR-455/456). The member also sets
tokens from the Design tab; preserve tokens you didn't touch, and set them
yourself when asked in plain words ("center that", "make it serif", "make the
image smaller", "make this slide a dark divider"). Families:
{tokens_grammar}
Blocks may also carry MEASURES — member-authored geometry from the canvas
gestures: data-w/data-h with style="--yw/--yh" (size in a frame), and on a
STAGED frame (a deck slide or a canvas artboard) data-x/data-y with
--yx/--yy (a positioned block) plus data-z with --yz (stacking among
positioned blocks — higher is in front; absence = document order). When
editing a block's content, preserve its measure attributes and its
style="--y*" declarations exactly; a re-laid page (arrangement change) is
the act that returns a positioned block to flow, never a content edit.

## Citing workspace objects (references, never copies)
- Embed a workspace file by REFERENCE, resolved live at render time:
  `<img data-ref="operation/brand/logo.png" data-ref-rev="<head-rev-id>" alt="...">` for
  images, `<div data-ref="operation/metrics/summary.csv" data-ref-kind="table"></div>`
  for a CSV rendered as a table. NEVER paste base64 or copy a cited file's
  bytes/contents into the artifact — the reference IS the point: when the
  source changes, the artifact stays current.
- Assets that belong to this artifact live beside it and are cited RELATIVE
  with a leading `./` (`data-ref="./assets/hero.png"` — resolved against the
  artifact's folder, so the project moves as a unit); shared workspace objects
  are cited by their workspace path (`data-ref="operation/..."`) and stay
  where they live — do not move or duplicate them.
- `data-ref-rev` is the citation's PIN — the cited file's head revision id.
  ALWAYS stamp it: read the cited file this turn (ReadFile reports its head
  revision) and put that id in the attribute. The pin is what lets the
  citation survive the path moving or being deleted, and it is the artifact's
  whole difference from a tool that bakes a copy. An empty pin is a citation
  that can only ever dangle — leave it empty ONLY if the file genuinely has no
  revision. When you rewrite a citation you already have, refresh its pin.
- Never edit a cited object's content inside the artifact. If the member asks
  to change a cited source, edit the SOURCE file itself.
- A page/section can wear a CITED BACKGROUND image: set data-ref="<image path>"
  and data-ref-kind="background" (plus the data-ref-rev pin) on the page
  element itself — the canvas renders it as a cover background. Pair it with
  data-scrim="dark|light" for text legibility and data-bg-pos="top|bottom" for
  focus. Never write inline style backgrounds — the citation IS the background.
- You can CREATE visual assets too — vector graphics are plain text: author
  diagrams, icons, and illustrations as `.svg` files into `./assets/` beside
  the artifact (WriteFile), then cite them (`data-ref="./assets/diagram.svg"`).
  Prefer an authored SVG over describing a picture you cannot make.
- A CHART is not one of them (ADR-538 D2). Charts cite DATA, never a picture:
  write the numbers as a `.csv` in the workspace, then cite it from a chart
  block (data-ref="<the csv>" data-ref-kind="chart", data-chart="bar|line|
  donut"). The projection draws it, so the chart stays true when the data
  changes — an authored SVG chart goes stale the moment a number moves.
- Motion is CSS only, never <script>: a script does not run in the viewer or
  in a shared link, so a component that needs one is invisible to readers.

## Style
Match the artifact's existing voice and CSS. If the workspace carries design
conventions (e.g. operation/CONVENTIONS.md), respect them.
""".rstrip()


def extract_template(artifact_content: str) -> Optional[str]:
    """The artifact's declared layout, from its data-template root attr."""
    m = re.search(r'data-template="([a-z-]+)"', artifact_content or "")
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# ADR-459 — the artifact reads as what it is. Both helpers are PURE and
# COMPUTED: the kind is lifted from content, the name from the namespace.
# Neither is stored — the storage half of this design was deleted, not built
# (a `kind` column would be a denormalized cache of `data-template`; a `title`
# column a second source for the artifact's own <h1> — ADR-456 D1).
# ---------------------------------------------------------------------------

#: Fallback when an artifact declares no (or an unknown) layout. Honest rather
#: than guessing — the same disposition the retired stem-matcher had.
UNKNOWN_KIND_LABEL = "File"


def artifact_kind(artifact_content: Optional[str]) -> dict[str, Optional[str]]:
    """The artifact's kind — LIFTED from its own ``data-template`` (ADR-459 D1).

    Returns ``{"kind": slug_or_None, "kind_label": label}``. The slug is an
    OPAQUE STRING (ADR-459 D3, mirroring ``AppId = string`` per ADR-436): a
    layout the kernel doesn't know still round-trips its slug, so a bundle can
    ship one with zero kernel touches (ADR-222 — the kernel names the slot,
    the program fills the value).

    Unknown-but-declared beats blank: a `tearsheet` from a bundle reads
    "Tearsheet" via titleize even before the kernel has a row for it.
    """
    slug = extract_template(artifact_content or "")
    if not slug:
        return {"kind": None, "kind_label": UNKNOWN_KIND_LABEL}
    # ADR-505 D2: a retired slug reports as its successor. The slug is what the
    # FE keys its glyph and its app routing on, so returning the raw legacy
    # value would split one artifact's identity in two — kind `article` wearing
    # label "Web". One name, resolved once, at the lift.
    slug = canonical_layout_slug(slug)
    known = resolve_layout(slug)
    if not known:
        # Deferred import: bundle_reader reads the program bundles off disk;
        # the kernel four resolve without ever touching it.
        from services.bundle_reader import list_bundle_layouts

        known = list_bundle_layouts().get(slug)
    label = known["label"] if known else _titleize(slug)
    return {"kind": slug, "kind_label": label}


def _titleize(slug: str) -> str:
    """`ir-deck-v3` → `Ir deck v3`. The ADR-312 plain-language mechanic, in
    SENTENCE case rather than Title Case.

    Deliberately DUMB, and the dumbness is the point. The creation modal
    lowercases the member's name into the slug (`slugify` in
    NewArtifactModal), so the original casing is genuinely gone — every
    reconstruction is a guess, and the only question is which guess reads
    least wrong.

    Sentence case (capitalize the first word, leave the rest) is the guess
    that loses smallest: it's how a person names a document, and it's wrong
    in ONE predictable way (an acronym reads "Ir" instead of "IR") rather
    than wrong in every word the way `.title()` is ("Ir Deck V3").

    An acronym heuristic was tried and rejected: "does it have vowels" makes
    IR/KPI/PRD look like ordinary words while flagging "my"; no rule
    distinguishes a typed "IR" from a typed "ir" once the case is gone. A
    cleverer guess would be wrong less often but wrong less PREDICTABLY,
    which is worse — the member can't learn it.

    The ceiling is honest: a true round-trip needs the typed name stored, and
    storing it is a second source for a fact the namespace already carries
    (ADR-459 D2 — the trade this ADR took on purpose). If acronym fidelity
    ever matters more than the storage cost, THAT is the ADR to write, not a
    smarter regex here.
    """
    words = slug.replace("-", " ").replace("_", " ").split()
    if not words:
        return ""
    return " ".join(w.capitalize() if i == 0 else w for i, w in enumerate(words))


def extract_title(artifact_content: Optional[str]) -> Optional[str]:
    """The artifact's own name, from its ``<title>`` (ADR-469 — the D1 lift).

    ``set_artifact_title`` writes the member's typed name here at creation and
    at every rename, ALWAYS and for every layout, and its docstring records why
    that element is the trustworthy one: *"the ``<title>`` element is always set
    — it is metadata, never authored."* Unlike the ``<h1>`` (a thesis on a paged
    layout, member-authored words once touched), nothing else may write it.

    So the name is a fact the artifact CARRIES, exactly as ``data-template``
    carries the kind. Returns None when the element is absent or empty — the
    caller falls back to the path.
    """
    m = re.search(r"<title>([^<]*)</title>", artifact_content or "")
    if not m:
        return None
    # set_artifact_title escapes on the way in; unescape on the way out so the
    # round-trip is exact (`&amp;` → `&`).
    return html_unescape(m.group(1)).strip() or None


def artifact_name(path: str, content: Optional[str] = None) -> str:
    """The artifact's operator-facing name — LIFTED from the artifact, with the
    namespace as fallback (ADR-469, amending ADR-459 D2).

    Two sources, in order:

    1. **The artifact's own ``<title>``** — what the member actually typed,
       exact: casing (`IR deck v3`, not `Ir deck v3`) and script (`한글 문서`,
       not `Untitled`) both survive. This is ADR-459 D1's lift pattern applied
       to the name, for D1's own stated reason: *"the kind was never in the
       name"* — and neither was the name.
    2. **The titleized meaning folder** — ADR-459 D2's rule, preserved verbatim
       as the fallback. It still serves every artifact whose content isn't to
       hand (a tree-node picker) or predates the lift.

    Why the fallback is no longer the primary: D2's derivation is lossy through
    `slugify`, and measurement showed the loss is not only the casing D2
    accepted. A name with no Latin characters slugs to the literal `untitled`,
    so distinct documents collide on one path — the ceiling D2 recorded in
    advance ("if fidelity ever outweighs the storage cost, that is its own
    ADR"). The lift clears it while storing nothing: the title was already
    being written, and content was already authoritative.

    Degrades honestly at every step: no content → the folder; no meaning folder
    → the titleized stem; nothing → "File".
    """
    lifted = extract_title(content)
    # A PLACEHOLDER title is not a name — fall through to the folder.
    #
    # Browser-tested 2026-07-20: an artifact created BEFORE ADR-469 never got
    # the typed name written into <title>, so it kept the skeleton placeholder
    # while its folder held the real name. Once the lift made content win, such
    # a file started reading as "Untitled document" — and a member clicking a
    # card so labelled opened `prd-for-yarnnn`. The label was honest and the
    # target was right; the NAME was wrong, which is worse than either.
    #
    # `_is_placeholder_title` is the same predicate `set_artifact_title` uses to
    # decide an h1 is untouched (derived from the layout scaffolds), so the two
    # can never disagree about what counts as "not yet named".
    if lifted and not _is_placeholder_title(lifted):
        return lifted
    parts = [p for p in (path or "").split("/") if p]
    if not parts:
        return UNKNOWN_KIND_LABEL
    region_tail = [p for p in STUDIO_ARTIFACT_REGION.split("/") if p]
    # The meaning folder is the segment holding the artifact — unless that IS
    # the region itself (a bare `operation/deck.html`), in which case use stem.
    parent = parts[-2] if len(parts) >= 2 else None
    if parent and parent not in region_tail:
        return _titleize(parent)
    stem = re.sub(r"\.[a-z0-9]+$", "", parts[-1], flags=re.IGNORECASE)
    return _titleize(stem) or UNKNOWN_KIND_LABEL


def extract_outline(artifact_content: str, limit: int = 24) -> list[str]:
    """Heading texts in document order — the artifact's outline.

    ADR-539 D3/D5 — reads HEADING_RUNGS, the same declared set the member's
    pane outline walks. Until 2026-08-09 this read h1/h2 while the pane read
    h1–h3, so the member and the lane saw DIFFERENT outlines of one document
    (ADR-526 §1.1 claimed parity; three divergent selectors made it false).
    Indentation encodes depth: two spaces per rung below the first."""
    rung_class = "".join(str(r) for r in HEADING_RUNGS)
    heads = re.findall(
        rf"<h([{rung_class}])[^>]*>(.*?)</h\1>", artifact_content or "", flags=re.DOTALL
    )
    out = []
    for level, raw in heads[:limit]:
        text = re.sub(r"<[^>]+>", "", raw).strip()
        if text:
            out.append("  " * (int(level) - min(HEADING_RUNGS)) + text)
    return out


def build_focus_line(focus: Optional[dict], template: str) -> str:
    """ADR-522 D5 — one bullet naming where the member is standing.

    The register is _POSTURE_FRAME's: operator words, "the member" as actor,
    prose rather than key-value, and **1-indexed** page numbers (the state is
    0-indexed; the member counts from one — the same conversion
    SelectionBreadcrumb's `pageNoun` and Studio's `askAboutSelection` already
    make).

    This is NOT ADR-446 D5's auto-seed returning. That was cut because it
    appended prose to the MEMBER'S composer on every click — visible spam they
    had to delete. This is a server-rendered line in the system posture, once
    per turn, which the member never sees and never has to clean up.

    Returns "" when nothing is declared: an app that declares nothing costs
    nothing.
    """
    if not focus:
        return ""

    scope = (focus.get("scope") or "document").strip()
    label = (focus.get("label") or "").strip()
    excerpt = (focus.get("excerpt") or "").strip()
    page = focus.get("page_index")
    viewport = focus.get("viewport_page_index")
    # The member's word for a page unit; a deck has slides, everything else
    # has sections (the SelectionBreadcrumb precedent).
    page_noun = "slide" if template == "deck" else "section"

    def _quoted(text: str) -> str:
        clipped = text[:80].strip()
        return f' — "{clipped}"' if clipped else ""

    if scope == "block":
        thing = label or "block"
        # A heading names the SECTION the member is writing in (D4) — but ONLY
        # on flow. Docs has no section unit, so the heading is the truest
        # available answer there and "this section" means from it to the next.
        # On a PAGED medium the page is already the unit, so a heading is just
        # a selected block and saying "writing under" would be false.
        if thing == "heading" and page_noun == "section":
            named = f' "{excerpt[:80].strip()}"' if excerpt else " (untitled)"
            return f"- The member is writing under the heading{named}."
        return f"- The member has the {thing} block selected{_quoted(excerpt)}."
    if scope == "container":
        thing = label or "container"
        # Operator words are sometimes plural ("columns"), so agree the article
        # rather than always emitting "a".
        article = "the" if thing.endswith("s") else "a"
        return f"- The member has {article} {thing} selected{_quoted(excerpt)}."
    if scope == "page":
        if page is None:
            return ""
        # D3: "viewing" (it is on screen) vs "selected" (they picked it). When
        # the page index came from the viewport alone, say viewing — that is
        # the staged-deck case, where paging changes what is shown and nothing
        # is selected.
        verb = "is viewing" if page == viewport else "has selected"
        return f"- The member {verb} {page_noun} {page + 1}."
    return ""


def build_studio_posture(
    artifact_path: str,
    artifact_content: str,
    focus: Optional[dict] = None,
) -> str:
    """The bound lane's authoring posture — pure, composed per turn.

    ``artifact_content`` is the artifact's CURRENT head (the runner reads it
    fresh each turn — derived, never stored). An empty/missing artifact still
    yields a posture: the lane can (re)create the file at the bound path.

    ``focus`` (ADR-522) is what the member is looking at THIS turn — one
    bullet, optional, transient. Absent → byte-identical to the pre-ADR-522
    posture.
    """
    template = extract_template(artifact_content) or "document"
    # Registry-resolved fallback (ADR-518 D3): `document` is Docs' row now, and
    # the kernel never imports an app. The last-resort clause keeps an
    # unknown template postured even before every app has registered.
    layout = (
        resolve_layout(template)
        or resolve_layout("document")
        or next(iter(_LAYOUT_REGISTRY.values()))
    )
    outline = extract_outline(artifact_content)
    outline_section = (
        "- Current outline:\n" + "\n".join(f"  {h}" for h in outline)
        if outline
        else "- The artifact is currently empty or missing — create it at the "
             "bound path from the member's direction."
    )
    # ADR-522 D5: the focus bullet rides as a sibling of the outline, before
    # the first `- PATCH` line — the member's PLACE reads next to the
    # artifact's SHAPE, which is the order the two are used in.
    focus_line = build_focus_line(focus, template)
    if focus_line:
        outline_section = f"{outline_section}\n{focus_line}"
    return _POSTURE_FRAME.format(
        path=artifact_path,
        template=template,
        outline_section=outline_section,
        # ADR-528 D5 — the roster the OWNING app offers. `layout` is already
        # resolved above (with the document fallback), so the app is read from
        # the row rather than re-derived from the slug.
        blocks_grammar=_blocks_grammar(layout.get("app")),
        arrangements_grammar=_arrangements_grammar(template),
        tokens_grammar=_tokens_grammar(),
        flow=layout["flow"],
    )
