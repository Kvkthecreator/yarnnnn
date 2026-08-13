# ADR-566 — The workspace allocates the agent's credential

> **Status**: **Accepted** (2026-08-13, operator-ratified in the agents discourse). Ships code (D3/D4/D5).
> **Date**: 2026-08-13
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — whose credential an agent acts through) + **Purpose** (Axiom 3 — that reach is a grant, and a grant is not authority). It resolves a reservation left in two vocabularies and closes the cross-reference gap between them.

**Amends**:
- [ADR-425](ADR-425-the-credential-is-an-account-object.md) **D3** — the reserved agent-owned credential model is **resolved and built**, restated in post-altitude vocabulary. Its two branches are decided: **own service account is primary**; *reuse-the-owner's* is **retired, not defaulted** (§4). D1 (a human's connector is their account object) is **untouched and re-affirmed** — this ADR adds a second, disjoint store, it does not move the first.
- [ADR-425](ADR-425-the-credential-is-an-account-object.md) **§4** — the "deliberate divergence from ChatGPT" clause named its own expiry at *"Altitude 3."* That altitude no longer exists (ADR-460 D1). The clause is rewritten against the fact it was actually tracking: not an altitude, but **whether a non-human principal holds a grant of its own**. It does, today (§2).
- [ADR-535](ADR-535-a-bound-connector-is-visible-to-the-members-lane.md) **D1** — narrowed to its actual subject. "A connector binding is a property of the member" is true of **the member's own connector** and was never a ruling about the workspace's. §3 states the boundary so the two stores cannot be conflated again.

**Preserves** (load-bearing, untouched):
- [ADR-460](ADR-460-agents-one-concept-independent-facts-one-gate.md) **D3.a** — the cliff. **Nothing is added to a registry row or a member manifest.** §2 argues why a credential is structurally not a row field, and the gates that hold D3.a stay green unchanged.
- [ADR-307](ADR-307-unified-permission-taxonomy.md) — the one consequential gate, including Phase 5's `external-write` family. This ADR routes *through* it and adds no bypass.
- [ADR-405](ADR-405-the-witness-dial.md) — permission is a grant, autonomy is the dial. This ADR is D1+D2 applied to reach.
- [ADR-373](ADR-373-multi-principal-substrate.md)/[ADR-431](ADR-431-the-connecting-member-owns-the-mcp-grant.md) — `principal_grants` and the roster. `own-agent` is an existing role with an existing ceiling; no new principal class.
- [ADR-382](ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md) **§4** — lifecycle, trust model, seat substrate, validation clock stay deferred. §5 states precisely why this ADR does not touch them.

---

## 1. Context — a reservation stranded in a retired vocabulary

ADR-425 (2026-07-09) inverted the credential's polarity: a human's connector is their account object, housed in the account door. It was right, it shipped, and it is untouched here.

But it carved out one case and reserved it:

> **D3** — *"When a **non-human principal must act through a platform** … it acquires a credential-use policy … **Own service account** — the agent holds its own credential (a workspace-service account). **This is the only connection legitimately keyed by `workspace_id`** — it belongs to the workspace's agent, not to any human."*

The reservation was never built, and six days later **the vocabulary it was written in was dissolved**. ADR-460 (2026-07-15) retired the A1/A2/A3 ladder and replaced it with independent facts. ADR-425 D3 still says *"A1 Freddie or an A2 hired agent."* ADR-425 §4 still names its expiry as *"Altitude 3."* Neither ADR cites the other — ADR-460's Preserves list does not mention ADR-425, and ADR-425 predates it.

The consequence, and the reason this ADR exists: **a live reservation became unreadable.** An audit of the agents surface (2026-08-13) read ADR-535 D1 — *"a connector binding is a property of the member, not the workspace"* — as a general ruling, concluded workspace-scoped connectors were foreclosed, and did not find ADR-425 D3 at all. The operator refuted it from memory of the surface that used to exist. A reservation nobody can find is indistinguishable from a refusal, and it had already produced one wrong answer.

**This is the ADR-535 failure mode named in its own §8** — *"the next such addition must not inherit it silently"* — arriving from the opposite direction: not a silent widening, but a silent narrowing, where a narrow ruling was read as a broad one because the broad one was written in a dead language.

## 2. D1 — Agent credential-reach is a GRANT, and a grant is not authority

The reconciliation, stated so it cannot drift: **ADR-460 D3.a and ADR-425 D3 are not in tension, because they govern different objects.**

D3.a makes consequential authority **unrepresentable in the registry row** — `KERNEL_AGENTS`, `POSTURE_ROW_KEYS`, `AGENT_MANIFEST_KEYS`. That is the correct home for that guard, and the reason is stated in the registry itself: a row is *config a member edits*. A field there is a switch, and a switch that grants authority is Rung 2 arriving as YAML.

**A credential is not a row field.** Under this ADR an agent reaches a workspace credential because it **holds a `principal_grants` row**, and every act through that credential passes the ADR-307 gate like any other consequential act. That answers ADR-405's own test in its own three terms:

| ADR-405's question | The answer here |
|---|---|
| **which grant?** | `role='own-agent'` — an existing role, existing CHECK constraint (migrations 189/234), existing ceiling |
| **which act-class?** | consequential platform write — an existing family (`external-write`, ADR-307 Phase 5) |
| **which dial setting?** | the witness dial, per-principal (ADR-405 D2) — before-witness by default |

A feature that can be expressed in those three terms is **not species law and not a new mechanism** (ADR-405 §5). This one can. So:

> **Nothing is added to any agent registry row, posture row, or member manifest. `AGENT_ROW_KEYS`, `POSTURE_ROW_KEYS`, and `AGENT_MANIFEST_KEYS` are byte-identical after this ADR.** The cliff holds exactly where D3.a put it.

**The distinction the earlier audit collapsed, recorded because it is the load-bearing one:** the exogenous track-record clock (ADR-380 D4, ADR-382 §4.4) gates **autonomy**, not **reach**. Reach is a grant; autonomy is a dial setting *on* that grant. Conflating them makes every credential question look like a Rung-2 question, which is how a cheap build gets mistaken for an expensive one.

## 3. D2 — Two stores, two questions, permanently disjoint

The failure this ADR must not re-create is the one ADR-425 §1 diagnosed: *"two facts crammed into one row."* So the boundary is stated once, structurally:

| | **The human's connector** | **The workspace's connector** |
|---|---|---|
| Whose | a member's own Slack/Notion/GitHub | the workspace's, allocated to its agents |
| Keyed | `user_id` (RLS, index, writes) | `workspace_id` |
| Scope filter | `account_scope_filter` | `workspace_credential_filter` (new, D3) |
| Door | account settings → Connectors (ADR-425 D1) | workspace settings → Connectors (D5) |
| Who acts through it | that member, and their lane as their hands | an `own-agent` principal, gated |
| Dies with | that human's account | the workspace |

**Neither store is a fallback for the other.** A workspace credential is never silently substituted when a member has none, and a member's credential is never reachable by an agent. The two reads answer different questions, and a caller that wants one must not be able to accidentally get the other — which is why D3 makes the resolution a chokepoint rather than a convention.

**ADR-535 is preserved exactly.** Its D2 (`list_integrations` on the lane surface) and D3 (the frame states the ceiling affirmatively) are unchanged: a member's lane still sees *the member's* bindings, because the lane is the member's hands. What ADR-535 D1 ruled — *"a lane sees the bindings of the member whose turn it is, and no others"* — remains true and is **strengthened** here: it now has a named counterpart it cannot be confused with.

## 4. D3 — Own service account is primary; owner-reuse is retired

ADR-425 D3 offered two branches and defaulted to *"reuse the owner's credential."* The operator's ruling (2026-08-13): **the workspace allocates the credential** — the second branch — and the first is **retired, not merely non-default**.

The reason is a member-visible property, not tidiness. Owner-reuse means the agent acts through a specific human's personal OAuth token: the agent's Slack messages are that human's Slack messages, the agent's reach dies when that human rotates a token or leaves, and the workspace's automation silently entangles one person's private auth. It also re-creates exactly the confusion ADR-425 §1 set out to remove — *"does this mean connectors for every individual user share the same permission and auth considerations?"* — one layer down.

An allocated workspace credential is the honest object: **the workspace holds it, the roster can show it, eviction of any human does not revoke it, and its acts attribute to the agent principal rather than to a borrowed human.**

`platform_connections.workspace_id` is the column ADR-425 D3 explicitly retained for this and is now load-bearing rather than reserved. **No migration is required** — the column exists (migration 201, additive) and the CHECK constraint on `principal_grants.role` already admits `own-agent` (migrations 189/234).

## 5. D4 — One chokepoint, fail-closed (the ADR-563 lesson applied)

Credential resolution today is **eight inline `.eq("user_id", auth.user_id)` lookups** across `services/platform_tools.py` (Slack, Notion, the Composio route, and the capability probes). There is no chokepoint. Adding a second store to that shape would mean eight independent opportunities to read the wrong one, and the next provider would make nine.

That is precisely the defect ADR-563 closed for MCP scopes — *the check belongs at the seam that already resolves identity, never at each call site, and it fails closed.* Applied here:

> **`resolve_platform_credential(auth, platform)` is the single resolution path.** It reads the acting principal from `auth`, selects the store from that fact alone — a human principal gets the account store, an `own-agent` principal gets the workspace store — and returns no credential when the principal is unrecognized. **It never falls back across the boundary.**

A fallback here would be the ADR-548 defect shape: *a fallback degrading to a plausible value is worse than one that fails.* An agent silently acting through the owner's Slack because its own allocation is missing is exactly a plausible wrong value, and it is the retired branch (D3) arriving through an error path.

**Gate**: `api/test_adr566_workspace_credential.py` asserts (a) no `platform_connections` read outside the chokepoint keys on a raw `user_id`, (b) the resolver fails closed on an unknown principal, (c) the two stores never cross-fall-back, and (d) `AGENT_ROW_KEYS` / `POSTURE_ROW_KEYS` / `AGENT_MANIFEST_KEYS` are unchanged — the D3.a ratchet, asserted from this side too.

## 6. D5 — The workspace Connectors pane returns, as the agents' credentials

Workspace Settings gains a **Connectors** pane. It is not the pane ADR-425 removed: that one presented *humans'* connectors under a workspace heading, which was the mis-scoping ADR-425 correctly fixed. This one presents **the workspace's own allocated credentials** — what its agents act through.

- The account door's Connectors pane is **unchanged** (ADR-425 D1). A member manages their own connectors there, exactly as today.
- The workspace pane is **authority-gated** like Billing (ADR-491 D1): allocating a credential an agent acts through is workspace governance, not a personal preference.
- Each row states the ceiling affirmatively, per ADR-535 D3's discipline: *what the agents may reach through it, and that every consequential act still waits for approval.* Naming a capability's edge is part of granting it.

## 7. What this ADR does NOT do

- **It does not add a field to any agent row or manifest** (ADR-460 D3.a). The gates that hold the cliff pass unchanged, and D4's gate asserts it from the new side.
- **It does not grant any agent consequential authority.** Reach is not authority: every consequential act through an allocated credential passes the ADR-307 gate and lands in the queue under the witness dial. An agent with a workspace Slack credential can, today, propose a Slack write and not send one.
- **It does not build the ADR-382 seat.** Lifecycle, trust model, per-seat substrate, and the validation clock stay deferred (§4 there). This ADR touches *reach*, which §4 never governed.
- **It does not give a chat lane new reach.** A lane is the member's hands (ADR-411 D4) and stays exactly as scoped: ADR-535's `list_integrations` visibility, no `platform_*` tool on the lane surface. **`LANE_TOOL_NAMES` and `LANE_SURFACE_EXTRA` are unchanged.**
- **It does not un-pause ADR-420's connector breadth.** No new provider is acquired; this is about which store an existing provider's credential lives in.
- **It does not move a human's connector.** ADR-425 D1 stands.
- **No migration.** The column and the role constraint both already exist.

## 8. Consequences

**Good.** A reservation that had become unreadable is resolved in the live vocabulary, with the two ADRs that disagreed now citing each other. The workspace can allocate a credential its agents act through without any human's personal auth being borrowed. Credential resolution gains a chokepoint where it had eight call sites, which is a defect class closed rather than a feature added.

**Cost.** A second credential store is a second thing to reason about, and the boundary between them is now load-bearing prose plus one gate. D2's table and D4's fail-closed resolver are the mitigations; the gate is what makes them structural.

**The risk, named.** The tempting next step is to let a lane reach *through* a workspace credential — that is the content-reach half ADR-535 §7 explicitly left gated, and it still requires the per-caller-class rung ADR-535 D4 recorded as owed. **This ADR does not build that rung and does not cross it.** An agent acting through an allocated credential does so as an `own-agent` principal at the ADR-307 gate, never as a member's lane.

## 9. One-line statement

**A human's connector is their account object and a workspace's connector is the workspace's — two disjoint stores behind one fail-closed resolver — so an agent acts through a credential the workspace allocated to it under an `own-agent` grant and the ADR-307 gate, which resolves ADR-425 D3 in the vocabulary that replaced altitudes without touching ADR-460 D3.a's cliff: reach is a grant, authority is a dial, and only the second was ever the thing we were deferring.**
