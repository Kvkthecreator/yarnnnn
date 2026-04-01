# YARNNN Value Realization Chain

> **Status**: Canonical (v2 — Era 3 rewrite)
> **Date**: 2026-03-24
> **Previous**: v1 (2026-03-16, platform-first model)
> **Related**: [FOUNDATIONS.md](FOUNDATIONS.md) (Axioms 2, 4, 5, 6), [NARRATIVE.md](../NARRATIVE.md) (Beats 3-5), [ADR-132](../adr/ADR-132-work-first-onboarding.md), [ADR-122](../adr/ADR-122-project-type-registry.md), [ADR-133](../adr/ADR-133-pm-coordinated-phase-dispatch.md)
> **Audience**: Engineering (canonical pipeline reference), IR/Strategy (value compounding narrative)

---

## The Chain

```
DESCRIBE  →  SCAFFOLD  →  CONNECT  →  FIRST VALUE  →  ACCUMULATE  →  COORDINATE  →  COMPOUND
   │            │            │             │               │              │              │
   ▼            ▼            ▼             ▼               ▼              ▼              ▼
User shares  Projects +   Platforms     First agent    Outputs feed   PM phases      Team intel
work context PM + team    enrich work-  run delivers   back, prefs    get smarter,   compounds:
             scaffolded   scoped        within         distill,       cross-phase    deeper
             from work    projects      minutes        domains        handoffs       expertise,
             description                               deepen         refine         better output
```

Each phase's output is the next phase's input. This is the product's compounding mechanism — and the reason a competitor starting from zero cannot replicate a tenured YARNNN instance.

---

## Phase 1: Describe (seconds)

**What happens**: User completes two-step onboarding: (1) "How is your work structured?" — single-focus vs. multi-scope, (2) define work scopes with context (text description + optional files). A single Sonnet inference extracts structured work units with rich specs.

**Who does it**: Onboarding page (`web/app/(authenticated)/onboarding/`) → inference endpoint → `scaffold_project()` for each work unit

**What it produces**:
- Work units extracted from user description (each with scope, deliverable type, implied audience, cadence)
- Work structure stored in `/memory/WORK.md`
- Ready for project scaffolding

**Design principle**: The most valuable input at onboarding is "what are you working on?" — not "which platform do you use." Work context determines project structure, agent types, scoping, and cadence. Platform connections are data enrichment, not the organizing principle (FOUNDATIONS.md Axiom 6).

**Why this matters**: A solo founder who says "I have 3 clients and a product launch" gets 4 correctly-scoped projects. Under the old platform-first model, connecting Slack would have produced one generic digest of everything.

**ADRs**: ADR-132 (work-first onboarding), ADR-122 (project type registry)

---

## Phase 2: Scaffold (seconds, immediate after Phase 1)

**What happens**: Each work unit becomes a project via `scaffold_project()`. The system creates a PM agent, typed contributor agents, and a three-file charter.

**Who does it**: Project type registry (`api/services/project_registry.py`)

**What it produces**:
- Project with charter files: `PROJECT.md` (objective, success criteria), `TEAM.md` (roster, capabilities), `PROCESS.md` (output spec, cadence, delivery)
- PM agent scoped to the project
- Contributor agents typed from the work description (briefer, analyst, researcher, etc.)
- Agent workspaces seeded: `AGENT.md`, `memory/reflections.md`, `memory/preferences.md`
- Cognitive files seeded for coherence protocol

**Design principle**: Deterministic scaffolding. No LLM needed to know that "track competitor pricing weekly" warrants a project with a scout + analyst + PM. Speed and reliability over sophistication. The PM and Composer handle the sophisticated decisions later.

**ADRs**: ADR-122 (project type registry + `scaffold_project()`), ADR-136 (three charter files), ADR-130 (agent type registry)

---

## Phase 3: Connect (seconds — can happen before, during, or after Phases 1-2)

**What happens**: User connects platforms via OAuth. Sources are auto-selected and mapped to work-scoped projects. Sync begins.

**Who does it**: OAuth callback (`api/routes/integrations.py`) → `compute_smart_defaults()` → platform sync worker

**What it produces**:
- Platform connection with encrypted credentials
- Landscape discovery (all available channels, pages)
- Smart source auto-selection mapped to existing projects (Slack channels → matching work scopes)
- First sync kicked off as background task
- `platform_content` rows — Slack messages, Notion pages — tagged with TTL-based retention

**Design principle**: Platform connections enrich existing work-scoped projects rather than creating new generic digests. A platform connection without work context falls back to bootstrap behavior (generic platform digest project). A platform connection *with* work context maps sources to the right projects.

**ADRs**: ADR-113 (auto source selection), ADR-132 (platform → work unit mapping), ADR-112 (sync efficiency)

---

## Phase 4: First Value (minutes after scaffolding)

**What happens**: The PM dispatches the first contributor run. The user sees a real output — a digest, analysis, or briefing of their actual work data — within minutes.

**Who does it**: PM pulse (Tier 3) → contributor dispatch → agent execution pipeline (`api/services/agent_execution.py`)

**What it produces**:
- Agent run with generated content (structured markdown + asset references)
- Output written to workspace: `/agents/{slug}/outputs/{date}/output.md` + `manifest.json`
- Output composed to HTML via compose engine
- Delivery via configured channel (in-app, email)

**Why this matters**: This is the moment of first value. The user described their work, the system scaffolded a team, and now they see a real deliverable produced by that team. If this output is good, the user trusts the system to do more. Every subsequent phase builds on this moment.

**Design principle**: First-run quality over configuration breadth (FOUNDATIONS.md Axiom 6). One correctly-scoped, well-structured output from a work-aware project beats three generic platform digests.

**ADRs**: ADR-133 (PM dispatch), ADR-130 (HTML-native output), ADR-118 (compose engine)

---

## Phase 5: Accumulate (days)

**What happens**: The recursive loop begins. Six things compound simultaneously:

1. **Platform sync continues** — new messages, pages flow in on schedule (daily for free, hourly for pro)
2. **Agent outputs feed back** — each run's output is written to workspace, becoming searchable input for future runs and for other agents via `QueryKnowledge`
3. **User feedback refines** — edits, approvals, and dismissals become learned preferences distilled into `memory/preferences.md`
4. **Agent reflections deepen** — post-run observations accumulate in `memory/observations.md`; reflections track mandate fitness over time in `memory/reflections.md` (ADR-149)
5. **Task knowledge accumulates** — each task builds its own knowledge substrate: `DELIVERABLE.md` (quality contract), `memory/feedback.md` (user corrections + TP evaluations), `memory/steering.md` (TP management notes) (ADR-149)
6. **Workspace context domains grow** — `/workspace/context/` accumulates structured domain knowledge that agents read and write, creating shared institutional memory across the workforce (ADR-151)

**Who does it**: Platform sync scheduler, agent execution pipeline, feedback distillation service, memory extraction service

**What it produces**:
- Growing knowledge base: raw platform data + agent-generated insights + user feedback signals
- Per-agent workspace state: observations, domain thesis, learned preferences, reflections
- Per-task knowledge: DELIVERABLE.md quality contracts, feedback history, TP steering notes (ADR-149)
- Accumulated context domains: `/workspace/context/` structured domain knowledge shared across agents (ADR-151)

**Why this matters**: This is where the moat forms. A briefer on day 30 knows what the user edited out of the last 4 briefings, which channels consistently produce signal, and what format the user prefers. A competitor starting from zero produces a generic summary. The gap widens with every cycle.

**Design principle**: Optimize for accumulation, not extraction (FOUNDATIONS.md Axiom 2). The internal/reflexive perception layers (agent outputs, user feedback, reflections, task knowledge, context domains) are more valuable long-term than the external layer (platform sync).

**ADRs**: ADR-072 (retention-based accumulation), ADR-117 (feedback distillation), ADR-128 (coherence protocol)

---

## Phase 6: Coordinate (days to weeks)

**What happens**: PM coordination matures. Three mechanisms deepen project execution quality:

1. **Phase dispatch refines** — PM learns which contributors need to run first, which handoffs work, which phases can parallelize
2. **Quality gating strengthens** — PM assesses contribution quality against project objective before triggering assembly. Low-quality contributions get steering via contribution briefs
3. **Cross-phase context injection** — PM curates prior phase outputs into briefs for next phase contributors. The researcher's findings become the analyst's context. The analyst's charts become the writer's evidence

**Who does it**: PM agent Tier 3 pulse, contribution briefs (`/contributions/{slug}/brief.md`), phase state tracking

**What it produces**:
- Refined work plans with structured phases and dependencies
- Quality-gated assembly: deliverables only assemble when contributions meet the bar
- Cross-phase context: each contributor benefits from prior phases' work
- PM coordination intelligence: which contributors are reliable, what assembly cadence works

**Why this matters**: This is where YARNNN becomes a coordinated team, not just co-located agents. A quarterly review where the researcher gathers data → analyst finds patterns → writer crafts narrative → PM assembles is structurally different from three agents producing independently.

**ADRs**: ADR-133 (phase dispatch), ADR-121 (PM as intelligence director), ADR-128 (coherence protocol)

---

## Phase 7: Compound (weeks to months)

**What happens**: Team intelligence compounds across the information hierarchy:

| Level | What | Example | Typical Phase |
|-------|------|---------|---------------|
| L0 | Raw signals | Slack messages, Notion pages | Phase 3 (Connect) |
| L1 | Digests | "Here's what happened in #engineering today" | Phase 4 (First Value) |
| L2 | Insights | "The team discussed migration 3 times this week" | Phase 5 (Accumulate) |
| L3 | Analysis | "Eng and product are misaligned on the migration timeline" | Phase 6 (Coordinate) |
| L4 | Team knowledge | Learned preferences, domain theses, PM coordination patterns | Accumulated across all phases |

**What it looks like**:
- A project's contributors each develop deep domain expertise — the briefer understands communication patterns, the analyst knows which metrics matter, the scout knows which competitor moves warrant attention
- PM coordination patterns mature — the PM knows when to dispatch, how to steer, what assembly quality looks like
- Cross-project intelligence: Composer identifies new project opportunities from mature single-project outputs
- User's work structure evolves: bounded projects complete and dissolve, persistent projects deepen, new scopes emerge

**The compounding property**: Each cycle's output is the next cycle's context. Every team member's output improves every other team member's context. PM coordination intelligence compounds independently of individual agent improvement. This creates three compounding loops running simultaneously:
- Agent-level: deeper domain expertise per contributor
- Project-level: better coordination, handoffs, assembly quality
- System-level: Composer creates new projects from mature outputs

**ADRs**: ADR-111 (Composer lifecycle), ADR-120 (project execution), ADR-126 (agent pulse)

---

## The Full Loop

```
        ┌──────────────────────────────────────────────────────┐
        │                                                      │
        ▼                                                      │
   [Describe] → [Scaffold] → [Connect] → [First Value]        │
                                              │                │
                                              ▼                │
                                         [Accumulate]          │
                                              │                │
                                              ▼                │
                                         [Coordinate]          │
                                              │                │
                                              ▼                │
                                         [Compound] ───────────┘
                                              │     (outputs + team
                                              │      intelligence
                                              │      feed back as
                                              │      perception)
                                              ▼
                                         User feedback
                                         refines all layers
```

The loop is self-reinforcing:
- Work description → correctly-scoped projects → PM-coordinated teams → better deliverables → richer substrate → smarter Composer decisions → new projects → deeper compounding
- User feedback at any point improves all downstream outputs — editing a briefing teaches a preference that propagates through the PM's quality gating to every contributor that reads that briefing's output

---

## Timeline: What the User Experiences

| Time | What Happens | What the User Sees |
|------|-------------|-------------------|
| **T+0s** | User describes work, projects scaffold | Orchestrator: "I've set up 3 projects for your client work" |
| **T+30s** | Platform connects, sources mapped to projects | Dashboard: "Slack connected — channels mapped to Client X, Client Y" |
| **T+90s** | PM dispatches first contributor runs | Dashboard: first deliverables appear per project |
| **Day 2-7** | Daily pulse cycles, agents accumulate observations | Deliverables arrive on schedule, improving with each cycle |
| **Week 2** | PM coordination matures, phases sequence properly | Cross-phase handoffs visible — analyst references researcher's findings |
| **Month 1** | Feedback loop has shaped every contributor | Outputs noticeably tailored — minimal edits needed |
| **Month 3** | Composer identifies cross-project opportunities | New projects suggested: "Your 3 client projects share patterns — want a Portfolio Overview?" |

---

## Separation of Concerns

Each phase has a single owner. No phase duplicates another's responsibility.

| Phase | Owner | Decides | Does NOT decide |
|-------|-------|---------|----------------|
| **Describe** | Onboarding + inference | What work scopes exist, what projects to scaffold | Which platform sources to sync |
| **Scaffold** | Project type registry + `scaffold_project()` | What charter, PM, and contributors each project gets | How those agents execute (that's the PM/agent's job) |
| **Connect** | OAuth callback + `compute_smart_defaults()` | Which sources to sync, which projects they map to | What agents to create |
| **First Value** | PM dispatch → agent execution pipeline | What to include in output, based on intelligence model | Which sources to sync or which projects to create |
| **Accumulate** | Sync scheduler + feedback distillation + memory extraction | When to sync, what feedback to distill, what to observe | What to do with accumulated knowledge (that's the agent's job) |
| **Coordinate** | PM pulse (Tier 3) | When to dispatch, how to steer, when to assemble | What content agents produce (that's the contributor's job) |
| **Compound** | Composer heartbeat + mature agent teams | What new projects are warranted, what lifecycle actions to take | How existing projects execute (that's the PM's job) |

---

## Why This Compounds (The Moat Paragraph)

A competitor building a Slack digest tool can match Phase 4 on day one. What they cannot match:

- **Phases 5-7 require time.** Accumulated feedback, agent memory, PM coordination intelligence, and cross-phase handoff quality are a function of tenure. There is no shortcut.
- **Team intelligence is multi-dimensional.** It's not just "better outputs" — it's better coordination, better phasing, better quality gating, better context injection between team members. These compound independently.
- **Each layer depends on the previous.** A coordinated quarterly review (Phase 7) requires weeks of individual contributor maturation (Phase 5) and PM coordination learning (Phase 6). You cannot skip to L3 analysis without L1 digests and L2 insights.
- **User feedback compounds across the team.** An edit to one contributor's output teaches a preference that propagates through PM quality gating to every contributor that reads that output. The correction is amplified, not isolated.
- **The substrate is personal.** It reflects this user's work structure, platforms, feedback history, and coordination preferences. It cannot be transferred or replicated.

This is FOUNDATIONS.md Axiom 4 in practice: value comes from accumulated attention. The coordinated agent team is how it's delivered. The accumulated team intelligence is the product.

---

## Code Reference

| Phase | Key Files | ADRs |
|-------|-----------|------|
| Describe | `web/app/(authenticated)/onboarding/`, `api/routes/onboarding.py` | ADR-132 |
| Scaffold | `api/services/project_registry.py`, `api/services/agent_creation.py` | ADR-122, ADR-136, ADR-130 |
| Connect | `api/routes/integrations.py`, `api/services/landscape.py`, `api/integrations/core/oauth.py` | ADR-113, ADR-112 |
| First Value | `api/services/agent_execution.py`, `api/services/agent_pipeline.py`, `api/services/agent_pulse.py` | ADR-133, ADR-130, ADR-126 |
| Accumulate | `api/jobs/platform_sync_scheduler.py`, `api/services/feedback_distillation.py`, `api/services/memory.py` | ADR-072, ADR-117, ADR-128 |
| Coordinate | `api/services/agent_pulse.py` (Tier 3), `api/services/workspace.py` (ProjectWorkspace) | ADR-133, ADR-121, ADR-120 |
| Compound | `api/services/composer.py`, mature agent execution (same pipeline) | ADR-111, ADR-126 |

---

## Implementation Status (2026-03-24)

| Phase | Status | Notes |
|-------|--------|-------|
| **1. Describe** | **Shipped** | 2-step onboarding, Sonnet inference, work unit extraction |
| **2. Scaffold** | **Shipped** | Project type registry, `scaffold_project()`, three charter files, PM + contributor creation |
| **3. Connect** | **Shipped** | Slack + Notion OAuth, auto-select, source-to-project mapping |
| **4. First Value** | **Shipped** | PM dispatch, compose engine, HTML-native output |
| **5. Accumulate** | **Shipped** | Feedback distillation, agent self-reflection, workspace accumulation |
| **6. Coordinate** | **Shipped** | PM phase dispatch, quality assessment, contribution steering, cross-phase context |
| **7. Compound** | **Infrastructure ready** | Composer heartbeat, project lifecycle. Cross-project composition depends on sufficient L1-L2 accumulation (typically month 2+). |

---

*This document is the canonical reference for YARNNN's value realization chain. NARRATIVE.md defines how to tell this story. FOUNDATIONS.md defines why it works. This document defines what happens, in what order, and who owns each phase.*
