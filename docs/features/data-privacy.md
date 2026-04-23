# Data & Privacy — Purge Layering & Workspace Reinit

> **Surface**: Settings → Account tab ("Data & Privacy" section)
> **Status**: Layered model fully shipped. All five layers (L1–L5) live in production. Post-flip streamline pass landed 2026-04-24 — purge coverage now matches the post-ADR-194/205/206/207/209 schema. The purge thread is closed.
> **History**: This doc lived at `docs/design/PURGE-LAYERING.md` through Phases 1–3 and was moved to `docs/features/data-privacy.md` in Phase 4 (2026-04-09) — it belongs with user-facing feature docs, not architectural design notes, now that the design is stable and shipped. It also supersedes the stale archived `docs/features/previous_versions/data-privacy.md` (deleted in the same commit).
>
> **Phase 1** (commit 16c7f0e, 2026-04-08): Transactional reinit on L2/L4 + ADR-158 platform context cleanup + OAuth bot reactivation. Fixed the latent correctness bug where post-purge workspace state depended on a lazy `/onboarding-state` race window.
>
> **Phase 2** (commit 86a1026, 2026-04-08): Post-purge `/work` routing (ADR-167 list mode) + layered model design memo.
>
> **Phase 3** (commit f3068a3, 2026-04-08): L1 endpoint shipped — `DELETE /account/work-history` with the "Clear Work History" Settings card. Reassessment after Phase 2 found that all three "blockers" the memo claimed for L1 were already resolved: (1) the per-user, per-path `workspace_files` purge primitive already exists in `back_office/workspace_cleanup.py`, (2) the `agent_runs → task_runs` rename has no commit timeline so L1 references the table as it exists today, (3) ADR-164 already removed task-lifecycle events from `activity_log` so L1 has nothing to delete there.
>
> **Phase 4** (commit f90f3b4 lineage, 2026-04-09): Doc move only. No code changes. `docs/design/PURGE-LAYERING.md` → `docs/features/data-privacy.md`; stale archived `docs/features/previous_versions/data-privacy.md` deleted (superseded by this doc); inbound references in `account.py` and `client.ts` updated to the new path.
>
> **Phase 5** (this commit, 2026-04-24): **Post-flip streamline pass.** Several ADR waves landed since Phase 4 — ADR-194 (Reviewer + `action_proposals`), ADR-205 (workspace scaffold collapse to YARNNN-only), ADR-206 (`_shared/` relocation), ADR-207 P4a (Platform Bots dissolve into capability bundles — no agent rows), ADR-209 (Authored Substrate `workspace_file_versions`). None of the new tables were in the purge paths. Streamline adds `workspace_file_versions` + `action_proposals` + `user_admin_flags` + `token_usage` to the right layers; deletes dead references (`work_credits`, `project_resources`, `agent_proposals`, `agent_context_log`, `user_interaction_patterns`, `trigger_event_log`, `user_platform_styles`, `slack_user_cache`, `action_outcomes`, `render_usage`, `filesystem_chunks.user_id`); adds `action_proposals` count to `DangerZoneStats`; rewrites the confirmation copy on the L2 card. Harness script `api/scripts/purge_user_data.py` receives the same pass (no functional shim — singular implementation, one canonical table set across prod routes + harness).
>
> **Related ADRs**: ADR-194 (Reviewer + `action_proposals`), ADR-205 (scaffold collapse), ADR-206 (`_shared/`), ADR-207 (Platform Bots as capabilities), ADR-209 (Authored Substrate), ADR-161 (daily-update anchor), ADR-164 (back office tasks), ADR-166 (output_kind taxonomy — the axis L1 slices on), ADR-167 (list/detail surfaces — `/work` is a meaningful post-purge landing). Historical: ADR-140 (original roster — superseded by ADR-205), ADR-151/152 (directory registry), ADR-153 (platform_content sunset), ADR-158 (platform bot ownership — superseded by ADR-207 P4a).

## The problem this memo exists to preserve

Before 2026-04-08, the purge endpoints in `api/routes/account.py` only deleted data. Workspace re-scaffolding happened **accidentally** via lazy init in `/user/onboarding-state` (in `api/routes/memory.py`) — whenever the next page load happened to hit that endpoint, `initialize_workspace()` would re-run because `has_agents == False`.

After Phases 1–4 (ADR-161 → ADR-164) this accidental path became a latent correctness bug. "Initialized workspace" now means more than agents + seed files; it also means the three essential tasks exist (`daily-update`, `back-office-agent-hygiene`, `back-office-workspace-cleanup`). A workspace without them is not dormant — it's broken. The daily-update heartbeat fires only if the task row exists, and a purge-then-wait window could silently miss a scheduled fire.

## What shipped in Phase 1 (2026-04-08)

Three narrow fixes. Singular implementation, no dual paths:

1. **Transactional reinit on `clear_workspace` and `full_account_reset`.**
   Both endpoints call `initialize_workspace()` synchronously at the end of the purge. Reinit failures are logged but don't fail the request — the `/user/onboarding-state` lazy path remains as a secondary safety net only.

2. **`clear_integrations` rewritten per ADR-158.**
   - Deletes `/workspace/context/{slack,notion,github}/` instead of the dead `/knowledge/` path (sunset by ADR-153).
   - **Pauses** platform-bot agents (`slack_bot`, `notion_bot`, `github_bot`) instead of orphaning or deleting them, preserving the ADR-140 roster invariant.
   - Does NOT touch: domain-steward agents, canonical context domains, IDENTITY/BRAND/AWARENESS, or the three essential tasks (they are platform-agnostic and TP-owned).

3. **OAuth reconnect reactivates paused bots.**
   `api/routes/integrations.py` OAuth callback now flips `slack_bot`/`notion_bot`/`github_bot` from `status='paused'` to `status='active'` after a successful connection upsert. Without this fix, a `clear_integrations → reconnect` cycle would leave bots permanently paused.

4. **`DangerZoneStats` field cleanup.**
   `platform_content` (a dropped table, ADR-153) → `platform_context_files` (a real count from `/workspace/context/{slack,notion,github}/` prefixes). Frontend types + settings page UI + confirmation copy all updated in the same commit.

## Post-flip purge architecture (current, 2026-04-24)

ADRs 194 / 205 / 207 / 209 moved the invariants. The table rows below reflect
the **current** post-LAYER-MAPPING-flip world. If you arrived via an older
commit or an older doc, the key shifts are:

- **Workforce at signup collapsed from 9 agents to 1** (ADR-205: YARNNN only).
  Specialists lazy-create on dispatch; Platform Bots dissolved to capability
  bundles bound to `platform_connections`, not agent rows (ADR-207 P4a).
- **Reviewer substrate at `/workspace/review/`** is scaffolded at signup too —
  seven files per ADR-194 v2, substrate-first (no table, filesystem is the
  authority).
- **Workspace context moved to `/workspace/context/_shared/`** (ADR-206):
  IDENTITY.md / BRAND.md / CONVENTIONS.md no longer at workspace root.
- **Authored Substrate** (ADR-209): every content-layer write produces a
  `workspace_file_versions` revision. Purges must wipe the revision chain
  before the files (no FK cascade).
- **Reviewer proposal queue** (ADR-194): `action_proposals` table must wipe
  on L2 / L4 — prior proposals must not survive a workspace reset.

## What the 4 purge actions now guarantee

| Action | Purges | Reinit | Preserves |
|---|---|---|---|
| **Clear Work History (L1)** | `agent_runs` · `/tasks/%/outputs/%` files · `/tasks/%/memory/_run_log.md` | None — invariants untouched | Tasks, agents, identity, accumulated context, chat, integrations |
| **Clear Workspace (L2)** | `workspace_file_versions` + `workspace_files`, agents, tasks, chat, activity, `action_proposals`, event_trigger_log, filesystem_documents, notifications, MCP OAuth | Full `initialize_workspace()`: YARNNN + Reviewer substrate + `_shared/` context + essential tasks | `platform_connections` (user doesn't re-OAuth) · `user_admin_flags` · `user_notification_preferences` · `token_usage` billing ledger |
| **Disconnect Platforms (L3)** | sync state, `/workspace/context/{slack,notion,github}/` (files **and** revisions), `platform_connections`, `export_log` | None (platform bots are not rows — reconnecting re-enables capabilities automatically) | YARNNN, specialists, user Agents, canonical context domains, `_shared/`, all tasks |
| **Full Data Reset (L4)** | Everything user-scoped + `workspaces` row + MCP OAuth + `token_usage` + `user_admin_flags` + `user_notification_preferences` | Recreates `workspaces` row, then full `initialize_workspace()` | Nothing (auth user only) |
| **Deactivate (L5)** | `workspace_file_versions` + `workspace_files` + MCP OAuth pre-wipe, then auth user delete cascades the rest | N/A (account gone) | Nothing |

### Invariants that hold post-purge

For `clear_workspace (L2)` / `full_account_reset (L4)`, the endpoint returns only when all of these are true:

- Exactly **1 agent row** exists: YARNNN (`role='thinking_partner'`, `origin='system_bootstrap'`, per ADR-205). Specialists are not rows at signup; they lazy-create on first dispatch.
- Reviewer substrate exists at `/workspace/review/` (seven canonical files per ADR-194 v2 workspace_init Phase 4: IDENTITY.md, OCCUPANT.md, principles.md, modes.md, decisions.md, handoffs.md, calibration.md).
- `_shared/` skeleton exists at `/workspace/context/_shared/` (IDENTITY.md, BRAND.md, CONVENTIONS.md, MANDATE.md — ADR-206 + ADR-207).
- Essential tasks exist: `daily-update` (ADR-161) + `back-office-agent-hygiene` + `back-office-workspace-cleanup` + `back-office-outcome-reconciliation` (ADR-164 + ADR-195 v2).

For `clear_integrations (L3)`:

- YARNNN + specialists + user-authored Agents all still exist.
- `_shared/` untouched.
- Canonical context domains (non-platform) untouched.
- Essential tasks untouched.
- Platform Bots were never agent rows — they're capability bundles gated by active `platform_connections` per ADR-207 P4a. Reconnecting restores the capability automatically.

## The layered purge model — fully shipped (L1–L5)

### Layer taxonomy

| Layer | Endpoint | Purges | Preserves | Reinit |
|---|---|---|---|---|
| **L1** | `DELETE /account/work-history` | All `agent_runs` rows · all `/tasks/%/outputs/%` files · all `/tasks/%/memory/_run_log.md` files | Tasks, agents, identity, accumulated context, chat sessions, platform connections, all per-task learning files (steering, feedback, reflections) | None — invariants untouched |
| **L2** | `DELETE /account/workspace` | `workspace_file_versions` + `workspace_files` · agents · tasks · chat sessions · activity log · `action_proposals` · event_trigger_log · filesystem_documents · notifications · MCP OAuth | `platform_connections` · `user_admin_flags` · `user_notification_preferences` · `token_usage` | Full `initialize_workspace()`: YARNNN agent + Reviewer substrate + `_shared/` + essential tasks |
| **L3** | `DELETE /account/integrations` | `/workspace/context/{slack,notion,github}/` (files **and** `workspace_file_versions` under those paths) · `platform_connections` · `sync_registry` · `integration_sync_config` · `export_log` | YARNNN, specialists, user-authored agents, canonical context domains, `_shared/`, all tasks (including essentials) | No agent rows to touch — Platform Bots are capability bundles per ADR-207 P4a; reconnecting restores automatically |
| **L4** | `DELETE /account/reset` | Everything user-scoped (L2 set + `platform_connections` + `sync_registry` + `export_log` + `destination_delivery_log` + `token_usage` + `user_admin_flags` + `user_notification_preferences`) · `workspaces` row · MCP OAuth tables | Nothing (auth user only) | Recreates `workspaces` row, then full `initialize_workspace()` |
| **L5** | `DELETE /account/deactivate` | `workspace_file_versions` + `workspace_files` + MCP OAuth pre-wipe, then auth user delete cascades all remaining user-scoped rows | Nothing | N/A |

### L1 contract — what is and isn't touched

L1 is the lightest layer. The user clicking "Clear Work History" expects "give me a clean slate without losing what I've built up." The contract:

**Deleted by L1:**
- All `agent_runs` rows belonging to the user (every past task execution record). The deletion happens via `agent_id IN (SELECT id FROM agents WHERE user_id = $1)` because `agent_runs` is scoped through `agents`, not directly via `user_id`. FK cascades wipe dependent rows on `agent_export_preferences`, `delivery_logs`, etc.
- `workspace_files` rows where `path LIKE '/tasks/%/outputs/%'` — every past output folder, every manifest, every binary artifact under any task slug.
- `workspace_files` rows where `path LIKE '/tasks/%/memory/_run_log.md'` — the agent's per-task observation log. Re-created on next run by `TaskWorkspace.append_run_log()`.

**NEVER touched by L1 (the L1 invariant set):**
- `tasks` table rows. Essential or otherwise. The user keeps every task they configured, including the next scheduled `next_run_at`.
- `agents` table rows. The roster is preserved verbatim.
- `chat_sessions` rows. The user's relationship with TP is conversational memory, not "work history." Wiping it would be surprising.
- `activity_log` rows. Per ADR-164, no task-lifecycle events are written here anymore. There's nothing in `activity_log` that L1 considers "work history" — it's only workspace-level events (chat sessions, integrations, agent approvals, scheduler heartbeat).
- `workspace_files` outside the two L1 path patterns. Specifically: `TASK.md`, `DELIVERABLE.md`, `memory/feedback.md`, `memory/steering.md`, `memory/reflections.md` for each task. Plus the entire `/workspace/context/` substrate (every accumulated context domain — competitors/, market/, etc.). Plus `IDENTITY.md`, `BRAND.md`, `AWARENESS.md`, `_playbook.md`, etc.
- `platform_connections`. OAuth tokens stay live.

**No reinit needed.** The L1 invariants don't include anything this endpoint touches. The next scheduled task fire automatically creates a fresh `/outputs/{date}/` folder and a fresh `_run_log.md`.

### Why L1 doesn't slice on `output_kind` (in spite of the Phase 2 design memo)

The Phase 2 memo proposed slicing L1 by ADR-166's `output_kind` enum: delete `produces_deliverable` outputs but not `accumulates_context` writes, etc. Phase 3 reassessment found this unnecessary:

1. **The path filter is sharper than the kind filter.** `/tasks/%/outputs/%` already excludes `accumulates_context` writes (those go to `/workspace/context/{domain}/`, not `/tasks/{slug}/outputs/`). The `accumulates_context` substrate is already preserved by the path-based filter.
2. **`external_action` outputs go to `/tasks/{slug}/outputs/` like everything else** (they write `output.txt` instead of `output.md`, but the path is the same). User intent for L1 is "clean my work history" — they want their past Slack-message records cleared just like their past report drafts.
3. **`system_maintenance` outputs (back office tasks) live under the same path pattern.** A user clearing work history reasonably expects past back-office reports to disappear too — they're work-history artifacts. The next scheduled hygiene/cleanup run will produce a fresh report.

So the simpler `path LIKE '/tasks/%/outputs/%'` rule is correct for all four `output_kind` values uniformly. Slicing by kind would have been over-engineering.

### What we learned about the Phase 2 "blockers"

The Phase 2 memo claimed three things blocked L1 implementation. Phase 3 reassessment found all three were already resolved:

1. **"`back-office-task-freshness` ADR needed for the selective purge primitive."** False premise. The primitive shape L1 needs (per-user, per-path `workspace_files` deletes scoped to a path pattern) already exists in `api/services/back_office/workspace_cleanup.py`. The same `client.table("workspace_files").delete().eq("user_id", user_id).like("path", pattern).execute()` shape. L1 just needed to call it with different filters. No new primitive required.
2. **"`agent_runs → task_runs` rename pending."** Not in flight. There's no commit timeline for the rename. L1 references `agent_runs` as the table is named today (2026-04-08); whenever the rename happens, L1 will sweep along with every other consumer in the same diff.
3. **"Full `activity_log` deprecation in flight."** Already done. ADR-164 already removed the 9 task-lifecycle event types from `activity_log` write paths. The current taxonomy is `chat_session`, `integration_*`, `agent_approved/rejected`, `agent_bootstrapped`, `agent_scheduled`, `scheduler_heartbeat` — none of which L1 considers "work history." L1 doesn't touch `activity_log` at all.

The lesson: the deferred-blocker section of a memo is the most error-prone part of any planning doc, because deferred items get re-evaluated against a moving codebase. **Always re-audit the blockers before deferring further; don't trust the previous memo's "still blocked" claim.**

### Task-dependency cascade on `clear_integrations` — still deferred

Independently from L1, this thread is still open: a user task with `output_kind = "external_action"` and a platform-specific delivery target should auto-pause when its target platform disconnects. A user task with `output_kind = "accumulates_context"` writing to `/workspace/context/{disconnected platform}/` should also auto-pause. Both are mechanically detectable from the registry without scanning TASK.md.

This is a task-lifecycle concern (belongs with `back-office-task-freshness` if/when that ADR materializes), not a purge concern. Mentioning it here so the implementation thread doesn't get separated from the purge layering work — but it's NOT a blocker for anything purge-related anymore.

## What is deliberately still deferred

### `workspace_state` writes from purge endpoints

`workspace_state` is a **derived** signal computed in `api/services/working_memory.py:143` from filesystem + SQL reads on every TP message. It's not stored. Purges don't need to "update" it — once the filesystem + tasks are restored by `initialize_workspace()`, the derivation returns the correct state automatically. Any proposal to store `workspace_state` should be evaluated as a separate change, not entangled with purge.

### Settings page post-purge chat state in other tabs

The frontend calls `clearMessages()` + routes to `/work` (Phase 2 update — was `/context` in Phase 1) after workspace/reset purge, and refreshes danger zone stats. This is sufficient for the common case. If a user has a background chat session open in another tab during a purge, that tab will get a 404 on the next message send — they'll need to reload. Documenting rather than fixing; the edge case is narrow and the recovery is a page reload.

### Phase 2 (2026-04-08): post-purge route change

After `clear_workspace` and `full_account_reset`, the Settings page used to route the user to `/context`. Phase 2 changed this to `/work`. Reasoning:

- Pre-ADR-167, `/work` auto-selected the first task on mount and dropped the user into a detail view they didn't ask for. Routing there post-purge felt jarring.
- ADR-167 deleted auto-select-first; `/work` is now a list-mode landing surface. Post-purge, the three essential tasks are immediately visible in the list — concrete proof that re-scaffolding worked.
- `/context` is for setting up identity/brand. Post-purge, the user already knows they wiped it; showing them an empty identity form first is less reassuring than showing them the work that's already scheduled.

## Smoke tests worth running (not executed pre-commit)

These require a running API + test account and are documented here so they don't get forgotten:

1. **`clear_workspace` on a real account**
   - Expect: response JSON `message` field reads `"restored 10 agents and 3 essential tasks"` (or similar)
   - Expect: `SELECT count(*) FROM agents WHERE user_id = $1` returns 10
   - Expect: `SELECT count(*) FROM tasks WHERE user_id = $1 AND essential = true` returns 3
   - Expect: `/api/workspace-files/tree` shows IDENTITY.md, BRAND.md, `/workspace/context/{all domains}/`

2. **`clear_integrations` on a connected Slack account**
   - Expect: `SELECT status FROM agents WHERE role = 'slack_bot' AND user_id = $1` returns `'paused'` (NOT missing)
   - Expect: No rows matching `path LIKE '/workspace/context/slack/%'`
   - Expect: Canonical context domains still present
   - Expect: `essential = true` tasks untouched

3. **Reconnect Slack after `clear_integrations`**
   - Flow: `clear_integrations` → OAuth flow for Slack → callback
   - Expect: `SELECT status FROM agents WHERE role = 'slack_bot' AND user_id = $1` returns `'active'`
   - Expect: landscape discovered, sources auto-selected (ADR-113)

4. **`full_account_reset` on a canary account**
   - Expect: Same as `clear_workspace` invariants PLUS a fresh `workspaces` row
   - Expect: MCP OAuth tables cleared (`mcp_oauth_codes`, `_access_tokens`, `_refresh_tokens` all empty for user)

## Files touched

### Phase 1 (commit 16c7f0e, 2026-04-08)

- `api/routes/account.py` — docstring, `DangerZoneStats` field, `get_danger_zone_stats`, `clear_workspace`, `clear_integrations`, `full_account_reset`
- `api/routes/integrations.py` — OAuth callback reactivates paused platform bots
- `web/lib/api/client.ts` — `getDangerZoneStats` response type
- `web/app/(authenticated)/settings/page.tsx` — `DangerZoneStats` interface, confirmation copy, post-purge comment cleanup
- `docs/design/PURGE-LAYERING.md` — this memo (initial draft)

### Phase 2 (2026-04-08, this commit)

- `web/app/(authenticated)/settings/page.tsx` — post-purge route changed from `/context` → `/work` (ADR-167 list-mode landing)
- `docs/design/PURGE-LAYERING.md` — added designed layer taxonomy (L1–L5) with `output_kind` axis from ADR-166; updated deferred-items section to reflect what's now ready vs still blocked

### Phase 3 (commit f3068a3, 2026-04-08)

- `api/routes/account.py` — new `DELETE /account/work-history` endpoint (`clear_work_history`); new helpers `_count_workspace_pattern`, `_delete_workspace_pattern`, `_user_agent_ids`, `_count_user_agent_runs`, `_delete_user_agent_runs`; `DangerZoneStats.agent_runs` field added; `get_danger_zone_stats` returns it; module docstring updated to describe all 5 layers
- `web/lib/api/client.ts` — `clearWorkHistory()` method added; `getDangerZoneStats` return type extended with `agent_runs`
- `web/app/(authenticated)/settings/page.tsx` — `DangerZoneStats` interface extended; `DangerAction` type extended with `"work-history"`; new "Clear Work History" card (with `History` lucide icon) inserted as first purge action above "Clear Workspace"; new branch in danger-action handler; new confirmation dialog branch with explicit preserved/deleted lists
- `docs/design/PURGE-LAYERING.md` — this memo: status header updated to "fully shipped", layer table marked with shipped endpoints, "Why L1 doesn't slice on output_kind" explanation added, "What we learned about the Phase 2 blockers" retrospective section added

### Phase 4 (this commit, 2026-04-09) — doc relocation only

- `docs/design/PURGE-LAYERING.md` → **`docs/features/data-privacy.md`** — moved via `git mv` so git history is preserved. The doc belongs in `features/` alongside other user-facing surface docs (`activity.md`, `agent-types.md`, `memory.md`, etc.) now that the design is stable and shipped. The `docs/design/` tree is for in-flight architectural design notes; this memo outlived that phase two commits ago.
- `docs/features/previous_versions/data-privacy.md` — **deleted**. The stale archived doc from 2026-04-01 (commit 0019571) described a pre-ADR-140/151/158/164 purge model with references to dropped tables (`platform_content`, `filesystem_documents`, `integration_import_jobs` in the purge flow). Singular implementation discipline: one canonical doc per topic, no parallel stale archive.
- `api/routes/account.py` — two `PURGE-LAYERING.md` references updated to `docs/features/data-privacy.md` (module docstring + `clear_work_history` docstring)
- `web/lib/api/client.ts` — one `PURGE-LAYERING.md` reference updated to `docs/features/data-privacy.md` (inline comment on `clearWorkHistory`)

No code behavior changes. No endpoint changes. No test changes.

## When to revisit this memo

The purge thread is **closed** as of Phase 3. The five-layer model is fully shipped and the invariants for each layer are documented above. There is no remaining purge work to schedule.

Triggers that would warrant reopening this memo:

- **Any change to the signup scaffold invariants** (ADR-205 YARNNN-only rule · ADR-194 v2 Reviewer substrate · ADR-206 `_shared/` skeleton · ADR-161 daily-update · ADR-164 back-office tasks) — the L2/L4 reinit invariants would shift, and L1's "preserved" set might need to grow if new always-present files are added under `/tasks/{slug}/`.
- **Any new user-scoped table added to the schema** — purge audit required. Historical misses (ADR-194 `action_proposals` added 2026-04-19, ADR-209 `workspace_file_versions` added 2026-04-23) both went unpurged for weeks before a 2026-04-24 streamline pass. New tables must land with purge coverage in the same commit.
- **Any new file convention added under `/tasks/{slug}/`** that the L1 contract should preserve. If a future ADR introduces, say, `/tasks/{slug}/memory/notes_for_user.md` or similar, decide whether L1 should keep it (and update the path filter accordingly).
- **`agent_runs → task_runs` rename**, when it eventually happens. L1 references `agent_runs` directly and will sweep along with every other consumer.
- **Discovery of a real bug** in any layer's reinit or invariant guarantee during canary observation.
- **A decision to implement or drop ADR-155** (workspace_state signal storage). Currently irrelevant because workspace_state is derived, not stored.

If `back-office-task-freshness` materializes as an ADR, the task-dependency cascade on `clear_integrations` (still deferred — see above) is the only purge-adjacent thread that should pick up. It's a task-lifecycle concern, not a purge layering concern, so it doesn't change the L1–L5 model.
