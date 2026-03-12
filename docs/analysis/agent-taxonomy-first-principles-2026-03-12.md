# Agent Taxonomy: First-Principles Reassessment

**Date:** 2026-03-12
**Authors:** Kevin Kim, Claude (analysis)
**Status:** Active discourse — not yet an ADR
**Context:** Post ADR-103 (agentic reframe), ADR-092 (mode taxonomy), ADR-106 (workspace architecture)

---

## Motivation

With the terminology migration (ADR-103) complete and workspace architecture (ADR-106) in progress, the current 7-type system (digest, brief, status, watch, deep_research, coordinator, custom) needs reassessment. These types were designed as purpose-first labels (ADR-093), but they conflate two fundamentally different dimensions and don't accommodate the platform's trajectory toward agentic actions, cross-agent orchestration, and interoperability.

The goal: a taxonomy so architecturally clean that it remains valid regardless of what future agentic frameworks emerge — horizontally extensible, interoperable, and future-proof.

---

## Part 1: The Core Tension in Current Types

### What the current types conflate

Each of the 7 types implicitly encodes multiple independent decisions:

| Type | Context source | Work behavior | Output shape | Implicit binding |
|------|---------------|---------------|-------------|-----------------|
| `digest` | Single platform | Summarize | Document | platform_bound |
| `brief` | Calendar + all platforms | Anticipate | Document | cross_platform |
| `status` | Multiple platforms | Synthesize | Document | cross_platform |
| `watch` | Platforms + knowledge | Monitor/diff | Document | cross_platform |
| `deep_research` | Platforms + web | Investigate | Document | hybrid |
| `coordinator` | Knowledge + agents | Orchestrate | Agent actions | autonomous |
| `custom` | User-defined | User-defined | Document | hybrid |

The problem: adding a new capability (e.g., "reply on Slack") requires either:
- Creating a new type (type explosion: `slack_responder`, `email_drafter`, `notion_updater`...)
- Overloading an existing type (what is a `digest` that also replies?)

Neither scales. The type system should be **compositional**, not enumerative.

### The `type_classification.binding` attempt

ADR-044 introduced `binding` (platform_bound, cross_platform, research, hybrid) as a secondary dimension. This was the right instinct — separating context source from purpose — but it's:
- Auto-inferred from type, not independently configurable
- Missing the knowledge-native domain (agents that reason over accumulated outputs)
- Not exposed as a first-class concept in the UI or execution pipeline

---

## Part 2: Two Orthogonal Axes

### Axis 1: Context Domain — Where the agent sources intelligence

| Domain | Source | Execution Strategy | Character |
|--------|--------|-------------------|-----------|
| **Platform** | Specific sources from one platform (Slack channels, Gmail labels, Notion pages, Calendar) | PlatformBoundStrategy → content dump | High-fidelity, recency-driven, bounded |
| **Cross-Platform** | Sources from multiple connected platforms | CrossPlatformStrategy → multi-platform dump | Broader, requires synthesis and prioritization |
| **Knowledge** | Accumulated `/knowledge/` filesystem + workspace files + agent outputs | AnalystStrategy → workspace-driven queries | Longitudinal, compounds over time, the moat |
| **Research** | Web search, external APIs, uploaded documents + knowledge grounding | ResearchStrategy → primitives-driven | Unbounded scope, requires scoping via instructions |
| **Autonomous** | Agent selects own context strategy dynamically | Agent-driven via full primitive set | Maximum flexibility, highest intelligence requirement |

**Key insight:** Platform and Cross-Platform are **dump-based** (context gathered before LLM call). Knowledge, Research, and Autonomous are **tool-driven** (agent queries what it needs during execution). This maps directly to the Reporter vs. Analyst archetype split in ADR-106.

### Axis 2: Work Pattern — What the agent does with intelligence

| Pattern | Verb | Output | Character |
|---------|------|--------|-----------|
| **Digest** | Compress, summarize | Document (recap, summary) | Lossy reduction, recency-weighted |
| **Prepare** | Anticipate, assemble | Document (brief, prep) | Event-driven, anticipatory, time-sensitive |
| **Monitor** | Track, diff, alert | Document or notification | Differential against baseline/thesis, stateful |
| **Research** | Investigate, analyze | Document (report, analysis) | Exploratory, goal-bounded, depth-first |
| **Synthesize** | Connect, derive insight | Document (insight, thesis) | Cross-source, pattern recognition, longitudinal |
| **Orchestrate** | Coordinate, dispatch | Agent actions (create/trigger agents) | Meta-level, reads agent outputs, manages fleet |
| **Act** | Execute, respond, post | Platform action (reply, send, update, post) | Agentic, requires permissions, approval-gated |

**Key insight:** Every pattern except Act produces a document. Act produces side effects in external systems. This is the fundamental capability boundary that needs architectural support.

### The Matrix

Agents are Domain × Pattern combinations. Not all cells are valid or useful:

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

## Part 3: The Action Layer — Capability as Policy, Not Dimension

### Why actions are not a separate type

Today, all agents follow: read → reason → write document. The output is always content delivered somewhere (email, Slack message, Notion page). But the delivery is **passive** — the agent produces a document, the delivery layer routes it.

Actions are fundamentally different:
- **Reply to a Slack thread** requires thread context + appropriate tone + timing
- **Send an email** requires recipient selection + subject + body composition
- **Update a Notion page** requires understanding page structure + targeted edits
- **Post to social media** requires platform-specific formatting + scheduling

These require **write-capable platform primitives** (not just read-only ones) and a **trust/approval model**.

### Capability level is derivative, not a dimension

**Key insight (discourse resolution, 2026-03-12):** Capability level (read-only → monitored → autonomous) is NOT an independent axis. It is a **graduated permission model applied to the agent's primitive set**, which is itself determined by the Skill (Work Pattern).

Rationale:
- A Monitor-skill agent always does the same cognitive work (track, diff, detect). Whether it writes a document, sends a notification, or replies in Slack depends on **which output primitives are enabled** — that's a permission on the Skill, not a separate dimension.
- Adding a 4th dimension (Scope × Skill × Trigger × Level) creates a cognitively impossible configuration space for users.
- The Skill already determines available tools. Capability level is an RBAC-like policy filter on those tools — closer to a trust setting than a taxonomic category.

Practically: an Act-skill agent with `auto_approve: false` operates at "staged" level. The same agent with `auto_approve: true` operates at "autonomous" level. That's a policy toggle, not a taxonomy change. The agent's identity, context strategy, and reasoning are identical.

### Capability as agent policy

```python
class ActionPolicy:
    """Per-agent permission model for write primitives.
    Derivative of Skill — not a taxonomic dimension."""

    approval_mode: Literal["staged", "auto"]  # default: staged
    rate_limit: Optional[int]                  # max actions per hour
    allowed_actions: list[str]                 # e.g., ["SlackReply", "SendEmail"]
    confidence_threshold: Optional[float]      # auto-approve above this (0.0-1.0)
```

### Architectural requirements for actions

1. **Write primitives**: `SlackReply`, `SlackPost`, `SendEmail`, `UpdateNotionPage`, `PostContent`
2. **Action queue**: proposed actions stored with context, awaiting approval
3. **Approval policy**: per-agent ActionPolicy (staged/auto per primitive type)
4. **Audit trail**: every action logged with provenance (what context triggered it, what the agent reasoned)
5. **Rate limiting**: prevent runaway agents from spamming platforms
6. **Rollback**: where possible, ability to undo actions (delete message, retract email)

---

## Part 4: Context Prioritization — The Missing Layer

### The current problem

Today, context injection is binary:
- **Reporters** (dump-based): receive ALL content from configured sources, chronologically ordered. No relevance scoring, no importance ranking. A 200-message Slack dump treats a CEO's strategic message the same as a bot notification.
- **Reasoning agents** (tool-driven): receive workspace context + primitives. They must search for relevant content themselves. No scaffolding, no "here's what's most relevant to start with."

### What's needed: a context scoring step

Before the agent LLM call, a lightweight scoring pass:

```
1. Resolve candidate content (from platform_content, workspace_files, knowledge base)
2. Score each item against:
   - Agent instructions (semantic similarity)
   - Agent thesis/domain (if exists)
   - Recency (decay curve, platform-specific)
   - Signal metadata (URGENT, DECISION, STALLED — already in platform_content)
   - User-authored flag (content by the user > content by others)
   - Prior run references (content the agent has used before)
3. Rank and select top-N within context budget
4. Format with importance tiers:
   - CRITICAL: high-signal, instruction-aligned, recent
   - RELEVANT: moderate signal, topically related
   - BACKGROUND: low signal but may provide context
```

This scoring happens **outside the LLM** (embedding similarity + heuristic signals), making it fast and cheap. It serves all agents:
- Reporters get better content in less space
- Reasoning agents get a curated starting point before they start querying
- Monitors get a pre-diffed view (what changed since last run)

### Context budget management

Different patterns need different context allocations:

| Pattern | Context Budget Strategy |
|---------|----------------------|
| Digest | High volume, shallow depth — many items, brief per item |
| Prepare | Targeted — only items related to upcoming event |
| Monitor | Differential — previous baseline + changes only |
| Research | Seed + expand — small curated seed, agent expands via tools |
| Synthesize | Longitudinal — agent outputs over time + current platform state |
| Orchestrate | Meta — agent statuses, recent outputs, system state |
| Act | Trigger-focused — the specific context that triggered the action |

---

## Part 5: Platform-Specific Agent Considerations

### The Slack question: digest vs. monitor vs. act

A Slack-focused agent configured with channels #engineering and #product could:

1. **Digest pattern**: "Here's what happened in your channels this week" — summarize all messages, highlight hot threads
2. **Monitor pattern**: "Alert when someone mentions a deadline or blocker" — track against keywords/patterns, output only when triggered
3. **Act pattern**: "Reply to @mentions in #support with helpful context" — read thread, compose reply, send (with approval)

These are NOT three different agents. They are **the same agent with different work patterns**. The source configuration (which channels) is shared. What differs:
- The prompt template (summarize vs. diff vs. respond)
- The available primitives (read-only vs. read-write)
- The output shape (document vs. notification vs. platform action)
- The trigger model (scheduled vs. threshold vs. event-driven)

**Recommendation:** Allow a single agent to have multiple work patterns, or more practically, make it trivial to create multiple agents sharing the same source configuration. The latter is simpler and maintains the "one agent, one job" principle from ADR-103.

### Multi-channel targeting

Current concern: "multiple slack channel selection then also reply on behalf could be additive not necessarily separate."

This is correct. Channel selection is a **context domain** concern, not a **work pattern** concern. An agent watching 5 channels for digest purposes uses the same source config as an agent watching those 5 channels for action purposes. The targeting granularity question (broad digest vs. targeted action) is resolved by **instructions**, not by source configuration.

Example:
- Agent "Eng Recap" — sources: [#engineering, #product, #incidents], pattern: digest, mode: recurring weekly
- Agent "Support Responder" — sources: [#support, #help], pattern: act, mode: reactive, instructions: "Reply to questions about our API with helpful context from documentation"

Same source picker, same channel selection UX. Different behavior via pattern + instructions.

---

## Part 6: Knowledge Synthesis vs. Platform Synthesis

### The distinction

| | Platform Synthesis | Knowledge Synthesis |
|---|-------------------|-------------------|
| **Reads from** | `platform_content` (ephemeral, TTL-managed) | `/knowledge/` filesystem (persistent, accumulated) |
| **Time horizon** | This period (day/week/month) | All time (longitudinal) |
| **Question** | "What happened?" | "What do we know?" |
| **Value** | Saves time reading raw content | Reveals patterns invisible in any single period |
| **Stickiness** | Moderate — any summarizer can do this | High — accumulated knowledge is the moat |
| **Current type** | `status` (cross-platform) | Not clearly represented |
| **Examples** | Weekly work summary | "How has the product roadmap evolved over the past month?", "What themes keep recurring in #engineering?" |

### Why this matters for YARNNN's moat

Platform synthesis is a commodity. Any tool with API access can summarize your Slack messages. It's necessary but not defensible.

Knowledge synthesis is the moat. It requires:
1. **Accumulated context** — weeks/months of digests, research, insights stored in `/knowledge/`
2. **Agent memory** — the agent's evolving understanding of what matters
3. **Cross-agent awareness** — synthesizing outputs from multiple specialized agents
4. **Longitudinal reasoning** — detecting patterns that span multiple time periods

This is why the Knowledge context domain is architecturally distinct. An agent operating in this domain reads from `/knowledge/`, not from `platform_content`. Its context is curated intelligence, not raw platform data. And its outputs feed back into `/knowledge/`, creating the recursive accumulation loop.

### The yarnnn content recursion

```
Platform Sync → platform_content (ephemeral)
    ↓
Platform Agent (digest) → /knowledge/digests/slack-eng-2026-03-12.md (persistent)
    ↓
Knowledge Agent (synthesize) → /knowledge/insights/eng-trends-march.md (persistent)
    ↓
Knowledge Agent (research) reads prior insights → /knowledge/research/eng-productivity-analysis.md
    ↓
TP or User queries /knowledge/ → sees compounding intelligence
```

Each layer adds value. Raw Slack messages expire in 14 days. But the digest persists. The synthesis of digests persists. The research grounded in those syntheses persists. The knowledge base grows richer over time, and agents operating at the Knowledge domain level get better context with each cycle.

---

## Part 7: Proposed Architecture (v2) — Scope × Skill × Trigger

### Industry-aligned naming (discourse resolution, 2026-03-12)

Analysis of naming conventions across A2A, MCP, Claude Agent SDK, CrewAI, AutoGen, and OpenAI Assistants converges on:

| Internal concept | User-facing term | Industry alignment |
|-----------------|-----------------|-------------------|
| Context Domain | **Scope** | MCP resource scopes, A2A context, OAuth scopes |
| Work Pattern | **Skill** | A2A Agent Card skills, CrewAI task, Claude SDK tools |
| Execution Mode | **Trigger** | Event-driven architecture, cron systems, webhook terminology |

These terms are intuitive for users ("What's your agent's scope?", "What skill does it use?", "What triggers it?") and map directly to protocol-level concepts.

### Two-dimensional agent definition + trigger

```python
class Scope(str, Enum):
    """What the agent has access to — determines context strategy."""
    PLATFORM = "platform"           # Specific sources from one platform
    CROSS_PLATFORM = "cross_platform"  # Sources from multiple platforms
    KNOWLEDGE = "knowledge"         # Accumulated /knowledge/ + workspace
    RESEARCH = "research"           # Web + knowledge grounding
    AUTONOMOUS = "autonomous"       # Agent selects own context strategy

class Skill(str, Enum):
    """What the agent does — determines prompt, primitives, output shape."""
    DIGEST = "digest"               # Compress and summarize
    PREPARE = "prepare"             # Anticipate and assemble (event-driven)
    MONITOR = "monitor"             # Track against baseline, detect changes
    RESEARCH = "research"           # Investigate with depth
    SYNTHESIZE = "synthesize"       # Cross-source analysis and insight
    ORCHESTRATE = "orchestrate"     # Coordinate other agents
    ACT = "act"                     # Take actions (future, permission-gated)

class Trigger(str, Enum):
    """When the agent runs — determines scheduler behavior."""
    RECURRING = "recurring"         # Clock-driven, fixed cadence
    GOAL = "goal"                   # Bounded task, completes when done
    REACTIVE = "reactive"           # Event-driven, threshold-triggered
    PROACTIVE = "proactive"         # Self-initiating, review-then-decide
    COORDINATOR = "coordinator"     # Meta-agent, dispatches others
```

An agent is: **Scope × Skill** (the two orthogonal axes) + **Trigger** (when) + **instructions** + **sources** + **schedule** + **action_policy** (if skill=act).

**Why Scope × Skill is the core and Trigger is supplementary:** Scope and Skill are the two *irreducible* questions every agent must answer (what do you know? what do you do?). Trigger is important but more operational — it governs scheduling, not identity. An agent's character is defined by its Scope × Skill; its lifecycle is governed by its Trigger.

### User-facing templates (convenience layer)

Templates are pre-configured Scope × Skill × Trigger combinations:

| Template Label | Scope | Skill | Default Trigger | Description |
|---------------|-------|-------|----------------|-------------|
| Slack Recap | platform | digest | recurring | Channel activity summary |
| Gmail Digest | platform | digest | recurring | Email digest by label |
| Meeting Prep | cross_platform | prepare | recurring | Calendar-driven briefing |
| Work Summary | cross_platform | synthesize | recurring | Cross-platform status |
| Channel Watch | platform | monitor | proactive | Track changes in specific channels |
| Domain Tracker | knowledge | monitor | proactive | Longitudinal domain monitoring |
| Deep Dive | research | research | goal | Bounded investigation |
| Proactive Insights | autonomous | synthesize | proactive | Self-directed intelligence |
| Coordinator | autonomous | orchestrate | coordinator | Agent fleet management |
| Custom | (user selects) | (user selects) | (user selects) | Full manual configuration |

Users pick a template → system sets Scope + Skill + Trigger with sensible defaults → user can override any dimension.

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

### Execution strategy by scope

```python
SCOPE_STRATEGIES = {
    "platform":       PlatformBoundStrategy,    # Content dump from single platform
    "cross_platform": CrossPlatformStrategy,    # Content dump from multiple platforms
    "knowledge":      KnowledgeStrategy,        # Workspace + /knowledge/ queries
    "research":       ResearchStrategy,         # Knowledge + WebSearch + documents
    "autonomous":     AutonomousStrategy,       # Full primitive set, agent-driven
}
```

### Lifecycle and ephemeral agents (discourse resolution, 2026-03-12)

**There are no "ephemeral agents."** If the Scope × Skill × Trigger framework is correct, every agent — including short-lived ones — fits within it. The reframe:

- A coordinator spawning a one-off task creates a `goal`-trigger agent. When the goal completes (single milestone), the agent transitions to `status: archived`. Its workspace freezes; its output persists in `/knowledge/`.
- This is a **lifecycle event**, not a special agent category. The taxonomy doesn't need an "ephemeral" flag — `goal` trigger with fast completion IS the ephemeral case.
- **Implication:** Agent creation must be cheap and lightweight. The UX should make spawning a goal-mode agent as easy as saying "research X" — because that IS what goal-trigger agents are for.

---

## Part 8: Interoperability and Future-Proofing

### Alignment with emerging standards

| Standard/Framework | YARNNN Alignment |
|-------------------|-----------------|
| **A2A (Agent-to-Agent)** | Domain × Pattern maps to Agent Card capabilities. An agent's Pattern defines its skills; its Domain defines its context needs. Agent Cards can be auto-generated from these. |
| **MCP (Model Context Protocol)** | Workspace files are already MCP-resource-shaped (ADR-106 Phase 3). Each `/agents/{slug}/` directory is a natural MCP resource scope. |
| **Claude Agent SDK** | Agent identity (instructions + memory + workspace) maps directly to SDK agent configuration. Patterns map to tool sets. |
| **OpenAI Assistants API** | Domain maps to file_search/code_interpreter tool selection. Pattern maps to assistant instructions template. |
| **LangGraph / CrewAI** | Domain × Pattern × Mode is a superset of role + goal + backstory. Mode adds execution character that these frameworks lack. |
| **AutoGen** | Orchestrate pattern with Autonomous domain is equivalent to AutoGen's GroupChat manager. |

### Why the two axes (+ trigger) survive any framework

Any agentic system must answer two fundamental questions:
1. **What does the agent know?** → Scope
2. **What does the agent do?** → Skill

These are irreducible. Every agent framework — A2A, MCP, Claude SDK, OpenAI Assistants, LangGraph, CrewAI, AutoGen, and whatever emerges next — must express both. The third question ("when does it run?" → Trigger) is operational, not definitional: it governs lifecycle, not identity.

The specific values within each axis can expand (new scopes, new skills, new triggers), but the axes themselves are stable. This is the test: **can you describe any agent, from any framework, as Scope × Skill + Trigger?**

- Claude Code agent: Scope=autonomous (filesystem), Skill=act (edit files), Trigger=reactive (user prompt)
- A Slack bot: Scope=platform (Slack), Skill=act (reply), Trigger=reactive (message event)
- A market research agent: Scope=research (web), Skill=research (investigate), Trigger=goal (complete when done)
- A CrewAI "manager": Scope=autonomous, Skill=orchestrate, Trigger=coordinator

No exceptions found. The framework is general.

### Horizontal expansion examples

**New Scope:** `"api"` — agent reads from REST/GraphQL APIs
- No changes to Skill or Trigger
- New strategy: `APIStrategy` (fetch from configured endpoints)
- New primitives: `FetchAPI`, `QueryGraphQL`

**New Skill:** `"report"` — agent produces formatted, structured reports
- No changes to Scope or Trigger
- New prompt template and output validation
- New primitives: `FormatTable`, `GenerateChart` (if needed)

**New Trigger:** `"continuous"` — agent runs as a long-lived process
- No changes to Scope or Skill
- New scheduler behavior: maintain persistent connection
- New primitives: `StreamUpdates`, `WatchForChanges`

Each expansion touches only one axis. The others remain stable.

---

## Part 9: Context Roll-Up Architecture

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

Each level is:
- **More compressed** than the level below
- **More valuable** per token
- **Longer-lived** (higher levels never expire)
- **More expensive to produce** (requires agent intelligence)

### Context injection by level

| Agent Domain | Primary Level | Secondary Level | Injection Style |
|-------------|--------------|-----------------|----------------|
| Platform | L0 (raw) | — | Dump (current) |
| Cross-Platform | L0 (raw, multi) | L1 (digests) | Dump + digest references |
| Knowledge | L1-L3 (curated) | L0 (on-demand via Search) | Workspace + queries |
| Research | L1-L3 + external | L0 (on-demand) | Seed + expand |
| Autonomous | All levels | All levels | Agent-directed |

### Prioritization signals per level

| Level | Prioritization Signal | Weight |
|-------|---------------------|--------|
| L0 | Recency + platform signals (URGENT, DECISION) + user-authored flag | High recency decay |
| L1 | Relevance to agent instructions + recency | Moderate recency decay |
| L2 | Semantic similarity to agent thesis + recency | Low recency decay |
| L3 | Direct instruction match + citation count | Minimal decay |
| L4 | Always injected (user profile/preferences) | No decay |

---

## Part 10: Stress-Testing and Exception Cases

### Exception 1: Agent that spans domains
**Case:** "Summarize my Slack + research market trends related to what's discussed."
**Analysis:** This is Platform (Slack) + Research (web) — two domains.
**Resolution:** Domain = `research` (superset that includes platform content via QueryKnowledge). The agent's instructions specify which platforms to ground in. Research domain agents have access to both knowledge base and web search.

### Exception 2: Agent that changes pattern over time
**Case:** "Start by researching competitors, then monitor for changes weekly."
**Analysis:** Research pattern (goal mode) → Monitor pattern (recurring mode) transition.
**Resolution:** This is a mode transition (goal → recurring), which ADR-092 already supports. The pattern can also transition: when the goal completes, the agent's work_pattern updates from `research` to `monitor`. This is a lifecycle event, not a taxonomy problem.

### Exception 3: Coordinator that also produces content
**Case:** "Watch engineering channels, create child agents for incidents, but also produce a weekly incident summary."
**Analysis:** Orchestrate pattern + Digest pattern in one agent.
**Resolution:** Two options: (a) the coordinator's own output IS the summary (orchestrate pattern can produce documents), or (b) the coordinator creates a child digest agent for the summary. Option (b) is cleaner — one agent, one job.

### Exception 4: Action agent with complex approval
**Case:** "Reply to customer questions on Slack, but only if confidence is high. Stage ambiguous cases for my review."
**Analysis:** Act pattern with conditional approval.
**Resolution:** The approval model is per-action, not per-agent. The agent proposes all actions; the approval policy filters. High-confidence → auto-approve. Ambiguous → stage for review. This is a policy layer, not a taxonomy concern.

### Exception 5: External API agent (future)
**Case:** "Fetch data from our internal dashboard API and produce a daily report."
**Analysis:** New context domain (API), Digest pattern.
**Resolution:** Add `api` domain. New primitives (`FetchAPI`). Pattern and Mode unchanged. The taxonomy accommodates this without restructuring.

---

## Part 11: Knowledge Quality — Principled Scaffold

### The invariant

Knowledge entries have **provenance and are correctable**. The system never treats accumulated knowledge as infallible — it treats it as the *current best understanding*, subject to revision.

This principle is stable regardless of how LLM capability, tools, and platform integrations evolve. The specific thresholds and scoring will change; the principle does not.

### Confidence model

Every `/knowledge/` entry carries implicit confidence derived from usage signals:

```python
class KnowledgeConfidence:
    """Derived from usage patterns, not explicitly set."""

    # Positive signals (increase confidence)
    user_edited: bool           # User reviewed and corrected → highest confidence
    referenced_by_agents: int   # Other agents cited this entry
    user_accessed: int          # User viewed/queried this entry
    age_days: int               # Older entries with sustained references are stable

    # Negative signals (decrease confidence)
    superseded_by: Optional[str]  # Newer entry on same topic exists
    source_expired: bool         # Underlying platform_content no longer exists
    never_referenced: bool       # Produced but never used by any agent or user

    @property
    def score(self) -> float:
        """0.0 to 1.0 — used for context ranking, not hard filtering."""
        # Weights evolve with system maturity; the signals are stable
        ...
```

### Quality correction loop

```
Agent produces output → /knowledge/{class}/{slug}/latest.md
    ↓
User edits output → corrected version REPLACES original in /knowledge/
    ↓
Edit distance recorded → ADR-101 learned preferences extracted
    ↓
Next run: agent receives learned preferences in system prompt
    ↓
Output quality improves → edit distance decreases → confidence increases
```

**Key design choice:** User corrections **replace**, they don't append. The knowledge base reflects current best understanding, not a changelog. The changelog lives in `agent_runs` (version history with edit_distance_score).

### Garbage collection principle

Knowledge entries are **never hard-deleted by TTL** (unlike platform_content). Instead:
- Unreferenced entries decay in ranking (lower confidence score → less likely to be injected as context)
- Superseded entries are archived (kept for provenance but not injected)
- Only explicit user deletion removes knowledge permanently

This is deliberate: the moat is accumulation. Aggressive pruning destroys the moat. Ranking-based deprioritization preserves accumulation while keeping context quality high.

### Evolution path

As LLM quality and tool ecosystems improve:
- Confidence scoring weights will be tuned (more sophisticated embedding models → better relevance scoring)
- Agent self-evaluation may emerge (agent reviews its own past outputs for consistency)
- Cross-agent validation may emerge (multiple agents corroborating same insight → higher confidence)

The scaffold (provenance + confidence signals + ranking) is stable. The weights and algorithms within it evolve.

---

## Part 12: External Invocation — MCP-First Path

### Immediate value (discourse resolution, 2026-03-12)

The first external invocation path is: **web-based LLM providers (Claude, ChatGPT, Gemini) invoke YARNNN via MCP for task execution on derived insights or conversation.**

This already has infrastructure (ADR-075 MCP server). The gap is exposing agent capabilities beyond read-only queries.

### Invocation model

```
External LLM (Claude.ai, ChatGPT, Gemini)
    → MCP connection to YARNNN
    → Available tools:
        - query_knowledge(query) → search accumulated knowledge
        - get_agent_output(agent_id) → read latest agent output
        - run_agent(agent_id) → trigger agent execution, return result
        - search_content(query, platform?) → search platform_content
    → YARNNN executes, returns results
    → External LLM incorporates into conversation
```

**Flow:** YARNNN gets invoked, not the other way around. The external LLM is the orchestrator; YARNNN is the **knowledge and execution substrate.**

### Framework compatibility

Because Scope × Skill maps to A2A Agent Card skills and MCP tool schemas:
- Each YARNNN agent can auto-generate an Agent Card from its Scope + Skill
- MCP tools can be dynamically registered per-agent based on Skill primitives
- External orchestrators can discover YARNNN agent capabilities via standard protocols

We don't need to implement A2A today. We need the internal model to be **expressible** in A2A when the time comes. Scope × Skill achieves this.

---

## Part 13: Minimum Viable Context Scoring (discourse resolution, round 3)

### Design principle

Start with signals that **already exist in the system** (no new infrastructure). Three multiplicative factors that convert chronological ordering into relevance ordering:

### Implementation

```python
def score_content(item: PlatformContent, agent_embedding: Optional[list]) -> float:
    """Minimum viable scoring. Three signals, multiplicative.
    Replaces ORDER BY source_timestamp DESC with ORDER BY score DESC."""

    # 1. Recency decay (0.3 to 1.0)
    #    Full score within 24h, linear decay to 0.3 floor over 7 days.
    #    Floor of 0.3 ensures old high-signal content isn't invisible.
    hours_old = (now() - item.source_timestamp).total_seconds() / 3600
    recency = max(0.3, 1.0 - (hours_old / 168) * 0.7)

    # 2. Signal boost (1.0 to 2.0)
    #    Uses metadata already computed during platform sync.
    boost = 1.0
    if item.metadata.get("is_user_authored"): boost += 0.4
    if item.metadata.get("has_action_request"): boost += 0.3
    if item.metadata.get("mentions_deadline"): boost += 0.2
    if item.metadata.get("mentions_blocker"): boost += 0.2
    if item.metadata.get("is_stalled_thread"): boost += 0.1
    boost = min(boost, 2.0)

    # 3. Instruction alignment (0.5 to 1.5)
    #    Embedding similarity between agent_instructions and content.
    #    One embedding per agent (cached), uses existing pgvector embeddings.
    if agent_embedding and item.embedding:
        similarity = cosine_similarity(agent_embedding, item.embedding)
        alignment = 0.5 + similarity
    else:
        alignment = 1.0  # neutral fallback

    return recency * boost * alignment
```

### Why these three signals

| Signal | Infrastructure cost | Impact |
|--------|-------------------|--------|
| Recency decay | Zero — timestamps exist | 2-day-old CEO message outranks 1-hour-old bot notification when combined with signal boost |
| Signal boost | Zero — metadata already in `platform_content.metadata` from sync | User-authored content and action requests surface above noise |
| Instruction alignment | One cached embedding per agent + existing pgvector | Agent about "product roadmap" preferentially sees product-related content |

### Context tier labels

Scored content is injected with tier labels so the agent LLM can prioritize:

```
Top 20% by score  → CRITICAL: [content]
Middle 50%        → RELEVANT: [content]
Bottom 30%        → BACKGROUND: [content]
```

### Deliberately excluded from Phase 1

- Cross-run reference tracking ("content the agent has used before") — requires new state
- Dynamic context budget allocation by skill — requires experimentation
- Semantic clustering (grouping related items) — nice but not minimum viable
- Knowledge confidence scoring — separate concern (Part 11), applies to `/knowledge/` not `platform_content`

These are Phase 2 improvements once basic scoring proves value.

---

## Discourse Resolution Log

### Resolved (2026-03-12, round 2)

| Question | Resolution | Rationale |
|----------|-----------|-----------|
| **Capability Level as a dimension?** | No — derivative of Skill. Capability is a graduated permission model (ActionPolicy) on the Skill's primitive set. | Adding a 4th dimension creates cognitive overload. Permission is RBAC, not taxonomy. Same agent identity with different approval settings is the same agent. |
| **Naming convention** | Scope / Skill / Trigger — aligned with A2A (skills), MCP (scopes), event-driven architecture (triggers) | Industry convergence analysis across 6 frameworks. |
| **Ephemeral agents** | No special category. Goal-trigger agents that complete quickly ARE the ephemeral case. Agent creation must be cheap. | If the framework is correct, every agent fits. "Ephemeral" is a lifecycle property of goal-trigger, not a taxonomy violation. |
| **External invocation priority** | MCP-first. YARNNN gets invoked by web LLMs (Claude, ChatGPT, Gemini). Framework compatibility via Scope × Skill → Agent Card mapping. | Immediate value is being a knowledge substrate for existing LLM providers. A2A implementation deferred until protocol stabilizes. |
| **Knowledge quality approach** | Principled scaffold: provenance + confidence signals + ranking-based deprioritization. No hard TTL on knowledge. Thresholds evolve; scaffold is stable. | LLM capability, tools, platforms all evolve dynamically. The invariant is: entries have provenance and are correctable. Everything else is tuning. |

### Resolved (2026-03-12, round 3)

| Question | Resolution | Rationale |
|----------|-----------|-----------|
| **Scope: user-configurable or auto-inferred?** | Auto-inferred, never exposed in UI. Derived from user's configured sources + skill. Agent escalates ambiguity to user. | User's job is supervisory (connect, select, instruct, approve). Scope is a system-internal execution strategy classification. User never thinks "platform scope" — they think "my Slack channels." |
| **Knowledge-scope L0 access** | Hard boundary at inception. Knowledge-scope agents have NO access to `platform_content`. If no knowledge exists, agent explicitly reports this and nudges toward platform agent runs. | Purity at inception prevents debugging ambiguity and incentive dilution. The accumulation loop must be forced to work before we relax boundaries. Creates observable dependency: platform agents → `/knowledge/` → knowledge agents. |
| **Multi-skill agents** | One agent, one skill. The framework holds. Multi-skill requests decompose into multiple agents sharing the same source configuration. Templates can create agent bundles. | Digest and Reply have different triggers, context budgets, quality evaluation, and failure modes. Combining them forces conflicting optimization targets. UX solution: "Slack Power User" template spawns Recap + Monitor + Responder agents in one action. |
| **Context scoring implementation** | Three-signal multiplicative scoring: recency decay × signal boost × instruction alignment. All signals use existing infrastructure (timestamps, metadata, pgvector embeddings). Tier labels (CRITICAL/RELEVANT/BACKGROUND) in context injection. | Zero new infrastructure. Meaningfully improves over chronological dump — high-signal old content outranks low-signal new content. Phase 2 adds cross-run references, dynamic budgets, semantic clustering. |

### Open (requires implementation learning)

1. **Agent-to-agent workspace access** — Direct workspace reads (coupled but powerful) vs. shared `/knowledge/` only (decoupled but limited)? Affects coordinator agent capabilities. Recommendation: `/knowledge/` only at inception (same purity principle), evaluate direct access when coordinator patterns mature.

2. **Template bundles** — Can a single template create multiple agents? UX implications for management (grouped display? linked lifecycle?). Needs design exploration.

3. **Scope upgrade path** — As knowledge accumulates, should a platform-scope agent be able to "upgrade" to knowledge-scope automatically? Or is this always a user decision (create a new knowledge-scope agent)?

4. **Agent ambiguity escalation** — How does an agent surface "I need more configuration" to the user? Via TP chat? Via notification? Via a dedicated "agent needs attention" state?

---

## Documentation Sweep Plan

### Blast radius assessment

| Severity | Files | Action |
|----------|-------|--------|
| **CRITICAL** | `docs/features/agent-types.md`, `docs/architecture/agents.md` (Type System section), `docs/features/agent-modes.md` (Type × Mode pairings), `docs/adr/ADR-093` | Full rewrite or supersession |
| **HIGH** | `docs/ESSENCE.md`, `docs/architecture/agent-execution-model.md`, `CLAUDE.md` | Targeted updates |
| **MODERATE** | `docs/architecture/workspace-conventions.md`, `docs/features/meeting-prep.md`, `docs/adr/ADR-106`, `docs/adr/ADR-107`, `docs/adr/ADR-081` | Terminology alignment + cross-references |
| **LOW** | 20+ other docs (four-layer-model, context, activity, sessions, monetization, narrative) | Stable — no type-specific content |

### Phased approach

**Phase 1: Foundation** — Create the canonical reference document (`docs/architecture/agent-framework.md`) that defines Scope × Skill × Trigger. Everything else references this. This document IS the taxonomy — not the ADR, not the analysis.

**Phase 2: Core alignment** — Update the 4 critical files:
- `ESSENCE.md` — Replace agent type references with framework vocabulary. Light touch — ESSENCE is already forward-looking.
- `architecture/agents.md` — Rewrite Type System section → Agent Framework section. Update schema documentation to reflect `scope` + `skill` fields.
- `features/agent-types.md` — Transform into `features/agent-framework.md`. Reorganize from 7-type list to Scope × Skill matrix with templates.
- `features/agent-modes.md` — Remove Type × Mode pairings table. Reframe as Skill × Trigger natural pairings.

**Phase 3: ADR lifecycle** — Write ADR-109 (Agent Framework: Scope × Skill × Trigger). Mark ADR-093 as superseded. Update cross-references in ADR-106, ADR-107, ADR-081, ADR-082, ADR-044.

**Phase 4: Secondary alignment** — Terminology updates in agent-execution-model.md (binding → scope), workspace-conventions.md (archetype alignment), meeting-prep.md (reframe as Prepare skill), CLAUDE.md (key references + terminology).

### Key principle: docs first, code later

This sweep updates documentation to reflect the decided framework. Code changes (schema migration, execution pipeline, frontend) are a separate implementation phase that follows. The docs establish what the code should become — they don't describe the code as it currently is.

### Staleness layers discovered

The current docs have three layers of staleness:
1. `architecture/agents.md` Type System section still references ADR-082's 8 types (`slack_channel_digest`, `gmail_inbox_brief`, etc.)
2. `features/agent-types.md` uses ADR-093's 7 types (`digest`, `brief`, `status`, etc.)
3. `ESSENCE.md` barely mentions types — it's mode-focused and closest to the new framework

The sweep resolves all three layers into one consistent vocabulary.