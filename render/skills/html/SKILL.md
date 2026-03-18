---
name: report
description: "Create styled HTML reports from markdown. Produces self-contained .html files with embedded CSS."
type: local
tools: ["pandoc"]
input_format: "JSON with markdown content and optional title/style"
output_formats: [".html"]
---

# HTML Report Skill

Creates self-contained HTML reports from markdown using pandoc with embedded CSS styling.

## Input Spec

The input is a JSON object:

```json
{
  "markdown": "# Report Title\n\nBody text with **bold** and tables...",
  "title": "Report Title (optional)",
  "style": "default"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `markdown` | string | yes | Markdown content to render |
| `title` | string | no | Document title (appears in `<title>` and header) |
| `style` | string | no | Style preset: `default` (clean sans-serif) |

## Output Formats

- `html` — Self-contained HTML with inline CSS. Opens in any browser. Best for sharing via email or embedding.

## Examples

### Weekly digest report
```json
{
  "type": "report",
  "input": {
    "markdown": "# Weekly Platform Digest\n\n## Slack Highlights\n\n- **#engineering**: Deployed v2.2 with zero downtime\n- **#product**: Q2 roadmap finalized\n\n## Gmail Summary\n\n| Sender | Subject | Priority |\n|--------|---------|----------|\n| CEO | Q2 Kickoff | High |\n| HR | Benefits Update | Low |\n\n## Action Items\n\n1. Review Q2 roadmap by Friday\n2. Submit expense reports",
    "title": "Weekly Digest — March 18, 2026"
  },
  "output_format": "html"
}
```

## Constraints

- Maximum markdown length: ~100KB
- Images must be referenced by URL (not embedded as base64)
- Tables render as styled HTML tables
- No JavaScript — static HTML only
- Single built-in style (clean, readable, print-friendly)
