# ADR-111: Agent Composer

**Status:** Proposed
**Date:** 2026-03-13
**Supersedes:** None
**Related:** ADR-092 (Coordinator Mode), ADR-109 (Agent Framework), ADR-110 (Onboarding Bootstrap), ADR-106 (Workspace Architecture)

---

## Context

### The Naming Problem

The current codebase has two agent creation mechanisms that are both mislabeled:

1. **`Write` primitive** (chat mode) — A generic entity creator that handles agents, memories, and documents via `ref="type:new"`. The agent path inside it is 100+ lines of field processing (`_process_agent()`). This is not "writing" — it's agent creation buried inside a generic write tool.

2. **`CreateAgent` primitive** (headless/coordinator only) — A dedicated agent creator, but scoped exclusively to coordinator agents. Has its own field processing, origin tracking, and workspace seeding — duplicating logic from Write's `_process_agent()`.

**Problem:** Two code paths for the same operation (creating agents), with different defaults, different field handling, and different mode gating. This violates singular implementation. Neither path includes any assessment intelligence — both are dumb writers that insert what they're told.

### The Missing Layer

Between "user has substrate" (connections, files, knowledge) and "agents exist" there is no **assessment and orchestration layer**. Today:

- **Platform connections** → user must manually create matching digest agents
- **Uploaded files** → no agent suggestion at all (knowledge-scope agents are invisible)
- **Multi-platform substrate** → no cross-platform agent suggestion (Work Summary, Meeting Prep)
- **Accumulated knowledge** → no longitudinal agent suggestion (Domain Tracker, Proactive Insights)
- **Agent maturity** → no lifecycle progression (digest → monitor → synthesize as tenure grows)

The Composer is this missing layer. It is not a primitive — it is a **service** that assesses substrate, matches templates, and orchestrates agent creation through the existing creation infrastructure.

## Decision

### 1. Unify Agent Creation into a Single Primitive

**Rename and harden the agent creation path.** Extract `_process_agent()` from `Write` into a dedicated `CreateAgent` primitive available in **both** chat and headless modes, with mode-specific defaults.

| Aspect | Current Write (chat) | Current CreateAgent (headless) | Unified CreateAgent |
|--------|---------------------|-------------------------------|-------------------|
| **Name** | `Write` | `CreateAgent` | `CreateAgent` |
| **Mode** | chat only | headless only | chat + headless |
| **Origin default** | (none) | `coordinator_created` | mode-dependent: `user_configured` (chat), `coordinator_created` (headless), `system_bootstrap` (bootstrap), `composer` (composer) |
| **Field processing** | `_process_agent()` in write.py | inline in coordinator.py | shared `create_agent_record()` in new `agent_creation.py` |
| **Workspace seeding** | Yes (AGENT.md) | Yes (AGENT.md) | Yes (shared) |
| **Scope inference** | Yes (ADR-109) | Yes (ADR-109) | Yes (shared) |
| **Dedup check** | No | Yes (coordinator memory) | Optional (caller decides) |
| **Immediate execution** | No (TP offers separately) | Yes (next_run_at=now) | Optional `execute_now` flag |

**`Write` primitive continues to exist** for memories and documents — it just no longer handles `ref="agent:new"`. If TP calls `Write(ref="agent:new", ...)`, it gets a clear error: "Use CreateAgent to create agents."

**Migration:**
- Extract shared agent creation logic into `api/services/agent_creation.py`
- `CreateAgent` tool definition updated with full field documentation (skill, scope, schedule, sources, instructions)
- Both chat-mode TP and headless coordinators call the same `create_agent_record()` function
- Coordinator-specific logic (dedup, origin override) stays in coordinator.py but calls shared function
- TP prompt updated: `Write(ref="agent:new")` → `CreateAgent(title, skill, ...)`

### 2. Introduce the Composer Service

The Composer is a **backend service** (not an agent, not a primitive) that:

```
assess_substrate(user_id) → SubstrateSnapshot
  ├── connections: [{platform, status, source_count, last_sync}]
  ├── uploaded_files: [{name, type, size, content_summary}]
  ├── workspace_files: [{path, type}]
  ├── existing_agents: [{id, skill, scope, sources, status}]
  └── usage_signals: [{type, count}]  # what they've asked TP about

match_templates(snapshot) → [AgentRecommendation]
  ├── template: TemplateLabel  # from ADR-109 canonical table
  ├── confidence: float  # how obvious this recommendation is
  ├── rationale: str  # why this agent for this substrate
  ├── sources: [DataSource]  # pre-populated
  ├── requires: [str]  # unmet prerequisites (e.g., "connect Gmail for full context")
  └── priority: int  # ordering hint

scaffold(recommendations, mode) → [AgentCreated]
  mode = "auto" | "suggest"
  ├── auto: create immediately (bootstrap path, high-confidence only)
  └── suggest: return recommendations for TP/UI to present
```

### 3. Composer Trigger Points

| Event | Composer Mode | What Happens |
|-------|--------------|--------------|
| **Platform connected + first sync** | `auto` (high confidence only) | Bootstrap path — deterministic digest creation (ADR-110) |
| **File uploaded to workspace** | `suggest` | Composer returns knowledge-scope recommendations; TP presents them |
| **Second platform connected** | `suggest` | Composer recommends cross-platform agents (Work Summary, Meeting Prep) |
| **Agent reaches N runs with low edit distance** | `suggest` | Composer recommends upgrade (digest → monitor, or add Proactive Insights) |
| **User asks TP "what else can yarnnn do?"** | `suggest` | Composer returns full gap analysis as TP context |
| **Nightly cron (low frequency)** | `suggest` | Passive substrate assessment, surfaces recommendations in next TP session |

### 4. Confidence Tiers

The Composer operates at two confidence levels:

**High confidence (auto-create, no LLM):**
- Single platform connected → matching digest agent
- This is the ADR-110 bootstrap path, subsumed by Composer

**Medium confidence (suggest via TP, optional LLM):**
- Multi-platform → Work Summary recommendation
- Calendar + other platforms → Meeting Prep recommendation
- Uploaded competitive docs → Domain Tracker recommendation
- Accumulated 2+ weeks of content → Proactive Insights recommendation

**Low confidence (present as options, never auto-create):**
- Deep Dive (requires user-specified research question)
- Custom agents
- Coordinator agents

### 5. Substrate Types and Template Affinity

| Substrate | Detected By | Natural Templates | Confidence |
|-----------|-------------|-------------------|------------|
| Single platform connection | `platform_connections` query | Platform digest (Slack Recap, Gmail Digest, Notion Summary) | High |
| Multi-platform connections | 2+ distinct platforms in connections | Work Summary, Meeting Prep | Medium |
| Calendar connection | Google Calendar in connections | Meeting Prep (requires cross-platform context) | Medium |
| Uploaded documents | `filesystem_documents` or `workspace_files` with user uploads | Domain Tracker, Deep Dive | Medium |
| Accumulated knowledge | `workspace_files` in `/knowledge/` above threshold | Proactive Insights | Medium |
| Agent maturity signal | Agent with 5+ runs, avg_edit_distance < 0.1 | Monitor upgrade, Proactive Insights | Low |

### 6. Composer Is Not an Agent

**Why a service, not a coordinator agent:**

- Bootstrap (high confidence) must fire synchronously post-OAuth — scheduler latency is unacceptable for "first 60 seconds"
- Assessment is mostly deterministic (count connections, check existing agents, lookup template table) — LLM is optional for medium-confidence recommendations
- Composer needs to be callable from multiple sites (OAuth callback, file upload handler, TP context enrichment, nightly cron) — agents only run via scheduler
- No persistent state needed beyond what already exists (connections, agents, workspace_files)

**A coordinator agent could be layered on top later** for the autonomous lifecycle progression case (agent maturity → recommend upgrade), where periodic review cadence makes sense.

## Phased Implementation

### Phase 1: CreateAgent Primitive Unification

- Extract `_process_agent()` into `api/services/agent_creation.py` as `create_agent_record()`
- New `CreateAgent` tool definition in `api/services/primitives/create_agent.py` (chat + headless)
- `Write` primitive rejects `ref="agent:new"` with redirect message
- Coordinator's `handle_create_agent()` calls shared `create_agent_record()`
- Update TP prompt: document `CreateAgent` as the agent creation tool
- Update `api/prompts/CHANGELOG.md`

### Phase 2: Onboarding Bootstrap (ADR-110)

- `api/services/onboarding_bootstrap.py` — deterministic bootstrap service
- Calls `create_agent_record()` with `origin="system_bootstrap"`
- Wired into platform sync completion handler
- OAuth redirect updated to return to dashboard
- Dashboard UX shows generating agent

### Phase 3: Composer Service (Suggest Mode)

- `api/services/composer.py` — `assess_substrate()`, `match_templates()`, `scaffold()`
- Wired into TP context enrichment: when user has unmatched substrate, TP sees recommendations
- Wired into file upload handler: uploaded files trigger `suggest` mode
- Wired into second-platform-connected event

### Phase 4: Lifecycle Progression (Future)

- Agent maturity signals feed into Composer
- Composer recommends upgrades (digest → monitor, add Proactive Insights)
- Optionally implemented as a system coordinator for periodic review

## Consequences

### Positive
- **Single agent creation path** — eliminates dual Write/_process_agent vs CreateAgent/handle_create_agent
- **Full taxonomy becomes accessible** — knowledge, research, and autonomous agents get surfaced naturally through substrate matching, not just platform-scoped digests
- **File uploads lead somewhere** — uploading docs without platform connections now has a clear agent path (Domain Tracker, Deep Dive)
- **Progressive sophistication** — bootstrap is instant and dumb; Composer adds intelligence gradually; lifecycle adds autonomy later
- **TP gets richer context** — Composer recommendations injected into TP sessions mean the orchestrator can proactively suggest agents during conversation

### Negative
- **New service to maintain** — Composer is a new abstraction layer between substrate and agents
- **Recommendation quality** — medium-confidence suggestions may be wrong; user must be able to dismiss easily
- **Primitive rename requires prompt update** — TP must learn to use `CreateAgent` instead of `Write(ref="agent:new")`

### Neutral
- Bootstrap (ADR-110) ships independently as Phase 2 — Composer enhances but doesn't block it
- `Write` primitive continues for memories and documents — no disruption to non-agent creation
- `origin` field gains two new values: `system_bootstrap` and `composer`

## Open Questions

1. **Should Composer auto-create cross-platform agents (medium confidence)?** Or always suggest? Auto-creating a Work Summary when second platform connects is aggressive but high-value.

2. **How does Composer interact with tier limits?** If free tier has 2 agent slots and bootstrap fills 1, Composer can only suggest 1 more. Should Composer prioritize recommendations by value?

3. **Should Composer recommendations persist?** If user dismisses a suggestion, should it come back? (Probably not — track dismissed recommendations to avoid nagging.)

4. **LLM involvement in medium-confidence tier?** Pure heuristics may suffice for "you have Slack + Calendar → suggest Meeting Prep." LLM adds value for nuanced cases (analyzing uploaded doc content to determine right agent type). Could be Phase 3+ optimization.

## References

- [ADR-092: Agent Intelligence & Mode Taxonomy](ADR-092-agent-intelligence-mode-taxonomy.md) — coordinator mode, CreateAgent primitive
- [ADR-109: Agent Framework](ADR-109-agent-framework.md) — Scope × Skill × Trigger taxonomy, canonical template table
- [ADR-110: Onboarding Bootstrap](ADR-110-onboarding-bootstrap.md) — deterministic bootstrap, subsumed by Composer Phase 2
- [ADR-106: Agent Workspace Architecture](ADR-106-agent-workspace-architecture.md) — workspace as substrate signal
- [Agent Framework (canonical)](../architecture/agent-framework.md) — template definitions
