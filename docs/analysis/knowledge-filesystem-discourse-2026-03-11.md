# Knowledge Filesystem Architecture — Design Discourse

**Date:** 2026-03-11
**Context:** Post ADR-106 Phase 1 completion (workspace as singular source of truth for agent intelligence). This discourse explores extending the filesystem model to agent-produced knowledge and its implications for agent types, actions, and the platform content architecture.
**Leads to:** ADR-107 (Knowledge Filesystem Architecture)

---

## Starting Point: The platform_content Question

After completing ADR-106 Phase 1 (agent intelligence migrated to workspace files), a natural question emerged: should `platform_content` — the table holding synced Slack, Gmail, Notion, Calendar data — also migrate to the workspace filesystem?

### Initial Assessment

Three options were considered:

**A. Leave it.** `platform_content` stays as-is. Workspace = agent brain. `platform_content` = shared perception layer. Two separate systems.

**B. Change consumption model.** `platform_content` schema stays, but agents pull from it via tools (like AnalystStrategy already does) instead of receiving a content dump in their prompt. No structural change to the table.

**C. Materialize into workspaces.** Platform content gets written to workspace files under `/knowledge/` paths. Agents read files, not table rows.

**Decision: B for external content, filesystem for yarnnn-produced content.** The schema for external platform data is fine — it's raw, TTL-managed, and well-indexed. The problem is how agent-produced content (yarnnn outputs) flows back into the shared context pool.

---

## The Recursive Knowledge Problem

YARNNN's core architectural thesis (ADR-072) is accumulation — the system gets smarter over time by accumulating context across platforms. ADR-102 extended this by writing agent outputs back into `platform_content` with `platform="yarnnn"`, closing the loop:

```
Platform data → Agent reads → Agent produces output → Output enters platform_content → Future agents read it
```

This recursion is the moat. But the current implementation is flat — yarnnn outputs are stored as undifferentiated `platform_content` rows with no structured metadata about:
- Which agent produced it and why
- What version of an output it represents
- Whether it supersedes a previous version
- What content class it belongs to (research, digest, analysis, brief)
- What confidence level or provenance chain it carries

A Slack message from `#general` and a research paper produced by a deep_research agent look structurally identical in `platform_content`. Downstream agents searching the shared pool can't distinguish between them without reading the full text.

### Why This Matters

When Agent B searches platform_content and finds a research paper from Agent A:
- Is this the latest version or a stale one?
- Was it superseded by a follow-up?
- What was the research question that prompted it?
- Should Agent B trust this as curated knowledge or treat it as raw data?

The flat table model forces all this reasoning into the LLM prompt. A filesystem model makes it structural.

---

## The Insight: Filesystem for Agent-Produced Knowledge

The filesystem model already proven for agent intelligence (AGENT.md, memory/) extends naturally to agent-produced knowledge. The key distinction:

| Concern | Storage | Model | Lifecycle |
|---------|---------|-------|-----------|
| **External data** (Slack, Gmail, etc.) | `platform_content` table | Flat rows, TTL-managed | Ephemeral (14-90d retention) |
| **Agent intelligence** (instructions, memory) | `workspace_files` under `/agents/{slug}/` | Filesystem, private | Persistent, agent-owned |
| **Agent-produced knowledge** | `workspace_files` under `/knowledge/` | Filesystem, shared | Persistent, version-aware |

The `/knowledge/` filesystem is the third storage domain — shared across agents, structurally organized, version-aware, and persistent. It's where the accumulation moat materializes as inspectable, navigable files.

### Proposed Filesystem Shape

```
workspace_files
  ├── /agents/{slug}/                    ← PRIVATE agent intelligence (ADR-106)
  │     AGENT.md
  │     memory/
  │       observations.md
  │       review-log.md
  │       goal.md
  │       state.md
  │     thesis.md
  │
  └── /knowledge/                        ← SHARED accumulated knowledge (NEW)
        ├── research/
        │     {topic-slug}/
        │       latest.md                ← current version
        │       v1.md, v2.md             ← historical (opt-in)
        │       metadata.json            ← provenance, agent_id, tags
        ├── digests/
        │     {source}-{date}.md         ← platform-specific recaps
        ├── analyses/
        │     {topic-slug}.md            ← cross-platform synthesis
        ├── briefs/
        │     {event-slug}.md            ← meeting prep, event context
        └── insights/
              {topic-slug}.md            ← proactive findings
```

---

## Stress Testing

### Metadata and Data Handling
Flat `platform_content` rows can't express relationships (supersession, provenance, versioning). A filesystem can — through directory structure, naming conventions, and metadata files. `/knowledge/research/openai-feature/v2.md` inherently communicates lineage. Structure IS metadata.

### Versioning Noise
Flat table: v1, v2, v3 all return in search results. Agent must parse which is current.
Filesystem: directory structure makes lineage explicit. `latest.md` or overwrite semantics keep the canonical version obvious.

### Trigger Chain and Recursion
The accumulation loop becomes traceable:
1. Slack mention about OpenAI feature → platform_content (external)
2. Research agent reads platform_content → writes `/knowledge/research/openai-feature/latest.md`
3. Synthesis agent searches `/knowledge/` → reads the research → writes `/knowledge/analyses/ai-landscape-q1.md`
4. Each step has a clear path. Cycle detection becomes path-based provenance tracking.

### Action Outputs vs Knowledge Outputs
Actions (Slack drafts, webhook payloads) don't belong in `/knowledge/`. They route through the delivery layer. Only knowledge artifacts enter the shared filesystem. The filesystem boundary IS the content classification.

### Search Performance
`workspace_files` already has pgvector embeddings and full-text search indexes (migration 100). `/knowledge/` files get the same indexing. Semantic search across the knowledge filesystem works with existing infrastructure.

### Retention
External platform data: TTL-based (Slack 14d, Gmail 30d, etc.) — expires automatically.
Knowledge files: intelligence-based — superseded by newer versions, archived by content class rules, never arbitrarily expired.

### Future Expansibility
- **New integrations**: External data → `platform_content`. Agent outputs about those platforms → `/knowledge/`. No schema changes.
- **Multi-tenant/team**: `/knowledge/` becomes a shared team filesystem. Agent private state stays in `/agents/`. Permission model maps to path prefixes.
- **Agent-to-agent collaboration**: Agent A writes to `/knowledge/research/topic/`. Agent B reads it. The filesystem IS the communication protocol.
- **Export/portability**: A filesystem of markdown files is inherently portable and human-readable.
- **MCP/A2A interop**: MCP resources map to file paths. Knowledge files are protocol-native.

---

## The OS Analogy

The architecture maps to an operating system model:

```
/agents/           = /home/          (per-user private state)
/knowledge/        = /var/shared/    (shared knowledge filesystem)
platform_content   = /dev/           (device drivers — raw external I/O)
delivery layer     = /proc/          (system services — actions, routing)
TP (orchestrator)  = shell           (user interface to the system)
```

Agents are processes. The workspace is the filesystem. `platform_content` is the hardware abstraction layer for external platforms. The delivery pipeline is the system services layer. This is an **agent-native operating system** where the filesystem is the universal interface.

---

## Implications for Agent Types

This architectural foundation suggests a natural two-tier agent model:

**Platform Agents** — Platform-specific, read from `platform_content`, produce platform-aware knowledge:
- Slack Recap Agent → writes to `/knowledge/digests/slack-{channel}-{date}.md`
- Gmail Digest Agent → writes to `/knowledge/digests/gmail-{label}-{date}.md`
- Calendar Brief Agent → writes to `/knowledge/briefs/{event}.md`
- Notion Watcher → writes to `/knowledge/insights/notion-{topic}.md`

**Synthesis Agents** — Platform-agnostic, read from `/knowledge/` (digested context), produce cross-cutting analysis:
- Work Status → reads multiple `/knowledge/digests/` → writes `/knowledge/analyses/status-{date}.md`
- Research Agent → reads `/knowledge/` + web → writes `/knowledge/research/{topic}/latest.md`
- Meeting Prep → reads `/knowledge/briefs/` + `/knowledge/insights/` → synthesizes

This isn't a rigid taxonomy — it's an emergent pattern. The filesystem structure makes the data flow self-documenting.

---

## Implications for Actions

The action model stays separate from the knowledge filesystem:

- **Text output** (today): markdown → deliver via email/Slack/stored doc
- **Draft action** (future): compose platform-specific draft → stage for approval → execute
- **Webhook/trigger** (future): structured payload → external system
- **Agent spawn** (exists): coordinator creates child agents

Actions route through the delivery layer. Only knowledge artifacts enter `/knowledge/`. This keeps the recursion loop clean — only curated intelligence feeds back into the shared context, not side-effects.

---

## Recursion Point: Where Outputs Enter /knowledge/

The critical design decision: agent outputs enter `/knowledge/` **at delivery time, not at generation time**. The existing pipeline:

```
Agent generates → draft in agent_runs → user approves (or auto-approve) → delivered
```

Extended:

```
→ delivered → knowledge artifact written to /knowledge/{class}/{topic}/latest.md
```

This means:
1. Only approved/delivered outputs enter the shared knowledge base
2. Users control what enters the accumulation loop
3. Draft/rejected outputs never pollute the shared context
4. The delivery layer handles both external delivery (email, Slack) and internal knowledge filing

---

## Relationship to Existing ADRs

- **ADR-072** (Unified Content Layer): `platform_content` retains its role for external data. The accumulation thesis extends to `/knowledge/` for agent-produced data.
- **ADR-102** (yarnnn Content Platform): Currently writes flat `platform="yarnnn"` rows. This would be superseded — agent outputs go to `/knowledge/` filesystem instead.
- **ADR-106** (Agent Workspace Architecture): Phase 1 complete (agent intelligence). This discourse defines the direction for Phase 2 (knowledge filesystem).
- **ADR-092** (Agent Intelligence & Mode Taxonomy): Platform agents and synthesis agents emerge as natural categories from the filesystem architecture.
- **ADR-093** (Agent Type Taxonomy): Agent types may need restructuring around platform-specific vs. synthesis distinction.

---

## Open Questions

1. **Migration path**: Existing `platform="yarnnn"` rows in `platform_content` — migrate to `/knowledge/` or let them TTL-expire?
2. **Auto-approve agents**: Recurring agents that auto-approve skip user review. Their outputs still enter `/knowledge/`? Probably yes — the auto-approve setting IS the user's consent.
3. **Knowledge file naming conventions**: How to derive topic slugs, handle collisions, manage directory depth?
4. **Coordinator orchestration**: When a coordinator spawns child agents that produce knowledge, how does the coordinator's `/knowledge/` relate to children's?
5. **TP access to /knowledge/**: Does the orchestrator (TP) search `/knowledge/` alongside `platform_content`? Probably yes — unified search across both.
6. **Embedding strategy**: Should `/knowledge/` files get embeddings on write (like `platform_content`)? Yes — same `workspace_files` infrastructure supports this.
