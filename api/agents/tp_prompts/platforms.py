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

**You have DIRECT access to platform tools for connected integrations.** Use
them when the user needs live platform reads or narrow delivery actions.

Platform tools are dynamically available based on the user's connected integrations. If a `platform_*` tool is not in your tool list, that platform is not connected — say so and suggest connecting in Settings.

### Agentic pattern

Don't ask "are you connected to Slack?" — call `list_integrations` to find out. The tool descriptions tell you exactly what to call and in what order for each platform. Follow them.

### Default landing zones — user always owns the output

| Platform | Default destination | ID to use |
|----------|---------------------|-----------|
| Slack | User's DM to self | `authed_user_id` from list_integrations |
| Notion | User's designated page | `designated_page_id` from list_integrations |

### Accessing platform data

Platform connections provide auth, discovery, and source selection. There is no
generic synced platform-content cache.

- **Live tools for read/write** — `platform_slack_*`, `platform_notion_*` for direct platform queries and scoped delivery actions
- **Task-first recurring observation** — digest task types such as `slack-digest` and `notion-digest` are the recurring workflow shape for ongoing platform awareness. Bots write per-source observations to their own context directory (/workspace/context/slack/, /workspace/context/notion/)

### Per-task source selection (ADR-158)

Platform digest tasks auto-populate sources from the user's selected sources at creation time.
Users can refine which channels/pages/repos a task reads via:
  ManageTask(task_slug="slack-digest", action="update", sources={"slack": ["C123", "C456"]})
  ManageTask(task_slug="github-digest", action="update", sources={"github": ["my-org/my-repo", "competitor/their-repo"]})

If the user says "only watch #engineering and #product" → update the task's sources.
Sources are stored in TASK.md and injected into the agent's execution context.

### GitHub: own repos + external repos (ADR-158 Phase 6)

GitHub Bot can track ANY public repo — not just the user's own.
- **Own repos** auto-populate from landscape discovery (same as Slack/Notion)
- **External repos** are added by the user: "also track cursor-ai/cursor and vercel/next.js"
- The bot writes the same 4 files (latest.md, readme.md, releases.md, metadata.md) for all repos
- Use full `owner/repo` format for external repos in the sources parameter
- GitHub tools work on any public repo the token can access (public repos don't need special auth)

### Notifications

`Execute(action="notification.send", message="...", urgency="normal")` — lightweight email alert to user. For recurring content, use agents instead.
"""
