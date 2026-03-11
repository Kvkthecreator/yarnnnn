# YARNNN GTM Positioning & Messaging

**Last Updated:** 2026-03-11 (v2.0 — ADR-103 agent-native vocabulary, updated competitive positioning, 2-tier model)

**Reference:** See [ESSENCE.md](../../ESSENCE.md) for core thesis and architecture. See [ADR-103](../../adr/ADR-103-agentic-framework-reframe.md) for vocabulary conventions.

---

## Core Positioning

**One-liner:** AI that works autonomously — and gets smarter the longer you use it

**Tagline:** It connects to your tools. It learns your world. It works while you don't.

**Elevator pitch:**
YARNNN deploys persistent AI agents that connect to the tools you already use — Slack, Gmail, Notion, Calendar — and accumulate knowledge of your work world over time. Then they work autonomously: producing reports, surfacing insights, and operating as an orchestrator that already knows your context. The longer you use it, the smarter each agent gets. Your agents after 90 days are incomparably better than on day one.

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
The missing ingredient in AI autonomy isn't better models — it's accumulated knowledge. An AI that knows your clients, your projects, your communication style, and your platform activity can do meaningful work independently. One that doesn't is just a fancy autocomplete.

### The Promise
**Persistent agents that actually work for you — not just with you.**

YARNNN:
1. **Connects to your tools** — Perception pipeline syncs Slack, Gmail, Notion, Calendar continuously
2. **Accumulates knowledge** — Every sync cycle deepens what each agent knows about your work world
3. **Works autonomously** — Agents produce output on schedule without prompting
4. **Gets smarter over time** — Your edits, your feedback, your patterns train each agent via its learning loop
5. **Becomes irreplaceable** — After 90 days of accumulated knowledge, switching costs are real

---

## ICP: Solo Professionals with Recurring Work Obligations

Primary targets who need AI that works autonomously across their tools:

### Consultants (Primary)
- **Use case:** Weekly client status reports, project updates
- **Pain:** Re-explaining context to AI every time, manual Slack/email aggregation
- **Pitch:** "An AI that reads your Slack, knows your clients, and writes the update for you."
- **Activation:** First agent produced autonomously from synced context

### Founders
- **Use case:** Monthly investor updates, board prep
- **Pain:** Dreading the monthly synthesis across scattered tools
- **Pitch:** "Your investor update writes itself from your actual work activity."
- **Activation:** Draft pulls real data from connected platforms

### Operations/Team Leads
- **Use case:** Team standups, progress reports, meeting briefs
- **Pain:** Manual aggregation across Slack, docs, calendar every day
- **Pitch:** "Your morning brief is ready before you are — pulled from last night's Slack and today's calendar."
- **Activation:** Cross-platform synthesis without prompting

### Researchers/Analysts
- **Use case:** Research digests, competitive intelligence briefs
- **Pain:** Monitoring multiple sources, synthesizing manually
- **Pitch:** "Briefs that get smarter because they accumulate what matters to you."
- **Activation:** Proactive agents triggered automatically when conditions warrant

---

## Messaging Framework

### What to Say

| Instead of... | Say... |
|---------------|--------|
| "Perception pipeline and knowledge base" | "Connects to your tools" |
| "Accumulated knowledge with retention" | "Gets smarter the longer you use it" |
| "Headless scheduled agent execution" | "Agents that work autonomously" |
| "Capability-based tool use" | "AI that can actually do things" |
| "Four-layer intelligence model with learning loop" | "Learns from everything you do" |
| "Knowledge accumulation as agent intelligence" | "Agents that work for you, not just with you" |
| "Edit distance metrics" | "Quality that improves over time" |
| "Agent workspace with inspectable memory" | "You can see exactly what each agent knows" |

### The Problem → Agitate → Solve

**For landing page / marketing:**

> **Problem:** Every AI tool you use forgets everything between sessions.
>
> **Agitate:** You open ChatGPT. You explain your clients again. You describe your project again. You specify the format again. You make the same corrections. Tomorrow? Same thing. You're the memory. You're the context. The AI is just the typist.
>
> **Solve:** YARNNN connects to your Slack, Gmail, Notion, and Calendar. It deploys persistent agents that accumulate knowledge of your work world continuously. Each agent produces output autonomously — and each run is better than the last because the agent's knowledge compounds. You supervise. The agents work.

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
| "I already use Notion AI / Gemini" | "Those only see what's inside their own platform. YARNNN agents synthesize across Slack, Gmail, Notion, and Calendar." |
| "Agent tools already exist" | "Autonomous without accumulated knowledge is just random. YARNNN agents are powered by months of compounded understanding of YOUR work." |
| "How do I know it's getting smarter?" | "Each agent has an inspectable workspace — you can see its memory, observations, and learned preferences. Every run needs fewer edits." |
| "I don't trust AI to work without me" | "You're the supervisor, not the operator. Every agent output is staged for your review before anything ships." |
| "What about data privacy?" | "Your data stays in your workspace with row-level security. Platform connections use OAuth — we never see your passwords." |

---

## Landing Page Headlines

### Hero Options (ranked)
1. "AI that works for you — and gets smarter every day."
2. "Connect your tools. Let AI do the work."
3. "The AI that knows your world and works while you don't."
4. "Autonomous AI, powered by your actual context."

### Section Headlines
- **The Problem:** "Every AI tool forgets everything between sessions."
- **The Insight:** "Autonomy without context is useless. Context without autonomy is just a database."
- **How It Works:** "Connect → Accumulate → Automate → Supervise"
- **The Moat:** "After 90 days, your AI knows things no other tool can replicate."
- **Use Cases:** "What YARNNN agents produce autonomously"

### CTAs
- Primary: "Connect your first tool"
- Secondary: "See it work"
- Closing: "Your AI after 90 days is incomparably better than day one."

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

1. **The orchestrator knows your context** — Ask about a project and it already knows the details from synced Slack/Gmail
2. **First autonomous agent output** — A report arrives without prompting, populated with real data from connected platforms
3. **Cross-platform synthesis** — An agent combines Slack messages, calendar context, and Notion docs into one coherent output
4. **Improvement over time** — The 5th run needs fewer edits than the 1st because accumulated knowledge made the agent smarter
5. **Proactive agent output** — An agent detects conditions warrant attention and produces output you didn't ask for

---

## Use Case Examples

### Weekly Client Status Report
- **Recipient:** Sarah Chen, VP Marketing at Acme Corp
- **Schedule:** Every Monday at 8am
- **Context sources:** Slack #client-acme channel, Gmail threads with Sarah, Notion project page
- **Autonomy:** YARNNN agent synthesizes last week's activity across platforms, produces draft, stages for review
- **Improvement:** By week 5, draft needs minimal edits because the agent knows which metrics Sarah cares about

### Monthly Investor Update
- **Recipient:** Board of Directors
- **Schedule:** First of every month
- **Context sources:** Gmail board threads, Slack #leadership, Calendar board prep meetings, Notion KPIs page
- **Autonomy:** YARNNN agent pulls real metrics, formats to learned structure, highlights what matters
- **Improvement:** Each month, less correction needed on emphasis and narrative framing

### Proactive Competitive Brief
- **Recipient:** Founder (you)
- **Trigger:** Proactive agent's periodic self-review detects conditions warrant a brief
- **Context sources:** Cross-platform knowledge base, accumulated competitive intelligence
- **Autonomy:** Agent generates when it judges conditions warrant — observe → sleep → generate cycle, not on every event

---

## The Narrative Arc (For Decks & Pitches)

1. **The world changed**: AI models got incredibly powerful — but they're all stateless
2. **Users showed us the demand**: ClawdBot/OpenClaw proved millions want AI that persists and knows them
3. **The gap**: No one combines persistent knowledge accumulation WITH autonomous agent output
4. **YARNNN fills it**: Connect your tools → accumulate knowledge → persistent agents that improve with tenure
5. **The moat**: Accumulated knowledge creates real switching costs — your agents after 90 days can't be replicated

---

## Usage Notes

This document should be updated when:
- Positioning thesis evolves based on market feedback
- New platform integrations ship (expanding the context surface)
- Competitive landscape changes (especially agent startups)
- User activation data reveals which "aha moments" actually convert

Reference this for all external communication: landing pages, docs, marketing, sales conversations, investor decks.
