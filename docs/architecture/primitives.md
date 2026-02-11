# Primitives Architecture

> **Status**: Canonical
> **Created**: 2026-02-10
> **Updated**: 2026-02-11 (ADR-038 Phase 2)
> **Related ADRs**: ADR-036 (Two-Layer), ADR-037 (Chat-First), ADR-038 (Filesystem-as-Context), ADR-042 (Execution Simplification)
> **Implementation**: `api/services/primitives/`

---

## Overview

Primitives are the universal operations available to the Thinking Partner (TP) for interacting with YARNNN's infrastructure layer. They replace domain-specific tools with a small set of composable operations.

### Design Principles

1. **Minimal Surface** — 7 primitives cover all use cases
2. **Universal Reference Syntax** — Consistent `type:identifier` addressing
3. **Composable** — Primitives combine for complex operations
4. **Self-Describing** — Results include context for further action

### Context Sources (First-Class)

YARNNN supports three equally-weighted context sources:

| Source | Storage | Entry Point | Searchable |
|--------|---------|-------------|------------|
| **Platforms** | `ephemeral_context` | OAuth → Import | `scope="platform_content"` |
| **Documents** | `documents` + `chunks` | File upload | `scope="document"` |
| **User-stated facts** | `memories` | Chat / TP Write | `scope="memory"` |

Users without platform connections can still provide rich context via documents and direct statements. This is not a fallback — all three sources are first-class.

---

## The 7 Primitives

| Primitive | Purpose | Input | Output |
|-----------|---------|-------|--------|
| **Read** | Get single entity | `ref` | `data` |
| **Write** | Create new entity | `ref`, `content` | `data`, `ref` |
| **Edit** | Modify existing entity | `ref`, `changes` | `data`, `changes_applied` |
| **List** | Find entities by pattern | `pattern` | `items`, `count` |
| **Search** | Find by content | `query`, `scope` | `results`, `count` |
| **Execute** | Trigger external operation | `action`, `target` | `result` |
| **Clarify** | Ask user for input | `question`, `options` | `ui_action` |

> **Note**: Todo and Respond primitives were removed per ADR-038 (Filesystem-as-Context).
> Todo will return when multi-step workflows require 30+ second operations.
> Respond was redundant with model output.

> **Future**: WebSearch primitive is planned for ADR-045 when research-type deliverables require external context. See "Deferred Primitives" section below.

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
| `platform` | `user_integrations` | Connected platforms (by provider name) |
| `document` | `documents` | Uploaded documents |
| `work` | `work_tickets` | Work execution records |
| `session` | `chat_sessions` | Chat sessions |
| `action` | (virtual) | Available actions for Execute |

#### Background Entities (Infrastructure)

| Type | Table | Description | Notes |
|------|-------|-------------|-------|
| `memory` | `memories` | User-stated facts | Background cache, auto-injected into context |
| `platform_content` | `ephemeral_context` | Imported platform data | Auto-gathered during generation |
| `domain` | `context_domains` | Emergent context domains | Deferred per ADR-042 |

> **ADR-038 Note**: `memory` is reserved for user-stated facts (`source_type` IN 'chat', 'user_stated', 'conversation', 'preference'). Platform imports (Slack/Gmail/Notion) are stored in `ephemeral_context`.
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

#### memory (User-Stated Facts)

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `content` | string | The memory content | ✓ Primary |
| `tags` | string[] | Categorization tags | ✓ Chips |
| `importance` | float | 0.0–1.0 retrieval weight | — |
| `source_type` | enum | `user_stated`, `chat`, `conversation`, `preference`, `manual` | — |
| `entities` | JSONB | Extracted entities | — |

**Display Priority:** `content` (truncated) > `tags`

**How to create:**
- TP uses `Write(ref="memory:new", content={content: "User prefers bullets"})` when user states a fact
- User uploads document → memories extracted automatically
- Manual entry via `create_memory_manual()` function

> **ADR-038 Note**: Memory is restricted to user-stated facts only. Platform imports do NOT write here.

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

#### document

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `filename` | string | Original filename | ✓ Primary |
| `content_type` | string | MIME type | ✓ Icon |
| `extracted_text` | string | Processed content | — |
| `size_bytes` | int | File size | — |

**Display Priority:** `filename` > `content_type`

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
| `memory` | `content` |
| `work` | `task`, `agent_type` |
| `document` | `name` |
| `domain` | `name` |

**Defaults Applied**:

| Type | Defaults |
|------|----------|
| `deliverable` | `status: active`, `frequency: weekly`, `governance: manual` |
| `memory` | `tags: []`, `source_type: conversation`, `is_active: true`, `importance: 0.5` |
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

**Scopes**: `platform_content`, `memory`, `document`, `deliverable`, `work`, `all`

**Platform Filter** (optional, for `platform_content` scope): `slack`, `gmail`, `notion`

> **Scope clarification**:
> - `memory` searches user-stated facts (things the user has told TP directly)
> - `document` searches uploaded files (PDF, DOCX, TXT, MD)
> - `platform_content` searches imported platform data (Slack/Gmail/Notion)

---

### Execute

Trigger external operations on entities.

**Input**:
```json
{
  "action": "platform.sync",
  "target": "platform:slack"
}
```

**Output**:
```json
{
  "success": true,
  "result": {
    "status": "started",
    "job_id": "job-uuid",
    "provider": "slack"
  },
  "action": "platform.sync",
  "target": "platform:slack"
}
```

**Available Actions**:

| Action | Target Type | Description | Requires |
|--------|-------------|-------------|----------|
| `platform.sync` | `platform` | Sync from platform | — |
| `platform.publish` | `deliverable` | Publish deliverable to platform | `via` |
| `platform.send` | `platform` | Send ad-hoc message to platform | `params` (see below) |
| `platform.auth` | `platform` | Initiate OAuth | — |
| `deliverable.generate` | `deliverable` | Generate content | — |
| `deliverable.schedule` | `deliverable` | Update schedule | — |
| `deliverable.approve` | `deliverable` | Approve version | `version_id` (optional) |
| `memory.extract` | `session` | Extract memories | — |
| `work.run` | `work` | Execute work | — |

**platform.send params by platform**:

| Platform | Required params | Example |
|----------|-----------------|---------|
| `slack` | `channel`, `message` | `{channel: "#general", message: "Hello!"}` |
| `gmail` | `to`, `subject`, `body` | `{to: "user@example.com", subject: "Hi", body: "..."}` |
| `notion` | `page_id`, `content` | `{page_id: "abc123", content: "Added note"}` |

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

These primitives are documented but not yet implemented. They will be added when specific use cases require them.

### WebSearch (ADR-045)

Web search capability for research-type deliverables.

**Trigger**: When `competitive_analysis`, `market_landscape`, or research-binding deliverables require external context.

**Input**:
```json
{
  "query": "competitor pricing strategies SaaS 2026",
  "max_results": 5
}
```

**Output**:
```json
{
  "success": true,
  "results": [
    {
      "title": "SaaS Pricing Trends 2026",
      "url": "https://...",
      "snippet": "Key findings show...",
      "score": 0.92
    }
  ],
  "count": 5
}
```

**Implementation considerations**:
- Provider options: Anthropic built-in (if available), Tavily, Brave Search
- Caching: 15-minute TTL for same query
- Cost: Per-search API cost, may require usage limits

### WebFetch (ADR-045)

Fetch and extract content from a specific URL.

**Trigger**: When TP or agent needs to pull content from a URL provided by user or discovered via WebSearch.

**Input**:
```json
{
  "url": "https://example.com/article",
  "extract_prompt": "Extract key pricing information"
}
```

**Output**:
```json
{
  "success": true,
  "content": "Extracted content...",
  "title": "Page Title",
  "url": "https://example.com/article"
}
```

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
