# ADR-115: Composer Workspace Density Model

**Status:** Implementing
**Date:** 2026-03-17
**Builds on:** ADR-111 (Agent Composer), ADR-114 (Substrate-Aware Assessment)

## Context

ADR-114 gave Composer knowledge corpus signals — it now sees what agents have *produced*. But 153 heartbeats over 14 hours all returned `HEARTBEAT_OK` because every heuristic gate was already satisfied: platforms covered, synthesize agent exists, knowledge not stale.

The system is behaving like a senior architect — conservative, only acting on clear gaps. But a new workspace needs the opposite: eager, proactive scaffolding. A junior employee doesn't wait for perfect information — they attempt tasks immediately, accept that early outputs will be imperfect, and self-correct through feedback.

### The Tension

YARNNN has two legitimate but opposing imperatives:

1. **Qualitative accumulation thesis** (mature workspaces): Agents improve over time through feedback, learned preferences, and compounding knowledge. Conservative Composer behavior protects quality.

2. **60-second magic onboarding** (new workspaces): Users need to see autonomous value immediately. An empty dashboard with no agent-generated knowledge is a dead product.

### Why Time-Based Tenure Is Wrong

A "first 72 hours" mode would be arbitrary and fragile:
- A power user connecting 5 platforms at 9am should see eager behavior for minutes, not days
- A user who ignores the platform for 2 weeks would graduate by calendar despite having zero engagement
- Time doesn't correlate with workspace state

## Decision

### Gate on workspace density, not time

Composer's eagerness is determined by **observable workspace state**, computed from signals already collected in `heartbeat_data_query()`:

```python
# Workspace density = f(knowledge_files, total_agent_runs, agent_count)
# All signals already available in the assessment dict — zero additional queries

workspace_density = classify_workspace_density(assessment)
# Returns: "sparse" | "developing" | "dense"
```

**Classification logic (pure function, no LLM):**

| Density | Condition | Composer Behavior |
|---------|-----------|-------------------|
| `sparse` | total_knowledge_files < 5 AND sum(total_runs) < 10 | **Eager** — propose agents even without perfect signal |
| `developing` | everything between sparse and dense | **Proactive** — propose agents for skill types the workspace lacks |
| `dense` | total_knowledge_files > 50 AND 3+ non-nascent agents | **Conservative** — workforce graduated, only act on clear gaps |

**Key design choice**: only `dense` workspaces return HEARTBEAT_OK through the density gate. Both `sparse` and `developing` route to LLM assessment. The difference is framing — sparse says "be eager, attempt anything", developing says "fill skill gaps." Dense is the graduation threshold where Composer trusts the workforce.

### Sparse workspace triggers

When `workspace_density != "dense"`, Composer routes to LLM assessment instead of returning HEARTBEAT_OK:

```python
# Both sparse and developing workspaces route to LLM — only dense graduates to HEARTBEAT_OK
if workspace_density != "dense" and has_substrate:
    if workspace_density == "sparse":
        return True, "sparse_workspace: ... — eager scaffolding mode"
    else:
        return True, "developing_workspace: ... — propose agents for missing skills"
```

This routes to the **existing LLM assessment path** (`run_composer_assessment`). The LLM receives the full workspace context including density label and decides what to create (or observe). No new deterministic creation path needed.

### COMPOSER_SYSTEM_PROMPT v1.2: Eager framing

The system prompt gains a workspace-density-aware principle:

```diff
  ## Principles
  - Bias toward action: if an agent would clearly help, recommend creating it
+ - In sparse workspaces (few knowledge files, few runs): be eager. Propose research
+   or analysis agents even without perfect signal. Early outputs that the user corrects
+   are more valuable than silence. Think like a junior employee — attempt the task,
+   accept feedback, improve.
+ - In dense workspaces (many knowledge files, mature agents): be conservative. Only
+   propose agents that fill clear gaps in the knowledge corpus.
  - Start with highest-value agents: platform digests before cross-platform synthesis before research
```

### What the LLM sees in sparse mode

The prompt trigger line will be:

```
## Trigger
sparse_workspace: workspace has 2 knowledge files and 3 total runs — eager scaffolding mode
```

Combined with the existing Knowledge Corpus section showing "Digests: 2, Analyses: 0, Research: 0", the LLM has enough context to propose a research or analysis agent. It may be wrong — and that's the point. The user corrects, the agent learns, the quality accumulates.

### Density classification in assessment dict

Add `workspace_density` to the return dict from `heartbeat_data_query()`:

```python
"workspace_density": "sparse",  # computed from knowledge + maturity signals
```

Also surface in `_build_composer_prompt()` and `run_heartbeat()` assessment_summary metadata.

## What This Is NOT

- **Not a separate "onboarding mode"** — workspace density is a continuous signal, not a toggle
- **Not deterministic agent creation** — sparse workspace routes to LLM assessment, same as all other non-coverage heuristics. The LLM decides what to create (or observe).
- **Not time-gated** — a workspace can be sparse for 1 hour or 30 days. It stays eager until knowledge accumulates.
- **Not lowering quality bars** — mature workspace agents still have the same approval/edit-distance lifecycle. Eager mode creates more agents; feedback loops still govern quality.

## Self-Correcting Properties

1. **Sparse → developing → dense is automatic**: As agents run and produce knowledge, density progresses. Once it crosses 50 files with 3+ non-nascent agents, density becomes "dense" and Composer becomes conservative.
2. **Underperformer lifecycle still fires**: If an eagerly-created agent gets poor feedback, the existing `lifecycle_underperformer` heuristic pauses it (8+ runs, <30% approval). The junior employee gets coached.
3. **Tier limits still apply**: Sparse workspace eagerness can't exceed the user's agent limit. Free tier (2 agents) naturally constrains overeager creation.
4. **No new DB queries**: Density is computed from signals already in the assessment dict.

## Implementation

Single file change: `api/services/composer.py`

1. Add `classify_workspace_density()` — pure function, ~15 lines
2. Add density to `heartbeat_data_query()` return dict
3. Add `sparse_workspace` heuristic to `should_composer_act()` — before final `HEARTBEAT_OK`
4. Update `COMPOSER_SYSTEM_PROMPT` to v1.2 with eager/conservative principle
5. Add density to `_build_composer_prompt()` context
6. Add density to `run_heartbeat()` assessment_summary

## References

- ADR-111: Agent Composer — lifecycle progression signals
- ADR-114: Composer Substrate-Aware Assessment — knowledge corpus signals
- FOUNDATIONS.md: Axiom 2 (Recursive Perception) — accumulated knowledge as substrate
