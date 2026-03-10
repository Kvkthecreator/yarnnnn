# Landing Page Narrative V2

**Date**: 2026-02-11
**Status**: Draft
**Purpose**: Define the evolved narrative for landing page revamp

---

## Core Narrative Shift

### Before (v1)
> "The things you send every week—written for you, getting better each time."

Focus: Output automation + learning loop

### After (v2)
> "yarnnn reads your Slack, Gmail, Notion, and Calendar—then writes the updates you owe people."

Focus: **Platform intelligence** + **emergent suggestions**

### Why Name the Platforms

Apple says "M3 chip" not "faster processor." Specificity builds credibility.

- **Slack, Gmail, Notion, Calendar** are recognizable—people immediately know if this is for them
- Shows we built something purpose-fit, not generic
- The platform names carry meaning (collaboration, communication, documentation, schedule)
- Avoids vague "connect your tools" language that sounds like every other integration

### But Also: Bring Your Own Data

The three platforms are the headline, but yarnnn works with any context you give it:

- **Paste in context** — Copy text from anywhere, yarnnn uses it
- **Describe what you know** — Just tell yarnnn what happened this week
- **More platforms coming** — Linear, Jira, Google Docs, etc.

**How to message this:**
> "yarnnn connects to Slack, Gmail, and Notion. Don't use those? You can paste in context or describe what you need—yarnnn works with whatever you give it."

This keeps the specificity of named platforms while leaving the door open. The headline stays concrete; the escape hatch is visible but secondary.

---

## The Two Big Ideas

### 1. Platform Intelligence

**Not this:** "Connect your tools so yarnnn can pull data"
**This:** "yarnnn understands what's happening in your tools"

What makes this different:

| Tool | What most apps see | What yarnnn sees |
|------|-------------------|------------------|
| **Slack** | Messages in a channel | Which threads are heating up. Who's waiting for answers. What decisions got made. |
| **Gmail** | Emails in your inbox | Which threads need replies. Who you haven't gotten back to. What's urgent vs. routine. |
| **Notion** | Pages and databases | What changed recently. Which docs are going stale. Where decisions are documented. |
| **Calendar** | A list of meetings | Who you're meeting with. What context you need. Which 1:1s are coming up. |

**The insight:** Your platforms already contain the signal. yarnnn reads it the way you would—if you had time to read everything.

### 2. Emergent Suggestions

**Not this:** "Set up your deliverables and yarnnn will write them"
**This:** "yarnnn notices what you need and offers to handle it"

How it works:

- You ask yarnnn to catch you up on Slack a few times
- yarnnn notices the pattern
- yarnnn offers: "Want me to send you a weekly digest every Monday?"

**The insight:** You shouldn't have to know what to automate. yarnnn figures it out from how you work.

---

## Narrative Flow (Home Page)

### Hero

**Headline:**
> yarnnn reads your Slack, Gmail, Notion, and Calendar—then writes the updates you owe people.

**Subhead:**
> Status reports. Investor updates. Meeting prep. yarnnn pulls context from your platforms, drafts it in your voice, and gets better every time you approve.

**CTA:** Start for free

**Secondary note (smaller text below CTA):**
> Don't use these platforms? You can paste in context or describe what you need—yarnnn works with whatever you give it.

---

**Alternative headlines (for testing):**

> Your Slack has the updates. Your Gmail has the threads. Your Notion has the notes. yarnnn turns them into the things you send.

> yarnnn connects to Slack, Gmail, and Notion. Reads what happened. Writes what you owe people.

> Status reports from your Slack. Investor updates from your Notion. Client briefs from your Gmail. Written by yarnnn, approved by you.

---

### Section 1: The Problem

**Header:** You already know what happened. Writing it up is the chore.

**Body:**
The context is there. Slack has the updates. Gmail has the threads. Notion has the notes. But every week you still spend hours pulling it together into something sendable.

It's not thinking work. It's just assembly.

**Visual opportunity:** Show scattered platforms → assembled update

---

### Section 2: Platform Intelligence

**Header:** yarnnn doesn't just pull messages. It understands what's happening.

**Body:**
Most integrations dump raw data. yarnnn reads your platforms the way you would—if you had time to read everything.

**Four cards (with platform icons):**

**Slack**
> Hot threads. Decisions made. Questions still waiting for answers. yarnnn sees the signal, not just the messages.

**Gmail**
> Who needs a reply. What's actually urgent. Threads that have gone cold. yarnnn reads your inbox like you do on a good day.

**Notion**
> Recent changes. Stale docs. Where decisions are documented. yarnnn knows what's current and what's not.

**Calendar**
> Who you're meeting. When you're meeting them. What context you need before you walk in. yarnnn connects meetings to everything else.

**Visual opportunity:** Platform icon + specific signal examples:
- Slack: thread with 12 replies + fire icon, message with ❓ + "unanswered" label
- Gmail: thread with "3 days" badge, sender with importance indicator
- Notion: page with "edited 2h ago" badge, page with "last touched 3 months ago" warning
- Calendar: event card with attendee avatars, "in 2 hours" badge, linked Slack/Gmail context

**Tagline for section:** "Four platforms. One intelligent reader."

**Future platforms teaser (subtle, below the cards):**
> Linear, Jira, Google Docs, GitHub, and more on the way. Want something specific? [Let us know →]

---

### Section 3: It Suggests What You Need

**Header:** yarnnn notices patterns. Then offers to automate them.

**Body:**
Ask yarnnn to summarize #engineering a few times. It notices. Then it offers: "Want me to send you a digest every Monday?"

Same for stakeholders. If you keep mentioning your manager or a specific client, yarnnn suggests a recurring update for them.

You don't configure automations. You just work. yarnnn figures out what's worth automating.

**Visual opportunity:** Side-by-side showing pattern → suggestion

**Left side (the pattern):**
```
Monday: "Catch me up on #engineering"
Wednesday: "What happened in #engineering today?"
Friday: "Summarize #engineering this week"
```

**Right side (the suggestion):**
```
💡 I noticed you check #engineering regularly.

Want me to send you a weekly digest
every Monday at 9am?

Sources: #engineering, #product
Format: Key updates, decisions, open questions

[Set this up]  [Customize]  [Not now]
```

**Tagline for section:** "The more you use yarnnn, the more it offers to do."

---

### Section 3.5: Calendar Connects Everything

**Header:** Your calendar knows who matters. yarnnn brings the context.

**Body:**
Meetings don't happen in isolation. The person you're meeting at 2pm? You've got Slack DMs with them, email threads, shared Notion docs. yarnnn pulls it all together before you walk in.

**Example: Meeting prep brief**

```
📅 1:1 with Sarah Chen — in 2 hours

Context from your platforms:

💬 Slack
  - Last DM: discussed Q1 hiring timeline (3 days ago)
  - Mentioned in #product: flagged API latency issue

📧 Gmail
  - Open thread: budget approval (awaiting your reply)
  - Last email: sent deck for board review

📝 Notion
  - Shared doc: Q1 OKRs (Sarah commented yesterday)

Suggested topics:
  • Follow up on hiring timeline
  • Respond to budget thread before meeting
  • Discuss API latency flag
```

**Why this matters:**
- You never walk into a meeting unprepared
- Context from every platform, organized by person
- yarnnn does the research, you do the thinking

**Visual opportunity:** Meeting card with attendee → expanded view showing Slack/Gmail/Notion context for that person

---

### Section 4: How It Works

**Header:** Three steps. Then it just runs.

**Step 1: Connect your tools**
> Link Slack, Gmail, Notion, or Google Calendar. One-time sign-in. yarnnn can now see what you see.

**Step 2: Tell it what you send (or let it suggest)**
> Describe what you need—a weekly status, a client update—or let yarnnn suggest based on your patterns.

**Step 3: Review and approve**
> When it's time, yarnnn drafts it. You read, tweak if needed, and send.

**Visual opportunity:** Horizontal flow with platform icons → deliverable types → review UI

---

### Section 5: It Gets Better

**Header:** Every approval teaches yarnnn something.

**Body:**
The first draft might need edits. The fifth needs fewer. By the tenth, you're just skimming and hitting approve.

yarnnn learns:
- Which sources matter most to you
- How you like things structured
- What tone fits each recipient
- What details are worth highlighting

**Visual opportunity:** Declining edit bar chart (already exists, could be enhanced)

---

### Section 6: What People Use It For

**Header:** Status reports. Investor updates. Client briefs. And more.

**Subhead:** If you send it regularly and your Slack, Gmail, or Notion has the context—yarnnn can write it.

**Grid layout with platform badges:**

| Deliverable | Pulls from | Who gets it |
|-------------|------------|-------------|
| Weekly status report | Slack #engineering, #product | Your manager |
| Investor update | Notion metrics, Slack #founders | Your investors |
| Meeting prep | Calendar + Slack + Gmail with attendees | You (before the meeting) |
| Client brief | Gmail threads, Notion project page | Your client |
| 1:1 prep | Calendar + Slack history + last meeting notes | You (before your 1:1) |
| Slack digest | Slack channels you pick | You (stay caught up) |
| Weekly preview | Calendar | You (know what's ahead) |

**Visual opportunity:**
- Each card shows platform icons (1-3 depending on sources)
- Arrow indicating flow: [platforms] → [deliverable] → [recipient]
- Real examples, not abstract descriptions

**Tagline for section:** "One setup. Fresh drafts whenever they're due."

---

### Section 7: More Platforms Coming

**Header:** Slack, Gmail, Notion, and Calendar are just the start.

**Body:**
We're building integrations for the tools you actually use.

**Coming soon:**
- **Linear** — Pull sprint updates and issue status
- **Jira** — Track tickets and project progress
- **Google Docs** — Reference your documents and notes
- **GitHub** — PRs, commits, and repo activity
- **Microsoft Teams** — For teams on the Microsoft stack

**Visual opportunity:** Grid of platform logos—4 lit up (current: Slack, Gmail, Notion, Calendar), others grayed with "coming soon" treatment

**CTA within section:**
> Want a specific integration? [Request it →]

---

### Section 8: Works Without Integrations Too

**Header:** No integrations? No problem.

**Body:**
yarnnn works best when connected to your platforms—but it doesn't require them.

**Two options:**
- **Paste context** — Copy in whatever you want yarnnn to work with
- **Describe it** — Just tell yarnnn what happened this week

yarnnn will draft from whatever you give it. Connect platforms later when you're ready.

**Visual opportunity:** Side-by-side showing "connected" flow vs "paste/describe" flow

---

### Section 9: CTA

**Header:** Stop writing updates. Start approving them.

**Subhead:** Free: 2 deliverables, all platforms. Pro: Unlimited.

**CTA:** Start for free

**Below CTA:**
> Works with Slack, Gmail, Notion, Calendar—or just paste in your own context.

---

## Narrative Flow (About Page)

### Hero

**Headline:**
> We built yarnnn because your Slack, Gmail, Notion, and Calendar already have everything you need to write that update.

**Body:**
The conversations are in Slack. The email threads are in Gmail. The project notes are in Notion. Your meetings are in Calendar. When you write a status report or prep for a 1:1, you're not creating anything new—you're assembling what's already there into a sendable shape.

That assembly work? A machine should do it. Your job is to review and decide what matters.

---

### Section: The Insight

**Three pillars:**

**Slack, Gmail, Notion, and Calendar already have the context**
> Your #engineering channel has the updates. Your inbox has the client threads. Your Notion has the project notes. Your calendar has the meetings. Every status report you've ever written, every 1:1 you've prepared for? The raw material was already there. You just spent an hour assembling it.

**Status reports follow patterns. So do investor updates. So do meeting preps.**
> The content changes weekly, but the shape stays the same. Section headers. Level of detail. What to highlight. yarnnn learns that shape from watching what you approve.

**Your job is judgment, not assembly**
> Should you mention the delayed timeline? Is this too much detail for the board? Does this sound like you? Those decisions require a human. The assembly doesn't. yarnnn handles assembly. You make the calls.

---

### Section: How It's Different

**Platform intelligence, not data extraction**
> Most integrations just pull messages and dump them somewhere. yarnnn reads your Slack like you would—seeing which threads are heating up, which questions are still open, which decisions got made. Same for Gmail (what's urgent, who's waiting), Notion (what changed, what's stale), and Calendar (who you're meeting, what context you need).

**Learns from approvals, not configuration**
> You don't set up rules or write prompts. You just review drafts and approve them. Every approval teaches yarnnn something—how you structure things, what tone you use for your manager vs. your investors, which details you always include.

**Suggests what you should automate**
> Ask yarnnn to summarize your Slack a few times. It notices. Then it offers to do that every Monday. You don't have to think about what to automate—yarnnn figures it out from how you work.

**Drafts on schedule, pings when ready**
> No daily prompting. No "generate" button to click. yarnnn drafts your weekly status on Monday morning and pings you when it's ready to review.

---

### Section: What It's Not

**Not a chatbot.** You don't prompt it with questions. You set up deliverables and review drafts.

**Not a template tool.** It doesn't fill in blanks. It synthesizes fresh content from current context.

**Not a writing app.** You're not typing in yarnnn. You're reviewing what it wrote.

**Not generic AI.** It's specifically for recurring things you send that pull from your existing tools.

---

## Narrative Flow (How It Works Page)

### Hero

**Headline:** How yarnnn works

**Subhead:** Connect your tools. Let yarnnn understand what's happening. Review and approve what it writes.

---

### Section: The Four Steps

**01. Connect your tools**

yarnnn links to Slack, Gmail, and Notion—wherever your work already lives.

What yarnnn sees:
- **Slack:** Channels and threads. Who's talking, what's decided, what's waiting.
- **Gmail:** Your inbox and labels. What's urgent, what needs replies, what's routine.
- **Notion:** Pages and databases. What changed, what's stale, what's linked.

**Visual:** Platform icons with signal examples beneath each

---

**02. Set up what you send (or let yarnnn suggest)**

Two paths:

**You know what you need:**
> Describe it—a weekly status for your manager, a monthly update for investors. Pick which channels or docs should feed into it.

**Let yarnnn figure it out:**
> Just use yarnnn for a while. Ask it to catch you up, summarize threads, draft replies. It'll notice patterns and suggest deliverables.

**Visual:** Split showing wizard vs. chat suggestion

---

**03. yarnnn drafts it**

When it's time—on schedule or when you ask—yarnnn:

1. Pulls fresh context from your connected tools
2. Reads it like you would (understanding what matters, not just extracting text)
3. Drafts the update in your voice

**Visual:** Data flow animation: platforms → processing → draft

---

**04. You review and approve**

The draft appears in your queue. You:
- Read through it
- Make any tweaks (or ask yarnnn to adjust)
- Approve when it looks right

Every approval teaches yarnnn something. Next time, fewer edits needed.

**Visual:** Review UI with refinement chips

---

### Section: What yarnnn Learns

**Which sources matter**
> If you always add context from #design but ignore #random, yarnnn prioritizes accordingly.

**How you structure things**
> The sections you keep, the order you prefer, how much detail feels right.

**Your tone for each audience**
> Formal for the board. Casual for your team. Direct for busy stakeholders.

**What to highlight**
> The metrics you always include. The wins worth calling out. The context your recipient actually cares about.

---

### Section: The Suggestion Loop

yarnnn doesn't just wait for instructions. It watches how you work.

**Pattern recognition:**
- Asked for Slack catch-ups three times? → Suggests a weekly digest
- Mentioned the same stakeholder repeatedly? → Suggests a recurring update
- Always pull from the same channels? → Suggests a deliverable combining them

**You stay in control:**
- Every suggestion is just an offer
- You can customize before accepting
- You can dismiss suggestions you don't want

**Visual:** Example of TP proposing a deliverable based on observed pattern

---

## Narrative Flow (Pricing Page)

### Hero

**Headline:** Simple pricing. Start free.

**Subhead:** Connect all your tools on any plan. Pay for more deliverables when you need them.

---

### Tiers

**Free — $0/month**
- 2 deliverables
- All platform connections (Slack, Gmail, Notion, Calendar)
- 2 sources/platform, syncs 2x daily
- 50k tokens/day

**Starter — $9/month**
- 5 deliverables
- 5+ sources/platform, syncs 4x daily
- Signal processing (auto-deliverable suggestions)
- 250k tokens/day

**Pro — $29/month**
- Unlimited deliverables
- Unlimited sources, hourly syncs
- 1M tokens/day
- Priority support

---

### What's Always Free

- **All platform connections** — Slack, Gmail, Notion, Calendar (and future integrations) on every plan
- **Paste or describe context** — Works without any integrations at all
- **Platform intelligence** — yarnnn reads your tools properly, not just extracting text
- **The learning loop** — Your edits improve drafts regardless of tier
- **Emergent suggestions** — yarnnn proposes deliverables on any plan

---

### FAQ

**Why is connecting tools free?**
> The platforms are where your context lives. Limiting connections would make yarnnn worse. We want you to connect everything—then decide which deliverables are worth automating.

**What if I don't use Slack, Gmail, Notion, or Google Calendar?**
> You can paste in context or describe what you need—yarnnn works with whatever you give it. And we're adding more integrations (Linear, Jira, Google Docs, Microsoft Teams) soon.

**What counts as a deliverable?**
> A deliverable is a recurring thing yarnnn produces: a weekly status, a monthly update, a daily digest. Each one counts as one deliverable, regardless of how often it runs. Free tier includes 2, Starter 5, Pro unlimited.

**Can I try Pro?**
> Start with Free (2 deliverables). When you need more, upgrade to Starter or Pro.

**What integrations are coming next?**
> Linear, Jira, Google Docs, GitHub, and Microsoft Teams are on the roadmap. [Request an integration →]

**What makes Calendar different from other integrations?**
> Calendar is the connective tissue. When you have a meeting with someone, yarnnn automatically pulls context from your Slack, Gmail, and Notion history with that person. It turns your calendar into a hub for understanding who you're meeting and what you need to know.

---

## Visual Design Principles

### Platform Icons

Replace emojis with recognizable, consistent icons:
- Slack: Use official mark or abstract representation with Slack purple/blue
- Gmail: Envelope with Gmail red accent
- Notion: Page icon with Notion grayscale

Icons should:
- Work at small sizes (16px) and large (48px)
- Have consistent stroke weight
- Use platform-associated colors as accents, not fills

### Signal Visualization

Show what yarnnn "sees" in each platform:

**Slack signals:**
- Thread depth indicator (nested replies icon)
- Heat indicator (flame or activity pulse)
- Decision marker (checkmark or resolution icon)
- Unanswered question (question mark with alert)

**Gmail signals:**
- Urgency indicator (priority arrow)
- Response needed (reply arrow with alert)
- Thread age (clock icon)
- Sender importance (star or relationship indicator)

**Notion signals:**
- Edit recency (pencil with time)
- Staleness (cobweb or dust icon, subtle)
- Comment activity (speech bubble with count)
- Link health (chain icon)

### Data Flow Visualization

Show context flowing from platforms to deliverable:

```
[Slack] ──┐
          ├──→ [yarnnn] ──→ [Draft] ──→ [You Review] ──→ [Sent]
[Gmail] ──┤
          │
[Notion]──┘
```

Animate with:
- Pulse effects on platform icons when "pulling"
- Flow lines showing data movement
- Processing indicator in the middle
- Draft appearing with subtle entrance

### Suggestion UI

Show yarnnn proposing a deliverable:

```
┌─────────────────────────────────────────────────────────────┐
│ 💡 yarnnn noticed something                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ You've asked me to catch you up on #engineering             │
│ three times this month.                                     │
│                                                             │
│ Want me to send you a weekly digest every Monday?           │
│                                                             │
│ [Set this up]  [Customize]  [Not now]                       │
└─────────────────────────────────────────────────────────────┘
```

### Review UI Preview

Show the supervision model in action:

```
┌─────────────────────────────────────────────────────────────┐
│ Weekly Status — Ready to review                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [Draft content preview, truncated]                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Built from: 💬 #engineering (23 messages)                   │
│             💬 #product (12 messages)                       │
│             📝 Sprint Planning (updated yesterday)          │
├─────────────────────────────────────────────────────────────┤
│ Quick refine: [Shorter] [More detail] [Casual] [Formal]     │
│                                                             │
│ [Edit draft]                      [Approve and send]        │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Terminology

Use plain language. Avoid jargon.

| Instead of | Say |
|------------|-----|
| Platform-bound deliverable | "From one platform" |
| Cross-platform synthesis | "Across platforms" |
| Context extraction | "Reading your tools" |
| Temporal pattern | "When it runs" (scheduled, on-demand) |
| Emergent discovery | "yarnnn notices patterns" |
| Supervision model | "You review, yarnnn writes" |
| Delta context | "What's new since last time" |
| Platform signals | "What's happening" or "what matters" |

---

## Competitive Positioning

**vs. ChatGPT / Claude chat:**
> Those are general-purpose. You prompt them each time. yarnnn is set-and-forget for recurring things.

**vs. Zapier / Make:**
> Those move data between apps. yarnnn understands context and writes human-quality content.

**vs. Notion AI / Slack AI:**
> Those work inside one platform. yarnnn synthesizes across all your tools.

**vs. Templates / Mail merge:**
> Those fill in blanks. yarnnn synthesizes fresh content from what actually happened.

---

## Implementation Notes

### Pages to Update

1. **Home** (`/app/page.tsx`)
   - New hero headline
   - Platform intelligence section (new)
   - Emergent suggestions section (new)
   - Revised how-it-works flow
   - Updated use cases with platform badges

2. **About** (`/app/about/page.tsx`)
   - New hero framing
   - Platform intelligence vs. data pulling distinction
   - Emergent learning emphasis

3. **How It Works** (`/app/how-it-works/page.tsx`)
   - Platform signal showcase (new)
   - Two paths: declare vs. let yarnnn suggest
   - Suggestion loop explanation (new)

4. **Pricing** (`/app/pricing/page.tsx`)
   - Emphasize platforms free on all tiers
   - Clarify what a "deliverable" is

### New Components Needed

1. `PlatformIcon` — Consistent icon component for Slack/Gmail/Notion
2. `PlatformSignals` — Visual representation of what yarnnn reads
3. `DataFlowDiagram` — Animated platform → yarnnn → output flow
4. `SuggestionCard` — Example of yarnnn proposing a deliverable
5. `ReviewPreview` — Example of the review/approve UI
6. `UseCaseCard` — Enhanced card with platform source badges

---

## Success Criteria

The new landing pages should make visitors understand:

1. **Platform intelligence** — yarnnn doesn't just pull data, it understands what's happening
2. **Emergent suggestions** — yarnnn proposes what you should automate based on patterns
3. **Supervision model** — you review and approve, yarnnn does the writing
4. **Learning loop** — it gets better the more you use it
5. **Simplicity** — despite the sophistication, it's easy to start

---

## Next Steps

1. Review and align on this narrative direction
2. Create component library (platform icons, signal visualizations)
3. Build out one page as prototype (suggest: How It Works)
4. Iterate on visual design
5. Roll out to remaining pages

---

## Related Documents

- [ADR-044: Deliverable Type Reconceptualization](../adr/ADR-044-deliverable-type-reconceptualization.md)
- [DECISION-001: Platform Sync Strategy](../product/DECISION-001-platform-sync-strategy.md)
- [Design Principle: The Supervision Model](./DESIGN-PRINCIPLE-supervision-model.md)