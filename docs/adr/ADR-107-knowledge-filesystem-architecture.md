# ADR-107: Knowledge Filesystem Architecture

**Status:** Accepted
**Date:** 2026-03-11
**Supersedes:** ADR-102 (yarnnn Content Platform — `platform="yarnnn"` rows replaced by `/knowledge/` filesystem)
**Related:**
- [ADR-106: Agent Workspace Architecture](ADR-106-agent-workspace-architecture.md) — Phase 1 (agent intelligence in workspace files)
- [ADR-072: Unified Content Layer](ADR-072-unified-content-layer-tp-execution-pipeline.md) — `platform_content` as accumulation layer
- [ADR-092: Agent Intelligence & Mode Taxonomy](ADR-092-agent-intelligence-mode-taxonomy.md) — agent modes and orchestration
- [ADR-093: Agent Type Taxonomy](ADR-093-agent-type-taxonomy.md) — type system (to be extended)
- [Analysis: Knowledge Filesystem Discourse](../analysis/knowledge-filesystem-discourse-2026-03-11.md)

---

## Context

ADR-106 Phase 1 established workspace files as the singular source of truth for agent intelligence (`/agents/{slug}/AGENT.md`, `memory/`). This proved the filesystem-over-Postgres model for agent-private state.

Two problems remain:

1. **Agent-produced knowledge is flat.** ADR-102 writes agent outputs to `platform_content` with `platform="yarnnn"`. These rows have no structured metadata — no versioning, no supersession, no provenance chain, no content classification. A research paper and a Slack message look structurally identical. Downstream agents searching the shared context pool cannot distinguish curated knowledge from raw data without reading full text.

2. **External content consumption is dump-based.** Reporter agents receive a chronological dump of `platform_content` via `get_content_summary_for_generation()`. This works for simple digests but produces garbage for reasoning agents. ADR-106's AnalystStrategy already moved reasoning agents to tool-driven consumption — this ADR extends that pattern to all agents.

## Decision

### 1. Three Storage Domains

| Domain | Backing Store | Scope | Lifecycle | Purpose |
|--------|--------------|-------|-----------|---------|
| **External Context** | `platform_content` table | Per-user, shared | TTL-managed (14-90d) | Raw platform data from Slack, Gmail, Notion, Calendar |
| **Agent Intelligence** | `workspace_files` under `/agents/{slug}/` | Per-agent, private | Persistent | Agent identity, memory, working state (ADR-106) |
| **Accumulated Knowledge** | `workspace_files` under `/knowledge/` | Per-user, shared | Persistent, version-aware | Agent-produced knowledge artifacts |

External context stays in `platform_content` — flat, TTL-managed, optimized for sync and search. No change to the perception pipeline.

Agent intelligence stays in `/agents/{slug}/` — private workspace files per ADR-106. No change.

Agent-produced knowledge moves from `platform_content` (`platform="yarnnn"`) to `/knowledge/` in `workspace_files`. This is the new accumulation layer where the recursive moat materializes as structured, inspectable, navigable files.

### 2. Knowledge Filesystem Structure

```
/knowledge/
  ├── digests/                          ← Platform-specific recaps
  │     {source}-{date}.md              ← e.g., slack-engineering-2026-03-11.md
  │
  ├── research/                         ← Deep research outputs
  │     {topic-slug}/
  │       latest.md                     ← Current version (canonical)
  │       v1.md, v2.md                  ← Historical versions (opt-in)
  │
  ├── analyses/                         ← Cross-platform synthesis
  │     {topic-slug}.md                 ← e.g., competitive-landscape-q1.md
  │
  ├── briefs/                           ← Event-driven preparation
  │     {event-slug}.md                 ← e.g., board-meeting-2026-03-15.md
  │
  └── insights/                         ← Proactive findings
        {topic-slug}.md                 ← e.g., engineering-velocity-trend.md
```

Each file carries metadata via `workspace_files` columns:
- `metadata.agent_id` — which agent produced it
- `metadata.run_id` — which generation run
- `metadata.supersedes` — previous version path (if any)
- `metadata.content_class` — digest, research, analysis, brief, insight
- `tags` — searchable topic tags
- `summary` — brief description for discovery

### 3. Content Consumption Model

All agents shift from content-dump to tool-driven consumption:

**Current (reporter agents):**
```
get_content_summary_for_generation() → dumps platform_content into prompt
```

**New (all agents):**
```
Agent uses tools → Search(platform_content) for external data
                 → Search(/knowledge/) for accumulated knowledge
                 → Agent decides what's relevant
                 → Produces output → writes to /knowledge/
```

AnalystStrategy (ADR-106) already implements this for reasoning agents. This ADR extends it to reporter agents (digest, status, brief), retiring the dump-into-prompt pattern.

### 4. Recursion Point: Delivery → Knowledge

Agent outputs enter `/knowledge/` at delivery time, not generation time:

```
Agent generates → draft in agent_runs → approved/auto-approved → delivered externally
                                                               → written to /knowledge/{class}/{slug}/latest.md
```

This ensures:
- Only approved outputs enter the shared knowledge base
- Users control the accumulation loop (via approval or auto-approve settings)
- Draft/rejected outputs never pollute shared context
- The delivery layer handles both external delivery and internal knowledge filing

### 5. Agent Type Implications

The filesystem architecture suggests two natural agent categories:

**Platform Agents** — Read from `platform_content`, produce platform-aware knowledge:
- Digest agents (Slack recap, Gmail digest) → `/knowledge/digests/`
- Watch agents (Notion watcher) → `/knowledge/insights/`
- Brief agents (Calendar prep) → `/knowledge/briefs/`

**Synthesis Agents** — Read from `/knowledge/` (digested context), produce cross-cutting analysis:
- Status agents → read `/knowledge/digests/` → `/knowledge/analyses/`
- Research agents → read `/knowledge/` + web → `/knowledge/research/`
- Coordinator agents → orchestrate platform + synthesis agents

This is not a rigid taxonomy. It's an emergent pattern from the filesystem structure. Agent types may evolve to carry platform-specific configuration (channel selection, thread expansion) independent of the type system.

### 6. Action Model

Actions (non-knowledge outputs) do NOT enter `/knowledge/`:

| Output Type | Where It Goes | Examples |
|------------|---------------|----------|
| Knowledge artifact | `/knowledge/{class}/{slug}/` | Research paper, digest, analysis |
| External delivery | Platform API (email, Slack, etc.) | Email notification, Slack post |
| Draft action (future) | Staged for approval → platform API | Draft Slack reply, Gmail draft |
| Webhook (future) | External endpoint | Structured payload to external system |

The filesystem boundary IS the content classification. If it's knowledge, it goes to `/knowledge/`. If it's an action, it routes through the delivery layer.

## OS Model

The full architecture maps to an operating system:

```
/agents/           = /home/          Per-process private state
/knowledge/        = /var/shared/    Shared knowledge filesystem
platform_content   = /dev/           Hardware abstraction (external I/O)
delivery layer     = /proc/          System services (actions, routing)
TP (orchestrator)  = shell           User interface
sync pipeline      = kernel drivers  Background I/O management
```

Agents are processes. Workspace is the filesystem. `platform_content` is the device driver layer. The delivery pipeline is system services. This is an agent-native operating system where the filesystem is the universal interface between agents, between the system and the user, and between perception and reasoning.

## Implementation Plan

**Principle: Singular implementation.** No dual-write. No backwards-compat shims. Pre-launch — existing test data will be wiped. Clean cutover.

### Phase 1: Knowledge Write + Read (singular cutover)

**Write path — replace `store_platform_content(platform="yarnnn")` with `/knowledge/` write:**
1. Add `write()` method to `KnowledgeBase` class in `workspace.py` (user-scoped, not agent-scoped)
2. Define content-class → directory mapping per agent type:
   - `digest` → `/knowledge/digests/{source}-{date}.md`
   - `status` → `/knowledge/analyses/{slug}-{date}.md`
   - `brief` → `/knowledge/briefs/{slug}-{date}.md`
   - `deep_research` → `/knowledge/research/{slug}/latest.md`
   - `watch` → `/knowledge/insights/{slug}.md`
   - `custom` → `/knowledge/analyses/{slug}-{date}.md`
3. Replace `store_platform_content()` call in `agent_execution.py` (lines 797-829) with `KnowledgeBase.write()`. Delete the ADR-102 block entirely.
4. File metadata: `{agent_id, run_id, content_class, agent_type, version_number}` stored in `workspace_files.metadata` JSONB

**Read path — update consumers to read from `/knowledge/` instead of `platform="yarnnn"`:**
5. `QueryKnowledge` primitive: remove `"yarnnn"` from platform enum. `KnowledgeBase.search()` already searches `/knowledge/` — the fallback to `platform_content` remains for external data only.
6. TP Search primitive (`search.py`): remove `"yarnnn"` from platform filter options.
7. Frontend `context/yarnnn/page.tsx`: redirect to query `workspace_files` under `/knowledge/` path (or remove page if not needed pre-launch).
8. Admin/system metrics: update `routes/system.py` and `routes/admin.py` to query `/knowledge/` files instead of `platform_content WHERE platform='yarnnn'`.

**Cleanup — delete ADR-102 infrastructure:**
9. Remove `"yarnnn"` from `PlatformType` literal in `platform_content.py`
10. Remove `"yarnnn_output"` from `RetainedReason` literal
11. Delete existing `platform_content` rows where `platform='yarnnn'` (SQL migration — pre-launch data wipe)
12. Mark ADR-102 as **Superseded by ADR-107** in its header

**Embeddings:** `workspace_files` already has pgvector embeddings via migration 100. `/knowledge/` files get indexed on write automatically — no additional work needed.

### Phase 2: Version Management
1. Implement supersession logic (new version replaces `latest.md`, archives previous as `v{N}.md`)
2. Provenance tracking in metadata (agent_id, run_id chain)
3. Knowledge retention policy (distinct from platform_content TTL)
4. MCP resource exposure for `/knowledge/` files (ADR-106 Phase 3)

### Phase 3: Agent Type Evolution
1. Platform-specific agent configurations (channel selection, thread handling per platform)
2. Synthesis agents read from `/knowledge/` (digested context) for cross-cutting analysis
3. Action framework beyond text output (draft actions, webhooks)
4. Coordinator orchestration across platform and synthesis agents

### Validation & Testing

**Pre-implementation:**
- [ ] Verify `workspace_files` RPC `search_workspace` works with `/knowledge/` prefix (user-scoped, not agent-scoped)
- [ ] Confirm `workspace_files` embeddings trigger on INSERT (migration 100)

**Post-implementation:**
- [ ] Trigger agent generation → verify output appears in `workspace_files` under `/knowledge/{class}/`
- [ ] `QueryKnowledge` primitive returns `/knowledge/` results (not platform_content fallback)
- [ ] `QueryKnowledge` still returns external platform data via fallback
- [ ] No `platform_content` rows with `platform='yarnnn'` exist
- [ ] `Search(scope="platform_content", platform="yarnnn")` removed — no longer valid
- [ ] Frontend `/context/yarnnn` page removed or redirected
- [ ] System status / admin metrics reflect `/knowledge/` file counts
- [ ] End-to-end: Agent A produces digest → stored in `/knowledge/digests/` → Agent B's `QueryKnowledge` finds it

## What This Supersedes

- **ADR-102** (yarnnn Content Platform): `platform="yarnnn"` rows in `platform_content` replaced by `/knowledge/` filesystem. The recursion loop now goes through structured files, not flat table rows.
- **Content dump pattern**: `get_content_summary_for_generation()` retired in Phase 2. All agents use tool-driven consumption.

## What This Does NOT Change

- **`platform_content` table**: Stays as-is for external platform data. Sync pipeline unchanged.
- **Agent intelligence** (ADR-106): `/agents/{slug}/` workspace files unchanged.
- **Delivery pipeline**: External delivery (email, Slack post) unchanged. Internal knowledge filing is an addition.
- **Retention for external data**: TTL-based retention for platform_content unchanged.
