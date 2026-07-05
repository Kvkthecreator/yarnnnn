# ADR-407: The Three-Scope Taxonomy — workspace content, member experience, account

**Status**: Proposed (2026-07-05) — doc-first; implementation phased (§8), each phase its own commit + gate
**Date**: 2026-07-05
**Dimension**: Substrate (Axiom 1, what persists and under which key) + Identity (Axiom 2, whose state it is) + Channel (Axiom 6, whose surface renders it)
**Relates to**: ADR-373 (multi-principal re-key — this ADR completes its read/enforcement half), ADR-378 (workspace as outermost unit), ADR-391 (three-layer cost model — D1's workspace balance gets its enforcement here), ADR-396 (pricing over the metered balance), ADR-404 (commons-first launch — the remainder list this ADR structures), ADR-405 (witness dial — D5's "presentation layer" gets a home), ADR-406 (stale-parent rejection — the FE wiring lands here), ADR-222 (OS framing — one shell becomes N shells)
**Amends**: ADR-373 (the re-key extends from the substrate spine to the full shared-content set), ADR-391 (balance enforcement re-keyed workspace-side), ADR-405 (per-member routing/preferences get a designed surface instead of being defined away), FOUNDATIONS DP17 (embodiment clause generalizes to N humans — cascade on ratification, candidate DP35)
**Derivation**: `docs/analysis/multi-user-workspace-scope-audit-2026-07-05.md`

---

## 1. Context — the re-key stopped one layer short

ADR-373 moved the substrate's binding unit from `user_id` to `workspace_id`,
and ADR-404 shipped the sweep spine + member invites. The audit
(see Derivation) shows what that arc actually generalized: **substrate binding**
(two tables), **authorization** (grants, fail-closed resolution), and **write
attribution** (`authored_by`, `principal_id`). It did not generalize:

1. **The operational read layer.** Every route and RPC outside the substrate
   core still scopes `eq("user_id", auth.user_id)` — zero `p_workspace_id`
   RPCs exist. A member can co-edit the shared files but sees empty rows on
   agents, recurrences, documents, proposals, emissions, chat, and account
   surfaces; wakes and recurrences run keyed to the owner; the balance gate
   resolves by `owner_id` so a member self-gates to $0 while their spend never
   debits the shared balance.
2. **The member-experience layer.** No state anywhere is keyed
   `(workspace_id, principal_id)`. Read cursors, shell/window state,
   notification addressing, and per-member preferences either live in
   localStorage (device-local, sometimes not even user-keyed) or don't exist.
   ADR-405 D5 correctly ruled these out of the *authorization* layer — but
   assigned them to a "presentation layer" that was never designed.

The root cause is not a missed sweep item; it is a **missing classification**.
The system has never named, as canon, which scope each piece of state belongs
to. Slack and Notion draw this line explicitly: the workspace owns the content;
each member owns their experience of it. YARNNN's canon still encodes the
singular operator at the axiom layer (FOUNDATIONS DP17: "one principal with two
runtime embodiments") and one shell over one userspace (ADR-222). ADR-391 §37
already admitted the model is "a frozen snapshot of N=1"; only the cost
architecture was un-frozen.

## 2. Decision — three scopes, declared for every store

**D1 — Every persistent store declares exactly one scope.** The three scopes:

- **Workspace content** — the shared commons. One copy per workspace; every
  principal with a grant reads the same rows; writes are attributed
  (ADR-209/373). Keyed by `workspace_id`.
- **Member experience** — one principal's first-person state *within* a
  workspace: sessions, read cursors, shell/window layout, notification
  addressing + delivery preferences, drafts. Keyed by
  `(workspace_id, principal_id)`. Never consulted for authorization
  (ADR-405 D5 preserved); losing it must never lose work.
- **Account** — the human independent of any workspace: auth identity, email,
  OAuth artifacts, cross-workspace subscription facts if any. Keyed by
  `user_id` / `principal_id` alone.

A store that cannot be classified is a design smell to resolve, not a fourth
category. New tables/state stores state their scope at introduction; the
classification table (§3) is the living registry.

**D2 — The interaction model is named: macOS, not Figma.** The product is N
first-person shells over one shared filesystem. Freshness is pull (polling /
on-focus refetch); conflict is surfaced at save via ADR-406's CAS (the FE must
pass `expected_head_version_id` and render the 409 with the intervening
principal's attribution); the only push channels are those where a shared live
stream genuinely exists (chat realtime today; after-witness emission later).
Continuous cross-client sync of views is explicitly a non-goal. This amends
ADR-222's shell mapping: the workspace has one filesystem and N shells; the
shell instance is member-experience scope, the compositor's inputs (SURFACES
overlay, program declaration) remain workspace scope.

**D3 — Workspace-content stragglers re-key to `workspace_id`.**
`execution_events` (add column + rollup index), `action_proposals`, `tasks`,
`agents`/`agent_runs`, `activity_log`, `wake_queue` (dedup becomes
`(workspace_id, wake_source, dedup_key)`), `token_usage` (or fold into the one
ledger per ADR-396's double-charge invariant), the emissions/delivery logs, and
the read layer over all of them (routes + the `p_user_id` RPC set, including
`search_workspace`/`match_workspace_files`/`search_workspace_semantic`).
`user_id` columns remain as attribution vestige where already present; the
scoping key is the workspace. Wake/recurrence execution runs *for the
workspace* (the audit found `wake.py` documenting `user_id` as "Workspace owner
UUID" — that comment becomes the code).

**D4 — The balance gate re-keys to the workspace (ADR-391 D1, enforced).**
`get_effective_balance` takes `p_workspace_id`; spend sums over
`execution_events.workspace_id`; every principal's metered judgment call draws
the one shared balance and hard-stops on the same zero (ADR-396 unchanged —
one meter, one ledger, one pool). Per-principal *allocation* (`_budget.yaml`
per principal, ADR-391 Layer ②) remains demand-gated; this ADR only fixes the
gate's key.

**D5 — Connections are workspace peripherals; credentials stay personal.**
`platform_connections` splits semantically: the *connection* (the peripheral
the workspace perceives through, ADR-401) is workspace content; the *OAuth
credential* inside it belongs to the member who granted it (account scope).
One table can carry both (`workspace_id` scoping + `connected_by` principal
attribution); disconnecting a departing member's credential kills the
peripheral visibly rather than silently (ADR-401 D3 teardown applies).

**D6 — Chat: per-member threads, workspace narrative.** `chat_sessions`
gains `workspace_id` and becomes member-experience scope: each principal's
conversation with the system agent is their own thread within the workspace
(the DM-with-the-assistant shape), keyed `(workspace_id, principal_id)`. The
*shared* timeline — the workspace Flow — is **derived from the attributed
ledgers** (`workspace_file_versions`, `execution_events`, emissions), per
DP29 and ADR-405 D3, not from any chat session. Freddie's autonomous narrative
therefore stops landing in the owner's private session
(`find_active_workspace_session` retires); autonomous invocations are already
in the ledgers, and addressed responses land in the addressing member's
thread. This resolves the audit's sharpest conflation (one "Flow" surface
backed by per-user substrate) without inventing a second narrative store.

**D7 — The member-experience home.** A new store keyed
`(workspace_id, principal_id)` — `member_state` — carrying: shell/window/dock
state (replacing the localStorage-only persistence; localStorage remains the
write-through cache), the attention read cursor, notification
addressing/delivery preferences (generalizing `user_notification_preferences`),
and future drafts. Explicitly **not substrate** (not `workspace_files` — it is
presentation state, not authored content; precedent: `wake_queue` as
non-authoritative compute, ADR-298). RLS: a principal reads/writes only their
own rows. The invite-accept `clearShellState` symptom-patch retires — window
state keyed per-(workspace, principal) makes it unnecessary — and the same
change gives cross-device shell continuity and per-workspace desktops.

**D8 — After-witness emission becomes real (ADR-405 D5, operationalized).**
Who is told = principals with an active grant whose scopes cover the acted-on
region, minus the actor (self-witness trivial, ADR-405 D4). The derivation
runs over the attributed ledgers at emission time (derived-never-stored);
`notifications` remains the transport record, now addressed per recipient
principal. Witness *queue* visibility follows the same rule: `action_proposals`
re-keys to workspace (D3) and any principal whose grant covers the proposal's
region may witness/approve; the approval records the approving principal.
Mute/digest live in `member_state` (D7) — presentation, never authorization.

**D9 — Workspace binding becomes first-class in the client.** The active
workspace moves from a raw un-keyed localStorage value to explicit,
user-keyed state with a minimal switcher (owner workspace + granted
workspaces); `X-Workspace-Id` continues as the transport. A member is expected
to hold both their own singleton and N granted commons (ADR-378 — workspaces
unrelated, no federation).

**D10 — FOUNDATIONS cascade (on ratification).** DP17's "one principal with
two runtime embodiments" generalizes: *the workspace has N accountable human
principals; each is one principal with two runtime embodiments (cockpit,
external LLM); the owner remains the constitutional author* (governance
authorship unchanged — ADR-386 D4 owner-immutability stands). The taxonomy
itself lands as candidate **DP35** (DP34 is reserved by ADR-395):
*every persistent store declares workspace-content, member-experience, or
account scope; member-experience state is never consulted for authorization
and never holds authored content.* ADR-222's shell row updates per D2.

## 3. The scope registry (initial classification)

| Store | Scope | Key (target) | Change |
|---|---|---|---|
| `workspace_files`, `workspace_file_versions`, `workspace_blobs` | content | workspace_id | done (ADR-373) |
| `principal_grants`, `workspace_invites` | content (authz) | workspace_id | done |
| `workspaces` (balance, tier) | content (billing root) | workspace_id | done; gate re-key = D4 |
| `execution_events`, `token_usage` | content (ledger) | + workspace_id | D3/D4 |
| `action_proposals` | content (witness queue) | + workspace_id | D3/D8 |
| `tasks`, `agents`, `agent_runs`, `activity_log`, `wake_queue` | content | + workspace_id | D3 |
| `platform_connections`, `sync_registry` | content (peripheral) + account (credential) | + workspace_id, `connected_by` | D5 |
| `chat_sessions`, `session_messages` | member experience | (workspace_id, principal_id) | D6 |
| `notifications` | member experience (transport) | recipient principal | D8 |
| `user_notification_preferences` | member experience | (workspace_id, principal_id) | fold into D7 |
| `member_state` (new) | member experience | (workspace_id, principal_id) | D7 |
| shell/window localStorage | member experience (cache of D7) | (workspace, principal) key | D7 |
| `auth.users`, `mcp_oauth_*` | account | user/principal | none |
| `_budget.yaml`, `_autonomy.yaml`, governance/persona files | content (constitution) | workspace filesystem | none (owner-authored, ADR-386 D4) |
| MCP recall/wake scoping (`mcp_composition.py`) | content reads | workspace via contextvar | D3 (closes the live Phase-3 TODO) |

## 4. What this ADR does NOT do

- No merge/CRDT/presence/live cursors — ADR-373's rejection stands; D2 names
  the model that makes them unnecessary. Presence-style features remain
  demand-gated.
- No change to governance authorship — the owner authors the constitution;
  members are locked out of `governance/ constitution/ persona/` by class
  default (ADR-373 D3). Co-ownership/transfer remains out of scope.
- No per-principal budget allocation (ADR-391 Layer ② stays demand-gated).
- No pricing change — ADR-396 stands; the commons-scale gate question stays
  where ADR-404 left it (re-cut at invites-scale, separate amendment).
- No federation — ADR-378's ceiling stands.

## 5. Alternatives considered

- **Shared chat channel (one session per workspace)** instead of D6: rejected —
  it turns N members' addressed turns into one interleaved thread the system
  agent must disambiguate, and it contradicts the ledgers-as-timeline canon
  (DP29/ADR-405 D3) by making a chat table the shared narrative's source of
  truth. The DM shape + derived Flow keeps one source of truth for "what
  happened" and gives each member a private working line to the agent.
- **Member-experience state as workspace files** (e.g. `/members/{id}/…`):
  rejected — it would put presentation state through the authored-substrate
  write path (attribution ceremony for a read cursor), pollute the commons'
  `ls`, and re-open the permission story ADR-405 D5 closed.
- **Sweep without the taxonomy** (just fix the named remainders): rejected —
  that is how the current state arose; without the classification each new
  table re-poses the question and the conflation regenerates.

## 6. Consequences

A second member becomes functionally real: same files (already true), same
agents/recurrences/proposals/activity, witnessing what their grant covers,
notified after-witness, drawing the shared balance, with their own thread,
desktop, and read cursor that follow them across devices. The N=1 case stays
byte-identical at every phase (the ADR-373 discipline). The known correctness
holes (member self-gates to $0; member deaf; member sees empty surfaces;
silent last-writer-wins) close in severity order.

## 7. Test discipline

Each phase ships a regression gate in the ADR-373 style
(`api/test_adr407_phaseN_*.py`): N=1 byte-identity proofs + member-visibility
probes (member sees workspace rows; member draws workspace balance; member
receives after-witness; member's thread is theirs; owner's is not).

## 8. Phases (each its own commit; sequence = severity order)

- **Phase 0 — the money gate** (bug-grade): `execution_events.workspace_id` +
  backfill; `get_effective_balance(p_workspace_id)`; `platform_limits` call
  sites. (D4)
- **Phase 1 — the read-layer sweep**: re-key routes + RPCs over the D3 set;
  wake/recurrence execution keyed to workspace; MCP recall TODO closed. (D3)
- **Phase 2 — the witness surface**: `action_proposals` re-key + standing-based
  visibility/approval; after-witness emission + per-recipient notifications.
  (D8)
- **Phase 3 — the member-experience home**: `member_state` table + shell-state
  write-through + read cursor + notification prefs; retire `clearShellState`.
  (D7)
- **Phase 4 — chat re-shape**: `chat_sessions` → (workspace, principal);
  Flow derives from ledgers; retire `find_active_workspace_session`. (D6)
- **Phase 5 — binding UX**: workspace switcher + user-keyed active-workspace
  state; FE 409 wiring on editors. (D2/D9)
- **Cascade (doc-only, on ratification)**: FOUNDATIONS DP17 amendment + DP35 +
  ADR-222 shell row + GLOSSARY entries (scope, member experience, member state).
  (D10)
