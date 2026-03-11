# Email Notifications

> **Status**: Active
> **ADRs**: ADR-018 (Agent Scheduling)

---

## Overview

YARNNN sends email notifications when agents are ready and when generation/delivery fails. Suggestion-created notifications are also supported. Emails are sent via Resend API.

---

## Architecture

### Key Files

| File | Purpose |
|------|---------|
| `api/jobs/email.py` | Resend API client |
| `api/services/delivery.py` | Delivery orchestration and notification triggers |
| `api/services/notifications.py` | Notification routing, preference checks, email send |
| `api/routes/webhooks.py` | Resend webhook ingestion (`/webhooks/resend/events`) for post-send outcomes |
| `api/jobs/unified_scheduler.py` | Cron entrypoint that triggers agent execution |
| `supabase/migrations/022_user_notification_preferences.sql` | User preferences table |

### Email Flow

```
Scheduler (every 5 min)
        │
        ▼
agent execution (dispatch_trigger)
        │
        ▼
delivery service (delivery.py)
        │
        ▼
notification service (notifications.py)
        │
        ├─ check user preferences (should_send_email)
        ▼
send email via Resend to user's auth email
        │
        ▼
Resend webhook (`/webhooks/resend/events`) updates export outcome status
```

---

## Current State

### What Works

| Component | Status | Notes |
|-----------|--------|-------|
| Resend API client | ✅ Complete | Async, error handling, proper config |
| Email templates | ✅ Complete | `agent_ready`, `agent_failed` |
| Scheduler integration | ✅ Complete | Every 5 min via Render cron, routed through delivery service |
| Preference checking | ✅ Complete | `should_send_email()` checks DB per notification type |
| Preferences DB table | ✅ Complete | With RLS and helper function |
| Delivery logging | ✅ Complete | `email_delivery_log` table |
| Resend webhook outcome tracking | ✅ Complete | `export_log.outcome` + `outcome_observed_at` updated from webhook events |

### What's Missing

| Component | Status | Priority |
|-----------|--------|----------|
| Preferences API endpoints | ✅ Complete | GET/PATCH `/api/account/notification-preferences` |
| Settings UI (Notifications tab) | ✅ Complete | `/settings?tab=notifications` |
| Unsubscribe mechanism | ❌ Missing | P2 |
| Email retry logic | ❌ Missing | P3 |

---

## Email Recipients

### Current Behavior

All emails go to the **user's authenticated email** (from Supabase auth). This is the email they signed up with.

```python
# In unified_scheduler.py
user = supabase.auth.admin.get_user_by_id(agent.user_id)
recipient_email = user.user.email
```

### Future Consideration: Agent-Level Recipients

The agent settings modal (see screenshot) has a **Recipient** field with:
- Name (e.g., "Sarah", "Board")
- Role (e.g., "Manager", "Investor")
- Notes (e.g., "prefers bullet points, wants metrics upfront")

**Current usage**: This is used to personalize the *content* of the agent (tone, focus areas), NOT to determine email recipients.

**Future possibility**: Allow sending directly to external recipients (e.g., board@company.com). This would require:
1. Email verification for external addresses
2. Consent/opt-in mechanism
3. Unsubscribe handling per recipient
4. Different email templates (third-party vs self)

**Decision**: For MVP, keep emails to the authenticated user only. The "Recipient" field informs content generation, not delivery.

---

## Data Model

### User Notification Preferences

```sql
-- Table: user_notification_preferences
CREATE TABLE user_notification_preferences (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),

    -- Email toggles (all default to true)
    email_agent_ready BOOLEAN DEFAULT true,
    email_agent_failed BOOLEAN DEFAULT true,
    email_suggestion_created BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,

    UNIQUE(user_id)
);
```

### Potential Future: Agent-Level Overrides

If we need per-agent email settings, we could add:

```sql
-- Future: agent_notification_settings
-- Overrides user defaults for specific agents
CREATE TABLE agent_notification_settings (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),

    -- Override user default (null = use user preference)
    send_email_on_ready BOOLEAN,

    -- External recipient (future feature)
    external_recipient_email TEXT,
    external_recipient_verified BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ
);
```

**Current decision**: Not implementing agent-level overrides for MVP.

---

## Email Templates

### 1. Agent Ready

Sent when a agent version is generated and delivered (ADR-066 delivery-first — no approval gate).

```
Subject: Your [Title] is ready for review

Body:
- Agent title and type
- Schedule description
- Next scheduled run
- CTA: "Review Now" → /dashboard?surface=agent-review&...
```

### 2. Agent Failed

Sent when pipeline execution fails.

```
Subject: Issue with your [Title]

Body:
- Error summary
- Troubleshooting guidance
- CTA: "View Agent" → /dashboard?surface=agent-detail&...
```

Preference handling: this notification is controlled by `email_agent_failed` independently from `email_agent_ready`.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RESEND_API_KEY` | Resend API key | Required |
| `RESEND_FROM_EMAIL` | Sender address | `yarnnn <noreply@yarnnn.com>` |
| `RESEND_WEBHOOK_SECRET` | Webhook signature secret (`whsec_*`) | Optional but recommended |
| `APP_URL` | Base URL for links | `https://yarnnn.com` |

### Render Configuration

```yaml
# render.yaml
services:
  - type: cron
    name: unified-scheduler
    schedule: "*/5 * * * *"
    envVars:
      - key: RESEND_API_KEY
        sync: false
```

---

## Implementation Phases

### Phase 1: Core Loop (Current Target)

**Goal**: Users receive emails for all agent events at their auth email.

- [x] Resend client and templates
- [x] Scheduler integration
- [x] Preferences database
- [x] API endpoints for preferences (GET/PATCH)
- [x] Settings UI with Notifications tab

**User experience**:
- Emails enabled by default
- User can toggle off in Settings → Notifications
- All emails go to signup email

### Phase 2: Production Hardening

- [ ] Unsubscribe links in email footer
- [ ] `List-Unsubscribe` header for email clients
- [x] Resend webhook for bounce/complaint handling
- [ ] Retry logic with exponential backoff

### Phase 3: Advanced Features (Future)

- [ ] Per-agent email toggles
- [ ] External recipient support (with verification)
- [ ] Email scheduling preferences (immediate vs batched)
- [ ] Email analytics dashboard

---

## Future Consideration: In-App Delivery Channel

**Date:** 2026-02-24
**Status:** Documented for future planning — no implementation needed now

### Context

Currently all agent delivery routes through email (Gmail API for content delivery, Resend for notifications). This is correct for MVP — email is the universal inbox and requires zero onboarding friction.

However, as YARNNN matures, a dedicated **in-app delivery surface** would provide:
- **Richer presentation**: Interactive content, source attribution links, execution metadata
- **No OAuth dependency**: In-app delivery doesn't require Gmail OAuth tokens
- **Version history browsing**: Side-by-side version comparison without leaving the app
- **Execution transparency**: Show strategy used, sources consulted, token counts — metadata that doesn't belong in email

### Architecture Support

The current delivery architecture already supports this via the **exporter registry pattern** ([api/integrations/exporters/registry.py](../../api/integrations/exporters/registry.py)):

```
delivery.py → ExporterRegistry.get_exporter(platform) → GmailExporter / SlackExporter / ...
```

Adding an in-app channel would require:
1. An `AppExporter` that writes to a `agent_inbox` or similar table
2. Registration in the exporter registry (`"app"` platform)
3. Frontend reads from that table on `/agents/[id]` page
4. Destination config: `{"platform": "app", "format": "markdown"}`

The `destinations` array (ADR-031 Phase 6) already supports multi-destination, so a agent could deliver to **both** email and in-app simultaneously.

### Current Decision

Email-first delivery is the right default. The in-app channel is a Phase 3+ enhancement that builds on, rather than replaces, email delivery. No schema or code changes needed now — this note ensures the architectural path is documented.

---

## Testing

### Manual Testing Checklist

- [ ] Create agent → scheduled run → email received
- [ ] Toggle preference off → no email sent
- [ ] Agent failure → failure email received
- [ ] Weekly digest triggers correctly

### Test Email Endpoint

```bash
# Send test email (requires auth)
curl -X POST https://api.yarnnn.com/api/test-email \
  -H "Authorization: Bearer $TOKEN"
```

---

## Related Documentation

- [Agent Architecture](../architecture/agents.md)
- [Backend Orchestration](../architecture/backend-orchestration.md) — F3 (Agent Execution), F7 (Weekly Digest)
- ADR-018: Agent Scheduling
- ADR-066: Delivery-First (no approval gate)

---

## Changelog

### 2026-03-11: Delivery Outcome Observability

- Added Resend webhook endpoint: `POST /webhooks/resend/events`
- Webhook events now update `export_log.outcome` and `outcome_observed_at`
- Bounce/complaint events propagate to `agent_runs.delivery_status='failed'`
- Added webhook environment variable docs (`RESEND_WEBHOOK_SECRET`)

### 2026-02-06: Documentation Created

- Documented current email infrastructure (80% complete)
- Clarified that "Recipient" field in agent settings is for content personalization, not email delivery
- Defined Phase 1 scope: core loop with user preferences
- Deferred agent-level email settings to future phases
