# Agent-readiness (orank scan) — remediation, 2026-07-08

[orank](https://ora.ai) scores how well a product supports AI-agent use cases across five
layers (Discovery, Identity, Access, Payments, Experience). This is the record of the
2026-07-08 remediation pass against the `yarnnn.com` scan (baseline **55/100, grade C**).

## What shipped (code)

| Gap (layer) | Fix | Where |
|---|---|---|
| **OpenAPI spec not published** (Access, −7) | Curated agent-facing OpenAPI 3.1 spec served at `yarnnn.com/openapi.json`. Documents the MCP interop verbs (`remember`/`recall`/`trace`) + the discovery card, with request/response schemas, OAuth 2.1 security scheme, and a structured `Error` schema. | `web/lib/openapi.ts`, `web/app/openapi.json/route.ts` |
| **No JSON error responses** (Access, −4) | FastAPI exception handlers normalize every error to `{ "error": { "code", "message", "hint" } }`. Covers raised `HTTPException` (4xx/5xx), request-validation failures (422, per-field hints), and otherwise-unhandled exceptions (500 — no HTML/traceback leak; Sentry still captures the real exception). | `api/main.py` |
| **JSON-LD lacks SoftwareApplication/Product** (Identity, −3) | Homepage now emits an `@graph` of `Organization` + `SoftwareApplication` (+ `Offer`) + `WebSite`, so agents can parse the product identity, not just the site. Schemas centralized for reuse. | `web/lib/metadata.ts`, `web/app/page.tsx` |
| **Developer resources not discoverable** (Discovery, −6) | New `/developers` hub — product-named title/headings, links to every developer resource (MCP connector, OpenAPI spec, discovery card, OAuth metadata, llms.txt, docs) at predictable URLs. Wired into the footer, `llms.txt` (new "Developer resources" section + Feeds), `sitemap.xml`, and it's crawlable in `robots.ts`. | `web/app/developers/page.tsx`, `web/components/landing/LandingFooter.tsx`, `web/app/llms.txt/route.ts`, `web/app/sitemap.ts` |

### Design note — why a curated OpenAPI spec, not a proxy of the backend
The FastAPI backend already auto-generates a full OpenAPI 3.1 doc (~85 auth-scoped internal
paths) at `yarnnn-api.onrender.com/openapi.json`. We do **not** re-serve that at the marketing
domain. Agents should see the surface we *support and document* — the MCP interop verbs, the
moat's public interop face — not the internal cockpit API whose shape churns ADR by ADR. The
curated spec at `web/lib/openapi.ts` is the single source of truth for the public contract.

## What remains (off-site editorial — cannot be done in the codebase)

- **Wikipedia article + Wikidata entity** (Discovery, −4). orank flags this as the
  highest-impact step for AI-search citation coverage. It requires:
  1. **Notability first** — earn independent third-party press coverage (Wikipedia rejects
     self-promotion; cited secondary sources are the gate).
  2. Draft the Wikipedia article from those cited references (not marketing copy).
  3. Create a **Wikidata** item with **P856 (official website) = `yarnnn.com`** and a
     matching external link on the Wikipedia article.

  This is a growth/PR task, not an engineering one. No code change moves this needle.

## Verify after deploy

```
# Re-scan
curl -X POST https://ora.ai/api/scan -H 'Content-Type: application/json' -d '{"url":"yarnnn.com"}'
# Or fetch cached score
curl https://ora.ai/api/score/yarnnn.com
```

Expected: Discovery, Identity, and Access all rise; Discovery's Wikipedia/Wikidata component
(−4) stays open until the off-site editorial work above lands.
