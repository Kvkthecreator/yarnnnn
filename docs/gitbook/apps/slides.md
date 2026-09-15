# Slides

Slides is where you build a deck. You shape it directly — objects on a stage, one idea per slide — and an AI lane sits beside it, bound to the file you're editing.

If you're writing an internal document, that's [Text](text.md). If you're writing for a reader outside the workspace, that's [Blogger](blogger.md). Slides is for the thing that gets *presented*: a slide deck — 16:9, spoken over, one idea per slide.

You name it and choose where it lives. Slides doesn't own a folder — decks go where they make sense in your workspace, next to the rest of your work.

## The grammar of a deck

Decks behave like Keynote or PowerPoint. The slide is the unit: "New slide" is the primary act, the navigator strip is real navigation, and clicking selects — a selected block gets a bounding box and eight handles, drags to position, and a second click puts the caret in its text. A deck is the one artifact with a coordinate space; everything else in the workspace flows.

Containers are real, selectable structure: click a column or a slide to select it, press **Esc** to walk up the chain (block → column → slide → deck), and use the layout controls — padding, alignment, width (hug or fill) — on whatever you have selected.

## Blocks

One vocabulary across every artifact the workspace composes:

Heading · Text · Callout · Quote · Bulleted list · Numbered list · Checklist · Divider · Toggle · Button · Component · Table · Metrics · Chart · Figure · Gallery

A Chart doesn't paste a picture — you pick a CSV from your workspace and the chart is drawn from it, live: when the data file changes, the chart follows. Shift-click collects several objects into a set; delete or duplicate then takes the whole set (the menu says the count), and align/distribute arrange it as one gesture.

Reach them from the insert menu, or from the block's right-click menu. "Turn into" only offers conversions the target block actually accepts. Figures and galleries cite real workspace files — a live reference, not a pasted copy.

## Arrangements

Layout presets that place content for you:

Title slide · Content · Two column · Comparison · Quote · Picture with caption · Section header · Agenda · Big number · Full-bleed image · Closing.

You can also ask the lane to **re-arrange** an existing deck: it plans where each block belongs, and the mechanism places them.

## Design

An inspector gives you per-block, per-container, and per-deck dials: width, alignment, tone, spacing, scrim, focus, typography, slide numbers. You can set a background on any slide, and create a reusable **design system** so a set of artifacts share one look.

## The bound lane

The right-hand column is a chat lane bound to the deck you have open. It's the same machinery as [Chat](chat.md), with two differences: it knows which file you're editing, and the agent beside you is **Editor**, who writes with you across decks and documents.

Two hands write to the same file:

- **You**, directly — typing, dragging, arranging
- **The lane**, when you ask it to draft, patch, or restructure

Both go through the same door, so both land as attributed revisions. Your own typing saves ambiently as you go; structural changes and lane writes re-render the canvas with your scroll position preserved.

**⌘Z / ⌘⇧Z** undo and redo. Undo is itself a revision — the record shows the correction rather than erasing the mistake.

## File operations

The open deck carries the standard verbs: rename, move, duplicate, copy link, move to trash. They behave identically to the same verbs on the [Files](files.md) surface.

## Export

A deck can leave the system as standard output (Print / PDF — one slide per landscape page).
