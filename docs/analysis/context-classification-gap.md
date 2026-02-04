# Analysis: Context Classification Gap

**Date:** 2026-02-04
**Related ADRs:** ADR-005, ADR-007, ADR-015
**Status:** Active - Resolution in Progress

---

## Executive Summary

YARNNN's architecture documents describe a robust context management system where projects serve as "context buckets" for task-specific knowledge. However, analysis reveals a critical gap: **the classification layer that routes context to appropriate buckets is not implemented**.

The data model, API endpoints, and work execution all support project-scoped context. What's missing is the upstream decision: "Which project does this context belong to?"

---

## What's Working

### 1. Data Model (ADR-005)

The `memories` table correctly implements two-tier scoping:

```sql
project_id UUID REFERENCES projects(id)  -- NULL = user-scoped, UUID = project-scoped
```

This design is sound and requires no changes.

### 2. API Endpoints (context.py)

Routes properly separate user vs project context:

| Endpoint | Purpose |
|----------|---------|
| `GET /user/memories` | User-scoped memories (project_id IS NULL) |
| `GET /projects/:id/memories` | Project-scoped memories |
| `GET /projects/:id/context` | Full bundle (user + project + docs) |

### 3. Work Execution (work_execution.py)

Context loading correctly merges both tiers:

```python
async def load_context_for_work(client, user_id, project_id, ...):
    # Loads user memories (project_id IS NULL)
    # Plus project memories (project_id = given UUID)
    # Returns unified ContextBundle
```

### 4. TP Tools (project_tools.py)

Tools exist for project and memory creation:
- `create_project` - TP can create organizational buckets
- `create_memory` - TP can create memories
- `create_deliverable` - Links work to projects

---

## What's Missing

### 1. Classification at Extraction Time

When TP creates memories (either through extraction or explicitly), there's no mechanism to determine which project bucket they belong to.

**Current behavior:**
- Memories created during project chat → defaults to that project's ID
- Memories created in ambient/global chat → NULL (user-scoped)
- No intelligent routing based on content

**Expected behavior (ADR-007 Phase 5):**
```python
{
    "name": "suggest_project_for_memory",
    "description": "When extracting a memory, suggest which project it belongs to",
    "input_schema": {
        "memory_content": "string",
        "suggested_project_id": "UUID or 'user'",
        "confidence": "0-1",
        "reason": "string"
    }
}
```

This tool is defined in ADR-007 but **not implemented**.

### 2. Project Visibility in ContextBrowserSurface

The UI only shows:
- Personal context (user-scoped)
- Current scope's context (if viewing a project)

There's no way to:
- Browse all projects' context from one view
- Move context between projects
- See which project a memory belongs to

### 3. Project Attribution in Confirmations

When TP creates context or work, the confirmation modals don't show:
- Which project the memory will be attributed to
- Option to change the target project
- Visibility of cross-project implications

---

## The Core Problem

The architecture assumes a **classification layer** that doesn't exist:

```
                     ┌─────────────────────────────────────────────┐
                     │              WHAT EXISTS                    │
                     └─────────────────────────────────────────────┘
                                         │
                     User input → TP → [Creates memory/work]
                                         │
                                         ▼
                     ┌───────────────────────────────────────────────┐
                     │  Memory created with whatever project_id     │
                     │  happens to be in current context (or NULL)  │
                     └───────────────────────────────────────────────┘

                     ┌─────────────────────────────────────────────┐
                     │              WHAT'S NEEDED                  │
                     └─────────────────────────────────────────────┘
                                         │
                     User input → TP → [Analyzes content]
                                         │
                                         ▼
                     ┌───────────────────────────────────────────────┐
                     │  CLASSIFICATION LAYER                         │
                     │  - Is this user-level or project-specific?   │
                     │  - Which project does this relate to?        │
                     │  - Should we ask the user?                   │
                     └───────────────────────────────────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────────────┐
                     │  Memory routed to appropriate bucket          │
                     │  with transparent attribution                 │
                     └───────────────────────────────────────────────┘
```

---

## Resolution Path

### Phase 1: Project Selector in ContextBrowserSurface

Add UI to browse context across all projects:

```
┌─────────────────────────────────────────────────────────────┐
│  Context Browser                                            │
├─────────────────────────────────────────────────────────────┤
│  [Personal] [Project ▼]                                     │
│             ├─ Client A                                     │
│             ├─ Client B                                     │
│             └─ Research                                     │
├─────────────────────────────────────────────────────────────┤
│  [🔍 Search...]                                             │
├─────────────────────────────────────────────────────────────┤
│  Memory cards for selected scope...                         │
└─────────────────────────────────────────────────────────────┘
```

### Phase 2: Enhanced TP Memory Routing

Update TP's system prompt and tool guidance to:
1. Consider content relevance to existing projects
2. Decide scope explicitly (user vs specific project)
3. Articulate the routing decision

### Phase 3: Attribution in Confirmations

When TP creates context, show:
- Target bucket (Personal / Project Name)
- Option to change before confirming
- Clear visual distinction

### Phase 4: Implement suggest_project_for_memory

Complete ADR-007 Phase 5:
- Add the tool to TP's capabilities
- Integrate with extraction pipeline
- Enable intelligent routing based on semantic similarity

---

## Schema Verification

Current schema supports all requirements. No changes needed:

```sql
-- memories table (ADR-005)
project_id UUID REFERENCES projects(id)  -- NULL = user, UUID = project

-- Indexes exist
CREATE INDEX idx_memories_project ON memories(project_id) WHERE is_active = true;
```

---

## Endpoint Verification

All endpoints are aligned:

| Endpoint | Schema | Status |
|----------|--------|--------|
| `/user/memories` | project_id IS NULL | ✅ Correct |
| `/projects/:id/memories` | project_id = :id | ✅ Correct |
| `/projects/:id/context` | Bundle assembly | ✅ Correct |

---

## Success Criteria

1. User can browse context for any project from ContextBrowserSurface
2. TP articulates routing decisions when creating memories
3. Confirmations show target bucket with option to change
4. Context reliably lands in appropriate buckets
5. Work execution receives correctly-scoped context

---

## References

- [ADR-005: Unified Memory with Embeddings](../adr/ADR-005-unified-memory-with-embeddings.md)
- [ADR-007: Thinking Partner Project Authority](../adr/ADR-007-thinking-partner-project-authority.md)
- [ADR-015: Unified Context Model](../adr/ADR-015-unified-context-model.md)
- [First Principles: Memory Architecture](memory-architecture-first-principles.md)
