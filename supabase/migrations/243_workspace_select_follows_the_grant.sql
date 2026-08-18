-- 243_workspace_select_follows_the_grant.sql
-- The `workspaces` SELECT policy predates the multi-principal re-key.
--
-- THE DEFECT (falsified on production 2026-08-18, as the real member
-- 2be30ac5… in a ROLLBACK txn):
--
--     member_sees_own_ws     | 1
--     member_sees_GRANTED_ws | 0     ← holds an ACTIVE grant into it
--
-- The policy is `owner_id = auth.uid()` — written in migration 001, when a
-- workspace had exactly one principal. ADR-373 made the workspace a
-- multi-principal commons and re-keyed the substrate, but this policy never
-- learned about grants. 12 principals currently hold a grant into a workspace
-- they do not own; every one of them reads ZERO rows from `workspaces`
-- through their own client.
--
-- Why it stayed invisible: the surfaces that MATTER most (the switcher,
-- `/workspace/memberships`) read through the SERVICE client, which bypasses
-- RLS — so the product looked correct. The member-client readers degrade
-- SILENTLY instead: `routes/subscription.py::get_subscription_status` returns
-- `tier="free"` on zero rows, and the checkout/portal paths 404. The
-- authority check that guards them (`has_billing_authority`) runs on the
-- service client and says YES — so a member with billing authority is told
-- they may manage billing, and then reads a workspace that appears not to
-- exist. An INCORRECT SUCCESS, not an error: exactly the failure Sentry
-- cannot see.
--
-- SCOPE — only SELECT changes. Deliberately NOT the other three:
--   UPDATE  stays owner-only. `routes/workspace.py::update_workspace_identity`
--           writes through the CALLER's client precisely so this policy is the
--           enforcement for rename/re-glyph. Widening it would let any granted
--           member rename the commons.
--   DELETE  stays owner-only. The ADR-578 lifecycle runs service-side behind
--           `has_workspace_clear_authority`.
--   INSERT  unchanged and unused (genesis mints via the service client).
--
-- Reach here means the SAME thing the app means by it
-- (`services/supabase.py::principal_reaches_workspace`): owner OR an active
-- grant. The policy therefore NARROWS nothing and GRANTS nothing new — it
-- stops hiding rows the caller was already authorized to read.
--
-- NOTE: no BEGIN/COMMIT here — the runner supplies the transaction
-- (--single-transaction). A self-committing migration defeats --dry-run: the
-- internal COMMIT fires first and the preview APPLIES FOR REAL.
--
-- Rollback: restore `USING (owner_id = auth.uid())` on the SELECT policy and
-- drop `principal_reaches_workspace_rls`.

-- A dedicated reach predicate. Deliberately NOT a widening of the existing
-- `is_workspace_member()` (migration 221): that one is role-restricted to
-- owner|member and is the predicate for CO-MEMBER GRANT visibility. Mutating
-- it would silently change who can enumerate whose grants — a different
-- question with a different answer. It also omits `viewer`, and ADR-517 D6
-- ruled a viewer must be able to ENTER the workspace they can view (the
-- switcher lists them), so a viewer must be able to read its row.
--
-- SECURITY DEFINER + a `principal_grants` read is what avoids RLS recursion:
-- evaluating this inside a `workspaces` policy must not re-enter a policy that
-- itself consults `workspaces`.
CREATE OR REPLACE FUNCTION public.principal_reaches_workspace_rls(p_workspace_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path TO 'public'
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.workspaces w
    WHERE w.id = p_workspace_id AND w.owner_id = auth.uid()
  ) OR EXISTS (
    SELECT 1 FROM public.principal_grants g
    WHERE g.workspace_id = p_workspace_id
      AND g.status = 'active'
      AND g.principal_id = (auth.uid())::text
  );
$$;

COMMENT ON FUNCTION public.principal_reaches_workspace_rls(uuid) IS
  'Migration 243: owner OR active grant — the RLS mirror of '
  'services/supabase.py::principal_reaches_workspace. Used ONLY by the '
  'workspaces SELECT policy. Distinct from is_workspace_member() (mig 221), '
  'which is role-restricted to owner|member and answers grant VISIBILITY.';

REVOKE ALL ON FUNCTION public.principal_reaches_workspace_rls(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.principal_reaches_workspace_rls(uuid) TO authenticated;

DROP POLICY IF EXISTS "Users can view own workspaces" ON public.workspaces;
CREATE POLICY "Principals view workspaces they reach"
  ON public.workspaces FOR SELECT
  USING (public.principal_reaches_workspace_rls(id));

-- ── Verify, and REFUSE to commit if the shape is wrong ──────────────────────
DO $$
DECLARE
  n_select INT;
  upd_qual TEXT;
BEGIN
  SELECT count(*) INTO n_select FROM pg_policies
   WHERE tablename = 'workspaces' AND cmd = 'SELECT';
  IF n_select <> 1 THEN
    RAISE EXCEPTION 'mig243: expected exactly 1 SELECT policy, found %', n_select;
  END IF;

  -- UPDATE must STILL be owner-only, or the identity PATCH loses its gate.
  SELECT qual INTO upd_qual FROM pg_policies
   WHERE tablename = 'workspaces' AND cmd = 'UPDATE' LIMIT 1;
  IF upd_qual IS NULL OR upd_qual NOT LIKE '%owner_id%' THEN
    RAISE EXCEPTION
      'mig243: the UPDATE policy must remain owner-only (found: %)', upd_qual;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'principal_reaches_workspace_rls'
  ) THEN
    RAISE EXCEPTION 'mig243: reach predicate missing';
  END IF;
END $$;

