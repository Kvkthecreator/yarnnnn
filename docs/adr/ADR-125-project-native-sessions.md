# ADR-125: Project-Native Session Architecture

**Status**: Proposed → Implementing
**Date**: 2026-03-20
**Supersedes**: ADR-087 (agent-scoped sessions), partially ADR-006 (session model)
**Extends**: ADR-122 (project-first), ADR-124 (meeting room)

---

## Context

Session management evolved incrementally:

1. **ADR-006** (2026-02): Global TP sessions — `chat_sessions` with `user_id`, 4h inactivity reuse.
2. **ADR-087** (2026-03): Agent-scoped sessions — `agent_id` FK on `chat_sessions`, separate thread per agent.
3. **ADR-119 P4b** (2026-03): Project-scoped sessions — `project_slug` on `chat_sessions`, lifetime persistence.
4. **ADR-124** (2026-03): Meeting room — ChatAgent routing within project sessions, author attribution on messages.

These are now three peer-level scoping paths on the same table (`agent_id`, `project_slug`, or neither). ADR-122 established that **all agents belong to projects**, but sessions don't reflect this hierarchy. Standalone agent sessions exist outside any project context, creating an identity ambiguity: the same agent can be chatted with via its project meeting room (ChatAgent, 13 tools) or via its standalone page (TP with agent scope, 22+ tools) — different prompts, different capabilities, different session histories.

## Decision

**Projects are the organizational boundary for all interactive sessions.** Two session scopes:

| Scope | Surface | Reuse rule | Who responds |
|-------|---------|------------|-------------|
| **Global TP** | `/orchestrator` | 4h inactivity | TP (full primitives) |
| **Project** | `/projects/{slug}` | 24h inactivity | TP or ChatAgent (routed by @-mention / thread) |

**No standalone agent sessions.** Agent interaction is always project-contextualized.

### Thread Model

Project sessions use a **group + thread** model within a single session row:

```
Project Session (the meeting room — group channel)
├── Group messages (thread_agent_id = NULL)
│   User ↔ PM, user ↔ contributors via @mention
├── Thread: user ↔ Slack Agent (thread_agent_id = agent-uuid-1)
│   1:1 deep-dive, feedback, instructions
├── Thread: user ↔ PM (thread_agent_id = pm-uuid)
│   1:1 steering, work plan review
└── Thread: user ↔ Synthesizer (thread_agent_id = agent-uuid-2)
    1:1 feedback on outputs
```

Threads are **not separate sessions** — they're a message-level filter (`thread_agent_id` on `session_messages`). The project session row remains singular.

### Schema Change

```sql
-- Phase 1: Add thread column
ALTER TABLE session_messages
ADD COLUMN thread_agent_id UUID REFERENCES agents(id) DEFAULT NULL;

-- Phase 1: Index for efficient thread queries
CREATE INDEX idx_session_messages_thread
ON session_messages(session_id, thread_agent_id)
WHERE thread_agent_id IS NOT NULL;
```

- `NULL` = group message (meeting room main channel)
- Set = thread message (1:1 with specific agent)

No new tables. No new session rows.

### Agent Page Transformation

The `/agents/{id}` page becomes the **agent's 1:1 thread view within its project**:

- Chat area renders the thread from the project session (filtered by `thread_agent_id`)
- The 6-tab workspace panel (Runs, Outputs, Instructions, Memory, Sessions, Settings) stays — it IS the agent's identity surface
- Navigation: agent page reads the agent's project membership, finds the project session, renders the thread
- For single-agent projects (`pm: False`), the project page and agent thread view collapse into one

### Session Routing (chat.py)

```python
# Before (three paths):
if project_slug:
    session = get_or_create_project_session(...)
elif agent_id:
    session = get_or_create_session(..., agent_id=agent_id)  # standalone
else:
    session = get_or_create_session(...)  # global TP

# After (two paths):
if project_slug or agent_id:
    # Agent requests → resolve to project, then use project session
    project_slug = project_slug or resolve_agent_project(agent_id)
    session = get_or_create_project_session(..., project_slug)
    # thread_agent_id set on messages, not on session
else:
    session = get_or_create_session(...)  # global TP
```

### Project Session Rotation

Project sessions rotate on **24h inactivity** (not lifetime). On rotation:

1. Generate author-aware summary (compaction prompt attributes decisions to participants)
2. Store summary on `chat_sessions.summary`
3. Create new session for the project
4. Thread summaries generated independently per `thread_agent_id`

### Global TP Awareness

Working memory `_get_recent_sessions_sync()` expands to include project session summaries:

```markdown
### Recent conversations
- 2026-03-20: Reviewed Notion recap output, updated instructions for brevity (notion-recap)
- 2026-03-19: PM steered cross-platform synthesis focus areas (cross-platform-insights)
- 2026-03-19: Connected Slack, set up recap project
```

TP doesn't need full project context — it needs to know what happened and where to point the user.

### What Gets Deleted

- `get_or_create_session()` `agent_id` parameter — agent sessions always go through project
- `chat_sessions.agent_id` column — deprecated (threads replace it at message level)
- Standalone agent session creation path in `chat.py`
- Agent-scoped session summary injection in `_extract_agent_scope()` (replaced by thread-aware project summaries)

## Phases

1. **Schema**: Add `thread_agent_id` to `session_messages` (nullable, non-breaking)
2. **Routing**: Reroute agent-scoped session creation through project sessions with thread_agent_id on messages
3. **Rotation**: Project session 24h rotation + author-aware compaction summaries
4. **Working memory**: Include project session summaries in global TP context
5. **Cleanup**: Delete standalone agent session path, deprecate `chat_sessions.agent_id`

## Consequences

**Positive:**
- Agent identity is enriched (project context always available), not diminished
- Single session per project = one place to look for all project conversation
- Threads give 1:1 depth without fragmenting the project boundary
- Global TP gets cross-project awareness via session summaries
- Simpler routing: two paths instead of three

**Negative:**
- Agent detail page frontend needs rework to read from project thread instead of standalone session
- Existing agent-scoped sessions need migration (or graceful fallback)
- Thread-filtered queries slightly more complex than session-level queries

**Neutral:**
- Headless mode unchanged (no sessions involved)
- Compaction mechanics same, just author-aware prompt
