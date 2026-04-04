# Context

> Layer 3 of 4 in the YARNNN four-layer model (ADR-063)
> **Updated**: 2026-04-03 — cleanup after ADR-153/156; stale sync-era references removed

---

## What it is

Context is the accumulated knowledge substrate that agents build up over time.
It lives in the workspace filesystem — primarily `/workspace/context/`
(domain-structured accumulated intelligence) and `/workspace/uploads/`
(user-contributed reference material).

Platform connections are adjacent to context, not part of context itself.
They provide auth, discovery, and source selection. YARNNN no longer maintains a
bulk-synced platform cache as a context layer.

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
- Not a bulk-synced platform cache — `platform_content` is sunset (ADR-153)

---

## Table Schema

### `platform_connections` — OAuth credentials and integration state

Stores encrypted OAuth tokens, platform metadata, discovered landscape, and
selected sources per platform per user. Still active — provides auth
infrastructure and source boundaries for platform access.

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

### Accumulated Context Domains (ADR-151, ADR-158)

`/workspace/context/` holds accumulated context. Two classes of domains:

**Canonical domains** — durable, steward-owned:

| Domain | Path | Content |
|--------|------|---------|
| Competitors | `/workspace/context/competitors/` | Competitive intelligence |
| Market | `/workspace/context/market/` | Market trends, industry data |
| Relationships | `/workspace/context/relationships/` | Key contacts, stakeholders |
| Projects | `/workspace/context/projects/` | Internal project context |
| Content | `/workspace/context/content/` | Content strategy, brand voice |
| Signals | `/workspace/context/signals/` | Notable events, triggers |

**Temporal domains** (ADR-158) — bot-owned, platform observations:

| Domain | Path | Content | Bot |
|--------|------|---------|-----|
| Slack | `/workspace/context/slack/` | Per-channel observations | Slack Bot |
| Notion | `/workspace/context/notion/` | Per-page observations | Notion Bot |
| GitHub | `/workspace/context/github/` | Per-repo observations (deferred) | GitHub Bot |

Canonical domains are populated by TP inference (ADR-144) and domain steward agent execution. Temporal domains are populated by platform bot digest tasks. TP sees both via working memory injection, but temporal domains are explicitly marked as non-canonical.

This cognitive context is injected as `mandate_context` in the agent's prompt.
It answers "what am I supposed to contribute?" rather than "what data is
available?"

### `sync_registry` — Resource coverage / legacy bookkeeping

Tracks per-resource timestamps, counts, exclusions, and error state for connected
platform resources. It remains in use for coverage and status surfaces, but it is
not evidence of an active generic sync pipeline.

---

## How content is accessed

**Chat mode** (TP primitives):
- `Search` — semantic search across workspace files (accumulated context, uploads, agent memory)
- `Read` — direct file read by path
- live `platform_*` tools — direct platform reads/actions when an integration is connected
- `WebSearch` — external web search

**Headless mode** (agent execution):
- `Search`, `ReadWorkspace`, `SearchWorkspace`, `QueryKnowledge` — workspace-scoped reads
- Agents gather context from `/workspace/context/` domains, prior task outputs, and task-owned files
- Platform monitoring task types exist in the task registry, but platform access should be treated as task-scoped workflow logic rather than a generic cached context layer

**Context UI** — `/context` surfaces:
- **Identity** (workspace identity and brand)
- **Documents** (uploaded reference material)
- **Context domains** (accumulated intelligence in `/workspace/context/`)

---

## Platform Integrations

All platforms use direct API clients — no bulk sync cache, no platform content
table in the active execution path.

| Platform | Client | What agents can access |
|---|---|---|
| Slack | `SlackAPIClient` direct REST | Channel history, thread replies, user profiles |
| Notion | `NotionAPIClient` direct REST | Page content, database rows |
| GitHub | `GitHubClient` direct REST | Issues, PRs from selected repos (ADR-147) |

> **ADR-131**: Gmail and Calendar sunset. `GoogleAPIClient` removed.

---

## The accumulation moat

Agents process external signals and write structured context to
`/workspace/context/` domains. Over time, the workspace accumulates:
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
| Is there a platform content cache? | No — `platform_content` is sunset (ADR-153). |
| Where does accumulated context live? | `/workspace/context/` domains — structured by the domain registry (ADR-151) |
| Can a document upload add Memory entries? | Not automatically. "Promote document to Memory" is a deferred feature |

---

## Related

- [ADR-072](../adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) — Unified content layer and TP execution pipeline
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Four-layer model
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
- [context-pipeline.md](../architecture/context-pipeline.md) — Technical pipeline detail
- [PLATFORM-INTEGRATIONS.md](../integrations/PLATFORM-INTEGRATIONS.md) — platform connection model
