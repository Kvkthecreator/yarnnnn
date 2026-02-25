# Use YARNNN from Claude, ChatGPT, and Other AI Tools

You don't have to visit yarnnn.com every time you want to use YARNNN. With the **MCP connector**, you can access your synced work context, trigger deliverables, and search across your platforms — all from the AI tool you already have open.

This works with **Claude** (claude.ai, Claude Desktop, Claude Code) and **ChatGPT**.

## What you can do from Claude or ChatGPT

Once connected, you can ask your AI tool to:

- **Search your work context** — "Search my Slack and Gmail for anything about the product launch"
- **Trigger a deliverable** — "Run my weekly engineering digest now"
- **Read deliverable output** — "Show me the latest version of my status report"
- **Check what's connected** — "What platforms are synced in YARNNN and when did they last update?"
- **View your profile** — "What does YARNNN know about my preferences?"

YARNNN becomes a tool your AI assistant can call — just like it can browse the web or read files.

## Prerequisites

Before setting up the connector:

1. You have a YARNNN account with at least one platform connected
2. Your sources have synced at least once (so there's content to query)

---

## Setup: Claude.ai

1. Go to **Settings** → **Connectors**
2. Click **Add custom connector**
3. Enter the details:
   - **Name**: `yarnnn`
   - **URL**: `https://yarnnn-mcp-server.onrender.com/mcp`
4. Click **Add**
5. Complete the authorization when prompted

<!-- Screenshot: Claude.ai connector setup dialog -->
<figure><img src="../.gitbook/assets/claude-connector-setup.png" alt="Adding YARNNN as a custom connector in Claude.ai settings"><figcaption>Adding YARNNN as a connector in Claude.ai</figcaption></figure>

That's it. Claude can now use YARNNN tools in any conversation. Try asking: *"Use YARNNN to search my Slack for discussions about the Q1 roadmap."*

---

## Setup: ChatGPT

ChatGPT supports MCP connectors through **Developer mode** in the Apps settings.

### Step 1: Enable Developer mode

1. Go to **Settings** → **Apps**
2. Scroll to **Advanced settings**
3. Toggle **Developer mode** on

<figure><img src="../.gitbook/assets/chatgpt-developer-mode.png" alt="Enabling Developer mode in ChatGPT settings"><figcaption>Enable Developer mode in ChatGPT → Apps → Advanced settings</figcaption></figure>

### Step 2: Create the YARNNN app

1. Click **Create app** (top right)
2. Fill in the details:
   - **Name**: `yarnnn`
   - **MCP Server URL**: `https://yarnnn-mcp-server.onrender.com/mcp`
   - **Authentication**: `OAuth`
   - Leave OAuth Client ID and Secret empty
3. Check the acknowledgment box
4. Click **Create**

<figure><img src="../.gitbook/assets/chatgpt-create-app.png" alt="Creating YARNNN as an MCP app in ChatGPT"><figcaption>Creating YARNNN as an app in ChatGPT Developer mode</figcaption></figure>

5. Complete the authorization when prompted

ChatGPT can now use YARNNN tools. Try asking: *"Use YARNNN to check what deliverables I have set up."*

---

## Setup: Claude Desktop

Add the following to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

---

## Setup: Claude Code

Run this command in your terminal:

```bash
claude mcp add yarnnn \
  --transport http \
  --url https://yarnnn-mcp-server.onrender.com/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

Replace `YOUR_TOKEN` with your bearer token. YARNNN tools will be available in your next Claude Code session.

---

## Available tools

Once connected, your AI tool has access to these YARNNN capabilities:

| What you can ask for | What happens |
|---|---|
| "Check my YARNNN status" | Shows connected platforms, sync freshness, active deliverables |
| "Search my Slack/Gmail/Notion for X" | Searches your synced content across platforms |
| "What does YARNNN know about me?" | Shows your profile, preferences, and learned patterns |
| "List my deliverables" | Shows all configured deliverables with schedules |
| "Run my weekly digest" | Triggers a deliverable to generate a new version now |
| "Show my latest status report" | Retrieves the most recent deliverable output |

## Tips

- **Be specific about YARNNN** — say "use YARNNN to search..." so your AI tool knows to use the connector rather than general web search
- **Works alongside other tools** — YARNNN adds to what Claude/ChatGPT can already do, it doesn't replace anything
- **Same data, different interface** — everything available via the connector is the same data you see on yarnnn.com
- **Synced content only** — the connector can only access content from platforms and sources you've already connected and synced in YARNNN

## FAQ

**Does this cost extra?**
No. The MCP connector is included with your YARNNN plan. It uses the same usage limits as the YARNNN web app.

**Can Claude/ChatGPT modify my YARNNN data?**
The connector can trigger deliverable runs, but it cannot modify your settings, disconnect platforms, or change your profile. It's primarily read-access with the ability to trigger existing deliverables.

**Do I need to keep yarnnn.com open?**
No. The connector works independently. You set up your platforms and deliverables on yarnnn.com, then use them from Claude or ChatGPT without needing the YARNNN tab open.
