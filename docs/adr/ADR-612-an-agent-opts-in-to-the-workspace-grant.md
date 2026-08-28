# ADR-612: An agent opts in to the workspace's grant

**Status**: Ratified 2026-08-26; **D5/D6 added same day** after the operator asked the question that exposed the gap — *"can the Text app and its Editor agent utilize a connected scope?"* The answer was NO, and D1–D4 alone left the control near-inert. (Operator thesis: *"workspace level connectors are more like workspace level grants and permissions handling — then an agent can opt in to use that connector explicitly … so a user can explicitly scope a connector for an agent, which changes its context scope"*). Phase 1 implemented same day.

**Builds on**: ADR-405 (permission is a grant) · ADR-577 (the credential is a HUMAN's; an agent caller is refused) · ADR-582 (connection = consent + credential + aperture) · ADR-585 (turn reach — the read-only platform surface) · ADR-596 D1/D2 (authority lives on grants and declarations, never on a being) · ADR-601 D1 (capability at the app).

**Amends ADR-611** D4/D5's framing. ADR-611 refused *per-agent apertures* and was right about that object; it did not distinguish a **grant** (what may be reached at all) from an **opt-in** (which granted thing this being works against). This ADR draws that line and builds the opt-in.

## Context

### The gap ADR-611 did not see

ADR-611 argued per-agent connector control was "coarser, not finer" — Supervisor covers every string, Editor covers two desks. That argument holds **only if** the agent dial replaces the declaration's source picking. It does not. The operator's model is three layers, each narrowing the one above:

| layer | object | question | today |
|---|---|---|---|
| workspace | **grant** | which connectors exist here, and what may they reach? | account-level (`platform_connections`, keyed `user_id`) |
| agent | **opt-in** | which of those does THIS being work against? | **absent — this ADR** |
| declaration | **ask** | which slices does THIS file pull? | `_string.yaml` sources, `ask ∩ aperture` |

Read that way, ADR-611's objection dissolves: an opt-in does not compete with the declaration, it sits above it. The two coexist, and per-file source picking stays exactly as fine-grained as it was.

### Why this is NOT authority on a being (the ADR-596 D1 test)

The cliff forbids a field that grants a being power. **An opt-in can only ever NARROW what the workspace already granted.** A being with `slack` opted in holds no reach the member's own connection did not already carry; a being with nothing opted in holds strictly less. There is no value of this field that widens anything.

That is the whole test, and it is enforceable rather than asserted: the opt-in is applied as a **set intersection against the connected platforms**, so an opt-in naming a platform the member never connected yields nothing. Widening is unrepresentable, not merely discouraged.

Two further consequences keep ADR-577 intact:
- The opt-in selects **which granted connector a being works against**. It never hands a being a credential; `is_agent_caller` still refuses, and the member's own turn is still what carries reach.
- The opt-in is **member data, not kernel data**. It does NOT live on the being's registry row (kernel code, `AGENT_ROW_KEYS`-whitelisted, and the whitelist deliberately admits no reach-shaped key). It lives in `member_state`, workspace-scoped.

### What a being is told today — all of it

Before this ADR, `turn_has_reach(app, artifact_path, derive_recipe)` derived reach from the turn's SHAPE alone (D5/D6 replace it), and when a turn had reach the frame said *"list_integrations tells you which platforms the member has CONNECTED (Notion, Slack, GitHub)"* — **every connected platform, for every being**. There is no per-being narrowing anywhere in the frame, the tool set, or the allowlist. "Scope a connector for an agent" is genuinely absent, not merely coarse.

## Decision

### D1 — The opt-in is member data in `member_state`, never a field on the being

Key: `agent_connectors`. Value: `{ "<agent_slug>": ["slack", "notion"], … }`, workspace-scoped by `member_state`'s own `(workspace_id, principal_id, key)` primary key.

`member_state` is the established home for exactly this shape (ADR-489 D5's notification prefs precedent): API-mediated, service-role RLS, workspace-scoped, and already covered by the purge paths. **No migration.**

It is deliberately NOT on the being's row: that row is kernel code, and `AGENT_ROW_KEYS` admits no reach-shaped key — the ADR-460 D3.a whitelist. Member preference about a kernel being is not a property of the being.

### D2 — Absent means EVERYTHING GRANTED, and that default is load-bearing

A being with no opt-in recorded reaches everything the member's connections carry — today's behaviour exactly. The default is not a placeholder: **an opt-in that defaulted to "nothing" would silently break every existing lane on deploy**, and a scoping feature whose rollout is a regression is not a scoping feature. Narrowing is an act the member takes, never one they inherit.

`{}` (an explicit empty list) is therefore meaningfully different from absence: it means *this being reaches no platform*, and is a choice the member made.

> **Amended 2026-08-27 (operator ruling) — absence is no longer REACHABLE from the surface.** The pane's "Follow my connections instead" link was the only caller of `set(slug, null)`; the toggles always send an array. It is deleted along with the "Editing" row, as part of a pass removing lines the surface states twice. **The distinction itself is unchanged** — `opt_in_for` still returns `None` for absence, callers still must not collapse it with `or []`, and every being still *starts* absent, which is the state the paragraph above exists to protect. What changed is only that a member who scopes a being cannot return it to "follows my connections" from this pane. Recorded rather than quietly absorbed, because it makes D2's default a one-way door in the UI while leaving it intact in the model — and the API path stays live, so restoring a control is a UI change with nothing to rebuild underneath.

### D3 — The opt-in narrows the CONTEXT SCOPE, not just a display

This is the half that makes the feature real. When a turn has reach, the being's opt-in filters, at one derivation point each:

- **the tool set** — `turn_reach_tool_names()` / `turn_reach_tool_defs()` gain the allowed platforms, so an un-opted platform's tools are not declared, not dispatchable, and not in the allowlist;
- **the frame prose** — the connector section names the being's OWN platforms rather than every connected one.

Since D5 the same resolution also answers *whether* the turn reaches at all, so both live in one function (`resolve_turn_reach`) rather than two.

Both derive from the SAME resolved set, which is the ADR-585 rule the Scout bug taught: the declared payload, the execution allowlist and the prose must be computed once, or they disagree and ship a lie.

### D4 — The workspace GRANT layer is named, and stays account-level for now

The operator's model calls layer 1 a workspace grant. Today `platform_connections` is keyed `user_id` under a single `USING (user_id = auth.uid())` policy — the re-key ADR-611 D4 priced. **This ADR does not take it.** The opt-in is built against the account-level connections that exist, and the re-key later changes *what is grantable* without changing the opt-in's shape — which is why this order is safe rather than merely expedient.

Stated plainly so the sequencing is not mistaken for a claim: **"workspace level" is aspirational at Phase 1.** The opt-in is workspace-scoped (it lives in `member_state`); the GRANT it narrows is still account-level.

### D5 — A desk turn reaches when the member scoped that being (amends ADR-585 D1)

> ⭐ **AMENDED by [ADR-615](ADR-615-reach-follows-the-principal.md) (2026-08-28) — this decision's DEFAULT is superseded.** D5 made a desk turn default-CLOSED, unlocked only by an explicit opt-in. ADR-615 found that posture rested on the turn's SHAPE standing in for the presence of a principal, which does not survive inspection: a desk turn and a chat turn are the same member, embodied identically. **Absence of an opt-in now means everything granted, at every surface** — matching D2 above, one layer up. The opt-in becomes purely subtractive, which strengthens rather than weakens the D1 cliff test. The boundary D5 was protecting is preserved structurally: unattended runs are toolless by construction. **D1–D4 below are unchanged.**

ADR-585 confined turn reach to the OPEN CHAT turn: *"App lanes and derive turns are workspace-disciplined (landed files only), the same as agents."* That confinement was correct **for the world it was written in** — there was no way to say WHICH connector an agent may use, so it was all-or-nothing and nothing was the safe default.

The opt-in is that missing expression. So the rule becomes: **a turn carries reach when it is the open chat (unchanged) OR when the member has explicitly scoped this being.** The caution survives; only the all-or-nothing that forced it goes.

Three properties keep this inside the boundaries ADR-585 was protecting, and none of them is a promise — each is structural:

- **Not an agent holding a credential.** A desk lane stamps `member:{id} via {model}` — a human's hands — so ADR-577's `is_agent_caller` refusal correctly does not trip. Unchanged by this ADR; it simply never applied to lane turns.
- **Still TRANSIENT** (intake-pipeline §5). Fetched content lives in the turn and dies with it; keeping it is an ordinary attributed write, exactly as in chat. The durable-intake pipeline is untouched.
- **Unattended standing runs cannot reach this at all.** They execute through `derive_turn.run_bounded_derive_turn`, which is *toolless by construction* ("No tools, one user message") and never calls `lane_tools_openai`. A scoped being does not gain live reach in its unattended runs — that would be a clock plus a credential, which is the combination ADR-596 D2 houses on grants and declarations, not here.

**Default-closed**: no opt-in recorded → no desk reach, exactly as before this ADR. A member must ask, per being.

**Scoped-to-nothing wins everywhere**, including open chat: if a member says a being reads through no connection, that is honoured even where the turn would otherwise have reached. `(True, ())` is unrepresentable — a being with nothing to reach does not carry the surface at all.

### D6 — `turn_has_reach` is DELETED, not kept beside its successor

It answered "does this turn reach?" from the turn's SHAPE alone, which stopped being the whole question the moment an opt-in could unlock a desk turn. `resolve_turn_reach` returns both halves from ONE lookup — resolving them separately would read the same row twice and could disagree between the reads, which is the precise shape of the Scout bug ADR-585 §5 exists to prevent.

## Consequences

- A member can scope a being to a subset of their connections, and the being's context genuinely changes — fewer tools, honest prose.
- ADR-611 D1/D2/D3 stand unchanged: the aperture still mounts on the connection, the ask still lives on the declaration. This ADR adds the layer between them.
- ADR-577 is untouched: no being holds a credential; the opt-in selects among the member's own.
- The `AGENT_ROW_KEYS` whitelist is unchanged — this feature deliberately adds nothing to it, which is the check that it stayed on the right side of the cliff.

**The rule this ADR leaves behind**: a grant is what MAY be reached; an opt-in is what a being CHOOSES to work against, and it can only ever narrow. A field that can only subtract is not authority.
