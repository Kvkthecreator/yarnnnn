# YARNNN: Coordinated Agent Teams for Recurring Knowledge Work

**Status:** Canonical (investor-facing architecture reference)
**Date:** 2026-03-24 (v2 — Era 3 rewrite)
**Previous:** v1 (2026-03-10, individual-agent model)
**Related:** [FOUNDATIONS.md](FOUNDATIONS.md), [ADR-130](../adr/ADR-130-html-native-output-substrate.md), [ADR-132](../adr/ADR-132-work-first-onboarding.md), [ADR-133](../adr/ADR-133-pm-coordinated-phase-dispatch.md), [ADR-136](../adr/ADR-136-project-charter-architecture.md)

---

## What YARNNN Is

YARNNN is a platform where **coordinated AI agent teams do your recurring knowledge work** — and get smarter the longer they work for you.

You describe your work. The system builds a team of AI specialists — a researcher, an analyst, a writer — coordinated by a PM agent that manages phases, quality, and delivery. Each team member has its own identity, memory, and accumulated expertise. The PM dispatches contributors in sequence, curates handoffs between phases, and assembles the final deliverable. The whole team improves with every cycle: agents learn your preferences, deepen domain expertise, and refine coordination.

**One sentence:** Tell it what you're working on. It builds a team of AI specialists, coordinates them through a PM, and delivers improving work products on your schedule.

---

## How It's Different

|  | Copilot Cowork | Claude Cowork | ChatGPT | YARNNN |
|---|---|---|---|---|
| **Initiation** | User hands off task | User starts session | User prompts | Autonomous — agents pulse, PM coordinates, work delivers on schedule |
| **Persistence** | Task-scoped | Session-scoped | Session-scoped | Persistent agent teams that exist indefinitely |
| **Memory** | Work IQ / Microsoft Graph | Local filesystem | Conversation history | Per-agent workspace: memory, preferences, self-assessments, domain thesis — compounding across executions |
| **Learning** | None | None | None | Feedback loop: user edits → distilled preferences → better next output |
| **Coordination** | Single task | Single session | Single conversation | PM-coordinated teams: phased execution, cross-agent handoffs, quality-gated assembly |
| **Cross-platform** | Microsoft only | Local machine only | None | Slack + Notion — synthesized into work-scoped projects |
| **Output** | Text response | Text/files | Text response | Composed HTML deliverables with charts, diagrams — exportable to PDF/PPTX/XLSX |
| **Idle cost** | N/A | N/A | N/A | Zero — agents sleep between pulses |

**The key insight:** Session-based AI starts from scratch every time. YARNNN agent teams compound. The 50th delivery of a weekly intelligence briefing is incomparably better than the 1st — because every team member has 50 cycles of accumulated memory, learned preferences, refined coordination, and deepened domain expertise.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                       USER LAYER                                  │
│                                                                   │
│  Onboarding               Orchestrator (TP)     Project Meeting   │
│  ┌────────────────┐       ┌──────────────┐      Room              │
│  │ "Describe your │       │ Meta-cognitive│      ┌──────────────┐ │
│  │  work" → scoped│       │ layer: creates│      │ Chat with     │ │
│  │  projects       │       │ agents,       │      │ agents,       │ │
│  │                 │       │ monitors,     │      │ @-mention,    │ │
│  │                 │       │ supervises    │      │ steer work    │ │
│  └────────────────┘       └──────────────┘      └──────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     PROJECT LAYER                                  │
│                                                                    │
│  Project: "Client X Weekly Brief"                                  │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │ Charter: PROJECT.md + TEAM.md + PROCESS.md                │     │
│  │                                                           │     │
│  │  PM Agent (coordinator)                                   │     │
│  │  ┌─────────────────────────────────────────────────┐     │     │
│  │  │ Pulse every 2h · Dispatches phases · Quality    │     │     │
│  │  │ gates · Assembles deliverable · Manages budget  │     │     │
│  │  └─────────────────────────────────────────────────┘     │     │
│  │                                                           │     │
│  │  Contributors:                                            │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │     │
│  │  │ Briefer  │  │ Analyst  │  │ Scout    │               │     │
│  │  │ (Slack   │  │ (cross-  │  │ (web     │               │     │
│  │  │  recap)  │  │  ref +   │  │  research)│               │     │
│  │  │          │  │  charts) │  │          │               │     │
│  │  └──────────┘  └──────────┘  └──────────┘               │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                    │
│  Each project carries: objective, team roster, output spec,        │
│  delivery cadence, work budget, PM coordination state              │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                  EXECUTION PIPELINE                                │
│                                                                    │
│  Pulse → Decide → Dispatch → Generate → Compose → Deliver        │
│                                                                    │
│  • PM pulses on cadence, dispatches contributors in phases        │
│  • Contributors generate structured markdown + asset references   │
│  • Compose engine renders HTML with layout modes                  │
│  • Export pipeline: HTML → PDF / XLSX on demand                   │
│  • Feedback: user edits → preferences → next cycle improvement    │
│  • Work budget: Free 60 / Pro 1000 units per month                │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                PERCEPTION + KNOWLEDGE LAYER                        │
│                                                                    │
│  Perception Pipeline          Workspace Filesystem                 │
│  ┌────────────────────┐      ┌──────────────────────────┐        │
│  │ Slack sync          │ ──▶ │ /knowledge/slack/          │        │
│  │ Notion sync         │     │ /knowledge/notion/         │        │
│  │                     │     │ /agents/{slug}/AGENT.md    │        │
│  │ (paginated,         │     │ /agents/{slug}/memory/     │        │
│  │  incremental,       │     │ /agents/{slug}/outputs/    │        │
│  │  tier-gated)        │     │ /projects/{slug}/          │        │
│  └────────────────────┘     │   PROJECT.md + TEAM.md     │        │
│                              │   PROCESS.md + memory/     │        │
│                              │ /user_shared/ (staging)    │        │
│                              └──────────────────────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Agent Types: The Team You Hire

Every agent is one of eight specialist types. Type determines capabilities — fixed at creation, deterministic. Persona comes from instructions, which are user-configurable.

| Type | What It Does | Capabilities |
|---|---|---|
| **Briefer** | Summarizes platform activity into concise digests | Read platforms, summarize, produce markdown, compose HTML |
| **Monitor** | Watches for changes and alerts on significant events | Read platforms, detect change, alert, produce markdown |
| **Researcher** | Investigates topics across platforms and the web | Read platforms, web search, investigate, chart, diagram |
| **Analyst** | Cross-references data, finds patterns, produces charts | Read platforms, data analysis, cross-reference, chart |
| **Drafter** | Produces structured content with visual elements | Read platforms, produce markdown, chart, diagram |
| **Writer** | Crafts narrative content | Read platforms, produce markdown |
| **Planner** | Creates plans and roadmaps | Read platforms, produce markdown |
| **Scout** | Scans external sources for intelligence | Read platforms, web search, chart |
| **PM** | Coordinates project execution (infrastructure, not user-facing type) | Read workspace, check freshness, steer contributors, trigger assembly, manage work plan |

Legacy roles (digest, synthesize, research, prepare, custom) are mapped via `LEGACY_ROLE_MAP` — no migration needed.

---

## Project Coordination: How Teams Work

Projects are the unit of delivery. Every project has a charter (three files), a PM, and one or more contributors.

### The Charter (ADR-136)

```
/projects/{slug}/
├── PROJECT.md      ← WHAT: objective, success criteria, audience
├── TEAM.md         ← WHO: contributors, types, capabilities, sources
├── PROCESS.md      ← HOW: output spec, cadence, delivery, phases
└── memory/         ← Working state (PM decisions, assessments, phase tracking)
```

Charter files are the constitution — written by user/TP/Composer, read by agents. Memory files are working state — accumulated by agents during execution. Strict separation.

### PM-Coordinated Phase Dispatch (ADR-133)

Contributors don't pulse independently. The PM owns the heartbeat and dispatches work in structured phases:

```
PM pulses on cadence (every 2h)
  → Reads structured work plan (phases, dependencies)
  → Checks: what phase are we in? What's blocking?
  → Dispatches contributor(s) for current phase with context
  → Contributors execute within injected phase context
  → PM reads contributor self-assessments on next pulse
  → PM advances phase, re-steers, or triggers assembly
```

Cross-phase context injection: PM curates prior phase outputs into briefs for the next phase. The researcher's findings become the analyst's input. The analyst's charts become the writer's evidence.

### Three Execution Modes

| Mode | Pulse Owner | Example |
|---|---|---|
| **Standalone agent** (no project) | Agent itself | A lone briefer running daily recaps |
| **Project contributor** (in project) | Project PM | A researcher assigned to Phase 1 |
| **PM agent** | PM itself | The coordinator, pulsing every 2h |

---

## The Agent Pulse: Autonomous Awareness (ADR-126)

Every agent has a pulse — an autonomous sense→decide cycle. The pulse is upstream of execution: a pulse that decides "generate" produces a run; one that decides "observe" or "wait" does not — but the pulse still happened, and that's visible intelligence.

### Three-Tier Funnel (cheap-first)

1. **Tier 1 (deterministic, zero LLM cost):** Fresh content? Budget available? Cadence met? ~80% of pulses resolve here.
2. **Tier 2 (Haiku self-assessment):** Agent reads own workspace, thesis, observations. Decides whether to generate. ~$0.001/pulse.
3. **Tier 3 (PM coordination):** PM reads contributor freshness, quality assessments, work plan. Dispatches phases. ~$0.01/pulse.

Decision taxonomy: `generate | observe | wait | escalate`. Each decision is a visible event — surfaced in project meeting rooms and dashboards. This is what makes agents a workforce you can watch, not a list of cron outputs.

---

## The Agent Intelligence Model

Every agent carries layered knowledge in its workspace filesystem:

```
/agents/{slug}/
├── AGENT.md                ← Identity: type, instructions, persona
├── thesis.md               ← Domain thesis: accumulated understanding
├── memory/
│   ├── preferences.md      ← Learned from user edits (feedback distillation)
│   ├── observations.md     ← Self-authored after each run
│   ├── self_assessment.md  ← Rolling 5-entry mandate/domain/confidence eval
│   └── directives.md       ← Accumulated user guidance from chat
└── outputs/{date}/
    ├── manifest.json       ← Output metadata, delivery status
    └── output.md           ← Generated content
```

This is how an agent on its 50th run produces better output than its 1st: it has 50 cycles of accumulated observations, distilled preferences, and refined self-assessments.

---

## Output Substrate: HTML-Native (ADR-130)

Three concerns, cleanly separated:

1. **Agents produce content** — structured markdown + asset references (SVG charts, Mermaid diagrams, PNG images)
2. **The platform composes** — markdown + assets → styled HTML with layout modes via the compose engine
3. **Export is derivative** — HTML → PDF, data → XLSX are mechanical, on-demand conversions

The agent never thinks about file formats. The compose engine handles presentation. Skills follow Claude Code's SKILL.md convention — each skill is a folder with instructions and scripts, expandable without framework changes. Eight skills live today: PDF, PPTX, XLSX, chart, mermaid, HTML, data export, image.

---

## Work-First Onboarding (ADR-132)

The entry point is **"describe your work"**, not "connect a platform."

```
Sign up → "How is your work structured?" → Define work scopes
  → Each scope becomes a project (scaffold_project())
  → Each project gets a PM + typed contributors
  → Connect platforms → sources mapped to work-scoped projects
  → Agents activate, scoped to your work, not platform topology
```

A solo founder who says "I have 3 clients and a product launch" gets 4 projects with correctly-scoped agent teams — not a generic Slack recap of everything. Platform connections enrich existing work-scoped projects rather than creating new generic digests.

---

## The Orchestrator (TP)

The Orchestrator is the singular meta-cognitive layer. It does not own a domain — it owns the system's attention allocation:

- **Conversational**: mediates between user and system
- **Compositional**: assesses the user's work substrate and scaffolds projects + agents (Composer capability)
- **Supervisory**: monitors project and agent health via PM status reports
- **Orchestrative**: adjusts, evolves, and dissolves agents based on changing needs

The Orchestrator creates PMs. PMs coordinate contributors. Contributors produce work. This is two layers — meta-cognitive (TP) and domain-cognitive (agents) — not three.

---

## Knowledge Accumulation

### The Perception Pipeline

YARNNN connects to two work platforms via OAuth:

| Platform | What's Synced | Retention |
|---|---|---|
| **Slack** | Channel messages, threads (expanded when substantive) | 14 days |
| **Notion** | Page content, tracked by last edit time | 90 days |

Sync is paginated, incremental (cursor-based), and tier-gated. Free tier: daily sync. Pro tier: hourly sync.

### The Recursive Property

```
External platforms → platform_content → agent execution → agent output →
  workspace (knowledge + memory) → next agent execution → ...
                              ↑                           |
                              └── user feedback ──────────┘
                              └── PM assessment ──────────┘
                              └── cross-agent reading ────┘
```

The workspace filesystem is the shared OS for agents and humans. Agent outputs feed back as knowledge. User feedback distills into preferences. PM assessments steer contributors. Cross-agent reading enables composition. This recursive loop is the compounding mechanism — and the reason a competitor starting from zero cannot replicate a tenured YARNNN instance.

---

## Infrastructure

Five services on Render (Singapore region):

| Service | Role |
|---|---|
| **API** (Web Service) | FastAPI — chat, agent CRUD, auth, project management, all user-facing endpoints |
| **Unified Scheduler** (Cron, every 5 min) | Triggers agent pulses, PM coordination, Composer heartbeat, memory extraction, workspace cleanup |
| **Platform Sync** (Cron, every 5 min) | Platform sync for all connected users (tier-gated frequency) |
| **MCP Server** (Web Service) | Exposes YARNNN agents to Claude.ai and Claude Desktop via MCP protocol (9 tools) |
| **Output Gateway** (Web Service, Docker) | Render service with skill library: compose engine, PDF/PPTX/XLSX export, chart/mermaid/image rendering |

No Redis, no queue, no background worker. All execution is inline. Agents sleep between pulse ticks at zero compute cost.

**LLM stack:**
- Agent generation + Orchestrator chat: Claude Sonnet 4 (Anthropic)
- Agent pulse self-assessment: Claude Haiku 4.5 (cost-efficient)
- Memory extraction: Claude Sonnet 4
- Onboarding inference: Claude Sonnet 4 (one-shot work scope extraction)

**Cost model:** ~$0.50/month per project at steady state. Tier 1 pulse resolves ~80% of decisions at zero LLM cost. Deterministic execution via charter-driven cadence enforcement.

---

## Monetization

| | Free | Pro ($19/mo) |
|---|---|---|
| Projects | 2 | 10 |
| Agents (excluding PMs) | 3 | 25 |
| Work units | 60/month | 1,000/month |
| Messages (Orchestrator) | 50/month | Unlimited |
| Platform sources | 5 Slack / 10 Notion | Unlimited |
| Sync frequency | Daily | Hourly |

Work units = agent runs + assemblies + renders. The system self-governs within budget. PM agents are infrastructure — excluded from agent limits.

---

## What's Built and Working

- Two-platform OAuth + landscape discovery + smart source auto-selection (Slack, Notion)
- Tier-gated perception pipeline (paginated, incremental)
- Workspace filesystem with folder conventions, versioning, lifecycle management
- Orchestrator agent (TP) — streaming, full capabilities, context-aware
- Project type registry + scaffold_project() — deterministic project creation
- PM agents with phase dispatch, quality assessment, contribution steering
- Three-tier agent pulse (deterministic → self-assessment → PM coordination)
- Agent types: 8 user-facing types + PM infrastructure (three-registry architecture)
- HTML compose engine + output gateway with 8-skill library
- Work budget governor (Free 60 / Pro 1000 units/month)
- Project meeting rooms with @-mention agent chat
- Three charter files (PROJECT.md, TEAM.md, PROCESS.md)
- Multi-agent coherence protocol (self-assessments, PM assessments, directive persistence)
- Feedback distillation (user edits → learned preferences)
- Agent self-reflection (post-run observations)
- Work-first onboarding (describe work → scaffold projects)
- Email delivery via Resend
- MCP server (OAuth 2.1 for Claude.ai, bearer token for Claude Desktop, 9 tools)
- Nightly memory extraction from Orchestrator conversations
- 2-tier monetization with Lemon Squeezy
- 136 Architecture Decision Records

---

## The Thesis

The AI landscape is converging on agents. Microsoft, Anthropic, and OpenAI are building session-based agents that execute tasks on demand. Startups are building single-agent automation tools.

YARNNN's bet: **the most valuable knowledge work is recurring, team-based, and improves with accumulated intelligence.** A weekly competitive brief, a client status report, a market analysis — these are not one-shot prompts. They are ongoing work that benefits from persistent teams with deepening expertise.

A session-based agent that writes your quarterly review starts from scratch every time. A YARNNN project with a researcher, analyst, and writer — coordinated by a PM that has managed 12 previous cycles — knows which data matters, which format your stakeholder prefers, which findings warrant escalation, and which sections you always edit out.

**That accumulated team intelligence is the product.** The coordinated agent team is how it's delivered.

---

*For the value realization chain, see [VALUE-CHAIN.md](VALUE-CHAIN.md). For first principles, see [FOUNDATIONS.md](FOUNDATIONS.md). For the three-registry architecture, see [output-substrate.md](output-substrate.md).*
