# ADR-002: Scheduling as First-Class Feature

## Status
Accepted

## Date
2026-01-28

## Context

YARNNN v5 is a knowledge work platform where users:
1. Accumulate context (blocks) about their work/projects
2. Trigger agent work (research, content, reporting)
3. Receive work outputs for review

The legacy YARNNN codebase had **no scheduling or notification system**. All work was on-demand—users had to actively check the platform.

Analysis of the sibling chat_companion repo revealed a mature scheduling system:
- Render cron jobs (every minute for messages, daily for pattern computation)
- Two-tier delivery (push + email)
- Time window flexibility
- Proactive intelligence (silence detection, pattern-based outreach)

We evaluated which patterns to adopt for YARNNN v5.

## Decision

### Scheduling: First-Class Feature

**Scheduled email digests are essential, not optional.**

The core value loop depends on delivery:
```
User adds context → Agent does work → Outputs delivered → User reviews
                                            ↑
                              (without this, outputs rot)
```

Without scheduling:
- Users must remember to check YARNNN (cognitive load)
- Work outputs sit unreviewed
- Platform becomes "another thing to check"
- Easy to abandon

With scheduling:
- YARNNN comes to the user
- Weekly digest surfaces what matters
- Consistent engagement without effort
- Outputs get reviewed and used

### Proactive Intelligence: Explicitly Out of Scope

Chat Companion's proactive features (silence detection, mood patterns, "thinking of you" messages) serve **relationship-building**. YARNNN serves **work execution**.

We reject these patterns because:
- "Haven't seen you in 3 days" feels guilt-inducing for a work tool
- Pattern-based personality adaptation adds complexity without value
- Emotional engagement optimization is wrong for a professional tool

**YARNNN optimizes for utility, not engagement.**

### Push Notifications: Deferred

Push notifications require:
- Mobile app infrastructure (React Native, Expo)
- Device registration and token management
- Platform-specific configuration (APNs, FCM)

Email is sufficient for MVP and matches the "professional work tool" positioning. Users check email; we meet them there.

## Implementation

### Phase 1 (Current)
- On-demand work execution
- No notifications

### Phase 2 (Scheduling)
- Weekly digest emails per workspace
- Render cron job (hourly check for due digests)
- Email via Resend (or similar transactional service)
- User controls: enable/disable, preferred day/time, timezone

### Database Schema (Phase 2)

```sql
-- Workspace digest preferences
ALTER TABLE workspaces ADD COLUMN digest_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE workspaces ADD COLUMN digest_day INTEGER DEFAULT 1; -- 0=Sun, 1=Mon, etc.
ALTER TABLE workspaces ADD COLUMN digest_hour INTEGER DEFAULT 9; -- 0-23 in user timezone
ALTER TABLE workspaces ADD COLUMN digest_timezone TEXT DEFAULT 'UTC';

-- Scheduled messages
CREATE TABLE scheduled_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    scheduled_for TIMESTAMPTZ NOT NULL,
    message_type TEXT NOT NULL, -- 'weekly_digest', 'work_complete', etc.
    content JSONB NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, sent, failed
    sent_at TIMESTAMPTZ,
    failure_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Cron Job Structure

```
api/jobs/
  scheduler.py      # Main scheduler entry point
  digest.py         # Digest generation logic
  email.py          # Email delivery (Resend)
```

Render cron runs hourly:
1. Query workspaces where `digest_enabled = true` and due this hour
2. For each workspace:
   - Gather recent activity (work tickets, outputs, new blocks)
   - Generate digest content
   - Send email
   - Record in scheduled_messages

## Consequences

### Positive
- Users receive value without active engagement
- Work outputs get reviewed
- Clear path to expand (more message types, different frequencies)
- Simple implementation (cron + email, no queues)

### Negative
- Must manage email deliverability (SPF, DKIM, reputation)
- Digest generation adds API compute
- Users may get "empty" digests (mitigate: skip if no activity)

### Neutral
- Push notifications remain an option for future mobile app
- No complex task queue infrastructure needed

## References

- Legacy YARNNN: No scheduling found
- chat_companion: Full scheduling with push + email
- Render cron documentation: https://render.com/docs/cronjobs
- Resend email API: https://resend.com/docs
