# ADR-006: Session and Message Architecture

**Status:** Accepted (Implemented)
**Date:** 2026-01-29
**Related:** ADR-005 (Unified Memory with Embeddings)
**Decision Makers:** Kevin Kim

## Context

With ADR-005's unified memory architecture now implemented, we need to address how chat sessions and messages are stored. The current implementation has several architectural issues discovered during production testing:

### Current State

**`agent_sessions` table (001_initial_schema.sql):**
```sql
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY,
    agent_type TEXT NOT NULL,
    messages JSONB DEFAULT '[]',     -- Full conversation as array
    metadata JSONB DEFAULT '{}',
    ticket_id UUID REFERENCES work_tickets(id),
    project_id UUID NOT NULL REFERENCES projects(id),  -- NOT NULL!
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

### Problems Identified

1. **Denormalized messages**: Storing full message array as JSONB prevents:
   - Individual message queries (search, filter by content)
   - Message-level operations (edit, delete, pagination)
   - Efficient partial loading (load recent 10 messages vs entire history)
   - Timeline views with date grouping

2. **Global chat blocked**: `project_id NOT NULL` constraint prevents storing global (user-level) chat sessions where no project exists

3. **No direct user ownership**: Sessions owned via project→workspace→owner chain, which:
   - Makes RLS policies complex and slow
   - Can't query "all my sessions" without JOIN cascade
   - Fails entirely for global chat (no project)

4. **Implicit session lifecycle**: Frontend manages session continuity by passing history on each request. No server-side session reuse logic means:
   - Multiple browser tabs = multiple sessions for same conversation
   - Page refresh loses current session state until next history load
   - No clear session boundaries (when does a conversation "end"?)

5. **No user_id column**: Can't implement global chat history endpoint

### Comparison: chat_companion Architecture

The chat_companion repo uses a normalized pattern that solves these issues:

```
conversations (session container)
    ├── id, user_id, channel, status
    ├── started_at, ended_at
    └── metadata (mood_summary, topics)

messages (individual messages)
    ├── id, conversation_id, role, content
    ├── sequence_number, created_at
    └── metadata (tokens, latency)
```

**Key patterns:**
- `get_or_create_conversation()` - reuses same session per day/channel
- Individual messages queryable and indexable
- Explicit session lifecycle (active → completed)
- Direct user_id on conversations for fast queries

## Decision

Evolve the session/message architecture to support both the current YARNNN patterns and chat_companion's proven practices.

### 1. Normalize Messages

Split `agent_sessions.messages` JSONB into separate `session_messages` table:

```sql
-- Rename for clarity: agent_sessions → chat_sessions
-- (agents can still use this for work ticket sessions)

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership (direct, not via project chain)
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Scope (nullable for global chat)
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,

    -- Session metadata
    session_type TEXT NOT NULL DEFAULT 'thinking_partner',
    status TEXT NOT NULL DEFAULT 'active',  -- active, completed, archived

    -- Lifecycle
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,

    -- Context snapshot (what memories were loaded)
    context_metadata JSONB DEFAULT '{}',
    -- {memories_count, context_type, model}

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE session_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,

    -- Message content
    role TEXT NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,

    -- Ordering
    sequence_number INTEGER NOT NULL,

    -- Metadata (optional)
    metadata JSONB DEFAULT '{}',
    -- {tokens, latency_ms, model}

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_project ON chat_sessions(project_id);
CREATE INDEX idx_chat_sessions_status ON chat_sessions(status) WHERE status = 'active';
CREATE INDEX idx_session_messages_session ON session_messages(session_id, sequence_number);
```

### 2. Session Lifecycle Management

Implement explicit session lifecycle with configurable scope:

```python
class SessionScope(Enum):
    CONVERSATION = "conversation"  # New session per exchange (legacy)
    DAILY = "daily"                # One session per project/day
    PROJECT = "project"            # Long-lived session per project

async def get_or_create_session(
    user_id: str,
    project_id: Optional[str],
    session_type: str = "thinking_partner",
    scope: SessionScope = SessionScope.DAILY
) -> ChatSession:
    """
    Get active session or create new one based on scope.

    Scope behaviors:
    - CONVERSATION: Always creates new session (backward compatible)
    - DAILY: Reuses active session from today, creates new if none exists
    - PROJECT: Reuses any active session for project, creates new if none
    """
    if scope == SessionScope.CONVERSATION:
        return await create_session(user_id, project_id, session_type)

    # Check for existing active session
    query_parts = [
        "user_id = :user_id",
        "session_type = :session_type",
        "status = 'active'"
    ]

    if project_id:
        query_parts.append("project_id = :project_id")
    else:
        query_parts.append("project_id IS NULL")

    if scope == SessionScope.DAILY:
        query_parts.append("DATE(started_at) = CURRENT_DATE")

    existing = await db.fetch_one(
        f"SELECT * FROM chat_sessions WHERE {' AND '.join(query_parts)} LIMIT 1",
        {"user_id": user_id, "project_id": project_id, "session_type": session_type}
    )

    if existing:
        return ChatSession(**existing)

    return await create_session(user_id, project_id, session_type)
```

### 3. Message Append Pattern

Change from "save full array" to "append message":

```python
async def append_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None
) -> SessionMessage:
    """Append a single message to session."""
    # Get next sequence number
    result = await db.fetch_one(
        "SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq "
        "FROM session_messages WHERE session_id = :session_id",
        {"session_id": session_id}
    )

    message = await db.execute(
        """
        INSERT INTO session_messages (session_id, role, content, sequence_number, metadata)
        VALUES (:session_id, :role, :content, :sequence_number, :metadata)
        RETURNING *
        """,
        {
            "session_id": session_id,
            "role": role,
            "content": content,
            "sequence_number": result["next_seq"],
            "metadata": metadata or {}
        }
    )

    return SessionMessage(**message)
```

### 4. History Loading

Support paginated history loading:

```python
async def get_session_messages(
    session_id: str,
    limit: int = 50,
    before_sequence: Optional[int] = None
) -> list[SessionMessage]:
    """Load messages with optional pagination."""
    query = """
        SELECT * FROM session_messages
        WHERE session_id = :session_id
    """

    if before_sequence:
        query += " AND sequence_number < :before_sequence"

    query += " ORDER BY sequence_number DESC LIMIT :limit"

    # Reverse to get chronological order
    messages = await db.fetch_all(query, {...})
    return list(reversed(messages))
```

### 5. RLS Policies

Simplified policies with direct user_id ownership:

```sql
-- Chat sessions: direct user ownership
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users own their chat sessions"
    ON chat_sessions FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Messages: inherit from session
ALTER TABLE session_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access messages in their sessions"
    ON session_messages FOR ALL
    USING (
        session_id IN (
            SELECT id FROM chat_sessions WHERE user_id = auth.uid()
        )
    );
```

## Migration Strategy

### Phase 1: Add New Tables (Non-breaking)

1. Create `chat_sessions` table (new name, doesn't conflict)
2. Create `session_messages` table
3. Update chat routes to use new tables
4. Keep `agent_sessions` for backward compatibility during transition

### Phase 2: Migrate Work Agent Sessions

1. Update work ticket agents to use `chat_sessions`
2. Migrate any needed data from `agent_sessions`
3. Deprecate `agent_sessions` table

### Phase 3: Cleanup

1. Drop `agent_sessions` table
2. Remove legacy code paths

## API Changes

### New Endpoints

```
GET  /api/chat/sessions                  # List user's sessions
GET  /api/chat/sessions/:id/messages     # Get session messages (paginated)
POST /api/chat/sessions/:id/messages     # Append message (internal)

# Project-scoped (existing, updated)
GET  /api/projects/:id/chat/sessions     # List project sessions
POST /api/projects/:id/chat              # Send message (uses get_or_create)
```

### Updated Response Format

```json
// GET /api/projects/:id/chat/history
{
  "session": {
    "id": "uuid",
    "status": "active",
    "started_at": "2026-01-29T10:00:00Z",
    "message_count": 12
  },
  "messages": [
    {"role": "user", "content": "...", "sequence": 1, "created_at": "..."},
    {"role": "assistant", "content": "...", "sequence": 2, "created_at": "..."}
  ],
  "has_more": false
}
```

## Consequences

### Positive

- **Queryable messages**: Can search, filter, paginate at message level
- **Global chat support**: `project_id` nullable enables user-level chat
- **Clear ownership**: Direct `user_id` simplifies RLS and queries
- **Session continuity**: Server-side session reuse prevents duplicate sessions
- **Scalable**: Normalized structure handles large conversation histories
- **Future features**: Enables message editing, reactions, threading

### Negative

- **Migration complexity**: Existing `agent_sessions` data needs handling
- **More queries**: 2 queries (session + messages) vs 1 (JSONB array)
- **Sequence management**: Need to handle concurrent message appends

### Risks

- **Concurrent appends**: Two requests could get same sequence number
- **Session reuse confusion**: User might expect fresh session on new tab

### Mitigations

- Use database-level sequence or `SELECT FOR UPDATE` for sequence numbers
- Add "New Conversation" button for explicit session reset
- Consider optimistic sequence with retry on conflict

## Decision Checklist

- [x] Create ADR-006 (this document)
- [x] Design migration `008_chat_sessions.sql`
- [x] Update chat routes to use new tables
- [x] Add global chat history endpoint (`GET /chat/history`)
- [x] Update frontend `useChat` hook for new API
- [ ] Add session management UI (optional - future)
- [x] Deploy Phase 1 (add tables)
- [ ] Deploy Phase 2 (migrate agent_sessions) - deferred
- [ ] Deploy Phase 3 (cleanup agent_sessions) - deferred

## References

- [ADR-005: Unified Memory with Embeddings](ADR-005-unified-memory-with-embeddings.md)
- [chat_companion conversation.py](../../chat_companion/api/src/services/conversation.py) - Reference implementation
- [PostgreSQL Advisory Locks](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS) - For sequence management
