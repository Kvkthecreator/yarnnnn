-- ADR-125: Project-Native Session Architecture — Phase 1
-- Add thread_agent_id to session_messages for 1:1 thread filtering within project sessions.
-- NULL = group message (meeting room main channel), set = thread message (1:1 with specific agent).

ALTER TABLE session_messages
ADD COLUMN thread_agent_id UUID REFERENCES agents(id) DEFAULT NULL;

-- Partial index for efficient thread queries (only indexes rows that ARE in a thread)
CREATE INDEX idx_session_messages_thread
ON session_messages(session_id, thread_agent_id)
WHERE thread_agent_id IS NOT NULL;
