# MCP Onboarding Surface — design for the connector-user journey

**Date**: 2026-06-25
**Hat**: B (external-developer design discourse — a build spec for operator (KVK) reaction, not canon). Recommends a frontend surface; the build lands in Hat-A `web/` once scoped.
**Origin**: KVK reconnecting via `mcp.yarnnn.com` hit "authorized but no MCP server found" (the bare-domain-vs-`/mcp`-path gotcha), and correctly read it as an **onboarding** problem — the connect flow currently piggybacks on the cockpit's app+auth logic, which is a shortcut, not the long-term shape. The connector-user (memory-first) is a different person than the cockpit operator.
**Status**: Design for ratification. Companion to `cross-llm-data-handling-and-use-cases-2026-06-25.md` (the trust story = this surface's content) + `mcp-custom-domain-handoff-2026-06-25.md` (the URL).

---

## 0. The core thesis: two different people, one shortcut to undo

YARNNN now serves two audiences through one moat (ADR-368 memory-first + delegation-deferred):

| | **Cockpit operator** | **Connector user (memory-first)** |
|---|---|---|
| Where they live | `yarnnn.com` — in the product | claude.ai / ChatGPT / Gemini — mid-conversation |
| Intent | Operate a workspace (mandate, Reviewer, recurrences) | Make their LLM remember things across rooms |
| What they need at signup | The full cockpit (`/desktop`) | Connect · confirm it works · get back to their LLM |
| What they get TODAY | `/desktop` (correct) | **`/desktop`** (wrong — overwhelming, off-intent) |

**The shortcut**: the MCP connect flow reuses the cockpit's Supabase session + `/auth/login` + post-login landing (`/desktop`). That was the right way to *prove the flow* (and it works — OAuth binding is solid). But it means a memory-user who just wants "Claude remembers things" lands in the full operator cockpit. The long-term shape is a **dedicated MCP onboarding surface** that is NOT the cockpit.

This is the same memory-vs-operation split ADR-368 already ratified at the tool layer, now surfacing at the onboarding layer. Consistent: the connector user gets a memory experience; the cockpit is for when/if they graduate to operating.

---

## 1. What already exists (reuse — do NOT rebuild)

The auth machinery is solid. The design reuses ALL of it:

- **`/mcp/authorize`** (`web/app/mcp/authorize/page.tsx`) — the OAuth handoff: ensures session, calls `completeAuthorize`, bounces back to the LLM. Works. (ADR-310 D4.)
- **`/api/mcp/oauth-callback`** (`api/routes/mcp.py`) — binds the real Supabase user to the pending code via JWT. Works. No alpha gate — any authenticated operator may bind.
- **`/auth/login`** — email/password + Google, signup + login modes, `next=` resume. Works.
- **The OAuth provider + `mcp_oauth_*` tables** — pending-code flow, per-request identity. Works.
- **The custom domain** — `mcp.yarnnn.com/mcp` (with path), issuer flipped. Works.

**None of this changes.** The design adds an *experience layer* around it; it does not touch the OAuth plumbing.

## 2. What's missing (the gaps the live test exposed)

1. **No "connect your LLM" surface at all.** `/connectors` is INBOUND platform integrations (Slack/Notion the workspace pulls from) — the opposite direction. There is no page that says "here's your connector URL, here's how to add it to Claude/ChatGPT/Gemini." A user has no way to *discover* the URL — so they guess the bare domain and hit the 404.
2. **The URL gotcha** (`mcp.yarnnn.com` vs `mcp.yarnnn.com/mcp`) has no guardrail — nothing surfaces the correct full URL copy-paste-ready.
3. **The post-connect landing is the cockpit** (`/desktop`) — wrong altitude for a memory-user. No "it's working, here's what to do next" moment.
4. **No proof-of-life.** After connecting, nothing confirms to the user that the round-trip works (the "told Claude, ChatGPT has it" magic is never *shown*, only promised).
5. **`/mcp/authorize` is a bare "Connecting…" page** — no brand, no reassurance, no framing of what's happening.

## 3. The proposed surface — `/connect` (the MCP onboarding home)

A dedicated, cockpit-separate surface for the connector journey. Four moments:

### Moment 1 — Discover (the connector setup page) — `/connect`
The thing that's wholly missing. A page (reachable post-signup AND from marketing) that gives the user everything to connect:
- **The exact URL, copy-paste-ready**: `https://mcp.yarnnn.com/mcp` (a copy button — never make them type it; this kills the 404 gotcha at the source).
- **Per-LLM instructions** (tabs/cards): claude.ai (Settings → Connectors → Add), ChatGPT (developer mode connector), Gemini, Claude Desktop (config JSON). Each with the URL pre-filled and a 2-3 step walkthrough.
- **What this does**, in one line per verb: "remember saves it · recall pulls it back · trace shows how it changed" — the trust story §6 distilled.

### Moment 2 — Authorize (the handoff) — `/mcp/authorize` (upgrade existing)
The user clicks connect in their LLM → lands here. Currently bare. Upgrade to:
- Brand + a one-line reassurance ("Connecting <client> to your YARNNN memory…").
- The login bounce stays (reuse `/auth/login`), but framed: a memory-user signing up here should feel they're creating a *memory*, not an operator account. Same Supabase auth; different copy.
- On success: redirect NOT to `/desktop` but to **Moment 4** (the connected confirmation), then back to the LLM.

### Moment 3 — (Reuse) the OAuth bind — no UI change
`completeAuthorize` → `/api/mcp/oauth-callback`. Untouched.

### Moment 4 — Confirm (proof-of-life) — `/connect/done` (new)
The missing "it's working" moment. After a successful connect:
- "✅ <client> is connected to your YARNNN memory."
- **Optional live proof**: a one-tap "test it" that does a `remember` + `recall` round-trip and shows the result — the magic, demonstrated not promised. (Uses the same primitives; ~$0.)
- "Connect another LLM" (the cross-room story is the point — nudge a second connection) + "Open your workspace" (the graduation path to the cockpit, for when they want more).

## 4. The dedicated-vs-cockpit boundary (the architecture decision)

- **`/connect*` is its own surface tree** — outside the `(authenticated)` cockpit shell. A connector-user may never see `/desktop`. The cockpit is reachable from Moment 4 as an *opt-in graduation*, not a forced landing.
- **Auth is shared, experience is separate.** Same Supabase user, same OAuth machinery — a connector-user and a cockpit-operator can be the same account. What differs is *where signup lands them* and *what they're shown*. (Signup via `/connect` → memory experience; signup via `yarnnn.com` → cockpit.)
- **This mirrors ADR-368's tool-layer split at the experience layer.** Memory-first is the front door; operation is the graduation. Don't force the cockpit on someone who came for memory.

## 5. Redirect logic (KVK's specific instinct — the part that's currently fragile)

The redirect chain is where the shortcut shows. Today: LLM → `/mcp/authorize` → (login bounce) → `/auth/login?next=/mcp/authorize?code=…` → back → `completeAuthorize` → LLM. The fragility:
- The post-login `next=` lands back at `/mcp/authorize` which redirects to the LLM — the user never sees a YARNNN confirmation, and a NEW user never learns what they just connected.
- **Fix**: insert Moment 4 (`/connect/done`) between the successful bind and the bounce-back, OR show it on next app-open. The redirect should pass *through* a YARNNN confirmation, not skip it.
- **Signup-mid-flow**: a brand-new user connecting from claude.ai hits login → picks signup → must confirm email (Supabase) → THEN resume. That email round-trip mid-OAuth is a real drop-off risk. Worth deciding: passwordless/magic-link or Google-only for the connector path to avoid the email-confirm interruption.

## 6. Build slices (sequenced — cheapest, highest-leverage first)

The full surface is the goal; build it in slices so value lands early:

1. **Slice 1 — `/connect` setup page (the URL fix).** Just the copy-paste URL + per-LLM instructions. Kills the 404 gotcha you hit. Small, high-leverage, ships first. *This is the cheapest fix to the actual problem.*
2. **Slice 2 — `/connect/done` confirmation** + redirect-through (Moment 4). The "it's working" moment + stops dumping users in the cockpit.
3. **Slice 3 — `/mcp/authorize` upgrade** (Moment 2 brand/copy) + the signup-mid-flow email decision (magic-link/Google-only).
4. **Slice 4 — live proof-of-life** (the test-it round-trip) + "connect another LLM" cross-room nudge.

Slices 1-2 fix everything the live test exposed. 3-4 are polish + magic. Recommend shipping 1 immediately (it's the URL gotcha), then 2, then validating with real users before 3-4.

## 7. Open questions for KVK

- **Does `/connect` live on `yarnnn.com` or `mcp.yarnnn.com`?** Recommend `yarnnn.com/connect` (it's an app/marketing page, served by the web app — the subdomain is the protocol endpoint only). Keep the protocol on the subdomain, the human page on the main domain.
- **Signup-for-connector: email/password (with the confirm interruption) vs magic-link vs Google-only?** The mid-OAuth email-confirm is the biggest drop risk; worth a deliberate choice.
- **How hard to push the cockpit "graduation"?** A memory-user may never want the operator surface. Is memory-only a valid terminal state, or is every connector-user a cockpit-operator-in-waiting? (This is the ADR-368 memory-vs-delegation question at the lifecycle layer.)
