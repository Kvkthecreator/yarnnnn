# Primitives Architecture

> **Status**: Canonical
> **Created**: 2026-02-10
> **Updated**: 2026-02-27 (consistency sweep — removed duplicate schema, ADR-076 references)
> **Related ADRs**: ADR-059 (Simplified Context), ADR-072 (Unified Content Layer), ADR-042 (Execution Simplification), ADR-045 (WebSearch), ADR-076 (Direct API), ADR-064 (Unified Memory)
> **Implementation**: `api/services/primitives/`

---

## Overview

Primitives are the universal operations available to the Thinking Partner (TP) for interacting with YARNNN's infrastructure layer. They replace domain-specific tools with a small set of composable operations.

### Design Principles

1. **Minimal Surface** — 10 primitives cover all use cases
2. **Universal Reference Syntax** — Consistent `type:identifier` addressing
3. **Composable** — Primitives combine for complex operations
4. **Self-Describing** — Results include context for further action

### Context Architecture (ADR-059, ADR-072)

YARNNN uses a four-layer model (ADR-063):

| Layer | Table | Purpose |
|-------|-------|---------|
| **Memory** | `user_context` | User facts, preferences, patterns |
| **Activity** | `activity_log` | System provenance (what YARNNN has done) |
| **Context** | `platform_content` | Synced platform data with retention-based accumulation |
| **Work** | `deliverable_versions` | Generated content outputs |

**Context Sources** (all first-class):

| Source | Storage | Entry Point | Searchable |
|--------|---------|-------------|------------|
| **Platforms** | `platform_content` | OAuth → Sync Worker | `scope="platform_content"` |
| **Documents** | `filesystem_documents` + `filesystem_chunks` | File upload | `scope="document"` |
| **Memory** | `user_context` | Nightly extraction + user edits | `scope="memory"` |

Users without platform connections can still provide rich context via documents and direct statements. Memory is extracted implicitly from conversations (ADR-064).

---

## The 10 Primitives

| Primitive | Purpose | Input | Output |
|-----------|---------|-------|--------|
| **Read** | Get single entity | `ref` | `data` |
| **Write** | Create new entity | `ref`, `content` | `data`, `ref` |
| **Edit** | Modify existing entity | `ref`, `changes` | `data`, `changes_applied` |
| **List** | Find entities by pattern | `pattern` | `items`, `count` |
| **Search** | Find by content | `query`, `scope` | `results`, `count` |
| **Execute** | Trigger external operation | `action`, `target` | `result` |
| **RefreshPlatformContent** | Sync latest platform data | `platform` | `items_synced`, `message` |
| **WebSearch** | Search the web | `query` | `results`, `count` |
| **list_integrations** | Discover connected platforms + metadata | — | `integrations` |
| **Clarify** | Ask user for input | `question`, `options` | `ui_action` |

> **Note**: Todo and Respond primitives were removed per ADR-038 (Filesystem-as-Context).
> Todo will return when multi-step workflows require 30+ second operations.
> Respond was redundant with model output.

> **list_integrations** returns `authed_user_id` (Slack), `designated_page_id` (Notion), `user_email` + `designated_calendar_id` (Gmail/Calendar). Call this first before any platform tool to get the correct IDs for default landing zones. Tool descriptions are the source of truth for platform tool workflow — not a separate prompt layer.

---

## Reference Syntax

All entity references follow a consistent grammar:

```
<type>:<identifier>[/<subpath>][?<query>]
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `type` | Entity type | `deliverable`, `platform_content`, `platform` |
| `identifier` | Entity ID or special | UUID, `new`, `latest`, `*` |
| `subpath` | Nested access | `/credentials`, `/sources/0` |
| `query` | Filter parameters | `?status=active&limit=10` |

### Entity Types

YARNNN uses a tiered entity model. **TP-facing** entities are directly addressable by the Thinking Partner. **Background** entities are infrastructure that TP doesn't directly manipulate.

#### TP-Facing Entities (6)

| Type | Table | Description |
|------|-------|-------------|
| `deliverable` | `deliverables` | Recurring content outputs |
| `platform` | `platform_connections` | Connected platforms (by provider name) |
| `document` | `documents` | Uploaded documents |
| `work` | `work_tickets` | Work execution records |
| `session` | `chat_sessions` | Chat sessions |
| `action` | (virtual) | Available actions for Execute |

#### Background Entities (Infrastructure)

| Type | Table | Description | Notes |
|------|-------|-------------|-------|
| `memory` | `user_context` | User facts, preferences, patterns | Auto-injected into context via working memory |
| `platform_content` | `platform_content` | Synced platform data | Retention-based accumulation (ADR-072) |

> **ADR-064 Note**: Memory is implicit — TP has no explicit memory tools. Extraction happens nightly from conversations. Users can edit memories via the Context page.
>
> **ADR-042 Note**: TP operates on 6 first-class entities. Memory and platform_content are background infrastructure—automatically injected into context, not directly queried by TP during normal operation.

### Entity Schemas

Each entity type has a defined schema. Key fields are shown for display purposes.

#### deliverable

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `title` | string | Deliverable name | ✓ Primary |
| `description` | string | Optional description | — |
| `status` | enum | `active`, `paused`, `archived` | ✓ Badge |
| `schedule` | JSONB | `{frequency, day, time, timezone}` | ✓ Frequency |
| `recipient_context` | JSONB | `{name, role, priorities}` | — |
| `sources` | JSONB[] | Data source configs | — |
| `template_structure` | JSONB | Output template config | — |
| `next_run_at` | timestamp | Next scheduled run | — |

**Display Priority:** `title` > `status` > `schedule.frequency`

#### platform_content

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `platform` | string | Source platform (slack, gmail, notion) | ✓ Badge |
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

**How memories are created** (ADR-064 — implicit memory):
- Nightly extraction from TP conversations (automatic)
- Activity pattern detection from `activity_log` (automatic)
- User edits via Context page (manual)

> **ADR-064 Note**: TP has no explicit memory creation tools. All memory extraction is implicit.

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

#### work

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `description` | string | Task description | ✓ Primary |
| `status` | enum | `pending`, `running`, `completed`, `failed` | ✓ Badge |
| `agent_type` | string | Which agent handles it | — |
| `result` | JSONB | Execution result | — |
| `deliverable_id` | UUID | Optional linked deliverable | — |

**Display Priority:** `description` > `status`

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
deliverable:uuid-123          # Specific deliverable
deliverable:latest            # Most recently updated deliverable
deliverable:*                 # All deliverables
deliverable:?status=active    # Active deliverables

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
  "ref": "deliverable:uuid-123"
}
```

**Output**:
```json
{
  "success": true,
  "data": { "id": "uuid-123", "title": "Weekly Update", ... },
  "ref": "deliverable:uuid-123",
  "entity_type": "deliverable"
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
  "ref": "deliverable:new",
  "content": {
    "title": "Weekly Status",
    "deliverable_type": "status_report"
  }
}
```

**Output**:
```json
{
  "success": true,
  "data": { "id": "new-uuid", "title": "Weekly Status", ... },
  "ref": "deliverable:new-uuid",
  "entity_type": "deliverable",
  "message": "Created deliverable: Weekly Status (weekly)"
}
```

**Required Fields by Type**:

| Type | Required |
|------|----------|
| `deliverable` | `title`, `deliverable_type` |
| `work` | `task`, `agent_type` |
| `document` | `name` |

**Defaults Applied**:

| Type | Defaults |
|------|----------|
| `deliverable` | `status: active`, `frequency: weekly` |
| `work` | `frequency: once`, `status: pending` |

---

### Edit

Modify an existing entity.

**Input**:
```json
{
  "ref": "deliverable:uuid-123",
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
  "ref": "deliverable:uuid-123",
  "changes_applied": ["status", "updated_at"]
}
```

**Immutable Fields** (cannot be edited):
- `id`
- `user_id`
- `created_at`

---

### List

Find entities by pattern (structural navigation).

**Input**:
```json
{
  "pattern": "deliverable:?status=active",
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
  "pattern": "deliverable:?status=active",
  "entity_type": "deliverable",
  "message": "Found 2 deliverable(s) (2 active)"
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

**Scopes**: `platform_content`, `document`, `deliverable`, `work`, `all`

**Platform Filter** (optional, for `platform_content` scope): `slack`, `gmail`, `notion`, `calendar`

> **Scope clarification**:
> - `platform_content` searches synced platform data (Slack/Gmail/Notion/Calendar). If stale/empty, use `RefreshPlatformContent` to sync latest (ADR-085).
> - `document` searches uploaded files (PDF, DOCX, TXT, MD)
> - `memory` is **not a valid scope** (ADR-065) — memory is already injected into working memory at session start. Passing `scope="memory"` returns an error.

---

### Execute

Trigger external operations on entities.

**Input**:
```json
{
  "action": "deliverable.generate",
  "target": "deliverable:uuid-123"
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
  "action": "deliverable.generate",
  "target": "deliverable:uuid-123"
}
```

**Available Actions**:

| Action | Target Type | Description | Requires |
|--------|-------------|-------------|----------|
| `platform.publish` | `deliverable` | Publish deliverable to platform | `via` |
| `deliverable.generate` | `deliverable` | Generate content | — |
| `deliverable.schedule` | `deliverable` | Update schedule | — |
| `deliverable.approve` | `deliverable` | Approve version | `version_id` (optional) |
| `memory.extract` | `session` | Extract memories | — |
| `work.run` | `work` | Execute work | — |
| `signal.process` | `system` | Run signal extraction | — |

> **Note**: `platform.sync` and `platform.send` removed — use `RefreshPlatformContent` primitive (ADR-085) and platform tools (`platform_slack_*`, etc.) respectively.

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

**Supported platforms**: `slack`, `gmail`, `notion`, `calendar`

**Mode**: Chat only (`["chat"]`). Headless mode uses `freshness.sync_stale_sources()` instead.

**Staleness threshold**: 30 minutes — skips re-sync if content was fetched recently.

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
├── __init__.py      # Module exports
├── refs.py          # Reference parser and resolver
├── registry.py      # Primitive registration + Clarify
├── read.py          # Read primitive
├── write.py         # Write primitive
├── edit.py          # Edit primitive
├── list.py          # List primitive
├── search.py        # Search primitive (text-based)
├── execute.py       # Execute primitive + action handlers
├── refresh.py       # RefreshPlatformContent primitive (ADR-085)
└── clarify.py       # Clarify primitive
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

### 2026-02-28 — RefreshPlatformContent primitive (ADR-085)
- Added `RefreshPlatformContent` primitive — synchronous cache refresh for platform content
- Removed `platform.sync` and `platform.send` from Execute action catalog (replaced by RefreshPlatformContent and platform tools respectively)
- Added `calendar` to Search platform filter enum
- Primitive count updated from 9 → 10
- File structure updated to include `refresh.py`

### 2026-02-23 — Schema references updated for ADR-059/072
- Context Architecture section updated: four-layer model, `platform_content` replaces `filesystem_items`, `user_context` replaces knowledge tables
- Entity type tables updated: `platform_connections` (was `user_integrations`), `user_context` (was `memories`), `platform_content` (was `ephemeral_context`), removed `domain`/`context_domains`
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
- TP-facing: deliverable, platform, document, work, session, action
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

## Deferred Primitives

### Todo (Deferred from ADR-038)

Progress tracking for multi-step operations.

**Trigger**: When operations take 30+ seconds and require user-visible progress.

**Status**: Deferred until needed. Current operations complete within acceptable timeframes.

---

## See Also

- [ADR-036: Two-Layer Architecture](../adr/ADR-036-two-layer-architecture.md)
- [ADR-037: Chat-First Surface Architecture](../adr/ADR-037-chat-first-surface-architecture.md)
- [ADR-038: Filesystem-as-Context Architecture](../adr/ADR-038-filesystem-as-context.md)
- [ADR-042: Deliverable Execution Simplification](../adr/ADR-042-deliverable-execution-simplification.md)
- [ADR-044: Deliverable Type Reconceptualization](../adr/ADR-044-deliverable-type-reconceptualization.md)
- [ADR-045: Deliverable Orchestration Redesign](../adr/ADR-045-deliverable-orchestration-redesign.md)
- [Testing Environment Guide](../testing/TESTING-ENVIRONMENT.md)
