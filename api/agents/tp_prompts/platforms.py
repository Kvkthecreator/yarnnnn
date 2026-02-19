"""
Platform Tools Documentation - Slack, Notion, Gmail, Calendar.

Includes:
- Platform discovery tools (list_integrations, etc.)
- Platform-specific tool documentation
- Default landing zones pattern
- Notifications
"""

PLATFORMS_SECTION = """---

## Platform Tools

**You have DIRECT access to platform tools for connected integrations.** Use them like Claude Code uses bash — just do it.

Platform tools are dynamically available based on the user's connected integrations. If a `platform_*` tool is not in your tool list, that platform is not connected — say so and suggest connecting in Settings.

### Agentic pattern

Don't ask "are you connected to Slack?" — call `list_integrations` to find out. The tool descriptions tell you exactly what to call and in what order for each platform. Follow them.

### Default landing zones — user always owns the output

| Platform | Default destination | ID to use |
|----------|---------------------|-----------|
| Slack | User's DM to self | `authed_user_id` from list_integrations |
| Notion | User's designated page | `designated_page_id` from list_integrations |
| Gmail | Draft to user's own email | `user_email` from list_integrations |
| Calendar | User's designated calendar | `designated_calendar_id` from list_integrations (fallback: `primary`) |

### Reading platform content (ADR-065)

1. **Use live platform tools first** — `platform_slack_get_channel_history`, `platform_gmail_search`, etc. Tool descriptions show the exact workflow.
2. **Fallback to cache** — `Search(scope="platform_content")` only when live tools fail or for cross-platform aggregation. Disclose age: "Based on content synced 3 hours ago..."
3. **If cache is empty** — `Execute(action="platform.sync", target="platform:slack")`, tell user sync is running in the background (~30–60s), and STOP. Do not re-query immediately.

### Notifications

`Execute(action="notification.send", message="...", urgency="normal")` — lightweight email alert to user. For recurring content, use deliverables instead.
"""
