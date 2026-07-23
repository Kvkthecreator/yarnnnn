# Studio

Studio is where you make things. You shape the artifact directly — and an AI lane sits beside it, bound to the file you're editing.

## Starting

Open Studio and you either pick up where you left off, or start something new. Four types:

| Type | Shape | What it's for |
|---|---|---|
| **Document** | Flow | An internal working document — sections under one title |
| **Article** | Flow | A publishing shape — blog post, essay, announcement |
| **Deck** | Paged | A slide deck — one idea per slide, 16:9 |
| **Page** | Paged | A landing page — hero, features, call to action |

You name it and choose where it lives. Studio doesn't own a folder — artifacts go where they make sense in your workspace, next to the rest of your work.

## Two shapes, two grammars

**Flow** (documents, articles) behaves like a page. You type into it. The outline on the left is a derived table of contents, not a structure you have to maintain. There's no "insert section" — you write, and the document flows.

**Paged** (decks, pages) behaves like Keynote or PowerPoint. The container is the unit: "new slide" is the primary act, the navigator strip is real navigation, and selecting a block is how you act on it. The navigator supports multi-select for managing slides in bulk.

## Blocks

One vocabulary across every type — twelve blocks:

Text · Callout · Quote · Checklist · Divider · Toggle · Button · Table · Metrics · Chart · Image · Gallery

Reach them from the toolbar, from a slash command in the text, or from the block's right-click menu. "Turn into" only offers conversions the target block actually accepts.

## Arrangements

Layout presets that place content for you.

For **decks**: Title slide · Content · Two column · Comparison · Quote · Picture with caption · Section header · Agenda · Big number · Full-bleed image · Closing.

For **pages**: Hero · Content · Feature grid · Testimonial · Call to action · Footer.

On a flow document an arrangement is a band you insert — a two-column stretch, a metrics row — not a page unit.

You can also ask the lane to **re-arrange** an existing artifact: it plans where each block belongs, and the mechanism places them.

## Design

An inspector gives you per-block and per-document dials: width, alignment, tone, height, fit, columns, vertical alignment, spacing, scrim, focus, typography, slide numbers. You can set a background on any page or slide, and create a reusable **design system** so a set of artifacts share one look.

## The bound lane

The right-hand column is a chat lane bound to the artifact you have open. It's the same machinery as [Chat](chat.md), with two differences: it knows which file you're editing, and it defaults to the **Designer**.

Two hands write to the same file:

- **You**, directly — typing, toolbar operations, dragging blocks
- **The lane**, when you ask it to draft, patch, or restructure

Both go through the same door, so both land as attributed revisions. Your own typing saves ambiently as you go; structural changes and lane writes re-render the canvas with your scroll position preserved.

**⌘Z / ⌘⇧Z** undo and redo. Undo is itself a revision — the record shows the correction rather than erasing the mistake.

## File operations

The open artifact carries the standard verbs: rename, move, duplicate, copy link, move to trash, upload. They behave identically to the same verbs on the [Files](files.md) surface.

## Export

Studio artifacts can leave the system as standard output. For visuals that should stay traceable back to their source composition, use [Images](images.md) instead — there, the rendered file is recorded as a derivation of the stage that produced it.
