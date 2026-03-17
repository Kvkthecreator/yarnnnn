# yarnnn / video

Programmatic video generation using [Remotion](https://remotion.dev). Claude Code has the Remotion best-practices skill installed (`.claude/skills/remotion-best-practices/`) so it can generate and edit compositions from natural language prompts.

## Quick start

```bash
cd video
npm install          # first time only
npm run dev          # opens Remotion Studio (preview + scrub)
```

## Rendering

```bash
# Render a specific composition
npx remotion render src/index.ts ProductDemo out/product-demo.mp4
npx remotion render src/index.ts SocialClip out/social-clip.mp4
npx remotion render src/index.ts ad-connect-once out/ad-connect-once.mp4

# Render all ad variants
for id in ad-works-while-you-sleep ad-first-ai-employee ad-dont-get-caught \
  ad-replace-chatgpt ad-still-using-chatgpt ad-connect-once \
  ad-context-compounds ad-stop-rebuilding; do
  npx remotion render src/index.ts "$id" "out/${id}.mp4"
done
```

## Compositions

| ID | Format | Duration | Purpose |
|----|--------|----------|---------|
| `ProductDemo` | 1920×1080 | 27s | Website / YouTube product explainer |
| `SocialClip` | 1080×1920 | 12s | Reels / TikTok / Shorts |
| `ad-*` (8 variants) | 1080×1080 | 6s each | Social ads (animated versions of static ad frames) |

## Project structure

```
video/
├── public/                    # Static assets available via staticFile()
│   ├── Pacifico-Regular.ttf   # Brand font (copied from web/public/fonts/)
│   ├── circleonly_yarnnn.png  # Yarn ball logo
│   └── logo.svg               # Full logo SVG
├── src/
│   ├── index.ts               # Remotion entry point
│   ├── Root.tsx                # Composition registry (all videos listed here)
│   ├── design.tsx              # Shared design system (see below)
│   └── compositions/
│       ├── AdSpot.tsx          # 8 ad variants (square, 6s)
│       ├── ProductDemo.tsx     # Product explainer (landscape, 27s)
│       └── SocialClip.tsx      # Short-form social (portrait, 12s)
├── remotion.config.ts          # Webpack + Tailwind config
└── out/                        # Rendered MP4s (gitignored)
```

## Design system (`src/design.tsx`)

Shared across all compositions. Changing `design.tsx` updates every video.

### Brand
- **Fonts**: Pacifico (brand wordmark), Inter (body — Google Fonts, loaded via `@remotion/google-fonts`)
- **Colors**: `COLOR.bg` (#fce8d5 peach), `COLOR.fg` (#1a1a1a), `COLOR.orange` (#e8622c), platform colors (slack, gmail, notion, calendar)

### Atoms
- `<YarnBall size={56} />` — yarn ball logo PNG
- `<Watermark />` — "yarnnn.com" in Pacifico, bottom-right
- `<PlatformSVG name="Slack" color={COLOR.slack} />` — platform icons (exact SVG paths from `web/components/landing/IntegrationHub.tsx`)

### Animation helpers
- `useFadeIn(delay, duration)` — opacity interpolation
- `useSlideUp(delay, distance)` — spring-based translateY
- `useSpring(delay, config)` — raw spring value (0→1)

## Relationship to `content/`

```
content/
├── _creatives/
│   ├── _brand/        # Static brand assets (logos, og-card)
│   └── ads/           # Static ad frame PNGs (reference designs)
├── posts/             # Blog content (copy source for video scripts)
└── _archive/
    └── yarnnn-brand-voice.md   # Brand voice guide (tone reference)
```

- **`content/_creatives/ads/`** holds the original static ad frames (Figma/ChatGPT exports). These are the design reference for `AdSpot.tsx` compositions.
- **`content/posts/`** contains blog posts whose themes can inform new video scripts.
- **`content/_archive/yarnnn-brand-voice.md`** and **`kevin-voice.md`** define tone — punchy, no hype, assert a position.

## Adding a new video

1. Create `src/compositions/MyVideo.tsx`
2. Import shared design: `import { COLOR, FONT, YarnBall, ... } from "../design"`
3. Register in `src/Root.tsx` with a `<Composition>` entry
4. Preview: `npm run dev` → select composition in Studio
5. Render: `npx remotion render src/index.ts MyVideo out/my-video.mp4`

## Adding a new ad variant

Add a new export in `AdSpot.tsx` using the `<AdFrame>` component:

```tsx
export const Ad_NewVariant: React.FC = () => (
  <AdFrame topLines={["top line"]} bottomLines={["bottom", "line"]} />
);
```

Then register in `Root.tsx`. The `AdFrame` handles all animation, yarn ball, and watermark automatically.

## Editing tips

- **All animations must use `useCurrentFrame()`** — CSS transitions/Tailwind animation classes are forbidden in Remotion
- **Timing**: Write in seconds, multiply by `fps` from `useVideoConfig()`
- **Sequencing**: Use `<Sequence from={frame} durationInFrames={n}>` for scene timing
- **Fonts**: Use `FONT.brand` (Pacifico) or `FONT.body` (Inter) from design.tsx — never raw strings
- **No new colors**: Use `COLOR.*` from design.tsx to stay on-brand
