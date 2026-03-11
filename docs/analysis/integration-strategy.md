# Integration Strategy Analysis

> **Status**: Analysis Draft
> **Last Updated**: 2026-02-06
> **Related**: ADR-001 (Foundational Principles), ADR-005 (Memory Architecture), ESSENCE.md

---

## Executive Summary

This analysis evaluates YARNNN's strategy for third-party integrations (Slack, Notion, etc.) versus building in-app rich editing features. Based on first principles analysis of YARNNN's foundational documents and the supervisor model design, **integrations are the strategic priority**.

---

## First Principles Analysis

### Core Design Principles (from ESSENCE.md & ADRs)

| Principle | Implication for Strategy |
|-----------|--------------------------|
| **Supervisor, not operator** | Users oversee AI work, don't manually edit outputs in YARNNN |
| **Professional work tool, not engagement platform** | Don't build features that keep users in-app longer than needed |
| **Meet users where they are** | Push outputs to where users already work (Slack, Notion, email) |
| **Two-layer memory** | User-scoped memories are portable across contexts |
| **Quality through iteration** | Improvement happens through TP feedback cycles, not manual editing |

### The Fundamental Question

> Should YARNNN invest in rich editing features (markdown editor, formatting tools, document collaboration) OR push outputs to tools users already use?

**Answer: Integrations.** Here's why:

1. **The supervisor model** - Users set up agents, review outputs, and approve/refine via conversation with TP. They don't need to be document editors.

2. **Quality loop is conversational** - When output needs improvement, user gives feedback to TP ("make it more concise", "add metrics section"). TP refines. This is fundamentally different from manually editing.

3. **Exit velocity matters** - A successful session ends with the user getting their agent OUT of YARNNN into their workflow. Friction to export = failed experience.

4. **Competitive positioning** - Notion is a document tool. Slack is a communication tool. YARNNN is an intelligence layer. Don't compete on document editing.

---

## Current State Assessment

### Review Surface Capabilities

| Feature | Current State | Needed for MVP |
|---------|--------------|----------------|
| View agent content | ✅ Plain text display | ✅ |
| Basic formatting | ❌ None | ⚠️ Markdown preview |
| Rich text editing | ❌ None | ❌ Not needed |
| Export (copy) | ✅ Implicit (select + copy) | ⚠️ One-click copy |
| Export (download) | ❌ Not implemented | ⚠️ Phase 2 |
| Export (email) | ✅ Email to self | ✅ |
| Export (Slack) | ❌ Not implemented | 🎯 Priority |
| Export (Notion) | ❌ Not implemented | 🎯 Priority |

### Agent Workflow (Phase 4 Gap)

From `DELIVERABLE-WORKFLOW.md`, Phase 4 "Post-Approval Actions" shows export options but is marked **❌ Not implemented**:

```
┌─────────────────────────────────────────────────────┐
│ ✓ Approved                                          │
├─────────────────────────────────────────────────────┤
│ Your Weekly Status Report is ready.                 │
│                                                     │
│ [Copy to Clipboard]  [Download PDF]  [Send Email]   │
│                                                     │
│ Next version: Monday, Feb 10 at 9:00 AM             │
└─────────────────────────────────────────────────────┘
```

**Proposed expansion:**
```
│ [Copy]  [Slack]  [Notion]  [Email]  [Download]      │
```

---

## Integration Priority Matrix

### Tier 1: Essential (P1)

| Integration | Why | Agent Types | User Story |
|-------------|-----|-------------------|------------|
| **Slack** | Most common professional communication tool. Low friction, high value. | All types | "Send my status report to #team-updates" |
| **Notion** | Popular for knowledge bases, project tracking. Many users already store documents there. | research_brief, meeting_summary, changelog | "Add this meeting summary to my Engineering Decisions wiki" |

### Tier 2: Strategic (P2)

| Integration | Why | Agent Types | User Story |
|-------------|-----|-------------------|------------|
| **Google Docs** | Common for collaborative document editing | client_proposal, board_update | "Create a Google Doc I can share with my board" |
| **Email (enhanced)** | Direct delivery to external recipients | stakeholder_update, board_update | "Email this directly to sarah@client.com" |

### Tier 3: Future (P3)

| Integration | Why | Agent Types | User Story |
|-------------|-----|-------------------|------------|
| **Microsoft 365** | Enterprise market | All | "Send to my OneDrive" |
| **Linear/Jira** | Dev tool integration | changelog, status_report | "Create a Linear issue from this" |
| **Calendar** | Scheduling integration | one_on_one_prep | "Add to my calendar with prep notes" |

---

## MCP as Integration Stack

> **Strategic direction**: Use MCP (Model Context Protocol) as the preferred tech stack for implementing Slack, Notion, and other integrations.

### What is MCP?

Model Context Protocol is Anthropic's standardized protocol for connecting AI assistants to external tools and data sources. Key ecosystem players:

- **Anthropic** - Creator and primary driver of MCP spec
- **Claude Desktop** - Native MCP client support
- **OpenAI/ChatGPT** - Converging toward similar interoperability patterns
- **Community** - Growing ecosystem of MCP servers for popular services

### Why MCP as Our Integration Stack

| Factor | Benefit |
|--------|---------|
| **Leverage existing servers** | Slack, Notion, Google MCP servers already exist - don't rebuild |
| **Future-proof** | As MCP ecosystem grows, we get integrations "for free" |
| **Industry alignment** | Building on emerging standard vs. proprietary integrations |
| **Reduced maintenance** | MCP server maintainers handle API changes, auth flows |
| **User portability** | Users can bring MCP configs from Claude Desktop |
| **Bidirectional value** | YARNNN can also expose MCP server for other AI tools |

### MCP Architecture Approaches

**Option A: MCP Client Only**
- YARNNN acts as MCP client, connecting to external MCP servers
- Users configure MCP servers (Slack, Notion, etc.)
- YARNNN invokes tools via MCP protocol
- Pros: Maximum leverage of ecosystem, minimal integration code
- Cons: Requires user to configure MCP servers, less seamless UX

**Option B: Managed MCP (Recommended)**
- YARNNN manages MCP server connections for users
- Pre-configured MCP servers for priority integrations (Slack, Notion)
- OAuth flows handled by YARNNN, tokens passed to MCP servers
- Users get "one-click" integration experience
- Pros: Best UX, still leverages MCP ecosystem
- Cons: Need to host/manage MCP server instances

**Option C: Hybrid MCP + Native**
- Use MCP for some integrations, native for others
- Native where MCP servers are immature or missing
- MCP where servers are stable and feature-complete
- Pros: Flexibility, can ship faster for some integrations
- Cons: Two codepaths to maintain

**Recommendation**: **Option B (Managed MCP)**

Provide seamless UX where users click "Connect Slack" and YARNNN handles the MCP server setup behind the scenes. Users don't need to know it's MCP - they just get working integrations.

### MCP Server Ecosystem Status

| Platform | MCP Server | Maturity | Notes |
|----------|------------|----------|-------|
| **Slack** | `@modelcontextprotocol/server-slack` | ✅ Stable | Post messages, read channels |
| **Notion** | `@notionhq/notion-mcp-server` | ✅ Stable | Create/update pages, query databases |
| **Google Drive** | `@anthropics/google-drive-mcp` | ⚠️ Beta | File read/write, search |
| **GitHub** | `@modelcontextprotocol/server-github` | ✅ Stable | Issues, PRs, repos |
| **Linear** | `linear-mcp-server` | ⚠️ Community | Issues, projects |
| **Calendar** | Various | ⚠️ Varies | Google Calendar, Outlook |

### Implementation Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                        YARNNN                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              MCP Client Layer                        │    │
│  │  - Manages connections to MCP servers               │    │
│  │  - Routes tool calls from TP/Export flow            │    │
│  │  - Handles auth token injection                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│           ┌───────────────┼───────────────┐                 │
│           ▼               ▼               ▼                 │
│    ┌───────────┐   ┌───────────┐   ┌───────────┐           │
│    │ Slack MCP │   │ Notion MCP│   │ Drive MCP │           │
│    │  Server   │   │  Server   │   │  Server   │           │
│    └───────────┘   └───────────┘   └───────────┘           │
│           │               │               │                 │
└───────────┼───────────────┼───────────────┼─────────────────┘
            ▼               ▼               ▼
      ┌──────────┐   ┌──────────┐   ┌──────────┐
      │ Slack API│   │Notion API│   │Drive API │
      └──────────┘   └──────────┘   └──────────┘
```

### YARNNN as MCP Server (Bidirectional)

Beyond consuming MCP servers, YARNNN can **expose** an MCP server:

```python
# Other AI tools can access YARNNN context via MCP
class YarnnnMCPServer:
    tools = [
        "get_user_memories",      # Access user's memory bank
        "get_agent",        # Fetch agent content
        "list_agents",      # List user's agents
        "export_agent",     # Export in various formats
    ]
```

This enables:
- Claude Desktop users to access YARNNN context
- Other AI assistants to leverage YARNNN's memory system
- Power users to build custom workflows

### Migration Path

1. **Phase 1**: Implement MCP client layer
2. **Phase 2**: Integrate Slack MCP server (managed)
3. **Phase 3**: Integrate Notion MCP server (managed)
4. **Phase 4**: Expose YARNNN MCP server
5. **Phase 5**: Allow user-configured MCP servers (power users)

---

## Agent Type → Integration Mapping

Based on `api/services/agent_pipeline.py` and `web/components/modals/AgentSettingsModal.tsx`:

| Agent Type | Primary Export | Secondary Export | Notes |
|-----------------|----------------|------------------|-------|
| `status_report` | Slack | Email | Team-wide visibility |
| `stakeholder_update` | Email | Slack | Often external recipients |
| `research_brief` | Notion | Google Docs | Reference material |
| `meeting_summary` | Notion | Slack | Meeting follow-ups |
| `client_proposal` | Google Docs | Email | Needs collaboration |
| `performance_self_assessment` | Google Docs | Email | HR/formal document |
| `newsletter_section` | Email | Notion | Mass distribution |
| `changelog` | Notion | Slack | Developer docs |
| `one_on_one_prep` | Calendar | Email | Time-bound |
| `board_update` | Email | Google Docs | Formal, external |
| `custom` | Copy | Any | User decides |

---

## Minimum Viable Review Surface

Instead of building a rich editor, the review surface needs:

### Must Have

1. **Markdown preview** - Render content properly (headers, lists, links)
2. **One-click copy** - Copy formatted content to clipboard
3. **Quick actions bar** - Export buttons (Slack, Notion, Email)
4. **TP connection** - "Refine this" opens TP with context

### Nice to Have

4. **Section navigation** - Jump to sections in long documents
5. **Diff view** - Compare with previous version
6. **Inline comments** - Mark sections for TP feedback

### Explicitly NOT Building

- Rich text editing (bold, italic, etc.)
- Formatting toolbar
- Collaborative editing
- Document version branching
- In-app document storage/organization

---

## Implementation Phases

### Phase 1: Foundation (Current Sprint)

1. **Markdown preview** in AgentReviewSurface
2. **Copy to clipboard** button with formatting
3. **Email enhancement** - Current email flow polish

### Phase 2: Slack Integration

1. **OAuth flow** for Slack workspace connection
2. **Channel selector** in export flow
3. **Message formatting** (Slack blocks/mrkdwn)
4. **Default channel per agent** (optional setting)

### Phase 3: Notion Integration

1. **OAuth flow** for Notion workspace connection
2. **Page/database selector**
3. **Notion block formatting**
4. **Template mapping** (agent type → Notion template)

### Phase 4: MCP Exploration

1. **MCP server** exposing YARNNN context
2. **Documentation** for power users
3. **Evaluate adoption** before deeper investment

---

## Architecture Considerations

### Integration Data Model

```sql
-- User's connected integrations
CREATE TABLE user_integrations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    provider TEXT NOT NULL,  -- 'slack', 'notion', 'google'
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    metadata JSONB,  -- workspace_id, etc.
    created_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
);

-- Agent export preferences
CREATE TABLE agent_export_preferences (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    provider TEXT NOT NULL,
    destination JSONB,  -- { channel: "#team-updates" } or { page_id: "..." }
    auto_export BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ
);
```

### Export Flow Architecture

```
User clicks [Slack] button
         │
         ▼
┌─────────────────────────────┐
│ Check user_integrations     │
│ for Slack connection        │
└─────────────────────────────┘
         │
    ┌────┴────┐
    │ Has     │ No
    │ Token?  │───▶ OAuth flow → Save token → Return
    │         │
    └────┬────┘
         │ Yes
         ▼
┌─────────────────────────────┐
│ Show channel selector       │
│ (fetch from Slack API)      │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Format content for Slack    │
│ (markdown → mrkdwn)         │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Post message via Slack API  │
│ Save export preference      │
└─────────────────────────────┘
```

---

## Success Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Export rate** | % of approved agents exported | >60% |
| **Integration adoption** | % of users with ≥1 integration | >40% |
| **Time to export** | Seconds from approval to export | <10s |
| **Return rate** | Users returning after first export | >50% |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| **OAuth complexity** | Use established libraries (NextAuth.js integrations) |
| **Token refresh failures** | Graceful degradation, re-auth prompts |
| **API rate limits** | Queue exports, batch where possible |
| **Format conversion bugs** | Comprehensive test suite for markdown→format conversions |
| **MCP evolving standard** | Monitor spec changes, don't over-invest until stable |

---

## Next Steps

1. [ ] Create ADR-026 for Integration Architecture decision
2. [ ] Prototype Slack OAuth flow
3. [ ] Design export action bar component
4. [ ] Research MCP server implementation patterns

---

## Appendix: Competitive Analysis

### How Others Handle This

| Product | Approach | Lesson for YARNNN |
|---------|----------|-------------------|
| **Notion AI** | Native (they ARE the document) | Different problem space |
| **Jasper** | Export-focused (Copy, Download, Integrations) | Similar model, validates approach |
| **Copy.ai** | Download templates, minimal editing | Similar model |
| **ChatGPT** | Copy + share link | Low friction, but no workflow integration |
| **ClawdBot** | Slack-native, outputs where users already are | Validates Slack-first |

---

## Changelog

### 2026-02-06: Initial Analysis
- Documented first principles evaluation
- Prioritized Slack → Notion integration path
- Defined minimum viable review surface
- Added MCP consideration per user feedback
