# YARNNN Content Ops

**Last consolidated:** 2026-03-13
**Replaces:** `_ops/POSTING_WORKFLOW.md`, `_templates/*.md` (7 files), `calendar/` format docs

---

## Posting Workflow

### Method

Claude in Chrome (visual browser automation). No APIs, no developer accounts. Requires browser tabs signed into each platform.

### Platforms

| Platform | Status | Method |
|----------|--------|--------|
| Twitter/X (@KVKitsme) | Signed in | Claude navigates, types, posts (with Kevin's confirmation) |
| LinkedIn (yarnnn company page) | Signed in | Claude posts as company page via `linkedin.com/company/99368741/admin/dashboard/` |
| Medium | Signed in | Import from blog URL preferred; manual compose also works |
| Reddit | **Kevin posts manually** | Claude in Chrome blocked on Reddit. Claude drafts, Kevin pastes. |
| yarnnn.com/blog | Via repo | Next.js deploy, not browser posting |

### Execution Flow

1. **Draft** — Content in `content/posts/` as markdown. Follow templates below.
2. **Review** — Kevin reviews. Edits or gives feedback. Marks `ready`.
3. **Post** — Claude reads content → navigates to platform → types → **asks Kevin to confirm before clicking Post** → screenshots as proof.
4. **Record** — Update calendar file with posted timestamp and URL.

### Critical Constraints

- **LinkedIn**: ALWAYS post as yarnnn company page, NEVER Kevin's personal profile. If compose modal doesn't show "yarnnn" as poster, STOP.
- **Medium**: Set canonical URL to yarnnn.com/blog version. Remove logo image that imports. Fix title suffix.
- **Reddit**: Kevin must have comment history in a subreddit before posting. Max 1 post/month per high-traffic sub.
- **Reddit markdown**: Use `*` for bullets (not `-`), `*text*` for italics (not `_text_`). Files in `posts/reddit/` should already be in Reddit format.

---

## Templates

### Blog Post (yarnnn.com/blog)

1,500-2,500 words. YARNNN brand voice.

**Title**: Match a GEO target query.
**Opening (2-3 sentences)**: Directly answer the title question. Self-contained, quotable. LLMs pull from first paragraphs.
**Section 1 — The Problem**: What's broken. Reference competitors by name.
**Section 2 — The Framework**: Define the named concept. The intellectual contribution.
**Section 3 — How It Works** (optional): Concrete examples. Can reference YARNNN.
**Section 4 — Comparison**: YARNNN vs alternatives. High GEO value.
**Closing**: Restate thesis. Link to related canonical posts. No hard CTA.

Checklist: Title matches GEO query? Opening answers it? Named concept defined? Competitors referenced? LLM would cite this?

---

### Twitter Single

Max 280 chars. Kevin's voice.

One idea. Sharp, opinionated, thesis-connected. Types: hot take, pain observation, reframe, question, build milestone.

No hashtags. No links (kills engagement). Must connect to thesis.

---

### Twitter Thread

4-6 tweets. Kevin's voice (or YARNNN brand for thesis threads).

1. **Hook** (<200 chars) — standalone, stops scrolling
2. **Problem** — visceral, specific pain
3. **Insight** — named concept, original thinking
4. **Evidence** — proof, example, data
5. **Implication** — why should reader care
6. **Close** (optional) — engagement question, soft link only if natural

Each tweet must work in isolation. End with a question, not a CTA.

---

### LinkedIn Personal Post

500-800 words. Kevin's voice.

**Line 1-2 — Hook** (critical, truncation happens here): Pain-first, specific.
**Body — Pain** (2-3 paras): Details consultants/professionals recognize.
**Body — Insight** (1-2 paras): Named concept introduced naturally.
**Body — Implication** (1-2 paras): What this means.
**Close**: Engagement question. NOT a CTA.

Max 3 hashtags. No links in body. Short paragraphs, white space.

---

### LinkedIn Article

1,000-1,500 words. YARNNN brand voice. Cross-post Thursday blog content.

Title + thesis opening + 3-5 sections with subheads + closing. Include author tagline. No product pitch.

---

### Medium Cross-Post

Import from `medium.com/p/import` → fix title (remove " | yarnnn") → delete imported logo → set canonical URL → add 3-5 tags → Kevin publishes.

Tags: "Artificial Intelligence," "AI Agents," "Productivity," "Technology," "Future of Work."

Publish within 24h of blog going live. Never edit Medium independently.

---

### Reddit (2-Track)

**Track 1 (r/yarnnn archive)**: Title matches blog post. Body = 2-3 sentence summary + canonical link + optional personal context.

**Track 2 (high-traffic subs)**: Original posts, subreddit-native framing. NOT cross-posts.

| Subreddit | Framing style |
|-----------|---------------|
| r/ChatGPT | Problem/solution from user perspective |
| r/artificial | Technical/conceptual |
| r/singularity | Novel framework, big-picture |
| r/consulting | Operational pain |
| r/startups | Build-in-public |

Value-first test: "Would this get upvoted without the product mention?" If no, rewrite.

File location: `posts/reddit/track1/{pillar}/` and `posts/reddit/track2/{pillar}/`

---

## Weekly Calendar Pattern

| Day | Pillar | Platform | Voice | Format |
|-----|--------|----------|-------|--------|
| Monday | P1 (Category) | Twitter + LinkedIn | YARNNN/Kevin | Short: sharp take through thesis lens |
| Tuesday | P2a (Thesis) or P4 (Founder) | LinkedIn personal | Kevin | 500-800 word narrative |
| Wednesday | P3 (Build-in-Public) | Twitter | Kevin | Build update connected to thesis |
| Thursday | P1 or P2 (Long-form) | Blog + Medium + LinkedIn article | YARNNN brand | Canonical GEO content |
| Friday | P4 (Founder) or P2a | Twitter | Kevin | Personal take, ClawdBot, hot take |

### Monthly Thursday Rotation (GEO)

Week 1: Tier 1 — Canonical concept definition
Week 2: Tier 3 — Category-level comparison
Week 3: Tier 1 — Different concept
Week 4: Tier 4 — Query-matching answer

---

## File Organization

```
content/
├── STRATEGY.md          ← what we do and why
├── VOICE_AND_BRAND.md   ← how we sound and look
├── OPS.md               ← how we execute (this file)
├── posts/               ← all published/draft content
│   ├── reddit/track1/
│   ├── reddit/track2/
│   ├── twitter/
│   ├── medium/
│   └── {blog posts}
├── calendar/            ← weekly planning files (2026-WXX.md)
├── _creatives/
│   ├── _brand/          ← logo files (visual assets only)
│   └── _reference/      ← competitive teardowns
└── _archive/            ← superseded strategy docs
```
