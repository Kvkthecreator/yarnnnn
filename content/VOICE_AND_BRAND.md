# YARNNN Voice & Brand

**Last consolidated:** 2026-03-16
**Replaces:** `_voice/kevin-voice.md`, `_voice/yarnnn-brand-voice.md`, `_voice/named-concepts.md`, `_creatives/_brand/BRAND.md`

---

## Three Voices

YARNNN operates in three distinct registers. They serve different purposes and should never be mixed.

| Voice | When | Register |
|-------|------|----------|
| **Kevin** | Engagement, build-in-public, replies, personal posts | Builder-authentic, first person, warm but direct |
| **YARNNN Brand** | Blog, canonical content, LinkedIn articles, GEO | Authoritative, thesis-driven, category-level |
| **YARNNN Ads** | Paid ads, landing page headlines, growth copy | Provocative, extremely short, outcome-only, zero functional language |

**The rules**: Kevin's voice = value comes from *who's saying it.* Brand voice = value comes from *what's being said.* Ad voice = value comes from *what the reader feels.*

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

### Readability (Kevin's voice)

Kevin's voice is naturally punchier than brand voice, but the same readability rules apply. Key additions for Kevin-authored content:

- **Lead with the opinion, not the setup.** "The SaaSpocalypse is aimed at the wrong target" not "In late February, markets erased hundreds of billions in value from enterprise software stocks."
- **Short paragraphs are the default.** Kevin's best social content uses 1-2 sentence paragraphs. Blog posts in Kevin's voice should do the same.
- **The LinkedIn version is the editing target.** When writing a Kevin-voice blog post, write the LinkedIn version (300-500 words) first. Then expand to blog length. This ensures the insight survives at every length.

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

### Readability rules (brand voice — applies to blog, Medium, LinkedIn articles)

These rules exist because our blog posts are intellectually rigorous but physically dense. The brand voice should feel *authoritative and generous*, not *academic and exhausting.* See `STRATEGY.md § Readability Standard` for full rationale.

- **Thesis in sentence one.** The opening sentence makes the claim. Not a setup, not a scene-setter, not "The AI industry has..." — the argument itself. Everything that follows is evidence.
- **Max 3 sentences per paragraph.** Dense 5-6 sentence blocks are the primary readability killer. Break them. Short paragraphs create visual rhythm and let important sentences breathe.
- **Bold one key sentence per section.** The sentence that, read alone, still communicates the section's point. This serves scanners and gives AI search engines a highlighted passage.
- **Kill hedges by default.** "To be fair," "there's a reasonable argument that," "these aren't necessarily competing" — these are reflex phrases that dilute every claim. Write the confident version first. Add qualification only when a specific claim genuinely requires it.
- **One analogy per argument.** If you need four examples to make one point, you don't trust the first example. Pick the strongest. The reader gets it.
- **Question-format H2 headers.** "The Retrieval Default" → "Why does the industry default to retrieval?" Questions serve scanners (should I read this section?) and GEO (query matching) simultaneously.
- **Paragraphs never start with "It's worth noting," "Interestingly," or "To be clear."** These are filler. Start with the substance.

### Example openings

Good: "Every AI agent startup makes the same architectural mistake: they build autonomy without context." · "ChatGPT is the most capable language model ever built. It also has no idea who you are."

Bad: "We're thrilled to introduce..." · "At YARNNN, we believe..." · "Our mission is to transform..."

### GEO-specific rules (blog/canonical)

- Title = query someone would ask an LLM
- First paragraph = direct answer (LLMs pull from first paragraphs)
- Reference known entities (ChatGPT, AutoGPT, Devin) for adjacency
- Define terms explicitly — definitions are highly citable

---

## YARNNN Ads Voice

**Use for**: Paid ads (Reddit, LinkedIn, Twitter/X), landing page headlines, growth copy, retargeting
**POV**: Second person implied ("you" is felt, rarely written). The reader is the subject.
**Handoff-ready**: Yes — but requires strict adherence to rules below

### Tone

Provocative. Extremely compressed. Outcome-only. The copy creates a feeling before the reader understands the product. Pattern-interrupts on a busy feed. Anti-marketing marketing.

### Rules

- The copy IS the ad. One line. No body text needed. No explainers.
- Sell feelings and outcomes, never features or integrations.
- Every ad targets a psychographic state, not a job title or industry.
- Must work alone on a 375px-wide mobile screen.
- Image does one job: brand recognition (logo + URL). Image never repeats or extends the headline.
- Zero functional language. If it sounds like a product spec, kill it.
- Uncomfortable > comfortable. The best ads make the reader feel something before they click.

### Target psychographic

People who are anxious about the AI revolution. They see AI agents everywhere on social media. They feel almost left behind. They use ChatGPT daily but aren't fully satisfied. They've heard of things like ClawdBot, OpenClaw, Claude, Cowork — but hit the setup wall or never tried. They're early adopters who aren't developers.

They don't think in terms of workflows and integrations. They think in terms of outcomes and feelings.

### YARNNN ads never say

- "Connects to your tools" / "integrates with Slack, Gmail, Notion"
- "Reduces friction" / "streamlines your workflow"
- "AI-powered" / "leveraging AI"
- "Game-changing" / "revolutionary" / "cutting-edge"
- Any sentence that lists capabilities or features
- Any sentence that requires understanding the tooling landscape
- Any sentence longer than ~10 words

### YARNNN ads always do

- Create urgency, curiosity, or social pressure in under 10 words
- Make the reader imagine using the product before they understand what it is
- Sound like something a friend would text you, not something a company would email you
- Differentiate from every other AI tool ad on the same feed

### Why not Claude's approach

Claude/Anthropic ads are functional and capability-focused: "sets up your Asana boards," "drafts Slack updates," "works with your tools." Every visual shows a task performed in a specific tool. This targets people who already understand the tooling landscape and want workflow optimization.

YARNNN deliberately avoids this because: (1) we can't out-design or out-spend Anthropic on polished capability demos, (2) functional positioning sounds like every other AI tool, (3) our target psychographic doesn't think in workflows — they think in outcomes, (4) YARNNN's actual differentiator (scheduled autonomous execution) is invisible in a functional framing.

Full competitive teardown: `_creatives/_reference/claude-linkedin-carousel.md`

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

### The Collective Principle

An ad is a system of parts — image, headline, body, CTA — each with one job. Parts supplement, never repeat. The headline carries the message. The image carries the brand. Together they form the ad. Separately they do nothing.

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

| Channel | Psychographic trigger | Dial up | Dial down |
|---------|-----------------------|---------|-----------|
| Reddit | "Am I behind?" / "Is this a cheat code?" | Casual, blunt, provocative | Polish, jargon, feature lists |
| LinkedIn | "Everyone's talking about AI agents" | Professional urgency | Casualness, technical specs |
| Twitter/X | "Wait, what is this?" | Punchy, witty, pattern-interrupt | Length, explanations |

### Testing framework

Run bets as separate ad sets under psychographic targeting. Same image (logo + yarnnn.com), same CTA, same destination URL. Only the headline copy changes. Lowest CAC after 2 weeks wins and gets scaled. See STRATEGY.md § Paid Ads for the four active bets.
