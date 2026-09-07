---
name: assembling-a-composite-document
description: Writes a prose document that has to carry figures, comparisons and evidence, deciding what earns a table and keeping every number traceable to the file it came from. Use when asked for a report, review, brief, one-pager, or any document where the numbers matter as much as the words.
metadata:
  target: One prose document whose every figure names the file it came from, and whose tables carry only what prose cannot.
  apps: [text]
---
# Assembling a composite document

Produce a prose document that carries evidence without turning into a spreadsheet. This is a text document: the words do the work, and a table earns its place only where prose genuinely cannot.

## Steps

1. **Separate the argument from the evidence.** Write the argument first, as sentences. Then ask which figures the reader needs to check it. Evidence that supports no sentence does not belong; a sentence that rests on no evidence needs marking as judgment.
2. **Put a number in prose unless the reader compares it.** A single figure belongs in the sentence that gives it meaning — "p95 latency fell to 505ms after the July migration" says more than a row. A table earns its place only when the reader scans across several values, and then it carries the comparison and nothing else.
3. **Name the source of every figure, inline.** Write where each number came from — the file, and the moment it was read. A number with no stated source cannot be rechecked and cannot be corrected; six months on, nobody knows whether it was measured or remembered. Where the document is derived from workspace files, `derived_from` names them on the write as well.
4. **Never silently restate a figure that lives in a file.** If the data sits in a CSV or a report, the document is a copy of it, and the copy is what will be wrong when the source moves. State that the figures come from that file, and keep the document's own numbers to the few the argument actually uses — copying a whole table into prose is how two versions of the truth start.
5. **Mark what is inferred.** Distinguish what the sources state from what you concluded. "(inferred)" beside a claim lets a reader challenge it; an unmarked inference reads as a measurement.
6. **Read it through with the tables covered.** The argument has to survive without them. If covering the tables loses the point, the point is sitting in the evidence rather than in the writing.

## Quality bar

- Every figure in the document can be traced to a named source.
- Tables carry comparisons; single figures live in sentences.
- Inferences are marked as inferences; measurements are not softened into hedges.
- Removing any table loses a specific comparison — not just "some detail".
- The document reads as one argument, not as a findings dump with connective tissue.

## Anti-patterns

A table because there are three of something. Copying a source file's rows wholesale so the document "has the data". A figure with no stated origin. Hedging a measured number ("roughly", "about") when the source is exact. Restating in prose the comparison the table beside it already makes. Leading with the evidence and leaving the reader to infer the argument.
