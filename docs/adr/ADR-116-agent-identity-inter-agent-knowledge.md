# ADR-116: Agent Identity & Inter-Agent Knowledge Infrastructure

**Status:** Proposed
**Date:** 2026-03-17
**Builds on:** ADR-106 (Workspace Architecture), ADR-107 (Knowledge Filesystem), ADR-109 (Agent Framework), ADR-111 (Composer), ADR-114 (Substrate-Aware Assessment)
**Related:**
- [FOUNDATIONS.md](../architecture/FOUNDATIONS.md) — Axiom 3 (Agents as Developing Entities), Axiom 2 (Recursive Perception)
- [Agent Framework](../architecture/agent-framework.md) — Scope × Skill × Trigger taxonomy
- [Workspace Conventions](../architecture/workspace-conventions.md) — path tree and access patterns
- [VALUE-CHAIN.md](../architecture/VALUE-CHAIN.md) — Phase 7 (Compound)

---

## Context

### What exists today

YARNNN agents have workspaces (ADR-106), produce knowledge artifacts (ADR-107), and are assessed by Composer (ADR-111/114/115). The workspace architecture is solid: per-agent `/agents/{slug}/` with AGENT.md, thesis.md, memory/, and shared `/knowledge/` with content-class organization.

### What's missing

Agents are **isolated by default**. Each agent's workspace is private. The only cross-agent path is QueryKnowledge, which searches `/knowledge/` by full-text — no metadata filtering, no provenance awareness, no agent discovery.

**Concrete gaps:**

1. **No agent discovery.** An agent (or Composer) cannot ask "what agents exist and what do they do?" The MCP server's `list_agents()` returns titles and schedules but not purpose, thesis, or capabilities.

2. **No metadata-aware knowledge queries.** Knowledge artifacts carry `agent_id`, `skill`, `scope` in JSONB metadata, but QueryKnowledge can only full-text search content. A synthesis agent cannot say "find all digest outputs from the Slack Recap agent."

3. **No cross-agent workspace reading.** Agent A cannot read Agent B's thesis.md or AGENT.md. Cross-agent intelligence flows only through the `/knowledge/` bottleneck.

4. **No agent identity for external consumers.** MCP exposes agent outputs but not agent identity. External agents (Claude Desktop, ChatGPT) can read what an agent produced but not what it is, what it knows, or how to interact with it.

5. **No consumption tracking.** ADR-114 Open Question 3: "How do we know which agents read /knowledge/?" Without this, Composer can't reason about agent dependencies or detect orphaned producers.

### Why now

ADR-115 (Workspace Density Model) gives Composer eagerness in sparse workspaces. But eager creation without inter-agent wiring produces independent agents that don't compound. The value chain stalls at Phase 6 (Compose) — agents exist but don't build on each other's work.

The agent-native ecosystem is materializing: A2A protocol, MCP resources, Resend's agent email, Claude Agent SDK. YARNNN's bet is that agents are first-class participants with their own identity and knowledge — not human proxies. This ADR builds the infrastructure for that thesis.

### Design principles

1. **Agent-native identity, not "on behalf of."** Agents publish under their own identity. Platform write (Slack posts, email sends) is a future distribution channel, not the identity layer.
2. **Workspace IS identity.** AGENT.md + thesis.md + memory/ already define who an agent is. The infrastructure need is making this discoverable, not creating a separate identity system.
3. **Knowledge compounds through explicit references.** Agents should know which other agents produce relevant knowledge and reference them explicitly, not rely on generic text search.
4. **Read-first, write-later.** Cross-agent access starts read-only. No agent modifies another agent's workspace.

---

## Decision

### Phase 1: Knowledge Metadata Search

**Problem:** QueryKnowledge primitive searches `/knowledge/` by text only. Metadata (agent_id, skill, scope, content_class) is stored but not queryable.

**Change:** Add metadata filter parameters to QueryKnowledge and create a supporting RPC.

```sql
-- New RPC: search_knowledge_by_metadata
CREATE OR REPLACE FUNCTION search_knowledge_by_metadata(
    p_user_id UUID,
    p_content_class TEXT DEFAULT NULL,
    p_agent_id UUID DEFAULT NULL,
    p_skill TEXT DEFAULT NULL,
    p_query TEXT DEFAULT NULL,
    p_limit INT DEFAULT 10
) RETURNS TABLE (
    path TEXT,
    content TEXT,
    metadata JSONB,
    tags TEXT[],
    updated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT wf.path, wf.content, wf.metadata, wf.tags, wf.updated_at
    FROM workspace_files wf
    WHERE wf.user_id = p_user_id
      AND wf.path LIKE '/knowledge/%'
      AND (p_content_class IS NULL OR wf.path LIKE '/knowledge/' || p_content_class || '/%')
      AND (p_agent_id IS NULL OR wf.metadata->>'agent_id' = p_agent_id::TEXT)
      AND (p_skill IS NULL OR wf.metadata->>'skill' = p_skill)
      AND (p_query IS NULL OR wf.content ILIKE '%' || p_query || '%')
    ORDER BY wf.updated_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**QueryKnowledge primitive extension:**

```python
# Existing: QueryKnowledge(query: str, content_class?: str)
# Extended: QueryKnowledge(query: str, content_class?: str, agent_id?: str, skill?: str)
```

**Unlocks:** Synthesis agents can query "all digests from Slack Recap agent." Monitor agents can diff against a specific agent's prior outputs. Composer can track which agents produce which knowledge classes.

### Phase 2: Agent Discovery Primitive

**Problem:** Agents and Composer cannot discover what other agents exist or what they do.

**Change:** New headless primitive `DiscoverAgents` + extend Composer's `heartbeat_data_query()`.

```python
# New primitive: DiscoverAgents
# Available to: synthesize, orchestrate skills (+ Composer internally)
{
    "name": "DiscoverAgents",
    "description": "Find agents in this workspace by capability, scope, or skill.",
    "parameters": {
        "skill": "Optional filter by skill (digest, monitor, research, etc.)",
        "scope": "Optional filter by scope (platform, knowledge, research, etc.)",
        "status": "Optional filter by status (active, paused). Default: active",
    },
    "returns": [{
        "id": "uuid",
        "title": "Slack Recap",
        "slug": "slack-recap",
        "skill": "digest",
        "scope": "platform",
        "thesis_summary": "First 200 chars of thesis.md",
        "sources": ["#engineering", "#product"],
        "last_run_at": "2026-03-17T09:00:00Z",
        "maturity": {"runs": 45, "approval_rate": 0.92},
    }]
}
```

**Implementation:** Query `agents` table + read `thesis.md` from workspace for each matching agent. Thesis summary is truncated to keep token budget manageable.

**Unlocks:** Coordinator agents can reason about the fleet. Synthesis agents can discover which digest agents cover which domains. Composer heartbeat can build an agent dependency graph.

### Phase 3: Cross-Agent Workspace Reading

**Problem:** Agent A cannot read Agent B's thesis.md, AGENT.md, or memory files. The only cross-agent path is `/knowledge/`.

**Change:** New headless primitive `ReadAgentContext` — read-only access to another agent's workspace identity files.

```python
# New primitive: ReadAgentContext
# Available to: synthesize, research, orchestrate skills
{
    "name": "ReadAgentContext",
    "description": "Read another agent's identity and domain understanding.",
    "parameters": {
        "agent_id": "UUID of the target agent",
        "files": "Which files to read. Options: 'identity' (AGENT.md + thesis.md), 'memory' (memory/*.md), 'all'. Default: 'identity'",
    },
    "returns": {
        "agent_title": "Slack Recap",
        "agent_md": "Contents of AGENT.md",
        "thesis": "Contents of thesis.md",
        "memory_files": {"observations.md": "...", "preferences.md": "..."},  # if requested
    }
}
```

**Boundary:** Read-only. No agent writes to another agent's workspace. `working/` and `runs/` directories are excluded (process artifacts, not identity).

**Unlocks:** A synthesis agent reads the Slack Recap agent's thesis to understand its editorial lens before synthesizing. A research agent reads an analyst's thesis to avoid redundant investigation. Coordinator reads all child agents' state.

### Phase 4: Agent Card & MCP Exposure

**Problem:** External agents (Claude Desktop, ChatGPT, other MCP clients) can read agent outputs but not agent identity or accumulated knowledge.

**Change:** Auto-generated agent card + new MCP tools.

**Agent card:** Generated from workspace files, not a separate artifact. Stored at `/agents/{slug}/agent-card.json` and regenerated on each run.

```json
{
    "agent_id": "uuid",
    "title": "Slack Recap",
    "slug": "slack-recap",
    "skill": "digest",
    "scope": "platform",
    "description": "First paragraph of AGENT.md",
    "thesis_summary": "First 200 chars of thesis.md",
    "sources": [{"platform": "slack", "resources": ["#engineering", "#product"]}],
    "output_format": "markdown_digest",
    "schedule": {"frequency": "daily", "time": "09:00"},
    "maturity": {
        "total_runs": 45,
        "approval_rate": 0.92,
        "edit_distance_trend": "decreasing",
        "knowledge_files_produced": 42
    },
    "last_output_at": "2026-03-17T09:00:00Z",
    "interop": {
        "mcp_resource": "workspace://agents/slack-recap/",
        "a2a_skills": ["digest", "summarize"],
        "input_format": "platform_content",
        "output_format": "markdown"
    }
}
```

**New MCP tools:**

```python
@mcp.tool()
async def get_agent_card(agent_id: str) -> dict:
    """Get an agent's identity card: who it is, what it does, how mature it is."""

@mcp.tool()
async def search_knowledge(query: str, content_class: str = None, agent_id: str = None) -> dict:
    """Search YARNNN's accumulated agent-produced knowledge (digests, analyses, research, insights)."""

@mcp.tool()
async def discover_agents(skill: str = None, scope: str = None) -> dict:
    """Discover available agents by capability. Returns agent cards."""
```

**Unlocks:** External agents can discover YARNNN's agent fleet, understand what each agent knows, query accumulated knowledge, and reason about which agent to invoke. This is YARNNN as knowledge substrate for any external AI system.

### Phase 5: Consumption Tracking & Composer Wiring

**Problem:** ADR-114 Open Question 3 — no way to know which agents consume which other agents' outputs.

**Change:** Lightweight consumption log. When an agent uses QueryKnowledge, DiscoverAgents, or ReadAgentContext and the result references another agent, log the reference.

```python
# In workspace_files metadata, append to consuming agent's state
# /agents/{consumer-slug}/memory/state.md
{
    "references": [
        {"agent_id": "producer-uuid", "agent_title": "Slack Recap", "last_read": "2026-03-17T10:00:00Z"},
    ]
}
```

**Composer integration:** `heartbeat_data_query()` reads these reference logs to build an agent dependency graph:

```python
"agent_graph": {
    "producers": [
        {"agent": "Slack Recap", "consumers": ["Work Summary", "Market Watch"]},
        {"agent": "Gmail Digest", "consumers": ["Work Summary"]},
    ],
    "orphaned_producers": ["Notion Summary"],  # produces knowledge nobody reads
    "disconnected_consumers": [],  # reads knowledge but sources are stale
}
```

**Composer heuristics:**
- `orphaned_producer`: Agent produces knowledge but no agent consumes it → suggest synthesis agent or pause
- `missing_producer`: Synthesis agent references a domain with no digest agent → suggest creating one
- `stale_dependency`: Producer agent paused/stale but consumers still active → alert

**Unlocks:** Composer reasons about agent supply chains, not just coverage gaps. The system self-organizes toward compounding knowledge.

---

## Implementation Sequence

| Phase | Scope | Dependencies | Estimated Effort |
|-------|-------|-------------|-----------------|
| **1: Knowledge metadata search** | RPC + primitive extension | None | Small — 1 migration, 1 primitive update |
| **2: Agent discovery** | New primitive + Composer extension | None (parallel with 1) | Small — new primitive, heartbeat query extension |
| **3: Cross-agent reading** | New primitive | Phase 2 (needs discovery to know what to read) | Medium — new primitive, access control |
| **4: Agent card + MCP** | Card generation + 3 MCP tools | Phase 2+3 (card needs discovery data) | Medium — auto-generation logic, MCP tool handlers |
| **5: Consumption tracking + Composer** | Logging + Composer graph | Phase 1+2+3 (needs primitives that produce references) | Medium — consumption log, Composer heuristics |

Phases 1 and 2 can proceed in parallel. Phase 3 follows. Phases 4 and 5 can proceed in parallel after 3.

---

## What This Does NOT Include

- **Platform write actions** (Slack post, email send, Notion update). Deferred. Agent identity infrastructure comes first; distribution channels follow.
- **Agent-to-agent RPC / A2A protocol.** Read-only cross-agent access is sufficient for the compounding loop. Real-time inter-agent messaging is future work.
- **Structured output schemas per skill.** Parked separately (see `docs/analysis/structured-output-schemas-2026-03-17.md`). Value increases after inter-agent consumption exists.
- **RSS/external feed ingestion.** Assessed and deferred (conversation 2026-03-17). Low strategic value relative to knowledge compounding.
- **Agent email identity** (e.g., Resend integration). Interesting distribution channel experiment but not core identity infrastructure.

---

## Relationship to Agent-Native Thesis

This ADR operationalizes the bet that **agents are first-class participants, not human proxies**.

| Principle | How This ADR Implements It |
|-----------|---------------------------|
| **Agents have identity** | Agent card (Phase 4) — structured, machine-readable identity derived from workspace |
| **Agents discover each other** | DiscoverAgents primitive (Phase 2) — agents query the fleet |
| **Agents build on each other** | ReadAgentContext (Phase 3) + Knowledge metadata search (Phase 1) — explicit cross-agent references |
| **External agents consume YARNNN** | MCP tools (Phase 4) — agent cards + knowledge search exposed to Claude Desktop, ChatGPT, etc. |
| **System self-organizes** | Consumption tracking (Phase 5) — Composer reasons about agent supply chains |

The workspace IS the identity. The knowledge filesystem IS the communication substrate. This ADR makes both discoverable and composable.

---

## Relationship to Existing Architecture

| Component | Current | After ADR-116 |
|-----------|---------|---------------|
| QueryKnowledge | Text search only | + metadata filters (agent_id, skill, scope) |
| Headless primitives | ReadWorkspace, WriteWorkspace, SearchWorkspace, ListWorkspace, QueryKnowledge | + DiscoverAgents, ReadAgentContext |
| MCP tools | 6 tools (status, agents, run, output, context, search) | + get_agent_card, search_knowledge, discover_agents |
| Composer heartbeat | Platform + agent metadata + knowledge corpus signals | + agent dependency graph |
| `should_composer_act()` | Coverage, staleness, knowledge gaps | + orphaned producers, missing producers, stale dependencies |
| Agent workspace | Private per-agent | Private per-agent + read-only cross-agent access for identity files |
| `/knowledge/` | Text-searchable | + metadata-filterable by producer agent |
| Agent card | Does not exist | Auto-generated from workspace, stored at `/agents/{slug}/agent-card.json` |
| workspace-conventions.md | `references/` marked "(future)" | Specified: `references/{agent-slug}/` for cached cross-agent context |

---

## Open Questions

1. **Agent card freshness.** Should the card regenerate on every run, or on a schedule? Every run is simple but adds write overhead. Stale cards are worse than slightly expensive cards — lean toward every run.

2. **Cross-agent read authorization.** Phase 3 allows any agent to read any other agent's identity files within the same user scope. Should there be skill-based gating (only synthesize/orchestrate skills can read other agents)? Current proposal: yes, skill-gated.

3. **Knowledge metadata indexing.** Phase 1's RPC uses `metadata->>'agent_id'` which isn't indexed. For small workspaces this is fine. At scale, need a GIN index on `workspace_files.metadata`. Defer indexing until query performance degrades.

4. **Agent card schema stability.** The agent-card.json schema will be consumed by external systems. Need a versioning strategy before Phase 4 ships. Propose: `"schema_version": "1"` field, external consumers check version.

5. **Circular references.** If Agent A references Agent B and B references A, does this cause issues? For read-only access, no — it's just mutual awareness. For Composer's dependency graph, treat it as a cycle and flag for review, don't block.

---

## References

- ADR-106: Agent Workspace Architecture
- ADR-107: Knowledge Filesystem Architecture
- ADR-109: Agent Framework (Scope × Skill × Trigger)
- ADR-111: Agent Composer
- ADR-114: Composer Substrate-Aware Assessment (Open Question 3)
- ADR-115: Composer Workspace Density Model
- FOUNDATIONS.md: Axiom 2 (Recursive Perception), Axiom 3 (Agents as Developing Entities)
- VALUE-CHAIN.md: Phase 7 (Compound)
- [Resend Agent Experience](https://resend.com/blog/agent-experience) — AX principles informing identity exposure
- [Analysis: Structured Output Schemas](../analysis/structured-output-schemas-2026-03-17.md) — parked, complementary work
