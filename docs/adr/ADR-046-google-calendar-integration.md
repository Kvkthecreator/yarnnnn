# ADR-046: Google Calendar Integration

**Date**: 2026-02-11
**Status**: Proposed
**Relates to**: ADR-031 (Platform-Native), ADR-044 (Type Reconceptualization), DECISION-001 (Platform Sync)

---

## Context

YARNNN currently integrates with three platforms:
- **Slack** — Team communication, channel discussions
- **Gmail** — Email threads, inbox management
- **Notion** — Documentation, project notes

These platforms provide **content context** — what happened, what was discussed, what was documented. However, a critical dimension is missing:

**Time and people context.**

Users' calendars contain:
- Who they meet with (and when)
- Recurring patterns (1:1s, team syncs, client calls)
- Meeting metadata (attendees, descriptions, links)
- The rhythm of their work week

This context is the **connective tissue** between other platforms. A meeting with Sarah naturally connects to:
- Recent Slack DMs with Sarah
- Email threads with Sarah
- Notion docs Sarah has edited

### Why Calendar is the Next Platform

| Factor | Assessment |
|--------|------------|
| **OAuth** | Already have Google OAuth from Gmail—same credentials, add scope |
| **MCP Server** | `@anthropic/mcp-server-google-calendar` or similar exists |
| **Data Model** | Simple: events with title, time, attendees, description |
| **Signals** | Clear: upcoming meetings, attendees, recurring patterns |
| **Cross-Platform Value** | Calendar events connect to people across all other platforms |

### Deliverable Types Unlocked

Calendar enables a new category of **time-triggered, person-aware** deliverables:

1. **Meeting Prep Brief** — Context for upcoming meetings from Slack/Gmail/Notion
2. **Weekly Preview** — "Your week: 12 meetings, 3 external, 2 recurring 1:1s"
3. **1:1 Prep** — Combine calendar + Slack history + last meeting notes
4. **Post-Meeting Summary** — Triggered after calendar event ends
5. **Availability Summary** — "Your free blocks this week" for planning

---

## Decision

Add Google Calendar as the fourth platform integration, leveraging existing Google OAuth infrastructure.

### Integration Approach

**Reuse Gmail's Google OAuth flow** with expanded scopes:

```python
# Current Gmail scopes
"https://www.googleapis.com/auth/gmail.readonly"

# Add Calendar scopes
"https://www.googleapis.com/auth/calendar.readonly"
"https://www.googleapis.com/auth/calendar.events.readonly"
```

**Two implementation options:**

| Option | Approach | Effort | Recommendation |
|--------|----------|--------|----------------|
| A | Shared Google integration (Gmail + Calendar) | Lower | **Recommended for v1** |
| B | Separate Calendar integration | Higher | Future if users want Calendar without Gmail |

**Decision**: Option A — Extend existing Gmail integration to include Calendar scopes.

Users connecting "Google" get access to both Gmail and Calendar data. The UI shows them as capabilities of the Google integration.

---

## Architecture

### 1. OAuth Scope Extension

```python
# oauth.py - Updated Gmail/Google config
"google": OAuthConfig(
    provider="google",  # Renamed from "gmail"
    client_id_env="GOOGLE_CLIENT_ID",
    client_secret_env="GOOGLE_CLIENT_SECRET",
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    scopes=[
        # Gmail
        "https://www.googleapis.com/auth/gmail.readonly",
        # Calendar (new)
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events.readonly",
    ],
    redirect_path="/api/integrations/google/callback",
)
```

**Migration note**: Existing Gmail integrations continue to work. Calendar features require re-auth to add new scopes.

### 2. Calendar Data Fetch

```python
# deliverable_pipeline.py - New fetch function
async def _fetch_calendar_data(
    user_id: str,
    integration: dict,
    source_config: dict,
    context: GenerationContext
) -> SourceFetchResult:
    """
    Fetch calendar events for context extraction.

    Source config:
    {
        "type": "integration_import",
        "provider": "calendar",
        "source": "primary",  # or specific calendar ID
        "filters": {
            "time_min": "now",
            "time_max": "+7d",  # or "2026-02-18"
            "attendee": "sarah@company.com",  # optional filter
            "recurring": true,  # only recurring events
        },
        "scope": {
            "max_items": 50,
            "include_description": true,
            "include_attendees": true,
        }
    }
    """
    # Use Google Calendar API directly (like Gmail)
    # MCP server available but direct API is simpler for read-only

    access_token = await get_valid_google_token(integration)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "timeMin": compute_time_min(source_config),
                "timeMax": compute_time_max(source_config),
                "maxResults": source_config.get("scope", {}).get("max_items", 50),
                "singleEvents": True,  # Expand recurring events
                "orderBy": "startTime",
            }
        )
        events = response.json().get("items", [])

    # Format for context
    formatted = format_calendar_events(events, source_config)

    return SourceFetchResult(
        content=formatted,
        items_fetched=len(events),
        metadata={"calendar_id": "primary", "time_range": "..."}
    )
```

### 3. Calendar-Specific Signals

Unlike content platforms, Calendar provides **temporal and relational signals**:

| Signal | Description | Use Case |
|--------|-------------|----------|
| **Attendees** | Who you're meeting with | Cross-reference with Slack/Gmail history |
| **Recurrence** | Meeting patterns (weekly 1:1, monthly board) | Identify stakeholder relationships |
| **Time proximity** | "Meeting in 2 hours" vs "meeting last week" | Urgency for prep briefs |
| **Meeting type** | 1:1, team sync, external, interview | Context for content tone |
| **Duration** | 30min vs 2hr | Depth of prep needed |
| **Description/Agenda** | Meeting notes, links | Additional context |

### 4. New Deliverable Types

```typescript
// types/index.ts - New calendar-related types
export type DeliverableType =
  // ... existing types ...

  // Calendar-triggered (ADR-046)
  | "meeting_prep"           // Context brief before a meeting
  | "weekly_calendar_preview" // Summary of upcoming week
  | "one_on_one_prep"        // 1:1-specific prep with history
  | "post_meeting_summary"   // Follow-up after meeting ends
```

#### Type Configurations

```typescript
interface MeetingPrepConfig {
  type: "meeting_prep";

  // Which meeting(s) to prep for
  meeting_filter: {
    time_window: "next_24h" | "next_48h" | "specific_event";
    event_id?: string;  // If specific_event
    attendee_filter?: string[];  // Only meetings with these people
    exclude_recurring?: boolean;  // Skip routine syncs
  };

  // What context to pull
  context_sources: {
    slack_history?: {
      channels: string[];  // Or "dm_with_attendees"
      lookback_days: number;
    };
    gmail_history?: {
      with_attendees: boolean;
      lookback_days: number;
    };
    notion_pages?: string[];  // Related project pages
    previous_meeting_notes?: boolean;
  };

  // Output structure
  sections: ("attendee_context" | "recent_interactions" | "open_items" | "suggested_topics")[];
}

interface WeeklyCalendarPreviewConfig {
  type: "weekly_calendar_preview";

  // What to include
  include: {
    meeting_count: boolean;
    external_meetings: boolean;
    recurring_vs_adhoc: boolean;
    free_blocks: boolean;
    busiest_day: boolean;
  };

  // Schedule
  schedule: {
    day: "sunday" | "monday";
    time: string;  // "08:00"
  };
}

interface OneOnOnePrepConfig {
  type: "one_on_one_prep";

  // The recurring 1:1 to prep for
  recurring_event_id: string;
  attendee_email: string;

  // What to include
  sections: (
    | "last_meeting_notes"
    | "slack_activity"
    | "shared_projects"
    | "open_questions"
    | "suggested_topics"
  )[];

  // How far back to look
  lookback_days: number;
}
```

### 5. Cross-Platform Context Assembly

Calendar's unique value is connecting **people** across platforms:

```python
async def assemble_meeting_prep_context(
    meeting: CalendarEvent,
    user_id: str,
    config: MeetingPrepConfig
) -> dict:
    """
    Pull context for a meeting from all relevant sources.
    """
    attendees = [a["email"] for a in meeting.get("attendees", [])]

    context = {
        "meeting": {
            "title": meeting["summary"],
            "time": meeting["start"]["dateTime"],
            "attendees": attendees,
            "description": meeting.get("description", ""),
        },
        "context_by_attendee": {}
    }

    for attendee in attendees:
        if attendee == user_email:
            continue  # Skip self

        attendee_context = {}

        # Slack: Recent DMs and shared channel activity
        if config.context_sources.get("slack_history"):
            attendee_context["slack"] = await fetch_slack_with_person(
                user_id, attendee,
                lookback_days=config.context_sources["slack_history"]["lookback_days"]
            )

        # Gmail: Recent email threads
        if config.context_sources.get("gmail_history"):
            attendee_context["gmail"] = await fetch_gmail_with_person(
                user_id, attendee,
                lookback_days=config.context_sources["gmail_history"]["lookback_days"]
            )

        # Notion: Pages they've edited or are mentioned in
        if config.context_sources.get("notion_pages"):
            attendee_context["notion"] = await fetch_notion_with_person(
                user_id, attendee
            )

        context["context_by_attendee"][attendee] = attendee_context

    return context
```

---

## Data Model

### Calendar Source in Deliverables

```sql
-- No new tables needed, use existing integration_import pattern

-- Example deliverable source config for meeting prep:
{
  "sources": [
    {
      "type": "integration_import",
      "provider": "calendar",
      "source": "primary",
      "filters": {
        "time_min": "now",
        "time_max": "+24h"
      }
    },
    {
      "type": "integration_import",
      "provider": "slack",
      "source": "dm_with_attendees",  -- Special source type
      "filters": {
        "after": "7d"
      }
    }
  ]
}
```

### Integration Metadata Update

```sql
-- user_integrations.metadata for Google integration
{
  "email": "user@company.com",
  "name": "User Name",
  "picture": "https://...",
  "scope": "gmail.readonly calendar.readonly calendar.events.readonly",
  "expires_at": "2026-02-11T15:00:00Z",
  "capabilities": ["gmail", "calendar"]  -- Track what's enabled
}
```

---

## Frontend Changes

### Integration Settings

Update Google integration card to show both capabilities:

```
┌─────────────────────────────────────────────────────────────┐
│ 🔗 Google                                     [Connected ✓] │
│   Account: user@company.com                                 │
│                                                             │
│   Capabilities:                                             │
│   ✓ Gmail — Read inbox and threads                         │
│   ✓ Calendar — Read events and attendees                   │
│                                                             │
│   [Manage] [Disconnect]                                     │
└─────────────────────────────────────────────────────────────┘
```

### Deliverable Creation

Add calendar-triggered types to wizard:

```
What kind of deliverable?

┌─────────────────────────────────────────────────────────────┐
│ 📅 Meeting Prep                                              │
│    Get context for upcoming meetings                         │
│    Pulls from: Calendar + Slack + Gmail                      │
├─────────────────────────────────────────────────────────────┤
│ 📅 Weekly Preview                                            │
│    Summary of your week ahead                                │
│    Pulls from: Calendar                                      │
├─────────────────────────────────────────────────────────────┤
│ 📅 1:1 Prep                                                  │
│    Prepare for recurring 1:1s                                │
│    Pulls from: Calendar + Slack + last meeting notes         │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: OAuth Scope Extension (Day 1)

1. Rename `gmail` provider to `google` in oauth.py
2. Add calendar scopes to Google OAuth config
3. Update integration routes for `/api/integrations/google/*`
4. Add migration path for existing Gmail integrations
5. Update frontend integration card

**Deliverable**: Users can connect Google with Calendar access

### Phase 2: Calendar Data Fetch (Day 2)

1. Implement `_fetch_calendar_data()` in pipeline
2. Add calendar event formatting
3. Add time window parsing utilities
4. Test with basic calendar fetch

**Deliverable**: Calendar events available as source data

### Phase 3: Meeting Prep Deliverable (Day 2-3)

1. Add `meeting_prep` deliverable type
2. Implement cross-platform attendee context assembly
3. Create generation prompt for meeting prep
4. Add to deliverable wizard

**Deliverable**: First calendar-triggered deliverable working

### Phase 4: Additional Types (Day 3-4)

1. Weekly calendar preview
2. 1:1 prep (with recurring event detection)
3. Post-meeting summary (event-triggered, future)

**Deliverable**: Full calendar deliverable suite

### Phase 5: Landing Page Update (Day 4)

1. Add Calendar to platform list
2. Update narrative for time-triggered deliverables
3. Add meeting prep to use case examples

**Deliverable**: Marketing reflects Calendar capability

---

## Migration Path

### Existing Gmail Users

Option 1 (Simple): Require re-auth for Calendar
- Show prompt: "Calendar features available! Reconnect Google to enable."
- New auth includes both scopes

Option 2 (Graceful): Incremental scope request
- Gmail features continue working
- Calendar features show "Enable Calendar" prompt
- Clicking triggers scope upgrade flow

**Decision**: Option 1 for v1. Simpler, and Calendar is a clear value-add.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| **Scope creep** | Calendar read-only in v1, no write operations |
| **Privacy concerns** | Clear UI showing what Calendar access enables |
| **Token refresh complexity** | Already handled for Gmail, same flow |
| **Rate limits** | Cache calendar data like other platforms (15-min TTL) |
| **External calendar access** | Start with primary calendar only |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Calendar connection rate | 50%+ of Google-connected users |
| Meeting prep adoption | 20%+ of Calendar users create meeting prep |
| Cross-platform richness | Meeting prep pulls from 2+ platforms |
| Time saved | Qualitative feedback on meeting prep value |

---

## Future Considerations

### Event-Triggered Deliverables (Future)

Calendar enables event-based triggers:
- "30 minutes before meeting" → Generate prep brief
- "Meeting ended" → Generate follow-up summary
- "New meeting added" → Suggest prep deliverable

Requires webhook infrastructure (Phase 4 of ADR-031).

### Calendar Write Operations (Future)

With write scopes, could:
- Create calendar events from deliverables
- Add meeting notes to event descriptions
- Schedule follow-up meetings

Deferred to v2.

### Shared Calendar Access (Future)

Team calendars, shared calendars for:
- Team availability synthesis
- Cross-team meeting coordination
- Project timeline tracking

Requires additional scopes and UX for calendar selection.

---

## Related Documents

- [ADR-031: Platform-Native Deliverables](./ADR-031-platform-native-deliverables.md)
- [ADR-044: Deliverable Type Reconceptualization](./ADR-044-deliverable-type-reconceptualization.md)
- [DECISION-001: Platform Sync Strategy](../product/DECISION-001-platform-sync-strategy.md)
- [LANDING-PAGE-NARRATIVE-V2](../design/LANDING-PAGE-NARRATIVE-V2.md)
