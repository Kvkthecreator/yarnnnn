# ADR-156: Single Intelligence Layer — Composer Sunset + Memory/Session In-Session

**Status:** Implemented (Phase 1: Composer sunset + Phase 2: Memory/session dissolution)
**Date:** 2026-04-03
**Supersedes:** ADR-111 (Agent Composer), ADR-114 (Composer Substrate-Aware Assessment)
**Partially supersedes:** ADR-064 (Unified Memory Service — nightly cron removed), ADR-126 (Agent Pulse — Composer portions)
**Related:** ADR-138 (Agents as Work Units), ADR-141 (Unified Execution Architecture), ADR-144 (Inference-First Shared Context), ADR-155 (Workspace Inference Onboarding)

---

## Context

### The Problem: Two Intelligence Layers

YARNNN has two systems that make LLM-driven judgment calls about workforce composition:

1. **TP (Thinking Partner)** — Sonnet, in-conversation. Creates agents, creates tasks, evaluates output, steers work. User sees every decision.

2. **Composer** (`api/services/composer.py`) — Haiku, background cron. Assesses workspace health, creates agents autonomously, pauses underperformers. User discovers decisions post-hoc via activity log.

This dual-intelligence model was established in ADR-111 when TP lacked workforce management primitives. Since then:
- ADR-138 gave TP `CreateTask`, `ManageTask` (evaluate/steer/complete)
- ADR-140 pre-scaffolded the agent roster (no creation needed at cold start)
- ADR-144 gave TP graduated context awareness (identity/brand/domains/tasks)
- ADR-155 gave TP `ManageDomains` for workspace-wide inference

TP now has full workforce management capability. Composer is a second intelligence layer making strategic decisions the user never sees happening.

### The Principle: Single Intelligence Layer

ADR-155 established that "TP is the single intelligence layer" when it eliminated `workspace_inference.py` (a background Haiku service making domain scaffolding decisions). The same principle applies to Composer — an LLM making workforce composition judgments outside the user's view violates single-intelligence-layer.

This is the same model Claude Code follows: all judgment happens in the conversation where the user can see, correct, and redirect. Nothing reorganizes your workspace overnight.

### What Composer Actually Does Today

| Function | LLM? | Verdict |
|----------|-------|---------|
| `heartbeat_data_query()` — workspace health assessment | No (pure SQL) | Absorb into working memory |
| `should_composer_act()` — 13 heuristic triggers | No (pure logic) | Delete (TP has workspace_state) |
| `_llm_composer_assessment()` — "should I create an agent?" | Yes (Haiku) | **Delete** — judgment moves to TP |
| `_execute_composer_decisions()` — autonomous agent creation | No (executes LLM decision) | **Delete** — TP creates via primitives |
| `run_lifecycle_assessment()` — pause underperformers | No (deterministic) | Move to scheduler as zero-LLM rule |
| `maybe_trigger_heartbeat()` — event-driven LLM trigger | Triggers LLM | **Delete** |

### Three Clean Layers

After this change, the architecture has three layers with no overlap:

```
SCHEDULER (Layer 1) — mechanical, zero LLM
  - Task scheduling: query tasks.next_run_at, fire execute_task()
  - System hygiene: pause underperformers, clean expired files
  - Memory extraction: nightly fact distillation (Haiku, extractive — not judgment)

TASK PIPELINE (Layer 2) — generation, Sonnet
  - execute_task(): read TASK.md -> gather context -> generate -> deliver
  - This IS the proactive loop. Recurring tasks = recurring intelligence.

TP (Layer 3) — orchestration, single intelligence
  - All judgment: create tasks, evaluate output, steer agents,
    suggest improvements, surface gaps — ALWAYS in conversation
  - Receives workspace health signals in working memory
  - Surfaces suggestions when user is present. User decides.
```

---

## Decision

### 1. Delete Composer

Delete `api/services/composer.py` and `api/test_adr111_composer.py` entirely.

Remove all call sites:
- `unified_scheduler.py`: remove `run_heartbeat` import and heartbeat loop
- `agent_execution.py`: remove `maybe_trigger_heartbeat` call after delivery

### 2. Absorb Two Signals into Working Memory

Enrich `working_memory.py` with two signals Composer uniquely computed that TP needs:

**Work budget status:**
```python
"work_budget": {
    "used": 42,
    "limit": 60,       # -1 = unlimited
    "exhausted": False
}
```

**Agent health flags** (per-agent approval rates for underperformer awareness):
```python
"agent_health": [
    {"title": "Weekly Briefing", "slug": "weekly-briefing", "approval_rate": 0.25, "run_count": 10, "flag": "underperforming"},
]
# Only agents with flag != "healthy" shown, to keep token budget tight
```

Both are pure SQL queries — no LLM cost.

### 3. Extract Deterministic Lifecycle Rule to Scheduler

The underperformer pause rule is mechanical:
- Agent has >= 8 runs AND < 30% approval rate AND is NOT user-configured
- Action: set `status = 'paused'`, write coaching note to feedback.md
- This is system hygiene, same as workspace file cleanup — belongs in scheduler

Add to `unified_scheduler.py` as a lightweight function (~30 lines). Runs once per scheduler cycle. Zero LLM.

### 4. TP Surfaces Suggestions in Conversation

Instead of Composer autonomously creating agents, TP sees workspace health signals and surfaces suggestions conversationally:

**Before (Composer):** Background Haiku decides "create an analyst agent" -> agent appears without user knowledge.

**After (TP):** Working memory shows `agent_health: [{flag: "underperforming", ...}]`. TP says: "Your Weekly Briefing task has had low approval (25% over 10 runs). Want me to pause it or adjust the deliverable spec?" User decides.

No new TP prompt section needed — the context awareness prompt (ADR-144) already guides TP to surface gaps based on working memory signals.

---

### Phase 2: Memory and Session Dissolution

Nightly Haiku cron jobs for memory extraction and session summaries are removed.
TP handles both in-session, following the Claude Code model.

**Memory extraction dissolved:**
- Before: Nightly cron → Haiku reads yesterday's sessions → extracts facts → writes notes.md
- After: TP proactively saves facts via `UpdateContext(target="memory")` during conversation
- Prompt guidance added to `tp_prompts/onboarding.py` ("In-Session Memory" section)
- `memory.py` retained for bulk import use only

**Session summaries dissolved:**
- Before: Nightly cron → Haiku summarizes yesterday's sessions → writes chat_sessions.summary
- After: Inline summary at session close (already exists in `chat.py:372`)
- Session continuity: TP writes shift notes to AWARENESS.md (already documented)

**Dead code removed:**
- `_get_work_index_sync()` in working_memory.py (WORK.md reader — dead post ADR-132)
- Nightly memory/session cron block in unified_scheduler.py (~110 lines)

---

## What This Does NOT Change

- **Task scheduling** — unchanged, Layer 1 mechanical
- **Task pipeline** — unchanged, Layer 2 generation
- **Context inference** — unchanged, TP-driven via UpdateContext
- **Agent roster** — unchanged, pre-scaffolded at signup (ADR-140)
- **Working memory structure** — extended with two new signals, not restructured

---

## Deferred Questions

These are real tensions surfaced during this decision. They are easier to design from the clean single-intelligence-layer foundation:

| Question | Context |
|----------|---------|
| Should TP have a periodic heartbeat (background, no user)? | If yes, TP becomes a background actor — different from "single intelligence in conversation" |
| How does the task pipeline report back to TP? | Tasks execute in isolation. TP doesn't know a task failed until user asks |
| Should evaluation be automatic (post-run) or user-initiated? | `ManageTask(evaluate)` exists but nothing triggers it automatically |

---

## Migration Plan

### Phase 1: Delete Composer (this ADR)

1. Delete `api/services/composer.py`
2. Delete `api/test_adr111_composer.py`
3. Remove `run_heartbeat` import + loop from `unified_scheduler.py`
4. Remove `maybe_trigger_heartbeat` call from `agent_execution.py`
5. Add work budget + agent health signals to `working_memory.py`
6. Add deterministic underperformer pause to `unified_scheduler.py`
7. Mark ADR-111 as superseded by ADR-156

### Phase 3: MEMORY.md Profile Deprecation + Import Jobs Table Drop

1. Remove MEMORY.md alias from workspace.py — IDENTITY.md returned as-is
2. Remove "About you" profile section from working_memory.py — Identity renders directly
3. Update callers (task_pipeline, agent_execution, integrations, system) to read "IDENTITY.md" key
4. Stub out import job readers (endpoints, system_state, working_memory failed_jobs)
5. Drop `integration_import_jobs` table (migration 139)
6. Clean up account reset references

### Phase 4: Deferred Design (separate ADR)

Address the deferred questions about TP heartbeat, task-to-TP feedback, and automatic evaluation. These require architectural discussion, not just code deletion.

---

## Files Changed

| File | Action |
|------|--------|
| `api/services/composer.py` | **DELETE** (Phase 1) |
| `api/test_adr111_composer.py` | **DELETE** (Phase 1) |
| `api/jobs/import_jobs.py` | **DELETE** (Phase 2) |
| `api/agents/integration/context_import.py` | **DELETE** (Phase 2) |
| `api/agents/integration/platform_semantics.py` | **DELETE** (Phase 2) |
| `api/jobs/unified_scheduler.py` | Remove heartbeat + imports + nightly crons |
| `api/services/agent_execution.py` | Remove `maybe_trigger_heartbeat` call |
| `api/services/working_memory.py` | Remove profile, add work_budget + agent_health |
| `api/services/workspace.py` | Remove MEMORY.md alias |
| `api/services/primitives/system_state.py` | Stub _get_failed_jobs |
| `api/routes/integrations.py` | Stub import endpoints |
| `api/routes/account.py` | Remove import_jobs cleanup |
| `supabase/migrations/139_drop_import_jobs.sql` | Drop table |
| `docs/adr/ADR-111-agent-composer.md` | Mark superseded by ADR-156 |
| `CLAUDE.md` | Update references |
