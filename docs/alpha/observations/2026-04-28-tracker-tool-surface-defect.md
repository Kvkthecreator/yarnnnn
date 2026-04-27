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
