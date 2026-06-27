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
    tools: [
      {
        name: "remember",
        description:
          "Save something worth keeping — a decision, fact, or preference. Durable, attributed, and available on the next recall.",
      },
      {
        name: "recall",
        description:
          "Pull what the user already knows about a subject. Returns the stored material; the host AI explains it.",
      },
      {
        name: "trace",
        description:
          "Show how a recorded fact changed over time — who changed it, when, and what changed.",
      },
    ],
    documentation: `${BRAND.url}/how-it-works`,
  };

  return new Response(JSON.stringify(card, null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
