import { getOpenApiSpec } from "@/lib/openapi";

/**
 * Curated agent-facing OpenAPI 3.1 spec, served at the predictable URL
 * agents probe: yarnnn.com/openapi.json.
 *
 * Documents yarnnn's public MCP interop verbs (remember / recall / trace).
 * See lib/openapi.ts for the rationale behind a hand-authored spec vs. proxying
 * the internal backend spec.
 */
export async function GET() {
  return new Response(JSON.stringify(getOpenApiSpec(), null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
