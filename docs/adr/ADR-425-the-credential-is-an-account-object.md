# ADR-425: The Credential Is an Account Object — Perception Is a Principal's, Not the Commons'

**Status**: Implemented (2026-07-09) — D1 (Connectors → account door) + D2 (Sources hidden) + the backend re-scope are live on `main`. Commits: `de93ea4` (backend — `scope_manifest` `platform_connections`→account, new `account_scope_filter`, 21 read reversals in `integrations.py`; DP35 3/3, ADR-407 phase1 5/5 green) + `e1f7192` (FE — registry `pane_of` flip, Connectors pane in the account door, Perception group removed, Sources hidden, redirect stubs + UserMenu re-pointed; `tsc --noEmit` clean). **No migration** (mig 201 was additive; RLS/index/writes were always `user_id`). **D3 (agent-owned credential policy for Freddie / hired agents) is RESERVED, not built** — it lands on first platform-reach demand. An Identity + Substrate + Channel ADR that **inverts the scope of a platform connection**: a human's connector (Slack, Drive, Notion, GitHub) is **their account object**, housed in User Settings — not a workspace peripheral. It retires the ADR-407 D5 "connection is workspace content" framing for the human case, moves the Connectors pane out of Workspace Settings to the account door, and **hides Sources from the operator surface entirely**. The one place a workspace-scoped credential legitimately arises — a **non-human principal (Freddie / a hired agent) acting through a platform** — gets an explicit *credential-use policy* (reuse the owner's, or hold its own), the account-choice ChatGPT surfaces on the agent, not the workspace.

**Date**: 2026-07-09
**Dimension**: Identity (Axiom 2 — whose credential a connection is) + Substrate (Axiom 1 — what scope `platform_connections` declares) + Channel (Axiom 6 — which settings door the affordance lives behind)

**Supersedes**:
- **ADR-407 D5** ("Connections are workspace peripherals; credentials stay personal") — the *split* is kept but its polarity inverts: the **credential is the primary object and it is account-scoped**; the workspace-peripheral fact survives only for the agent-owned case (D3 here), not for a human's connector.
- **ADR-415 D2** (Connectors + Sources restored to Workspace Settings → Perception) — the *un-hiding* rationale (don't gate a management surface behind a dormancy flag) is preserved; the *placement* (Workspace Settings) is reversed for Connectors and dissolved for Sources. ADR-415 ratified "don't hide the management pane"; it inherited "Workspace Settings" as the home unexamined from the ADR-341 → ADR-385 lineage. This ADR examines it.

**Amends**:
- `api/services/scope_manifest.yaml` — `platform_connections` re-scoped `content` → the credential fact becomes **account**; the peripheral-observability tail (`sync_registry`) stays `content` only for the agent-owned case (D3), otherwise account.
- **ADR-401** Amendment note (2026-07-04, "the principal-binding of connections") — its *deferral* resolves in this direction for humans: a connection is **authorized-by-principal AND owned-by-principal**; "feeds-the-workspace" survives only when the principal is an agent (D3).
- **ADR-373** (`platform_connections` re-key) — the `user_id → workspace_id` re-key on `platform_connections` is **reversed for the human case** at the *read-filter* layer (application code), where it actually lived. **No schema migration is required** (implementation finding, 2026-07-09): migration 201 only *added* a `workspace_id` column and backfilled it — it never moved the RLS policy (still `user_id = auth.uid()`), the primary index (`idx_platform_connections_user`), or the write path off `user_id`. The workspace-scoping only ever reached the `substrate_scope_filter` read preference in `integrations.py`. So the reversal is code + manifest, not DDL. The `workspace_id` column is **retained as-is** — vestigial for humans, reserved for the future D3 agent-owned connection (adding `connected_by`/`owner_kind` is deferred with D3, not built speculatively here per Singular Implementation).

**Preserves**:
- **ADR-420** D1/amendments (engine vs connector breadth) — this ADR is the *inbound-peripheral* counterpart of ADR-420's already-ratified *outbound* rule ("a lane's connector reach is under the member's grant"). Same principle — connector reach follows the principal, never the commons — applied to the in-side. They compose; nothing in ADR-420 is contradicted.
- **ADR-408** (three AI altitudes) — the credential-use policy attaches to the altitude: humans (their own), A1 Freddie (a policy), A2 persona agents (per-user for now).
- **ADR-307** (one gate, one queue) + **ADR-405** (the witness dial) — unchanged. Auth-mode, witness policy, and capability scope remain distinct axes; this ADR only relocates the *credential* axis. (It notes, non-normatively, that ChatGPT co-locates all three on the agent screen — a UI convergence worth revisiting when the agent-account surface is built, D3.)
- **ADR-320** permission topology — unchanged. This ADR changes *which door* a credential is managed behind and *what scope the store declares*; it does not touch the path-root gate.
- The **OAuth-credential account class** already in the manifest (`mcp_oauth_*`, labeled "OAuth credential") — `platform_connections`' credential joins that existing class; the account scope is not a new invention.

---

## 1. Context — the confusion, and why the current framing manufactures it

The operator, looking at the live Connectors pane under Workspace Settings, asked the question the current framing cannot answer cleanly:

> *"Does this mean connectors for every individual user within the workspace share the same permission and auth considerations? That seems confusing."*

It is confusing because the current canon (ADR-407 D5) says the **connection** is workspace content and only the **OAuth credential inside it** is account-scoped — two facts crammed into one row, with the second half (`connected_by`) **not yet implemented** (ADR-401 amendment, deferred). So the honest state of the system is: *we scoped the connection to the workspace, then had to bolt a `connected_by` patch onto it to recover the human — and never shipped the patch.* The strain is the evidence the polarity is backwards.

ChatGPT's business/enterprise agent setup names the real decision. On the **agent** screen (not a workspace-connectors screen) it asks: *"Which account should the agent use?"* — **End-user account** ("each user signs in with their own") vs **Agent-owned account** ("use one account for everyone who uses this agent"). The decisive detail: the question **only exists because an agent needs to act**. For a human using their own Drive, there is no account question — it is simply their account. ChatGPT did not build a "workspace connections" concept and then recover the human; it kept the human's credential with the human and raised the shared-vs-own question *only at the agent*.

That is the model this ADR adopts — with one deliberate divergence from ChatGPT (§4).

## 2. The inversion

**A credential is an account object.** Each human's platform connections live in **their User Settings** — their auth, their tokens, torn down with their account (the account door's danger zone already assumes exactly this: *"Disconnect N connected platforms · Delete OAuth tokens — you'll need to reconnect"*). There is **no shared "workspace connections" concept for humans.** Perception through a platform is a property of a **principal**, not the commons.

The workspace-scoping of `platform_connections` (ADR-407 D5, migration 201) is retired **for the human case**. It survives only to scope the *agent-owned* connection (§3).

This resolves the operator's confusion directly: **members never shared one auth — each human brings their own.** The only place a shared-vs-own question arises is at a *non-human* principal, and it is raised *there*, explicitly.

## 3. Decisions

### D1 — Connectors move to the account door (User Settings), per-human

The Connectors pane leaves Workspace Settings → Perception and lands in the account door (`settings` slug — the UserMenu-opened window that today holds only "Account"). A human manages *their own* connectors there: connect, see status/freshness, disconnect. `platform_connections`' credential fact re-scopes `content` → **account** in `scope_manifest.yaml`, joining the `mcp_oauth_*` "OAuth credential" class it already sits beside conceptually.

The workspace does not present "its connectors." It presents (unchanged) **who has a grant** (Workspace Members, ADR-373) and **what those principals have authored** (the commons). What each member perceives *through* is that member's account concern.

### D2 — Sources is hidden from the operator surface

Sources (`_sources.yaml` web/RSS watches) is **removed from the operator's view.** The operator ruling is explicit: *hide it altogether.* Implementation preference (operator-stated): if the cleanest hide is to leave the pane in Workspace Settings and gate it off, that is acceptable — the **intent is gone-from-view, not relocated.** The `SourcesCard` component, the `/api/sources` read, and the `_sources.yaml` substrate are **not deleted** (a program may still declare standing watches; ADR-335/336 perception-field canon is untouched at the substrate layer) — only the operator-facing pane is withdrawn. This is a `hide-not-delete` per the ADR-404 precedent, but permanent-by-default rather than dormancy-gated: no operator surface renders Sources until a future ADR gives standing watches a first-class home.

### D3 — The agent-owned credential: the one legitimate workspace-scoped connection

When a **non-human principal must act through a platform** — **A1 Freddie** or an **A2 hired agent** — it acquires a **credential-use policy**, chosen once per connection, à la ChatGPT's agent-account panel but **scoped to the agent, not the workspace**:

- **Reuse the owner's credential** (default) — the agent perceives/acts through the workspace owner's existing account connection. No new OAuth grant; the owner's token is reused. This is the N=1-friendly default: the solo operator's Freddie simply uses the operator's connectors.
- **Own service account** — the agent holds its own credential (a workspace-service account). This is the only connection legitimately keyed by `workspace_id` — it belongs to the workspace's agent, not to any human. The surviving `platform_connections.workspace_id` column scopes exactly this case.

**A2 chat LLM models stay per-user** (operator-stated: *"here I guess we're still using per-user, which is fine"*) — consistent with the human rule (each principal brings their own), so no agent-account question arises for them yet.

The credential-use policy surface is a **follow-on** — it lands when Freddie or a hired agent first needs platform reach (ADR-380 Rung-2 territory for A2; Freddie's is A1 and can come sooner if a mandate demands platform perception). This ADR **reserves the model and the default**; it does not build the picker.

### D4 — Auth mode, witness policy, and capability scope stay separate axes

ChatGPT co-locates three things on its agent panel: the account choice (D3), a "Write action safety: Always ask" dial, and per-action write toggles. In YARNNN these are already three ratified axes — the credential (this ADR), the **witness dial** (ADR-405), and the **permission gate / capability scope** (ADR-307). This ADR relocates only the credential axis. It does **not** merge them. When the D3 agent-account surface is built, whether to *present* them together (ChatGPT's convergence) is a UI question for that ADR — the underlying axes remain distinct so that a change to one never silently moves another.

## 4. The deliberate divergence from ChatGPT — and its expiry

ChatGPT makes "End-user vs Agent-owned" a per-connection toggle on **every** agent. YARNNN does **not** offer humans an "agent-owned" mode for their *own* perception — a human's connector is unconditionally theirs (D1). The agent-account choice exists **only for a non-human principal** (D3). The reason: in YARNNN the human is a first-class principal in the commons, not a "user of an agent." ChatGPT's frame is agent-centric (the agent is the product; the human is its user); YARNNN's is commons-centric (the human and the agents are co-principals over one substrate). So the account question belongs *only* where a non-human needs to borrow or hold a credential — never as a mode imposed on a human's own auth.

**This is the current state, and it is provisional — it holds for the launch era (Altitudes 1–2).** The human/agent asymmetry (humans own their credential outright; only non-human principals face the account choice) rests on the human being categorically *more* first-class than the agents. That asymmetry is expected to **soften or dissolve at Altitude 3** — true on-par agents that are principals in the commons at parity with human users (ADR-408 A3, ADR-380 Rung-2+). When an agent is a peer rather than a hired non-human, the clean "the account question exists only for a non-human" line blurs, and a per-principal credential-mode choice (closer to ChatGPT's symmetric toggle) may become correct. **Do not treat §4 as a permanent principle.** It is the right stance *now*; revisit it when Altitude-3 parity is designed.

## 5. Blast radius (for the build ADR/commit — none rides this doc)

Doc-first; no code lands with this ADR. When built:

| Target | Change | Decision |
|---|---|---|
| `web/app/(authenticated)/workspace-settings/page.tsx` | Remove the Perception group (Connectors + Sources) | D1, D2 |
| `web/app/(authenticated)/settings/page.tsx` (account door) | Add a Connectors pane (per-human); reuse `ConnectedIntegrationsSection` | D1 |
| `web/app/(authenticated)/connectors/page.tsx` (redirect stub) | Re-point `→ /settings?settings.pane=connectors` (was workspace-settings) | D1 |
| `web/app/(authenticated)/sources/page.tsx` (redirect stub) | Retire or point at a no-op; Sources has no operator door | D2 |
| `api/services/scope_manifest.yaml` | `platform_connections` credential → `account`; keep `sync_registry` peripheral rows for the D3 agent-owned case | D1, D3 |
| `api/routes/integrations.py` | The disconnect DELETE + reads key on the **human** (`user_id`) again for human connectors — stop routing them through `substrate_scope_filter`'s workspace preference; the D3 agent-owned path (future) keys on `workspace_id` | D1, D3 |
| **No migration** | The reversal is code + manifest only — RLS/index/write-path were never re-keyed off `user_id` (mig 201 was additive); `workspace_id` column retained as-is for future D3 | D1 |
| Freddie / agent envelope | The credential-use policy (reuse-owner default) — reserved, built on demand | D3 |
| `docs/adr/ADR-407` D5 + registry row · `ADR-415` D2 · `ADR-401` amendment | Status banners: superseded/amended by ADR-425 | header |
| `FOUNDATIONS.md` DP35 / GLOSSARY "Three Scopes" | The connection example flips: connection credential is the account example, not the content-peripheral example | doc cascade |

## 6. Open questions

- **OQ1 — The agent-account picker surface (D3).** Where does Freddie's credential-use policy render — the System Agent panes (ADR-418), the agent detail (ADR-419 AgentConstitutionBlock), or a new connection sub-surface? Deferred to the build ADR; gated on first platform-reach demand.
- **OQ2 — Owner-credential reuse mechanics (D3 default).** "Reuse the owner's credential" means Freddie acts through the owner's `platform_connections` row. Does that need an explicit grant fact (an ADR-373 scope on the platform), or is owner-reuse implicit in Freddie being the workspace's A1 steward? Likely the latter (Freddie is not a foreign principal), but state it when built.
- **OQ3 — Sources' eventual home (D2).** Hidden now. If standing web/RSS watches earn a first-class operator surface later (a genuine "the operation watches the world" act, distinct from a human's OAuth connector), it returns as its own thing — not re-merged with Connectors under a cosmetic "Perception" grouping.
- **OQ4 — Multi-workspace connector reuse.** A human in two workspaces has *one* account, so one set of connectors. Does their Slack automatically feed both workspaces, or is per-workspace opt-in required? The account-scoping (D1) implies the credential is shared across the human's workspaces, but *which workspace a capture feeds* is a separate routing decision. Surface when multi-workspace + capture both ship.

---

## Appendix — why this is finishing an unfinished decision, not overturning a fresh one

ADR-407 D5 shipped the workspace-peripheral framing but immediately needed `connected_by` (deferred, ADR-401 amendment) to recover the human — a patch that never landed. ADR-415 D2 "restored" Connectors to Workspace Settings, but its ratified thesis was *"don't hide a management pane behind a dormancy flag"*; the Workspace-Settings home rode in from the ADR-341 → ADR-385 lineage without re-examination (ADR-415 §2 is a surface-confusion argument, not a scope argument). And ADR-420 — the most recent adjacent ruling — **already** established for the *outbound* case that "a lane's connector reach is under the member's grant," i.e. connector reach follows the principal, not the commons. This ADR applies that same, already-ratified principle to the *inbound* case ADR-420 explicitly left to ADR-401. The polarity inversion is therefore not a reversal against the grain of recent canon — it is the completion of a direction the canon was already turning toward, made coherent by moving the credential to where its danger-zone teardown already lives: the human's account.
