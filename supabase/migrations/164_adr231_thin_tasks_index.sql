-- ADR-231 Phase 3.4 — tasks table becomes the thin scheduling index (Path B).
--
-- Authoritative recurrence-declaration substrate is workspace_files YAML at
-- declaration_path. This table is fully reconstructable from filesystem state
-- via services.scheduling.materialize_scheduling_index().
--
-- Naming note: the table identifier "tasks" is preserved as the index
-- identifier (per ADR-231 D4 Path B). The COMMENT below makes this explicit
-- so the name doesn't suggest task-as-substrate (which dissolved per D2).
--
-- Schema changes:
--   - DROP COLUMN mode (was added by 132; dissolves per D5 — temporal behavior
--     is now implied by the recurrence shape, which is implied by substrate
--     location)
--   - DROP COLUMN essential (was added by 141; dissolves per D6 —
--     daily-update reframes as a recurrence declaration; if the operator
--     deletes the YAML, the recurrence stops)
--   - ADD COLUMN declaration_path TEXT (pointer to authoritative YAML)
--   - ADD COLUMN paused BOOLEAN NOT NULL DEFAULT FALSE (explicit flag,
--     replaces status='paused' enum value)
--   - Update tasks_status_check to drop 'paused' from allowed values
--   - Refresh idx_tasks_next_run to incorporate the paused gate
--
-- Pre-migration callers in services.scheduling are forward-compatible:
-- they write declaration_path + paused when present, fall back when not.
-- After this migration applies, every active row carries declaration_path
-- (set by the next materialize_scheduling_index sweep).

-- Step 1: drop dissolved columns
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_mode_check;
ALTER TABLE tasks DROP COLUMN IF EXISTS mode;
ALTER TABLE tasks DROP COLUMN IF EXISTS essential;

-- Step 2: add declaration_path — pointer to authoritative YAML
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS declaration_path TEXT;
CREATE INDEX IF NOT EXISTS idx_tasks_declaration_path ON tasks (declaration_path);

-- Step 3: explicit paused flag (was implicit via status='paused')
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS paused BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE tasks SET paused = TRUE WHERE status = 'paused';

-- Step 4: simplify status enum (paused is no longer a status; it's a flag)
UPDATE tasks SET status = 'active' WHERE status = 'paused';
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
ALTER TABLE tasks ADD CONSTRAINT tasks_status_check CHECK (
  status IN ('active', 'completed', 'archived')
);

-- Step 5: refresh next_run_at index incorporating paused gate
DROP INDEX IF EXISTS idx_tasks_next_run;
CREATE INDEX idx_tasks_next_run
  ON tasks (next_run_at)
  WHERE status = 'active' AND paused = FALSE;

-- Step 6: documentation — make the Path B intent explicit at the schema layer
COMMENT ON TABLE tasks IS
  'ADR-231 D4 Path B thin scheduling index. Authoritative recurrence-'
  'declaration substrate is workspace_files YAML at declaration_path. '
  'This table is materialized from filesystem state and is fully '
  'reconstructable via services.scheduling.materialize_scheduling_index(). '
  'The table name "tasks" identifies the SCHEDULING INDEX, not work substrate '
  '(which dissolved per ADR-231 D2). See ADR-231 §D4 for rationale on '
  'preserving this identifier.';

COMMENT ON COLUMN tasks.declaration_path IS
  'Workspace path to the authoritative YAML recurrence declaration '
  '(e.g., /workspace/reports/{slug}/_spec.yaml). The scheduler re-parses '
  'the YAML at this path on every tick — the row is the index, the YAML '
  'is truth. See services.recurrence.RecurrenceDeclaration for the '
  'substrate model.';

COMMENT ON COLUMN tasks.paused IS
  'ADR-231 explicit pause flag (replaces status=paused enum value). '
  'Mirrors RecurrenceDeclaration.paused — the scheduler skips rows '
  'where paused=true. The YAML declaration also carries `paused:` and '
  '`paused_until:`; the index value is materialized from there.';
