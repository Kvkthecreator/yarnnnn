# 2026-04-28 — Tracker tool-surface defect: task `required_capabilities` is a gate, not a tool augmentation

## Context

Phase B alpha-trader-1 monitoring exposed that the Tracker agent
on track-universe runs uses WebSearch (30 calls in one run) instead
of its declared platform tool `platform_trading_get_market_data`,
even though the workspace has an active Alpaca trading connection.

## Root cause

Mismatch between two systems:

1. **Task-level capability declaration** (TASK.md `**Required
   Capabilities:** read_trading`) is currently a **gate only**:
   `task_pipeline.py:1845-1861` checks the user has the platform
   connection, then proceeds. If missing → `_fail`. Otherwise →
   continue, but does NOTHING ELSE with the capability list.

2. **Agent-level capability declaration** (`orchestration.py:401`
   for Tracker) drives `get_type_capabilities(role)` →
   `get_platform_tools_for_capabilities(auth, capabilities)` →
   actual tool list returned to the LLM.

The Tracker role's capability list is:
```python
"capabilities": [
    "read_workspace", "search_knowledge",
    "read_slack", "read_notion", "read_github",
    "web_search", "investigate", "produce_markdown",
],
```

**`read_trading` is NOT in that list.** And it shouldn't be — Tracker
is a universal role per ADR-176, and adding trading caps would be
exactly the ICP-leakage that ADR-188 forbids ("registries are
template libraries, not exhaustive product definitions").

The result is that when alpha-trader-1's track-universe task
dispatches Tracker:
- The capability gate at line 1845 sees `required_capabilities:
  [read_trading]`, the user has the trading connection → gate passes.
- The agent-level capability resolution at line 1032 (`platform_tools.py`)
  returns NO trading tools (Tracker doesn't declare `read_trading`).
- The LLM gets a tool surface with WebSearch but no
  `platform_trading_get_market_data`.
- LLM does the only thing it can: WebSearches for "AAPL price RSI
  today" and tries to scrape.
- 30 WebSearches later, the agent emits a one-line "v10 returns 401"
  and the task delivers an empty output.

## Why this is structural

Per ADR-176 (work-first agent model) + ADR-188 (domain-agnostic
framework), the design is:
- Role taxonomy is fixed and ICP-agnostic
- Workspace specialization comes from operator-authored substrate
  (TASK.md, `_operator_profile.md`, etc.) and program bundles
  (alpha-trader's `read_trading` capability declaration)
- Tasks declare what they need, agents declare what they are

But the implementation only honors HALF of that architecture: tasks
declare needs, agents declare identity, and **the dispatcher fails
to merge them when assembling the agent's tool surface**.

This isn't a Tracker bug. It's a dispatcher bug. The same defect
will hit:
- Analyst on signal-evaluation (also declares `read_trading`)
- Writer on pre-market-brief (no required caps, but uses tools to
  read trading context)
- Analyst on trade-proposal (declares `read_trading`,
  `write_trading`)
- Every alpha-trader-2 task (same role assignments)
- Any future program with platform-bundle capabilities (alpha-commerce
  with `read_commerce` / `write_commerce`)

## Proposed minimal fix

In `task_pipeline.py:_generate` (line 3194), change the
`get_headless_tools_for_agent` call to merge the agent's role
capabilities with the task's `required_capabilities` before
resolving platform tools.

Concrete change:

```python
# task_pipeline.py around line 3194
# CURRENT:
headless_tools = await get_headless_tools_for_agent(
    client, user_id, agent=agent, agent_sources=[],
)

# PROPOSED:
# Plumb task_info.required_capabilities through; merge with agent role.
headless_tools = await get_headless_tools_for_agent(
    client, user_id,
    agent=agent,
    agent_sources=[],
    task_required_capabilities=task_required_capabilities,  # new param
)
```

In `primitives/registry.py:get_headless_tools_for_agent`, accept
`task_required_capabilities` and pass through to
`get_platform_tools_for_agent`. In `platform_tools.py:1027`, augment
the resolution:

```python
# platform_tools.py:1027 — PROPOSED:
async def get_platform_tools_for_agent(
    auth: Any, agent: dict,
    task_required_capabilities: list[str] = None,
) -> list[dict]:
    role = (agent or {}).get("role", "")
    role_capabilities = get_type_capabilities(role) if role else []
    # Merge: role caps + task-declared caps (deduped)
    all_capabilities = list(set(role_capabilities + (task_required_capabilities or [])))
    return await get_platform_tools_for_capabilities(auth, all_capabilities)
```

Three call sites need plumbing:
- `task_pipeline.py:2128` (single-step path)
- `task_pipeline.py:2793` (multi-step path)
- `task_pipeline.py:4058` (TP back-office path — probably moot, TP
  doesn't declare task-required caps but harmless to pass)

`task_info.required_capabilities` is already parsed at
`task_pipeline.py:1845` so the value is in scope.

## What this fix does NOT do

- Does NOT add trading caps to the Tracker role definition (preserves
  ADR-176 universal-role contract)
- Does NOT change ADR-207's "TASK.md is dispatch-authoritative"
  principle — it actually MAKES that principle real for tools
- Does NOT touch the capability gate (line 1845) — still gates on
  platform connection availability

## What we don't yet know

- Whether prompt-level guidance also needs to change. Even with the
  trading tools in the surface, the Tracker's `default_instructions`
  ("check your monitored sources for what changed since your last
  run") may still steer the LLM toward WebSearch-style monitoring
  rather than "fetch hourly bars and compute indicators." The fix
  above is necessary but may not be sufficient.
- Whether ADR-173 accumulation-first reading of `_operator_profile.md`
  is reaching the Tracker prompt. The 30-WebSearch run suggests the
  agent didn't realize the indicator math was already declared in
  substrate.

If the tool-surface fix lands and the Tracker still WebSearches,
the next fix is in the Tracker `default_instructions` —
domain-conditional guidance: "if a `_operator_profile.md` declares
mechanical indicator definitions for your domain, READ those first
and use the platform fetch tools to populate state, do NOT WebSearch."

## Phase B status

Implementation deferred — this is a kernel-level dispatcher change
affecting all users, all tasks, all programs. Should land as its own
focused commit/ADR rather than during a Phase B observation cycle.

The issue is reproducible and observable — every track-universe firing
on alpha-trader-1 will reproduce it (and alpha-trader-2 once
scaffolded). Fix can be designed + ADR'd + landed in a separate
session, then re-validated by re-triggering track-universe.

## Recommended next ADR

ADR-XXX: Task-Level Capability Augmentation. Codifies the fix above
+ updates ADR-207 P3 to reflect that task-level required_capabilities
serves both as a gate AND as a tool-surface augmentation. Ratifies
the architectural promise that "TASK.md is dispatch-authoritative"
applies uniformly to gating + tool resolution.

---

## Update — 2026-04-28 03:14 UTC: ADR-227 was already shipped — the Pydantic-drop was the real load-bearing defect

ADR-227 (commit 7690f6b) had already landed at 2026-04-28 08:42 KST
(23:42 UTC 04-27). The dispatcher merge code was correct. But re-triggering
track-universe twice on seulkim88 today still produced 16-17 WebSearch
calls and zero `platform_trading_get_market_data` calls. Two upstream
defects layered between the dispatcher and the agent's tool surface:

### Defect 1 — AGENT.md staleness

`agent_creation.py:175` seeds AGENT.md from `default_instructions` exactly
once at agent-creation time. seulkim88's Tracker row was created
2026-04-27 06:49 UTC — *before* ADR-227 added the "Source Priority" block
to the Tracker template. The ADR-227 prompt update never reached this
agent. seulkim88's Tracker AGENT.md was 426 chars; current template is
1355 chars.

Fixed via one-shot reconciliation: `api/scripts/alpha_ops/resync_agents.py`
detects drift between AGENT_TEMPLATES.<role>.default_instructions and the
current AGENT.md, re-writes via authored substrate (ADR-209) with
`authored_by="system:agent-resync"`. Applied to seulkim88's Tracker.

Drift was Tracker-only — Analyst, Writer, thinking_partner all matched
their templates. So the surface is bounded by what's been edited recently
(ADR-227 only touched Tracker).

### Defect 2 — Pydantic field drop on POST /api/tasks (the load-bearing one)

After re-sync, the next track-universe still produced 16 WebSearch calls
and zero platform tool calls. The new prompt was in AGENT.md, but the
agent's *tool surface* didn't contain `platform_trading_get_market_data`.

Inspection of seulkim88's TASK.md files revealed: **all 6 trader tasks
were missing the `**Required Capabilities:**` field.** scaffold_trader.py
correctly POSTs `required_capabilities: ["read_trading"]`, but
`api/routes/tasks.py:TaskCreate` (Pydantic model) didn't declare
`required_capabilities` as a field. Pydantic silently strips unknown
fields. The value was dropped before it reached `_handle_create`, and
TASK.md was serialized without the field. The ADR-227 dispatcher gate at
[task_pipeline.py:1845](../../api/services/task_pipeline.py#L1845)
never fired, the platform tool merge never happened, and the Tracker's
effective tool surface was the universal-role default — `read_workspace`,
`search_knowledge`, `read_slack`, `read_notion`, `read_github`,
`web_search`, `investigate`, `produce_markdown` — but no `read_trading`.

The Tracker's prompt could not recover from a tool surface that didn't
include the platform tool. It correctly recognized the prompt was telling
it to use platform tools (the new "Source Priority" guidance) but had no
such tool to call, so it fell back to WebSearch.

Fixed in commit fa660f7:
1. `api/routes/tasks.py`: declare `required_capabilities` on TaskCreate
2. `api/scripts/alpha_ops/backfill_required_capabilities.py`: one-shot
   TASK.md backfill via authored substrate for tasks created before the
   API fix landed. Inserts the field after the last `**Field:**` header
   line. Idempotent.

### Validation

Post-backfill re-trigger of track-universe (03:12 UTC):
- **Tools used: `platform_trading_get_market_data` (5)**
- **Zero WebSearch calls**
- 5 tickers fetched with live data, indicators computed
- 77s, 1 tool round (parallel batched calls)
- Output is coherent, not truncated mid-loop

This is the first track-universe run on seulkim88 that exercises the
intended ADR-227 path end-to-end.

### Remaining defect: tool round budget calibration

The agent fetched 5 of 15 universe tickers before hitting round limit.
This is not a steering issue (tool selection is now correct); it's a
budget mismatch — `accumulates_context` over 15 entities needs more
rounds than the universal `cross_platform` budget of 8 (16 in bootstrap).

Either:
- Pipeline-side: scale budget with universe size for accumulates_context
  tasks
- Prompt-side: explicit pacing in the task instruction ("budget 1-2 calls
  per ticker; if you can't cover the universe, write a partial state and
  flag remaining tickers")

Deferred to next session.

### Lesson — symptom altitude vs root-cause altitude

The 2026-04-26 paper-loop log identified A1 ("Domain-authored files not
auto-injected") as the highest-leverage gap. That fix was upstream of the
Tracker run path — and it correctly led to ADR-220 (authored substrate in
directory registry). The 2026-04-28 first-half observation identified the
"prompt steers toward WebSearch" symptom and proposed prompt fixes
(ADR-227's Source Priority block). Both fixes were correct at their
altitudes. Neither was the load-bearing one.

The load-bearing fix was a **route-layer Pydantic schema drop** — invisible
from the agent's perspective, invisible from the substrate's perspective,
visible only by tracing why a `**Required Capabilities:**` field was
absent from a TASK.md that the script clearly POSTed it for.

The audit pattern that surfaced it: don't trust the layer where the
symptom appears. Trace the data path from operator intent
(scaffold_trader.py declares `read_trading`) to runtime result (TASK.md
has no field). The drop was at the API boundary, two layers upstream of
the symptom.
