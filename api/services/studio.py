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

STUDIO_LAYOUTS: dict[str, dict[str, str]] = {
    "document": {
        "label": "Document",
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
  <h1>Untitled document</h1>
  <p class="lede">One sentence on what this document is for.</p>
  <section data-block="prose" data-block-id="b1">
    <h2>First section</h2>
    <p>Start here.</p>
  </section>
</main>""",
    },
    "deck": {
        "label": "Deck",
        "description": "A slide deck — one idea per slide, spoken over.",
        "flow": (
            "each slide is <section class=\"slide\"> (a flow container, not a "
            "block); blocks live INSIDE slides. The first slide is the title "
            "slide (kicker + h1 thesis); every other slide is one idea led by an "
            "<h2>. Keep slide text sparse — a deck is spoken over, not read."
        ),
        "skin": """
    .slide { min-height: 92vh; padding: 4rem 3.5rem; display: flex;
             flex-direction: column; justify-content: center;
             border-bottom: 2px solid #e8e4de; page-break-after: always; }
    .slide h1 { font-size: 2.6rem; max-width: 34rem; }
    .slide h2 { font-size: 1.9rem; margin-bottom: 1.25rem; }
    .slide .kicker { color: var(--accent); font-size: 0.85rem;
                     letter-spacing: 0.08em; text-transform: uppercase;
                     margin-bottom: 1rem; }
    .slide p { max-width: 36rem; }
    .slide .cols { display: flex; gap: 2.5rem; align-items: flex-start; }
    .slide .col { flex: 1; min-width: 0; }
""".strip("\n"),
        "scaffold": """<section class="slide">
  <p class="kicker">Untitled deck</p>
  <h1>The one-line thesis goes here.</h1>
  <p>Subtitle or framing sentence.</p>
</section>
<section class="slide">
  <div data-block="prose" data-block-id="b1">
    <h2>First point</h2>
    <p>One idea per slide.</p>
  </div>
</section>""",
    },
    "article": {
        "label": "Article",
        "description": "A publishing shape — blog post, essay, announcement.",
        "flow": (
            "one <article> with a <header> (h1 title, .subtitle promise, .byline "
            "— the header is a flow container, not a block) followed by blocks of "
            "flowing prose; figures carry cited images. Written to be read by "
            "someone outside the workspace."
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
    <h1>Untitled article</h1>
    <p class="subtitle">The one-sentence promise to the reader.</p>
    <p class="byline">Byline · Date</p>
  </header>
  <div data-block="prose" data-block-id="b1">
    <p>Opening paragraph.</p>
  </div>
</article>""",
    },
}


# ---------------------------------------------------------------------------
# Containers (ADR-444) — the slide-master grain. Per-LAYOUT structural
# arrangements the member applies to a SELECTED container (a deck slide) or
# inserts fresh — deterministic, member-attributed operations, no LLM.
# `data-container` names the arrangement; `data-slot` regions receive the
# container's blocks on a deterministic reflow (first slot takes existing
# blocks; other slots keep their placeholders).
# ---------------------------------------------------------------------------

STUDIO_CONTAINERS: dict[str, dict[str, dict[str, str]]] = {
    "deck": {
        "title": {
            "label": "Title slide",
            "description": "Kicker, thesis headline, framing line.",
            "fragment": """<section class="slide" data-container="title">
  <p class="kicker">Kicker</p>
  <h1>The headline goes here.</h1>
  <p>Framing sentence.</p>
</section>""",
        },
        "content": {
            "label": "Content",
            "description": "A heading with content below.",
            "fragment": """<section class="slide" data-container="content">
  <h2>Slide title</h2>
  <div data-slot="main"></div>
</section>""",
        },
        "two-column": {
            "label": "Two column",
            "description": "A heading over two side-by-side regions.",
            "fragment": """<section class="slide" data-container="two-column">
  <h2>Slide title</h2>
  <div class="cols">
    <div class="col" data-slot="main"></div>
    <div class="col" data-slot="side"><p>Second column.</p></div>
  </div>
</section>""",
        },
        "quote": {
            "label": "Quote",
            "description": "One centered pull quote.",
            "fragment": """<section class="slide" data-container="quote">
  <div data-slot="main">
    <blockquote data-block="quote" data-block-id="b1"><p>The quote.</p><cite>Attribution</cite></blockquote>
  </div>
</section>""",
        },
    },
    # document/article containers arrive as rows here when demanded — the
    # registry admits them with zero mechanism change.
    "document": {},
    "article": {},
}


def build_skeleton(layout: str) -> str:
    """Assemble a new artifact's first revision: layout × starter blocks.

    The skeleton is self-describing (``data-template`` on the root; blocks
    annotated ``data-block`` + ``data-block-id``) and script-free (the canvas
    strips executables anyway — defense in depth).
    """
    lay = STUDIO_LAYOUTS[layout]
    title = f"Untitled {lay['label'].lower()}"
    return f"""<!doctype html>
<html data-template="{layout}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{_SHARED_CSS}
{lay['skin']}
</style>
</head>
<body>
{lay['scaffold']}
</body>
</html>
"""


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


_POSTURE_FRAME = """
## Studio: you are authoring one artifact
This lane is bound to `{path}` (layout: {template}). Your job is to author
and revise THAT artifact; the member sees it re-render beside this chat after
every write.
{outline_section}
- PATCH, don't rewrite: prefer EditFile with exact old/new fragments for
  changes; reserve WriteFile (full replace) for re-drafts the member
  explicitly asks for. Small patches keep the revision history legible.
- The member can also insert blocks and slides DIRECTLY (operator-authored
  revisions land between your turns): always re-read before editing, treat
  the current content as truth, and never renumber or remove existing
  data-block-id values you didn't create.
- The artifact is self-contained HTML: inline CSS only, no <script> and no
  external URLs — the canvas renders it fully sandboxed (scripts never run),
  and everything it shows must come from the workspace.

## Blocks (the component grammar)
Compose content as BLOCKS: each top-level content unit carries
data-block="<kind>" plus a short unique data-block-id (e.g. "b7") that you
stamp when creating a block and PRESERVE when editing it. Patch WITHIN block
boundaries — one block per edit where possible — and address blocks by their
id when the member selects one. Content that fits no kind may stay
unannotated; the grammar teaches, it never rejects. Kinds:
{blocks_grammar}

## Layout
This artifact's layout is {template}: {flow}
When the member asks to change the layout: preserve every block and its
data-block-id, replace the <style> skin and the flow structure per the
target layout's grammar, and update data-template on the root. A layout
change is an ordinary edit — versioned and revertible like any other.

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
        flow=layout["flow"],
    )
