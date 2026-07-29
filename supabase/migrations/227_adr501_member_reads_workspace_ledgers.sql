-- 227 — A member reads the workspace's LEDGERS, not just its files (ADR-501).
--
-- THE BUG THIS CLOSES (Hat-B probe, 2026-07-29, live against prod)
-- ADR-501 rescoped the read path in the APPLICATION layer: /api/system/
-- execution-events, /api/radar/hubs, the workspace nav's recurrences and the
-- scheduler heartbeat all moved from `.eq("user_id", …)` to the workspace
-- spine (`substrate_scope_filter` / the acting-workspace owner). Correct — and
-- still dark for a member, because RLS strips the rows underneath the filter.
--
--   workspace_files   → grant-aware SELECT policy (migration 189)  ← WORKS
--   execution_events  → `auth.uid() = user_id`                     ← member sees ~nothing
--   activity_log      → `auth.uid() = user_id`                     ← heartbeat invisible
--   tasks             → `user_id = auth.uid()`                     ← radar hubs + recurrences empty
--
-- Probe receipt: bound to the shared workspace, the owner read 5 execution
-- events and 1 radar hub; the member read 1 and 0. Every application check
-- passed. This is the same shape as migration 221 (a member could not read its
-- co-members' grants) one table-family over: policies written for the N=1
-- world that ADR-373 made multi-principal and never re-cut.
--
-- WHY THE POLICY, NOT THE CALLERS
-- The alternative is routing each reader through the service client, which is
-- a per-caller contract that isn't in any signature — 221 already argued this
-- and fixed the policy instead. Same call here: make the table tell the truth
-- to any authorized reader.
--
-- ADDITIVE, NEVER WIDENING BEYOND THE GRANT
-- Each policy below is a SECOND SELECT policy (Postgres ORs them), so the
-- existing own-rows policy is untouched and the N=1 world is byte-identical.
-- Reach is bounded by `is_workspace_member(workspace_id)` — the same
-- recursion-safe SECURITY DEFINER predicate migration 221 introduced, which
-- resolves owner-OR-active-grant. A revoked member loses reach on their next
-- statement, exactly like workspace_files.
--
-- READ ONLY. No INSERT/UPDATE/DELETE policy is added: writes to these ledgers
-- are the system's (service client), and a member's write authority is the
-- ADR-501 grant gate's business, not RLS's.

-- ── execution_events — the invocation ledger (/activity, radar sweep health) ──
DROP POLICY IF EXISTS "Members read workspace execution events" ON public.execution_events;
CREATE POLICY "Members read workspace execution events"
  ON public.execution_events
  FOR SELECT
  USING (
    workspace_id IS NOT NULL
    AND public.is_workspace_member(workspace_id)
  );

-- ── activity_log — scheduler heartbeat + system-status legibility ─────────────
DROP POLICY IF EXISTS "Members read workspace activity" ON public.activity_log;
CREATE POLICY "Members read workspace activity"
  ON public.activity_log
  FOR SELECT
  USING (
    workspace_id IS NOT NULL
    AND public.is_workspace_member(workspace_id)
  );

-- ── tasks — the thin scheduling index (radar hubs, nav recurrences) ───────────
-- NOTE the existing policy here is FOR ALL, not FOR SELECT. A second policy is
-- still additive for SELECT (permissive policies OR within a command), and this
-- one is SELECT-only, so a member gains read reach and no write reach.
DROP POLICY IF EXISTS "Members read workspace tasks" ON public.tasks;
CREATE POLICY "Members read workspace tasks"
  ON public.tasks
  FOR SELECT
  USING (
    workspace_id IS NOT NULL
    AND public.is_workspace_member(workspace_id)
  );
