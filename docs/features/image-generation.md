# Image Generation Skill — Implementation Plan

**Status:** Phase 1 Implemented, Phase 2 In Progress
**Date:** 2026-04-03
**Related:** ADR-157 (fetch-asset skill), ADR-118 (skills as capability layer)
**Replaces:** Current `image` skill (Pillow text+rectangles)

## Context

The current `image` render skill (`render/skills/image/`) is a basic Pillow-based card generator — colored rectangles + text on a canvas. It can't embed images, use real typography, or produce anything visually compelling.

With ADR-157 establishing the `assets/` subfolder convention and `fetch-asset` skill for favicons, the platform now has visual asset infrastructure. The missing piece: **generating original images** for context enrichment and synthesis deliverables.

## API Selection: Gemini Native Image Generation

**Model:** `gemini-2.5-flash-image` via Google Gemini API
**Endpoint:** `POST generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent`
**Auth:** `GOOGLE_API_KEY` (API key, same as chat_companion project)

### Why Gemini native (not Imagen 4, not DALL-E, not Replicate)

| Factor | Gemini Native | Imagen 4 | DALL-E 3 | Replicate Flux |
|--------|--------------|----------|----------|----------------|
| **Free tier** | 500/day | ~0 (needs billing) | None | None |
| **Cost/image** | ~$0.04 (paid) | $0.02 | $0.04-0.08 | $0.003 |
| **Auth** | API key (have it) | Same API key | Separate key | Separate key |
| **Text rendering** | 94-96% accuracy | Basic | Good | Basic |
| **Editing/refinement** | Yes (multi-turn) | No | No | No |
| **Reference images** | Up to 14 | No | No | Yes (IP adapter) |
| **SDK** | google-genai | Same | openai | replicate |

**Decision:** `gemini-2.5-flash-image` — 500 free images/day is more than enough for YARNNN's scale. Same API key as Gemini text. Multi-turn editing enables iterative refinement. No new dependency or billing account needed.

### Rate limits (free tier)

- 500 requests/day
- 15 requests/minute
- Default resolution: 1024x1024
- Aspect ratios: 1:1, 3:2, 2:3, 4:3, 3:4, 16:9, 9:16, etc.

### Response format

- Returns base64-encoded image data in `candidates[].content.parts[].inline_data`
- MIME type: `image/png` or `image/jpeg`
- Must decode + upload to Supabase Storage (same pattern as other render skills)

## Skill Design

### Replace, not extend

Delete the current `render/skills/image/` (Pillow card generator). Replace with a `generate-image` skill backed by Gemini. The new skill name is distinct to avoid confusion — agents calling `type="image"` get the old behavior during transition, `type="generate-image"` gets AI generation.

**Alternative:** Rename the skill in-place. The SKILL.md `name:` field controls the type mapping. Change `name: image` to `name: generate-image`, update callers. The folder stays `image/` but the capability is completely different.

### Interface

```json
{
  "type": "generate-image",
  "input": {
    "prompt": "Professional illustration of autonomous AI agents collaborating in a modern workspace, clean minimal style, white background",
    "aspect_ratio": "16:9",
    "style": "professional",
    "size": "1K"
  },
  "output_format": "png",
  "user_id": "..."
}
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | yes | Image generation prompt |
| `aspect_ratio` | string | no | Aspect ratio (default: "1:1"). Options: 1:1, 3:2, 16:9, 9:16, 4:3, etc. |
| `style` | string | no | Style hint injected into prompt: "professional", "minimal", "technical", "editorial" |
| `size` | string | no | Resolution: "512", "1K" (default), "2K" |

### Style presets

Professional business context demands consistent visual quality. Style presets inject prompt suffixes:

```python
STYLE_PRESETS = {
    "professional": "clean professional style, corporate, minimal, white background",
    "minimal": "minimalist design, clean lines, whitespace, modern",
    "technical": "technical diagram style, clear labels, structured layout",
    "editorial": "editorial illustration, magazine quality, sophisticated",
}
```

### Implementation

```python
# render/skills/image/scripts/render.py (replacement)

from google import genai
from google.genai import types

async def render_image(input_data: dict, output_format: str) -> tuple[bytes, str]:
    prompt = input_data["prompt"]
    aspect_ratio = input_data.get("aspect_ratio", "1:1")
    style = input_data.get("style", "professional")
    size = input_data.get("size", "1K")
    
    # Inject style preset
    if style in STYLE_PRESETS:
        prompt = f"{prompt}, {STYLE_PRESETS[style]}"
    
    client = genai.Client()  # uses GOOGLE_API_KEY env var
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )
    
    # Extract base64 image from response
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            return base64.b64decode(part.inline_data.data), part.inline_data.mime_type
    
    raise ValueError("No image generated")
```

## Use Cases

### Context enrichment (stored in `assets/` folders)

| Domain | Asset Type | Example Prompt |
|--------|-----------|----------------|
| Content Research | Hero image | "Professional illustration of multi-agent AI coordination, minimal style" |
| Market | Segment visual | "Abstract visualization of the AI automation market landscape" |
| Projects | Project cover | "Modern project management dashboard visualization" |

### Synthesis deliverables (embedded in HTML output)

| Task Type | Visual | Example |
|-----------|--------|---------|
| Competitive Brief | Market map illustration | Conceptual positioning diagram |
| Content Brief | Topic hero image | Blog post header |
| Stakeholder Update | Executive visual | Professional cover graphic |
| Launch Material | Announcement visual | Product launch graphic |

### Brand-consistent generation

The workspace has `BRAND.md` with visual style guidelines (colors, typography preferences, style notes). The skill can read brand context and inject it into prompts:

```
"Generate [user prompt], using brand colors #000000 and #ffffff, clean sans-serif aesthetic, minimal decoration"
```

## Integration Points

### 1. Render service (Docker)

- **New dependency:** `google-genai` package in `render/requirements.txt`
- **Env var:** `GOOGLE_API_KEY` on the output gateway service
- **Auto-discovery:** Skill folder stays `image/`, SKILL.md `name:` changes

### 2. RuntimeDispatch (existing)

- No changes needed — `image` type already allowed
- Agents call: `RuntimeDispatch(type="generate-image", input={prompt: "..."}, output_format="png")`
- Workspace write path: `assets/` folder via `workspace_path` override

### 3. Step instructions (existing)

- `update-context` and `derive-output` already mention RuntimeDispatch for visual assets
- May need specific guidance: "For content topics without a company favicon, generate a topic illustration"

### 4. ManageDomains (future)

- Content research entities could get auto-generated hero images at scaffold time
- Same pattern as favicon fetch: non-blocking, stored in `assets/`

## Phases

### Phase 1: Skill replacement
1. Delete current `render/skills/image/scripts/render.py` (Pillow card generator)
2. Write new `render_image()` backed by Gemini
3. Add `google-genai` to `render/requirements.txt`
4. Add `GOOGLE_API_KEY` to render service env vars
5. Update SKILL.md with new interface
6. Test locally and deploy

### Phase 2: Agent integration
1. Update step instructions for content-specific image generation
2. Add brand context injection (read BRAND.md, inject style into prompts)
3. Test with content-brief and competitive-brief task types

### Phase 3: Quality refinement (deferred)
1. Multi-turn editing (regenerate with feedback)
2. Reference image support (use existing assets as style references)
3. Image evaluation/quality gate before storage

## Cost Model

At YARNNN's current scale (1 workspace, testing phase):
- Free tier (500/day) is more than sufficient
- Even at 10 workspaces with daily tasks: ~50 images/day = well within free tier
- At scale (1000 workspaces): ~$20/day at paid tier pricing

## Risks

1. **Content safety filters** — Google blocks ~20% of prompts. Business/professional prompts should be safe but may need retry logic.
2. **SynthID watermark** — Invisible but embedded in all generated images. Not a concern for internal business use but worth noting.
3. **Quality variance** — AI-generated images can be inconsistent. Style presets help but aren't guaranteed.
4. **Latency** — Image generation is 5-15 seconds. Acceptable for async task execution but not for real-time chat.
5. **Imagen deprecation precedent** — Imagen 3 deprecated within a year. Model names may change. Abstract behind skill interface.

## Dependencies

- `google-genai` Python package
- `GOOGLE_API_KEY` environment variable on render service
- Existing: Supabase Storage, workspace_files, RuntimeDispatch, assets/ convention
