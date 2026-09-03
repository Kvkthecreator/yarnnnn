---
name: composing-an-image
description: Composes an image on an artboard as depth-ordered layers placed by coordinate, with a focal hierarchy legible at thumbnail size. Use when asked for an ad, poster, social post, OG image, banner, or thumbnail, or to lay out or restack a visual.
metadata:
  target: An image artifact whose artboard carries placed, depth-ordered layers with a legible focal hierarchy.
  apps: [images]
---
# Composing an image

Produce a COMPOSITION on an artboard: overlapping layers placed in a coordinate space, not a document that happens to hold a picture. The pane posture owns the token grammar (`data-x`/`data-y`/`data-z`, opacity, blend); these are the CRAFT constraints.

The artifact is the SOURCE; the raster derived from it is the deliverable. Compose for the exported pixels, not for the HTML.

## Steps

1. **Read the brief for the ONE thing.** An image carries a single message. Name it before placing anything; if you cannot say it in a sentence, the composition has no focal point yet.
2. **Build the stack bottom-up**: background (`z` lowest) → subject/imagery → scrim if needed → text → mark/logo (`z` highest). Give every layer a `data-z`; unstamped layers fall to the bottom and the order stops being yours.
3. **Place by coordinate, not by flow.** Every layer carries both `data-x` and `data-y` — one without the other is not positioned. Anchor text to one edge and keep a consistent margin; a headline at 8% left reads as deliberate, at 11% as an accident.
4. **Earn legibility before styling.** Text over imagery needs contrast: a `scrim`, a `data-blend="multiply"` panel, or a dimmed layer (`data-opacity`). Check the text's own region, not the image's average.
5. **Set the type hierarchy by size and weight, not by count.** One dominant line, one supporting line, one small mark. Three type sizes is a composition; five is a flyer.

## Quality bar

- **The thumbnail test.** At 10% size the focal message still reads. If it needs full size to parse, the hierarchy is flat.
- Text sits fully inside the frame with margin to spare — never touching an edge, never overlapping the subject's face or focal detail.
- Contrast is verified against what is actually BEHIND the text, at that layer's own coordinates.
- Every layer is there for the one message. A layer you cannot justify is deleted, not dimmed.
- Colour comes from the palette variables and the design system, never raw hex.

## Restacking and revising

- Depth is a property, not an accident of document order: to move a layer forward, change its `data-z`, never its position in the markup.
- A member's `lock` or `hide` is an instruction — leave locked layers alone, and never delete a hidden layer to "clean up".
- When asked to change one layer, patch that layer. Recomposing the whole artboard to move a headline discards placement the member may have set by hand on the canvas.

## Anti-patterns

Prose blocks on an artboard (bulleted lists, paragraphs, captions — this is not a document). Centring everything. Text straight onto a busy photo with no scrim. Full-opacity overlays that bury the subject. A logo scaled to compete with the headline. Layers stacked at the same `z`. Filling the frame because it is empty — negative space is composition, not a gap.
