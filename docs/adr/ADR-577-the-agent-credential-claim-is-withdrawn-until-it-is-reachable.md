# ADR-577 — The Agent-Credential Claim Is Withdrawn Until It Is Reachable

**Status**: Proposed (2026-08-18)
**Date**: 2026-08-18
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Identity (Axiom 2 — whose credential an act runs through) + Substrate (Axiom 1 — one fact, one column) + Channel (Axiom 6 — what a settings pane asserts)
**Relates to**: ADR-425 (the credential is an account object; D3 reserved the agent case), ADR-566 (the workspace allocates the agent's credential — the claim this ADR measures), ADR-431 (the connecting member owns the grant; `connected_by`), ADR-407 D5 + migration 201 (the additive `workspace_id` re-key and its owner-fill trigger), ADR-405 (reach is a grant, authority is a dial), ADR-576 (the same defect class, one day earlier), ADR-494 (registry drift)
**Amends**: **ADR-566 D2/D3/D5** — the two-store split is retained as the *decided direction* and withdrawn as a *shipped property*. **ADR-425 AD1** — the double meaning of `workspace_id` is resolved to *routing*.

---

## 1. Context — a guarantee that no execution path establishes

ADR-566 states the rule plainly, and `services/platform_credentials.py:22-29` repeats it in a boxed warning:

> ⚠️ NO CROSS-STORE FALLBACK, EVER ⚠️
> An agent whose workspace credential is missing gets NOTHING — it does not
> silently fall through to the owner's personal token.

**Production does exactly what that warning forbids.** Four independent findings, each with a receipt, and each sufficient on its own.

### 1a. The agent branch is unreachable — driven, not read

`is_agent_principal` (`platform_credentials.py:93-96`) reads `getattr(auth, "workspace_id", None)` and returns `False` when absent, *before* the grant lookup. `HeadlessAuth.__init__` (`registry.py:985-1009`) never sets `workspace_id`. Driven against the real objects:

```
caller_identity  : specialist:researcher
has workspace_id : False
is_agent_principal: False
```

Every agent execution therefore takes the `else` branch and reads `("user_id", auth.user_id)` — and that `user_id` is the **workspace owner's**, because the Freddie/wake stack is keyed by owner (`workspace_context.py:156`). The retired ADR-425 D3 "reuse the owner's credential" branch is what runs, reached through an error path nobody chose.

### 1b. There are no `own-agent` grants — so wiring 1a alone would change nothing

```
principal_grants by role:  owner 11 active · foreign-llm 4 active/8 revoked
                           member 1 active/3 revoked · viewer 1 revoked
own-agent: ZERO ROWS, any status, any workspace (15 workspaces)
```

`_WORKSPACE_CREDENTIAL_ROLES = {"own-agent"}` can never match. The classification would still return `False` with `workspace_id` threaded through. **Two independent breaks, not one** — which is why "just wire `HeadlessAuth`" is not the fix.

### 1c. A live trigger merges the two "disjoint" stores

```
trg_fill_workspace_id  BEFORE INSERT ON platform_connections
  → workspace_id := (SELECT id FROM workspaces WHERE owner_id = NEW.user_id)
```

The OAuth insert (`integrations.py:1697`) never sets `workspace_id`; the trigger stamps it. So **the owner's personal connection sits in both stores simultaneously** — one row satisfying both `("user_id", owner)` and `("workspace_id", ws)`. ADR-566 §3 D2's "permanently disjoint" is false at the data layer, and the boxed warning is defeated *below* the code that states it.

ADR-566 asserted "**No migration is required** — the column exists (migration 201, additive)". Migration 201 also installed this trigger, left `UNIQUE(user_id, platform)` un-widened, and left RLS at `user_id = auth.uid()`. All three were inherited unexamined.

### 1d. The claim is user-visible, and it is false

`WorkspaceCredentialsCard` is mounted at `workspace-settings/page.tsx:245` and renders `GET /integrations/workspace-credentials`, which filters `("workspace_id", ws)`. Because of 1c, production returns:

| platform | is the owner's personal token |
|---|---|
| slack | **yes** |
| notion | **yes** |
| github | **yes** |

The pane's own header says *"a member's own Slack is theirs, keyed `user_id`, and no agent reaches it"* — while listing exactly those rows as **"what this workspace's AGENTS act through."** An operator reading it is told their personal tokens are workspace agent credentials. That is the most consequential form of the defect: not a dormant capability, but **a surface asserting a security property that inverts the truth.**

### 1e. A second credential read sits outside the chokepoint

`capability_available` (`orchestration.py:1561`) decides which tools an agent is *offered* via a raw `.eq("user_id", user_id)` read. The ADR-566 gate cannot see it: the gate matches reads containing `credentials_encrypted`, and this one selects `attestation_grade`. The chokepoint is not a chokepoint.

### 1f. `workspace_id` carries two incompatible meanings

- **ADR-425 AD1**: `workspace_id` = **routing** — "which workspace this credential is routed to feed. NOT ownership."
- **ADR-566 D3**: `workspace_id` = **ownership** — the workspace's own allocated credential.

The trigger writes the routing meaning; `workspace_credential_filter` reads the ownership meaning. This is precisely the "two facts crammed into one row" failure ADR-425 §1 diagnosed and ADR-566 promised not to re-create.

### 1g. The allocation door was never built

`/integrations/workspace-credentials` is **GET only** — no POST, no DELETE. No workspace credential can be created through the product. The store is unfillable except by the trigger, which fills it with the wrong thing.

---

## 2. The decision principle

ADR-566's *direction* is right and is not being reversed: a human's personal token must never silently become an agent's. What is wrong is that the system **claims to have achieved it**. A claim that no execution path establishes is worse than an acknowledged gap, because it terminates inquiry — this ADR exists only because an unrelated GitHub audit happened to trace the call.

Two options were weighed.

**Option A — build the missing half now**: thread `workspace_id` through `HeadlessAuth`, mint `own-agent` grants, drop the trigger, add workspace-aware RLS, build the allocation door. **Rejected as this ADR's scope.** It is five coupled changes to *who may act through whose token*, on a store with **zero rows and zero demand** — no agent has ever needed platform reach (ADR-425 D3: the agent store "lands on first platform-reach demand"; that demand has not arrived, and ADR-576 established there is currently no surface through which an agent can reach a connector at all). Building authority machinery ahead of demand is how the unreachable branch got written in the first place.

**Option B — withdraw the claim, keep the direction** (adopted). Delete what asserts a false property; keep and sharpen the canon that says what must be true when the demand arrives; make the gap **loud** rather than silent.

The rule this encodes, stated generally: **a security property must be established by an execution path, not by prose or by a gate that cannot see the violation.** Where it isn't, the honest move is withdrawal, not documentation.

---

## 3. D1 — The unreachable agent branch is deleted, not repaired

`is_agent_principal`, `_WORKSPACE_CREDENTIAL_ROLES`, and `workspace_credential_filter` are **deleted**. `resolve_platform_credential` keeps exactly one behavior — the account store, keyed `user_id` — and says so.

**Why deletion over repair.** The branch is dead in two independent ways (1a, 1b), guards a store that is empty and unfillable (1g), and cannot be reached by any surface that exists (ADR-576: no chat lane, app lane, steward, or MCP path reaches a connector). Repairing it would ship reach-machinery for a demand that has not arrived, and leave a second store live behind a trigger that mis-fills it. Per Singular Implementation: **one credential path, or an explicit refusal — never a dormant second path that looks live.**

The module survives as the chokepoint. Its value was never the two-store branch; it was collapsing eight inline `.eq("user_id", …)` lookups into one seam. That value is kept.

### D1.a — The refusal is explicit and loud

Deleting the branch must not read as "agents may use the human store." `resolve_platform_credential` gains an affirmative refusal: an agent-shaped caller (`HeadlessAuth`, `caller_identity` starting `specialist:`/`agent:`) is **refused a credential and logged at WARNING**, rather than silently resolving the owner's.

This is the behavior ADR-566 D2 always specified. It is now *reached*, because it keys on what the auth object actually carries instead of on a grant role that no row holds. **The guarantee becomes true by making the denial reachable, not by making the second store work.**

Consequence, stated rather than discovered later: `harvest.py` — the one live LLM+platform path (`routes/harvest.py`, no FE caller since ADR-437) — stops resolving the owner's token when invoked headlessly. That is the correct outcome, and it is why this is a decision rather than a cleanup.

---

## 4. D2 — `workspace_id` means routing, and the trigger that writes it stays

The double meaning (1f) resolves to **ADR-425 AD1: routing**. `workspace_id` records which workspace a credential feeds. It is not an ownership claim and never grants an agent anything.

`trg_fill_workspace_id` is therefore **correct and is retained** — it fills the routing fact, which is exactly what it was written to do in migration 201. It only looked like a defect while a second reader interpreted the column as ownership. With that reader deleted (D1), the ambiguity is gone.

**No migration is required, and this time that claim is verified rather than asserted**: the trigger is unchanged, RLS is unchanged, `UNIQUE(user_id, platform)` is unchanged, and no column is added or dropped. What changes is that exactly one meaning now reads the column.

---

## 5. D3 — The workspace-credentials pane and route are deleted

`WorkspaceCredentialsCard`, its mount, its client method, the `GET /integrations/workspace-credentials` route, and its response model are **deleted**.

The pane renders a store that (a) cannot be filled through the product, (b) is filled by the trigger with the owner's personal connections, and (c) is described to the operator as something it is not (1d). Every one of those is disqualifying on its own.

**Rejected: fixing the copy.** Honest copy over an unfillable store would be a pane that always renders empty — which reads as "nothing allocated" and re-asserts, more quietly, that allocation is a thing this product does. **Rejected: filtering out owner-owned rows.** That is a symptom fix over the ambiguity D2 resolves, and it would leave a permanently empty pane.

ADR-566 D5's *intent* — that a workspace's agent credentials be legible when they exist — is preserved in canon (§7) and re-enters with the allocation door, not before it.

---

## 6. D4 — The chokepoint gate is widened to what it claims to guard

The ADR-566 gate matched only reads containing `credentials_encrypted`, so `capability_available`'s `attestation_grade` read (1e) was invisible. The gate now flags **any `platform_connections` read outside the chokepoint that carries an `auth`/`user_id`**, with an explicit allowlist for the legitimate non-credential readers (the settings routes that manage a member's own connections).

`capability_available` keeps reading `user_id` — that is correct for a human's capability probe — but is now *seen* by the gate, so a future agent path cannot slip through the same blind spot.

---

## 7. What this ADR does not do, and what must be true when it is undone

> Carried forward in
> [`connector-reach-and-the-commons.md`](../architecture/connector-reach-and-the-commons.md),
> including the DELETED-BUT-NAMED seams (§5 there) so they are not rediscovered
> as gaps.

Not decided here, and deliberately left for first real demand:

- **The agent credential store.** ADR-425 D3's reservation stands. When an agent genuinely needs platform reach, it returns as a *whole*: allocation door (POST/DELETE), workspace-aware RLS, `UNIQUE(workspace_id, platform)`, a `workspace_id`-bearing auth object, real `own-agent` grants, and the D5 pane. **Partial delivery is what this ADR is cleaning up; it must not recur.**
- **`platform_connections.connected_by`** — named by ADR-407 D5, deferred by ADR-425 AD5, extended to grants by ADR-431, never built on this table. Harmless while every connection is the owner's; required the moment a non-owner member connects, or ADR-401 D3 teardown cannot identify what to revoke.
- **Connector data reaching the commons** (derive) — ADR-576 §5. Untouched.

**The re-entry test**, written now so it cannot be waived later: before any future ADR may claim an agent acts through a workspace credential, it must exhibit **a driven trace** — a real auth object, through the real resolver, returning the workspace row — not a passing gate and not a docstring. That is the evidence standard this ADR's absence created.

---

## 8. Gate

`api/test_adr577_credential_claim.py` asserts:

1. `resolve_platform_credential` resolves the account store for a human auth.
2. An agent-shaped auth is **REFUSED** — driven through the real resolver, not inspected.
3. The deleted symbols (`is_agent_principal`, `workspace_credential_filter`, `_WORKSPACE_CREDENTIAL_ROLES`) are absent.
4. No route serves `/integrations/workspace-credentials`.
5. `WorkspaceCredentialsCard` and its client method are absent from the FE.
6. D4 — every `platform_connections` read outside the chokepoint is on the allowlist.

Each is falsified against a real call before landing.
