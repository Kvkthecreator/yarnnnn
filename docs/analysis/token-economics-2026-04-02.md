# Token Economics & Cost Management

**Date:** 2026-04-02
**Status:** Active — infrastructure fixes deployed, product optimization ongoing

## Context

YARNNN runs autonomous agents that execute recurring tasks via Claude API. Each task execution involves multi-round tool use (WebSearch, WriteWorkspace, etc.), where each round re-sends the full conversation history. This creates a multiplicative cost structure that, unmanaged, makes the product unprofitable.

This document captures the cost model, what we learned from the first production runs, the infrastructure fixes applied, and the remaining optimization path.

## Anthropic Pricing (as of April 2026)

| Model | Input ($/MTok) | Output ($/MTok) | Cache Write | Cache Read |
|-------|---------------|-----------------|-------------|------------|
| Sonnet 4 | $3.00 | $15.00 | $3.75 | $0.30 (90% discount) |
| Haiku 4.5 | $0.80 | $4.00 | $1.00 | $0.08 |

Key insight: **input tokens dominate cost**. Output is 5x more expensive per token, but input volume is 50-100x larger. Reducing input is the primary lever.

## Cost Anatomy of a Task Execution

A single task execution consists of:

```
System prompt (static)     ~5K tokens    — agent identity, methodology, rules
User message (dynamic)     ~8-12K tokens — objective, context, gathered workspace data
Tool rounds (multiplier)   N rounds      — each re-sends system + messages + results
```

### The Multiplication Problem

Without optimization, each tool round re-sends everything:

| Round | Incremental (new result) | Cumulative (re-sent) | Total input |
|-------|--------------------------|----------------------|-------------|
| 1 | 15K (system + user) | 0 | 15K |
| 2 | ~5K (tool result) | 15K | 20K |
| 3 | ~5K | 20K | 25K |
| ... | | | |
| 8 | ~5K | 50K | 55K |
| **Sum across all rounds** | | | **~280K** |

With 13 rounds (bootstrap): **~680K tokens**. With 200KB WebSearch results (pre-fix): **840K+**.

### Three-Layer Defense (implemented 2026-04-02)

Modeled after Claude Code's approach:

**Layer 1: Per-result truncation**
- `_truncate_tool_result()` caps each tool result to 2K chars
- WebSearch `_MAX_CONTENT_LENGTH` reduced from 200K to 12K chars
- Impact: prevents any single result from being >3K tokens

**Layer 2: Microcompact (history clearing)**
- `_microcompact_tool_history()` keeps only the 3 most recent tool results
- Older results replaced with `[Prior tool result cleared]`
- Runs before each API call in rounds 2+
- Impact: conversation stays flat instead of growing linearly

**Layer 3: Prompt caching**
- System prompt split into static (cached) + dynamic (uncached) content blocks
- `cache_control: {"type": "ephemeral"}` on static portion (~5K tokens)
- TTL: 5 minutes (Anthropic ephemeral cache)
- Impact: ~90% discount on static system prompt for rounds 2+ within one execution

### Observed Results

| Run | Phase | Rounds | Input tokens | Cache read | Cost | Input:Output |
|-----|-------|--------|-------------|------------|------|-------------|
| v2 (pre-fix) | bootstrap | ? | 260K | 0 | $0.84 | 63:1 |
| v3 (pre-fix) | bootstrap | ? | 840K | 0 | $2.62 | 131:1 |
| Market (post-fix) | bootstrap | ? | 315K | 114K | $1.05 | 45:1 |
| **v4 (post-fix)** | **steady** | **8** | **207K** | **57K** | **$0.65** | **111:1** |

## Unit Economics

### Current state (post-fix)

| Metric | Bootstrap run | Steady-state run |
|--------|-------------|-----------------|
| Input tokens | ~315K | ~207K |
| Output tokens | ~7K | ~2K |
| Cost per run | ~$1.05 | ~$0.65 |
| Tool rounds | 8-16 | 8 |

### Per-user monthly cost model

| Scenario | Tasks | Cadence | Runs/mo | Cost/mo | vs Pro revenue ($19) |
|----------|-------|---------|---------|---------|---------------------|
| Light (1 task, weekly) | 1 | weekly | 4 | $2.60 | 14% (healthy) |
| Medium (3 tasks, weekly) | 3 | weekly | 12 | $7.80 | 41% (marginal) |
| Heavy (5 tasks, mixed) | 5 | weekly | 20 | $13.00 | 68% (underwater) |
| Target (5 tasks, optimized) | 5 | weekly | 20 | $6.00 | 32% (healthy) |

**Healthy SaaS margin**: LLM cost should be <35% of revenue.

### Target cost per run: $0.30

To hit the target, input tokens need to drop from 207K to ~80-100K per steady-state run.

## Remaining Optimization Path

### Product-level (prompt/behavior changes)

1. **Phase-aware search depth**
   - Bootstrap: 8-16 rounds, broad research (current behavior, justified)
   - Steady state: 2-4 targeted rounds, delta-focused ("what changed since last cycle?")
   - Implementation: awareness.md already tracks domain state; prompt should use it to limit scope

2. **Context gathering efficiency**
   - Currently: `gather_task_context()` reads all entity files in the domain
   - Target: read only `_tracker.md` (synthesis) + entities modified since last run
   - Implementation: workspace file `updated_at` filtering

3. **Model routing**
   - Context tasks (update-context): could use Haiku for entity updates ($0.80/MTok vs $3.00)
   - Output tasks (competitive-brief, market-report): keep Sonnet for quality
   - Implementation: task_types registry gets a `model` field

### Infrastructure-level (already done or low priority)

| Fix | Status | Impact |
|-----|--------|--------|
| Prompt caching (content blocks) | Deployed | ~30% on system prompt |
| Tool result truncation | Deployed | ~50% on result size |
| Microcompact (history clearing) | Deployed | ~40% on cumulative growth |
| WebSearch content cap (200K→12K) | Deployed | Prevents extreme cases |
| Atomic task claim (no duplicates) | Deployed | Eliminates wasted runs |
| Autocompact (full conversation summary) | Not needed yet | Would help for 15+ round runs |

## Observability

Three layers, all operational:

| Layer | Location | What it shows |
|-------|----------|--------------|
| **Logs** | Render → `[TOKENS]` | Per-API-call: in, out, cache_create, cache_read, cache_hit%, model |
| **DB** | `agent_runs.metadata` | Per-run: input_tokens, output_tokens, cache_*, tool_rounds, tools_used |
| **Dashboard** | `/admin` | Aggregated: daily cost by caller, per-task breakdown, cache hit% |

## Scheduler Concurrency

Render cron spawns 2-3 worker instances per cycle. Fixed via atomic claim (CAS pattern on `next_run_at`). Heartbeat count (~318/day vs expected ~288) confirms multiple instances but no duplicate task execution.

## Key Files

| File | Role |
|------|------|
| `api/services/anthropic.py` | `_prepare_system()`, `_microcompact_tool_history()`, `[TOKENS]` logging |
| `api/services/task_pipeline.py` | `_generate()` with truncation + microcompact, `build_task_execution_prompt()` with cached blocks |
| `api/agents/tp_prompts/__init__.py` | TP prompt caching (static/dynamic split) |
| `api/services/primitives/web_search.py` | `_MAX_CONTENT_LENGTH` cap |
| `api/jobs/unified_scheduler.py` | Atomic task claim |
| `api/routes/admin.py` | Token usage + execution stats endpoints |
| `docs/features/admin-dashboard.md` | Dashboard documentation |
