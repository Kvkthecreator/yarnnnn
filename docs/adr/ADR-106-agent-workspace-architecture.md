# ADR-106: Agent Workspace Architecture

**Status:** Accepted
**Date:** 2026-03-11
**Supersedes:** ADR-072 (platform_content as flat knowledge base — extended, not replaced), ADR-087 (agent_memory JSONB — replaced by workspace files)
**Related:**
- [ADR-103: Agentic Framework Reframe](ADR-103-agentic-framework-reframe.md) — agents as persistent specialists
- [ADR-101: Agent Intelligence Model](ADR-101-agent-intelligence-model.md) — four-layer model (skills/directives/memory/feedback)
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md) — headless mode primitives
- [ADR-081: Execution Path Consolidation](ADR-081-execution-path-consolidation.md) — binding-aware strategies
- [Analysis: Agent Workspace Architecture Discourse](../analysis/agent-workspace-architecture-2026-03-11.md)

---

## Context

YARNNN agents produce low-quality output when their context need doesn't match the context pipeline. Specifically:

1. **All agents receive the same context scaffolding** — a chronological dump of all platform content from configured sources (`get_content_summary_for_generation()`). This is correct for reporter agents (digest, status, brief) whose job is to summarize what happened. It produces garbage for reasoning agents (proactive insights, research, watch) who need to form judgments about what matters.

2. **Agent memory is an opaque JSONB blob** (`agent_memory` column on `agents` table). It can't be queried, searched, or structured. An agent's accumulated intelligence is invisible to the system and to the user.

3. **No workspace isolation.** All agents share the same flat `platform_content` table. An agent can't maintain a structured understanding of its domain, save intermediate research, or build up working state across runs.

4. **The industry is converging on file-based agent interfaces.** Claude Code uses filesystem memory (`.claude/memory/`). The Claude Agent SDK exposes persistent directories. Agent-vfs, AgentFS, and the Three-File Pattern all implement filesystem semantics for agent state. MCP and A2A protocols use file-like conventions (`.well-known/agent-card.json`, MCP resources). LLMs are pre-trained on filesystem operations and exhibit zero-shot competence with file-based interfaces.

## Decision

### 1. Virtual Filesystem over Postgres

Every agent gets a **workspace** — a virtual filesystem backed by a Postgres table. Agents interact with their workspace through path-based operations (read, write, list, search). The backing store is invisible to the agent.

```sql
CREATE TABLE workspace_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    path TEXT NOT NULL,              -- e.g., '/agents/proactive-insights/thesis.md'
    content TEXT NOT NULL DEFAULT '',
    summary TEXT,                    -- brief description for discovery
    content_type TEXT DEFAULT 'text/markdown',
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    embedding vector(1536),          -- semantic search
    size_bytes INTEGER GENERATED ALWAYS AS (octet_length(content)) STORED,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(user_id, path)
);

-- Path-based access
CREATE INDEX idx_ws_path ON workspace_files(user_id, path);
CREATE INDEX idx_ws_path_prefix ON workspace_files(user_id, path text_pattern_ops);
-- Semantic search
CREATE INDEX idx_ws_embedding ON workspace_files USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100) WHERE embedding IS NOT NULL;
-- Full-text search
CREATE INDEX idx_ws_fts ON workspace_files USING gin (to_tsvector('english', content));
-- Tag-based discovery
CREATE INDEX idx_ws_tags ON workspace_files USING gin (tags);
-- Recent changes
CREATE INDEX idx_ws_updated ON workspace_files(user_id, updated_at DESC);
```

### 2. Canonical Path Conventions

The path structure IS the schema. New agent types don't need schema changes — they use new path conventions.

```
/users/{user_id}/
  workspace.md                          # Global user context
  preferences.md                        # Learned preferences (replaces user_memory KV)

  /knowledge/                           # The knowledge base (replaces platform_content)
    /slack/
      /{channel_name}/
        {date}.md                       # Daily content snapshots
    /gmail/
      /{label}/
        {date}.md
    /notion/
      /{page_name}.md
    /calendar/
      {date}.md
    /yarnnn/                            # Agent outputs (always retained)
      {agent_slug}-v{N}.md

  /agents/
    /{agent_slug}/
      agent.md                          # Identity, configuration, schedule
      directives.md                     # User-authored behavioral instructions
      thesis.md                         # Current domain understanding (self-evolving)
      memory.md                         # Accumulated observations from review passes
      feedback.md                       # Learned preferences from edit history
      /runs/
        v{N}.md                         # Output + metadata per run
      /working/                         # Intermediate research, saved searches
        {topic}.md
      /references/                      # Content this agent found valuable
        {ref}.md
```

### 3. Storage-Agnostic Abstraction Layer

Agent code interacts with an `AgentWorkspace` interface, not with the database directly. This preserves optionality for future migration to cloud storage (S3/GCS).

```python
class AgentWorkspace:
    """Storage-agnostic workspace for an agent."""

    def __init__(self, db_client, user_id: str, agent_slug: str):
        self.base_path = f"/agents/{agent_slug}"

    async def read(self, relative_path: str) -> str | None:
        """Read a file. e.g., read('thesis.md')"""

    async def write(self, relative_path: str, content: str, summary: str = None):
        """Write a file (create or overwrite)."""

    async def append(self, relative_path: str, content: str):
        """Append to a file."""

    async def list(self, relative_path: str = "", recursive: bool = False) -> list[str]:
        """List files in a directory."""

    async def search(self, query: str, path_prefix: str = None) -> list[SearchResult]:
        """Full-text search within workspace."""

    async def semantic_search(self, query: str, path_prefix: str = None, limit: int = 10) -> list[SearchResult]:
        """Vector similarity search within workspace."""

    async def delete(self, relative_path: str):
        """Delete a file."""

    async def exists(self, relative_path: str) -> bool:
        """Check if a file exists."""
```

A `KnowledgeBase` class provides access to the shared `/knowledge/` directory (the perception pipeline's output). Agents query it through the same file-like interface.

### 4. Agent Archetypes Drive Context Strategy

Replace binding-based strategy selection with archetype-driven strategies:

| Archetype | Current binding | New strategy | Context flow |
|---|---|---|---|
| **Reporter** | `platform_bound`, `cross_platform` | `ReporterStrategy` | Load knowledge base dump (current behavior) → generate |
| **Analyst** | `hybrid` | `AnalystStrategy` | Load workspace (thesis + memory) → agent queries knowledge base via Search → generate → update workspace |
| **Researcher** | `research` | `ResearcherStrategy` | Load workspace (thesis + working notes) → agent queries knowledge base + WebSearch → generate → update workspace |
| **Operator** | (future) | `OperatorStrategy` | Load workspace (templates + action history) → agent executes workflow → update workspace |

For reporter agents, nothing changes — they still get the platform content dump. For reasoning agents, the pipeline inverts: the agent drives its own context gathering from its workspace.

### 5. Review Pass → Generation Continuity

Currently the proactive review pass (Haiku) and generation pass (Sonnet) are disconnected — Haiku decides to generate, but Sonnet starts fresh with a platform dump.

With workspaces:
- Review pass writes observations and reasoning to `/agents/{slug}/working/review-{date}.md`
- Generation pass reads those observations as its starting point
- No intelligence is lost between phases

### 6. Migration: platform_content → Knowledge Base Files

`platform_content` rows are materialized as workspace files under `/knowledge/`. The perception pipeline writes to workspace files instead of (or in addition to) the flat table.

**Phase 1:** Workspace files are the primary store for agent state. `platform_content` continues to exist for the perception pipeline and reporter agents.

**Phase 2:** Perception pipeline writes directly to workspace files. `platform_content` becomes a view or is retired.

### 7. Interop: Workspace as MCP Resources

Agent workspace files are naturally exposed as MCP resources:
- `workspace://agents/proactive-insights/thesis.md` → MCP resource URI
- External agents (Claude Desktop, other platforms) can discover and read workspace contents
- A2A Agent Cards can reference workspace paths for capability discovery

---

## What Changes

### Schema

| Before | After |
|---|---|
| `agent_memory JSONB` on agents table | `workspace_files` table with path-based access |
| `user_memory` key-value table | Workspace files at `/workspace.md`, `/preferences.md` |
| `platform_content` flat table | Continues for perception pipeline; materialized into `/knowledge/` for agent access |

### Execution Pipeline (reasoning agents)

| Before | After |
|---|---|
| `get_execution_strategy()` by binding | `get_execution_strategy()` by archetype |
| `strategy.gather_context()` dumps platform_content | `strategy.load_workspace()` loads agent's working state |
| Agent receives dump + instructions | Agent receives workspace context + primitives to query knowledge base |
| Agent generates from dump | Agent reasons → queries → generates |
| Review pass output discarded | Review pass writes to workspace, generation reads it |

### Execution Pipeline (reporter agents)

No change. Reporter agents continue to receive platform content dumps. Their workspace is minimal (outputs + feedback only).

### Agent Intelligence Model (ADR-101) — mapped to workspace

| Layer | Before | After |
|---|---|---|
| Skills | Hardcoded per type | Hardcoded per archetype (same) |
| Directives | `agent_instructions` column | `/agents/{slug}/directives.md` |
| Memory | `agent_memory` JSONB | `/agents/{slug}/memory.md` + `/agents/{slug}/working/*.md` |
| Feedback | `get_past_versions_context()` | `/agents/{slug}/feedback.md` |

### New Primitives (headless mode)

Reasoning agents in headless mode get workspace primitives:

```python
PRIMITIVE_MODES = {
    # Existing...
    "Search":             ["chat", "headless"],
    "WebSearch":          ["chat", "headless"],

    # New workspace primitives (headless reasoning agents)
    "ReadWorkspace":      ["headless"],   # read from agent's workspace
    "WriteWorkspace":     ["headless"],   # write to agent's workspace (thesis, observations)
    "SearchWorkspace":    ["headless"],   # search within workspace
    "QueryKnowledge":     ["headless"],   # search the shared knowledge base
}
```

---

## Implementation Phases

### Phase 1: Foundation (immediate)

1. Create `workspace_files` table (migration)
2. Implement `AgentWorkspace` and `KnowledgeBase` abstraction classes
3. Add `AnalystStrategy` — loads workspace, doesn't pre-gather platform dump
4. Wire Proactive Insights (`deep_research` type) to use `AnalystStrategy`
5. Add workspace headless primitives (`ReadWorkspace`, `WriteWorkspace`, `SearchWorkspace`, `QueryKnowledge`)
6. Migrate `agent_memory` JSONB → workspace files for existing agents
7. Review pass writes to workspace; generation pass reads from workspace

### Phase 2: Knowledge Base Migration

1. Perception pipeline writes to workspace files under `/knowledge/`
2. Materialization: `platform_content` rows → workspace files (daily snapshots per source)
3. Reporter agents can optionally read from workspace `/knowledge/` instead of `platform_content` directly
4. `user_memory` KV migrated to workspace files

### Phase 3: Interop and UI

1. Expose workspace files as MCP resources
2. Workspace browser in frontend UI (inspect agent state, edit directives)
3. A2A Agent Card generation from workspace
4. Evaluate cloud storage migration (S3/GCS) based on scale needs

---

## What This Enables

1. **Reasoning agents that improve with tenure.** Thesis evolves across runs. Observations compound. Working notes persist.
2. **Inspectable agent intelligence.** Users browse workspace files. Debug by reading, not querying.
3. **Cross-agent intelligence.** Coordinator reads child agents' theses. Agents reference each other's workspace items.
4. **Protocol-native interop.** Workspace files map directly to MCP resources and A2A capabilities.
5. **Storage-agnostic future.** Abstraction layer preserves optionality. Swap Postgres for S3 without changing agent code.

---

## Anti-Patterns

**Storing agent state in JSONB blobs.** Opaque, unqueryable, not searchable. The workspace replaces this with structured, human-readable files.

**Pre-gathering context for reasoning agents.** The platform dump is correct for reporters. For reasoning agents, it's noise. Let the agent drive its own context gathering from its workspace.

**Separate memory systems.** Agent memory, user memory, platform content, and agent outputs are currently four separate systems. The workspace unifies them under one file-based interface with a shared path convention.

**Tight coupling to Postgres.** Agent code should interact with the `AgentWorkspace` interface, not with SQL. This enables infrastructure evolution without code changes.

---

## Decision Context

This ADR was reached through extended discourse examining:
1. Why Proactive Insights produced irrelevant content (Korean beauty program in a YARNNN-focused agent)
2. The distinction between reporter and reasoning agents
3. How the four-layer intelligence model should drive context gathering
4. Industry evidence for file-based agent interfaces (Claude Code, agent-vfs, AgentFS, Three-File Pattern)
5. Protocol alignment (MCP resources, A2A Agent Cards)
6. Option B (virtual filesystem over Postgres) vs Option C (actual cloud filesystem)

Full discourse captured in [analysis/agent-workspace-architecture-2026-03-11.md](../analysis/agent-workspace-architecture-2026-03-11.md).

The core bet: **agent intelligence should be stored as human-readable files in navigable workspaces.** This aligns with industry direction and makes agents inspectable, portable, and composable. The virtual filesystem over Postgres delivers this at minimal infrastructure cost while preserving optionality for cloud storage migration.
