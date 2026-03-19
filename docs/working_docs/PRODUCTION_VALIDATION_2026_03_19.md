# Production Validation Report — 2026-03-19

## Scope

End-to-end validation of ADR-117 P3 (duties, role portfolios, seniority) + ADR-118 (skills, render service, RuntimeDispatch) + ADR-119 (workspace filesystem, output folders, manifests) + ADR-120 (work budget, PM agents, projects) across the live kvkthecreator@gmail.com fleet.

## Critical Bugs Found & Fixed

### 1. `agent_execution.py` — ModuleNotFoundError (SEVERITY: P0)
- **Symptom**: ALL agent runs fail with 500 on production
- **Cause**: Line 51 used `from api.services.agent_framework import ...` — the `api.` prefix doesn't resolve on Render where the working directory IS `api/`
- **Fix**: Changed to `from services.agent_framework import ...`
- **Commit**: `169ec44`
- **Impact**: No agent runs could execute since ADR-117 P3 was deployed (commit `70fb035`)

### 2. `agents_role_check` constraint missing `pm` (SEVERITY: P1)
- **Symptom**: Composer `_execute_create_project()` fails with CHECK constraint violation when creating PM agents
- **Cause**: ADR-120 P1 introduced the `pm` role but the DB CHECK constraint was never updated
- **Fix**: Migration 120 — added `pm` to `agents_role_check`
- **Commit**: `169ec44`
- **Impact**: No projects could be created via Composer

### 3. `workspace.py` `list_duties()` TypeError (SEVERITY: P2)
- **Symptom**: Would crash any code calling list_duties() — `string indices must be integers`
- **Cause**: Treated workspace `list()` results (strings) as dicts
- **Fix**: Changed to iterate strings directly
- **Commit**: `86dd8fe`

### 4. `composer.py` `_execute_promote_duty()` ImportError (SEVERITY: P2)
- **Symptom**: Any Composer duty promotion would crash
- **Cause**: Imported `get_agent_slug` from `agent_creation` instead of `workspace`
- **Fix**: Corrected import path
- **Commit**: `86dd8fe`

### 5. `activity_log` CHECK constraint (SEVERITY: P2)
- **Symptom**: 5 new ADR-117 P3 event types would be rejected by DB
- **Cause**: Python `VALID_EVENT_TYPES` updated but DB constraint was not
- **Fix**: Migration 119
- **Commit**: `86dd8fe`

## Fleet Configuration Applied

### Delivery Gaps Fixed
| Agent | Issue | Fix |
|---|---|---|
| Deep Research: Knowledge Gaps & Unknowns | No destination | Set to kvkthecreator@gmail.com |
| Weekly Slack Summary | No destination | Set to kvkthecreator@gmail.com |

### Test Agent Cleaned Up
- `TEST_ADR118_D3_Output Substrate Agent` — archived (stuck in `generating`, delivers to `test@example.com`)

### Duties JSONB Populated (9 agents)
All agents now have explicit `duties` JSONB, activating the multi-duty path in the scheduler.

| Agent | Role | Seniority | Duties |
|---|---|---|---|
| Slack Recap | digest | senior (12 runs, 100%) | digest(recurring), monitor(reactive) |
| Notion Summary | digest | associate (6 runs, 100%) | digest(recurring) |
| Weekly Cross-Platform Synthesis | synthesize | new | synthesize(recurring) |
| Weekly Analysis: Patterns & Gaps | synthesize | new | synthesize(recurring) |
| Deep Research | research | new | research(goal) |
| Weekly Actionable Insights | prepare | new | prepare(recurring) |
| Insights Consumer & Recommender | custom | new | custom(recurring) |
| Weekly Insights Digest | digest | new | digest(recurring) |
| Weekly Slack Summary | digest | new | digest(recurring) |

Slack Recap also received workspace duty files (`/duties/digest.md`, `/duties/monitor.md`) and updated `AGENT.md` with Duties & Capabilities section.

## Execution Results

### 4 Skill-Eligible Agents Triggered (manual runs via production API)

| Agent | Role | Run ID | Status | Email Sent |
|---|---|---|---|---|
| Weekly Cross-Platform Synthesis | synthesize | `11bad9ac` | delivered | Yes (Resend: `6c80bb89`) |
| Weekly Analysis: Patterns & Gaps | synthesize | `e1d40771` | delivered | Yes (Resend: `64198bec`) |
| Deep Research: Knowledge Gaps & Unknowns | research | `69ca4281` | delivered | Yes (Resend: `fce9ddd8`) |
| Insights Consumer & Recommender | custom | `2857411f` | delivered | Yes (Resend: `acd62e7f`) |

### Pipeline Verification

| Layer | Status | Detail |
|---|---|---|
| Duty resolution | Pass | Agents ran with populated duties JSONB, no errors |
| SKILL.md injection | Pass | Skill-eligible roles received skill docs in system prompt |
| Agent execution | Pass | 4/4 completed without LLM or pipeline errors |
| Workspace output folders | Pass | 8 files created (4 output.md + 4 manifest.json) |
| Manifest structure | Pass | All fields present: run_id, agent_id, version, role, files[], delivery{} |
| Email delivery | Pass | 4/4 delivered via Resend, external_id logged in manifest |
| RuntimeDispatch (renders) | Not triggered | LLM chose text-only output for all 4 runs — expected for current content |
| Work budget | Pass | No budget violations (Free tier: 60 WU/mo) |

### RuntimeDispatch Gap

The render pipeline (skills → RuntimeDispatch → render service → storage → workspace → email attachment) was NOT exercised in this validation because:
- The LLM decides autonomously whether to produce binary artifacts
- For synthesis/research/custom roles processing Slack/Notion content, text-only output is the natural choice
- To force-test renders: either (a) adjust agent instructions to explicitly request charts/PDFs, or (b) create a purpose-built validation agent with instructions like "produce a PDF summary and a chart of activity trends"

## RLS & Grants Verification

### activity_log
- RLS: Enabled, not forced (service_role bypasses)
- Policies: SELECT only (`Users can view own activity` — `auth.uid() = user_id`)
- Grants: `service_role` has full INSERT — correct for write_activity() path
- No INSERT policy needed — all writes use service client

### agents
- `agents_role_check` now includes: digest, prepare, synthesize, monitor, research, act, custom, pm

## Observations for Future Work

1. **RuntimeDispatch validation** — needs a dedicated run with instructions that explicitly request rendered output. Consider adding "include a chart of activity volume" to a synthesize agent's instructions.
2. **Composer `'skill'` KeyError** — seen in scheduler logs (March 18 01:50-02:06). Likely transient LLM hallucination in Composer assessment response — the code consistently uses `role`, not `skill`. Monitor.
3. **Zero approvals** — all 12 Slack Recap runs are `delivered` but none `approved`. The seniority system counts delivered as positive, but explicit user approval/rejection feedback would strengthen the signal.
4. **Seniority is runtime-derived** — no `seniority` column on `agents` table. `classify_seniority()` computes it from run history each time. Consider caching if performance matters at scale.
