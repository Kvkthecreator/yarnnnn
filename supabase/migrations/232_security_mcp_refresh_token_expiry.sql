-- 232_security_mcp_refresh_token_expiry.sql
-- Security audit (2026-08-03): MCP refresh tokens never expired.
--
-- FINDING: REFRESH_TOKEN_LIFETIME (30 days) was defined but dead — the
-- refresh-token inserts wrote no expiry and load_refresh_token checked none.
-- A stolen refresh token granted perpetual, silently self-renewing access
-- until manually revoked. Also: rotation deleted the old token with no reuse
-- detection, so a replayed (already-rotated) token was indistinguishable from
-- an expired one — no token-family alarm (OAuth 2.1 §4.3.1).
--
-- This migration adds the columns; the code (oauth_provider.py) writes + checks
-- them. Backfill: existing tokens get created_at + 30 days so live connectors
-- are not abruptly cut (they re-auth at the new horizon).

ALTER TABLE mcp_oauth_refresh_tokens
  ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- Backfill existing rows to created_at + 30 days (the intended lifetime).
UPDATE mcp_oauth_refresh_tokens
  SET expires_at = COALESCE(created_at, NOW()) + INTERVAL '30 days'
  WHERE expires_at IS NULL;

-- rotated_at marks a token that has been consumed by rotation. We soft-mark
-- rather than hard-delete so a REPLAY of an already-rotated token is detectable
-- (reuse detection) instead of silently indistinguishable from "unknown token".
ALTER TABLE mcp_oauth_refresh_tokens
  ADD COLUMN IF NOT EXISTS rotated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_mcp_oauth_refresh_tokens_expires
  ON mcp_oauth_refresh_tokens(expires_at);

COMMENT ON COLUMN mcp_oauth_refresh_tokens.expires_at IS
  'Refresh-token expiry (mig 232). NULL-checked as expired by load_refresh_token.';
COMMENT ON COLUMN mcp_oauth_refresh_tokens.rotated_at IS
  'Set when consumed by rotation (mig 232). A load of a rotated token is a reuse signal.';
