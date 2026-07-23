# Platform Connections

You can authorise YARNNN to read from the platforms where your work already happens.

> **Current status.** Connecting a platform and choosing what's in scope works today. **Scheduled background pulling is not running yet** — the capture lane is turned off. So connecting a platform does not currently populate your workspace on its own.
>
> Until it's on, the reliable ways to get material in are [uploads](../apps/files.md) and the [MCP connector](mcp-connector.md). We'd rather say this plainly than have you wonder why nothing arrived.

## Where

**Settings → Connections.**

Platform credentials are yours, not the workspace's — they're keyed to your account, which is why they live in the account door rather than Workspace Settings.

## Available

| Platform | Auth | What you scope |
|---|---|---|
| **Slack** | OAuth | Channels |
| **Notion** | OAuth | Pages and databases |
| **GitHub** | OAuth | Repositories |
| **Lemon Squeezy** | API key | — |
| **Alpaca Trading** | API key | — |

## Connecting

1. **Settings → Connections**
2. Pick a platform and authorise it
3. In the connection's **Manage** view, choose which channels, pages, or repos are in scope

Access is read-only. YARNNN doesn't post in Slack or edit your Notion pages.

## Retention

Raw material captured from a platform is held for a window set by your plan — 7 days on Free, 30 days on the paid plan — and you can set a shorter window yourself within that ceiling.

This applies only to raw captured material. Anything derived from it, and anything you author, is kept until you delete it.

## Disconnecting

Disconnect from the connection's card. This immediately stops any future reading and removes the connection's configuration. Material already in your workspace stays where it is — it's yours, and it's attributed.
