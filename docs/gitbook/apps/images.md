# Images

Images is for composed visuals — social posts, ads, banners, covers. You place layered objects on a stage of a fixed size.

## Size first

Unlike a document, an image starts with its dimensions. Pick a preset or set your own:

| Preset | Size |
|---|---|
| Square | 1080 × 1080 |
| Story | 1080 × 1920 |
| Wide | 1600 × 900 |
| Ad | 1200 × 628 |
| Portrait | 1080 × 1350 |
| Banner | 1500 × 500 |

Custom width × height is supported.

## The stage

The stage is an open canvas: you position everything. Each object has X, Y, and Z (stacking) plus width and height. It uses the same block vocabulary as [Studio](studio.md) — text, images, shapes, metrics — placed freely rather than flowed.

## Composing with AI

Describe what you want and the app decomposes the brief into layers, places them on the stage, and generates the elements that need generating. You get a composition you can then adjust by hand — not a flat image you can only accept or regenerate.

This is the point of Images being its own app: **the composition is the source.** The rendered PNG is a derivation of it, recorded as such. You can always go back to the stage, change one layer, and re-render — and the history connects the two.

## Export

Export happens in your browser, rendering the stage you're already looking at. The exported raster stays traceable to the composition and the revision that produced it.

## Editing with a lane

Like Studio, Images has a bound chat lane on the right. It can read and write the composition with the same file verbs any lane has.
