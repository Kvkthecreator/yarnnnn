# ADR-024: Context Classification Layer

**Status:** Implemented
**Date:** 2026-02-04
**Related:** ADR-005 (Unified Memory), ADR-007 (TP Authority), ADR-015 (Unified Context)
**Decision Makers:** Kevin Kim

## Context

YARNNN's memory architecture (ADR-005) correctly implements two-tier scoping via `memories.project_id`:
- `NULL` = user-scoped (personal, cross-project)
- `UUID` = project-scoped (task-specific)

However, there's no classification layer to determine which bucket context belongs to. Currently:
- Context created during project chat defaults to that project
- Context in ambient/global chat defaults to user-scoped (NULL)
- No intelligent routing based on content semantics

This leads to:
1. Misattributed context (project-specific facts stored as user-level)
2. Invisible project assignment (user doesn't see where context goes)
3. Incomplete implementation of ADR-007 Phase 5 (`suggest_project_for_memory`)

## Decision

Implement a **Context Classification Layer** with three components:

### 1. Project-Aware ContextBrowserSurface

Enable browsing context across all projects, not just current scope:

```typescript
interface ContextBrowserProps {
  scope: 'user' | 'project' | 'work';
  scopeId?: string;
  allowProjectSelection?: boolean;  // NEW: Enable cross-project browsing
}
```

The component will:
- Show a project selector dropdown when `allowProjectSelection=true`
- Fetch and display context for selected project
- Support moving context between buckets (future)

### 2. TP Routing Guidance

Enhance TP's system prompt to explicitly consider routing:

```markdown
## Memory Routing

When creating or extracting memories, determine the appropriate scope:

**User-scoped (personal):** Facts about the user that apply everywhere
- Communication preferences ("prefers bullet points")
- Business facts ("works at Acme Corp")
- Domain expertise ("10 years in fintech")

**Project-scoped:** Information specific to one initiative
- Requirements ("report needs 3 sections")
- Deadlines ("due Tuesday")
- Client details ("client prefers formal tone")

When uncertain, prefer project-scoped for task-specific details.
Always state your routing decision when creating context.
```

### 3. Attribution in Confirmations

Update SetupConfirmModal and memory creation UI to show:
- Target bucket (Personal / Project Name)
- Visual indicator of scope
- Future: Option to change before confirming

### 4. suggest_project_for_memory Tool (ADR-007 Phase 5)

Complete the implementation defined in ADR-007:

```python
{
    "name": "suggest_project_for_memory",
    "description": "Suggest which project a memory belongs to based on content",
    "input_schema": {
        "type": "object",
        "properties": {
            "memory_content": {"type": "string"},
            "suggested_project_id": {
                "type": "string",
                "description": "UUID of project, or 'user' for user-scoped"
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "reason": {"type": "string"}
        },
        "required": ["memory_content", "suggested_project_id", "confidence"]
    }
}
```

## Implementation

### Phase 1: Project Selector in ContextBrowserSurface

```typescript
// Add project selection to ContextBrowserSurface
const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
  scope === 'project' ? scopeId : null
);

// Fetch user's projects for dropdown
const { data: projects } = useSWR('/api/projects', fetcher);

// Dynamic context fetching based on selection
const contextEndpoint = selectedProjectId
  ? `/api/projects/${selectedProjectId}/memories`
  : '/api/user/memories';
```

### Phase 2: TP System Prompt Enhancement

Add routing guidance to `THINKING_PARTNER_SYSTEM_PROMPT`:

```python
ROUTING_GUIDANCE = """
## Memory Routing

When creating memories, explicitly determine scope:

1. **Analyze the content** - Is this about the user or a specific task?
2. **Check existing projects** - Does this relate to an active project?
3. **State your decision** - "I'll save this to [Personal/Project Name] because..."

Default heuristics:
- Preferences, patterns, expertise → Personal
- Requirements, deadlines, client details → Project-scoped
- Uncertain? → Ask the user
"""
```

### Phase 3: Attribution Display

Update memory creation confirmations:

```typescript
interface MemoryConfirmation {
  content: string;
  targetScope: 'user' | 'project';
  targetProjectId?: string;
  targetProjectName?: string;  // Display name
}

// In confirmation modal
<div className="text-sm text-muted-foreground">
  Saving to: {targetScope === 'user' ? 'Personal' : targetProjectName}
</div>
```

### Phase 4: suggest_project_for_memory Tool

```python
# api/services/project_tools.py

async def handle_suggest_project_for_memory(
    auth: UserClient,
    input: dict
) -> dict:
    """Suggest project routing based on content similarity."""
    content = input["memory_content"]

    # Get user's projects with their context
    projects = await list_projects(auth)

    # Semantic similarity check against project memories
    suggestions = []
    for project in projects:
        project_memories = await get_project_memories(auth, project["id"])
        similarity = await calculate_similarity(content, project_memories)
        suggestions.append({
            "project_id": project["id"],
            "project_name": project["name"],
            "similarity": similarity
        })

    # Sort by similarity
    suggestions.sort(key=lambda x: x["similarity"], reverse=True)

    # Top suggestion or user-scoped if no good match
    if suggestions and suggestions[0]["similarity"] > 0.5:
        return {
            "suggested_project_id": suggestions[0]["project_id"],
            "suggested_project_name": suggestions[0]["project_name"],
            "confidence": suggestions[0]["similarity"],
            "reason": f"Content relates to {suggestions[0]['project_name']}"
        }
    else:
        return {
            "suggested_project_id": "user",
            "suggested_project_name": "Personal",
            "confidence": 0.8,
            "reason": "Content appears to be general/cross-project"
        }

TOOL_HANDLERS["suggest_project_for_memory"] = handle_suggest_project_for_memory
```

## Consequences

### Positive
- Context reliably routes to appropriate buckets
- Users see and control where context is stored
- TP behavior becomes transparent and predictable
- Completes ADR-007 Phase 5 implementation
- Work execution receives correctly-scoped context

### Negative
- Additional TP round-trips for routing decisions
- UI complexity (project selector dropdown)
- Potential for TP to over-ask about routing

### Mitigations
- Cache project list for fast selection
- Use sensible defaults (current project if in project context)
- Tune system prompt to minimize unnecessary routing questions
- Allow batch routing for multiple memories

## Migration

No schema changes required. This is purely:
1. UI enhancement (ContextBrowserSurface)
2. Prompt enhancement (TP system prompt)
3. Tool implementation (suggest_project_for_memory)

## Verification Checklist

- [x] ContextBrowserSurface shows project selector
- [x] Projects endpoint returns all user projects
- [x] TP articulates routing decisions in responses (system prompt updated)
- [x] Confirmation modals show target bucket (create_memory returns attribution)
- [x] suggest_project_for_memory tool functional
- [x] Work execution receives correct context (already working per ADR-015)

## References

- [Analysis: Context Classification Gap](../analysis/context-classification-gap.md)
- [ADR-005: Unified Memory with Embeddings](ADR-005-unified-memory-with-embeddings.md)
- [ADR-007: Thinking Partner Project Authority](ADR-007-thinking-partner-project-authority.md)
- [ADR-015: Unified Context Model](ADR-015-unified-context-model.md)
