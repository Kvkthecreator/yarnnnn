-- MCP OAuth 2.1 token storage — ADR-075
-- Supports dynamic client registration, authorization codes, access/refresh tokens
-- Used by the MCP server's OAuthAuthorizationServerProvider
-- Service key access only (no RLS) — MCP server uses SUPABASE_SERVICE_KEY

CREATE TABLE IF NOT EXISTS mcp_oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret TEXT,
    redirect_uris JSONB NOT NULL DEFAULT '[]',
    client_name TEXT,
    grant_types JSONB NOT NULL DEFAULT '["authorization_code"]',
    response_types JSONB NOT NULL DEFAULT '["code"]',
    scope TEXT DEFAULT 'read',
    token_endpoint_auth_method TEXT DEFAULT 'none',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mcp_oauth_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES mcp_oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    redirect_uri TEXT NOT NULL,
    scope TEXT DEFAULT 'read',
    code_challenge TEXT,
    code_challenge_method TEXT DEFAULT 'S256',
    state TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mcp_oauth_access_tokens (
    token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES mcp_oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT ARRAY['read'],
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mcp_oauth_refresh_tokens (
    token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES mcp_oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT ARRAY['read'],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for token lookups
CREATE INDEX IF NOT EXISTS idx_mcp_oauth_codes_expires ON mcp_oauth_codes(expires_at);
CREATE INDEX IF NOT EXISTS idx_mcp_oauth_access_tokens_expires ON mcp_oauth_access_tokens(expires_at);
