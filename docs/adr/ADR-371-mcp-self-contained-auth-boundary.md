# ADR-371 — The MCP Service as a Self-Contained Auth Boundary

> **Renumbered 2026-06-26**: was ADR-370; collided with ADR-370 (Context — the operation's boundary surface), which is the more heavily-referenced 370 and keeps the number. This auth-boundary ADR moved to 371. Content unchanged; status preserved.
> **Status**: **Accepted** (2026-06-25) — model ratified; the §D2 build-shape decision is RESOLVED (A1 — a tiny standalone auth frontend, shared DB). Ready for implementation.
> **Date**: 2026-06-25
> **Authors**: KVK + Claude
> **Discourse base**: [`docs/analysis/mcp-onboarding-surface-design-2026-06-25.md`](../analysis/mcp-onboarding-surface-design-2026-06-25.md) (the framing correction + the two-principal model) + [`docs/analysis/cross-llm-data-handling-and-use-cases-2026-06-25.md`](../analysis/cross-llm-data-handling-and-use-cases-2026-06-25.md) (the data-handling guarantees).
> **Supersedes**: [ADR-310](ADR-310-judged-substrate-interop-face.md) **D4's login *mechanism*** — the `authorize()` redirect to `yarnnn.com/mcp/authorize` + the cockpit-Supabase-session coupling. ADR-310 D4's **per-request identity *principle* SURVIVES** (each caller resolves to its own scope; isolation by `.eq("user_id", …)`); only *how the caller authenticates* changes.
> **Preserves**: [ADR-368](ADR-368-memory-first-interop-surface.md) (the memory verbs + dump/placement + the `yarnnn:mcp:<client>` attribution), [ADR-311](ADR-311-primitive-interop-surface.md) D7 (protocol-agnostic verbs — A2A is the second binding this ADR makes concrete at the auth layer), [ADR-320/366](ADR-320-constitution-region-topological-cut.md) (the permission topology a new caller-class slots into), [ADR-310](ADR-310-judged-substrate-interop-face.md) D5 (shared-workspace deferral — the `user_id→workspace_id` re-key A2A shares).
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — who authenticates + how the caller is attributed) + **Channel** (Axiom 6 — the "Foreign LLM / agent via MCP" channel's auth shape).

---

## 1. The correction this ADR ratifies

ADR-310 D4 made MCP **multi-user** by resolving identity per-request — correct and preserved. But it implemented the *login* by **redirecting the browser out to `yarnnn.com`** (the cockpit's Supabase session does the auth, then `/api/mcp/oauth-callback` binds it). That coupling is the error this ADR corrects.

**The operator's reframe (2026-06-25):** MCP signup/login should be **headless and self-contained on the MCP service** — it happens inside the OAuth handshake the LLM initiates, *in ChatGPT/Claude*, with **no trip to yarnnn.com, no cockpit**. It is **API-shaped, not app-shaped.** And *that* is why it is consistent with A2A: if the human path authenticates directly against the MCP boundary (lightweight), then human and agent do the **same shape of thing** — authenticate-to-endpoint → token → call verbs — differing only in *credential type*. One auth model, two credentials. This is not just cleaner UX; it is **better data handling**: one identity-resolution path, one attribution model, one permission gate, no app-coupled second path to keep consistent.

The wrong mindset (now retired): treating this as "onboarding" with a `/connect` page, a confirmation surface, and "cockpit graduation." The right mindset: **the MCP service is its own auth boundary**, and onboarding is almost entirely *docs/marketing* (the connector URL + per-LLM setup steps), not a product surface.

## 2. The model — one boundary, two principals, two credentials

| | **Human** | **Agent (A2A)** |
|---|---|---|
| Credential | Lightweight login (MCP-served) | `client_credentials` (client_id + secret) |
| UI | Minimal sign-in IN the OAuth popup, then closes | None — pure token endpoint |
| Grant | `authorization_code` (interactive) | `client_credentials` (machine) |
| Identity bound | The human's `user_id` | The agent's own identity |
| Attribution | `yarnnn:mcp:<client>` (ADR-368 §3) | `a2a:<agent-id>` (new `a2a:` prefix) |
| Where | `mcp.yarnnn.com` | `mcp.yarnnn.com/token` |
| Gate | lowest-trust, `operation/` commons only | identical (lowest-trust) |
| Judgment | Reviewer places + judges (ADR-368 D5) | identical |

Everything except the credential and the attribution prefix is **shared**. That sharing is the thesis.

## 3. The honest constraints (named so the decision is real)

### C1 — A human signup cannot be fully zero-UI (OAuth security floor)
A human creating an account must prove identity (password, or Google consent). That **requires a UI moment** — ChatGPT pops a browser for exactly this; it cannot be collected headlessly inside a tool call. So "headless" for the human path means **minimal + MCP-served**, NOT *no UI*. An agent has no such floor (`client_credentials` is pure token exchange, no UI). This asymmetry is intrinsic, not a design failure.

### C2 — The MCP service has no user-auth capability today
The MCP service holds the Supabase **service key** only — it can read/write `mcp_oauth_*` but cannot *log a user in*. **That is why** ADR-310 D4 redirects to yarnnn.com (the web app's Supabase client does the login). Making auth self-contained means **giving the MCP service its own user-login capability**. This is the real, bounded work this ADR authorizes — not a copy-paste.

### C3 — The A2A-shaped precedent already exists
The **static-bearer path** (`MCP_BEARER_TOKEN` / `MCP_USER_ID`, used by Claude Desktop) is *already* a non-interactive, token-based auth mapping to a user — the A2A model, partly built. A2A generalizes it (per-agent credentials, not one env token); the human path adds a thin login to mint the per-user equivalent. The architecture is not foreign to the codebase.

## D. Decisions

### D1 — The MCP service authenticates its own callers (the principle)
The interop face is a self-contained auth boundary. Identity resolution (`resolve_request_client`) stays per-request (ADR-310 D4 preserved), but the *credential is presented to and validated by the MCP boundary*, not delegated to the cockpit. The `authorize()` redirect to `yarnnn.com` and the cockpit-session coupling are removed.

### D2 — The human-login build shape: **A1 — a tiny standalone auth frontend, shared DB** (DECIDED 2026-06-25)

The MCP human-login is a **dedicated, minimal auth frontend** (a few pages + Supabase JS), deployed standalone on the MCP auth domain (`mcp.yarnnn.com` or `auth.yarnnn.com`), serving the login moment inside the OAuth popup — **no trip to yarnnn.com, no cockpit.** The chosen shape, with its load-bearing constraints:

**Constraint 1 — the DB is MANDATORILY SHARED (the constraint that makes this "tiny").** The auth frontend authenticates against the **same Supabase project, the same `auth.users`, the same workspace substrate** as yarnnn.com. It is NOT a separate identity system — it is a **separate door to the same account.** A user who signs up via the MCP auth frontend gets a real yarnnn account, byte-identical to one created on yarnnn.com. This is what keeps A1 small: it's not a parallel auth stack, it's a few pages running the *same Supabase JS auth the web app already runs*, deployed standalone and styled minimal. (Were the DB separate, this would be a whole parallel identity system — huge. Shared DB → tiny.)

**Constraint 2 — separate ONBOARDING, shared ACCESS.** The user onboards through the lightweight MCP door (headless, in-popup). **Thereafter they can always go to yarnnn.com** and log into the full cockpit with the *same credentials* — same account, same substrate. The separation is at the *connect moment*, not a permanent product partition. The MCP auth frontend is a thin alternate entrance to the same building, never a different building.

**Why A1 over the alternatives** (sub-shapes considered):
- **A1 (chosen)** — a standalone-*shaped* minimal auth frontend. Genuinely self-contained at the connect moment; keeps the Python FastMCP service doing only protocol + token endpoints (what it's built for); the distinction pays off for future independence (white-label/embedded) without forking identity.
- **A2 (rejected)** — make the pure-Python FastMCP service serve HTML auth itself. Rejected: forces a protocol backend to do browser-auth UI (Google consent, email flows) it's architecturally not meant to — fighting the framework, a tar pit. The MCP service is `__init__/__main__/auth/oauth_provider/server` — no frontend, by design.
- **Option B (rejected)** — redirect to a stripped page on the web app. Rejected: not fully self-contained; the operator is explicitly pushing for the separation to "pay off in future." A1 is the terminal-pure form and worth building now.

**A1 build sub-shape — A1-lite (chosen at implementation, 2026-06-25):** A1 has two build paths to the same outcome:
- **A1-lite (CHOSEN)** — an **isolated auth route-group inside the existing web app**, served under the MCP auth domain, styled minimal, structurally walled off from the cockpit (its own route tree, never renders `/desktop` chrome, never lands a user in the cockpit). Reuses the web app's Supabase client (shared anon key, shared `auth.users` — Constraint 1 satisfied). Delivers **everything the A1 decision required** — separate onboarding door, shared DB/account, never the cockpit, future-independent — **without a 5th deployable.** This is the build form.
- **A1-full (deferred-compatible)** — extract that route-group into a genuinely separate deployment (`auth.yarnnn.com`, own Vercel/Render project) **if** a near-term requirement demands deployment-level isolation (white-label/embedded where the web app can't be in the loop at all). A1-lite is forward-compatible: the extraction is moving an isolated route tree, not a rewrite.

The decision principle holds either way (separate door, shared DB, never the cockpit); A1-lite is the cost-appropriate realization. Building a separate deployment for a handful of auth pages with no isolation requirement yet would be premature.

**The one infra touch beyond the frontend:** because the DB/auth config is shared, the MCP auth domain must be added to the Supabase project's **allowed redirect URLs** (+ the Google OAuth client's authorized origins). A config addition to the *existing* project — NOT a new Supabase project. Email templates may want an MCP-aware variant but can reuse the defaults.

### D3 — A2A is the second binding, designed-in-contract, build-deferred
A2A's auth is the `client_credentials` grant on the MCP token endpoint. The OAuth client model **already carries the fields** (`client_secret`, `grant_types`, `token_endpoint_auth_method` — `oauth_provider.py`); `grant_types` accepts `["client_credentials"]`. The contracts are fixed now (per discourse §8): separate door / shared destination; `authored_by="a2a:<agent-id>"` (new `a2a:` prefix in `VALID_AUTHOR_PREFIXES`); same gate + judgment as the `mcp` caller; capability-scoped via the OAuth `scope` field; revocable + auditable (every A2A invocation emits a narrative entry per ADR-368 D4).
**Build-deferred** until a real agent caller exists (the imagined-consumer guard). The provisioning UI + `client_credentials` wiring wait; A2A becomes **its own ADR** when a concrete caller appears, inheriting these contracts.

### D4 — A2A's foundational dependency is the shared workspace re-key
A2A needs **agent-distinct identity** (the agent acts on a workspace but is not its human owner). This is the **same `user_id → workspace_id` re-key ADR-310 D5 already defers** for shared-workspace. One re-key unlocks both futures. Until it happens, both are correctly deferred *for the same reason*. When the re-key is scoped, scope it to serve both — not one. The human path (D1/D2) needs **no** re-key; it ships on the current 1:1 model.

### D5 — Onboarding is docs/marketing, not a product surface
There is no `/connect` page, no confirmation surface, no cockpit graduation in the kernel. The "here's your connector URL (`https://mcp.yarnnn.com/mcp` — with the path) + per-LLM setup steps" content lives on the **landing site / setup docs**. The only product UI is the thin auth page (Option A or B). This is what "almost no front-end" means.

## 4. What this supersedes / amends

- **Supersedes** ADR-310 D4's login *mechanism* (the yarnnn.com redirect + cockpit coupling in `oauth_provider.py::authorize` lines ~137/171 + the `/api/mcp/oauth-callback` cockpit handoff, depending on D2 choice). ADR-310 D4's **per-request identity principle is preserved**.
- **Preserves** ADR-310 D5 (shared-workspace deferral — D4 above leans on it), ADR-368 (verbs + attribution; `a2a:` extends the same model), ADR-311 D7 (A2A as second binding), ADR-320/366 (a new caller-class is one `CALLER_WRITE_POLICY` entry).
- **Amends** (on implementation) `api/mcp_server/oauth_provider.py` (the `authorize` flow), `api/mcp_server/auth.py` (identity resolution unchanged in principle), and — per D3 when A2A builds — `VALID_AUTHOR_PREFIXES` (+`a2a:`) and a `client_credentials` token path.

## 5. Implementation sequencing (D2 resolved = A1)

1. **Slice 0 — Supabase config**: add the MCP auth domain to allowed redirect URLs + Google authorized origins (existing project, not new). Prerequisite for A1.
2. **Slice 1 — the standalone auth frontend (A1)**: a minimal deployable (a few pages + Supabase JS, same anon key as the web app) on the MCP auth domain. Serves login/signup in the OAuth popup; on success, returns to the LLM — never `/desktop`. Rewire `oauth_provider.py::authorize` to point the popup here instead of `yarnnn.com/mcp/authorize`; the bind step (`/api/mcp/oauth-callback` or its A1 equivalent) preserves per-request identity (ADR-310 D4). Ships on the 1:1 model, no re-key.
3. **Slice 2 — the connector-URL docs** (`mcp.yarnnn.com/mcp` with path + per-LLM steps) on the landing/setup surface. Kills the bare-domain 404. Pure content.
4. **A2A** — deferred per D3; its own ADR when a caller is real; gated on the D4 re-key.

**Render parity note:** A1 is a new deployable (a 5th surface — a static/thin frontend). It needs the shared `SUPABASE_URL` + `SUPABASE_ANON_KEY` (NOT the service key — anon key only, this is a user-facing auth client). Document it in the Render service table on build.

## 6. Rejected alternatives

- **The `/connect` onboarding surface** (the original discourse §0–§7) — app-onboarding thinking; rejected by the framing correction. The MCP boundary is API-shaped; onboarding is docs, not a product flow.
- **Fully zero-UI human signup** (API-key paste) — rejected: worse UX for non-technical users, and the human-UI floor (C1) means a login moment is unavoidable anyway; the win is making it *minimal*, not *absent*.
- **D2 Option B** (strip the redirect to an MCP-scoped page on the web app) — rejected in favor of A1: the operator is pushing for the separation to pay off in future independence; A1 is the terminal-pure form and worth building now, kept tiny by the shared-DB constraint.
- **D2 sub-shape A2** (the Python FastMCP service serves HTML auth) — rejected: forces a protocol backend to do browser-auth UI; fights the framework.
- **A separate identity system / separate DB for MCP** — rejected (D2 Constraint 1): the DB is mandatorily shared; the MCP auth frontend is a separate *door* to the *same* account, not a separate identity. Separate-DB would make A1 a huge parallel auth stack instead of a few thin pages.
- **Designing A2A's full UI now** — deferred (D3): no real caller; the imagined-consumer trap. Contracts fixed; UI waits.
- **Doing the workspace re-key now to unlock A2A** — rejected as premature (D4): foundational change, demand-gated, not on the human-path critical path.
