# ACTIVATION_100USERS.md

**Objective:** 100 paying users. Not followers. Not impressions. Users.
**Version:** 3.0 (v2 preserved inline with `[v2]` annotations where replaced; v1 archived in `./archive/`)
**Date:** 2026-04-01
**Status:** Strategy reset — psychographic emphasis, organizational intelligence reframe
**Budget:** $150–300 (Reddit ads, Phase 1); $500–880 total across 30 days
**Owner:** Kevin
**References:** [GTM_POSITIONING.md v3.0](../strategy/GTM_POSITIONING.md), [CONTENT_STRATEGY_v1.md](../strategy/CONTENT_STRATEGY_v1.md), [ICP_ANALYSIS_APRIL_2026.md](../strategy/ICP_ANALYSIS_APRIL_2026.md)

---

## Why This File Exists

The content strategy and positioning docs describe a system for sustained organic growth. That system matters — but it doesn't answer the immediate question:

**Where do the first 100 non-network users come from, and what makes them pay?**

This is the only activation doc that matters right now. Everything else is archived or reference material. This file is a live experiment log — updated as we spend real money, track real results, and learn what actually converts a stranger into a YARNNN user.

**Archived docs** (in `./archive/`):
- `ACTIVATION_PLAYBOOK_v1.md` — original organic playbook (2026-02-23)
- `ACTIVATION_PLAYBOOK_v2_archived.md` — updated with pointer to this doc
- `ACTIVATION_100USERS_v1.md` — first draft before ICP stress test

---

## v3.0 Strategy Reset: Why Psychographic Leads

v2 tested two hypotheses in parallel (Psychographic vs. Occupation). Neither was executed — the tracking tables are empty. Meanwhile, the product architecture evolved significantly (ADR-138 through ADR-153), and a deeper ICP analysis (April 2026) identified the "automation paradox" that breaks the occupation-first approach: high-pain tasks are too high-stakes to trust AI, and low-stakes tasks aren't painful enough to justify the product.

**The resolution:** Lead with the psychographic ICP but reframe the value prop from "automate your deliverables" to "gain organizational intelligence capabilities." The product now pre-scaffolds a roster of domain experts (ADR-140) — this directly addresses the psychographic audience's gap between "I want AI agents" and "I have AI agents working for me." They sign up, and the team is already there.

The occupation ICP (consultants, fractional execs) remains valid as a secondary segment but is no longer the primary wedge. The psychographic audience is larger, better matched to the product's current architecture, and more likely to convert on the "intelligence team" pitch than the "report automation" pitch.

---

## The Three Hypotheses (Revised — Psychographic Emphasis)

### Hypothesis A (PRIMARY) — Psychographic ICP: "The Intelligence-Hungry Professional"

> A professional who feels the gap between the organizational intelligence they should have (competitor tracking, market awareness, operational synthesis) and what they actually maintain. They've heard about AI agents, believe in the promise, but haven't found one that works without heavy setup. They want an AI team, not an AI tool.

**Who this person is:** They're on r/productivity, r/Entrepreneur, r/smallbusiness, r/startups, and LinkedIn. They may be a founder, a Head of Ops, a Chief of Staff, or a senior generalist at a 10-50 person company. They've tried ChatGPT, maybe pay for Plus or Pro. They've heard "AI agents" on podcasts and LinkedIn. The critical difference from v2: **they don't just want "an AI agent" abstractly — they want organizational capabilities they know they're missing.** They know they should track competitors. They know market signals slip through. They've tried and failed to sustain these practices.

**Why this is now primary:**
- The product directly delivers what they want: a pre-scaffolded roster of domain experts (competitive intelligence, market research, business development, operations, marketing) ready on day one (ADR-140)
- No setup gap — agents exist at signup. The "desire without a job-to-be-done" problem from v2 is partially solved because the roster itself suggests the jobs: "Your Competitive Intelligence agent can track [competitor]. Your Market Research agent can monitor [sector]."
- The ClawdBot demand signal (17,830 GitHub stars) was from this psychographic, not from consultants
- Larger addressable market than occupation-specific segments
- The "organizational intelligence" pitch is stickier than "report automation" because it frames YARNNN as a capability, not a feature

**The v2 risk (churn from no job-to-be-done) and how v3 architecture mitigates it:**
v2 worried this audience would sign up, not know what to assign, and churn. Three architectural changes reduce this risk:
1. Pre-scaffolded roster (ADR-140): The team is there on day one with named domains — this itself suggests what to assign
2. Inference-first context building (ADR-144): No forms. Talk to the orchestrator in plain English ("I want to track these three competitors") and it creates the right tasks
3. Task type registry (ADR-145): Curated task types with clear descriptions — the user picks from a menu, not from a blank canvas

**What we'd learn if this works:** YARNNN's market is "professionals who need organizational intelligence capabilities" — a much larger market than "professionals who need recurring deliverables automated." The product is an intelligence team, not a report generator.

### Hypothesis B (SECONDARY) — Occupation ICP: "The Senior Operator at a Growing Company"

> A Head of Ops, Chief of Staff, VP Strategy, or COO at a 10-50 person company who is personally responsible for maintaining organizational awareness across competitive, market, and operational domains, and who currently does this through ad-hoc effort that constantly falls behind.

**Who this person is:** They're on LinkedIn, in Chief of Staff Network communities, Pavilion (formerly Revenue Collective), Rands Leadership Slack. They manage the "intelligence layer" of a growing company — competitive tracking, market monitoring, operational synthesis, investor/board reporting — but don't have dedicated staff for any domain.

**Why this might be right:** Strongest product-market alignment of any segment. Their job description literally matches the pre-scaffolded roster. They have company budget (not personal budget). They experience the pain weekly, not monthly. They've already tried to build these practices and watched them fail.

**Why this might be wrong:** Smaller community presence on Reddit (harder to reach via ads). May require LinkedIn/community outreach rather than Reddit ads. Longer evaluation cycle (company purchase vs. personal purchase).

**What we'd learn if this works:** YARNNN's wedge is "fractional intelligence team for growing companies." Growth is B2B, community-driven, and LinkedIn-native.

### Hypothesis C (TERTIARY) — Occupation ICP: "Multi-Client Professional" [preserved from v2]

> Solo consultant, freelancer, or fractional exec managing 3-8 clients with recurring deliverables.

**Status:** Demoted from primary to tertiary. The April 2026 ICP analysis identified the automation paradox: client-facing deliverables are too high-stakes to trust AI (trust barrier), and internal summaries aren't painful enough to justify the product. This segment may convert after seeing the "intelligence team" framing — they'd use YARNNN for their own competitive intelligence and market research, not for client deliverables initially. The client deliverable use case may emerge after trust is established through personal use.

---

## The iPod Principle

A framing principle for creative direction across both tracks.

Apple didn't market the iPod in MP3 player forums. "1000 songs in your pocket" appeared on billboards — in front of people who had a CD collection and a commute. The copy didn't mention storage capacity, file formats, or the MP3 category. It described an outcome in words a 12-year-old understands.

But the iPod analogy also teaches: by 2001, most people had **heard** of MP3 players. The term had awareness. Apple didn't avoid the category — they transcended it.

For YARNNN, "AI agents" is in a similar position in March 2026. Most professionals have heard the term. They associate it with "AI that does things for me." The question isn't whether to use the term — it's whether the term **pulls** (creates desire) or just **doesn't confuse** (passive awareness).

Within any mainstream community there are early adopters — the people who tried Notion in 2018, used Superhuman before it was cool. These people pride themselves on finding tools first. Making them feel like they're getting in early on something inevitable is a genuine psychological trigger — and for YARNNN it's literally true. The product is in beta. Early-bird pricing exists. "First 100 users" is a real number, not manufactured scarcity.

This is why the creative direction is two-tracked within each hypothesis. We test both "skip the category, lead with outcome" and "lean into the category, reward the early adopter."

---

## Phase 1: Reddit Ads — The Two-Track Experiment (Days 1–7)

### Why Reddit Ads First

| Channel | Time to signal | Cost to signal | Audience targeting | Why now / why not |
|---------|---------------|----------------|-------------------|-------------------|
| Reddit Ads | 48–72 hours | $50–100 per test | Subreddit-level (precise) | **Now.** Lowest CAC path to signal. Native format. Subreddit = built-in A/B. |
| Organic Reddit | 24 hours | $0 | Subreddit-level | Good supplement. One post is one shot per community — ads let you iterate. |
| Twitter/X | 4–6 weeks | $0 | Algorithmic (unpredictable) | Start posting now for profile credibility, but don't expect signups yet. |
| LinkedIn | 4–6 weeks | $0 | Professional (high ICP fit) | Start posting now. Compounds over weeks, not days. |
| Meta (FB/IG) | 48–72 hours | $50–100 per test | Interest + demographic | **Phase 3 candidate.** If psychographic ICP validates on Reddit, Meta is the scale channel. |
| Product Hunt | One shot | $0 | Broad tech/startup | **Not yet.** Need retention data + testimonials. |
| Show HN | One shot | $0 | Technical early adopters | **Not yet.** Save until demo is polished. |

Reddit is the cheapest way to test message × audience fit. At $2–5 CPC, $150 buys 30–75 real clicks. But Reddit may not be the scale channel. If psychographic ICP wins, scaling likely moves to Meta. If occupation ICP wins, scaling stays on Reddit + LinkedIn.

---

### Track A — Psychographic Targeting (PRIMARY — 60% of budget)

**Subreddits:** Where mainstream professionals talk about work, productivity, and business growth. These are intelligence-hungry professionals, not AI hobbyists.

| Subreddit | Members | Why this audience | What we learn |
|-----------|---------|-------------------|---------------|
| **r/productivity** | 1.5M | Actively looking to work smarter. Tool-curious. Includes senior ops people and founders. | Does the "intelligence team" pitch resonate with people who want to be more systematically informed? |
| **r/Entrepreneur** | 2.5M | Founders and business owners drowning in the gap between "what I should track" and "what I actually do." | Does the capability gap ("I should track competitors but don't") drive more urgency than the task pain ("writing reports takes too long")? |
| **r/smallbusiness** | 1.5M | Business owners who hear about AI everywhere but haven't adopted. Many run 5-30 person companies — the exact size where they need intelligence but can't hire for it. | Can we convert someone on the "your AI team" pitch without requiring them to have a specific use case in mind? |
| **r/startups** | 1.2M | Early-stage founders who need organizational capabilities but are stretched thin. | Does the "intelligence team for $19/mo" framing resonate with people who can't hire? |

**Three creative directions within Track A (v3.0):**

#### A1 — Intelligence Team (Capability Framing)

Lead with the organizational capability gap. Position YARNNN as the team they can't hire.

> **Competitive intelligence. Market research. Operational awareness. $19/month.**
>
> YARNNN gives you a team of AI domain experts that connect to your Slack and Notion, learn your business, and work autonomously. They track competitors, monitor your market, and deliver briefings on schedule — getting smarter every week.
>
> The intelligence team your company needs. Powered by AI that actually knows your business.
>
> → yarnnn.com

**Why this might work:** Names the specific capabilities the reader knows they're missing. "$19/month" makes the "I can't hire for this" objection irrelevant. Speaks to the gap between "what I should do" and "what I actually do." Concrete enough to imagine using, abstract enough to self-select.

**Risk:** "Intelligence team" may feel corporate or intimidating to solo founders. The pitch requires the reader to already feel the capability gap.

#### A2 — AI Team Activation (Early-Adopter + Team Framing)

Embrace the agent term. Make the reader feel ahead of the curve. But frame it as a team, not a tool.

> **Everyone's talking about AI agents. Here's your team.**
>
> Five domain experts — competitive intelligence, market research, business development, operations, marketing — that connect to your tools, learn your world, and work while you don't.
>
> No code. No configuration. Sign up and your team is ready.
>
> → yarnnn.com

**Why this might work:** "Here's your team" is more powerful than "here's yours" (v2) because it shifts from singular tool to organizational capability. "Five domain experts" makes the value tangible and specific. Pre-scaffolded roster means the promise is literally true — the team is ready at signup.

**Risk:** "Five domain experts" may feel like overreach if the reader is skeptical about AI capability. "Team" metaphor may not land if they've been burned by other "AI that works for you" claims.

#### A3 — Desire-First (Habit Enablement Framing)

Lead with the things the reader wishes they did but doesn't.

> **You know you should track competitors. Monitor your market. Stay ahead of industry shifts.**
>
> You don't. Nobody has time. YARNNN does.
>
> AI agents that build knowledge of your business continuously — so when you need a competitive brief, market analysis, or strategic overview, the thinking is already done.
>
> → yarnnn.com

**Why this might work:** Directly names the habits the reader has tried and failed to sustain. "You know you should... You don't" is a sharp hook that creates recognition. Positions YARNNN as enabling new capabilities rather than automating existing work — the v3.0 reframe.

**Risk:** "You don't" may feel judgmental. The pitch is abstract — no specific deliverable or time-saved claim. May attract interest without purchase intent.

#### What Track A Results Tell Us (v3.0)

| Result | Interpretation | Next move |
|--------|---------------|-----------|
| A1 wins | The capability gap is the sharpest pain. "Intelligence team" framing resonates. | Position YARNNN as fractional intelligence team. LinkedIn becomes scale channel. Pursue Hypothesis B (senior operators) aggressively. |
| A2 wins | "AI agent" term has pull AND "team" framing adds weight. Early-adopter identity works. | Position YARNNN as "the AI team for non-technical professionals." Scale on Reddit + Meta. |
| A3 wins | Habit enablement > task automation. The desire for capabilities they don't have is the trigger. | Double down on "what you wish you did" messaging. Content strategy pivots to aspiration, not pain. |
| A1+A3 tie, A2 loses | Capability framing works; agent/team language doesn't add value. | Drop "AI agent" from ads. Lead with organizational capabilities. |
| None convert | Psychographic audience on Reddit isn't the right channel, or the intelligence team pitch doesn't trigger purchase intent. | Shift to LinkedIn/community outreach (Hypothesis B). 5 manual conversations before more spend. |

---

### Track B — Occupation Targeting (SECONDARY — 25% of budget)

**v3.0 change:** Track B shifts from "multi-client consultants" to "senior operators at growing companies" — the segment with the strongest product-market alignment to the domain-steward roster. Consultant-specific ads move to Track C (tertiary).

**Channels:** LinkedIn is the primary channel for this segment, not Reddit. Reddit ads in this track target adjacent communities.

| Channel / Subreddit | Audience | Why | What we learn |
|-----------|---------|-------------------|---------------|
| **LinkedIn (organic + sponsored)** | Heads of Ops, Chiefs of Staff, VPs Strategy at 10-50 person companies | This is where senior operators live professionally. Highest ICP density. | Does the "fractional intelligence team" pitch convert someone with company budget? |
| **r/startups** | 1.2M | Founders at the stage where they need intelligence but can't hire for it | Does the company-capability framing resonate with early-stage founders? |
| **r/Entrepreneur** | 2.5M (overlap with Track A) | Business owners experiencing the intelligence gap | Shared with Track A — different creative (ops-focused vs. aspiration-focused) |

**Two creative directions within Track B:**

#### B1 — Capability Gap (Fractional Team Framing)

Lead with the organizational gap. Speak to the person who manages the "intelligence layer" and knows it's falling behind.

> **Your company needs competitive intelligence, market awareness, and operational synthesis. You don't have the team for it.**
>
> YARNNN gives you five AI domain experts that connect to your Slack and Notion, learn your business continuously, and deliver briefings on schedule. Competitive Intelligence. Market Research. Business Development. Operations. Marketing.
>
> The intelligence team you need. $19/month.
>
> → yarnnn.com

**Why this might work:** Names the exact gap the senior operator feels daily. "$19/month" makes the ROI obvious against the alternative (hiring). Specific domain names make it concrete and credible.

**Risk:** "Five AI domain experts" may trigger skepticism. LinkedIn audience may want proof before clicking.

#### B2 — Hiring Analogy

Frame the purchase decision as a hiring decision, not a tool purchase.

> **What if you could hire a competitive analyst, a market researcher, and a strategy synthesizer — for $19/month?**
>
> YARNNN deploys AI domain experts that connect to your Slack and Notion, accumulate knowledge of your business, and produce work autonomously. They get better every month because they're building on accumulated understanding.
>
> Your first 90 days are free. Meet your team.
>
> → yarnnn.com

**Why this might work:** The hiring analogy makes the value proposition immediately concrete. Every senior operator has wished they could hire these roles. "$19/month" creates a visceral contrast with the actual cost of these hires.

**Risk:** "AI domain experts" is an unproven category. The reader may not believe AI can do these jobs well enough.

### Track C — Consultant Targeting (TERTIARY — 15% of budget)

**Preserved from v2 as a narrow test.** Multi-client professionals with recurring deliverables. Demoted because: (1) high-stakes client work = high trust barrier, (2) the ICP analysis showed these users are more likely to adopt for personal intelligence first, then graduate to client work.

| Subreddit | Members | Why | What we learn |
|-----------|---------|-----|---------------|
| **r/freelance** | 300K | Multi-client freelancers | Does the intelligence-team pitch work better than the report-automation pitch for this audience? |
| **r/consulting** | 400K | Solo consultants | Can we convert consultants on "competitive intelligence for your practice" rather than "automate your client reports"? |

**Single creative direction (testing reframed pitch only):**

#### C1 — Intelligence for Your Practice

> **You track your clients' worlds. Who tracks yours?**
>
> YARNNN gives consultants an AI intelligence team — competitive tracking, market monitoring, and strategic synthesis — that learns your practice and works autonomously. Stop flying blind on your own business while you're heads-down in client work.
>
> → yarnnn.com

**Why this might work:** Reframes YARNNN for consultants as a tool for their own business intelligence, not client deliverables. Avoids the trust barrier entirely. "Who tracks yours?" creates recognition of the gap.

---

### Phase 1 Test Matrix (v3.0 — Psychographic Emphasis)

**~14 ads total. Staggered execution (recommended):**

**Week 1 (Days 1-4):** Track A on Reddit — 12 ads across 4 subreddits × 3 creatives. Budget: ~$250. This is the primary hypothesis and gets the most spend.

**Week 1-2 (Days 3-7):** Track B on LinkedIn — 2 sponsored posts (B1, B2). Budget: ~$100. Run concurrently with Track A tail.

**Week 2 (Days 5-7):** Track C on Reddit — 2 ads (C1 in r/freelance, r/consulting). Budget: ~$50. Minimal spend, just enough for signal.

**Track A (PRIMARY — 60% of budget):**

| | r/productivity | r/Entrepreneur | r/smallbusiness | r/startups |
|---|---|---|---|---|
| **A1** (Intelligence Team) | Ad 1 | Ad 2 | Ad 3 | Ad 4 |
| **A2** (AI Team Activation) | Ad 5 | Ad 6 | Ad 7 | Ad 8 |
| **A3** (Desire-First) | Ad 9 | Ad 10 | Ad 11 | Ad 12 |

**Track B (SECONDARY — 25%):** LinkedIn sponsored posts (B1 capability gap, B2 hiring analogy)

**Track C (TERTIARY — 15%):** Reddit (C1 in r/freelance, C1 in r/consulting)

### Reading the Results (72 Hours)

**Cross-track signals:**

| Signal | What it means | Next move |
|--------|--------------|-----------|
| Track A outperforms B+C | Psychographic ICP is real. The intelligence-team pitch resonates broadly. | Scale Track A winners. Test Meta ads for mainstream reach. Refine onboarding around roster discovery. |
| Track B outperforms A+C | Senior operators are the wedge. Company-capability framing converts better than personal-aspiration framing. | LinkedIn becomes primary channel. Community outreach (Chief of Staff Network, Pavilion). |
| Track A + B both convert, C doesn't | Intelligence-team pitch works; deliverable-automation pitch doesn't. The v3.0 reframe is validated. | Kill consultant-specific messaging. Unified pitch: "your intelligence team." |
| Track C outperforms A+B | Consultant segment was right all along — but the reframed pitch (intelligence for your practice, not client deliverables) is what unlocked it. | Revert consultant as primary ICP but keep the intelligence framing. |
| None convert | Product-market fit not yet proven. Landing page, product, or entire thesis needs work. | Stop spending. 5 manual conversations with target users before any more spend. |

**Within Track A signals (most important — this is the primary hypothesis):**

| Signal | What it means | Next move |
|--------|--------------|-----------|
| A1 wins (Intelligence Team) | The capability gap is the trigger. "Five domain experts" is concrete enough. | Position YARNNN as "fractional intelligence team." All messaging leads with capability names. |
| A2 wins (AI Team Activation) | "AI agents" + "team" framing = maximum pull. Early-adopter identity works. | Lead with "your AI team." The agent term has power when framed as team, not tool. |
| A3 wins (Desire-First) | Habit enablement > task automation. The aspirational gap ("you know you should...") is the sharpest hook. | Pivot messaging to "enable what you wish you did." Content strategy becomes aspiration-first. |
| r/Entrepreneur dominates | Founders feeling the intelligence gap are the wedge audience. | Focus on founder communities. Test on Indie Hackers and founder Slack groups. |
| r/smallbusiness dominates | Small business owners (non-startup) are an untapped segment. Lower AI literacy but higher pain. | Simplify onboarding further. Test on Meta targeting small business owners. |

**Diagnostic framework if nothing converts:**

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| High impressions + low CTR | "Intelligence team" framing doesn't stop the scroll | Test more provocative hooks: "Your company has no intelligence team" / "You're flying blind" |
| High CTR + low signups | Landing page doesn't deliver on the ad promise | Redesign landing page around roster discovery and domain expert introductions |
| Signups + no task creation | Roster doesn't self-explain; users don't know what to assign | Add guided task creation: "Your Competitive Intelligence agent is ready. Who are your top 3 competitors?" |
| Tasks created + no return after first output | Output quality doesn't justify the promise | Improve task pipeline, context gathering, output formatting |
| All funnels break | The intelligence team pitch may not trigger purchase intent | 5 manual conversations. Test: "Would you pay $19/mo for a competitive intelligence agent that tracked [their actual competitors]?" |

---

## Guardrails: Three Conditions for a Valid Experiment

These emerged from stress-testing. Not nice-to-haves — conditions for the data to be readable.

### Guardrail 1: The Roster Must Self-Explain (Desire-to-Use-Case Bridge)

**Updated for v3.0 architecture:** The pre-scaffolded roster (ADR-140) partially solves the "don't know what to assign" problem — users see five named domain experts at signup. But they still need to bridge from "I have agents" to "I've assigned work."

**Requirement:** After signup, the roster view must immediately suggest domain-specific first tasks:
- "Your Competitive Intelligence agent is ready. Who are your top 3 competitors?" → Creates a competitor tracking task
- "Your Market Research agent can monitor your industry. What sector are you in?" → Creates a market monitoring task
- "Connect Slack and your agents start learning your business context automatically."

The orchestrator (TP) should proactively suggest the first task based on context from the signup conversation (ADR-144 inference-first model). No blank canvas.

### Guardrail 2: Context Bootstrapping Speed

Broader audience = wider variance in existing platform data. Some users will have rich Slack workspaces. Others will connect with very little.

**Requirement (updated for ADR-153):** Since platform content sync is gone and agents pull data live during task execution, the first task output quality depends on what's available at execution time. If the user has minimal platform data, the first output should still be useful — leaning on web research and the agent's domain expertise rather than requiring rich platform data.

Surface context-readiness signals:
- "Your Competitive Intelligence agent found 8 competitor mentions in your Slack. Rich context available."
- "Limited platform data so far. Your agent will supplement with web research. Connect more tools for richer results."

### Guardrail 3: Free-to-Paid Conversion Path

$19/mo works in some ads to signal "real product" and anchor value against the hiring alternative. But it should not gate signup.

**Requirement:** Free tier must be prominent. No payment required to try. The conversion trigger is: user sees first autonomous output from an agent that references accumulated context they didn't explicitly provide. That's the "aha" moment. Payment prompt appears after the aha moment, not before.

Sequence: Ad click → landing page → free signup → meet your roster → connect Slack/Notion → assign first task (guided) → first output arrives → "Your Competitive Intelligence agent just delivered. Upgrade to Pro for unlimited tasks." → conversion.

---

## Phase 2: Organic Amplification (Days 5–14)

Once Phase 1 identifies winning track + creative direction, organic content amplifies without additional spend.

### Reddit Organic (1 post per winning subreddit)

Rewrite winning ad angle as an authentic "I built this" post.

**If Track A won (Intelligence Team / Psychographic):**

> Title: I kept hearing about AI agents and thinking "cool, but where's mine?" So I built a team of them that actually knows my business.
>
> I'm a solo founder who spent 10 years in CRM/GTM. I know I should track competitors, monitor my market, and stay ahead of industry shifts. I never sustained any of it — too many things competing for attention.
>
> So I built YARNNN. You sign up and get five AI domain experts — competitive intelligence, market research, business development, operations, marketing — that connect to your Slack and Notion, learn your world continuously, and work autonomously on schedule. Each one builds knowledge over time. By month 3, your competitive intelligence agent knows things about your market that a fresh ChatGPT session never could.
>
> No code. No prompt engineering. Your team is ready at signup.
>
> Beta. Looking for people who feel the gap between "what I should track" and "what I actually do."
>
> → yarnnn.com

**If Track B won (Senior Operator / Capability Gap):**

> Title: My 15-person company needs competitive intelligence, market research, and operational awareness. Can't hire for any of it. Built an AI team instead.
>
> I'm a solo founder who spent 10 years in CRM/GTM. Every growing company hits this point: you need organizational intelligence but can't justify hiring a competitive analyst, a market researcher, and a chief of staff. The work falls to whoever has 20 minutes on Friday, and it never gets done properly.
>
> So I built YARNNN. It gives you a roster of AI domain experts that connect to your Slack and Notion, accumulate knowledge of your business, and produce work on schedule. They get better every month because the knowledge compounds.
>
> Beta. $19/mo for the intelligence team your company needs.
>
> → yarnnn.com

**Rules:**
- Reply to every comment.
- Max 2 subreddits per week.
- Lead with the capability gap or the aspiration, not the product features.

### Twitter (3x/week — start Day 1)

Purpose at this stage: profile credibility, ClawdBot bridge story, compounding.

**Week 1:**
- Day 1: Pain tweet. "I use ChatGPT every day. Every day, it has no idea who my clients are."
- Day 3: Build-in-public. Connect to thesis.
- Day 5: ClawdBot thread. "17,830 GitHub stars in 24 hours. Here's what everyone missed."

Adapt voice to winning track after Phase 1 data.

### LinkedIn (1x/week — start Day 2)

Personal narrative format. Link in comments. End with engagement question, not CTA.

Adapt to winning track after Phase 1 data.

---

## Phase 3: Scale What Converts (Days 14–30)

Enter Phase 3 only when Phase 1 and 2 have answered: which ICP, which creative, does the product deliver.

### If Track A won (psychographic — intelligence team pitch on Reddit):
- Scale winning variant to remaining Reddit communities (r/marketing, r/projectmanagement, r/SaaS).
- **Test Meta (Facebook/Instagram) ads** — $100-200. Reddit validated the message; Meta is where the mainstream audience scales.
- **Test Twitter/X promoted tweets** — same creative adapted for Twitter format.
- Refine onboarding: roster discovery experience, guided first-task creation.
- Budget: $300-500.

### If Track B won (senior operators — capability gap on LinkedIn):
- LinkedIn becomes primary channel: 2x/week organic posting + sponsored content scale.
- **Community outreach:** Chief of Staff Network, Pavilion, Rands Leadership Slack. DM outreach, not posts.
- **Partner channel:** Startup accelerators, fractional exec networks, ops communities.
- Budget: $300-500.

### If A+B both converted (intelligence team pitch works across psychographic and occupation):
- Unified pitch: "the intelligence team your company needs." Scale on highest-converting channel regardless of track.
- Test across both Reddit (broad psychographic) and LinkedIn (senior operators) with the same core message.

### If nothing converted:
- Stop spending immediately. Diagnose using the framework above.
- **5 manual conversations** with target users. Specifically test: "Would you pay $19/month for five AI domain experts that track your competitors, monitor your market, and deliver briefings weekly?" If the answer is no, the intelligence team pitch doesn't have purchase intent. If the answer is "yes but...", the objection tells you what to fix.
- Consider: is the landing page delivering on the ad promise? Does the product experience match what the ads describe?

---

## Pre-Launch Checklist (Before Any Dollar Goes Out)

- [ ] **Signup flow works end-to-end.** Test as a stranger, not the developer.
- [ ] **Time to aha < 5 minutes.** From signup to orchestrator demonstrating context awareness.
- [ ] **Landing page matches ad promise.** "AI that works for you" or "AI agents for everyone" — not a generic AI pitch.
- [ ] **Onboarding suggests specific use cases.** "Here are 3 things your AI can do now" (Guardrail 1).
- [ ] **Context-richness signal visible after sync** (Guardrail 2).
- [ ] **Free tier prominent.** No payment required to try (Guardrail 3).
- [ ] **Checkout works.** Stripe/Lemon Squeezy flow tested.
- [ ] **UTM tracking set up.** Unique UTM per variant. Trace: ad → site → signup → connect → TP session → return → upgrade.

---

## Tracking & Results Log

### Phase 1 — Track A (Psychographic — PRIMARY)

| Date | Variant | Subreddit | Spend | Impressions | Clicks | CTR | Signups | Tasks Created | CAC | Notes |
|------|---------|-----------|-------|-------------|--------|-----|---------|--------------|-----|-------|
| | A1 (Intelligence Team) | r/productivity | | | | | | | | |
| | A1 | r/Entrepreneur | | | | | | | | |
| | A1 | r/smallbusiness | | | | | | | | |
| | A1 | r/startups | | | | | | | | |
| | A2 (AI Team) | r/productivity | | | | | | | | |
| | A2 | r/Entrepreneur | | | | | | | | |
| | A2 | r/smallbusiness | | | | | | | | |
| | A2 | r/startups | | | | | | | | |
| | A3 (Desire-First) | r/productivity | | | | | | | | |
| | A3 | r/Entrepreneur | | | | | | | | |
| | A3 | r/smallbusiness | | | | | | | | |
| | A3 | r/startups | | | | | | | | |

### Phase 1 — Track B (Senior Operators — SECONDARY)

| Date | Variant | Channel | Spend | Impressions | Clicks | CTR | Signups | Tasks Created | CAC | Notes |
|------|---------|---------|-------|-------------|--------|-----|---------|--------------|-----|-------|
| | B1 (Capability Gap) | LinkedIn Sponsored | | | | | | | | |
| | B2 (Hiring Analogy) | LinkedIn Sponsored | | | | | | | | |

### Phase 1 — Track C (Consultants — TERTIARY)

| Date | Variant | Subreddit | Spend | Impressions | Clicks | CTR | Signups | Tasks Created | CAC | Notes |
|------|---------|-----------|-------|-------------|--------|-----|---------|--------------|-----|-------|
| | C1 (Intelligence for Practice) | r/freelance | | | | | | | | |
| | C1 | r/consulting | | | | | | | | |

### Phase 2 Results

| Date | Channel | Post Type | Track | Reach | Engagement | Signups | Notes |
|------|---------|-----------|-------|-------|------------|---------|-------|
| | | | | | | | |

### Phase 3 Results

| Date | Channel | Variant | Spend | Signups | CAC | Retention (7d) | Notes |
|------|---------|---------|-------|---------|-----|-----------------|-------|
| | | | | | | | |

### Learnings Log

| Date | What we tested | What we learned | Decision made |
|------|---------------|----------------|---------------|
| | | | |

---

## Budget Allocation

| Phase | Channel | Budget | Timeline | Goal |
|-------|---------|--------|----------|------|
| Phase 1 | Reddit Ads — Track A (12 variants, psychographic) | ~$250 | Days 1–4 | Test intelligence team pitch × 3 creatives × 4 subreddits |
| Phase 1 | LinkedIn Sponsored — Track B (2 variants, senior ops) | ~$100 | Days 3–7 | Test capability gap pitch with company buyers |
| Phase 1 | Reddit Ads — Track C (2 variants, consultants) | ~$50 | Days 5–7 | Test reframed consultant pitch |
| Phase 2 | Organic (Reddit + Twitter + LinkedIn) | $0 | Days 5–14 | Amplify winning message |
| Phase 3 | Scale winning channel (Reddit/Meta/LinkedIn) | $300–500 | Days 14–30 | 50–100 users at <$10 CAC |
| **Total** | | **$500–900** | **30 days** | **100 users** |

---

## Success Criteria

| Milestone | Target | By when |
|-----------|--------|---------|
| Phase 1 ads live | Track A running on Reddit | Day 1 |
| First non-network signup | 1 | Day 5 |
| First task created by a stranger | 1 | Day 7 |
| Winning track identified (A, B, or C) | Clear signal | Day 7 |
| Winning creative identified | A1/A2/A3, B1/B2, or C1 winner | Day 7 |
| 10 users who create at least one task | 10 | Day 14 |
| CAC established | <$10 | Day 14 |
| First user returns after first output | Retention signal | Day 14 |
| 50 users | 50 | Day 21 |
| 100 users | 100 | Day 30 |

---

## What This File Is Not

This is not the content strategy (see [CONTENT_STRATEGY_v1.md](../CONTENT_STRATEGY_v1.md)).
This is not the messaging framework (see [GTM_POSITIONING.md](../../GTM_POSITIONING.md)).
This is not the IR narrative or investor-facing positioning — those docs stand as-is.

This is the experiment that tests whether any of those strategies are built on a real foundation.
