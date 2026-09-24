-- Migration 262 (ADR-666): the run — one row per run, shared with the workspace, live.
--
-- WHY. A standing run had no state of its own: what the Supervisor called a run
-- was reconstructed from cost-ledger rows in `execution_events` and a revision
-- matched to them by a time window. A browser run lasts minutes, is watched,
-- can be stopped and can wait — it needs a state. And a browser act's receipt
-- lived only on the assistant row of a PRIVATE conversation
-- (`session_messages.metadata.receipts`), so no colleague could see what an
-- agent did on a site for the workspace.
--
-- WHAT. `runs` is an ACT LEDGER, the fourth beside workspace_file_versions,
-- execution_events and action_proposals: what happened, never workspace state.
-- The service role writes it (services/runs.py is its one writer); every member
-- of the workspace reads it (ADR-666 D6 — the conversation stays private, the
-- run is shared).
--
-- REALTIME. Published under the migration-240 ceremony: RLS stays ON and
-- Realtime evaluates the SELECT policy per subscriber, so publishing widens WHEN
-- a member learns of a run, never WHO may.
--
-- THE RECEIPTS MOVE. The 9 assistant rows that carry `metadata.receipts` (the
-- browser trials of 2026-09-23) each become a run; the row keeps `run_id` and
-- loses `receipts`. After this, a receipt has one home.

CREATE TABLE IF NOT EXISTS public.runs (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  user_id       uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  topic         text,
  lane_id       uuid REFERENCES public.chat_sessions(id) ON DELETE SET NULL,
  kind          text NOT NULL CHECK (kind IN ('derive', 'browser')),
  trigger       text NOT NULL CHECK (trigger IN ('scheduled', 'manual', 'chat')),
  state         text NOT NULL DEFAULT 'queued'
                  CHECK (state IN ('queued', 'running', 'waiting', 'done', 'failed', 'stopped')),
  waiting_on    jsonb,
  outcome       text,
  steps         jsonb NOT NULL DEFAULT '[]'::jsonb,
  revision_id   uuid,
  record_path   text,
  started_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  ended_at      timestamptz
);

CREATE INDEX IF NOT EXISTS idx_runs_workspace_started
  ON public.runs (workspace_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_workspace_topic
  ON public.runs (workspace_id, topic, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_live
  ON public.runs (workspace_id) WHERE state IN ('queued', 'running', 'waiting');
-- ADR-666 D4 — a due tick never stacks a second waiting run on one declaration.
CREATE UNIQUE INDEX IF NOT EXISTS runs_one_waiting_per_topic
  ON public.runs (workspace_id, topic) WHERE state = 'waiting' AND topic IS NOT NULL;

DROP TRIGGER IF EXISTS update_runs_updated_at ON public.runs;
CREATE TRIGGER update_runs_updated_at
  BEFORE UPDATE ON public.runs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Members read workspace runs" ON public.runs;
CREATE POLICY "Members read workspace runs" ON public.runs
  FOR SELECT USING (is_workspace_member(workspace_id));

DROP POLICY IF EXISTS "Service role manages runs" ON public.runs;
CREATE POLICY "Service role manages runs" ON public.runs
  TO service_role USING (true) WITH CHECK (true);

DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.runs;
EXCEPTION
  WHEN duplicate_object THEN
    RAISE NOTICE 'runs already in supabase_realtime publication — skipping';
END $$;

-- The receipts move (ADR-666 D5): one run per assistant row that carries them.
DO $$
DECLARE
  m record;
  new_id uuid;
BEGIN
  FOR m IN
    SELECT sm.id, sm.metadata, sm.created_at, cs.id AS lane_id, cs.workspace_id, cs.user_id
    FROM public.session_messages sm
    JOIN public.chat_sessions cs ON cs.id = sm.session_id
    WHERE sm.metadata ? 'receipts' AND cs.workspace_id IS NOT NULL
  LOOP
    INSERT INTO public.runs (workspace_id, user_id, lane_id, kind, trigger, state,
                             outcome, steps, started_at, ended_at)
    VALUES (
      m.workspace_id, m.user_id, m.lane_id, 'browser', 'chat',
      CASE WHEN (m.metadata->>'stopped')::boolean THEN 'stopped' ELSE 'done' END,
      NULL,
      COALESCE((
        SELECT jsonb_agg(r || jsonb_build_object('at', m.created_at))
        FROM jsonb_array_elements(m.metadata->'receipts') r
      ), '[]'::jsonb),
      m.created_at, m.created_at
    )
    RETURNING id INTO new_id;

    UPDATE public.session_messages
       SET metadata = (metadata - 'receipts') || jsonb_build_object('run_id', new_id)
     WHERE id = m.id;
  END LOOP;
END $$;

-- Verify the LIVE objects — the runner's exit code is not verification.
DO $$
DECLARE
  in_pub boolean;
  rls_on boolean;
  left_receipts int;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE schemaname = 'public' AND tablename = 'runs' AND pubname = 'supabase_realtime'
  ) INTO in_pub;
  SELECT relrowsecurity FROM pg_class WHERE oid = 'public.runs'::regclass INTO rls_on;
  SELECT count(*) FROM public.session_messages WHERE metadata ? 'receipts' INTO left_receipts;
  IF NOT in_pub THEN RAISE EXCEPTION 'runs is not in the supabase_realtime publication'; END IF;
  IF NOT rls_on THEN RAISE EXCEPTION 'runs has RLS off — refusing to publish it'; END IF;
  IF left_receipts > 0 THEN RAISE EXCEPTION '% rows still carry metadata.receipts', left_receipts; END IF;
END $$;
