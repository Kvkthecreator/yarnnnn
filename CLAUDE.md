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
- **ADR-049**: Context freshness model - session history approach (partially superseded by ADR-067)
- **ADR-059**: Simplified context model - current Memory schema (user_context), inference removal
- **ADR-062**: Platform context architecture - filesystem_items role (conversational search cache only)
- **ADR-063**: Four-layer model (Memory / Activity / Context / Work) - activity_log, working memory injection
- **ADR-067**: Session compaction and continuity - follows Claude Code's model (session summaries, inactivity boundary, in-session compaction)

If an external system (Claude Code, ChatGPT, etc.) does something differently, check if YARNNN has an ADR explaining why we chose a different approach. ADR-049's "no summarization" stance is superseded by ADR-067.

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
- `filesystem_items` (not `ephemeral_context`)
- `filesystem_documents` / `filesystem_chunks`
- `user_context` — single Memory store (replaces knowledge_profile, knowledge_styles, knowledge_domains, knowledge_entries)

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
| Frontend API Client | `web/lib/api/client.ts` |
| Onboarding UI | `web/components/onboarding/` |

---

## Common Pitfalls

1. **Schema mismatch**: Code referencing old table/column names after ADR-058 migration
2. **Tool loop exhaustion**: TP hits `max_tool_rounds=5` without text response if tools return empty
3. **PGRST205 errors**: PostgREST schema cache needs refresh after table changes
4. **OAuth provider vs platform**: Google OAuth provides both `gmail` and `calendar` capabilities

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
