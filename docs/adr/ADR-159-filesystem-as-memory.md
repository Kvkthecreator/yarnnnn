# ADR-159: Filesystem-as-Memory — Referential Context Injection

**Status:** Proposed
**Date:** 2026-04-06
**Supersedes:** Working memory dump model (ADR-059 injection, ADR-063 four-layer model)
**Evolves:** ADR-067 (session compaction), ADR-087 (agent scoped context), ADR-156 (in-session memory)
**Depends on:** ADR-106 (workspace architecture), ADR-138 (agents as work units), ADR-142 (unified filesystem)

---

## Context

TP's current approach: assemble a large working memory block (~3-8K tokens) and inject it into every API call alongside the full conversation history (~2-15K tokens). This means every message costs ~13-23K input tokens regardless of whether TP needs that context.

The system already has a filesystem abstraction (workspace_files) and tools for on-demand reading (ReadWorkspace, GetSystemState). Agent task execution already uses the referential model — agents read workspace files during execution rather than receiving everything in the prompt. TP should do the same.

### Cost analysis (current model)

Per TP message (20-message session average):
- System prompt (static): ~5K tokens (partially cached at ~26%)
- Working memory (dynamic): ~3K tokens (never cached, changes per turn)
- Conversation history: ~8K tokens (grows linearly, dominant cost)
- Tool definitions: ~4K tokens (partially cached)
- **Total: ~20K input tokens per message**

Over a 20-message session: ~400K input tokens. At $3/M input: ~$1.20 per session.

### Target (filesystem-as-memory model)

Per TP message:
- System prompt (compact index + static rules): ~1.5K tokens (highly cacheable)
- Last 5 messages: ~2-3K tokens (rolling window)
- Tool definitions (core only): ~2K tokens (cacheable)
- On-demand reads: ~0-2K tokens (only when TP needs detail)
- **Total: ~5-8K input tokens per message**

Over a 20-message session: ~120K input tokens. At $3/M input: ~$0.36 per session.
**~70% cost reduction.**

---

## Decision

### Principle: Index in prompt, detail on demand

TP receives a compact index of what exists in the workspace (~200-500 tokens) instead of the full working memory dump (~3-8K tokens). TP reads workspace files on demand when it needs detail.

Conversation history is windowed to the last 5 messages. Older conversation context is compacted into a workspace file (`/workspace/memory/conversation.md`) that TP reads on demand.

### Three tiers of context

| Tier | Always in prompt | Content | Tokens |
|------|-----------------|---------|--------|
| **Compact index** | Yes | Agent count, task count, platform status, workspace readiness, surface context | ~200-500 |
| **Recent messages** | Yes | Last 5 messages (rolling window) | ~2-3K |
| **On-demand files** | No — TP reads via tools | conversation.md, notes.md, awareness.md, agent details, domain files | 0 (until read) |

### Compact index structure

```
## Workspace
- 8 agents (5 domain stewards, 1 synthesizer, 2 bots)
- 6 active tasks
- 3 platforms connected (Slack, Notion, GitHub)
- Identity: rich | Brand: set

## Currently viewing
{surface_context — e.g., "Agents page > Competitive Intelligence (competitors/)"}

## Quick status
- Last task run: Track Competitors, 2h ago
- Coming up: Slack Digest tomorrow, Market Research Monday
- Needs attention: Operations has 0 entities

## Memory files available (read with ReadWorkspace)
- /workspace/memory/notes.md — stable user facts
- /workspace/memory/awareness.md — your shift notes from prior sessions
- /workspace/memory/conversation.md — summary of earlier conversation
```

### Conversation compaction as file writes

Instead of database-level session compaction, TP writes conversation summaries to workspace files:

1. **Every 5 messages**: System writes a rolling summary to `/workspace/memory/conversation.md`
2. **On session close** (4h inactivity): Final summary written, becomes the starting context for next session
3. **conversation.md format**: High-fidelity summary prioritizing decisions, corrections, instructions — not topics

```markdown
# Conversation Summary
Last updated: 2026-04-06 14:30 UTC

## Recent decisions
- Created 5 tracking tasks + 1 synthesis task (stakeholder update)
- User confirmed entities: 6 competitors, 3 market segments
- User preference: weekly cadence for competitor tracking

## Current focus
- Testing onboarding flow with IR deck upload
- Reviewing competitor entity profiles for accuracy

## Open items
- Operations agent has no tasks — needs project context from user
- Stakeholder update task created but not yet triggered (waiting for context tasks)
```

### Message window

The API call includes only the **last 5 messages** (user + assistant pairs). This is a rolling window, not a fixed buffer. The window is message-count-based for simplicity (token-budget-based is a future optimization).

Tool-heavy turns (e.g., 5 CreateTask calls) count as one message. The window contains ~2-3K tokens of recent conversation.

### Surface-aware context

The compact index includes a "Currently viewing" section that changes based on the user's page:

| Surface | Currently viewing | Extra context |
|---------|------------------|---------------|
| Home | "Home page" | Daily briefing signals |
| Agents (no selection) | "Agents overview" | Agent roster summary |
| Agents (agent selected) | "Competitive Intelligence (competitors/)" | That agent's domain summary |
| Context | "Workspace explorer > competitors/" | Current path + file metadata |

This replaces the per-surface session model. One session, surface context as metadata.

### Tool set trimming (deferred)

Surface-aware tool definitions are a natural extension but deferred for simplicity. All 15 tools remain available. The token savings from the compact index and message window are sufficient for Phase 1.

---

## Unified session model (companion change)

This ADR assumes the unified session model (implemented in fc4302b):
- One session per workspace (user_id as proxy)
- No agent-scoped or task-scoped sessions
- Surface context on messages, not sessions
- Messages persist across page navigations

---

## Stress test findings

### Scenario analysis

| Scenario | Risk | Assessment |
|---|---|---|
| **Cold start (new user)** | None | Compact index shows "0 tasks, 0 entities" — sufficient signal |
| **Page switching mid-conversation** | Low | Last 5 messages + surface context shift. TP adapts without session reset |
| **Long session (50 messages)** | **Medium** | conversation.md summary loses specificity. Mitigated: decisions + corrections saved to notes.md (stable facts) |
| **Full roster status query** | Low | One extra GetSystemState tool call. Acceptable latency |
| **Task pipeline execution** | None | Separate path, uses TASK.md + DELIVERABLE.md directly |
| **conversation.md write failure** | Low | Last 5 messages are ground truth. conversation.md is supplementary |
| **Multi-tool turns** | **Medium** | Tool-heavy turns inflate message window. Token-budget windowing is future optimization |
| **Cross-session reference ("last week you said...")** | Low | awareness.md handles shift notes. notes.md handles stable facts |

### Key tradeoffs

1. **Summary fidelity vs. token cost**: Compacting 50 messages into a 300-token summary loses detail. Mitigation: high-fidelity summaries that prioritize actionable content (decisions, corrections, instructions), not topics.

2. **Latency on first context access**: TP may need to call ReadWorkspace before answering. Adds ~1-2 seconds per tool round. Acceptable for detailed queries; most messages don't need workspace reads.

3. **Message window edge cases**: A 5-message window can miss context from message #6. Mitigation: conversation.md captures rolling context; TP reads it when uncertain.

---

## Implementation plan

### Phase 1: Compact index + message window

| Step | What | Files |
|------|------|-------|
| 1 | Replace working memory dump with compact index builder | `api/services/working_memory.py` |
| 2 | Implement 5-message rolling window in chat route | `api/routes/chat.py` |
| 3 | Write conversation.md after every 5 messages | `api/routes/chat.py` |
| 4 | Update TP system prompt to reference files instead of inline content | `api/agents/tp_prompts/onboarding.py` |
| 5 | Update TP system prompt base with compact index template | `api/agents/tp_prompts/base.py` |

### Phase 2: Conversation file lifecycle

| Step | What | Files |
|------|------|-------|
| 6 | Write final conversation.md on session close (4h inactivity) | `api/routes/chat.py` |
| 7 | Inject prior session conversation.md summary into next session's compact index | `api/services/working_memory.py` |
| 8 | Verify TP reads conversation.md when it needs older context | Manual E2E test |

### Phase 3: Surface-aware index (deferred)

| Step | What | Files |
|------|------|-------|
| 9 | Add surface-specific detail to compact index | `api/services/working_memory.py` |
| 10 | Trim tool definitions based on surface (optional) | `api/services/primitives/registry.py` |

---

## What this supersedes

| Previous approach | Replacement |
|---|---|
| Full working memory dump (~3-8K tokens per message) | Compact index (~200-500 tokens) + on-demand reads |
| Full conversation history in API call (~2-15K tokens) | Last 5 messages (~2-3K tokens) + conversation.md |
| Per-scope sessions (global/agent/task) | Unified session + surface context metadata |
| Database-level session compaction | File-level conversation.md writes |
| Static tool set (15 tools always) | Core tools always (Phase 1), surface-trimmed (Phase 3) |

---

## What this preserves

| Mechanism | Status |
|---|---|
| Workspace files (IDENTITY.md, notes.md, awareness.md) | Unchanged — already the memory substrate |
| ReadWorkspace / GetSystemState tools | Unchanged — already available to TP |
| In-session memory writes via UpdateContext | Unchanged — TP writes facts to notes.md during conversation |
| Prompt caching (static/dynamic block split) | Enhanced — smaller static block = higher cache hit rate |
| Chat UI message display | Unchanged — full history from database, not from API window |
| Session summaries on close | Evolved — written to conversation.md instead of chat_sessions.summary |

---

## Consistency with Claude Code model

| Claude Code | YARNNN (after this ADR) |
|---|---|
| Compact system prompt (~3K) | Compact index + static rules (~1.5-2K) |
| Auto-compaction at context limit | conversation.md written every 5 messages |
| Read tool for file access | ReadWorkspace for workspace files |
| No pre-loaded file content | No pre-loaded working memory content |
| Conversation stays in context window | Last 5 messages in API call |
| CLAUDE.md read on demand | IDENTITY.md, notes.md read on demand |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-04-06 | v1 — Initial proposal. Compact index, message window, conversation.md, stress test findings. |
