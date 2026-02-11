# ADR-040: Implementation Gaps Analysis

> **Companion document to ADR-040**
> **Date**: 2026-02-11

This document maps the current state of each component to the required changes for ADR-040 implementation.

---

## 1. Delivery Service

**File**: `api/services/delivery.py`

### Current State
- Governance levels defined: `manual`, `semi_auto`, `full_auto`
- Delivery pipeline: gather → synthesize → stage → approve → deliver
- `execute_delivery()` handles final export to destinations
- No notification calls at any pipeline stage

### Required Changes

```diff
# After staging (manual governance)
+ await send_notification(
+     user_id=deliverable.user_id,
+     message=f"'{deliverable.title}' is ready for review",
+     channel="in_app",
+     source_type="deliverable",
+     source_id=instance_id
+ )

# After delivery (semi_auto governance)
+ await send_notification(
+     user_id=deliverable.user_id,
+     message=f"'{deliverable.title}' delivered to {destination}",
+     channel="in_app",
+     urgency="low",
+     source_type="deliverable",
+     source_id=instance_id
+ )

# On delivery failure
+ await send_notification(
+     user_id=deliverable.user_id,
+     message=f"Delivery failed for '{deliverable.title}': {error}",
+     channel="in_app",
+     urgency="high",
+     source_type="deliverable",
+     source_id=instance_id
+ )
```

### Full-Auto Governance
Currently, even `full_auto` deliverables require approval. Need to add:

```python
if governance == "full_auto":
    # Skip approval, deliver immediately
    result = await execute_delivery(instance)
    # Optionally log/notify at low priority
    return result
```

---

## 2. Event Triggers

**File**: `api/services/event_triggers.py`

### Current State
- `PlatformEvent` dataclass for normalized events
- `get_deliverables_for_event()` matches events to deliverables
- `execute_event_triggers()` runs matched deliverables
- Cooldown in-memory (`_cooldown_cache` dict)
- No event logging
- Only triggers deliverables, not notifications

### Required Changes

#### 2.1 Database Cooldown (replace in-memory)

```sql
CREATE TABLE event_trigger_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    deliverable_id UUID,
    monitor_id UUID,

    -- Event info
    platform TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_id TEXT,
    event_data JSONB,

    -- Cooldown key
    cooldown_key TEXT NOT NULL,

    -- Timestamps
    triggered_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id)
);

CREATE INDEX idx_trigger_log_cooldown ON event_trigger_log(cooldown_key, triggered_at DESC);
```

```python
# Replace _cooldown_cache with database queries
async def check_cooldown(db_client, deliverable_id, cooldown, event):
    key = _get_cooldown_key(deliverable_id, cooldown.type, event)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=cooldown.duration_minutes)

    result = db_client.table("event_trigger_log")\
        .select("triggered_at")\
        .eq("cooldown_key", key)\
        .gte("triggered_at", cutoff.isoformat())\
        .limit(1)\
        .execute()

    if result.data:
        return True, "In cooldown"
    return False, None
```

#### 2.2 Support Notification-Only Triggers

```python
@dataclass
class TriggerMatch:
    deliverable_id: Optional[str]  # Now optional
    notification_template: Optional[str]  # New field
    action_type: Literal["trigger_deliverable", "send_notification", "both"]
    # ... existing fields
```

#### 2.3 Event Logging

```python
async def log_trigger_event(db_client, event, match, result):
    """Log every trigger for audit trail."""
    db_client.table("event_trigger_log").insert({
        "user_id": event.user_id,
        "deliverable_id": match.deliverable_id,
        "monitor_id": match.monitor_id,
        "platform": event.platform,
        "event_type": event.event_type,
        "resource_id": event.resource_id,
        "cooldown_key": _get_cooldown_key(...),
        "event_data": event.event_data,
    }).execute()
```

---

## 3. TP Tools

**File**: `api/services/project_tools.py`

### Current State
- `THINKING_PARTNER_TOOLS` includes platform operation tools (ADR-039)
- No notification-sending capability
- TP can create deliverables but not send lightweight alerts

### Required Changes

#### 3.1 Add send_notification Tool

```python
SEND_NOTIFICATION_TOOL = {
    "name": "send_notification",
    "description": """Send a lightweight notification to the user.

    Use this for:
    - Alerting about something you noticed
    - Confirming an action completed
    - Proactive insights that don't need a full deliverable

    WHEN TO USE:
    - Quick alerts: "Your Slack sync completed"
    - Observations: "I noticed 3 urgent emails from Sarah"
    - Confirmations: "I've updated your weekly digest settings"

    WHEN NOT TO USE (use deliverables instead):
    - Recurring content (digests, summaries)
    - Content that needs review/approval
    - Anything that should be scheduled
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The notification message (keep concise)"
            },
            "channel": {
                "type": "string",
                "enum": ["in_app", "email", "slack_dm"],
                "default": "in_app",
                "description": "How to deliver"
            },
            "urgency": {
                "type": "string",
                "enum": ["low", "normal", "high"],
                "default": "normal"
            },
            "context": {
                "type": "object",
                "description": "Related context (deliverable_id, url, etc.)"
            }
        },
        "required": ["message"]
    }
}

# Add to THINKING_PARTNER_TOOLS
THINKING_PARTNER_TOOLS = [
    # ... existing tools ...
    SEND_NOTIFICATION_TOOL,
]

# Add handler
async def handle_send_notification(auth, input: dict) -> dict:
    from services.notifications import send_notification

    result = await send_notification(
        user_id=auth.user_id,
        message=input["message"],
        channel=input.get("channel", "in_app"),
        urgency=input.get("urgency", "normal"),
        context=input.get("context"),
        source_type="tp"
    )

    return {
        "success": True,
        "notification_id": result["id"],
        "message": f"Notification sent via {input.get('channel', 'in_app')}"
    }
```

---

## 4. Notification Service (New)

**New File**: `api/services/notifications.py`

### Required Implementation

```python
"""
Notification Service - ADR-040

Lightweight notification delivery separate from deliverables.
"""

import logging
from datetime import datetime, timezone
from typing import Literal, Optional
from dataclasses import dataclass

from db import get_client

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    id: str
    status: Literal["sent", "pending", "failed"]
    error: Optional[str] = None


async def send_notification(
    user_id: str,
    message: str,
    channel: Literal["in_app", "email", "slack_dm", "push"] = "in_app",
    urgency: Literal["low", "normal", "high"] = "normal",
    context: Optional[dict] = None,
    source_type: Literal["system", "monitor", "tp", "deliverable"] = "system",
    source_id: Optional[str] = None,
) -> NotificationResult:
    """
    Send a notification to a user.

    Args:
        user_id: Target user
        message: Notification text
        channel: Delivery channel
        urgency: Priority level
        context: Optional related context
        source_type: What triggered this notification
        source_id: ID of triggering entity

    Returns:
        NotificationResult with status
    """
    client = get_client()

    # Create notification record
    notification = client.table("notifications").insert({
        "user_id": user_id,
        "message": message,
        "channel": channel,
        "urgency": urgency,
        "context": context or {},
        "source_type": source_type,
        "source_id": source_id,
        "status": "pending",
    }).execute()

    notification_id = notification.data[0]["id"]

    # Deliver based on channel
    try:
        if channel == "in_app":
            # In-app notifications are already "delivered" by being in the table
            # Frontend polls/subscribes to notifications table
            status = "sent"

        elif channel == "email":
            from jobs.unified_scheduler import send_notification_email
            await send_notification_email(user_id, message, context)
            status = "sent"

        elif channel == "slack_dm":
            from integrations.exporters.slack import SlackExporter
            # Use DM draft mechanism
            # ... implementation
            status = "sent"

        elif channel == "push":
            # Future: Firebase/OneSignal integration
            logger.warning(f"Push notifications not yet implemented")
            status = "pending"

        # Update status
        client.table("notifications").update({
            "status": status,
            "sent_at": datetime.now(timezone.utc).isoformat() if status == "sent" else None
        }).eq("id", notification_id).execute()

        logger.info(f"[NOTIFICATION] Sent to {user_id} via {channel}: {message[:50]}...")

        return NotificationResult(id=notification_id, status=status)

    except Exception as e:
        logger.error(f"[NOTIFICATION] Failed: {e}")

        client.table("notifications").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", notification_id).execute()

        return NotificationResult(id=notification_id, status="failed", error=str(e))


async def get_user_notifications(
    user_id: str,
    status: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Get notifications for a user (for in-app display)."""
    client = get_client()

    query = client.table("notifications")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .limit(limit)

    if status:
        query = query.eq("status", status)

    result = query.execute()
    return result.data or []


async def dismiss_notification(notification_id: str, user_id: str) -> bool:
    """Mark a notification as dismissed."""
    client = get_client()

    result = client.table("notifications").update({
        "status": "dismissed"
    }).eq("id", notification_id).eq("user_id", user_id).execute()

    return len(result.data) > 0
```

---

## 5. Frontend: In-App Notifications

**Files**: `web/components/`, `web/contexts/`

### Required Changes

#### 5.1 Notification Context

```typescript
// web/contexts/NotificationContext.tsx

interface Notification {
  id: string;
  message: string;
  channel: string;
  urgency: 'low' | 'normal' | 'high';
  context?: Record<string, unknown>;
  source_type: string;
  created_at: string;
  status: string;
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  dismiss: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
}
```

#### 5.2 Notification Bell/Panel

```typescript
// web/components/NotificationBell.tsx
// - Bell icon with unread count badge
// - Dropdown/panel showing recent notifications
// - Click to dismiss or navigate to context
```

#### 5.3 Real-time Updates

```typescript
// Subscribe to notifications table changes
useEffect(() => {
  const channel = supabase
    .channel('notifications')
    .on('postgres_changes', {
      event: 'INSERT',
      schema: 'public',
      table: 'notifications',
      filter: `user_id=eq.${userId}`
    }, (payload) => {
      // Add to notifications list
      // Show toast for high urgency
    })
    .subscribe();

  return () => supabase.removeChannel(channel);
}, [userId]);
```

---

## 6. Database Migrations

### Migration 1: notifications table

```sql
-- migrations/20260211_create_notifications.sql

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),

    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',

    channel TEXT NOT NULL CHECK (channel IN ('push', 'email', 'slack_dm', 'in_app')),
    urgency TEXT DEFAULT 'normal' CHECK (urgency IN ('low', 'normal', 'high')),

    source_type TEXT NOT NULL CHECK (source_type IN ('system', 'monitor', 'tp', 'deliverable')),
    source_id UUID,

    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'dismissed')),
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

CREATE INDEX idx_notifications_user_status ON notifications(user_id, status);
CREATE INDEX idx_notifications_user_created ON notifications(user_id, created_at DESC);

-- RLS policies
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own notifications"
    ON notifications FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own notifications"
    ON notifications FOR UPDATE
    USING (auth.uid() = user_id);
```

### Migration 2: event_trigger_log table

```sql
-- migrations/20260211_create_event_trigger_log.sql

CREATE TABLE event_trigger_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    deliverable_id UUID REFERENCES deliverables(id),
    monitor_id UUID,

    platform TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_id TEXT,
    event_data JSONB,

    cooldown_key TEXT NOT NULL,

    triggered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trigger_log_cooldown ON event_trigger_log(cooldown_key, triggered_at DESC);
CREATE INDEX idx_trigger_log_user ON event_trigger_log(user_id, triggered_at DESC);

-- RLS policies
ALTER TABLE event_trigger_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own trigger logs"
    ON event_trigger_log FOR SELECT
    USING (auth.uid() = user_id);
```

---

## 7. Implementation Order

### Phase 1: Foundation (Required First)
1. ✅ Create `notifications` table migration
2. ✅ Create `api/services/notifications.py`
3. ✅ Basic in-app notification delivery

### Phase 2: TP Integration
4. Add `send_notification` tool to TP
5. Wire delivery.py → notifications for staged instances

### Phase 3: Governance Completion
6. Implement full_auto governance (skip approval)
7. Wire delivery.py → notifications for delivery outcomes

### Phase 4: Event Triggers
8. Create `event_trigger_log` table migration
9. Replace in-memory cooldown with database
10. Add notification-only trigger support

### Phase 5: Frontend
11. NotificationContext and provider
12. NotificationBell component
13. Real-time subscription

### Phase 6: Monitors (Future)
14. Monitors table and service
15. Monitor management UI
16. Monitor → trigger wiring

---

## Summary

| Gap | Priority | Effort | Dependencies |
|-----|----------|--------|--------------|
| Notifications table | P0 | Small | None |
| Notification service | P0 | Medium | Table |
| TP send_notification tool | P1 | Small | Service |
| Delivery → notification wiring | P1 | Medium | Service |
| Full-auto governance | P1 | Small | Service |
| Event trigger logging | P2 | Medium | Table |
| Database cooldown | P2 | Medium | Log table |
| Frontend notifications | P2 | Medium | Service |
| Monitors | P3 | Large | All above |
