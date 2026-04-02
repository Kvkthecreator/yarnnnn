# Context

> Layer 3 of 4 in the YARNNN four-layer model (ADR-063)
> **Updated**: 2026-04-02 — ADR-155 workspace-wide inference; context page as onboarding surface
> Previous: 2026-03-31 — ADR-153 platform_content sunset; context flows through tracking tasks

---

## What it is

Context is the accumulated knowledge substrate that agents build up over time. It lives in the workspace filesystem — primarily `/workspace/context/` (domain-structured accumulated intelligence) and `/workspace/uploads/` (user-contributed reference material).

**Platform data flows through tracking tasks.** Connect a platform (Slack, Notion, GitHub) → create a monitoring task → the assigned agent calls platform APIs live during execution → accumulated context builds in `/workspace/context/` domains. There is no intermediate staging table (ADR-153: `platform_content` sunset).

Context is never injected wholesale into the TP system prompt. It is fetched on demand, during a session, via TP primitives (`Search`, `Read`, `GetSystemState`).

**Analogy**: Context is the filesystem that Claude Code reads — source files exist on disk, but only the relevant ones are opened and read when needed. YARNNN's "disk" is the accumulated workspace context, enriched by agent execution over time.

---

## Context Page as Onboarding Surface (ADR-155)

During workspace setup (identity empty/sparse, no tasks), the context page (`/context`) is the **landing surface**. The TP inference component is front and center — wide layout, no sidebar distractions.

When the user provides identity context (text, URL, doc), workspace-wide inference triggers:
- ALL context domains scaffold simultaneously (competitors, market, relationships, projects, content)
- Entity stubs populate with inferred content + `[Needs research]` gaps
- The user watches folders appear and stubs populate in real time
- TP narrates: "Found 4 competitors and 2 market segments. Adjust?"

Three workspace maturity phases determine routing:
- **Setup** (identity empty) → `/context` is home, `/tasks` shows empty state
- **Scaffolded** (identity rich, domains seeded) → `/context` is home, TP suggests tasks
- **Active** (tasks exist) → `/tasks` is home (normal operation)

---

## What it is not

- Not stable user knowledge — that is Memory (`user_memory`)
- Not a log of YARNNN's actions — that is Activity (`activity_log`)
- Not generated output — that is Work (`agent_runs`, `/tasks/{slug}/outputs/`)
- Not pre-loaded into the TP prompt — TP fetches it on demand
- Not a bulk-synced platform cache — `platform_content` table is sunset (ADR-153)

---

## The `platform_content` table — DEPRECATED (ADR-153)

> **Sunset.** The `platform_content` table and its bulk sync pipeline are deprecated. Platform data now flows through tracking tasks: agents call platform APIs live during execution and write structured context to `/workspace/context/` domains. The table may still contain legacy data but is no longer written to or read from by the active execution pipeline.

---

## Table Schema

### `platform_content` — DEPRECATED (ADR-153)

Legacy bulk-synced platform content table. No longer written to or read from by the active pipeline. Schema retained for reference only. See ADR-153 for migration details.

### `platform_connections` — OAuth credentials and settings

Stores encrypted OAuth tokens, sync preferences, selected sources, and last_synced_at per platform per user. Still active — provides auth infrastructure for live API calls during agent execution.

### `workspace_files` — Primary context substrate

All accumulated context lives here as workspace files:
- `/workspace/context/{domain}/` — accumulated intelligence domains (competitors, market, relationships, etc.)
- `/workspace/uploads/` — user-uploaded reference material
- `/agents/{slug}/memory/` — agent knowledge and reflections
- `/tasks/{slug}/outputs/` — task execution outputs

Searchable via `Search` primitive — semantic vector search over workspace content.

### Agent Cognitive Files — Self-Awareness Context (ADR-128, ADR-149)

In addition to external platform data and shared knowledge, agents read **cognitive context** from workspace files during headless execution:

| What the agent reads | Source path | Purpose |
|---------------------|-------------|---------|
| Own last reflection | `/agents/{slug}/memory/reflections.md` | Reflect on whether conditions changed since last run |
| User directives | `/agents/{slug}/memory/directives.md` | Durable user guidance from conversation |
| Task feedback | `/tasks/{slug}/memory/feedback.md` | Accumulated user feedback distilled from edits |
| Task steering | `/tasks/{slug}/memory/steering.md` | TP/user steering directives for next run |

### Accumulated Context Domains (ADR-151)

`/workspace/context/` holds accumulated context shared across all tasks and agents. Six domains:

| Domain | Path | Content |
|--------|------|---------|
| Competitors | `/workspace/context/competitors/` | Competitive intelligence |
| Market | `/workspace/context/market/` | Market trends, industry data |
| Relationships | `/workspace/context/relationships/` | Key contacts, stakeholders |
| Projects | `/workspace/context/projects/` | Internal project context |
| Content | `/workspace/context/content/` | Content strategy, brand voice |
| Signals | `/workspace/context/signals/` | Notable events, triggers |

Context domains are populated by TP inference (ADR-144) and agent execution, providing shared grounding that enriches all task outputs.

This cognitive context is injected as `mandate_context` in the agent's prompt — presented alongside gathered platform/knowledge context. It answers "what am I supposed to contribute and how does PM evaluate the project?" rather than "what data is available?"

The three context substrates (external platforms, internal knowledge, agent cognition) are peer layers — each contributes to the agent's situational awareness. See [FOUNDATIONS.md](../architecture/FOUNDATIONS.md) Axiom 2 for the three intelligence substrates.

### `sync_registry` — Per-resource sync state (legacy)

Tracks cursor and last_synced_at per `(user_id, platform, resource_id)`. Legacy table from the bulk sync era — may still be used for OAuth health checks.

---

## How content is accessed

**Chat mode** (TP primitives):
- `Search` — semantic search across workspace files (accumulated context, uploads, agent memory)
- `Read` — direct file read by path
- `RefreshPlatformContent(platform="...")` — live platform API call for fresh data
- `WebSearch` — external web search

**Headless mode** (agent execution):
- `Search`, `ReadWorkspace`, `SearchWorkspace`, `QueryKnowledge` — workspace-scoped reads
- `RefreshPlatformContent` — live platform API calls during execution
- Agents gather context from `/workspace/context/` domains, prior task outputs, and live API calls

**Context UI** — `/context` surfaces:
- **Identity** (workspace identity and brand)
- **Documents** (uploaded reference material)
- **Context domains** (accumulated intelligence in `/workspace/context/`)

---

## Platform Integrations

All platforms use Direct API clients — no MCP, no gateway (ADR-076). Agents call these APIs live during task execution (ADR-153).

| Platform | Client | What agents can access |
|---|---|---|
| Slack | `SlackAPIClient` direct REST | Channel history, thread replies, user profiles |
| Notion | `NotionAPIClient` direct REST | Page content, database rows |
| GitHub | `GitHubClient` direct REST | Issues, PRs from selected repos (ADR-147) |

> **ADR-131**: Gmail and Calendar sunset. `GoogleAPIClient` removed.

---

## The accumulation moat

Agents process external signals and write structured context to `/workspace/context/` domains. Over time, the workspace accumulates:
- Domain-structured intelligence (competitor profiles, market trends, relationship maps)
- Agent memory and reflections (learned preferences, domain theses)
- Task outputs (deliverables, research artifacts)

This is how YARNNN builds intelligence over time. A user with 6 months of agent history has a rich workspace of accumulated context that compounds with each execution cycle.

**Key insight**: Agents decide what matters. Raw platform data is ephemeral — structured context in the workspace is the compounding moat.

---

## Boundaries

| Question | Answer |
|---|---|
| Does TP get context in its system prompt? | No — Context is fetched on demand via primitives, never pre-loaded |
| Is there a platform content cache? | No — `platform_content` is sunset (ADR-153). Agents call platform APIs live during execution. |
| Where does accumulated context live? | `/workspace/context/` domains — structured by the domain registry (ADR-151) |
| Can a document upload add Memory entries? | Not automatically. "Promote document to Memory" is a deferred feature |

---

## Related

- [ADR-072](../adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) — Unified content layer and TP execution pipeline
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Four-layer model
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
- [context-pipeline.md](../architecture/context-pipeline.md) — Technical pipeline detail
- `api/services/platform_content.py` — Unified content service
- `api/workers/platform_worker.py` — sync worker
- `api/services/primitives/search.py` — `Search(scope="platform_content")`
