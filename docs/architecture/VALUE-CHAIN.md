# YARNNN Value Realization Chain

> **Status**: Canonical
> **Date**: 2026-03-16
> **Related**: [FOUNDATIONS.md](FOUNDATIONS.md) (Axioms 2, 4, 5), [NARRATIVE.md](../NARRATIVE.md) (Beats 3-5), [ADR-110](../adr/ADR-110-onboarding-bootstrap.md), [ADR-111](../adr/ADR-111-agent-composer.md), [ADR-113](../adr/ADR-113-auto-source-selection.md)
> **Audience**: Engineering (canonical pipeline reference), IR/Strategy (value compounding narrative)

---

## The Chain

```
CONNECT  →  PERCEIVE  →  BOOTSTRAP  →  FIRST VALUE  →  ACCUMULATE  →  COMPOSE  →  COMPOUND
  │            │             │              │               │             │            │
  ▼            ▼             ▼              ▼               ▼             ▼            ▼
OAuth +      Smart        Auto-create    First agent     Outputs       Composer     Second-order
auto-select  defaults +   platform       run delivers    feed back     identifies   agents build
sources      first sync   digest agent   within minutes  as content    new patterns on first-order
                                                                                    outputs
```

Each phase's output is the next phase's input. This is the product's compounding mechanism — and the reason a competitor starting from zero cannot replicate a tenured YARNNN instance.

---

## Phase 1: Connect (seconds)

**What happens**: User clicks a platform card on the dashboard. OAuth completes. The system takes over.

**Who does it**: OAuth callback (`api/routes/integrations.py`)

**What it produces**:
- Platform connection with encrypted credentials
- Landscape discovery (all available channels, labels, pages, calendars)
- Smart source auto-selection via `compute_smart_defaults()` (ADR-113)
- First sync kicked off as a background task
- Redirect to `/dashboard` — not a configuration page

**Design principle**: Zero decisions required from the user. Source selection is automatic, informed by multi-signal heuristics (channel purpose, name patterns, type, recency). Manual curation is available later as optional refinement, never as a prerequisite.

**ADRs**: ADR-113 (auto source selection), ADR-057 (onboarding flow), ADR-112 (sync efficiency)

---

## Phase 2: Perceive (seconds to minutes)

**What happens**: Platform sync fetches content from auto-selected sources. Raw work data flows into the knowledge base.

**Who does it**: Platform sync worker (`api/workers/platform_worker.py`)

**What it produces**:
- `platform_content` rows — Slack messages, Gmail threads, Notion pages, Calendar events
- Paginated, incremental, platform-specific extraction (thread expansion, user resolution, deduplication)
- Content tagged with TTL-based retention (Slack 14d, Gmail 30d, Notion 90d, Calendar 2d)

**Design principle**: The perception pipeline is the onramp. It meets users where their work already lives. But it is not the engine — the engine is what agents do with this substrate (Phases 4-7).

**ADRs**: ADR-077 (sync overhaul), ADR-072 (unified content layer), ADR-112 (sync efficiency)

---

## Phase 3: Bootstrap (immediate, post-sync)

**What happens**: Sync completes. The system deterministically creates a matching digest agent for the platform.

**Who does it**: Onboarding bootstrap (`api/services/onboarding_bootstrap.py`)

**What it produces**:
- Platform-specific digest agent: Slack Recap, Gmail Digest, Notion Summary, Calendar Brief
- Agent created with `origin=system_bootstrap`, pre-configured skill, schedule, and sources
- First agent run triggered immediately

**Design principle**: Deterministic, zero-LLM. No intelligence needed to know that connecting Slack warrants a Slack digest. Speed and reliability over sophistication. The Composer (Phase 6) handles the sophisticated decisions.

**ADRs**: ADR-110 (onboarding bootstrap), ADR-109 (agent framework)

---

## Phase 4: First Value (minutes after connection)

**What happens**: The bootstrapped agent executes its first run. The user sees a real output — a digest of their actual work data — within minutes of connecting.

**Who does it**: Agent execution pipeline (`api/services/agent_execution.py`, `api/services/agent_pipeline.py`)

**What it produces**:
- Agent run with generated content (draft or delivered)
- Output written to `/knowledge/` filesystem as structured, searchable workspace files (ADR-107, supersedes ADR-102)
- Delivery via configured channel (in-app, email, Slack)

**Why this matters**: This is the moment of first value. The user connected a platform and received a useful output without configuring anything. Every subsequent phase builds on this moment. If this output is poor, the chain stalls. If it's good, the user trusts the system to do more.

**Design principle**: First-run quality over configuration breadth (FOUNDATIONS.md Axiom 6). One excellent auto-generated output beats three manually configured mediocre ones.

**ADRs**: ADR-101 (intelligence model), ADR-107 (knowledge filesystem), ADR-080 (unified agent modes)

---

## Phase 5: Accumulate (days)

**What happens**: The recursive loop begins. Three things compound simultaneously:

1. **Platform sync continues** — new messages, emails, pages, events flow in on schedule (daily for free, hourly for pro)
2. **Agent outputs feed back** — each digest run's output is written to `/knowledge/` as structured workspace files (ADR-107), becoming searchable input for future agent runs and for other agents via `QueryKnowledge`
3. **User feedback refines** — edits, approvals, and dismissals become learned preferences injected into future agent prompts

**Who does it**: Platform sync scheduler, agent execution pipeline, memory extraction service

**What it produces**:
- Growing knowledge base: raw platform data + agent-generated insights + user feedback signals
- Per-agent memory: observations, domain notes, goal progress
- Learned preferences: format choices, content priorities, tone adjustments extracted from edit history

**Why this matters**: This is where the product's moat forms. A Slack digest on day 30 knows what the user edited out of the last 4 digests, which channels consistently produce signal, and what format the user prefers. A competitor starting from zero produces a generic summary. The gap widens with every cycle.

**Design principle**: Optimize for accumulation, not extraction (FOUNDATIONS.md Axiom 2). The internal/reflexive perception layers (agent outputs, user feedback) are more valuable long-term than the external layer (platform sync).

**ADRs**: ADR-072 (retention-based accumulation), ADR-087 (agent-scoped context), ADR-101 (intelligence model — feedback layer)

---

## Phase 6: Compose (days to weeks)

**What happens**: The Composer — TP exercising judgment about what attention the user's work requires — assesses the enriched substrate and identifies opportunities for new agents.

**Who does it**: TP's Composer capability (ADR-111, FOUNDATIONS.md Axiom 5)

**Triggers**:
- Periodic heartbeat (self-assessment on cadence)
- Platform connection event (new substrate available)
- Agent feedback patterns (maturity signals, user corrections)
- Sufficient accumulated substrate (enough runs, enough data to reason over)

**What it produces**:
- High-confidence agents auto-created (with "Auto" badge on dashboard) — coverage gap fills are deterministic, no LLM
- Cross-platform synthesis agents created when mature digests exist (lifecycle expansion)
- LLM-assessed agents (Haiku) for non-obvious opportunities — engaged user patterns, cross-platform synthesis
- Lifecycle actions: underperformer pausing (<30% approval, 8+ runs), cross-agent consolidation

**Design principle**: The Composer reasons about the full substrate — not just "which platforms are connected" but what agent outputs exist, what patterns emerge across platforms, what the user's feedback signals indicate they care about. Platform content is the onramp; accumulated agent work is the signal.

**ADRs**: ADR-111 (Agent Composer), ADR-109 (scope × skill × trigger taxonomy)

---

## Phase 7: Compound (weeks to months)

**What happens**: Second-order agents build on first-order outputs. The information hierarchy (FOUNDATIONS.md Axiom 4) deepens:

| Level | What | Example | Typical Phase |
|-------|------|---------|---------------|
| L0 | Raw signals | Slack messages, email threads | Phase 2 (Perceive) |
| L1 | Digests | "Here's what happened in #engineering today" | Phase 4 (First Value) |
| L2 | Insights | "The team discussed migration 3 times this week" | Phase 5 (Accumulate) |
| L3 | Analysis | "Eng and product are misaligned on migration timeline" | Phase 7 (Compound) |
| L4 | User knowledge | Learned preferences, domain theses, standing instructions | Accumulated across all phases |

**What it looks like**:
- A Slack Recap agent (L1) produces daily digests
- Those digests accumulate as `/knowledge/digests/` files (ADR-107)
- The Composer identifies a pattern: engineering discussions span Slack and Gmail
- It creates an "Engineering Week in Review" agent (L2-L3) that reads digest outputs + raw platform content
- That agent's outputs feed back into the substrate
- Months later, enough accumulated L2-L3 outputs exist for quarterly trend analysis or board prep synthesis

**The compounding property**: Each level's output is the next level's input. Higher-level agents don't re-read raw Slack messages — they read curated digests and prior analyses. This means:
- Quality improves with every layer (signal-to-noise ratio increases)
- Coverage widens (cross-platform synthesis becomes possible)
- Cost decreases (higher-level agents process distilled content, not raw firehose)
- Switching costs deepen (accumulated L2-L4 content is irreplaceable)

**ADRs**: ADR-107 (knowledge filesystem), ADR-106 (workspace architecture), ADR-072 (retention model)

---

## The Full Loop

```
        ┌──────────────────────────────────────────────────────┐
        │                                                      │
        ▼                                                      │
   [Connect] → [Perceive] → [Bootstrap] → [First Value]       │
                                               │               │
                                               ▼               │
                                          [Accumulate]         │
                                               │               │
                                               ▼               │
                                          [Compose]            │
                                               │               │
                                               ▼               │
                                          [Compound] ──────────┘
                                               │          (outputs feed back
                                               │           as perception)
                                               ▼
                                          User feedback
                                          refines all layers
```

The loop is self-reinforcing:
- More platform data → better digest agents → richer substrate → smarter Composer decisions → higher-level agents → outputs feed back as content → even richer substrate
- User feedback at any point improves all downstream outputs — editing a digest teaches the agent preferences that compound across every future run

---

## Timeline: What the User Experiences

| Time | What happens | What the user sees |
|------|-------------|-------------------|
| **T+0s** | OAuth completes, sources auto-selected | Dashboard: "Slack connected" |
| **T+10s** | Sync begins fetching content | Dashboard: "Syncing..." |
| **T+60s** | Sync completes, bootstrap creates digest agent, first run executes | Dashboard: first agent appears, first output delivered |
| **Day 2-7** | Daily syncs accumulate content, digest agent runs daily | Digests arrive on schedule, improving with each run |
| **Week 2** | Composer heartbeat assesses substrate | Dashboard: Composer suggests cross-platform agent or auto-creates one |
| **Month 1** | Multiple agents running, user has given feedback on several outputs | Agents noticeably tailored to user's preferences and priorities |
| **Month 3** | L2-L3 agents producing insights from accumulated digest outputs | System understands the user's work at a level no fresh start can replicate |

---

## Separation of Concerns

Each phase has a single owner. No phase duplicates another's responsibility.

| Phase | Owner | Decides | Does NOT decide |
|-------|-------|---------|----------------|
| **Connect** | OAuth callback + `compute_smart_defaults()` | Which sources to sync | What agents to create |
| **Perceive** | Platform sync worker | What content to extract and store | What's important in that content |
| **Bootstrap** | Onboarding bootstrap | Which deterministic digest agent to create | Whether this is the right agent for the user |
| **First Value** | Agent execution pipeline | What to include in the output, based on its intelligence model | Which sources to sync or which agents to create |
| **Accumulate** | Sync scheduler + memory extraction | When to sync, what feedback to extract | What to do with accumulated knowledge |
| **Compose** | TP Composer capability | What new agents are warranted by the substrate | How those agents execute (that's the agent's job) |
| **Compound** | Second-order agent execution | What higher-level insights to produce | What first-order agents should do differently |

---

## Why This Compounds (The Moat Paragraph)

A competitor building a Slack digest tool can match Phase 4 on day one. What they cannot match:

- **Phases 5-7 require time.** Accumulated feedback, agent memory, learned preferences, and layered outputs are a function of tenure. There is no shortcut.
- **Each layer depends on the previous.** A cross-platform synthesis agent (Phase 7) requires weeks of digest outputs (Phase 5) to reason over. You cannot skip to L3 analysis without L1 digests.
- **User feedback compounds across all layers.** An edit to a Slack digest teaches a preference that propagates to every agent that reads that digest's output. The correction is amplified, not isolated.
- **The substrate is personal.** It reflects this user's work, this user's platforms, this user's feedback history. It cannot be transferred or replicated from another user's data.

This is FOUNDATIONS.md Axiom 4 in practice: value comes from accumulated attention. The agent is how it's delivered. The accumulated intelligence is the product.

---

## Code Reference

| Phase | Key files | ADRs |
|-------|-----------|------|
| Connect | `api/routes/integrations.py`, `api/services/landscape.py`, `api/integrations/core/oauth.py` | ADR-113, ADR-057 |
| Perceive | `api/workers/platform_worker.py`, `api/integrations/core/{slack,google,notion}_client.py` | ADR-077, ADR-072, ADR-112 |
| Bootstrap | `api/services/onboarding_bootstrap.py` | ADR-110 |
| First Value | `api/services/agent_execution.py`, `api/services/agent_pipeline.py` | ADR-101, ADR-107, ADR-080 |
| Accumulate | `api/jobs/platform_sync_scheduler.py`, `api/services/memory.py`, `api/services/workspace.py` | ADR-072, ADR-087, ADR-107 |
| Compose | TP Composer capability (`api/services/composer.py`) | ADR-111, ADR-109 |
| Compound | Agent execution (same pipeline, higher-level agents) + `QueryKnowledge` primitive | ADR-107, ADR-106 |

---

## Implementation Status (2026-03-16)

| Phase | Status | Notes |
|-------|--------|-------|
| **1. Connect** | **Shipped** | ADR-113 auto-select + sync in OAuth callback |
| **2. Perceive** | **Shipped** | All 4 platforms, paginated, incremental, tier-gated |
| **3. Bootstrap** | **Shipped** | Deterministic digest creation + inline first-run execution |
| **4. First Value** | **Shipped** | Bootstrap executes first run inline (not waiting for scheduler) |
| **5. Accumulate** | **Shipped** | Agent outputs → `/knowledge/` (ADR-107). Feedback → learned preferences (ADR-101). Sync continues on schedule. |
| **6. Compose** | **Shipped** | All three bounded contexts active: Bootstrap (deterministic, ADR-110), Heartbeat (scheduled in `unified_scheduler.py`, tier-gated: Free=daily, Pro=every 5min), Lifecycle (underperformer pausing, scope expansion, cross-agent consolidation). LLM reasoning (Haiku) fires only when `should_composer_act()` identifies actionable gaps. |
| **7. Compound** | **Infrastructure ready** | `QueryKnowledge` primitive lets agents search `/knowledge/`. Cross-platform and synthesis agents auto-created by Composer when mature digests exist. Second-order agent creation is autonomous — depends on sufficient L1 digest accumulation (typically week 2+). |

### Composer Bounded Contexts (ADR-111)

1. **Bootstrap** — deterministic agent creation on platform connect. Inline first-run execution. **Shipped.**
2. **Heartbeat** — periodic TP self-assessment on cadence. `run_heartbeat()` called from `unified_scheduler.py` per user. Free=midnight UTC only, Pro=every 5-min cycle. 7 trigger conditions: coverage gaps, underperformers, lifecycle expansion, cross-platform opportunity, stale agents, engaged user, cross-agent patterns. **Shipped.**
3. **Lifecycle** — underperformer pausing (auto-pause at <30% approval, 8+ runs), scope expansion (mature digests → synthesis agent), cross-agent consolidation. **Shipped.**

Phase 7 readiness depends on Phase 6 creating second-order agents, which requires sufficient accumulated L1 outputs — a function of time, not missing code.

---

*This document is the canonical reference for YARNNN's value realization chain. NARRATIVE.md defines how to tell this story. FOUNDATIONS.md defines why it works. This document defines what happens, in what order, and who owns each phase.*
