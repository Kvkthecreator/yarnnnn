# Email Notifications

> **Status**: Core infrastructure complete, user preferences UI pending
> **ADRs**: ADR-018 (Deliverable Scheduling)

---

## Overview

YARNNN sends email notifications when deliverables are ready for review, when generation fails, and for weekly activity digests. Emails are sent via Resend API.

---

## Architecture

### Key Files

| File | Purpose |
|------|---------|
| `api/jobs/email.py` | Resend API client, email templates |
| `api/jobs/unified_scheduler.py` | Cron job that triggers emails on deliverable completion |
| `api/jobs/digest.py` | Weekly digest content generation |
| `supabase/migrations/022_user_notification_preferences.sql` | User preferences table |

### Email Flow

```
Scheduler (every 5 min)
        │
        ▼
┌─────────────────────────────┐
│ Query due deliverables      │
│ WHERE next_run_at <= now    │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Execute pipeline            │
│ gather → synthesize → deliver │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Check user preference       │
│ should_send_email()         │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ Send email via Resend       │
│ to user's auth email        │
└─────────────────────────────┘
```

---

## Current State

### What Works

| Component | Status | Notes |
|-----------|--------|-------|
| Resend API client | ✅ Complete | Async, error handling, proper config |
| Email templates | ✅ Complete | `deliverable_ready`, `deliverable_failed`, `work_complete`, `weekly_digest` |
| Scheduler integration | ✅ Complete | Every 5 min via Render cron |
| Preference checking | ✅ Complete | `should_send_email()` checks DB |
| Preferences DB table | ✅ Complete | With RLS and helper function |
| Delivery logging | ✅ Complete | `email_delivery_log` table |

### What's Missing

| Component | Status | Priority |
|-----------|--------|----------|
| Preferences API endpoints | ❌ Missing | P1 |
| Settings UI (Notifications tab) | ❌ Missing | P1 |
| Unsubscribe mechanism | ❌ Missing | P2 |
| Resend webhook handling | ❌ Missing | P2 |
| Email retry logic | ❌ Missing | P3 |

---

## Email Recipients

### Current Behavior

All emails go to the **user's authenticated email** (from Supabase auth). This is the email they signed up with.

```python
# In unified_scheduler.py
user = supabase.auth.admin.get_user_by_id(deliverable.user_id)
recipient_email = user.user.email
```

### Future Consideration: Deliverable-Level Recipients

The deliverable settings modal (see screenshot) has a **Recipient** field with:
- Name (e.g., "Sarah", "Board")
- Role (e.g., "Manager", "Investor")
- Notes (e.g., "prefers bullet points, wants metrics upfront")

**Current usage**: This is used to personalize the *content* of the deliverable (tone, focus areas), NOT to determine email recipients.

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
    email_deliverable_ready BOOLEAN DEFAULT true,
    email_deliverable_failed BOOLEAN DEFAULT true,
    email_work_complete BOOLEAN DEFAULT true,
    email_weekly_digest BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,

    UNIQUE(user_id)
);
```

### Potential Future: Deliverable-Level Overrides

If we need per-deliverable email settings, we could add:

```sql
-- Future: deliverable_notification_settings
-- Overrides user defaults for specific deliverables
CREATE TABLE deliverable_notification_settings (
    id UUID PRIMARY KEY,
    deliverable_id UUID REFERENCES deliverables(id),

    -- Override user default (null = use user preference)
    send_email_on_ready BOOLEAN,

    -- External recipient (future feature)
    external_recipient_email TEXT,
    external_recipient_verified BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ
);
```

**Current decision**: Not implementing deliverable-level overrides for MVP.

---

## Email Templates

### 1. Deliverable Ready

Sent when a deliverable version is generated and delivered (ADR-066 delivery-first — no approval gate).

```
Subject: Your [Title] is ready for review

Body:
- Deliverable title and type
- Schedule description
- Next scheduled run
- CTA: "Review Now" → /dashboard?surface=deliverable-review&...
```

### 2. Deliverable Failed

Sent when pipeline execution fails.

```
Subject: Issue with your [Title]

Body:
- Error summary
- Troubleshooting guidance
- CTA: "View Deliverable" → /dashboard?surface=deliverable-detail&...
```

### 3. Work Complete

Sent when a work ticket finishes execution.

```
Subject: Work complete: [Task description]

Body:
- Project name
- Agent type
- Generated outputs list
- CTA: "View Results" → /dashboard?project=...
```

### 4. Weekly Digest

Sent once per week with activity summary.

```
Subject: Your weekly yarnnn digest

Body:
- Tickets completed
- Outputs delivered
- Active projects
- Top outputs
- CTA: "Open Dashboard"
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RESEND_API_KEY` | Resend API key | Required |
| `RESEND_FROM_EMAIL` | Sender address | `yarnnn <noreply@yarnnn.com>` |
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

**Goal**: Users receive emails for all deliverable events at their auth email.

- [x] Resend client and templates
- [x] Scheduler integration
- [x] Preferences database
- [ ] API endpoints for preferences (GET/PATCH)
- [ ] Settings UI with Notifications tab

**User experience**:
- Emails enabled by default
- User can toggle off in Settings → Notifications
- All emails go to signup email

### Phase 2: Production Hardening

- [ ] Unsubscribe links in email footer
- [ ] `List-Unsubscribe` header for email clients
- [ ] Resend webhook for bounce/complaint handling
- [ ] Retry logic with exponential backoff

### Phase 3: Advanced Features (Future)

- [ ] Per-deliverable email toggles
- [ ] External recipient support (with verification)
- [ ] Email scheduling preferences (immediate vs batched)
- [ ] Email analytics dashboard

---

## Future Consideration: In-App Delivery Channel

**Date:** 2026-02-24
**Status:** Documented for future planning — no implementation needed now

### Context

Currently all deliverable delivery routes through email (Gmail API for content delivery, Resend for notifications). This is correct for MVP — email is the universal inbox and requires zero onboarding friction.

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
1. An `AppExporter` that writes to a `deliverable_inbox` or similar table
2. Registration in the exporter registry (`"app"` platform)
3. Frontend reads from that table on `/deliverables/[id]` page
4. Destination config: `{"platform": "app", "format": "markdown"}`

The `destinations` array (ADR-031 Phase 6) already supports multi-destination, so a deliverable could deliver to **both** email and in-app simultaneously.

### Current Decision

Email-first delivery is the right default. The in-app channel is a Phase 3+ enhancement that builds on, rather than replaces, email delivery. No schema or code changes needed now — this note ensures the architectural path is documented.

---

## Testing

### Manual Testing Checklist

- [ ] Create deliverable → scheduled run → email received
- [ ] Toggle preference off → no email sent
- [ ] Deliverable failure → failure email received
- [ ] Weekly digest triggers correctly

### Test Email Endpoint

```bash
# Send test email (requires auth)
curl -X POST https://api.yarnnn.com/api/test-email \
  -H "Authorization: Bearer $TOKEN"
```

---

## Related Documentation

- [Deliverable Architecture](../architecture/deliverables.md)
- [Backend Orchestration](../architecture/backend-orchestration.md) — F3 (Deliverable Execution), F7 (Weekly Digest)
- ADR-018: Deliverable Scheduling
- ADR-066: Delivery-First (no approval gate)

---

## Changelog

### 2026-02-06: Documentation Created

- Documented current email infrastructure (80% complete)
- Clarified that "Recipient" field in deliverable settings is for content personalization, not email delivery
- Defined Phase 1 scope: core loop with user preferences
- Deferred deliverable-level email settings to future phases
