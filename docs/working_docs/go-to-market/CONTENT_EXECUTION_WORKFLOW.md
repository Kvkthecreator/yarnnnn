# YARNNN Content Execution Workflow

**Date:** 2026-02-25
**Status:** Working draft
**Depends on:** [CONTENT_STRATEGY_v1.md](CONTENT_STRATEGY_v1.md)
**Purpose:** Make the content strategy executable, repeatable, and autonomous using Claude in Cowork mode + Chrome browser extension.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                 yarnnn/content/                       │
│           (inside existing repo folder)               │
│                                                       │
│  _strategy/    ← Strategy + GEO targets              │
│  _templates/   ← Reusable post templates per platform │
│  _voice/       ← Voice guides + named concepts        │
│  calendar/     ← Weekly plans                         │
│  posts/        ← All content (draft → published)      │
│  metrics/      ← Engagement tracking + GEO checks     │
└──────────────┬────────────────────────────────────────┘
               │
               │  Claude drafts content locally,
               │  then posts directly via browser
               │
               ▼
┌─────────────────────────────────────────────────────┐
│            CLAUDE IN CHROME (Browser Tabs)            │
│                                                       │
│  Tab 1: Twitter/X (logged in as Kevin)               │
│  Tab 2: LinkedIn (logged in as Kevin)                │
│  Tab 3: Medium / yarnnn blog (logged in)             │
│  Tab 4: Reddit (logged in — only when needed)        │
│                                                       │
│  Claude types content → publishes → records URL       │
│  Reports results back to Kevin                        │
└─────────────────────────────────────────────────────┘
```

**Key principles:**
- **No review gates.** Claude drafts and posts directly. Nothing in this content is sensitive or confidential.
- **Modifications happen separately.** If something needs changing after posting, that's a separate workflow — not a pre-publish gate.
- **Everything lives in the repo.** `yarnnn/content/` is the single source of truth. No external tools needed.

---

## 2. Folder Structure

```
yarnnn/content/
│
├── _strategy/
│   ├── CONTENT_STRATEGY_v1.md        ← Symlink or copy from docs/working_docs/
│   └── GEO_QUERY_TARGETS.md          ← Target queries for GEO tracking
│
├── _templates/
│   ├── twitter-thread.md
│   ├── twitter-single.md
│   ├── linkedin-personal.md
│   ├── linkedin-article.md
│   ├── blog-canonical.md
│   ├── reddit-narrative.md
│   └── medium-crosspost.md
│
├── _voice/
│   ├── kevin-voice.md
│   ├── yarnnn-brand-voice.md
│   └── named-concepts.md
│
├── calendar/
│   └── 2026-W09.md                   ← One file per week
│
├── posts/
│   └── 2026-02-25-context-gap-twitter/
│       ├── content.md                ← The post content
│       └── meta.md                   ← Metadata + post-publish info
│
└── metrics/
    ├── weekly-2026-W09.md
    └── geo-checks/
        └── 2026-03.md
```

### Naming Convention for Posts

`YYYY-MM-DD-[slug]-[platform]/`

Examples:
- `2026-02-25-context-gap-twitter/`
- `2026-02-27-90-day-moat-linkedin/`
- `2026-02-27-context-vs-memory-blog/`

### meta.md Template

```markdown
# Meta

- **Pillar:** 1 (Category Authority)
- **Layer:** Discovery
- **Concept:** The Context Gap
- **GEO Tier:** Tier 1
- **Platform:** Twitter (thread)
- **Voice:** Kevin
- **Target Query:** "why AI agents produce generic output"
- **Published:** 2026-02-25 10:30 PST
- **URL:** https://twitter.com/kvkthecreator/status/...
- **Engagement (last check):** 340 impressions, 12 likes, 3 replies
```

---

## 3. Execution Flow

### The Cycle (Weekly)

```
1. PLAN    → Claude creates calendar/2026-WXX.md
2. DRAFT   → Claude creates posts in posts/ (content.md + meta.md)
3. POST    → Claude opens browser tabs, publishes each post directly
4. REPORT  → Claude updates meta.md with URLs, reports back to Kevin
5. MEASURE → Claude checks engagement at end of week, writes metrics/
```

No gates between steps. Claude runs 1→2→3→4 in a single session if all platform tabs are ready, or across multiple sessions if preferred.

---

## 4. Claude Session Instructions

### Session: "Run This Week's Content"

**Trigger:** Kevin says something like "run this week's content" or "do the content cycle"
**Duration:** ~30-45 min for full plan + draft + post cycle
**Tabs needed:** Platform tabs open and logged in

**Steps:**

**1. Plan**
- Read `_strategy/CONTENT_STRATEGY_v1.md` for pillars, cadence, GEO rotation
- Read most recent `calendar/` file for context on what's been done
- Read most recent `metrics/` file if available for what performed
- Create `calendar/2026-WXX.md`:

```markdown
# Week XX (Mon [date] – Fri [date])

| Day | Pillar | Platform | Concept | Voice | Hook |
|-----|--------|----------|---------|-------|------|
| Mon | P1 | Twitter | Context Gap | Kevin | "Every AI agent disappoints for the same reason..." |
| Tue | P2a | LinkedIn | Autonomy Spectrum | Kevin | "I spent 10 years building context systems..." |
| Wed | P3 | Twitter | — | Kevin | "This week: YARNNN reads your Notion pages..." |
| Thu | P1 | Blog + Medium | 90-Day Moat | YARNNN | "The 90-Day Moat: Why Your AI Gets Better" |
| Fri | P4 | Twitter | ClawdBot | Kevin | "17,830 stars in 24 hours. Here's what they wanted." |

**GEO rotation:** Week X = Tier [1/3/4] — [description]
**Notes:** [any timely hooks or adjustments]
```

**2. Draft**
- Read relevant template from `_templates/`
- Read relevant voice guide from `_voice/`
- For each post, create `posts/YYYY-MM-DD-[slug]-[platform]/content.md` + `meta.md`
- Quality self-check per post:
  - Connects to at least one named concept?
  - Correct voice (Kevin vs. YARNNN brand)?
  - Pillar 1 is category-level, NOT consultant-specific?
  - GEO content title/opening matches target query?
  - Platform format correct (char limits, structure)?
  - No internal jargon?

**3. Post**
- Open the platform tab for today's post
- Navigate to compose interface
- Type the content from `content.md`
- Publish directly (no confirmation needed)
- Screenshot the published post
- Update `meta.md` with published timestamp and URL

**4. Report**
- Tell Kevin what was posted: platform, hook, URL
- Share the screenshot
- Note any issues (platform errors, formatting problems)

---

### Session: "Post Today's Content"

**Trigger:** Kevin says "post today's content" (when drafts already exist from a prior planning session)
**Duration:** ~5 min per post
**Tabs needed:** Relevant platform tab

**Steps:**
1. Read today's post from `posts/` (based on `calendar/` schedule)
2. Open platform tab → compose → type → publish
3. Update `meta.md` with URL
4. Report back to Kevin

---

### Session: "Weekly Metrics"

**Trigger:** Kevin says "check this week's content" or "how did the posts do"
**Duration:** ~10 min
**Tabs needed:** Platform tabs (to check engagement)

**Steps:**
1. Open each platform and check engagement on this week's published posts
2. Create `metrics/weekly-2026-WXX.md`:

```markdown
# Week XX Performance

| Date | Platform | Concept | Impressions | Engagement | Notes |
|------|----------|---------|-------------|------------|-------|
| 02-25 | Twitter | Context Gap | 340 | 12 likes, 3 replies | Replies asked for more detail |
| 02-26 | LinkedIn | Autonomy Spectrum | 890 | 24 reactions, 2 DMs | DMs from consultants |
| ... | ... | ... | ... | ... | ... |

## What Worked
- [Concept/pillar/platform that performed best]

## What to Adjust
- [Changes for next week]
```

3. Update each post's `meta.md` with latest engagement numbers
4. Report summary to Kevin

---

### Session: "Monthly GEO Check"

**Trigger:** First week of each month, or Kevin asks "check GEO"
**Duration:** ~15 min
**Tabs needed:** ChatGPT, Claude.ai, Gemini tabs

**Steps:**
1. Open each LLM in a browser tab
2. Ask each the target queries from `_strategy/GEO_QUERY_TARGETS.md`
3. Record results in `metrics/geo-checks/2026-MM.md`
4. Report to Kevin: is YARNNN showing up? Which queries? Progress vs. last month?

---

## 5. Browser Tab Setup

Before any posting session, these tabs must be open and **already logged in**:

| Tab | URL | Account |
|-----|-----|---------|
| 1 | twitter.com | @kvkthecreator |
| 2 | linkedin.com | Kevin's profile |
| 3 | medium.com | YARNNN or Kevin |
| 4 | reddit.com | Kevin's account (only when Reddit post scheduled) |

Claude does NOT log into accounts. All tabs must be pre-authenticated.

### Platform-Specific Notes

**Twitter threads:** Compose first tweet, use "+" to add each subsequent tweet.
**Twitter singles:** Type in the tweet box and post.
**LinkedIn posts:** "Start a post" from the feed. Verify preview looks right.
**LinkedIn articles:** "Write article" from post creation menu.
**Medium:** "New story" → set title → paste body → add tags → publish with canonical URL.
**Reddit:** Navigate to subreddit → "Create post" → text format. Must be value-first, no marketing language.

---

## 6. Templates

Templates live in `content/_templates/`. Claude reads these before drafting to ensure consistent structure.

### twitter-thread.md

```
Tweet 1 (Hook): Sharp, standalone, under 200 chars. Tease the insight.
Tweet 2 (Problem): Expand the pain. Make it visceral.
Tweet 3 (Insight): Introduce the named concept explicitly.
Tweet 4 (Evidence): Proof, example, analogy. Make it concrete.
Tweet 5 (Implication): What this means for the reader. Why care?
Tweet 6 (Close, optional): Engagement prompt. Soft link to yarnnn.com only if natural.

Max 6 tweets. No hashtags unless trending. End with a question, not a CTA.
```

### twitter-single.md

```
Max 280 chars. Sharp, opinionated, thesis-connected.
One named concept per tweet.
No hashtags. No links unless essential.
```

### linkedin-personal.md

```
500-800 words. Pain → Insight → Solution arc.
Voice: Kevin. First person, professional but warm.

Line 1-2 (Hook): Must stop the scroll. Pain-first, personal, specific.
  Example: "I spent 45 minutes this morning re-explaining my clients to ChatGPT. Again."

Body (Pain): 2-3 paragraphs. Relatable. Specific details consultants/founders recognize.
Body (Insight): 1-2 paragraphs. Introduce named concept naturally, not as marketing.
Body (Implication): 1-2 paragraphs. What it means. Where things are heading.

Close: Engagement prompt (question that invites comments).
  Example: "What's the most tedious recurring deliverable in your work?"

Hashtags: Max 3. Only if genuinely relevant.
```

### blog-canonical.md

```
1,500-2,500 words. GEO-optimized.
Voice: YARNNN brand. Authoritative, clear, generous.

Title: Must match a target GEO query.
  e.g., "What Is Context-Powered Autonomy?"

Opening paragraph: Directly answer the title question in 2-3 sentences.
  LLMs pull from first paragraphs. Make it self-contained and quotable.

Section 1 (Problem): What's broken. Reference competitors by name (GEO adjacency).
Section 2 (Framework): Define the named concept clearly.
Section 3 (How It Works): Concrete examples. Can reference YARNNN specifically.
Section 4 (Comparison): How YARNNN differs from alternatives. High GEO value.
Closing: Restate thesis. Link to related canonical posts.
```

### reddit-narrative.md

```
Value-first. No marketing language.
"I noticed..." or "I built..." framing.
Must pass: "Would this get upvoted even without the product mention?"
Max 1 post/month per subreddit. Comments > original posts.
```

---

## 7. Iteration Workflow (Separate from Posting)

If Kevin wants to modify published content or adjust strategy based on results:

**"Revise a post":** Kevin shares the post URL or slug. Claude reads the original from `posts/`, makes changes, and reposts or edits in-platform if the platform allows.

**"Adjust strategy":** Kevin shares observations. Claude updates `_strategy/CONTENT_STRATEGY_v1.md` and adjusts upcoming `calendar/` entries.

**"Change templates":** Claude updates `_templates/` based on what's performing.

These are ad-hoc — triggered by Kevin, not scheduled.

---

## 8. Quick Start

1. **Folder structure:** Already created at `yarnnn/content/`
2. **Next:** Tell Claude "populate the templates and voice guides"
3. **Then:** "Plan and draft this week's content"
4. **Then:** Open browser tabs (pre-logged-in) and say "post today's content"

That's it. No setup beyond what exists right now.
