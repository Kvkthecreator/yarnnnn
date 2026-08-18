-- Migration 240 (ADR-575): add workspace_file_versions to supabase_realtime.
--
-- WHY. Text's conflict banner exists because the surface learns about another
-- principal's write only by COLLIDING with it at save time. Notion's members
-- never see that screen: rendering a record SUBSCRIBES the client to it, and
-- the server pushes a version number on every commit (MessageStore), which the
-- client answers with a targeted refetch. We already run that exact pattern —
-- `web/lib/realtime/use-session-messages-realtime.ts`, added by migration 170
-- for session_messages, and written explicitly as a reusable primitive.
--
-- It was never extended to the substrate. Verified against production before
-- writing this migration:
--
--   SELECT tablename FROM pg_publication_tables WHERE pubname='supabase_realtime';
--     chat_sessions
--     session_messages
--
-- So a subscription on file revisions would have delivered NOTHING, silently —
-- the failure mode that reads as "realtime is wired and quiet" rather than as
-- an error. The publication is the enabling half; the hook is useless without
-- it.
--
-- The measured symptom (production, /workspace/seulki/babo-song-concept.md):
-- FOUR revisions — three `operator`, one `yarnnn:mcp:claude.ai` — while the
-- surface's Properties pane read "No revisions yet." and a 409 banner was up.
-- The connector's write was invisible until it collided.
--
-- RLS. Preserved as-is and NOT relaxed. The existing SELECT policy is
-- workspace-scoped:
--
--   "Members view workspace file versions" (SELECT):
--     workspace_id IN (
--       SELECT id FROM workspaces WHERE owner_id = auth.uid()
--       UNION
--       SELECT workspace_id FROM principal_grants
--        WHERE principal_id = auth.uid()::text AND status = 'active'
--     )
--
-- Realtime evaluates that policy per subscriber, so the channel can only emit
-- revision rows the member could already have read through the API. Publishing
-- a table does NOT widen who may see its rows; it widens WHEN they find out.
-- This is the same reasoning migration 170 recorded for session_messages.
--
-- Note the row payload carries `path`, `authored_by`, `created_at` and
-- `workspace_id` — no file CONTENT. The push is an invalidation signal (the
-- Notion shape: send a version, refetch what went stale), never a content
-- channel, so no substrate bytes cross a realtime socket.
--
-- Idempotency: ALTER PUBLICATION ... ADD TABLE raises on an already-published
-- table, so the DO block swallows duplicate_object and the migration is safe
-- to re-run (migration 170's shape).

DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.workspace_file_versions;
EXCEPTION
  WHEN duplicate_object THEN
    RAISE NOTICE 'workspace_file_versions already in supabase_realtime publication — skipping';
END $$;

-- Verify the LIVE object. The runner's exit code is not verification: an
-- ALTER that silently no-ops would still exit 0, so read the catalog back and
-- fail loudly if the table is not actually published.
DO $$
DECLARE
  in_pub boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE schemaname = 'public'
      AND tablename = 'workspace_file_versions'
      AND pubname = 'supabase_realtime'
  ) INTO in_pub;
  IF NOT in_pub THEN
    RAISE EXCEPTION 'Migration 240 failed: workspace_file_versions not in supabase_realtime publication after ALTER';
  END IF;
END $$;

-- Verify RLS is still ON. Publishing a table to a replication slot is exactly
-- the moment a disabled RLS flag would stop being a latent bug and start
-- broadcasting every workspace's revision feed to every subscriber.
DO $$
DECLARE
  rls_on boolean;
BEGIN
  SELECT relrowsecurity INTO rls_on
    FROM pg_class WHERE relname = 'workspace_file_versions';
  IF NOT rls_on THEN
    RAISE EXCEPTION 'Migration 240 refused: RLS is DISABLED on workspace_file_versions — publishing it would broadcast rows across workspaces';
  END IF;
END $$;
