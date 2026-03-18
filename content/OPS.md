# YARNNN Content Ops

**Last consolidated:** 2026-03-16
**Replaces:** `_ops/POSTING_WORKFLOW.md`, `_templates/*.md` (7 files), `calendar/` format docs

---

## Posting Workflow

### Method

Claude in Chrome (visual browser automation). No APIs, no developer accounts. Requires browser tabs signed into each platform.

### Platforms

| Platform | Status | Method |
|----------|--------|--------|
| Twitter/X (@KVKitsme) | Signed in (Premium) | Claude navigates, types, posts (with Kevin's confirmation). Threads + Articles available. |
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
- **X Articles**: Always publish blog first (24-48h lead time for Google indexing). Include "Originally published at yarnnn.com/blog/[slug]" at the bottom. For high-priority posts, publish a thread on blog day AND an X Article 3-7 days later — thread for reach, article for depth/permanence.

---

## Templates

### Blog Post (yarnnn.com/blog)

**Updated 2026-03-16.** See `STRATEGY.md § Readability Standard` for full rationale.

Two formats. Both use YARNNN brand voice + readability rules from `VOICE_AND_BRAND.md`.

#### Standalone post (800-1,200 words)

The default format. Every sentence earns its place.

```
Title — makes the claim (matches a GEO query)

[1-2 sentences] — States the complete thesis. This IS the answer.
A reader who stops here still knows the argument.

---

## [Question-format H2] — Core argument (~400 words)
Evidence, examples, specific data points (2-3 citations).
Max 3 sentences per paragraph. Bold one key sentence.

## [Question-format H2] — Nuance or counterargument (~300 words)
Where the thesis gets complicated. Concede what's fair.
One analogy max.

## [Question-format H2] — What this means (~200 words)
Implications for the reader. Why they should care now.

Related reading links. No hard CTA.
```

#### Pillar/hub post (1,500-2,000 words)

Reserved for the 5 hub pages (see `STRATEGY.md § Consolidation Plan`). Same readability rules but more sections and deeper evidence. Refreshed quarterly.

```
Title — definitive claim for the theme cluster

[2-3 sentences] — Complete thesis. Self-contained, quotable, GEO-citable.

## [Question H2] — The problem (reference competitors by name)
## [Question H2] — The framework (define the named concept)
## [Question H2] — How it works (concrete examples, can reference YARNNN)
## [Question H2] — Comparison (YARNNN vs alternatives, high GEO value)
## [Question H2] — Open questions (intellectual honesty)

Related spoke links. No hard CTA.
```

#### Blog post checklist

- [ ] Title matches a GEO target query?
- [ ] Thesis stated in first 30 words?
- [ ] First 150 words form a complete, quotable answer?
- [ ] H2 headers are question-format?
- [ ] Each section has one bolded key sentence?
- [ ] No paragraph exceeds 3 sentences?
- [ ] Hedges removed unless specifically necessary?
- [ ] Max one analogy per argument?
- [ ] 2-3 statistics or citations included?
- [ ] Named concept defined? Competitors referenced?
- [ ] Internal links to hub page (if spoke) or to spokes (if hub)?
- [ ] Word count within range? (800-1,200 standalone / 1,500-2,000 hub)

#### Cross-posting pipeline (every blog post)

**Atomic content approach:** Don't write 1,200 words then compress. Start small, expand up.

1. **Blog post** (800-1,500 words) — full argument with evidence, committed to repo
2. **LinkedIn company post** (200-400 words) — condensed version posted to yarnnn company page. Includes blog URL at bottom.
3. **X/Twitter post** (<280 chars) — sharp thesis + blog URL. URLs count as 23 chars regardless of length.
4. **X Article** — full cross-post from blog (see X Article template below). Published 3-7 days after blog for depth/permanence/indexing.
5. **Medium draft** — full article pasted via browser, saved as draft. Set canonical URL on publish. Within 1 week of blog.

**Execution method:** Claude in Chrome (visual browser automation). For each platform:
- **LinkedIn**: Navigate to yarnnn company page → "+ Create" → "Start a post" → type content directly into composer → click Post. Note: LinkedIn's Quill editor sometimes requires JS injection (`editor.innerHTML = ...`) if direct typing fails.
- **X/Twitter**: Navigate to `x.com/compose/post` → type tweet → verify character count (circle must be blue, not red) → click Post. For threads, use the "+" button to add tweets.
- **X Articles**: Navigate to `x.com/compose/article` → type/paste content → publish. Include "Originally published at yarnnn.com/blog/[slug]" at bottom.
- **Medium**: Navigate to `medium.com/new-story` → type title → press Enter → paste body via ClipboardEvent JS injection into ProseMirror editor → saves as draft automatically.

**Timing:** Blog commit first (push to deploy). LinkedIn + X tweet same session. X Article 3-7 days later. Medium within 1 week. Reddit when natural opportunity arises.

This ensures every piece of content has a natural short form at every length. The blog post isn't the source that gets compressed — the insight is the source that gets expanded per platform.

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

### X Article

**Added 2026-03-16.** Requires X Premium.

800-1,200 words. Kevin's voice or YARNNN brand (match the blog post's voice). Cross-post from Thursday blog content — X Articles are the X-native equivalent of Medium cross-posts.

**Why X Articles matter**: X Articles live on x.com, get indexed by Google, are shareable as native X content, and show up in X search. Unlike threads, they don't fragment the argument across tweets. Unlike external links, they don't get algorithmic suppression. This is the best of both worlds for long-form on X.

**Structure**: Same as the blog post. Don't rewrite — adapt lightly for the platform.

**Canonical note**: X Articles don't support canonical URL tags the way Medium does. To protect SEO, blog goes live first and gets indexed (24-48h minimum) before the X Article publishes. The X Article should include a "Originally published at yarnnn.com/blog/[slug]" line at the bottom.

**Cross-posting with threads**: For high-priority posts, publish BOTH a thread (day of blog publish, for engagement/reach) AND an X Article (3-7 days later, for depth/indexing/permanence). The thread hooks attention; the article captures readers who want the full argument without leaving X.

**File location**: `posts/x-articles/` (create as needed, matching blog post slugs).

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

800-1,200 words. YARNNN brand voice. Cross-post Thursday blog content. Same readability rules as blog (question H2s, short paragraphs, bolded key sentences).

Title + thesis opening + 3-5 sections with question subheads + closing. Include author tagline. No product pitch.

---

### Medium Cross-Post

Import from `medium.com/p/import` → fix title (remove " | yarnnn") → delete imported logo → set canonical URL → add 3-5 tags → Kevin publishes.

Tags: "Artificial Intelligence," "AI Agents," "Productivity," "Technology," "Future of Work."

Publish within 1 week of blog going live (was 24h — giving Google more indexing time first). Never edit Medium independently.

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
| Thursday | P1 or P2 (Long-form) | Blog + Twitter thread + LinkedIn article | YARNNN brand | Canonical GEO content. Thread same day. |
| Mon-Wed (following week) | — | X Article + Medium | Match blog voice | Cross-post last Thursday's blog. X Article first, Medium second. |
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
│   ├── x-articles/      ← X Article cross-posts (match blog slugs)
│   ├── medium/
│   └── {blog posts}
├── calendar/            ← weekly planning files (2026-WXX.md)
├── _creatives/
│   ├── _brand/          ← logo files (visual assets only)
│   └── _reference/      ← competitive teardowns
└── _archive/            ← superseded strategy docs
```
