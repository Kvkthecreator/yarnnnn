-- Migration 105: Allow users to write their own workspace_files
--
-- workspace_files previously only had SELECT for users and ALL for service role.
-- User-initiated writes (profile, preferences, notes via /api/memory) need
-- INSERT/UPDATE/DELETE with user JWT.

CREATE POLICY "Users can insert own workspace files"
  ON workspace_files FOR INSERT
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own workspace files"
  ON workspace_files FOR UPDATE
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own workspace files"
  ON workspace_files FOR DELETE
  USING (user_id = auth.uid());
