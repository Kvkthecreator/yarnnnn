import { BRAND } from "@/lib/metadata";

/**
 * MCP discovery card — the website→server breadcrumb.
 *
 * This is the marketing site (yarnnn.com) advertising that an MCP server
 * exists and where to reach it. It is distinct from the MCP server's own
 * OAuth `.well-known/*` metadata (served by mcp.yarnnn.com itself).
 *
 * Shape follows the emerging SEP-1649 server-card convention (proposed, not
 * yet merged into the core MCP spec as of mid-2026). It is additive — an
 * MCP-capable agent that understands it can auto-discover the connector;
 * everything else ignores it harmlessly.
 *
 * The registry-shaped listing (server.json, the 2025-12-11 schema) lives at
 * docs/features/mcp/server.json — the same URL, published by the operator.
 */

const MCP_URL = "https://mcp.yarnnn.com";

export async function GET() {
  const card = {
    name: BRAND.name,
    description: BRAND.tagline,
    server: {
      url: MCP_URL,
      transport: "streamable-http",
      authentication: {
        type: "oauth2",
        // The server publishes the full OAuth metadata at its own well-known path.
        authorization_metadata: `${MCP_URL}/.well-known/oauth-authorization-server`,
      },
    },
    // ADR-635 D9 — the card no longer enumerates tools. It advertised
    // `remember`/`recall`/`trace` for months after ADR-543 retired them
    // without aliases: a second copy of the verb list drifted the moment the
    // server's changed. The server's own `tools/list` is the source of truth;
    // a card that names the server and how to authorize is complete.
    documentation: `${BRAND.url}/how-it-works`,
  };

  return new Response(JSON.stringify(card, null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
