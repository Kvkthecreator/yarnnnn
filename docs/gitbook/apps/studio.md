# Studio

Studio is where you lay things out. You shape the artifact directly — objects on a stage, bands on a page — and an AI lane sits beside it, bound to the file you're editing.

If you're writing an internal document, that's [Docs](docs.md). Studio is for the two shapes that are *composed*, not just written:

| Type | Shape | What it's for |
|---|---|---|
| **Deck** | Staged | A slide deck — one idea per slide, 16:9, spoken over |
| **Web** | Banded | A published page — blog post, essay, or landing page, read by someone outside the workspace |

You name it and choose where it lives. Studio doesn't own a folder — artifacts go where they make sense in your workspace, next to the rest of your work.

## Two media, two grammars

**Decks** behave like Keynote or PowerPoint. The slide is the unit: "New slide" is the primary act, the navigator strip is real navigation, and clicking selects — a selected block gets a bounding box and eight handles, drags to position, and a second click puts the caret in its text. A deck is the one type with a coordinate space.

**Web pages** are band-first. You stack full-width sections — a hero, features, a testimonial, a call to action, or a `prose` band for long-form writing — and each band centers its content in a reading column. There's no positioning on a web page: it has a viewport, not a frame, so the bands reflow to any width.

Containers are real, selectable structure: click a column or a slide to select it, press **Esc** to walk up the chain (block → column → slide/band → page), and use the layout controls — padding, alignment, width (hug or fill) — on whatever you have selected.

## Blocks

One vocabulary across every type:

Text · Callout · Quote · Checklist · Divider · Toggle · Button · Table · Metrics · Chart · Figure · Gallery

Reach them from the insert menu, or from the block's right-click menu. "Turn into" only offers conversions the target block actually accepts. Figures and galleries cite real workspace files — a live reference, not a pasted copy.

## Arrangements

Layout presets that place content for you.

For **decks**: Title slide · Content · Two column · Comparison · Quote · Picture with caption · Section header · Agenda · Big number · Full-bleed image · Closing.

For **web pages**: Hero · Content · Feature grid · Testimonial · Call to action · Footer — plus the long-form pair (prose header · prose) that opens a blog post or essay.

You can also ask the lane to **re-arrange** an existing artifact: it plans where each block belongs, and the mechanism places them.

## Design

An inspector gives you per-block, per-container, and per-document dials: width, alignment, tone, spacing, scrim, focus, typography, slide numbers. You can set a background on any slide or band, and create a reusable **design system** so a set of artifacts share one look.

## The bound lane

The right-hand column is a chat lane bound to the artifact you have open. It's the same machinery as [Chat](chat.md), with two differences: it knows which file you're editing, and it defaults to the **Designer**.

Two hands write to the same file:

- **You**, directly — typing, dragging, arranging
- **The lane**, when you ask it to draft, patch, or restructure

Both go through the same door, so both land as attributed revisions. Your own typing saves ambiently as you go; structural changes and lane writes re-render the canvas with your scroll position preserved.

**⌘Z / ⌘⇧Z** undo and redo. Undo is itself a revision — the record shows the correction rather than erasing the mistake.

## File operations

The open artifact carries the standard verbs: rename, move, duplicate, copy link, move to trash. They behave identically to the same verbs on the [Files](files.md) surface.

## Export

Studio artifacts can leave the system as standard output (Print / PDF — a deck prints one slide per landscape page).
