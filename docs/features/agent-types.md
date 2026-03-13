# Agent Skills — Feature Reference

**Status:** Living document
**Date:** 2026-03-12
**Related:** [Agent Framework: Scope × Skill × Trigger](../architecture/agent-framework.md), [ADR-109: Agent Framework Migration](../adr/ADR-109-agent-framework.md) (pending), [Quality Testing Framework](../development/agent-quality-testing.md)

Each agent is defined by two orthogonal axes: **Scope** (what it knows) and **Skill** (what it does). This document captures validated output formats, execution details, and design decisions per skill. Skills are added here as they go through quality validation (see testing framework).

**Targeting (ADR-104):** All user intent for "what this agent should focus on" flows through `agent_instructions`. Instructions are dual-injected: into the headless system prompt (behavioral constraints) and into the skill prompt user message (priority lens for the gathered context). There are no per-source filters or structured scope fields — instructions are the unified targeting layer. ADR-105 migrates instruction editing to the chat surface (directives via chat, configuration in drawer).

---

## How Users Create Agents

Users don't think in terms of Scope × Skill — they pick a **template** that maps to a pre-configured combination:

| Template Label | Skill | Default Scope | Default Trigger | Description |
|---------------|-------|---------------|----------------|-------------|
| **Slack Recap** | digest | platform | recurring | Channel activity summary |
| **Gmail Digest** | digest | platform | recurring | Email digest by label |
| **Notion Summary** | digest | platform | recurring | Page and database activity summary |
| **Meeting Prep** | prepare | cross_platform | recurring | Calendar-driven briefing |
| **Work Summary** | synthesize | cross_platform | recurring | Cross-platform status update |
| **Channel Watch** | monitor | platform | proactive | Track changes in specific channels |
| **Domain Tracker** | monitor | knowledge | proactive | Longitudinal domain monitoring |
| **Deep Dive** | research | research | goal | Bounded investigation |
| **Proactive Insights** | synthesize | autonomous | proactive | Self-directed intelligence |
| **Coordinator** | orchestrate | autonomous | coordinator | Agent fleet management |
| **Custom** | (user selects) | (inferred) | (user selects) | Full manual configuration |

Scope is **auto-inferred** from the user's configured sources — never set directly. See [Agent Framework](../architecture/agent-framework.md#scope-is-auto-inferred-never-user-configured) for inference rules.

### Creation paths

| Path | Who initiates | Templates covered | Status |
|------|--------------|-------------------|--------|
| **Chat (TP)** | User via conversation | All templates | Active — TP uses Write primitive (planned: CreateAgent, ADR-111) |
| **UI form** | User via `/agents/new` | All templates | Active |
| **Bootstrap** | System, post-connection | Platform digests only (Slack Recap, Gmail Digest, Notion Summary) | Planned (ADR-110) |
| **Composer** | System, substrate-assessed | Full taxonomy (cross-platform, knowledge, research) | Planned (ADR-111) |
| **Coordinator** | Coordinator agent | Any (via CreateAgent primitive) | Active (ADR-092) |

See [ADR-110](../adr/ADR-110-onboarding-bootstrap.md) and [ADR-111](../adr/ADR-111-agent-composer.md) for planned creation paths.

### Sequencing model

```
Acquisition wedge:     Work Summary (cross-platform synthesis)
Trust builder:         Meeting Prep (daily calendar-driven prep)
Retention foundation:  Recap (daily/weekly platform catchup)
Deepening hooks:       Proactive Insights, Domain Tracker, Coordinator
```

---

## Skill: Digest

**Verb:** Compress, summarize
**Output:** Document (recap, summary)
**Character:** Lossy reduction, recency-weighted

### What it does

Catches the user up on activity within their configured sources. Platform-wide — covers all synced sources (channels, labels, pages), not just one.

### Output format: highlights + by-source breakdown

**Highlights** — top 3-5 things that happened across the configured sources. Decisions, problems surfaced, progress on key work.

**By Source** — subsection per source with `###` headers:
- Slack: by channel (`### #engineering`, `### #daily-work`)
- Gmail: by category or sender (`### Infrastructure Alerts`)
- Notion: by page or database (`### Architecture Docs`)
- Calendar: by timeframe (`### This Week`)

**Design rule:** Every source with data gets a subsection. Low activity noted briefly.

### Scope behavior

| Scope | Template | Behavior |
|-------|----------|----------|
| **platform** | Slack Recap, Gmail Digest, Notion Summary | Single-platform synthesis. One recap per platform per user (enforced at creation). Title set dynamically: "Slack Recap", "Gmail Recap", "Notion Summary". |
| **cross_platform** | — | Multi-platform synthesis. All connected sources summarized. |

### Validated output details

**Validated:** 2026-03-06 (Pass 2)
**Prompt version:** v2 — tracked in `api/prompts/CHANGELOG.md`

### Execution details

- **Strategy:** PlatformBoundStrategy (platform scope) / CrossPlatformStrategy (cross_platform)
- **Default trigger:** `recurring`
- **Headless agent:** 3 tool rounds max
- **Delivery:** Email via Resend (ADR-066)

---

## Skill: Prepare

**Verb:** Anticipate, assemble
**Output:** Document (brief, prep)
**Character:** Event-driven, anticipatory, time-sensitive

### What it does

Reads the user's Google Calendar and assembles a prep briefing — with context pulled from Slack, Gmail, and Notion for each meeting. Delivers intelligence the user needs before key events.

### Key features

- **Daily batch:** runs once per morning, covers today + tomorrow morning (no gap between deliveries)
- **Meeting classification:** adapts prep depth per meeting type (recurring internal, external/new, large group, low-stakes)
- **Cross-platform context:** surfaces attendee mentions from Slack, recent email threads, Notion docs
- **Requires Google Calendar** — explicit dependency

### Scope behavior

| Scope | Template | Behavior |
|-------|----------|----------|
| **platform** | — | Single-platform prep (calendar only). Uncommon. |
| **cross_platform** | Meeting Prep | Full cross-platform context per meeting. Natural fit. |

### Constraints

- One per user (at Meeting Prep template level)
- Daily frequency only
- Google Calendar must be connected

### Validated output details

**Validated:** 2026-03-06 (Pass 3)
**Prompt version:** v3 — tracked in `api/prompts/CHANGELOG.md`
**Full details:** [docs/features/meeting-prep.md](meeting-prep.md)

### Execution details

- **Strategy:** CrossPlatformStrategy
- **Default trigger:** `recurring` (daily)
- **Sources:** Calendar + all connected platforms
- **Delivery:** Email via Resend (ADR-066)

---

## Skill: Monitor

**Verb:** Track, diff, alert
**Output:** Document or notification
**Character:** Differential against baseline/thesis, stateful

### What it does

Maintains awareness of a domain over time and surfaces changes when they cross a significance threshold. Stateful — each execution builds on accumulated observations, not a fresh scan.

### Scope behavior

| Scope | Template | Behavior |
|-------|----------|----------|
| **platform** | Channel Watch | Watches specific platform sources. Threshold-based generation. |
| **cross_platform** | — | Watches multiple platforms for cross-cutting patterns. |
| **knowledge** | Domain Tracker | Monitors accumulated `/knowledge/` filesystem. Longitudinal tracking against a thesis. |
| **research** | — | Market watch. Platform signals + web research for external context. |

### Memory role

- Maintains `observations` — agent-authored notes from each review cycle
- Builds a `thesis` document — the agent's evolving understanding of what's normal vs. significant
- Review log captures patterns over time

### Execution details

- **Strategy:** varies by scope (PlatformBound / Knowledge / Research)
- **Default trigger:** `proactive` or `reactive`
- **Headless agent:** 3–6 tool rounds (scope-dependent)
- **Workspace primitives:** ReadWorkspace, WriteWorkspace (stateful tracking)
- **Delivery:** Email via Resend (ADR-066)

---

## Skill: Research

**Verb:** Investigate, analyze
**Output:** Document (report, analysis)
**Character:** Exploratory, goal-bounded, depth-first

### What it does

Bounded investigation into a specific topic. Combines internal knowledge with external web research. Runs until the research objective is complete, then stops.

### Scope behavior

| Scope | Template | Behavior |
|-------|----------|----------|
| **knowledge** | — | Deep analysis of accumulated internal knowledge. No web. |
| **research** | Deep Dive | Internal knowledge + web search. Natural fit for most investigations. |
| **autonomous** | — | Self-directed research. Agent selects own context strategy. Advanced. |

### Lifecycle (progressive autonomy)

1. **Creation:** User defines research objective via instructions.
2. **First run:** Broad investigation — internal knowledge scan + web research on strongest leads.
3. **User refinement:** Review output, chat with TP about focus areas → instructions and workspace updated.
4. **Completion:** Agent assesses goal completion after each run. When objective is met, agent pauses itself (goal trigger).

### Execution details

- **Strategy:** ResearchStrategy (research scope) / KnowledgeStrategy (knowledge scope)
- **Default trigger:** `goal`
- **Headless agent:** 6 tool rounds (extended for depth)
- **Primitives:** WebSearch, QueryKnowledge, ReadWorkspace, WriteWorkspace, SearchWorkspace
- **Delivery:** Email via Resend (ADR-066)

---

## Skill: Synthesize

**Verb:** Connect, derive insight
**Output:** Document (insight, thesis, status update)
**Character:** Cross-source, pattern recognition, longitudinal

### What it does

Synthesizes activity across multiple sources into a structured document — connecting patterns, identifying cross-platform cause-and-effect chains, and producing intelligence the user didn't know to ask for.

### Output format: two-part structure

**Part 1 — Cross-Source Synthesis** (intelligence layer):
- TL;DR executive summary
- Key accomplishments (drawn from all sources)
- Blockers and risks
- Next steps with owners
- Cross-platform connections — cause-and-effect chains across sources

**Part 2 — Source Activity** (evidence layer):
- Separate `## Section` per connected platform
- Slack: grouped by channel
- Gmail: notable emails, action items
- Notion: document updates, changes
- Calendar: upcoming events (when present)

**Design rule:** Every platform with data gets a section. No update is still news — low activity is reported briefly to confirm nothing was missed.

### Scope behavior

| Scope | Template | Behavior |
|-------|----------|----------|
| **cross_platform** | Work Summary | Multi-platform activity synthesis. Audience-targeted. |
| **knowledge** | — | Synthesizes accumulated `/knowledge/` entries. Longitudinal insight. |
| **autonomous** | Proactive Insights | Self-directed. Agent selects own signals, combines internal + external intelligence. |

### Proactive Insights variant (autonomous × synthesize)

The most advanced synthesize configuration. The agent autonomously spots emerging themes across connected platforms and investigates them externally.

**Why this is different from ChatGPT/Perplexity:** No external research tool can see what's happening inside the user's organization. Proactive Insights combines internal signal detection with external web research — grounded in what the user's team is actually working on.

**Output format: signals + watching**

- **This Week's Signals** — 2-4 emerging themes with internal signal, external context (WebSearch with URLs), and "why this matters"
- **What I'm Watching** — 1-2 patterns not yet strong enough to report. Shows progressive learning.

**Execution:**
- Two-phase: Haiku review → conditional Sonnet generation
- Review pass: scans platform_content for emerging themes, uses WebSearch for external relevance
- Generation: Full Sonnet with 6 tool rounds (WebSearch + Search)

### Validated output details (Work Summary)

**Validated:** 2026-03-06 (Pass 1)
**Prompt version:** v4 — tracked in `api/prompts/CHANGELOG.md`

### Validated output details (Proactive Insights)

**Validated:** 2026-03-06 (Pass 4)
**Prompt version:** v2 — tracked in `api/prompts/CHANGELOG.md`

### Execution details

- **Strategy:** CrossPlatformStrategy (cross_platform) / KnowledgeStrategy (knowledge) / AutonomousStrategy (autonomous)
- **Default trigger:** `recurring` (Work Summary) / `proactive` (Proactive Insights)
- **Headless agent:** 3 tool rounds (cross_platform) / 6 tool rounds (autonomous)
- **Delivery:** Email via Resend (ADR-066)

---

## Skill: Orchestrate

**Verb:** Coordinate, dispatch
**Output:** Agent actions (create/trigger agents)
**Character:** Meta-level, reads agent outputs, manages fleet

### What it does

A coordinator agent watches a domain and dispatches work. When conditions warrant, it creates new agents or advances existing agents' schedules. It reads accumulated knowledge and agent outputs — not raw platform data.

### Scope behavior

| Scope | Template | Behavior |
|-------|----------|----------|
| **autonomous** | Coordinator | Full primitive set. Reads agent fleet, creates/triggers as needed. |

### Memory role

- `review_log` — self-authored domain assessments from each review cycle
- `created_agents` — deduplication log preventing duplicate agents for the same event

### Execution details

- **Strategy:** AutonomousStrategy
- **Trigger:** `coordinator` (periodic review + create/trigger primitives)
- **Primitives:** CreateAgent, AdvanceAgentSchedule, ReadWorkspace, WriteWorkspace, QueryKnowledge
- **Delivery:** Agent actions (no document output)

---

## Skill: Act (future)

**Verb:** Execute, respond, post
**Output:** Platform action (reply, send, update, post)
**Character:** Agentic, requires permissions, approval-gated

### What it will do

Execute actions on connected platforms — reply to Slack threads, send emails, update Notion pages. Gated by `ActionPolicy` (per-agent permission model).

### Why it's not yet built

YARNNN's supervision model requires review before external delivery. The `act` skill requires:
1. ActionPolicy infrastructure (staged vs. auto approval)
2. Action audit trail in `activity_log`
3. User confidence in agent intelligence (accumulated through digest/synthesize usage)

### Scope behavior (planned)

| Scope | Template | Behavior |
|-------|----------|----------|
| **platform** | Slack Responder | Reply to threads in configured channels. Approval-gated. |
| **cross_platform** | — | Cross-platform actions. Advanced. |
| **autonomous** | Auto Action | Self-directed action execution. Highest trust level. |

---

## Hidden Pre-Launch (2026-03-12)

The following skills/templates are implemented in the backend but hidden from the creation UI:

| Template | Skill | Reason hidden | Restore when |
|----------|-------|--------------|--------------|
| **Channel Watch** | monitor | Promises monitoring but architecture is polling-based (1-24hr sync). Misleading UX. | Sub-5-minute sync or webhook infrastructure |
| **Domain Tracker** | monitor | Knowledge-scope agents need accumulated knowledge base to function. | Platform agents have run long enough to build `/knowledge/` |
| **Coordinator** | orchestrate | Power-user meta-feature. Not needed for initial adoption. | User base has power users creating 5+ agents |
| **Custom** | (varies) | Adds ambiguity. Users should choose from validated templates pre-launch. | Post-launch, if users request flexibility beyond active templates |

---

## Key Files (shared across all skills)

| Concern | Location |
|---------|----------|
| Skill prompts | `api/services/agent_pipeline.py` (TYPE_PROMPTS → SKILL_PROMPTS) |
| Default instructions | `api/services/agent_pipeline.py` (DEFAULT_INSTRUCTIONS) |
| Execution strategies | `api/services/execution_strategies.py` |
| Primitive registry | `api/services/primitives/registry.py` |
| Content fetching | `api/services/platform_content.py` |
| Generation pipeline | `api/services/agent_execution.py` |
| Framework reference | [docs/architecture/agent-framework.md](../architecture/agent-framework.md) |
| Targeting architecture | [ADR-104](../adr/ADR-104-agent-instructions-unified-targeting.md) |
| Quality testing | `docs/development/agent-quality-testing.md` |
