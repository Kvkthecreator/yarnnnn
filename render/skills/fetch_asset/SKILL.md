---
name: fetch-asset
description: "Fetch external visual assets (favicons, logos) from URLs and store in Supabase Storage."
type: local
tools: ["httpx"]
input_format: "JSON with URL and asset type"
output_formats: [".png", ".ico", ".jpg", ".svg"]
---

# Fetch Asset Skill

Fetches external visual assets (favicons, logos) and returns the raw bytes for storage upload.

## Input Spec

```json
{
  "url": "cursor.com",
  "asset_type": "favicon",
  "size": 64
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | Domain name or full URL. For favicons, just the domain (e.g., "cursor.com"). |
| `asset_type` | string | no | Asset type: `favicon` (default). Future: `logo`, `screenshot`. |
| `size` | integer | no | Desired size in pixels (default: 64). Favicon API supports 16, 32, 64, 128, 256. |

## Output Formats

- `png` — Default for favicons. Always returns PNG regardless of source format.

## Examples

### Fetch a company favicon
```json
{
  "type": "fetch-asset",
  "input": {
    "url": "anthropic.com",
    "asset_type": "favicon",
    "size": 128
  },
  "output_format": "png"
}
```

## Constraints

- Maximum asset size: 1MB
- Fetch timeout: 10 seconds
- Only `favicon` type supported in v1
- Size clamped to [16, 256] pixels for favicons
