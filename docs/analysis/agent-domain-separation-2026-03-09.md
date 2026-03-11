# Analysis: Agent Domain Separation

**Date:** 2026-03-09
**Status:** Assessed and deferred
**Context:** User raised whether proactive/agentic behavior should be carved out as a separate domain from agents

---

## Question

Should yarnnn create a separate "agents" domain distinct from agents — with its own table, routes, scheduler, and frontend — rather than continuing to expand agent types and modes?

## Current State

Agents serve as the unified execution unit for all background work. The mode taxonomy (ADR-092) provides five modes:

| Mode | Behavior |
|------|----------|
| `recurring` | Scheduled generation on a cadence |
| `goal` | Works toward a defined objective, stops when achieved |
| `reactive` | Triggered by platform events (new Slack message, email, etc.) |
| `proactive` | System-initiated based on context analysis (proactive review) |
| `coordinator` | Orchestrates other agents |

All modes share: the same `agents` table, the same execution pipeline (`execute_agent_generation`), the same scheduler (`unified_scheduler`), the same frontend surfaces, and the same intelligence model (ADR-101: Skills/Directives/Memory/Feedback).

## Arguments For Separation

1. **Conceptual clarity**: A "agent" implies a document/artifact. Proactive insights and coordinator orchestration feel more like agent behavior than document generation.

2. **Different lifecycles**: A recurring newsletter has a predictable cadence and output format. A coordinator or reactive agent has event-driven, unpredictable execution patterns.

3. **Different UI needs**: Document agents need version history, editing, quality metrics. Agent-like agents need execution logs, decision traces, action history.

4. **Future sub-agent capabilities**: If agents gain the ability to create other agents, modify their own directives, or chain actions, the agent abstraction becomes strained.

5. **Mode sprawl**: The mode taxonomy already has 5 entries. Adding more agent-like behaviors (e.g., approval workflows, multi-step pipelines) would further stretch the agent concept.

## Arguments Against Separation (Now)

1. **Massive duplication**: Splitting means duplicating or abstracting:
   - Database tables (`agents` → `agents` + `agents`)
   - API routes (`/agents/` → `/agents/` + `/agents/`)
   - Scheduler logic (cron dispatch, trigger dispatch)
   - Execution pipeline (context gathering, draft generation, delivery)
   - Frontend surfaces (list, detail, settings, versions)
   - Intelligence model (instructions, memory, feedback)

2. **Shared orchestration**: Both "agents" and "agents" would need the same: context gathering (platform_content search), LLM generation (headless agent), delivery (email/Slack/Notion export), scheduling (cron + trigger dispatch), and memory accumulation.

3. **The mode system already provides the seam**: `mode` acts as a discriminator. Code paths that differ by mode (e.g., coordinator pipeline in `proactive_review.py`) already branch on mode — they don't need a separate table to do so.

4. **Premature abstraction**: We have 2 active agents. The pain of mode expansion is theoretical. The cost of premature splitting is real — doubled surface area, migration complexity, conceptual overhead for users.

5. **One user, one product**: The user interacts with "agents" as a unified concept. Splitting into "agents" + "agents" creates a conceptual fork that requires explanation: "Your newsletter is a agent, but your proactive insights are an agent." This is confusing when the setup experience (title, instructions, sources, schedule) is identical.

## Recommendation

**Defer separation. Prepare the seam.**

The current mode system provides sufficient discriminating power. The agent execution pipeline is mode-aware already — coordinator and proactive modes have distinct code paths. If we reach a point where:

- More than 3 modes are "agent-like" (no document output, event-driven, action-oriented)
- Users express confusion about "agents" containing non-document entities
- The execution pipeline requires fundamentally different orchestration per mode

...then extract the agent domain at that point, using `mode` as the migration discriminator.

### Preparing the seam (no code changes needed now)

The following patterns already exist and would ease future extraction:

1. **Mode-gated code paths**: `if mode == "coordinator"` branches in `proactive_review.py`
2. **Strategy pattern**: `get_execution_strategy(agent)` dispatches per type — could dispatch per mode instead
3. **Type prompt templates**: Per-type templates in `agent_pipeline.py` are already modular
4. **Memory model**: `agent_memory` JSONB is schema-flexible — agent-specific memory shapes can coexist

If splitting becomes necessary, the migration path is:
1. Create `agents` table with same schema as `agents`
2. Migrate rows where `mode in ('proactive', 'coordinator', 'reactive')` to `agents`
3. Create parallel routes/frontend
4. Eventually deprecate agent-like modes from agents

---

## Related ADRs

- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md) — one agent, mode-gated primitives
- [ADR-092: Mode Taxonomy](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) — five modes, signal processing dissolved
- [ADR-101: Agent Intelligence Model](../adr/ADR-101-agent-intelligence-model.md) — four-layer knowledge shared across all modes
- [ADR-102: yarnnn Content Platform](../adr/ADR-102-yarnnn-content-platform.md) — agent outputs as platform_content
