# YARNNN Voice & Brand

**Last consolidated:** 2026-03-13
**Replaces:** `_voice/kevin-voice.md`, `_voice/yarnnn-brand-voice.md`, `_voice/named-concepts.md`, `_creatives/_brand/BRAND.md`

---

## Two Voices

**The rule**: If the content's value comes from *who's saying it*, use Kevin's voice. If it comes from *what's being said*, use YARNNN brand voice.

---

## Kevin's Voice

**Use for**: Pillars 3 & 4, product demos, hot takes, replies, LinkedIn personal posts, Twitter, Reddit, Indie Hackers
**POV**: First person ("I built...", "I noticed...", "Here's what I learned...")
**Handoff-ready**: No — this voice is Kevin's permanently

### Tone

Warm but direct. Builder-authentic. Occasionally vulnerable. Opinionated without being combative. Smart friend who builds things explaining what they're working on.

### Rules

- First person always. "I" not "we."
- Specific > abstract. "I spent 45 minutes re-explaining my clients to ChatGPT" not "AI tools lack persistence."
- Pain before solution. Open with what's broken.
- No marketing language. Never "game-changing," "revolutionary," "cutting-edge," "unlock," "leverage."
- Honest about limitations. Credibility > polish.
- Numbers when available. "17,830 GitHub stars in 24 hours" not "massive traction."

### Kevin talks about

The CRM/GTM background. The ClawdBot/OpenClaw story. Building YARNNN solo — loneliness, clarity, tradeoffs. Specific moments: a deliverable that surprised him, a sync insight. Honest metrics even when small. AI news through the context/autonomy lens.

### Kevin doesn't talk about

Internal architecture details. Pricing strategy. Competitor bashing. Vague promises.

### Example openings

Good: "I use ChatGPT every day. Every day, it forgets everything." · "10 years in CRM taught me one thing: the problem is never intelligence. It's context." · "This week I watched my AI write a client update I would've spent an hour on. It got 80% right."

Bad: "Excited to announce..." · "In today's rapidly evolving AI landscape..." · "We believe the future of work is autonomous."

### Platform adjustments

| Platform | Kevin sounds like... | Never sounds like... |
|----------|---------------------|---------------------|
| Twitter | Sharpest, most compressed. One idea per tweet. | Reply-guy fishing for engagement |
| LinkedIn | Warmer, more narrative. Pain → insight arcs. | "Great post! I'd add..." followed by pitch |
| Reddit | Most conversational. "I built..." framing. | Founder doing market research disguised as conversation |
| HN | Technically-grounded, hard-won insight. | Marketer who learned enough vocab to pass |
| Indie Hackers | Most vulnerable. Real numbers, real challenges. | Polished startup narrative |

---

## YARNNN Brand Voice

**Use for**: Pillar 1 (Category Authority), Pillar 2a (thesis posts), canonical blog, Medium, LinkedIn articles
**POV**: Second/third person ("Your AI...", "YARNNN does...", "The system...")
**Handoff-ready**: Yes — a future GTM hire can write in this voice

### Tone

Authoritative but generous. Clear but not dumbed-down. Thesis-driven — every piece asserts a position. Think: Stripe's blog, not Salesforce's marketing page.

### Rules

- Assert a position. "Context is what makes AI autonomy meaningful" not "Context might help."
- Category-level framing. Speak to the AI space, not to consultants.
- Named concepts as contributions to discourse, not product features.
- Reference competitors by name. Specificity builds credibility and GEO adjacency.
- Structured for LLM consumption. Clear titles, direct opening paragraphs, defined terms.
- No hype. Never "revolutionary." Describe what happens and why it matters.
- Concede where appropriate. "ChatGPT is incredibly powerful" before explaining what it lacks.

### Example openings

Good: "Every AI agent startup makes the same architectural mistake: they build autonomy without context." · "ChatGPT is the most capable language model ever built. It also has no idea who you are."

Bad: "We're thrilled to introduce..." · "At YARNNN, we believe..." · "Our mission is to transform..."

### GEO-specific rules (blog/canonical)

- Title = query someone would ask an LLM
- First paragraph = direct answer (LLMs pull from first paragraphs)
- Reference known entities (ChatGPT, AutoGPT, Devin) for adjacency
- Define terms explicitly — definitions are highly citable

---

## Visual Identity

### Colors

| Role | Hex | Usage |
|------|-----|-------|
| Primary | `#F26522` | Logo, CTAs, emphasis accents |
| Dark BG | `#0A0A0A` | Dark-mode assets |
| Light BG | `#FFFFFF` | Light-mode assets, cards |
| Text/White | `#FFFFFF` | Headlines on dark backgrounds |
| Text/Dim | `#FFFFFF` @ 60% | Body copy on dark backgrounds |
| Text/Dark | `#111111` | Headlines on light backgrounds |

### Logo

Primary mark: orange yarn ball (circle). Files in `_creatives/_brand/`: `circleonly_yarnnn.png`, `yarn-logo-dark.png` (for light bg), `yarn-logo-light.png` (for dark bg), `circleonly_yarnnn_1.svg` (vector).

### Typography

Preferred: Inter (400, 500, 600, 700, 800). Fallback: -apple-system, system-ui, sans-serif. Headlines: Bold/ExtraBold, tight tracking (-0.02em).

---

## Ad Creative Guidelines

### Image rules

Purpose: brand recognition + scroll-stopping. NOT a second copy of the headline.

What works: Logo prominently, bold yarnnn.com, single accent color, high contrast.
What doesn't: Text paragraphs in the image, repeating the headline, busy compositions.
Scale test: if the image is 150px tall on a phone, can you still recognize it?
Max text in image: brand name or URL only (5 words absolute max).

### Platform specs

| Platform | Image size | Notes |
|----------|-----------|-------|
| Reddit | 1200×628 | Card format, image below text |
| LinkedIn | 1200×627 | Image primary, text truncates fast |
| Twitter/X | 1600×900 | Image dominates the card |
| General | 1200×1200 | Square fallback |

### File naming

`{platform}/{concept}-{variant}-v{version}.{ext}` — e.g. `reddit/monday-morning-v2.png`

Source files (HTML/SVG/PY) saved alongside PNGs for iteration.

### Tone by channel (ads)

| Channel | Dial up | Dial down |
|---------|---------|-----------|
| Reddit | Casual, blunt | Polish, jargon |
| LinkedIn | Professional | Casualness |
| Twitter/X | Punchy, witty | Length |
