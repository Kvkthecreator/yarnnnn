import { BRAND } from "@/lib/metadata";

/**
 * Curated, agent-facing OpenAPI 3.1 specification for yarnnn.
 *
 * This is NOT the full internal API (the FastAPI backend auto-generates ~85
 * auth-scoped internal paths at the API host). This document describes the
 * *stable, public, agent-relevant* surface: the file-native MCP verbs that let
 * any MCP-capable assistant read and write a user's workspace, plus discovery.
 *
 * Why a hand-authored spec rather than proxying the backend:
 *   - Agents should see the surface we *support* and *document*, not the
 *     internal cockpit API which changes shape ADR by ADR.
 *   - The MCP verbs are the moat's interop face and the thing an external
 *     agent actually calls. That's what belongs in a published contract.
 *
 * ADR-543 retired the memory ontology (remember / recall / trace) with NO
 * aliases and NO shims — a host calling them gets tool-not-found. This spec
 * advertised them for months afterwards, so an agent that generated a client
 * from it failed on every call. That is the same drift ADR-635 D9 removed from
 * the discovery card; this file was the surviving copy.
 *
 * The roster below is DATA, and `test_gitbook_docs_current.py` asserts it is
 * the same set as `_INTEROP_VERBS` in api/mcp_server/server.py — the one source
 * of truth. A new verb is a row there plus its @mcp.tool, then a row here;
 * never a sentence that counts things.
 *
 * Served at yarnnn.com/openapi.json — the predictable URL agents probe.
 */

const MCP_URL = "https://mcp.yarnnn.com";

/**
 * The published interop roster: verb → what an agent gets by calling it.
 * Mirrors `_INTEROP_VERBS` (api/mcp_server/server.py), gate-enforced as a set.
 */
const INTEROP_VERBS: ReadonlyArray<{
  name: string;
  kind: "read" | "write";
  summary: string;
  description: string;
}> = [
  {
    name: "whoami",
    kind: "read",
    summary: "Name where you are standing",
    description:
      "Returns which workspace this connection is bound to, whether that is " +
      "the one the operator chose, who your writes will be signed as, and " +
      "which of these verbs your token authorizes. Call it once at the start " +
      "of real work, and always before writing somewhere the user assumed — " +
      "a person can belong to more than one workspace.",
  },
  {
    name: "open",
    kind: "read",
    summary: "Read one exact file",
    description:
      "Returns the exact current content, who last changed it, when, and its " +
      "recent attributed revisions. A binary file answers with its type, size " +
      "and a short-lived content URL instead of text. An unknown path returns " +
      "found: false — open never guesses. Read-only and idempotent.",
  },
  {
    name: "list",
    kind: "read",
    summary: "Enumerate the files under a folder",
    description:
      "Returns every file under the folder — path, an open-able reference, " +
      "size, who last changed it, and when. Accepts a `since` timestamp for " +
      "the change feed (\"what moved since I was last here\") and offset/limit " +
      "paging. Read-only and idempotent.",
  },
  {
    name: "search",
    kind: "read",
    summary: "Find files by meaning",
    description:
      "Returns ranked matches — path, an open-able reference, an excerpt, when " +
      "it was last updated, a similarity score — plus a confidence signal " +
      "(high, ambiguous, weak, none). yarnnn returns the material; the calling " +
      "model explains it. Read-only and idempotent.",
  },
  {
    name: "history",
    kind: "read",
    summary: "Show how one exact file changed over time",
    description:
      "Returns the revision chain newest-first: who authored each revision, " +
      "when, what changed, the revision id, and a diff against its " +
      "predecessor. If the file cites sources, each cited file's chain is " +
      "appended. Read-only and idempotent.",
  },
  {
    name: "save",
    kind: "write",
    summary: "Write a file back as an attributed revision",
    description:
      "An overwrite, not a patch. Pass the head revision id from open as " +
      "base_revision — the read-before-write guarantee. If someone changed the " +
      "file since, the save returns stale_write with who holds the head. Omit " +
      "base_revision only to create a new file. Every prior version stays on " +
      "the chain, so this is not destructive; it is not idempotent.",
  },
  {
    name: "edit",
    kind: "write",
    summary: "Change part of a file — an anchored edit",
    description:
      "Replaces exact current text with a replacement. Only the change " +
      "travels, so content you never read is never at risk — the right verb " +
      "for large files and concurrent work. Fails loudly if the anchor is " +
      "missing or ambiguous; never guesses.",
  },
  {
    name: "delete",
    kind: "write",
    summary: "Remove a file from the live workspace",
    description:
      "Nothing is lost: the revision chain keeps the content, history still " +
      "walks it, and the file can be restored. The reason is recorded on the " +
      "attributed tombstone.",
  },
  {
    name: "move",
    kind: "write",
    summary: "Move or rename a file",
    description:
      "Refuses to overwrite an existing destination — delete it first, by " +
      "intent. The reason is recorded on both revisions.",
  },
  {
    name: "request_upload",
    kind: "write",
    summary: "Get a short-lived URL to upload a file",
    description:
      "For content that arrives as bytes rather than text — an image, a PDF, " +
      "an export. The upload lands as an attributed file like any other.",
  },
  {
    name: "share",
    kind: "write",
    summary: "Mint a share link",
    description:
      "Shares one file, or the whole workspace when no file is named, as " +
      "member (full access) or viewer (read-only). Returns the link for the " +
      "calling model to relay. Whoever opens it sees the work and who made " +
      "it; joining the workspace requires sign-in.",
  },
];

function verbPath(verb: (typeof INTEROP_VERBS)[number]) {
  const errorRef = { $ref: "#/components/schemas/Error" };
  return {
    post: {
      operationId: verb.name,
      tags: [verb.kind === "read" ? "read" : "write"],
      summary: verb.summary,
      description:
        verb.description +
        "\n\nInvoked as an MCP tool over streamable-http. The operation below " +
        "models that tool call for agents and tooling that treat MCP tools as " +
        "callable operations; the authoritative argument schema is the one the " +
        "server returns from tools/list.",
      requestBody: {
        required: true,
        content: {
          "application/json": {
            schema: { $ref: "#/components/schemas/ToolCallArguments" },
          },
        },
      },
      responses: {
        "200": {
          description: "The tool result.",
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/ToolResult" },
            },
          },
        },
        "400": {
          description: "Invalid arguments for this verb.",
          content: { "application/json": { schema: errorRef } },
        },
        "401": {
          description: "Missing or invalid OAuth credentials.",
          content: { "application/json": { schema: errorRef } },
        },
        "403": {
          description:
            "Authenticated, but this connection's grant does not authorize " +
            "this verb in this workspace.",
          content: { "application/json": { schema: errorRef } },
        },
      },
      security: [{ oauth2: [] }],
    },
  };
}

export function getOpenApiSpec() {
  const verbPaths = Object.fromEntries(
    INTEROP_VERBS.map((verb) => [`/${verb.name}`, verbPath(verb)]),
  );

  return {
    openapi: "3.1.0",
    info: {
      title: "yarnnn API",
      version: "2.0.0",
      summary: BRAND.tagline,
      description:
        "yarnnn is a shared, attributed workspace for AI + human work. This " +
        "specification documents yarnnn's public, agent-facing surface: the " +
        "Model Context Protocol (MCP) verbs that let any MCP-capable assistant " +
        "read and write a user's workspace files, with full provenance.\n\n" +
        "The verbs are file-native — they open, list, search, save, edit and " +
        "move files, and every write lands as an attributed revision on a " +
        "walkable chain. They are exposed over an MCP server at " +
        MCP_URL +
        " (transport: streamable-http, auth: OAuth 2.1). The HTTP operations " +
        "below describe those verbs for agents and tooling that model MCP " +
        "tools as callable operations; the server's own tools/list is the " +
        "authoritative argument schema. For the machine discovery card see " +
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
        name: "read",
        description:
          "Read the workspace. Read-only and idempotent — safe to call freely.",
      },
      {
        name: "write",
        description:
          "Change the workspace. Every write carries its author and lands as a " +
          "revision on a chain you can walk.",
      },
      { name: "discovery", description: "Machine-discoverable metadata." },
    ],
    paths: {
      ...verbPaths,
      "/.well-known/mcp.json": {
        get: {
          operationId: "getMcpDiscoveryCard",
          tags: ["discovery"],
          summary: "MCP connector discovery card",
          description:
            "Machine-readable card advertising the yarnnn MCP server, its " +
            "transport and where to find its OAuth metadata. It does not " +
            "enumerate tools — the server's own tools/list is the source of " +
            "truth. Served from the marketing domain at " +
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
            "/.well-known/oauth-authorization-server. Local clients that serve " +
            "one user may present a bearer token from account settings instead.",
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
        ToolCallArguments: {
          type: "object",
          description:
            "The verb's arguments. Most verbs take a `reference` — a file " +
            "named as yarnnn://workspace/{path}, /workspace/{path}, or a " +
            "workspace-relative path. The authoritative per-verb schema is the " +
            "one the MCP server returns from tools/list; it is not duplicated " +
            "here, because a second copy drifts the moment the server's changes.",
          properties: {
            reference: {
              type: "string",
              description:
                "The file this call acts on, where the verb takes one.",
              examples: ["yarnnn://workspace/Documents/notes.md"],
            },
          },
          additionalProperties: true,
        },
        ToolResult: {
          type: "object",
          description:
            "An MCP tool result. Reads answer with the material and its " +
            "attribution; writes answer with the revision they created.",
          additionalProperties: true,
        },
        Error: {
          type: "object",
          properties: {
            error: {
              type: "object",
              properties: {
                code: { type: "string" },
                message: { type: "string" },
                hint: { type: ["string", "null"] },
              },
              required: ["code", "message"],
            },
          },
          required: ["error"],
        },
      },
    },
  };
}
