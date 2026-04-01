# YARNNN GTM Positioning & Messaging

**Last Updated:** 2026-04-01 (v3.0 — organizational intelligence reframe, psychographic ICP emphasis, architecture alignment with ADR-138/140/141/151/153)

**Reference:** See [ESSENCE.md](../../ESSENCE.md) for core thesis and architecture. See [ADR-138](../../adr/ADR-138-agents-as-work-units.md) for current model (Agents = WHO, Tasks = WHAT).

**What changed in v3.0:** The product architecture evolved significantly between v2.0 and v3.0. Gmail/Calendar integrations removed (ADR-131). Platform content sync replaced by live task-driven data access (ADR-153). Agents are now pre-scaffolded domain-stewards with accumulated context domains (ADR-140, ADR-151). Tasks are work units assigned to agents (ADR-138). The value proposition shifts from "automate recurring deliverables" to "gain organizational intelligence capabilities you can't sustain manually." ICP emphasis shifts from occupation-first (consultants) to psychographic-first (intelligence-hungry professionals).

---

## Core Positioning

**One-liner:** Your AI team that learns your business and works while you don't

**Tagline:** Five domain experts. Always learning. Always working. $19/month.

**Elevator pitch:**
YARNNN gives you a pre-built team of AI domain experts — competitive intelligence, market research, business development, operations, and marketing — that connect to your Slack and Notion, accumulate knowledge of your business over time, and produce work autonomously. You assign tasks, they execute on schedule, and every cycle they get better because they're building on months of accumulated domain knowledge. It's the intelligence team you need but can't afford to hire.

**The reframe (v3.0):** The product isn't "automate your reports." It's "gain organizational capabilities you've never had." Most growing companies know they should track competitors, monitor their market, synthesize operational signals — but no one has time and they can't justify hiring specialists. YARNNN is the fractional intelligence team that does this work continuously and gets smarter with tenure.

---

## The Core Problem

### What users experience:
- AI tools that forget everything between sessions
- Spending time re-explaining context every single time
- No AI that can actually DO work independently — only assist
- Agent tools that are autonomous but generic (no context about YOUR work)

### The visceral moment:
> "I use ChatGPT every day. Every day, I explain the same things. It still doesn't know my clients, my projects, or how I like things done."

### How competitors fail:
- **ChatGPT/Claude:** Powerful but stateless. Start from scratch every session.
- **Agent startups (Devin, AutoGPT):** Autonomous but context-free. Generic output.
- **Notion AI / workspace AI:** Trapped in one platform. Can't see across your tools.
- **Custom GPTs:** Slightly better instructions, but no real context accumulation.

---

## YARNNN's Value Proposition

### The Insight
The missing ingredient in AI isn't better models — it's accumulated organizational knowledge. Every company needs competitive intelligence, market awareness, operational synthesis, and strategic reporting. Most can't sustain these practices manually, and a fresh ChatGPT session knows nothing about their business. The gap isn't "who writes the report" — it's "who maintains the institutional knowledge that makes the report valuable."

### The Promise
**A team of domain experts that accumulate your organizational intelligence — and work autonomously.**

YARNNN:
1. **Pre-scaffolds a domain expert roster** — Sign up and you have agents for competitive intelligence, market research, business development, operations, and marketing (ADR-140)
2. **Connects to your platforms** — Slack and Notion today; agents pull data live during task execution (ADR-153)
3. **Accumulates domain knowledge** — Each agent builds structured context in its domain (`/workspace/context/competitors/`, `/workspace/context/market/`, etc.) that persists and deepens (ADR-151)
4. **Executes tasks autonomously** — Assign a task (recurring briefing, goal-driven research, reactive monitoring); agents execute on schedule and deliver (ADR-138, ADR-141)
5. **Gets smarter with tenure** — Feedback distills into preferences, context domains deepen, outputs improve because the underlying knowledge improves (ADR-117, ADR-149)
6. **Becomes irreplaceable** — After 90 days of accumulated domain knowledge, your competitive intelligence agent knows things about your market that can't be replicated by starting over

---

## ICP: The Intelligence-Hungry Professional (Psychographic-First)

**v3.0 reframe:** Previous ICP was defined by occupation (consultants, founders, ops leads) and anchored on deliverable automation. That framing broke under scrutiny — see `ICP_ANALYSIS_APRIL_2026.md`. The reframe defines ICP by psychographic profile first, occupation second. The core question isn't "who has painful recurring deliverables?" but "who needs accumulated domain intelligence but can't justify hiring for it?"

### The Psychographic Profile

**Who they are psychographically:**
- They feel the gap between "what I should know about my business environment" and "what I actually track systematically"
- They've tried to build intelligence practices (competitor tracking, market monitoring, operational synthesis) and failed to sustain them
- They already use AI tools ($20-60/mo) and understand AI is powerful, but are frustrated that every session starts from zero
- They're not looking for a report writer — they want organizational capabilities they don't currently have
- They value accumulated knowledge over one-off outputs. They intuitively get that an agent that's tracked their competitors for 6 months is more valuable than one that just Googled them today

**The behavioral signal:** They've already tried and failed to sustain an intelligence practice. They set up a Notion database for competitor tracking that went stale. They started a "weekly market scan" habit that died. They know they should have a systematic approach to domain intelligence but can't maintain the discipline alone.

**The visceral moment (updated):**
> "I know I should be tracking competitors. I know I should have a market intelligence practice. I know signals are slipping through. But I can't sustain it manually, and I can't hire someone for each domain."

### Primary Segment: The Senior Operator (10-50 person company)

**Titles:** Head of Ops, Chief of Staff, VP Strategy, COO, or founder still wearing these hats
- Personally responsible for organizational awareness across competitive, market, and operational domains
- Company has outgrown the founder doing everything but can't hire domain specialists
- Already paying for tools (Notion, Slack, various dashboards) and spending time stitching together fragmented intelligence
- **Pitch:** "The intelligence team you need but can't hire. Five domain experts — competitive intelligence, market research, business development, operations, marketing — that learn your business and work autonomously."
- **Activation:** First task output that references accumulated context the user didn't explicitly provide
- **Why this works:** Direct match to the pre-scaffolded roster (ADR-140). The product literally gives them what they need — a team of domain specialists.

### Secondary Segment: The AI-Aware Professional (Psychographic Hypothesis A from ACTIVATION_100USERS)

**Who:** Non-technical professionals who've heard about AI agents, understand the promise, but haven't found one that actually works for them without setup, coding, or constant hand-holding
- They're on r/productivity, r/Entrepreneur, r/smallbusiness
- They've tried ChatGPT Plus and maybe a GPT or two, but AI still feels like a tool they operate rather than a team that works for them
- The gap between "AI agents will change everything" (what they hear) and "I have AI agents working for me" (what they experience) feels insurmountable
- **Pitch:** "Everyone's talking about AI agents. Here's your team. No code, no setup. Connect your Slack and Notion, and your agents start learning your world."
- **Activation:** Signing up and seeing a pre-built roster of domain experts ready to work — zero configuration
- **Why this works:** ADR-140 pre-scaffolds agents at signup. The gap this audience feels (desire for agents, no idea how to get one) is bridged by the product existing as a ready-made team.

### Tertiary Segment: The Multi-Client Professional (Legacy Profile A)

**Who:** Solo consultants, fractional execs, freelance strategists managing 3-8 clients
- This was the original primary ICP. Still valid but narrower than originally estimated.
- The deliverable-automation pitch ("your Monday report writes itself") is less compelling than the domain-intelligence pitch ("your competitive intelligence function runs continuously")
- **Pitch:** "Each client gets their own accumulated context. Your agents know client A's priorities, client B's metrics, client C's stakeholders — and produce updates that reflect months of accumulated understanding."
- **Risk:** High-stakes client work = high trust barrier. May need 3-6 months of non-client use before trusting YARNNN with client deliverables.

### Deprioritized Segments

**Ops Lead / Team Coordinator (Previous Profile C):** Absorbed into Primary Segment. The relevant subset is the senior operator at a growing company, not the middle-management coordinator at a larger org.

**Researcher / Analyst (Previous Profile D):** Deferred. Context source mismatch partially resolved (ADR-153 allows live data access during tasks), but competing tools (Perplexity, Elicit) have deepened their moats. Revisit when web research capabilities mature.

---

## Messaging Framework

### What to Say

| Instead of... | Say... |
|---------------|--------|
| "Pre-scaffolded agent roster (ADR-140)" | "Your AI team is ready on day one" |
| "Context domains with accumulated workspace intelligence" | "Gets smarter the longer you use it" |
| "Task execution pipeline (ADR-141)" | "Agents that work autonomously on schedule" |
| "Domain-steward agents with capability registries" | "Domain experts for each area of your business" |
| "Feedback distillation to DELIVERABLE.md preferences" | "Learns from everything you do" |
| "Workspace filesystem with structured context" | "You can see exactly what each agent knows" |
| "TP as orchestrator with primitives" | "Talk to your AI team in plain English" |
| "Tasks as work units (ADR-138)" | "Assign work. They deliver." |

### The Problem → Agitate → Solve

**PAS v3.0 — Organizational intelligence framing:**

> **Problem:** Your company needs competitive intelligence, market awareness, and operational synthesis. But no one has time, and you can't hire for each domain.
>
> **Agitate:** You know you should be tracking competitors systematically. You know market signals are slipping through. You've tried — a Notion database, a weekly scan habit, an ad-hoc ChatGPT session. It never sticks. The knowledge fragments, the habit dies, and you're back to operating on instinct and stale information.
>
> **Solve:** YARNNN gives you a team of domain experts — competitive intelligence, market research, business development, operations, marketing — that connect to your Slack and Notion, accumulate knowledge of your business continuously, and produce work on schedule. Each agent builds lasting domain knowledge. After 90 days, your competitive intelligence agent knows things about your market that a fresh AI session never could. You supervise. The team works.

**PAS alt — Psychographic / desire framing (for broad audience):**

> **Problem:** Everyone's talking about AI agents. You still don't have one working for you.
>
> **Agitate:** You've tried ChatGPT. You've tried custom GPTs. Every session starts from scratch. You're the memory. You're the context. The AI is just the typist. You hear "AI agents will change everything" and think — when? How?
>
> **Solve:** YARNNN gives you an AI team on day one. No code. No configuration. Connect your Slack and Notion, tell it what you need, and your agents start learning your world and producing work. Five domain experts, always improving, always working. This is what AI agents were supposed to be.

---

## Competitive Positioning

### vs Microsoft Copilot Cowork
"Copilot Cowork requires you to hand off a task. YARNNN agents run autonomously — on schedule, proactively, or in response to events — without anyone asking. They're persistent specialists, not session-based assistants."

### vs Claude Cowork
"Claude Cowork is session-based: you start a task, it executes, the session ends. YARNNN agents persist across time. They accumulate memory from every execution, learn from your corrections, and produce better output on their 50th run than their 1st. No session to start. No context to re-establish."

### vs OpenClaw
"OpenClaw runs one always-on agent per workspace. YARNNN runs many sleeping specialists — each with its own workspace, directives, and execution mode. Twenty agents at zero idle cost, each improving at its specific job."

### vs Workspace AI (Notion AI, Glean, Granola)
"Single-platform knowledge, no autonomous output. Notion AI knows your pages but not your Slack. Glean is enterprise search with no agent layer. YARNNN is the only product that accumulates cross-platform knowledge and uses it for autonomous recurring agents."

### The Comparison Table

| | Copilot Cowork | Claude Cowork | OpenClaw | YARNNN |
|---|---|---|---|---|
| Initiation | User hands off task | User starts session | Always-on heartbeat | **Scheduled, proactive, or event-driven** |
| Persistence | Task-scoped | Session-scoped | Single workspace agent | **Many persistent agents** |
| Memory | Work IQ (platform data) | Filesystem access | MEMORY.md per workspace | **Per-agent workspace + global user knowledge** |
| Learning | None | None | Accumulated logs | **Learning loop from user edits** |
| Multi-agent | No | No | One per workspace | **Native: coordinator spawns/directs agents** |
| Idle cost | N/A | N/A | Heartbeat compute | **Zero (sleep-wake architecture)** |

---

## Objection Handling

| Objection | Response |
|-----------|----------|
| "ChatGPT is good enough" | "ChatGPT is powerful but stateless. YARNNN deploys persistent agents that accumulate knowledge from your tools. After 90 days, there's no comparison." |
| "I already use Notion AI / Gemini" | "Those only see what's inside their own platform. YARNNN agents synthesize across Slack and Notion while pulling live data from web sources." |
| "Agent tools already exist" | "Autonomous without accumulated knowledge is just random. YARNNN agents are powered by months of compounded understanding of YOUR work." |
| "How do I know it's getting smarter?" | "Each agent has an inspectable workspace — you can see its memory, observations, and learned preferences. Every run needs fewer edits." |
| "I don't trust AI to work without me" | "You're the supervisor, not the operator. Every agent output is staged for your review before anything ships." |
| "What about data privacy?" | "Your data stays in your workspace with row-level security. Platform connections use OAuth — we never see your passwords." |

---

## Landing Page Headlines

### Hero Options (ranked — v3.0 intelligence team framing)
1. "The intelligence team your company needs — powered by AI that learns your business."
2. "Five domain experts. Always learning. Always working. $19/month."
3. "Everyone's talking about AI agents. Here's your team."
4. "AI that doesn't just answer questions — it builds organizational knowledge."

### Section Headlines
- **The Problem:** "You need competitive intelligence, market research, and operational awareness. You don't have the team for it."
- **The Insight:** "The missing piece isn't a better AI model — it's accumulated domain knowledge."
- **How It Works:** "Sign up → Meet your team → Assign tasks → They learn and deliver"
- **The Moat:** "After 90 days, your agents know things about your business that can't be replicated."
- **The Roster:** "Competitive intelligence. Market research. Business development. Operations. Marketing. Executive synthesis."

### CTAs
- Primary: "Meet your AI team"
- Secondary: "See what they can do"
- Closing: "Your intelligence team after 90 days is incomparably better than day one."

---

## What We're NOT Saying

Avoid technical framing:
- ❌ "Four-layer model with bidirectional learning"
- ❌ "Retention-based knowledge accumulation pipeline"
- ❌ "Capability-based agent execution with primitives"
- ❌ "workspace_files with pgvector semantic search"

Avoid weak positioning:
- ❌ "AI that remembers" (too generic — memory isn't the product, autonomy is)
- ❌ "Context-aware AI work platform" (passive, doesn't convey autonomy)
- ❌ "Recurring output platform" (feature-level, not thesis-level)
- ❌ "Works while you sleep" (feature, not value prop)
- ❌ "Better ChatGPT" (commodity comparison, not differentiation)

Avoid overclaiming:
- ❌ "Fully autonomous AI agent" (user still supervises — that's the model)
- ❌ "Replaces your assistant" (augments workflow, doesn't replace humans)
- ❌ "AGI for work" (overblown, invites skepticism)

---

## Activation Moments

The "aha" moments that convert users:

1. **The roster is already there** — Sign up and see five domain experts ready to work, no configuration needed (ADR-140 pre-scaffolding)
2. **The orchestrator knows your context** — Talk to the TP, and it already understands your business from connected platforms and shared context
3. **First task output from accumulated context** — A competitive brief arrives that references things the agent learned from your Slack over the past week — context you didn't explicitly provide
4. **Domain knowledge deepens visibly** — Browse `/workspace/context/competitors/` and see structured knowledge your agent has been building — entity files, synthesis docs, trend observations
5. **Improvement over time** — The 5th run needs fewer edits because the agent's domain knowledge deepened and your feedback distilled into preferences

---

## Use Case Examples (v3.0 — domain intelligence framing)

### Weekly Competitive Intelligence Briefing
- **Agent:** Competitive Intelligence domain-steward
- **Task mode:** Recurring (weekly)
- **What the agent does:** Monitors competitor activity via connected Slack channels and Notion pages, researches publicly available signals, accumulates findings in `/workspace/context/competitors/{competitor}/` entity folders
- **Output:** Weekly brief synthesizing competitive movements, new entries, positioning shifts
- **Accumulated value:** By month 3, the agent has a rich competitor knowledge base that makes each brief more insightful than the last. It's not just reporting this week's news — it's interpreting it against months of accumulated context

### Monthly Executive Synthesis
- **Agent:** Executive Reporting synthesizer
- **Task mode:** Recurring (monthly)
- **What the agent does:** Reads across all context domains (competitive, market, operations, business development) and synthesizes a cross-domain executive summary
- **Output:** Monthly report that connects dots across domains — "competitor X launched feature Y (competitive) while our Slack activity shows customer complaints about Z (operations) — this is an exposure worth addressing"
- **Accumulated value:** The synthesizer gets better because the domain-stewards it reads from get better. The intelligence compounds across the entire roster

### Goal-Driven Market Research
- **Agent:** Market Research domain-steward
- **Task mode:** Goal (bounded)
- **What the agent does:** Receives a research question ("What's the competitive landscape for AI agent platforms in 2026?"), conducts research across available sources, builds structured findings in `/workspace/context/market/`
- **Output:** Research deliverable addressing the specific question, grounded in both new research and any previously accumulated market context
- **Accumulated value:** Even after the goal-task completes, the market knowledge persists in the workspace. Future tasks can build on it

---

## The Narrative Arc (For Decks & Pitches — v3.0)

1. **The world changed**: AI models got incredibly powerful — but they're all stateless and generic
2. **The real gap**: Every growing company needs competitive intelligence, market research, operational awareness — but can't hire specialists for each domain
3. **AI should fill this**: But current tools (ChatGPT, Copilot, agent startups) forget everything between sessions and produce generic output
4. **YARNNN fills it**: A pre-built team of domain experts that connect to your platforms, accumulate knowledge of your business continuously, and produce work autonomously
5. **The moat**: Accumulated domain knowledge creates real switching costs — your intelligence team after 90 days knows things about your business that can't be replicated by starting over
6. **The trajectory**: Today, humans consume the intelligence. Tomorrow, other AI systems do too. The accumulated organizational knowledge becomes the substrate that powers everything

---

## Usage Notes

This document should be updated when:
- Positioning thesis evolves based on market feedback
- New platform integrations ship (expanding the context surface)
- Competitive landscape changes (especially agent startups)
- User activation data reveals which "aha moments" actually convert

Reference this for all external communication: landing pages, docs, marketing, sales conversations, investor decks.
