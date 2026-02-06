# ADR-027: Integration Read Architecture

> **Status**: Implemented (Phases 1-3, 5)
> **Created**: 2026-02-06
> **Related**: ADR-026 (Integration Architecture), ADR-015 (Unified Context Model)

---

## Context

ADR-026 established YARNNN's integration architecture for **exporting** deliverables. Two gaps remain:

1. **Context Cold Start**: New users have no context. Building from scratch delays time-to-value.
2. **One-Way Data Flow**: Current integrations only push out. No mechanism to pull context in.

With OAuth connections to Slack and Notion, we can read from these platforms.

---

## Decision

**All integration reads are agent-mediated. Raw API data is never stored directly.**

This aligns with YARNNN's core philosophy from ESSENCE.md:

> **Agent-to-agent architecture, user as supervisor.**
>
> Context Loading → Agent Execution (LLM call) → Output Capture

### The Principle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WRONG: Raw API passthrough                                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    Slack API ──────────────────────────────────────────> context_sources
              raw messages dumped directly (useless)

┌─────────────────────────────────────────────────────────────────────────────┐
│  CORRECT: Agent-mediated integration                                        │
└─────────────────────────────────────────────────────────────────────────────┘

    Slack API ────> Integration Agent ────> context_sources
                    (LLM interprets)        (structured blocks)

    - Extracts decisions
    - Identifies action items
    - Learns communication style
    - Structures for retrieval
```

### Why Agents Are Mandatory

| Raw API Data | Agent-Processed Context |
|--------------|------------------------|
| `{"text": "let's go with option B"}` | "**Decision**: Team chose Option B for Q1 roadmap. Stakeholders: @alice, @bob. Date: 2026-02-01" |
| 50 messages about meeting logistics | Filtered out (noise) |
| Thread with technical discussion | "**Technical Context**: API rate limits require caching layer. Estimated 2 weeks." |

Raw data is noise. Agents extract signal.

---

## Architecture

Per ADR-026, **MCP is the primary integration stack** - for both reads and writes.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Agent-Mediated Integration Flow (via MCP)                │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Data Source  │     │ MCP Server   │     │ Integration  │     │  Context     │
│ (Slack/      │────>│ (via MCP     │────>│ Agent (LLM)  │────>│  Store       │
│  Notion)     │     │  Client)     │     │              │     │  (blocks)    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                │ Also produces:
                                                ▼
                                         ┌──────────────┐
                                         │ Style/Prefs  │
                                         │ (memories)   │
                                         └──────────────┘
```

### Components

1. **MCP Client Layer** (`api/integrations/core/client.py`)
   - MCPClientManager spawns MCP servers as subprocesses
   - Uses official MCP servers (`@modelcontextprotocol/server-slack`, `@notionhq/notion-mcp-server`)
   - Handles data acquisition via MCP tools (read channels, get history, search pages)
   - **No direct API calls** - all external communication via MCP

2. **Integration Agents** (`api/agents/integration/`)
   - Receive raw data from MCP as input
   - LLM interprets and structures
   - Output: context blocks, memories, style profiles

3. **Context Store** (existing `memories` table per ADR-005)
   - Stores agent-processed output with `source_type = 'import'`
   - Provenance tracked via `source_ref` JSONB column
   - Inherits unified memory architecture (embeddings, project scoping)

### Why MCP for Reads (Not Direct APIs)?

ADR-026 explicitly rejected "Native API Integrations (No MCP)" because:
- Duplicates work that MCP servers already do
- Higher maintenance burden (API changes, auth flows)
- Misses industry convergence toward MCP
- Less extensible for future integrations

The same logic applies to reads as to writes. MCP servers handle:
- API authentication
- Pagination
- Rate limiting
- Data transformation

---

## Integration Agent Types

| Agent | Input | Output | Use Case |
|-------|-------|--------|----------|
| **ContextImportAgent** | Slack channel / Notion page | Context blocks | Onboarding, cold start |
| **StyleLearningAgent** | User's messages | Communication profile (memory) | Personalization |
| **SyncAgent** | Delta since last sync | Updated context blocks | Keep context fresh |
| **DraftAssistAgent** | Thread + context | Draft reply | Active Slack work |

### Example: ContextImportAgent

```python
# api/agents/integration/context_import.py

class ContextImportAgent(BaseAgent):
    """Import external content as structured context blocks."""

    async def execute(
        self,
        raw_data: list[dict],  # Raw messages/pages from API
        source: str,           # "slack" | "notion"
        project_id: str,
        parameters: dict
    ) -> AgentResult:
        """
        1. Build prompt with raw data
        2. LLM extracts and structures
        3. Return context blocks
        """

        system_prompt = """You are a context extraction agent for YARNNN.

        Given raw messages/content from {source}, extract and structure:

        1. **Decisions** - What was decided, by whom, when
        2. **Action Items** - Tasks, owners, deadlines
        3. **Project Context** - Goals, constraints, requirements
        4. **Key People** - Stakeholders, their roles/preferences
        5. **Technical Details** - Architecture, constraints, dependencies

        Filter out:
        - Casual conversation / small talk
        - Meeting logistics
        - Off-topic tangents

        Output as structured blocks, each with:
        - type: decision | action_item | context | person | technical
        - content: The extracted information (concise, professional)
        - metadata: source_ts, participants, confidence
        """

        response = await self.llm.complete(
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps(raw_data)}]
        )

        return AgentResult(
            blocks=self._parse_blocks(response),
            metadata={"source": source, "items_processed": len(raw_data)}
        )
```

---

## Invocation Paths

The same agent can be invoked multiple ways:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Agent Invocation Paths                              │
└─────────────────────────────────────────────────────────────────────────────┘

1. YARNNN UI (Onboarding)
   User clicks "Import from Slack" → API endpoint → Agent execution

2. Scheduled Job (Continuous Sync)
   Cron job → Fetch delta → Agent execution → Update context

3. Claude Desktop (AI-Assisted)
   User in Claude: "Read #engineering and save decisions to YARNNN"
   Claude Desktop → MCP read tools → Agent execution → YARNNN MCP save

4. TP Conversation
   User to TP: "Import context from my Notion project page"
   TP recognizes intent → Triggers integration agent
```

All paths use the same agent. The agent is the consistent intelligence layer.

---

## API Design

### Import Endpoints

```
POST /api/integrations/slack/import
Body: {
    "resource_id": "C123...",       // Channel ID
    "resource_name": "#engineering", // Display name
    "project_id": "uuid",           // Optional project scope
    "instructions": "Focus on product decisions",  // Optional user guidance
    "config": {                     // Optional config (Phase 5)
        "learn_style": true,        // Extract communication style
        "style_user_id": "U123..."  // Slack user ID to analyze (optional)
    }
}
Response: {
    "id": "uuid",
    "provider": "slack",
    "resource_id": "C123...",
    "status": "pending",
    "progress": 0,
    "created_at": "2026-02-06T..."
}

GET /api/integrations/import/{job_id}
Response: {
    "id": "uuid",
    "status": "completed",
    "result": {
        "blocks_created": 12,
        "items_processed": 47,
        "items_filtered": 35,
        "summary": "Imported 12 context blocks covering product roadmap decisions...",
        "style_learned": true,          // Phase 5
        "style_confidence": "high"      // Phase 5
    }
}
```

### Resource Discovery Endpoints

```
GET /api/integrations/slack/channels
Response: { "channels": [{ "id", "name", "member_count" }] }

GET /api/integrations/notion/pages
Response: { "pages": [{ "id", "title", "last_edited" }] }
```

---

## Data Model

### Import Jobs Table

```sql
CREATE TABLE integration_import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    project_id UUID REFERENCES projects(id),
    provider TEXT NOT NULL,  -- 'slack' | 'notion'
    resource_id TEXT NOT NULL,  -- channel_id, page_id
    resource_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    instructions TEXT,  -- Optional user guidance for agent
    result JSONB,  -- { blocks_created, items_processed, items_filtered, summary }
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
```

### Memory Storage (Imported Context)

Imported context is stored in the **existing `memories` table** (ADR-005), not a separate table:

```sql
-- Imported context stored as memories
INSERT INTO memories (user_id, project_id, content, source_type, source_ref, importance, tags)
VALUES (
    'user-uuid',
    'project-uuid',  -- NULL for user-scoped
    'Team decided to use PostgreSQL for the new API.',
    'import',  -- source_type indicates imported content
    '{
        "platform": "slack",
        "resource_id": "C0123CHANNEL",
        "resource_name": "#engineering",
        "job_id": "job-uuid",
        "block_type": "decision",
        "metadata": {"confidence": "high", "participants": ["@alice", "@bob"]}
    }',
    0.9,  -- High importance for decisions
    ARRAY['decision']
);
```

This leverages the unified memory architecture:
- **Scope**: `project_id = NULL` → user-scoped (portable), `project_id = uuid` → project-scoped
- **Retrieval**: Embedding-based similarity search works out of the box
- **Provenance**: `source_ref` JSONB tracks origin platform, resource, and job

### Sync Configuration (Future)

```sql
CREATE TABLE integration_sync_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    project_id UUID REFERENCES projects(id),
    provider TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_name TEXT,
    sync_enabled BOOLEAN DEFAULT true,
    sync_interval_hours INT DEFAULT 24,
    last_synced_at TIMESTAMPTZ,
    sync_cursor TEXT,  -- Provider-specific (Slack ts, Notion edited_time)
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(user_id, provider, resource_id)
);
```

---

## Implementation Phases

### Phase 1: Foundation (This PR)

- [x] Add MCP read methods to `MCPClientManager` (list_slack_channels, get_slack_channel_history, search_notion_pages, get_notion_page_content)
- [x] Create `api/agents/integration/context_import.py` - Import agent
- [x] Add database migration for import jobs table (`024_integration_import_jobs.sql`)
- [x] Add resource discovery endpoints (`/integrations/slack/channels`, `/integrations/notion/pages`)
- [x] Add import job endpoints (`/integrations/slack/import`, `/integrations/notion/import`)

### Phase 2: Background Job Processing

- [x] Create `api/jobs/import_jobs.py` - processes pending import jobs
- [x] Integrate into `unified_scheduler.py` (runs every 5 minutes)
- [x] Store extracted context to `memories` table (source_type='import')
- [x] Job status tracked via `integration_import_jobs` table

### Phase 3: Onboarding UI

- [x] "Import context" button on connected integrations in Settings
- [x] `IntegrationImportModal` component with channel/page picker
- [x] Import progress indicator with polling
- [x] Import summary display with blocks created, items processed, noise filtered
- [x] Style learning toggle option during import

### Phase 4: Continuous Sync (Deferred)

**Status**: Intentionally deferred. See rationale below.

- [ ] Sync configuration UI
- [ ] Scheduled sync job (cron)
- [ ] Incremental import (delta processing)
- [ ] Sync status indicators

#### Why Deferred

Phase 4 was deprioritized in favor of more fundamental architectural exploration. The manual import flow (Phases 1-3) covers the core use case. Continuous sync is convenience/polish.

**Key Insight**: While designing Phase 4, we recognized that "continuous sync" touches on a deeper question about how YARNNN models deliverables and their relationship to external platforms. This led to the exploration documented in:

- [Analysis: Deliverable-Scoped Context](../analysis/deliverable-scoped-context.md) - Missing memory layer
- [ADR-028: Destination-First Deliverables](./ADR-028-destination-first-deliverables.md) - Conceptual reframe

#### The Larger Question

Continuous sync assumes the current model: "keep context fresh so deliverables are better." But a more profound insight emerged:

> **The deliverable isn't the content. It's the commitment to deliver something to a destination.**

If destination becomes first-class in the deliverable model:
- Style context auto-infers from destination (Slack → casual style)
- Sync becomes bidirectional awareness (not just context freshness)
- The supervision point shifts from "review content" to "supervise delivery commitment"

Phase 4 will be revisited after ADR-028 exploration concludes. The current import flow remains sufficient for MVP.

#### When to Reconsider

- If users frequently re-import the same channels (indicates need for automation)
- If stale context visibly degrades deliverable quality
- After ADR-028 design decisions are made (destination-first may change sync requirements)

### Phase 5: Style Learning

- [x] `StyleLearningAgent` for multi-context communication patterns
- [x] User writing profiles stored as user-scoped memories (`project_id = NULL`)
- [x] Platform-aware style profiles (Slack: casual/realtime, Notion: formal/documentation)
- [x] Style integration into deliverable pipeline via `style_context` parameter
- [x] UI toggle for style learning during import

---

## Phase 5: Style Learning Details

### Key Insight: Context-Dependent Style

The same user writes differently across platforms:

| Platform | Context | Typical Style |
|----------|---------|---------------|
| Slack | realtime_chat | Casual, brief, emoji-friendly |
| Notion | documentation | Structured, thorough, formal |
| Email | formal_comms | Professional, warm opening/closing |

**Decision**: Store separate style memories per platform, tagged appropriately.

### StyleProfile Data Model

```python
@dataclass
class StyleProfile:
    platform: str       # slack, notion, email
    context: str        # realtime_chat, documentation, formal_comms
    tone: str           # formal, casual, professional, friendly
    verbosity: str      # concise, moderate, detailed
    structure: str      # bullets, paragraphs, mixed, headers
    vocabulary_notes: str
    sentence_style: str
    common_phrases: list[str]
    emoji_usage: str    # never, minimal, moderate, frequent
    formatting_preferences: str
    full_profile: str   # Complete description for prompts
    sample_size: int
    confidence: str     # high, medium, low
```

### Style Memory Storage

```sql
-- Style memories are user-scoped (portable across projects)
INSERT INTO memories (user_id, project_id, content, source_type, source_ref, importance, tags)
VALUES (
    'user-uuid',
    NULL,  -- User-scoped, not project-scoped
    '## Communication Style Profile (Slack)

    **Context**: Realtime Chat
    **Confidence**: high (based on 47 samples)

    ### Core Attributes
    - **Tone**: casual
    - **Verbosity**: concise
    - **Structure**: mixed
    - **Emoji Usage**: moderate

    ### Detailed Profile
    [Full profile description...]',
    'import',
    '{"analysis_type": "style", "platform": "slack", "context": "realtime_chat", ...}',
    0.8,  -- High importance for style
    ARRAY['style', 'slack', 'realtime_chat']
);
```

### Style Application in Deliverables

1. **Deliverable Configuration**:
   ```json
   {
     "deliverable_type": "status_report",
     "type_config": {
       "style_context": "slack",  // Use slack style for this deliverable
       ...
     }
   }
   ```

2. **Pipeline Integration**:
   - `execute_synthesize_step` extracts `style_context` from `type_config`
   - Passes to content agent as parameter
   - Agent's `build_context_prompt` selects matching style memory
   - Style profile included in system prompt for generation

3. **Style Selection Logic**:
   - If `style_context` provided, find matching style memory by tag
   - If multiple styles exist, use the most relevant match
   - If no match, include all available style profiles for agent to choose

---

## Security

### OAuth Scopes (Extended for Reads)

| Provider | Current | Add for Reads |
|----------|---------|---------------|
| Slack | `chat:write` | `channels:history`, `channels:read`, `groups:history` |
| Notion | `insert_content` | `read_content` |

Users may need to re-authorize to grant additional scopes.

### Data Handling

- Raw API data is transient (not persisted)
- Only agent-processed blocks are stored
- Source metadata preserved for provenance
- User controls what to import (explicit action)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Users who import during onboarding | >30% |
| Time to meaningful context | <5 minutes |
| Context quality (user satisfaction) | >4/5 rating |
| Sync configuration adoption | >20% of integration users |

---

## References

- [ADR-026: Integration Architecture](./ADR-026-integration-architecture.md)
- [ESSENCE.md](../ESSENCE.md) - Agent execution pattern
- [Slack API](https://api.slack.com/methods)
- [Notion API](https://developers.notion.com/)
