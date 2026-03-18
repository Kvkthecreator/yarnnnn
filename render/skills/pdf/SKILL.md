---
name: document
description: "Create PDF or DOCX documents from markdown. Produces formatted documents using pandoc with LaTeX."
type: local
tools: ["pandoc", "texlive-latex-base"]
input_format: "JSON with markdown content and optional title"
output_formats: [".pdf", ".docx"]
---

# PDF / Document Skill

Converts markdown content to formatted PDF or DOCX documents using pandoc.

## Input Spec

The input is a JSON object:

```json
{
  "markdown": "# Heading\n\nBody text with **bold** and *italic*...",
  "title": "Document Title (optional)"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `markdown` | string | yes | Markdown content to render |
| `title` | string | no | Document title (appears in metadata) |

## Output Formats

- `pdf` — Rendered via pdflatex. Best for sharing and printing.
- `docx` — Microsoft Word format. Best when recipient needs to edit.

## Examples

### Simple report
```json
{
  "type": "document",
  "input": {
    "markdown": "# Q1 Revenue Report\n\n## Summary\n\nRevenue grew 15% QoQ...\n\n## Details\n\n| Quarter | Revenue |\n|---------|--------|\n| Q4 | $1.2M |\n| Q1 | $1.38M |",
    "title": "Q1 Revenue Report"
  },
  "output_format": "pdf"
}
```

## Constraints

- Maximum markdown length: ~100KB (pandoc memory limits)
- Images must be referenced by URL (no local paths)
- LaTeX math supported via `$...$` and `$$...$$`
- Tables render as standard pandoc tables
- No custom CSS/styling — pandoc default formatting
