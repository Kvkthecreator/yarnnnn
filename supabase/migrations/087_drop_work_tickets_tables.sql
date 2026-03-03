-- ADR-090 Phase 4: Drop legacy work_tickets execution tables
--
-- work_tickets, work_outputs, and work_execution_log are fully replaced by:
--   - deliverable_versions (primary execution record)
--   - activity_log (audit trail)
--
-- agent_sessions is the old pre-ADR-080 agent session table (empty, superseded
-- by chat_sessions + session_messages).
--
-- All backend writers/readers and frontend consumers removed in ADR-090 Phase 3.

DROP TABLE IF EXISTS agent_sessions;
DROP TABLE IF EXISTS work_execution_log;
DROP TABLE IF EXISTS work_outputs;
DROP TABLE IF EXISTS work_tickets;
