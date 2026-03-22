# Production Testing Playbook — ADR-120/121/122/124/125/126

> Comprehensive E2E validation for the shipped agent platform stack.
> Run against production with kvkthecreator@gmail.com fleet.
> Last updated: 2026-03-20.

---

## Pre-Flight Checks

- [ ] API health: `GET https://yarnnn-api.onrender.com/health` → `{"status":"ok"}`
- [ ] All 5 Render services running (API, Unified Scheduler, Platform Sync, MCP Server, Render)
- [ ] `SUPABASE_SERVICE_KEY` available for admin endpoints
- [ ] Test user has: active agents, platform connections, at least one project
- [ ] SQL access via psql (see `docs/database/ACCESS.md`)

### Baseline Snapshot

```sql
-- Take baseline before testing
SELECT 'agents' as entity, COUNT(*) as total,
  COUNT(*) FILTER (WHERE status = 'active') as active
FROM agents WHERE user_id = '{USER_ID}'
UNION ALL
SELECT 'agent_runs', COUNT(*), COUNT(*) FILTER (WHERE status = 'delivered')
FROM agent_runs ar JOIN agents a ON a.id = ar.agent_id WHERE a.user_id = '{USER_ID}'
UNION ALL
SELECT 'work_units', COALESCE(SUM(units_consumed), 0)::int, COUNT(*)::int
FROM work_units WHERE user_id = '{USER_ID}'
  AND created_at >= date_trunc('month', NOW())
UNION ALL
SELECT 'projects', COUNT(*), COUNT(*) FILTER (WHERE path LIKE '%/PROJECT.md')
FROM workspace_files WHERE user_id = '{USER_ID}' AND path LIKE '/projects/%/PROJECT.md';
```

---

## 1. Fresh User Flow — OAuth → Bootstrap → First Pulse → First Run (ADR-110/122/126)

Tests the complete onboarding pipeline: platform connect → auto-bootstrap → project creation → first agent pulse.

### 1.1 Platform Connection + Bootstrap

**Trigger:** Connect a new platform via OAuth (or simulate with existing user + new platform).

**Expected sequence:**
1. OAuth callback → `maybe_bootstrap_project()` called
2. Project created via `scaffold_project(type_key)` — e.g., `slack_digest` for Slack
3. Agent auto-created inside project with `origin=system_bootstrap`
4. First sync completes → `platform_content` rows populated
5. Agent `next_pulse_at` set to near-future

**Verify:**
```sql
-- Check project was scaffolded
SELECT path, LEFT(content, 300) as preview, created_at
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/projects/%/PROJECT.md'
ORDER BY created_at DESC LIMIT 1;

-- Check bootstrap agent created inside project
SELECT a.id, a.title, a.role, a.scope, a.status, a.mode,
  a.next_pulse_at, a.created_at
FROM agents a
WHERE a.user_id = '{USER_ID}'
ORDER BY a.created_at DESC LIMIT 3;

-- Verify type_key uniqueness (no duplicate platform projects)
SELECT path, content
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/projects/%/PROJECT.md'
  AND content LIKE '%type_key: slack_digest%';
```

**Pass if:** PROJECT.md exists with correct `type_key`, agent has `role=digest`, `next_pulse_at` is set.
**Fail if:** No project created, agent created outside project, or duplicate type_key project.

### 1.2 First Pulse Fires

**Trigger:** Wait for scheduler tick (≤5 min) or set `next_pulse_at = NOW()`:

```sql
UPDATE agents SET next_pulse_at = NOW()
WHERE id = '{AGENT_ID}'
RETURNING id, title, role, next_pulse_at;
```

**Expected:**
1. Scheduler picks up agent via `get_due_pulse_agents()`
2. Tier 1 pulse: lightweight check (no LLM call for digest role with 12h cadence)
3. If content available → triggers run
4. `next_pulse_at` advances per `ROLE_PULSE_CADENCE`

**Verify:**
```sql
-- Check pulse advanced
SELECT id, title, role, next_pulse_at, last_run_at
FROM agents WHERE id = '{AGENT_ID}';

-- Check activity log for pulse event
SELECT event_type, summary, metadata, created_at
FROM activity_log
WHERE user_id = '{USER_ID}'
  AND event_type IN ('agent_pulse', 'agent_pulse_skip', 'agent_run')
ORDER BY created_at DESC LIMIT 5;
```

**Pass if:** `next_pulse_at` advanced, activity_log has pulse event.
**Fail if:** `next_pulse_at` unchanged, no activity log entry, or error in logs.

---

## 2. Pulse Funnel — Tier 1/2/3 Validation (ADR-126)

Tests the three-tier pulse decision pipeline: cheap heuristic → Haiku triage → full generation.

### 2.1 Tier 1 — Heuristic Skip (No Content Change)

**Setup:** Run an agent, then immediately set `next_pulse_at = NOW()` again (no new content since last run).

```sql
-- After a successful run, force immediate re-pulse
UPDATE agents SET next_pulse_at = NOW()
WHERE id = '{AGENT_ID}'
RETURNING id, title, last_run_at;
```

**Expected:** Tier 1 heuristic detects no new content → skips without LLM call.

**Verify:**
```sql
SELECT event_type, summary, metadata->>'tier' as tier, metadata->>'decision' as decision
FROM activity_log
WHERE user_id = '{USER_ID}'
  AND event_ref = '{AGENT_ID}'
  AND event_type IN ('agent_pulse', 'agent_pulse_skip')
ORDER BY created_at DESC LIMIT 3;
```

**Pass if:** `agent_pulse_skip` event with tier=1, decision=skip.
**Fail if:** Full generation triggered (wasted LLM call), or no event logged.

### 2.2 Tier 2 — Haiku Triage (New Content, Ambiguous)

**Setup:** Ensure fresh platform_content exists since last run, for a `monitor` role agent (15min cadence).

**Expected:** Tier 1 passes (content changed) → Tier 2 Haiku assesses → decides generate or skip.

**Verify:**
```sql
SELECT event_type, summary,
  metadata->>'tier' as tier,
  metadata->>'decision' as decision,
  metadata->>'reason' as reason
FROM activity_log
WHERE user_id = '{USER_ID}'
  AND event_type LIKE 'agent_pulse%'
ORDER BY created_at DESC LIMIT 5;
```

**Pass if:** Tier 2 event logged with Haiku decision and reasoning.
**Fail if:** Tier 2 skipped entirely, or Haiku call errors.

### 2.3 Tier 3 — Full Generation

**Trigger:** Either via Tier 2 approve, or manual `POST /api/agents/{id}/run`.

**Verify:**
```sql
-- Check run completed
SELECT version_number, status, delivery_status, draft_content IS NOT NULL as has_draft,
  created_at
FROM agent_runs
WHERE agent_id = '{AGENT_ID}'
ORDER BY version_number DESC LIMIT 1;

-- Check output folder created (ADR-119)
SELECT path, lifecycle, version, updated_at
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/agents/%/outputs/%'
ORDER BY updated_at DESC LIMIT 5;

-- Check manifest
SELECT path, LEFT(content, 500) as manifest_preview
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '%/manifest.json'
ORDER BY updated_at DESC LIMIT 1;
```

**Pass if:** Run delivered, output folder + manifest.json created with correct structure.
**Fail if:** Run stuck in `generating`, no output folder, or manifest missing.

### 2.4 Role-Based Pulse Cadence Verification

**Expected cadences** (from `ROLE_PULSE_CADENCE`):

| Role | Cadence | Next Pulse After Run |
|------|---------|---------------------|
| monitor | 15 min | last_run + 15min |
| pm | 30 min | last_run + 30min |
| digest | 12 hours | last_run + 12h |
| prepare | 12 hours | last_run + 12h |
| synthesize | schedule | per agent schedule |
| research | schedule | per agent schedule |
| custom | schedule | per agent schedule |

```sql
-- Verify cadence alignment
SELECT a.id, a.title, a.role,
  a.next_pulse_at,
  a.last_run_at,
  EXTRACT(EPOCH FROM (a.next_pulse_at - a.last_run_at)) / 60 as minutes_between
FROM agents a
WHERE a.user_id = '{USER_ID}' AND a.status = 'active'
ORDER BY a.role;
```

**Pass if:** Each role's `next_pulse_at - last_run_at` matches expected cadence (±5min tolerance).
**Fail if:** Cadence misaligned or `next_pulse_at` NULL for active agents.

---

## 3. Project Execution — PM Intelligence Loop (ADR-120/121)

Tests the full project lifecycle: creation → PM heartbeat → contributor steering → assembly.

### 3.1 Project Creation via Composer or API

**Trigger:** Create a multi-agent project:

```bash
curl -s -X POST "https://yarnnn-api.onrender.com/projects" \
  -H "Authorization: Bearer {JWT}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Weekly Intelligence Report",
    "type_key": "cross_platform_synthesis",
    "objective": {
      "deliverable": "Weekly intelligence report",
      "audience": "Founder",
      "format": "pptx",
      "purpose": "Strategic awareness"
    },
    "delivery": {"channel": "email", "target": "kvkthecreator@gmail.com"}
  }' | python3 -m json.tool
```

**Verify:**
```sql
-- PROJECT.md written
SELECT path, LEFT(content, 500) as preview
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/projects/%/PROJECT.md'
ORDER BY created_at DESC LIMIT 1;

-- PM agent auto-created
SELECT id, title, role, status, next_pulse_at
FROM agents
WHERE user_id = '{USER_ID}' AND role = 'pm'
ORDER BY created_at DESC LIMIT 1;

-- Contributors linked
SELECT path
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/projects/%/contributions/%'
ORDER BY path;
```

**Pass if:** PROJECT.md has objective, PM agent created with `role=pm`, contributor folders exist.
**Fail if:** No PM, missing objective fields, `agents_role_check` constraint violation.

### 3.2 PM Heartbeat — First Run (update_work_plan)

**Trigger:** Force PM pulse:
```sql
UPDATE agents SET next_pulse_at = NOW(), last_run_at = NULL
WHERE id = '{PM_AGENT_ID}' RETURNING id, title;
```

**Expected:** First PM run should produce `update_work_plan` action (no work plan exists yet).

**Verify:**
```sql
-- PM run completed
SELECT version_number, status, LEFT(draft_content, 300) as decision_preview
FROM agent_runs
WHERE agent_id = '{PM_AGENT_ID}'
ORDER BY version_number DESC LIMIT 1;

-- Work plan written to PM memory
SELECT path, LEFT(content, 500) as preview
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/agents/%pm%/memory/work_plan.md'
ORDER BY updated_at DESC LIMIT 1;

-- Activity log
SELECT event_type, summary, metadata->>'action' as pm_action
FROM activity_log
WHERE event_ref = '{PM_AGENT_ID}'
ORDER BY created_at DESC LIMIT 3;
```

**Pass if:** PM produced valid JSON with `update_work_plan` action, `work_plan.md` written.
**Fail if:** PM produced markdown instead of JSON, `NameError` on `type_config`, or work plan missing.

### 3.3 PM Steering — Contribution Briefs (ADR-121)

**Trigger:** Run PM again after work plan exists.

**Expected:** PM should `assess_quality` or `steer_contributor` — writing briefs to guide contributors.

**Verify:**
```sql
-- Check for contribution briefs
SELECT path, LEFT(content, 300) as brief_preview
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/projects/%/contributions/%/brief.md'
ORDER BY path;

-- Check PM decision was steer or assess
SELECT event_type, summary, metadata->>'action' as pm_action
FROM activity_log
WHERE event_ref = '{PM_AGENT_ID}'
  AND event_type IN ('project_pm_decision', 'agent_run')
ORDER BY created_at DESC LIMIT 3;
```

**Pass if:** Brief.md written with focus areas, PM action was `steer_contributor` or `assess_quality`.
**Fail if:** PM only does `update_work_plan` repeatedly (stuck loop), or brief is empty.

### 3.4 Assembly Execution

**Trigger:** PM decides `assemble` (all contributors fresh, work plan satisfied).

**Expected sequence:**
1. PM produces `assemble` action
2. Contribution gathering: reads contributor output folders
3. Assembly composition: LLM integrates contributions
4. If format=pptx: RenderAsset → render service → PPTX
5. Upload to Supabase Storage
6. Manifest written with sources + delivery status
7. Email delivery via Resend

**Verify:**
```sql
-- Assembly output folder
SELECT path, lifecycle, LEFT(content, 200) as preview
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/projects/%/outputs/%'
ORDER BY updated_at DESC LIMIT 5;

-- Manifest with delivery info
SELECT path, content
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/projects/%/outputs/%/manifest.json'
ORDER BY updated_at DESC LIMIT 1;

-- Render usage (if PPTX/chart produced)
SELECT skill_name, status, file_size, created_at
FROM render_usage
WHERE user_id = '{USER_ID}'
ORDER BY created_at DESC LIMIT 3;

-- Work units consumed
SELECT action_type, units_consumed, agent_id, created_at
FROM work_units
WHERE user_id = '{USER_ID}'
ORDER BY created_at DESC LIMIT 10;
```

**Pass if:** Assembly output exists, manifest has sources + delivery, work_units recorded for assembly + render.
**Fail if:** Assembly empty, no manifest, render failed, or work_units not tracked.

---

## 4. Meeting Room — ChatAgent + @-mentions (ADR-124)

Tests the project meeting room: agent-attributed chat, PM routing, @-mentions.

### 4.1 Project Session Creation

**Trigger:** Send a message in a project-scoped chat session.

```bash
curl -s -X POST "https://yarnnn-api.onrender.com/api/chat" \
  -H "Authorization: Bearer {JWT}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the current status of this project?",
    "project_slug": "{SLUG}",
    "target_agent_id": "{PM_AGENT_ID}"
  }' --no-buffer
```

**Expected:**
1. Session created with `agent_id` pointing to PM
2. PM responds (not TP) using `PM_CHAT_PROMPT`
3. SSE `stream_start` event includes author attribution
4. `session_messages.metadata` has `author_agent_id`, `author_agent_slug`, `author_role`

**Verify:**
```sql
-- Session created with project context
SELECT cs.id, cs.agent_id, cs.created_at,
  a.title as agent_title, a.role as agent_role
FROM chat_sessions cs
LEFT JOIN agents a ON a.id = cs.agent_id
WHERE cs.user_id = '{USER_ID}'
ORDER BY cs.created_at DESC LIMIT 3;

-- Messages have author attribution
SELECT sm.role, sm.metadata->>'author_agent_slug' as author,
  sm.metadata->>'author_role' as author_role,
  LEFT(sm.content, 200) as preview
FROM session_messages sm
JOIN chat_sessions cs ON cs.id = sm.session_id
WHERE cs.user_id = '{USER_ID}'
ORDER BY sm.created_at DESC LIMIT 5;
```

**Pass if:** PM responds with project-aware content, author attribution in metadata.
**Fail if:** TP responds instead of PM, no author attribution, or session not scoped to project.

### 4.2 @-mention Routing to Contributors

**Trigger:** Send a message with `@{contributor-slug}` mention in project chat.

**Expected:** Message routed to the mentioned contributor agent (not PM).

**Verify:** Check `session_messages.metadata.author_agent_slug` matches the mentioned agent.

**Pass if:** Contributor agent responds with role-appropriate content.
**Fail if:** PM intercepts the message, or routing fails with 500.

### 4.3 ChatAgent Primitive Availability

**Expected:** `agent_chat` mode exposes 13 primitives (subset of chat + headless).

```sql
-- Verify via run metadata (if logged)
SELECT metadata->>'mode' as mode, metadata->>'tools_available' as tools
FROM agent_runs
WHERE agent_id = '{PM_AGENT_ID}'
ORDER BY version_number DESC LIMIT 1;
```

---

## 5. Work Budget Enforcement (ADR-120)

Tests that autonomous work is bounded per user per billing period.

### 5.1 Budget Tracking

**Verify current budget state:**
```sql
SELECT action_type, SUM(units_consumed) as total_units, COUNT(*) as actions
FROM work_units
WHERE user_id = '{USER_ID}'
  AND created_at >= date_trunc('month', NOW())
GROUP BY action_type
ORDER BY total_units DESC;
```

### 5.2 Budget Gate on Agent Run

**Expected:** Scheduler checks `check_work_budget()` before each run. If budget exhausted → agent skipped with escalation.

**Simulate budget exhaustion (CAUTION — production):**
```sql
-- Check current usage vs limit
SELECT
  (SELECT COALESCE(SUM(units_consumed), 0) FROM work_units
   WHERE user_id = '{USER_ID}'
     AND created_at >= date_trunc('month', NOW())) as used,
  CASE WHEN w.subscription_status = 'pro' THEN 1000 ELSE 60 END as limit
FROM workspaces w
WHERE w.user_id = '{USER_ID}';
```

**Pass if:** Work units increment after each run/assembly/render action.
**Fail if:** Work units not tracked, or budget-exceeded agent still runs.

### 5.3 Budget Escalation

**Expected:** When budget is exhausted, PM action should be `escalate` with reason `budget_exhausted`.

**Verify:**
```sql
SELECT event_type, summary, metadata->>'action' as action, metadata->>'reason' as reason
FROM activity_log
WHERE user_id = '{USER_ID}'
  AND event_type = 'project_pm_decision'
  AND metadata->>'action' = 'escalate'
ORDER BY created_at DESC LIMIT 3;
```

---

## 6. Project Type Registry — Bootstrap + Uniqueness (ADR-122)

Tests that project creation flows through the unified registry.

### 6.1 Bootstrap Creates Correct Type

```sql
-- Verify type_key on all projects
SELECT
  SUBSTRING(content FROM 'type_key: (.+)') as type_key,
  path
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/projects/%/PROJECT.md';
```

**Expected type_keys:**
| Platform | Type Key |
|----------|----------|
| Slack | `slack_digest` |
| Notion | `notion_digest` |
| Cross-platform | `cross_platform_synthesis` |
| Custom | `custom` |

### 6.2 Uniqueness Enforcement

**Trigger:** Try to create a second `slack_digest` project (should be blocked).

**Pass if:** Second creation rejected or skipped.
**Fail if:** Duplicate platform project created.

### 6.3 Scaffold Completeness

**For each scaffolded project, verify:**
```sql
-- PROJECT.md exists
SELECT COUNT(*) FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/projects/%/PROJECT.md';

-- Agent created inside project
SELECT a.title, a.role, a.scope, a.status
FROM agents a
WHERE a.user_id = '{USER_ID}'
  AND EXISTS (
    SELECT 1 FROM workspace_files wf
    WHERE wf.user_id = '{USER_ID}'
      AND wf.path LIKE '/projects/%/contributions/' || REPLACE(LOWER(a.title), ' ', '-') || '/%'
  );
```

---

## 7. Composer Integration — Pulse Escalation + Project Awareness (ADR-126/120)

Tests that Composer receives pulse escalations and has budget/project awareness.

### 7.1 Pulse Escalation to Composer

**Trigger:** An agent pulse escalation should appear in Composer's assessment data.

```sql
-- Check for pulse escalation events
SELECT event_type, summary, event_ref, metadata, created_at
FROM activity_log
WHERE user_id = '{USER_ID}'
  AND event_type = 'agent_pulse_escalation'
ORDER BY created_at DESC LIMIT 5;
```

**Expected:** `should_composer_act()` returns `True` with reason `pulse_escalation` when escalation events exist.

### 7.2 Composer Assessment Completeness

**Verify assessment has all required fields:**
```sql
-- Trigger assessment via admin or wait for heartbeat
-- Then check activity_log for composer event
SELECT event_type, summary,
  metadata->>'reason' as reason,
  metadata->>'should_act' as should_act,
  metadata->'assessment'->'pulse_health' as pulse_health,
  metadata->'assessment'->'workspace_density' as density
FROM activity_log
WHERE user_id = '{USER_ID}'
  AND event_type IN ('composer_assessment', 'composer_heartbeat')
ORDER BY created_at DESC LIMIT 1;
```

**Required assessment fields:** `connected_platforms`, `agents`, `knowledge`, `maturity`, `coverage`, `pulse_health`, `workspace_density`, `feedback`, `health`, `tier`, `total_agent_runs`, `agent_graph`.

### 7.3 Composer Project Creation

**Expected:** When Composer identifies a cross-platform opportunity, it can `create_project` via `_execute_create_project()` → `scaffold_project()`.

---

## 8. Seniority & Duty Progression (ADR-117 Phase 3)

Tests the feedback-gated developmental model.

### 8.1 Seniority Classification

```sql
-- Verify seniority for all agents
SELECT a.id, a.title, a.role,
  COUNT(ar.id) as total_runs,
  COUNT(ar.id) FILTER (WHERE ar.status = 'delivered') as delivered,
  COUNT(ar.id) FILTER (WHERE ar.user_approved = true) as approved,
  CASE
    WHEN COUNT(ar.id) >= 10 AND
         COUNT(ar.id) FILTER (WHERE ar.user_approved = true)::float /
         NULLIF(COUNT(ar.id) FILTER (WHERE ar.status = 'delivered'), 0) >= 0.8
    THEN 'senior'
    WHEN COUNT(ar.id) >= 5 AND
         COUNT(ar.id) FILTER (WHERE ar.user_approved = true)::float /
         NULLIF(COUNT(ar.id) FILTER (WHERE ar.status = 'delivered'), 0) >= 0.6
    THEN 'associate'
    ELSE 'new'
  END as expected_seniority
FROM agents a
LEFT JOIN agent_runs ar ON ar.agent_id = a.id
WHERE a.user_id = '{USER_ID}' AND a.status = 'active'
GROUP BY a.id ORDER BY total_runs DESC;
```

### 8.2 Duty Portfolio Validation

```sql
-- Check duties JSONB populated
SELECT id, title, role, duties,
  jsonb_array_length(COALESCE(duties, '[]'::jsonb)) as duty_count
FROM agents
WHERE user_id = '{USER_ID}' AND status = 'active'
ORDER BY role;
```

**Expected per `ROLE_PORTFOLIOS`:**

| Role | New Duties | Associate Adds | Senior Adds |
|------|-----------|---------------|------------|
| digest | digest(recurring) | monitor(reactive) | synthesize(reactive) |
| synthesize | synthesize(recurring) | research(goal) | — |
| research | research(goal) | synthesize(recurring) | — |
| monitor | monitor(reactive) | digest(recurring) | — |
| pm | — | — | — |

### 8.3 Duty Promotion by Composer

**Trigger:** Composer `promote_duty` action for an associate/senior agent.

**Verify:**
```sql
-- Check duties column updated
SELECT id, title, role, duties
FROM agents WHERE id = '{AGENT_ID}';

-- Check workspace duty file created
SELECT path, LEFT(content, 200) as preview
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '/agents/%/duties/%'
ORDER BY path;
```

---

## 9. Feedback Substrate (ADR-117 Phases 1-2)

Cross-reference with `docs/testing/adr-117-feedback-substrate-tests.md` for detailed test steps.

### 9.1 Self-Observation on Run

```sql
SELECT path, LEFT(content, 300) as preview, updated_at
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '%/memory/observations.md'
ORDER BY updated_at DESC LIMIT 3;
```

**Pass if:** `(self)` entries with topics and source coverage after each run.

### 9.2 Preferences Distillation on Edit

**Trigger:** PATCH a run's `final_content`.

```sql
SELECT path, LEFT(content, 300) as preview, updated_at
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path LIKE '%/memory/preferences.md'
ORDER BY updated_at DESC LIMIT 3;
```

**Pass if:** Structured preferences with `# User Preferences` header.

### 9.3 Workspace Context Loading

```sql
SELECT version_number, metadata->'sources_used' as sources
FROM agent_runs
WHERE agent_id = '{AGENT_ID}'
ORDER BY version_number DESC LIMIT 1;
```

**Pass if:** `sources_used` includes `"workspace"`.

---

## 10. Cross-Cutting Verification

### 10.1 Activity Log Event Types

All these event types should appear in activity_log over a full test cycle:

```sql
SELECT event_type, COUNT(*) as occurrences, MAX(created_at) as latest
FROM activity_log
WHERE user_id = '{USER_ID}'
  AND created_at > NOW() - INTERVAL '1 day'
GROUP BY event_type
ORDER BY latest DESC;
```

**Expected event types:**
- `agent_run` — agent execution
- `agent_pulse` / `agent_pulse_skip` — pulse tier decisions
- `agent_pulse_escalation` — budget or failure escalation
- `project_pm_decision` — PM action (update_work_plan, steer, assess, assemble, escalate)
- `project_assembly` — assembly completed
- `composer_heartbeat` / `composer_assessment` — Composer cycle
- `platform_synced` — sync events
- `bootstrap_project` — auto-scaffolded project

### 10.2 No Error Patterns in Logs

Check Render logs for these MUST-NOT-APPEAR patterns:

| Pattern | Indicates |
|---------|-----------|
| `ModuleNotFoundError` | Import path broken (api. prefix on Render) |
| `NameError: name 'type_config'` | PM scope variable leak |
| `CHECK constraint.*agents_role_check` | Missing role in DB constraint |
| `PGRST205` / `PGRST301` | PostgREST schema cache stale |
| `KeyError: 'skill'` | Old field name (should be 'role') |

### 10.3 Workspace File Integrity

```sql
-- Check for orphaned files (no parent agent/project)
SELECT path, lifecycle, updated_at
FROM workspace_files
WHERE user_id = '{USER_ID}'
  AND path NOT LIKE '/agents/%'
  AND path NOT LIKE '/projects/%'
  AND path NOT LIKE '/knowledge/%'
  AND path NOT LIKE '/working/%'
  AND path NOT LIKE '/user_shared/%'
ORDER BY updated_at DESC;

-- Check lifecycle distribution
SELECT lifecycle, COUNT(*) as files
FROM workspace_files
WHERE user_id = '{USER_ID}'
GROUP BY lifecycle;
```

---

## Quick Smoke Test (10 min)

If short on time, these 8 checks cover critical paths:

1. **Load `/agents`** — agents list renders, roles display correctly
2. **Load `/projects`** — projects list renders, type badges correct
3. **Click into a project** — meeting room loads, PM is default interlocutor
4. **Trigger "Run Now"** on an agent — execution completes, output folder created
5. **Check work_units** — units recorded for the run
6. **Check `next_pulse_at`** — advanced per role cadence after run
7. **Check Render logs** — no `NameError`, `ModuleNotFoundError`, or `PGRST` errors
8. **Send meeting room message** — PM responds with author attribution

---

## Results Template

| # | Test | Result | Notes |
|---|------|--------|-------|
| 1.1 | Bootstrap project creation | | |
| 1.2 | First pulse fires | | |
| 2.1 | Tier 1 heuristic skip | | |
| 2.2 | Tier 2 Haiku triage | | |
| 2.3 | Tier 3 full generation | | |
| 2.4 | Role-based cadence | | |
| 3.1 | Project creation | | |
| 3.2 | PM first run (work_plan) | | |
| 3.3 | PM steering (briefs) | | |
| 3.4 | Assembly execution | | |
| 4.1 | Project session + PM routing | | |
| 4.2 | @-mention routing | | |
| 4.3 | ChatAgent primitives | | |
| 5.1 | Budget tracking | | |
| 5.2 | Budget gate | | |
| 5.3 | Budget escalation | | |
| 6.1 | Bootstrap type_key | | |
| 6.2 | Uniqueness enforcement | | |
| 6.3 | Scaffold completeness | | |
| 7.1 | Pulse escalation to Composer | | |
| 7.2 | Assessment completeness | | |
| 7.3 | Composer project creation | | |
| 8.1 | Seniority classification | | |
| 8.2 | Duty portfolio | | |
| 8.3 | Duty promotion | | |
| 9.1 | Self-observation | | |
| 9.2 | Preferences distillation | | |
| 9.3 | Workspace context loading | | |
| 10.1 | Activity log events | | |
| 10.2 | No error patterns | | |
| 10.3 | Workspace integrity | | |

---

*Scaffolded 2026-03-20. Covers ADR-120/121/122/124/125/126 + cross-cutting ADR-117/119.*
