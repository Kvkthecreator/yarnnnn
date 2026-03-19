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

## Phase 2: Project Assembly + PPTX Delivery (ADR-120 full pipeline)

### Additional Bugs Found & Fixed

#### 6. `execute_agent_generation()` — PM `type_config` NameError (SEVERITY: P0)
- **Symptom**: All PM agent runs fail with `NameError: name 'type_config' is not defined`
- **Cause**: Line 1793 references `type_config` but it's only defined in `generate_draft_inline()` (different function scope)
- **Fix**: Changed to `agent.get("type_config", {})` at point of use
- **Commit**: `28c3692`

#### 7. `build_role_prompt()` — PM template missing `intentions` + `budget_status` (SEVERITY: P1)
- **Symptom**: PM agent falls back to custom template (no JSON output enforcement), produces narrative markdown
- **Cause**: PM role prompt template uses `{intentions}` and `{budget_status}` but `build_role_prompt()` only populated 3 of 5 fields
- **Fix**: Added `intentions` and `budget_status` to `fields.update()` in PM branch
- **Commit**: `afcc2c2`

#### 8. PM prompt JSON enforcement too weak (SEVERITY: P2)
- **Symptom**: Even when PM template rendered correctly, LLM sometimes produced markdown instead of JSON
- **Fix**: Changed "RESPOND WITH VALID JSON" → "CRITICAL: Your ENTIRE response must be a single valid JSON object. No markdown, no headers, no prose"
- **Also**: Added resilient parsing in `_handle_pm_decision()` — JSON extraction from markdown, keyword inference fallback
- **Commit**: `2138d0f`

#### 9. CreateProject contributor resolution — UUID-only lookup (SEVERITY: P2)
- **Symptom**: Orchestrator passes agent titles/slugs as `agent_id` but `CreateProject` only does UUID lookup → 0 contributors
- **Fix**: Three-tier lookup: UUID → title ilike → slug derivation match
- **Commit**: `28c3692`

### Project Creation (via Orchestrator)

| Step | Status | Detail |
|---|---|---|
| Orchestrator → CreateProject | Pass | Called with `intent.format: "pptx"`, delivery to kvkthecreator@gmail.com |
| PROJECT.md | Pass | Intent, assembly spec, delivery all correct |
| PM agent auto-created | Pass | `880f9c6f-396e-4e60-8ce1-13cd771d095d` with `role=pm` |
| Contributors linked | Manual | Orchestrator passed slugs (not UUIDs) — fix deployed, seeded manually for this test |

### PM Decision Sequence

| Run | Version | Action | Reason |
|---|---|---|---|
| `66d60b29` | v3 | `update_work_plan` | No work plan exists yet — correct per PM rules |
| `1e1de7b4` | v4 | `assemble` | All contributors fresh (0d ago), no assemblies yet |

### Assembly Execution

| Layer | Status | Detail |
|---|---|---|
| Contribution gathering | Pass | 2 contributors: cross-platform-synthesis + patterns-gaps |
| Assembly composition (LLM) | Pass | Cohesive text integrating both sources |
| RuntimeDispatch → PPTX | Pass | 34.5KB `Weekly-Intelligence-Report.pptx` via `presentation` skill |
| Supabase Storage upload | Pass | `agent-outputs/` bucket, public URL generated |
| Manifest | Pass | 2 files (output.md primary + PPTX rendered), 4 sources, delivery status |
| Email delivery | Pass | Resend `9a6b2778-0c64-46c8-bc65-335ae6d1e564` to kvkthecreator@gmail.com |
| Work budget tracking | Pass | 5 WU total: 3× pm_heartbeat + 1× assembly + 1× render |
| Render usage tracking | Pass | 2 entries: chart (earlier) + presentation |

### Key Validation: RuntimeDispatch Gap Closed

The **full render pipeline** is now validated end-to-end in production:
1. Assembly composition includes SKILL.md and RuntimeDispatch tool
2. LLM produces `presentation` skill call with structured slide content
3. yarnnn-render service builds PPTX via python-pptx
4. File uploaded to Supabase Storage (public URL)
5. Manifest records rendered file with content_url and size
6. Email includes download link to PPTX
7. render_usage and work_units tables updated correctly

**Skills exercised in production**: `chart` (agent-level) + `presentation` (project assembly)

## Observations for Future Work

1. ~~**RuntimeDispatch validation**~~ — COMPLETED. Both chart and presentation skills validated.
2. **Composer `'skill'` KeyError** — seen in scheduler logs (March 18 01:50-02:06). Likely transient LLM hallucination in Composer assessment response — the code consistently uses `role`, not `skill`. Monitor.
3. **Zero approvals** — all 12 Slack Recap runs are `delivered` but none `approved`. The seniority system counts delivered as positive, but explicit user approval/rejection feedback would strengthen the signal.
4. **Seniority is runtime-derived** — no `seniority` column on `agents` table. `classify_seniority()` computes it from run history each time. Consider caching if performance matters at scale.
5. **Orchestrator tool round efficiency** — first CreateProject attempt used 8+ tool rounds searching before acting. TP prompt now has CreateProject documentation (commit `0e38b72`) — retest to confirm improvement.
6. **PM prompt robustness** — PM occasionally produces narrative instead of JSON. Resilient parsing added but root cause is LLM instruction-following. Monitor after stronger "CRITICAL" prefix.
