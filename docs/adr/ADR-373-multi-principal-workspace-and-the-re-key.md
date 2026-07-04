# ADR-373 — The Multi-Principal Workspace and the `user_id → workspace_id` Re-Key

> **Status**: **Accepted** (2026-06-26). Foundational, pre-launch. Phased implementation: **Phase 1 (schema re-key) Implemented** (migration 189); **Phase 2 (the per-principal GRANT-CONSULT at the gate) Implemented 2026-06-29** — the gate authorizes at principal granularity via `principal_grants` with class-default fallback; the uniform `resolve_principal_id(auth)` keys owner→user_id / foreign-llm→OAuth client_id / agent→slug; the safety invariant (owner/NULL-scope = byte-identical to the pre-consult gate) is proven against all 11 live owner grants (99/0). A read-only **Workspace Members** legibility panel ships in Workspace Settings. Adjacent gate-fix landed in the same session: the MCP topology lock was DORMANT (exact `== "yarnnn:mcp"` matcher missed the live room-qualified `yarnnn:mcp:<client>` form) — fixed to `startswith`, activating the ADR-320-intended foreign-LLM lock. **Sweep spine Implemented 2026-07-04 (ADR-404 step 4, migration 198)**: grant-aware workspace resolution (`resolve_workspace_for_principal` — owner-first, `X-Workspace-Id` header validated fail-closed, fresh-invitee grant fallback) + request-scoped binding (`services/workspace_context.py` contextvar, published at `get_user_client`) + workspace-keyed substrate core (`authored_substrate` reads/head/tombstone/revisions + `UserMemory`/`AgentWorkspace` queries via `_scoped`; the live-row identity moves to UNIQUE `(workspace_id, path)` with a user_id-preserving update-or-insert — a member's write lands on the commons row instead of forking) + membership write RLS. Gate `api/test_adr373_sweep_spine.py` 26/26. **Named remainders**: route-level `.eq("user_id")` filters + `p_user_id` RPCs (re-key with member provisioning); legacy UNIQUE(user_id,path) drops in migration 199 after this code deploys. Provisioning UX + role richness remain post-launch (D4). See [`docs/analysis/adr373-grant-consult-AUDIT-FINDINGS-2026-06-29.md`](../analysis/adr373-grant-consult-AUDIT-FINDINGS-2026-06-29.md) + [`docs/analysis/adr373-grant-consult-implementation-scope-2026-06-29.md`](../analysis/adr373-grant-consult-implementation-scope-2026-06-29.md). **This satisfies the [ADR-384](ADR-384-the-re-founding-meaning-folders-permission-as-metadata.md) §7 re-founding prerequisite.**
> **Date**: 2026-06-26
> **Authors**: KVK (operator) + Claude (collaborator)
> **Completed by**: [ADR-378](ADR-378-the-workspace-as-the-outermost-unit.md) (2026-06-27) — this ADR establishes the workspace as the substrate's *binding unit* but stops *at* the boundary; ADR-378 names that the boundary **is** the ceiling (the workspace is the *outermost* unit YARNNN composes; federation across workspaces is the deliberately-unbuilt layer above it) and records the single-filesystem model (one commons, N attributed principals, kernel-concerns-as-metadata) as the rationale that makes the ceiling a strength.
> **Discourse base**: [`docs/analysis/the-three-rung-framework-and-the-multi-principal-wedge-2026-06-26.md`](../analysis/the-three-rung-framework-and-the-multi-principal-wedge-2026-06-26.md) — the metaphor test that named the substrate's true shape (ledger / membrane / steward), the multi-principal wedge decision (D2), the re-key-as-foundational call (D3), per-principal grant (D4), and the code-grounded implementation audit (§6) that found the seam pre-cut at every layer.
> **Supersedes**: [ADR-371](ADR-371-mcp-self-contained-auth-boundary.md)'s **1:1 identity assumption** ("1 account = 1 workspace = 1 user_id"). ADR-371's auth *mechanism* (self-contained boundary, in-popup login, `client_credentials` for A2A, shared-DB door) is **PRESERVED**; only identity *resolution* changes — `resolve_request_client` resolves a principal to `(workspace_id, grant)` rather than to a bare `user_id`. ADR-371 D4 already named this as the shared dependency it deferred; this ADR scopes it.
> **Preserves**: [ADR-209](ADR-209-authored-substrate.md) (the single write path `write_revision()` — re-keyed, not replaced; the revision chain becomes the per-principal diff), [ADR-286](ADR-286-single-writer-per-path.md) (single-writer-per-path — the discipline that makes multi-principal tractable *without* merge/CRDT), [ADR-320](ADR-320-constitution-region-topological-cut.md)/[ADR-366](ADR-366-autonomy-mode-as-execution-breadth.md) (the topology lock — `CALLER_WRITE_POLICY` becomes the per-principal-class *default grant*, not a deletion), [ADR-288](ADR-288-caller-identity.md) (`caller_identity` per-principal — the field the grant consults), [ADR-307](ADR-307-unified-permission-taxonomy.md) (the single gate at `execute_primitive`), [ADR-368](ADR-368-memory-first-interop-surface.md) (the memory verbs + the placement seat — already designed workspace-level, §D3 below), [ADR-310](ADR-310-judged-substrate-interop-face.md) D5 (the shared-workspace deferral this resolves).
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — the workspace gains an open set of principals, each authenticated and attributed as itself) + **Substrate** (Axiom 1 — the substrate's binding unit moves from the user to the workspace, an attributed commons many principals write to).

---

## 1. The decision in one sentence

**The binding unit of substrate is the workspace, not the user; an open set of *principals* (humans, their agents, other humans, third-party platforms, foreign and local LLMs) attribute into one shared, judged commons, each authorized by a per-principal grant; and the `user_id → workspace_id` re-key that makes this true is foundational and lands before launch.**

This is the moat at full strength (discourse base D2): *a single attributed substrate, written to by many principals, under one accountable judgment seat, served to every room each principal works in* — the version the frontier labs cannot occupy, because being the neutral commons across rival LLMs and arbitrary platforms is structurally incompatible with being any one of those principals.

## 2. Why this is foundational and pre-launch (not a later expansion)

The discourse base settled the strategy; this section records why it cannot wait.

- **The wedge IS multi-principal.** A *personal* substrate (one user, their own LLMs) wedges into the exact space the labs are most incentivized to own from inside their walls (ChatGPT memory, Claude Projects). A *multi-principal* substrate wedges into a structurally-unowned space. The wedge determines the data model; the data model cannot be retrofitted after launch onto live user data without a migration far more expensive than doing it now at launch scale (few rows, no SLA).
- **The imagined-consumer guard FLIPS.** The non-human principals already exist: the `mcp` caller ships today; agents ship today; A2A's `a2a:` prefix is spec'd (ADR-371 D3). The attribution taxonomy is *already* principal-agnostic (`VALID_AUTHOR_PREFIXES` = `operator` / `agent:` / `reviewer:` / `yarnnn:` / `specialist:` / `system:` / `dispatcher:`). **The keying is the only thing still stuck at `user_id`.** This is generalizing a model the code already half-implements — not building ahead of demand.
- **One re-key unlocks all futures.** ADR-310 D5 (shared workspace) and ADR-371 D4 (A2A) both defer the *same* `user_id → workspace_id` re-key. ADR-371 D4's own words: *"scope it to serve both — not one."* This ADR generalizes "both" to "all principals" and does the re-key once.

## 3. The decisions

### D1 — The workspace is the substrate's binding unit; the user becomes a member

A new `workspaces` table. Every substrate row (`workspace_files`, `workspace_file_versions`; `workspace_blobs` stays content-addressed and global, shared across workspaces by sha256 as today) is re-keyed from `user_id` to `workspace_id`. `user_id` does not vanish — it relocates to a **membership** fact (D2's `principal_grants`), not a substrate key.

**The 1:1 world is the N=1 case, by construction.** Backfill: every existing `user_id` → a singleton `workspace_id` (the workspace whose sole owner is that user). After backfill, a solo operator is a workspace with one human principal; a team is a workspace with N human principals; a pure-platform integration is a workspace with zero humans and K platform principals. **Same model; the principal count is data.** This is the proof the re-key is a clean generalization, not a rewrite: the singleton case reproduces today's exact behavior with zero functional change.

### D2 — A principal is any authenticated caller; authorization is a per-principal GRANT

A **principal** is any authenticated caller that reaches a workspace's substrate: a human, a human's own agent, another human, their agent, a third-party platform, a foreign LLM (claude.ai/ChatGPT via MCP), an open-source/local model (via A2A). Each principal is bound to a workspace by a **grant**:

```
principal_grants(
  principal_id      -- the caller's stable identity (auth.users.id for a human;
                    --   the agent slug; the OAuth client_id for MCP/A2A; …)
  workspace_id      -- the workspace this grant is for
  role              -- the principal-class role (D4): owner | member |
                    --   own-agent | foreign-llm | platform | a2a
  scopes            -- the write-region set this principal may author
                    --   (defaults to the role's class-default; D4)
  granted_by        -- attribution of who issued the grant (the owner, or system)
  status            -- active | revoked
)
```

The grant is the authorization unit. It **completes a symmetry the code already half-has**: today the system *attributes* at principal granularity (`agent:alpha-research`, `reviewer:ai-sonnet-v8`, `yarnnn:mcp:claude.ai`) but *authorizes* only at a coarse class level (`CALLER_WRITE_POLICY[class]`). After this ADR, *who may write here* is described at the same granularity as *who wrote here* — which is exactly what lets `trace` say "bob's agent, scoped to specs, wrote this" **with authority**.

#### D2.a — The foreign-LLM principal is the PROVIDER (host-id), not the OAuth client_id (AMENDED 2026-06-30)

The original D2 keyed the foreign-LLM `principal_id` on the **OAuth `client_id`** ("the OAuth client_id for MCP/A2A"). A live measurement (2026-06-30, prompted by the AI Connections roster showing 5 Claude + 2 ChatGPT rows) falsified that as the right grain:

- **`client_id` is an OAuth *session-registration* identity, not a *membership* identity.** Connectors re-register over dynamic client registration (DCR) on reconnect / version bump / token loss — each time minting a **brand-new `client_id`**. The live data: one human's Claude fragmented into **5** distinct `client_id`s (only 1 with a token today; 4 stale) and ChatGPT into **2**. Keying membership on `client_id` makes the roster grow an unbounded tail of dead registrations — one per reconnect, forever. That is not a display bug to group away; it is the wrong identity.
- **The operator's mental model is the PROVIDER**: "Claude is connected to my workspace" is *one* relationship, regardless of how many times its connector re-registered. The member is "Claude", not "this week's Claude OAuth client".

**The correction:** the foreign-LLM (+ platform/a2a) `principal_id` is the **stable provider/host id** resolved through the **ADR-379 Host Profiles registry** (`mcp_server/presentation/hosts.py::resolve_host_id` → `"chatgpt" | "claude.ai" | "gemini" | …`) — the SINGLE canonical identity resolver the codebase already owns (its CI gate forbids host-name resolution leaking elsewhere). One provider = one grant per workspace, across all its `client_id` re-registrations.

This is **non-breaking for the consult's safety invariant** and *strengthens* authorization:
- **`resolve_principal_id` (the consult key)** resolves the MCP caller to its host-id (it already carries `caller_identity = yarnnn:mcp:<client_name>`, and falls back to the registered name / client_id via `resolve_host_id`). The owner / agent / system branches are **untouched** — only the `yarnnn:mcp*` branch changes, so the owner-path byte-identical invariant (proven 99/0) is preserved by construction.
- **Narrowing now binds the provider, not a session.** Pre-amendment, an operator narrowing "Claude" would be escaped by Claude's next reconnect (new `client_id` → no grant → class default). Provider-keying closes that hole: the narrow attaches to `claude.ai`, and every Claude session — including future reconnects — inherits it. The amendment *fixes a latent narrow-escape bug*, it doesn't introduce risk.
- **Eviction sweeps all of the provider's tokens.** `evict_principal` must delete OAuth tokens across **every `client_id` registered to the host** (not by `principal_id`, which is now a host-id with no matching token rows) — so "revoke Claude" disconnects all its sessions, the honest semantic.
- **The roster is naturally one-row-per-provider** — no display grouping, no stale tail. The members endpoint humanizes the host-id directly (`claude.ai` → "Claude").

A migration collapses the live 7 `client_id`-keyed grants → 2 host-keyed grants (`claude.ai`, `chatgpt`), reversibly (the stale rows → `revoked` audit; the host rows created `granted_by='system:adr373-d2a-rekey'`). The owner grants (keyed on `user_id`, a stable human identity — not a churning registration) are **untouched**: D2.a is scoped to the foreign-LLM/platform/a2a classes whose identity was a session artifact.

"Grant" is deliberate, not incidental, vocabulary: ADR-366 already split `governance/` into **GRANT** (`_autonomy` + `_budget`, *how far a principal's decisions bind*) vs contract. The write-region grant is the same concept one level out: *what substrate a principal may author*. One vocabulary, two altitudes — Singular Implementation, not a second authorization language.

### D3 — `CALLER_WRITE_POLICY` is REINTERPRETED as the per-class default grant — not deleted

The live topology table ([`workspace_paths.py:241`](../../api/services/workspace_paths.py#L241)) is not removed. It becomes the **default grant a principal inherits from its role-class when it has no explicit narrowing grant**:

| Role-class | Default grant (= today's `CALLER_WRITE_POLICY`, reinterpreted) |
|---|---|
| `owner` | all roots except `system/` (today's `operator`) |
| `member` | `operation/` + `agents/`; locked from `governance/ contract/ constitution/ persona/ system/` (today's `agent` shape, applied to a human collaborator) |
| `own-agent` | per-grant within the `member` ceiling (domain-scoped, dispatcher-enforced as today) |
| `foreign-llm` (`mcp`) | `operation/` commons only (today's `mcp`) — the `operation/memory/` inbox in practice |
| `platform` | `operation/` source-intake region only |
| `a2a` | `operation/` commons (same lowest-trust floor as `foreign-llm`) |
| `system` | named-path discipline (unchanged) |

> **Amended by [ADR-376](ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) (ledger-intake, 2026-06-26):** the *raw-intake* regions for the non-human classes are evolved from the `operation/memory/` inbox *in practice* to per-transport raw-lane sublanes — `foreign-llm` → `inbound/mcp/{client}/`, `platform` → `inbound/{platform}/`, `a2a` → `inbound/a2a/{id}/` — each single-writer at the sublane (sharper than the shared `operation/` inbox, so D5's single-writer reasoning is *strengthened*, not weakened). The classes retain their `operation/` commons grant for any *derived* writes; the steward's placement (D5) becomes a derive-and-cite into `operation/` carrying `derived_from`. This is additive to the per-class default-grant model — no change to D3's reinterpretation, D5's conflict-closed-by-construction argument (which this makes literally true: raw and derived become distinct objects), or the re-key.

This is why the grant model is **additive and backward-compatible by construction**: a principal with no explicit grant inherits its class default — *today's exact behavior*. An explicit grant *narrows within* (a member scoped to one domain) or, for the owner, *is* the ceiling. The N=1 owner inherits the `operator`/`owner` default and **nothing changes for existing workspaces**.

The insertion point is one function: [`_caller_class(auth)` at workspace.py:1753](../../api/services/primitives/workspace.py#L1753) today collapses a per-principal `caller_identity` to a class key and `_is_path_locked` reads `CALLER_WRITE_POLICY[class]`. Post-ADR it resolves the principal's grant (`principal_grants(principal_id, workspace_id) → scopes`), falling back to the class default. **The single-writer-per-path topology (ADR-286/320) is unchanged** — it is the substrate the grant sits on: the grant decides *which principal owns which region*; single-writer guarantees *one owner per path*; they compose, neither is rebuilt.

### D4 — The role taxonomy ships at its SIMPLEST-VIABLE shape; richer grants are additive post-launch

The discourse base named the role/grant taxonomy as the one genuinely-open decision (seam #1). Resolved here at the floor, with the richer model explicitly additive:

**Ships at launch (the floor):**
- **`owner`** — the workspace creator; class-default = all-but-`system/`. Today's solo user *is* an owner of a singleton workspace.
- **`foreign-llm` / `a2a` / `platform`** — the non-human principal classes that *already exist in code*; class-default = `operation/` commons. These need the re-key but no new UX (they authenticate via OAuth/`client_credentials`, ADR-371).
- **`member`** (human) and **`own-agent`** — the role *slots exist* in the schema from day one (so the model is genuinely multi-principal, not owner-only), with class-defaults defined, but the **invitation/provisioning UX is post-launch**. A workspace can *hold* members; the surface to *add* one ships when multi-human demand is demonstrated.

**Additive post-launch (not foreclosed, deliberately unscoped):** per-path member scopes (a member restricted to one domain), granular agent grants (an own-agent scoped to `operation/specs/` only), role richness beyond the six classes. These are **new grant rows, not a restructure** — the `principal_grants` shape carries them without schema change. This is the "prep but don't scope the diff" posture (discourse base, KVK): the *key* and the *grant table* are foundational and ship now; the *grant UX/role richness* is deferred without foreclosure.

### D5 — Single-writer-per-path closes the multi-principal conflict question by construction

The deepest-seeming risk of a multi-party substrate — "two principals write conflicting content, what resolves it?" — is **closed by the discipline already shipped** (ADR-286, verified in discourse base §6.3 / §7.3):

- **Mechanical conflict cannot occur.** Different principals write different paths (`remember` writes `operation/memory/{slug}.md` per-principal; agents write their own domains). **No two principals ever co-write one file.** There is no merge, no CRDT, no operational-transform layer — and there must never be one. This is the single largest build the model *avoids*: Notion needs OT because it allows same-block co-editing; YARNNN does not allow same-path co-writing, so it skips the entire merge layer. This exclusion is as firm as ADR-209 §7's no-branches stance, one level up.
- **Semantic conflict across paths is JUDGMENT, not a data-layer problem.** If principal A's path asserts X about Acme and principal B's asserts not-X, **both writes succeed, both are attributed, both appear in `trace`** — and the steward (ADR-368 D5) reconciles them against ground-truth into its own `reviewer:` revision. The disagreement is the signal the fiduciary exists to resolve (a bank reconciles two conflicting deposit slips; it does not crash). Contributor identity survives the reconciliation as `trace`-visible evidence. **The conflict question is the moat doing its named work, not a hole in it.**
- **The steward was already designed workspace-level.** The placement adapter's own comment ([mcp_composition.py:594](../../api/services/mcp_composition.py#L594)) states it: *"the Reviewer is a WORKSPACE-level seat (one per workspace), not per-user … the wake must fire for the WORKSPACE that owns this substrate, independent of which member's LLM wrote it."* The multi-principal arbiter role is latent in the design, not invented here. The re-key's wake-scoping (`wake_scope = user_id → resolved workspace_id`) is the one-line change that comment already wrote.

### D6 — Identity resolution gains a workspace+grant lookup; the auth MECHANISM (ADR-371) is untouched

`resolve_request_client` ([`api/mcp_server/auth.py`](../../api/mcp_server/auth.py)) today returns a `user_id`. Post-ADR it resolves `principal → (workspace_id, role, grant)`. Both auth paths gain the lookup: the OAuth path (claude.ai/ChatGPT/human-login) and the static-bearer path (`MCP_USER_ID`, Claude Desktop). **What a principal does to authenticate is unchanged** — ADR-371's self-contained boundary, in-popup login, and `client_credentials` for A2A all survive. The `a2a:` prefix (spec'd in ADR-371 D3, confirmed *absent* from `VALID_AUTHOR_PREFIXES` today — genuinely build-deferred, not half-shipped) is added when the first A2A caller is real; the re-key is its prerequisite, not its trigger.

## 4. Implementation scope (four pre-cut seams)

The discourse base audit (§6) found the architecture cut this seam across three prior ADRs (209 single write path, 288 caller-identity, 320 topology) before it was needed. The re-key is **foundational but bounded** — concentrated, not sprawling:

| Layer | Change | Size | Pre-cut by |
|---|---|---|---|
| **Substrate keying** | `+workspaces` table; `workspace_id` FK on `workspace_file_versions` + `workspace_files` + `head_version_id` reads; `user_id`→membership; **118 query sites / 49 files** re-pointed (Phase-1 scoping pass corrected the earlier "~16/2" undercount); RLS `user_id = auth.uid()` → membership check | **Foundational; multi-day sweep, but chokepointed** — `user_id` rides one dataclass (`AuthenticatedClient`, [supabase.py:44](../../api/services/supabase.py#L44)) so `workspace_id` is derived once + threaded; the user-JWT read majority re-keys at the RLS layer (zero route-line changes), leaving the explicit-scope service-key callers as the real sweep | ADR-209 single write path + `AuthenticatedClient` chokepoint |
| **Gate / grant** | `_caller_class` consults `principal_grants` (class-default fallback); `CALLER_WRITE_POLICY` reinterpreted as class-defaults (no table edit, only how it's consulted); `+principal_grants` table + CRUD | **One function + one table** | ADR-288 caller-identity, ADR-320 topology |
| **MCP→wake** | `wake_scope = auth.user_id` → resolved `workspace_id` | **One line** (the code's own TODO at mcp_composition.py:594) | ADR-368 D5 isolation |
| **Auth resolution** | `resolve_request_client` returns `(workspace_id, grant)`; `+a2a:` prefix when A2A is real | **Resolution-only; mechanism survives** | ADR-371 D1/D4 |
| **Merge / CRDT / branching** | **none** — excluded by construction (D5) | **Zero** | ADR-286 single-writer, ADR-209 §7 |

### Phasing

1. **Phase 1 — the schema re-key (the foundational spine).** `workspaces` table; `workspace_id` FK + backfill (every `user_id` → singleton workspace, owner-grant seeded); grow `AuthenticatedClient` with `workspace_id` (derived once); thread `workspace_id` through `write_revision` + its 4 helpers (the spine); re-key RLS to membership; then the explicit-scope sweep across the service-key callers (the bulk of the 118 sites — the user-JWT reads come for free via RLS). Ships the N=1 world byte-identical (the regression gate proves it before the sweep). **This is the pre-launch blocker.** Migration `189_adr373_multi_principal_rekey.sql`. Build order: migration + `AuthenticatedClient` + `write_revision` spine → prove byte-identical N=1 → then the service-file sweep.
2. **Phase 2 — `principal_grants` + the gate consult. ✅ IMPLEMENTED 2026-06-29.** The grant table (Phase 1); the gate consult landed: `services/supabase.py::resolve_principal_id(auth)` (the uniform principal-id abstraction — owner→`user_id`, foreign-llm→OAuth `client_id`, agent→slug, system→actor) + `services/primitives/workspace.py::_is_path_locked_for_principal(auth, path)` (the grant-aware wrapper: explicit `scopes` → allow-list narrowing; no grant / NULL scopes → fall through to the class-default `_is_path_locked` = today's behavior). Both gate call sites (the MCP branch + the Reviewer branch in `permission.py`) route through it. `AuthenticatedClient` grew `principal_id` (the 3rd field, after `caller_identity` + `workspace_id`); the JWT path stamps `user_id`, the MCP path stamps `client_id`. Owner + foreign-llm/a2a/platform class-defaults live. Regression: `api/test_adr373_grant_consult.py` (20/20) — fallback-identity (byte-identical), grant-honored (allow-list), per-request memoization, MCP-fix. Member/own-agent slots present, **provisioning UX deferred to a separate Workspace Members ADR** (operator decision, 2026-06-29 — the FE this session is read-only legibility only). The polarity subtlety (CALLER_WRITE_POLICY = LOCKED prefixes vs grant `scopes` = ALLOWED regions, complements) is handled in `_is_path_locked_for_principal`.
3. **Phase 3 — MCP→wake + auth resolution re-key.** The one-line `wake_scope`; `resolve_request_client` workspace+grant resolution. Re-points ADR-371's 1:1 assumption.
4. **Post-launch (additive) — member/agent grant UX + role richness.** New grant rows, no schema change (D4).

## 5. What this does NOT do

- **Does not build merge / CRDT / operational-transform / real-time co-edit.** Excluded by single-writer-per-path (D5). The largest avoided build; must never be silently re-added.
- **Does not build branching / fork / PR-review.** Excluded by ADR-209 §7, unchanged.
- **Does not ship a rich role taxonomy or member-invite UX at launch.** Simplest-viable floor (D4); richer grants are additive.
- **Does not change the auth mechanism, the single write path, the topology lock, the gate location, the wake machinery, or the steward's judgment loop.** It re-keys their binding unit and adds a grant consult; it rebuilds none of them.
- **Does not change `workspace_blobs`.** Content-addressing is global by sha256; identical content across workspaces still reuses one blob. Scoping lives at the revision/file layer, which is what re-keys.

## 6. Doc cascade (same commit or fast-follow)

- **New:** this ADR.
- **Amend banner — ADR-371:** the 1:1 identity assumption is superseded by ADR-373 D1/D6; the auth mechanism is preserved.
- **Amend banner — ADR-310:** D5's shared-workspace deferral is resolved by ADR-373.
- **Amend note — ADR-320/366:** `CALLER_WRITE_POLICY` is reinterpreted as the per-class default grant (no table change; ADR-373 D3).
- **Amend note — ADR-368:** the placement seat is confirmed workspace-level; the wake-scope re-key is named (ADR-373 D5).
- **CLAUDE.md** — the schema section (`workspace_files`/`workspace_file_versions` re-keyed; `+workspaces`, `+principal_grants`); the surface-model note that the workspace is multi-principal.
- **`docs/architecture/authored-substrate.md`** — the binding unit updates from `(user_id, path)` to `(workspace_id, path)`; the per-principal-diff framing (the revision chain *is* the diff); the no-merge exclusion restated for the multi-principal case.
- **GLOSSARY** — "Principal" entry; "Grant (write-region)" entry; "Workspace" updated from user-synonym to multi-principal binding unit.
- **Gate:** `api/test_adr373_rekey.py` — backfill reproduces N=1 behavior; class-default fallback equals today's `CALLER_WRITE_POLICY`; single-writer-per-path holds for placed files; no merge path introduced.

## 7. Rejected alternatives

- **Personal substrate, re-key deferred** (the two prior deferrals, ADR-310 D5 / ADR-371 D4 as-was). Rejected: the wedge is multi-principal (discourse base D2); deferring the key means launching the wrong product and paying a far costlier live-data migration later.
- **Coarse trust-class table instead of per-principal grant.** Rejected (discourse base D4): introduces a second authorization vocabulary parallel to ADR-366's "grant," and leaves authorization coarser than attribution — the asymmetry the per-principal grant exists to close.
- **Re-key the schema but keep authorization owner-only.** Rejected: an owner-only multi-tenant substrate is not multi-*principal* — it forecloses the member/agent/platform futures the wedge depends on. The role slots ship in the schema (D4) even though their UX is deferred.
- **Build the collaboration layer (merge/CRDT/presence) now.** Rejected: single-writer-per-path makes it unnecessary (D5); it is the biggest avoided cost, not a deferred feature.
- **Rich role taxonomy + member-invite UX at launch.** Deferred, not rejected (D4): additive grant rows, demand-gated; shipping it now is building ahead of the multi-human signal.
