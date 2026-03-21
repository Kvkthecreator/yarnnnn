# Projects as Product Direction

**Date:** 2026-03-18
**Status:** Proposed
**Related:**
- [Agent Framework: Scope × Role × Trigger](../architecture/agent-framework.md) — taxonomy + user-facing identity section
- [Agent Presentation Principles](AGENT-PRESENTATION-PRINCIPLES.md) — source-first mental model (extends to project-first)
- [Supervision Dashboard](SUPERVISION-DASHBOARD.md) — current dashboard (v1, agent-centric; v2 adds projects)
- [Surface-Action Mapping](SURFACE-ACTION-MAPPING.md) — directive vs configuration surfaces (unchanged)
- [ADR-119: Workspace Filesystem Architecture](../adr/ADR-119-workspace-filesystem-architecture.md) — project folder conventions
- [ADR-118: Skills as Capability Layer](../adr/ADR-118-skills-as-capability-layer.md) — output skills

---

## The Direction

Projects are a first-class concept in the product — prominent once introduced, and the natural container for composed, multi-agent value. Standalone agents remain valid and are the bootstrap entry point. The dashboard surfaces both, with projects becoming the primary unit as the user's workforce matures.

This is NOT "everything must be a project." It IS "projects are where the product's unique value lives, and the product should make that visible and accessible."

## Why

Standalone agents (Slack recap, email digest) are table-stakes — every AI tool does this. The moat is **composition**: multiple specialized agents producing assembled deliverables that none could produce alone. Projects are the user-facing container for that composition. If the product hides projects behind progressive disclosure, users never discover the moat. If the product leads with projects alongside agents as soon as onboarding is complete, users see the upgrade path immediately.

For a pre-user product fighting for adoption: the magic moment of "Your Slack Agent sent you a recap" gets users in the door. The retention moment of "Your Q2 Review project assembled a deck from three agents' work" keeps them.

## Settled Decisions

These were resolved through architectural discourse (2026-03-18) and should not be re-litigated without new evidence.

1. **Projects are optional, not mandatory.** Bootstrap creates standalone agents. Projects are created when the user asks or when Composer detects composition opportunities. No project wrapper for single-agent cases.

2. **Standalone agents are valid.** A Slack digest agent that's not part of any project is a complete, useful entity. It has full feedback loops, output skills, and identity. "Your Slack Agent" is a first-class citizen.

3. **Agents can contribute to multiple projects.** An agent has one workspace but can contribute to N projects. The agent's output lives in its own workspace; projects reference it. Project-specific contributions go to `/projects/{slug}/contributions/{own-slug}/`.

4. **Platform sync is infrastructure; digest agents are workers.** The cron that fetches raw Slack data is invisible. The digest agent that produces a meaningful summary is visible, manageable, and has full feedback loops. Both exist; only the agent is user-facing.

5. **Composer manages project assembly.** No dedicated coordinator agent. Composer reads contributions, invokes output gateway skills, writes assembled output to `/projects/{slug}/assembly/`. Single-surface model preserved.

8. **PM is a coherence monitor, not just a logistics coordinator.** PM reads contributor self-assessment histories (rolling, 5 recent) and walks prerequisite layers (commitment → structure → context → quality → readiness) every pulse. PM writes `project_assessment.md` as an authoritative snapshot. Contributors read it to understand project constraints. This is the multi-agent coherence protocol (ADR-128).

6. **Projects are ongoing, not scheduled.** No cron expression on projects. Composer assembles when contributions have meaningfully changed. Projects trail indefinitely until archived by user, Composer, or dissolution.

7. **TP/Composer is the single conversational surface.** User says "let's talk about the Q2 review" and Composer scopes context to that project. No separate project chat interface.

## Frontend Impact Summary

Based on audit of existing pages and components:

| Page | Route | Current State | Impact | What Changes |
|---|---|---|---|---|
| **Dashboard** | `/dashboard` | Flat agent health grid + Composer feed | **HIGH** | Add project section above agent grid |
| **Orchestrator** | `/orchestrator` | TP chat | **MEDIUM** | Project-scoped context parameter |
| **Agent list** | `/agents` | Source-grouped flat list | **MEDIUM** | Add project filter/grouping |
| **Agent detail** | `/agents/[id]` | Chat + 5-tab panel | **MEDIUM** | Add "Projects" indicator, breadcrumb |
| **Project detail** | `/projects/[slug]` | **NEW** | — | New page: chat + panel (Assembly, Contributors, Instructions, Memory, Settings) |
| **Navigation** | Top bar dropdown | Dashboard, Orchestrator, Agents | **MEDIUM** | Add Projects to primary nav |
| **Onboarding** | `/onboarding/*` | Platform connection flow | **LOW** | No change — bootstrap still creates agents. Projects introduced post-onboarding via Composer |

## Dashboard Evolution

### Current (v1 — agent-centric, implemented)

```
┌─────────────────────────────────────────────────────┐
│  Dashboard                                          │
│                                                     │
│  [Attention banner — items needing review]           │
│                                                     │
│  AGENT HEALTH GRID                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│  │ [Slack]      │ │ [Gmail]      │ │ [Notion]     ││
│  │ Weekly Recap │ │ Email Digest │ │ Project Track ││
│  │ ● Mature ✓2h│ │ ● Dev ✓1d   │ │ ○ Paused ⚠  ││
│  └──────────────┘ └──────────────┘ └──────────────┘│
│                                                     │
│  COMPOSER ACTIVITY                                  │
│  ✨ Created "Cross-Platform Weekly" — 12h ago       │
│  ⏸ Paused "Daily Standup Notes" — 1d ago           │
└─────────────────────────────────────────────────────┘
```

### Proposed (v2 — projects + agents)

```
┌─────────────────────────────────────────────────────┐
│  Dashboard                                          │
│                                                     │
│  [Attention banner — items needing review]           │
│                                                     │
│  PROJECTS                                           │
│  ┌────────────────────────────────────────────────┐ │
│  │ 📋 Your Monday Brief                           │ │
│  │ Slack Agent · Gmail Agent · Calendar Prep      │ │
│  │ Last assembled: Mon 9am · PDF + PPTX           │ │
│  │ ✓ Delivered · 3 contributors                   │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │ 📋 Competitor Watch                            │ │
│  │ Market Researcher · Industry Monitor           │ │
│  │ Last assembled: 3d ago · PDF                   │ │
│  │ ✓ Delivered · 2 contributors                   │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  STANDALONE AGENTS                                  │
│  ┌──────────────┐ ┌──────────────┐                 │
│  │ [Slack]      │ │ [Notion]     │                 │
│  │ Weekly Recap │ │ Page Tracker │                 │
│  │ ● Mature ✓2h│ │ ● Dev ✓1d   │                 │
│  └──────────────┘ └──────────────┘                 │
│                                                     │
│  COMPOSER ACTIVITY                                  │
│  💡 Suggested: Combine Slack + Email into project   │
│  ✨ Created "Competitor Watch" project — 2d ago     │
└─────────────────────────────────────────────────────┘
```

Key changes from v1 to v2:
- **Projects section appears above standalone agents** — projects are the higher-value unit
- **Project cards show contributors** — the user sees which agents feed into the project
- **Standalone agents section** — agents not yet part of any project. Visual nudge: "these could be more powerful in a project"
- **Composer activity includes project actions** — project creation, assembly, suggestions
- **When user has zero projects** — section shows a prompt: "As your agents mature, Composer will suggest ways to combine their outputs. You can also ask: 'Create a project for my Monday meetings.'"

## Project Detail Page

New route: `/projects/[slug]`

### How project detail differs from agent detail

An agent detail page shows one worker's state: its instructions, memory, and outputs. A project detail page shows a **coordination layer**: objective that flows downstream to contributors, an assembly spec that defines how parts combine, and assembled outputs that are greater than the sum of contributions. The data relationships are fundamentally different.

| Aspect | Agent Detail | Project Detail |
|---|---|---|
| **Identity doc** | AGENT.md — behavioral instructions for one worker | PROJECT.md — objective, contributors, assembly spec, output requirements |
| **Core data** | One agent's runs and outputs | Multiple agents' contributions + assembled outputs |
| **Instructions** | "How to do your job" (behavioral) | "What this project produces, for whom, in what format" (objective) |
| **Feedback target** | User edits → this agent's preferences.md | User edits assembly → project preferences.md (+ can trace to specific contributor) |
| **Memory** | Agent's own observations + learned preferences | Project-level: what the assembly needs, cross-contribution patterns |
| **Settings** | Schedule, sources, delivery, skill authorizations | Delivery, contributor management, archive/dissolve |
| **Chat context** | 1:1 with this agent about its work | With Composer about this project (contributors, assembly, objective changes) |

### PROJECT.md schema

PROJECT.md is the project's identity document. It carries more than AGENT.md because it defines a coordination contract:

```markdown
# {Project Title}

## Objective
What this project produces, who it's for, why it exists.
- **Deliverable**: Weekly executive brief
- **Audience**: Leadership team
- **Format**: PDF deck with charts
- **Purpose**: Keep leadership informed on engineering + market + client signals

## Contributors
| Agent | Expected Contribution |
|-------|----------------------|
| Your Slack Agent | Engineering channel activity summary |
| Your Gmail Agent | Client communication highlights from email |
| Your Market Researcher | Competitive landscape updates |

## Assembly Spec
How contributions combine into the final deliverable:
- Executive summary synthesizing all contributions
- Section per domain: Engineering (Slack), Client (Gmail), Market (Research)
- Include revenue trend chart + activity heatmap
- Output format: PPTX deck + PDF export

## Delivery
- Channel: email
- Recipients: user
```

**Note on agent types used in examples**: All contributors reference agents that actually exist from bootstrap or Composer. Bootstrap creates platform-named agents per ADR-110: "Your Slack Agent" (Slack → digest), "Your Gmail Agent" (Gmail → digest), "Your Notion Agent" (Notion → digest). Composer creates cross-cutting agents: "Your Work Summary" (synthesize), "Your Market Researcher" (research). There is no "Gmail Agent" — Gmail is the platform, email is a delivery channel. The agent is named after the platform it reads from, not the output method.

**Objective** is the key differentiator. It answers "what and why" at the project level, which is upstream of any individual agent's instructions. When Composer assembles, it reads the objective to understand what the assembled output should accomplish. When contributing agents read PROJECT.md (via ReadAgentContext), the objective shapes their contributions — the Slack digest agent knows it's contributing to an executive brief, not a developer standup.

**Assembly spec** defines output requirements. If the spec says "PPTX deck with charts," Composer knows it needs `pptx` and `chart` skills during assembly. If a contributing agent doesn't have chart data, the assembly degrades gracefully (text section instead of chart) rather than failing.

### Page layout

Same workspace layout pattern (chat + panel), different panel tabs:

```
┌─────────────────────────────────────────────────────────────┐
│  ← Dashboard  /  Your Monday Brief                          │
│                                                             │
│  ┌─────────────────────────┐ ┌────────────────────────────┐│
│  │                         │ │  Assembly │ Contributors │  ││
│  │                         │ │  Objective │ Memory │ Settings ││
│  │                         │ ├────────────────────────────┤│
│  │      CHAT AREA          │ │                            ││
│  │                         │ │  ASSEMBLY (selected)       ││
│  │  Talk to Composer about │ │                            ││
│  │  this project:          │ │  Latest: 2026-03-17T0900   ││
│  │  - Review assembly      │ │  ┌────────────────────┐   ││
│  │  - Change objective        │ │  │ 📄 Monday Brief.pdf│   ││
│  │  - Add/remove agents    │ │  │ 📊 Revenue trend   │   ││
│  │  - Give feedback        │ │  │ 📝 output.md       │   ││
│  │                         │ │  └────────────────────┘   ││
│  │                         │ │  Sources: Slack Agent,     ││
│  │                         │ │  Gmail Agent, Researcher   ││
│  │                         │ │                            ││
│  │                         │ │  Previous assemblies...    ││
│  └─────────────────────────┘ └────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Panel tabs

**Assembly** — assembled outputs by date. Each assembly shows:
- Files with download/preview (PDF, PPTX, charts, text)
- Which contributions were included (linked to contributing agents)
- Delivery status (sent, pending, failed)
- Manifest data (sources, skills used, assembly timestamp)

**Contributors** — the project's team. Each contributor shows:
- Agent name + platform icon + link to agent detail
- Expected contribution (from PROJECT.md)
- Last contribution date + staleness indicator
- Skill authorization status (does the agent have skills the project needs?)
- Health: is the contributor actively producing? Is its output being included in assemblies?

**Objective** — PROJECT.md content, editable. This is NOT "instructions" in the agent sense. It's the project's purpose and coordination contract:
- What the project produces (deliverable description)
- Who it's for (audience)
- What format (output requirements → implies skill needs)
- How contributions combine (assembly spec)
- Editing objective may cascade: changing format from "PDF report" to "PPTX deck" changes skill requirements

**Memory** — project-level accumulated state:
- `preferences.md` — distilled from user feedback on assembled outputs ("leadership prefers bullet points over paragraphs," "include the chart on page 1")
- `observations.md` — cross-contribution patterns Composer has noticed ("Slack data and email data overlap on client mentions — deduplicate in assembly")
- `project_assessment.md` — PM's layered evaluation (ADR-128): which prerequisite layer (commitment/structure/context/quality/readiness) is the current constraint. Rewritten every PM pulse.
- `decisions.md` — project-level decisions persisted from meeting room conversations (ADR-128). Accumulated, not overwritten.
- Read-only display. System-written, not user-editable.

**Settings** — project configuration:
- Delivery destination (email, Slack, Notion)
- Add/remove contributors (links to agent selection)
- Archive/dissolve project
- Output format preferences (override assembly spec without editing full PROJECT.md)

## Agent Detail Updates

Existing route: `/agents/[id]`

Minimal changes:
- **Project membership indicator** — if agent contributes to projects, show badges/links: "Contributing to: Monday Brief, Q2 Review"
- **Breadcrumb** — if navigated from a project page, show: "← Your Monday Brief / Slack Agent"
- **Contribution status** — in Settings tab, show which projects this agent contributes to and what it's expected to provide
- No structural changes to the 5-tab panel (Runs, Instructions, Memory, Sessions, Settings)

## Navigation Updates

Current top-bar dropdown:
```
Dashboard
Orchestrator
Work (Agents)
Context
Memory
Activity
System
```

Proposed:
```
Dashboard
Orchestrator
Projects          ← NEW (list of projects)
Agents            ← renamed from "Work"
Context
Memory
Activity
System
```

Projects route (`/projects`) shows a list view of all projects with status, last assembly date, contributor count. Clicking a project navigates to `/projects/[slug]`.

## Onboarding: No Change

Bootstrap flow remains: connect platform → create standalone agent → first run → magic moment email. Projects are introduced post-onboarding, either by Composer suggestion or user request via chat. This preserves the simplest possible entry point while keeping projects discoverable from the dashboard.

## Creation Flows

### Standalone agent creation (existing, unchanged)

User talks to Composer: "Create a Slack digest for my engineering channels." Composer calls CreateAgent → agent appears on dashboard. No project involvement.

### Project creation (new — CreateProject)

Project creation is more complex than agent creation because of **objective parsing and requirements propagation**.

**User-initiated flow:**

1. User says: "Create a project for my Monday executive brief — combine Slack and Gmail into a PDF deck"
2. Composer parses objective:
   - Deliverable: executive brief
   - Audience: implied executive/leadership
   - Format: PDF deck → requires `pptx` and/or `pdf` skills
   - Contributors needed: Slack agent + Gmail agent
   - Cadence: weekly (Monday)
3. Composer checks existing agents:
   - Slack digest agent exists? → assign as contributor
   - Gmail digest agent exists? → assign as contributor
   - If either doesn't exist → create it first, then assign
4. Composer checks skill requirements:
   - Project needs PDF output → output gateway has `pdf` skill ✓
   - Project needs charts → output gateway has `chart` skill ✓
   - Contributing agents need skill authorization? → Composer updates AGENT.md if needed
5. Composer creates project:
   - Writes `/projects/{slug}/PROJECT.md` with objective, contributors, assembly spec
   - Creates `/projects/{slug}/memory/`, `/projects/{slug}/contributions/`, `/projects/{slug}/assembly/`
   - Notifies contributing agents (project context injected on next run)
6. Project appears on dashboard. First assembly happens when contributing agents next produce outputs.

**Composer-initiated flow:**

1. Heartbeat detects: Slack agent's output consistently appears as source in synthesis agent's manifest
2. Composer proposes: "Your Slack Agent and Gmail Agent could combine into a Monday Brief"
3. User approves → Composer executes CreateProject with inferred objective
4. Or user modifies: "Yes, but make it a PDF deck, not just text" → Composer adjusts objective and skill requirements

### Updating a project (EditProject)

Changing objective cascades downstream:

- "Change format from PDF to PPTX deck" → assembly spec updates → skill requirements change → Composer verifies contributing agents have appropriate data for deck format
- "Add my research agent to this project" → PROJECT.md contributors list updates → research agent gets project context on next run → next assembly includes research contribution
- "Remove the email section" → contributor removed from PROJECT.md → agent continues standalone but no longer contributes
- "Change audience to the engineering team" → objective updates → preferences shift (technical detail level increases) → distills into project preferences.md over time

### Archiving a project

- User says "archive the Q2 review" OR Composer detects: no new contributions + no user engagement for extended period
- PROJECT.md status → archived, all project workspace_files lifecycle → archived
- Contributing agents are NOT affected — they continue as standalone agents
- Assembly history preserved for reference (archived, not deleted)

## Empty States

**Dashboard with zero projects, some agents:**
> Your agents are building up intelligence. As they mature, Composer will suggest ways to combine their outputs into richer deliverables. You can also ask: "Create a project for my Monday meetings."

**Dashboard with zero agents:**
> Connect a platform to get started. Your first agent will begin working immediately.

**Projects list with zero projects:**
> Projects combine outputs from multiple agents into assembled deliverables — presentations, reports, briefs. Ask Composer to create one, or wait for a suggestion as your agents mature.

## Versioning Note

This document introduces **v2** of the dashboard design. The current implementation (SUPERVISION-DASHBOARD.md) is v1 and remains accurate for the agent-centric surfaces. When projects are implemented in the frontend, SUPERVISION-DASHBOARD.md should be updated to reference this document for the project additions.

AGENT-PRESENTATION-PRINCIPLES.md remains valid — the source-first mental model applies within projects (project cards show contributor platform icons). The grouping hierarchy extends from `Source > Agent` to `Project > Source > Agent`.
