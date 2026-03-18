# Primitives Architecture v2

> **Status**: Canonical
> **Created**: 2026-02-11
> **Supersedes**: primitives.md (v1, 2026-02-10)
> **Related ADRs**: ADR-036, ADR-037, ADR-038 (Filesystem-as-Context)
> **Implementation**: `api/services/primitives/`

---

## Overview

Primitives are the universal operations available to the Thinking Partner (TP) for interacting with YARNNN's infrastructure layer. They replace domain-specific tools with a small set of composable operations.

### Core Analogy

YARNNN's entity space is the user's **filesystem**. Platforms (Slack, Notion) and documents are the source files. Agents are the build outputs. TP navigates and acts on this filesystem using primitives — the same way Claude Code navigates a codebase with Read, Write, Search, and Bash.

```
Claude Code filesystem         YARNNN filesystem
─────────────────────         ─────────────────
/project/src/                 platform:slack (synced content)
/project/docs/                platform:notion (synced content)
/project/README.md            document:* (uploads)
/project/CLAUDE.md            user profile (context injection)
.git/ history                 session:* (conversation history)
build output                  agent:* (generated work)
CI jobs                       work:* (execution records)
```

### Design Principles

1. **Minimal Surface** — 7 primitives cover all use cases
2. **Universal Reference Syntax** — Consistent `type:identifier` addressing
3. **Composable** — Primitives combine for complex operations
4. **Self-Describing** — Results include context for further action
5. **Filesystem-as-Context** — Platforms and documents are the source of truth, not extracted copies

---

## The 7 Primitives

| Primitive | Purpose | Input | Output |
|-----------|---------|-------|--------|
| **Read** | Get single entity | `ref` | `data` |
| **Write** | Create new entity | `ref`, `content` | `data`, `ref` |
| **Edit** | Modify existing entity | `ref`, `changes` | `data`, `changes_applied` |
| **List** | Find entities by pattern | `pattern` | `items`, `count` |
| **Search** | Find by semantic meaning | `query`, `scope` | `results`, `count` |
| **Execute** | Trigger external operation | `action`, `target` | `result` |
| **Clarify** | Ask user for input | `question`, `options` | `ui_action` |

### Removed from v1

| Primitive | Reason | Replacement |
|-----------|--------|-------------|
| **Respond** | Model's natural text output serves this purpose | TP's message IS the response |
| **Todo** | No multi-step workflows yet that need progress UI | Re-add when `agent.generate` pipelines exist |

---

## Reference Syntax

All entity references follow a consistent grammar:

```
<type>:<identifier>[/<subpath>][?<query>]
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `type` | Entity type | `agent`, `platform`, `document` |
| `identifier` | Entity ID or special | UUID, `new`, `latest`, `*` |
| `subpath` | Nested access | `/credentials`, `/channels/eng` |
| `query` | Filter parameters | `?status=active&limit=10` |

### Entity Types

| Type | Table | Description | Filesystem Analogy |
|------|-------|-------------|-------------------|
| `agent` | `agents` | Recurring content outputs | Build output |
| `platform` | `user_integrations` | Connected platforms (by provider) | Source directories |
| `document` | `documents` | Uploaded documents | Source files |
| `work` | `work_tickets` | Work execution records | CI job logs |
| `session` | `chat_sessions` | Chat sessions | Shell history |
| `action` | (virtual) | Available actions for Execute | Available commands |

### Demoted Entity Types

| Type | Status | Rationale |
|------|--------|-----------|
| `memory` | Background cache | Memories are written as cache/audit trail. TP doesn't interact directly — relevant context is injected at session start. |
| `domain` | Deferred | Emergent categorization. Not essential for TP operations. Re-evaluate when user base grows. |

### Entity Schemas

#### agent

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `title` | string | Agent name | ✓ Primary |
| `description` | string | Optional description | — |
| `status` | enum | `active`, `paused`, `archived` | ✓ Badge |
| `schedule` | JSONB | `{frequency, day, time, timezone}` | ✓ Frequency |
| `recipient_context` | JSONB | `{name, role, priorities}` | — |
| `sources` | JSONB[] | Data source configs | — |
| `template_structure` | JSONB | Output template config | — |
| `next_run_at` | timestamp | Next scheduled run | — |

#### platform

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `provider` | string | Platform name (slack, notion, etc.) | ✓ Primary |
| `status` | string | Connection status | ✓ Badge |
| `credentials` | JSONB | OAuth tokens (encrypted) | — |
| `settings` | JSONB | Platform-specific settings | — |
| `last_synced_at` | timestamp | Last sync time | ✓ Subtitle |
| `sync_summary` | JSONB | Summary of synced content | — |

**New in v2:** `last_synced_at` and `sync_summary` — platforms now carry their own summarized state, reducing need for separate memory extraction.

#### document

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `filename` | string | Original filename | ✓ Primary |
| `content_type` | string | MIME type | ✓ Icon |
| `extracted_text` | string | Processed content | — |
| `size_bytes` | int | File size | — |

#### work

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `description` | string | Task description | ✓ Primary |
| `status` | enum | `pending`, `running`, `completed`, `failed` | ✓ Badge |
| `agent_type` | string | Which agent handles it | — |
| `result` | JSONB | Execution result | — |
| `agent_id` | UUID | Optional linked agent | — |

#### session

| Field | Type | Description | Display |
|-------|------|-------------|---------|
| `id` | UUID | Primary key | — |
| `created_at` | timestamp | Session start | ✓ Date |
| `messages` | JSONB[] | Chat history | — |
| `summary` | string | AI-generated summary | — |

### Special Identifiers

| Identifier | Meaning | Used With |
|------------|---------|-----------|
| `new` | Create operation | Write |
| `current` | Current active entity | Session |
| `latest` | Most recently updated | Read, Edit |
| `*` | All entities (collection) | List |

### Examples

```
agent:uuid-123              # Specific agent
agent:latest                # Most recently updated
agent:*                     # All agents
agent:?status=active        # Active agents

platform:slack                    # Slack integration (by provider)
platform:slack/channels/eng       # Specific synced content
platform:*                        # All platforms

document:*                        # All documents
document:?content_type=pdf        # Filtered documents

action:*                          # All available actions
action:platform.*                 # Platform actions only
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

**Errors**: `missing_ref`, `invalid_ref`, `not_found`

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
| `work` | `task`, `agent_type` |
| `document` | `name` |

**Defaults Applied**:

| Type | Defaults |
|------|----------|
| `agent` | `status: active`, `frequency: weekly`, `governance: manual` |
| `work` | `frequency: once`, `status: pending` |

---

### Edit

Modify an existing entity.

**Input**:
```json
{
  "ref": "agent:uuid-123",
  "changes": { "status": "paused" }
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

**Immutable Fields**: `id`, `user_id`, `created_at`

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

Find entities by semantic meaning (embedding search).

**Input**:
```json
{
  "query": "database migration decisions",
  "scope": "document",
  "limit": 10
}
```

**Output**:
```json
{
  "success": true,
  "results": [
    {
      "entity_type": "document",
      "ref": "document:uuid-123",
      "data": { "filename": "architecture-notes.md", ... },
      "score": 0.89
    }
  ],
  "count": 1,
  "query": "database migration decisions",
  "scope": "document"
}
```

**Scopes**: `agent`, `document`, `platform_content`, `all`

**Note:** `memory` scope removed. If platform content is indexed, use `platform_content`. For cross-entity search, use `all`.

---

### Execute

Trigger external operations on entities. This is where YARNNN's core value loop lives.

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

**Core Value Loop Actions**:

| Action | Target | Description | The "Why" |
|--------|--------|-------------|-----------|
| `platform.sync` | `platform` | Pull content from platform | Populate the filesystem |
| `agent.generate` | `agent` | Generate content from sources | Produce the build output |
| `platform.publish` | `agent` | Push agent to platform | Deliver the output |

**Supporting Actions**:

| Action | Target | Description |
|--------|--------|-------------|
| `platform.auth` | `platform` | Initiate OAuth |
| `agent.schedule` | `agent` | Update schedule |
| `agent.approve` | `agent` | Approve version |
| `work.run` | `work` | Execute generic work |

**Removed:** `memory.extract` — now a background job triggered by `platform.sync`, not a TP-facing action.

---

### Clarify

Ask the user for input. **Last resort** — only after List/Search exploration fails to resolve ambiguity.

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

## Context Injection (Session Start)

Instead of TP searching memories at runtime, relevant context is preloaded at session start. This is YARNNN's equivalent of Claude Code reading `CLAUDE.md`.

### What Gets Injected

```python
context = {
    "user_profile": {
        "name": "...",
        "role": "...",
        "preferences": { ... },
        "timezone": "..."
    },
    "active_agents": [
        # List(pattern="agent:?status=active") — preloaded
        { "id": "...", "title": "Weekly Update", "frequency": "weekly", ... }
    ],
    "connected_platforms": [
        # List(pattern="platform:*") — preloaded
        { "provider": "slack", "status": "connected", "last_synced": "..." }
    ],
    "recent_sessions": [
        # Last 2-3 session summaries
        { "date": "...", "summary": "Discussed pausing the weekly report..." }
    ]
}
```

### Why This Replaces Memory Search

| Before (v1) | After (v2) |
|-------------|------------|
| TP calls `Search(scope="memory")` at runtime | Context pre-injected, TP reads it directly |
| Memories extracted and stored separately | Source content lives on platforms/documents |
| Importance scoring determines retrieval | Active entities and recent sessions = sufficient context |
| Embedding search for user facts | User profile loaded every session |

### When TP Still Needs to Search

- User asks about something from a specific document → `Search(scope="document")`
- User references old platform content → `Search(scope="platform_content")`
- User asks about a specific agent detail → `Read(ref="agent:uuid")`

The difference: TP searches **source material**, not extracted copies.

---

## Error Handling

### Response Format

```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable description"
}
```

### Common Error Codes

`missing_ref`, `missing_pattern`, `missing_query`, `invalid_ref`, `invalid_pattern`, `not_found`, `permission_denied`, `unsupported_type`, `execution_failed`

### Error Recovery (TP Behavior)

When a primitive fails, TP should:
1. Read the error message
2. Try to resolve (wrong ref? search for the right one)
3. Don't surface infrastructure errors to the user unless actionable

```
# Example: Read fails with not_found
Read(ref="agent:uuid-wrong") → error: not_found
→ List(pattern="agent:*") → find the right UUID
→ Read(ref="agent:uuid-correct") → success
```

The user never sees "Entity not found" — they see the result.

---

## Implementation

### File Structure

```
api/services/primitives/
├── __init__.py      # Module exports
├── refs.py          # Reference parser and resolver
├── registry.py      # Primitive registration
├── read.py          # Read primitive
├── write.py         # Write primitive
├── edit.py          # Edit primitive
├── list.py          # List primitive
├── search.py        # Search primitive (semantic)
├── execute.py       # Execute primitive + action handlers
└── clarify.py       # Clarify primitive
```

**Removed:** `todo.py` (deferred), `Respond` logic from `registry.py`

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
    ├─ success → Result dict → TP decides next action or responds
    │
    └─ error → Error dict → TP attempts recovery or responds with explanation
```

### Integration with TP

```python
from services.primitives import PRIMITIVES, execute_primitive

# TP uses PRIMITIVES as tool definitions (7 tools)
self.tools = PRIMITIVES

# TP executes via unified handler
result = await execute_primitive(auth, tool_use.name, tool_use.input)
```

---

## Migration from v1

| Change | Action Required |
|--------|----------------|
| Respond primitive removed | Remove from `registry.py`, TP prompt |
| Todo primitive removed | Remove from `registry.py`, `todo.py`, TP prompt |
| Memory scope removed from Search | Update `search.py` to remove `memory` scope |
| `memory.extract` removed from Execute | Make it a background job on `platform.sync` |
| `sync_summary` added to platform schema | DB migration to add column |
| Context injection added | New `build_session_context()` function |

---

## Changelog

### 2026-02-11 — v2: Filesystem-as-Context

- **Reduced to 7 primitives** (removed Respond, Todo)
- **Demoted memory** from first-class entity to background cache
- **Demoted domain** to deferred status
- **Added context injection** — preload user profile, active agents, platform summaries
- **Clarified core value loop** — Sync → Generate → Publish
- **Added error recovery guidance** for TP behavior
- **Added filesystem analogy** mapping Claude Code patterns to YARNNN entities
- **Removed `memory` scope** from Search, added `platform_content`
- **Moved `memory.extract`** from Execute action to background job

### 2026-02-10 — v1: Initial Implementation
- 9 primitives: Read, Write, Edit, List, Search, Execute, Todo, Respond, Clarify
- Reference syntax with `type:identifier[/subpath][?query]`
- Action catalog for Execute primitive
- UI action support for Respond, Clarify, Todo

---

## See Also

- [ADR-036: Two-Layer Architecture](../adr/ADR-036-two-layer-architecture.md)
- [ADR-037: Chat-First Surface Architecture](../adr/ADR-037-chat-first-surface-architecture.md)
- [ADR-038: Filesystem-as-Context](../adr/ADR-038-filesystem-as-context.md)
- [TP Prompt Guide v5](./tp-prompt-guide.md)
