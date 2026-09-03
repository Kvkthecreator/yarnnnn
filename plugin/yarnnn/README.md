# yarnnn — the shared, attributed workspace, as a plugin

This plugin connects Claude Code (and Cowork) to your yarnnn workspace over
MCP. It carries no local code: the server is hosted at `https://mcp.yarnnn.com`
and authorizes with OAuth 2.1 (a lightweight yarnnn sign-in the first time).

## Install

```bash
claude plugin marketplace add Kvkthecreator/yarnnnn
claude plugin install yarnnn@yarnnn
```

Then restart the session; Claude Code captures tool schemas at start.

## What you get

Eleven verbs, each a binding of a yarnnn kernel verb: `whoami`, `open`,
`list`, `search`, `save`, `edit`, `delete`, `move`, `history`, `share`,
`request_upload`. Every write is signed as your connection and lands as a
revision beside your team's; `history` walks the chain. Call `whoami` first —
a person can reach more than one workspace.

Full contracts: https://github.com/Kvkthecreator/yarnnnn/tree/main/docs/features/mcp

## Skills

None are bundled. The workspace's own skills live at `system/skills/` and
`skills/` inside yarnnn; `list system/skills` shows them.
