# ADR-058: Knowledge Base Architecture

> **Status**: Accepted
> **Created**: 2026-02-13
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-038 (Claude Code Architecture Mapping), ADR-039 (Unified Context Surface), ADR-049 (Context Freshness Model), ADR-034 (Emergent Context Domains)
> **Supersedes**: ADR-034 (partial - domain implementation), ADR-039 (partial - context surface)

---

## Context

### The Problem

After extensive refactoring toward a "filesystem-as-context" model (ADR-038), YARNNN successfully treats platform content (`ephemeral_context`) as the primary data source — analogous to how Claude Code treats a repository. However, a critical gap emerged:

**Claude Code has two layers:**
1. `/repo` — The filesystem (code, raw data)
2. `/docs` — The narrative (CLAUDE.md, ADRs, guides)

**YARNNN only has one:**
1. `ephemeral_context` — The filesystem (platform content)
2. ~~Missing~~ — The narrative layer

This mirrors the Moltbot/ClawdBot pattern where `SOUL.md` and `USER.md` provide structured, human-readable knowledge that the agent can grep and reference.

### The Insight

Raw platform data (Slack messages, emails, Notion pages) is **filesystem** — it's the source of truth but not the meaning. Users need a **knowledge layer** that captures:

- Who they are (profile)
- How they communicate (styles per platform)
- What they're working on (domains)
- What matters to them (preferences, facts, decisions)

This knowledge should be:
1. **Inferred** from the filesystem (not manually curated)
2. **Structured** for retrieval (grep-able, not just vector search)
3. **Editable** by the user (overrides for corrections)
4. **Transparent** (user can see what TP "knows")

### Terminology Confusion

Current naming conflates concepts:

| Term | Problem |
|------|---------|
| `ephemeral_context` | "Ephemeral" suggests temporary, but it's the persistent filesystem |
| `memories` | Overloaded — means both "user facts" and "extracted content" |
| `context_domains` | Unclear relationship to other context concepts |
| "Tell TP" | Labeled "directly in chat" but is actually a form |

---

## Decision

### 1. Adopt Clean Terminology

Align with Claude Code and Moltbot mental models:

| Concept | New Term | Definition |
|---------|----------|------------|
| Raw synced data | **Filesystem** | Platform content + uploaded documents |
| Derived narrative | **Knowledge** | Inferred profile, styles, domains, facts |
| Current prompt state | **Working Memory** | What TP has in context for this request |
| Chat history | **Sessions** | API coherence only, also an inference source |

### 2. Architecture: Filesystem + Knowledge

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YARNNN CONTEXT                              │
│                    (The "Repo" equivalent)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   FILESYSTEM (Raw Data)              KNOWLEDGE (Inferred Narrative) │
│   ─────────────────────              ────────────────────────────── │
│                                                                     │
│   platforms/                         knowledge/                     │
│   ├── slack/                         ├── profile                    │
│   │   └── [synced messages]          │   "Kevin, Founder..."        │
│   ├── gmail/                         │                              │
│   │   └── [synced emails]            ├── styles/                    │
│   ├── notion/                        │   ├── slack                  │
│   │   └── [synced pages]             │   │   "Casual, minimal"      │
│   └── calendar/                      │   ├── email                  │
│       └── [synced events]            │   │   "Formal, structured"   │
│                                      │   └── notion                 │
│   documents/                         │       "Headers, bullets"     │
│   └── [uploaded files]               │                              │
│                                      ├── domains/                   │
│   conversations/                     │   ├── acme                   │
│   └── [session messages]             │   │   "Client since Jan..."  │
│                                      │   └── bigco                  │
│                                      │       "Advisory retainer..." │
│                                      │                              │
│                                      └── entries/                   │
│                                          [preferences, facts,       │
│                                           decisions, instructions]  │
│                                                                     │
│   ↑ Source of truth                  ↑ Derived from filesystem     │
│   ↑ Synced/uploaded/recorded         ↑ Inference + user edits      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. Knowledge is Inferred, Not Curated

```
Filesystem (source of truth)
       ↓
   [Inference Engine]  ← Periodic jobs + on-demand
       ↓
Knowledge Base (derived narrative)
       ↓
   [User Edits]  ← Optional overrides
       ↓
Working Memory (prompt injection)
```

**Key principle**: The Knowledge Base is a **cache of meaning**, not a separate source of truth. Users don't manually maintain it — inference does. But users CAN inspect and override.

### 4. Inference Sources

The inference engine processes:

| Source | Extracts |
|--------|----------|
| `filesystem_items` (platform messages) | Styles, facts, decisions, entities |
| `filesystem_documents` (uploads) | Facts, domain context |
| `session_messages` (conversations) | Preferences, corrections, stated facts |
| `deliverables` (configuration) | Domain groupings |

### 5. User Override Pattern

Every inferred field has a `stated_` counterpart:

```python
def get_user_name(profile):
    # User override takes precedence over inference
    return profile.stated_name or profile.inferred_name
```

This allows:
- Inference to do the heavy lifting
- Users to correct when inference is wrong
- Transparency about what's inferred vs stated

### 6. Sessions Remain Simple

Per ADR-049, sessions are for **API coherence only**:
- Token-based truncation (~50k tokens)
- No compression or rollup
- Knowledge extraction replaces "remembering" from chat

When a user says "remember that I prefer bullets", the inference engine extracts this to `knowledge_entries`, not session history.

---

## Schema Design

### Filesystem Tables

```sql
-- Platform OAuth connections
CREATE TABLE platform_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,  -- 'slack', 'gmail', 'notion', 'calendar'
    status TEXT DEFAULT 'active',
    credentials_encrypted TEXT,
    metadata JSONB DEFAULT '{}',
    settings JSONB DEFAULT '{}',
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(user_id, platform)
);

-- Synced platform content (the "filesystem")
CREATE TABLE filesystem_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_name TEXT,
    item_id TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT,  -- 'message', 'email', 'page', 'event'
    author TEXT,        -- For style inference (is this user's own message?)
    is_user_authored BOOLEAN DEFAULT false,
    source_timestamp TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    sync_batch_id UUID,
    synced_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,

    UNIQUE(user_id, platform, resource_id, item_id)
);

-- Uploaded documents
CREATE TABLE filesystem_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    storage_path TEXT NOT NULL,
    processing_status TEXT DEFAULT 'pending',
    page_count INTEGER,
    word_count INTEGER,
    error_message TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT now(),
    processed_at TIMESTAMPTZ
);

-- Document chunks for retrieval
CREATE TABLE filesystem_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES filesystem_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    embedding vector(1536),
    token_count INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Sync state tracking
CREATE TABLE sync_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_name TEXT,
    last_synced_at TIMESTAMPTZ,
    platform_cursor TEXT,
    item_count INTEGER DEFAULT 0,
    sync_metadata JSONB DEFAULT '{}',

    UNIQUE(user_id, platform, resource_id)
);
```

### Knowledge Tables

```sql
-- User profile (inferred + editable)
CREATE TABLE knowledge_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Inferred fields
    inferred_name TEXT,
    inferred_role TEXT,
    inferred_company TEXT,
    inferred_timezone TEXT,
    inferred_summary TEXT,  -- "Founder building an AI product..."

    -- User overrides (take precedence)
    stated_name TEXT,
    stated_role TEXT,
    stated_company TEXT,
    stated_timezone TEXT,
    stated_summary TEXT,

    -- Inference metadata
    last_inferred_at TIMESTAMPTZ,
    inference_sources JSONB DEFAULT '[]',
    inference_confidence FLOAT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Platform-specific communication styles
CREATE TABLE knowledge_styles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,  -- 'slack', 'email', 'notion'

    -- Inferred style attributes
    tone TEXT,              -- 'casual', 'formal', 'mixed'
    verbosity TEXT,         -- 'minimal', 'moderate', 'detailed'
    formatting JSONB DEFAULT '{}',  -- {uses_emoji, uses_bullets, avg_length, etc.}
    vocabulary_notes TEXT,  -- "Uses technical jargon", "Avoids corporate speak"
    sample_excerpts TEXT[], -- Actual examples of user's writing

    -- User overrides
    stated_preferences JSONB DEFAULT '{}',

    -- Inference metadata
    sample_count INTEGER DEFAULT 0,
    last_inferred_at TIMESTAMPTZ,
    inference_sources JSONB DEFAULT '[]',

    UNIQUE(user_id, platform)
);

-- Work domains (inferred from deliverable patterns)
CREATE TABLE knowledge_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Identity
    name TEXT NOT NULL,
    name_source TEXT DEFAULT 'inferred',  -- 'inferred' or 'user'

    -- Inferred narrative
    summary TEXT,           -- "Consulting engagement for enterprise client..."
    key_facts TEXT[],       -- ["Launch date March 15", "Budget approved"]
    key_people JSONB DEFAULT '[]',  -- [{name, role, notes}]
    key_decisions TEXT[],   -- Important decisions made

    -- Source mapping (which filesystem resources belong here)
    sources JSONB DEFAULT '[]',  -- [{platform, resource_id, resource_name}]

    -- Flags
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,

    -- Inference metadata
    last_inferred_at TIMESTAMPTZ,
    inference_confidence FLOAT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- General knowledge entries (preferences, facts, decisions)
CREATE TABLE knowledge_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    domain_id UUID REFERENCES knowledge_domains(id) ON DELETE SET NULL,

    content TEXT NOT NULL,
    entry_type TEXT NOT NULL,  -- 'preference', 'fact', 'decision', 'instruction'

    -- Source tracking
    source TEXT NOT NULL,  -- 'inferred', 'user_stated', 'document', 'conversation'
    source_ref JSONB,      -- {table, id} for traceability

    -- For inferred entries
    confidence FLOAT,
    inference_sources JSONB DEFAULT '[]',

    -- Organization
    tags TEXT[] DEFAULT '{}',
    importance FLOAT DEFAULT 0.5,

    -- Lifecycle
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### Session Tables (Minimal Changes)

```sql
-- Chat sessions (unchanged purpose: API coherence)
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    domain_id UUID REFERENCES knowledge_domains(id),

    status TEXT DEFAULT 'active',
    summary TEXT,  -- Optional session summary

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Session messages (now also an inference source)
CREATE TABLE session_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,

    role TEXT NOT NULL,  -- 'user', 'assistant'
    content TEXT,
    sequence_number INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',

    -- Knowledge extraction tracking
    knowledge_extracted BOOLEAN DEFAULT false,
    knowledge_extracted_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Deliverables (Updated References)

```sql
CREATE TABLE deliverables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    domain_id UUID REFERENCES knowledge_domains(id),

    title TEXT NOT NULL,
    deliverable_type TEXT,
    status TEXT DEFAULT 'active',

    -- Sources point to filesystem
    sources JSONB DEFAULT '[]',  -- [{platform, resource_id, resource_name}]

    -- Configuration
    schedule JSONB,
    recipient_context JSONB,
    template JSONB,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    next_run_at TIMESTAMPTZ
);

CREATE TABLE deliverable_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deliverable_id UUID NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,

    content TEXT,
    version_number INTEGER NOT NULL,
    status TEXT DEFAULT 'draft',

    -- Source snapshot (what was used at generation time)
    source_snapshots JSONB DEFAULT '[]',

    generated_at TIMESTAMPTZ DEFAULT now(),
    approved_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ
);
```

---

## Working Memory (TP Prompt Injection)

### What TP Sees

```python
async def build_working_memory(user_id: str, client) -> dict:
    """
    Build the context object injected into TP's system prompt.
    Reads from Knowledge tables, not Filesystem directly.
    """
    return {
        "profile": await get_knowledge_profile(user_id, client),
        "styles": await get_knowledge_styles(user_id, client),
        "domains": await get_active_domains(user_id, client),
        "entries": await get_recent_entries(user_id, client, limit=20),
        "platforms": await get_platform_status(user_id, client),
        "deliverables": await get_active_deliverables(user_id, client),
    }
```

### Formatted Prompt Section

```markdown
## Your Knowledge

**Profile**: Kevin, Founder at YARNNN
- Building an AI-powered context platform
- Based in [timezone] (inferred from calendar)

**Communication Styles**:
- Slack: Casual, minimal, no emoji (from 142 messages)
- Email: Formal with clear structure (from 47 sent)
- Notion: Headers + bullet points (from 12 pages)

**Work Domains**:
- YARNNN (default): Product development, launch preparation
  Sources: #product, #engineering, Notion workspace
- Consulting: 2 active clients (Acme, BigCo)

**Key Knowledge**:
- Prefers bullet points over prose [stated]
- Reports typically due Fridays [inferred from calendar]
- Launch target: end of Q1 [inferred from conversations]

## Connected Platforms
- Slack: 3 channels (synced 2h ago)
- Gmail: Inbox (synced 1h ago)
- Notion: 5 pages (synced 3d ago - stale)

## Active Deliverables
- Weekly Status → Sarah (Fridays)
- Board Update → Marcus (Monthly)
```

---

## Inference Engine

### Triggers

| Event | Inference Action |
|-------|------------------|
| After platform sync | Style inference from new user-authored messages |
| After deliverable created/updated | Domain re-clustering |
| Daily scheduled job | Profile refresh, domain summaries, entry cleanup |
| User requests "Refresh" | Full re-inference |
| After chat session | Extract knowledge from conversation |

### Style Inference

```python
async def infer_platform_style(user_id: str, platform: str, client):
    """
    Analyze user-authored messages to infer communication style.
    """
    # Get recent user-authored messages
    messages = await client.table("filesystem_items").select("*").eq(
        "user_id", user_id
    ).eq(
        "platform", platform
    ).eq(
        "is_user_authored", True
    ).order(
        "source_timestamp", desc=True
    ).limit(100).execute()

    if not messages.data:
        return None

    # Analyze patterns
    analysis = await analyze_writing_style(messages.data)

    # Upsert to knowledge_styles
    await client.table("knowledge_styles").upsert({
        "user_id": user_id,
        "platform": platform,
        "tone": analysis.tone,
        "verbosity": analysis.verbosity,
        "formatting": analysis.formatting,
        "sample_excerpts": analysis.excerpts[:5],
        "sample_count": len(messages.data),
        "last_inferred_at": datetime.now(UTC).isoformat(),
        "inference_sources": [{"table": "filesystem_items", "count": len(messages.data)}]
    }).execute()
```

### Conversation Extraction

```python
async def extract_knowledge_from_conversation(session_id: str, client):
    """
    Extract knowledge entries from chat messages.
    Runs after session or periodically.
    """
    # Get unprocessed user messages
    messages = await client.table("session_messages").select("*").eq(
        "session_id", session_id
    ).eq(
        "role", "user"
    ).eq(
        "knowledge_extracted", False
    ).execute()

    for msg in messages.data:
        # Use LLM to identify extractable knowledge
        extractions = await identify_knowledge(msg["content"])

        for extraction in extractions:
            await client.table("knowledge_entries").insert({
                "user_id": user_id,
                "content": extraction.content,
                "entry_type": extraction.type,  # preference, fact, decision
                "source": "conversation",
                "source_ref": {"table": "session_messages", "id": msg["id"]},
                "confidence": extraction.confidence,
            }).execute()

        # Mark as processed
        await client.table("session_messages").update({
            "knowledge_extracted": True,
            "knowledge_extracted_at": datetime.now(UTC).isoformat()
        }).eq("id", msg["id"]).execute()
```

---

## Context Page UI

### Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Context                                           [Refresh All ↻]  │
├──────────────┬──────────────────────────────────────────────────────┤
│              │                                                      │
│  KNOWLEDGE   │  Profile                              [Edit]         │
│  ● Profile   │  ──────────────────────────────────────────────────  │
│  ○ Styles    │  Kevin · Founder at YARNNN                           │
│  ○ Domains   │  "Building an AI-powered context platform"           │
│  ○ Entries   │  ⓘ Inferred from email signatures                   │
│              │                                                      │
│  ──────────  │  Styles                                              │
│              │  ──────────────────────────────────────────────────  │
│  FILESYSTEM  │  ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│  ○ Platforms │  │ Slack   │ │ Email   │ │ Notion  │               │
│  ○ Documents │  │ Casual  │ │ Formal  │ │ Struct. │               │
│              │  │ 142 msg │ │ 47 sent │ │ 12 pgs  │               │
│  ──────────  │  └─────────┘ └─────────┘ └─────────┘               │
│              │                                                      │
│  ACTIONS     │  Domains                                             │
│  [+ Add      │  ──────────────────────────────────────────────────  │
│   Knowledge] │  ┌───────────────────────────────────────────────┐  │
│              │  │ YARNNN (default)                    [Edit]     │  │
│              │  │ Product development, launch prep               │  │
│              │  │ Sources: #product · #engineering · Notion      │  │
│              │  └───────────────────────────────────────────────┘  │
│              │                                                      │
│              │  Entries                                [+ Add]      │
│              │  ──────────────────────────────────────────────────  │
│              │  • Prefers bullet points (stated)                   │
│              │  • Reports due Fridays (inferred · calendar)        │
│              │  • Launch target end of Q1 (inferred · chat)        │
│              │                                                      │
└──────────────┴──────────────────────────────────────────────────────┘
```

### Empty State

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                    Your context is empty                            │
│                                                                     │
│    TP works best when it knows about your work.                    │
│    Add context from any of these sources:                           │
│                                                                     │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│    │ Connect     │  │ Upload      │  │ Add         │              │
│    │ Platforms   │  │ Documents   │  │ Knowledge   │              │
│    │             │  │             │  │             │              │
│    │ Slack,      │  │ PDFs,       │  │ Tell TP     │              │
│    │ Gmail,      │  │ docs,       │  │ about you   │              │
│    │ Notion      │  │ notes       │  │ directly    │              │
│    └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                     │
│    Connect platforms to auto-learn your style and context.         │
│    Or add knowledge directly — TP will remember it.                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Migration Plan

### Phase 1: Schema Creation (Non-Breaking)

1. Create new tables alongside existing
2. No data migration yet
3. Deploy and validate schema

### Phase 2: Data Migration

```sql
-- Migrate user_integrations → platform_connections
INSERT INTO platform_connections (id, user_id, platform, status, ...)
SELECT id, user_id, provider, status, ...
FROM user_integrations;

-- Migrate ephemeral_context → filesystem_items
INSERT INTO filesystem_items (id, user_id, platform, resource_id, ...)
SELECT id, user_id, platform, resource_id, ...
FROM ephemeral_context;

-- Migrate documents → filesystem_documents
INSERT INTO filesystem_documents (id, user_id, filename, ...)
SELECT id, user_id, filename, ...
FROM documents;

-- Migrate context_domains → knowledge_domains
INSERT INTO knowledge_domains (id, user_id, name, ...)
SELECT id, user_id, name, ...
FROM context_domains;

-- Migrate memories (user_stated) → knowledge_entries
INSERT INTO knowledge_entries (user_id, content, entry_type, source, ...)
SELECT user_id, content, 'preference', 'user_stated', ...
FROM memories
WHERE source_type IN ('user_stated', 'chat', 'conversation');

-- Create default knowledge_profile for each user
INSERT INTO knowledge_profile (user_id)
SELECT DISTINCT user_id FROM platform_connections;
```

### Phase 3: API Migration

1. Create new routes under `/api/v2/`
2. Update services to use new tables
3. Dual-write during transition

### Phase 4: Frontend Migration

1. Update Context page to new schema
2. Update API client
3. Remove old components

### Phase 5: Cleanup

1. Remove old tables
2. Remove v1 routes
3. Update all references

---

## Consequences

### Positive

1. **Clear mental model** — Filesystem vs Knowledge distinction
2. **Inference-driven** — Users don't manually curate
3. **Transparent** — Users see what TP knows and why
4. **Editable** — User overrides when inference is wrong
5. **Grep-able** — Structured knowledge for retrieval
6. **Aligned** — Matches Claude Code and Moltbot patterns

### Negative

1. **Migration effort** — Schema and code changes
2. **Inference complexity** — Need to build extraction pipelines
3. **Naming churn** — Existing code uses old terms

### Mitigations

- Clean-slate migration (pre-launch, no users)
- Phased rollout with dual-write
- Comprehensive test coverage

---

## Implementation Status

> **Completed**: 2026-02-13

### Phase 1-5: Schema & Migration ✅

All schema changes and migrations applied:

| Migration | Status | Description |
|-----------|--------|-------------|
| 043 | ✅ Applied | Create new schema tables |
| 044 | ✅ Applied | Data migration from old tables |
| 045 | ✅ Applied | Drop old tables, cleanup |
| 046 | ✅ Applied | Restore integration_import_jobs |
| 047 | ✅ Applied | Fix memory RPCs for knowledge_entries |
| 048 | ✅ Applied | Fix domain RPCs for knowledge_domains.sources |

### Backend Updates ✅

- All routes updated to use new table names (`platform_connections`, `filesystem_items`, `knowledge_domains`, `knowledge_entries`)
- All RPC functions updated to use new schema
- Legacy code and backwards compatibility shims removed
- TP working memory injection verified against new schema

### Frontend Updates ✅

- `DomainSource.platform` type updated (was `provider`)
- Context page uses correct API endpoints
- Deliverable source selection verified
- Platform detail pages verified

### Inference Engine ✅

- `api/services/profile_inference.py` - Infers user profile from filesystem content
- Triggered automatically after platform sync
- Uses Claude Haiku for LLM-based extraction
- 24-hour cooldown to avoid redundant processing

### Conversation Extraction ✅

- `api/services/extraction.py` - Already integrated in chat.py
- Fires as background task after each TP conversation
- Extracts facts, preferences, decisions to `knowledge_entries`

### Entity Enrichment Pattern ✅

TP primitives resolve entity references via `api/services/primitives/refs.py`. Some entities require **enrichment** from auxiliary tables to provide complete data:

| Entity Type | Base Table | Enrichment Source | Function |
|------------|------------|-------------------|----------|
| `document` | `filesystem_documents` | `filesystem_chunks` (content) | `_enrich_document_with_content()` |
| `platform` | `platform_connections` | `sync_registry` (sync status) | `_enrich_platform_with_sync_status()` |

**Why enrichment matters**: Base tables store metadata, but related data (content, sync status) lives in auxiliary tables. Without enrichment, TP would see incomplete data (e.g., "Last sync: Never" when `sync_registry` has the actual sync timestamp).

**Consistency requirement**: If a UI page (e.g., Context page at `/context/[platform]`) shows data by querying multiple tables, TP primitives must use the same enrichment pattern to avoid data mismatches.

**Adding new enrichments**: Follow the pattern in `resolve_ref()`:
```python
# In resolve_ref() after base query:
if ref.entity_type == "your_type":
    entity = await _enrich_your_type_with_data(client, auth.user_id, entity)
```

### User Override UI ✅

- Profile editing in `/context?section=profile`
- Style preferences editing in `/context?section=styles`
- `stated_*` fields take precedence over `inferred_*` fields
- Visual indicator shows "custom" vs "inferred" values

---

## Open Questions (Deferred)

1. **Knowledge export** — Should users be able to download as Markdown files?
2. **Knowledge sharing** — Can domains be shared between users (teams)?
3. **Inference UI** — Should users see inference in real-time or only results?
4. **Confidence thresholds** — When is inference confident enough to surface?

---

## References

- [ADR-038: Claude Code Architecture Mapping](ADR-038-claude-code-architecture-mapping.md)
- [ADR-039: Unified Context Surface](ADR-039-unified-context-surface.md)
- [ADR-049: Context Freshness Model](ADR-049-context-freshness-model.md)
- [Moltbot Architecture Analysis](../research/CLAWDBOT_ANALYSIS.md)
- Claude Code `/docs` and `CLAUDE.md` patterns
