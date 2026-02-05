# Thinking Partner (TP) Configuration

> **Status**: Active development
> **ADRs**: ADR-023 (Supervisor Desk), ADR-025 (Claude Code Agentic Alignment)

---

## Overview

The Thinking Partner (TP) is YARNNN's conversational AI assistant. This document tracks configuration changes, prompt engineering decisions, and implementation details for future reference.

---

## Architecture

### Key Files

| File | Purpose |
|------|---------|
| `api/agents/thinking_partner.py` | Core TP agent with system prompts and tool execution |
| `api/routes/chat.py` | Chat endpoint handling TP streaming and session management |
| `api/services/skills.py` | Skills system for slash commands |
| `web/contexts/TPContext.tsx` | Frontend state management for TP |
| `web/components/tp/TPDrawer.tsx` | UI component for TP conversation |

### Communication Flow

```
User Input → TPDrawer → TPContext.sendMessage() → POST /api/chat
                                                        │
                                                        ▼
                                              ThinkingPartnerAgent
                                                        │
                                                        ▼
                                              Claude API (streaming)
                                                        │
                                                        ▼
                                              Tool Execution Loop
                                                        │
                                                        ▼
                                              SSE Events → TPContext
                                                        │
                                                        ▼
                                              UI Updates (messages, status)
```

---

## System Prompt Structure

The TP system prompt (`SYSTEM_PROMPT_WITH_TOOLS`) follows this structure:

1. **Context Scope** - Current project or personal context
2. **Memory Context** - User and project memories
3. **Surface Content** (optional) - What user is currently viewing
4. **Core Instructions** - Tool usage patterns, response guidelines
5. **Domain-Specific Sections** - Plan mode, todo tracking, deliverable creation
6. **Skill Prompt** (optional) - Injected when a skill is active

---

## Session Management

### History Storage

Sessions use a `daily` scope - messages within the same day are grouped together.

**History Limits** (Claude Code alignment):
- Maximum 30 messages loaded into context (prevents overflow)
- Always starts with a user message (Anthropic API requirement)
- Most recent messages are prioritized

**Message Storage** (as of 2025-02-05):
- User messages: Plain text content
- Assistant messages: Text content + metadata
- Metadata includes:
  - `model`: Model used for generation
  - `tools_used`: List of tool names called
  - `tool_history`: Detailed tool call records for coherence

### Tool History Format

```json
{
  "tool_history": [
    {
      "type": "tool_call",
      "name": "list_deliverables",
      "input_summary": "{}",
      "result_summary": "{\"success\": true, \"count\": 10, ...}"
    },
    {
      "type": "text",
      "content": "You have 10 active deliverables."
    }
  ]
}
```

### History Reconstruction (Claude Code Pattern)

When loading history, we reconstruct Anthropic-format messages with proper `tool_use` and `tool_result` blocks:

```python
# Stored format (simplified)
{"role": "assistant", "content": "...", "metadata": {"tool_history": [...]}}

# Reconstructed for Claude API (structured)
[
  {"role": "assistant", "content": [
    {"type": "tool_use", "id": "tool_list_deliverables_0", "name": "list_deliverables", "input": {}},
    {"type": "text", "text": "You have 10 deliverables."}
  ]},
  {"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "tool_list_deliverables_0", "content": "..."}
  ]}
]
```

This matches how Claude Code maintains tool context across turns, improving coherence.

---

## Configuration Changelog

### 2025-02-05: Structured History & Context Limits (Claude Code Alignment)

**Problem**:
1. TP was repeating previous responses (coherence issue)
2. Long sessions could overflow context window
3. Simplified text-based history lost tool context fidelity

**Root Cause**: Tool calls weren't stored properly, and history wasn't limited or structured like Claude Code.

**Fix**:
1. Added `MAX_HISTORY_MESSAGES = 30` limit to prevent context overflow
2. Implemented `build_history_for_claude()` helper function
3. Reconstruct proper Anthropic `tool_use`/`tool_result` message blocks
4. Store `tool_history` in message metadata with input/result summaries

**Files Changed**:
- `api/routes/chat.py`: New `build_history_for_claude()` function, both endpoints updated

### 2025-02-05: Clarification Response Handling

**Problem**: When user clicked a clarify option, TP called navigation tools instead of acting on the selection.

**Root Cause**: The selected option was treated as a new request rather than a response to the previous clarify call.

**Fix**:
1. Added `_detect_clarification_response()` to check if previous turn had a clarify call
2. Wrap clarification responses with `[CLARIFICATION RESPONSE]` guidance to prompt action

**Files Changed**:
- `api/agents/thinking_partner.py`: Added detection and wrapping logic

### 2025-02-05: Performance Optimization

**Problem**: Jittery lag in TP responses, loading state persisting.

**Fix**:
1. Batch streaming status updates (update every ~50 chars instead of every chunk)
2. Ensure final status update after stream completion

**Files Changed**:
- `web/contexts/TPContext.tsx`: Throttle status updates during streaming

### 2025-02-04: Stale Todos Fix

**Problem**: Todo list from previous workflow lingered when switching topics.

**Fix**: Dispatch `CLEAR_WORK_STATE` at start of `sendMessage()` to reset todos.

**Files Changed**:
- `web/contexts/TPContext.tsx`: Added CLEAR_WORK_STATE dispatch

### 2025-02-04: Mobile Layout Fix

**Problem**: iOS Safari keyboard broke the drawer layout.

**Fix**: Use `100dvh` (dynamic viewport height) instead of `inset-0`.

**Files Changed**:
- `web/components/tp/TPDrawer.tsx`: Changed to h-[100dvh]

---

## Known Issues

### Context Indicator Behavior

The context indicator in TPDrawer shows:
- **Surface label**: Current surface type (Deliverables, Dashboard, etc.)
- **Project selector**: Selected project or "Personal"

This reflects the **current UI state**, not necessarily the context TP used for a response. Future enhancement could show "context used" separately.

### Response Streaming Performance

Large responses with many tool calls can cause UI lag due to frequent re-renders. Current mitigation: batch status updates every ~50 characters.

---

## Testing Checklist

When making TP changes, verify:

- [ ] Basic conversation works
- [ ] Tool calls execute correctly
- [ ] Clarify options are clickable and work
- [ ] Multi-turn conversations maintain coherence
- [ ] Skills (slash commands) work
- [ ] Mobile layout works (iOS Safari with keyboard)
- [ ] Loading state clears after response
- [ ] Todo progress displays correctly

---

## Future Considerations

1. **Streaming Optimization**: Consider debouncing status updates more aggressively
2. **Context Display**: Show "context used for this response" in UI
3. **Session Boundaries**: Consider conversation-scoped sessions vs daily sessions
4. **Error Recovery**: Better handling of partial stream failures
