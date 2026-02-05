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

This allows Claude to understand what tools it called in previous turns, maintaining conversation coherence.

---

## Configuration Changelog

### 2025-02-05: Coherence Fix

**Problem**: TP was repeating previous responses instead of answering new questions.

**Root Cause**: Tool calls weren't being stored in session history. When loading history, Claude only saw the text output from `respond()`, not the tools it had called (e.g., `list_deliverables`).

**Fix**:
1. Store `tool_history` in message metadata when saving assistant messages
2. Reconstruct tool context when loading history (prefix with `[Called tool_name]`)

**Files Changed**:
- `api/routes/chat.py`: Track tool calls during streaming, store in metadata

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
