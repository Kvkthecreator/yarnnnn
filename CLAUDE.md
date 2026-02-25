# CLAUDE.md - Development Guidelines for YARNNN

This file provides context and guidelines for Claude Code when working on this codebase.

## Project Overview

YARNNN is a context-aware AI work platform. The core product is **Thinking Partner (TP)** - an AI assistant that understands users through synced platform context (Slack, Gmail, Notion, Calendar) and uploaded documents.

**Architecture**: Next.js frontend → FastAPI backend → Supabase (Postgres) → Claude API

## Core Execution Disciplines

### 0. Before Proposing Architectural Changes

**ALWAYS check existing ADRs first** before suggesting new patterns or comparing against external systems:

```bash
# Search for existing decisions on a topic
ls docs/adr/ | grep -i "<topic>"
# Or search ADR content
grep -r "<keyword>" docs/adr/
```

Key ADRs that define YARNNN's philosophy (not just implementation):
- **ADR-049**: Context freshness model - SUPERSEDED by ADR-072 (accumulation moat thesis)
- **ADR-059**: Simplified context model - current Memory schema (user_context), inference removal
- **ADR-062**: Platform context architecture - SUPERSEDED by ADR-072 (unified content layer)
- **ADR-063**: Four-layer model (Memory / Activity / Context / Work) - activity_log, working memory injection
- **ADR-067**: Session compaction and continuity - follows Claude Code's model
- **ADR-072**: Unified Content Layer - platform_content with retention-based accumulation, TP execution pipeline

If an external system (Claude Code, ChatGPT, etc.) does something differently, check if YARNNN has an ADR explaining why we chose a different approach.

### 1. Documentation Alongside Code

When refactoring or implementing features:
- Update relevant ADRs with implementation status
- Update `docs/database/ACCESS.md` if schema changes
- Keep inline docstrings current with behavior

### 2. Singular Implementation (No Dual Approaches)

- **Delete legacy code** when replacing with new implementation
- **No backwards-compatibility shims** unless explicitly required for migration
- **One way to do things** - avoid parallel implementations that cause confusion
- If old code is superseded, remove it entirely

### 3. Database Operations

- **SQL execution**: Refer to `docs/database/ACCESS.md` for connection strings
- **Migrations**: Run via psql with the connection string in ACCESS.md
- **Schema verification**: Always verify table/column names match current schema
- **PostgREST cache**: After schema changes, may need Supabase dashboard refresh

### 4. Code Quality Checks

Before completing work:
- **Double-check endpoints**: Verify API routes match frontend calls
- **Column name mismatches**: Ensure code uses current schema (e.g., `platform` not `provider`)
- **Import paths**: Verify all imports resolve correctly

### 5. Render Service Parity

YARNNN runs on **4 Render services** that share code and env vars. When changing environment variables, secrets, or architectural patterns, check ALL services:

| Service | Type | Render ID |
|---------|------|-----------|
| yarnnn-api | Web Service | `srv-d5sqotcr85hc73dpkqdg` |
| yarnnn-worker | Background Worker | `srv-d4sebn6mcj7s73bu8en0` |
| yarnnn-unified-scheduler | Cron Job | `crn-d604uqili9vc73ankvag` |
| yarnnn-mcp-server | Web Service | `srv-d6f4vg1drdic739nli4g` |

**Critical shared env vars** (must be on API + Worker + Scheduler):
- `INTEGRATION_ENCRYPTION_KEY` — Fernet key for OAuth token decryption. Worker/Scheduler **cannot sync** without it.
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — needed by Worker for token refresh
- `NOTION_CLIENT_ID` / `NOTION_CLIENT_SECRET` — needed by Worker for Notion API

**MCP Server env vars** (separate from above — MCP server uses service key, not user JWTs):
- `SUPABASE_SERVICE_KEY` — Service key for RLS bypass (same as Worker/Scheduler)
- `MCP_USER_ID` — User UUID for data scoping (auto-approve OAuth + static bearer fallback)
- `MCP_BEARER_TOKEN` — Static bearer token for Claude Desktop/Code
- `MCP_SERVER_URL` — OAuth issuer URL (defaults to `https://yarnnn-mcp-server.onrender.com`)

**MCP Auth model** (ADR-075): OAuth 2.1 for Claude.ai/ChatGPT (auto-approve, tokens stored in `mcp_oauth_*` tables). Static bearer token fallback for Claude Desktop/Code. See `api/mcp_server/oauth_provider.py`.

**Common mistake**: Adding an env var to the API service but forgetting Worker/Scheduler. The API handles OAuth and stores tokens; the Worker decrypts and uses them. Both need the encryption key and OAuth client credentials.

Use Render MCP tools (`update_environment_variables`) to check/set env vars across services.

**Note**: All platforms (Slack, Notion, Gmail, Calendar) use Direct API clients — no gateway service needed (ADR-076).

### 6. Git Workflow

- **Commit when appropriate**: Can commit and push when changes are complete and tested
- **Meaningful commits**: Use conventional commit style with ADR references where applicable
- **No force pushes** to main unless explicitly requested

### 7. Progress Tracking

- **Use TodoWrite tool** for multi-step tasks to track progress
- **Share progress** to keep context visible across conversation turns
- **Mark todos complete immediately** after finishing each step

---

## Prompt Change Protocol

When modifying any prompt or tool definition in these files:
- `api/agents/thinking_partner.py` (TP system prompt)
- `api/services/primitives/*.py` (tool definitions)
- `api/services/extraction.py` (extraction prompts)

You MUST:
1. Update `api/prompts/CHANGELOG.md` with the change
2. Note the expected behavior change
3. If significant, increment the version comment at the top of the prompt section

### Changelog Format

```markdown
## [YYYY.MM.DD.N] - Description

### Changed
- file.py: What changed and why
- Expected behavior: How this affects TP/tool behavior
```

---

## Key Architecture References

### ADR-064: Unified Memory Service

**Memory is implicit** — TP no longer has explicit memory tools (`create_memory`, `update_memory`, etc.)

- Memory extraction happens via nightly cron (midnight UTC) via `api/services/memory.py` — NOT at real-time session end
- User can still edit memories directly via Context page
- Working memory injected into TP prompt is unchanged

**Key files**:
- `api/services/memory.py` — extraction service
- `api/services/working_memory.py` — formats memory for prompt injection
- `docs/features/memory.md` — user-facing docs

### ADR-059: Simplified Context Model (Current Schema)

**Tables** (use these names, not legacy):
- `platform_connections` (not `user_integrations`)
- `platform_content` — unified content layer with retention (ADR-072, replaces `filesystem_items`)
- `filesystem_documents` / `filesystem_chunks` — uploaded documents only
- `user_context` — single Memory store (replaces knowledge_profile, knowledge_styles, knowledge_domains, knowledge_entries)
- `mcp_oauth_clients` / `mcp_oauth_codes` / `mcp_oauth_access_tokens` / `mcp_oauth_refresh_tokens` — MCP OAuth 2.1 storage (ADR-075, service key only)

**Removed files** (ADR-064):
- `api/services/extraction.py` — replaced by `memory.py`

**Removed tables** (ADR-059 — do not reference in new code):
- `knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries`

### ADR-057: Streamlined Onboarding

- OAuth redirects to `/dashboard?provider=X&status=connected`
- `PlatformSyncStatus` detects params and opens source selection modal
- Tier-gated source limits (free = 1 per platform)

### ADR-056: Per-Source Sync

- Sync operates per-source (channel, label, page) not per-platform
- `integration_import_jobs` tracks sync state per resource

---

## File Locations

| Concern | Location |
|---------|----------|
| TP Agent | `api/agents/thinking_partner.py` |
| Tool Primitives | `api/services/primitives/*.py` |
| Memory Service | `api/services/memory.py` |
| Working Memory | `api/services/working_memory.py` |
| Chat/Streaming | `api/services/anthropic.py` |
| OAuth Flow | `api/integrations/core/oauth.py` |
| Platform Sync | `api/integrations/{slack,gmail,notion}/` |
| Scheduler | `api/jobs/unified_scheduler.py` |
| MCP Server | `api/mcp_server/` (ADR-075) |
| Frontend API Client | `web/lib/api/client.ts` |
| Onboarding UI | `web/components/onboarding/` |

---

## Common Pitfalls

1. **Schema mismatch**: Code referencing old table/column names after ADR-058 migration
2. **Tool loop exhaustion**: TP hits `max_tool_rounds=5` without text response if tools return empty
3. **PGRST205 errors**: PostgREST schema cache needs refresh after table changes
4. **OAuth provider vs platform**: Google OAuth provides both `gmail` and `calendar` capabilities
5. **Render env var drift**: Worker/Scheduler missing env vars that API has — Worker silently fails to decrypt tokens, reports `success=True` with 0 items. Always check all services.
6. **Backend/frontend field name mismatch**: Backend returns one shape (e.g., `selected_sources`), frontend expects another (e.g., `sources`). Verify API response matches frontend consumer.

---

## Quick Commands

```bash
# Run API locally
cd api && uvicorn main:app --reload --port 8000

# Run frontend locally
cd web && pnpm dev

# Run SQL migration
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" -f supabase/migrations/XXX_name.sql

# Check recent commits
git log --oneline -20
```
