# Sessions

> How YARNNN conversations start, continue, and end — and what carries over between them.

---

## The short version (current model — ADR-159 + ADR-186 + ADR-219 + ADR-220)

- **One session per workspace** — no agent-scoped or task-scoped sessions. Surface context (which page/agent the user is viewing) is metadata on messages, not a session boundary.
- Sessions use **inactivity-based boundaries** (4-hour gap = new session).
- YARNNN receives a **compact index** (~200-500 tokens, hard 600-token ceiling) of workspace state instead of a full working memory dump (~3-8K tokens). YARNNN reads workspace files on demand via `ReadFile`.
- **Three-layer context model** (ADR-220): static-cached prompt + workspace state pointers + windowed conversation history. See "Layered context model" section below.
- **Message window**: last 10 messages sent to API. Older conversation context compacted into `/workspace/memory/conversation.md` — YARNNN reads on demand. Non-conversation Identity classes (system/reviewer/agent/external — ADR-219) are filtered from the API messages list and surface via `recent.md` instead (ADR-220 Commit A).
- **In-session compaction is filesystem-native**: `conversation.md` written every 5 messages as a rolling summary. The 40K-token in-session LLM compaction (ADR-067 Phase 3) was deleted in ADR-220 Commit C — `conversation.md` is the singular compaction substrate.
- **Recent material non-conversation events** roll up daily into `/workspace/memory/recent.md` via the `back-office-narrative-digest` task (ADR-220 Commit C). Counterpart to ADR-209's substrate-authorship signal.
- Cross-session continuity via shift notes (`/workspace/memory/awareness.md`) and stable facts (`/workspace/memory/notes.md`).

---

## Layered context model (ADR-220)

Every YARNNN chat turn assembles its prompt from three layers. Token budget and ownership boundaries:

| Layer | Source | Cached? | Token budget | Identity-handling |
|---|---|---|---|---|
| **Layer 1 — Static** | `BASE` + behavioral profile (workspace/entity per ADR-186) + `TOOLS_CORE` + `PLATFORMS` + `CONTEXT_AWARENESS` | Yes (cache_control: ephemeral) | ~12-15K, ~95% cache hit | n/a — no per-turn variance |
| **Layer 2 — Workspace state** | `format_compact_index()` + two complementary one-liner pointers | No (changes per turn) | 600-token ceiling | Per-Identity authorship one-liner (ADR-209); narrative events one-liner (ADR-220 → recent.md) |
| **Layer 3 — Conversation history** | `build_history_for_claude()` over the last 10 `session_messages` | Partial | ~2-3K | **Filtered to user/assistant only** (ADR-220 Commit A) |

### Two complementary signals in Layer 2

The compact index gets two one-liner pointers, each ~30 tokens, both pointing at filesystem-native files for on-demand detail.

**Substrate axis (ADR-209):**
```
Recent activity (24h, 23 revisions): operator (3), yarnnn (12), agent (5), system (3) — use ListRevisions/ReadRevision/DiffRevisions to inspect.
```
Answers: "who wrote what file" — file-level mutation truth from `workspace_file_versions`.

**Narrative axis (ADR-220):**
```
Recent events (24h, 7 material non-conversation): 3 reviewer, 2 agent, 1 external, 1 system — read /workspace/memory/recent.md if needed.
```
Answers: "what invocations happened" — invocation-level activity from `session_messages`, filtered to material weight + non-conversation Identity classes.

The two layers don't duplicate. Substrate authorship is the *file-system* fact; narrative is the *operator-facing log*. Most invocations produce substrate mutations, but not all (e.g., `pull_context` MCP read), and some substrate mutations don't have a narrative entry (e.g., backfill migrations). They are orthogonal axes of the same workspace.

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
| Stable user facts (name, role, preferences) | `/workspace/memory/notes.md` | YARNNN writes in-session via UpdateContext(target="memory") |
| Shift handoff notes | `/workspace/memory/awareness.md` | YARNNN writes in-session via UpdateContext(target="awareness") |
| Prior conversation summary | `/workspace/memory/conversation.md` | Written every 5 messages + on session close |
| Recent material non-conversation events | `/workspace/memory/recent.md` | Written daily by `back-office-narrative-digest` task (ADR-220) |
| Agent roster + task status | `agents` + `tasks` tables | Live queries in compact index |
| Platform connection status | `platform_connections` | Live query in compact index |
| Recent substrate authorship | `workspace_file_versions` | One-line signal in compact index (ADR-209) |

**What does NOT carry over:**
- Raw conversation history (only the summary in conversation.md)
- Tool execution results
- Full working memory dump (replaced by compact index)

---

## Contrast with Claude Code

| | Claude Code | YARNNN (ADR-159 + ADR-220) |
|---|---|---|
| **Session boundary** | Context-window-driven | Inactivity-based (4h) |
| **In-session compaction** | Auto-compaction (LLM `<summary>` block) when near context limit | conversation.md written every 5 user messages (filesystem-native, zero LLM) |
| **Cross-session memory** | CLAUDE.md + auto memory (MEMORY.md) | notes.md + awareness.md + conversation.md |
| **Context injection** | Compact prompt, read files on demand | Compact index, ReadFile on demand |
| **Tool definitions** | Available tools in prompt | Same (~14 chat tools, ~4K tokens, cached) |
| **File access** | Read tool | ReadFile primitive |
| **Conversation log** | user/assistant turns only | Six Identity classes (user/assistant/system/reviewer/agent/external — ADR-219). API messages filter to user/assistant; non-conversation classes surface via `recent.md` (ADR-220) |
| **Tool-history retention** | "Tool outputs drop first" auto-compaction | Most-recent tool turn structured; older tool turns collapse to one-line summaries (ADR-220 Commit B) |

The models are now closely aligned. Both use referential injection (point to files, read on demand) rather than dump-everything-into-prompt. ADR-220 closes the post-ADR-219 gaps — non-conversation roles, older tool-history bloat, in-session LLM compaction.

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
- [ADR-159](../adr/ADR-159-filesystem-as-memory.md) — Filesystem-as-memory architecture (Implemented)
- [ADR-186](../adr/ADR-186-tp-prompt-profiles.md) — Surface-aware prompt profiles (workspace / entity)
- [ADR-209](../adr/ADR-209-authored-substrate.md) — Authored substrate signal (file-level "who wrote what")
- [ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) — Narrative substrate (six Identity classes on session_messages)
- [ADR-220](../adr/ADR-220-layered-context-strategy.md) — Layered context strategy + recent.md narrative-side rollup + in-session LLM compaction sunset
- [ADR-067](../adr/ADR-067-session-compaction-architecture.md) — Session compaction (Phase 1+2 Implemented; Phase 3 superseded by ADR-220)
- [ADR-156](../adr/ADR-156-composer-sunset.md) — In-session memory writes (Implemented)
- `api/routes/chat.py` — session creation, message append, history building (filtered to user/assistant per ADR-220 A)
- `api/services/working_memory.py` — compact index builder (with two complementary one-liner pointers per ADR-220 C)
- `api/services/back_office/narrative_digest.py` — daily roll-up writer for chat-card + recent.md
