# Connecting yarnnn to your LLM

> **Parent**: [README.md](README.md)
> **Audience**: end users connecting yarnnn to Claude / ChatGPT / Gemini, and the landing/onboarding surface that renders these steps.
> **Status**: canonical connector-setup source (ADR-370 Slice 2). The landing site + in-app setup should render FROM this — one source of truth for the URL + steps.

---

## The connector URL

```
https://mcp.yarnnn.com
```

That's it — the bare domain, no path. The MCP protocol is served at the root (ADR-370 Slice 2), so there's nothing extra to remember.

> **Historical note:** earlier the protocol lived at `/mcp` (the SDK default), which caused a "no MCP server found at the provided URL" error when users typed the bare domain. That's fixed — the protocol now answers at the root, so the natural thing to type just works.

---

## What connecting does

You connect yarnnn to whichever LLMs you use. Then:
- **open / list / search** — any LLM you've connected reads the same shared workspace: exact files, the folder tree, or search by meaning.
- **save** — what one LLM writes lands as an attributed revision every other LLM (and your team) sees. Your thinking stays coherent across rooms.
- **history** — see how any file changed over time, and which LLM or person contributed each version.
- **share** — mint a member/viewer link straight from the conversation.

You sign in once per LLM (a lightweight yarnnn login — same account across all of them). You can also visit [yarnnn.com](https://yarnnn.com) anytime with the same credentials.

---

## Per-LLM setup

### Claude (claude.ai — web + mobile)

1. Settings → **Connectors** → **Add custom connector** (or **Add connector → Custom**).
2. Paste the URL: **`https://mcp.yarnnn.com`**
3. Authorize → you'll be sent to a yarnnn sign-in (sign in or create your account) → it returns you to Claude.
4. Done. The `open` / `list` / `search` / `save` / `history` / `share` tools are now available.

### ChatGPT (developer mode connectors)

1. Settings → **Connectors** (developer mode) → **Add**.
2. Paste the URL: **`https://mcp.yarnnn.com`**
3. Complete the OAuth sign-in → returns to ChatGPT.

### Gemini

1. Add the MCP connector with URL **`https://mcp.yarnnn.com`**.
2. Complete the yarnnn sign-in.

### Claude Desktop (config file)

Claude Desktop uses a config JSON rather than a URL field. Add:

```json
{
  "mcpServers": {
    "yarnnn": {
      "url": "https://mcp.yarnnn.com"
    }
  }
}
```

---

## What sign-in looks like (and why it's separate from the cockpit)

When you connect, the yarnnn sign-in that appears is the **MCP auth surface** — a lightweight login dedicated to the connect moment (ADR-370). It is intentionally NOT the full yarnnn cockpit: you're connecting a memory, not opening the operator workspace. After sign-in you go straight back to your LLM.

It's the **same account** either way — sign in here, and you can later open the full cockpit at [yarnnn.com](https://yarnnn.com) with the same credentials. Separate door, same building.

---

## The surface changed — making your host see it

**Your host caches yarnnn's tool list.** When we ship a new verb (or a new parameter
on an existing one), a host that connected earlier keeps serving its cached copy —
sometimes for days. It is not broken, and reconnecting usually does **not** clear it.

Measured on 2026-08-07, both against the same live server on the same deploy:

| Host | What it saw | Frozen since |
|---|---|---|
| claude.ai | all six verbs, but `save` was missing its newest parameter | ~4 days |
| ChatGPT | only three verbs — the pre-`open`/`save`/`share` set | ~5 days |

The cause was ours: yarnnn advertised `capabilities.tools.listChanged: false`, which
told every host the list would never change — so caching it forever was the correct
behavior. That declaration is fixed (ADR-533 §13), and a spec-compliant host will now
re-check on its **next** connect. But the fix cannot reach back into a cache that was
already taken, so if your host is showing an old surface:

| Host | How to force a fresh tool list |
|---|---|
| **ChatGPT** | Settings → Connectors → yarnnn → **`Refresh`**. ChatGPT pins a *version snapshot* of a dev-mode connector, so a deploy never reaches it on its own — and **remove + re-add does NOT help** (it re-pins the same snapshot). Refresh is the only action that pulls the current manifest; the `Version notes` field bumps (`dev-3` → `dev-4`) when it lands. See [SUBMISSION.md](SUBMISSION.md) §4. |
| **claude.ai / Claude Desktop** | Settings → Connectors → toggle yarnnn off, then on. A "Tools list refreshed" toast confirms it. |
| **Claude Code** | Restart the session — tool schemas are captured at session start and never update mid-session. |

**Verify it actually landed — don't trust the toast.** The settings panel is the receipt.
Check a field that only exists in the build you're expecting:

- `save` should list **five** inputs — `reference · content · base_revision · message · derived_from`.
- `search`'s description should mention **`confidence`**.

A refresh that bumps the version but leaves those unchanged did not pull the new manifest.

**How to tell whether it worked:** ask your host to list the yarnnn tools it has.
The current surface is the file-native roster (ADR-543) — `open · list · search · save · history · share`. The pre-543 memory verbs (`remember`/`recall`/`trace`) are gone WITHOUT aliases: a host on a stale manifest gets tool-not-found on them until it reconnects.
Fewer than six means the cache is still stale. (Ask it to *call* `open` too: a host can
hold a tool it did not list.)

> A host's own account of its tools is a self-report, not proof. If it insists a verb
> is missing, have it attempt the call — the error it returns distinguishes "not in my
> manifest" from "I did not think to list it."

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "no MCP server found at the provided URL" / "token exchange failed … reverted" | A stale / half-connected connector left over from an earlier attempt | Remove the connector entirely, then re-add with `https://mcp.yarnnn.com` |
| Connector shows connected but a verb is missing, or a verb lacks a new parameter | The host cached an older tool list | See **The surface changed** above — reconnecting is often not enough; remove + re-add |
| Sign-in loops / "could not establish session" | Cookies/session issue in the popup | Complete the sign-in in the same browser; retry the connect from your LLM |

---

## For the landing/onboarding surface (implementation note)

This doc is the **single source of truth** for the connector URL + steps. When the landing site or in-app setup renders "connect your LLM," it should:
- Surface `https://mcp.yarnnn.com` as a **copy-paste button** (still nice-to-have, but the bare domain is now forgiving).
- Render the per-LLM steps above.
- The URL is the bare domain — nothing to get wrong now that the protocol is at root.
