# Cross-LLM Data Handling & Use Cases — the trust story for real external users

**Date**: 2026-06-25
**Hat**: B (external-developer discourse — analysis, not canon). Grounds the data-handling model + use cases as YARNNN crosses from dogfooding to real external users via the MCP connector.
**Status**: Discourse for operator (KVK) reaction. Establishes the trust story; informs the onboarding-hardening + custom-domain work.
**Origin**: KVK's "remember from Claude, recall from ChatGPT — do we have the right data handling?" + the first live claude.ai test (ADR-368), which validated the happy path AND surfaced two edges (the consistency window, the attribution gap).

---

## 0. The headline: the cross-LLM flow already works for a new user

This is grounded in code, not aspiration (verified 2026-06-25):

- **Identity is per-request from the OAuth token** (`resolve_request_client` → `get_access_token().user_id`). claude.ai and ChatGPT each run their own OAuth handshake, but both bind to the **same real yarnnn account** via the `/api/mcp/oauth-callback` login step (ADR-310 D4).
- **All substrate is scoped by `.eq("user_id", …)`** on every query. So a `remember` from Claude and a `recall` from ChatGPT, authenticated as the same yarnnn account, hit the **same substrate**.
- **A brand-new user's first connect works end-to-end**: claude.ai → MCP `/authorize` → `/mcp/authorize?code=…` → if not logged in, bounced to `/auth/login` (which has a **signup mode** — email/password + Google) → after auth, the flow **resumes with the code preserved** → `completeAuthorize` binds their real `user_id` → back to Claude. They repeat from ChatGPT → same account → shared memory.

**So "remember from Claude, recall from ChatGPT" is not a feature to build — it is the architecture working.** The infrastructure is there. What's left for real users is *polish, one branded-domain decision, and a couple of honest edges* — not a missing capability.

---

## 1. The data-handling model (who sees what)

### The binding unit is the yarnnn account (today: 1 account = 1 workspace = 1 user_id)

- Every connected LLM authenticates **as the operator** (their yarnnn login), and reaches **their own** substrate. No cross-user leakage: the service key bypasses RLS, but isolation is enforced by explicit `user_id` scoping on every query (the same pattern the scheduler uses).
- **A foreign LLM never gets broad read of the workspace.** It gets exactly three verbs: `recall` (read accumulated memory by subject), `trace` (read the revision history of a fact), `remember` (write to the memory inbox). No `list all files`, no governance/persona/system reads, no other users' data.

### What a foreign LLM may WRITE (the permission floor)

- A foreign caller (`yarnnn:mcp`) is locked to the `operation/` commons (specifically the memory inbox `operation/memory/`). It **cannot** write the operator's constitution, the judgment seat, governance, or orchestration runtime (`CALLER_WRITE_POLICY` — ADR-320/366). The gate is the authority; the surface only ever constructs inbox paths.
- Every write is **attributed and judged**: stamped `authored_by="yarnnn:mcp:<client>"` (now naming the room — see §3), and the Reviewer is invoked to place it and check it against ground-truth (ADR-368 D5). A foreign LLM contributes *memory*; the judgment seat decides where it belongs and whether it's sound.

### What crosses the boundary, and what doesn't

| Crosses (foreign LLM can reach) | Stays inside (foreign LLM never reaches) |
|---|---|
| Accumulated memory by subject (`recall`) | The operator's mandate, persona, governance, autonomy dials |
| The revision history of a fact (`trace`) | The Reviewer's seat substrate / judgment internals |
| The ability to contribute a memory (`remember` → inbox) | Other users' workspaces (hard `user_id` isolation) |
| Provenance: who contributed each fact, when | Direct file enumeration / arbitrary path reads |

---

## 2. The consistency model (the edge the live test surfaced)

The first claude.ai test caught a real property worth stating plainly, because it's a *guarantee question* for real users:

- **`recall` is immediately consistent.** A `remember` commits synchronously; a `recall` from any other LLM sees the content **instantly**. The cross-room promise ("told Claude at 3pm, ChatGPT has it at 4pm") holds with no lag.
- **`trace` and *placement* are eventually consistent** (one Reviewer cycle, ~60s in the test). The write is recorded as revision #1 *immediately* (so `trace` shows "contributed via claude.ai, awaiting placement" right away — this is the corrected reading; the first live `trace` returned empty due to a since-fixed path bug, NOT because the chain was empty). The Reviewer's *placement* (filing the dump from the inbox into its real home) lands a cycle later as revision #2.

**The honest guarantee to make to users:** *what you remember is instantly recallable everywhere; how it's filed and judged settles within a short window.* This is the right promise — it's the strength (immediate cross-room memory) without overclaiming instant judgment. Don't promise simultaneous trace/placement consistency; promise eventual placement with immediate recall.

**Decision flagged**: if the Reviewer is slow/unfunded on a workspace, the dump stays in the inbox indefinitely (recall still works; placement just doesn't happen). For real users this is fine as a floor (capture never fails), but the onboarding should set the expectation that placement depends on an active judgment seat.

---

## 3. The attribution model (the gap, now closed at the substrate layer)

The live test surfaced an asymmetry: the Reviewer was attributed specifically (`reviewer:ai:reviewer-sonnet-v8`) but the foreign write was generic (`yarnnn:mcp` / provenance `mcp:unknown`). Claude correctly noted the schema *can* carry a specific author — so the foreign write should too.

**Two layers, both now addressed:**
- **Provenance stamp** (the inline `<!-- source: mcp:<client> -->` comment): was `mcp:unknown` because `derive_client_name` read the raw HTTP request (no client_id; claude.ai's UA lacks "claude"). Fixed to read the OAuth token's `client_id` (`derive_client_name_from_token`).
- **`authored_by` on the revision** (the structural attribution `trace` surfaces): was the bare `yarnnn:mcp`. Now **client-qualified** — `caller_identity = "yarnnn:mcp:<client>"` (e.g. `yarnnn:mcp:claude.ai`), set at request time from the OAuth client_id. Validates under the existing `yarnnn:` prefix (no schema change). So `trace` now reads: **"contributed via `yarnnn:mcp:claude.ai` → filed by `reviewer:ai:…`"** — the cross-LLM provenance story made literal, naming the room.

This is the differentiator at full strength: not just "a fact has history" but "*which LLM in which room* contributed each version, and how your judgment seat responded." No storage connector has this.

---

## 4. Use cases (what real users actually do with this)

Grounded in the three verbs, ordered by how a real user encounters them:

1. **Continuity across rooms (the wedge).** Conclude something with Claude; switch to ChatGPT tomorrow; it already knows. The user stops re-explaining context every time they switch LLMs. This is the standalone value — it needs no calibrated Reviewer, just the shared substrate.
2. **Capture-in-the-moment.** Mid-conversation, the user shares a decision/insight; the LLM `remember`s it proactively (the descriptions instruct this). Their thinking accumulates without a separate note-taking step.
3. **Consult before reasoning.** The LLM `recall`s what the user already knows about a subject *before* answering, so its response is grounded in the user's accumulated context, not cold.
4. **Provenance / "how did I get here" (the differentiator).** The user (or any LLM) `trace`s how a fact evolved — who contributed it, when, how the judgment seat filed/revised it. This is the thing a plain memory or storage connector cannot do.
5. **(Deferred, ADR-368 §6) Delegation.** "YARNNN, take this on" — addressed work into the operation. Not built; the memory-first surface is the proven floor.

---

## 5. What's left before real external users (the punch list, sequenced by cost-of-delay)

1. **Custom MCP domain (`mcp.yarnnn.com`) — TIME-SENSITIVE, do first.** The `onrender.com` URL is the OAuth *issuer*, stored in every connector. Renaming after users connect breaks their connection (issuer mismatch → forced reconnect). Cheap now, expensive once real users are connected. Needs DNS + Render dashboard (operator-owned); the env-var change + parity check is small.
2. **Attribution — done at the substrate layer (§3); verify live.** The `yarnnn:mcp:<client>` change is shipped but unverified on a real OAuth call (needs the live context). Confirm on the next claude.ai test that `trace` names the room and provenance reads `mcp:claude.ai`.
3. **Onboarding hardening — last, scoped by this doc.** The flow works but is bare: `/mcp/authorize` is a thin "Connecting…" page; a brand-new user lands in an empty workspace with no explanation of what remember/recall/trace do or what "shared memory across LLMs" means. Real users need the first-connect to explain itself — the trust story above is the content.

---

## 6. The trust statement (draftable from this, for the user-facing surface)

> Connect yarnnn to Claude, ChatGPT, Gemini — whichever LLMs you use. What you tell one, the others can recall, instantly. Every contribution is attributed to the room it came from and filed by your own judgment seat. yarnnn never lets a foreign LLM rewrite your intent or read another person's workspace — it gives each LLM exactly three things: remember, recall, and trace. Your thinking stays coherent across rooms; your provenance stays intact; your judgment stays yours.
