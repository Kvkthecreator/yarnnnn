-- ADR-573 — the connector is bound to a workspace at consent.
--
-- ADR-373 D6 (2026-08-17) made the connector resolve the SAME workspace the
-- member's own default resolves to, closing an incorrect-success where writes
-- landed in a workspace the member was not looking at. It explicitly left the
-- SELECTION problem open: a connector still could not NAME a workspace, so a
-- principal who reaches more than one takes their default and cannot reach the
-- others at all.
--
-- That is not hypothetical. A production principal owns "My Workspace" and is
-- an active member of the shared "yarnnn workspace"; every one of their
-- connector writes landed in the owner workspace, and the commons — the
-- workspace the membership exists FOR — was unreachable from the connector.
--
-- This migration adds the binding column to the OAuth tables. The operator
-- chooses at the consent screen; the choice is stamped on the code, carried to
-- the tokens at exchange, and read per-request.
--
-- NULLABLE BY DESIGN, and that is the whole compatibility story: every token
-- issued before this migration has workspace_id IS NULL, and the runtime reads
-- NULL as "resolve the principal's default" — i.e. exactly ADR-373 D6's
-- behaviour. No backfill, no deploy-day repointing of live connectors. A
-- connector only changes where it writes when its owner re-authorizes and
-- picks. (A backfill to the currently-resolved default would look harmless and
-- would FREEZE today's resolution for connections whose default may later move
-- legitimately — so it is deliberately not done.)
--
-- No FK to workspaces(id) on the token tables on purpose: these are
-- service-scoped auth rows with their own lifecycle (revoke, rotate, expire,
-- account-delete sweeps in routes/account.py). A workspace deletion must not
-- cascade-delete auth history; the runtime re-checks reach on every request
-- anyway (a revoked member loses reach at once — principal_reaches_workspace
-- is deliberately uncached), so a dangling id fails closed rather than
-- granting anything.

ALTER TABLE mcp_oauth_codes
  ADD COLUMN IF NOT EXISTS workspace_id UUID;

ALTER TABLE mcp_oauth_access_tokens
  ADD COLUMN IF NOT EXISTS workspace_id UUID;

ALTER TABLE mcp_oauth_refresh_tokens
  ADD COLUMN IF NOT EXISTS workspace_id UUID;

COMMENT ON COLUMN mcp_oauth_codes.workspace_id IS
  'ADR-573: the workspace the operator chose at consent. NULL = pre-573 or '
  'unchosen; the runtime then resolves the principal''s default (ADR-373 D6).';

COMMENT ON COLUMN mcp_oauth_access_tokens.workspace_id IS
  'ADR-573: the workspace this connection is bound to, carried from the auth '
  'code at exchange. NULL = resolve the principal''s default (ADR-373 D6). '
  'Reach is re-checked per request, so this narrows but never grants.';

COMMENT ON COLUMN mcp_oauth_refresh_tokens.workspace_id IS
  'ADR-573: carried alongside the access token so a silent refresh rotation '
  'preserves the binding. A refresh that dropped it would migrate a bound '
  'connector back to the default without anyone acting.';
