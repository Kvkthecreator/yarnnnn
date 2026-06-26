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
| `trace` widget renders + populates | ⚠️ verify live (the poll fix, [2026.06.26.7]) — the hero screenshot depends on this |
| Tools behave reliably, no crashes, complete (not a demo) | ⚠️ exercise all three end-to-end on the demo account |
| Privacy policy published | ❌ §3 — blocker |
| Demo/test account seeded with multi-revision content | ❌ provision so `trace` shows a real timeline |
| Identity verification (OpenAI dashboard) | ❌ complete before submit |
| Logo + screenshots | ❌ produce |

**Do not submit until the ⚠️/❌ rows are closed.** Submitting an incomplete app burns a review cycle (and "complete apps only — demos rejected" is a stated rule).

---

## 5. Driving the submission via Claude Cowork (Chrome)

Cowork can operate Chrome to fill the dashboard form on your behalf. **It cannot complete the parts that need YOUR identity/secrets** — log in, identity verification, and any 2FA must be done by you; hand Cowork the session once you're authenticated. Treat this as "Cowork fills the long form; you own auth + the final Submit click."

**Prep (you, before Cowork):**
1. Publish the privacy policy (§3) and have its URL.
2. Have logo + 3–4 screenshots saved locally (the `trace` timeline populated is the hero).
3. Seed the demo/test account with multi-revision content; note its credentials.
4. Log into `platform.openai.com` yourself and complete identity verification.

**Cowork prompt (paste this, adjust specifics):**

> Open Chrome to `https://platform.openai.com/apps-manage`. I'm already logged in. Help me submit my app "YARNNN" for review. Use this metadata: [paste the §2 table values]. The MCP server URL is `https://mcp.yarnnn.com` (OAuth). For each form field, fill the value from my metadata; for logo and screenshots, use the files at [paths]; for the privacy policy URL use `https://yarnnn.com/privacy`. Fill the test prompts and test-account credentials I give you. **Do NOT click the final Submit or check the confirmation boxes — stop and show me the completed form for review first.** If a field is unclear or asks for something I haven't provided, pause and ask me.

**Guardrails for Cowork (important):**
- **Stop before Submit.** The form has confirmation checkboxes (legal attestations) and a Submit that starts the review — you make that call, not Cowork. Have it fill everything, then hand back for your review + final click.
- **Never paste secrets into chat.** Test-account credentials and any tokens go directly into the browser form fields, not into the Cowork conversation. Tell Cowork to type them into the page, not echo them.
- **One in-review version at a time** — if you need to change something after submitting, "Cancel Review" rather than creating a second app (OpenAI constraint).
- After Submit: you get an email with a **Case ID**; status shows in the dashboard.

---

## 6. The honest readiness statement

**Technically, the tools are submission-shaped** (annotations, schemas, copy, auth, clean URL — all done). **The remaining blockers are non-code:** a published privacy policy, a seeded demo account, identity verification, logo + screenshots, and a confirmed-rendering `trace` widget for the hero shot. None are hard; all are yours (or content/legal), not engineering. Close §4's ❌/⚠️ rows, then run §5.
