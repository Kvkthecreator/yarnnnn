# Posting Workflow — Operational Guide

**Last updated:** 2026-02-25
**Method:** Claude in Chrome (visual browser automation)
**Requirement:** Browser tabs signed into each platform

---

## How It Works

Claude in Chrome can navigate to any platform you're signed into, interact with compose interfaces (click, type, submit), and take screenshots to verify results. No API keys, no developer accounts, no separate tooling.

### Confirmed Platforms

| Platform | URL | Status | Compose Method |
|----------|-----|--------|----------------|
| X/Twitter | x.com/home | Signed in (@KVKitsme) | Click "What's happening?" → type → Post button |
| LinkedIn | linkedin.com/company/99368741/admin/ | Signed in (yarnnn company page) | "+ Create" → "Start a post" → type → Post button |
| Medium | medium.com/new-story | Signed in | Click "Write" → type title + body → "..." menu for canonical URL → Publish |
| Reddit (r/yarnnn) | reddit.com/r/yarnnn | **Manual — Kevin posts** (Claude in Chrome blocked) | Kevin pastes prepared content directly |
| Reddit (high-traffic subs) | reddit.com/r/{subreddit} | **Manual — Kevin posts** (Claude in Chrome blocked) | Kevin pastes prepared content directly |
| yarnnn.com/blog | yarnnn.com | **No blog section yet — needs to be built in repo** | Deploy via repo (Next.js), not browser posting |

### What Was Tested (2026-02-25)

1. **X/Twitter:** Navigated → clicked compose box → typed test text → Post button became active → cleared text. Full compose chain works. Account: @KVKitsme.
2. **LinkedIn:** Navigated to yarnnn company page admin → clicked "+ Create" → "Start a post" → compose modal confirmed "yarnnn — Post to Anyone". Posts as company page, not personal profile.
3. **Medium:** Signed in. Import flow tested at `medium.com/p/import` — paste blog URL → Import → draft created with full article content. Title needs manual cleanup (remove " | yarnnn" suffix). YARNNN logo imports as first image and must be deleted. Drafts auto-save; publishing is manual. Manual compose ("Write") also works.
4. **Reddit:** Claude in Chrome blocks reddit.com (safety restriction). Cannot automate. Kevin posts manually. Reddit is a **core GEO channel** with a 2-track system: r/yarnnn (archive) + high-traffic subs (native discussion posts). See `_strategy/CONTENT_STRATEGY_v1.md` for full Reddit strategy.
5. **yarnnn.com/blog:** No blog route exists yet. Blog content is deployed via the Next.js repo, not browser posting.

---

## Execution Flow

### Step 1: Draft Content (in repo)
- Content lives in `content/posts/YYYY-WXX/` as markdown files
- Each file follows the relevant template from `content/_templates/`
- Voice guide from `content/_voice/` applied during drafting

### Step 2: Review
- Kevin reviews the draft in the markdown file
- Edits directly or gives feedback
- Marks status as `ready` when approved

### Step 3: Post via Browser
When Kevin says "post it":
1. Claude reads the approved content from the markdown file
2. Claude navigates to the target platform tab (already signed in)
3. Claude clicks into the compose interface
4. Claude types the content
5. **Claude asks Kevin for confirmation before clicking Post** (safety rule)
6. Kevin confirms → Claude clicks Post
7. Claude takes a screenshot as proof of publication
8. Claude updates the markdown file with: posted timestamp, URL (if available)

### Step 4: Record
- Update the calendar file (`content/calendar/2026-WXX.md`) status to `posted`
- Add the live URL to the post file

---

## Platform-Specific Notes

### X/Twitter — Single Tweet
- Navigate to x.com/home
- Click compose box ("What's happening?")
- Type content (max 280 chars)
- Confirm → click Post

### X/Twitter — Thread
- Click compose box, type first tweet
- Click the "+" button to add next tweet in thread
- Repeat for each tweet in the thread
- Confirm → click "Post all"

### LinkedIn — Company Page Post (CRITICAL: always post as yarnnn, NEVER as Kevin's personal profile)
- Navigate to linkedin.com/company/99368741/admin/dashboard/
- Click "+ Create" → "Start a post"
- Compose modal shows "yarnnn — Post to Anyone" (confirms posting as company page)
- Type content in the modal
- Confirm → click Post

### LinkedIn — Company Page Article
- Navigate to linkedin.com/company/99368741/admin/dashboard/
- Click "+ Create" → "Publish an article"
- Follow the article editor flow
- Confirm → click Publish

**CONSTRAINT:** Kevin's day company cannot know about yarnnn. All LinkedIn posting must be via the yarnnn company page admin, never Kevin's personal profile. If the compose modal doesn't show "yarnnn" as the poster, STOP and alert Kevin.

### Medium
- **Import method (preferred for cross-posts):** Navigate to `medium.com/p/import` → paste the yarnnn.com/blog URL → click Import → Medium pulls in the full article as a draft
- **After import:** Fix title (remove " | yarnnn" suffix that gets pulled from HTML `<title>`), delete the YARNNN logo image that imports as the first image
- **Draft behavior:** Medium auto-saves imported stories as drafts. They **cannot be published immediately** through the import flow — Kevin publishes manually when ready.
- **Manual method:** Navigate to medium.com → "Write" → type/paste content directly
- Set canonical URL (critical for GEO)
- Add tags
- Kevin publishes when ready

### Reddit — Track 1: r/yarnnn Archive (Kevin posts manually)

Claude in Chrome cannot automate Reddit (safety restriction). Claude prepares the content; Kevin posts it.

**File location:** `content/posts/reddit/track1/{pillar-folder}/`
- Files are organized by pillar: `pillar-1/`, `pillar-1b/`, `pillar-2a/`, etc.
- Each file is numbered sequentially across pillars (01-08 = Pillar 1, 09-17 = Pillar 1b, etc.)

**Workflow:**
1. Claude reads the approved blog post from the markdown file
2. Claude drafts a Reddit post in the markdown file with:
   - **Title:** Matches blog post title
   - **Body:** Full blog content, converted to Reddit markdown format (see Reddit Markdown below)
3. Claude presents the draft to Kevin for review
4. Kevin navigates to reddit.com/r/yarnnn → clicks "Create Post"
5. Kevin pastes the title and body
6. Kevin clicks Post
7. Kevin shares the Reddit URL with Claude
8. Claude updates the markdown file with: posted timestamp, Reddit URL

**Cadence:** Every Thursday long-form blog post gets an r/yarnnn cross-post. Build updates as they happen.

### Reddit — Track 2: Native Discussion Posts (Kevin posts manually)

These are NOT cross-posts. They're original posts written for each subreddit's culture.

**File location:** `content/posts/reddit/track2/{pillar-folder}/`
- Same pillar subfolder structure as Track 1
- Filename includes target subreddit: `09-personalization-trap-r-chatgpt.md`

**Workflow:**
1. During content pillar planning, Claude identifies 2-3 posts from the batch that are strongest for Reddit
2. Claude drafts Reddit-native versions using the `reddit-narrative.md` template, adapted to each target subreddit
3. **Claude converts markdown to Reddit format** (see Reddit Markdown below)
4. Kevin reviews — applying the value-first test: "Would this get upvoted even without the product mention?"
5. Kevin navigates to the target subreddit → clicks "Create Post"
6. Kevin pastes the title and body
7. Kevin clicks Post
8. Kevin shares the Reddit URL with Claude
9. Claude updates the content file with: posted timestamp, Reddit URL, subreddit name

**Cadence:** 2-3 posts per content pillar cycle. Max 1 post/month per high-traffic subreddit.

**Critical rules:**
- Kevin must check the subreddit rules before posting (some subs ban self-promotion or require minimum karma)
- Kevin should have existing comment history in a subreddit before posting original content there
- If a post doesn't pass the "upvoted without product mention" test, do NOT post it

### Reddit Markdown Conversion (IMPORTANT)

Reddit uses a slightly different markdown dialect. When preparing reddit posts, Claude MUST convert from standard markdown to Reddit markdown:

| Element | Standard Markdown | Reddit Markdown |
|---------|------------------|-----------------|
| Bullets | `- item` | `* item` |
| Italics | `_text_` | `*text*` |
| Bold | `**text**` | `**text**` (same) |
| Headers | `## Header` | `## Header` (same — ensure blank line before) |
| Links | `[text](url)` | `[text](url)` (same) |
| Quotes | `> text` | `> text` (same) |
| Strikethrough | `~~text~~` | `~~text~~` (same) |
| Superscript | N/A | `super^script` |
| Spoilers | N/A | `>!spoiler!<` |

**Key rules:**
- Always use `*` for unordered lists, not `-`
- Ensure blank line before headers and after paragraphs
- Reddit doesn't support nested headers well — avoid going deeper than `###`
- Reddit renders `_underscores_` inconsistently — always use `*asterisks*` for italics
- Numbered lists work the same: `1.` prefix
- Tables work but must have header row with `|---|` separator

**Conversion is done at file creation time** — all files in `content/posts/reddit/` should already be in Reddit markdown format, ready for Kevin to paste directly.

### Blog (yarnnn.com)
- This is deployed via the repo, not browser posting
- Write the blog post content → push to repo → Vercel deploys

---

## Requirements

1. **Claude in Chrome extension** must be connected (it is as of 2026-02-25)
2. **Browser tabs signed in** to each platform — keep persistent sessions
3. **Kevin's confirmation** before any Post/Publish click (non-negotiable safety rule)

## What This Replaces

- No Twitter/X API needed
- No developer accounts needed
- No OAuth token management
- No scheduling tools (for now — can revisit if needed)
- No separate posting scripts

## Limitations

- Requires an active browser session (tabs must be signed in)
- If a platform session expires, Kevin needs to re-login manually
- Thread posting on X requires multiple compose interactions (slower but works)
- Cannot schedule posts for future times (manual trigger only, which is what we chose)
