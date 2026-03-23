---
name: video
description: Short-form video generation via Remotion (15-30s clips)
output_formats: [mp4]
---

# Video Skill

Produces short-form video clips (15-30 seconds max) from structured scene specifications.

## When to Use

Use this skill when the output benefits from motion:
- Animated metric reveals (numbers counting up, chart animations)
- Short product announcements or feature highlights
- Social media clips with text overlays
- Animated diagrams showing process flows
- Before/after comparisons with transitions

## Constraints

- **Maximum duration: 30 seconds.** This is a hard limit. Design concise, impactful clips.
- **Resolution: 1080x1920 (vertical/stories) or 1920x1080 (landscape).** Specify in the input.
- **No audio.** Videos are silent — use text overlays for messaging.
- **Keep scenes simple.** 3-5 scenes per video. Each scene: background color/gradient + text + optional data visualization.

## Input Specification

```json
{
  "title": "Q2 Revenue Growth",
  "orientation": "landscape",
  "duration_seconds": 20,
  "scenes": [
    {
      "type": "title",
      "text": "Q2 Revenue Report",
      "subtitle": "Key metrics at a glance",
      "duration": 4,
      "background": "#1a56db"
    },
    {
      "type": "metric",
      "label": "Revenue",
      "value": "$2.8M",
      "change": "+33%",
      "duration": 5,
      "animate": "count_up"
    },
    {
      "type": "comparison",
      "items": [
        {"label": "Q1", "value": "$2.1M"},
        {"label": "Q2", "value": "$2.8M"}
      ],
      "duration": 5
    },
    {
      "type": "text",
      "heading": "Key Drivers",
      "bullets": ["Enterprise expansion +45%", "New logos +12", "Churn reduced to 2.1%"],
      "duration": 6
    }
  ]
}
```

## Scene Types

| Type | Purpose | Required Fields |
|------|---------|----------------|
| `title` | Opening/closing slide | text, duration |
| `metric` | Single number highlight | label, value, duration |
| `comparison` | Side-by-side values | items (array), duration |
| `text` | Bullet points or paragraph | heading, bullets or body, duration |
| `chart` | Animated chart reveal | chart_type, data, duration |

## Output

- Format: MP4 (H.264)
- Uploaded to storage, returns `output_url`
- Reference in markdown: `![Video](assets/video-name.mp4)`

## Example Tool Call

```
RuntimeDispatch(
  type="video",
  input={
    "title": "Weekly Metrics",
    "orientation": "landscape",
    "duration_seconds": 15,
    "scenes": [
      {"type": "title", "text": "This Week in Numbers", "duration": 3},
      {"type": "metric", "label": "Active Users", "value": "12,450", "change": "+8%", "duration": 4, "animate": "count_up"},
      {"type": "metric", "label": "Revenue", "value": "$180K", "change": "+12%", "duration": 4, "animate": "count_up"},
      {"type": "text", "heading": "Highlights", "bullets": ["Launched v2.1", "Enterprise pilot started"], "duration": 4}
    ]
  },
  output_format="mp4"
)
```
