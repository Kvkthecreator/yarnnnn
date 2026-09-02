"""
Blogger — the publish medium's app (ADR-627).

The OUTWARD type returns, under the app that owns its future. ADR-505 D2
merged `article` + `page` into one band-first type ("HTML for someone outside
the workspace"); ADR-599 D5 deleted it with its future named as this arc. The
row below is that type resurrected as `post` — same grammar, same band
family, article-first scaffold — with its `app` declaration naming Blogger.

The retired outward slugs (`article` · `page` · `web`) re-alias to `post` in
`RETIRED_LAYOUT_SLUGS`, so the legacy outward artifacts resolve again and are
never rewritten (ADR-481 D5: legacy renders, never migrates).

BAND-FIRST, NEVER OBJECT-FIRST (ADR-505 D3, unchanged). No x/y/z here, ever:
a published page has a VIEWPORT, not a frame (ADR-461 D4), so a percentage
position means something different at every width. The reference class agrees
— Medium, Substack, Ghost ship zero positional control. Geometry is
unreachable here STRUCTURALLY: `block-staged` tests `.slide` ancestry and a
band is not a slide.

PUBLISHING OUTWARD IS NOT HERE (ADR-627 D5 / ADR-628). Blogger v1's output is
workspace artifacts; the publish act is a third disposition of platform reach
with its own ADR. Nothing in this module may reach an external platform.
"""

#: The slug of the document type Blogger owns. Opaque + stable (ADR-459 D1).
POST_SLUG = "post"

BLOGGER_LAYOUTS: dict[str, dict[str, str]] = {
    POST_SLUG: {
        "app": "blogger",
        "label": "Post",
        "mode": "paged",
        "description": "A published piece — blog post, essay, landing page.",
        "flow": (
            "one <main> of full-width section BANDS, each <section data-arrange=…> "
            "stacked vertically. A blog post or essay opens with a `prose-header` "
            "band (kicker/h1/standfirst/byline) and continues in `prose` and "
            "`content` bands; a landing page opens with a `hero` (kicker + h1 "
            "promise + tagline + button), stacks feature/testimonial bands, and "
            "closes on a call-to-action. Band content centers itself in a reading "
            "column; a band may wear a cited background image (data-ref + "
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
        # ARTICLE-FIRST scaffold — the one place `post` diverges from the
        # deleted `web` row, whose scaffold opened as a landing page (hero +
        # content). Blogger's member writes posts; a landing page is still one
        # band-pick away (`hero`), which is exactly the ADR-505 D2 point: the
        # difference is which bands you stack, not which type you chose.
        "scaffold": """<main>
  <section data-arrange="prose-header">
    <div data-area="main" data-area-role="body">
      <p class="kicker" data-block="heading" data-block-id="k1">Untitled post</p>
      <h1 data-block="heading" data-block-id="t1">The title of the piece.</h1>
      <p class="standfirst" data-block="heading" data-block-id="s1">The one-sentence promise to the reader.</p>
      <p class="byline" data-block="heading" data-block-id="y1">Byline · Date</p>
    </div>
  </section>
  <section data-arrange="prose">
    <div data-area="main" data-area-role="body">
      <div data-block="prose" data-block-id="b1"><p>Start writing.</p></div>
    </div>
  </section>
</main>""",
    },
}


# The band family — ADR-456 D4's builder-class section stack, widened by
# ADR-505 D2 with the two long-form bands, deleted by ADR-599 D5, resurrected
# here VERBATIM in structure (registry key `post`; the fragments are grammar
# the kernel CSS still renders — deletion stopped creation, never reading).
BLOGGER_ARRANGEMENTS: dict[str, dict[str, dict]] = {
    POST_SLUG: {
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


# Blogger registers its document type with the shared machinery (ADR-472 D2)
# and its AI configuration with the app registry (ADR-562 D2). The builders
# (skeleton, posture, artifact-kind) are kernel code every authoring app
# consumes — registration is how Blogger reaches them. The pane job overlay is
# the shared studio posture (ADR-606 D3): the app is Studio-parameterized, so
# the studio job (block grammar + design-system skin contract) IS its job.
from services.authoring import (  # noqa: E402  (registration side-effect)
    register_app,
    register_layouts,
    studio_pane_posture,
)

register_layouts(BLOGGER_LAYOUTS, BLOGGER_ARRANGEMENTS)

# ADR-627 D2 — the app's voice is its own agent, not a second app on Editor:
# Editor's contract is the member's document in the member's voice; Blogger
# writes for a reader OUTSIDE the workspace. Those postures conflict in one
# character. `standing_executor` stays undeclared (the resident executes —
# ADR-604 D2's common case), so a standing declaration naming this app derives
# Blogger with no further wiring (ADR-603 D2).
register_app("blogger", resident="blogger", posture=studio_pane_posture)


__all__ = ["BLOGGER_LAYOUTS", "BLOGGER_ARRANGEMENTS", "POST_SLUG"]
