# MCP Connector — Claude & ChatGPT

You do not need to stay inside yarnnn.com to use YARNNN. With the **MCP connector**, Claude, ChatGPT, and other compatible MCP clients can use YARNNN as a shared context hub.

This works today with **Claude** (claude.ai, Claude Desktop, Claude Code) and **ChatGPT**.

## What MCP is for

YARNNN is the shared layer that keeps your thinking coherent across LLMs.

Instead of starting cold in every new chat, your external AI tool can:

- pull grounded context from the same YARNNN workspace
- start work from a curated bundle instead of a blank prompt
- write decisions or observations back into that workspace

The workforce inside YARNNN stays in the background. Across MCP, what matters is a simple three-tool surface that matches how people think.

## The three tools

| Intent | Tool | What it does |
|---|---|---|
| "Work on this." | `work_on_this` | Starts a work session with a curated bundle of context around a subject |
| "Pull my context about ___." | `pull_context` | Returns ranked raw material about a subject or question |
| "Remember this." | `remember_this` | Writes an observation, decision, or insight back into the workspace |

That is the MCP surface. The connector is not an admin panel for listing agents, triggering tasks, or operating the whole backend from a foreign LLM.

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

That is it. Claude can now use YARNNN tools in any conversation. Try asking: _"Use YARNNN to pull my context about the Q1 roadmap."_ 

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

ChatGPT can now use YARNNN tools. Try asking: _"Use YARNNN to work on our board update."_ 

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

Once connected, your AI tool has access to three intent-shaped tools:

| What you can ask for | What happens |
|---|---|
| "Work on this launch plan" | Calls `work_on_this` and returns a curated starting bundle |
| "Pull my context about Acme" | Calls `pull_context` and returns ranked raw material |
| "Remember that legal wants a redline before Friday" | Calls `remember_this` and stores it in the right workspace area |

## Tips

* **Be explicit** — say "use YARNNN to..." so Claude or ChatGPT uses the connector instead of guessing
* **Think in subjects, not backend objects** — ask for context, work sessions, and remembered decisions
* **Same substrate, different interface** — the connector exposes the same YARNNN workspace your web product uses
* **Best after first sync** — the connector is most useful once YARNNN already has grounded context to work with

## FAQ

**Does this cost extra?** No. The MCP connector is included with your YARNNN plan.

**Can Claude/ChatGPT modify my YARNNN data?** It can contribute observations or decisions through `remember_this`, but it is not a general-purpose admin surface for changing your whole workspace.

**Do I need to keep yarnnn.com open?** No. Set up platforms and agents once, then use them from Claude or ChatGPT without keeping the YARNNN tab open.
