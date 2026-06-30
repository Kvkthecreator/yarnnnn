# ADR-386 — Workspace Members: the Grant Lifecycle (auto-provision · revoke/evict · narrow)

> **Status**: **Accepted** (2026-06-29) — doc-first, operator-signed-off; implementation (§6) follows in the same arc. Backend lifecycle + two operator verbs; **no schema migration** (the grant table already carries `status` + `scopes`, ADR-373 migration 189).
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: the grant-consult ship session (2026-06-29) + the live substrate survey — 11 owner grants (NULL scopes) ONLY, 13 registered MCP clients (8 Claude / 3 ChatGPT / 2 test), **126 tokens but 7 (client,user) pairs and 1 distinct user** = the real demand is *one human connecting their own external LLMs*. Design for the open set; build only for what is knocking.
> **Builds on**: [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) — the per-principal **grant-consult is Implemented** (`principal_grants` + `resolve_principal_id` + `_is_path_locked_for_principal`, the gate honors grants with class-default fallback, owner/NULL-scope proven byte-identical 99/0). ADR-373 shipped the consult that *reads* grants; **this ADR ships the lifecycle that creates + governs them.** It resolves ADR-373 D4's deferred "provisioning UX" — at the floor (foreign-llm auto-provision + revoke/narrow), NOT the full role taxonomy.
> **Companion (the consumer)**: [ADR-385](ADR-385-channels-the-perception-and-principal-surface.md) (Proposed, concurrent lane) — surfaces `foreign-llm` members as an *External Agents* perception channel (a filtered mount of the existing `WorkspaceMembersCard`, `role ∈ {foreign-llm, a2a, platform}`). **ADR-385 is the VIEW; this ADR is the LIFECYCLE.** Load-bearing dependency: 385's External Agents pane is **EMPTY until this ADR's auto-provision populates it** — today there are zero `foreign-llm` grant rows, so a Members/External-Agents surface reading `principal_grants` shows only the owner. This ADR is what makes those surfaces non-trivial. The two compose with no FE collision (385 owns the Channels surface; this owns Settings → Access verbs + the backend) and no authorization overlap (385 reads, this writes).
> **Preserves**: [ADR-286](ADR-286-kernel-program-substrate-single-writer.md) (single-writer-per-path — a foreign-llm member writes its own `inbound/mcp/{client}/` raw lane + the `operation/` commons; no co-write), [ADR-307](ADR-307-unified-permission-taxonomy.md) (the single gate — this ADR adds NO gate logic; revoke = eviction makes the consult untouched, §3), [ADR-288](ADR-288-caller-identity.md) (attribution per-principal — the membership names match the `authored_by` taxonomy), [ADR-371](ADR-371-mcp-self-contained-auth-boundary.md) (the OAuth mechanism — auto-provision hooks the existing token-mint, changes no auth flow), [ADR-320](ADR-320-constitution-region-topological-cut.md)/[ADR-366](ADR-366-autonomy-mode-as-execution-breadth.md) (the topology + breadth model — `scopes` narrows *within* the class ceiling, never widens past it).
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — principals become governed members of the workspace) + **Substrate** (Axiom 1 — the grant row is the authorization fact; its lifecycle is substrate state).

---

## 1. The decision in one sentence

**An external LLM that connects via OAuth automatically becomes a named, revocable `foreign-llm` member of the workspace (a `principal_grants` row, lazily ensured at token-mint); the operator can then NARROW its write-region (tighten `scopes` below the class default) or REVOKE it (full eviction — grant revoked + OAuth tokens deleted); the `owner` grant is immutable from the surface, and the four not-yet-pressured roles (`member`/`own-agent`/`platform`/`a2a`) keep their schema slots + documented defaults but no provisioning path until their principal type appears.**

## 2. Why this is the right floor (grounded in the live N)

The grant-consult shipped the *reading* of grants, but **the only grants that exist are the 11 owner backfills** (ADR-373 migration 189). So the multi-principal authorization is wired and inert: there is no member to govern, and ADR-385's External Agents pane would render empty. The live data names exactly one real pressure — **one human, connecting Claude + ChatGPT to their own workspace** (1 distinct user across all MCP tokens). That is the principal class this ADR makes real.

The discipline (the operator's framing, [[the imagined-consumer guard]] flipped — ADR-373 §2): **the non-human principal already exists in production** (the `foreign-llm` caller ships today; 13 clients are registered). Auto-provisioning its grant is *generalizing a model the code already half-implements* — the consult already treats it as `mcp`-class; this just makes the membership a legible, governable row instead of an invisible class-default. We are not building ahead of demand; we are making an existing principal accountable.

Conversely: there is **no second human, no third-party platform**. Building human-invite UX or platform-onboarding now would be the speculative build ADR-373 D4 deferred. So those roles stay name-only.

## 3. The decisions

### D1 — Foreign-LLM grants auto-provision on OAuth connect

When an external LLM completes the OAuth flow (`mcp_server/oauth_provider.py::exchange_authorization_code`, the token-mint that already carries `client_id` + `user_id`), the system **lazily ensures** a grant:

```
principal_grants(
  principal_id = client_id,                     -- the OAuth client (the room: claude.ai/chatgpt)
  workspace_id = resolve_owner_workspace_id(user_id),
  role         = 'foreign-llm',
  scopes       = NULL,                           -- class default (operation/ commons + inbound/ raw lane)
  granted_by   = 'system:oauth-connect',
  status       = 'active'
)
```

Idempotent (the `uq_principal_grant_active` partial unique index makes a repeat a no-op). The member appears in Workspace Members → Access immediately, named (`Claude` / `ChatGPT`, resolved from `mcp_oauth_clients.client_name`), with its write-region rendered.

**Provisioning site — AMENDED 2026-06-30 (D1.a):** the original spec fired auto-provision at **initial authorize only** (`exchange_authorization_code`), reasoning a refresh implies the grant already exists. A live-substrate measurement (2026-06-30) falsified that reasoning's *completeness*: **every connected LLM in production (all 7 active clients) authorized BEFORE the hook deployed, and stays alive indefinitely via silent `exchange_refresh_token` rotation — which never fired the authorize-only hook.** Result: real, writing foreign-LLM principals ("Claude saved to memory") with **zero grant rows**, and an External-Agents pane that read empty while the LLMs were demonstrably active. The authorize-only site was correct for *new* connectors but left the entire *already-connected* population permanently invisible.

The honest model is **membership tracks "has a live token + writes the commons," not "happened to authorize after the hook shipped."** So provisioning now fires on **BOTH** OAuth token-mint paths:
- `exchange_authorization_code` (D1, the first connect) — unchanged.
- `exchange_refresh_token` (D1.a, the silent rotation) — added. Idempotent (the partial-unique index makes the steady-state rotation a no-op after the first); a pre-hook connector self-heals into a grant on its next rotation (minutes-to-hours).

Both sites call the same `ensure_principal_grant`; both are best-effort (a grant failure never breaks the token flow). This makes the gap structural-proof: no foreign LLM that holds a live token can stay an invisible non-member, regardless of *when* it first connected.

**Why auto, not operator-admit:** the consult *already* authorizes the connected LLM at the `mcp` class default — it can already write `operation/`. The choice is only whether that capability is *legible + revocable* (a row) or *implicit + invisible* (a class fall-through). Auto-provision makes membership honest the moment it is real, rather than surfacing it only after misuse. The grant is the audit + control handle for a capability that exists regardless.

### D2 — Two operator verbs on existing members: NARROW and REVOKE

The Workspace Members panel (read-only as shipped, ADR-373) gains two verbs, operating **only on grants that already exist** (no invite flow):

- **NARROW** — tighten the member's `scopes` below its class default (e.g. restrict a foreign-LLM to `operation/memory/` only, or to a single domain). Authz-only: writes `principal_grants.scopes`, the OAuth token is untouched, the LLM stays connected and can still read. This directly exercises the **grant-honored allow-list path the consult already supports** (ADR-373 D2). A narrow can only *reduce* reach within the class ceiling; it can never widen past it.

- **REVOKE = FULL EVICTION** — the member is removed. Two coupled writes: (a) `principal_grants.status = 'revoked'` (the audit record of the eviction), and (b) **delete the principal's OAuth access + refresh tokens** (`mcp_oauth_*_tokens` by `client_id`). The external LLM is fully disconnected — it can no longer authenticate, read, or write; reconnecting requires a fresh OAuth authorize (which re-auto-provisions a new active grant, D1). This is the crisp, honest semantic of "revoke this member": *gone*, not "can write a bit less" (that is what NARROW is for).

**The verb split is the design's clarity:** NARROW adjusts authorization (token lives); REVOKE evicts (token dies). The operator never has to reason about a half-present member.

### D3 — Revoke-as-eviction needs NO gate change (the dividend)

A naive "revoke = deny" would force the consult to treat `status='revoked'` as a hard DENY — a new gate branch, a new failure mode to test. **Eviction makes that unnecessary:** a revoked principal has no OAuth token, so it cannot authenticate, so it never reaches the gate at all. The consult keeps querying `status='active'` exactly as it does today; `revoked` is a pure audit record, never consulted on a hot path. **One less moving part in the highest-blast-radius function in the system.** The grant-consult shipped in ADR-373 is final; this ADR does not touch it.

### D4 — The owner grant is immutable from the surface

The `owner` row exposes **no** NARROW/REVOKE verbs (FE), and the lifecycle endpoints **hard-reject** any mutation targeting a grant with `role='owner'` (BE, 403) — belt-and-suspenders. The operator cannot revoke or narrow their own all-but-`system/` access through this surface, so the catastrophic self-lockout is impossible by construction. (Transferring ownership is a separate, deliberate flow, out of scope.)

### D5 — Two roles real, four name-only

| Role | Status at launch | Default write-region | Provisioning |
|---|---|---|---|
| `owner` | **REAL** | all roots except `system/` | exists (signup / migration 189 backfill); immutable here (D4) |
| `foreign-llm` | **REAL** | `operation/` commons + `inbound/mcp/{client}/` raw lane | auto on OAuth connect (D1); narrow/revoke (D2) |
| `member` (human) | name-only | `operation/` + `agents/` (the agent-class shape applied to a collaborator) | **deferred** — blocked by the re-key (D6), not by demand |
| `own-agent` | name-only | per-grant within the `member` ceiling | **deferred** — couples to dispatcher integration |
| `platform` | name-only | `operation/` source-intake region | **deferred** — no platform principal exists (future Linear/Slack) |
| `a2a` | name-only | `operation/` commons (lowest-trust floor) | **deferred** — `a2a:` prefix not yet in `VALID_AUTHOR_PREFIXES` (ADR-371 D3) |

Name-only = the schema slot + the documented class default exist (the model is genuinely multi-principal, not owner-only), but no code path creates such a grant yet. Each lights up when its principal type first appears in production — additive grant rows, no schema change (ADR-373 D4).

### D6 — The `member` (multi-human) role's hard prerequisite is the substrate re-key — NOT demand

The instinct is to defer `member` because "no second human exists." That is true but soft, and it hides the real gate. A live-code measurement (2026-06-29) found the precise blocker:

- **Substrate is still `user_id`-keyed at the data layer.** Every substrate read/write scopes on `.eq("user_id", …)`; the write path (`authored_substrate.py`) carries the `UNIQUE(user_id, path)` constraint + the `on_conflict="user_id,path"` upsert. **Zero substrate queries key on `workspace_id` for reads.** ADR-373 Phase 1 shipped the *schema* re-key (the `workspace_id` column, backfilled) + the `AuthenticatedClient` chokepoint — but the **118-site query sweep is NOT done** (`workspace_id` is threaded to exactly one read site).
- **`resolve_owner_workspace_id` resolves by `owner_id`** — it structurally *cannot* resolve a workspace for a non-owner member. A second human's `user_id` → *their own* singleton workspace, not the one they hold a grant into.

So a `member` grant today would be **honored by the gate (authorization) but ignored by the data layer (scoping)**: the grant says "you may write workspace X," but every substrate query still scopes to the member's own `user_id` ≠ workspace X's data. That is a silent correctness hole, not a partial feature.

**Why `foreign-llm` is exempt** (and why it ships here while `member` cannot): a foreign LLM authenticates **as the operator** — the OAuth token carries the *operator's* `user_id` (`auth.py`). So its substrate scoping rides the human's identity and lands on the right data *by construction*; the `client_id` distinguishes it only for attribution + authorization (the grant + the `trace` chain), which is exactly the layer this ADR governs. The data-scoping re-key is irrelevant to it.

**The precise statement**: `member`'s hard prerequisite is **completing the ADR-373 substrate re-key** (the ~118-site `user_id → workspace_id` sweep + membership RLS cutover + a `resolve_member_workspace_id` that resolves by grant, not ownership) — the same *shape* of prerequisite that the grant-consult was for `foreign-llm`. It is a separate, pre-launch-sized project (ADR-373 §4 named the sweep "foundational; multi-day, chokepointed"), not a section of this ADR. Until it lands, `member` stays name-only — and the deferral is honest about *why*: the substrate, not the market.

## 4. What this does NOT do

- **No human-invite / member-provisioning UX.** ADR-373 D4 defers it; zero second humans exist. The `member` slot is name-only (D5).
- **No new gate logic.** Revoke-as-eviction sidesteps the consult entirely (D3); narrow uses the already-shipped allow-list path.
- **No schema migration.** `principal_grants` already carries `status` + `scopes` (migration 189). The work is INSERT-on-connect, UPDATE-scopes, and DELETE-tokens-on-revoke.
- **No perception surface.** The External Agents channel is ADR-385's; this populates the data it reads, it does not build the view.
- **No platform / a2a / own-agent provisioning.** Name-only (D5); built when their principal appears.

## 5. Rejected alternatives

- **Stay class-default; operator explicitly admits each LLM.** Rejected (D1): the connected LLM is already authorized at the class default — leaving it invisible until manually admitted means the membership is *implicit and ungoverned* during the exact window it is active. Auto-provision makes the real capability legible + revocable.
- **Revoke = grant-only (token lives), with a "revoked = hard deny" consult branch.** Rejected (D3): adds a new branch to the highest-blast-radius function and a half-present-member state the operator must reason about. Eviction is both the cleaner mental model and the smaller change.
- **Fold this into ADR-385 (one external-agents ADR).** Rejected on concurrent-lane discipline: ADR-385 is an uncommitted, untracked draft owned by another lane, classified as pure **Channel**/presentation ("no new authorization machinery"). Folding authorization *lifecycle* into it corrupts its thesis and risks a conflict on in-flight work. Separate concerns, separate records, cross-referenced (Singular Implementation is a code property, not an ADR-count one).
- **Fully specify all six roles now.** Rejected (D5): four of six have no live principal; specifying their provisioning + lifecycle would lock in a role model (esp. `own-agent` scoping) before the integration that would inform it. Build for what is knocking.

- **Open up multi-human (`member`) in this ADR.** Rejected (D6) — and the rejection is the clarifying thought experiment, preserved here: the multi-human blocker is **not** demand, it is the unfinished ADR-373 substrate re-key. Substrate is still `user_id`-keyed (118-site sweep undone; `resolve_owner_workspace_id` resolves by ownership). A `member` grant today would authorize at the gate but mis-scope at the data layer (every query still keys on the member's own `user_id`, not the granted workspace) — a silent correctness hole. `foreign-llm` escapes this because it authenticates *as the operator* and rides the operator's `user_id` scoping. So multi-human is a separate, pre-launch-sized project (the re-key sweep), not a section of this ADR; `member` is `re-key`-gated exactly as `foreign-llm` was `consult`-gated.
- ~~**Auto-provision on every token refresh.** Rejected (D1): a refresh implies an existing grant; firing at authorize-only is semantically correct (idempotency makes refresh harmless but redundant).~~ **REVERSED 2026-06-30 (D1.a).** The "a refresh implies an existing grant" premise holds only for connectors that authorized *after* the hook shipped. The live population authorized *before* it, so for them a refresh is the ONLY token-mint event that ever happens — and authorize-only left them grant-less + invisible. Refresh-path provisioning is now the durable fix (idempotent; the steady-state rotation is a no-op; a pre-hook connector self-heals on its next rotation). The original "harmless but redundant" judgment was right about the *steady state* and wrong about the *transition* — and the transition is the entire live N.

## 6. Implementation spec (sequenced, reversible, test-gated)

Cheapest-and-safest first; each step green before the next.

1. **[BACKEND — helpers]** `services/principal_grants.py` (new): `ensure_principal_grant(client, principal_id, workspace_id, role, scopes=None, granted_by)` (idempotent upsert on the active partial-unique key) + `narrow_grant(client, principal_id, workspace_id, scopes)` (UPDATE scopes; reject owner) + `evict_principal(client, principal_id, workspace_id)` (UPDATE status='revoked' + delete OAuth tokens by client_id; reject owner). All service-client; all reject `role='owner'`.
2. **[BACKEND — OAuth token deletion by client]** `mcp_server/oauth_provider.py`: add `delete_tokens_for_client(client_id)` (sibling of the existing by-token deletes at :357/374-376) — deletes from `mcp_oauth_access_tokens` + `mcp_oauth_refresh_tokens` by `client_id`. Used by `evict_principal`.
3. **[BACKEND — the auto-provision hook]** `exchange_authorization_code` (oauth_provider.py:~230): after the token insert, call `ensure_principal_grant(principal_id=client.client_id, workspace_id=resolve_owner_workspace_id(user_id), role='foreign-llm', granted_by='system:oauth-connect')`. Best-effort + logged — a grant-ensure failure must NOT break the OAuth flow (the consult still falls to class-default, so the LLM is not locked out).
3a. **[BACKEND — the refresh-path hook]** (D1.a, 2026-06-30) `exchange_refresh_token` (oauth_provider.py:~315): the SAME `ensure_principal_grant` call after the rotated-token insert, `granted_by='system:oauth-refresh'`. Idempotent (no-op once the grant exists); a pre-hook connector self-heals on its next silent rotation. Same best-effort try/except. Singular: one helper, two hook sites — the shared block is extracted to a private `_ensure_foreign_llm_grant(user_id, client_id, granted_by)` so the two paths can't drift.
3b. **[BACKEND — one-time backfill]** (D1.a) `scripts/backfill_foreign_llm_grants.py`: for every `mcp_oauth_clients` row with a live access OR refresh token, resolve the authorizing user → owner workspace and `ensure_principal_grant(role='foreign-llm', granted_by='system:adr386-backfill')`. Idempotent, re-runnable. Populates the pane NOW rather than waiting for each connector's next rotation. Belt-and-suspenders with 3a (the durable fix).
4. **[BACKEND — endpoints]** `routes/workspace.py`: `POST /api/workspace/members/{principal_id}/narrow` (body: `scopes: list[str]`) + `POST /api/workspace/members/{principal_id}/revoke`. Both resolve the caller's workspace, reject owner-targeted mutations (403), call the §6.1 helpers.
5. **[FE — the verbs]** `WorkspaceMembersCard.tsx`: add Revoke + Narrow affordances per member row, **hidden on the owner row**. Narrow = a region multi-select (the ADR-320 roots, presented as friendly labels — reuse `REGION_LABEL`). **Revoke MUST emphasize the eviction weight** (operator requirement, 2026-06-29): a deliberate confirmation modal/alert — not an inline one-click — that names the consequence plainly ("Disconnect Claude? It loses all access immediately and must re-authorize from scratch to return. This deletes its connection tokens."). The emphasis is the point: revoke is a full eviction (D2/D3), and the surface must make that irreversible-feeling weight legible *before* the click, distinct from the lightweight Narrow. Optimistic refresh via the existing `getMembers`.
6. **[TESTS]** `api/test_adr386_member_lifecycle.py`: auto-provision idempotency; narrow tightens (and the consult then denies outside the narrowed set — reuse the grant-honored harness); revoke flips status + deletes tokens; **owner-immutability (narrow/revoke owner → 403)**; auto-provision failure does not break OAuth. Plus the live N=1 check: an OAuth connect against a real workspace produces exactly one `foreign-llm` row.

**Validation gap (named, not faked):** the multi-human `member` path stays unexercised (no second human, ADR-373 D5 / triple-check R4). This ADR's live-validatable surface is the foreign-LLM lifecycle only; `member`/`own-agent`/`platform`/`a2a` are name-only and validate when their principal appears.

**D1.a validation (2026-06-30):** the original "auto-provision validated, first firing awaits a real connect" gap is CLOSED differently than expected — not by a browser re-authorize (the connectors rotate refresh tokens rather than re-authorize, so that never fired), but by the refresh-path hook (3a) + backfill (3b). The backfill provisions the live population against the production DB (receipt: N foreign-llm grants appear, the External-Agents → AI Connections pane renders them named + revocable); the refresh hook keeps it durable. This is the honest live-firing the authorize-only spec couldn't produce.

## 7. Doc cascade (when this implements)

- ADR-373 status: D4's "provisioning UX deferred" → "foreign-llm provisioning Implemented (ADR-386); member/agent/platform/a2a deferred."
- ADR-385: cross-reference confirmed — its External Agents pane is populated by this ADR's auto-provision.
- CLAUDE.md schema (`principal_grants`): add the lifecycle (auto-provision site + revoke=eviction + the two endpoints).
- `WORKSPACE.md` (design surface contracts): the Workspace Members panel gains its CRUD shape (read + narrow + revoke; no create/invite).

---

**This ADR makes the grant-consult's machinery *exercised*.** ADR-373 wired the gate to honor grants; until a non-owner grant exists, that wiring is inert and ADR-385's surfaces are empty. The foreign-LLM lifecycle — auto-provision on connect, narrow/evict on demand — is the smallest, most honest set of grant rows the live workspace actually needs, and it turns the dormant-lock fix (ADR-373, the activated MCP topology lock) into something an operator can *see and steer*: the external LLMs reaching into their workspace, named, scoped, and revocable.
