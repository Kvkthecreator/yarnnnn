# ADR-027: Integration Read Architecture

> **Status**: Draft
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

3. **Context Store** (existing `context_sources`, `blocks`)
   - Stores agent-processed output
   - Tagged with source metadata for provenance

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
    "channel_id": "C123...",
    "project_id": "uuid",
    "days_back": 30,
    "instructions": "Focus on product decisions"  // Optional user guidance
}
Response: {
    "job_id": "uuid",
    "status": "processing"
}

GET /api/integrations/import/{job_id}
Response: {
    "status": "completed",
    "blocks_created": 12,
    "memories_created": 3,
    "summary": "Imported 12 context blocks covering product roadmap decisions..."
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

```sql
-- Import job tracking
CREATE TABLE integration_import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    project_id UUID REFERENCES projects(id),
    provider TEXT NOT NULL,
    resource_id TEXT NOT NULL,  -- channel_id, page_id
    resource_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    instructions TEXT,  -- Optional user guidance for agent
    result JSONB,  -- { blocks_created, memories_created, summary }
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Sync configuration for continuous imports
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

- [ ] Create `api/workers/import_job_processor.py` - processes pending jobs
- [ ] Integrate MCP data fetching with ContextImportAgent
- [ ] Store extracted context blocks to `context_sources`
- [ ] Update job status and progress in real-time

### Phase 3: Onboarding UI

- [ ] "Import context from..." in project creation
- [ ] Channel/page picker modal
- [ ] Import progress indicator
- [ ] Import summary display

### Phase 4: Continuous Sync

- [ ] Sync configuration UI
- [ ] Scheduled sync job (cron)
- [ ] Incremental import (delta processing)
- [ ] Sync status indicators

### Phase 5: Style Learning (Future)

- [ ] StyleLearningAgent for communication patterns
- [ ] User writing profile stored as memory
- [ ] Applied to deliverable generation

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
