# Primitives Architecture

> **Status**: ⚠️ STALE — this document predates ADR-138 (project layer collapse, 2026-03-25). It still references projects, PM primitives, agent_chat mode, CreateProject, AdvanceAgentSchedule, and entity schemas that no longer exist. **See [ADR-146](../adr/ADR-146-primitive-hardening.md) for the consolidation plan.** This doc will be rewritten as part of ADR-146 Gate 3.
>
> **Created**: 2026-02-10
> **Updated**: 2026-03-20 (primitive cleanup — dead weight removed, role-gated agent_chat, three-mode architecture)
> **Related ADRs**: ADR-059, ADR-072, ADR-080 (Unified Agent Modes), ADR-106 (Workspace), ADR-116 (Inter-Agent), ADR-118 (Skills/Output Gateway), ADR-138 (Agents as Work Units), ADR-141 (Unified Execution), ADR-146 (Primitive Hardening)
> **Implementation**: `api/services/primitives/`

---

## Overview

Primitives are the universal operations available to YARNNN agents for interacting with infrastructure. They operate across three modes:

- **chat** — TP (Orchestrator) in user-facing conversation
- **headless** — Background agent execution (scheduled runs, Composer)
- **agent_chat** — Agents participating in project meeting rooms (ADR-124)

### Design Principles

1. **Minimal Surface** — 25 primitives across three modes (was 27; Todo + Respond removed 2026-03-20)
2. **Universal Reference Syntax** — Consistent `type:identifier` addressing
3. **Composable** — Primitives combine for complex operations
4. **Self-Describing** — Results include context for further action
5. **Mode-Gated** — Each primitive declares which modes it supports (ADR-080)
6. **Role-Gated** — Within agent_chat, PM-only write primitives enforced at runtime (ADR-124)

### Context Architecture (ADR-059, ADR-072)

YARNNN uses a four-layer model (ADR-063):

| Layer | Table | Purpose |
|-------|-------|---------|
| **Memory** | `user_memory` | User facts, preferences, patterns |
| **Activity** | `activity_log` | System provenance (what YARNNN has done) |
| **Context** | `platform_content` | Synced platform data with retention-based accumulation |
| **Work** | `agent_runs` | Generated content outputs |

**Context Sources** (all first-class):

| Source | Storage | Entry Point | Searchable |
|--------|---------|-------------|------------|
| **Platforms** | `platform_content` | OAuth → Sync Worker | `scope="platform_content"` |
| **Documents** | `filesystem_documents` + `filesystem_chunks` | File upload | `scope="document"` |
| **Memory** | `user_memory` | Nightly extraction + user edits | `scope="memory"` |

Users without platform connections can still provide rich context via documents and direct statements. Memory is extracted implicitly from conversations (ADR-064).

---

## The 25 Primitives

### Core Data Operations (chat + headless)

| Primitive | Purpose | Modes |
|-----------|---------|-------|
| **Read** | Get single entity by ref | chat, headless |
| **Write** | Create new entity | chat |
| **Edit** | Modify existing entity | chat |
| **List** | Find entities by pattern | chat, headless |
| **Search** | Find by content (text search) | chat, headless |

### External Operations

| Primitive | Purpose | Modes |
|-----------|---------|-------|
| **Execute** | Orchestration actions (generate, publish, acknowledge, schedule) | chat |
| **RefreshPlatformContent** | Sync latest platform data | chat, headless |
| **WebSearch** | Search the web (Anthropic native tool) | chat, headless |

### User & System

| Primitive | Purpose | Modes |
|-----------|---------|-------|
| **SaveMemory** | Persist user-stated fact to workspace memory | chat |
| **list_integrations** | Discover connected platforms + metadata | chat |
| **GetSystemState** | System introspection (sync status, health) | chat, headless |
| **Clarify** | Ask user for input | chat, agent_chat |

### Agent Lifecycle (ADR-111, ADR-122)

| Primitive | Purpose | Modes |
|-----------|---------|-------|
| **CreateAgent** | Create new agent (unified path via `create_agent_record()`) | chat, headless |
| **CreateProject** | Create project — title-only (auto-infers agent type + lifecycle), type_key (platform digests), or explicit (custom agents). ADR-132. | chat, headless |
| **AdvanceAgentSchedule** | Set agent's next_pulse_at to now | headless |

### Agent Workspace (ADR-106, ADR-116)

| Primitive | Purpose | Modes |
|-----------|---------|-------|
| **ReadWorkspace** | Read file from agent's workspace | headless, agent_chat |
| **WriteWorkspace** | Write file to agent's workspace | headless, agent_chat |
| **SearchWorkspace** | Full-text search within workspace | headless, agent_chat |
| **QueryKnowledge** | Search /knowledge/ base with metadata filters | headless, agent_chat |
| **ListWorkspace** | List workspace files | headless, agent_chat |
| **DiscoverAgents** | Find agents by role/scope/status | headless, agent_chat |
| **ReadAgentContext** | Read another agent's workspace (cross-agent) | headless, agent_chat |

### Project Execution (ADR-119, ADR-120, ADR-124)

| Primitive | Purpose | Modes | Role Gate |
|-----------|---------|-------|-----------|
| **ReadProject** | Read project charter | chat, headless, agent_chat | — |
| **CheckContributorFreshness** | Check contributor output freshness | headless, agent_chat | — |
| **ReadProjectStatus** | Full project state (charter + freshness + work plan) | headless, agent_chat | — |
| **RequestContributorAdvance** | Advance contributor agent's schedule | headless, agent_chat | **PM only** |
| **UpdateWorkPlan** | Update PM's work plan | headless, agent_chat | **PM only** |

### Role Gating (ADR-124)

In `agent_chat` mode, **read primitives are open to all agents** — any agent can check project status and contributor freshness. **Write/coordination primitives are PM-only** — `RequestContributorAdvance` and `UpdateWorkPlan` return `not_authorized` for non-PM agents. Principle: anyone can check the board, only PM moves the tickets.

### Removed Primitives

- **Todo** — removed 2026-03-20. Conversation stream is the progress indicator (Claude Code pattern).
- **Respond** — removed 2026-03-20. TP's natural text output serves as the response.
- **Execute(agent.approve)** — removed 2026-03-20. ADR-066 removed approval gates; handler also had a bug.
- **Execute(memory.extract)** — removed 2026-03-20. ADR-064 moved extraction to nightly cron.

> **list_integrations** returns `authed_user_id` (Slack), `designated_page_id` (Notion). Call this first before any platform tool to get the correct IDs for default landing zones.

---

## Reference Syntax

All entity references follow a consistent grammar:

```
<type>:<identifier>[/<subpath>][?<query>]
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `type` | Entity type | `agent`, `platform_content`, `platform` |
| `identifier` | Entity ID or special | UUID, `new`, `latest`, `*` |
| `subpath` | Nested access | `/credentials`, `/sources/0` |
| `query` | Filter parameters | `?status=active&limit=10` |

### Entity Types

YARNNN uses a tiered entity model. **TP-facing** entities are directly addressable by the Thinking Partner. **Background** entities are infrastructure that TP doesn't directly manipulate.

#### TP-Facing Entities (5)

| Type | Table | Description |
|------|-------|-------------|
| `agent` | `agents` | Recurring content outputs with scoped instructions + memory |
| `platform` | `platform_connections` | Connected platforms (by provider name) |
| `document` | `documents` | Uploaded documents |
| `session` | `chat_sessions` | Chat sessions (scoped via `agent_id`) |
| `action` | (virtual) | Available actions for Execute |

> **ADR-090 Note**: `work` entity removed — `work_tickets` table dropped. Agent execution audit trail migrated to `activity_log`.

#### Background Entities (Infrastructure)

| Type | Table | Description | Notes |
|------|-------|-------------|-------|
| `memory` | `workspace_files /memory/` | User facts, preferences, patterns | Auto-injected into context via working memory. TP can write via SaveMemory (ADR-108) |
| `platform_content` | `platform_content` | Synced platform data | Retention-based accumulation (ADR-072) |

> **ADR-108 Note**: Memory is stored in `/memory/` files (MEMORY.md, preferences.md, notes.md) within `workspace_files`. TP can persist user-stated facts via the `SaveMemory` primitive (chat-mode only). Nightly cron extracts implicit facts from conversations. Users manage all entries via the Memory page.
>
> **ADR-042 Note**: TP operates on 6 first-class entities. Memory and platform_content are background infrastructure—automatically injected into context, not directly queried by TP during normal operation.

### Entity Schemas

Each entity type has a defined schema. Key fields are shown for display purposes.

#### agent

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `title` | string | Agent name | ✓ Primary |
| `status` | enum | `active`, `paused`, `archived` | ✓ Badge |
| `mode` | enum | `recurring` \| `goal` | ✓ Badge |
| `schedule` | JSONB | `{frequency, day, time, timezone}` | ✓ Frequency |
| `sources` | JSONB[] | Data source configs | — |
| `destination` | JSONB | `{platform, target}` | — |
| `next_pulse_at` | timestamp | Next scheduled pulse | — |
| `agent_instructions` | TEXT | Agent behavioral instructions (user-editable) | — |
| `agent_memory` | JSONB | `{observations: [{date, source, note}], goal: {description, status, milestones}}` | — |

**Display Priority:** `title` > `status` > `mode` > `schedule.frequency`

> **ADR-087 Note**: `agent_instructions` and `agent_memory` are scoped to each agent and injected into the headless generation prompt. Memory is system-accumulated; use `Edit(append_observation)` or `Edit(set_goal)` — never write raw `agent_memory`. See Edit spec below.

#### platform_content

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `platform` | string | Source platform (slack, notion, yarnnn) | ✓ Badge |
| `resource_name` | string | Channel/folder/page name | ✓ Primary |
| `content` | string | The imported content | ✓ Truncated |
| `content_type` | string | Type (message, email, page, etc.) | — |
| `source_timestamp` | timestamp | When content was created on platform | — |
| `expires_at` | timestamp | TTL for ephemeral content | — |
| `platform_metadata` | JSONB | Platform-specific data | — |

**Display Priority:** `resource_name` > `platform` > `content` (truncated)

#### memory (User Context — ADR-059)

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `key` | string | Unique identifier within category | ✓ Primary |
| `content` | string | The memory content | ✓ Primary |
| `category` | string | Classification (preference, business_fact, work_pattern, etc.) | ✓ Badge |
| `importance` | float | 0.0–1.0 retrieval weight | — |
| `source_type` | string | `extracted`, `explicit` | — |
| `confidence` | float | 0.0–1.0 extraction confidence | — |

**Display Priority:** `content` (truncated) > `category`

**How memories are created** (ADR-108):
- `SaveMemory` primitive — TP persists user-stated facts in real time (chat-mode only)
- Nightly extraction from TP conversations (automatic, midnight UTC cron)
- User edits via Memory page (manual)

#### document (Uploaded Files)

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `filename` | string | Original filename | ✓ Primary |
| `file_type` | string | Extension (pdf, docx, txt, md) | ✓ Badge |
| `file_size` | int | Size in bytes | — |
| `processing_status` | enum | `pending`, `processing`, `completed`, `failed` | ✓ Badge |
| `word_count` | int | Extracted word count | — |
| `page_count` | int | Page count (PDF only) | — |

**Display Priority:** `filename` > `file_type` > `processing_status`

**How to upload:** POST `/documents/upload` with multipart file (PDF, DOCX, TXT, MD up to 25MB)

**Processing pipeline:** Upload → Extract text → Chunk → Embed → Extract memories

#### platform

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `provider` | string | Platform name (slack, notion, etc.) | ✓ Primary |
| `status` | string | Connection status | ✓ Badge |
| `credentials` | JSONB | OAuth tokens (encrypted) | — |
| `settings` | JSONB | Platform-specific settings | — |

**Display Priority:** `provider` > `status`

#### session

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `created_at` | timestamp | Session start | ✓ Date |
| `messages` | JSONB[] | Chat history | — |
| `summary` | string | AI-generated summary | — |

**Display Priority:** `created_at` > `summary`

### Special Identifiers

| Identifier | Meaning | Used With |
|------------|---------|-----------|
| `new` | Create operation | Write |
| `current` | Current active entity | Session |
| `latest` | Most recently updated | Read, Edit |
| `*` | All entities (collection) | List |

### Examples

```
agent:uuid-123          # Specific agent
agent:latest            # Most recently updated agent
agent:*                 # All agents
agent:?status=active    # Active agents

platform:slack               # Slack integration (by provider)
platform:*/credentials       # All platforms, credentials subpath

platform_content:*           # All imported platform content
platform_content:?platform=slack&limit=20  # Slack content only

memory:*                     # User-stated facts (narrowed scope)
memory:?type=fact&limit=10   # Filtered user facts

action:*                     # All available actions
action:platform.*            # Platform actions only
```

---

## Primitive Specifications

### Read

Retrieve a single entity by reference.

**Input**:
```json
{
  "ref": "agent:uuid-123"
}
```

**Output**:
```json
{
  "success": true,
  "data": { "id": "uuid-123", "title": "Weekly Update", ... },
  "ref": "agent:uuid-123",
  "entity_type": "agent"
}
```

**Errors**:
- `missing_ref` — No ref provided
- `invalid_ref` — Malformed reference
- `not_found` — Entity doesn't exist

---

### Write

Create a new entity.

**Input**:
```json
{
  "ref": "agent:new",
  "content": {
    "title": "Weekly Status",
    "agent_type": "status_report"
  }
}
```

**Output**:
```json
{
  "success": true,
  "data": { "id": "new-uuid", "title": "Weekly Status", ... },
  "ref": "agent:new-uuid",
  "entity_type": "agent",
  "message": "Created agent: Weekly Status (weekly)"
}
```

**Required Fields by Type**:

| Type | Required |
|------|----------|
| `agent` | `title`, `agent_type` |
| `document` | `name` |

**Defaults Applied**:

| Type | Defaults |
|------|----------|
| `agent` | `status: active`, `frequency: weekly`, `mode: recurring` |

---

### Edit

Modify an existing entity.

**Input**:
```json
{
  "ref": "agent:uuid-123",
  "changes": {
    "status": "paused"
  }
}
```

**Output**:
```json
{
  "success": true,
  "data": { "id": "uuid-123", "status": "paused", ... },
  "ref": "agent:uuid-123",
  "changes_applied": ["status", "updated_at"]
}
```

**Immutable Fields** (cannot be edited):
- `id`, `user_id`, `created_at`

**Agent-specific editable fields** (ADR-087/091):
- `status` — `active` / `paused` / `archived`
- `agent_instructions` — plain text behavioral instructions for the agent
- `schedule` — update recurrence
- `destination` — update delivery target

**Agent memory writes — scoped operations only** (ADR-091):

Raw `agent_memory` writes are blocked. Use scoped keys instead:

```json
// Append an observation (never replaces existing observations)
{
  "ref": "agent:uuid-123",
  "changes": {
    "append_observation": { "note": "Q4 data is now finalized", "source": "user" }
  }
}

// Set or replace the goal object (observations untouched)
{
  "ref": "agent:uuid-123",
  "changes": {
    "set_goal": { "description": "...", "status": "in_progress", "milestones": ["..."] }
  }
}
```

Observations are capped at 20 most recent. For lightweight observation appends from conversation context, prefer `Execute(action="agent.acknowledge", ...)` — it's a single-call shorthand.

---

### List

Find entities by pattern (structural navigation).

**Input**:
```json
{
  "pattern": "agent:?status=active",
  "limit": 10,
  "order_by": "updated_at"
}
```

**Output**:
```json
{
  "success": true,
  "items": [
    { "id": "uuid-1", "title": "Weekly Update", ... },
    { "id": "uuid-2", "title": "Daily Digest", ... }
  ],
  "count": 2,
  "pattern": "agent:?status=active",
  "entity_type": "agent",
  "message": "Found 2 agent(s) (2 active)"
}
```

---

### Search

Find entities by content using text search.

**Input**:
```json
{
  "query": "database migration decisions",
  "scope": "platform_content",
  "platform": "slack",
  "limit": 10
}
```

**Output**:
```json
{
  "success": true,
  "results": [
    {
      "entity_type": "platform_content",
      "ref": "platform:slack:uuid-123",
      "platform": "slack",
      "resource_name": "#engineering",
      "data": { "content": "We decided to use Supabase...", ... },
      "score": 0.5
    }
  ],
  "count": 1,
  "query": "database migration decisions",
  "scope": "platform_content"
}
```

**Scopes**: `platform_content`, `document`, `agent`, `work`, `all`

**Platform Filter** (optional, for `platform_content` scope): `slack`, `notion`, `yarnnn`

> **Scope clarification**:
> - `platform_content` searches synced platform data (Slack/Notion) and agent outputs (`yarnnn`, ADR-102). If external content is stale/empty, use `RefreshPlatformContent` to sync latest (ADR-085).
> - `document` searches uploaded files (PDF, DOCX, TXT, MD)
> - `memory` is **not a valid scope** (ADR-065) — memory is already injected into working memory at session start. Passing `scope="memory"` returns an error.

---

### Execute

Trigger external operations on entities.

**Input**:
```json
{
  "action": "agent.generate",
  "target": "agent:uuid-123"
}
```

**Output**:
```json
{
  "success": true,
  "result": {
    "status": "staged",
    "version_id": "version-uuid",
    "version_number": 3
  },
  "action": "agent.generate",
  "target": "agent:uuid-123"
}
```

**Available Actions** (4 — cleaned up 2026-03-20):

| Action | Target Type | Description | Requires |
|--------|-------------|-------------|----------|
| `platform.publish` | `agent` | Publish agent content to platform | `via` |
| `agent.generate` | `agent` | Run content generation pipeline | — |
| `agent.schedule` | `agent` | Update agent schedule | — |
| `agent.acknowledge` | `agent` | Append one observation from conversation context to workspace (lightweight, no generation) | `params.note` |

> **Removed actions**: `agent.approve` (ADR-066 removed approval gates), `memory.extract` (ADR-064 moved to nightly cron), `signal.process` (ADR-092 dissolved signals), `platform.sync` / `platform.send` / `work.run` (replaced by dedicated primitives).

**`agent.acknowledge` vs `Edit(append_observation)`:**
- `acknowledge` — TP calls this during chat when the user says something worth persisting ("note that Q4 is finalized"). Single call, source="user", immediate.
- `append_observation` via Edit — more explicit, allows setting `source` field, can be chained with other changes. Use when you want fine-grained control.

---

### RefreshPlatformContent (ADR-085)

Synchronous write-through cache refresh. Calls the same `_sync_platform_async()` worker pipeline as the scheduler, but awaited within the chat turn.

**Input**:
```json
{
  "platform": "slack"
}
```

**Output** (fresh sync):
```json
{
  "success": true,
  "platform": "slack",
  "items_synced": 42,
  "refreshed_at": "2026-02-28T10:30:00Z",
  "message": "Refreshed slack: 42 items synced. Use Search(scope='platform_content', platform='slack') to query."
}
```

**Output** (skipped — already fresh):
```json
{
  "success": true,
  "platform": "slack",
  "items_synced": 0,
  "skipped": true,
  "existing_items": 150,
  "message": "slack content is fresh (synced within 30min). 150 items available."
}
```

**Supported platforms**: `slack`, `notion` (not `yarnnn` — agent outputs are written internally, not synced)

> **ADR-131**: Gmail and Calendar sunset. Only Slack and Notion remain as connected platforms.

**Mode**: Chat only (`["chat"]`). Headless mode uses `freshness.sync_stale_sources()` instead.

**Staleness threshold**: 30 minutes — skips re-sync if content was fetched recently.

---

### SaveMemory (ADR-108)

Persist a user-stated fact, preference, or instruction to `/memory/notes.md`.

**Input**:
```json
{
  "content": "Prefers bullet points over prose",
  "entry_type": "preference"
}
```

**Output**:
```json
{
  "success": true,
  "message": "Remembered: Prefers bullet points over prose",
  "entry_type": "preference"
}
```

**Entry types**: `fact` (about the user), `preference` (how they like things), `instruction` (standing directive). Default: `fact`.

**Mode**: Chat only (`["chat"]`). Not available in headless mode.

**Deduplication**: Checks existing notes before adding (case-insensitive content match). Returns `already_exists: true` if duplicate.

**Scope**: Add-only. Users manage existing entries (edit, delete) via the Memory page.

---

### Clarify

Ask the user for input before proceeding.

**Input**:
```json
{
  "question": "Which channel should I use as the source?",
  "options": ["#acme-eng", "#acme-product", "#general"]
}
```

**Output**:
```json
{
  "success": true,
  "question": "Which channel should I use as the source?",
  "options": ["#acme-eng", "#acme-product", "#general"],
  "ui_action": {
    "type": "CLARIFY",
    "data": { "question": "...", "options": [...] }
  }
}
```

---

## UI Actions

Primitives can return `ui_action` to trigger frontend behavior:

| Type | Purpose | Data |
|------|---------|------|
| `CLARIFY` | Show focused question | `question`, `options` |

---

## Error Response Format

All primitives return errors in consistent format:

```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable description",
  // Additional context varies by error type
}
```

Common error codes:
- `missing_ref`, `missing_pattern`, `missing_query`
- `invalid_ref`, `invalid_pattern`
- `not_found`
- `permission_denied`
- `unsupported_type`
- `execution_failed`

---

## Implementation

### File Structure

```
api/services/primitives/
├── __init__.py           # Module exports
├── refs.py               # Reference parser and resolver
├── registry.py           # Primitive registration, mode gating, Clarify + list_integrations handlers
├── read.py               # Read primitive
├── write.py              # Write primitive
├── edit.py               # Edit primitive
├── list.py               # List primitive
├── search.py             # Search primitive (text-based)
├── execute.py            # Execute primitive + action handlers (4 actions)
├── refresh.py            # RefreshPlatformContent (ADR-085)
├── save_memory.py        # SaveMemory (ADR-108)
├── web_search.py         # WebSearch (Anthropic native tool)
├── system_state.py       # GetSystemState
├── coordinator.py        # CreateAgent + AdvanceAgentSchedule (ADR-111)
├── workspace.py          # 7 workspace primitives (ADR-106, ADR-116)
├── runtime_dispatch.py   # RenderAsset — type-scoped asset production (ADR-130, was RuntimeDispatch)
├── project.py            # CreateProject + ReadProject (ADR-119, ADR-122)
└── project_execution.py  # 4 PM/project primitives (ADR-120)
```

### Execution Flow

```
TP Agent
    │
    ▼
execute_primitive(auth, name, input)
    │
    ▼
HANDLERS[name](auth, input)
    │
    ▼
Result dict with success, data, ui_action
```

### Integration with TP

```python
from services.primitives import PRIMITIVES, execute_primitive

# TP uses PRIMITIVES as tool definitions
self.tools = PRIMITIVES

# TP executes via unified handler
result = await execute_primitive(auth, tool_use.name, tool_use.input)
```

---

## Changelog

### 2026-03-20 — Primitive cleanup + three-mode architecture

- **Primitives reduced from 27 to 25**: Removed Todo (dead weight — conversation is progress), Respond (redundant with model output).
- **Execute actions reduced from 6 to 4**: Removed `agent.approve` (ADR-066 removed approval gates; handler had `run_id` bug), `memory.extract` (ADR-064 moved to nightly cron; no handler existed).
- **Three-mode architecture documented**: chat (TP), headless (background agents), agent_chat (meeting room agents per ADR-124).
- **Role gating**: PM-only write primitives (`RequestContributorAdvance`, `UpdateWorkPlan`) enforced at runtime in `ChatAgent.tool_executor`. Read primitives open to all agent_chat agents.
- **Full primitive inventory updated**: Added all workspace, project, coordinator, and inter-agent primitives that accumulated since 2026-03-04.
- **File structure updated**: Reflects current 17-file primitive directory.
- **Dead code removed**: `_search_user_memories()` (unreachable), `SEARCH_FIELDS["memory"]` (unused).

### 2026-03-04 — ADR-090 + ADR-091 updates

- **Edit primitive**: Added `agent_instructions` as editable field. Added scoped `agent_memory` write paths: `append_observation` (appends, never replaces, cap 20) and `set_goal` (replaces goal only). Raw `agent_memory` writes blocked to prevent clobbering system-accumulated memory.
- **Execute primitive**: Added `agent.acknowledge` action — lightweight observation append from conversation context (no generation). Removed `work.run` (ADR-090 — `work` entity dropped).
- **Entity schema**: `work` entity removed (ADR-090 — `work_tickets` table dropped). Agent schema updated with `agent_instructions`, `agent_memory`, `mode` fields (ADR-087).
- **TP-Facing Entities**: 6 → 5 (work removed).

### 2026-02-28 — RefreshPlatformContent primitive (ADR-085)
- Added `RefreshPlatformContent` primitive — synchronous cache refresh for platform content
- Removed `platform.sync` and `platform.send` from Execute action catalog (replaced by RefreshPlatformContent and platform tools respectively)
- Added `calendar` to Search platform filter enum
- Primitive count updated from 9 → 10
- File structure updated to include `refresh.py`

### 2026-02-23 — Schema references updated for ADR-059/072
- Context Architecture section updated: four-layer model, `platform_content` replaces `filesystem_items`, `user_memory` replaces knowledge tables
- Entity type tables updated: `platform_connections` (was `user_integrations`), `user_memory` (was `memories`), `platform_content` (was `ephemeral_context`), removed `domain`/`context_domains`
- Memory entity schema rewritten for ADR-064 implicit memory model
- Removed `memory` and `domain` from Write required fields (TP no longer has explicit memory tools)

### 2026-02-19 — list_integrations wired; WebSearch promoted from deferred
- `list_integrations` added to PRIMITIVES in `registry.py` with handler wired from `project_tools.py`
  - Previously documented in `platforms.py` prompt but not in schema — a ghost tool TP couldn't call
  - Tool `description` field now carries all behavioral docs (agentic pattern, landing zone IDs)
- `WebSearch` promoted from "Deferred Primitives" — already shipped (ADR-045)
- `platforms.py` PLATFORMS_SECTION slimmed to behavioral framing only; per-tool docs now live in tool definitions
  - Tool descriptions are the source of truth for platform workflow docs, not a separate prompt layer
- Primitive count updated from 7 → 9 (WebSearch + list_integrations)

### 2026-02-11 — ADR-042 Entity Tier Clarification
- Clarified entity types into TP-facing (6) and background (3) tiers
- TP-facing: agent, platform, document, work, session, action
- Background: memory, platform_content, domain
- Added ADR-042 reference for execution simplification

### 2026-02-11 — Manual Context as First-Class
- Added "Context Sources" section documenting platforms, documents, and user-stated facts as equally-weighted
- Search now includes `memory` scope for user-stated facts (source_type IN user_stated, chat, conversation, preference, manual)
- Fixed document search field (`filename` not `name`)
- Write primitive now uses `source_type="user_stated"` for TP-created memories
- Added document entity schema to documentation

### 2026-02-11 — ADR-038 Phase 2 (Single Storage Layer)
- Reduced from 9 to 7 primitives: Removed Todo and Respond per ADR-038
- Added `platform_content` entity type mapping to `ephemeral_context` table
- Narrowed `memory` entity to user-stated facts only (source_type='chat', 'user_stated', 'conversation', 'preference')
- Search primitive now uses `scope="platform_content"` for imported platform data
- Legacy `memory` scope auto-redirects to `platform_content` for backwards compatibility
- Removed dual-write to memories table from import jobs

### 2026-02-10 — Initial Implementation
- 9 primitives: Read, Write, Edit, List, Search, Execute, Todo, Respond, Clarify
- Reference syntax with `type:identifier[/subpath][?query]`
- Action catalog for Execute primitive
- UI action support for Respond, Clarify, Todo

---

## See Also

- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md) — chat + headless mode model
- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — workspace primitives
- [ADR-116: Agent Identity & Inter-Agent Knowledge](../adr/ADR-116-agent-identity-inter-agent-knowledge.md) — DiscoverAgents, ReadAgentContext
- [ADR-118: Skills as Capability Layer](../adr/ADR-118-skills-as-capability-layer.md) — output gateway
- [ADR-130: Agent Capability Substrate](../adr/ADR-130-html-native-output-substrate.md) — three-registry architecture, RenderAsset (replaces RuntimeDispatch)
- [ADR-119: Workspace Filesystem Architecture](../adr/ADR-119-workspace-filesystem-architecture.md) — project primitives
- [ADR-120: Project Execution & Work Budget](../adr/ADR-120-project-execution-work-budget.md) — PM primitives
- [ADR-122: Project Type Registry](../adr/ADR-122-project-type-registry.md) — scaffold_project()
- [ADR-124: Project Meeting Room](../adr/ADR-124-project-meeting-room.md) — agent_chat mode + role gating
