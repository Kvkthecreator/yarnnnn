---
name: presentation
description: "Create presentations from slide specs. Produces .pptx files from structured JSON input describing slides, layouts, and content."
type: local
tools: ["python-pptx"]
input_format: "JSON slide spec with title and slides array"
output_formats: [".pptx"]
---

# PPTX Skill

Creates PowerPoint presentations from structured slide specifications using python-pptx.

## Input Spec

The input is a JSON object:

```json
{
  "title": "Presentation Title",
  "subtitle": "Optional subtitle for title slide",
  "slides": [
    {
      "title": "Slide Title",
      "content": "Bullet point 1\nBullet point 2\nBullet point 3",
      "layout": "content"
    }
  ]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Presentation title (shown on title slide) |
| `subtitle` | string | no | Subtitle on title slide |
| `slides` | array | yes | Array of slide objects |
| `slides[].title` | string | yes | Slide heading |
| `slides[].content` | string | yes | Slide body — newlines become bullet points |
| `slides[].layout` | string | no | Layout type (currently: `content` only) |

## Output Formats

- `pptx` — PowerPoint format. 16:9 widescreen (13.333" × 7.5").

## Examples

### Weekly team update
```json
{
  "type": "presentation",
  "input": {
    "title": "Engineering Weekly Update",
    "subtitle": "Week of March 17, 2026",
    "slides": [
      {
        "title": "Highlights",
        "content": "Shipped ADR-118 Phase C\nRender service handling 50+ requests/day\nZero downtime during migration"
      },
      {
        "title": "Metrics",
        "content": "API latency p99: 240ms (down from 380ms)\nAgent success rate: 94%\nNew users this week: 12"
      },
      {
        "title": "Next Week",
        "content": "Skills alignment (D.1)\nRender service hardening (D.2)\nOutput folder conventions (ADR-119)"
      }
    ]
  },
  "output_format": "pptx"
}
```

## Constraints

- Maximum 50 slides per presentation
- Content is text-only — no embedded images in slides (yet)
- Single layout type (`content` with title + body)
- Font size: 18pt body text
- No custom themes or color schemes — default PowerPoint styling
