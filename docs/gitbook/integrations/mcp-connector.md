# MCP Connector — ChatGPT, Claude & More

You don't have to be in YARNNN to use YARNNN. Connect it to the AI you already work in, and that AI can read from and write to the same workspace.

**Server URL:** `https://mcp.yarnnn.com`

This works today with **ChatGPT**, **Claude** (claude.ai, Claude Desktop, Claude Code), and any MCP-capable client. It's included on every plan, including Free — an AI connection is never a billed seat.

## What it's for

Your context stops being trapped in whichever app you happened to use.

- Tell ChatGPT something worth keeping, and ask Claude about it tomorrow
- Start a conversation somewhere else and have it grounded in your actual work
- Ask any connected AI how a fact in your workspace got there, and who changed it

## The three verbs

| Verb | What it does |
|---|---|
| `remember` | Saves something worth keeping — a decision, an insight, a fact, a preference. Lands as an attributed file in your workspace, retrievable immediately. |
| `recall` | Pulls what your workspace already knows about a subject. Returns the material plus a confidence signal; the AI you're talking to explains it in its own voice. |
| `trace` | Shows how a recorded fact changed over time — who changed it, when, and what the change was. This is the one a plain storage connector can't do. |

Every write from a connected AI is attributed to it by name. You'll see `claude.ai` or `chatgpt` on the revision, and the connection appears as a revocable row in your members roster.

---

## Setup: Claude.ai

1. **Settings** → **Connectors**
2. **Add custom connector**
3. Name: `yarnnn` · URL: `https://mcp.yarnnn.com`
4. **Add**, then complete the authorisation

Try: *"Use YARNNN to recall what I know about the Q1 roadmap."*

<figure><img src="../.gitbook/assets/mcp connect - claud.png" alt=""><figcaption></figcaption></figure>

---

## Setup: ChatGPT

ChatGPT connects MCP servers through Developer mode.

### Step 1 — Enable Developer mode

**Settings** → **Apps** → **Advanced settings** → toggle **Developer mode** on.

<figure><img src="../.gitbook/assets/mcp connect - openai2.png" alt=""><figcaption></figcaption></figure>

### Step 2 — Create the app

1. **Create app**
2. Name: `yarnnn` · MCP Server URL: `https://mcp.yarnnn.com` · Authentication: **OAuth**
3. Leave the OAuth Client ID and Secret empty
4. Check the acknowledgment, click **Create**, and complete the authorisation

<figure><img src="../.gitbook/assets/mcp connect - openai3.png" alt=""><figcaption></figcaption></figure>

ChatGPT also renders YARNNN's results as inline cards — a trace timeline, recall cards, a save receipt — rather than plain text.

---

## Setup: Claude Desktop

Add to your config file:

**macOS** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "yarnnn": {
      "type": "streamable-http",
      "url": "https://mcp.yarnnn.com",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

Replace `YOUR_TOKEN` with the bearer token from your YARNNN account settings, then restart Claude Desktop.

---

## Setup: Claude Code

```bash
claude mcp add yarnnn \
  --transport http \
  --url https://mcp.yarnnn.com \
  --header "Authorization: Bearer YOUR_TOKEN"
```

Tools are available in your next session.

---

## Tips

- **Be explicit at first** — "use YARNNN to…" so the client reaches for the connector rather than guessing. Once it's used a few times, most clients pick it up on their own.
- **Think in subjects.** `recall` and `trace` take a subject, not a file path. Ask about the thing, not the location.
- **Confidence is a real signal.** When `recall` comes back ambiguous, several things matched and none dominated — a good client will ask you which you meant rather than picking the first.
- **It's the same workspace.** Anything you save from ChatGPT is in Files when you next open YARNNN, and vice versa.

## Managing connections

Every connected AI appears at **Workspace Settings → Access** as a named row under **AI connections**, showing which provider it is and who connected it.

From there you can:

- **Narrow** what region of the workspace it may write to
- **Revoke** it — which ends the grant and deletes its tokens; it would have to reconnect

In a team workspace, each person's connections are their own. Revoking yours doesn't touch a teammate's.

## FAQ

**Does it cost extra?** No. MCP access is included on every plan, and an AI connection is never a seat.

**Can a connected AI change my whole workspace?** It can write what you ask it to remember. Its write access is a grant you can narrow or revoke at any time, and everything it writes is attributed to it — so you can always see what came from where.

**Do I need to keep YARNNN open?** No.

**Which clients work?** Anything that speaks MCP. ChatGPT, Claude.ai, Claude Desktop, Claude Code, Cursor, and others are recognised by name; a spec-compliant client that isn't gets the standard text experience.
