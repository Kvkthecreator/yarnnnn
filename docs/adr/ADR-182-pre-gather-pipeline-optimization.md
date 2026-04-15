# ADR-182: Pre-Gather Pipeline Optimization — Mechanical Context Assembly

> **Status**: Phase 1-2 Implemented (extended gathering + output_kind-aware tool surface)
> **Date**: 2026-04-15
> **Authors**: KVK, Claude
> **Extends**: ADR-141 (Unified Execution Architecture), ADR-173 (Accumulation-First Execution)
> **Preserves**: ADR-149 (Task Lifecycle / DELIVERABLE.md), ADR-151 (Shared Context Domains), ADR-170 (Compose Substrate)
> **Informs**: TOKEN-ECONOMICS-ANALYSIS.md Section 6 (Cost Optimization Opportunities)

---

## Context

YARNNN's task pipeline (ADR-141) already separates mechanical scheduling (Layer 1, zero LLM) from generation (Layer 2, Sonnet). Within Layer 2, context gathering (`gather_task_context()`) is already **100% mechanical** — pure SQL queries against `workspace_files`, zero LLM cost. The function reads domain files, synthesis summaries, entity trackers, agent identity, and user notes, then concatenates them into a `context_text` string injected as `## Gathered Context` in the user message.

However, the generation step (`_run_headless_generation_loop()`) still provides 16 headless tool definitions and allows up to 5-13 tool rounds per task. In practice, many of these rounds are the agent performing reads that could have been gathered mechanically:

| Tool | Typical usage | Predictable? |
|------|--------------|--------------|
| `ReadFile` | Read entity profiles, tracker files | **Yes** — declared in `context_reads`/`context_writes` |
| `SearchFiles` | Find relevant workspace content | **Mostly** — domain folder is known |
| `QueryKnowledge` | Search across domains | **Mostly** — objective keywords are known |
| `ListFiles` | Discover what exists | **Yes** — folder paths are declared |
| `WebSearch` | Research external sources | **No** — requires LLM judgment |
| `WriteFile` | Update domain context | **No** — requires generated content |
| `RuntimeDispatch` | Generate charts/images | **No** — requires generated spec |

**Observation:** For the majority of task types (`track-*`, `*-report`, `*-brief`, `*-digest`), 60-80% of tool rounds are predictable reads. The agent spends 3-4 LLM roundtrips reading files it already knows about from the task type registry before producing the actual output on the final round.

**Cost impact of tool rounds:**

Each tool round re-sends the full conversation history (even with microcompaction):
- Round 1: ~15K input tokens (system + tools + context)
- Round 2: ~20K (+ round 1 results, microcompacted)
- Round 3: ~25K (+ round 2)
- Round 4: ~30K (synthesis)

Eliminating 2-3 read-only rounds from a typical 4-round task saves ~35K input tokens per run. At $3/MTok uncached: **~$0.10 saved per task execution**.

### Relationship to Batch API

The Batch API (Anthropic, 50% off) requires single-shot requests — no tool loops. Today, most task runs cannot use batch because they need tool loops for context reads. If context is pre-gathered mechanically, the synthesis step becomes a single LLM call with no tools — **batch-eligible**. This converts the pipeline optimization from a standalone 50-70% input token reduction into a potential **additional 50% on top** via batch pricing.

However, timezone distribution across users means there's no clean batch window. Tasks fire individually throughout the day per user's local schedule. The primary value of this ADR is the pipeline optimization itself; batch eligibility is a compounding bonus if/when implemented.

---

## Decision

### Split Layer 2 into two explicit phases

**Phase A: Mechanical Context Assembly (zero LLM)**

A deterministic step that runs before any LLM call. Reads everything the agent would predictably request during tool rounds and materializes it into the generation prompt.

This is NOT new infrastructure — `gather_task_context()` already does most of this work. The optimization extends it to cover reads that agents currently perform via tool rounds:

1. **Everything `gather_task_context()` already does** (unchanged):
   - Task awareness (`awareness.md`)
   - Source scope resolution
   - Domain tracker + entity files (objective-matched)
   - Accumulated context domains (`/workspace/context/`)
   - Agent identity + playbooks (`ws.load_context()`)
   - User notes

2. **New mechanical reads** (currently done by agents via tool rounds):
   - **Prior output inspection**: read `outputs/latest/output.md` for all modes (not just goal mode). Inject as `## Prior Output` section with staleness annotation.
   - **Full entity file loading for `accumulates_context` tasks**: currently budget-capped at 8 files with the expectation that agents fetch more via tools. For tasks whose `context_writes` declares a single domain with ≤20 entities, load all entity primary files (still within token budget via truncation).
   - **Cross-domain entity matching**: if `context_reads` includes multiple domains, load entity files from each domain that share slug names (e.g., competitor slug `acme` exists in both `competitors/` and `market/` domains). Currently agents discover this via `SearchFiles` during tool rounds.

3. **Prompt-embedded file listing** (new):
   - Inject a compact file inventory of `outputs/latest/` so agents know what assets exist without calling `ListFiles`. Format: `## Output Inventory\n- hero.png (EXISTS, 2026-04-15)\n- output.md (EXISTS, 2026-04-15)`.

### Reduce tool surface for synthesis-only tasks

For tasks where pre-gathering covers all predictable reads, the generation step can run with a **reduced tool set**:

| Task output_kind | Tool surface | Rationale |
|---|---|---|
| `produces_deliverable` | Reduced: `WriteFile`, `RuntimeDispatch` only | All reads pre-gathered; agent only needs to write output + generate assets |
| `accumulates_context` | Full headless set | Agent writes to domain files during tool rounds — write targets require LLM judgment |
| `external_action` | Full headless set | Platform tool calls require LLM judgment |
| `system_maintenance` | No tools (back office, deterministic) | Already handled by ADR-164 |

**`produces_deliverable` tasks are the primary optimization target.** These are the revenue-driving tasks (reports, briefs, digests) and the highest-volume execution path.

For `produces_deliverable` with `page_structure` (ADR-170), the generation brief already provides structured section-level guidance. Combined with full pre-gathered context, the agent has everything it needs to produce output in a single synthesis pass.

### What changes in the pipeline

```
CURRENT (ADR-141):
  execute_task()
    → gather_task_context()           # mechanical, ~0 cost
    → build_task_execution_prompt()   # build prompt
    → _run_headless_generation_loop() # Sonnet, 3-5 tool rounds, 16 tools
      ├── Round 1: ReadFile × 2       # agent reads what it needs
      ├── Round 2: SearchFiles × 1    # agent searches for more
      ├── Round 3: ReadFile × 1       # agent reads search results
      └── Round 4: synthesis          # agent produces output
    → save + compose + deliver

PROPOSED (ADR-182):
  execute_task()
    → gather_task_context()           # mechanical, EXTENDED — more reads pre-loaded
    → build_task_execution_prompt()   # build prompt, EXTENDED — richer context
    → _run_headless_generation_loop() # Sonnet, 0-1 tool rounds, reduced tools
      └── Round 1: synthesis          # agent produces output directly
    → save + compose + deliver
```

### What does NOT change

- **`accumulates_context` tasks** keep full tool surface. Their purpose is to read + write domain files during execution. Pre-gathering their write targets doesn't help — the LLM needs to decide what to write.
- **Research tasks with `WebSearch`** keep full tool rounds. External research requires LLM judgment for query formulation.
- **TP chat mode** is unaffected. Chat is real-time with full primitives.
- **Multi-step pipelines** are unaffected per-step. Each step independently gets pre-gathered context. Step N+1 still receives step N's output as handoff.
- **The `_run_headless_generation_loop()` function signature** doesn't change. It already accepts `tools` and `max_tool_rounds` parameters. The optimization passes fewer tools and lower round limits for eligible tasks.

---

## Cost Impact

### Per-task savings (produces_deliverable)

| Component | Current | With ADR-182 | Savings |
|---|---|---|---|
| Cached input (system + tools) | ~7,000 tokens, $0.002 | ~4,000 tokens, $0.001 | ~50% (fewer tools) |
| Uncached input (context + tool results) | ~12,000 tokens, $0.036 | ~8,000 tokens, $0.024 | ~33% (no tool round accumulation) |
| Output | ~2,500 tokens, $0.038 | ~2,500 tokens, $0.038 | 0% (unchanged) |
| **Total** | **$0.076** | **$0.063** | **~17%** |

The savings from reduced input tokens are partially offset by richer pre-gathered context injected upfront. Net savings per task: **$0.01-0.02**.

### Real savings: eliminated tool rounds

The bigger win is eliminating the *geometric growth* of multi-round conversations:

| Rounds | Total input (current) | Total input (ADR-182) | Savings |
|---|---|---|---|
| 1 round (synthesis only) | 15K | 18K (richer pre-gather) | -20% (slightly more) |
| 4 rounds (typical) | 15K + 20K + 25K + 30K = **90K** | 18K (single round) | **80%** |
| 6 rounds (research) | **~180K** | N/A (research keeps rounds) | N/A |

**At 4 rounds eliminated**: 72K fewer input tokens per task = **$0.22 saved** (uncached at $3/MTok).

Combined with output tokens ($0.038 unchanged): task drops from **$0.25 to $0.06** for a 4-round task. For the typical 2-3 round produces_deliverable task: **$0.12 → $0.06, ~50% reduction**.

### Scale impact

| Scale | Tasks/month | Current cost | With ADR-182 | Monthly savings |
|---|---|---|---|---|
| 3 users (current) | ~40 | $3.20 | $1.60 | $1.60 |
| 50 Pro users | ~3,000 | $240 | $120 | **$120** |
| 200 Pro users | ~12,000 | $960 | $480 | **$480** |

### With Batch API stacking (future)

If produces_deliverable tasks become single-shot (no tools), they qualify for Batch API (50% off):

| Optimization | Per-task cost | vs. baseline |
|---|---|---|
| Current (multi-round, standard API) | $0.12 | — |
| ADR-182 only (single-round, standard API) | $0.06 | **50% off** |
| ADR-182 + Batch API (single-round, batch) | $0.03 | **75% off** |

---

## Implementation

### Phase 1: Extended mechanical gathering (Implemented 2026-04-15)

Extended `gather_task_context()` with two additional read sources (cross-domain entity matching deferred):

1. **Prior output for all modes**: reads `outputs/latest/output.md`, truncates to 3000 chars, injects as `## Prior Output (latest run)`. Graceful degradation: first run has no prior output, section is omitted.
2. **Output inventory**: reads `outputs/latest/` file listing, injects as compact `## Output Inventory (outputs/latest/)` section. Filters out `sys_*` internal files. Shows filename + date.

Key implementation: added as section 5 in `gather_task_context()`, after user notes. Non-fatal — any read failure is logged and skipped.

### Phase 2: Reduced tool surface for produces_deliverable (Implemented 2026-04-15)

In `execute_task()`, after determining `output_kind`, produces_deliverable tasks (except bootstrap phase) get a reduced tool surface:

```python
if output_kind == "produces_deliverable" and task_phase != "bootstrap":
    _tool_overrides = [WRITE_FILE_TOOL, RUNTIME_DISPATCH_TOOL]
    _max_rounds_override = 2  # asset generation only
```

`_generate()` gained two new optional params: `tool_overrides: Optional[list[dict]]` and `max_rounds_override: Optional[int]`. When set, these bypass the default full headless tool resolution and scope-based round limits.

Bootstrap phase is excluded — first runs need full tool surface for deep research.

Prompt updated: "Accumulation-First Execution" and "Tool Usage" sections in `build_task_execution_prompt()` rewritten to reflect pre-loaded context model. Agent is told prior output and inventory are already in gathered context.

### Phase 3: Batch API eligibility (Deferred)

Once Phase 2 validates that produces_deliverable tasks reliably complete in 0-1 tool rounds, route scheduled runs through Batch API. This is the same deferred Batch API work described in TOKEN-ECONOMICS Section 8, now with a clear eligibility path.

Trigger: monthly task execution cost exceeds $300.

---

## Risks

**Risk: Agent produces lower-quality output without tool access.**
Mitigation: Phase 2 starts with produces_deliverable only (reports, briefs). These are synthesis tasks — the agent's job is to compose from provided context, not discover new information. Monitor output quality (approval rates, TP evaluation scores) for regression.

**Risk: Pre-gathered context exceeds token budget.**
Mitigation: Existing budget caps (`_TOTAL_FILE_BUDGET`, `_PER_DOMAIN_CEILING`) already bound context size. Extended reads (prior output, inventory) add ~500-1000 tokens. Total stays within the ~20K char / ~5K token budget.

**Risk: Removes agent agency for edge cases.**
Mitigation: Full tool surface preserved for `accumulates_context` and `external_action` tasks. Only `produces_deliverable` gets reduced tools. If specific produces_deliverable task types need tools (e.g., a report that requires live WebSearch), the type registry can declare `requires_tool_loops: true` to opt out.

---

## Consequences

**Positive:**
- 50% cost reduction on produces_deliverable tasks (the primary revenue driver)
- Enables Batch API eligibility for the highest-volume execution path
- Reduces latency: 1 LLM round instead of 4 = faster task completion
- Aligns with ADR-173 (accumulation-first): if workspace holds current state, reading it mechanically is strictly better than routing reads through an LLM
- Reduces Anthropic API call volume (fewer roundtrips = less rate limit pressure at scale)

**Neutral:**
- `accumulates_context` tasks unchanged — their value is in the tool loop itself
- TP chat mode unchanged — interactive primitives stay full
- Multi-step pipelines unchanged per-step

**Negative:**
- Richer pre-gathered context means slightly larger first-round input (~3K more tokens)
- Type registry may need `requires_tool_loops` escape hatch for edge cases
- Monitoring required: output quality regression check post-Phase 2

---

## Decision Record

| Question | Decision |
|---|---|
| Which tasks get reduced tools? | `produces_deliverable` only. Others keep full surface. |
| What tools remain for synthesis? | `WriteFile` + `RuntimeDispatch` (output + assets) |
| Does this change the scheduler? | No. Scheduler fires `execute_task()` unchanged. |
| Does this affect TP? | No. Chat mode is unaffected. |
| When to implement Batch API? | When monthly task cost exceeds $300 (TOKEN-ECONOMICS trigger) |
| How to opt out per task type? | `requires_tool_loops: true` in task type registry (future, if needed) |
