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
- **ADR-049**: Context freshness model - explains why NO history compression/summarization
- **ADR-034**: Domain-scoped context - why memories are scoped, not global
- **ADR-058**: Knowledge base architecture - current schema decisions

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

### 5. Git Workflow

- **Commit when appropriate**: Can commit and push when changes are complete and tested
- **Meaningful commits**: Use conventional commit style with ADR references where applicable
- **No force pushes** to main unless explicitly requested

### 6. Progress Tracking

- **Use TodoWrite tool** for multi-step tasks to track progress
- **Share progress** to keep context visible across conversation turns
- **Mark todos complete immediately** after finishing each step

---

## Prompt Change Protocol

When modifying any prompt or tool definition in these files:
- `api/agents/thinking_partner.py` (TP system prompt)
- `api/services/primitives/*.py` (tool definitions)
- `api/services/extraction.py` (extraction prompts)
- `api/services/profile_inference.py` (inference prompts)

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

### ADR-058: Knowledge Base Architecture (Current Schema)

**Tables** (use these names, not legacy):
- `platform_connections` (not `user_integrations`)
- `filesystem_items` (not `ephemeral_context`)
- `filesystem_documents` / `filesystem_chunks`
- `knowledge_domains` / `knowledge_entries`
- `knowledge_profile` / `knowledge_styles`
- `sync_registry` - per-resource sync status tracking

### Entity Enrichment Pattern (refs.py)

TP primitives resolve entity references via `api/services/primitives/refs.py`. Some entities require **enrichment** from auxiliary tables to provide complete data:

| Entity Type | Base Table | Enrichment Source | Function |
|------------|------------|-------------------|----------|
| `document` | `filesystem_documents` | `filesystem_chunks` (content) | `_enrich_document_with_content()` |
| `platform` | `platform_connections` | `sync_registry` (sync status) | `_enrich_platform_with_sync_status()` |

**Why enrichment matters**: Base tables store metadata, but related data (content, sync status) lives in auxiliary tables. Without enrichment, TP sees incomplete data (e.g., "Last sync: Never" when data exists).

**Adding new enrichments**: Follow the pattern in `resolve_ref()`:
```python
if ref.entity_type == "your_type":
    entity = await _enrich_your_type_with_data(client, auth.user_id, entity)
```

**Consistency requirement**: If a UI page (e.g., Context page) shows data by joining tables, TP primitives must use the same enrichment pattern to avoid data mismatches.

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
| Chat/Streaming | `api/services/anthropic.py` |
| OAuth Flow | `api/integrations/core/oauth.py` |
| Platform Sync | `api/integrations/{slack,gmail,notion}/` |
| Scheduler | `api/jobs/unified_scheduler.py` |
| Frontend API Client | `web/lib/api/client.ts` |
| Onboarding UI | `web/components/onboarding/` |

---

## Common Pitfalls

1. **Schema mismatch**: Code referencing old table/column names after ADR-058 migration
2. **Tool loop exhaustion**: TP hits `max_tool_rounds=5` without text response if tools return empty
3. **PGRST205 errors**: PostgREST schema cache needs refresh after table changes
4. **OAuth provider vs platform**: Google OAuth provides both `gmail` and `calendar` capabilities
5. **FastAPI route ordering**: Static routes (e.g., `/suggested`) must be defined BEFORE parameterized routes (e.g., `/{deliverable_id}`) or the static path gets matched as a parameter, causing 422 validation errors
6. **Data source mismatch**: If UI shows data from joined tables but TP queries base table only, add enrichment in `refs.py` (see Entity Enrichment Pattern above)

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
