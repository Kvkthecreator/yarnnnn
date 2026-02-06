# ADR-029: Email as Full Integration Platform

> **Status**: Draft (Needs Scoping)
> **Created**: 2026-02-06
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

## Proposed Scope

### Phase 1: Email Connection (MCP)

```
Email MCP Server
├── email_list_messages     # List recent/filtered messages
├── email_get_message       # Get full message + thread
├── email_get_thread        # Get conversation thread
├── email_send              # Send new email
├── email_reply             # Reply to thread
├── email_forward           # Forward with context
├── email_label             # Apply labels/folders
└── email_search            # Search inbox
```

Supported providers (via OAuth or IMAP):
- Gmail (OAuth)
- Outlook/Microsoft 365 (OAuth)
- Generic IMAP (credentials)

### Phase 2: Email Data Sources

Extend ADR-027 to support email sources:

```python
DataSource = {
    "type": "integration_import",
    "provider": "email",
    "source": "inbox",           # or "sent", "thread:abc123"
    "filters": {
        "from": "sarah@company.com",
        "subject_contains": "weekly update",
        "after": "7d"
    }
}
```

### Phase 3: Email-Specific Deliverables

New deliverable types that make sense for email:

| Type | Schedule | Output |
|------|----------|--------|
| `inbox_summary` | Daily/Weekly | Digest of inbox activity |
| `reply_draft` | On-demand | Draft reply to specific thread |
| `follow_up_tracker` | Daily | List of threads needing response |
| `thread_summary` | On-demand | Summarize long conversation |

### Phase 4: Email as Destination

Full destination-first support for email:

```python
Deliverable = {
    "destination": {
        "platform": "email",
        "target": "sarah@company.com",   # Recipient
        "format": "send",                # or "reply", "forward"
        "options": {
            "thread_id": "abc123",       # For reply/forward
            "cc": ["team@company.com"],
            "subject": "Weekly Update"   # For new emails
        }
    }
}
```

---

## Technical Considerations

### 1. Privacy & Security

Email is highly personal. Requirements:
- End-to-end encryption for stored content
- Clear user consent for inbox access
- Minimal data retention (don't store full inbox)
- Audit logging for all email actions

### 2. Rate Limits & Quotas

Email providers have strict limits:
- Gmail: 500 emails/day (consumer), 2000/day (Workspace)
- Outlook: Varies by plan
- Need queuing, throttling, retry logic

### 3. Deliverability

Sent emails must land in inbox, not spam:
- SPF/DKIM/DMARC compliance
- Sender reputation management
- Opt for user's own SMTP when possible

### 4. Style Context

Email requires relationship-aware style:
- Formal for external contacts
- Casual for close colleagues
- Context from historical thread tone
- User's personal writing style

This connects to deliverable-scoped context (deferred in ADR-028).

---

## Relationship to Existing Architecture

### ADR-026: Integration Architecture

Email becomes a first-class integration provider:
- `IntegrationProvider.EMAIL`
- OAuth or IMAP credentials stored in `user_integrations`
- MCP server for email operations

### ADR-027: Integration Reads

Email sources work identically to Slack/Notion:
- Data sources can reference email threads
- Import jobs extract content during gather phase
- Same import_content structure

### ADR-028: Destination-First

Email is a valid destination platform:
- `destination.platform = "email"`
- Governance applies (semi_auto = send on approval)
- Style inferred from recipient relationship

---

## Use Cases to Validate

Before implementation, validate these use cases:

1. **Weekly inbox summary** - "Every Monday, summarize my inbox from the past week"
2. **Meeting follow-up** - "After each meeting, draft follow-up emails to attendees"
3. **Reply drafts** - "Draft a reply to emails from my manager"
4. **Thread context** - "Use this email thread as context for my status report"
5. **Auto-organization** - "Label incoming emails by project"

---

## Questions to Resolve

1. **Provider priority**: Start with Gmail only, or multi-provider from start?
2. **MCP vs. direct API**: Use MCP email server, or direct Gmail/Outlook APIs?
3. **Storage model**: How much email content to cache locally?
4. **Style learning**: How to learn user's email style per-relationship?
5. **Reply vs. send**: Should deliverables auto-reply, or always new threads?

---

## Next Steps

1. [ ] Validate use cases with user feedback
2. [ ] Research Gmail/Outlook MCP server options
3. [ ] Define MVP scope (likely: Gmail + inbox summary + send)
4. [ ] Design privacy/consent flow
5. [ ] Implement as full integration (not just exporter)

---

## References

- [ADR-026: Integration Architecture](./ADR-026-integration-architecture.md)
- [ADR-027: Integration Read Architecture](./ADR-027-integration-read-architecture.md)
- [ADR-028: Destination-First Deliverables](./ADR-028-destination-first-deliverables.md)
- [Analysis: Deliverable-Scoped Context](../analysis/deliverable-scoped-context.md)
