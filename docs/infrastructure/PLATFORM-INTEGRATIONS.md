# Platform Integrations Architecture

> Backend infrastructure documentation for YARNNN platform integrations.

## Overview

YARNNN integrates with four external platforms:

| Platform | OAuth Provider | Transport | TP Tools | Deliverable Source | Deliverable Export |
|----------|---------------|-----------|----------|-------------------|-------------------|
| Slack | slack | MCP Gateway | Yes | Yes | Yes |
| Notion | notion | Direct API | Yes | Yes | Yes |
| Gmail | google | Direct API | Yes | Yes | Yes |
| Calendar | google | Direct API | Yes | Yes | Yes |

## Architecture

```
                          ┌─────────────────────────────────────┐
                          │           yarnnn-api                 │
                          │            (Python)                  │
                          │                                      │
                          │  ┌────────────────────────────────┐  │
                          │  │     Platform Router            │  │
                          │  │                                │  │
                          │  │  Routes by provider:           │  │
                          │  │  ├─ slack    → MCP Gateway     │  │
                          │  │  ├─ notion   → Direct API      │  │
                          │  │  ├─ gmail    → Direct API      │  │
                          │  │  └─ calendar → Direct API      │  │
                          │  └────────────────────────────────┘  │
                          │              │                       │
                          │              │ Slack, Notion         │
                          │              ▼                       │
                          │  ┌────────────────────────────────┐  │
                          │  │    mcp_gateway.py              │  │
                          │  │    (HTTP client)               │  │
                          │  └────────────┬───────────────────┘  │
                          │               │                      │
                          └───────────────┼──────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    yarnnn-mcp-gateway                           │
│                      (Node.js/Express)                          │
│                                                                 │
│  ┌─────────────────────────┐                                    │
│  │ @modelcontextprotocol/  │  (Notion removed: uses Direct API) │
│  │   server-slack          │                                    │
│  └─────────────────────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Provider Details

### Slack (MCP Gateway)

**OAuth Config**: [oauth.py](../../api/integrations/core/oauth.py)
```python
scopes = [
    "chat:write",        # Post messages
    "channels:read",     # List public channels
    "channels:history",  # Read public messages
    "channels:join",     # Auto-join for import
    "groups:read",       # List private channels
    "groups:history",    # Read private messages
    "users:read",        # Get user info
    "im:write",          # DM channels
]
```

**TP Tools** (defined in [platform_tools.py](../../api/services/platform_tools.py)):
- `platform_slack_send_message` - Send DM to user
- `platform_slack_list_channels` - List available channels

**Data Flow**:
```
TP calls tool → platform_tools.py → mcp_gateway.py (HTTP) → yarnnn-mcp-gateway → Slack API
```

---

### Notion (Direct API)

**OAuth Config**: Uses Notion's built-in OAuth (no scopes needed)

**TP Tools**:
- `platform_notion_search` - Search pages/databases
- `platform_notion_create_comment` - Add comments

**Why Direct API (not MCP)**:
- `@notionhq/notion-mcp-server` requires internal `ntn_...` integration tokens, not OAuth tokens
- Notion's hosted MCP (`mcp.notion.com`) manages its own OAuth sessions — no way to inject ours
- Direct calls to `api.notion.com` work correctly with YARNNN's OAuth tokens
- `NotionAPIClient` (`api/integrations/core/notion_client.py`) handles all Notion REST operations

**Data Flow**:
```
TP tool call → platform_tools.py → NotionAPIClient → api.notion.com
                              ↓
Platform sync → platform_worker._sync_notion() → NotionAPIClient → api.notion.com
                              ↓
Deliverable pipeline → _fetch_notion_data() → NotionAPIClient → api.notion.com
```

---

### Gmail (Direct API)

**OAuth Config**: Part of unified Google OAuth
```python
scopes = [
    "https://www.googleapis.com/auth/gmail.readonly",   # Read emails for context
    "https://www.googleapis.com/auth/gmail.send",       # Send deliverables
    "https://www.googleapis.com/auth/gmail.compose",    # Create drafts
    "https://www.googleapis.com/auth/gmail.modify",     # Labels, archive
]
```

**TP Tools** (defined in [platform_tools.py](../../api/services/platform_tools.py)):
- `platform_gmail_search` - Search messages with Gmail query syntax
- `platform_gmail_get_thread` - Get full email thread
- `platform_gmail_send` - Send email
- `platform_gmail_create_draft` - Create draft for user review

**Used For**:
- **TP Tools**: Direct email search, reading threads, sending/drafting
- **Deliverable Sources**: Fetch emails for inbox_summary, thread_summary
- **Deliverable Export**: Send/draft emails via GmailExporter

**Data Flow**:
```
TP tool call → platform_tools.py → Direct Google Gmail API v1
                              ↓
Deliverable pipeline → _fetch_gmail_data() → Google Gmail API v1
```

**Why Direct API (not MCP)**:
- No official Google MCP server
- Token refresh handling already in Python
- Full control over API calls and error handling

---

### Calendar (Direct API)

**OAuth Config**: Shares Google OAuth with Gmail
```python
scopes = [
    "https://www.googleapis.com/auth/calendar.readonly",         # List calendars
    "https://www.googleapis.com/auth/calendar.events.readonly",  # Read events
    "https://www.googleapis.com/auth/calendar.events",           # Create/edit events
]
```

**TP Tools** (defined in [platform_tools.py](../../api/services/platform_tools.py)):
- `platform_calendar_list_events` - List upcoming events with time filters
- `platform_calendar_get_event` - Get event details with attendees
- `platform_calendar_create_event` - Create new calendar events

**Used For**:
- **TP Tools**: Query calendar, create events
- **Deliverable Sources**: Fetch events for meeting_prep, weekly_calendar_preview
- **Cross-Platform Context**: Connect meeting attendees to Slack/Gmail history

**Data Flow**:
```
TP tool call → platform_tools.py → Direct Google Calendar API v3
                              ↓
Deliverable pipeline → _fetch_calendar_data() → Google Calendar API v3
```

**Key Implementation** ([deliverable_pipeline.py:635-760](../../api/services/deliverable_pipeline.py)):
```python
async def _fetch_calendar_data(...):
    # Get fresh access token (with refresh if needed)
    access_token = await get_valid_google_token(integration)

    # Fetch events
    response = await client.get(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": True,  # Expand recurring
            "orderBy": "startTime",
        }
    )
```

---

## OAuth Provider Mapping

The backend stores integrations by their OAuth provider name:

| Frontend Display | Backend Provider | OAuth Flow |
|-----------------|------------------|------------|
| Slack | `slack` | Slack OAuth |
| Gmail | `gmail` or `google` | Google OAuth |
| Notion | `notion` | Notion OAuth |
| Calendar | `google` or `gmail`* | Google OAuth (same as Gmail) |

*Calendar uses the Google integration - no separate OAuth flow

**Legacy Note**: Older users have `gmail` provider, newer users get `google`. Backend handles both.

---

## Token Management

### Slack & Notion
- Tokens don't expire
- No refresh needed

### Google (Gmail + Calendar)
- Access tokens expire in 1 hour
- Refresh tokens stored encrypted
- Auto-refresh in `get_valid_google_token()`

```python
# In deliverable_pipeline.py
async def get_valid_google_token(integration: dict) -> str:
    """Get a valid Google access token, refreshing if needed."""
    metadata = integration.get("metadata", {})
    expires_at = metadata.get("expires_at")

    if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
        # Token expired, refresh it
        refresh_token = token_manager.decrypt(integration["refresh_token_encrypted"])
        new_token = await refresh_google_token(refresh_token)
        # Update database with new token
        ...

    return token_manager.decrypt(integration["access_token_encrypted"])
```

---

## Adding New Platforms

### MCP Gateway Route (Slack pattern)
1. Add OAuth config to [oauth.py](../../api/integrations/core/oauth.py)
2. Add to [platform_registry.py](../../api/integrations/platform_registry.py)
3. Add MCP server to `yarnnn-mcp-gateway/src/mcp/client-manager.ts`
4. Define TP tools in [platform_tools.py](../../api/services/platform_tools.py)

### Direct API Route (Gmail/Calendar/Notion pattern)
1. Add OAuth config to oauth.py
2. Define TP tools in [platform_tools.py](../../api/services/platform_tools.py) with handler functions
3. Implement fetch function in [deliverable_pipeline.py](../../api/services/deliverable_pipeline.py)
4. Add exporter if write operations needed

---

## Environment Variables

```bash
# Slack
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=

# Notion
NOTION_CLIENT_ID=
NOTION_CLIENT_SECRET=

# Google (Gmail + Calendar)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# MCP Gateway
MCP_GATEWAY_URL=https://yarnnn-mcp-gateway.onrender.com
```

---

## Related Documentation

- [ADR-026: Integration Architecture](../adr/ADR-026-integration-architecture.md)
- [ADR-029: Email Integration Platform](../adr/ADR-029-email-integration-platform.md)
- [ADR-046: Google Calendar Integration](../adr/ADR-046-google-calendar-integration.md)
- [ADR-050: MCP Gateway Architecture](../adr/ADR-050-mcp-gateway-architecture.md)
- [Render Services](./RENDER-SERVICES.md)
