-- Migration 182 — ADR-310 D4 (Auth Piece 2): pending MCP auth codes
--
-- Real OAuth login binds the actual Supabase user to the auth code AFTER the
-- operator authenticates on yarnnn.com. Between MCP /authorize and the web
-- callback, the code exists in a PENDING state with no user yet.
--
-- mcp_oauth_codes.user_id was NOT NULL (single-user auto-approve stamped
-- MCP_USER_ID at /authorize time). Relax to nullable so a pending code can be
-- written before login completes. load_authorization_code rejects codes whose
-- user_id is still NULL (never exchangeable), so a pending code can never mint
-- a token.

ALTER TABLE mcp_oauth_codes ALTER COLUMN user_id DROP NOT NULL;

COMMENT ON COLUMN mcp_oauth_codes.user_id IS
  'Supabase user UUID bound to this auth code. NULL = pending (awaiting web '
  'login via /api/mcp/oauth-callback). NULL codes are never exchangeable. '
  'ADR-310 D4.';
