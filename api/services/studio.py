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
from html import escape as html_escape
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
# ---------------------------------------------------------------------------

STUDIO_BLOCKS: dict[str, dict[str, str]] = {
    "prose": {
        "label": "Text",
        "group": "content",
        "description": "A heading + flowing paragraphs — the default content unit.",
        "markup": '<section data-block="prose" data-block-id="b1"><h2>Heading</h2><p>…</p></section>',
    },
    "callout": {
        "label": "Callout",
        "group": "content",
        "description": "A visually offset aside that highlights one point.",
        "markup": '<aside data-block="callout" data-block-id="b2"><p>…</p></aside>',
    },
    "quote": {
        "label": "Quote",
        "group": "content",
        "description": "A pull quote with optional attribution.",
        "markup": '<blockquote data-block="quote" data-block-id="b3"><p>…</p><cite>…</cite></blockquote>',
    },
    "checklist": {
        "label": "Checklist",
        "group": "content",
        "description": "A list of discrete items or steps.",
        "markup": '<ul data-block="checklist" data-block-id="b4"><li>…</li></ul>',
    },
    # ADR-456 Wave 1 — the builder/Notion registry growth (rows, not mechanisms).
    "divider": {
        "label": "Divider",
        "group": "content",
        "description": "A horizontal rule between sections of content.",
        "markup": '<hr data-block="divider" data-block-id="b9">',
    },
    "toggle": {
        "label": "Toggle",
        "group": "content",
        "description": "A collapsible section — a summary line that expands.",
        "markup": '<details data-block="toggle" data-block-id="b10"><summary>Summary line</summary><p>…</p></details>',
    },
    "button": {
        "label": "Button",
        "group": "content",
        "description": "A call-to-action link, styled by the palette.",
        "markup": '<p data-block="button" data-block-id="b11"><a href="https://…">Call to action</a></p>',
    },
    "table": {
        "label": "Table",
        "group": "data",
        "description": "A live table CITED from a workspace CSV (never pasted).",
        "markup": '<div data-block="table" data-block-id="b5" data-ref="operation/…/data.csv" data-ref-kind="table"></div>',
    },
    "metrics": {
        "label": "Metrics",
        "group": "data",
        "description": "A row of headline numbers with labels.",
        "markup": '<div data-block="metrics" data-block-id="b6"><div class="metric"><strong>42%</strong><span>label</span></div></div>',
    },
    "chart": {
        "label": "Chart",
        "group": "data",
        "description": "An authored SVG chart in ./assets/, cited by reference.",
        "markup": '<figure data-block="chart" data-block-id="b7"><img data-ref="./assets/chart.svg" data-ref-rev="" alt="…"><figcaption>…</figcaption></figure>',
    },
    "figure": {
        "label": "Image",
        "group": "media",
        "description": "A workspace image CITED by reference, with a caption.",
        "markup": '<figure data-block="figure" data-block-id="b8"><img data-ref="operation/…/img.png" data-ref-rev="" alt="…"><figcaption>…</figcaption></figure>',
    },
    "gallery": {
        "label": "Gallery",
        "group": "media",
        "description": "A grid of workspace images, each CITED by reference.",
        "markup": '<div data-block="gallery" data-block-id="b12"><figure><img data-ref="operation/…/img.png" data-ref-rev="" alt=""><figcaption></figcaption></figure></div>',
    },
}


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
    figcaption { font-size: 0.85rem; color: var(--muted); margin-top: 0.5rem; }
    table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
    th, td { border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; }
    aside[data-block="callout"] { border-left: 3px solid var(--accent);
        background: rgba(180,84,10,0.06); padding: 0.75rem 1rem; margin: 1.25rem 0; }
    blockquote[data-block="quote"] { border-left: 3px solid #ddd; padding: 0.5rem 1rem;
        margin: 1.25rem 0; font-style: italic; }
    blockquote[data-block="quote"] cite { display: block; margin-top: 0.5rem;
        font-size: 0.85rem; color: var(--muted); font-style: normal; }
    ul[data-block="checklist"] { list-style: none; margin: 1rem 0; }
    ul[data-block="checklist"] li { padding-left: 1.5rem; position: relative; margin: 0.35rem 0; }
    ul[data-block="checklist"] li::before { content: "☐"; position: absolute; left: 0; }
    div[data-block="metrics"] { display: flex; gap: 1.5rem; flex-wrap: wrap; margin: 1.25rem 0; }
    div[data-block="metrics"] .metric strong { display: block; font-size: 1.6rem; }
    div[data-block="metrics"] .metric span { font-size: 0.8rem; color: var(--muted); }
""".strip("\n")

#: A layout's **mode** — the composition seam (2026-07-15). Two honest kinds of
#: artifact were wearing one workbench:
#:
#:   paged (deck, page) — the CONTAINER is the unit. A slide IS a page; a
#:     landing band IS a section. "New slide/section" is the primary authoring
#:     act, and a navigator strip is real navigation (PowerPoint/Keynote).
#:
#:   flow  (document, article) — BLOCKS are the unit and they flow. There is no
#:     section to insert; the outline is a derived table of contents, not
#:     structure. Insert is located at the pointer, never at "the document"
#:     (Notion/Docs).
#:
#: The chrome DERIVES from this: the paged affordances (the New-‹noun› gallery,
#: the navigator strip) are native to `paged` and were bolted onto `flow`, where
#: they fight the model — the tell was the 2026-07-14 ruling that a document's
#: outline "doesn't earn its width" and ships collapsed. An affordance defaulted
#: off is usually one that does not belong.
#:
#: Arrangements survive in `flow` — but as a BLOCK the pointer inserts (a
#: two-column band, a metrics band), never as a page unit. That reframing is
#: what keeps the capability without the collision.
#:
#: NB: distinct from each layout's `flow` KEY below, which is prose describing
#: the layout's markup shape to the lane. `mode` is the machine seam; `flow` is
#: pedagogy.
STUDIO_LAYOUT_MODES = ("flow", "paged")

STUDIO_LAYOUTS: dict[str, dict[str, str]] = {
    "document": {
        "label": "Document",
        "mode": "flow",
        "description": "An internal working document — sections under one title.",
        "flow": (
            "one <main> holding an <h1> title and a short lede <p>, then blocks "
            "flowing vertically. Clarity over polish."
        ),
        "skin": """
    main { max-width: 46rem; margin: 0 auto; padding: 3rem 1.5rem; }
    h1 { font-size: 2rem; margin-bottom: 0.5rem; }
    section[data-block] { margin-top: 2rem; }
    section[data-block] h2 { font-size: 1.3rem; margin-bottom: 0.75rem; }
""".strip("\n"),
        "scaffold": """<main>
  <h1 data-block="heading" data-block-id="t1">Untitled document</h1>
  <p class="lede" data-block="heading" data-block-id="t2">One sentence on what this document is for.</p>
  <section data-arrange="title-lede">
    <h2 data-block="heading" data-block-id="t3">First section</h2>
    <div data-slot="main">
      <div data-block="prose" data-block-id="b1"><p>Start here.</p></div>
    </div>
  </section>
</main>""",
    },
    "deck": {
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
    body { background: #e8e4de; }
    /* A deck slide is LANDSCAPE 16:9 — a fixed-aspect page, centered, one per
       screen. aspect-ratio keeps it landscape in the canvas AND in a scaled
       thumbnail (the navigator renders the same markup). */
    .slide { width: min(100%, 62rem); aspect-ratio: 16 / 9; margin: 1.5rem auto;
             padding: 3.5rem 4rem; display: flex; flex-direction: column;
             justify-content: center; background: var(--paper);
             box-shadow: 0 1px 6px rgba(0,0,0,0.08); overflow: hidden;
             page-break-after: always; }
    .slide h1 { font-size: 2.4rem; max-width: 34rem; }
    .slide h2 { font-size: 1.7rem; margin-bottom: 1rem; }
    .slide .kicker { color: var(--accent); font-size: 0.85rem;
                     letter-spacing: 0.08em; text-transform: uppercase;
                     margin-bottom: 1rem; }
    .slide p { max-width: 36rem; }
    .slide .cols { display: flex; gap: 2.5rem; align-items: flex-start; }
    .slide .col { flex: 1; min-width: 0; }
""".strip("\n"),
        "scaffold": """<section class="slide" data-arrange="title">
  <p class="kicker" data-block="heading" data-block-id="k1">Untitled deck</p>
  <h1 data-block="heading" data-block-id="t1">The one-line thesis goes here.</h1>
  <p data-block="heading" data-block-id="f1">Subtitle or framing sentence.</p>
</section>
<section class="slide" data-arrange="content">
  <h2 data-block="heading" data-block-id="t2">First point</h2>
  <div data-block="prose" data-block-id="b1">
    <p>One idea per slide.</p>
  </div>
</section>""",
    },
    "article": {
        "label": "Article",
        "mode": "flow",
        "description": "A publishing shape — blog post, essay, announcement.",
        "flow": (
            "one <article> with a <header> (h1 title, .subtitle promise, .byline "
            "— the header is a flow container; its title/subtitle/byline ARE "
            "heading blocks, data-block=\"heading\", so the member can edit them "
            "in place) followed by blocks of flowing prose; figures carry cited "
            "images. Written to be read by someone outside the workspace."
        ),
        "skin": """
    article { max-width: 42rem; margin: 0 auto; padding: 3.5rem 1.5rem; }
    header { margin-bottom: 2.5rem; }
    header h1 { font-size: 2.2rem; margin-bottom: 0.75rem; }
    header .subtitle { font-size: 1.15rem; color: var(--muted); }
    header .byline { font-size: 0.85rem; color: var(--muted); margin-top: 1rem;
                     letter-spacing: 0.02em; }
    article [data-block="prose"] p { margin: 1rem 0; }
""".strip("\n"),
        "scaffold": """<article>
  <header>
    <h1 data-block="heading" data-block-id="t1">Untitled article</h1>
    <p class="subtitle" data-block="heading" data-block-id="t2">The one-sentence promise to the reader.</p>
    <p class="byline" data-block="heading" data-block-id="t3">Byline · Date</p>
  </header>
  <section data-arrange="section">
    <div data-slot="main">
      <div data-block="prose" data-block-id="b1"><p>Opening paragraph.</p></div>
    </div>
  </section>
</article>""",
    },
    # ADR-456 D4 (Wave 3): the fourth layout — the landing page. Full-width
    # section BANDS (each an arrangement) with the content column centered
    # inside; heroes carry a cited background (data-ref-kind="background").
    "page": {
        "label": "Page",
        "mode": "paged",
        "description": "A landing page — hero, features, call to action.",
        "flow": (
            "one <main> of full-width section BANDS, each <section data-arrange=…> "
            "stacked vertically: a hero (kicker + h1 promise + tagline + button), "
            "then content/feature/testimonial bands, closing on a call-to-action. "
            "Band content centers itself; a band may wear a cited background image "
            "(data-ref + data-ref-kind=\"background\" on the section) with a "
            "data-scrim for legibility. Written to convert a visitor, not to be "
            "read top-to-bottom."
        ),
        "skin": """
    section[data-arrange] { padding: 4rem 1.5rem; }
    section[data-arrange] > * { max-width: 56rem; margin-left: auto; margin-right: auto; }
    section[data-arrange="hero"] { padding: 6rem 1.5rem; text-align: center; }
    h1 { font-size: 2.6rem; margin-bottom: 0.75rem; }
    .kicker { color: var(--accent); font-size: 0.85rem; letter-spacing: 0.08em;
              text-transform: uppercase; margin-bottom: 1rem; }
    .tagline { font-size: 1.2rem; color: var(--muted); }
    section[data-arrange] h2 { font-size: 1.8rem; margin-bottom: 1rem; }
""".strip("\n"),
        "scaffold": """<main>
  <section data-arrange="hero">
    <p class="kicker" data-block="heading" data-block-id="k1">Untitled page</p>
    <h1 data-block="heading" data-block-id="t1">The headline promise.</h1>
    <p class="tagline" data-block="heading" data-block-id="s1">One sentence expanding on it.</p>
    <p data-block="button" data-block-id="c1"><a href="https://…">Call to action</a></p>
  </section>
  <section data-arrange="content">
    <h2 data-block="heading" data-block-id="t2">First section</h2>
    <div data-slot="main">
      <div data-block="prose" data-block-id="b1"><p>Start here.</p></div>
    </div>
  </section>
</main>""",
    },
}


# ---------------------------------------------------------------------------
# Arrangements (ADR-447) — the composition layer, PROMOTED from ADR-444's
# deck-only "slide masters" to a first-class, per-document-type grammar.
# An arrangement says WHERE content goes on a page/section: grids, slots,
# overlays, sizings. It is orthogonal to the block (what content is) and the
# skin (how it looks). v1 is page-grain (whole page/slide); section-band
# nesting is phase 2.
#
# Each row: label + description (operator words) · grain ('page' in v1) ·
# slots (each {name, role}: role='flow' accepts blocks on a reflow,
# role='heading' is structural and anchors) · fragment (the deterministic
# insertion payload — data-arrange names the arrangement; data-slot marks the
# regions; the FE stamps fresh block ids and writes through the mechanical
# door). Grammar not schema (R4): an un-arranged artifact stays valid.
# ---------------------------------------------------------------------------

STUDIO_ARRANGEMENTS: dict[str, dict[str, dict]] = {
    "deck": {
        "title": {
            "label": "Title slide",
            "description": "Kicker, thesis headline, framing line.",
            "grain": "page",
            "slots": [{"name": "heading", "role": "heading"}],
            "fragment": """<section class="slide" data-arrange="title">
  <p class="kicker" data-block="heading" data-block-id="k1">Kicker</p>
  <h1 data-block="heading" data-block-id="t1">The headline goes here.</h1>
  <p data-block="heading" data-block-id="f1">Framing sentence.</p>
</section>""",
        },
        "content": {
            "label": "Content",
            "description": "A heading with content below.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section class="slide" data-arrange="content">
  <h2 data-block="heading" data-block-id="t1">Slide title</h2>
  <div data-slot="main"></div>
</section>""",
        },
        "two-column": {
            "label": "Two column",
            "description": "A heading over two side-by-side regions.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}, {"name": "side", "role": "flow"}],
            "fragment": """<section class="slide" data-arrange="two-column">
  <h2 data-block="heading" data-block-id="t1">Slide title</h2>
  <div class="cols">
    <div class="col" data-slot="main"></div>
    <div class="col" data-slot="side"><p>Second column.</p></div>
  </div>
</section>""",
        },
        "comparison": {
            "label": "Comparison",
            "description": "Two headed columns, side by side.",
            "grain": "page",
            "slots": [{"name": "left", "role": "flow"}, {"name": "right", "role": "flow"}],
            "fragment": """<section class="slide" data-arrange="comparison">
  <h2 data-block="heading" data-block-id="t1">Slide title</h2>
  <div class="cols">
    <div class="col"><h3 data-block="heading" data-block-id="l1">Option A</h3><div data-slot="left"></div></div>
    <div class="col"><h3 data-block="heading" data-block-id="r1">Option B</h3><div data-slot="right"></div></div>
  </div>
</section>""",
        },
        "quote": {
            "label": "Quote",
            "description": "One centered pull quote.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section class="slide" data-arrange="quote">
  <div data-slot="main">
    <blockquote data-block="quote" data-block-id="b1"><p>The quote.</p><cite>Attribution</cite></blockquote>
  </div>
</section>""",
        },
        # ADR-453: the two deck rows that make the media role + tone token real.
        "picture-with-caption": {
            "label": "Picture with caption",
            "description": "A big cited image beside its commentary.",
            "grain": "page",
            "slots": [{"name": "media", "role": "media"}, {"name": "caption", "role": "flow"}],
            "fragment": """<section class="slide" data-arrange="picture-with-caption">
  <h2 data-block="heading" data-block-id="t1">Slide title</h2>
  <div class="cols">
    <div class="col" data-slot="media"></div>
    <div class="col" data-slot="caption"><p>What this picture shows, and why it matters.</p></div>
  </div>
</section>""",
        },
        "section-header": {
            "label": "Section header",
            "description": "A full-tone divider slide that names the next part.",
            "grain": "page",
            "slots": [{"name": "heading", "role": "heading"}],
            "fragment": """<section class="slide" data-arrange="section-header" data-tone="inverse">
  <p class="kicker" data-block="heading" data-block-id="k1">Part</p>
  <h1 data-block="heading" data-block-id="t1">Section title</h1>
</section>""",
        },
        # ADR-456 Wave 1 — the builder-class deck rows. Their CSS lives in the
        # KERNEL stylesheet (not the layout skin) so they retrofit into
        # existing decks via the versioned upsert.
        "agenda": {
            "label": "Agenda",
            "description": "A heading over the run of topics.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section class="slide" data-arrange="agenda">
  <h2 data-block="heading" data-block-id="t1">Agenda</h2>
  <div data-slot="main">
    <ul data-block="checklist" data-block-id="b1"><li>First topic</li><li>Second topic</li><li>Third topic</li></ul>
  </div>
</section>""",
        },
        "big-number": {
            "label": "Big number",
            "description": "One headline metric, front and center.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section class="slide" data-arrange="big-number">
  <p class="kicker" data-block="heading" data-block-id="k1">The headline number</p>
  <div data-slot="main">
    <div data-block="metrics" data-block-id="b1"><div class="metric"><strong>42%</strong><span>what it measures</span></div></div>
  </div>
</section>""",
        },
        "full-bleed": {
            "label": "Full-bleed image",
            "description": "One cited image filling the whole slide.",
            "grain": "page",
            "slots": [{"name": "media", "role": "media"}],
            "fragment": """<section class="slide" data-arrange="full-bleed">
  <div data-slot="media"></div>
</section>""",
        },
        "closing": {
            "label": "Closing",
            "description": "A full-tone thank-you slide with the next step.",
            "grain": "page",
            "slots": [{"name": "heading", "role": "heading"}],
            "fragment": """<section class="slide" data-arrange="closing" data-tone="inverse">
  <p class="kicker" data-block="heading" data-block-id="k1">Thank you</p>
  <h1 data-block="heading" data-block-id="t1">The closing line.</h1>
  <p data-block="heading" data-block-id="f1">Contact · next step</p>
</section>""",
        },
    },
    "document": {
        "title-lede": {
            "label": "Title + lede",
            "description": "A title and one-line lede, then content.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section data-arrange="title-lede">
  <h2 data-block="heading" data-block-id="t1">Section title</h2>
  <p class="lede" data-block="heading" data-block-id="l1">One line on what this section is for.</p>
  <div data-slot="main"></div>
</section>""",
        },
        "two-column": {
            "label": "Two column",
            "description": "A heading over two side-by-side regions.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}, {"name": "side", "role": "flow"}],
            "fragment": """<section data-arrange="two-column">
  <h2 data-block="heading" data-block-id="t1">Section title</h2>
  <div class="cols">
    <div class="col" data-slot="main"></div>
    <div class="col" data-slot="side"></div>
  </div>
</section>""",
        },
        # ADR-456 Wave 1 — the document rows.
        "checklist-section": {
            "label": "Checklist",
            "description": "A heading over a list of items or steps.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section data-arrange="checklist-section">
  <h2 data-block="heading" data-block-id="t1">Section title</h2>
  <div data-slot="main">
    <ul data-block="checklist" data-block-id="b1"><li>First item</li><li>Second item</li></ul>
  </div>
</section>""",
        },
        "metrics-band": {
            "label": "Metrics",
            "description": "A heading over a row of headline numbers.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section data-arrange="metrics-band">
  <h2 data-block="heading" data-block-id="t1">Section title</h2>
  <div data-slot="main">
    <div data-block="metrics" data-block-id="b1"><div class="metric"><strong>42%</strong><span>label</span></div></div>
  </div>
</section>""",
        },
    },
    "article": {
        "section": {
            "label": "Section",
            "description": "A subheading and flowing prose.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section data-arrange="section">
  <h2 data-block="heading" data-block-id="t1">Section heading</h2>
  <div data-slot="main"></div>
</section>""",
        },
        "pull-quote": {
            "label": "Pull quote",
            "description": "A prose region with an offset pull quote aside.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section data-arrange="pull-quote">
  <blockquote data-block="quote" data-block-id="q1"><p>The line worth pulling.</p></blockquote>
  <div data-slot="main"></div>
</section>""",
        },
        "lead-image": {
            "label": "Lead image",
            "description": "A cited image leading into prose.",
            "grain": "page",
            "slots": [{"name": "media", "role": "media"}, {"name": "main", "role": "flow"}],
            "fragment": """<section data-arrange="lead-image">
  <div data-slot="media"></div>
  <div data-slot="main"></div>
</section>""",
        },
    },
    # ADR-456 D4 (Wave 3): the page layout's band family — the builder-class
    # section stack (hero · content · features · testimonial · CTA · footer).
    "page": {
        "hero": {
            "label": "Hero",
            "description": "The headline band — kicker, promise, tagline, button.",
            "grain": "page",
            "slots": [{"name": "heading", "role": "heading"}],
            "fragment": """<section data-arrange="hero">
  <p class="kicker" data-block="heading" data-block-id="k1">Kicker</p>
  <h1 data-block="heading" data-block-id="t1">The headline promise.</h1>
  <p class="tagline" data-block="heading" data-block-id="s1">One sentence expanding on it.</p>
  <p data-block="button" data-block-id="c1"><a href="https://…">Call to action</a></p>
</section>""",
        },
        "content": {
            "label": "Content",
            "description": "A heading with content below.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section data-arrange="content">
  <h2 data-block="heading" data-block-id="t1">Section title</h2>
  <div data-slot="main"></div>
</section>""",
        },
        "feature-grid": {
            "label": "Feature grid",
            "description": "A heading over three side-by-side features.",
            "grain": "page",
            "slots": [
                {"name": "a", "role": "flow"},
                {"name": "b", "role": "flow"},
                {"name": "c", "role": "flow"},
            ],
            "fragment": """<section data-arrange="feature-grid">
  <h2 data-block="heading" data-block-id="t1">Section title</h2>
  <div class="cols">
    <div class="col" data-slot="a"><div data-block="prose" data-block-id="b1"><h3>Feature</h3><p>One sentence on it.</p></div></div>
    <div class="col" data-slot="b"><div data-block="prose" data-block-id="b2"><h3>Feature</h3><p>One sentence on it.</p></div></div>
    <div class="col" data-slot="c"><div data-block="prose" data-block-id="b3"><h3>Feature</h3><p>One sentence on it.</p></div></div>
  </div>
</section>""",
        },
        "testimonial": {
            "label": "Testimonial",
            "description": "One centered quote with attribution.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section data-arrange="testimonial">
  <div data-slot="main">
    <blockquote data-block="quote" data-block-id="q1"><p>What a customer said.</p><cite>Name, role</cite></blockquote>
  </div>
</section>""",
        },
        "cta": {
            "label": "Call to action",
            "description": "A closing ask — heading and button, centered.",
            "grain": "page",
            "slots": [{"name": "heading", "role": "heading"}],
            "fragment": """<section data-arrange="cta" data-tone="accent">
  <h2 data-block="heading" data-block-id="t1">The closing ask.</h2>
  <p data-block="button" data-block-id="c1"><a href="https://…">Call to action</a></p>
</section>""",
        },
        "footer": {
            "label": "Footer",
            "description": "A quiet closing band — fine print, contact.",
            "grain": "page",
            "slots": [{"name": "main", "role": "flow"}],
            "fragment": """<section data-arrange="footer">
  <div data-slot="main">
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
# `applies` vocabulary (the FE gates controls by it):
#   block         — any [data-block]
#   media         — media blocks only (MEDIA_BLOCK_KINDS)
#   page          — any [data-arrange] page/slide
#   page-multicol — pages whose arrangement has ≥2 flow slots
#   page-deck     — deck slides only
#   document      — the artifact ROOT (<html>), all layouts (ADR-455)
#   document-flow — the artifact root, document/article only (a deck is a
#                   fixed 16:9 stage and a page is full-width bands — measure
#                   applies to neither)
#   document-deck — the artifact root, deck only (slide numbers, ADR-456)
#   page-bg       — a page/section carrying a cited background image
#                   (data-ref-kind="background" on the element, ADR-456 W3)
# ---------------------------------------------------------------------------

#: Block kinds the media-grain tokens (height/fit) apply to.
MEDIA_BLOCK_KINDS = {"figure", "chart", "gallery"}

STUDIO_TOKENS: dict[str, dict] = {
    "align": {
        "label": "Align",
        "applies": ["block"],
        "values": [
            {"value": "start", "label": "Left"},
            {"value": "center", "label": "Center"},
            {"value": "end", "label": "Right"},
        ],
        "description": "content alignment within the block's region",
    },
    "tone": {
        "label": "Tone",
        "applies": ["block", "page"],
        "values": [
            {"value": "accent", "label": "Accent"},
            {"value": "muted", "label": "Muted"},
            {"value": "inverse", "label": "Inverse"},
        ],
        "description": "emphasis via the palette variables — never raw color",
    },
    "height": {
        "label": "Height",
        "applies": ["media"],
        "values": [
            {"value": "s", "label": "Small"},
            {"value": "m", "label": "Medium"},
            {"value": "l", "label": "Large"},
        ],
        "description": "image height preset on a figure/chart block",
    },
    "fit": {
        "label": "Fit",
        "applies": ["media"],
        "values": [
            {"value": "cover", "label": "Fill"},
            {"value": "contain", "label": "Fit"},
        ],
        "description": "how the image fills its box",
    },
    "ratio": {
        "label": "Columns",
        "applies": ["page-multicol"],
        "values": [
            {"value": "2-1", "label": "Wide left"},
            {"value": "1-2", "label": "Wide right"},
        ],
        "description": "column weighting on a multi-column page (absence = even)",
    },
    "valign": {
        "label": "Vertical align",
        "applies": ["page-deck"],
        "values": [
            {"value": "start", "label": "Top"},
            {"value": "end", "label": "Bottom"},
        ],
        "description": "where the slide's content sits (absence = centered)",
    },
    # ADR-456 Wave 1: breathing room on a page/section — presets, never pixels.
    "pad": {
        "label": "Spacing",
        "applies": ["page"],
        "values": [
            {"value": "s", "label": "Tight"},
            {"value": "l", "label": "Airy"},
        ],
        "description": "the page/section's breathing room (absence = the layout default)",
    },
    # ADR-456 W3: the cited-background pair — a page/section wearing a
    # data-ref-kind="background" citation styles it with these, never inline.
    "scrim": {
        "label": "Scrim",
        "applies": ["page-bg"],
        "values": [
            {"value": "dark", "label": "Dark"},
            {"value": "light", "label": "Light"},
        ],
        "description": "a legibility overlay on the page's cited background image",
    },
    "bg-pos": {
        "label": "Focus",
        "applies": ["page-bg"],
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
        "applies": ["document"],
        "values": [
            {"value": "serif", "label": "Serif"},
            {"value": "sans", "label": "Sans"},
            {"value": "mono", "label": "Mono"},
        ],
        "description": "the artifact's typeface family (absence = the layout/design-system default)",
    },
    "measure": {
        "label": "Width",
        "applies": ["document-flow"],
        "values": [
            {"value": "wide", "label": "Wide"},
        ],
        "description": "the content column width on a document/article (absence = the layout default)",
    },
    # ADR-456 Wave 1: slide numbers — CSS counters, script-free, opt-in.
    "pagenum": {
        "label": "Slide numbers",
        "applies": ["document-deck"],
        "values": [
            {"value": "on", "label": "On"},
        ],
        "description": "slide numbers in the corner of every slide (deck; absence = off)",
    },
}

#: The kernel CSS that interprets tokens — carried by every artifact in the
#: MARKED, VERSIONED kernel style element (D2). Themed through the same
#: custom properties the layouts declare and a design system may override
#: (cascade: unmarked layout style < data-kernel < data-skin).
STUDIO_KERNEL_CSS = """
/* Block-kind + arrangement CSS (ADR-456 W1) — lives in the KERNEL element,
   not the layout skin, so new kinds/arrangements retrofit into existing
   artifacts via the versioned upsert. Token rules come LAST in this sheet so
   a token wins at equal specificity. */
hr[data-block="divider"] { border: 0; border-top: 1px solid #ddd; margin: 2.25rem 0; }
details[data-block="toggle"] { margin: 1rem 0; border: 1px solid #ddd;
  border-radius: var(--radius, 6px); padding: 0.5rem 0.9rem; }
details[data-block="toggle"] summary { cursor: pointer; font-weight: 600; }
details[data-block="toggle"][open] summary { margin-bottom: 0.5rem; }
p[data-block="button"] { margin: 1.5rem 0; }
p[data-block="button"] a { display: inline-block; background: var(--accent, #b4540a);
  color: var(--paper, #fdfcfa); padding: 0.55rem 1.2rem;
  border-radius: var(--radius, 6px); text-decoration: none; font-weight: 600; }
div[data-block="gallery"] { display: grid; gap: 0.75rem; margin: 1.5rem 0;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); }
div[data-block="gallery"] figure { margin: 0; }
div[data-block="gallery"] img { width: 100%; aspect-ratio: 4 / 3;
  object-fit: cover; border-radius: var(--radius, 4px); }
div[data-block="gallery"] figcaption { font-size: 0.75rem; }
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
  font-style: italic; font-size: 1.3rem; }
[data-arrange="footer"] { font-size: 0.85rem; color: var(--muted, #6b6b6b); }
.slide[data-arrange="full-bleed"] { padding: 0; }
.slide[data-arrange="full-bleed"] [data-slot="media"] { flex: 1; display: flex; min-height: 0; }
.slide[data-arrange="full-bleed"] figure { flex: 1; margin: 0; min-width: 0; }
.slide[data-arrange="full-bleed"] img { width: 100%; height: 100%;
  object-fit: cover; max-height: none; }
[data-arrange="big-number"] div[data-block="metrics"] { justify-content: center;
  text-align: center; }
[data-arrange="big-number"] div[data-block="metrics"] .metric strong {
  font-size: 4rem; line-height: 1.1; }
[data-arrange="big-number"] div[data-block="metrics"] .metric span { font-size: 1rem; }
/* Property tokens (ADR-453) — interpreted here, themed by custom properties. */
[data-align="center"] { text-align: center; }
[data-align="center"] img { margin-inline: auto; }
[data-align="end"] { text-align: right; }
[data-align="end"] img { margin-inline-start: auto; }
[data-tone="accent"] { color: var(--accent, #b4540a); }
[data-tone="muted"] { color: var(--muted, #6b6b6b); }
[data-block][data-tone="inverse"] { background: var(--ink, #1a1a1a);
  color: var(--paper, #fdfcfa); padding: 1rem 1.25rem; border-radius: 6px; }
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
.slide[data-valign="start"] { justify-content: flex-start; }
.slide[data-valign="end"] { justify-content: flex-end; }
.slide[data-pad="s"] { padding: 2rem 2.5rem; }
.slide[data-pad="l"] { padding: 4.5rem 5.5rem; }
[data-arrange][data-pad="s"]:not(.slide) { padding-block: 0.25rem; }
[data-arrange][data-pad="l"]:not(.slide) { padding-block: 2.5rem; }
/* Document-grain tokens (ADR-455) — on the artifact root. */
html[data-font="serif"] body { font-family: Georgia, 'Times New Roman', serif; }
html[data-font="sans"] body { font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; }
html[data-font="mono"] body { font-family: ui-monospace, 'SF Mono', Menlo, monospace; }
html[data-measure="wide"] main, html[data-measure="wide"] article { max-width: 64rem; }
/* Slide numbers (ADR-456 W1) — CSS counters, opt-in on the deck root. */
html[data-pagenum="on"] body { counter-reset: slide; }
html[data-pagenum="on"] .slide { counter-increment: slide; position: relative; }
html[data-pagenum="on"] .slide::after { content: counter(slide); position: absolute;
  right: 1.25rem; bottom: 0.9rem; font-size: 0.7rem; color: var(--muted, #6b6b6b); }
/* Responsive stacking (ADR-456 W1): document/article multi-column bands stack
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

#: Bump when STUDIO_KERNEL_CSS changes shape — the FE upserts any artifact
#: carrying an older data-kernel-v on its next mechanical op (the retrofit).
#: v2: document-grain font/measure rules (ADR-455).
#: v3: Wave-1 block/arrangement rules + pad/pagenum tokens + responsive
#:     stacking (ADR-456) — block/arrangement CSS lives HERE, not the layout
#:     skin, precisely so this retrofit carries it into existing artifacts.
#: v4: Wave-3 (ADR-456) — cited page backgrounds (data-ref-kind="background"
#:     + scrim/bg-pos), the generic non-slide .cols (document/article
#:     two-column made real), page-band accents, --radius adoption.
# v5 (2026-07-15): the .cols carve-out retired — the kernel owns the column band
# for every layout. A pre-ADR-444 deck's baked skin has no `.slide .cols`, and
# the kernel's `:not(.slide)` rule excluded it, so its two-column slides stacked
# silently. Bumping the version is what makes the retrofit reach them.
STUDIO_KERNEL_CSS_VERSION = 5


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


#: Every layout's scaffolded h1 text — the ONLY strings `set_artifact_title`
#: may overwrite. DERIVED from the registry, so editing a scaffold can never
#: silently orphan this list and start overwriting a member's authored title.
_SCAFFOLD_TITLES: frozenset[str] = frozenset(
    re.sub(r"<[^>]+>", "", m.group(1)).strip()
    for m in (
        re.search(r"<h1\b[^>]*>(.*?)</h1>", lay["scaffold"], re.S)
        for lay in STUDIO_LAYOUTS.values()
    )
    if m
)


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


def build_skeleton(layout: str, title: str | None = None) -> str:
    """Assemble a new artifact's first revision: layout × starter blocks.

    The skeleton is self-describing (``data-template`` on the root; blocks
    annotated ``data-block`` + ``data-block-id``) and script-free (the canvas
    strips executables anyway — defense in depth).

    `title` (the name the member typed at creation) titles the artifact as well
    as the file — see `set_artifact_title`. Absent, the placeholder stands.
    """
    lay = STUDIO_LAYOUTS[layout]
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

def _blocks_grammar() -> str:
    return "\n".join(
        f"  - {kind} — {b['description']}\n    e.g. {b['markup']}"
        for kind, b in STUDIO_BLOCKS.items()
    )


def _arrangements_grammar(template: str) -> str:
    """The arrangement roster for a layout — the composition options the lane
    can author or re-lay to (ADR-447). Grammar, not schema."""
    rows = STUDIO_ARRANGEMENTS.get(template, {})
    if not rows:
        return "  (no named arrangements for this layout — a single flow.)"
    return "\n".join(
        f"  - {slug} — {a['description']} (slots: "
        + ", ".join(s["name"] for s in a["slots"])
        + ")"
        for slug, a in rows.items()
    )


def _tokens_grammar() -> str:
    """The property-token roster (ADR-453) — one line per family, derived from
    the registry so the posture and the Design tab never drift."""
    return "\n".join(
        f'  - data-{key}="' + "|".join(v["value"] for v in t["values"]) + f'" — {t["description"]}'
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
  explicitly asks for. Small patches keep the revision history legible.
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

## Arrangements (where content goes on a page/section)
Each page or section carries an ARRANGEMENT — data-arrange="<slug>" on the
page element (a deck slide, or a document/article <section>), with
data-slot="<name>" regions that hold blocks. The arrangement is the
composition (grids, columns, slots); the block is the content; keep them
distinct. When you author a new page/section, annotate it with data-arrange
and give its content regions data-slot. When you re-lay a page to a different
arrangement, move existing blocks INTACT (ids preserved) into the new
arrangement's slots — heading blocks anchor the page and are not swept. The
member also re-arranges directly with the toolbar; treat the current
arrangement as truth and re-read before editing. Arrangements for this
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

## Citing workspace objects (references, never copies)
- Embed a workspace file by REFERENCE, resolved live at render time:
  `<img data-ref="operation/brand/logo.png" data-ref-rev="" alt="...">` for
  images, `<div data-ref="operation/metrics/summary.csv" data-ref-kind="table"></div>`
  for a CSV rendered as a table. NEVER paste base64 or copy a cited file's
  bytes/contents into the artifact — the reference IS the point: when the
  source changes, the artifact stays current.
- Assets that belong to this artifact live beside it and are cited RELATIVE
  with a leading `./` (`data-ref="./assets/hero.png"` — resolved against the
  artifact's folder, so the project moves as a unit); shared workspace objects
  are cited by their workspace path (`data-ref="operation/..."`) and stay
  where they live — do not move or duplicate them.
- `data-ref-rev` is the citation's pin: when you have the cited file's head
  revision id (from reading it this turn), stamp it there; otherwise leave it
  empty. The pin is the fallback if the path later moves or is deleted.
- Never edit a cited object's content inside the artifact. If the member asks
  to change a cited source, edit the SOURCE file itself.
- A page/section can wear a CITED BACKGROUND image: set data-ref="<image path>"
  and data-ref-kind="background" (plus the data-ref-rev pin) on the page
  element itself — the canvas renders it as a cover background. Pair it with
  data-scrim="dark|light" for text legibility and data-bg-pos="top|bottom" for
  focus. Never write inline style backgrounds — the citation IS the background.
- You can CREATE visual assets too — vector graphics are plain text: author
  charts, diagrams, icons, and illustrations as `.svg` files into `./assets/`
  beside the artifact (WriteFile), then cite them (`data-ref="./assets/chart.svg"`).
  Prefer an authored SVG over describing a picture you cannot make.

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
    known = STUDIO_LAYOUTS.get(slug)
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


def artifact_name(path: str) -> str:
    """The artifact's operator-facing name — the titleized MEANING FOLDER.

    `operation/ir-deck-v3/deck.html` → "IR deck v3" (as the member typed it at
    creation; the modal slugified it into the folder). DP33: the namespace
    carries meaning, so the name needs no storage — it is already there.

    Degrades honestly: an artifact sitting directly in the region with no
    meaning folder falls back to its titleized stem rather than inventing one.
    """
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
    """Heading texts (h1/h2) in document order — the artifact's outline."""
    heads = re.findall(
        r"<h([12])[^>]*>(.*?)</h\1>", artifact_content or "", flags=re.DOTALL
    )
    out = []
    for level, raw in heads[:limit]:
        text = re.sub(r"<[^>]+>", "", raw).strip()
        if text:
            out.append(("  " if level == "2" else "") + text)
    return out


def build_studio_posture(artifact_path: str, artifact_content: str) -> str:
    """The bound lane's authoring posture — pure, composed per turn.

    ``artifact_content`` is the artifact's CURRENT head (the runner reads it
    fresh each turn — derived, never stored). An empty/missing artifact still
    yields a posture: the lane can (re)create the file at the bound path.
    """
    template = extract_template(artifact_content) or "document"
    layout = STUDIO_LAYOUTS.get(template, STUDIO_LAYOUTS["document"])
    outline = extract_outline(artifact_content)
    outline_section = (
        "- Current outline:\n" + "\n".join(f"  {h}" for h in outline)
        if outline
        else "- The artifact is currently empty or missing — create it at the "
             "bound path from the member's direction."
    )
    return _POSTURE_FRAME.format(
        path=artifact_path,
        template=template,
        outline_section=outline_section,
        blocks_grammar=_blocks_grammar(),
        arrangements_grammar=_arrangements_grammar(template),
        tokens_grammar=_tokens_grammar(),
        flow=layout["flow"],
    )
