"""
Docs — the writing app's document type (ADR-518).

The CAPTURE medium, carved from Studio's table the way `canvas` left for
IMAGES (ADR-472 D1/D7): the app boundary is the MODULE (ADR-473 D2). The row
below is `STUDIO_LAYOUTS["document"]` moved verbatim — same slug, same mode,
same skin, same scaffold — with its `app` declaration now naming the app that
owns it. Nothing at the substrate changes: `data-template="document"` values
in live artifacts are untouched, and every reader resolves through the shared
registry (`services/authoring.py::resolve_layout`).

The shared machinery (skeleton builder, posture, artifact-kind, the write
door, the projection) is kernel code all three authoring apps consume —
registration is how Docs reaches it without Studio importing an app or the
builders being forked (ADR-472 D2, "one implementation, N consumers").

Docs registers NO arrangements: `document` is `flow`, and arrangements are
`paged`-only (ADR-481 D1, hardened by ADR-505 D1). Two columns inside a
document would be a BLOCK kind, not an arrangement.
"""

#: The slug of the document type Docs owns. Opaque + stable (ADR-459 D1).
DOCUMENT_SLUG = "document"

# ADR-505 D1: the CAPTURE medium. Notes, drafts, PRDs, meeting records —
# the type where information ARRIVES and is continuously revised, and the
# workspace's centre of gravity (9 of 18 live artifacts at the cut, and the
# only two with real authored substance). Its expressive scope is the
# markdown-grade essentials (headings, prose, lists, quote, callout, table,
# image, divider) — deliberately NOT a layout surface. Every region
# mechanism (arrangements, slots, geometry) is absent BY DEFINITION here,
# not by measurement: a capture surface that asks "where on the page" has
# stopped being a capture surface.
DOCS_LAYOUTS: dict[str, dict[str, str]] = {
    DOCUMENT_SLUG: {
        "app": "docs",
        "label": "Document",
        "mode": "flow",
        "description": "Notes, drafts, working documents — capture and revise.",
        "flow": (
            "one <main> holding an <h1> title and a short lede <p>, then blocks "
            "flowing vertically. Clarity over polish."
        ),
        "skin": """
    main { max-width: 46rem; margin: 0 auto; padding: 3rem 1.5rem; }
    h1 { font-size: var(--text-3xl, 2rem); margin-bottom: 0.5rem; }
    section[data-block] { margin-top: 2rem; }
    section[data-block] h2 { font-size: var(--text-xl, 1.3rem); margin-bottom: 0.75rem; }
""".strip("\n"),
        # ADR-481 D1: FLAT. A blank document is a blank page — no arrangement
        # wrapper, no empty slot. The old scaffold shipped a `title-lede`
        # section around an empty `data-slot="main"`, which on a flowing
        # document renders as a dead vertical void wearing an "+ Add here"
        # and a gutter attached to nothing. A slot is a PAGED concept.
        "scaffold": """<main>
  <h1 data-block="heading" data-block-id="t1">Untitled document</h1>
  <p class="lede" data-block="heading" data-block-id="t2">One sentence on what this document is for.</p>
  <h2 data-block="heading" data-block-id="t3">First section</h2>
  <div data-block="prose" data-block-id="b1"><p>Start here.</p></div>
</main>""",
    },
}


# Docs registers its document type with the shared machinery (ADR-472 D2 via
# ADR-518 D3) and its AI configuration with the app registry (ADR-562 D2). The
# builders (skeleton, posture, artifact-kind) are kernel code every authoring
# app consumes — registration is how Docs reaches them.
from services.authoring import register_app, register_layouts  # noqa: E402  (registration side-effect)

register_layouts(DOCS_LAYOUTS)

# ADR-562 D3 — the resident, declared where the app lives (re-homed from
# `web/lib/apps/authoring.ts`, which is DELETED). Designer is triple-resident
# (Docs · Studio · IMAGES, ADR-467 D3); a writing-postured resident for Docs
# stays a separate, demand-gated decision, so today's honest declaration is the
# resident that already carries the authoring lane. When that decision arrives
# it is a one-line edit HERE — which is the whole point of the re-home.
register_app("docs", resident="designer")


__all__ = ["DOCS_LAYOUTS", "DOCUMENT_SLUG"]
