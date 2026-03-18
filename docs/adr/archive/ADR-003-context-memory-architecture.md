# ADR-003: Context & Memory Architecture

**Status:** Proposed
**Date:** 2025-01-29
**Decision Makers:** Kevin Kim

## Context

YARNNN v5 needs a robust context and memory system that:
1. Supports multiple input channels (manual, chat-derived, documents, integrations)
2. Enables shared memory across agents and work types within a project
3. Maintains interoperability with external LLMs (Claude, ChatGPT, Gemini)
4. Scales from simple text blocks to sophisticated semantic understanding

We have two reference architectures to learn from:
- **Legacy YARN (v3)**: Sophisticated P0→P4 substrate pipeline with semantic blocks and composition intelligence
- **Companion AI**: Three-tier memory system with async extraction and personalization

## Decision Drivers

1. **Progressive complexity**: Start simple, add sophistication as needed
2. **Agent-centric**: Memory serves agents, not just storage
3. **Interoperability**: External sources and LLMs as first-class citizens
4. **Conversation-native**: Chat is a primary context derivation channel
5. **Composability**: Context should be assemblable for different purposes

## Architectural Analysis

### Legacy YARN Substrate (What We Learned)

**Strengths:**
- Staged pipeline (P0→P4) provides clear processing phases
- Semantic typing (guideline, insight, fact) enables smart composition
- Block relations (supports, contradicts, extends) capture knowledge structure
- Composition intelligence with coherence scoring

**Weaknesses:**
- Over-engineered for early stage (8+ substrate types)
- Complex state machines (PROPOSED→ACCEPTED→LOCKED)
- Heavy upfront investment before delivering value
- "Message bus" architecture added coordination overhead

**Key Insight:** The P0 (raw dump) → P1 (extracted blocks) concept is sound, but the 5-stage pipeline was premature optimization.

### Companion AI Memory (What We Learned)

**Strengths:**
- Three-tier hierarchy (Working → Active → Core) maps to reality
- Fire-and-forget async extraction doesn't block UX
- Memory categories (fact, preference, goal, event) are user-centric
- Priority-based retrieval for context assembly
- Upsert pattern prevents duplicates elegantly

**Weaknesses:**
- Designed for 1:1 companion relationship, not project-based work
- Thread tracking assumes ongoing user "life" not discrete projects
- No document/file handling
- No output generation (consumption-only memory)

**Key Insight:** Async extraction from conversation with priority-based retrieval is powerful and should be adopted.

## Proposed Architecture

### Three-Layer Memory Model

```
┌─────────────────────────────────────────────────────────────┐
│                    PROJECT MEMORY                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: DERIVED KNOWLEDGE                                  │
│  ├─ Insights (agent-generated understanding)                 │
│  ├─ Relations (supports, contradicts, extends)               │
│  └─ Summaries (compressed representations)                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: STRUCTURED CONTEXT                                 │
│  ├─ Blocks (semantic units with type + metadata)             │
│  │   Types: fact, guideline, requirement, insight, note      │
│  ├─ Entities (people, orgs, concepts mentioned)              │
│  └─ Tags (user-defined categorization)                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: RAW SOURCES                                        │
│  ├─ Documents (files: PDF, DOCX, images)                     │
│  ├─ Chat History (conversation transcripts)                  │
│  ├─ Manual Input (direct text entry)                         │
│  └─ External Imports (Claude/ChatGPT exports, integrations)  │
└─────────────────────────────────────────────────────────────┘
```

### Context Derivation Channels (Priority Order)

| Channel | Source | Extraction Method | Phase |
|---------|--------|-------------------|-------|
| **Chat** | ThinkingPartner conversations | Async background extraction | P1 |
| **Import** | Claude/ChatGPT conversation exports | Parse + batch extraction | P1 |
| **Documents** | Uploaded files | OCR/parse + extraction | P2 |
| **Manual** | Direct block creation | User-provided | P1 |
| **MCP/Integration** | External tools | API-based | P3 |

### Phase 1 (Now): Foundation

**Tables (extend current schema):**
```sql
-- Extend blocks table with semantic typing
ALTER TABLE blocks ADD COLUMN semantic_type TEXT; -- fact, guideline, requirement, insight, note
ALTER TABLE blocks ADD COLUMN source_type TEXT;   -- manual, chat, document, import
ALTER TABLE blocks ADD COLUMN source_ref UUID;    -- reference to source (session_id, document_id)
ALTER TABLE blocks ADD COLUMN importance FLOAT DEFAULT 0.5;  -- 0-1 relevance score
ALTER TABLE blocks ADD COLUMN expires_at TIMESTAMPTZ;        -- optional TTL

-- Context extraction log (for observability)
CREATE TABLE extraction_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id),
    source_type TEXT NOT NULL,
    source_ref UUID,
    status TEXT NOT NULL, -- pending, processing, completed, failed
    items_extracted INTEGER DEFAULT 0,
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Capabilities:**
- Manual block creation (existing API works)
- Chat-derived extraction (async after ThinkingPartner responses)
- Basic retrieval for agent context assembly

### Phase 2 (Next): Documents & Imports

**New tables:**
```sql
-- Track extraction from documents
ALTER TABLE documents ADD COLUMN extraction_status TEXT DEFAULT 'pending';
ALTER TABLE documents ADD COLUMN extracted_text TEXT;

-- External conversation imports
CREATE TABLE conversation_imports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id),
    source TEXT NOT NULL, -- claude, chatgpt, gemini
    original_format TEXT, -- json, markdown
    content JSONB NOT NULL,
    extraction_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Capabilities:**
- Document upload → text extraction → block derivation
- Claude/ChatGPT export import → parse → block derivation
- Unified context retrieval across all sources

### Phase 3 (Future): Intelligence & Integrations

**Capabilities:**
- Block relations (semantic linking)
- Project-level summaries/insights
- MCP integrations
- Cross-project context sharing

## Context Assembly for Agents

When an agent needs context, the system assembles it using priority-based retrieval:

```python
def get_agent_context(project_id: UUID, max_tokens: int = 4000) -> str:
    """Assemble context for agent consumption."""

    # Priority 1: High-importance blocks (user-marked or extracted as important)
    priority_blocks = get_blocks(project_id, min_importance=0.8)

    # Priority 2: Recent blocks (last 7 days)
    recent_blocks = get_blocks(project_id, since=days_ago(7))

    # Priority 3: Type-specific (facts, guidelines always included)
    core_blocks = get_blocks(project_id, types=['fact', 'guideline', 'requirement'])

    # Deduplicate and assemble within token budget
    return assemble_context(priority_blocks, recent_blocks, core_blocks, max_tokens)
```

## Chat-Derived Context Extraction

Adopt the Companion AI pattern of fire-and-forget extraction:

```python
async def on_chat_response_complete(project_id: UUID, messages: list[dict]):
    """Trigger background extraction after chat response streams."""
    asyncio.create_task(
        extract_context_from_conversation(project_id, messages)
    )

async def extract_context_from_conversation(project_id: UUID, messages: list[dict]):
    """Background extraction - doesn't block user."""
    try:
        # Use LLM to extract facts, decisions, requirements from conversation
        extracted = await llm_extract_blocks(messages)

        for item in extracted:
            # Upsert pattern: (project_id, semantic_type, content_hash)
            upsert_block(
                project_id=project_id,
                content=item['content'],
                semantic_type=item['type'],
                source_type='chat',
                importance=item.get('importance', 0.5)
            )

        log_extraction(project_id, 'chat', 'completed', len(extracted))
    except Exception as e:
        log_extraction(project_id, 'chat', 'failed', error=str(e))
```

## External LLM Interoperability

### Import Strategy

Support importing conversation exports from:
- **Claude**: JSON export format (messages array)
- **ChatGPT**: JSON export format (conversations/messages)
- **Gemini**: Markdown/JSON exports

```python
async def import_external_conversation(
    project_id: UUID,
    source: str,  # 'claude' | 'chatgpt' | 'gemini'
    content: dict | str
) -> int:
    """Import and extract from external LLM conversations."""

    # Store raw import
    import_id = create_import(project_id, source, content)

    # Parse to normalized message format
    messages = parse_external_format(source, content)

    # Extract blocks (same pipeline as chat)
    extracted = await llm_extract_blocks(messages)

    for item in extracted:
        upsert_block(
            project_id=project_id,
            content=item['content'],
            semantic_type=item['type'],
            source_type='import',
            source_ref=import_id
        )

    return len(extracted)
```

### Export Strategy (Future)

Enable YARNNN context to be exported for use in external LLMs:
- Markdown summary format
- JSON structured format
- "Context card" shareable format

## Decision

1. **Adopt three-layer memory model**: Raw Sources → Structured Context → Derived Knowledge
2. **Prioritize chat-derived extraction**: Implement async extraction from ThinkingPartner
3. **Defer document handling to Phase 2**: Focus on chat flow first
4. **Design for import from day 1**: Structure supports external LLM conversation import
5. **Keep blocks simple**: Extend with semantic_type and importance, avoid complex state machines

## Consequences

### Positive
- Chat becomes natural context-building interface (users already chatting)
- External LLM imports make YARNNN a "vault" for AI conversations
- Progressive enhancement path doesn't require big-bang migration
- Agents get assembled context without knowing source details

### Negative
- Async extraction adds background processing complexity
- Import parsing requires format-specific logic per LLM
- Context assembly heuristics may need tuning per use case

### Risks
- Extraction quality depends on LLM (garbage in → garbage out)
- Token budget management for large context sets
- Duplicate detection across sources

## Implementation Roadmap

**Guiding Principle:** Extraction is the first-class feature. Manual CRUD is an escape hatch, not the primary UX.

### Phase 1A: Chat-Derived Extraction (Immediate)
- [x] Add semantic_type, source_type, importance to blocks table
- [ ] Implement extraction service with LLM prompt
- [ ] Fire-and-forget extraction after ThinkingPartner responses
- [ ] Context assembly for agent consumption

### Phase 1B: Bulk Text Import (Immediate)
- [ ] Bulk import endpoint (paste text → extract blocks)
- [ ] Simple "Import Context" UI in Context tab
- [ ] Solves cold start / onboarding problem

### Phase 2: Block Display & Curation
- [ ] Context tab shows extracted blocks (read-first)
- [ ] Edit/delete individual blocks
- [ ] Manual block creation (escape hatch)
- [ ] Importance marking / archival

### Phase 3: Documents & External Imports
- [ ] Document upload + text extraction
- [ ] Claude/ChatGPT conversation import
- [ ] Context export for external use

### Phase 4: Intelligence & Integrations
- [ ] Block relations and semantic linking
- [ ] MCP integrations
- [ ] Cross-project context sharing

## References

- Companion AI Memory Architecture (see exploration notes)
- Legacy YARN v3 Substrate System (see exploration notes)
- [Claude Conversation Export Format](https://support.anthropic.com/)
- [ChatGPT Data Export](https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history)
