---
name: writing-an-office-file
description: Hands workspace work to someone outside it as a Word, PowerPoint or Excel file, structuring the source so it survives the conversion and landing the office file as a new file cited to its source. Use when asked for a .docx, .pptx or .xlsx, or for something to send, attach or print.
metadata:
  target: One new .docx/.pptx/.xlsx beside its source, derived_from that source, which stays the file the work continues in.
---
# Writing an office file

An office file is a copy for a reader outside the workspace. The source stays where the work lives; the office file is what gets sent.

## Steps

1. **Decide whether a file is wanted at all.** A teammate in the workspace reads the source itself — share that. Write an office file only when the reader is outside, or asked for the format by name.
2. **Get the source right first, in the workspace.** The conversion keeps structure and words: headings, lists, tables, bold, italics, links, slide titles. It drops styling — fonts, colours, layout, images. If something matters to the reader, it has to be in the structure: a heading, not a large bold line; a real table, not aligned text.
3. **Match the source to the format.** A document comes from Markdown or HTML. A sheet comes from CSV: one header row, one value per cell, plain numbers (`1200`, not `$1,200`) where the reader will compute. A presentation comes only from a Slides deck — one idea per slide, its title as the slide's heading. There are no speaker notes to carry; put what must be said on the slide or in a separate document.
4. **Convert the file; do not retype it.** WriteFile to the office path with `content=''` and `derived_from=[the source]` — the kernel reads the source itself, so a long deck never passes through you and cannot be clipped on the way. Pass the source as `content` only for a short file that does not yet exist anywhere.
5. **Name it beside its source.** `the-acme-deal/proposal.md` becomes `the-acme-deal/proposal.docx`. Do not overwrite an earlier export the member may already have sent. Pick a new name instead.
6. **Say what came through and what did not.** Tell the member where the new file is, and name anything the format could not carry (an image, a colour-coded status) so they can fix it before sending.

## Quality bar

- The office file cites its source, and the source is unchanged.
- Every heading, list and table in the source appears in the file.
- A sheet's numbers are numbers; nothing in it is a formula it did not ask for.
- The member knows what the format dropped before they send it.

## Anti-patterns

Editing the office file instead of the source, so the next export loses the fix. Re-emitting a whole deck's HTML as `content` to convert it. Styling carried by look alone (big text, colour) that the conversion drops. Promising the result will look like the in-app view.
