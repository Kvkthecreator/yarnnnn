# Integrations

YARNNN connects to the tools where your work already happens so TP and your agents can operate with real context.

## Supported platforms

| Platform | What YARNNN reads | Typical first value |
|---|---|---|
| [Slack](slack.md) | Selected channel activity | Team recap, signal watch, discussion summary |
| [Notion](notion.md) | Selected pages and databases | Doc-grounded summary, project context, research input |

## Connection model

When you connect a platform, YARNNN:

1. authenticates through OAuth
2. receives read-only access
3. discovers available sources
4. applies smart default coverage
5. starts syncing

You can refine source coverage later from the product.

## Why integrations matter

Integrations are the onramp into the system's substrate.

They make it possible to:

- answer questions grounded in your real work
- bootstrap useful tasks and grounded agent work quickly
- synthesize across platforms instead of staying in a single silo
- build better output over time as the substrate deepens

## External AI access

You can also use YARNNN from Claude, ChatGPT, and compatible clients through the [MCP connector](mcp-connector.md).

## Security

- all integrations are read-only
- tokens are encrypted at rest
- data is scoped to your account
- you can disconnect any integration at any time
