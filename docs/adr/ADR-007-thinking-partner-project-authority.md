# ADR-007: Thinking Partner Project Authority

**Status:** Proposed
**Date:** 2026-01-29
**Related:** ADR-005 (Unified Memory), ADR-006 (Session Architecture)
**Decision Makers:** Kevin Kim

## Context

Currently, projects are explicitly created and managed by users through the UI. The Thinking Partner (TP) agent has read-only access to memories but cannot organize or structure the user's workspace.

This creates friction:
- Users must context-switch between chatting and organizing
- TP understands context boundaries better than manual bucketing
- Cross-project insights require manual memory management
- Future integrations (external sources) need intelligent routing

### Current Architecture

```
User → Creates Project → Adds context → Chats with TP (scoped to project)
           ↓                  ↓
      Manual action      Manual action
```

### Proposed Architecture (Hybrid)

```
User ←→ Chats with TP ←→ TP organizes into projects
              ↓
    Automatic organization + User override capability
```

## Decision

Implement **Hybrid Project Authority** for Thinking Partner:

1. **TP can autonomously create/organize projects** based on conversation context
2. **Users retain full manual control** to create, rename, merge, delete projects
3. **TP respects user-created boundaries** and asks before restructuring
4. **All TP actions are transparent** and logged in conversation

### Tool Definitions

```python
THINKING_PARTNER_TOOLS = [
    {
        "name": "create_project",
        "description": "Create a new project when a distinct topic/goal emerges that warrants separate context. Use sparingly - only when conversation clearly indicates a new domain.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Short, descriptive project name"},
                "description": {"type": "string", "description": "Brief description of project scope"},
                "reason": {"type": "string", "description": "Why this warrants a new project (shown to user)"}
            },
            "required": ["name", "reason"]
        }
    },
    {
        "name": "suggest_project_for_memory",
        "description": "When extracting a memory, suggest which project it belongs to (or user-level if cross-cutting)",
        "input_schema": {
            "type": "object",
            "properties": {
                "memory_content": {"type": "string"},
                "suggested_project_id": {"type": "string", "description": "UUID or 'user' for user-level"},
                "confidence": {"type": "number", "description": "0-1 confidence in suggestion"},
                "reason": {"type": "string"}
            },
            "required": ["memory_content", "suggested_project_id", "confidence"]
        }
    },
    {
        "name": "list_projects",
        "description": "Get user's existing projects to understand current organization",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]
```

### Behavioral Guidelines (System Prompt)

```markdown
## Project Organization Authority

You have the ability to help organize the user's workspace:

**When to create a project:**
- User mentions a distinct goal, initiative, or domain
- Conversation reveals a clear boundary between topics
- User explicitly asks you to organize something

**When NOT to create a project:**
- Single questions or quick tasks
- Topics that fit existing projects
- User preference for flat organization (if stated)

**Always:**
- Explain why you're creating a project
- Ask for confirmation on significant reorganization
- Respect existing user-created project boundaries
```

### Implementation Phases

#### Phase 1: Tool Infrastructure (Foundation)
- Add `tools` parameter to `chat_completion()`
- Implement tool-use response parsing
- Add basic agentic loop to BaseAgent
- Pass auth context through agent execution

#### Phase 2: Read-Only Tools
- Implement `list_projects` tool
- TP can reference projects in responses
- No mutations yet, validates infrastructure

#### Phase 3: Project Creation
- Implement `create_project` tool
- Add transparency logging (tool use shown in chat)
- User can see "TP created project: X"

#### Phase 4: Memory Organization
- Implement `suggest_project_for_memory`
- Integrate with extraction pipeline
- TP influences scope during memory creation

#### Phase 5: Advanced Operations (Future)
- `merge_projects` - Combine related projects
- `archive_project` - Soft-delete with confirmation
- `move_memory` - Reassign memory scope

## Technical Design

### 1. Updated Chat Completion

```python
# services/anthropic.py

async def chat_completion_with_tools(
    messages: list[dict],
    system: str,
    model: str,
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
    max_tokens: int = 4096,
) -> dict:
    """Chat completion with optional tool use."""
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        tools=tools,
        tool_choice={"type": tool_choice} if tools else None,
    )
    return {
        "content": response.content,
        "stop_reason": response.stop_reason,
        "usage": response.usage,
    }
```

### 2. Agentic Loop in ThinkingPartner

```python
# agents/thinking_partner.py

class ThinkingPartnerAgent(BaseAgent):
    tools = THINKING_PARTNER_TOOLS

    async def execute_with_tools(
        self,
        task: str,
        context: ContextBundle,
        auth: UserClient,
        parameters: dict,
    ) -> AgentResult:
        messages = self._build_messages(task, parameters.get("history", []))
        system = self._build_system_prompt(context)

        max_iterations = 5  # Prevent infinite loops

        for _ in range(max_iterations):
            response = await chat_completion_with_tools(
                messages=messages,
                system=system,
                model=self.model,
                tools=self.tools,
            )

            if response["stop_reason"] == "end_turn":
                # Normal text response
                return AgentResult(
                    output=self._extract_text(response["content"]),
                    metadata={"tool_calls": []}
                )

            elif response["stop_reason"] == "tool_use":
                # Execute tool and continue
                tool_results = await self._execute_tools(
                    response["content"],
                    auth
                )
                messages.append({"role": "assistant", "content": response["content"]})
                messages.append({"role": "user", "content": tool_results})

        return AgentResult(output="Max iterations reached", metadata={})

    async def _execute_tools(
        self,
        content: list,
        auth: UserClient
    ) -> list[dict]:
        """Execute tool calls and return results."""
        results = []
        for block in content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                if handler:
                    result = await handler(auth, block.input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })
        return results
```

### 3. Tool Handlers

```python
# services/project_tools.py

async def handle_create_project(auth: UserClient, input: dict) -> dict:
    """Create a project on behalf of TP."""
    workspace = await get_or_create_workspace(auth)

    result = auth.client.table("projects").insert({
        "name": input["name"],
        "description": input.get("description", ""),
        "workspace_id": workspace["id"],
    }).execute()

    return {
        "success": True,
        "project": result.data[0],
        "message": f"Created project '{input['name']}'"
    }

async def handle_list_projects(auth: UserClient, input: dict) -> dict:
    """List user's projects."""
    workspace = await get_or_create_workspace(auth)

    result = auth.client.table("projects")\
        .select("id, name, description")\
        .eq("workspace_id", workspace["id"])\
        .execute()

    return {
        "projects": result.data,
        "count": len(result.data)
    }

TOOL_HANDLERS = {
    "create_project": handle_create_project,
    "list_projects": handle_list_projects,
    "suggest_project_for_memory": handle_suggest_memory_scope,
}
```

### 4. Transparency in Chat

When TP uses a tool, the action should be visible:

```python
# In chat route response stream
if tool_call:
    yield f"data: {json.dumps({'tool_use': {'name': tool_call.name, 'reason': tool_call.input.get('reason')}})}\n\n"
```

Frontend displays:
```
🔧 Created project "API Redesign" - This conversation is clearly about restructuring your backend APIs, which warrants dedicated context.
```

## Consequences

### Positive
- **Reduced friction**: Users chat naturally, organization emerges
- **Better context boundaries**: TP understands semantic boundaries
- **Scalable organization**: Works with many projects/memories
- **Foundation for more agents**: Tool infrastructure reusable

### Negative
- **Complexity**: Agentic loop adds failure modes
- **Latency**: Tool calls add round-trips
- **Trust**: Users must trust TP's organization decisions

### Mitigations
- Max iteration limits prevent runaway loops
- All tool actions logged and visible
- User can always override/undo TP actions
- Start with read-only tools, add mutations gradually

## Migration Strategy

No data migration needed. This is additive:
1. Add tool infrastructure (no behavior change)
2. Enable tools for new conversations
3. Existing sessions continue working (no tools)

## Alternatives Considered

### A. Full Agent Authority
TP has complete control, user is observer.
**Rejected**: Too opaque, removes user agency.

### B. Suggestion-Only
TP suggests, user must confirm every action.
**Rejected**: Too much friction, defeats purpose.

### C. Keep Manual
Users continue managing projects explicitly.
**Rejected**: Doesn't solve the core UX problem.

## Decision Checklist

- [ ] Create ADR-007 (this document)
- [ ] Implement tool infrastructure in anthropic.py
- [ ] Add agentic loop to BaseAgent
- [ ] Implement Phase 2: list_projects (read-only)
- [ ] Test and validate infrastructure
- [ ] Implement Phase 3: create_project
- [ ] Add UI transparency for tool calls
- [ ] Implement Phase 4: memory organization
- [ ] User testing and iteration

## References

- [ADR-005: Unified Memory with Embeddings](ADR-005-unified-memory-with-embeddings.md)
- [ADR-006: Session and Message Architecture](ADR-006-session-message-architecture.md)
- [Anthropic Tool Use Documentation](https://docs.anthropic.com/claude/docs/tool-use)
