# ADR-431 — The Connecting Member Owns the MCP Grant: Foreign-LLM Principals Are Per-Member, Not Per-Workspace

> **Status**: **Implemented** (2026-07-09). Surfaced from an operator audit of the Workspace Members roster: with multiple humans now in a workspace, each with their own ChatGPT/Claude MCP connection, the roster showed a single provider-collapsed "External LLM" row that could not say *whose* connection it was — and the grant table physically could not hold two members' same-provider connections. **All of D1–D5 shipped** (migration 209 + `principal_grants.py` + OAuth hook + gate consult + roster + `WorkspaceMembersCard` + regression gate `test_adr431_connecting_member.py` 7/7). N=1 byte-identical: migration backfilled the 2 live foreign-LLM grants → their workspace owner; owner/member grants carry `connected_by` NULL (coalesced to `principal_id` in the widened index) so the owner path is unchanged (ADR-373 consult suite 25/25 + ADR-386 lifecycle 12/12 still green). Live-DB validation: two distinct members' same-provider grants coexist; a true `(provider, workspace, connected_by)` duplicate is rejected by `uq_principal_grant_active`.

**Date**: 2026-07-09
**Dimension**: Identity (Axiom 2 — whose connection a foreign-LLM grant is) + Substrate (Axiom 1 — the relational unit of `principal_grants`) + Channel (Axiom 6 — where an AI connection is surfaced)

**Supersedes / amends**:
- **ADR-373 D2.a** ("one provider = one grant per workspace"; foreign-LLM `principal_id` is the provider host-id). D2.a's *problem* — a connector re-mints its OAuth `client_id` on every re-registration, fragmenting one connection into many dead rows — is real and its fix (resolve the client to a stable provider identity) is **preserved**. What this ADR changes is the **relational unit**: the grant is keyed by *(provider, **connecting member**, workspace)*, not *(provider, workspace)*. "One provider = one grant" was correct at N=1 (one human, so "ChatGPT is connected here" unambiguously meant "my ChatGPT"). At N>1 it collapses distinct members' connections into one row.
- **ADR-386 D1** (foreign-LLM grants auto-provision on OAuth token-mint). The auto-provision survives; the grant it writes now records `connected_by` (the member whose OAuth session minted the token), and the active-grant uniqueness widens to include it.
- **ADR-425 Amendment AD5** (`connected_by` promoted from "reserved for D3" → "needed for human member-routing"). This ADR **completes AD5's direction**: AD5 established that the moment a member routes a *platform* credential into a shared commons you need `connected_by` to attribute + tear it down. The identical logic applies to a *foreign-LLM* connection — it is a member's connection, authorized under the member's session, and must tear down on that member's eviction. AD5 named the column for platform connectors; this ADR extends it to the foreign-LLM grant, where the same relational fact was missing.

**Preserves**:
- **ADR-415 D3** (AI principals are governable on Workspace Settings → Access). This ADR does **not** move AI principals off the Access roster (the "split them out to their own door" option was considered and rejected — §5). It makes the roster *correct* for multiple members, not smaller.
- **ADR-373** multi-principal thesis, **ADR-307/405** (gate + witness dial), **ADR-320** permission topology, **ADR-286/378** single-writer-no-CRDT. The write-region grant semantics are unchanged; only the grant's *identity key* widens.
- **N=1 byte-identical.** A solo operator's workspace has exactly one member (the owner), so every foreign-LLM grant's `connected_by` is the owner and the widened uniqueness degenerates to today's `(provider, workspace)`. The migration is a column add + backfill-to-owner; no owner-visible behavior changes.

---

## 1. The problem the operator found

The Workspace Members roster (Workspace Settings → Access, `WorkspaceMembersCard`) shows, for a workspace with three humans (owner + two members) each connected to ChatGPT and Claude over MCP:

```
kvkthecreator@gmail.com (you)   Owner
ChatGPT                         External LLM   ← whose?
Claude                          External LLM   ← whose?
seulkim88@gmail.com             Member
nickyandnicholas@gmail.com      Member
```

The two "External LLM" rows are **provider-collapsed and member-blind**. The operator's exact framing:

> *"we now have multiple users, with multiple mcp connections. the current seems mis-placed from the new relational consideration."*

This is not a rendering bug. It is a **relational-model** flaw, and it is load-bearing at the schema:

- `principal_grants` uniqueness is `UNIQUE (principal_id, workspace_id) WHERE status='active'` (migration 189).
- For a foreign-LLM principal, `principal_id` is the **provider host-id** (`chatgpt`, `claude.ai`) per ADR-373 D2.a.
- Therefore **there is exactly one active foreign-LLM row per provider per workspace**, and **no column records which member connected it.**

When seulkim connects *their* ChatGPT to a workspace that already has the owner's ChatGPT grant, `ensure_principal_grant` finds the existing active `(chatgpt, workspace)` row and **no-ops** (ADR-386 D1's idempotency). seulkim's connection is silently folded into the owner's grant row. The roster cannot distinguish them; a narrow/revoke on "ChatGPT" acts on *both* members' connections at once (or, via `client_ids_for_provider`, on whichever tokens happen to be present). The model has no seat for "seulkim's ChatGPT" as distinct from "the owner's ChatGPT."

### Why this was invisible until now

At N=1 the provider-collapsed key is *correct*: one human means one ChatGPT connection means one unambiguous grant. ADR-373 D2.a was reasoning from the live single-operator population (it collapsed 7 fragmented `client_id` rows → 2 provider rows for one workspace, `d5b9029b`). The collapse was the right fix for *client_id churn within one member's connection*. It over-collapsed by also merging *across members*, but there were no other members to reveal it. The commons-first launch (ADR-404, member invites live) is the first time N>1 humans share a workspace — which is exactly when the flaw becomes reachable.

---

## 2. The principle

**A foreign-LLM connection is a member's connection, not the workspace's.** It is authorized under a specific human's OAuth session (the member ran the connect flow from *their* ChatGPT), it perceives the commons on *their* behalf, and it must be torn down when *that member* is evicted — not survive because a different member also happens to use ChatGPT.

This is the same principle ADR-425 applied to human platform credentials ("perception through a platform is a property of a **principal**, not the commons") — extended to the principal-that-is-an-AI. ADR-425 kept humans' *credentials* on the human. This ADR keeps a foreign-LLM's *grant* keyed to the human who connected it. The two are the same move seen from the two sides of an MCP connection: outbound (human → platform, ADR-425) and inbound (external LLM → commons, here).

The relational unit of a foreign-LLM grant is therefore **(provider, connecting-member, workspace)**, not **(provider, workspace)**.

---

## 3. Decisions

### D1 — `principal_grants` gains `connected_by`; active-uniqueness widens to include it

Add `connected_by UUID` (nullable, FK `auth.users.id`) to `principal_grants` — the human member under whose authorization this grant exists. For:
- **owner / member** grants: `connected_by = principal_id` (a human's grant is trivially their own) or NULL (equivalent — see D3).
- **foreign-llm / a2a** grants: `connected_by` = the `MCP_USER_ID` / authenticated human whose OAuth token-mint provisioned the grant (ADR-386 D1's `exchange_authorization_code` / `exchange_refresh_token` paths know this — it is the session's user).
- **own-agent / platform**: `connected_by` = the human who created/authorized the principal (owner by default at N=1).

Replace the active-uniqueness index:

```sql
-- was: UNIQUE (principal_id, workspace_id) WHERE status='active'
-- now: a foreign-LLM's identity includes WHO connected it.
UNIQUE (principal_id, workspace_id, connected_by) WHERE status='active'
```

with `connected_by` coalesced for the human/agent classes so their behavior is unchanged (a human's grant is unique per `(user, workspace)` regardless). The widening is *only* meaningful for the classes where one provider can be connected by many members.

**N=1 backfill**: every existing foreign-LLM grant gets `connected_by = workspace.owner_id`. This is provably correct today — every live foreign-LLM grant was minted by the solo owner (the ADR-373 D2.a receipt: all 7→2 collapsed grants trace to the single owner of `d5b9029b`). Byte-identical after backfill.

### D2 — auto-provision records the connecting member

`ensure_principal_grant` (ADR-386 D1) and its two OAuth call sites (`_ensure_foreign_llm_grant` on `exchange_authorization_code` + `exchange_refresh_token`) thread the session's human `user_id` as `connected_by`. The idempotency check widens: an existing active `(provider, workspace, connected_by)` is the no-op key. Now seulkim's ChatGPT and the owner's ChatGPT are two distinct grant rows — each attributed, each independently narrow/revoke-able.

### D3 — the roster humanizes AI rows by their connecting member

`GET /workspace/members` returns `connected_by` (and its resolved email) on each grant. `WorkspaceMembersCard` renders a foreign-LLM row as **"ChatGPT · connected by seulkim88@gmail.com"** (or "· your connection" for the viewer's own). The provider stays the primary label + icon; the connecting member is the secondary attribution that resolves the operator's "whose?" question. This is the icon/label update the operator asked for, done *after* the relational fact exists to hang it on — otherwise the icon change would be cosmetic paint over a model that can't tell the two ChatGPTs apart.

Grouping stays by **role** (ADR-385's rejected-transport-grouping principle holds); `connected_by` is row-level attribution, not a grouping axis.

### D4 — revoke/narrow act on the specific member's connection

With the widened key, `evict_principal` / `narrow_grant` target the `(provider, workspace, connected_by)` row — revoking "seulkim's ChatGPT" leaves the owner's ChatGPT connected. Token deletion (`client_ids_for_provider`) is scoped to the tokens minted under *that* `connected_by` session, not all of the provider's tokens in the workspace. This closes a latent authority bug: today a revoke of "ChatGPT" would (via provider-wide token sweep) disconnect a *different* member's ChatGPT.

### D5 — member eviction cascades to their AI connections

When a human member is evicted (ADR-386 revoke), their foreign-LLM / a2a grants (`connected_by = that member`) are revoked in the same act — a member's departure takes their AI connections with them. This is the AD5 teardown-key semantics, now with a concrete cascade. (Owner eviction is impossible — ADR-386 D4 — so the owner's AI connections are never orphaned this way.)

---

## 3b. What is NOT a principal — the A2 chat model (the stress test)

The relational fix above only makes sense against a sharp line the operator pressured and the canon draws precisely: **a member's in-chat model is not a principal and never appears on this roster.**

When a human chats with Sonnet / Gemini / a router-driven model inside a YARNNN chat lane (ADR-408 Altitude 2), the model runs **as that member's hands**. Every file write attributes as `member:{user_id} via {model}` (`lane_runner.py::lane_caller_identity`), and `_caller_class` maps the `member:` prefix **to the operator class** — so **the member's own grant is the permission boundary**. The model holds no grant, no identity, no roster row. It is a *tool the principal is holding*, recorded in the `via {model}` suffix for legibility only. ADR-408's altitude table states it outright: *"Altitude-2 helpers are NOT principals."*

The line, stated once so no future work blurs it:

| | **A2 chat model** (Sonnet/Gemini via the router) | **foreign-LLM** (ChatGPT/Claude over MCP) |
|---|---|---|
| Where it runs | *inside* a YARNNN chat lane, driven by the router | *outside*, reaching in over MCP |
| Whose act is it | **the member's** — `member:{user} via {model}` | **its own** — `chatgpt` / `claude.ai` |
| Authorization boundary | the member's grant | its own grant (`connected_by` the authorizing member, D1) |
| Roster row | **none** — the member is the principal | **yes** — it is a member |
| Operator's phrasing | "seulkim using chat with Sonnet" | "seulkim authorized ChatGPT to reach in" |

**The invariant that keeps the taxonomy coherent (from the stress test):** `connected_by` traces **every non-human principal to the human who authorized it**. An A2 tool has no grant because it never needed one — it borrows the member's. A foreign-LLM has its own grant *and* a `connected_by` — it acts autonomously but only because a specific human let it in, and it dies when that human leaves (D5). The A2/principal line is therefore not "is it an AI" (both are); it is **"whose authorization does the write travel under — the human's session (tool) or the connection's own OAuth (principal)."**

**The roster scope, exhaustively:** humans (`owner`, `member`), external LLMs / automation reaching in (`foreign-llm`, `a2a`, `platform`), and (future, ADR-382) Altitude-3 persona agents (`own-agent`). Router-driven chat models are *deliberately absent by design*, not an omission.

> **Corollary (the two-ChatGPT case).** The same human may both (a) use ChatGPT-the-model in a chat lane — no roster row, writes as `member:X via ...` — and (b) have connected ChatGPT-the-product over MCP — one roster row, `connected_by X`, writes as `chatgpt`. Same human, same brand, two identities, one roster row. This is *correct* (two genuinely different acts: driving a tool vs authorizing an autonomous reacher-in); the roster copy (§3c) must make the distinction legible so an operator does not read the row as "seulkim's chat."

## 3c. Display — clear, minimal, shipped now (FE-only, ahead of the schema)

The operator's ruling: *"clear but minimal ways of displaying the information now — applying icons/badges to help with the conceptual framing — should suffice,"* implementation delegated. The display lands **immediately, FE-only**, using data the roster already carries (`role`); the `connected_by` attribution (D3) enriches it once the schema ships.

- **Two partitions, one fetch (DP29):** the flat roster splits into **People** (`owner`, `member`) and **AI connections** (`foreign-llm`, `a2a`, `platform`, `own-agent`). The confusing screenshot was a flat list where "ChatGPT" sat between two humans with no signal it is a different *kind* of principal. The AI section renders only when at least one AI principal exists (a cold-start owner-only workspace sees a clean People list, no empty AI box).
- **A one-line kind hint on each AI row** naming the distinguishing fact — *"Connects over MCP · writes as itself"* — the visible counterpart to §3b's line.
- **Per-provider brand marks** (2026-07-09 follow-on, operator-chosen): each external-LLM row renders its PROVIDER brand glyph (OpenAI for ChatGPT, Anthropic for Claude, …) keyed on `principal_id` (= the ADR-379 host-id), so ChatGPT ≠ Claude at a glance. Single source `web/lib/ai-providers/brand-icons.tsx` (the `connectors/registry.tsx` pattern — host-id → mark, generic `Cpu` fallback for unmapped providers, monochrome `currentColor` so the neutral roster tone is preserved). Humans + own-agent keep the role's lucide glyph.
- **Deferred to D3 (schema):** the `connected_by` sub-label ("· connected by seulkim88@gmail.com" / "· your connection"). Until the column exists, the partition + kind-hint carry the framing; the connecting-member attribution is the enrichment ADR-431's schema unlocks.

Landed in `WorkspaceMembersCard.tsx` (2026-07-09) alongside the dead-code deletion (the `roleGroups`/`roleFilter` props + `MemberRoleGroup` type, unreachable since ADR-415 D4 removed their only caller). This is the one piece of ADR-431 that ships before ratification — it is pure legibility over existing data and reversible; the schema re-key (D1–D5) remains Proposed.

## 4. What this achieves

- The roster answers "whose ChatGPT?" — the exact operator question.
- Two members' same-provider connections are **two grants**, independently governed. No silent collapse, no cross-member revoke.
- Foreign-LLM connections inherit the human-credential principle (ADR-425): a connection belongs to the principal who authorized it and tears down with them.
- ADR-373 D2.a's client_id-churn fix is preserved (still resolve client → stable provider identity); the identity is now *per member*, not *per workspace*.
- N=1 is byte-identical.

---

## 5. Alternatives considered

- **Split AI principals off the Access roster into their own door (extend ADR-425 to foreign-LLM).** Rejected. ADR-425 moved *human credentials* off the workspace because a credential is an outbound account object. A foreign-LLM grant is *inbound* — it is a writer of the commons, and "who can write the commons" is exactly what the Access roster governs (ADR-415 D3). Moving it to an account door would break the "one place to narrow/revoke who writes here" act. The problem was never *that AI is on the roster* — it was that the roster *couldn't tell members' connections apart*. Fix the relational unit, keep the surface.
- **Filter foreign-LLM off the default roster (UI-only).** Rejected as a fix (kept as an optional later filter chip, ADR-415 D3's own note). Hiding the rows doesn't resolve the schema collapse — two members' connections still can't coexist as grants; a hidden-but-broken model is worse than a visible one.
- **Leave the provider-collapsed key; disambiguate in the UI only.** Impossible — the UI has nothing to disambiguate *by*; the collapse happens at the unique index before any row reaches the UI.

---

## 6. Consequences / risks

- **Migration touches a live gate table.** The uniqueness index is load-bearing for `ensure_principal_grant` idempotency and the gate consult (`_load_active_grant`). The index swap must be transactional and the coalesce-for-humans clause must be proven to leave owner/member lookups byte-identical (regression: the existing `test_adr373_grant_consult.py` owner byte-identical block must stay green).
- **`connected_by` is nullable + backfilled** — pre-migration rows are all owner-minted (proven), so the backfill is total; but the column must tolerate NULL at the coalesce boundary for the human/agent classes where it is definitionally redundant.
- **The consult's provider resolution** (`resolve_provider_id`) is unchanged — a foreign-LLM caller still resolves to its provider host-id; the *grant lookup* now additionally scopes by the caller's session user. This is the one subtle spot: the MCP caller must carry enough identity to resolve `connected_by` at consult time. Verify `MCP_USER_ID` / the OAuth token's bound user reaches the consult (it does today — the token→user binding exists; it is just not read into the grant key yet).

---

## 7. Blast radius (all SHIPPED 2026-07-09)

| Target | Change | Decision |
|---|---|---|
| `supabase/migrations/209_adr431_connected_by.sql` | Added `connected_by UUID`; swapped active-uniqueness to `(principal_id, workspace_id, COALESCE(connected_by::text, principal_id))` (coalesced for human/agent — byte-identical); backfilled the 10 non-human grants → workspace owner; `idx_principal_grants_connected_by` for the D5 cascade | D1 |
| `api/services/principal_grants.py` | `ensure_principal_grant` accepts + writes `connected_by` (idempotency key widened, `is_("connected_by","null")` for the singleton case); `narrow_grant`/`evict_principal`/`_load_active_grant` take `connected_by`; `delete_tokens_for_client(client_id, user_id)` scopes the sweep to the member; new `cascade_member_ai_connections` (D5) | D2, D4, D5 |
| `api/mcp_server/oauth_provider.py::_ensure_foreign_llm_grant` | Threads the session `user_id` as `connected_by` on both mint paths | D2 |
| `api/services/primitives/workspace.py::_lookup_grant_scopes` | Consult keys `connected_by = auth.user_id` for external principals (principal_id ≠ user_id); **MEMBER-FIRST, PROVIDER-WIDE FALLBACK** (prefer the member's grant, else the NULL-connected legacy/backfill grant); cache key widened to the 3-tuple. Owner path (connected_by None) byte-identical — single fetch. | D2, §6 |
| `api/routes/workspace.py` | `get_workspace_members` returns `connected_by` + `connected_by_label` (resolves the authorizing member's email / "your connection"); narrow + revoke routes take `connected_by`; revoke fires the D5 cascade | D3, D4, D5 |
| `api/services/principals.py::load_principal_roster` | Selects + returns `connected_by` for the steward envelope's principal-commons fact | D3 |
| `web/lib/api/client.ts` | `getMembers` types `connected_by`/`connected_by_label`; `narrowMember`/`revokeMember` accept + pass `connectedBy` | D3, D4 |
| `web/components/workspace-concepts/WorkspaceMembersCard.tsx` | People / AI-connections partition + per-AI-row kind hint (§3c) + the `connected_by` sub-label ("· connected by {email}"); narrow/revoke thread `connected_by`. Dead `roleGroups`/`roleFilter` props + `MemberRoleGroup` type deleted (ADR-415 D4 removed their caller). `tsc --noEmit` clean. | §3c, D3, D4 |
| `api/test_adr431_connecting_member.py` (new) | 7/7 — multi-member coexistence, member-first consult, scoped revoke (grant + token), D5 cascade, N=1 singleton | D1–D5 |

**Implementation finding (§6 confirmed):** the member-first-then-provider-wide fallback in the consult is load-bearing — without it, a NULL-connected legacy/backfill grant (e.g. an owner's narrow applied without naming the member) would be invisible to a consult that filters by `connected_by`, silently dropping the caller to the class default. The fallback preserves every pre-431 grant's authority while enabling per-member grants.
| `FOUNDATIONS.md` / GLOSSARY / ADR-373 D2.a status banner | Note the relational-unit widening; D2.a's client-churn fix preserved, per-workspace collapse superseded | header |

---

## 8. Open questions

- **OQ1 — a2a / platform `connected_by`.** These classes are still name-only (ADR-386 D6). When an a2a caller first connects, its `connected_by` is the human who authorized the agent — the same rule. No pre-build needed; reserve the column semantics.
- **OQ2 — the same member, two ChatGPT accounts.** If one human connects two distinct ChatGPT accounts to one workspace, `(provider, workspace, connected_by)` collapses them again. Likely fine at launch (a member has one ChatGPT); if it becomes real, the key extends to the OAuth account subject, not the provider host. Deferred — do not pre-build (ADR-401 discipline).
- **OQ3 — cross-workspace AI connection reuse.** A member in two workspaces connecting the same ChatGPT is two grants (one per workspace), which is correct — the AI perceives each commons under a per-workspace grant. Mirrors ADR-425 AD1's account-credential / per-workspace-routing split. No action.
