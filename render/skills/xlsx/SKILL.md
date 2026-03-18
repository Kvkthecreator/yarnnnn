---
name: spreadsheet
description: "Create spreadsheets from tabular data specs. Produces .xlsx files with styled headers, auto-width columns, and multiple sheets."
type: local
tools: ["openpyxl"]
input_format: "JSON with sheets array (or flat headers+rows)"
output_formats: [".xlsx"]
---

# XLSX Skill

Creates Excel spreadsheets from structured tabular data using openpyxl.

## Input Spec

The input supports two formats:

### Multi-sheet format
```json
{
  "title": "Workbook Title",
  "sheets": [
    {
      "name": "Sheet Name",
      "headers": ["Column A", "Column B", "Column C"],
      "rows": [
        ["value1", "value2", "value3"],
        ["value4", "value5", "value6"]
      ]
    }
  ]
}
```

### Flat format (single sheet)
```json
{
  "title": "Sheet Name",
  "headers": ["Column A", "Column B"],
  "rows": [["value1", "value2"]]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | no | Workbook or sheet title |
| `sheets` | array | no | Array of sheet objects (if absent, uses flat format) |
| `sheets[].name` | string | yes | Sheet tab name |
| `sheets[].headers` | array[string] | yes | Column headers |
| `sheets[].rows` | array[array] | yes | Data rows (values can be string, number, or null) |
| `headers` | array[string] | flat only | Column headers for single-sheet mode |
| `rows` | array[array] | flat only | Data rows for single-sheet mode |

## Output Formats

- `xlsx` — Excel format with styled headers (bold, centered, light gray background) and auto-width columns.

## Examples

### Metrics export
```json
{
  "type": "spreadsheet",
  "input": {
    "title": "Agent Metrics",
    "sheets": [
      {
        "name": "Weekly",
        "headers": ["Week", "Runs", "Success Rate", "Avg Duration"],
        "rows": [
          ["2026-W10", 42, "94%", "3.2s"],
          ["2026-W11", 38, "97%", "2.8s"],
          ["2026-W12", 45, "96%", "2.9s"]
        ]
      },
      {
        "name": "By Agent",
        "headers": ["Agent", "Skill", "Runs", "Approval Rate"],
        "rows": [
          ["Slack Recap", "digest", 12, "100%"],
          ["Gmail Digest", "digest", 8, "88%"],
          ["Market Monitor", "monitor", 22, "95%"]
        ]
      }
    ]
  },
  "output_format": "xlsx"
}
```

## Constraints

- Maximum column width: 50 characters
- Values are written as-is (no formula support)
- No charts or graphs within spreadsheet — use the chart skill for visualizations
- No merged cells or conditional formatting
