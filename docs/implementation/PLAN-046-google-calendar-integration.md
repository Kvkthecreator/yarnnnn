# Implementation Plan: Google Calendar Integration (ADR-046)

**Date**: 2026-02-11
**Estimated Effort**: 3-4 days
**Prerequisites**: Existing Google OAuth (Gmail) infrastructure

---

## Overview

Add Google Calendar as the fourth platform integration, leveraging existing Google OAuth infrastructure from Gmail. This enables time-triggered, person-aware deliverables like meeting prep and weekly previews.

---

## Phase 1: OAuth Scope Extension (Day 1)

### 1.1 Update OAuth Configuration

**File**: `api/integrations/core/oauth.py`

```python
# Rename provider from "gmail" to "google" for clarity
# Add calendar scopes

"google": OAuthConfig(
    provider="google",
    client_id_env="GOOGLE_CLIENT_ID",
    client_secret_env="GOOGLE_CLIENT_SECRET",
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    scopes=[
        # Gmail (existing)
        "https://www.googleapis.com/auth/gmail.readonly",
        # Calendar (new)
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events.readonly",
    ],
    redirect_path="/api/integrations/google/callback",
)
```

**Tasks**:
- [ ] Add calendar scopes to existing Google OAuth config
- [ ] Consider renaming `gmail` → `google` provider (or keep as alias)
- [ ] Update redirect path if renaming

### 1.2 Update Integration Routes

**File**: `api/routes/integrations.py`

**Tasks**:
- [ ] Add `/api/integrations/google/authorize` route (or alias gmail)
- [ ] Add `/api/integrations/google/callback` handler
- [ ] Update metadata extraction to include calendar capabilities

### 1.3 Update Token Exchange

**File**: `api/integrations/core/oauth.py` (exchange_code_for_token)

```python
# Add capabilities tracking to metadata
return {
    "user_id": user_id,
    "provider": "google",  # or keep "gmail" with capabilities
    "access_token_encrypted": token_manager.encrypt(data["access_token"]),
    "refresh_token_encrypted": token_manager.encrypt(data["refresh_token"]),
    "metadata": {
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "scope": data.get("scope"),
        "expires_at": expires_at.isoformat(),
        "capabilities": ["gmail", "calendar"],  # NEW
    },
    "status": IntegrationStatus.ACTIVE.value,
}
```

**Tasks**:
- [ ] Add `capabilities` field to metadata
- [ ] Parse scopes to determine which capabilities are enabled

### 1.4 Migration Path for Existing Gmail Users

**Options**:

A. **Prompt for re-auth** (simpler)
   - Show UI prompt: "Calendar features available! Reconnect Google to enable."
   - New auth flow includes both scopes

B. **Incremental scope upgrade** (more complex)
   - Gmail continues working
   - Calendar shows "Enable" button
   - Triggers partial re-auth for new scope

**Decision**: Option A for v1

**Tasks**:
- [ ] Add UI indicator for "Calendar available" on existing Gmail integrations
- [ ] Re-auth flow grants both scopes

---

## Phase 2: Calendar Data Fetch (Day 2)

### 2.1 Create Calendar Fetch Function

**File**: `api/services/deliverable_pipeline.py`

```python
async def _fetch_calendar_data(
    mcp_manager,
    token_manager,
    integration: dict,
    source_config: dict,
    context: GenerationContext,
) -> SourceFetchResult:
    """
    Fetch calendar events from Google Calendar API.

    source_config example:
    {
        "type": "integration_import",
        "provider": "calendar",
        "source": "primary",
        "filters": {
            "time_min": "now",
            "time_max": "+24h",  # or "+7d", or ISO date
            "attendee": "sarah@example.com",  # optional
        },
        "scope": {
            "max_items": 50,
            "include_description": true,
            "include_attendees": true,
        }
    }
    """
    # Get valid access token (refresh if needed)
    access_token = await get_valid_google_token(token_manager, integration)

    # Parse time filters
    time_min = parse_time_filter(source_config.get("filters", {}).get("time_min", "now"))
    time_max = parse_time_filter(source_config.get("filters", {}).get("time_max", "+7d"))

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "timeMin": time_min.isoformat() + "Z",
                "timeMax": time_max.isoformat() + "Z",
                "maxResults": source_config.get("scope", {}).get("max_items", 50),
                "singleEvents": True,
                "orderBy": "startTime",
            }
        )

        if response.status_code != 200:
            raise IntegrationError(f"Calendar API error: {response.text}")

        events = response.json().get("items", [])

    # Apply attendee filter if specified
    if source_config.get("filters", {}).get("attendee"):
        target_attendee = source_config["filters"]["attendee"].lower()
        events = [
            e for e in events
            if any(
                a.get("email", "").lower() == target_attendee
                for a in e.get("attendees", [])
            )
        ]

    # Format events for context
    formatted = format_calendar_events(events, source_config.get("scope", {}))

    return SourceFetchResult(
        content=formatted,
        items_fetched=len(events),
        metadata={
            "calendar_id": "primary",
            "time_range": f"{time_min} to {time_max}",
        }
    )
```

**Tasks**:
- [ ] Implement `_fetch_calendar_data()` function
- [ ] Implement `parse_time_filter()` for relative times ("+24h", "+7d", "now")
- [ ] Implement `format_calendar_events()` for markdown output
- [ ] Add to source dispatch in `fetch_integration_source_data()`

### 2.2 Calendar Event Formatting

```python
def format_calendar_events(
    events: list[dict],
    scope: dict,
) -> str:
    """Format calendar events as markdown for context."""

    if not events:
        return "No upcoming events in this time range."

    lines = ["## Upcoming Calendar Events\n"]

    for event in events:
        start = event.get("start", {})
        start_time = start.get("dateTime") or start.get("date")

        # Event header
        lines.append(f"### {event.get('summary', 'Untitled')}")
        lines.append(f"**When**: {format_datetime(start_time)}")

        # Attendees
        if scope.get("include_attendees", True):
            attendees = event.get("attendees", [])
            if attendees:
                attendee_names = [
                    a.get("displayName") or a.get("email")
                    for a in attendees
                    if not a.get("self")
                ]
                if attendee_names:
                    lines.append(f"**With**: {', '.join(attendee_names)}")

        # Description
        if scope.get("include_description", True):
            desc = event.get("description", "")
            if desc:
                lines.append(f"**Notes**: {desc[:500]}...")  # Truncate

        # Meeting link
        if event.get("hangoutLink"):
            lines.append(f"**Link**: {event['hangoutLink']}")

        lines.append("")  # Blank line between events

    return "\n".join(lines)
```

**Tasks**:
- [ ] Implement event formatting
- [ ] Handle all-day events vs. timed events
- [ ] Truncate long descriptions
- [ ] Include meeting links (Zoom, Meet, etc.)

### 2.3 Time Filter Utilities

```python
from datetime import datetime, timedelta
import re

def parse_time_filter(filter_str: str) -> datetime:
    """
    Parse relative or absolute time filter.

    Examples:
        "now" → current time
        "+24h" → 24 hours from now
        "+7d" → 7 days from now
        "2026-02-18" → specific date
        "2026-02-18T14:00:00" → specific datetime
    """
    if filter_str == "now":
        return datetime.utcnow()

    # Relative: +Xh or +Xd
    relative_match = re.match(r"\+(\d+)([hd])", filter_str)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        if unit == "h":
            return datetime.utcnow() + timedelta(hours=amount)
        elif unit == "d":
            return datetime.utcnow() + timedelta(days=amount)

    # Absolute: ISO format
    try:
        return datetime.fromisoformat(filter_str.replace("Z", "+00:00"))
    except ValueError:
        pass

    # Date only
    try:
        return datetime.strptime(filter_str, "%Y-%m-%d")
    except ValueError:
        pass

    raise ValueError(f"Invalid time filter: {filter_str}")
```

**Tasks**:
- [ ] Implement time filter parsing
- [ ] Handle timezone considerations
- [ ] Add unit tests

---

## Phase 3: Meeting Prep Deliverable (Day 2-3)

### 3.1 Add Meeting Prep Type

**File**: `web/types/index.ts`

```typescript
export type DeliverableType =
  // ... existing types ...

  // Calendar-triggered (ADR-046)
  | "meeting_prep"           // Context brief before a meeting
  | "weekly_calendar_preview" // Summary of upcoming week
  | "one_on_one_prep"        // 1:1-specific prep with history
```

**Tasks**:
- [ ] Add new deliverable types to TypeScript types
- [ ] Add type metadata (tier, description, etc.)

### 3.2 Meeting Prep Configuration

**File**: `web/types/index.ts` (or new config file)

```typescript
interface MeetingPrepConfig {
  type: "meeting_prep";

  // Which meetings to prep for
  meeting_filter: {
    time_window: "next_24h" | "next_48h" | "today";
    exclude_recurring?: boolean;  // Skip routine syncs
    min_attendees?: number;       // Only meetings with 2+ people
  };

  // Cross-platform context to pull
  context_sources: {
    slack_history?: {
      mode: "dm_with_attendees" | "channels";
      channels?: string[];
      lookback_days: number;
    };
    gmail_history?: {
      with_attendees: boolean;
      lookback_days: number;
    };
    notion_pages?: string[];
  };

  // Output sections
  sections: (
    | "meeting_details"
    | "attendee_context"
    | "recent_interactions"
    | "open_items"
    | "suggested_topics"
  )[];
}
```

**Tasks**:
- [ ] Define config schema for meeting prep
- [ ] Add to deliverable config types

### 3.3 Cross-Platform Attendee Context

**File**: `api/services/deliverable_pipeline.py`

```python
async def assemble_meeting_prep_context(
    events: list[dict],
    user_id: str,
    user_email: str,
    config: dict,
    mcp_manager,
    token_manager,
    integrations: dict,
) -> str:
    """
    Assemble cross-platform context for meeting prep.
    Pulls Slack/Gmail/Notion history with meeting attendees.
    """
    context_parts = []

    for event in events:
        attendees = [
            a.get("email") for a in event.get("attendees", [])
            if a.get("email") != user_email and not a.get("resource")
        ]

        if not attendees:
            continue

        event_context = [
            f"## {event.get('summary', 'Meeting')}",
            f"**When**: {format_datetime(event['start'])}",
            f"**With**: {', '.join(attendees)}",
            ""
        ]

        # Pull context for each attendee
        for attendee in attendees:
            attendee_context = await fetch_cross_platform_context_for_person(
                user_id=user_id,
                person_email=attendee,
                config=config.get("context_sources", {}),
                mcp_manager=mcp_manager,
                token_manager=token_manager,
                integrations=integrations,
            )

            if attendee_context:
                event_context.append(f"### Context with {attendee}")
                event_context.append(attendee_context)
                event_context.append("")

        context_parts.append("\n".join(event_context))

    return "\n---\n".join(context_parts)


async def fetch_cross_platform_context_for_person(
    user_id: str,
    person_email: str,
    config: dict,
    mcp_manager,
    token_manager,
    integrations: dict,
) -> str:
    """
    Fetch Slack DMs, Gmail threads, and Notion activity with a person.
    """
    parts = []

    # Slack: DMs with person
    if config.get("slack_history") and "slack" in integrations:
        slack_context = await fetch_slack_dm_history(
            integrations["slack"],
            person_email,
            lookback_days=config["slack_history"].get("lookback_days", 7),
            mcp_manager=mcp_manager,
            token_manager=token_manager,
        )
        if slack_context:
            parts.append(f"**Slack**:\n{slack_context}")

    # Gmail: Threads with person
    if config.get("gmail_history") and "google" in integrations:
        gmail_context = await fetch_gmail_with_person(
            integrations["google"],
            person_email,
            lookback_days=config["gmail_history"].get("lookback_days", 14),
            token_manager=token_manager,
        )
        if gmail_context:
            parts.append(f"**Email**:\n{gmail_context}")

    # Notion: Pages they've edited (future enhancement)
    # This requires more complex logic to find shared activity

    return "\n\n".join(parts) if parts else ""
```

**Tasks**:
- [ ] Implement `assemble_meeting_prep_context()`
- [ ] Implement `fetch_cross_platform_context_for_person()`
- [ ] Implement `fetch_slack_dm_history()` (find DM channel, fetch messages)
- [ ] Implement `fetch_gmail_with_person()` (search by from/to)

### 3.4 Meeting Prep Generation Prompt

**File**: `api/prompts/deliverable_prompts.py` (or similar)

```python
MEETING_PREP_PROMPT = """
You are preparing a meeting brief for the user.

## Meeting Details
{meeting_details}

## Context from Platforms
{platform_context}

## Instructions
Create a concise meeting prep brief with these sections:

1. **Meeting Overview** - Who, when, what (if known)
2. **Recent Context** - Key points from recent Slack/email interactions
3. **Open Items** - Things that seem unresolved or pending
4. **Suggested Topics** - Based on context, what might be worth discussing

Keep it scannable. The user will read this right before the meeting.
Highlight action items or unresolved questions prominently.
"""
```

**Tasks**:
- [ ] Create meeting prep generation prompt
- [ ] Handle edge cases (no context, many meetings, etc.)

### 3.5 Add to Deliverable Wizard

**File**: `web/components/wizards/DeliverableWizard.tsx` (or similar)

**Tasks**:
- [ ] Add "Meeting Prep" as deliverable type option
- [ ] Show Calendar icon
- [ ] Configure meeting filter options
- [ ] Configure which platforms to pull context from
- [ ] Set schedule (e.g., "30 min before meetings" or "daily at 8am")

---

## Phase 4: Additional Calendar Types (Day 3-4)

### 4.1 Weekly Calendar Preview

Simple deliverable that summarizes the week ahead.

```python
# Config
{
    "type": "weekly_calendar_preview",
    "schedule": {"day": "sunday", "time": "18:00"},
    "include": {
        "meeting_count": true,
        "external_meetings": true,
        "recurring_vs_adhoc": true,
        "free_blocks": true,
        "busiest_day": true,
    }
}
```

**Output example**:
```markdown
## Your Week Ahead (Feb 12-16)

**12 meetings** scheduled
- 3 external (clients, partners)
- 5 recurring (1:1s, standups)
- 4 ad-hoc

**Busiest day**: Wednesday (4 meetings)

**Longest free block**: Thursday 2-5pm

**Notable meetings**:
- Board meeting (Tue 10am) - 2 hours, 8 attendees
- Client kickoff with Acme (Wed 2pm) - external
```

**Tasks**:
- [ ] Implement weekly preview logic
- [ ] Calculate meeting statistics
- [ ] Identify free blocks
- [ ] Add to wizard

### 4.2 1:1 Prep

Specialized meeting prep for recurring 1:1s.

```python
# Config
{
    "type": "one_on_one_prep",
    "recurring_event_title": "1:1 with Sarah",  # or event_id
    "attendee_email": "sarah@company.com",
    "sections": [
        "last_meeting_notes",
        "slack_activity",
        "shared_projects",
        "suggested_topics"
    ],
    "lookback_days": 14,
}
```

**Tasks**:
- [ ] Detect recurring events by title pattern or ID
- [ ] Pull history from last occurrence
- [ ] More focused than general meeting prep
- [ ] Add to wizard with special 1:1 flow

---

## Phase 5: Frontend Updates (Day 4)

### 5.1 Integration Settings Card

Update Google integration card to show both Gmail and Calendar:

```tsx
// components/settings/IntegrationCard.tsx

<Card>
  <CardHeader>
    <GoogleIcon />
    <h3>Google</h3>
    <Badge variant="success">Connected</Badge>
  </CardHeader>
  <CardContent>
    <p className="text-muted">Account: {metadata.email}</p>

    <div className="capabilities">
      <div className="capability">
        <GmailIcon />
        <span>Gmail — Read inbox and threads</span>
        <CheckIcon className="text-green-500" />
      </div>
      <div className="capability">
        <CalendarIcon />
        <span>Calendar — Read events and attendees</span>
        <CheckIcon className="text-green-500" />
      </div>
    </div>
  </CardContent>
  <CardFooter>
    <Button variant="outline">Manage</Button>
    <Button variant="destructive">Disconnect</Button>
  </CardFooter>
</Card>
```

**Tasks**:
- [ ] Update integration card layout
- [ ] Show capabilities based on metadata
- [ ] Add icons for Gmail and Calendar

### 5.2 Deliverable Wizard Updates

**Tasks**:
- [ ] Add Calendar as platform icon in source selection
- [ ] Add meeting prep/weekly preview to type selection
- [ ] Add meeting filter configuration step
- [ ] Add cross-platform context source selection

### 5.3 Platform Icons

**Tasks**:
- [ ] Add Google Calendar icon to icon set
- [ ] Update `PlatformIcon` component

---

## Testing Plan

### Unit Tests

- [ ] `parse_time_filter()` - relative and absolute times
- [ ] `format_calendar_events()` - various event types
- [ ] `fetch_calendar_data()` - mock API responses

### Integration Tests

- [ ] OAuth flow with calendar scopes
- [ ] Calendar API fetch with real token
- [ ] Cross-platform context assembly

### E2E Tests

- [ ] Connect Google with Calendar
- [ ] Create meeting prep deliverable
- [ ] Generate meeting prep output
- [ ] Weekly preview generation

---

## Rollout Plan

### Stage 1: Internal Testing
- Deploy to staging
- Test with team calendars
- Validate cross-platform context

### Stage 2: Beta Users
- Enable for select users
- Gather feedback on meeting prep quality
- Iterate on prompts and formatting

### Stage 3: General Availability
- Enable for all users
- Update landing page
- Announce in changelog

---

## Files to Modify/Create

### New Files
- [ ] `api/services/calendar_fetch.py` (or add to pipeline)
- [ ] `docs/implementation/PLAN-046-google-calendar-integration.md` (this file)

### Modified Files
- [ ] `api/integrations/core/oauth.py` — Add calendar scopes
- [ ] `api/routes/integrations.py` — Update routes if renaming
- [ ] `api/services/deliverable_pipeline.py` — Add calendar fetch, meeting prep context
- [ ] `web/types/index.ts` — Add new deliverable types
- [ ] `web/components/settings/IntegrationCard.tsx` — Show capabilities
- [ ] `web/components/wizards/DeliverableWizard.tsx` — Add calendar types
- [ ] `docs/design/LANDING-PAGE-NARRATIVE-V2.md` — Already updated

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Calendar connection rate | 50%+ of Google users | `user_integrations` with calendar scope |
| Meeting prep creation | 20%+ of Calendar users | Deliverables with type = meeting_prep |
| Cross-platform usage | 70%+ meeting preps use 2+ platforms | Source config analysis |
| User satisfaction | Positive feedback | User surveys, support tickets |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Scope creep | Calendar read-only in v1, no write |
| API rate limits | Cache events, 15-min TTL |
| Token refresh issues | Reuse Gmail refresh logic |
| Privacy concerns | Clear UI showing what's accessed |

---

## Open Questions

1. **Provider naming**: Keep "gmail" and add "calendar" separate, or rename to "google"?
   - Recommendation: Rename to "google" with capabilities metadata

2. **Shared vs. primary calendar**: Should we support shared calendars?
   - Recommendation: Primary only for v1

3. **Event-triggered prep**: Generate prep X minutes before meeting?
   - Recommendation: Scheduled-only for v1, event triggers in v2

---

## References

- [ADR-046: Google Calendar Integration](../adr/ADR-046-google-calendar-integration.md)
- [Google Calendar API Docs](https://developers.google.com/calendar/api/v3/reference)
- [OAuth Scopes for Google Calendar](https://developers.google.com/calendar/api/auth)
