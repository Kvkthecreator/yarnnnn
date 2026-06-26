# ADR-373 — The Multi-Principal Workspace and the `user_id → workspace_id` Re-Key

> **Status**: **Accepted** (2026-06-26). Foundational, pre-launch. Phased implementation; the schema re-key is Phase 1.
> **Date**: 2026-06-26
> **Authors**: KVK (operator) + Claude (collaborator)
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
| **Substrate keying** | `+workspaces` table; `workspace_id` FK on `workspace_file_versions` + `workspace_files` + `head_version_id` reads; `user_id`→membership; ~16 scoping sites re-pointed; RLS `user_id = auth.uid()` → membership check | **Foundational, bounded** (one write path, small read set) | ADR-209 single write path |
| **Gate / grant** | `_caller_class` consults `principal_grants` (class-default fallback); `CALLER_WRITE_POLICY` reinterpreted as class-defaults (no table edit, only how it's consulted); `+principal_grants` table + CRUD | **One function + one table** | ADR-288 caller-identity, ADR-320 topology |
| **MCP→wake** | `wake_scope = auth.user_id` → resolved `workspace_id` | **One line** (the code's own TODO at mcp_composition.py:594) | ADR-368 D5 isolation |
| **Auth resolution** | `resolve_request_client` returns `(workspace_id, grant)`; `+a2a:` prefix when A2A is real | **Resolution-only; mechanism survives** | ADR-371 D1/D4 |
| **Merge / CRDT / branching** | **none** — excluded by construction (D5) | **Zero** | ADR-286 single-writer, ADR-209 §7 |

### Phasing

1. **Phase 1 — the schema re-key (the foundational spine).** `workspaces` table; `workspace_id` FK + backfill (every `user_id` → singleton workspace, owner-grant seeded); re-point the ~16 substrate scoping sites; RLS via membership. Ships the N=1 world byte-identical. **This is the pre-launch blocker.** Migration `189_adr373_multi_principal_rekey.sql`.
2. **Phase 2 — `principal_grants` + the gate consult.** The grant table; `_caller_class` → grant lookup with class-default fallback; owner + foreign-llm/a2a/platform class-defaults live. Member/own-agent slots present, provisioning UX deferred (D4).
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
