# ADR-496 — A Member's Own Connections Answer on the Account Door

**Status**: Accepted (2026-07-29, operator-ratified — "let's first do the surface gap resolution, then discuss the inbound workspace-level consideration separately"). Implemented same day.
**Date**: 2026-07-29
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Channel (Axiom 6 — where a member's own connections are legible)
**Relates to**: ADR-431 (the connecting member owns the MCP grant — the relational fact this renders), ADR-425 (the credential is an account object — the outbound half already on this door), ADR-373/386 (`principal_grants`, the grant lifecycle), ADR-424 (operator zones — the `write_zones` projection reused here), ADR-340 DP29 (mirror once, compose few), ADR-491/494 (the two settings doors this sits inside), ADR-407 (three-scope taxonomy — workspace content vs member experience vs account)
**Amends**: nothing. **Defers**: workspace-level (shared) AI connections — see §5.

---

## 1. Context — a surface gap, not a model gap

The operator, reviewing Workspace Settings → Members: *"what about MCP connections? It's currently nested under AI Connections in workspace members, but mind, we can have user-level connections and workspace level."*

The audit found the **model is already right and ratified**. ADR-431 (Implemented 2026-07-09) made the relational unit of a foreign-LLM grant `(provider, connecting-member, workspace)` — precisely because a provider-collapsed key silently folded a second member's ChatGPT into the first member's grant row, so a revoke would kill both. Live receipt (2026-07-29):

```
principal_id | role        | connected_by
-------------+-------------+--------------------------------------
chatgpt      | foreign-llm | 2abf3f96…  (the owner)
claude.ai    | foreign-llm | 2abf3f96…  (the owner)
+ 2 human members who could each connect their own
```

ADR-431 §2 states the principle: **an MCP connection is a member's connection, not the workspace's** — authorized under one human's OAuth session, perceiving on their behalf, torn down on *their* eviction.

**The gap is where that fact is legible.** The only surface rendering it was Workspace Settings → Members — a roster whose primary job is governing *other people*. A member asking the ordinary question *"what have I connected?"* had to open a workspace-governance surface and visually filter for their own rows. Meanwhile the *outbound* half of exactly the same question — their platform credentials — already answered on the account door (ADR-425).

One member, one question, two directions across the same MCP boundary, and only one of them had a home on the member's own door.

## 2. D1 — The account door mirrors the member's own inbound connections

`MyAiConnectionsSection` renders on User Settings → Connectors, beneath the outbound platform connectors. It is a **read-only mirror** (ADR-340 DP29, "mirror once"):

- **Scope**: only rows where `connected_by_is_you` (served by `GET /workspace/members`, ADR-431 D3). A member never sees a peer's connection on their personal door. This is the load-bearing check — it is a privacy boundary, not a display preference, and the gate verifies it fails when removed.
- **No governance verbs.** No narrow, revoke, invite, or spend cap. Governance stays singular in `WorkspaceMembersCard`; this pane **links across** to it.
- **Shared primitives.** Reuses the roster's `providerBrandIcon` module and the same `write_zones` chips, so two surfaces for one fact cannot drift into two visual languages.

The pane subtitle now names both directions: *"platforms you reach out to, and AI assistants that reach in."* Previously it described only the outbound half — accurate before this change, incomplete after.

## 3. Why a mirror and not a move

Moving the AI-connections roster to the account door would break the workspace door's actual job. An owner governing a shared commons needs to see **everyone's** principals in one place — that is what makes narrow/revoke meaningful. Two surfaces, two jobs:

| Surface | Question it answers | Verbs |
|---|---|---|
| Workspace Settings → Members | *Who and what can act in this commons?* | narrow · revoke · invite · cap |
| User Settings → Connectors | *What have **I** connected, in and out?* | connect · disconnect (outbound only) |

This is the deliberate tiered redundancy of ADR-367 D3's macOS Control-Center/System-Settings model, not duplication.

## 4. Why this is cheap

Zero backend work. `connected_by`, `connected_by_is_you`, `label`, and `write_zones` are all already served — ADR-431 built the attributed fact, ADR-424 built the zone projection. This ADR only reads them from a second place. That is the dividend of ADR-431 having fixed the *model* first: the surface question became a filter.

## 5. Deferred — workspace-level (shared) AI connections

The operator's framing named two scopes: user-level and workspace-level. **Today only user-level exists**, and this ADR does not change that.

`own-agent` and `a2a` are in the `principal_grants.role` CHECK constraint, and `evict_principal` already handles them — but **no code path creates one**. They are reserved seats (ADR-382, Rung-2 persona agents, deferred).

A workspace-level connection — one credential shared by every member, the "agent-owned account" pattern — is a genuine capability with a trust model attached: who authorizes it, who it acts as, what happens when its authorizer leaves, and how its writes attribute under DP32. That is a separate discourse, explicitly sequenced after this one by operator ruling. **Deliberately not designed here**, so that a surface cleanup does not smuggle in a permission model.

## 6. Validation

- `api/test_adr496_my_ai_connections.py` — **16/16**: viewer-scoping, role filtering, four separate no-governance-verb checks, governance-still-in-the-roster, the cross-link, both backend fields, the mount, drill-in hiding, the subtitle, and shared icon reuse. The privacy check is **verified to fail** when the `connected_by_is_you` filter is removed.
- `tsc --noEmit` clean; `next build` green (170/170).
- Live receipt: the two active foreign-LLM grants both carry `connected_by` = the owner, so the pane renders ChatGPT + Claude for that viewer.

**Not verified by these gates** (needs a human click): the rendered pane in a live session, and — because prod is N=1 for AI connections today — the multi-member case where a peer's connection must *not* appear. The filter is receipted at the data layer; the rendered negative needs a second member to connect their own assistant.
