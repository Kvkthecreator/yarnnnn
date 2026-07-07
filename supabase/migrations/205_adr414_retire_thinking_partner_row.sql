-- Migration 205 — ADR-414 D3: the ADR-216 collapse.
-- One system agent (Freddie); the rail is its voice. The thinking_partner
-- agents-table row was ADR-216's "pragmatic implementation substrate"
-- (chat session state + continuity) — nothing reads it at runtime anymore:
--   * routes/feed.py + mcp_server key sessions on chat_sessions.session_type
--     (the 'thinking_partner' SLUG survives there as data-compat);
--   * the roster has filtered the row out since ADR-272;
--   * back-office task ownership dissolved with ADR-260/261.
-- workspace_init stops scaffolding it in the same commit. FK posture:
-- agent_runs cascades (no live runs attach to this row class);
-- chat_sessions.agent_id is SET NULL (and was NULL for narrative sessions
-- by construction since ADR-219).

DELETE FROM agents
WHERE role = 'thinking_partner'
  AND origin = 'system_bootstrap';

-- Receipt query (run after):
--   SELECT count(*) FROM agents WHERE role = 'thinking_partner';
-- Expected: 0.
