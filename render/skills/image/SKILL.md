---
name: image
description: "Generate images from text prompts using Google Gemini. Professional business visuals, illustrations, and conceptual graphics."
type: local
tools: ["google-genai"]
input_format: "JSON with prompt and optional style/aspect ratio"
output_formats: [".png", ".jpg"]
---

# Image Generation Skill

Generates images from text prompts via Google Gemini (`gemini-2.5-flash-image`).
Produces professional business visuals, illustrations, and conceptual graphics.

## Input Spec

```json
{
  "prompt": "Professional illustration of autonomous AI agents collaborating",
  "aspect_ratio": "16:9",
  "style": "professional",
  "size": "1K"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | yes | What to generate. Be specific and descriptive. Max 2000 chars. |
| `aspect_ratio` | string | no | Aspect ratio (default: "1:1"). Options: 1:1, 3:2, 2:3, 4:3, 3:4, 16:9, 9:16, 4:5, 5:4 |
| `style` | string | no | Style preset or custom text (default: "professional"). Presets: professional, minimal, technical, editorial, abstract. Or pass custom: "watercolor, soft tones" |
| `size` | string | no | Resolution: "512", "1K" (default), "2K" |

### Style Presets

| Preset | Description |
|--------|-------------|
| `professional` | Clean corporate aesthetic, minimal, high quality |
| `minimal` | Minimalist design, clean lines, generous whitespace |
| `technical` | Diagram-like, clear labels, structured layout |
| `editorial` | Magazine quality, sophisticated composition |
| `abstract` | Geometric shapes, modern art style |

## Output Formats

- `png` — Lossless. Best for graphics, illustrations, diagrams.
- `jpg` — Lossy (smaller). Best for photographic or complex visuals.

## Examples

### Topic hero image for content
```json
{
  "type": "image",
  "input": {
    "prompt": "Conceptual illustration of multi-agent AI systems coordinating autonomous workflows, showing interconnected nodes and data flows",
    "aspect_ratio": "16:9",
    "style": "minimal"
  },
  "output_format": "png"
}
```

### Market visualization
```json
{
  "type": "image",
  "input": {
    "prompt": "Abstract visualization of the AI automation market landscape with layered segments showing growth areas",
    "aspect_ratio": "3:2",
    "style": "abstract"
  },
  "output_format": "png"
}
```

### Report cover graphic
```json
{
  "type": "image",
  "input": {
    "prompt": "Professional business report cover showing quarterly competitive intelligence dashboard with clean data visualization elements",
    "aspect_ratio": "4:3",
    "style": "professional"
  },
  "output_format": "png"
}
```

## Constraints

- Maximum prompt length: 2000 characters
- Resolution: up to 1024x1024 (1K) on free tier
- Rate limit: 500 images/day (free tier), 15/minute
- Safety filters may block some prompts — rephrase if blocked
- Latency: 5-15 seconds per generation
- All generated images include invisible SynthID watermark
