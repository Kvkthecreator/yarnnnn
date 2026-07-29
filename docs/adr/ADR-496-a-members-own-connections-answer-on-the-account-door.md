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

## 2. D1 — The account door renders the ROSTER COMPONENT, scoped to the viewer

**Operator correction, same day:** the first implementation was a purpose-built
`MyAiConnectionsSection` that *looked* like the roster — its own row markup, its
own labels, its own empty state. The operator's ruling: *"can't you align with
workspace views and information and display — want it to be as similar as
possible."*

That was the right call, and stronger than a styling note. A look-alike is a
**dual approach**: two components rendering one fact, guaranteed to drift the
first time either is touched. The twin is **deleted**. `WorkspaceMembersCard`
— the same component the workspace door renders — gains two orthogonal props:

| Prop | Default | Effect |
|---|---|---|
| `scope` | `'workspace'` | `'mine'` filters to principals the viewer authorized (`connected_by_is_you`) and omits the People section |
| `readOnly` | `false` | drops the narrow/revoke verbs |

Plus a `footer` slot for the cross-link. The account door mounts
`<WorkspaceMembersCard variant="compact" scope="mine" readOnly … />`.

Both new props **default to the prior behavior**, so the workspace door — which
passes only `variant="full"` — is byte-identical. The two surfaces are now
identical *by construction* rather than by careful copying: one fetch, one
partition, one row renderer, one set of brand marks and zone chips.

Scope semantics:
- `'mine'` keeps only rows where `connected_by_is_you` (the attributed fact
  ADR-431 D3 already serves). A member never sees a peer's connection on their
  personal door. This is a **privacy boundary**, not a display preference — the
  gate verifies it fails when removed.
- Under `'mine'` the **People section is omitted**: *"who else is in this
  workspace"* is a commons question, answered on the workspace door. The account
  door answers only *"what have I connected"*.

The pane subtitle now names both directions: *"platforms you reach out to, and
AI assistants that reach in."* Previously it described only the outbound half.

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

`own-agent` and `a2a` are in the `principal_grants.role` CHECK constraint and `evict_principal` handles them. **Correction (ADR-497, same day): `own-agent` DOES have a creation path** — `programs.py::mint_hire_grant`, on program activation (ADR-414 D5 program-as-hire); it is reachable with zero live rows, not unreachable. `a2a` is the genuinely uncreatable one (a reserved seat, ADR-382 Rung-2). The claim as originally written here was half wrong.

A workspace-level connection — one credential shared by every member, the "agent-owned account" pattern — is a genuine capability with a trust model attached: who authorizes it, who it acts as, what happens when its authorizer leaves, and how its writes attribute under DP32. That is a separate discourse, explicitly sequenced after this one by operator ruling. **Deliberately not designed here**, so that a surface cleanup does not smuggle in a permission model.

## 6. Validation

- `api/test_adr496_my_ai_connections.py` — **15/15**: component reuse (and that the twin is *deleted*), the scope axis, viewer-scoping, one-fetch, People omission, readOnly, governance-still-on-the-workspace-door, the cross-link, both backend fields, drill-in hiding, and the subtitle. The privacy check is **verified to fail** when the `connected_by_is_you` filter is removed.
- `tsc --noEmit` clean; `next build` green (170/170).
- Live receipt: the two active foreign-LLM grants both carry `connected_by` = the owner, so the pane renders ChatGPT + Claude for that viewer.

**Peer-exclusion — RECEIPTED (2026-07-29)**, closing the gap this section originally recorded. Prod is N=1 for AI connections, so the multi-member negative was manufactured in a rolled-back transaction on the live grants table: one grant reassigned to the workspace's actual second member (`nickyandnicholas`), then the endpoint's own `cb == auth.user_id` expression evaluated for both viewers over the same rows.

```
 principal_id | is_you_for_OWNER | is_you_for_MEMBER
--------------+------------------+-------------------
 chatgpt      | f                | t
 claude.ai    | t                | f
```

Disjoint at the server; the `scope='mine'` predicate replayed on both payloads yields `["claude.ai"]` for the owner and `["chatgpt"]` for the member, with the workspace door still showing both (narrowing the account door must not narrow the commons). Rollback verified — both grants restored byte-identical. Full write-up: [`docs/evaluations/sessions/adr496-peer-exclusion-2026-07-29.md`](../evaluations/sessions/adr496-peer-exclusion-2026-07-29.md).

**Still not verified** (needs a human click): the *rendered* pane in a live browser. The check above validates the server expression and the filter predicate, not pixels. Also unexercised: the OAuth path that would write a second member's `connected_by` for real (covered by ADR-431's own gate — this evaluation covers the read, not the write).
