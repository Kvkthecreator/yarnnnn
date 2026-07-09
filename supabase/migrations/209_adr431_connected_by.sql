-- =============================================================================
-- ADR-431 — The connecting member owns the MCP grant
-- =============================================================================
-- The relational unit of a foreign-LLM grant was (provider, workspace) — one
-- row per provider per workspace, member-blind. At N=1 that was correct (one
-- human ⇒ "ChatGPT is connected here" unambiguously meant "my ChatGPT"). With
-- multiple members each connecting their own ChatGPT/Claude over MCP, the
-- provider-collapsed key silently folds distinct members' connections into one
-- row: `ensure_principal_grant` finds the existing active (chatgpt, workspace)
-- and no-ops the second member onto the first.
--
-- The fix: the grant records WHO connected it (`connected_by`), and the
-- active-uniqueness widens to include it — so (chatgpt, workspace, seulkim) and
-- (chatgpt, workspace, owner) are two independently-governed grants.
--
-- N=1 BYTE-IDENTICAL. The widened index coalesces connected_by to principal_id
-- for the human/agent classes (where it is definitionally redundant), so an
-- owner/member lookup is unique per (principal_id, workspace) exactly as before.
-- Backfill sets every existing non-human grant's connected_by = the workspace
-- owner — provably correct on live data (the two active foreign-llm grants on
-- workspace d5b9029b both trace to that workspace's single owner; receipt in
-- ADR-431 §1).
--
-- Depends on: 189_adr373_multi_principal_rekey.sql (principal_grants +
-- uq_principal_grant_active).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. The connecting-member column
-- -----------------------------------------------------------------------------
-- Nullable: for owner/member/own-agent the fact is redundant (a human's grant
-- is trivially their own) and the coalesce in the index treats NULL as
-- principal_id. For foreign-llm/a2a/platform it names the authorizing human.
-- No FK to auth.users (that table lives in the `auth` schema; principal_grants
-- already stores auth.users.id as TEXT in principal_id without an FK — keep the
-- same discipline so the column is uniform).
ALTER TABLE principal_grants
    ADD COLUMN IF NOT EXISTS connected_by UUID;

COMMENT ON COLUMN principal_grants.connected_by IS
    'ADR-431: the human member under whose authorization this grant exists. '
    'For a foreign-LLM/a2a/platform principal, the member whose OAuth session '
    'minted the token (the "whose ChatGPT" fact + the eviction-cascade key). '
    'NULL/redundant for owner/member/own-agent (a human''s grant is their own). '
    'The invariant that traces every non-human principal to an authorizing human.';

-- -----------------------------------------------------------------------------
-- 2. Backfill — every existing non-human grant's connected_by = the workspace owner
-- -----------------------------------------------------------------------------
-- Provably correct: on live data every active foreign-llm grant was minted by
-- the workspace's solo owner (ADR-373 D2.a receipt). Idempotent (only NULLs).
UPDATE principal_grants pg
SET connected_by = w.owner_id
FROM workspaces w
WHERE w.id = pg.workspace_id
  AND pg.role IN ('foreign-llm', 'a2a', 'platform', 'own-agent')
  AND pg.connected_by IS NULL;

-- -----------------------------------------------------------------------------
-- 3. Widen the active-uniqueness to include the connecting member
-- -----------------------------------------------------------------------------
-- Drop the (principal_id, workspace_id) partial-unique and replace it with one
-- that coalesces connected_by → principal_id. Effect:
--   • owner/member (connected_by NULL or = principal_id) → unique per
--     (principal_id, workspace), byte-identical to the old index.
--   • foreign-llm (distinct connected_by per member) → one active grant per
--     (provider, workspace, member); two members' same-provider connections
--     coexist as two rows.
DROP INDEX IF EXISTS uq_principal_grant_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_principal_grant_active
    ON principal_grants(principal_id, workspace_id, (COALESCE(connected_by::text, principal_id)))
    WHERE status = 'active';

-- A lookup index for the eviction cascade (all of a member's grants).
CREATE INDEX IF NOT EXISTS idx_principal_grants_connected_by
    ON principal_grants(connected_by, status)
    WHERE connected_by IS NOT NULL;
