# MCP Tool Reference

The MCP server exposes exactly three tools. For setup, see the [MCP connector guide](../integrations/mcp-connector.md).

**Endpoint:** `https://mcp.yarnnn.com`
**Transport:** streamable-http, served at the root path
**Auth:** OAuth 2.1 (dynamic client registration), or a bearer token for local clients
**Discovery:** `https://yarnnn.com/.well-known/mcp.json`
**OAuth metadata:** `https://mcp.yarnnn.com/.well-known/oauth-authorization-server`

---

## `remember`

Save something worth keeping. A write.

| Parameter | Type | Required | Meaning |
|---|---|---|---|
| `content` | string | yes | What to remember |
| `about` | string | no | A subject hint, to help place it |

Returns the path it was written to, its provenance (source, date, original context), and a `remembered` status. The write is durable and retrievable by subject immediately.

Not read-only, not destructive, not idempotent.

---

## `recall`

Pull what the workspace already knows about a subject. A read.

| Parameter | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `subject` | string | yes | | What to look up |
| `question` | string | no | | A specific question about it |
| `domain` | string | no | | Narrow the search |
| `limit` | integer | no | 10 | Max results (up to 30) |

Returns matching chunks — each with its path, an excerpt, when it was last updated, its domain, its source, and a similarity score — plus totals and a **confidence** signal:

| Confidence | Meaning |
|---|---|
| `high` | A clear, dominant match |
| `ambiguous` | Several matches, none dominant — ask which was meant rather than assuming the first |
| `weak` | Something matched, but loosely |
| `none` | Nothing matched |

YARNNN returns the material; the calling model explains it. Read-only and idempotent.

---

## `trace`

Show how a recorded fact changed over time. A read.

| Parameter | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `subject` | string | yes | | What to trace |
| `limit` | integer | no | 10 | Max revisions (up to 30) |

Returns the resolved path and its history newest-first — for each revision: who authored it, when, what changed, the revision id, and a diff. Plus a `resolution` field (`exact` · `ambiguous` · `weak` · `none`).

Read-only and idempotent.

---

## Attribution

Every write through MCP is attributed to the calling client — `yarnnn:mcp:claude.ai`, `yarnnn:mcp:chatgpt`, and so on. That attribution appears on the revision in Files and identifies the connection in the members roster, where it can be narrowed or revoked.

Each call also lands a narrative entry in the workspace, so work done from another AI is visible to someone working in YARNNN.

## Host rendering

ChatGPT renders results as inline widgets — a trace timeline, recall cards, and a save receipt. Other hosts get the text response. Clients are recognised by name; an unrecognised but spec-compliant client gets the text path.
