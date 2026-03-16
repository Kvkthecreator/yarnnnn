# Agent Framework: Scope × Skill × Trigger

**Status:** Canonical
**Date:** 2026-03-12
**Supersedes:** ADR-093 (7 purpose-first types), ADR-082 (8-type consolidation), ADR-044 (type reconceptualization)
**Related:**
- [ADR-092: Agent Intelligence & Mode Taxonomy](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) — mode system (preserved as Trigger axis)
- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — workspace filesystem, archetype-driven strategies
- [ADR-107: Knowledge Filesystem Architecture](../adr/ADR-107-knowledge-filesystem-architecture.md) — `/knowledge/` filesystem, three storage domains
- [ADR-101: Agent Intelligence Model](../adr/ADR-101-agent-intelligence-model.md) — four-layer knowledge model
- [ADR-104: Agent Instructions as Unified Targeting](../adr/ADR-104-agent-instructions-unified-targeting.md)
- [Analysis: Agent Taxonomy First Principles](../analysis/agent-taxonomy-first-principles-2026-03-12.md) — full discourse and stress-testing
- [Agent Presentation Principles](../design/AGENT-PRESENTATION-PRINCIPLES.md) — frontend: source-first grouping, card anatomy, creation flow

---

> **Relationship to FOUNDATIONS.md (2026-03-16):** This framework describes the **initial configuration** of an agent — its starting point. FOUNDATIONS.md Axiom 3 (Agents as Developing Entities) describes how agents evolve beyond this initial configuration over time: intentions become dynamic and multiple, capabilities are earned through feedback, autonomy graduates per-capability. The Scope × Skill × Trigger taxonomy is the seed; the developmental trajectory is the growth. See [Agent Developmental Model Considerations](../analysis/agent-developmental-model-considerations.md) for the pre-decision analysis on developmental trajectory. See [ADR-092 revision notes](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) for reframing of proactive/coordinator modes as TP supervisory capabilities.

## Foundational Principle

Every agent answers two irreducible questions:

1. **What does the agent know?** → **Scope** — determines context strategy
2. **What does the agent do?** → **Skill** — determines prompt, primitives, output shape

A third operational question governs lifecycle:

3. **When does the agent act?** → **Trigger** — determines scheduler behavior

An agent's **identity** is defined by Scope × Skill. Its **lifecycle** is governed by Trigger. These are orthogonal: any Scope can combine with any Skill, and any Scope × Skill combination can run on any Trigger.

This framework is designed to survive any future agentic protocol. A2A Agent Cards, MCP resources, Claude Agent SDK, OpenAI Assistants — all express Scope (what the agent accesses), Skill (what it can do), and Trigger (when it runs). The specific values within each axis expand; the axes themselves are stable.

---

## Axis 1: Scope — What the agent knows

Scope determines the agent's **context strategy** — how intelligence is gathered before and during execution.

| Scope | Source | Strategy | Character |
|-------|--------|----------|-----------|
| **platform** | Specific sources from one platform (Slack channels, Gmail labels, Notion pages, Calendar) | PlatformBoundStrategy → content dump | High-fidelity, recency-driven, bounded |
| **cross_platform** | Sources from multiple connected platforms | CrossPlatformStrategy → multi-platform dump | Broader, requires synthesis and prioritization |
| **knowledge** | Accumulated `/knowledge/` filesystem + workspace files + agent outputs | KnowledgeStrategy → workspace-driven queries | Longitudinal, compounds over time, the moat |
| **research** | Web search, external APIs, uploaded documents + knowledge grounding | ResearchStrategy → primitives-driven | Unbounded scope, requires scoping via instructions |
| **autonomous** | Agent selects own context strategy dynamically | AutonomousStrategy → full primitive set | Maximum flexibility, highest intelligence requirement |

### Key architectural distinction

**Platform** and **cross_platform** scopes are **dump-based**: context is gathered before the LLM call via `get_content_summary_for_generation()`. The agent receives pre-assembled content.

**Knowledge**, **research**, and **autonomous** scopes are **tool-driven**: the agent receives workspace context (thesis, memory, working notes) and drives its own investigation via primitives (QueryKnowledge, WebSearch, SearchWorkspace). This maps to the Reporter vs. Analyst archetype split (ADR-106).

### Scope is auto-inferred, never user-configured

Users configure **sources** (connect Slack, select channels) and **instructions** (describe focus). Scope is derived:

```
0 platform sources + research skill        → research
0 platform sources + any other skill       → knowledge
1 platform                                 → platform
2+ platforms                               → cross_platform
coordinator/orchestrate skill              → autonomous
```

The user never thinks "platform scope" — they think "my Slack channels." Scope is a system-internal execution strategy classification.

### Knowledge-scope boundary (inception principle)

> **Implementation status (2026-03-16):** This boundary is documented as architectural intent but not yet enforced in code. Current execution strategies do not block `platform_content` access for knowledge-scope agents. Enforcement deferred to Phase 3 (ADR-106 workspace architecture). The design principle remains valid — the accumulation loop should be forced to work before boundaries are relaxed.

Knowledge-scope agents have **NO access** to `platform_content` at inception. If no accumulated knowledge exists, the agent explicitly reports this:

> "No accumulated knowledge available for this domain. Platform agents need to run first to build the knowledge base."

This creates an observable dependency: platform agents → `/knowledge/` → knowledge agents. The accumulation loop must be forced to work before boundaries are relaxed.

---

## Axis 2: Skill — What the agent does

Skill determines the agent's **prompt template**, **available primitives**, **output shape**, and **quality evaluation**.

| Skill | Verb | Output | Character |
|-------|------|--------|-----------|
| **digest** | Compress, summarize | Document (recap, summary) | Lossy reduction, recency-weighted |
| **prepare** | Anticipate, assemble | Document (brief, prep) | Event-driven, anticipatory, time-sensitive |
| **monitor** | Track, diff, alert | Document or notification | Differential against baseline/thesis, stateful |
| **research** | Investigate, analyze | Document (report, analysis) | Exploratory, goal-bounded, depth-first |
| **synthesize** | Connect, derive insight | Document (insight, thesis) | Cross-source, pattern recognition, longitudinal |
| **orchestrate** | Coordinate, dispatch | Agent actions (create/trigger agents) | Meta-level, reads agent outputs, manages fleet |
| **act** | Execute, respond, post | Platform action (reply, send, update, post) | Agentic, requires permissions, approval-gated (future) |

### One agent, one skill

Multi-skill requests decompose into multiple agents sharing the same source configuration. This is architecturally correct because:

- Digest and Reply have different triggers, context budgets, quality evaluation, and failure modes
- Combining them forces conflicting optimization targets
- UX solution: templates can create **agent bundles** — one user action, multiple correctly-scoped agents

### Primitive gating by skill

```python
SKILL_PRIMITIVES = {
    "digest":       ["Search", "Read", "RefreshPlatformContent", "QueryKnowledge"],
    "prepare":      ["Search", "Read", "RefreshPlatformContent", "QueryKnowledge", "WebSearch"],
    "monitor":      ["Search", "Read", "RefreshPlatformContent", "QueryKnowledge", "ReadWorkspace", "WriteWorkspace"],
    "research":     ["Search", "Read", "RefreshPlatformContent", "QueryKnowledge", "WebSearch", "ReadWorkspace", "WriteWorkspace", "SearchWorkspace"],
    "synthesize":   ["Search", "Read", "QueryKnowledge", "ReadWorkspace", "WriteWorkspace", "SearchWorkspace"],
    "orchestrate":  ["Search", "Read", "QueryKnowledge", "ReadWorkspace", "WriteWorkspace", "CreateAgent", "AdvanceAgentSchedule"],
    "act":          ["Search", "Read", "QueryKnowledge", "SlackReply", "SlackPost", "SendEmail", "UpdateNotionPage"],  # future, gated by ActionPolicy
}
```

### Action capability is policy, not dimension

Capability level (read-only → monitored → autonomous) is NOT a separate axis. It is a **graduated permission model** (ActionPolicy) applied to the skill's primitive set:

```python
class ActionPolicy:
    """Per-agent permission model for write primitives.
    Derivative of Skill — not a taxonomic dimension."""

    approval_mode: Literal["staged", "auto"]  # default: staged
    rate_limit: Optional[int]                  # max actions per hour
    allowed_actions: list[str]                 # e.g., ["SlackReply", "SendEmail"]
    confidence_threshold: Optional[float]      # auto-approve above this (0.0-1.0)
```

An act-skill agent with `auto_approve: false` operates at "staged" level. Same agent with `auto_approve: true` operates at "autonomous" level. That's a policy toggle, not a taxonomy change.

---

## Axis 3: Trigger — When the agent acts

Trigger determines **scheduler behavior** and **execution lifecycle**. Preserved from ADR-092's mode taxonomy — renamed for industry alignment.

| Trigger | Character | Execution | Memory Role |
|---------|-----------|-----------|-------------|
| **recurring** | Clockwork | Fixed schedule, always runs on time | Learned preferences, format patterns |
| **goal** | Project | Fixed schedule, stops when objective complete | Goal progress, milestone tracking |
| **reactive** | On-call | Event-driven, accumulates observations, generates at threshold | Agent-authored event observations |
| **proactive** | Living specialist | Periodic self-review, generates when conditions warrant | Self-authored domain review log |
| **coordinator** | Meta-specialist | Periodic review + can create/trigger child agents | Review log + created_agents deduplication |

Trigger is important but operational — it governs scheduling, not identity. An agent's character is defined by its Scope × Skill; its lifecycle is governed by its Trigger.

---

## The Scope × Skill Matrix

Not all combinations are natural, but the matrix is open — invalid combinations degrade gracefully rather than failing.

```
                Platform    Cross-Plat   Knowledge   Research    Autonomous
                ────────    ──────────   ─────────   ────────    ──────────
Digest          ✓ Recap     ✓ Summary    ○           ─           ─
Prepare         ✓ Prep      ✓ Brief      ○           ─           ─
Monitor         ✓ Channel   ✓ Cross      ✓ Domain    ✓ Market    ─
                  Watch       Watch        Tracker     Watch
Research        ─           ─            ✓ Deep       ✓ Web       ✓ Auto
                                          Dive        Research     Research
Synthesize      ─           ✓ Status     ✓ Insight   ─           ✓ Proactive
Orchestrate     ─           ─            ─           ─           ✓ Coord
Act             ✓ Reply     ✓ Cross-     ─           ─           ✓ Auto
                  /Post       post                                  Action

✓ = natural fit, ○ = possible but uncommon, ─ = nonsensical
```

---

## Templates — User-Facing Convenience Layer

Templates are pre-configured Scope × Skill × Trigger combinations with sensible defaults. Users pick a template to start; the system sets the dimensions. Advanced users can override.

| Template Label | Scope | Skill | Default Trigger | Description |
|---------------|-------|-------|----------------|-------------|
| **Slack Recap** | platform | digest | recurring | Channel activity summary |
| **Gmail Digest** | platform | digest | recurring | Email digest by label |
| **Notion Summary** | platform | digest | recurring | Page and database activity summary |
| **Meeting Prep** | cross_platform | prepare | recurring | Calendar-driven briefing |
| **Work Summary** | cross_platform | synthesize | recurring | Cross-platform status update |
| **Channel Watch** | platform | monitor | proactive | Track changes in specific channels |
| **Domain Tracker** | knowledge | monitor | proactive | Longitudinal domain monitoring |
| **Deep Dive** | research | research | goal | Bounded investigation |
| **Proactive Insights** | autonomous | synthesize | proactive | Self-directed intelligence |
| **Coordinator** | autonomous | orchestrate | coordinator | Agent fleet management |
| **Custom** | (inferred) | (user selects) | (user selects) | Full manual configuration |

### Bootstrap templates (ADR-110, planned)

When a platform is connected and first sync completes, the bootstrap service auto-creates the matching digest template:

| Platform Connected | Template Created | Notes |
|-------------------|-----------------|-------|
| Slack | Slack Recap | All synced channels |
| Gmail | Gmail Digest | All synced labels |
| Notion | Notion Summary | All synced pages |
| Calendar | *(none)* | Meeting Prep requires cross-platform context — deferred to Composer (ADR-111) |

See [ADR-110](../adr/ADR-110-onboarding-bootstrap.md) for trigger points and idempotency rules. The Composer (ADR-111) extends bootstrap to medium-confidence templates (cross-platform, knowledge-scope, research-scope) via substrate assessment.

### Template bundles (future)

A single template can create multiple agents sharing the same source configuration:

- **"Slack Power User"** → creates Slack Recap (digest, recurring) + Channel Watch (monitor, proactive) + Slack Responder (act, reactive) — same channels, different skills

---

## Execution Strategies by Scope

```python
SCOPE_STRATEGIES = {
    "platform":       PlatformBoundStrategy,    # Content dump from single platform
    "cross_platform": CrossPlatformStrategy,    # Content dump from multiple platforms
    "knowledge":      KnowledgeStrategy,        # Workspace + /knowledge/ queries
    "research":       ResearchStrategy,         # Knowledge + WebSearch + documents
    "autonomous":     AutonomousStrategy,       # Full primitive set, agent-driven
}
```

### Context scoring (all scopes)

Before context injection, a three-signal scoring pass replaces chronological ordering with relevance ordering:

1. **Recency decay** (0.3–1.0) — full score within 24h, linear decay to floor over 7 days
2. **Signal boost** (1.0–2.0) — uses existing `platform_content.metadata` signals (user_authored, action_request, deadline, blocker)
3. **Instruction alignment** (0.5–1.5) — embedding similarity between `agent_instructions` and content

Scored content is injected with tier labels:
- Top 20% → `CRITICAL`
- Middle 50% → `RELEVANT`
- Bottom 30% → `BACKGROUND`

Zero new infrastructure — uses existing timestamps, metadata, and pgvector embeddings.

---

## Context Roll-Up Architecture

### The information hierarchy

```
Level 0: Raw Platform Data (platform_content, TTL-managed)
  ↓ Platform agents digest
Level 1: Curated Digests (/knowledge/digests/, persistent)
  ↓ Knowledge agents synthesize
Level 2: Synthesized Insights (/knowledge/insights/, persistent)
  ↓ Research agents analyze
Level 3: Deep Analysis (/knowledge/research/, persistent)
  ↓ User + TP consume
Level 4: User Knowledge (/memory/, persistent)
```

Each level is more compressed, more valuable per token, longer-lived, and more expensive to produce.

### Knowledge quality invariant

Knowledge entries have **provenance and are correctable**. The system treats accumulated knowledge as the *current best understanding*, subject to revision — never as infallible.

- User corrections **replace** the original (not append)
- Unreferenced entries decay in ranking (deprioritized, never hard-deleted)
- Superseded entries are archived (kept for provenance, not injected)
- Only explicit user deletion removes knowledge permanently

The moat is accumulation. Aggressive pruning destroys the moat. Ranking-based deprioritization preserves accumulation while keeping context quality high.

---

## Interoperability

### Protocol alignment

| Standard | YARNNN Mapping |
|----------|---------------|
| **A2A Agent Cards** | Skill → skills list. Scope → context/capabilities. Auto-generate Agent Cards from Scope + Skill. |
| **MCP Resources** | Each `/agents/{slug}/` workspace is a natural MCP resource scope. Skill primitives map to MCP tools. |
| **Claude Agent SDK** | Agent identity (instructions + memory + workspace) maps to SDK agent config. Skill → tool sets. |
| **OpenAI Assistants** | Scope → file_search/code_interpreter selection. Skill → instructions template. |
| **LangGraph / CrewAI** | Scope × Skill × Trigger is a superset of role + goal + backstory. |

### External invocation (MCP-first)

YARNNN gets invoked by web-based LLM providers (Claude, ChatGPT, Gemini) via MCP:

```
External LLM → MCP → YARNNN tools:
  - query_knowledge(query) → search accumulated knowledge
  - get_agent_output(agent_id) → read latest agent output
  - run_agent(agent_id) → trigger execution, return result
  - search_content(query, platform?) → search platform_content
```

YARNNN is the **knowledge and execution substrate**. The external LLM orchestrates; YARNNN provides accumulated intelligence.

---

## Horizontal Expansion

Each axis expands independently:

**New Scope:** `"api"` — agent reads from REST/GraphQL APIs
- New strategy: `APIStrategy`
- New primitives: `FetchAPI`, `QueryGraphQL`
- Skill and Trigger unchanged

**New Skill:** `"report"` — agent produces formatted, structured reports
- New prompt template and output validation
- Scope and Trigger unchanged

**New Trigger:** `"continuous"` — agent runs as a long-lived process
- New scheduler behavior
- Scope and Skill unchanged

This is the test of the taxonomy: each expansion touches one axis. The others remain stable.

---

## Migration from Current Type System

### Backfill map (agent_type → Scope × Skill)

| Current `agent_type` | Scope (inferred) | Skill | Default Trigger |
|---------------------|-------------------|-------|----------------|
| `digest` | platform (from sources) | digest | recurring |
| `brief` | cross_platform | prepare | recurring |
| `status` | cross_platform | synthesize | recurring |
| `watch` | knowledge or platform | monitor | proactive |
| `deep_research` | research | research | goal |
| `coordinator` | autonomous | orchestrate | coordinator |
| `custom` | (inferred from sources) | (inferred or custom) | (preserved) |

### Schema evolution

```sql
-- Phase 1: Add new fields alongside existing
ALTER TABLE agents ADD COLUMN scope TEXT;
ALTER TABLE agents ADD COLUMN skill TEXT;
-- agent_type remains for backwards compatibility during migration
-- mode is renamed conceptually to trigger (column name may stay for migration simplicity)

-- Phase 2: Backfill from agent_type
UPDATE agents SET scope = 'platform', skill = 'digest' WHERE agent_type = 'digest';
UPDATE agents SET scope = 'cross_platform', skill = 'prepare' WHERE agent_type = 'brief';
UPDATE agents SET scope = 'cross_platform', skill = 'synthesize' WHERE agent_type = 'status';
UPDATE agents SET scope = 'knowledge', skill = 'monitor' WHERE agent_type = 'watch';
UPDATE agents SET scope = 'research', skill = 'research' WHERE agent_type = 'deep_research';
UPDATE agents SET scope = 'autonomous', skill = 'orchestrate' WHERE agent_type = 'coordinator';
UPDATE agents SET scope = 'research', skill = 'research' WHERE agent_type = 'custom';

-- Phase 3: Execution pipeline reads scope + skill instead of agent_type
-- Phase 4: Drop agent_type column
```

---

## Key Files

| Concern | Location |
|---------|----------|
| This document | `docs/architecture/agent-framework.md` |
| Discourse & stress-testing | `docs/analysis/agent-taxonomy-first-principles-2026-03-12.md` |
| Execution strategies | `api/services/execution_strategies.py` |
| Primitive registry | `api/services/primitives/registry.py` |
| Type prompts (→ skill prompts) | `api/services/agent_pipeline.py` |
| Agent execution pipeline | `api/services/agent_execution.py` |
| Agent workspace | `api/services/workspace.py` |
| Frontend constants | `web/lib/constants/agents.ts` |

---

*This document is the canonical reference for agent taxonomy. For the full discourse that produced this framework, see the [analysis document](../analysis/agent-taxonomy-first-principles-2026-03-12.md). For the formal ADR, see ADR-109 (pending).*
