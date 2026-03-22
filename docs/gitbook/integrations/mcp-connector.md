# MCP Connector — Claude & ChatGPT

You do not need to stay inside yarnnn.com to use YARNNN. With the **MCP connector**, Claude or ChatGPT can access your synced work context, inspect agents, and trigger work through YARNNN.

This works with **Claude** (claude.ai, Claude Desktop, Claude Code) and **ChatGPT**.

## What you can do from Claude or ChatGPT

Once connected, you can ask your AI tool to:

* **Search your work context** — "Use YARNNN to search Slack and Notion for anything about the product launch"
* **Trigger an agent** — "Run my weekly engineering recap in YARNNN"
* **Read agent output** — "Show me the latest status update from YARNNN"
* **Check what's connected** — "What platforms are synced in YARNNN?"
* **View your profile** — "What does YARNNN know about my preferences?"

YARNNN becomes a context and agent layer your external AI tool can call directly.

## Prerequisites

Before setting up the connector:

1. You have a YARNNN account
2. At least one platform or document source has synced
3. You want external AI tools to work against YARNNN's substrate instead of starting from zero

***

## Setup: Claude.ai

1. Go to **Settings** → **Connectors**
2. Click **Add custom connector**
3. Enter the details:
   * **Name**: `yarnnn`
   * **URL**: `https://yarnnn-mcp-server.onrender.com/mcp`
4. Click **Add**
5. Complete the authorization when prompted

That is it. Claude can now use YARNNN tools in any conversation. Try asking: _"Use YARNNN to search my Slack for discussions about the Q1 roadmap."_

<figure><img src="../.gitbook/assets/mcp connect - claud.png" alt=""><figcaption></figcaption></figure>

***

## Setup: ChatGPT

ChatGPT supports MCP connectors through **Developer mode** in the Apps settings.

### Step 1: Enable Developer mode

1. Go to **Settings** → **Apps**
2. Scroll to **Advanced settings**
3. Toggle **Developer mode** on

<figure><img src="../.gitbook/assets/mcp connect - openai2.png" alt=""><figcaption></figcaption></figure>

### Step 2: Create the YARNNN app

1. Click **Create app** (top right)
2. Fill in the details:
   * **Name**: `yarnnn`
   * **MCP Server URL**: `https://yarnnn-mcp-server.onrender.com/mcp`
   * **Authentication**: `OAuth`
   * Leave OAuth Client ID and Secret empty
3. Check the acknowledgment box
4. Click **Create**
5. Complete the authorization when prompted

ChatGPT can now use YARNNN tools. Try asking: _"Use YARNNN to check what agents I have set up."_

<figure><img src="../.gitbook/assets/mcp connect - openai3.png" alt=""><figcaption></figcaption></figure>

***

## Setup: Claude Desktop

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json` **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "yarnnn": {
      "type": "streamable-http",
      "url": "https://yarnnn-mcp-server.onrender.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

Replace `YOUR_TOKEN` with the bearer token from your YARNNN account settings. Restart Claude Desktop after saving.

***

## Setup: Claude Code

Run this command in your terminal:

```bash
claude mcp add yarnnn \
  --transport http \
  --url https://yarnnn-mcp-server.onrender.com/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

Replace `YOUR_TOKEN` with your bearer token. YARNNN tools will be available in your next Claude Code session.

***

## Available tools

Once connected, your AI tool has access to these YARNNN capabilities:

| What you can ask for | What happens |
|---|---|
| "Check my YARNNN status" | Shows connected platforms, sync freshness, and active agents |
| "Search my Slack/Notion for X" | Searches synced content across platforms |
| "What does YARNNN know about me?" | Shows profile, preferences, and learned patterns |
| "List my agents" | Shows configured agents with schedules |
| "Run my weekly digest" | Triggers an agent to generate a new run |
| "Show my latest status report" | Retrieves the latest agent output |

## Tips

* **Be explicit** — say "use YARNNN to..." so Claude or ChatGPT uses the connector instead of guessing
* **Same substrate, different interface** — the connector exposes the same YARNNN context you use in the product
* **Best after first sync** — the connector is most useful once YARNNN already has grounded context to work with

## FAQ

**Does this cost extra?** No. The MCP connector is included with your YARNNN plan. It uses the same usage limits as the YARNNN web app.

**Can Claude/ChatGPT modify my YARNNN data?** The connector can trigger existing work, but it is not a general-purpose admin surface for changing all of your settings.

**Do I need to keep yarnnn.com open?** No. Set up platforms and agents once, then use them from Claude or ChatGPT without keeping the YARNNN tab open.
