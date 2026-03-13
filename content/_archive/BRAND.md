# YARNNN Brand — Creative Asset Guidelines

## Identity

**Product**: Autonomous agent platform for recurring knowledge work.
**One-liner**: Persistent AI agents that connect to your work tools, run on schedule, and deliver outputs that improve with tenure.
**URL**: yarnnn.com

## Visual Identity

### Colors
| Role       | Hex       | Usage                                    |
|------------|-----------|------------------------------------------|
| Primary    | `#F26522` | Logo, CTAs, emphasis accents             |
| Dark BG    | `#0A0A0A` | Default background for dark-mode assets  |
| Light BG   | `#FFFFFF` | Light-mode assets, cards                 |
| Text/White | `#FFFFFF` | Headline text on dark backgrounds        |
| Text/Dim   | `#FFFFFF` @ 60% opacity | Body copy on dark backgrounds |
| Text/Dark  | `#111111` | Headline text on light backgrounds       |

### Logo
- **Primary mark**: Orange yarn ball (circle, no wordmark). File: `circleonly_yarnnn.png`
- **Dark wordmark**: `yarn-logo-dark.png` (for light backgrounds)
- **Light wordmark**: `yarn-logo-light.png` (for dark backgrounds)
- **Logo SVG**: `circleonly_yarnnn_1.svg` (vector, scalable)
- **Minimum clear space**: Half the logo diameter on all sides

### Typography
- **Preferred**: Inter (weights: 400, 500, 600, 700, 800)
- **Fallback**: -apple-system, system-ui, sans-serif
- **Headline style**: Bold/ExtraBold, tight tracking (-0.02em)

## Voice & Tone (Ads)

### Personality
Confident peer who's already solved the problem. Not salesy, not robotic. Speaks in short declarative sentences. Understands the pain of repetitive knowledge work.

### Voice Attributes
- **Direct**: Short sentences. No filler. Say what it does.
- **Confident**: "Already done" not "could help you."
- **Concrete**: Name the tools (Slack, Gmail, Notion, Calendar). Name the outcome.
- **Human**: Speaks to "you" and "your Monday morning."

### Tone by Channel
| Channel   | Dial up       | Dial down      |
|-----------|---------------|----------------|
| Reddit    | Casual, blunt | Polish, jargon |
| LinkedIn  | Professional  | Casualness     |
| Twitter/X | Punchy, witty | Length          |

## Ad Creative Strategy

### The Collective Principle
An ad is not one image — it's a **system of parts** working together. Each part has a single job:

| Part              | Job                                        | Don't repeat from other parts |
|-------------------|--------------------------------------------|-------------------------------|
| **Headline text** | Hook — the promise or pain point           | Don't restate in image        |
| **Body text**     | Explain — what it does, how it works       | Don't restate in image        |
| **Image**         | Stop the scroll — bold visual identity     | Don't include body copy       |
| **CTA button**    | Convert — "Learn More", "Get Started"      | Platform provides this        |

### Image Guidelines
- **Purpose**: Brand recognition + scroll-stopping visual. NOT a second copy of the headline.
- **What works**: Logo mark prominently. Bold `yarnnn.com` wordmark. Single accent color. High contrast.
- **What doesn't work**: Paragraphs of text in the image. Repeating the headline. Busy compositions. Tiny logos at mobile scale.
- **Scale test**: If the image is 150px tall on a phone, can you still read/recognize it? If not, simplify.
- **Max text in image**: Brand name or URL only (5 words absolute max).

### Platform Specs
| Platform  | Image Size    | Notes                                       |
|-----------|---------------|---------------------------------------------|
| Reddit    | 1200 x 628   | Card format — image sits below text          |
| LinkedIn  | 1200 x 627   | Image is primary, text truncates fast        |
| Twitter/X | 1600 x 900   | Image dominates the card                     |
| General   | 1200 x 1200  | Square, works as fallback anywhere           |

### File Naming
```
{platform}/{concept}-{variant}-v{version}.{ext}
```
Examples: `reddit/monday-morning-v2.png`, `linkedin/already-done-dark-v1.png`

Source files (HTML/SVG/PY) saved alongside PNGs for iteration.
