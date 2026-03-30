---
name: document
description: "Create PDF or DOCX documents from HTML or markdown. HTML input preferred (from composed output.html)."
type: local
tools: ["pandoc", "texlive-latex-base"]
input_format: "JSON with html (preferred) or markdown content"
output_formats: [".pdf", ".docx"]
---

# PDF / Document Skill

Converts HTML or markdown to formatted PDF or DOCX documents using pandoc.

**Primary input: HTML** (from composed output.html — preserves styling, tables, asset references).
**Fallback input: markdown** (for direct usage or when HTML not available).

## Input Spec

```json
{
  "html": "<html>..composed output.html content..</html>",
  "title": "Document Title (optional)"
}
```

OR (fallback):

```json
{
  "markdown": "# Heading\n\nBody text...",
  "title": "Document Title (optional)"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `html` | string | preferred | Composed HTML content (from output.html) |
| `markdown` | string | fallback | Markdown content (if no HTML available) |
| `title` | string | no | Document title (appears in metadata) |

## Output Formats

- `pdf` — Rendered via pdflatex. Best for sharing and printing.
- `docx` — Microsoft Word format. Best when recipient needs to edit.

## Constraints

- Maximum content length: ~100KB
- Images must be referenced by URL (no local paths)
- LaTeX math supported via `$...$` and `$$...$$`
- Tables render from HTML structure or pandoc markdown tables
