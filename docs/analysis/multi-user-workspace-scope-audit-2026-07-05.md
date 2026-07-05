# Multi-User Workspace Scope Audit — shared data vs member experience (2026-07-05)

**Status**: Findings document (Hat-B evaluation of Hat-A state). Feeds ADR-407.
**Method**: Five parallel codebase sweeps (schema/migrations, backend routes+services,
frontend state, concept semantics, canon intent), synthesized against the
Slack/Notion reference model: *workspace-shared content* vs *per-member
experience* vs *account-personal*.
**Question**: after the ADR-373→406 multi-principal arc, is the distinction
between shared workspace data and individual user experience actually
represented in the architecture?

**Answer**: No — not as a design axis. The arc re-keyed exactly three things
(substrate binding, authorization, write attribution) and left two whole layers
at the N=1 identity: the **operational read layer** (shared data still
user-keyed) and the **member-experience layer** (no home at all). Parts are
known-deferred (named remainders); the experience layer specifically is an
unrecognized blind spot — canon partly defines it away (ADR-405 D5) and the
axiom layer still encodes a singular operator (FOUNDATIONS DP17).

---

## 1. What the re-key actually touched

Migration `189_adr373_multi_principal_rekey.sql` added `workspace_id` to
exactly **two** tables: `workspace_files` and `workspace_file_versions`
(UNIQUE(workspace_id, path) live in 198; legacy UNIQUE(user_id, path) dropped
in 199). Plus the authorization tables (`principal_grants`, `workspace_invites`)
and the pre-existing `workspaces` row as billing root. Grep-verified: **no
other table has a `workspace_id` column.** Migration 192 added
`execution_events.principal_id` (attribution) — but not `workspace_id`.

What works correctly today:

- **Resolution spine** — JWT → `X-Workspace-Id` → validated fail-closed against
  `principal_grants` (403 on no grant) → contextvar sweep
  (`services/supabase.py:161`, `services/workspace_context.py`). Correct and
  member-aware.
- **Substrate core** — `authored_substrate.py` + `services/workspace.py`
  (`_scoped()`/`_substrate_scope`) genuinely workspace-keyed; a member reads and
  writes shared files/memory/revisions with enforced per-principal attribution.
- **Invite accept** — joins (grant into existing workspace), does not scaffold a
  duplicate workspace (`workspace_invites.py::accept_invite`).
- **ADR-406 CAS** — the right conflict primitive for the intended
  open/edit/save model (though FE never wires the 409 — §5.6).

## 2. Table inventory (keying vs semantic class)

| Table | Keys today | Semantic class | Verdict |
|---|---|---|---|
| `workspaces` | owner_id; holds balance/tier/allowance | billing root | correct (ADR-391/396) |
| `principal_grants` / `workspace_invites` | principal_id + workspace_id | authorization | correct |
| `workspace_files` / `workspace_file_versions` | workspace_id (+ user_id vestige) | shared substrate | correct (re-keyed) |
| `workspace_blobs` | sha256 (global CAS) | shared content | correct |
| `balance_transactions` | workspace_id | billing | correct |
| `execution_events` | user_id (+ principal_id) | shared cost/exec ledger | **MISMATCH** — no workspace_id to roll up by |
| `token_usage` | user_id | spend ledger | **MISMATCH** |
| `wake_queue` | user_id (dedup UNIQUE(user_id,…)) | shared exec infra | **MISMATCH** |
| `action_proposals` | user_id | shared witness queue | **MISMATCH** |
| `agents` / `agent_runs` | user_id (transitive) | shared actors/content | **MISMATCH** |
| `tasks` (scheduling index) | user_id; UNIQUE(user_id, slug) | shared recurrences | **MISMATCH** |
| `activity_log` | user_id | shared audit | **MISMATCH** |
| `platform_connections` / `sync_registry` | user_id | shared connector vs personal credential | **AMBIGUOUS** — needs an explicit call |
| `chat_sessions` / `session_messages` | user_id (via session) | conflated (see §5.2) | needs a product decision |
| `notifications` | user_id | per-member delivery (correct class) | addressing broken for members (§5.4) |
| `user_notification_preferences` | user_id | member preference | correct class; should generalize to (workspace, principal) |
| `mcp_oauth_*` | user_id + client_id | auth artifacts | correct |

**RPC layer**: ~14 `p_user_id` RPCs (`get_effective_balance`,
`search_workspace`/`match_workspace_files`, `search_workspace_semantic`,
`get_or_create_chat_session`, `get_effective_profile`, monthly-usage set, …).
**Zero `p_workspace_id` RPCs exist.** Even where RLS on the substrate tables
permits workspace reads, the query layer still shows a member only their own
rows.

**Per-member-within-workspace state**: no table keyed
`(workspace_id, principal_id)` exists anywhere. Read cursors, per-member
preferences, per-member shell state have **no home**.

## 3. Backend route/service scoping

Workspace-keyed: `routes/workspace.py` (mostly), `authored_substrate.py`,
`services/workspace.py`, grant/invite machinery.

Still user_id-keyed (a member sees their own empty rows, or the wrong scope):
`routes/{account,agents,integrations,recurrences,documents,sources,proposals,
emissions,authored,narrative,feed}.py`; `services/{budget,notifications,
working_memory,wake,wake_queue,recurrence,platform_limits,telemetry}.py`.
The wake path takes `user_id` documented as "Workspace owner UUID"
(`wake.py:145`). MCP recall reads are user-scoped with a live
`TODO(shared-workspace / Phase 3)` (`mcp_composition.py:1160-1175`) —
"accidentally correct" only because foreign LLMs authenticate as the owner.

## 4. Frontend state inventory

| State | Persistence | Effective scope |
|---|---|---|
| Dock kept / open windows / foreground / geometry | localStorage `…:<userId>` | per-user, per-browser, **workspace-blind** (`surface-preferences.ts:33-36`) |
| Active workspace binding | localStorage `yarnnn.active-workspace` | per-browser, **not user-keyed** (`client.ts:128`) |
| Chat drawer open/width, layout mode, files/recents view mode | localStorage, un-keyed | **browser-global** |
| Attention "last seen" read cursor | localStorage `yarnnn:attention:last-seen` | **browser-global — not even per-user** (`AttentionCenter.tsx:56`) |
| Any backend-persisted preference | — | **does not exist** (deferred in `surface-preferences.ts:18-21`) |

`clearShellState` on invite-accept (ADR-404 step 5, commit `b3b1aca`) is the
symptom-patch for window state being per-user instead of per-(user, workspace) —
the code comment names per-(user, workspace) keying as the "durable follow-on."
There is **no workspace switcher**; `setActiveWorkspace` has exactly one caller
(invite-accept). Same user on two devices = two divergent desktops (no backend
persistence).

Freshness model: 30–60s polling + one Supabase Realtime channel
(`session_messages` inserts). No React Query. ADR-406's
`expected_head_version_id`/409 is plumbed in the API client
(`client.ts:1348-1373`) but **no editor passes it and no component handles a
409** — member B's save silently stales member A's open window
(last-writer-wins, unsurfaced).

## 5. Ranked findings

**5.1 Money gate is owner-keyed while balance storage is workspace-keyed
(correctness break).** `balance_usd`/`allowance_usd` live on `workspaces`
(correct per ADR-391/396), but `get_effective_balance(p_user_id)` (migration
194) resolves `WHERE owner_id = p_user_id` and sums spend
`WHERE ee.user_id = p_user_id`. A member resolves no workspace → $0 →
hard-stopped; their spend never debits the shared balance. `execution_events`
has `principal_id` but no `workspace_id`.

**5.2 Chat/narrative is per-user substrate presented as the shared workspace
Flow.** `chat_sessions.user_id`; each member gets a private thread;
`find_active_workspace_session` resolves by user_id despite its name
(`narrative.py:297,317`) so Freddie's autonomous narrative lands only in the
owner's session. Under N>1: N+1 disjoint narratives, no shared timeline.
Needs an explicit decision (shared channel vs per-member thread + derived
workspace Flow).

**5.3 Witness queue invisible to members.** `action_proposals` is user-keyed
(`routes/proposals.py:149,186`); a member cannot see or approve the
owner's/Freddie's proposals — contradicting ADR-405 D5's own claim that
grant-holders with standing witness acts on their regions.

**5.4 Members receive nothing.** Notifications, narrative landings, daily
P&L, and all operator-addressed email resolve to one user_id (the owner)
(`notifications.py:66,104`; ADR-299 D6 pin). No after-witness emission code
exists (grep: nothing). A member co-editing the commons is structurally deaf.

**5.5 Operational read surfaces show a member their own empty rows** (§3).

**5.6 The member-experience layer is browser-local accident, not
architecture** (§4). Plus the unwired 409.

## 6. Canon assessment

- ADR-391 §37 is the canon's own admission: the model is "a frozen snapshot of
  N=1" — only the cost *architecture* was un-frozen, not the enforcement.
- ADR-405 D5 defines per-member routing/preferences away ("derived, not
  configured"; mute/digest are "presentation-layer… never authorization-layer")
  with **no surface designed to hold that presentation layer**.
- FOUNDATIONS DP17 still encodes "the operator is one principal with two
  runtime embodiments" — never amended to N humans by the ADR-373→406 arc.
- ADR-222's OS mapping has ONE shell, ONE userspace, ONE operator overlay — the
  metaphor was never extended to N shells over one filesystem, which is exactly
  what the intended macOS-style interaction model requires.
- Presence/activity-of-others/collaboration-feed were *explicitly deferred*
  ("wait for demonstrated multi-human demand") — those are planned deferrals,
  not blind spots. The blind spot is narrower and deeper: **no doc anywhere
  names read-state / sessions / per-member routing / per-member preferences as
  a coherent design object.**

## 7. Interaction-model note (macOS, not Figma)

The intended model — shared filesystem, first-person per-user sessions,
open/edit/save, conflict-on-save — is the *cheap* model and the bones already
lean toward it: polling freshness is fine, CAS (ADR-406) is the right conflict
primitive, realtime is only needed where a shared live channel genuinely exists
(chat). What the model requires and the system lacks is precisely the
middle-scope taxonomy: N per-user shells (per-(workspace, principal) session
state) over one shared, workspace-keyed data plane — plus wiring the 409 so
"save over someone's change" is surfaced instead of silent.

## 8. Disposition

Resolved by **ADR-407** (the three-scope taxonomy + phased re-key). The
migration burden is wide but mostly mechanical (add `workspace_id` +
re-key reads/RPCs); the genuinely new build is the member-experience home and
the chat/narrative decision. The substrate spine — the schema-risky part — is
already done.
