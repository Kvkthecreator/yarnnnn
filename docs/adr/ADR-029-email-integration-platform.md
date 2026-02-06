# ADR-029: Email as Full Integration Platform

> **Status**: Accepted (Phase 1 Implemented)
> **Created**: 2026-02-06
> **Updated**: 2026-02-06 (Gmail Phase 1 implementation complete)
> **Related**: ADR-026 (Integration Architecture), ADR-027 (Integration Reads), ADR-028 (Destination-First)

---

## Context

During ADR-028 implementation, we initially framed email as "just another exporter" alongside Slack and Notion. However, email is fundamentally different — it's a bidirectional communication platform with unique characteristics that warrant full integration treatment.

### Why Email ≠ Just an Exporter

| Aspect | Slack/Notion | Email |
|--------|--------------|-------|
| Connection | OAuth to workspace | Personal inbox (IMAP/OAuth) |
| Read | Channel/page content | Inbox, threads, conversations |
| Write | Post message/page | Send, reply, forward |
| Context | Workspace-scoped | Person-to-person, highly private |
| Tone/Style | Per-workspace norms | Per-relationship, highly personal |

Email requires the same bidirectional MCP treatment as Slack/Notion:
- **Import**: Read inbox for context (decisions, requests, follow-ups)
- **Export**: Send/reply/forward with appropriate tone and context

---

## The Insight

> **Email is a platform where deliverables can both originate from and be delivered to.**

### Email as Context Source (Read)

Like ADR-027's Slack/Notion reads, email provides rich context:

| Use Case | Context Extracted |
|----------|-------------------|
| Inbox triage | Pending items, urgency, senders |
| Thread context | Conversation history for replies |
| Meeting follow-ups | Action items mentioned in threads |
| Decision tracking | Approvals, rejections, next steps |

### Email as Destination (Write)

Beyond simple export, email-specific deliverables:

| Deliverable Type | Description |
|------------------|-------------|
| Weekly inbox summary | AI-generated overview of inbox activity |
| Auto-reply drafts | Context-aware reply suggestions |
| Follow-up reminders | "You haven't replied to X in 3 days" |
| Thread summarizer | Summarize long email threads |
| Auto-organization | Categorize/label incoming emails |

---

## Implementation

### Decision: Gmail-First with MCP

**Provider**: Gmail only (via OAuth 2.0)
**MCP Server**: `@shinzolabs/gmail-mcp`
**Authentication**: OAuth tokens passed via environment variables (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)

This aligns with existing Slack/Notion patterns using MCP servers via stdio transport.

### Phase 1: Gmail Integration (COMPLETE) ✅

#### OAuth Configuration

```python
# api/integrations/core/oauth.py
"gmail": OAuthConfig(
    provider="gmail",
    client_id_env="GOOGLE_CLIENT_ID",
    client_secret_env="GOOGLE_CLIENT_SECRET",
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    scopes=[
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.modify",
    ],
    redirect_path="/api/integrations/gmail/callback",
)
```

#### MCP Server Configuration

```python
# api/integrations/core/client.py
SERVER_COMMANDS = {
    "gmail": ["npx", "-y", "@shinzolabs/gmail-mcp"],
}
SERVER_ENV_KEYS = {
    "gmail": ["CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"],
}
```

#### Gmail Exporter

```python
# api/integrations/exporters/gmail.py
class GmailExporter(DestinationExporter):
    platform = "gmail"
    supported_formats = ["send", "draft", "reply"]

    # Uses MCP for all operations
    # Supports: send directly, create draft, reply to thread
```

#### MCPClientManager Gmail Operations

- `list_gmail_messages(query, max_results)` - List/search messages
- `get_gmail_message(message_id)` - Get full message content
- `get_gmail_thread(thread_id)` - Get conversation thread
- `send_gmail_message(to, subject, body, cc, thread_id)` - Send email
- `create_gmail_draft(to, subject, body, cc, thread_id)` - Create draft

#### Gmail Import Jobs

```python
# api/jobs/import_jobs.py
async def process_gmail_import(job, integration, mcp_manager, agent, token_manager):
    # Supports:
    # - "inbox" - Recent inbox messages
    # - "thread:<id>" - Specific thread
    # - "query:<query>" - Gmail search query

    # Fetches messages, runs ContextImportAgent, stores as memories
    # Optional style learning from email writing patterns
```

#### Key Files

| File | Purpose |
|------|---------|
| `api/integrations/core/oauth.py` | Gmail OAuth config |
| `api/integrations/core/client.py` | MCP server config + Gmail operations |
| `api/integrations/exporters/gmail.py` | GmailExporter implementation |
| `api/integrations/exporters/registry.py` | Gmail exporter registration |
| `api/routes/integrations.py` | Gmail import route + destination normalization |
| `api/jobs/import_jobs.py` | Gmail import job processor |
| `web/types/index.ts` | Gmail types for frontend |

### Phase 2: Email Data Sources (Planned)

Extend data source types to include Gmail:

```typescript
DataSource = {
  type: "integration_import",
  provider: "gmail",
  source: "inbox" | "thread:<id>" | "query:<query>",
  filters: {
    from?: string,
    subject_contains?: string,
    after?: string  // "7d", "2024-01-01"
  }
}
```

### Phase 3: Email-Specific Deliverables (Planned)

New deliverable types:

| Type | Schedule | Output |
|------|----------|--------|
| `inbox_summary` | Daily/Weekly | Digest of inbox activity |
| `reply_draft` | On-demand | Draft reply to specific thread |
| `follow_up_tracker` | Daily | List of threads needing response |
| `thread_summary` | On-demand | Summarize long conversation |

### Phase 4: Advanced Features (Future)

- Email style learning per-relationship
- Auto-organization with labels
- Engagement tracking (opens, replies)

---

## Technical Considerations

### 1. Privacy & Security

Email is highly personal. Current approach:
- Refresh tokens encrypted at rest
- No email content stored (fetched on-demand via MCP)
- All actions logged in export_log
- OAuth scopes are minimal (no delete permission)

### 2. Rate Limits

Gmail API limits:
- Consumer: 500 emails/day
- Workspace: 2000/day

Current approach: No rate limiting in Phase 1. Will add queuing in Phase 2 if needed.

### 3. Deliverability

Emails sent via user's own Gmail account:
- No deliverability issues (not sending as YARNNN)
- User's reputation, not platform's
- Drafts option for review before send

### 4. Style Context

Gmail exporter returns `style_context = "email"` for pipeline style inference.
Future: Learn user's email style per-relationship via StyleLearningAgent.

---

## Destination Schema

```python
Destination = {
    "platform": "gmail",
    "target": "recipient@example.com",
    "format": "send" | "draft" | "reply",
    "options": {
        "cc": "other@example.com",
        "subject": "Custom subject",
        "thread_id": "abc123"  # For replies
    }
}
```

---

## Questions Resolved

1. **Provider priority**: Gmail only for now. Outlook later if needed.
2. **MCP vs. direct API**: MCP (`@shinzolabs/gmail-mcp`) for consistency.
3. **Storage model**: No storage. Fetch on-demand via MCP.
4. **Style learning**: Deferred to Phase 3. Uses "email" style context for now.
5. **Reply vs. send**: Both supported. Format determines behavior.

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Gmail OAuth completion rate | >90% |
| Email export success rate | >99% |
| Import job success rate | >95% |
| Time to send (via MCP) | <3 seconds |

---

## References

- [ADR-026: Integration Architecture](./ADR-026-integration-architecture.md)
- [ADR-027: Integration Read Architecture](./ADR-027-integration-read-architecture.md)
- [ADR-028: Destination-First Deliverables](./ADR-028-destination-first-deliverables.md)
- [Analysis: Deliverable-Scoped Context](../analysis/deliverable-scoped-context.md)
- [@shinzolabs/gmail-mcp](https://github.com/shinzo-labs/gmail-mcp) - MCP server used
