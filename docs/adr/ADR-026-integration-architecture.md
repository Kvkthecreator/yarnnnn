# ADR-026: Integration Architecture

> **Status**: Draft
> **Created**: 2026-02-06
> **Related**: ADR-001 (Foundational Principles), ADR-018 (Recurring Deliverables), ADR-019 (Deliverable Types)

---

## Context

YARNNN generates deliverables (status reports, research briefs, board updates, etc.) that users need to distribute through their existing workflows. The current review surface provides basic viewing but lacks efficient export paths.

Two strategic directions exist:

1. **Build rich editing features** - Markdown editor, formatting toolbar, collaboration tools
2. **Build integrations** - Push outputs to Slack, Notion, Google Docs, etc.

This ADR establishes the architectural direction for how YARNNN delivers value to users' external workflows.

---

## Decision

**YARNNN will prioritize third-party integrations over in-app editing features, using MCP (Model Context Protocol) as the preferred integration stack.**

The review surface will remain minimal (view + copy + quick export), while investment goes toward:

1. **MCP client layer** - Core infrastructure for connecting to MCP servers (P1)
2. **Slack integration via MCP** - Using `@modelcontextprotocol/server-slack` (P1)
3. **Notion integration via MCP** - Using `@notionhq/notion-mcp-server` (P1)
4. **YARNNN MCP server** - Expose YARNNN context to other AI tools (P2)
5. **Google Docs via MCP** - As MCP server matures (P2)

### Rationale

#### Alignment with Supervisor Model

From ADR-001 and ESSENCE.md, YARNNN's mental model is:

> Users are supervisors of AI-generated work, not operators of document tools.

Quality improvement happens through TP conversation ("make it more concise"), not manual text editing. Building a rich editor contradicts this model.

#### Utility Focus

From the design principle "professional work tool, not engagement platform":

> Minimize time spent in-app; maximize value delivered to workflow.

Users should approve a deliverable and immediately export it to where they work. Friction to export = failed experience.

#### Competitive Positioning

Notion, Google Docs, and Microsoft 365 have decades of investment in document editing. YARNNN cannot and should not compete on this axis. Our moat is the intelligence layer (TP + memory system + recurring automation).

---

## Consequences

### Positive

- Focus investment on differentiated capabilities (intelligence, not documents)
- Meet users in their existing workflows
- Faster time-to-value for approved deliverables
- Clear product boundaries (YARNNN = generation, Slack/Notion = distribution)

### Negative

- Users cannot deeply edit content in YARNNN (by design)
- Dependency on MCP ecosystem maturity and stability
- MCP server availability varies by platform
- Need to manage MCP server instances (if self-hosting)

### Neutral

- Review surface needs markdown preview (not editing, just display)
- Export preferences become part of deliverable configuration

---

## Architectural Approach

### Integration Types

| Type | Description | Examples |
|------|-------------|----------|
| **Push** | YARNNN sends content to external service | Slack message, Notion page |
| **Link** | User receives link to view content externally | Google Docs, Calendar event |
| **Download** | User downloads file locally | PDF, Markdown file |

### Data Model

```sql
-- User's connected integrations
CREATE TABLE user_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,  -- 'slack', 'notion', 'google'
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    metadata JSONB DEFAULT '{}',  -- { workspace_id, team_name, etc. }
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,

    UNIQUE(user_id, provider)
);

-- Deliverable-specific export preferences
CREATE TABLE deliverable_export_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deliverable_id UUID NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    destination JSONB NOT NULL,  -- { channel_id, page_id, etc. }
    auto_export BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(deliverable_id, provider)
);

-- Export history for debugging and analytics
CREATE TABLE export_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deliverable_version_id UUID NOT NULL REFERENCES deliverable_versions(id),
    provider TEXT NOT NULL,
    destination JSONB,
    status TEXT NOT NULL,  -- 'success', 'failed', 'pending'
    error_message TEXT,
    external_id TEXT,  -- Slack message ts, Notion page id, etc.
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### MCP-Based Export Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Review Surface  │────▶│ MCP Client      │────▶│ MCP Server      │
│ [Slack] button  │     │ Layer           │     │ (Slack/Notion)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │ External API    │
         │                       │              │ (Slack, Notion) │
         │                       │              └─────────────────┘
         │                       ▼
         │              ┌─────────────────┐
         │              │ Export Log      │
         │              │ (audit trail)   │
         │              └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Check Auth      │
│ (OAuth token?)  │
└─────────────────┘
         │
    ┌────┴────┐
    │ Yes     │ No
    ▼         ▼
  MCP Call   OAuth Flow
             then MCP Call
```

### Format Conversion

MCP servers typically handle format conversion internally, but we may need conversion for:

| Scenario | Conversion | Handler |
|----------|------------|---------|
| Slack MCP | Markdown → mrkdwn | MCP server handles |
| Notion MCP | Markdown → Blocks | MCP server handles |
| Email (native) | Markdown → HTML | Our FormatConverter |
| Download | Markdown → PDF | Our FormatConverter |

```python
# api/services/format_converter.py
# Only needed for non-MCP exports (email, download)

class FormatConverter:
    @staticmethod
    def markdown_to_html(content: str) -> str:
        """Convert markdown to HTML for email."""
        pass

    @staticmethod
    def markdown_to_pdf(content: str) -> bytes:
        """Convert markdown to PDF for download."""
        pass
```

---

## MCP as Primary Integration Stack

### Why MCP?

| Factor | Benefit |
|--------|---------|
| **Leverage ecosystem** | Slack, Notion MCP servers already exist and are maintained |
| **Reduced maintenance** | MCP server maintainers handle API changes |
| **Industry alignment** | Building on emerging standard vs. proprietary |
| **Bidirectional** | YARNNN can also expose MCP server |
| **User portability** | Users can reuse MCP configs from Claude Desktop |

### MCP Server Ecosystem

| Platform | MCP Server | Status | Notes |
|----------|------------|--------|-------|
| Slack | `@modelcontextprotocol/server-slack` | ✅ Stable | Post messages, read channels |
| Notion | `@notionhq/notion-mcp-server` | ✅ Stable | Pages, databases |
| Google Drive | `@anthropics/google-drive-mcp` | ⚠️ Beta | Files, search |
| GitHub | `@modelcontextprotocol/server-github` | ✅ Stable | Issues, PRs |
| Linear | `linear-mcp-server` | ⚠️ Community | Issues, projects |

### MCP Client Architecture

#### Technical Implementation (Validated Feb 2026)

Based on research into the MCP ecosystem:

**SDK**: Official `mcp` Python package (v1.x stable, PyPI)
```bash
pip install "mcp[cli]"
```

**Transport**: Stdio (subprocess) - the standard pattern used by Claude Desktop
- MCP servers run as **subprocesses** communicating via stdin/stdout
- No separate service deployment needed
- Official servers (`@modelcontextprotocol/server-slack`, `@notionhq/notion-mcp-server`) are Node.js packages
- Both can be spawned from Python using `npx`

**Token Passing**: Environment variables to subprocess
- Slack: `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID`
- Notion: `AUTH_TOKEN` (internal integration token)

**Render Compatibility**: ✅ Verified
- Node.js available on Render (confirmed via existing `yarnnn-mcp-server` service)
- `npx` can be called from Python services

#### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     YARNNN API (FastAPI)                     │
├─────────────────────────────────────────────────────────────┤
│  MCPClientManager                                            │
│  - Spawns MCP servers as subprocesses (stdio transport)     │
│  - Passes decrypted tokens via env vars                      │
│  - Manages client sessions per user+provider                 │
└─────────────────────────────────────────────────────────────┘
         │                              │
         │ subprocess (npx)             │ subprocess (npx)
         ▼                              ▼
┌─────────────────┐          ┌─────────────────┐
│ server-slack    │          │ notion-mcp-server│
│ (Node.js)       │          │ (Node.js)        │
│                 │          │                  │
│ env:            │          │ env:             │
│ SLACK_BOT_TOKEN │          │ AUTH_TOKEN       │
│ SLACK_TEAM_ID   │          │                  │
└─────────────────┘          └─────────────────┘
         │                              │
         ▼                              ▼
    Slack API                      Notion API
```

#### Implementation

```python
# api/integrations/core/client.py

from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClientManager:
    """Manages MCP server connections via stdio subprocess transport."""

    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._exit_stacks: dict[str, AsyncExitStack] = {}

    async def get_session(
        self,
        user_id: str,
        provider: str,
        env: dict[str, str]
    ) -> ClientSession:
        """Get or create MCP client session for user+provider."""
        key = f"{user_id}:{provider}"

        if key not in self._sessions:
            # Determine command based on provider
            server_commands = {
                "slack": ["npx", "@modelcontextprotocol/server-slack"],
                "notion": ["npx", "@notionhq/notion-mcp-server", "--transport", "stdio"],
            }

            cmd = server_commands.get(provider)
            if not cmd:
                raise ValueError(f"Unknown provider: {provider}")

            server_params = StdioServerParameters(
                command=cmd[0],
                args=cmd[1:],
                env=env  # Tokens passed here
            )

            exit_stack = AsyncExitStack()
            self._exit_stacks[key] = exit_stack

            stdio_transport = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            session = await exit_stack.enter_async_context(
                ClientSession(stdio_transport[0], stdio_transport[1])
            )
            await session.initialize()

            self._sessions[key] = session

        return self._sessions[key]

    async def export_to_slack(
        self,
        user_id: str,
        channel: str,
        content: str,
        bot_token: str,
        team_id: str
    ) -> dict:
        """Export content to Slack via MCP."""
        session = await self.get_session(
            user_id,
            "slack",
            env={
                "SLACK_BOT_TOKEN": bot_token,
                "SLACK_TEAM_ID": team_id
            }
        )
        result = await session.call_tool(
            "slack_post_message",
            {"channel": channel, "text": content}
        )
        return result

    async def close_session(self, user_id: str, provider: str):
        """Close a specific session."""
        key = f"{user_id}:{provider}"
        if key in self._exit_stacks:
            await self._exit_stacks[key].aclose()
            del self._exit_stacks[key]
            del self._sessions[key]

    async def close_all(self):
        """Close all sessions (for cleanup)."""
        for key in list(self._exit_stacks.keys()):
            await self._exit_stacks[key].aclose()
        self._sessions.clear()
        self._exit_stacks.clear()
```

### YARNNN as MCP Server (Bidirectional)

YARNNN can expose its own MCP server for other AI tools:

```python
# api/mcp/server.py

from mcp import Server, Tool

class YarnnnMCPServer(Server):
    """MCP server exposing YARNNN context and capabilities."""

    tools = [
        Tool(
            name="get_memories",
            description="Get user's memories for context",
            parameters={"scope": "string"}
        ),
        Tool(
            name="get_deliverable",
            description="Get deliverable content",
            parameters={"deliverable_id": "string"}
        ),
        Tool(
            name="list_deliverables",
            description="List user's deliverables",
            parameters={"status": "string?"}
        ),
    ]

    async def handle_get_memories(self, scope: str) -> list:
        """Return user memories for the given scope."""
        pass

    async def handle_get_deliverable(self, deliverable_id: str) -> dict:
        """Return deliverable content."""
        pass
```

This enables:
- Claude Desktop accessing YARNNN context
- Other AI tools leveraging YARNNN's memory system
- Custom workflows via MCP composition

### Managed vs User-Configured MCP

**Managed MCP (Default Experience):**
- User clicks "Connect Slack"
- YARNNN handles OAuth, stores token
- YARNNN manages MCP server connection
- User doesn't need to know it's MCP

**User-Configured MCP (Power Users):**
- Advanced users can add custom MCP servers
- Bring-your-own integrations
- Phase 2 feature

### MCP Implementation Phases

1. **Phase 1**: MCP client layer + Slack integration
2. **Phase 2**: Notion integration via MCP
3. **Phase 3**: YARNNN MCP server (expose context)
4. **Phase 4**: User-configured MCP servers

---

## Deliverable Type Mapping

Each deliverable type has recommended export destinations:

| Type | Primary | Secondary | Notes |
|------|---------|-----------|-------|
| `status_report` | Slack | Email | Team channels |
| `stakeholder_update` | Email | Slack | External recipients |
| `research_brief` | Notion | Slack | Reference docs |
| `meeting_summary` | Notion | Slack | Wiki pages |
| `client_proposal` | Google Docs | Email | Collaboration |
| `performance_self_assessment` | Google Docs | Email | Formal docs |
| `newsletter_section` | Email | Notion | Distribution |
| `changelog` | Notion | Slack | Dev docs |
| `one_on_one_prep` | Email | Calendar | Time-bound |
| `board_update` | Email | Google Docs | Formal |
| `custom` | Copy | Any | User decides |

These mappings inform:
1. Default export button order in UI
2. Suggested destinations when setting up new deliverables
3. Auto-export configuration options

---

## Review Surface Scope

The review surface (DeliverableReviewSurface) will be enhanced minimally:

### In Scope

- Markdown rendering (view-only)
- Copy to clipboard (formatted)
- Export action bar (Slack, Notion, Email, Download)
- Section navigation for long documents
- "Refine with TP" quick action

### Out of Scope

- Rich text editing
- Formatting toolbar
- Collaborative editing
- Document version branching
- Inline text selection/modification

---

## Implementation Phases

### Phase 1: Foundation + MCP Client (Week 1-2)

- [ ] MCP client layer (`api/services/mcp_client.py`)
- [ ] `user_integrations` table migration
- [ ] Markdown preview component
- [ ] Copy-to-clipboard with formatting
- [ ] Export action bar UI component

### Phase 2: Slack via MCP (Week 3-4)

- [ ] Slack OAuth flow
- [ ] Slack MCP server integration (`@modelcontextprotocol/server-slack`)
- [ ] Channel selector component
- [ ] Export log table and tracking
- [ ] End-to-end Slack export flow

### Phase 3: Notion via MCP (Week 5-6)

- [ ] Notion OAuth flow
- [ ] Notion MCP server integration (`@notionhq/notion-mcp-server`)
- [ ] Page/database selector component
- [ ] End-to-end Notion export flow

### Phase 4: YARNNN MCP Server (Week 7-8)

- [ ] Expose YARNNN as MCP server
- [ ] Tools: `get_memories`, `get_deliverable`, `list_deliverables`
- [ ] Documentation for Claude Desktop users
- [ ] Test with external MCP clients

### Phase 5: Polish & Auto-Export (Week 9-10)

- [ ] Deliverable export preferences UI
- [ ] Auto-export on approval option
- [ ] Export history view
- [ ] Error handling and retry logic

### Phase 6: User-Configured MCP (Future)

- [ ] UI for adding custom MCP servers
- [ ] MCP server discovery/validation
- [ ] Power user documentation

---

## Security Considerations

### Token Storage

- OAuth tokens encrypted at rest
- Refresh tokens stored separately
- Token rotation on refresh
- Immediate revocation on disconnect

### Scopes

Request minimum OAuth scopes:

| Provider | Scopes |
|----------|--------|
| Slack | `chat:write`, `channels:read` |
| Notion | `read_content`, `insert_content` |
| Google | `drive.file` |

### Audit Trail

All exports logged with:
- Timestamp
- User ID
- Deliverable version
- Destination
- Success/failure status

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Export adoption | >60% of approved versions exported | `export_log` query |
| Integration connection rate | >40% of active users | `user_integrations` count |
| Export success rate | >95% | `export_log` status |
| Time from approval to export | <10 seconds | UX timing |

---

## Alternatives Considered

### Alternative 1: Build Rich Editor

Build markdown editor with formatting, preview, and collaboration.

**Rejected because:**
- Contradicts supervisor model
- Competes with Notion/Docs on their turf
- High development cost for non-differentiated feature

### Alternative 2: Native API Integrations (No MCP)

Build direct integrations with Slack API, Notion API, etc.

**Rejected because:**
- Duplicates work that MCP servers already do
- Higher maintenance burden (API changes, auth flows)
- Misses industry convergence toward MCP
- Less extensible for future integrations

### Alternative 3: MCP User-Managed Only

Let users configure their own MCP servers, no managed experience.

**Rejected because:**
- Poor default experience for non-technical users
- Requires MCP knowledge and setup
- Higher friction to first export

### Alternative 4: Download-Only

Only support local downloads (PDF, Markdown, DOCX).

**Rejected because:**
- High friction (download → upload to Slack)
- Doesn't meet users where they work
- Misses automation opportunity (auto-export)

---

## References

- [docs/analysis/integration-strategy.md](../analysis/integration-strategy.md) - Detailed analysis
- [docs/workflows/DELIVERABLE-WORKFLOW.md](../workflows/DELIVERABLE-WORKFLOW.md) - Phase 4 gap
- [docs/ESSENCE.md](../ESSENCE.md) - Core principles
- [Slack Block Kit](https://api.slack.com/block-kit)
- [Notion API](https://developers.notion.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

## Changelog

### 2026-02-06: Technical Validation & Implementation Start

- Validated MCP SDK availability (`mcp` package v1.x on PyPI)
- Confirmed subprocess/stdio transport as standard pattern
- Verified Node.js/npx availability on Render
- Created database migration `023_integrations.sql`:
  - `user_integrations` - OAuth token storage
  - `deliverable_export_preferences` - Per-deliverable export config
  - `export_log` - Audit trail
- Updated MCPClientManager implementation with real SDK patterns

### 2026-02-06: Initial Draft

- Established integration-first architecture decision
- **MCP as primary integration stack** (not just escape hatch)
- Prioritized: MCP client → Slack via MCP → Notion via MCP → YARNNN MCP server
- Defined data model for integrations
- Scoped review surface enhancements
- Added bidirectional MCP (YARNNN as both client and server)
