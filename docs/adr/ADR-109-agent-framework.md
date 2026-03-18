# ADR-109: Agent Framework — Scope × Role × Trigger

> **Naming update (2026-03-17):** The second axis was renamed from "Skill" to "Role" per [ADR-118 Resolved Decision #4](ADR-118-skills-as-capability-layer.md) to eliminate naming overload with output gateway skills (pptx, pdf, xlsx, etc.). "Role" = what an agent does (behavioral). "Skill" = what an agent can produce (output capability). The `agents.skill` column will be renamed to `agents.role` as part of ADR-118 Phase D.1 migration. References to "skill" in this ADR refer to the behavioral axis (now called "role").

**Status:** Implemented (pending `skill` → `role` column rename)
**Date:** 2026-03-12
**Authors:** Kevin Kim, Claude (analysis + discourse)
**Supersedes:**
- [ADR-093: Agent Type Taxonomy](ADR-093-agent-type-taxonomy.md) — 7 purpose-first types decomposed into orthogonal Scope × Skill
- [ADR-082: Agent Type Consolidation](ADR-082-agent-type-consolidation.md) — 27→8 type consolidation
- [ADR-044: Agent Type Reconceptualization](ADR-044-agent-type-reconceptualization.md) — type_classification binding system

**Related:**
- [ADR-092: Agent Intelligence & Mode Taxonomy](ADR-092-agent-intelligence-mode-taxonomy.md) — five modes preserved as Trigger axis
- [ADR-106: Agent Workspace Architecture](ADR-106-agent-workspace-architecture.md) — workspace filesystem, scope-driven strategies
- [ADR-107: Knowledge Filesystem Architecture](ADR-107-knowledge-filesystem-architecture.md) — `/knowledge/` enabling knowledge-scope agents
- [ADR-101: Agent Intelligence Model](ADR-101-agent-intelligence-model.md) — four-layer knowledge model
- [ADR-104: Agent Instructions as Unified Targeting](ADR-104-agent-instructions-unified-targeting.md) — instructions as targeting layer

**Canonical Reference:** [docs/architecture/agent-framework.md](../architecture/agent-framework.md)
**Analysis Document:** [docs/analysis/agent-taxonomy-first-principles-2026-03-12.md](../analysis/agent-taxonomy-first-principles-2026-03-12.md)

---

## Context

The agent type system evolved through ADR-044 (reconceptualization), ADR-082 (27→8 consolidation), and ADR-093 (8→7 purpose-first types). The resulting 7 types (`digest`, `brief`, `status`, `watch`, `deep_research`, `coordinator`, `custom`) conflate multiple independent dimensions:

1. **Platform binding is embedded in type behavior.** A `digest` implies platform-bound, single-platform reading. A `status` implies cross-platform. But both are "summarize what happened" — the platform binding is a context strategy detail, not a user intent.

2. **Execution strategy is coupled to type.** The `type_classification.binding` field (`platform_bound`, `cross_platform`, `research`, `hybrid`) determines execution strategy. But binding should be derived from the agent's configured sources — not from a type name.

3. **Future agentic actions have no home.** An agent that replies to Slack threads, sends emails, or updates Notion pages cannot be classified under the current type system. The `act` skill — agents that execute actions on connected platforms — requires a separate dimension from content generation skills.

4. **Knowledge-first agents are conflated with platform agents.** A `watch` agent could monitor platform sources (Channel Watch) or accumulated knowledge (Domain Tracker). These have fundamentally different context strategies but share a type.

5. **The type system is not horizontally extensible.** Adding a new capability (e.g., API monitoring, structured reporting) requires a new type, which cascades into prompts, strategies, UI labels, and wizard flows. A compositional system would allow adding a new scope or skill independently.

After ADR-092 separated *when* agents act (modes) from *what* they produce (types), the remaining conflation is between *what they know* and *what they do*.

---

## Decision

Replace the `agent_type` column with two orthogonal axes — **Scope** and **Skill** — plus the preserved operational dimension **Trigger** (ADR-092 modes renamed for industry alignment).

### The three axes

**Scope** — What the agent knows (context strategy):
| Value | Source | Strategy |
|-------|--------|----------|
| `platform` | Single platform sources | PlatformBoundStrategy |
| `cross_platform` | Multiple platform sources | CrossPlatformStrategy |
| `knowledge` | Accumulated `/knowledge/` + workspace | KnowledgeStrategy |
| `research` | Web + documents + knowledge | ResearchStrategy |
| `autonomous` | Agent-selected, full primitives | AutonomousStrategy |

**Skill** — What the agent does (prompt, primitives, output shape):
| Value | Verb | Output |
|-------|------|--------|
| `digest` | Compress, summarize | Document |
| `prepare` | Anticipate, assemble | Document |
| `monitor` | Track, diff, alert | Document or notification |
| `research` | Investigate, analyze | Document |
| `synthesize` | Connect, derive insight | Document |
| `orchestrate` | Coordinate, dispatch | Agent actions |
| `act` | Execute, respond, post | Platform action (future) |

**Trigger** — When the agent acts (scheduler behavior):
| Value | Character |
|-------|-----------|
| `recurring` | Fixed schedule |
| `goal` | Schedule, stops at objective |
| `reactive` | Event-driven accumulation |
| `proactive` | Periodic self-review |
| `coordinator` | Review + create/trigger agents |

### Key design principles

1. **Scope is auto-inferred, never user-configured.** Users configure sources and instructions. Scope is derived: 1 platform → `platform`, 2+ → `cross_platform`, 0 sources + research skill → `research`, orchestrate skill → `autonomous`.

2. **One agent, one skill.** Multi-skill requests decompose into agent bundles sharing source configuration. Templates can create multiple agents from one user action.

3. **Primitive gating by skill.** Each skill defines its available primitives. `digest` gets read-only tools. `research` gets WebSearch + workspace. `orchestrate` gets CreateAgent + AdvanceAgentSchedule. `act` gets platform write primitives (gated by ActionPolicy).

4. **Action capability is policy, not dimension.** Read-only → monitored → autonomous is a graduated permission model (ActionPolicy) on the skill's primitive set, not a fourth taxonomic axis.

5. **Knowledge-scope boundary.** At inception, knowledge-scope agents have NO access to `platform_content`. They must use accumulated `/knowledge/` entries. This forces the accumulation loop to work.

6. **Templates are the user-facing layer.** Users pick templates (Slack Recap, Meeting Prep, Work Summary, etc.), not raw Scope × Skill. Advanced users can override.

### Schema evolution

```sql
-- Phase 1: Add new fields alongside existing
ALTER TABLE agents ADD COLUMN scope TEXT;
ALTER TABLE agents ADD COLUMN skill TEXT;

-- Phase 2: Backfill from agent_type
UPDATE agents SET scope = 'platform', skill = 'digest' WHERE agent_type = 'digest';
UPDATE agents SET scope = 'cross_platform', skill = 'prepare' WHERE agent_type = 'brief';
UPDATE agents SET scope = 'cross_platform', skill = 'synthesize' WHERE agent_type = 'status';
UPDATE agents SET scope = 'knowledge', skill = 'monitor' WHERE agent_type = 'watch';
UPDATE agents SET scope = 'research', skill = 'research' WHERE agent_type = 'deep_research';
UPDATE agents SET scope = 'autonomous', skill = 'orchestrate' WHERE agent_type = 'coordinator';
UPDATE agents SET scope = 'research', skill = 'research' WHERE agent_type = 'custom';

-- Phase 3: Pipeline reads scope + skill instead of agent_type
-- Phase 4: Drop agent_type column
```

---

## Implementation Plan

### Phase 1: Schema + Backend (pending)
- Add `scope` and `skill` columns to `agents` table
- Backfill existing agents
- Add scope inference function (sources → scope)
- Update execution strategy selection to use scope
- Add SKILL_PRIMITIVES gating to primitive registry
- Update `agent_pipeline.py` — TYPE_PROMPTS → SKILL_PROMPTS

### Phase 2: Frontend (pending)
- Template-based creation wizard
- Scope × Skill display on agent cards
- Update constants: AGENT_TYPE_LABELS → SKILL_LABELS + SCOPE_LABELS

### Phase 3: Cleanup (pending)
- Drop `agent_type` column
- Remove `type_classification` JSONB column
- Delete old type-specific code paths
- Clean up deprecated type constants

---

## Consequences

### Positive
- **Horizontally extensible:** New scope (e.g., `api`) or skill (e.g., `report`) touches one axis — others remain stable
- **Future-proof:** Framework survives any agentic protocol (A2A, MCP, Claude Agent SDK). Scope maps to capabilities/context. Skill maps to tools/actions. Trigger maps to lifecycle.
- **Agentic actions have a home:** The `act` skill with ActionPolicy enables Slack replies, email sends, Notion updates — without conflating action agents with content agents
- **Knowledge-scope agents unlock the moat:** Agents that read accumulated `/knowledge/` create a true information hierarchy (L0 → L1 → L2 → L3 → L4)
- **Clean separation of concerns:** Context strategy (scope) is independent from work behavior (skill) is independent from lifecycle (trigger)

### Negative
- **Migration complexity:** `agent_type` → `scope` + `skill` requires careful backfill and dual-read period
- **Template abstraction layer:** Users interact with templates, not raw Scope × Skill — adds one indirection layer
- **Scope inference logic:** Auto-inferring scope from sources is a new code path that must handle edge cases

### Neutral
- **Trigger axis preserved:** ADR-092 modes are renamed "triggers" but behavior is unchanged
- **Instructions unchanged:** ADR-104 unified targeting layer works identically with Scope × Skill
- **Workspace unchanged:** ADR-106 workspace architecture is scope-independent

---

## Stress Tests

Five exception cases validated during discourse (see [analysis document](../analysis/agent-taxonomy-first-principles-2026-03-12.md)):

1. **"Slack bot that digests AND replies"** → Two agents: (platform, digest, recurring) + (platform, act, reactive). Same sources, different skills. Template bundle: "Slack Power User."

2. **"Cross-platform daily summary with meeting prep"** → Two agents: (cross_platform, synthesize, recurring) + (cross_platform, prepare, recurring). Different output shapes require different skills.

3. **"Market research that monitors competitors and produces deep reports"** → Two agents: (research, monitor, proactive) + (research, research, goal). Monitor watches ongoing; research investigates bounded.

4. **"Knowledge agent with no accumulated knowledge yet"** → Reports "No accumulated knowledge available" and nudges user/system to create platform agents first. Hard boundary enforced.

5. **"Coordinator that also produces its own content"** → Two agents: (autonomous, orchestrate, coordinator) + (cross_platform, synthesize, recurring). Coordination and content production are separate skills.

---

## References

- [Agent Framework (canonical)](../architecture/agent-framework.md) — full Scope × Skill matrix, templates, primitive gating, context scoring, interoperability mapping
- [Agent Skills Reference](../features/agent-types.md) — per-skill output formats, validated details, execution specifics
- [Analysis: Agent Taxonomy First Principles](../analysis/agent-taxonomy-first-principles-2026-03-12.md) — full discourse, stress-testing, decision rationale
- [ESSENCE.md](../ESSENCE.md) — updated domain model and agent taxonomy reference
