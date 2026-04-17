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
- **Task-first recurring sync** — platform sync task types (`slack-digest`, `notion-digest`, `github-digest`, `commerce-digest`, `trading-digest`) are the recurring workflow for ongoing platform awareness. Bots write per-source observations to their own context directory (/workspace/context/slack/, /workspace/context/notion/, /workspace/context/trading/, etc.)

### Per-task source selection (ADR-158)

Platform sync tasks auto-populate sources from the user's selected sources at creation time.
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

### Trading: closed-loop market intelligence (ADR-187)

Trading Bot owns two canonical context domains: `trading/` (per-instrument market data, signals, analysis) and `portfolio/` (account state, positions, trade history, performance). Four task types:

- `trading-digest` — syncs account + market data into context domains (Trading Bot, daily)
- `trading-signal` — generates signals from accumulated context (Analyst, daily)
- `trading-execute` — executes approved signals via Alpaca API (Trading Bot, daily, skips if no signals)
- `portfolio-review` — weekly performance report with signal accuracy and benchmark comparison (Analyst)

Trading tools: `platform_trading_get_account`, `platform_trading_get_positions`, `platform_trading_get_orders`, `platform_trading_get_market_data`, `platform_trading_get_portfolio_history` (read), `platform_trading_submit_order`, `platform_trading_cancel_order`, `platform_trading_close_position` (write).

Paper/live mode is controlled by the connection metadata (`paper: true/false`). The user decides when to go live.
"""
