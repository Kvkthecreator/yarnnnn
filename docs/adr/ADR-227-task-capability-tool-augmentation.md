# ADR-227: Task Capability Tool Augmentation

> **Status:** **Implemented 2026-04-28.** Three-file fix landed: `services/platform_tools.py::get_platform_tools_for_agent` accepts `task_required_capabilities` kwarg and merges with role caps before resolving tools; `services/primitives/registry.py::get_headless_tools_for_agent` plumbs the param through; `services/task_pipeline.py::_generate` and the two task-pipeline call sites pass `task_info["required_capabilities"]` through. Also lands a Tracker prompt fix establishing source priority (`_operator_profile.md` → `platform_*` tools → WebSearch as last resort).
> **Date:** 2026-04-28
> **Authors:** KVK, Claude
> **Related:** ADR-176 (Work-First Agent Model — universal-role taxonomy), ADR-188 (Domain-Agnostic Framework — registries as template libraries), ADR-207 P3+P4b (TASK.md is dispatch-authoritative; `**Required Capabilities:**` declared inline), ADR-224 (Kernel/Program Boundary — program-specific capabilities live in bundle MANIFEST.yaml), ADR-173 (Accumulation-First Execution — read substrate before searching), ADR-225 (Compositor Layer — bundle-supplied capabilities enter kernel via lookup fallback)
> **Surfaces:** Phase B alpha-trader-1 observation (2026-04-27 to 2026-04-28). The Tracker agent on track-universe ran 30 WebSearch calls and emitted "v10 returns 401" instead of calling `platform_trading_get_market_data`. Investigation showed the platform tool was never in its tool surface despite the user having an active Alpaca trading connection and the task declaring `required_capabilities: [read_trading]`.

---

## Context

Per ADR-176 (Work-First Agent Model) + ADR-188 (Domain-Agnostic Framework), YARNNN's role taxonomy is **universal and ICP-agnostic**:

- **Roles** (Researcher, Analyst, Writer, Tracker, Designer, Reporting) declare what the agent IS — capabilities it has by virtue of its role identity. These do not vary per program.
- **Tasks** (TASK.md) declare what the work NEEDS — including program-specific platform capabilities like `read_trading`, `read_commerce`, `read_github`. These are operator/bundle-authored per workspace.
- **Programs** (alpha-trader, alpha-commerce, etc.) supply program-specific capabilities through bundle `MANIFEST.yaml` declarations consumed by `bundle_reader.py` per ADR-224.

The architecture promises that operators can compose universal roles against program-specific capabilities — Tracker on alpha-trader's `track-universe`, Tracker on alpha-commerce's `customer-watch`, both work without modifying Tracker.

ADR-207 P3 implemented the **gate side** of this promise: when a task declares `**Required Capabilities:**`, dispatch checks the user has the corresponding platform connection. If yes → proceed. If no → `_fail("Required capability unavailable")`.

But the **resolution side** of the same promise was not implemented. When the gate passed, the agent's tool surface was still resolved from its role's capability list alone (`get_type_capabilities(role)`). Program-specific capabilities the task declared were silently dropped.

### The defect surfaced

Phase B alpha-trader-1 monitoring (2026-04-27) exposed the cascade. The Tracker agent runs `track-universe` which declares:

```
**Agent:** tracker
**Required Capabilities:** read_trading
```

`read_trading` is provided by the alpha-trader bundle's MANIFEST and grants tools including `platform_trading_get_market_data`. The user has an active Alpaca trading connection, so the gate at `task_pipeline.py:1845` passes.

But Tracker's role-level capability list at `orchestration.py:401-405` is:

```python
"capabilities": [
    "read_workspace", "search_knowledge",
    "read_slack", "read_notion", "read_github",
    "web_search", "investigate", "produce_markdown",
],
```

`read_trading` is NOT in that list — and shouldn't be, per ADR-176. Tracker is a universal role.

Result: the LLM never received `platform_trading_get_market_data` in its tool surface. With WebSearch as the only "fetch external data" tool available, the agent burned 30 WebSearches trying to look up "AAPL price RSI today," parsed Google results, eventually hallucinated a "v10 returns 401" error string from one of those results, and emitted a one-line failure as the entire delivered output.

This affects every program × universal-role combination:
- Tracker on `track-universe` (alpha-trader): missing `platform_trading_*`
- Analyst on `signal-evaluation` (alpha-trader): missing `platform_trading_*`
- Analyst on `trade-proposal` (alpha-trader): missing `platform_trading_*` + `write_trading`
- Writer on `pre-market-brief` (alpha-trader): no required caps declared, but the same defect would fire if it did
- Any future alpha-commerce, alpha-prediction, etc. tasks

The framework was structurally promising one thing and delivering another.

---

## Decision

**Task-declared `required_capabilities` augment the agent's role capabilities when resolving the platform tool surface.** Roles continue to declare universal identity; tasks add ICP context; the dispatcher merges both before asking the platform-tool registry for tools.

This is **NOT** about overriding roles — Tracker stays Tracker. It is about closing the gap that left bundle-supplied capabilities unreachable to universal-role agents.

Specifically:

1. `platform_tools.py::get_platform_tools_for_agent(auth, agent, task_required_capabilities=None)` accepts a new optional kwarg. Internally, it merges `get_type_capabilities(role) + (task_required_capabilities or [])` deduped, then resolves tools.

2. `primitives/registry.py::get_headless_tools_for_agent(...)` accepts and forwards `task_required_capabilities` to `get_platform_tools_for_agent`.

3. `task_pipeline.py::_generate(...)` accepts `task_required_capabilities`. The two task-pipeline call sites (single-step at line 2128, multi-step at line 2795) pass `task_info["required_capabilities"]` through.

4. The legacy direct-generation paths (`task_pipeline._execute_direct`, `agent_execution.generate_draft_inline`) do NOT pass anything — those paths run without a TASK.md and resolve from role-only as before. Their behavior is unchanged.

5. The capability gate at `task_pipeline.py:1845` is unchanged. Gating still validates platform connections. The new code adds tool resolution; it does not duplicate or replace gating.

### Why merge order is "role first, task appended"

The merge dedupes preserving role-first declaration order. This makes role capabilities authoritative for the agent's identity (e.g., `produce_markdown` always appears before any task-specific capability) while letting tasks append the program-specific extensions the role doesn't know about. The order has no functional impact on tool resolution but makes prompt assembly + logs deterministic.

---

## Companion: Tracker prompt fix

The dispatcher fix gives the Tracker access to platform tools but does not guarantee the LLM uses them. The Tracker's `default_instructions` previously framed the role generically ("check your monitored sources for what changed") with no priority among `web_search`, `read_slack`, `read_notion`, `read_github`. This let the LLM pick WebSearch as the easiest path even when platform tools were available.

Updated Tracker `default_instructions` add an explicit Source Priority section (ADR-227 + ADR-173 accumulation-first):

1. Read `_operator_profile.md` in the task's primary context domain. If it declares mechanical definitions (signals, entities, indicators, pairs, thresholds, formulas), those ARE the authoritative spec — do NOT WebSearch to re-derive them.
2. If your tool surface includes `platform_*` tools, USE THEM. They are the authoritative live-data path for connected platforms.
3. WebSearch is the LAST resort — only when the operator profile points to an external reference AND no platform tool covers it.

Analyst and Writer roles already declare "Do not search the web — you work from accumulated context" in their default instructions and do not have `web_search` in their capability lists, so they are not affected by the Tracker-specific WebSearch-fallback bias. The Tracker prompt change is the only behavioral injection in this commit.

`api/prompts/CHANGELOG.md` updated.

---

## What this fix does NOT do

- Does NOT add program-specific capabilities to universal role definitions. Tracker stays Tracker; ADR-176's universal-role contract is intact.
- Does NOT change `task_info` parsing or TASK.md schema. `**Required Capabilities:**` reads exactly the same.
- Does NOT change the capability gate semantics. Gating still validates platform connections.
- Does NOT alter the `_execute_direct` or `generate_draft_inline` legacy paths (taskless agent runs).
- Does NOT touch ADR-225's compositor or the surface-side capability rendering.

---

## Validation

Three call sites under `task_pipeline._generate` benefit:
- `track-universe` (Tracker, single-step, declares `read_trading`)
- `signal-evaluation` (Analyst, single-step, declares `read_trading`)
- `trade-proposal` (Analyst, single-step, declares `read_trading` + `write_trading`)
- `weekly-performance-review`, `quarterly-signal-audit` (Analyst, single-step, no required_caps — unchanged behavior)

Phase B re-trigger plan: after deploy, manually trigger track-universe via `POST /api/tasks/track-universe/run` for alpha-trader-1. Expected behavior:
- Agent receives `platform_trading_get_market_data` in its tool surface (verifiable via `awareness.md` "Tools used:" entry, which should now show `platform_trading_get_market_data` calls instead of 30 WebSearches).
- Agent reads `_operator_profile.md`, picks up the IH-N signal definitions + ticker universe.
- Agent calls `platform_trading_get_market_data` for each ticker, computes per-ticker state, writes per-ticker context files under `/workspace/context/trading/{ticker}.md`.
- `_tracker.md` rebuilds with real per-ticker entities (not slug churn).

If the agent still WebSearches even with platform tools available, that's a deeper prompt issue requiring iteration on the Tracker `default_instructions` or scope-specific guidance. The structural fix is necessary regardless; the prompt fix here is its companion best-effort.

---

## Forward note: prompt versioning

KVK observed during this session that prompt iteration is becoming primitive enough to deserve formal versioning, similar to how the kernel and project types are versioned for workspaces. This ADR does not implement prompt versioning — it lands a single point-fix on Tracker's prompt — but the observation is real and merits its own ADR.

What "prompt versioning" might look like in YARNNN:
- Every behavioral injection (role `default_instructions`, role `methodology` playbooks, the prompt profiles in `yarnnn_prompts/`, the task-execution prompt in `task_pipeline.py:build_task_execution_prompt`) becomes a versioned artifact with a stable identifier and explicit migration path.
- Workspaces could pin to a prompt version the way ADR-223 lets workspaces pin to a bundle version.
- Regression on a known-good prompt could be diagnosed by version diff, not only by behavioral observation.

This is a future ADR, not this one. Tracking under "future work — prompt versioning" in `api/prompts/CHANGELOG.md`.

---

## Test gate

Manual validation on Phase B alpha-trader-1 + alpha-trader-2 (when scaffolded). Automated test gate not added — the tool resolution is exercised by every task pipeline run; a regression would surface as Phase B observability degradation. If the merge logic ever needs to be made more sophisticated (e.g., role capabilities should override task capabilities in some cases), an automated unit test in `api/test_*.py` becomes warranted.
