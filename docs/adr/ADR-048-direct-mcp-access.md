# ADR-048: Direct MCP Access for Thinking Partner

> **Status**: Accepted
> **Created**: 2026-02-12
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-025 (Claude Code Alignment), ADR-039 (Agentic Platform Operations), ADR-047 (Platform Integration Validation)

---

## Context

### The Problem

TP (Thinking Partner) was accessing platform integrations (Slack, Notion, Gmail) through wrapper actions in the Execute primitive:

```
TP → Execute(action="platform.send") → wrapper code → MCP subprocess
TP → Execute(action="platform.search") → wrapper code → MCP subprocess
```

This created several issues:
1. **Indirection**: Every new MCP capability required implementing a wrapper
2. **Inconsistency**: TP couldn't use MCP tools that we hadn't explicitly wrapped
3. **Divergence from Claude Code**: Claude Code exposes MCP tools directly; we were hiding them

### The Architectural Question

From discussion with stakeholder:
> "integrations are just a data-source, the metaphorical mapping to Claude Code for file system and repo to our entities including platforms"

This reframing positions platforms as **first-class entities** TP should naturally work with, not external services to carefully broker.

### Reference: Claude Code Pattern

Claude Code's architecture:
- **Tools (primitives)**: Bash, Read, Write, Edit, Grep, Glob, etc.
- **MCP tools (external)**: `mcp__slack__*`, `mcp__notion__*` - directly callable
- **Skills (workflows)**: `/commit`, `/review-pr` - instructions that orchestrate tools
- **Subagents (isolation)**: For parallel work or context isolation, NOT task specialization

Key insight: MCP tools are treated as **first-class tools**, not hidden behind abstractions.

---

## Decision

**TP gets direct access to MCP tools**, following Claude Code's pattern.

### What Changes

**Before (Option B - wrappers):**
```
TP tools:
├── 7 primitives (Read, Write, Edit, Search, List, Execute, Clarify)
├── Execute wraps: platform.send, platform.search
└── MCP hidden from TP
```

**After (Option A - direct access):**
```
TP tools:
├── 7 primitives (Read, Write, Edit, Search, List, Execute, Clarify)
├── Execute for YARNNN orchestration only (deliverable.generate, platform.sync, etc.)
├── mcp__slack__* tools (direct)
├── mcp__notion__* tools (direct)
└── Platform helper tools (list_integrations, list_platform_resources, etc.)
```

### Execute Primitive Scope (What Stays)

Execute remains for **YARNNN-specific orchestration**, not MCP wrapping:

| Action | Purpose |
|--------|---------|
| `deliverable.generate` | Trigger content generation pipeline |
| `deliverable.approve` | Approve pending version |
| `deliverable.schedule` | Update schedule |
| `platform.sync` | Sync data into ephemeral_context |
| `platform.publish` | Publish deliverable to platform |
| `work.run` | Execute background work |
| `memory.extract` | Extract memories from conversation |

### What Gets Removed from Execute

| Removed | Replaced By |
|---------|-------------|
| `platform.send` | `mcp__slack__slack_post_message`, `mcp__notion__notion-create-comment` |
| `platform.search` | `mcp__notion__notion-search`, `mcp__slack__slack_list_channels` |

### MCP Tool Availability

TP gains access to MCP tools based on user's connected integrations:

**Slack** (when connected):
- `mcp__slack__slack_post_message`
- `mcp__slack__slack_list_channels`
- `mcp__slack__slack_get_users`
- `mcp__slack__slack_get_channel_history`

**Notion** (when connected):
- `mcp__notion__notion-search`
- `mcp__notion__notion-create-comment`
- `mcp__notion__notion-create-pages`
- `mcp__notion__notion-fetch`
- `mcp__notion__notion-update-page`

**Gmail**: Uses direct API (not MCP), accessed via `send_notification` tool.

---

## Implementation

### Phase 1: Remove Wrappers

1. Remove `platform.send` and `platform.search` from Execute's `ACTION_CATALOG`
2. Remove `_handle_platform_send`, `_handle_platform_search` handlers
3. Remove `_send_slack_message`, `_send_notion_content`, `_search_slack`, `_search_notion` functions
4. Remove `_search_platform_live` from refs.py

### Phase 2: Expose MCP Tools

1. Modify TP tool list construction to include MCP tools for connected platforms
2. Add MCP guidance to TP system prompt (quirks, parameter names)
3. Keep platform_registry for quirks documentation (used in system prompt)

### Phase 3: Update Documentation

1. Update CHANGELOG with architecture change
2. Update QUIRKS.md to reference MCP tools directly
3. Update platform_registry capabilities to show MCP tool names

---

## System Prompt Changes

Add to TP system prompt:

```markdown
## Platform MCP Tools

When platforms are connected, you have direct access to their MCP tools.

### Slack (mcp__slack__*)

**mcp__slack__slack_post_message**
- `channel_id`: Use C... (channel ID), #name, U... (user ID for DM), or resolve "self"
- `text`: Message content
- Note: @mentions like @me don't work. Use list_integrations to get authed_user_id for "self"

**mcp__slack__slack_list_channels** - Lists all channels (use to find channel IDs)

**mcp__slack__slack_get_users** - Lists all users (use to find user IDs for DMs)

### Notion (mcp__notion__*)

**mcp__notion__notion-search**
- `query`: Search term
- `query_type`: "internal" (default)
- Returns page IDs you can use with other tools

**mcp__notion__notion-create-comment**
- `parent`: `{page_id: "uuid"}`
- `rich_text`: `[{type: "text", text: {content: "..."}}]`
- Page must be shared with the integration

**mcp__notion__notion-fetch**
- `id`: Page UUID or URL
- Returns page content as Markdown

### Gmail

Gmail uses direct API, not MCP. Use `send_notification` for emails.
```

---

## Consequences

### Positive

1. **Aligned with Claude Code** - Proven pattern, ecosystem compatibility
2. **Maximum flexibility** - TP can use any MCP capability
3. **Less code to maintain** - No wrapper handlers
4. **Transparency** - User sees what tools TP is calling
5. **Extensibility** - New MCP tools automatically available

### Negative

1. **Larger tool list** - More tools in TP's prompt
2. **Quirks in prompt** - Must teach TP about MCP parameter names
3. **Migration work** - Remove existing wrappers

### Mitigations

- Platform registry still documents quirks for system prompt
- Platform helper tools (`list_integrations`, `list_platform_resources`) remain for discovery
- Skills can package common patterns (e.g., "DM user" skill)

---

## UI Consideration

When TP calls an MCP tool, the chat interface should show a platform icon to indicate external action. This maintains transparency about what TP is doing.

---

## Discipline

This change follows established principles:

1. **Singular approach** - Remove dual patterns (Execute wrappers AND MCP)
2. **Version control** - Incremental commits with clear messages
3. **Documentation** - ADRs, CHANGELOG, QUIRKS updated together

---

## See Also

- [ADR-025: Claude Code Agentic Alignment](ADR-025-claude-code-agentic-alignment.md)
- [ADR-039: Agentic Platform Operations](ADR-039-agentic-platform-operations.md)
- [ADR-047: Platform Integration Validation](ADR-047-platform-integration-validation.md)
- [Integration Changelog](../integrations/CHANGELOG.md)
- [Platform Quirks Guide](../integrations/QUIRKS.md)
