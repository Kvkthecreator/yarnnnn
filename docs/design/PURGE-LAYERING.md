# Purge Layering & Workspace Reinit

> **Status**: Phase 1 shipped (2026-04-08, commit 16c7f0e). Phase 2 follow-up shipped (2026-04-08): post-purge `/work` routing + layered model design recorded below. Layered implementation deferred pending `back-office-task-freshness`.
> **Scope**: Settings → Account tab purge actions and their relationship to workspace invariants.
> **Related ADRs**: ADR-140 (roster), ADR-151/152 (directory registry), ADR-153 (platform_content sunset), ADR-158 (platform bot ownership), ADR-161 (daily-update anchor), ADR-164 (back office tasks), ADR-166 (output_kind taxonomy — gives us the right axis to slice purge layers), ADR-167 (list/detail surfaces — `/work` is a meaningful post-purge landing).

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

## What the 4 purge actions now guarantee

| Action | Purges | Reinit | Preserves |
|---|---|---|---|
| **Clear Workspace** | agents, tasks, workspace_files, chat, activity, work_credits | Full `initialize_workspace()`: 10 agents, context domains, seed files, 3 essential tasks | platform_connections (so user doesn't re-OAuth) |
| **Disconnect Platforms** | sync state, `/workspace/context/{slack,notion,github}/`, platform_connections | Pauses platform bots (reconnect flips back to active) | Domain stewards, canonical domains, IDENTITY/BRAND, all tasks including essential ones |
| **Full Data Reset** | Everything user-scoped + workspaces row | Recreates workspaces row, then full `initialize_workspace()` | Nothing (auth user only) |
| **Deactivate** | Auth user (cascades everything) | N/A (account gone) | Nothing |

### Invariants that now hold post-purge

For `clear_workspace` / `full_account_reset`, the endpoint returns only when all of these are true:

- 10 agents exist (9 domain-stewards/synthesizer + TP, per DEFAULT_ROSTER)
- All context domain directories with synthesis files + `_tracker.md` + `assets/`
- IDENTITY.md / BRAND.md / AWARENESS.md / _playbook.md / style.md / notes.md / WORKSPACE.md seeded
- Three essential tasks exist: `daily-update`, `back-office-agent-hygiene`, `back-office-workspace-cleanup`

For `clear_integrations`:

- All 10 agents still exist (platform bots paused, not deleted)
- Canonical context domains untouched
- Essential tasks untouched
- Reconnect flow will reactivate paused bots automatically

## The layered purge model — designed, not yet implemented

ADR-166 (registry coherence pass) gave us the taxonomy axis we were missing in Phase 1: every task carries an `output_kind` (`accumulates_context | produces_deliverable | external_action | system_maintenance`). This is the right axis to slice purge layers because it directly maps "what gets deleted" to "what kind of work product the user is choosing to abandon."

The full layered model is designed below. It is **not yet implemented** because three load-bearing pieces are still in motion (see "What still blocks implementation" further down) and shipping the layers now would mean rewriting them after those land. When the prerequisites are in place, this section becomes the implementation spec.

### Layer taxonomy

| Layer | Action | Purges (by `output_kind`) | Purges (other) | Reinit |
|---|---|---|---|---|
| **L1** | Soft reset (work history) | `produces_deliverable` outputs · `external_action` run logs | chat sessions · `activity_log` (narrowed scope per ADR-164) | None — invariants intact |
| **L2** | Workspace reset | + `accumulates_context` (all `/workspace/context/{domain}/`) | + `agent_runs` for purged tasks | Re-scaffold context domains via `initialize_workspace()` Phase 1 only |
| **L3** | Disconnect platforms | (only `accumulates_context` under `/workspace/context/{slack,notion,github}/`) | + `platform_connections` · sync state · `slack_user_cache` | Pause platform-bot agents (already shipped Phase 1) |
| **L4** | Full reset | All four `output_kind` values | + agents · tasks · `workspaces` row · MCP OAuth | Full `initialize_workspace()` (already shipped Phase 1) |
| **L5** | Deactivate | All four | + auth user (cascade) | N/A |

The current 4-button UI already implements L3, L4, L5, and a coarse hybrid of L1+L2+context-keep. Phase 2 of this memo adds the full L1 (which has no UI today) and splits the existing L2-ish "Clear Workspace" into a true L2 that preserves identity/brand.

### Mapping to existing endpoints

Today's `account.py` has 4 endpoints. The layered model needs 5 — L1 is the new one. Migration strategy:

| Today's endpoint | Maps to | Status |
|---|---|---|
| `DELETE /account/workspace` (Clear Workspace) | **L2** (Workspace reset) | Shipped in Phase 1, will be slightly narrowed when L1 ships separately |
| `DELETE /account/integrations` (Disconnect Platforms) | **L3** | Shipped in Phase 1 |
| `DELETE /account/reset` (Full Data Reset) | **L4** | Shipped in Phase 1 |
| `DELETE /account/deactivate` (Deactivate) | **L5** | Shipped in Phase 1 |
| (none) | **L1** (Soft reset / clear work history) | **NEW** — requires `back-office-task-freshness` machinery |

### Why L1 needs `back-office-task-freshness`

L1 selectively deletes by `output_kind`. That requires walking `tasks` joined with their `output_kind` from the registry, then deleting only the matching `agent_runs` + output folders. This is the same primitive `back-office-task-freshness` will need to expose for its own purpose (selectively trimming stale `agent_runs` rows). Building L1 before that primitive exists means writing throwaway code; building L1 after means a small wrapper around the existing primitive. Wait.

### What still blocks implementation

The layered model is **designed** but not buildable today because:

1. **`back-office-task-freshness` ADR not yet shipped.** It will introduce the per-task selective purge primitive that L1 needs to call.
2. **`agent_runs → task_runs` rename pending.** Whatever the L1 endpoint references in code will need renaming in the same window. Doing it once at rename time is one diff; doing it twice means churn.
3. **Full `activity_log` deprecation in flight.** ADR-164 narrowed its role; the table stays but with fewer event types. L1 needs to know which `activity_log` rows to keep (workspace-level events) vs delete (task-level work history). That answer becomes stable after the deprecation lands.

When all three are in place, L1 implementation is approximately:
- 1 new endpoint in `account.py` (DELETE `/account/work-history`) calling the new selective purge primitive
- 1 new card in the Settings → Account "Data & Privacy" section (above "Clear Workspace")
- 1 confirmation dialog
- ~50 lines total

### Task-dependency cascade on `clear_integrations` — ready when L1 ships

ADR-166's `output_kind` makes this easier than I thought when writing the original memo. A user task with `output_kind = "external_action"` and a platform-specific delivery target should auto-pause when its target platform disconnects. A user task with `output_kind = "accumulates_context"` writing to `/workspace/context/{disconnected platform}/` should also auto-pause. Both are mechanically detectable from the registry without scanning TASK.md.

This is still a task-lifecycle concern (belongs with `back-office-task-freshness`), not a purge concern. Mentioning it here so the implementation thread doesn't get separated from the purge layering work.

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

## When to revisit this memo

The next time this memo gets touched, it should be the **L1 implementation pass**. That happens when all three of these have landed:

- [ ] `back-office-task-freshness` ADR/implementation (provides the per-task selective purge primitive L1 calls)
- [ ] Full `activity_log` deprecation (clarifies which rows L1 keeps vs deletes)
- [ ] `agent_runs → task_runs` rename (avoids L1 referencing a column name that's about to change)

When all three are ✅, the L1 implementation is ~50 LOC: one new endpoint, one new Settings card, one confirmation dialog. The design above is the spec; just implement it.

Other triggers that would warrant revisiting earlier:

- Any change to `DEFAULT_ROSTER` or the essential task set (ADR-140 / ADR-161 / ADR-164) — the reinit invariants would shift
- A decision to implement or drop ADR-155 (workspace_state signal storage)
- Discovery of a real bug in Phase 1's transactional reinit during canary observation
