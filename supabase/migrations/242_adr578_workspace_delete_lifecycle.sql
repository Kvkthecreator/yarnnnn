-- 242_adr578_workspace_delete_lifecycle.sql
-- ADR-578 — deleting a workspace is a lifecycle, not a button.
--
-- Two changes, both preconditions for a delete that can actually run:
--
-- 1. `deleted_at` / `deleted_by` on workspaces — the soft-delete state (D1).
--    A soft-deleted workspace keeps every byte; it is hidden from the switcher
--    and refused by the reach check, so it is unreachable without being
--    destroyed. Restore is a column write. NOTHING expires on a timer
--    (ADR-478 D2: a schedule that destroys a member's work unwitnessed is the
--    one convention canon already refused).
--
-- 2. The two FINANCIAL tables stop cascading (D5). Today
--    `balance_transactions` and `subscription_events` both CASCADE from
--    workspaces, so purging a workspace would silently destroy billing
--    history the business may be required to retain. They move to SET NULL on
--    a nullable workspace_id, with the workspace identity preserved in a
--    plain `workspace_ref` column so a surviving ledger row still says which
--    workspace it belonged to.
--
--    Every OTHER cascade is left alone: content is meant to die with its
--    commons (ADR-478 D3's semantic, one scope up — unrecoverable, not
--    unremembered).
--
-- NOTE: no BEGIN/COMMIT here — the runner supplies the transaction
-- (--single-transaction). A self-committing migration defeats --dry-run: the
-- internal COMMIT fires first and the preview APPLIES FOR REAL.
--
-- Rollback: drop the two columns, drop workspace_ref, restore the two FKs to
-- ON DELETE CASCADE, re-assert NOT NULL on balance_transactions.workspace_id.

-- ── 1. Soft-delete state ────────────────────────────────────────────────────
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS deleted_by UUID;

COMMENT ON COLUMN workspaces.deleted_at IS
  'ADR-578 D1: soft-delete timestamp. Non-null = hidden from the switcher and '
  'refused by principal_reaches_workspace; all content retained. No timer '
  'expires this (ADR-478 D2) — the purge is a second, explicit act.';
COMMENT ON COLUMN workspaces.deleted_by IS
  'ADR-578 D1: the principal who soft-deleted it (auth.users id). Kept for the '
  'restore surface and the activity record; not an FK, so purging the actor''s '
  'account never resurrects or blocks a deleted workspace.';

-- Partial index: every live read filters `deleted_at IS NULL`, and the live set
-- is the overwhelming majority, so index the DELETED rows instead — that is the
-- selective side and the one the restore/purge surfaces scan.
CREATE INDEX IF NOT EXISTS idx_workspaces_deleted
  ON workspaces (deleted_at) WHERE deleted_at IS NOT NULL;

-- ── 2. Financial history outlives its workspace ─────────────────────────────
-- balance_transactions: NOT NULL today, so relax it before SET NULL can fire.
ALTER TABLE balance_transactions
  ADD COLUMN IF NOT EXISTS workspace_ref UUID;
UPDATE balance_transactions SET workspace_ref = workspace_id WHERE workspace_ref IS NULL;
ALTER TABLE balance_transactions ALTER COLUMN workspace_id DROP NOT NULL;
ALTER TABLE balance_transactions DROP CONSTRAINT IF EXISTS balance_transactions_workspace_id_fkey;
ALTER TABLE balance_transactions
  ADD CONSTRAINT balance_transactions_workspace_id_fkey
  FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL;

COMMENT ON COLUMN balance_transactions.workspace_ref IS
  'ADR-578 D5: the workspace this ledger row belonged to, preserved verbatim. '
  'workspace_id goes NULL when the workspace is purged (SET NULL); this column '
  'is NOT an FK and survives, so financial history still names its origin.';

-- subscription_events: already nullable.
ALTER TABLE subscription_events
  ADD COLUMN IF NOT EXISTS workspace_ref UUID;
UPDATE subscription_events SET workspace_ref = workspace_id WHERE workspace_ref IS NULL;
ALTER TABLE subscription_events DROP CONSTRAINT IF EXISTS subscription_events_workspace_id_fkey;
ALTER TABLE subscription_events
  ADD CONSTRAINT subscription_events_workspace_id_fkey
  FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL;

COMMENT ON COLUMN subscription_events.workspace_ref IS
  'ADR-578 D5: see balance_transactions.workspace_ref.';

-- ── 3. Verify, and REFUSE to commit if the shape is not what we claimed ─────
DO $$
DECLARE
  n_cascade INT;
  n_setnull INT;
BEGIN
  SELECT count(*) INTO n_setnull
  FROM pg_constraint
  WHERE confrelid = 'workspaces'::regclass AND contype = 'f'
    AND confdeltype = 'n'
    AND conrelid::regclass::text IN ('balance_transactions', 'subscription_events');
  IF n_setnull <> 2 THEN
    RAISE EXCEPTION
      'ADR-578 D5: expected both financial FKs to be SET NULL, found %', n_setnull;
  END IF;

  -- The financial tables must NOT still cascade, or a purge destroys the ledger.
  SELECT count(*) INTO n_cascade
  FROM pg_constraint
  WHERE confrelid = 'workspaces'::regclass AND contype = 'f'
    AND confdeltype = 'c'
    AND conrelid::regclass::text IN ('balance_transactions', 'subscription_events');
  IF n_cascade <> 0 THEN
    RAISE EXCEPTION 'ADR-578 D5: a financial FK still CASCADEs (%)', n_cascade;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'workspaces' AND column_name = 'deleted_at'
  ) THEN
    RAISE EXCEPTION 'ADR-578 D1: workspaces.deleted_at missing';
  END IF;
END $$;

