# Primitives Architecture

> **Status**: Canonical
> **Created**: 2026-02-10
> **Related ADRs**: ADR-036 (Two-Layer Architecture), ADR-037 (Chat-First Surface)
> **Implementation**: `api/services/primitives/`

---

## Overview

Primitives are the universal operations available to the Thinking Partner (TP) for interacting with YARNNN's infrastructure layer. They replace domain-specific tools with a small set of composable operations.

### Design Principles

1. **Minimal Surface** — 9 primitives cover all use cases
2. **Universal Reference Syntax** — Consistent `type:identifier` addressing
3. **Composable** — Primitives combine for complex operations
4. **Self-Describing** — Results include context for further action

---

## The 9 Primitives

| Primitive | Purpose | Input | Output |
|-----------|---------|-------|--------|
| **Read** | Get single entity | `ref` | `data` |
| **Write** | Create new entity | `ref`, `content` | `data`, `ref` |
| **Edit** | Modify existing entity | `ref`, `changes` | `data`, `changes_applied` |
| **List** | Find entities by pattern | `pattern` | `items`, `count` |
| **Search** | Find by semantic meaning | `query`, `scope` | `results`, `count` |
| **Execute** | Trigger external operation | `action`, `target` | `result` |
| **Todo** | Track progress | `todos` | `todos` |
| **Respond** | Send message to user | `message` | `ui_action` |
| **Clarify** | Ask user for input | `question`, `options` | `ui_action` |

---

## Reference Syntax

All entity references follow a consistent grammar:

```
<type>:<identifier>[/<subpath>][?<query>]
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `type` | Entity type | `deliverable`, `memory`, `platform` |
| `identifier` | Entity ID or special | UUID, `new`, `latest`, `*` |
| `subpath` | Nested access | `/credentials`, `/sources/0` |
| `query` | Filter parameters | `?status=active&limit=10` |

### Entity Types

| Type | Table | Description |
|------|-------|-------------|
| `deliverable` | `deliverables` | Recurring content outputs |
| `platform` | `user_integrations` | Connected platforms (by provider name) |
| `memory` | `memories` | Context memories |
| `session` | `chat_sessions` | Chat sessions |
| `domain` | `context_domains` | Emergent context domains |
| `document` | `documents` | Uploaded documents |
| `work` | `work_tickets` | Work execution records |
| `action` | (virtual) | Available actions for Execute |

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

memory:*                     # All memories
memory:?type=fact&limit=10   # Filtered memories

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

Find entities by semantic meaning (embedding search).

**Input**:
```json
{
  "query": "database migration decisions",
  "scope": "memory",
  "limit": 10
}
```

**Output**:
```json
{
  "success": true,
  "results": [
    {
      "entity_type": "memory",
      "ref": "memory:uuid-123",
      "data": { "content": "We decided to use Supabase...", ... },
      "score": 0.89
    }
  ],
  "count": 1,
  "query": "database migration decisions",
  "scope": "memory"
}
```

**Scopes**: `memory`, `deliverable`, `document`, `work`, `all`

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
| `platform.publish` | `deliverable` | Publish to platform | `via` |
| `platform.auth` | `platform` | Initiate OAuth | — |
| `deliverable.generate` | `deliverable` | Generate content | — |
| `deliverable.schedule` | `deliverable` | Update schedule | — |
| `deliverable.approve` | `deliverable` | Approve version | `version_id` (optional) |
| `memory.extract` | `session` | Extract memories | — |
| `work.run` | `work` | Execute work | — |

---

### Todo

Track multi-step work progress.

**Input**:
```json
{
  "todos": [
    { "content": "Gather sources", "status": "completed", "activeForm": "Gathering sources" },
    { "content": "Generate draft", "status": "in_progress", "activeForm": "Generating draft" },
    { "content": "Review output", "status": "pending", "activeForm": "Reviewing output" }
  ]
}
```

**Output**:
```json
{
  "success": true,
  "todos": [...],
  "ui_action": {
    "type": "UPDATE_TODOS",
    "data": { "todos": [...] }
  }
}
```

---

### Respond

Send a message to the user (appears inline in chat).

**Input**:
```json
{
  "message": "I've created your weekly status update."
}
```

**Output**:
```json
{
  "success": true,
  "message": "I've created your weekly status update.",
  "ui_action": {
    "type": "RESPOND",
    "data": { "message": "..." }
  }
}
```

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
| `RESPOND` | Display message inline | `message` |
| `CLARIFY` | Show focused question | `question`, `options` |
| `UPDATE_TODOS` | Update todo display | `todos` |

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
├── registry.py      # Primitive registration + Respond/Clarify
├── read.py          # Read primitive
├── write.py         # Write primitive
├── edit.py          # Edit primitive
├── list.py          # List primitive
├── search.py        # Search primitive (semantic)
├── execute.py       # Execute primitive + action handlers
└── todo.py          # Todo primitive
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

### 2026-02-10 — Initial Implementation
- 9 primitives: Read, Write, Edit, List, Search, Execute, Todo, Respond, Clarify
- Reference syntax with `type:identifier[/subpath][?query]`
- Action catalog for Execute primitive
- UI action support for Respond, Clarify, Todo

---

## See Also

- [ADR-036: Two-Layer Architecture](../adr/ADR-036-two-layer-architecture.md)
- [ADR-037: Chat-First Surface Architecture](../adr/ADR-037-chat-first-surface-architecture.md)
- [Testing Environment Guide](../testing/TESTING-ENVIRONMENT.md)
