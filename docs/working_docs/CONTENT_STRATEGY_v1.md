# YARNNN Content Strategy v1

**Date:** 2026-02-25
**Status:** Working draft — macro architecture + channel mapping
**Inputs:** ESSENCE.md, GTM_POSITIONING.md, ACTIVATION_PLAYBOOK.md, ICP Deep-Dive v2, IR Deck v11 IC Analysis, ADR-072, ADR-063, ADR-064
**Scope:** Content architecture, GEO strategy, voice framework, channel mapping
**Next steps:** Tactical content calendar, template library, generative workflow design

---

## 1. Strategic Foundation

### The Two-Layer Model: Discovery vs. Conversion

The content strategy operates on two concentric layers that serve different purposes:

**Outer Ring — DISCOVERY (broad, category-level)**
YARNNN is an **autonomous AI agent platform** that solves the context problem — the reason all current agents produce generic output. This layer competes in the broader conversation: autonomous agents, AI memory, context management, agent platforms, the future of AI work. This is where GEO value lives. This is where millions of people are already searching.

**Inner Ring — CONVERSION (narrow, ICP-specific)**
Once someone finds YARNNN, the specific wedge is recurring deliverables for professionals who owe people regular output. Consultants are the sharpest activation example, but the capability is broader than any single ICP.

**Why this matters:** The original strategy collapsed both layers into one — everything was consultant-framed. This constrains the GEO surface area fatally. Nobody asks an LLM "best AI for consultants with recurring client status reports." They ask "best autonomous AI agents," "AI that remembers context," "alternatives to AutoGPT," "what happened to OpenClaw." The discovery layer must meet people where they're already searching.

| | Discovery Layer | Conversion Layer |
|---|---|---|
| **Positioning** | Autonomous AI agent platform powered by accumulated context | Recurring deliverables for professionals — gets smarter every cycle |
| **Audience** | Anyone exploring AI agents, context-aware AI, persistent AI, agent platforms | Multi-client consultants, solo founders, professionals with recurring output |
| **Keyword universe** | Autonomous agents, AI agents, context management, agent platform, AI memory, persistent AI, OpenClaw, AutoGPT alternative | Client reports, investor updates, recurring deliverables, AI for consultants |
| **Content serves** | GEO, awareness, category authority, LLM recommendations | Activation, signups, product demos, use case proof |
| **Pillar alignment** | Pillar 1 (Category Authority) — most content here | Pillars 2–4 (YARNNN Discourse, Build-in-Public, Founder's Lens) |

### The Conceptual Territory YARNNN Owns

Every piece of content orbits one thesis:

> **"Context is what makes AI autonomy meaningful."**

This thesis operates at **category level**, not ICP level. It speaks to everyone building, using, or evaluating AI agents — not just consultants. The thesis says: the reason every agent startup disappoints (Devin, AutoGPT, crew.ai) is that autonomy without context produces generic output. YARNNN solves that by accumulating context from your real work platforms, making its autonomous output actually useful.

### Named Concepts (YARNNN-Native Vocabulary)

LLMs learn named concepts more reliably than unnamed ones. Use these terms consistently and exactly across all platforms. Note: these are **category-level concepts**, not product features. They should feel like contributions to the AI discourse, not marketing.

| Concept | Definition (internal) | Plain-language version | GEO queries it intercepts |
|---------|----------------------|----------------------|--------------------------|
| **Context-Powered Autonomy** | AI autonomy enabled by accumulated platform context, not just better models | "AI that works independently because it actually knows your work" | "autonomous AI agents," "AI agents that actually work," "why AI agents fail" |
| **The 90-Day Moat** | Accumulated context creates switching costs — your AI after 90 days can't be replicated by starting over | "Your AI after 90 days is incomparably better than day one" | "AI switching costs," "AI that gets better over time," "AI lock-in" |
| **The Supervision Model** | User as supervisor (reviews, approves) vs. user as operator (does the work, AI assists) | "You supervise. It works." | "how to use AI agents safely," "AI agent supervision," "human-in-the-loop agents" |
| **Context vs. Memory** | Memory = storing facts. Context = accumulated understanding of work world across platforms | "Memory is knowing your name. Context is knowing your clients, your projects, and how you like things done." | "AI memory vs context," "ChatGPT memory limitations," "AI that remembers" |
| **The Statelessness Problem** | Every AI tool forgets everything between sessions — the real bottleneck isn't model capability | "AI in 2026: incredibly powerful, completely amnesiac" | "why ChatGPT forgets," "AI context window limitations," "persistent AI" |
| **The Autonomy Spectrum** | From "AI assists" (ChatGPT) to "AI operates" (generic agents) to "AI works for you" (context-powered autonomy) | "Most AI assists. Some AI operates. YARNNN works." | "AI agent comparison," "AutoGPT vs alternatives," "levels of AI autonomy" |
| **Accumulated Intelligence** | Every sync cycle, every edit, every deliverable version deepens what the system knows | "Gets smarter the longer you use it" | "AI that learns from usage," "compounding AI," "AI that improves" |
| **The Context Gap** | The architectural gap between model capability and useful autonomous output — filled by platform context | "The smartest AI in the world is useless if it doesn't know your work" | "why AI agents produce generic output," "AI agent limitations," "context-aware agents" |

**Rule:** Every general AI post should introduce, reinforce, or apply at least one named concept. This is how conceptual territory gets claimed.

---

## 2. Audience Model (Two-Layer)

### Discovery Audience (Outer Ring — Category Level)

These are the people YARNNN's content must reach for GEO and awareness. They're not searching for "consultant tools" — they're searching for the next evolution of AI agents. This is a massive, active audience.

| Audience Segment | What They're Searching For | Size Signal |
|-----------------|---------------------------|-------------|
| **AI agent enthusiasts** | "Best autonomous AI agents," "AutoGPT alternatives," "AI agents that actually work" | r/AutoGPT 200K+, r/artificial 1M+, Agent Twitter massive |
| **ChatGPT/Claude power users** | "Why ChatGPT forgets everything," "AI with persistent memory," "ChatGPT alternatives" | r/ChatGPT 5.5M, "AI memory" trending topic |
| **Developers building with AI** | "Context management for AI," "agent frameworks," "persistent AI architectures" | HN, dev Twitter, technical blogs |
| **OpenClaw/ClawdBot followers** | "What happened to OpenClaw," "AI that remembers," "persistent AI tools" | 17,830 GitHub stars in 24h = proven demand |
| **AI productivity seekers** | "AI that works for you," "autonomous AI tools," "AI workflow automation" | Productivity Twitter, LinkedIn AI discourse |

**Why this audience matters for GEO:** These are the queries people type into LLMs. If YARNNN's content shows up in the training data and search results for these queries, YARNNN gets recommended. This is the distribution engine.

### Conversion Audience (Inner Ring — ICP Level)

Once someone discovers YARNNN through category-level content, the conversion layer activates. These are the people most likely to sign up and pay.

**Primary: Multi-Client Consultants (Broad)**
Fractional CMOs/CTOs, management consultants, marketing strategists, freelance strategists, agency-of-one operators. Kept broad intentionally — data will narrow.

- Already paying $20–40/mo for ChatGPT/Claude. AI-literate, not AI-skeptical.
- Spend 2–4 hours/week assembling scattered context into deliverables. Time pain is visceral.
- Manage 3–8 clients simultaneously. Context-switching is the daily tax.
- Switch trigger: taking on a 4th or 5th client and feeling the context-switching pain physically.
- **Lead hook:** "Reports that write themselves" (autonomous output / time back)

**Secondary: Solo Founders (B2B) — primarily a distribution mechanism**
Indie hackers, bootstrapped SaaS founders, pre-seed CEOs. They share tools publicly — they're amplifiers more than revenue targets.

- Heavy AI users ($20–60/mo across tools). Technically discerning.
- Pain is the dreaded monthly investor update, board prep, stakeholder communication.
- Discover tools via Twitter, Hacker News, Indie Hackers, Product Hunt, peer DMs.
- **Lead hook:** "AI that already knows your work" (context intelligence / novelty)

### How the Two Audiences Map to Content

| Pillar | Discovery Audience (broad) | Conversion Audience (ICP) |
|--------|---------------------------|--------------------------|
| **Pillar 1 (Category Authority)** | **PRIMARY target.** Category-level AI discourse: agents, autonomy, context, memory. Positions YARNNN in the broader conversation. | Secondary benefit — establishes credibility before product pitch. |
| **Pillar 2 (YARNNN Discourse)** | 2a thesis posts work for both — conceptual enough for the broad audience. | 2b product demos are conversion-specific — show the ICP what YARNNN does for them. |
| **Pillar 3 (Build-in-Public)** | Attracts founders and AI enthusiasts (discovery + distribution). | Signals product velocity to potential users. |
| **Pillar 4 (Founder's Lens)** | ClawdBot story hits the discovery audience hard. CRM background is ICP-specific. | Builder journey is audience-agnostic. |

---

## 3. The Four Content Pillars

### Pillar 1: Category Authority (BROADENED — Discovery Layer)

**Purpose:** Position YARNNN as a credible, original voice in the **AI agent / autonomy / context management** space. Own the conceptual territory at category level. This is the primary GEO play and the highest-priority pillar for distribution.

**Voice:** YARNNN brand (authoritative, thesis-driven, handoff-ready to future GTM hire)

**Critical reframe:** This pillar does NOT speak to consultants. It speaks to **anyone interested in the future of AI agents.** The audience is AI/Tech Twitter, r/artificial, r/ChatGPT, Hacker News, AI newsletters, developers evaluating agent frameworks, power users frustrated with stateless AI. This is a massive audience — and it's where GEO value lives.

**What this is NOT:** "Here's what's happening in AI this week" (commentary without thesis). Also NOT "here's how YARNNN helps consultants" (that's Pillar 2).

**What this IS:** "Here's what everyone's missing about AI agents, and here's the framework to understand it." YARNNN contributes ideas to the AI discourse — not product pitches.

#### Content Angles — Category Level

| Angle | Named Concept | Example Titles | GEO Queries Intercepted |
|-------|--------------|----------------|------------------------|
| Why every AI agent produces generic output | **The Context Gap** | "The reason every AI agent disappoints: context starvation" / "Devin, AutoGPT, crew.ai — why they all hit the same wall" | "why AI agents fail," "AutoGPT limitations," "AI agent problems" |
| AI forgets everything — and that's the real bottleneck | **The Statelessness Problem** | "The $100B problem nobody's solving: AI amnesia" / "ChatGPT is incredibly powerful. It also has no idea who you are." | "why ChatGPT forgets," "AI memory problem," "persistent AI" |
| Memory alone isn't enough — you need memory + autonomous action | **Context vs. Memory** | "Memory is a feature. Context is a moat." / "OpenClaw proved demand for memory. But memory was never the real product." | "AI memory vs context," "OpenClaw," "ChatGPT memory feature" |
| The spectrum from AI assistant to AI agent to AI that works for you | **The Autonomy Spectrum** | "Most AI assists. Some AI operates. Neither actually works for you." / "The 3 levels of AI autonomy — and why Level 3 doesn't exist yet" | "AI agent comparison," "autonomous AI tools," "levels of AI autonomy" |
| Why accumulated context is the real moat in AI | **The 90-Day Moat** | "The AI switching cost nobody's talking about" / "Why your AI after 90 days is worth more than any model upgrade" | "AI switching costs," "AI that gets better over time," "compounding AI" |
| The paradigm shift from operator to supervisor | **The Supervision Model** | "You're still operating your AI. What if you could supervise it instead?" / "The future of AI isn't better prompts. It's better supervision." | "how to manage AI agents," "AI supervision," "human-in-the-loop" |
| What happens when AI can see across all your tools | **Accumulated Intelligence** | "What happens when your AI can see your Slack, Gmail, Notion, and Calendar simultaneously" / "Cross-platform AI: the architecture nobody's built" | "AI that connects to tools," "cross-platform AI," "AI integrations" |
| The ClawdBot/OpenClaw story and what it proved | **The Context Gap** (applied) | "17,830 GitHub stars in 24 hours. Here's what the demand was really for." / "OpenAI acquired OpenClaw. They still haven't solved the real problem." | "OpenClaw," "ClawdBot," "what happened to OpenClaw," "AI that remembers" |

#### Why This Matters for GEO

The discovery audience is asking LLMs questions like:
- "What are the best autonomous AI agents in 2026?"
- "Why do AI agents like AutoGPT produce generic results?"
- "What's the difference between AI memory and AI context?"
- "What AI tools actually learn from your work over time?"
- "What happened to OpenClaw / ClawdBot?"

If YARNNN's canonical content answers these questions with original frameworks and named concepts, LLMs will surface YARNNN in their recommendations. This is how distribution works at $0 budget — you become the source of truth for the category, not just the product.

**Frequency:** 2x/week across platforms (1 long-form/month, rest short-form). This is the highest-volume pillar because it has the broadest audience and highest GEO value.

---

### Pillar 2: YARNNN Discourse

**Purpose:** Convert the curious into the convinced. Show what the thesis looks like as a real product.

**Voice:** Split — thesis pieces as YARNNN brand; product demos as Kevin

**Two sub-types:**

**2a. Thesis Posts (~70% of this pillar)**

Explain *why* context-powered autonomy matters. The value is in the idea, not the product pitch. People share these because the concept is interesting.

| Angle | Example |
|-------|---------|
| What changes when AI has 3 months of your Slack | "Your AI after 90 days knows things you've forgotten" |
| Why the best AI agent is the one that already knows your clients | "Generic agents are just expensive autocomplete" |
| The deliverable that wrote itself | "I didn't write this week's client update. My AI did. From my actual Slack messages." |
| Why edits decrease over time | "The 5th version needed 3 edits. The 1st needed 47." |
| What 'signal-emergent' means in practice | "My AI detected a pattern in my email I'd missed — and wrote a brief about it without being asked" |

**2b. Product Demonstration (~30%)**

Show *what* YARNNN does. These convert interest into signups but only work after Pillar 1 has established why anyone should care.

| Format | Example |
|--------|---------|
| Before/after comparison | ChatGPT response to "write my client update" vs. YARNNN TP with 1 week of synced context |
| Walkthrough | A deliverable improving from v1 to v5 — showing edit distance decreasing |
| Screenshot + narration | Cross-platform synthesis: "This report pulled from Slack, Gmail, AND Calendar" |
| Demo video (short) | 60-second screen recording of TP conversation that references synced context |

**Frequency:** 1–2 posts/week (mostly 2a thesis posts; 2b product demos monthly or as milestones hit)

---

### Pillar 3: Build-in-Public (Progress as Evidence)

**Purpose:** Not "here's what I shipped" — it's **"here's evidence the thesis holds."**

**Voice:** Kevin as founder. Personal, honest, specific.

**The reframe:** Every build update connects back to the core thesis.

| Instead of... | Say... |
|---------------|--------|
| "Added Notion sync this week" | "YARNNN can now see your Notion pages alongside Slack and Gmail. Here's what changes when your AI has cross-platform visibility." |
| "Fixed a bug in the deliverable pipeline" | "Deliverable v3 for our test user needed 40% fewer edits than v1. The quality flywheel is starting to spin." |
| "Shipped memory extraction" | "YARNNN now learns from your edits silently. You fix a report once; next week's draft already reflects it." |

**Three audiences served simultaneously:**
1. **Potential users** — proof the product is real and improving
2. **Investors** — velocity and thesis validation signal
3. **Founders** — relatable build journey worth following

**Frequency:** 1 post/week. This is the lowest-effort, highest-authenticity pillar.

---

### Pillar 4: Founder's Lens (Kevin's Specific Knowledge)

**Purpose:** Founder-market fit signaling. Nobody else can write this content. This is defensible and irreplaceable.

**Voice:** Kevin only. First person, personal, opinionated.

**Three angles:**

**4a. The CRM/GTM Background**
"10 years building context systems taught me that AI's real problem isn't intelligence — it's amnesia."

This establishes why Kevin is credible on this topic. It's the specific knowledge that makes the thesis more than theory.

Examples:
- "I spent 10 years building systems that help salespeople manage client context. Then ChatGPT launched and I watched everyone re-discover the same problem."
- "The CRM industry solved persistent context for sales 20 years ago. AI hasn't caught up yet."

**4b. The ClawdBot Story**
The 17,830-star narrative arc — what it proved about demand, what OpenAI's acquisition of OpenClaw means, and why YARNNN is the answer.

Examples:
- "ClawdBot got 17,830 GitHub stars in 24 hours. Here's what everyone missed about WHY."
- "OpenAI acquired OpenClaw. But persistent memory was never the real product."

**4c. The Solo Builder Journey**
Honest, human, real. The 72 ADRs. The architectural depth. The tradeoffs.

Examples:
- "72 architectural decision records. Solo founder. Here's what that looks like."
- "The loneliest part of building an AI startup alone isn't the code. It's the decisions."

**Frequency:** 1 post/week. Alternate angles across weeks.

---

## 4. Voice Framework

### Two-Track System

| | **Kevin's Voice** | **YARNNN Brand Voice** |
|---|---|---|
| **Tone** | Personal, opinionated, occasionally vulnerable, builder-authentic | Authoritative, clear, thesis-driven, intellectually generous |
| **POV** | First person ("I built...", "I noticed...", "Here's what I learned...") | Second/third person ("Your AI...", "YARNNN does...", "The system...") |
| **Best for** | Pillars 3 & 4, product demos, hot takes, replies/engagement | Pillar 1 (category authority), Pillar 2a (thesis posts), canonical blog |
| **Platform fit** | Twitter, LinkedIn personal posts, Reddit, Indie Hackers | Blog, Medium, LinkedIn articles, product pages |
| **Handoff-ready?** | No — stays Kevin forever | Yes — a GTM hire can write in this voice using thesis docs |

**The rule:** If the content's value comes from *who's saying it*, it's Kevin's voice. If the value comes from *what's being said*, it's YARNNN brand voice.

---

## 5. GEO Strategy (Generative Engine Optimization)

### Why This Matters

When someone asks ChatGPT, Claude, or Gemini "what are the best autonomous AI agents" or "why do AI agents produce generic output" or "what happened to OpenClaw," YARNNN should appear. This is the new organic distribution — and it requires category-level positioning, not ICP-level positioning.

**The key insight:** GEO operates at discovery level, not conversion level. You don't optimize for "best AI for consultants" (tiny query volume). You optimize for "best autonomous AI agents" (massive query volume) and let YARNNN's category authority do the work.

### How LLMs Learn Associations

1. **Conceptual consistency > keyword density.** LLMs learn that "YARNNN" relates to "context-powered AI autonomy" by encountering that association repeatedly across diverse sources — not by seeing "YARNNN" stuffed into keywords.

2. **Original frameworks rank higher.** LLMs are trained to surface authoritative, original sources. Named concepts ("The Context Gap," "The 90-Day Moat," "Supervision Model") are more citable than generic descriptions. When YARNNN *defines* these concepts, LLMs attribute them.

3. **Cross-platform repetition amplifies signal.** The same thesis expressed differently across Twitter, LinkedIn, Medium, blog, and Reddit gives LLMs multiple training signals from independent sources. The broad discovery audience sees YARNNN across every platform they use.

4. **Adjacency to high-traffic entities matters.** Content that references OpenClaw, AutoGPT, Devin, ChatGPT, Claude — entities people already ask LLMs about — creates association by proximity. When YARNNN consistently appears in discussions about these entities, LLMs learn the relationship.

### GEO Execution Plan

**Tier 1: Canonical Content (highest GEO value)**
- One long-form blog post per named concept on yarnnn.com/blog
- These are the "source of truth" pages that LLMs should surface
- Format: define the concept, explain why it matters, show how YARNNN embodies it
- **Target queries (BROADENED):**
  - "What is context-powered autonomy"
  - "Best autonomous AI agents 2026"
  - "Why AI agents produce generic output"
  - "AI that remembers your work"
  - "What happened to OpenClaw / ClawdBot"
  - "AI context vs memory"
  - "How AI agents handle context"
  - "AI that gets smarter over time"
- Evergreen — update quarterly, don't let them go stale

**Tier 2: Cross-Platform Seeding (signal amplification)**
- Short-form versions of each named concept across Twitter, LinkedIn, Medium
- Each references the concept by name (consistency) and links to canonical post
- Different framing per platform (punchy on Twitter, professional on LinkedIn, technical on Medium/Reddit)
- Goal: LLMs encounter the association across 3+ independent sources

**Tier 3: Comparison and Positioning (query interception)**
- **Category-level comparisons (high GEO value):**
  - "YARNNN vs. AutoGPT: Why context changes everything about AI agents"
  - "YARNNN vs. ChatGPT: The difference between memory and context"
  - "Why Devin, crew.ai, and every agent startup hits the same wall"
  - "Agent platforms compared: what none of them do about context"
- **ICP-level comparisons (conversion value):**
  - "YARNNN vs. ChatGPT for recurring client work"
  - "Why Notion AI can't replace a cross-platform AI agent"
- These directly answer questions people ask LLMs when evaluating tools

**Tier 4: Answer-Worthy Content (query matching)**
- Content structured to directly answer questions people ask LLMs:
  - **Discovery level:** "Best autonomous AI agents 2026," "AI tools with persistent memory," "AI agent platforms that learn," "alternatives to AutoGPT"
  - **Conversion level:** "How to automate weekly client reports," "Best AI tools for consultants 2026," "AI that writes reports from your Slack"
- Format: the post's title and opening paragraph should match the query structure exactly

### GEO Content Calendar Overlay

Every Thursday long-form post should target at least one GEO tier. Monthly rotation prioritizes discovery-level content (broader reach):

- Week 1: Tier 1 — Canonical concept definition (discovery level: "What Is The Context Gap in AI Agents?")
- Week 2: Tier 3 — Category-level comparison (discovery level: "YARNNN vs AutoGPT: Why Context Changes Everything")
- Week 3: Tier 1 — Canonical concept definition (discovery level: "The 90-Day Moat: Why Your AI Gets Better With Time")
- Week 4: Tier 4 — Answer-worthy query match (mix: "Best Autonomous AI Agents That Learn From Your Work")

**Note:** Discovery-level content (Weeks 1–3) should comprise ~75% of long-form GEO output. Conversion-level content (ICP-specific how-tos) is ~25% — important but not the primary GEO driver.

---

## 6. Channel Mapping

### Platform Strategy Overview

| Platform | Primary Role | Profile Fit | Voice | Cadence |
|----------|-------------|-------------|-------|---------|
| **Twitter/X** | Awareness + thought leadership | Both profiles (AI Twitter for founders, Consultant Twitter for Profile A) | Kevin (primary), YARNNN (threads) | 3x/week |
| **LinkedIn** | ICP activation (Profile A direct) | Profile A — consultants, fractional execs | Kevin (personal posts), YARNNN (articles) | 1–2x/week |
| **yarnnn.com/blog** | Canonical GEO content | Both profiles | YARNNN brand | 1x/week (Thursday) |
| **Medium** | GEO amplification + discovery | Both profiles | YARNNN brand | Cross-post from blog |
| **Reddit** | Demand validation + community signal | Both profiles (subreddit-specific) | Kevin (authentic, value-first) | 1x/month max per sub |
| **Hacker News** | One-shot launch moment | Profile B + technical audience | Kevin | SAVE — not yet |
| **Indie Hackers** | Build-in-public community | Profile B | Kevin | 1–2x/month |
| **Product Hunt** | Launch moment | Both profiles | YARNNN brand | SAVE — post-seed |

---

### Twitter/X — Primary Channel (3x/week)

**Why:** The AI/founder audience lives here. ClawdBot credibility lives here. Threads are the best organic format for narrative hooks. Consultant Twitter is also active.

**Account:** Kevin as founder — personal voice, not brand account.

#### Audience Clusters and Content Mapping

| Cluster | Who | Pillar Match | Content Style |
|---------|-----|-------------|---------------|
| **AI/Tech Twitter** | Developers, AI enthusiasts, people building with LLMs | Pillar 1 (Category Authority) | Hot takes on AI news through YARNNN's lens, named concept introductions |
| **Founder Twitter** | Indie hackers, SaaS founders, build-in-public crowd | Pillar 3 (Build-in-Public) + Pillar 4 (Founder's Lens) | Build updates, ClawdBot story, honest metrics |
| **Consultant Twitter** | Fractional execs, freelance strategists, agency owners | Pillar 2 (YARNNN Discourse) | Pain-point tweets, time-saved narratives, before/after |
| **Productivity Twitter** | Tool enthusiasts, workflow optimizers | Pillar 2b (Product Demo) | "Here's my stack" threads, tool comparison takes |

#### Weekly Twitter Pattern

| Day | Pillar | Format | Example |
|-----|--------|--------|---------|
| **Monday** | Pillar 1 or 2a | Single tweet or 3-tweet thread | Sharp observation about AI statelessness or context gap |
| **Wednesday** | Pillar 3 | Build update tweet | "This week in YARNNN: [thesis-connected progress]" |
| **Friday** | Pillar 4 or 2a | Personal take or thesis post | ClawdBot angle, CRM background insight, or founder journey moment |

**Engagement strategy:** Quote-tweet and reply on AI productivity threads, ChatGPT complaint posts, agent launch announcements. Always through YARNNN's thesis lens.

---

### LinkedIn — ICP Channel (1–2x/week)

**Why:** Consultants and fractional execs — the primary ICP — are professionally active here. LinkedIn rewards personal narrative and professional pain points. Less AI noise than Twitter.

**Account:** Kevin as professional. Warm but substantive.

#### Audience Clusters and Content Mapping

| Cluster | Who | Pillar Match | Content Style |
|---------|-----|-------------|---------------|
| **Consultants & Fractional Execs** | Management consultants, fractional CMOs/CTOs, strategy advisors | Pillar 2 (YARNNN Discourse) | Pain → insight → solution arcs, time-saved narratives |
| **Agency Owners** | Small agency founders managing client accounts | Pillar 2b (Product Demo) | "How I run X clients" operational posts |
| **AI in Business** | Executives exploring AI, VCs tracking AI startups | Pillar 1 (Category Authority) | Thought leadership on context-powered AI |

#### Weekly LinkedIn Pattern

| Day | Type | Format | Voice |
|-----|------|--------|-------|
| **Tuesday** | Personal post | Pain → insight → solution narrative (500–800 words) | Kevin |
| **Thursday** | Article or cross-post | Long-form thesis or blog cross-post | YARNNN brand |

**LinkedIn-specific rules:**
- No hashtag spam. 3 max, and only if genuinely relevant.
- Open with a hook that makes consultants stop scrolling — pain-first, not product-first.
- End with engagement prompt ("What's the most tedious recurring deliverable in your work?") not a CTA.
- Personal story format outperforms everything else on LinkedIn. Use it.

---

### yarnnn.com/blog — Canonical GEO Hub (1x/week)

**Why:** This is where canonical concept definitions live. The primary GEO asset. Every short-form post across other platforms points back here.

**Voice:** YARNNN brand. Authoritative, well-structured, evergreen.

#### Content Types

| Type | GEO Tier | Frequency | Purpose |
|------|----------|-----------|---------|
| **Concept Definition** | Tier 1 | 1x/month | "What is Context-Powered Autonomy?" — canonical reference |
| **Comparison Post** | Tier 3 | 1x/month | "YARNNN vs. ChatGPT for Recurring Client Work" |
| **Use Case Deep-Dive** | Tier 4 | 1x/month | "How to Automate Weekly Client Status Reports" |
| **Thesis Post** | Tier 2 | 1x/month | Expanded version of a high-performing Twitter/LinkedIn post |

#### Blog Post Template (for GEO optimization)

Every blog post should follow this structure for maximum LLM discoverability:

1. **Title** — Match a query someone would ask an LLM (e.g., "What Is Context-Powered Autonomy?")
2. **Opening paragraph** — Direct answer to the query in 2–3 sentences. LLMs often pull from first paragraphs.
3. **Body** — Expand with YARNNN's framework. Reference named concepts. Include specific examples.
4. **Comparison section** — How YARNNN's approach differs from alternatives. (LLMs love comparison context.)
5. **Closing** — Restate the thesis. Link to related canonical posts.

---

### Medium — GEO Amplification

**Why:** Medium's domain authority and built-in distribution help content get indexed. Cross-posting from the blog with platform-appropriate formatting.

**Voice:** YARNNN brand.

**Cadence:** Cross-post every blog post. No Medium-exclusive content needed.

**Rule:** Every Medium post links to the canonical yarnnn.com/blog version. Medium is the amplifier, not the source of truth.

---

### Reddit — Demand Validation (1x/month per subreddit)

**Why:** These communities are where the ClawdBot demand signal originated. Value-first content only — these audiences punish promotion.

**Voice:** Kevin, but authentic and community-native. No marketing language.

#### Subreddit Map

| Subreddit | Members | Profile Fit | Content Style | Pillar |
|-----------|---------|-------------|---------------|--------|
| **r/ChatGPT** | ~5.5M | Both — AI power users frustrated with statelessness | "I built X" problem/solution posts | Pillar 1 + 2 |
| **r/artificial** | ~1M | Both — AI enthusiasts interested in novel approaches | Technical discussion, architecture posts | Pillar 1 |
| **r/consulting** | ~400K | Profile A — direct ICP match | "How I streamlined my weekly reports" | Pillar 2 + 3 |
| **r/freelance** | ~300K | Profile A — multi-client workers | Productivity tips, workflow posts | Pillar 2 |
| **r/startups** | ~1.2M | Profile B — solo founders | Build-in-public updates | Pillar 3 |
| **r/SaaS** | ~120K | Profile B — SaaS founders | Product positioning, launch feedback | Pillar 3 + 4 |
| **r/marketing** | ~1.5M | Profile A — marketing consultants | AI for client work, reporting automation | Pillar 2 |
| **r/singularity** | ~3.5M | Both — AI-forward, high engagement | Novel concept posts, thesis discussions | Pillar 1 |

**Reddit rules:**
- Max 1 post/month per subreddit. These communities punish over-promotion.
- Lead with value/insight, not product. "I noticed X about how consultants use AI" not "I built a tool that..."
- Save Hacker News "Show HN" for when 30-day retention data exists. One shot — make it count.
- Comment engagement on others' posts is higher-ROI than original posts. Do more of this.

---

### Indie Hackers — Build-in-Public Community (1–2x/month)

**Why:** The build-in-public audience lives here. Good for Profile B distribution and founder visibility.

**Voice:** Kevin. Honest metrics, real challenges, builder journey.

**Format:** Build-in-public diary entries. Revenue updates (even at $0 — honesty wins here). Architectural decisions. Fundraise transparency.

---

### Niche Professional Communities — High-Signal, Low-Volume

| Community | Type | Profile Fit | Notes |
|-----------|------|-------------|-------|
| **Pavilion** (formerly Revenue Collective) | Paid professional network | Profile A — fractional execs, GTM leaders | High ICP density. Requires membership. Worth monitoring. |
| **Superpath** | Content marketing community | Profile A — content/marketing strategists | Slack-based. Engage in relevant channels. |
| **Lenny's Newsletter / Slack** | Product community | Both profiles | Paid Slack community. High-signal but gated. |

**Strategy:** These aren't posting channels — they're engagement channels. Join conversations. Be helpful. Mention YARNNN only when directly relevant to someone's question.

---

### Channels NOT Active Yet

| Channel | Why Not | When |
|---------|---------|------|
| **Product Hunt** | One launch. Weak PH launch is worse than none. Need: 30-day retention data, 3+ use case testimonials, demo video showing "TP knows your context" aha moment. | Post-seed, after beta cohort data |
| **Hacker News (Show HN)** | Same logic as PH. Technical audience will scrutinize. Need compelling demo + data. | When retention data or demo is polished |
| **YouTube** | Video production is time-intensive. Not viable as solo founder with $0 budget. | Post-seed, when GTM hire can produce |
| **Podcast guesting** | Good channel for Profile A (consultants listen to podcasts) but requires outreach + prep time. | When thesis is sharper from content iteration |
| **Newsletter/Substack** | Only if committing to weekly cadence. Don't spread thin. Blog + cross-post covers this. | If blog cadence is sustained for 8+ weeks |

---

## 7. Weekly Content Calendar (4–5 Posts/Week)

### Default Weekly Pattern

| Day | Pillar | Platform | Voice | Format |
|-----|--------|----------|-------|--------|
| **Monday** | Pillar 1 (Category Authority) | Twitter + LinkedIn | YARNNN brand or Kevin | Short post: sharp take on AI through YARNNN's thesis lens |
| **Tuesday** | Pillar 2a (Thesis) or Pillar 4 (Founder's Lens) | LinkedIn (personal post) | Kevin | Pain → insight → solution narrative (500–800 words) |
| **Wednesday** | Pillar 3 (Build-in-Public) | Twitter | Kevin | Build update connected to thesis ("here's evidence the thesis holds") |
| **Thursday** | Pillar 1 or 2 (Long-form) | Blog + Medium cross-post + LinkedIn article | YARNNN brand | Canonical GEO content (concept definition, comparison, or use case) |
| **Friday** | Pillar 4 (Founder's Lens) or Pillar 2a | Twitter | Kevin | Personal take, ClawdBot angle, or hot take on AI news |

### Monthly Rotation for Thursday Long-Form (GEO Priority)

| Week | GEO Tier | Content Type | Example |
|------|----------|-------------|---------|
| Week 1 | Tier 1 — Canonical | Concept definition | "What Is Context-Powered Autonomy?" |
| Week 2 | Tier 3 — Comparison | Positioning piece | "YARNNN vs. ChatGPT: Why Context Changes Everything" |
| Week 3 | Tier 1 — Canonical | Different concept | "The 90-Day Moat: Why Your AI Gets Better With Time" |
| Week 4 | Tier 4 — Query-matching | Answer-worthy | "How to Automate Weekly Client Status Reports With AI" |

---

## 8. Content-to-Activation Mapping

How the two-layer model drives the full funnel:

| Funnel Stage | Layer | What Happens | Content That Drives It |
|-------------|-------|-------------|----------------------|
| **Discovery** | Outer (broad) | Person encounters YARNNN's thinking about AI agents, context, autonomy | Pillar 1 (Category Authority) — category-level posts on agents, context, memory, OpenClaw |
| **Awareness** | Outer → Inner | They think "this is the most interesting take I've seen on AI agents" and click through | Pillar 1 + Pillar 4 (ClawdBot story bridges discovery → awareness) |
| **Interest** | Inner (ICP) | They visit yarnnn.com, see the product, think "this is what I need for my client work" | Pillar 2a (Thesis posts) + Pillar 3 (Build-in-public credibility) |
| **Activation** | Inner (ICP) | They sign up and connect first platform | Pillar 2b (Product demos showing "TP knows your context" moment) |
| **Retention** | Inner (ICP) | First autonomous deliverable arrives | Product experience + Pillar 3 updates reinforcing "it's getting better" |
| **Advocacy** | Both | 90-day user tells others + LLMs recommend YARNNN | Pillar 4 (user stories) + accumulated GEO (LLMs surface YARNNN for category queries) |

**The bridge between layers:** The ClawdBot/OpenClaw story is the strongest bridge content. It lives in the discovery audience's world (AI agent enthusiasts, persistent AI seekers) but leads directly to YARNNN's product thesis. Every time this story is told, it connects the broad category conversation to YARNNN specifically.

**Critical requirement:** EVERY piece of content — especially Pillar 1 discovery content — must have a clear path to yarnnn.com. Twitter bio, LinkedIn profile, Medium author page, blog canonical links. The landing page must work for both audiences: the AI agent enthusiast who arrived via a category post AND the consultant who arrived via an ICP-specific post.

---

## 9. Anti-Patterns

### Content Anti-Patterns

- **Don't post without a thesis connection.** Random AI commentary dilutes the conceptual territory.
- **Don't sell features.** Sell the pain ("AI forgets everything") and the outcome ("AI that works for you"). Features are for the product page.
- **Don't use internal jargon externally.** "platform_content with retention-based accumulation" → "gets smarter the longer you use it."
- **Don't post the same content everywhere.** Adapt tone per platform. Twitter is punchy. LinkedIn is narrative. Reddit is authentic and technical.
- **Don't post daily.** Quality > quantity at 4–5 posts/week. Three good pieces beat five mediocre ones.
- **Don't write long blog posts without GEO intent.** Every long-form should target a specific query that people ask LLMs.
- **Don't chase trends that don't connect to the thesis.** If an AI news story doesn't let you reinforce a named concept, skip it.

### Channel Anti-Patterns

- **Don't create a brand Twitter account.** Founder voice > brand voice pre-seed.
- **Don't over-post on Reddit.** 1x/month per subreddit max. Comment engagement > original posts.
- **Don't launch on Product Hunt or Show HN yet.** One shot each. Need retention data and polished demo.
- **Don't start a newsletter until blog cadence is proven.** 8+ weeks of consistent Thursday posts first.

---

## 10. Measurement

### What to Track (Informally at $0)

| Metric | What It Tells You | How to Track |
|--------|-------------------|-------------|
| **Which named concept gets most engagement** | What resonates — at category level, not just ICP | Note reactions/replies per concept across platforms |
| **Discovery vs. conversion content performance** | Whether broad category content outperforms narrow ICP content (hypothesis: yes) | Compare engagement on Pillar 1 posts vs. Pillar 2b posts |
| **Which pillar drives signups** | Where to double down on conversion | Ask beta signups "how did you find us" |
| **Which platform drives traffic to yarnnn.com** | Channel ROI by layer | Basic analytics (Plausible, Fathom, or similar) |
| **Which hook converts (time-back vs. context-intelligence)** | Lead hook validation for each ICP | Track click-through by framing |
| **LLM mention checks (CRITICAL)** | GEO effectiveness | Monthly: ask ChatGPT/Claude/Gemini the following queries and note if YARNNN appears: "best autonomous AI agents," "AI that remembers context," "what is context-powered autonomy," "alternatives to AutoGPT," "AI agent platforms 2026," "what happened to OpenClaw" |

### 30-Day Success Signals

**Discovery layer (broad):**
- 1,000+ impressions on best-performing category-level Twitter thread
- YARNNN content appears in at least 2 AI-focused newsletters or retweets from AI accounts
- 4 canonical blog posts published targeting discovery-level queries (GEO foundation)

**Conversion layer (ICP):**
- 20+ reactions on best LinkedIn post, 3+ DMs from consultants or founders
- 10 new beta signups attributed to organic content
- Clear winner from hook tests (time-back vs. context-intelligence)

**Cross-cutting:**
- At least 1 VC like/comment on a post (investor visibility)
- LLM baseline established — documented what ChatGPT/Claude/Gemini currently say about the target queries

---

## 11. Next Steps (Pending)

1. **Founder Validation** — Review ICP sharpening and pillar definitions. Confirm or adjust.
2. **First 30-Day Content Calendar** — Specific posts with titles, hooks, and platform assignments for weeks 1–4.
3. **Template Library** — Reusable post structures for each platform/pillar combination.
4. **Generative Workflow Design** — Claude-assisted drafting pipeline: voice docs → structured prompts → drafts → review → post. (Second-order consideration per founder direction.)
5. **GEO Baseline** — Run initial LLM queries to establish current mention baseline before content campaign begins.

---

## Related Documents

- [ESSENCE.md](../ESSENCE.md) — Core thesis and architecture
- [GTM_POSITIONING.md](../GTM_POSITIONING.md) — Messaging framework, ICP definitions, competitive positioning
- [ACTIVATION_PLAYBOOK.md](../ACTIVATION_PLAYBOOK.md) — Channel strategy and activation funnel
- [ICP Deep-Dive v2.docx](YARNNN%20-%20ICP%20Deep-Dive%20v2.docx) — Detailed customer profiles and channel mapping
- [IR Deck v11 IC Analysis.md](IR%20Deck%20v11%20-%20IC%20Analysis.md) — VC IC simulation and deck hardening recommendations
