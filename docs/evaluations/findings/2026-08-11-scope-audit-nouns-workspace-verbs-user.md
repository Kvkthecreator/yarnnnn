# Scope audit — nouns are workspace, verbs are user (2026-08-11)

> **RESOLVED by ADR-548** (same day). Findings 1, 2, 3's misroute and 5 are
> fixed; the doorway gate that would have caught Finding 1 now exists and has
> been falsified. Finding 4's `chat_sessions.workspace_id` nullability is
> deliberately still open — it needs a live data check before a constraint.
> This document is kept as the evaluation record; ADR-548 is the decision.

Hat B (evaluation). Audited at `7a18bd7`, clean tree. Every claim below carries a
file:line receipt; claims I could not verify are marked as such.

**The premise is already canon, and it is already named.** ADR-407 D1 declares
exactly three scopes; FOUNDATIONS DP35 states them verbatim and supplies a
drift checklist. The operator's framing — nouns/commons at workspace level,
chats/real-time at user level — is not a new law to write. It is ADR-407 D1.

So this audit is not "is the model right." It is **"where has the code drifted
from a model that already exists, and why did the gates not catch it."**

---

## The one-line answer

The **verb axis is correct**. The **noun axis is correct at the route layer and
broken at the primitive layer** — one file, eight queries, with the correct
helper sitting unused in the same file.

| Layer | Scope key | Member-aware |
|---|---|---|
| HTTP routes (`api/routes/*`) | `substrate_scope_filter` → `workspace_id` | yes |
| MCP compositions (`mcp_composition.py`) | `_substrate_scope` → `workspace_id` | yes |
| Data layer (`services/workspace.py::_scoped`) | `workspace_id` | yes |
| **Primitives (`primitives/workspace.py`)** | **bare `user_id`** | **NO** |

---

## Finding 1 — the primitive layer is member-blind (P0)

`api/services/primitives/workspace.py` — eight substrate reads key the bare
caller instead of the workspace:

| Line | Table | Function |
|---|---|---|
| **1826** | `workspace_files` | `_list_tree` ← **ListFiles** |
| **1096** | `workspace_files` | `_exact_search` ← **SearchFiles** fallback |
| 1730 | `workspace_files` | `handle_query_knowledge` (no-query listing) |
| 1397 | `workspace_files` | `handle_duplicate_file` |
| 1484 | `workspace_files` | `handle_move_file` |
| 56 | `workspace_files` | `_embed_workspace_file` (metadata-only) |
| 2013 | `agents` | `handle_discover_agents` |
| 2129 | `agents` | `handle_read_agent_file` |

Verified at `workspace.py:1819-1832`:

```python
auth.client.table("workspace_files")
  .select("path, content_bytes, updated_at, "
          "workspace_file_versions!head_version_id(authored_by, created_at)")
  .eq("user_id", auth.user_id)      # ← 1826
```

**The correct helper is in the same file and used once.** `_scope_filter` at
`:620-622` wraps `substrate_scope_filter`; its only call site is `:579`
(`handle_read_file`'s binary probe). So ReadFile is workspace-keyed and
ListFiles is not — *within one module*.

**Half-fixed, which is the tell.** `handle_search_files:1576` and
`handle_query_knowledge:1675` DO resolve `effective_workspace_id` for their
**RPC** branch. Only the table-query fallbacks stayed user-keyed. Someone swept
the RPC path and missed the fallback beside it.

**Symptom shape.** A member searching the commons gets `[]` for every file the
owner authored — HTTP 200, no error, no Sentry event. This is the exact
signature the member-read-path arc already recorded: *Sentry is blind to
incorrect successes.*

**The duplicate that proves it.** `mcp_composition.py:782` (`compose_list`) is a
near-verbatim copy of `_list_tree` — same table, same select, same `.like` /
`.in_` — differing **only** in the scope-filter line. One copy is right.

---

## Finding 2 — the scope gate is RED on main, and blind where it is green

`api/test_adr414_phase_f_dp35.py` — **1 failed, 2 passed at `7a18bd7` on a clean
tree** (pre-existing, not a regression):

```
scope_manifest.yaml declares store(s) with no `.table(...)` reference
(stale — remove or tombstone): ['conversation_messages', 'conversations']
```

Those two tables were dropped by migration 226 (ADR-495). The manifest still
declares them.

**The deeper problem is what the gate cannot see.** It scans for `.table("X")`
string literals in code, so a table that exists in Postgres but is absent from
code is invisible. Verified absent from `scope_manifest.yaml`:

- `integration_sync_config` — **live**, referenced `routes/account.py:610,710`
- `user_admin_flags` — **live**, referenced `routes/account.py:502,665,716`
- `agent_context_log`, `slack_user_cache` — no code references; likely live
  orphan tables in prod carrying `user_id` with no scope declaration

`test_adr373_sweep_spine.py` (12 passed) has the mirror-image blindness: it
proves `substrate_scope_filter` behaves correctly **when called**, and never
checks that substrate readers call it. That is precisely why Finding 1 shipped
green — *the gates test the room, not the doorway.*

---

## Finding 3 — the settings surface

**A dead cross-link (verified).** `scopeParamKey(slug,key)` →
`` `${slug}.${key}` `` (`useSurfacePreferences.tsx:96-98`), and
`SettingsPaneShell.tsx:268` reads `surfaceParam.get("pane")` — the namespaced
key only. Three shipped links use the bare `?pane=`:

- `settings/page.tsx:496` → `/workspace-settings?pane=danger` — **lands on
  Members, not Danger Zone.** The one that actually misroutes.
- `settings/page.tsx:411` (`?pane=members`) and `WorkspaceDangerZone.tsx:215`
  (`?pane=account`) work **by luck** — each names its door's default pane.

The 2026-07-31 settings click-pass (`findings/2026-07-31-settings-surfaces-click-pass.md`)
ran this door live against prod and did **not** catch this: it verified the pane
chrome renders (its line 76 lists Danger Zone among them) but reached the panes
via the sidebar, never via the in-app cross-link. The door was tested; the
doorway to it was not.

**Scope split across the two doors is otherwise sound**, and better than it
looks:

- `/workspace-settings` — Members, Billing, Autonomy, Danger Zone: all
  `workspace_id`.
- `/settings` — Account, Connectors: `user_id`, correct per ADR-425 (a platform
  credential is an account object) and `account_scope_filter`.
- Notification prefs key `(workspace_id, principal_id)` — correct
  member-experience scope, `member_state.py:90`.

**One audit claim I checked and it was wrong.** The Usage pane was reported as
user-scoped under a workspace title. It is not: `get_usage_detail`
(`platform_limits.py:581-600`) resolves `_acting_workspace_id(user_id)` then
queries `.eq("workspace_id", ws_id)`. The `user_id` parameter is a resolution
seed, not the scope key. Usage is correctly workspace-scoped.

**Authority gaps (real, lower severity than they first read).**
`_require_workspace_clear_authority` guards work-history (`account.py:436`) and
clear-workspace (`:539`) but not `/account/reset` or `/account/integrations`.
Mitigating: reset deletes `workspaces` by `owner_id`, so a non-owner cannot
destroy the owner's workspace. The gate also returns early when `workspace_id`
is falsy (`:146-147`).

**Dead/dormant UI.** `SystemAgentPanes.tsx:78-91` exports a pane group whose
`about`/`activity` panes have no mount. `SourcesCard`, `ExpectedOutputCard`,
`MandateCard`, `PrinciplesCard` — retained, no JSX mount. The whole retention
dial is invisible on a default deployment (`ConnectedIntegrationsSection.tsx:386`
gates on `captureEnabled`, which defaults false).

---

## Finding 4 — the verb axis is correct (and better than the docs say)

ADR-495 deleted the private/shared distinction on purpose: **there is no `scope`
column**, verified across all migrations. What survives is a `session_type`
discriminator:

- `session_type='thinking_partner'` (steward rail) — genuinely per-user:
  `feed.py:1384` `.eq("user_id", auth.user_id)`, RLS `ELSE user_id = auth.uid()`.
- `session_type='lane'` (/chat) — **cast-scoped ∩ workspace grant**, not
  user-scoped: `lanes.py:322-342`.

`lane_runner.py:1-30` states the doctrine exactly as the operator did: *"lanes
are isolated conversations; the workspace is the shared memory."* Transcripts
are per-lane; the durable output lands in workspace-scoped files.

**Structural weak point.** `chat_sessions.workspace_id` is **nullable**
(`migration 203:20-21`, never `SET NOT NULL`), while both the RLS policy
(`236:71`) and the app guard (`lanes.py:256` `if ws and ...`) treat NULL as
"skip the workspace check" — two conditional bypasses stacked. Its child
`conversation_members.workspace_id` DID get `SET NOT NULL` (migration 228); the
parent never did.

**Stale doc.** `ChatSurface.tsx:31-32` says `GET /api/lanes` returns "only the
viewer's lanes" — pre-ADR-495 wording; it is now cast-scoped.

---

## Finding 5 — wrong helper, opposite direction

`api/services/bundle_reader.py:239` (the launcher's app list) calls
`.eq(*substrate_scope_filter(user_id))` on `platform_connections` — a table
`workspace_context.py:88-91` **explicitly excludes** ("use
`account_scope_filter`", ADR-425). `routes/workspace.py:2979` keys the same
table on `user_id`. So the launcher's program surfaces and the workspace-state
cockpit disagree about what a connector belongs to.

---

## What I did NOT verify

- Nothing was run against prod or the live DB. DB-backed pytests 401 in this
  shell; only static gates are meaningful here.
- The 5 suspected orphan tables are inferred from migrations + absence of code
  references, not from introspecting Postgres.
- No click-pass. The `?pane=danger` misroute is read off the code path and
  deserves a browser confirmation.

---

## Recommended order

1. **Finding 1** — route the 8 primitive queries through `_scope_filter`. Small,
   mechanical, closes a silent member-facing data-loss class.
2. **A gate that greps the doorway** — assert no `.eq("user_id"` on a
   workspace-content table outside the declared fallback helpers. Finding 1
   shipped past 12 green gates; without this it regresses.
3. **Finding 2's red** — tombstone or remove the two phantom manifest rows;
   declare `integration_sync_config` + `user_admin_flags`.
4. **Finding 3's misroute** — one-line fix to the namespaced param.
5. **Finding 5** — one-line helper swap.
6. **`chat_sessions.workspace_id SET NOT NULL`** — needs a data check first.

Each is independently shippable. None requires a new ADR: every one restores a
law that ADR-407 / ADR-373 / ADR-425 already wrote.
