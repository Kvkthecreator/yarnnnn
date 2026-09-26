-- 266 — the MCP scope is granted at consent, never defaulted (ADR-563 Amendment 1).
--
-- ADR-563 made the scope tiers real but left two defaults deciding the grant:
-- the SDK registered every client at `files:read` (a ceiling the SDK then held
-- every authorize request to, so ChatGPT could never be granted write), and a
-- missing scope anywhere fell to the column default `'read'` — the legacy
-- full-access grant, which is how every new Claude connection got delete and
-- share. The operator now picks the tier on the consent screen and the bind is
-- the one writer of the code's scope.
--
-- 1. Every registered client's ceiling is every grantable tier, so a client
--    registered under the old default can be granted any tier on reconnect.
-- 2. The `'read'` defaults are dropped: a row that names no scope is refused
--    (codes) or cannot be written at all (tokens are NOT NULL), never full access.
--
-- Tokens already issued keep exactly the scopes they carry; legacy `read` is
-- still honoured (ADR-563 D1). Nothing live is narrowed or widened.

UPDATE mcp_oauth_clients
SET scope = 'files:read files:write files:share'
WHERE scope IS DISTINCT FROM 'files:read files:write files:share';

ALTER TABLE mcp_oauth_clients        ALTER COLUMN scope  DROP DEFAULT;
ALTER TABLE mcp_oauth_codes          ALTER COLUMN scope  DROP DEFAULT;
ALTER TABLE mcp_oauth_access_tokens  ALTER COLUMN scopes DROP DEFAULT;
ALTER TABLE mcp_oauth_refresh_tokens ALTER COLUMN scopes DROP DEFAULT;
