# ADR-117 Feedback Substrate — Test Playbook

> Tests for the unified feedback substrate (ADR-117 Phases 1-2).
> Run against production with your test user. Requires at least one agent with delivered runs.

---

## Pre-test: Baseline check

Confirm your test user has:
- At least one active agent with 2+ delivered runs (for distillation to produce meaningful preferences)
- Platform connections synced (Slack, Gmail, or Notion — at least one)
- Agent workspace exists (`workspace_files` rows for the agent's slug)

```sql
-- Check active agents with runs
SELECT a.id, a.title, a.skill, a.scope,
       COUNT(ar.id) as run_count,
       COUNT(ar.id) FILTER (WHERE ar.status = 'delivered') as delivered_count
FROM agents a
LEFT JOIN agent_runs ar ON ar.agent_id = a.id
WHERE a.user_id = '<your-user-id>' AND a.status = 'active'
GROUP BY a.id ORDER BY delivered_count DESC;
```

---

## Test 1: Self-Observation on Agent Run (Phase 2)

**Trigger:** Run an agent (via scheduler, admin trigger, or manual `POST /api/agents/{id}/run`)

**Expected post-delivery state:**
1. `workspace_files` should have a row with `path LIKE '/agents/{slug}/memory/observations.md'`
2. The content should include a timestamped `(self)` observation entry
3. Entry should contain: topics, source coverage, item count

**Verify:**
```sql
-- Check observations.md exists and has self-observation
SELECT path, LEFT(content, 500) as content_preview, updated_at
FROM workspace_files
WHERE user_id = '<your-user-id>'
  AND path LIKE '%/memory/observations.md'
ORDER BY updated_at DESC;
```

**Pass if:** Content contains `(self)` entries with topics and source coverage.
**Fail if:** No observations.md, or observations missing `(self)` source tag.

---

## Test 2: Feedback Distillation on Version Edit (Phase 1)

**Trigger:** Edit a delivered version via the dashboard (PATCH `/api/agents/{agent_id}/runs/{run_id}`)
- Change `final_content` (add an "Action Items" section) OR
- Add a `feedback_notes` value (e.g., "too long, needs to be more concise")

**Expected:**
1. `workspace_files` should have `path LIKE '/agents/{slug}/memory/preferences.md'`
2. Content should be structured with `# User Preferences` header
3. If edits were made: should list additions/deletions with frequency counts
4. If feedback notes were given: should include them verbatim under "## Explicit feedback"

**Verify:**
```sql
-- Check preferences.md after edit
SELECT path, LEFT(content, 500) as content_preview, updated_at
FROM workspace_files
WHERE user_id = '<your-user-id>'
  AND path LIKE '%/memory/preferences.md'
ORDER BY updated_at DESC;
```

**Pass if:** preferences.md contains structured directives derived from edit patterns.
**Fail if:** No preferences.md, or content is raw edit patterns instead of distilled directives.

---

## Test 3: Workspace Context Loading (All Strategies)

**Trigger:** Run an agent after Tests 1 and 2 have populated observations.md and preferences.md.

**Expected:**
1. The agent's gathered context (visible in `agent_runs.metadata`) should include `workspace` in `sources_used`
2. The generated output should reflect accumulated preferences (e.g., if preferences say "Always include Action Items", the output should have an Action Items section)

**Verify:**
```sql
-- Check latest run metadata includes workspace source
SELECT version_number, metadata->'sources_used' as sources,
       metadata->'strategy' as strategy,
       LEFT(draft_content, 200) as draft_preview
FROM agent_runs
WHERE agent_id = '<agent-id>'
ORDER BY version_number DESC LIMIT 1;
```

**Pass if:** `sources_used` includes `"workspace"`.
**Fail if:** `sources_used` missing `"workspace"` — strategy didn't load workspace context.

---

## Test 4: Supervisor Notes from Composer (Phase 1c)

**Prerequisite:** An agent with low approval rate (or manually trigger composer lifecycle).

**Expected:** When Composer identifies an underperformer and writes coaching:
1. `workspace_files` should have `path LIKE '/agents/{slug}/memory/supervisor-notes.md'`
2. Content should include `# Supervisor Assessment` header
3. Content should include specific coaching (not just "observe" or "pause")

**Verify:**
```sql
-- Check supervisor-notes.md
SELECT path, LEFT(content, 500) as content_preview, updated_at
FROM workspace_files
WHERE user_id = '<your-user-id>'
  AND path LIKE '%/memory/supervisor-notes.md'
ORDER BY updated_at DESC;
```

**Note:** This is harder to trigger naturally — may need to wait for a heartbeat cycle with an underperforming agent. Can also verify the code path exists via import validation.

---

## Test 5: No Dual Feedback Path (Singular Implementation)

**Verify:** The old `get_past_versions_context()` injection path is fully removed.

```sql
-- Check: no "## Learned Preferences" or "PAST VERSIONS" in any recent system prompt
-- (This is a code-level check, not DB — see verification below)
```

**Code verification:**
1. `api/services/agent_execution.py` has NO `learned_preferences` parameter
2. `api/services/agent_pipeline.py` has NO `get_past_versions_context()` function
3. `api/services/agent_pipeline.py` `build_skill_prompt()` has NO `past_versions` parameter
4. All skill templates have NO `{past_versions}` placeholder

**Pass if:** All four checks pass (verified via import chain test above).
**Fail if:** Any old feedback path remnant exists.

---

## Test 6: Observation Accumulation Over Multiple Runs

**Trigger:** Run the same agent 3+ times.

**Expected:**
1. `memory/observations.md` should have 3+ timestamped entries
2. Each entry has different content (different topics, potentially different item counts)
3. Entries are appended, not overwritten

**Verify:**
```sql
SELECT path, content, updated_at
FROM workspace_files
WHERE user_id = '<your-user-id>'
  AND path LIKE '%/memory/observations.md'
ORDER BY updated_at DESC;
```

**Pass if:** Multiple `(self)` entries with different timestamps and content.
**Fail if:** Only one entry (overwritten) or identical entries.

---

## Test 7: Preferences Overwrite (Not Append)

**Trigger:** Edit a version twice (two separate PATCH calls with different edits).

**Expected:**
1. `memory/preferences.md` should be overwritten each time (not appended)
2. Content represents the *current best understanding* across all recent runs
3. Old patterns that stopped recurring may drop out

**Verify:** Compare `updated_at` timestamp — should be from the second edit. Content should reflect aggregate patterns from all runs, not just the latest edit.

---

## Results Template

| Test | Result | Notes |
|------|--------|-------|
| 1: Self-Observation | | |
| 2: Feedback Distillation | | |
| 3: Workspace Context Loading | | |
| 4: Supervisor Notes | | |
| 5: No Dual Path | | |
| 6: Observation Accumulation | | |
| 7: Preferences Overwrite | | |
