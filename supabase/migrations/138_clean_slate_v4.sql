-- ADR-152: Clean slate for v4 domain-steward architecture
-- Wipes all test data so workspace_init creates fresh v4 agents + domains.
-- Pre-launch only — this migration destroys all user data.

-- Clear workspace files (context, outputs, agent files, task files)
DELETE FROM workspace_files;

-- Clear tasks and task-related data
DELETE FROM tasks;

-- Clear agent runs (output history)
DELETE FROM agent_runs;

-- Clear agents (will be recreated by workspace_init with v4 templates)
DELETE FROM agents;

-- Clear chat sessions and messages (fresh start)
DELETE FROM session_messages;
DELETE FROM chat_sessions;

-- Clear activity log
DELETE FROM activity_log;

-- Note: platform_connections preserved (OAuth tokens still valid)
-- Note: filesystem_documents preserved (user uploads still valid)
-- Note: user accounts preserved (auth.users untouched)
