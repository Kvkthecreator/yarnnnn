# ADR-029: Email as Full Integration Platform

> **Status**: Accepted (Phases 1-3 Implemented)
> **Created**: 2026-02-06
> **Updated**: 2026-02-06 (Gmail Phases 1-3 implementation complete)
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

### Phase 2: Email Data Sources (COMPLETE) ✅

#### DataSource Type Extension

```typescript
// web/types/index.ts
export type DataSourceType = "url" | "document" | "description" | "integration_import";

export type IntegrationProvider = "slack" | "notion" | "gmail";

export interface IntegrationImportFilters {
  from?: string;           // Email sender filter
  subject_contains?: string; // Subject line filter
  after?: string;          // Time filter: "7d", "30d", or ISO date
  channel_id?: string;     // Slack channel filter
  page_id?: string;        // Notion page filter
}

export interface DataSource {
  type: DataSourceType;
  value: string;
  label?: string;
  provider?: IntegrationProvider;  // Required when type = "integration_import"
  source?: string;                 // "inbox", "thread:<id>", "query:<query>"
  filters?: IntegrationImportFilters;
}
```

#### Pipeline Integration

The gather step now fetches live data from integrations:

```python
# api/services/deliverable_pipeline.py
async def fetch_integration_source_data(client, user_id, source):
    """Fetch data from Gmail/Slack/Notion via MCP during gather step."""
    # Supports all three integration providers
    # Applies filters (from, subject_contains, after, etc.)
    # Returns formatted context for the synthesis prompt
```

#### Key Changes

| File | Change |
|------|--------|
| `web/types/index.ts` | Added `integration_import` DataSourceType, IntegrationImportFilters |
| `api/services/deliverable_pipeline.py` | Added `fetch_integration_source_data()`, updated `execute_gather_step()` |

### Phase 3: Email-Specific Deliverables (COMPLETE) ✅

#### New Deliverable Types

```typescript
// web/types/index.ts
export type DeliverableType =
  // ... existing types ...
  // ADR-029 Phase 3: Email-specific types
  | "inbox_summary"
  | "reply_draft"
  | "follow_up_tracker"
  | "thread_summary";
```

| Type | Use Case | Key Config |
|------|----------|------------|
| `inbox_summary` | Daily/weekly digest of inbox activity | `summary_period`, `inbox_scope`, `prioritization` |
| `reply_draft` | Generate context-aware reply to thread | `thread_id`, `tone`, `include_original_quotes` |
| `follow_up_tracker` | Track threads needing response | `tracking_period`, `prioritize_by` |
| `thread_summary` | Summarize long email conversations | `thread_id`, `detail_level` |

#### Type Configurations

```typescript
// web/types/index.ts
export interface InboxSummaryConfig {
  summary_period: "daily" | "weekly";
  inbox_scope: "all" | "unread" | "flagged";
  sections: InboxSummarySections;
  prioritization: "by_sender" | "by_urgency" | "chronological";
  include_thread_context: boolean;
}

export interface ReplyDraftConfig {
  thread_id: string;
  tone: "formal" | "professional" | "friendly" | "brief";
  sections: ReplyDraftSections;
  include_original_quotes: boolean;
  suggested_actions?: string[];
}

export interface FollowUpTrackerConfig {
  tracking_period: "7d" | "14d" | "30d";
  sections: FollowUpTrackerSections;
  include_thread_links: boolean;
  prioritize_by: "age" | "sender_importance" | "subject";
}

export interface ThreadSummaryConfig {
  thread_id: string;
  sections: ThreadSummarySections;
  detail_level: "brief" | "detailed";
  highlight_action_items: boolean;
}
```

#### Pipeline Support

Type-specific prompts and validators added to `deliverable_pipeline.py`:

- `TYPE_PROMPTS["inbox_summary"]` - Structured inbox digest generation
- `TYPE_PROMPTS["reply_draft"]` - Context-aware reply drafting
- `TYPE_PROMPTS["follow_up_tracker"]` - Follow-up tracking and prioritization
- `TYPE_PROMPTS["thread_summary"]` - Conversation summarization

- `validate_inbox_summary()` - Checks for scannable structure, sections
- `validate_reply_draft()` - Checks greeting, closing, acknowledgment
- `validate_follow_up_tracker()` - Checks for specific items and structure
- `validate_thread_summary()` - Checks detail level and sections

#### Key Files

| File | Change |
|------|--------|
| `web/types/index.ts` | Added 4 email deliverable types + configs |
| `api/services/deliverable_pipeline.py` | Added prompts, section templates, validators |

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
