import { BRAND } from "@/lib/metadata";

/**
 * Curated, agent-facing OpenAPI 3.1 specification for yarnnn.
 *
 * This is NOT the full internal API (the FastAPI backend auto-generates ~85
 * auth-scoped internal paths at the API host). This document describes the
 * *stable, public, agent-relevant* surface: the MCP interop verbs
 * (remember / recall / trace) that let any MCP-capable assistant read and write
 * a user's durable yarnnn memory, plus discovery + health endpoints.
 *
 * Why a hand-authored spec rather than proxying the backend:
 *   - Agents should see the surface we *support* and *document*, not the
 *     internal cockpit API which changes shape ADR by ADR.
 *   - The MCP verbs are the moat's interop face and the thing an external
 *     agent actually calls. That's what belongs in a published contract.
 *
 * Served at yarnnn.com/openapi.json — the predictable URL agents probe.
 */

const MCP_URL = "https://mcp.yarnnn.com";

export function getOpenApiSpec() {
  return {
    openapi: "3.1.0",
    info: {
      title: "yarnnn API",
      version: "1.0.0",
      summary: BRAND.tagline,
      description:
        "yarnnn is a durable, attributed memory layer for AI + human work. " +
        "This specification documents yarnnn's public, agent-facing surface: the " +
        "Model Context Protocol (MCP) interop verbs that let any MCP-capable " +
        "assistant read and write a user's shared memory, with full provenance.\n\n" +
        "The three verbs — remember, recall, trace — are exposed over an MCP " +
        "server at " +
        MCP_URL +
        " (transport: streamable-http, auth: OAuth 2.1). The HTTP operations " +
        "below describe those verbs' request/response shapes for agents and " +
        "tooling that model MCP tools as callable operations. For the machine " +
        "discovery card see " +
        BRAND.url +
        "/.well-known/mcp.json; for human docs see " +
        BRAND.url +
        "/developers.",
      contact: {
        name: "yarnnn",
        url: `${BRAND.url}/developers`,
        email: "admin@yarnnn.com",
      },
      termsOfService: `${BRAND.url}/terms`,
      license: {
        name: "Proprietary",
        url: `${BRAND.url}/terms`,
      },
    },
    servers: [
      {
        url: MCP_URL,
        description:
          "yarnnn MCP server — the interop face. MCP-capable assistants connect " +
          "here over streamable-http with OAuth 2.1.",
      },
    ],
    externalDocs: {
      description: "yarnnn developer resources — API, MCP, auth, discovery",
      url: `${BRAND.url}/developers`,
    },
    tags: [
      {
        name: "memory",
        description:
          "Durable, attributed memory verbs. Every write carries its author; " +
          "every fact carries provenance you can trace.",
      },
      { name: "discovery", description: "Machine-discoverable metadata." },
    ],
    paths: {
      "/remember": {
        post: {
          operationId: "remember",
          tags: ["memory"],
          summary: "Save something worth keeping into durable memory",
          description:
            "Save a decision, insight, fact, or preference into the user's " +
            "durable yarnnn memory. The write is synchronous and durable — the " +
            "moment it returns the memory is stored, attributed, and immediately " +
            "retrievable by a subsequent recall or trace on the same subject.",
          requestBody: {
            required: true,
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/RememberRequest" },
              },
            },
          },
          responses: {
            "200": {
              description: "Memory stored and immediately retrievable.",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/RememberResult" },
                },
              },
            },
            "400": {
              description: "Invalid request (e.g. empty content).",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/Error" },
                },
              },
            },
            "401": {
              description: "Missing or invalid OAuth credentials.",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/Error" },
                },
              },
            },
          },
          security: [{ oauth2: [] }],
        },
      },
      "/recall": {
        post: {
          operationId: "recall",
          tags: ["memory"],
          summary: "Pull what the user already knows about a subject",
          description:
            "Retrieve the user's accumulated memory about a subject (a person, " +
            "company, market, project, or topic). Returns the stored material " +
            "plus a confidence signal; the host assistant explains it in its own " +
            "voice. On ambiguous confidence (several matches, none dominant), ask " +
            "which subject is meant rather than guessing.",
          requestBody: {
            required: true,
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/RecallRequest" },
              },
            },
          },
          responses: {
            "200": {
              description: "Recalled material with a confidence signal.",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/RecallResult" },
                },
              },
            },
            "401": {
              description: "Missing or invalid OAuth credentials.",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/Error" },
                },
              },
            },
          },
          security: [{ oauth2: [] }],
        },
      },
      "/trace": {
        post: {
          operationId: "trace",
          tags: ["memory"],
          summary: "Show how a recorded fact changed over time",
          description:
            "Return the authored revision chain for a subject — who changed it, " +
            "when, and what the change was. This is yarnnn's distinguishing " +
            "capability: a plain storage connector cannot show provenance over " +
            "time.",
          requestBody: {
            required: true,
            content: {
              "application/json": {
                schema: { $ref: "#/components/schemas/TraceRequest" },
              },
            },
          },
          responses: {
            "200": {
              description: "The attributed revision chain for the subject.",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/TraceResult" },
                },
              },
            },
            "401": {
              description: "Missing or invalid OAuth credentials.",
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/Error" },
                },
              },
            },
          },
          security: [{ oauth2: [] }],
        },
      },
      "/.well-known/mcp.json": {
        get: {
          operationId: "getMcpDiscoveryCard",
          tags: ["discovery"],
          summary: "MCP connector discovery card",
          description:
            "Machine-readable card advertising the yarnnn MCP server, its " +
            "transport, OAuth metadata location, and tool list. Served from the " +
            "marketing domain at " +
            BRAND.url +
            "/.well-known/mcp.json.",
          security: [],
          responses: {
            "200": {
              description: "The MCP discovery card.",
              content: { "application/json": { schema: { type: "object" } } },
            },
          },
        },
      },
    },
    components: {
      securitySchemes: {
        oauth2: {
          type: "oauth2",
          description:
            "OAuth 2.1. The MCP server publishes full authorization-server " +
            "metadata at " +
            MCP_URL +
            "/.well-known/oauth-authorization-server.",
          flows: {
            authorizationCode: {
              authorizationUrl: `${MCP_URL}/authorize`,
              tokenUrl: `${MCP_URL}/token`,
              scopes: {},
            },
          },
        },
      },
      schemas: {
        RememberRequest: {
          type: "object",
          required: ["content"],
          properties: {
            content: {
              type: "string",
              description:
                "The thing to remember — the user's words or a faithful summary. Required.",
            },
            about: {
              type: "string",
              description:
                "Optional subject hint (a company, person, project, or topic).",
            },
          },
        },
        RememberResult: {
          type: "object",
          properties: {
            success: { type: "boolean" },
            status: {
              type: "string",
              description: 'e.g. "remembered" once stored and retrievable.',
              examples: ["remembered"],
            },
            subject: {
              type: "string",
              description: "The subject the memory was filed under.",
            },
          },
        },
        RecallRequest: {
          type: "object",
          required: ["subject"],
          properties: {
            subject: {
              type: "string",
              description:
                "What to recall about — a person, company, market, project, or topic. Required.",
            },
            question: {
              type: "string",
              description: "Optional specific question to focus the recall.",
            },
            domain: {
              type: "string",
              description: "Optional domain to scope the recall.",
            },
            limit: {
              type: "integer",
              default: 10,
              description: "Maximum number of items to return.",
            },
          },
        },
        RecallResult: {
          type: "object",
          properties: {
            success: { type: "boolean" },
            confidence: {
              type: "string",
              description:
                "Retrieval confidence. On 'ambiguous', ask the user which subject is meant.",
              enum: ["high", "medium", "low", "ambiguous", "none"],
            },
            items: {
              type: "array",
              description: "The recalled memory material.",
              items: { type: "object" },
            },
          },
        },
        TraceRequest: {
          type: "object",
          required: ["subject"],
          properties: {
            subject: {
              type: "string",
              description: "The subject whose history to trace. Required.",
            },
            limit: {
              type: "integer",
              default: 10,
              description: "Maximum number of revisions to return.",
            },
          },
        },
        TraceResult: {
          type: "object",
          properties: {
            success: { type: "boolean" },
            subject: { type: "string" },
            revisions: {
              type: "array",
              description:
                "The authored revision chain — each entry names who changed the fact, when, and what changed.",
              items: {
                type: "object",
                properties: {
                  author: { type: "string" },
                  changed_at: { type: "string", format: "date-time" },
                  change: { type: "string" },
                },
              },
            },
          },
        },
        Error: {
          type: "object",
          description:
            "Structured JSON error. Agents parse `error.code` and may surface `error.hint`.",
          required: ["error"],
          properties: {
            error: {
              type: "object",
              required: ["code", "message"],
              properties: {
                code: {
                  type: "string",
                  description: "Machine-readable error code.",
                  examples: ["empty_content", "unauthorized", "not_found"],
                },
                message: {
                  type: "string",
                  description: "Human-readable explanation.",
                },
                hint: {
                  type: "string",
                  description: "Optional resolution hint for the agent.",
                },
              },
            },
          },
        },
      },
    },
  };
}
