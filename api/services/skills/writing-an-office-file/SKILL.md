---
name: writing-an-office-file
description: Changes a member's Word, Excel or PowerPoint file in place at the addresses ReadFile shows, keeping its formatting and formulas — or creates a new office file for a reader outside. Use when asked to update or fill in a .docx, .xlsx or .pptx, or for something to send or attach.
metadata:
  target: The member's office file changed in place (one revision, only the asked-for elements) — or one new .docx/.pptx/.xlsx beside its source, derived_from it.
---
# Writing an office file

A member's .docx, .xlsx or .pptx IS the document — its template, styles, formulas and layout are theirs. You change its words and values where they sit; you never rebuild it.

## Changing an existing file

1. **Read it first.** ReadFile returns its text with an address on every element: `[p12]` a Word paragraph (`[p3 · Heading 2]` names its style), `Budget!B7` an Excel cell (column letter + row number from the table), `[s3/5]` a slide shape, `s3/7/r2c1` a table cell, `s3/notes` the notes. A formula shows beside its value: `=SUM(B2:B19) → 4210`.
2. **Edit at the address.** `EditFile(path, anchor={'at': 'p12'}, old_string='30 days', new_string='45 days')` replaces a phrase inside that element and keeps its formatting. Omit `old_string` to replace the whole element; `new_string=''` deletes a Word paragraph. `anchor={'after': 'p12'}` adds a paragraph; `style='Heading 2'` uses one of the document's own styles.
3. **Batch related changes.** Several edits as `edits=[{at, old_string?, new_string}, …]` land as ONE revision — updating a budget's figures is one edit, not twenty.
4. **Write values the way the sheet holds them.** `1250` or `1,250` is a number, `25%` is 0.25, `=SUM(B2:B4)` is a formula, `'=text` is literal text. Change an input, not a total: its formula recalculates when the file is opened in Excel.
5. **Re-read before the next round.** An inserted paragraph moves the addresses after it.
6. **Say what changed.** In Word your edits show as tracked changes under your name; the member accepts them there. Name the cells or paragraphs you touched.

## Creating a new file

For a reader outside the workspace, from work that lives here. WriteFile to a NEW office path with `content=''` and `derived_from=[the source]` — the kernel reads it, so a long source never passes through you. A document comes from Markdown or HTML, a sheet from CSV (plain numbers, one header row), a presentation only from a Slides deck. The conversion keeps structure and words and drops styling, so put emphasis in headings and tables, and tell the member what the format could not carry.

## Quality bar

- Only the elements asked about changed; every other part of the file is as it was.
- A sheet's formulas still compute; nothing that was a formula became a number.
- A new file cites its source and sits beside it, never over an existing file.

## Anti-patterns

Writing an existing office file back from its text — refused, because it would drop the member's formatting and formulas. Overwriting a total instead of the input it sums. Twenty single-cell calls where one `edits` batch belongs. Guessing an address instead of reading it.
