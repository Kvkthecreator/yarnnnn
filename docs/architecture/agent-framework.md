# Agent Framework: Scope × Role × Trigger

**Status:** Canonical
**Date:** 2026-03-12 (updated 2026-03-17: `skill` axis renamed to `role` per ADR-118 Resolved Decision #4 — eliminates naming overload with output gateway skills)
**Supersedes:** ADR-093 (7 purpose-first types), ADR-082 (8-type consolidation), ADR-044 (type reconceptualization)
**Related:**
- [ADR-092: Agent Intelligence & Mode Taxonomy](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) — mode system (preserved as Trigger axis)
- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — workspace filesystem, archetype-driven strategies
- [ADR-107: Knowledge Filesystem Architecture](../adr/ADR-107-knowledge-filesystem-architecture.md) — `/knowledge/` filesystem, three storage domains
- [ADR-116: Agent Identity & Inter-Agent Knowledge](../adr/ADR-116-agent-identity-inter-agent-knowledge.md) — agent discovery, cross-agent reading, agent cards, MCP exposure
- [ADR-101: Agent Intelligence Model](../adr/ADR-101-agent-intelligence-model.md) — four-layer knowledge model
- [ADR-104: Agent Instructions as Unified Targeting](../adr/ADR-104-agent-instructions-unified-targeting.md)
- [Analysis: Agent Taxonomy First Principles](../analysis/agent-taxonomy-first-principles-2026-03-12.md) — full discourse and stress-testing
- [Agent Presentation Principles](../design/AGENT-PRESENTATION-PRINCIPLES.md) — frontend: source-first grouping, card anatomy, creation flow

---

> **Relationship to FOUNDATIONS.md (2026-03-16):** This framework describes the **initial configuration** of an agent — its starting point. FOUNDATIONS.md Axiom 3 (Agents as Developing Entities) describes how agents evolve beyond this initial configuration over time: intentions become dynamic and multiple, capabilities are earned through feedback, autonomy graduates per-capability. The Scope × Role × Trigger taxonomy is the seed; the developmental trajectory is the growth. See [Agent Developmental Model Considerations](../analysis/agent-developmental-model-considerations.md) for the pre-decision analysis on developmental trajectory. See [ADR-092 revision notes](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) for reframing of proactive/coordinator modes as TP supervisory capabilities.

## Foundational Principle

Every agent answers two irreducible questions:

1. **What does the agent know?** → **Scope** — determines context strategy
2. **What does the agent do?** → **Role** — determines prompt, primitives, output shape

A third operational question governs lifecycle:

3. **When does the agent act?** → **Trigger** — determines scheduler behavior

An agent's **identity** is defined by Scope × Role. Its **lifecycle** is governed by Trigger. These are orthogonal: any Scope can combine with any Role, and any Scope × Role combination can run on any Trigger.

This framework is designed to survive any future agentic protocol. A2A Agent Cards, MCP resources, Claude Agent SDK, OpenAI Assistants — all express Scope (what the agent accesses), Role (what it does), and Trigger (when it runs). The specific values within each axis expand; the axes themselves are stable.

> **Naming note (ADR-118):** This axis was previously called "Skill." Renamed to "Role" to eliminate overload with output gateway skills (pptx, pdf, xlsx, etc.). "Role" = what an agent does (behavioral). "Skill" = what an agent can produce (output capability). See [ADR-118: Skills as Capability Layer](../adr/ADR-118-skills-as-capability-layer.md).

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
0 platform sources + research role         → research
0 platform sources + any other role        → knowledge
1 platform                                 → platform
2+ platforms                               → cross_platform
```

The user never thinks "platform scope" — they think "my Slack channels." Scope is a system-internal execution strategy classification.

### Knowledge-scope boundary (inception principle)

> **Implementation status (2026-03-16):** This boundary is documented as architectural intent but not yet enforced in code. Current execution strategies do not block `platform_content` access for knowledge-scope agents. Enforcement deferred to Phase 3 (ADR-106 workspace architecture). The design principle remains valid — the accumulation loop should be forced to work before boundaries are relaxed.

Knowledge-scope agents have **NO access** to `platform_content` at inception. If no accumulated knowledge exists, the agent explicitly reports this:

> "No accumulated knowledge available for this domain. Platform agents need to run first to build the knowledge base."

This creates an observable dependency: platform agents → `/knowledge/` → knowledge agents. The accumulation loop must be forced to work before boundaries are relaxed.

---

## Axis 2: Role — What the agent does

Role determines the agent's **prompt template**, **available primitives**, **output shape**, and **quality evaluation**.

| Role | Verb | Output | Character |
|-------|------|--------|-----------|
| **digest** | Compress, summarize | Document (recap, summary) | Lossy reduction, recency-weighted |
| **prepare** | Anticipate, assemble | Document (brief, prep) | Event-driven, anticipatory, time-sensitive |
| **monitor** | Track, diff, alert | Document or notification | Differential against baseline/thesis, stateful |
| **research** | Investigate, analyze | Document (report, analysis) | Exploratory, goal-bounded, depth-first |
| **synthesize** | Connect, derive insight | Document (insight, thesis) | Cross-source, pattern recognition, longitudinal |
| **act** | Execute, respond, post | Platform action (reply, send, update, post) | Agentic, requires permissions, approval-gated (future) |

> **Removed: `orchestrate`** (2026-03-18). The orchestrate role described coordination that is actually performed by TP (chat) and Composer (cron service) — neither of which is an agent in the database. No orchestrate agent was ever instantiated in code. Agent fleet management is a backend infrastructure concern (Composer, ADR-111), not an agent role. If domain-specific fleet coordination is needed in the future, it can be re-added. See also: the `coordinator` trigger (below) remains valid as a scheduling mode.

### One agent, one seed role — duties expand (ADR-117 Phase 3)

An agent's **role** (its seed identity) never changes. A digest agent is always a digest agent. But senior agents earn **duties** — additional responsibilities within pre-configured career tracks (role portfolios).

Multi-role requests at inception still decompose into multiple agents. But a mature digest agent can earn a monitor duty, gaining alert capabilities within the same domain context. This preserves accumulated workspace knowledge instead of fragmenting it across separate agents.

- The **role** determines the agent's core identity, initial primitives, and prompt template
- **Duties** expand at senior seniority, adding new trigger × role combinations to the agent
- Each duty run uses the duty's role for prompt selection, SKILL.md injection, and primitive gating
- **Role portfolios** are pre-configured and deterministic — Composer promotes along known tracks, never invents combinations

See: [Agent Development: Role Portfolios & Duties](#agent-development-role-portfolios--duties) below.

### Primitive gating by role

```python
ROLE_PRIMITIVES = {
    "digest":       ["Search", "Read", "RefreshPlatformContent", "QueryKnowledge"],
    "prepare":      ["Search", "Read", "RefreshPlatformContent", "QueryKnowledge", "WebSearch"],
    "monitor":      ["Search", "Read", "RefreshPlatformContent", "QueryKnowledge", "ReadWorkspace", "WriteWorkspace"],
    "research":     ["Search", "Read", "RefreshPlatformContent", "QueryKnowledge", "WebSearch", "ReadWorkspace", "WriteWorkspace", "SearchWorkspace"],
    "synthesize":   ["Search", "Read", "QueryKnowledge", "ReadWorkspace", "WriteWorkspace", "SearchWorkspace", "DiscoverAgents", "ReadAgentContext"],
    "act":          ["Search", "Read", "QueryKnowledge", "SlackReply", "SlackPost", "SendEmail", "UpdateNotionPage"],  # future, gated by ActionPolicy
}
# DiscoverAgents, ReadAgentContext: ADR-116 — inter-agent discovery and cross-agent workspace reading
# RuntimeDispatch: ADR-118 — added to all roles when agent has authorized skills in AGENT.md
```

### Action capability is policy, not dimension

Capability level (read-only → monitored → autonomous) is NOT a separate axis. It is a **graduated permission model** (ActionPolicy) applied to the role's primitive set:

```python
class ActionPolicy:
    """Per-agent permission model for write primitives.
    Derivative of Role — not a taxonomic dimension."""

    approval_mode: Literal["staged", "auto"]  # default: staged
    rate_limit: Optional[int]                  # max actions per hour
    allowed_actions: list[str]                 # e.g., ["SlackReply", "SendEmail"]
    confidence_threshold: Optional[float]      # auto-approve above this (0.0-1.0)
```

An act-role agent with `auto_approve: false` operates at "staged" level. Same agent with `auto_approve: true` operates at "autonomous" level. That's a policy toggle, not a taxonomy change.

---

## Axis 3: Trigger — When the agent acts

Trigger determines **scheduler behavior** and **execution lifecycle**. Preserved from ADR-092's mode taxonomy — renamed for industry alignment.

| Trigger | Character | Execution | Memory Role |
|---------|-----------|-----------|-------------|
| **recurring** | Clockwork | Fixed schedule, always runs on time | Learned preferences, format patterns |
| **goal** | Project | Fixed schedule, stops when objective complete | Goal progress, milestone tracking |
| **reactive** | On-call | Event-driven, accumulates observations, generates at threshold | Agent-authored event observations |
| **proactive** | Living specialist | Periodic self-review, generates when conditions warrant | Self-authored domain review log |
| **coordinator** | Meta-specialist | Periodic review via Composer (ADR-111) | Review log + lifecycle signals |

> **Note on `coordinator` trigger**: This trigger mode subjects the agent to Composer's supervisory review cycle. Composer (a backend service, not an agent) manages fleet-level decisions: creating agents, pausing underperformers, proposing projects. The coordinator trigger is how an agent signals that it participates in this supervisory loop — it does NOT mean the agent itself orchestrates other agents.

Trigger is important but operational — it governs scheduling, not identity. An agent's character is defined by its Scope × Role; its lifecycle is governed by its Trigger.

---

## The Scope × Role Matrix

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
Act             ✓ Reply     ✓ Cross-     ─           ─           ✓ Auto
                  /Post       post                                  Action

✓ = natural fit, ○ = possible but uncommon, ─ = nonsensical
```

---

## Templates — User-Facing Convenience Layer

Templates are pre-configured Scope × Role × Trigger combinations with sensible defaults. Users pick a template to start; the system sets the dimensions. Advanced users can override.

| Template Label | Scope | Role | Default Trigger | Description |
|---------------|-------|-------|----------------|-------------|
| **Slack Recap** | platform | digest | recurring | Channel activity summary |
| **Gmail Recap** | platform | digest | recurring | Email recap by label |
| **Notion Recap** | platform | digest | recurring | Page and database activity recap |
| **Meeting Prep** | cross_platform | prepare | recurring | Calendar-driven briefing |
| **Work Summary** | cross_platform | synthesize | recurring | Cross-platform status update |
| **Channel Watch** | platform | monitor | proactive | Track changes in specific channels |
| **Domain Tracker** | knowledge | monitor | proactive | Longitudinal domain monitoring |
| **Deep Dive** | research | research | goal | Bounded investigation |
| **Proactive Insights** | autonomous | synthesize | proactive | Self-directed intelligence |
| **Custom** | (inferred) | (user selects) | (user selects) | Full manual configuration |

### Bootstrap templates (ADR-110, planned)

When a platform is connected and first sync completes, the bootstrap service auto-creates the matching digest template:

| Platform Connected | Project Created | Members Created | Notes |
|-------------------|----------------|-----------------|-------|
| Slack | Slack Recap | Slack Agent + PM | All synced channels |
| Gmail | Gmail Recap | Gmail Agent + PM | All synced labels |
| Notion | Notion Recap | Notion Agent + PM | All synced pages |
| Calendar | *(none)* | Meeting Prep requires cross-platform context — deferred to Composer (ADR-111) |

See [ADR-110](../adr/ADR-110-onboarding-bootstrap.md) for trigger points and idempotency rules. The Composer (ADR-111) extends bootstrap to medium-confidence templates (cross-platform, knowledge-scope, research-scope) via substrate assessment.

### Template bundles (future)

A single template can create multiple agents sharing the same source configuration:

- **"Slack Power User"** → creates Slack Recap (digest, recurring) + Channel Watch (monitor, proactive) + Slack Responder (act, reactive) — same channels, different skills

---

## User-Facing Agent Identity

The Scope × Role × Trigger taxonomy is internal. Users never see "platform-scoped digest-role recurring-trigger agent." They see **workers with job titles** that produce **deliverables they care about**.

### The framing principle

Agents are presented as **employees with jobs**, not technical configurations. The job title is the primary identity. The user thinks: "my Slack agent handles my Slack," "my Meeting Prep gets me ready for calls," "my Market Researcher investigates competitors." The taxonomy drives execution behind the scenes; the job title drives the user's mental model.

### How job titles map to the taxonomy

| User sees (job title) | Internal (Scope × Role) | Why this framing works |
|---|---|---|
| **Your Slack Agent** | platform + digest | Platform IS the job for simple agents |
| **Your Gmail Agent** | platform + digest | Same — platform name carries all context |
| **Your Notion Agent** | platform + digest | Same pattern |
| **Your Meeting Prep** | cross_platform + prepare | The deliverable IS the job |
| **Your Weekly Brief** | cross_platform + synthesize | The recurring output IS the job |
| **Your Channel Watch** | platform + monitor | The domain being watched IS the job |
| **Your Competitor Watch** | knowledge + monitor | Same — domain-named |
| **Your Market Researcher** | research + research | The investigation IS the job |
| **Your Deep Dive: [topic]** | research + research (goal) | Topic-scoped job |
| **Your Chief of Staff** | autonomous + synthesize | The cross-cutting judgment IS the job |

### Platform agents: 1:1 platform to agent

For platform-scoped agents, the platform IS the identity. "Your Slack Agent" is immediately understood. Users don't need to know it's a digest agent — it handles their Slack. Bootstrap (ADR-110) creates these automatically: connect Slack → get "Your Slack Agent."

As a platform agent matures and gains output skills (ADR-118), it might graduate from text-only to producing a PDF weekly recap or a chart of activity trends. The identity stays "Your Slack Agent" — the deliverable gets richer, but the job hasn't changed.

### Cross-cutting agents: job-framed, not scope-framed

For agents that read from multiple platforms or accumulated knowledge, the identity is the **job they do** or the **deliverable they produce**, not the technical scope:

- "Your Weekly Brief" (not "Your Cross-Platform Synthesize Agent")
- "Your Competitor Watch" (not "Your Knowledge-Scope Monitor Agent")
- "Your Market Researcher" (not "Your Research-Scope Research Agent")

The user describes a need ("I need a weekly brief for my Monday meetings"), Composer creates an agent with the right scope, role, and trigger, and the agent's title reflects the job — not the configuration.

### Output skills don't change the identity

An agent's authorized output skills (pptx, pdf, xlsx, chart) are its **toolbox**, not its identity. A research agent that produces a PDF report and one that produces a PDF + spreadsheet + presentation are both "Your Market Researcher." The tools are assigned per-agent in AGENT.md by Composer based on what the job requires. Users see the deliverables; they don't configure the toolbox.

This is the video editor analogy: a video editor's job is editing video, but they might also produce thumbnails, transcripts, or social clips. The job title stays the same; the output types vary based on what's needed.

### Projects: prominent but optional

Projects (ADR-119) are a first-class concept — prominent in the dashboard once introduced, and the natural container for composed multi-agent value. But they are NOT mandatory. Standalone agents are valid and are the bootstrap entry point.

The product surfaces **both** projects and standalone agents:
- **Projects** appear at the top of the dashboard as the higher-value unit. "Your Monday Brief" with 3 contributing agents producing an assembled deck.
- **Standalone agents** appear below as individual workers. "Your Slack Agent" producing a weekly recap.

An agent can be standalone AND contribute to projects simultaneously. Its workspace is its own; projects reference its outputs. Standalone agents that aren't part of any project are a visual nudge: "these could be more powerful in a project."

Projects are introduced post-onboarding — either by Composer suggestion ("Your Slack and Gmail agents could combine into a Monday Brief") or user request via chat. Bootstrap creates standalone agents for the simplest possible entry point.

For full product design: see [Projects Product Direction](../design/PROJECTS-PRODUCT-DIRECTION.md).

### Progression: how identity evolves

| Stage | Seniority | What happens | User sees |
|---|---|---|---|
| **Bootstrap** | New | User connects Slack → system creates digest agent | "Your Slack Agent" appears on dashboard |
| **First value** | New | Agent runs, produces text recap | Email: "Here's your Slack recap" |
| **Earning trust** | New → Associate | 5+ runs, 60%+ approval | Agent reliability established |
| **Skill graduation** | Associate | Composer authorizes PDF skill based on seniority | Email now includes a PDF attachment |
| **Duty promotion** | Senior | 10+ runs, 80%+ approval → Composer adds monitor duty | Agent now watches for escalations + digests |
| **Job agent** | New | User asks "I need a weekly brief" → Composer creates cross-platform agent | "Your Weekly Brief" appears as standalone agent |
| **Project** | Any | User asks or Composer suggests combining agents → project created | "Your Monday Brief" project appears above agents on dashboard |
| **Composition** | Any | Project assembles outputs from contributing agents | Assembled deck/report delivered, standalone agents contribute silently |

At every stage, the user sees workers with job titles and projects with deliverables. The technical complexity (scope inference, role selection, skill authorization, duty promotion, project assembly) is invisible.

---

## Agent Development: Role Portfolios & Duties (ADR-117 Phase 3)

### Seniority Levels

Seniority is **derived** from feedback history, not stored:

| Level | Threshold | Employee analogy |
|---|---|---|
| **New** | Default (< 5 runs or < 60% approval) | Just hired, learning the ropes |
| **Associate** | ≥ 5 runs AND ≥ 60% approval | Promoted, trusted, consistent |
| **Senior** | ≥ 10 runs AND ≥ 80% approval | Ready for expanded responsibilities |

Classification: `classify_seniority()` in `api/services/agent_framework.py`.

### Role Portfolios

Pre-configured career tracks. Deterministic, versioned, testable. Composer promotes along known tracks — never invents combinations.

| Seed Role | New | Associate | Senior (gains) |
|---|---|---|---|
| **digest** | digest (recurring) | digest (recurring) | + **monitor** (reactive) |
| **monitor** | monitor (recurring) | monitor (recurring) | + **act** (reactive, future) |
| **synthesize** | synthesize (recurring) | synthesize (recurring) | + **research** (goal) |
| **research** | research (goal) | research (goal) | + **monitor** (proactive) |
| **prepare** | prepare (recurring) | prepare (recurring) | (no expansion) |
| **pm** | pm (proactive) | pm (proactive) | (no expansion) |
| **custom** | custom (recurring) | custom (recurring) | (no expansion) |

Registry: `ROLE_PORTFOLIOS` in `api/services/agent_framework.py`.

### Duty Mechanics

- **Storage**: `agents.duties` JSONB column + `/agents/{slug}/duties/{duty}.md` workspace files
- **Execution**: Each duty run resolves `effective_role` from the duty, overriding the seed role for prompt selection, SKILL.md injection, and primitive gating
- **Scheduling**: `resolve_due_duties()` returns all active duties; scheduler iterates and dispatches each with `trigger_context.duty`
- **Tagging**: `agent_runs.duty_name` records which duty produced the run
- **Backwards compat**: `duties=null` → synthetic single duty matching seed role

### Promotion Flow

1. Composer heartbeat detects senior agent with available duty promotion
2. `_execute_promote_duty()` validates against `ROLE_PORTFOLIOS`
3. Writes: `agents.duties` JSONB + workspace `duties/{duty}.md` + AGENT.md update
4. Activity event: `duty_promoted` in `activity_log`
5. Next scheduler cycle picks up the new duty

### Delivery Model — Agents Produce, Projects Deliver

Agents write output to their workspace. Projects deliver to the user. PM coordinates delivery timing based on project cadence and contribution freshness.

- **Single-agent projects**: PM passthrough — one contribution in, one output delivered.
- **Multi-agent projects**: PM assembles contributions, delivers composed output.
- **No direct agent delivery**: `destination=None` on all member agents. Delivery configuration lives on PROJECT.md.
- **PM for all projects**: Every project gets a PM at scaffold time, no exceptions. PM agents are project infrastructure, excluded from tier agent limits.

See [PROJECT-DELIVERY-MODEL.md](../design/PROJECT-DELIVERY-MODEL.md) for full design rationale.

> **Supersedes**: Previous "All Direct" model (N+1 deliveries). Migration path: dual-write during transition, then cut over.

---

## Output Skills (ADR-118)

Skills are the output gateway's capability library. When a duty fires, its role determines RuntimeDispatch access:

| Duty Role | Output Skills | Example |
|---|---|---|
| digest | ❌ text only | Slack Recap email |
| prepare | ❌ text only | Meeting briefing |
| monitor | ✅ all 8 skills | Alert with chart |
| research | ✅ all 8 skills | Report with visualizations |
| synthesize | ✅ all 8 skills | Cross-platform deck |
| act | ❌ platform actions (future) | Slack reply |
| pm | ❌ text only | Assembly coordination |
| custom | ✅ all 8 skills | User-defined |

**8 available skills**: pdf, pptx, xlsx, chart, mermaid, html, data_export, image

Gate: `SKILL_ENABLED_ROLES` in `api/services/agent_framework.py`. When a duty's role is in this set, the agent gets SKILL.md injection and RuntimeDispatch access for that run.

Key insight: A digest agent's **monitor duty** gets skill access; its **digest duty** does not. Per-run, not per-agent.

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
| **A2A Agent Cards** | Role → skills list. Scope → context/capabilities. Auto-generate Agent Cards from Scope + Role. |
| **MCP Resources** | Each `/agents/{slug}/` workspace is a natural MCP resource scope. Role primitives map to MCP tools. |
| **Claude Agent SDK** | Agent identity (instructions + memory + workspace) maps to SDK agent config. Role → tool sets. |
| **OpenAI Assistants** | Scope → file_search/code_interpreter selection. Role → instructions template. |
| **LangGraph / CrewAI** | Scope × Role × Trigger is a superset of role + goal + backstory. |

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
- Role and Trigger unchanged

**New Role:** `"report"` — agent produces formatted, structured reports
- New prompt template and output validation
- Scope and Trigger unchanged

**New Trigger:** `"continuous"` — agent runs as a long-lived process
- New scheduler behavior
- Scope and Role unchanged

This is the test of the taxonomy: each expansion touches one axis. The others remain stable.

---

## Migration from Current Type System

### Backfill map (agent_type → Scope × Role)

| Current `agent_type` | Scope (inferred) | Role | Default Trigger |
|---------------------|-------------------|-------|----------------|
| `digest` | platform (from sources) | digest | recurring |
| `brief` | cross_platform | prepare | recurring |
| `status` | cross_platform | synthesize | recurring |
| `watch` | knowledge or platform | monitor | proactive |
| `deep_research` | research | research | goal |
| `coordinator` | autonomous | synthesize | coordinator |
| `custom` | (inferred from sources) | (inferred or custom) | (preserved) |

### Schema evolution

```sql
-- Phase 1: Add new fields alongside existing
ALTER TABLE agents ADD COLUMN scope TEXT;
ALTER TABLE agents ADD COLUMN role TEXT;  -- was: skill, renamed per ADR-118 RD#4
-- agent_type remains for backwards compatibility during migration
-- mode is renamed conceptually to trigger (column name may stay for migration simplicity)

-- Phase 2: Backfill from agent_type
UPDATE agents SET scope = 'platform', role = 'digest' WHERE agent_type = 'digest';
UPDATE agents SET scope = 'cross_platform', role = 'prepare' WHERE agent_type = 'brief';
UPDATE agents SET scope = 'cross_platform', role = 'synthesize' WHERE agent_type = 'status';
UPDATE agents SET scope = 'knowledge', role = 'monitor' WHERE agent_type = 'watch';
UPDATE agents SET scope = 'research', role = 'research' WHERE agent_type = 'deep_research';
UPDATE agents SET scope = 'autonomous', role = 'synthesize' WHERE agent_type = 'coordinator';
UPDATE agents SET scope = 'research', role = 'research' WHERE agent_type = 'custom';

-- Phase 3: Execution pipeline reads scope + role instead of agent_type
-- Phase 4: Drop agent_type column
```

---

## Key Files

| Concern | Location |
|---------|----------|
| This document | `docs/architecture/agent-framework.md` |
| Role portfolios & seniority | `api/services/agent_framework.py` (ADR-117 Phase 3) |
| Discourse & stress-testing | `docs/analysis/agent-taxonomy-first-principles-2026-03-12.md` |
| Execution strategies | `api/services/execution_strategies.py` |
| Primitive registry | `api/services/primitives/registry.py` |
| Type prompts (→ role prompts) | `api/services/agent_pipeline.py` |
| Agent execution pipeline | `api/services/agent_execution.py` |
| Agent workspace | `api/services/workspace.py` |
| Composer (duty promotion) | `api/services/composer.py` |
| Output gateway skills | `render/skills/` (ADR-118) |
| Frontend constants | `web/lib/constants/agents.ts` |

---

*This document is the canonical reference for agent taxonomy. For the full discourse that produced this framework, see the [analysis document](../analysis/agent-taxonomy-first-principles-2026-03-12.md). For the formal ADR, see ADR-109 (pending).*
