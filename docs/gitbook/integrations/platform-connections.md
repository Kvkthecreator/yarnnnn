# Platform Connections

You can authorise YARNNN to read from the platforms where your work already happens.

> **Current status.** Connecting a platform and choosing what's in scope works today. **Scheduled background pulling is not running yet** — the capture lane is turned off. So connecting a platform does not currently populate your workspace on its own.
>
> Until it's on, the reliable ways to get material in are [uploads](../apps/files.md) and the [MCP connector](mcp-connector.md). We'd rather say this plainly than have you wonder why nothing arrived.

## Where

**Settings → Connections.**

Platform credentials are yours, not the workspace's — they're keyed to your account, which is why they live in the account door rather than Workspace Settings.

## Available

| Platform | Auth | Direction | What you scope |
|---|---|---|---|
| **Slack** | OAuth | Inbound | Channels |
| **Notion** | OAuth | Inbound | Pages and databases |
| **GitHub** | OAuth | Inbound | Repositories |
| **WordPress** | OAuth | **Outbound** | The site you publish to |

## Connecting

1. Open **[Reach](../apps/reach.md)** → Connected
2. Pick a platform and authorise it
3. Choose which channels, pages, or repos are in scope

## Inbound and outbound

**Slack, Notion and GitHub are read-only.** YARNNN doesn't post in Slack or edit
your Notion pages — it reads what you've put in scope.

**WordPress is the exception**, and deliberately so: it's the path a
[Blogger](../apps/blogger.md) post takes to get published. Anything heading out
that way surfaces on Reach's **Leaving** pane for you to execute first. Nothing
crosses the boundary without a member's click.

## Connections are yours, not the workspace's

A connection is held under **your** account. Other members of the same workspace
hold and see their own, and an agent is never handed your credential — when an
agent's work needs to cross the boundary, it surfaces for you to click.

## Retention

Raw material captured from a platform is held for a window set by your plan — 7 days on Free, 30 days on the paid plan — and you can set a shorter window yourself within that ceiling.

This applies only to raw captured material. Anything derived from it, and anything you author, is kept until you delete it.

## Disconnecting

Disconnect from the connection's card. This immediately stops any future reading and removes the connection's configuration. Material already in your workspace stays where it is — it's yours, and it's attributed.
