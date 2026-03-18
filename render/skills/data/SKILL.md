---
name: data_export
description: "Export structured data as CSV or JSON files. No external dependencies — pure Python."
type: local
tools: []
input_format: "JSON with headers+rows (CSV) or arbitrary data (JSON)"
output_formats: [".csv", ".json"]
---

# Data Export Skill

Exports structured data to CSV or JSON format using Python stdlib.

## Input Spec

### For CSV output

```json
{
  "headers": ["Column A", "Column B", "Column C"],
  "rows": [
    ["value1", "value2", "value3"],
    ["value4", "value5", "value6"]
  ],
  "title": "Optional filename hint"
}
```

### For JSON output

```json
{
  "data": { "any": "valid JSON structure" },
  "title": "Optional filename hint"
}
```

If `data` is not provided for JSON, the entire input is exported as-is.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `headers` | array[string] | CSV only | Column headers |
| `rows` | array[array] | CSV only | Data rows |
| `data` | any | JSON only | Arbitrary JSON data to export |
| `title` | string | no | Filename hint (metadata only) |

## Output Formats

- `csv` — Comma-separated values. UTF-8 with BOM for Excel compatibility.
- `json` — Pretty-printed JSON with 2-space indent.

## Examples

### CSV metrics export
```json
{
  "type": "data_export",
  "input": {
    "headers": ["Agent", "Runs", "Success Rate", "Avg Duration"],
    "rows": [
      ["Slack Recap", 42, "94%", "3.2s"],
      ["Gmail Digest", 38, "97%", "2.8s"],
      ["Market Monitor", 45, "96%", "2.9s"]
    ]
  },
  "output_format": "csv"
}
```

### JSON data dump
```json
{
  "type": "data_export",
  "input": {
    "data": {
      "report_date": "2026-03-18",
      "metrics": {"total_runs": 125, "success_rate": 0.96},
      "agents": [{"name": "Slack Recap", "status": "active"}]
    }
  },
  "output_format": "json"
}
```

## Constraints

- Maximum data size: ~5MB (matches render service limit)
- CSV values containing commas or newlines are properly quoted
- JSON output is always pretty-printed (human-readable)
- No schema validation — data is exported as-provided
