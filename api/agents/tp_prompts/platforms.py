"""
Platform Tools Documentation - Slack, Notion.

ADR-131: Gmail and Calendar removed (sunset).

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

### Accessing platform data

Platform data enters the workspace through tracking tasks (Monitor Slack, Monitor Notion). These tasks capture signals into /workspace/context/signals/ and produce digests. Other agents read this context for their domain work.

Platform connections provide auth. If the user asks about platform activity, suggest creating a monitoring task.

- **Live tools for read/write** — `platform_slack_*`, `platform_notion_*` for real-time queries, sending, CRUD
- **Ongoing awareness** — create a tracking task (e.g., `monitor-slack` on Slack Bot, `monitor-notion` on Notion Bot) to build context over time

### Notifications

`Execute(action="notification.send", message="...", urgency="normal")` — lightweight email alert to user. For recurring content, use agents instead.
"""
