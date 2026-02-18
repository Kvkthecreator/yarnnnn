# ADR-059: Simplified Context Model

**Status**: Accepted
**Date**: 2026-02-17
**Implemented**: 2026-02-18
**Replaces**: Portions of ADR-058 (knowledge inference layer), ADR-034 (domain inference)

---

## Problem

ADR-058 introduced a four-layer pipeline: `filesystem_items` → inference engine → `knowledge_*` tables → working memory → TP prompt. In practice:

- Notion sync uses the wrong MCP path and likely fails silently
- Style learning only runs during Slack import with a special flag
- Domain inference requires deliverables to exist before it produces anything
- Profile inference depends on Claude Haiku running correctly after every sync
- `knowledge_entries` has four different writers with unclear ownership
- The working memory builder assembles from tables that may be empty or stale

The result: TP is often operating with less context than the user thinks it has, and diagnosing why is hard because failures are silent.

**The layers add complexity without proportional value.** The Claude Code analogy (ADR-038) is instructive: Claude Code doesn't infer your personality from your commits. It reads CLAUDE.md (user-stated) and the files themselves. That's it.

---

## Assessment of what's actually needed

### What TP needs to do its job well

1. **Who is this person** — name, role, company, timezone
2. **How do they write** — tone and verbosity per platform (stated, not inferred)
3. **What context from their platforms** — recent Slack messages, emails, Notion pages, calendar events
4. **What deliverables are active** — so TP knows what they're working on
5. **What platforms are connected** — with sync freshness

That's it. Items 3–5 already exist directly as `filesystem_items`, `deliverables`, and `platform_connections`. Items 1–2 are the only thing that needs a dedicated stated-preference store.

### What the current inference layer adds (vs costs)

| What | Value | Cost |
|------|-------|------|
| Profile inference (Haiku post-sync) | Low — user knows their own name/role | API call per sync, can be stale, silent failure |
| Style inference (Sonnet from Slack messages) | Medium — genuinely useful if working | Gated flag, barely triggered, complex |
| Domain inference (graph algorithm from deliverables) | Low — domains are mostly obvious | Requires deliverables to exist, adds schema complexity |
| knowledge_entries (4 writers) | Medium — facts/preferences are useful | Unclear ownership, drift, no good trigger |

The inference layer's core problem: it requires everything upstream to be working correctly to deliver value. When Notion sync is broken, Notion styles are never inferred. When no deliverables exist, domains are empty. Failures are invisible.

---

## Decision: Collapse to two stores

Replace the inference pipeline with two flat stores:

### Store 1: `user_context` (replaces knowledge_profile + knowledge_styles + knowledge_entries)

A single table for user-stated and TP-written context. Analogous to CLAUDE.md.

```sql
user_context (
  id uuid primary key,
  user_id uuid references auth.users,
  key text not null,          -- 'name', 'role', 'company', 'timezone', 'tone_slack',
                               -- 'tone_gmail', 'verbosity', 'preference:X', 'fact:X'
  value text not null,         -- the actual content
  source text not null,        -- 'user_stated' | 'tp_extracted' | 'document'
  confidence float default 1.0,
  created_at timestamptz,
  updated_at timestamptz,
  unique(user_id, key)         -- one value per key per user
)
```

**Written by:**
- User directly (profile form, Context page preferences)
- TP during conversation ("Remember I prefer bullet points")
- Document upload extraction

**Never written by:** Background inference jobs. If TP learns something, it writes it during the conversation, in context, with the user present.

**Read by:** Working memory builder — simple `SELECT * FROM user_context WHERE user_id = ?`

### Store 2: `filesystem_items` (unchanged)

Platform content with TTL. Synced on schedule. TP searches this when it needs to recall specific platform content.

### What is removed

- `knowledge_profile` — replaced by `user_context` keys: `name`, `role`, `company`, `timezone`
- `knowledge_styles` — replaced by `user_context` keys: `tone_{platform}`, `verbosity_{platform}`
- `knowledge_domains` — removed. Deliverables carry their own source list. Domain grouping is a UI concept, not a data concept.
- `knowledge_entries` — replaced by `user_context` with `key = 'fact:X'` or `key = 'preference:X'`
- `profile_inference.py` — removed
- `domain_inference.py` — removed (domain clustering logic removed; deliverables keep source refs)
- `style_learning.py` — removed (TP learns style conversationally, not from batch inference)
- `working_memory.py` — simplified to just read `user_context` + platform status

---

## Revised working memory (~2,000 tokens)

```
### About you
{user_context keys: name, role, company, timezone}

### Your preferences
{user_context keys: tone_*, verbosity_*, preference:*}

### What you've told me
{user_context keys: fact:*, instruction:*}

### Active deliverables
{deliverables: title, destination, sources, schedule — max 5}

### Connected platforms
{platform_connections: name, status, last_synced, freshness}
```

Raw `filesystem_items` content is NOT in the system prompt. TP fetches it via Search when needed. This keeps the prompt small and the data fresh.

---

## What this changes for TP behavior

**Before:** TP hoped that inference ran correctly and knowledge tables were populated.

**After:** TP starts with only what the user has explicitly stated or TP has explicitly written during prior conversations. For platform content, TP calls Search. This is honest — TP knows exactly what it knows and why.

**First-session behavior:** Working memory is sparse (user hasn't stated anything yet). TP asks or infers from conversation, then writes to `user_context` with `source='tp_extracted'`. Subsequent sessions accumulate stated context naturally.

This is how Claude Code works: CLAUDE.md starts empty, grows as the user adds preferences, and Claude reads what's actually there.

---

## Migration path

1. **Add `user_context` table** (migration)
2. **Migrate existing data**: `knowledge_profile` stated fields → `user_context`, `knowledge_entries` user_stated entries → `user_context`
3. **Simplify `working_memory.py`** to read from `user_context` only
4. **Update Context page**: Profile + Entries sections read/write `user_context`; Styles section simplified to stated preferences only
5. **Remove inference jobs**: `profile_inference.py`, `domain_inference.py`, `style_learning.py`
6. **Remove tables**: `knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries` (after migration)
7. **Keep `knowledge_domains` UI concept** as a frontend filter on deliverables (no DB table needed)

---

## What stays the same

- `filesystem_items` — unchanged, same sync pipeline
- `platform_connections` — unchanged
- `deliverables` — unchanged, sources stay on deliverable
- Search primitive — unchanged, still queries `filesystem_items`
- Platform tools — unchanged, still do live API calls
- Sync scheduler — unchanged

---

## Known tradeoff

Losing automatic style inference means TP doesn't automatically learn "you write casually on Slack but formally in email" from your messages. Instead it learns this conversationally or the user states it explicitly.

This is an acceptable tradeoff because:
- The inference wasn't reliably running anyway
- Conversational learning is more accurate (user can correct in real time)
- Stated preferences are transparent (user can see exactly what TP knows)

Style inference can be re-introduced later as an opt-in feature once the foundation is stable.

---

## ADR-058 checklist file

Move `ADR-058-implementation-checklist.md` to `docs/adr/ADR-058-implementation-checklist.md`. It documents completed migration work, not an active checklist.
