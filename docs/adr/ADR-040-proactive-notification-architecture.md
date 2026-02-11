# ADR-040: Proactive Notification Architecture

> **Status**: Accepted
> **Date**: 2026-02-11
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-028 (Delivery Subsystem), ADR-031 (Slack Export), ADR-039 (Agentic Platform Operations)

## Implementation Status: ✅ Complete

**Streamlined Approach**: Email via Resend + in-session TP responses.
- Push notifications (Firebase/OneSignal) deferred to future
- In-app notification UI deferred to future
- Database tables created for audit/logging

---

## Context

YARNNN's vision includes proactive outreach — "reaching out, pushing" like Clawdbot/Moltbot. The infrastructure exists in pieces but isn't wired together coherently:

### Current State Audit

| Component | Status | Location |
|-----------|--------|----------|
| **Delivery Service** | Built | `api/services/delivery.py` |
| **Governance Levels** | Defined | manual, semi_auto, full_auto |
| **Event Triggers** | Partial | `api/services/event_triggers.py` |
| **Cooldown Management** | In-memory | `event_triggers.py:_cooldown_cache` |
| **Slack Exporter** | Built | `api/integrations/exporters/slack.py` |
| **Gmail Exporter** | Built | `api/integrations/exporters/gmail.py` |
| **Email Notifications** | Functions exist | `api/jobs/unified_scheduler.py` |
| **Push Notification Wiring** | ❌ Missing | Delivery → Notification gap |
| **TP Notification Tools** | ❌ Missing | TP can't send notifications |
| **Event Trigger Logging** | ❌ Missing | No audit trail |
| **Full-auto Governance** | ❌ Not implemented | Always requires approval |

### The Problem

1. **Deliverables ≠ Notifications**: Deliverables are recurring content artifacts (digests, summaries). Notifications are lightweight, often one-off messages ("Your sync completed", "New mentions detected").

2. **TP Can't Notify**: TP can create deliverables but can't send a simple "I noticed X" push notification.

3. **Event Triggers Disconnected**: Event handlers exist but don't trigger the notification pipeline.

4. **Governance Incomplete**: `full_auto` is defined but delivery always stops at approval stage.

## Decision

### Three-Part Proactive Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PROACTIVE LAYER                                │
├───────────────────┬─────────────────────┬───────────────────────────┤
│   DELIVERABLES    │   NOTIFICATIONS     │      MONITORS             │
├───────────────────┼─────────────────────┼───────────────────────────┤
│ Recurring content │ Lightweight alerts  │ Conditions that trigger   │
│ artifacts         │ and messages        │ deliverables/notifications│
│                   │                     │                           │
│ • Weekly digests  │ • "Sync complete"   │ • Slack mention detected  │
│ • Daily summaries │ • "I noticed X"     │ • Email from VIP          │
│ • Research briefs │ • "Action needed"   │ • Calendar conflict       │
│ • Status updates  │ • "Reminder: Y"     │ • Keyword detected        │
├───────────────────┼─────────────────────┼───────────────────────────┤
│ Heavy pipeline:   │ Light pipeline:     │ No pipeline:              │
│ gather→synthesize │ format→send         │ evaluate→trigger          │
│ →stage→approve    │                     │                           │
│ →deliver          │                     │                           │
├───────────────────┼─────────────────────┼───────────────────────────┤
│ Governance:       │ Governance:         │ Governance:               │
│ manual/semi/full  │ always auto         │ defines what triggers     │
└───────────────────┴─────────────────────┴───────────────────────────┘
```

### Notifications as First-Class Concept

Notifications are NOT mini-deliverables. They are a separate, lightweight mechanism:

```python
@dataclass
class Notification:
    """A lightweight proactive message."""
    id: str
    user_id: str

    # Content
    message: str                    # The notification text
    context: Optional[dict]         # Related context (deliverable_id, event, etc.)

    # Delivery
    channel: Literal["push", "email", "slack_dm", "in_app"]
    urgency: Literal["low", "normal", "high"]

    # Source
    source_type: Literal["system", "monitor", "tp", "deliverable"]
    source_id: Optional[str]        # deliverable_id, monitor_id, etc.

    # State
    status: Literal["pending", "sent", "failed", "dismissed"]
    created_at: datetime
    sent_at: Optional[datetime]
```

### TP Gets Notification Tools

TP should be able to send notifications without creating full deliverables:

```python
SEND_NOTIFICATION_TOOL = {
    "name": "send_notification",
    "description": """
    Send a lightweight notification to the user.

    Use this for:
    - Alerting about something you noticed
    - Confirming an action completed
    - Proactive insights that don't need a full deliverable

    This is DIFFERENT from deliverables:
    - Notifications: one-off, lightweight, immediate
    - Deliverables: recurring, content-rich, scheduled
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "The notification message"},
            "channel": {
                "type": "string",
                "enum": ["push", "email", "slack_dm", "in_app"],
                "description": "How to deliver the notification"
            },
            "urgency": {
                "type": "string",
                "enum": ["low", "normal", "high"],
                "default": "normal"
            },
            "context": {
                "type": "object",
                "description": "Optional context (related deliverable, event, etc.)"
            }
        },
        "required": ["message", "channel"]
    }
}
```

### Monitors Define Triggers

Monitors are conditions that trigger deliverables OR notifications:

```python
@dataclass
class Monitor:
    """A condition that triggers proactive actions."""
    id: str
    user_id: str
    name: str

    # Condition
    platform: Literal["slack", "gmail", "notion", "calendar"]
    event_types: list[str]          # ["app_mention", "message_im"]
    resource_ids: list[str]         # Channel IDs, labels, etc.
    filters: Optional[dict]         # keyword_filter, sender_filter, etc.

    # Action
    action_type: Literal["trigger_deliverable", "send_notification", "both"]
    deliverable_id: Optional[str]   # If triggering a deliverable
    notification_template: Optional[str]  # If sending notification

    # Throttling
    cooldown: CooldownConfig

    # State
    status: Literal["active", "paused", "disabled"]
    last_triggered: Optional[datetime]
```

### Governance Completion

For `full_auto` governance to work:

```python
# In delivery.py

async def process_staged_instance(instance_id: str) -> dict:
    """Process a staged deliverable instance."""
    instance = await get_instance(instance_id)
    deliverable = await get_deliverable(instance.deliverable_id)

    governance = deliverable.governance

    if governance == "manual":
        # Create notification about pending approval
        await send_notification(
            user_id=deliverable.user_id,
            message=f"'{deliverable.title}' is ready for review",
            channel="in_app",
            context={"instance_id": instance_id}
        )
        return {"status": "pending_approval"}

    elif governance == "semi_auto":
        # Deliver but notify
        result = await execute_delivery(instance)
        await send_notification(
            user_id=deliverable.user_id,
            message=f"'{deliverable.title}' was delivered to {result.destination}",
            channel="in_app",
            context={"instance_id": instance_id, "external_url": result.external_url}
        )
        return result

    elif governance == "full_auto":
        # Deliver silently (or with low-priority notification)
        result = await execute_delivery(instance)
        # Optional: low-priority notification for audit
        return result
```

## Implementation Summary (Completed)

### What Was Built

1. **Database Tables** (Migration 041):
   - `notifications` - Audit log for all notifications sent
   - `event_trigger_log` - Database-backed cooldown + audit for event triggers

2. **Notification Service** (`api/services/notifications.py`):
   - `send_notification()` - Main entry point
   - `notify_deliverable_ready/delivered/failed()` - Convenience functions
   - Email delivery via existing Resend infrastructure

3. **Delivery Service Updates** (`api/services/delivery.py`):
   - ADR-040 wiring: notifications sent on delivery success/failure
   - `semi_auto` governance: sends "delivered to X" notification
   - Failure notifications sent for all governance levels

4. **TP Tool** (`send_notification` in `project_tools.py`):
   - TP can proactively send email notifications
   - Respects user notification preferences

5. **Event Triggers** (`api/services/event_triggers.py`):
   - `check_cooldown_db()` - Database-backed cooldown check
   - `record_trigger_db()` - Logs triggers for audit + cooldown

### Streamlined Approach

Instead of building full in-app notifications:
- **Email via Resend**: Async notifications when user not in session
- **TP session**: If user is chatting, TP responds directly (no separate notification)

This defers complexity (push, in-app UI) while delivering core proactive capability.

---

## Original Implementation Plan (Reference)

### Phase 1: Database Schema (notifications table)

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,

    -- Content
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',

    -- Delivery
    channel TEXT NOT NULL CHECK (channel IN ('push', 'email', 'slack_dm', 'in_app')),
    urgency TEXT DEFAULT 'normal' CHECK (urgency IN ('low', 'normal', 'high')),

    -- Source
    source_type TEXT NOT NULL CHECK (source_type IN ('system', 'monitor', 'tp', 'deliverable')),
    source_id UUID,

    -- State
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'dismissed')),
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ,

    -- Indexes
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id)
);

CREATE INDEX idx_notifications_user_status ON notifications(user_id, status);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
```

### Phase 2: Notification Service

```
api/services/notifications.py
├── send_notification()      # Main entry point
├── format_notification()    # Channel-specific formatting
├── deliver_notification()   # Actual delivery (email, push, etc.)
└── get_user_notifications() # Fetch for in-app display
```

### Phase 3: Wire Delivery → Notifications

Update `delivery.py` to call notification service at key points:
- When instance staged (manual governance)
- When instance delivered (semi_auto governance)
- When delivery fails

### Phase 4: TP Notification Tool

Add `send_notification` to `THINKING_PARTNER_TOOLS` with handler.

### Phase 5: Event Trigger → Notification

Update `event_triggers.py` to:
- Log trigger events to a table
- Support notification-only triggers (not just deliverable triggers)
- Use database for cooldown (not in-memory)

### Phase 6: Monitors (Future)

Create monitors as configurable triggers that can:
- Trigger deliverables
- Send notifications
- Both

## Consequences

### Positive

- **Clear separation**: Deliverables for content, notifications for alerts
- **TP empowerment**: TP can proactively reach out without heavy deliverable creation
- **Governance completion**: full_auto actually works
- **Audit trail**: All notifications logged in database
- **Flexibility**: Monitors can trigger either deliverables or notifications

### Negative

- **New table**: Another table to maintain
- **Complexity**: Three concepts instead of one
- **Migration**: Existing event triggers need updating

### Mitigations

- Notifications table is simple and low-maintenance
- Clear documentation and ADR explain when to use what
- Phased rollout allows testing each piece

## Open Questions

1. **Push notification service**: Which service for mobile/desktop push? (Firebase? OneSignal?)
2. **In-app notification UI**: Where do in-app notifications appear?
3. **Notification preferences**: Per-channel preferences? Quiet hours?
4. **Monitor UI**: How do users create/manage monitors?

## Appendix: Clawdbot Heartbeat Pattern

Reference from `docs/research/CLAWDBOT_ANALYSIS.md`:

```
Clawdbot's "heartbeat" was a scheduled check-in that:
1. Gathered context (recent activity, calendar, etc.)
2. Decided if proactive message warranted
3. Sent via platform (Slack DM usually)

YARNNN equivalent:
- Monitors = the "decide if warranted" logic
- Notifications = the "send via platform" mechanism
- TP = can manually trigger either
```
