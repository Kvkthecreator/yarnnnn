"""The Studio — kernel constants + posture for the first authoring app (ADR-440).

This module is the Studio's PROGRAM half, housed as code per ADR-440 D6
("apps bring program, not substrate" — ADR-414 D2 precedent): the template
skeletons a new artifact starts from, the per-template grammar, and the
posture overlay a BOUND lane receives at turn time. Nothing here is ever
seeded into a workspace as a file; the only substrate the Studio produces
is the artifacts members author.

Consumers:
- ``routes/studio.py`` — template listing + artifact creation (skeletons).
- ``services/lane_runner.py`` — ``build_studio_posture`` composed into the
  conventions projection when a lane carries an ``artifact_path`` binding
  (ADR-440 D3). Pure function: the runner does the I/O, this module never
  touches the DB.

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
# Templates (ADR-440 D4) — Document · Deck · Article
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
""".strip("\n")

_DOCUMENT_SKELETON = f"""<!doctype html>
<html data-template="document">
<head>
<meta charset="utf-8">
<title>Untitled document</title>
<style>
{_SHARED_CSS}
    main {{ max-width: 46rem; margin: 0 auto; padding: 3rem 1.5rem; }}
    h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
    section {{ margin-top: 2rem; }}
    section h2 {{ font-size: 1.3rem; margin-bottom: 0.75rem; }}
</style>
</head>
<body>
<main>
  <h1>Untitled document</h1>
  <p class="lede">One sentence on what this document is for.</p>
  <section>
    <h2>First section</h2>
    <p>Start here.</p>
  </section>
</main>
</body>
</html>
"""

_DECK_SKELETON = f"""<!doctype html>
<html data-template="deck">
<head>
<meta charset="utf-8">
<title>Untitled deck</title>
<style>
{_SHARED_CSS}
    .slide {{ min-height: 92vh; padding: 4rem 3.5rem; display: flex;
             flex-direction: column; justify-content: center;
             border-bottom: 2px solid #e8e4de; page-break-after: always; }}
    .slide h1 {{ font-size: 2.6rem; max-width: 34rem; }}
    .slide h2 {{ font-size: 1.9rem; margin-bottom: 1.25rem; }}
    .slide .kicker {{ color: var(--accent); font-size: 0.85rem;
                     letter-spacing: 0.08em; text-transform: uppercase;
                     margin-bottom: 1rem; }}
    .slide p {{ max-width: 36rem; }}
</style>
</head>
<body>
<section class="slide">
  <p class="kicker">Untitled deck</p>
  <h1>The one-line thesis goes here.</h1>
  <p>Subtitle or framing sentence.</p>
</section>
<section class="slide">
  <h2>First point</h2>
  <p>One idea per slide.</p>
</section>
</body>
</html>
"""

_ARTICLE_SKELETON = f"""<!doctype html>
<html data-template="article">
<head>
<meta charset="utf-8">
<title>Untitled article</title>
<style>
{_SHARED_CSS}
    article {{ max-width: 42rem; margin: 0 auto; padding: 3.5rem 1.5rem; }}
    header {{ margin-bottom: 2.5rem; }}
    header h1 {{ font-size: 2.2rem; margin-bottom: 0.75rem; }}
    header .subtitle {{ font-size: 1.15rem; color: var(--muted); }}
    header .byline {{ font-size: 0.85rem; color: var(--muted); margin-top: 1rem;
                     letter-spacing: 0.02em; }}
    article > p {{ margin: 1rem 0; }}
</style>
</head>
<body>
<article>
  <header>
    <h1>Untitled article</h1>
    <p class="subtitle">The one-sentence promise to the reader.</p>
    <p class="byline">Byline · Date</p>
  </header>
  <p>Opening paragraph.</p>
</article>
</body>
</html>
"""

_TEMPLATE_GRAMMARS = {
    "document": (
        "- Structure: one <main> holding an <h1> title, a short lede <p>, then "
        "<section> blocks each led by an <h2>. Internal working document — "
        "clarity over polish."
    ),
    "deck": (
        "- Structure: each slide is <section class=\"slide\">. The first slide is "
        "the title slide (kicker + h1 thesis); every other slide is one idea, led "
        "by an <h2>. Add slides as siblings; never nest slides. Keep slide text "
        "sparse — a deck is spoken over, not read."
    ),
    "article": (
        "- Structure: one <article> with a <header> (h1 title, .subtitle promise, "
        ".byline) followed by flowing prose <p> blocks; use <figure> + "
        "<figcaption> for cited images. This is the publishing shape — written to "
        "be read by someone outside the workspace."
    ),
}

#: The registry the routes + posture read. Slug → {label, description, skeleton}.
STUDIO_TEMPLATES: dict[str, dict[str, str]] = {
    "document": {
        "label": "Document",
        "description": "An internal working document — sections under one title.",
        "skeleton": _DOCUMENT_SKELETON,
    },
    "deck": {
        "label": "Deck",
        "description": "A slide deck — one idea per slide, spoken over.",
        "skeleton": _DECK_SKELETON,
    },
    "article": {
        "label": "Article",
        "description": "A publishing shape — blog post, essay, announcement.",
        "skeleton": _ARTICLE_SKELETON,
    },
}


# ---------------------------------------------------------------------------
# Posture (ADR-440 D3) — the bound lane's authoring overlay, composed at
# turn time. PURE: caller supplies the artifact's current content.
# ---------------------------------------------------------------------------

_POSTURE_FRAME = """
## Studio: you are authoring one artifact
This lane is bound to `{path}` (template: {template}). Your job is to author
and revise THAT artifact; the member sees it re-render beside this chat after
every write.
{outline_section}
- PATCH, don't rewrite: prefer EditFile with exact old/new fragments for
  changes; reserve WriteFile (full replace) for re-drafts the member
  explicitly asks for. Small patches keep the revision history legible.
- The artifact is self-contained HTML: inline CSS only, no <script> and no
  external URLs — the canvas renders it fully sandboxed (scripts never run),
  and everything it shows must come from the workspace.
{grammar}

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

## Style
Match the artifact's existing voice and CSS. If the workspace carries design
conventions (e.g. operation/CONVENTIONS.md), respect them.
""".rstrip()


def extract_template(artifact_content: str) -> Optional[str]:
    """The artifact's declared template, from its data-template root attr."""
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
    grammar = _TEMPLATE_GRAMMARS.get(template, _TEMPLATE_GRAMMARS["document"])
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
        grammar=grammar,
    )
