-- ADR-161: Daily Update as Anchor — essential flag on tasks
--
-- Adds a metadata flag distinguishing essential tasks (currently only
-- daily-update) from user-managed tasks. Essential tasks cannot be archived
-- or auto-paused. They can be paused manually by the user.
--
-- The flag is set at workspace initialization (ADR-161 Phase 5 of
-- workspace_init.initialize_workspace) and is not user-settable through any
-- primitive — it is system metadata, not configuration.
--
-- See: docs/adr/ADR-161-daily-update-anchor.md

ALTER TABLE tasks
ADD COLUMN essential boolean NOT NULL DEFAULT false;

-- Narrow index — there will be at most one essential task per user.
-- Used by workspace_init idempotency check and ManageTask guards.
CREATE INDEX idx_tasks_essential ON tasks(user_id, essential)
WHERE essential = true;

COMMENT ON COLUMN tasks.essential IS
  'ADR-161: Essential tasks (e.g., daily-update) cannot be deleted or auto-paused. Set at workspace initialization, not user-settable.';
