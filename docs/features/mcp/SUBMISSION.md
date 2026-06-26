# YARNNN → ChatGPT App Directory — Submission Playbook

> **Status**: Pre-submission prep. The app is live in **developer mode** (connector `https://mcp.yarnnn.com`, OAuth). This doc is the path from dev-mode → submitted → listed: the positioning, the exact metadata to fill, the privacy/compliance checklist, the readiness gaps, and how to drive the submission via Claude Cowork (Chrome).
> **Updated**: 2026-06-26
> **Governing**: ADR-372 (the rendered interop face) + ADR-368 (the three verbs) + ADR-371 (auth boundary).
> **Source of truth for the flow**: OpenAI Apps SDK docs — [submission](https://developers.openai.com/apps-sdk/deploy/submission), [submission guidelines](https://developers.openai.com/apps-sdk/app-submission-guidelines), [connect from ChatGPT](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt). Re-read these before submitting — OpenAI is still scaling the process and fields change.

---

## 1. The positioning — how to NOT seem "weird" to the reviewer

OpenAI's listing bar is: *"serves a clear purpose, reliably does what it promises, provides functionality not natively supported by ChatGPT's core conversation, meaningfully helps common user intents."* YARNNN clears this easily — **persistent, attributed memory with a revision history is exactly "not native to ChatGPT."** The risk is not the capability; it's *framing the capability as "carry your data to competitor LLMs"* inside OpenAI's own store.

**The frame we lead with (review-facing):**

> **YARNNN is durable, attributed memory for ChatGPT.** Save a decision, fact, or preference once; recall it later in your own words; and *trace* how any recorded idea changed over time — who changed it, when, and what changed. It's the long-term memory + version history a chat doesn't keep on its own.

**Why this framing is honest AND review-safe:**
- Every claim is true. We don't hide portability — it's simply not the *pitch*. Portability is a property the user discovers and the privacy policy discloses, not a competitor-pointed sales line in the listing.
- `trace` (the ADR-209 revision chain) is the differentiator that makes "not native to ChatGPT" obvious and defensible. **Lead with trace.** A reviewer who sees who-changed-what-when over a recorded idea immediately understands this isn't a thin wrapper.
- "Memory + version history" is a clean, familiar product category. No reviewer squints at "a notebook that remembers and shows its edit history."

**What we DON'T say in listing/tool copy** (already removed from the tools, [server.py](../../../api/mcp_server/server.py)):
- "follows you across every LLM" / "visible to any other LLM you switch to" / enumerating "ChatGPT, Claude, Gemini."
- Anything that reads as "use ChatGPT to leave ChatGPT."

**What we CAN say** (benefit-framed, not competitor-framed): "your memory persists," "durable," "available wherever you work," "portable, attributed knowledge." The portability lives in the **privacy policy** (where disclosure is required and correct) and the **marketing site** (our surface, not OpenAI's).

---

## 2. The submission metadata (fill these exactly)

The dashboard form ([platform.openai.com/apps-manage](https://platform.openai.com/apps-manage)) asks for these. Drafts below — tune voice, keep the frame.

| Field | Value |
|---|---|
| **App name** | `YARNNN` (or `YARNNN Memory` if a bare brand reads thin to the reviewer) |
| **Short description** | Durable, attributed memory for ChatGPT — remember decisions and facts, recall them later, and trace how your thinking changed over time. |
| **Long description** | YARNNN gives ChatGPT a long-term memory with a history. **Remember** anything worth keeping — a decision, a fact, a preference — in one step. **Recall** what you already know about a subject when it comes up, in your own words. **Trace** how a recorded idea evolved: who changed it, when, and what changed — the version history a chat doesn't keep. Your knowledge persists and stays attributed. |
| **Category** | Productivity / Knowledge management (pick the closest the directory offers) |
| **Logo** | YARNNN mark (square, per directory spec — check current size requirement) |
| **Company URL** | `https://yarnnn.com` |
| **Privacy policy URL** | `https://yarnnn.com/privacy` — **MUST exist before submit (see §3)** |
| **MCP server URL** | `https://mcp.yarnnn.com` |
| **Auth** | OAuth 2.1 (the dashboard collects client details) |
| **Test credentials** | A demo account + bearer/login the reviewer can use. **Required** — apps that need a fresh sign-up or inaccessible 2FA are rejected. Provision a seeded demo workspace with real multi-revision content so `trace` shows a populated timeline. |
| **Screenshots** | 3–4: (1) a `remember` confirmation, (2) a `recall` with ranked results, (3) **the `trace` timeline widget populated** (the differentiator — make this the hero), (4) optional: the diff expander open. |
| **Test prompts** | "Remember that we chose Postgres over DynamoDB for cost." · "What do I know about our database decision?" · "Trace how my thinking on `standing_intent` changed." (use a demo subject WITH history so the widget populates) |
| **Localization** | English to start; add countries as availability allows. |

---

## 3. Privacy policy — the hard requirement (blocker)

OpenAI **requires a published privacy policy** stating: categories of personal data collected, purposes, categories of recipients, and retention timelines. YARNNN stores user-authored substrate, so this must be explicit and honest. Minimum contents:

- **What we collect**: the content the user chooses to save (`remember`), their OAuth identity, and operational metadata (timestamps, provenance/attribution).
- **Why**: to provide durable memory + recall + revision history.
- **Recipients**: YARNNN's infrastructure (Supabase/Postgres, Render). **If portability across other LLM hosts is a feature, disclose here** that the user's own connected LLM clients can read/write their workspace on the user's behalf — this is the correct, required place to state it (not the listing copy).
- **Retention**: how long substrate + revisions are kept; the user's deletion path.
- **No prohibited data**: we do not collect PCI, PHI, government IDs, or auth credentials of third parties.

This is a **content/legal task, not code** — it must be live at `yarnnn.com/privacy` before submission.

---

## 4. Technical readiness checklist

| Item | Status |
|---|---|
| MCP server live at clean URL | ✅ `https://mcp.yarnnn.com` (ADR-370/371) |
| OAuth 2.1 | ✅ (ADR-075/371) |
| Action annotations correct (`readOnlyHint`/`destructiveHint`/`openWorldHint`) | ✅ fixed 2026-06-26 ([2026.06.26.9]) — was the named rejection risk |
| Output schemas declared | ✅ fixed 2026-06-26 |
| Review-friendly tool copy (no competitor-pointing) | ✅ fixed 2026-06-26 |
| `trace` widget renders + populates | ✅ **VALIDATED LIVE in ChatGPT 2026-06-26** — timeline renders 10 SPY rows, provenance badges, show-changes diffs; model still narrates (D3). See §7. |
| Tools behave reliably, no crashes, complete (not a demo) | ⚠️ exercise all three end-to-end on the demo account |
| Privacy policy published | ✅ updated 2026-06-26 (66d1447) — `yarnnn.com/privacy` §5 discloses the MCP/connected-LLM data flow; deploys with web |
| Demo/test account seeded with multi-revision content | ❌ provision so `trace` shows a real timeline |
| Identity verification (OpenAI dashboard) | ❌ complete before submit |
| Logo + screenshots | ❌ produce |

**Do not submit until the ⚠️/❌ rows are closed.** Submitting an incomplete app burns a review cycle (and "complete apps only — demos rejected" is a stated rule).

### 4a. The widget-binding contract (validated 2026-06-26) — and the cache gotcha that cost us a day

For a ChatGPT-rendered widget, ALL of these are load-bearing (we proved it by elimination):
1. **Tool DEFINITION `_meta`**: `openai/outputTemplate` (the binding key — NOT `ui.resourceUri`), `openai/widgetAccessible: true`, `openai/toolInvocation/{invoking,invoked}`.
2. **Served RESOURCE `_meta`**: the SAME `openai/*` keys (not just `ui.domain`/`csp`). This was the final missing piece — ChatGPT's skybridge needs them on the resource to wire `window.openai`.
3. **Resource MIME**: `text/html+skybridge` (not the generic `text/html;profile=mcp-app`).
4. **Widget reads data** via `window.openai.toolOutput` + the `openai:set_globals` event + a poll fallback (see `useToolResult.ts`).
5. **The tool returns a `CallToolResult`** with the full result in BOTH `structuredContent` and `content` (the lowlevel MCP handler drops `_meta` from a bare-dict return).

> **THE GOTCHA (cost ~a day of debugging):** ChatGPT pins a **version snapshot** of a dev-mode connector. New deploys do NOT reach it until you click **Settings → Connectors → [your connector] → `Refresh`** (the snapshot version note bumps `dev-1`→`dev-2`). Reconnecting (remove + re-add) does NOT do this. Before testing ANY tool/widget change in ChatGPT: **click Refresh, then verify the descriptions/flags in the settings panel changed** — that panel IS the confirmation the new code loaded. Several "the widget is broken" rounds were actually "ChatGPT is serving the stale snapshot."

---

## 5. Driving the submission via Claude Cowork (Chrome)

Cowork can operate Chrome to **fill the dashboard form** on your behalf. **It cannot do the parts that need YOUR identity/secrets** — login, identity verification, 2FA, and the final Submit are yours. Model it as: *you* clear the gating prep, *Cowork* types the long form, *you* review + Submit.

### What's already done (as of 2026-06-26 — don't redo these)
- ✅ **Tools are submission-shaped**: annotations, output schemas, review-safe copy, OAuth, clean URL `mcp.yarnnn.com`.
- ✅ **Privacy policy** live at `https://yarnnn.com/privacy` (§5 discloses the MCP/connected-LLM data flow).
- ✅ **All three widgets render live in ChatGPT** (trace-timeline, recall-cards, remember-receipt) — validated; the hero screenshots exist to be taken.

### Gating prep YOU must finish before running Cowork (the real remaining blockers)
1. **Identity verification** — log into `platform.openai.com` and complete it. (Yours; Cowork can't.)
2. **Demo / test account** — create a YARNNN account + connect it, seeded with real content so the reviewer's `trace`/`recall` show populated widgets (e.g. a few `remember` saves + a multi-revision file). Note its credentials. (The reviewer uses these; an empty workspace shows empty widgets.)
3. **Logo** — square, per the directory's current size spec.
4. **3–4 screenshots** saved locally — the gallery: (a) `trace` timeline with a diff expanded [hero], (b) `recall` with a populated card showing the `mcp:chatgpt` provenance chip, (c) the `remember` ✓ receipt, (d) optional. Frame the widget **plus a bit of the model's prose** — shows the "widget + narration" experience.

Until #1–#4 exist, there is nothing for Cowork to usefully do — the form requires them.

### Cowork prompt (paste once #1–#4 are ready; fill the bracketed bits)

> Open Chrome to `https://platform.openai.com/apps-manage`. I'm already logged in and identity-verified. Help me submit my app **YARNNN** for review — but **do NOT click the final Submit or check any confirmation/legal boxes; fill everything, then stop and show me the completed form to review.**
>
> App metadata:
> - **Name:** YARNNN
> - **Short description:** Durable, attributed memory for ChatGPT — remember decisions and facts, recall them later, and trace how your thinking changed over time.
> - **Long description:** [paste the §2 long description]
> - **Category:** Productivity / Knowledge management (closest available)
> - **Company URL:** `https://yarnnn.com`
> - **Privacy policy URL:** `https://yarnnn.com/privacy`
> - **MCP server URL:** `https://mcp.yarnnn.com` (auth: OAuth)
> - **Logo:** the file at [path]
> - **Screenshots:** the files at [paths], in this order [trace, recall, remember]
> - **Test prompts:** "Remember that we chose Postgres over DynamoDB for cost." / "What do I know about our database decision?" / "Trace how my thinking on [a seeded subject] changed."
> - **Test account:** I'll give you the login to type directly into the form — type it into the page field, never echo it back in this chat.
> - **Country availability:** [your choice]
>
> For each form field, fill the matching value. If a field is unclear or asks for something I haven't given you, **pause and ask me** rather than guessing.

### Guardrails for Cowork (non-negotiable)
- **Stop before Submit.** The form has legal-attestation checkboxes and a Submit that starts review — *you* make that call after reviewing the filled form.
- **Never echo secrets into chat.** Test-account credentials go directly into the page field; tell Cowork to type, not repeat.
- **One in-review version at a time** — to change something after submitting, use "Cancel Review", don't create a second app (OpenAI constraint).
- **After Submit:** you get an email with a **Case ID**; status shows in the dashboard. Review timelines vary.

---

## 6. The honest readiness statement

**The technical app is DONE** — all three tools render live in ChatGPT, the privacy policy is published, annotations/schemas/copy/auth are all in place. **The only remaining blockers are operational and entirely yours** (identity verification, demo account, logo, screenshots — §5 gating prep). None are engineering. Finish those four, then run the §5 Cowork prompt.
