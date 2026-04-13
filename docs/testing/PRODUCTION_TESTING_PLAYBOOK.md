# Production Testing Playbook — ADR-138/141/149/163/164/166/167/176

> E2E validation for the current agent + task architecture.
> Run against production with kvkthecreator@gmail.com.
> Last updated: 2026-04-13.
>
> **What changed since last version (2026-04-10):**
> - ADR-176: Universal specialist roster replaces ICP domain-steward roster
> - 9 agents at signup: 6 universal specialists (Researcher, Analyst, Writer, Tracker, Designer, TP) + 3 platform bots
> - Capability split: accumulation agents (Researcher, Analyst, Writer, Tracker) vs production (Designer)
> - Domain context directories created by work demand, not pre-scaffolded at signup
>
> **What changed since 2026-03-20:**
> - Projects/PM/Composer/pulse engine all deleted (ADR-138, ADR-156, ADR-141, ADR-126 dissolved)
> - Architecture is now: Agents (WHO) + Tasks (WHAT) + TP (orchestration)
> - Three-layer execution: Scheduler (SQL) → Task Pipeline (generate) → TP (chat)
> - 4 output_kinds per ADR-166: `accumulates_context | produces_deliverable | external_action | system_maintenance`
> - Surface is Chat | Work | Agents | Context (ADR-163)
> - Back office tasks are TP-owned essential tasks visible in /work (ADR-164)

---

## Pre-Flight

```bash
# API health
curl -s https://yarnnn-api.onrender.com/health

# Get USER_ID for kvkthecreator@gmail.com
psql "$SUPABASE_URL" -c "SELECT id FROM workspaces WHERE user_id = (SELECT id FROM auth.users WHERE email='kvkthecreator@gmail.com') LIMIT 1;"
```

```sql
-- Baseline snapshot for kvkthecreator@gmail.com
-- Replace USER_ID below with the UUID from above

SELECT 'tasks' as entity, COUNT(*) as total,
  COUNT(*) FILTER (WHERE status = 'active') as active,
  COUNT(*) FILTER (WHERE essential = true) as essential
FROM tasks WHERE user_id = :'USER_ID'
UNION ALL
SELECT 'agents', COUNT(*), COUNT(*) FILTER (WHERE status = 'active'), 0
FROM agents WHERE user_id = :'USER_ID'
UNION ALL
SELECT 'agent_runs (this month)', COUNT(*),
  COUNT(*) FILTER (WHERE status = 'delivered'), 0
FROM agent_runs ar
JOIN agents a ON a.id = ar.agent_id
WHERE a.user_id = :'USER_ID'
  AND ar.created_at >= date_trunc('month', NOW());
```

---

## 1. Pre-Scaffolded Roster Verification (ADR-176)

Every workspace gets exactly 9 agents at sign-up. Verify the roster is intact and correctly typed.

```sql
SELECT title, role, status, scope
FROM agents
WHERE user_id = :'USER_ID'
ORDER BY role;
```

**Expected roster (9 agents — ADR-176 universal specialists):**

| Title | Role | Class |
|-------|------|-------|
| Researcher | researcher | specialist |
| Analyst | analyst | specialist |
| Writer | writer | specialist |
| Tracker | tracker | specialist |
| Designer | designer | specialist |
| Thinking Partner | thinking_partner | meta-cognitive |
| Slack Bot | slack_bot | platform-bot |
| Notion Bot | notion_bot | platform-bot |
| GitHub Bot | github_bot | platform-bot |

**Pass if:** All 9 present, status=active for non-bot agents, AGENT.md exists in workspace.
**Fail if:** Missing agents, wrong role values, constraint violations.

```sql
-- Verify AGENT.md files exist for each
SELECT path, LENGTH(content) as chars
FROM workspace_files
WHERE user_id = :'USER_ID'
  AND path LIKE '/agents/%/AGENT.md'
ORDER BY path;
```

---

## 2. Essential Tasks Verification (ADR-161/164)

Three tasks are auto-scaffolded as essential at sign-up and cannot be archived.

```sql
SELECT slug, status, essential, mode, schedule, next_run_at, last_run_at
FROM tasks
WHERE user_id = :'USER_ID'
  AND essential = true
ORDER BY slug;
```

**Expected:**

| Slug | Mode | Essential |
|------|------|-----------|
| daily-update | recurring | true |
| back-office-agent-hygiene | recurring | true |
| back-office-workspace-cleanup | recurring | true |

**Pass if:** All 3 present with `essential=true`, `status=active`.
**Fail if:** Missing any of the 3, or `essential=false`.

---

## 3. Output Kind A — `produces_deliverable`: Daily Update (ADR-161)

The `daily-update` is the heartbeat artifact. Tests the full single-step deliverable pipeline.

### 3.1 Trigger a Run

**Via UI:** On `/work`, click into `daily-update` → Run Now.

**Via SQL (force immediate):**
```sql
UPDATE tasks SET next_run_at = NOW()
WHERE user_id = :'USER_ID' AND slug = 'daily-update'
RETURNING slug, next_run_at;
```

Wait 3–5 minutes for the scheduler tick.

### 3.2 Verify Output

```sql
-- agent_runs record created
SELECT ar.version_number, ar.status, ar.delivery_status,
  LEFT(ar.draft_content, 200) as preview,
  ar.created_at
FROM agent_runs ar
JOIN agents a ON a.id = ar.agent_id
WHERE a.user_id = :'USER_ID'
  AND ar.metadata->>'task_slug' = 'daily-update'
ORDER BY ar.version_number DESC LIMIT 1;

-- Output file written to task workspace
SELECT path, lifecycle, LENGTH(content) as chars, updated_at
FROM workspace_files
WHERE user_id = :'USER_ID'
  AND path LIKE '/tasks/daily-update/outputs/%'
ORDER BY updated_at DESC LIMIT 5;

-- Manifest written
SELECT path, content
FROM workspace_files
WHERE user_id = :'USER_ID'
  AND path LIKE '/tasks/daily-update/outputs/%/manifest.json'
ORDER BY updated_at DESC LIMIT 1;
```

**Pass if:** `agent_runs.status = 'delivered'`, output folder exists, manifest.json present with delivery metadata.
**Fail if:** Status stuck at `generating`, no output file, missing manifest.

### 3.3 Email Delivery Check

Check kvkthecreator@gmail.com inbox for a daily update email from yarnnn.
- Subject line should reference date
- Body should be HTML (not raw markdown)
- If workspace is empty: deterministic template with CTA (ADR-161 empty-state branch)

### 3.4 next_run_at Advancement

```sql
SELECT slug, last_run_at, next_run_at,
  EXTRACT(EPOCH FROM (next_run_at - last_run_at)) / 3600 as hours_gap
FROM tasks
WHERE user_id = :'USER_ID' AND slug = 'daily-update';
```

**Pass if:** `next_run_at` is ~24 hours after `last_run_at`.

---

## 4. Output Kind A — `produces_deliverable`: Competitive Brief (Multi-Step)

Tests the multi-step `_execute_pipeline()` path — two agents, output handoff.

### 4.1 Setup

Create or verify a `competitive-brief` task exists with a `track-competitors` context task feeding it.

**Via TP chat:** "Create a competitive brief task for me"

**Verify task created:**
```sql
SELECT slug, mode, status, next_run_at
FROM tasks
WHERE user_id = :'USER_ID' AND slug LIKE 'competitive%'
ORDER BY created_at DESC LIMIT 3;

-- Check TASK.md for multi-step process
SELECT path, content
FROM workspace_files
WHERE user_id = :'USER_ID'
  AND path LIKE '/tasks/%competitive%/TASK.md'
ORDER BY path LIMIT 1;
```

The TASK.md should have a `## Process` section with 2 steps: `update-context` (competitive_intel) + `derive-output` (executive).

### 4.2 Trigger Run

```sql
UPDATE tasks SET next_run_at = NOW()
WHERE user_id = :'USER_ID' AND slug LIKE '%competitive-brief%'
RETURNING slug, next_run_at;
```

### 4.3 Verify Pipeline Execution

```sql
-- Step outputs created (step-1/, step-2/ folders)
SELECT path, lifecycle, LENGTH(content) as chars
FROM workspace_files
WHERE user_id = :'USER_ID'
  AND path LIKE '/tasks/%competitive%/outputs/%'
ORDER BY path;

-- Final manifest includes both steps
SELECT path, content
FROM workspace_files
WHERE user_id = :'USER_ID'
  AND path LIKE '/tasks/%competitive%/outputs/%/manifest.json'
ORDER BY updated_at DESC LIMIT 1;

-- agent_runs shows final output
SELECT ar.version_number, ar.status,
  ar.metadata->>'task_slug' as task,
  ar.metadata->>'step_count' as steps
FROM agent_runs ar
JOIN agents a ON a.id = ar.agent_id
WHERE a.user_id = :'USER_ID'
  AND ar.metadata->>'task_slug' LIKE '%competitive%'
ORDER BY ar.created_at DESC LIMIT 1;
```

**Pass if:** Step folders written (`step-1/`, `step-2/`), final manifest has `sources` array with both steps, delivery status in manifest.
**Fail if:** Only one step ran, manifest missing step sources, no handoff between steps.

---

## 5. Output Kind B — `accumulates_context`: Track Competitors

Tests the context accumulation path — agent writes to `/workspace/context/` domain.

### 5.1 Trigger Run

```sql
UPDATE tasks SET next_run_at = NOW()
WHERE user_id = :'USER_ID' AND slug = 'track-competitors'
RETURNING slug, next_run_at;
```

### 5.2 Verify Context Write-Back

```sql
-- Entity files in context domain
SELECT path, LENGTH(content) as chars, updated_at
FROM workspace_files
WHERE user_id = :'USER_ID'
  AND path LIKE '/workspace/context/competitors/%'
ORDER BY updated_at DESC LIMIT 10;

-- Signals domain also written
SELECT path, LENGTH(content) as chars, updated_at
FROM workspace_files
WHERE user_id = :'USER_ID'
  AND path LIKE '/workspace/context/signals/%'
ORDER BY updated_at DESC LIMIT 5;

-- No deliverable output (accumulates_context tasks don't produce agent_runs deliveries)
SELECT COUNT(*) as run_count
FROM agent_runs ar
JOIN agents a ON a.id = ar.agent_id
WHERE a.user_id = :'USER_ID'
  AND ar.metadata->>'task_slug' = 'track-competitors'
  AND ar.status = 'delivered'
ORDER BY ar.created_at DESC;
```

**Pass if:** Competitor entity files updated/created, signals written, task workspace shows output.
**Fail if:** No context domain files written, wrong path prefix (should be `/workspace/context/` not `/tasks/`).

---

## 6. Output Kind C — `system_maintenance`: Back Office Tasks (ADR-164)

Tests TP-owned back office tasks executing via `_execute_tp_task()`.

### 6.1 Trigger Agent Hygiene

```sql
UPDATE tasks SET next_run_at = NOW()
WHERE user_id = :'USER_ID' AND slug = 'back-office-agent-hygiene'
RETURNING slug, next_run_at;
```

### 6.2 Verify Execution

```sql
-- Task ran (next_run_at advanced)
SELECT slug, last_run_at, next_run_at, status
FROM tasks
WHERE user_id = :'USER_ID' AND slug = 'back-office-agent-hygiene';

-- Check hygiene output in task workspace
SELECT path, LENGTH(content) as chars, updated_at
FROM workspace_files
WHERE user_id = :'USER_ID'
  AND path LIKE '/tasks/back-office-agent-hygiene/%'
ORDER BY updated_at DESC LIMIT 5;
```

**Pass if:** `next_run_at` advanced, no errors in Render logs.
**Fail if:** `ModuleNotFoundError` for back_office executor path, task stuck.

---

## 7. /work Surface — List/Detail Modes (ADR-167)

Tests the new list/detail surface without auto-select-first behavior.

### 7.1 List Mode

1. Navigate to `/work` — should show **full-width task list** (not a pre-selected task)
2. Filter chips should be visible: All | Deliverable | Tracking | Action | Maintenance
3. Group-by default: by Output kind

**Verify:**
- No task auto-selected on landing
- Filter chips map to `output_kind` values
- `daily-update` appears under "Deliverable"
- `track-competitors` appears under "Tracking"
- `back-office-*` tasks appear under "Maintenance"

### 7.2 Detail Mode

1. Click any task → URL changes to `/work?task={slug}`
2. PageHeader renders: `Work > {Task Title}` breadcrumb
3. Objective block visible
4. Kind-specific middle component renders:
   - Deliverable tasks → `OutputPreview` (iframe of latest HTML output)
   - Tracking tasks → `TrackingMiddle` (domain folder link + CHANGELOG)
   - Maintenance tasks → `MaintenanceMiddle` (hygiene log, objective block suppressed)

### 7.3 Breadcrumb Navigation

1. Click "Work" in breadcrumb → returns to list mode (`/work`, no `?task=`)
2. No breadcrumb floating bar visible (deleted in ADR-167 V2 amendment)
3. PageHeader is inline, not floating

---

## 8. /agents Surface — Roster Mode (ADR-167)

### 8.1 Roster Grouping

Navigate to `/agents` — should show grouped roster (no auto-select):
- **Specialists**: Researcher, Analyst, Writer, Tracker, Designer
- **Meta-Cognitive**: Thinking Partner
- **Platform Bots**: Slack Bot, Notion Bot, GitHub Bot

**Verify:**
- `meta-cognitive` class label renders correctly (was a bug — missing from CLASS_LABELS)
- Each card shows: active task count, last run freshness, approval rate (if ≥5 runs)

### 8.2 Agent Detail

1. Click any agent → `/agents?agent={slug}`
2. PageHeader: `Agents > {Agent Title}` breadcrumb
3. IdentityCard + HealthCard visible (no separate header band)
4. "See this agent's work" link routes to `/work?agent={slug}`

---

## 9. Chat Surface — TP Orchestration (ADR-163/159)

### 9.1 Compact Index Injection

The TP prompt should include a compact workspace index (not full memory dump).

Send a message in chat: "What tasks do I have running?"

**Expected behavior:**
- TP references tasks from compact index
- Response mentions `daily-update` (essential anchor)
- Token usage visibly lower than old full-dump model (~200-500 token index vs 3-8K dump)

### 9.2 ManageTask via Chat

Send: "Pause my track-competitors task"

**Expected:** TP calls `ManageTask(action="pause", task_slug="track-competitors")`

```sql
SELECT slug, status FROM tasks
WHERE user_id = :'USER_ID' AND slug = 'track-competitors';
```

**Pass if:** Task status changes to `paused`.

### 9.3 CreateTask via Chat (ManageTask action=create)

Send: "Create a weekly market report for me"

**Expected:** TP calls `ManageTask(action="create", ...)` — NOT `CreateTask` (deleted in ADR-168 Commit 3).

```sql
SELECT slug, status, mode FROM tasks
WHERE user_id = :'USER_ID'
ORDER BY created_at DESC LIMIT 1;
```

**Pass if:** New task created, `CreateTask` NOT referenced in Render logs (primitive deleted).

---

## 10. Primitive Surface Verification (ADR-168)

The rename protocol means old primitive names must be gone from all live callers.

### 10.1 Grep Gate (Run Locally)

```bash
cd /Users/macbook/yarnnn

# These names must NOT appear in live code (api/ and web/)
echo "=== Old primitives (must be 0 results) ==="
grep -r "ReadWorkspace\|WriteWorkspace\|SearchWorkspace\|ListWorkspace\|ReadAgentContext" api/ --include="*.py" | grep -v "test_\|#\|\.pyc" | grep -v "renamed\|old\|deleted\|superseded"
grep -r "\"Read\"\|\"List\"\|\"Search\"\|\"Edit\"" api/services/primitives/ --include="*.py" | grep "name="
grep -r "CreateTask\b" api/ --include="*.py" | grep -v "test_\|#"
grep -r "Execute\b" api/services/primitives/ --include="*.py" | grep "def \|name="
```

**Pass if:** All return 0 results.
**Fail if:** Any old primitive name still referenced in execution path.

### 10.2 Registered Primitives Check

```bash
cd /Users/macbook/yarnnn/api
python3 -c "
from services.primitives.registry import CHAT_TOOLS, HEADLESS_TOOLS
chat_names = [t['name'] for t in CHAT_TOOLS]
headless_names = [t['name'] for t in HEADLESS_TOOLS]
print('Chat tools:', len(chat_names))
print(sorted(chat_names))
print()
print('Headless tools:', len(headless_names))
print(sorted(headless_names))
# Verify old names absent
for old in ['ReadWorkspace', 'WriteWorkspace', 'SearchWorkspace', 'CreateTask', 'Execute', 'Read', 'List', 'Search', 'Edit']:
    if old in chat_names or old in headless_names:
        print(f'FAIL: {old} still registered')
"
```

**Expected:** Chat = 13 tools, Headless = 14 static tools. No old names present.

---

## 11. TP as Agent (ADR-164) — Thinking Partner Identity

### 11.1 TP Agent Record

```sql
SELECT id, title, role, status, scope
FROM agents
WHERE user_id = :'USER_ID' AND role = 'thinking_partner';
```

**Pass if:** 1 row returned with `role='thinking_partner'`.

### 11.2 Back Office Task Dispatched to TP

The task pipeline dispatches `output_kind='system_maintenance'` tasks via `_execute_tp_task()`.

```bash
# Check Render API logs after triggering back-office-agent-hygiene
# Look for: "[TASK_EXEC] TP task: back-office-agent-hygiene"
# Must NOT see: "[TASK_EXEC] No agent found" for TP tasks
```

---

## 12. Render Log Error Gate

After running all tests, check Render logs for the API service (`srv-d5sqotcr85hc73dpkqdg`).

**MUST NOT APPEAR:**

| Pattern | Indicates |
|---------|-----------|
| `ModuleNotFoundError` | Import path broken (api. prefix missing on Render) |
| `NameError: name 'type_config'` | Old PM scope leak (should be gone post-ADR-138) |
| `CHECK constraint.*agents_role_check` | Missing role in DB constraint |
| `PGRST205` / `PGRST301` | PostgREST schema cache stale |
| `KeyError: 'skill'` | Old field name (should be 'role' since ADR-109) |
| `ReadWorkspace\|WriteWorkspace\|CreateTask\|Execute` | Deleted primitive still called |
| `project_slug\|pm_agent\|work_units\|work_plan` | Deleted project-layer references |
| `agent_pulse\|pulse_tier\|composer` | Deleted infrastructure still referenced |

---

## Quick Smoke Test (10 min)

1. **`/work` loads** in list mode — no task pre-selected, filter chips visible
2. **Click `daily-update`** → detail view loads, OutputPreview shows latest HTML
3. **Run Now** on `daily-update` → execution completes, email received at kvkthecreator@gmail.com
4. **`/agents` loads** in roster mode — 9 agents grouped by class, Thinking Partner label renders
5. **Chat: "What tasks are active?"** → TP responds from compact index, no working memory dump
6. **Chat: "Pause track-competitors"** → `ManageTask` called, task status changes in DB
7. **Back office task runs** — `back-office-agent-hygiene` runs without error
8. **Render logs** — no error patterns from the gate above

---

## Results Table

| # | Test | Result | Notes |
|---|------|--------|-------|
| 1 | Roster: 9 agents present + AGENT.md files | | |
| 2 | Essential tasks: 3 present, essential=true | | |
| 3.1 | daily-update: triggers + runs | | |
| 3.2 | daily-update: output folder + manifest | | |
| 3.3 | daily-update: email delivered | | |
| 3.4 | daily-update: next_run_at advances 24h | | |
| 4.1 | competitive-brief: TASK.md has 2-step process | | |
| 4.2 | competitive-brief: step-1/ and step-2/ written | | |
| 4.3 | competitive-brief: manifest has both step sources | | |
| 5.1 | track-competitors: context domain files written | | |
| 5.2 | track-competitors: signals domain also written | | |
| 6.1 | back-office-hygiene: runs without error | | |
| 7.1 | /work list mode: no auto-select | | |
| 7.2 | /work detail mode: kind-correct middle component | | |
| 7.3 | breadcrumb: inline PageHeader, no floating bar | | |
| 8.1 | /agents roster: 3 groups, meta-cognitive label | | |
| 8.2 | /agents detail: IdentityCard + HealthCard | | |
| 9.1 | chat: compact index (not full dump) | | |
| 9.2 | chat: ManageTask pause works | | |
| 9.3 | chat: ManageTask create (not CreateTask) | | |
| 10.1 | grep gate: old primitive names = 0 | | |
| 10.2 | registered primitives: 13 chat / 14 headless | | |
| 11.1 | TP agent record: role=thinking_partner | | |
| 11.2 | back office dispatch: _execute_tp_task logs | | |
| 12 | Render logs: no error patterns | | |

---

*Updated 2026-04-13. Covers ADR-138/141/149/156/161/163/164/166/167/168/176.*
*Supersedes 2026-03-20 version (Projects/PM/Composer/pulse architecture — all deleted).*
