# ADR-051: Platform Context Page Patterns

**Status**: Accepted
**Date**: 2026-02-12
**Related**: ADR-030, ADR-033, ADR-046, ADR-050

## Context

Each platform integration (Slack, Gmail, Notion, Calendar) has a dedicated context page at `/context/[platform]`. These pages need consistent UX patterns while accommodating platform-specific differences.

## Decision

### Universal Pattern: Resources as Context Sources

All platforms follow the same fundamental pattern:

```
┌─────────────────────────────────────────────────────────┐
│ CONTEXT SOURCES (Input)                                 │
│ "Select which [resources] to include as context"        │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ☑ Resource Name              Synced 2 hours ago    │ │
│ │ ☐ Resource Name              Not synced            │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ OUTPUT DESTINATION (if applicable)                      │
│ "Where TP writes outputs by default"                    │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📄 Designated resource                    [Change]  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ DELIVERABLES                                            │
│ Active deliverables using this platform                 │
└─────────────────────────────────────────────────────────┘
```

### Platform-Specific Resources

| Platform | Resource Type | Resource Label | Sync Behavior |
|----------|--------------|----------------|---------------|
| Slack | Channels | Channels | Messages from selected channels |
| Gmail | Labels | Labels | Emails with selected labels |
| Notion | Pages | Pages | Content from selected pages |
| Calendar | Calendars | Calendars | Events from selected calendars |

### Resource Row Information

Each resource row displays:
1. **Checkbox** - Selection state
2. **Icon** - Platform-specific resource icon
3. **Name** - Resource name (channel name, label, page title, calendar name)
4. **Badges** - Platform-specific indicators:
   - Calendar: "Primary" badge for primary calendar
   - Notion: "Database" badge for database resources
   - Slack: Lock icon for private channels
5. **Metadata** - Platform-specific details:
   - Slack: member count + sync status
   - Gmail: sync status
   - Notion: parent type (Top-level page | Nested page | Database item) + sync status
   - Calendar: "Events queried on-demand" (no sync concept)
6. **Sync status** (non-Calendar):
   - Items extracted count
   - Last synced timestamp (e.g., "synced 2 hours ago")
7. **Coverage badge** (non-Calendar): Synced | Partial | Stale | Not synced

### Output Destinations (ADR-050)

Some platforms support "designated outputs" - default locations for TP to write:

| Platform | Output Type | Purpose |
|----------|------------|---------|
| Notion | Designated Page | Where TP adds comments/outputs |
| Calendar | Designated Calendar | Where TP creates events |
| Gmail | User's email | Auto-detected from OAuth, used for drafts |
| Slack | (none) | Messages go to specific channels per deliverable |

### Section Ordering

1. **Context Sources** (input) - Always first, primary action
2. **Output Destination** (if applicable) - Second, clearly labeled as "for outputs"
3. **Deliverables** - Third, shows what's using this platform
4. **Recent Context** - Fourth, shows extracted memories/facts

### Tier Limits

Each resource type has tier-based limits:
- `slack_channels`: Channels selectable
- `gmail_labels`: Labels selectable
- `notion_pages`: Pages selectable
- `calendar_events`: Calendars selectable (note: limit name may need update)

## Key Implementation Notes

### Calendar-Specific Considerations

Calendar differs from other platforms:
1. **No landscape endpoint** - Uses `listGoogleCalendars()` instead of `getLandscape()`
2. **Shared OAuth** - Uses Google OAuth shared with Gmail
3. **Time-based context** - Events are queried by time range, not synced wholesale
4. **Cross-platform synthesis** - Calendar events connect people across platforms (attendees link to Slack DMs, email threads)

### Future Cross-Platform Synthesis

Resources from all platforms contribute to cross-platform deliverables. Example scenario:
> User sees "Chad" mentioned meeting in Slack → Calendar has the event → TP creates reminder email with Slack context + Calendar details + Notion page link

This requires all platforms to be first-class context sources with consistent selection patterns.

## Consequences

### Positive
- Consistent UX across all platforms
- Clear mental model: select sources → get context → create deliverables
- Extensible to new platforms
- Supports cross-platform synthesis

### Negative
- Calendar's time-based nature requires different UX (hidden sync badge, on-demand query messaging)

## Implementation Status (2026-02-12)

| Platform | Output Section | Resource Metadata | Sync Display | Status |
|----------|---------------|-------------------|--------------|--------|
| Slack | N/A | member count | Standard sync | ✅ Complete |
| Gmail | Output Email (user's email) | - | Standard sync | ✅ Complete |
| Notion | Output Page | parent_type, Database badge | Standard sync | ✅ Complete |
| Calendar | Output Calendar | Primary badge | "On-demand" (no sync) | ✅ Complete |

## Future Considerations

1. **Gmail labels** - May want to show email count per label
2. **Calendar** - Consider showing upcoming events preview
3. **All platforms** - Consider bulk import actions, refresh buttons

## Related Files

- `web/app/(authenticated)/context/[platform]/page.tsx` - Main implementation
- `web/components/deliverables/TypeSelector.tsx` - Deliverable type selection
- `api/services/platform_tools.py` - Platform tool definitions
