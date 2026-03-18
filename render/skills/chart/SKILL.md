---
name: chart
description: "Create charts and data visualizations. Produces PNG or SVG images from data specs using matplotlib."
type: local
tools: ["matplotlib", "numpy"]
input_format: "JSON with chart_type, labels, and datasets"
output_formats: [".png", ".svg"]
---

# Chart Skill

Creates data visualizations (bar, line, pie charts) from structured data using matplotlib.

## Input Spec

The input is a JSON object:

```json
{
  "chart_type": "bar",
  "title": "Chart Title",
  "labels": ["Label 1", "Label 2", "Label 3"],
  "datasets": [
    {"label": "Series A", "data": [10, 20, 30]},
    {"label": "Series B", "data": [15, 25, 35]}
  ],
  "x_label": "X Axis Label (optional)",
  "y_label": "Y Axis Label (optional)"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chart_type` | string | yes | `bar`, `line`, or `pie` |
| `title` | string | yes | Chart title |
| `labels` | array[string] | yes | X-axis labels (or pie slice labels) |
| `datasets` | array | yes | Data series array |
| `datasets[].label` | string | no | Series name (shown in legend) |
| `datasets[].data` | array[number] | yes | Numeric values (must match labels length) |
| `x_label` | string | no | X-axis label |
| `y_label` | string | no | Y-axis label |

### Chart Types

- **`bar`** — Grouped bar chart. Multiple datasets shown side-by-side. X-axis labels rotated 45° for readability.
- **`line`** — Line chart with markers. Each dataset is a separate line.
- **`pie`** — Pie chart. Uses first dataset only. Shows percentage labels.

## Output Formats

- `png` — Raster image at 150 DPI. Best for embedding in presentations and emails.
- `svg` — Vector image. Best for web display and scaling.

## Examples

### Revenue comparison
```json
{
  "type": "chart",
  "input": {
    "chart_type": "bar",
    "title": "Quarterly Revenue",
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "datasets": [
      {"label": "2025", "data": [1200, 1350, 1100, 1500]},
      {"label": "2026", "data": [1380, 1600, null, null]}
    ],
    "y_label": "Revenue ($K)"
  },
  "output_format": "png"
}
```

### Trend line
```json
{
  "type": "chart",
  "input": {
    "chart_type": "line",
    "title": "Weekly Active Users",
    "labels": ["W1", "W2", "W3", "W4", "W5"],
    "datasets": [{"label": "Users", "data": [100, 120, 115, 140, 160]}],
    "y_label": "Users"
  },
  "output_format": "svg"
}
```

## Constraints

- Figure size: 10" × 6" at 150 DPI (PNG) or vector (SVG)
- Maximum labels: ~50 (readability degrades beyond this)
- Pie charts use first dataset only — additional datasets ignored
- No custom colors or themes — matplotlib default colormap
- No annotations, trend lines, or secondary axes
