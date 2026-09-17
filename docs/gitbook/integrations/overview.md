# Connect Your AI

There are three ways material moves between YARNNN and the outside world.

## 1. The MCP connector — your other AI reaches in

This is the main one. Connect ChatGPT, Claude, or any MCP-capable client to `https://mcp.yarnnn.com` and it can save to, search, and walk the history of your workspace directly.

This is what makes YARNNN shared memory rather than another app with its own memory: you keep working wherever you already work, and everything lands in one place you own.

Three things follow from that, and they're the reason this isn't just cloud storage with a plugin:

- **It's the same files.** A connected AI reads and writes exactly what you see in Files — not a copy, not a synced index. Save something from ChatGPT and it's there when you open YARNNN.
- **Every change is signed by whoever made it.** A connected AI writes as *itself*, not as you. Your history shows `you · Tuesday`, `claude.ai · Wednesday`, `chatgpt · Thursday` — so "who changed this, and when?" has a real answer even when the answer isn't a person.
- **You decide how far it reaches.** Each connection is granted read, write, or share access, and you can narrow it to part of the workspace or revoke it outright.

→ [MCP connector setup](mcp-connector.md)

Included on every plan, including Free. An AI connection is never a billed seat.

## 2. Platform connections — bringing in work from elsewhere

Authorise Slack, Notion, GitHub, and a couple of others so YARNNN can read from them.

→ [Platform connections](platform-connections.md)

{% hint style="warning" %}
**Status:** you can connect a platform and choose which channels or pages are in scope. Automatic pulling on a cadence isn't running yet, so for now the reliable way to get material in is uploading it or saving it over MCP.
{% endhint %}

## 3. Uploads — the direct route

Files → right-click → **Add Files**, or drag files in. PDF, DOCX, TXT, MD, and ZIP. They land in Downloads, get a searchable text version derived alongside the original, and every lane can read them immediately.

→ [Files](../apps/files.md)

## Which to use

| You want to… | Use |
|---|---|
| Keep working in ChatGPT/Claude but stop losing context | MCP connector |
| Get documents you already have into the workspace | Uploads |
| Let YARNNN read from Slack or Notion | Platform connections |
| Give a teammate access | An [invite](../concepts/working-with-a-team.md), not a connection |

## Security

- Platform connections use OAuth; tokens are encrypted at rest
- MCP connections use OAuth 2.1, or a bearer token for local clients
- Every connection is a named row you can revoke at **Workspace Settings → Access**
- Everything written through any connection is attributed to it
