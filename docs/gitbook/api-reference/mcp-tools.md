# MCP Tool Reference

The MCP server exposes nine file-native tools. For setup, see the [MCP connector guide](../integrations/mcp-connector.md).

**Endpoint:** `https://mcp.yarnnn.com`
**Transport:** streamable-http, served at the root path
**Auth:** OAuth 2.1 (dynamic client registration), or a bearer token for local clients
**Discovery:** `https://yarnnn.com/.well-known/mcp.json`
**OAuth metadata:** `https://mcp.yarnnn.com/.well-known/oauth-authorization-server`

> Connected before 2026-08-10? The surface changed twice that day (the
> memory verbs retired; `edit`/`delete`/`move` + the change feed added) —
> disconnect and reconnect the integration so your host fetches the current
> tool list.

---

## `open`

Read one exact file. A read.

| Parameter | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `reference` | string | yes | | `yarnnn://workspace/{path}`, `/workspace/{path}`, or a workspace-relative path |
| `revisions` | integer | no | 5 | Recent revisions to summarize (up to 10) |

Returns the exact current content (`truncated: true` if capped), who last
changed it, when, and its recent attributed revisions. An unknown path returns
`found: false` — open never guesses. Read-only and idempotent.

---

## `list`

Enumerate the files under a folder. A read.

| Parameter | Type | Required | Meaning |
|---|---|---|---|
| `reference` | string | no | The folder; omit to list the whole workspace |

Returns every file under the folder — path, an open-able reference, size, who
last changed it, and when — plus `truncated: true` when the subtree exceeded
the cap. Read-only and idempotent.

---

### Change feed + paging (`list`)

| Parameter | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `since` | string | no | | ISO timestamp — only files changed after this moment ("what moved since I was last here") |
| `limit` | integer | no | 500 | Page size (cap 500) |
| `offset` | integer | no | 0 | Page start; use `next_offset` from a truncated call |

## `search`

Find files by meaning. A read.

| Parameter | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `query` | string | yes | | What to find |
| `limit` | integer | no | 10 | Max results (up to 30) |

Returns ranked matches — each with its path, an open-able reference, an
excerpt, when it was last updated, and a similarity score — plus totals and a
**confidence** signal:

| Confidence | Meaning |
|---|---|
| `high` | A clear, dominant match |
| `ambiguous` | Several matches, none dominant — ask which was meant rather than assuming the first |
| `weak` | Something matched, but loosely |
| `none` | Nothing matched |

YARNNN returns the material; the calling model explains it. Read-only and idempotent.

---

## `save`

Write a file back as an attributed revision. A write.

| Parameter | Type | Required | Meaning |
|---|---|---|---|
| `reference` | string | yes | The file, same grammar as `open` |
| `content` | string | yes | The full new content (an overwrite, not a patch) |
| `base_revision` | string | for existing files | The head revision id from `open` — the read-before-write guarantee |
| `message` | string | no | A one-line change description |
| `derived_from` | string[] | no | References of the workspace sources this was made from |

| `confirm_full_replace` | boolean | for large files | Required `true` to wholesale-overwrite a file larger than open's cap — any open of it was truncated, so stated intent is required; prefer `edit` |

If someone changed the file since it was opened, the save returns
`stale_write` with who holds the head — re-open, merge, save again. Omit
`base_revision` only to create a new file. Not destructive (every prior
version stays on the chain), not idempotent.

---

## `edit`

Change part of a file — an anchored edit. A write.

| Parameter | Type | Required | Meaning |
|---|---|---|---|
| `reference` | string | yes | The file, same grammar as `open` |
| `old` | string | yes | Exact current text to replace (verbatim; unique unless `replace_all`) |
| `new` | string | yes | The replacement |
| `replace_all` | boolean | no | Replace every occurrence |
| `message` | string | no | One-line change description |

Only the change travels — content you never read is never at risk, which
makes this the right verb for large files and concurrent work. Fails loudly
if the anchor is missing or ambiguous; never guesses.

---

## `delete`

Remove a file from the live workspace. A write.

| Parameter | Type | Required | Meaning |
|---|---|---|---|
| `reference` | string | yes | The file, same grammar as `open` |
| `message` | string | no | Why — recorded on the attributed tombstone |

Nothing is lost: the revision chain keeps the content, `history` still walks
it, and the file can be restored.

---

## `move`

Move or rename a file. A write.

| Parameter | Type | Required | Meaning |
|---|---|---|---|
| `reference` | string | yes | The file's current path |
| `new_reference` | string | yes | The destination (must not already exist) |
| `message` | string | no | Why — recorded on both revisions |

Refuses to overwrite an existing destination — `delete` it first, by intent.

---

## `history`

Show how one exact file changed over time. A read.

| Parameter | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `reference` | string | yes | | The file, same grammar as `open` |
| `limit` | integer | no | 10 | Max revisions (up to 30) |

Returns the revision chain newest-first — for each revision: who authored it,
when, what changed, the revision id, and a diff against its predecessor. If
the file cites sources (`derived_from`), each cited file's chain is appended.
An unknown path returns `found: false` — search first when you only know the
topic. Read-only and idempotent.

---

## `share`

Mint a share link. A write.

| Parameter | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `reference` | string | no | | A file to share; omit to share the workspace |
| `access` | string | no | `member` | `member` (full access) or `viewer` (read-only) |

Returns the link for the calling model to relay. Whoever opens it sees the
work and who made it; joining the workspace requires sign-in.

---

## Attribution

Every write through MCP is attributed to the calling client — `yarnnn:mcp:claude.ai`, `yarnnn:mcp:chatgpt`, and so on. That attribution appears on the revision in Files and identifies the connection in the members roster, where it can be narrowed or revoked.

Each call also lands a narrative entry in the workspace, so work done from another AI is visible to someone working in YARNNN.

## Host rendering

ChatGPT renders results as inline widgets — a history timeline, search-result cards, and file receipts. Other hosts get the text response. Clients are recognised by name; an unrecognised but spec-compliant client gets the text path.
