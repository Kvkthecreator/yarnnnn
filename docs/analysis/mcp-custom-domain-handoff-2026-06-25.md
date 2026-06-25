# MCP Custom Domain — handoff steps (kill the onrender.com URL)

**Date**: 2026-06-25
**Hat**: B (operator handoff — KVK owns DNS + the Render dashboard; this is the runbook).
**Why now**: time-sensitive. The `onrender.com` URL is the OAuth **issuer**, stored in every connected claude.ai/ChatGPT connector. Renaming it AFTER real users connect breaks their connection (issuer mismatch → forced reconnect). Do this **before** external users connect — it's cheap now, churny later.

## What it is (and isn't)

- **No code change.** The URL flows entirely through the `MCP_SERVER_URL` env var (default `https://yarnnn-mcp-server.onrender.com` in `mcp_server/server.py`). There are zero hardcoded references in `api/` or `web/` (verified 2026-06-25). So this is purely: add a custom domain in Render + point DNS + update one env var.
- It changes the OAuth **issuer URL** (`AuthSettings.issuer_url` / `resource_server_url`) and the discovery documents (`/.well-known/oauth-authorization-server`) to the new domain.

## Steps (in order)

1. **Pick the domain.** Recommend `mcp.yarnnn.com` (clear, scoped to the MCP service; doesn't collide with the app at `yarnnn.com`).

2. **Add it as a custom domain on the MCP Render service** (`yarnnn-mcp-server`, `srv-d6f4vg1drdic739nli4g`):
   - Render dashboard → the MCP service → Settings → Custom Domains → Add `mcp.yarnnn.com`.
   - Render shows you the DNS target (a CNAME).

3. **Point DNS.** At your DNS provider for `yarnnn.com`, add a `CNAME` record: `mcp` → the target Render gave you. Wait for verification (Render shows "Verified" + issues the TLS cert; usually minutes).

4. **Update the env var** so the OAuth issuer matches the new domain. This must be set on the MCP service:
   - `MCP_SERVER_URL = https://mcp.yarnnn.com`
   - (Can be done via Render dashboard env vars, or the Render MCP `update_environment_variables` tool once a workspace is selected.)

5. **Redeploy the MCP service** (env-var change triggers it, or trigger manually). On boot, the discovery docs + issuer now advertise `mcp.yarnnn.com`.

6. **Verify** (anonymous, no auth needed):
   ```bash
   curl -s https://mcp.yarnnn.com/.well-known/oauth-authorization-server | head -c 300
   ```
   The `issuer` and endpoints should all read `https://mcp.yarnnn.com`.

7. **The connector URL you hand to users is `https://mcp.yarnnn.com/mcp`** — WITH the `/mcp` path. ⚠️ **This is a real gotcha (KVK hit it 2026-06-25):** the bare `https://mcp.yarnnn.com` returns 404 at root (OAuth discovery at `/.well-known/...` resolves, so the user gets "your account was authorized, but no MCP server was found at the provided URL" — auth succeeds, then the protocol endpoint 404s). The MCP protocol is served at **`/mcp`** (verified: `/mcp` → 401 auth-gated = correct; `/` → 404). Same convention as the old `yarnnn-mcp-server.onrender.com/mcp`. Put the full `/mcp` URL in every docs/onboarding/setup instruction; never the bare domain.

### Why a subdomain + `/mcp`, not `yarnnn.com/mcp` (the decision, recorded)

`yarnnn.com/mcp` looks cleaner but is the WRONG and harder path: `yarnnn.com` points to the **Next.js web app** (a different Render service), while the MCP server is a **separate service**. A domain points to one service, so `yarnnn.com/mcp` would route to the web app, not the MCP server. Making it work would need a reverse proxy splitting traffic by path — real infra, another failure point, to buy a cosmetically shorter URL. A **subdomain is the standard clean way to give a separate service its own address**: `mcp.yarnnn.com` → MCP service, `yarnnn.com` → web app, no proxy. The doubled "mcp" (`mcp.yarnnn.com/mcp`) is not redundant branding — `mcp.` = *which service*, `/mcp` = *which endpoint on it* (vs `/authorize`, `/token`, `/.well-known/…`); the old onrender URL had the same shape. The only way to drop the `/mcp` suffix is a code change to mount the MCP protocol at the service root — not worth it for a string a user pastes once.

## Parity / blast-radius check (Render Service Parity discipline)

- **Only the MCP service** uses `MCP_SERVER_URL` — it's the OAuth issuer for the connector. The API / Scheduler / Output-gateway services do NOT need it. (The API hosts `/api/mcp/oauth-callback`, but that's a path on the app domain, unaffected by the MCP issuer rename.)
- **Already-connected connectors** (your dogfooding claude.ai): their stored issuer is the old onrender URL. After the rename they may need a one-time disconnect/reconnect. Since you're pre-external-users, that's a you-only cost — exactly why now is the cheap moment.
- **No DB / schema / RLS impact.** OAuth tokens in `mcp_oauth_*` are keyed by client/user, not issuer URL; existing tokens keep working (the issuer is advertised, not stored per-token in a breaking way). If a connector revalidates issuer strictly, it reconnects — acceptable pre-launch.

## One judgment call for KVK

Whether to **keep the onrender URL working in parallel** for a grace period (set the custom domain as primary but don't remove the onrender one) vs. cut over hard. Recommend: keep both live through your launch window (Render serves the service on both the onrender subdomain and the custom domain by default), advertise only `mcp.yarnnn.com` to new users, and retire the onrender reference from docs once no connector uses it.
