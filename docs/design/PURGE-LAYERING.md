# Purge Layering & Workspace Reinit

> **Status**: Phase 1 shipped (2026-04-08). Layered model deferred pending post-Phase-4 refactors.
> **Scope**: Settings → Account tab purge actions and their relationship to workspace invariants.
> **Related ADRs**: ADR-140 (roster), ADR-151/152 (directory registry), ADR-153 (platform_content sunset), ADR-158 (platform bot ownership), ADR-161 (daily-update anchor), ADR-164 (back office tasks).

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

## What is deliberately deferred

### The layered purge model (3/4/5 layers)

A proper taxonomy of purge actions scoped by invariant (Layer 1 = work history soft reset; Layer 2 = workspace reset keeping connections; Layer 3 = disconnect platforms; Layer 4 = full reset; Layer 5 = deactivate) was **not designed**. The current 4-button model works, and designing a layered model now — while the following refactors are in flight — would mean rewriting it multiple times:

- `back-office-task-freshness` (the original question that started the ADR-164 thread)
- Full `activity_log` deprecation (table stays with narrower role)
- Task type / primitive re-optimization
- `agent_runs → task_runs` rename
- Frontend filter-by-agent UI on `/work`

When those refactors land, the invariant set will be stable enough to design the layer model coherently. Revisit this memo then.

### `workspace_state` writes from purge endpoints

`workspace_state` is a **derived** signal computed in `api/services/working_memory.py:143` from filesystem + SQL reads on every TP message. It's not stored. Purges don't need to "update" it — once the filesystem + tasks are restored by `initialize_workspace()`, the derivation returns the correct state automatically. Any proposal to store `workspace_state` should be evaluated as a separate change, not entangled with purge.

### Task-dependency cascade on `clear_integrations`

If a **user-authored** task declares `context_reads` referencing a paused platform domain (e.g. a user task that reads from `/workspace/context/slack/`), the task remains `active`. After integration purge, that task will still fire on its schedule and attempt to read an empty directory. The right behavior is probably auto-pause-then-resume-on-reconnect, but:

1. It requires scanning task filesystem state (`context_reads` is in TASK.md, not the DB), which is expensive on every disconnect.
2. It's a task-lifecycle concern, not a purge concern — it belongs with the upcoming `back-office-task-freshness` work.
3. Essential tasks are explicitly platform-agnostic so they are not affected.

Deferred. Add to the back-office-task-freshness scope.

### Settings page post-purge chat state

The frontend currently calls `clearMessages()` + `router.push('/context')` after workspace/reset purge, and separately refreshes danger zone stats. This is sufficient for the common case. If a user has a background chat session open in another tab during a purge, that tab will get a 404 on the next message send — they'll need to reload. Documenting rather than fixing; the edge case is narrow and the recovery is a page reload.

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

## Files touched in Phase 1

- `api/routes/account.py` — docstring, `DangerZoneStats` field, `get_danger_zone_stats`, `clear_workspace`, `clear_integrations`, `full_account_reset`
- `api/routes/integrations.py` — OAuth callback reactivates paused platform bots
- `web/lib/api/client.ts` — `getDangerZoneStats` response type
- `web/app/(authenticated)/settings/page.tsx` — `DangerZoneStats` interface, confirmation copy, post-purge comment cleanup
- `docs/design/PURGE-LAYERING.md` — this memo

## When to revisit this memo

Revisit when any of the following lands:

- `back-office-task-freshness` ADR/implementation
- Full `activity_log` deprecation
- Task type / primitive re-optimization
- Any change to the `DEFAULT_ROSTER` or essential task set (ADR-140 / ADR-161 / ADR-164)
- A decision to implement or drop ADR-155 (workspace_state signal)

At that point, reassess whether a layered purge model is worth building and what the right layer boundaries are.
