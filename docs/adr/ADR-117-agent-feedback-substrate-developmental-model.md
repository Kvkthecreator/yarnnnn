# ADR-117: Agent Feedback Substrate & Developmental Model

**Status:** Phase 1 Implemented, Phases 2-3 Proposed
**Date:** 2026-03-17
**Builds on:** ADR-101 (Intelligence Model), ADR-106 (Workspace Architecture), ADR-109 (Agent Framework), ADR-111 (Composer)
**Unparks:** `docs/analysis/agent-developmental-model-considerations.md` (was blocked on TP Composer clarity — ADR-111 now implemented)

## Context

### Three Disconnected Feedback Rails

Agents today receive feedback from three sources, each on a separate rail:

1. **User edits** → `agent_runs.edit_categories` + `feedback_notes` → injected into prompt via `get_past_versions_context()` as raw patterns ("User added: X, User removed: Y")
2. **Agent self-observation** → `workspace/memory/observations.md` → loaded via `load_context()` — but **only for analyst/research scope agents**. Digest agents (the majority) never accumulate workspace memory.
3. **Composer lifecycle** → maturity signals (approval_rate, edit_distance_trend) → used for pause/promote decisions in `should_composer_act()` — but **never communicated to the agent itself**

### What's Missing

- **Digest agents have no longitudinal memory.** They receive a platform dump, generate, forget. The `get_past_versions_context()` injection gives them raw edit patterns, but no accumulated domain understanding, no thesis, no observations. Every run starts from zero context beyond the platform dump.

- **Feedback is never distilled.** Raw edit patterns ("User added: action items, User removed: meeting summaries") are injected verbatim. They're never converted into persistent behavioral adjustments. After 10 runs, the agent has 10 raw patterns — not a refined understanding of what the user wants.

- **Composer and agent don't share a feedback substrate.** Composer knows the agent has 70% approval. The agent doesn't know where it stands. Composer can pause an underperformer, but can't write "focus more on action items" to the agent's workspace. The supervisor can fire but can't coach.

- **No path from single-skill to multi-capability.** FOUNDATIONS.md Axiom 3 describes agents evolving from digest → monitor → research → act within a domain. ADR-109 says "one agent, one skill" at inception. But there's no mechanism to add capabilities to a maturing agent. The only option today is Composer creating a separate agent — which fragments the accumulated context.

### The Junior Employee Analogy

If agents are junior employees:
- User feedback is direct supervisor coaching
- Composer assessments are HR/management reviews
- Self-reflection is the employee's own professional development

Today these three channels produce feedback that goes to three different places. A real employee has one brain that integrates all feedback sources. The agent needs one too — its **workspace**.

## Decision

### Principle: The Workspace IS the Unified Feedback Substrate

All feedback — regardless of source — converges to the agent's workspace files, distinguished by source and weight. The workspace is the agent's persistent brain, not just a storage layer.

```
/agents/{slug}/
  AGENT.md                     # Identity + instructions (Composer/user-authored)
  thesis.md                    # Domain understanding (agent-authored, evolves)
  /memory/
    preferences.md             # Distilled from user edits (system-written post-delivery)
    observations.md            # Agent's own reflections (agent-written post-generation)
    supervisor-notes.md        # Composer/TP assessments (system-written on lifecycle events)
  /intentions/                 # Phase 3: multi-intention support
    {intention-slug}.md        # Per-intention config, trigger, quality tracking
```

### Feedback Source Hierarchy

When feedback conflicts, source weight determines precedence:

| Source | Weight | Example | Written To |
|--------|--------|---------|-----------|
| **User explicit** (edit, instruction change) | Highest | User removes meeting summaries section | `memory/preferences.md` |
| **User implicit** (approval without edit) | High | Approved 5 straight runs — format is correct | `memory/preferences.md` (positive signal) |
| **Composer/TP assessment** | Medium | "Agent is underperforming on action item coverage" | `memory/supervisor-notes.md` |
| **Agent self-reflection** | Base | "This run had thin Slack data — 3 channels silent" | `memory/observations.md` |

All sources are visible to the agent on next run via `load_context()`. The agent's system prompt sees the full picture, not fragments.

## Implementation

### Phase 1: Unified Feedback for All Agents

**Goal:** Every agent — including digest — benefits from accumulated workspace memory. User edit patterns are distilled into persistent preferences.

#### 1a. Feedback Distillation (post-delivery hook)

After a version is delivered and the user provides feedback (edit/approve), distill the cumulative feedback history into `memory/preferences.md`:

```python
# Called from agents.py PATCH version endpoint, after edit_categories are computed
async def distill_feedback_to_workspace(client, user_id, agent, agent_run):
    """
    Distill cumulative feedback into workspace preferences.
    Replaces raw pattern injection with structured, persistent preferences.
    """
    ws = AgentWorkspace(client, user_id, get_agent_slug(agent))

    # Get last N runs with feedback
    runs = get_recent_feedback(client, agent["id"], limit=10)

    # Distill patterns into structured preferences
    preferences = _build_preferences(runs)

    await ws.write("memory/preferences.md", preferences,
                   summary="Distilled user feedback preferences")
```

The distillation converts raw edit signals into behavioral directives:
- "User added action items in 4 of 5 runs" → "Always include an Action Items section"
- "User removed meeting summaries in 3 runs" → "Omit detailed meeting-by-meeting summaries"
- "Feedback note: 'too long'" → "Keep output concise — user prefers brevity"

**Key design choice:** `preferences.md` is **overwritten** each time (not appended). It represents the current best understanding of what the user wants, distilled from all available feedback. Old patterns that stop recurring naturally drop out.

#### 1b. Extend Reporter Strategies to Load Workspace Context

Currently, `PlatformBoundStrategy` and `CrossPlatformStrategy` (used by digest/synthesize agents) inject `get_past_versions_context()` as raw patterns. After Phase 1:

1. Reporter strategies call `ws.load_context()` to load AGENT.md + thesis + memory (including `preferences.md`)
2. `get_past_versions_context()` raw injection is removed — the distilled preferences in workspace are the single source of truth
3. Reporter agents remain dump-based for platform content, but gain longitudinal workspace memory

**Singular implementation:** Delete the raw `get_past_versions_context()` injection from reporter strategies. Replace with workspace `load_context()`. One feedback path, not two.

#### 1c. Supervisor Notes (Composer → Agent)

When Composer runs a lifecycle assessment that results in actionable coaching (not just "observe" or "pause"), write a note to the agent's workspace:

```python
# In composer.py, after lifecycle assessment
if decision.get("coaching"):
    ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
    await ws.write("memory/supervisor-notes.md", decision["coaching"],
                   summary="Composer coaching feedback")
```

This bridges the gap where Composer knows the agent is underperforming but the agent doesn't know why.

### Phase 2: Agent Self-Reflection

**Goal:** Agents write brief post-generation observations, accumulating longitudinal domain awareness.

After generating output, the execution pipeline appends a structured observation:

```python
# In agent_execution.py, after successful generation
observation = _extract_observation(draft_content, gathered_context)
ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
await ws.record_observation(observation, source="self")
```

The observation is lightweight — extracted from the generation itself, not a separate LLM call:
- What topics dominated this run
- What sources had thin/no data
- What the agent would investigate further given more time

For digest agents this creates the longitudinal awareness they currently lack: "Slack #engineering has been quiet for 3 consecutive runs" or "Gmail action items keep recurring around quarterly planning."

**The analyst directive already asks for this** (`_build_analyst_directive` lines 400-403). Phase 2 extends self-reflection to all skills, not just analyst scope.

### Phase 3: Intentions Architecture

**Goal:** A mature agent gains additional capabilities within its domain, sharing accumulated workspace context.

This is the formalization of FOUNDATIONS.md Axiom 3:

> "What started as a digest agent now monitors, researches, and acts within its domain."

#### Intentions as Sub-Agent Units of Work

An intention represents one skill × trigger combination within an agent's identity:

```
/agents/slack-recap/intentions/
  digest.md          # skill=digest, trigger=recurring daily, status=active
  monitor.md         # skill=monitor, trigger=reactive, status=proposed (by Composer)
```

Each intention has:
- **Skill** — determines primitives, prompt, output shape
- **Trigger** — determines when this intention fires (independent of other intentions)
- **Status** — proposed | active | paused | retired
- **Quality tracking** — per-intention approval rate, edit distance

The agent's identity (workspace, thesis, memory, preferences) is shared across all intentions. A Slack agent that digests daily and monitors for escalations shares the same accumulated understanding of the user's Slack workspace.

#### Composer Proposes Intentions, Not New Agents

When Composer's substrate assessment detects that a mature platform agent could benefit from monitoring or research:

```json
{"action": "add_intention", "agent_id": "...", "skill": "monitor",
 "trigger": "reactive", "reason": "Agent has 80%+ approval over 10 runs,
 domain thesis is stable — ready for monitoring capability"}
```

This replaces creating a separate "Slack Monitor" agent that fragments the accumulated context.

#### Capability Gating

Capability level is **derived from feedback history**, not a static column:

```python
def get_capability_level(agent_runs) -> str:
    """Derived from approval_rate and edit_distance across recent runs."""
    if approval_rate >= 0.8 and avg_edit_distance < 0.2 and total_runs >= 10:
        return "mature"     # Can earn monitor, research intentions
    if approval_rate >= 0.6 and total_runs >= 5:
        return "developing" # Accumulating, not ready for expansion
    return "nascent"        # Still learning basics
```

This signal already exists in Composer's maturity assessment — Phase 3 makes it available for intention gating.

#### Schema Consideration

Phase 3 may require:
- `agent_intentions` table or workspace-only storage (prefer workspace-first, schema later if needed)
- Execution pipeline changes: unified_scheduler dispatches per-intention, not per-agent
- Agent output tagging: which intention produced this run

**Deferred until Phase 1-2 prove the workspace feedback substrate works.**

## Relationship to Existing Architecture

| Component | Before ADR-117 | After ADR-117 |
|-----------|----------------|---------------|
| Digest agent feedback | Raw edit pattern injection via `get_past_versions_context()` | Distilled `preferences.md` via workspace `load_context()` |
| Digest agent memory | None — no workspace context loaded | Full workspace: AGENT.md + thesis + memory + preferences |
| Composer → agent coaching | Composer pauses/promotes but can't coach | `supervisor-notes.md` in agent workspace |
| Agent self-reflection | Analyst/research only (in `_build_analyst_directive`) | All skills — post-generation observation append |
| Multi-skill agents | Not possible — one agent, one skill forever | Intentions within agent identity (Phase 3) |
| `get_past_versions_context()` | Active — raw pattern injection in all strategies | Phase 1: deleted — replaced by workspace preferences |

### ADR Cross-References Updated

| ADR | Update |
|-----|--------|
| **ADR-101** | Four-layer model valid; Memory and Directives storage updated to workspace (ADR-106). Feedback layer unchanged (agent_runs fields). Phase 1 feedback distillation supersedes raw `get_past_versions_context()` injection. |
| **ADR-106** | Phase 1 foundation enables this ADR. `load_context()` becomes universal (not analyst-only). `memory/preferences.md` and `memory/supervisor-notes.md` are new workspace conventions. |
| **ADR-109** | Scope × Skill × Trigger remains the initial configuration. Intentions (Phase 3) extend, not replace — an agent gains intentions while preserving its seed taxonomy. |
| **ADR-111** | Composer gains coaching capability (supervisor-notes). Intention proposal is a new Composer action alongside create/observe/adjust/dissolve. |
| **FOUNDATIONS.md** | Axiom 3 (Agents as Developing Entities) is formalized. Axiom 5 (TP's Compositional Capability) extended with coaching write-path. |

## What This Is NOT

- **Not autonomous self-modification** — agents don't rewrite their own instructions. They accumulate observations and preferences; the system (or user) distills behavioral changes.
- **Not a new database schema** (Phase 1-2) — workspace files are the substrate. No new tables.
- **Not breaking one-agent-one-skill** (Phase 1-2) — intentions are Phase 3. Phase 1-2 improve feedback quality within the existing single-skill model.
- **Not replacing user feedback primacy** — user edits remain highest-weight. Self-reflection and Composer coaching supplement, not override.

## Open Questions

1. **Distillation frequency:** Should `preferences.md` be rewritten after every feedback event, or batched (e.g., after 3+ new feedback signals)? Start with every event; optimize if workspace writes become expensive.
2. **Observation extraction without LLM:** Phase 2 self-reflection needs structured observation from the generation output. Can this be rule-based (topic extraction, source coverage) or does it need a lightweight LLM pass? Start rule-based; upgrade if insufficient.
3. **Intention scheduling:** Phase 3 intentions need independent triggers. Does the scheduler dispatch per-intention (new concept) or per-agent with intention routing (simpler)? Defer to Phase 3 design.
4. **Intention vs separate agent threshold:** When should Composer propose an intention vs a new agent? Initial heuristic: same platform scope → intention; different scope → new agent.

## References

- FOUNDATIONS.md: Axiom 3 (Agents as Developing Entities), Axiom 4 (Accumulated Attention), Axiom 5 (TP's Compositional Capability)
- ADR-101: Agent Intelligence Model — four-layer knowledge model
- ADR-106: Agent Workspace Architecture — workspace as intelligence persistence layer
- ADR-109: Agent Framework — Scope × Skill × Trigger taxonomy (initial configuration)
- ADR-111: Agent Composer — TP's compositional and lifecycle capability
- ADR-114/115: Composer substrate awareness and workspace density model
- `docs/analysis/agent-developmental-model-considerations.md` — pre-decision analysis (now formalized by this ADR)
