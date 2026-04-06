# Sessions

> How TP conversations start, continue, and end — and what carries over between them.

---

## The short version (current model — ADR-159 proposed)

- **One session per workspace** — no agent-scoped or task-scoped sessions. Surface context (which page/agent the user is viewing) is metadata on messages, not a session boundary.
- Sessions use **inactivity-based boundaries** (4-hour gap = new session).
- TP receives a **compact index** (~200-500 tokens) of workspace state instead of a full working memory dump (~3-8K tokens). TP reads workspace files on demand via ReadWorkspace.
- **Message window**: last 5 messages sent to API. Older conversation context compacted into `/workspace/memory/conversation.md` — TP reads on demand.
- **In-session compaction**: `conversation.md` written every 5 messages as a rolling summary.
- Cross-session continuity via shift notes (`/workspace/memory/awareness.md`) and stable facts (`/workspace/memory/notes.md`).

---

## Session lifecycle

### Starting a session

Every chat message goes through `get_or_create_session()` in [chat.py](../../api/routes/chat.py):

- **If a session exists with activity within the last 4 hours**: reuse it
- **If not**: create a new `chat_sessions` row

Unified session model (ADR-159): all messages route to the global session regardless of which page the user is on. `agent_id` and `task_slug` on `chat_sessions` are deprecated — surface context is tracked per message, not per session.

### Within a session

Every user message and assistant response is appended to `session_messages`. The API call receives:

| Content | Tokens | Source |
|---------|--------|--------|
| Compact index | ~200-500 | Built from agents + tasks + workspace state |
| Last 5 messages | ~2-3K | Rolling window from session_messages |
| System prompt (static rules + tools) | ~3-4K | Cached via prompt caching |
| On-demand reads | 0-2K | Only when TP calls ReadWorkspace |

Total: ~5-8K input tokens per message (vs ~18-23K in previous model).

### Conversation compaction

Every 5 messages, the system writes a rolling summary to `/workspace/memory/conversation.md`. This file captures decisions, corrections, instructions, and current focus — not just topics.

TP reads `conversation.md` via ReadWorkspace when it needs older context (e.g., user references something from earlier in the session).

### Ending a session

Sessions close on 4-hour inactivity. On close, a final `conversation.md` summary is written. The `awareness.md` file (TP's shift notes) carries context to the next session.

---

## What carries over between sessions

| What | Source | How it gets there |
|---|---|---|
| Stable user facts (name, role, preferences) | `/workspace/memory/notes.md` | TP writes in-session via UpdateContext(target="memory") |
| Shift handoff notes | `/workspace/memory/awareness.md` | TP writes in-session via UpdateContext(target="awareness") |
| Prior conversation summary | `/workspace/memory/conversation.md` | Written every 5 messages + on session close |
| Agent roster + task status | `agents` + `tasks` tables | Live queries in compact index |
| Platform connection status | `platform_connections` | Live query in compact index |

**What does NOT carry over:**
- Raw conversation history (only the summary in conversation.md)
- Tool execution results
- Full working memory dump (replaced by compact index)

---

## Contrast with Claude Code

| | Claude Code | YARNNN (ADR-159) |
|---|---|---|
| **Session boundary** | Context-window-driven | Inactivity-based (4h) |
| **In-session compaction** | Auto-compaction (`<summary>` block) | conversation.md written every 5 messages |
| **Cross-session memory** | CLAUDE.md + auto memory (MEMORY.md) | notes.md + awareness.md + conversation.md |
| **Context injection** | Compact prompt, read files on demand | Compact index, ReadWorkspace on demand |
| **Tool definitions** | Available tools in prompt | Same (15 tools, ~4K tokens, cached) |
| **File access** | Read tool | ReadWorkspace tool |

The models are now closely aligned. Both use referential injection (point to files, read on demand) rather than dump-everything-into-prompt.

---

## Unified session model

Previous model (ADR-087, ADR-125): per-scope sessions (global, agent-scoped, task-scoped). Navigating between pages cleared messages and loaded different session histories.

Current model (ADR-159): one session per workspace. Messages persist across page navigations. Surface context (which page/agent the user is viewing) is sent per message and used for working memory injection — TP adapts its focus without session boundaries.

| Previous | Current |
|---|---|
| Global session (Home, Context) | One session for all pages |
| Agent-scoped session (per agent) | Surface context metadata per message |
| Task-scoped session (per task) | Surface context metadata per message |
| Messages cleared on navigation | Messages persist |
| `agent_id` on chat_sessions | Deprecated — surface_context on messages |

---

## Architecture direction (ADR-159)

### Phase 1: Compact index + message window

Replace working memory dump with compact index builder. Implement 5-message rolling window. Write conversation.md every 5 messages. Update TP prompts to reference files.

### Phase 2: Conversation file lifecycle

Write final conversation.md on session close. Inject prior session summary into next session's compact index. Verify TP reads conversation.md for older context.

### Phase 3: Surface-aware index

Add surface-specific detail to compact index (e.g., agent domain summary when viewing an agent). Optionally trim tool definitions by surface.

---

## Related

- [Memory](./memory.md) — what persists across sessions and how it's written
- [ADR-159](../adr/ADR-159-filesystem-as-memory.md) — Filesystem-as-memory architecture (proposed)
- [ADR-067](../adr/ADR-067-session-compaction-architecture.md) — Session compaction (implemented, evolved by ADR-159)
- [ADR-156](../adr/ADR-156-composer-sunset.md) — In-session memory writes (implemented)
- `api/routes/chat.py` — session creation, message append, history building
- `api/services/working_memory.py` — compact index builder
