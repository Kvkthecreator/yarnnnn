# ADR-038: Claude Code Architecture Mapping

**Status:** Canon
**Date:** 2026-02-10
**Related:** ADR-025 (Claude Code Agentic Alignment), ADR-036 (Two-Layer Architecture), ADR-037 (Chat-First Surface)
**Spawned:** ADR-039 (Background Work Agents), ADR-040 (Semantic Skill Matching), ADR-041 (MCP Server Exposure)

---

## Context

Before implementing specific TP features (skill interface, pattern recognition), we need a comprehensive understanding of how Claude Code and Claude Agent SDK patterns map to YARNNN's existing infrastructure. This ensures architectural alignment and prevents divergent implementations.

### Why This Mapping Matters

YARNNN's TP (Thinking Partner) was designed independently but converges on many of the same patterns that Anthropic has standardized in Claude Code and the Agent SDK. By explicitly mapping these equivalences:

1. **Validate architectural decisions** — Confirm we're building on proven patterns
2. **Identify gaps** — See what Claude Code has that we lack (and vice versa)
3. **Guide implementation** — Know where to look for reference patterns
4. **Enable interoperability** — Future SDK integration becomes possible

---

## The Mapping

### Overview: Architectural Equivalence

| Claude Code / Agent SDK | YARNNN TP | Notes |
|-------------------------|-----------|-------|
| **Agentic Loop** | `execute_stream_with_tools()` | Same pattern: prompt → tool → result → loop |
| **Tools (built-in)** | `THINKING_PARTNER_TOOLS` | 16 tools: respond, clarify, CRUD, navigation |
| **MCP Servers** | Platform Integrations | Slack, Gmail, Notion readers/exporters |
| **TodoWrite** | `todo_write` tool | Identical semantics |
| **Skills** | Skill Registry | `/board-update` ≈ `/commit` |
| **Context/Memory** | `ContextBundle` | Memories + documents + domain scope |
| **Sub-agents (Task)** | Work Agents | ResearchAgent, ContentAgent, ReportingAgent |
| **Plan Mode** | ADR-025 Tier 1 | [PLAN] → [GATE] → [EXEC] → [VALIDATE] |
| **Streaming** | SSE with StreamingResponse | Same event types |
| **Conversation History** | `session_messages` | Reconstructed for model coherence |

---

## Detailed Mapping

### 1. Tool System

#### Claude Code Pattern

Claude Code has two categories of tools:
- **Built-in tools**: Read, Edit, Write, Bash, Grep, Glob, WebFetch, etc.
- **MCP tools**: Dynamically discovered from configured MCP servers

Tools are invoked via the model's `tool_use` block, executed, and results fed back as `tool_result`.

#### YARNNN TP Equivalent

```
api/services/project_tools.py (2800 lines)
├── Communication: respond, clarify, todo_write
├── Navigation: list_memories, list_deliverables, get_work
├── CRUD: create_memory, update_deliverable, delete_work
└── Execution: run_deliverable, create_work
```

**Key differences:**

| Aspect | Claude Code | YARNNN TP |
|--------|-------------|-----------|
| Tool count | ~20 built-in + MCP | 16 core tools |
| Focus | Code manipulation | Entity management |
| Output routing | Console/files | UI surfaces (via `ui_action`) |
| Context injection | Codebase files | Memories + documents |

**UI Action Pattern (YARNNN-specific):**

YARNNN tools return `ui_action` to drive frontend state:
```python
{
    "success": True,
    "deliverables": [...],
    "ui_action": {
        "type": "OPEN_SURFACE",
        "surface": "deliverable-list",
        "data": { "status": "active" }
    }
}
```

This is analogous to Claude Code tools that produce visible output (Bash console, Read file content) — but structured for React/UI consumption.

---

### 2. Agent / Sub-Agent Architecture

#### Claude Code Pattern

Claude Code uses the `Task` tool to spawn sub-agents:
```
Task tool → spawns new agent process
├── subagent_type: Bash, Explore, Plan, etc.
├── prompt: what to accomplish
├── run_in_background: optional async
└── Returns: result or agent_id for resume
```

Sub-agents have isolated context but can share through prompts.

#### YARNNN TP Equivalent

```
api/agents/
├── base.py           # BaseAgent abstract class
├── thinking_partner.py  # Orchestrator (like Claude Code's main loop)
├── research.py       # ResearchAgent (like Explore sub-agent)
├── content.py        # ContentAgent (specialized writer)
└── reporting.py      # ReportingAgent (summaries)
```

**Delegation pattern:**
```python
# ThinkingPartnerAgent delegates to work agents
research_agent = ResearchAgent()
result = await research_agent.execute(
    task="Investigate competitor pricing",
    context=context_bundle,
    auth=auth
)
# Result stored in work_outputs table
```

**Key differences:**

| Aspect | Claude Code | YARNNN TP |
|--------|-------------|-----------|
| Spawn mechanism | Task tool | Direct instantiation |
| Context sharing | Via prompt | Via ContextBundle |
| Output storage | Same conversation | `work_outputs` table |
| Background mode | Yes (run_in_background) | No (sync only currently) |
| Resume capability | Yes (agent_id) | No |

**Opportunity: Background Work Agents**

YARNNN could benefit from background agent capability for long-running tasks like:
- Deep research on a topic
- Comprehensive deliverable generation
- Batch processing across multiple sources

---

### 3. MCP / Platform Integration

#### Claude Code Pattern

MCP (Model Context Protocol) provides external integrations:
```
MCP Servers
├── Transport: stdio, SSE, HTTP
├── Discovery: list tools at runtime
├── Invocation: mcp__servername__toolname
└── Examples: Slack, GitHub, databases
```

Claude Code treats MCP tools identically to built-in tools after discovery.

#### YARNNN TP Equivalent

```
api/integrations/
├── core/
│   ├── client.py    # Integration client base
│   ├── oauth.py     # OAuth flow handling
│   ├── tokens.py    # Token refresh/storage
│   └── types.py     # Type definitions
├── providers/       # OAuth provider configs (Google, Slack, etc.)
├── readers/         # Read from platforms
│   ├── slack.py     # Slack channel/thread reading
│   ├── gmail.py     # Gmail message reading
│   └── notion.py    # Notion page/database reading
└── exporters/       # Write to platforms
    ├── slack.py     # Post to Slack
    ├── gmail.py     # Send/draft emails
    └── notion.py    # Create/update Notion pages
```

**Mapping:**

| MCP Concept | YARNNN Equivalent |
|-------------|-------------------|
| MCP Server | Reader + Exporter per platform |
| Transport | HTTP/OAuth (not stdio) |
| Tool discovery | Fixed at deploy (not runtime) |
| `mcp__slack__read_channel` | `SlackReader.fetch_channel_messages()` |
| `mcp__notion__create_page` | `NotionExporter.create_page()` |

**Key difference: Deliverable-mediated access**

YARNNN doesn't expose platforms as raw tools. Instead:
1. User creates a deliverable linked to platform sources
2. Pipeline extracts from sources → generates output
3. Output optionally exported back to platform

This is more constrained than MCP's "any tool anytime" model, but provides:
- Predictable recurring workflows
- Audit trail via deliverable history
- Approval gates before platform writes

---

### 4. Orchestration / Agentic Loop

#### Claude Code Pattern

```
while not done:
    response = await model.complete(messages + tools)

    if response.has_tool_use:
        for tool_use in response.tool_uses:
            result = await execute_tool(tool_use)
            messages.append(tool_result)
    else:
        done = True

return response.text
```

With limits: `max_iterations`, timeouts, etc.

#### YARNNN TP Equivalent

```python
# api/agents/thinking_partner.py
async def execute_stream_with_tools(
    task, context, auth, parameters
) -> AsyncGenerator[StreamEvent, None]:

    messages = build_history(parameters.get('history', []))
    system = build_system_prompt(context, skill_prompt)

    for round_num in range(max_iterations):
        async with client.messages.stream(...) as stream:
            async for text in stream.text_stream:
                yield StreamEvent(type="text", content=text)

            response = await stream.get_final_message()

        if response.stop_reason == "tool_use":
            for tool_use in response.content:
                yield StreamEvent(type="tool_use", content=tool_use)
                result = await execute_tool(tool_use)
                yield StreamEvent(type="tool_result", content=result)
        else:
            break

    yield StreamEvent(type="done", content=None)
```

**Equivalence confirmed:** Same pattern, same semantics.

---

### 5. Streaming

#### Claude Code Pattern

Real-time streaming of:
- Text chunks (as model generates)
- Tool use announcements (before execution)
- Tool results (after execution)

#### YARNNN TP Equivalent

```python
# api/routes/chat.py
@router.post("/chat")
async def global_chat(...):
    async def response_stream():
        async for event in agent.execute_stream_with_tools(...):
            if event.type == "text":
                yield f"data: {json.dumps({'content': event.content})}\n\n"
            elif event.type == "tool_use":
                yield f"data: {json.dumps({'tool_use': event.content})}\n\n"
            elif event.type == "tool_result":
                yield f"data: {json.dumps({'tool_result': event.content})}\n\n"
            elif event.type == "done":
                yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        response_stream(),
        media_type="text/event-stream"
    )
```

**Frontend consumption (TPContext.tsx):**
```typescript
const reader = response.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    // Parse SSE, update status, handle ui_actions
}
```

**Equivalence confirmed:** Same SSE pattern.

---

### 6. Skills / Slash Commands

#### Claude Code Pattern

```
Skills = prompt expansions + expected behaviors
├── /commit → git commit workflow
├── /review-pr → PR review workflow
├── /help → usage information
└── Detection: explicit (/) or implicit (intent)
```

Skills modify the system prompt with domain-specific instructions.

#### YARNNN TP Equivalent

```python
# api/services/skills.py
SKILLS = {
    "board-update": {
        "name": "board-update",
        "trigger_patterns": ["board update", "investor update"],
        "deliverable_type": "board_update",
        "system_prompt_addition": """
        ## Active Skill: Board Update Creation

        [PLAN] Phase → Check assumptions, gather info
        [GATE] Phase → HARD STOP, wait for user confirmation
        [EXEC] Phase → Create entities (only after gate approval)
        [VALIDATE] Phase → Verify results, offer next steps
        """
    }
}
```

**Skill detection flow:**
```python
# In thinking_partner.py
active_skill = detect_skill(user_message)  # Pattern matching
skill_prompt = get_skill_prompt_addition(active_skill)
system = build_system_prompt(..., skill_prompt=skill_prompt)
```

**Mapping:**

| Claude Code Skill | YARNNN Skill | Notes |
|-------------------|--------------|-------|
| /commit | /board-update | Workflow-specific prompt |
| /review-pr | /status-report | Review-oriented flow |
| - | /research-brief | YARNNN-specific |
| - | /stakeholder-update | YARNNN-specific |

**Key insight:** YARNNN skills are deliverable-creation workflows, not code workflows. Same pattern, different domain.

---

### 7. Plan Mode / Approval Gates

#### Claude Code Pattern

Claude Code enters "plan mode" for complex tasks:
1. Explore codebase
2. Design approach
3. Write plan to file
4. User approves via ExitPlanMode
5. Execute plan

#### YARNNN TP Equivalent

ADR-025 specifies four-phase workflow:

```
[PLAN] → Create todos, state assumptions
    ↓
[GATE] → HARD STOP, present plan, wait for confirmation
    ↓
[EXEC] → Execute only after user says "yes"
    ↓
[VALIDATE] → Verify results, offer next steps
```

**Key difference:** YARNNN's gate is inline (clarify tool), not modal (ExitPlanMode).

**Opportunity: Modal Approval UI**

For high-stakes operations (delete, bulk changes), YARNNN could benefit from a modal confirmation similar to Claude Code's ExitPlanMode — currently implemented as `SetupConfirmModal` for deliverable setup.

---

### 8. Context / Memory

#### Claude Code Pattern

Context = codebase files read into conversation:
- File contents via Read tool
- Search results via Grep/Glob
- Git state via Bash
- Summarization for long contexts

#### YARNNN TP Equivalent

```python
@dataclass
class ContextBundle:
    memories: list[Memory]       # User/domain memories
    documents: list[dict]        # Uploaded documents
    domain_id: Optional[UUID]    # Active context scope
    domain_name: Optional[str]

    @property
    def user_memories(self) -> list[Memory]:
        """Default domain (user profile) memories"""

    @property
    def domain_memories(self) -> list[Memory]:
        """Domain-scoped memories for active domain"""
```

**Memory structure:**
```python
@dataclass
class Memory:
    content: str
    importance: float
    tags: list[str]       # "preference", "fact", "instruction"
    entities: dict        # NLP extraction
    source_type: str      # "chat", "document", "import"
    domain_id: Optional[UUID]
```

**Mapping:**

| Claude Code Context | YARNNN Context |
|---------------------|----------------|
| Codebase files | Uploaded documents |
| File search | Memory search |
| Working directory | Active domain |
| Git state | Deliverable state |
| - | Platform extracts |

**YARNNN addition: Platform extracts**

YARNNN enriches context with data pulled from connected platforms:
- Slack channel messages
- Gmail inbox items
- Notion page content

This is similar to MCP resource reading but mediated through the deliverable system.

---

### 9. Session / Conversation Management

#### Claude Code Pattern

- Each CLI session is a conversation
- Context summarization for long conversations
- No persistent cross-session memory (stateless)

#### YARNNN TP Equivalent

```sql
-- chat_sessions table
id, user_id, session_type, scope, status, created_at

-- session_messages table
id, session_id, role, content, sequence_number, metadata
```

**Scope options:**
- `conversation` — New session each time
- `daily` — Reuse today's active session

**History reconstruction for Claude:**
```python
def build_history_for_claude(messages):
    """Reconstruct tool_use/tool_result blocks from metadata"""
    # Ensures model sees coherent tool history
```

**YARNNN addition: Persistent memory**

Unlike Claude Code, YARNNN extracts durable context:
- Conversations → Memory extraction → Persisted to DB
- User corrections → Preference learning → Applied to future work

---

## Gap Analysis

### What Claude Code Has That YARNNN Lacks

| Capability | Claude Code | YARNNN Gap | Priority |
|------------|-------------|------------|----------|
| Background agents | Task with run_in_background | ~~Sync only~~ ✅ ADR-039 | ~~Medium~~ Done |
| Agent resume | Resume via agent_id | No persistence | Low |
| File editing | Edit, Write tools | N/A (different domain) | N/A |
| Code execution | Bash tool | N/A | N/A |
| Web search | WebSearch tool | Could add | Medium |
| Plan file | Writes plan.md | Inline via respond() | N/A |

### What YARNNN Has That Claude Code Lacks

| Capability | YARNNN | Claude Code Gap |
|------------|--------|-----------------|
| Recurring execution | Scheduled deliverables | One-shot only |
| Approval queues | Staged review surface | None |
| Platform integration | OAuth + readers/exporters | MCP (similar) |
| Preference learning | Feedback → memory | Stateless |
| UI surfaces | Rich React components | Terminal output |
| Domain scoping | Memory isolation per domain | Global context |

---

## Implementation Implications

### 1. Skill Interface (ADR-038.1)

Given the mapping, skill implementation should follow Claude Code patterns:
- Slash command detection ✓ (exists)
- Prompt expansion ✓ (exists)
- Todo tracking ✓ (exists)
- Plan/Gate/Exec flow ✓ (exists)

**Remaining work:**
- SkillPicker UI for discoverability (deprioritized per ADR-025)
- Skill customization (deferred)

### 2. Pattern Recognition ✅ (ADR-040 Implemented)

Claude Code implicitly detects patterns ("add tests" → test-runner skill). YARNNN has `trigger_patterns` in skill definitions:
```python
"trigger_patterns": ["board update", "investor update", "board report"]
```

**✅ Implemented (ADR-040):**
- Semantic similarity matching via `detect_skill_hybrid()` in `services/skills.py`
- Embedding-based fallback with 0.72 threshold
- Pattern matching first (fast), semantic fallback (higher recall)

**Deferred:**
- User correction learning ("when I say X, I mean skill Y")

### 3. Deep Research / Sub-agents ✅ (ADR-039 Implemented)

Claude Code's Task tool with Explore agent maps to YARNNN's ResearchAgent:
- Both investigate and synthesize
- Both return structured results
- YARNNN stores output in `work_outputs`

**✅ Implemented (ADR-039):**
- Background execution via `run_in_background=True` in `create_and_execute_work()`
- Redis/RQ job queue with worker process
- Progress tracking via `/work/{id}/status` endpoint
- Graceful fallback to sync execution if queue unavailable

**Deferred:**
- Progressive updates via streaming (SSE for background jobs)

### 4. MCP Interoperability (ADR-041 Deferred)

Future direction: YARNNN's platform integrations could expose an MCP interface:
```
mcp__yarnnn__list_deliverables
mcp__yarnnn__run_deliverable
mcp__yarnnn__get_memories
```

This would allow Claude Code to orchestrate YARNNN workflows.

**Deferred (ADR-041):** MCP server exposure is additive integration, not core architecture. Deferred pending validation of ADR-039/ADR-040 and clearer Claude Code adoption signals.

---

## Decision

### Architectural Confidence: Confirmed

The mapping validates that YARNNN's TP infrastructure is architecturally aligned with Claude Code patterns:

1. **Agentic loop** — Identical pattern
2. **Tool system** — Same invocation model, different tools
3. **Skills** — Same prompt-expansion pattern
4. **Streaming** — Same SSE pattern
5. **Context** — Same injection model, different sources

### Implementation Direction

With confidence in the mapping, three enhancement ADRs were spawned:

1. **ADR-040: Semantic Skill Matching** (P1) — Extend trigger_patterns with embeddings
2. **ADR-039: Background Work Agents** (P2) — Add run_in_background capability
3. **ADR-041: MCP Server Exposure** (P3) — Expose YARNNN as MCP server

### No Divergence Required

The mapping shows we're already aligned. Enhancement work can proceed without architectural changes.

---

## References

- Claude Code source patterns (observed via claude-code-guide research)
- Claude Agent SDK documentation
- ADR-025: Claude Code Agentic Alignment
- ADR-036: Two-Layer Architecture
- ADR-037: Chat-First Surface Architecture
- **ADR-039: Background Work Agents** — Spawned from gap analysis
- **ADR-040: Semantic Skill Matching** — Spawned from gap analysis
- **ADR-041: MCP Server Exposure** — Spawned from gap analysis
- YARNNN source: `api/services/`, `api/agents/`, `web/contexts/`

---

## Appendix: Quick Reference Table

| You Want To... | Claude Code Does... | YARNNN Does... |
|----------------|---------------------|----------------|
| Track work progress | TodoWrite tool | todo_write tool |
| Execute skill | /commit → prompt expansion | /board-update → prompt expansion |
| Spawn sub-agent | Task(subagent_type=Explore) | ResearchAgent.execute() |
| Read external data | MCP tools | Platform readers |
| Write external data | Bash, Edit tools | Platform exporters |
| Stream responses | SSE text/tool_use/tool_result | SSE content/tool_use/tool_result |
| Get user approval | ExitPlanMode | clarify() or SetupConfirmModal |
| Inject context | Read files → messages | ContextBundle → system prompt |
| Persist learning | N/A (stateless) | Memory extraction → DB |
