-- 221 — A member can read its co-members' grants (the multi-principal roster).
--
-- THE BUG THIS CLOSES
-- The only SELECT policy on principal_grants was `principal_id = auth.uid()` —
-- a principal sees ONLY its own grant row. Written for the N=1 world (you only
-- ever saw yourself). ADR-373 made the workspace a multi-principal commons, and
-- this policy was never re-cut. The fallout: any read of principal_grants
-- through a USER-scoped client, filtered by workspace_id, silently returns just
-- the caller's own row.
--
-- Concretely: `count_human_seats(auth.client, workspace_id)` queries this table
-- and returned 1 for the owner regardless of real headcount. The Billing pane
-- read "1 seat — just you" while the avatar menu (served by the SERVICE client,
-- which bypasses RLS) correctly read "3 people." Worse, the checkout seat
-- quantity was computed the same way — a 3-human team was billed for 1 seat.
--
-- WHY THE POLICY, NOT THE CALLERS
-- Every reader that got this right had to reach for the service client
-- explicitly; the members endpoint left a comment saying it did so "because
-- membership RLS is mid-transition." That workaround is a per-caller contract
-- ("pass a service client or I lie") that isn't in any signature — the next
-- caller inherits the trap (witness.py already sits on it). Fixing the policy
-- makes the table tell the truth to any authorized reader, so no caller needs
-- to know to route around it.
--
-- THE RECURSION GUARD
-- The naive policy — "a member may read a workspace's grants iff they are a
-- member of it" — reads principal_grants to answer a policy ON principal_grants:
-- infinite recursion. The standard fix is a SECURITY DEFINER function that reads
-- the table with RLS BYPASSED, breaking the loop. Postgres does not re-apply the
-- calling row's policy inside a SECURITY DEFINER body.

-- ── The membership predicate (recursion-safe) ──────────────────────────────
-- SECURITY DEFINER → runs as the function OWNER, bypassing RLS on the table it
-- reads, so the policy that CALLS it never re-enters itself. STABLE (one value
-- per (uid, ws) within a statement) lets the planner cache it. Scoped search_path
-- so a malicious search_path can't shadow `principal_grants`.
CREATE OR REPLACE FUNCTION public.is_workspace_member(p_workspace_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.principal_grants g
    WHERE g.workspace_id = p_workspace_id
      AND g.status = 'active'
      AND g.role IN ('owner', 'member')
      AND g.principal_id = (auth.uid())::text
  );
$$;

COMMENT ON FUNCTION public.is_workspace_member(uuid) IS
  'True if the calling user (auth.uid()) holds an active owner/member grant to '
  'the workspace. SECURITY DEFINER so an RLS policy on principal_grants can call '
  'it without recursing. Membership = a HUMAN role only (AI principals are not '
  'members). Migration 221.';

-- Only authenticated users evaluate this; keep the surface tight.
REVOKE ALL ON FUNCTION public.is_workspace_member(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_workspace_member(uuid) TO authenticated;

-- ── The co-member read policy ──────────────────────────────────────────────
-- Additive to the existing "Principals view own grants" policy (RLS policies
-- OR together): a principal keeps seeing its own row always, and now also sees
-- every grant in any workspace where it is an active owner/member. This is
-- exactly the roster the /workspace/members surface already serves via the
-- service client; the read scope is the full row (roles, scopes, connected_by),
-- matching ADR-373's shared-commons legibility.
--
-- WRITES ARE UNCHANGED. There is no member-facing INSERT/UPDATE/DELETE policy;
-- grant mutations stay service-role-only (principal_grants.py). A member gains
-- READ legibility, never the ability to grant, narrow, or revoke.
DROP POLICY IF EXISTS "Members view co-member grants" ON public.principal_grants;
CREATE POLICY "Members view co-member grants"
  ON public.principal_grants
  FOR SELECT
  TO authenticated
  USING (public.is_workspace_member(workspace_id));
