-- 256 — ADR-465 D2: the cold-user door mints AT MOST ONE workspace per owner.
--
-- ## The defect
--
-- `ensure_owner_workspace` (services/supabase.py) is check-then-insert with no
-- database guard. Its own module docstring (services/workspace_genesis.py)
-- states the invariant as already true — "structurally a FIRST-workspace
-- function: it cannot mint a second and must not be taught to" — but that was
-- only ever enforced in application code, between a SELECT and an INSERT.
--
-- The frontend issues several concurrent authenticated requests on first load.
-- Every one of them passes through the cold-user door in `get_user_client`.
-- On a cold sign-up they all resolve "no workspace" before any INSERT lands,
-- and each mints. Observed on production:
--
--   mrson920924@gmail.com  9 workspaces in 148 ms  (2026-09-16 02:35:13)
--   jjaxnoodle@gmail.com   2 workspaces in  76 ms  (2026-09-16 17:48:01)
--
-- The 9-workspace case raised NO alert: every owner grant succeeded, so it was
-- silent. The 2-workspace case alerted only because an unrelated transient
-- ([Errno 11] on the shared HTTP/2 service client) made one grant write fail,
-- leaving a workspace reachable by nobody — the exact state the ⭐⭐⭐ comment
-- in `ensure_owner_workspace` warns about. The louder failure was the
-- smaller bug.
--
-- ## Why a marker column and not a predicate on `name`
--
-- The obvious guard — unique on (owner_id) WHERE name = 'My Workspace' — is
-- wrong twice over: a rename escapes it, and an operator may legitimately name
-- a deliberate workspace "My Workspace". `free_balance_granted` does not
-- discriminate either; BOTH mint paths end at true (the cold door via the
-- migration-144 default, deliberate genesis by explicit stamp).
--
-- So the discriminator is recorded explicitly and is IMMUTABLE: which act gave
-- birth to the row. That is a constitutional fact about the workspace, not a
-- mutable preference, and it is exactly what the two mint paths disagree about.
--
-- ADR-465 D2's deliberate genesis (`create_workspace`) stays NON-idempotent and
-- unconstrained: "asking twice means wanting two". Only the implicit door is
-- capped, which is the behaviour its own docstring already claims.


-- ── The marker ───────────────────────────────────────────────────────────────
-- 'auto'       — minted by the cold-user door (implicit, idempotent, carries
--                the ADR-172 signup grant).
-- 'deliberate' — minted by `create_workspace` (explicit, named, zero balance).
ALTER TABLE public.workspaces
  ADD COLUMN IF NOT EXISTS genesis_kind text NOT NULL DEFAULT 'auto';

ALTER TABLE public.workspaces
  DROP CONSTRAINT IF EXISTS workspaces_genesis_kind_check;
ALTER TABLE public.workspaces
  ADD CONSTRAINT workspaces_genesis_kind_check
  CHECK (genesis_kind IN ('auto', 'deliberate'));

COMMENT ON COLUMN public.workspaces.genesis_kind IS
  'Which act minted this row: auto (cold-user door, at most one per owner) or '
  'deliberate (create_workspace, unbounded). ADR-465 D2. Immutable after birth.';

-- ── Backfill ─────────────────────────────────────────────────────────────────
-- A NAMED workspace can only have come from deliberate genesis: the cold door
-- inserts the literal DEFAULT_WORKSPACE_NAME and nothing else. Rows still
-- carrying that name are auto-minted (the default already covers them).
UPDATE public.workspaces
   SET genesis_kind = 'deliberate'
 WHERE name IS DISTINCT FROM 'My Workspace';



-- ── Deduplicate the races already on disk ────────────────────────────────────
-- Keep the OLDEST auto-minted workspace per owner. That is not an arbitrary
-- pick: `resolve_owner_workspace_id` orders `created_at ASC`, so the oldest row
-- is the one every session already resolves and the only one any member has
-- actually been browsing. Deleting it would move people's home.
--
-- Verified read-only on production before writing this (2026-09-17), for the
-- 9 doomed rows across the two affected accounts:
--   authored files .... 0   (all 17 paths per workspace are mirrored kernel
--                            artifacts under /workspace/system/ — skills and
--                            agent faces, replaced by the mirror on next run)
--   lanes ............. 0
--   ledger rows ....... 0   (the $3 signup grant rides the balance_usd column
--                            default and was never written to
--                            balance_transactions, so the duplicated
--                            balance was never accounted money)
-- Nothing authored is destroyed. Re-verify these counts before applying.
CREATE TEMP TABLE _doomed ON COMMIT DROP AS
  SELECT w.id
    FROM public.workspaces w
   WHERE w.deleted_at IS NULL
     AND w.genesis_kind = 'auto'
     AND w.id <> (
       SELECT w2.id FROM public.workspaces w2
        WHERE w2.owner_id = w.owner_id
          AND w2.deleted_at IS NULL
          AND w2.genesis_kind = 'auto'
        ORDER BY w2.created_at ASC, w2.id ASC
        LIMIT 1
     );

-- The child rows go with it: workspace_files, workspace_file_versions,
-- principal_grants, member_state, conversation_members, workspace_blobs,
-- workspace_shares, workspace_invites and workspace_upload_tickets all carry
-- ON DELETE CASCADE. Seven FKs do NOT (they have no referential action, so they
-- RESTRICT): chat_sessions, execution_events, tasks, activity_log,
-- action_proposals, platform_connections, sync_registry. Those are asserted
-- empty here rather than assumed — if a duplicate ever accumulated real work,
-- this migration ABORTS instead of destroying or orphaning it.
DO $$
DECLARE blockers int;
BEGIN
  SELECT (SELECT count(*) FROM public.chat_sessions        WHERE workspace_id IN (SELECT id FROM _doomed))
       + (SELECT count(*) FROM public.execution_events     WHERE workspace_id IN (SELECT id FROM _doomed))
       + (SELECT count(*) FROM public.tasks                WHERE workspace_id IN (SELECT id FROM _doomed))
       + (SELECT count(*) FROM public.activity_log         WHERE workspace_id IN (SELECT id FROM _doomed))
       + (SELECT count(*) FROM public.action_proposals     WHERE workspace_id IN (SELECT id FROM _doomed))
       + (SELECT count(*) FROM public.platform_connections WHERE workspace_id IN (SELECT id FROM _doomed))
       + (SELECT count(*) FROM public.sync_registry        WHERE workspace_id IN (SELECT id FROM _doomed))
    INTO blockers;
  IF blockers > 0 THEN
    RAISE EXCEPTION
      'refusing to delete: % live child row(s) reference a duplicate workspace', blockers;
  END IF;
END $$;

DELETE FROM public.workspaces
 WHERE id IN (SELECT id FROM _doomed);

-- ── The guard ────────────────────────────────────────────────────────────────
-- Now the invariant `ensure_owner_workspace` has always ASSERTED is enforced
-- where a concurrent INSERT cannot slip past it. The second racer gets a
-- unique violation; the app's existing re-check reads the winner's row and
-- returns it, which is the idempotent behaviour the door already promises.
--
-- Scoped to genesis_kind='auto' so deliberate genesis stays unbounded, and to
-- live rows so a deleted workspace never blocks a re-mint (services/
-- workspace_delete.py routes a deleted owner back through the cold door).
CREATE UNIQUE INDEX IF NOT EXISTS workspaces_one_auto_per_owner
  ON public.workspaces (owner_id)
  WHERE deleted_at IS NULL AND genesis_kind = 'auto';

