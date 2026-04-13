# Agent Playbook Framework — Design Document

**Status:** Phase 1 Implemented
**Date:** 2026-04-04
**Related:** ADR-118 (skills/SKILL.md convention), ADR-140 (agent workforce), ADR-143 (methodology seeding)

## Governing Axioms

These principles govern agent configuration, capability assignment, and playbook design:

1. **Agents develop inward, not outward.** Each agent gets better at its specific domain through accumulated context, feedback, and refined playbooks — not by acquiring new capabilities. The CI agent becomes a better competitor analyst, not a better image generator.

2. **Capabilities are fixed, methodology evolves.** What an agent CAN do (chart, mermaid, image) is set at creation by type. HOW it does it (playbooks) evolves with feedback. Capabilities = axis 2 (fixed). Playbooks = accumulated institutional knowledge.

3. **Production is a specialization, not a shared concern.** Visual production (image generation, video composition) belongs to agents whose identity is *production* — Marketing & Creative. Domain agents (CI, Market Research, Operations) produce data visualizations (charts, diagrams) as part of analysis, but not creative/editorial visuals.

4. **Multi-agent collaboration via process steps, not capability sharing.** When a deliverable needs deep analysis AND rich visuals, the answer is a multi-step process (researcher analyzes → producer creates), not giving the researcher image generation. The `process` array in task types supports this.

5. **Playbooks are the agent development substrate.** They accumulate domain-specific methodology — the agent's institutional knowledge about how to do its work. Feedback distillation refines playbooks over time. This is how agents get incrementally better each cycle.

## Problem

Agent playbooks (`_playbook-*.md`) are loaded in full into the system prompt on every execution. As playbooks grow (visual production, research methodology, output formatting), prompt token usage scales linearly. The Marketing agent already consumes ~1,200 tokens on playbooks alone.

Current load mechanism (`load_context()`) does a filesystem scan → read all `_playbook*` files → concatenate into system prompt. No filtering by task context, no summarization, no on-demand loading.

## Design Principles

### 1. Index in prompt, content on demand (IMPLEMENTED)

Follow Claude Code's CLAUDE.md pattern: the system prompt contains a **compact index** (~233 tokens) of available playbooks with one-line descriptions + critical rules. Full playbook content is NOT injected — agent reads via ReadWorkspace on demand. Same pattern applied to SKILL.md docs (~102 tokens vs ~1,500 tokens full injection). Total savings: ~3,115 tokens per execution (~39%).

```
## Available Playbooks
- **Outputs**: Report/presentation/document structure and quality criteria
- **Formats**: Format selection heuristics, tone calibration, structural patterns
- **Visual**: Image generation by output type, video construction, asset re-use
```

The agent sees what's available and can reference it when making decisions, but the full content isn't burning prompt tokens on every call.

### 2. Task-type routing

Playbook relevance is deterministic from the task type. A `content-brief` task needs the visual and formats playbooks. A `research-topics` task needs the research playbook. A `track-competitors` task needs neither.

```python
# In task_types.py or agent_framework.py
TASK_PLAYBOOK_MAP = {
    "content-brief": ["visual", "formats", "outputs"],
    "launch-material": ["visual", "formats", "outputs"],
    "research-topics": ["research"],
    "track-competitors": ["research"],
    "competitive-brief": ["outputs", "formats"],
    ...
}
```

Only the relevant playbooks get loaded into the full prompt. Others are indexed but not expanded.

### 3. Playbook registry (not filesystem scan)

Currently playbooks are discovered via filesystem scan (`list("memory/")` + filter by `_playbook` prefix). This is fragile — it can't distinguish between active playbooks and archived ones, and it can't attach metadata (description, relevance tags).

Proposed: playbooks are registered in the agent type definition with metadata:

```python
"methodology": {
    "_playbook-outputs.md": {
        "description": "Report, presentation, and document structure",
        "tags": ["synthesis", "formatting"],
        "content": "# Output Playbook\n\n..."
    },
    "_playbook-visual.md": {
        "description": "Image and video generation by output context",
        "tags": ["visual", "image", "video"],
        "content": "# Visual Production Playbook\n\n..."
    },
}
```

### 4. Cross-agent consistency

The framework must work identically for all agent types. The Marketing agent gets visual playbooks, the Competitive Intelligence agent gets research playbooks, the Executive agent gets synthesis playbooks — same mechanism, different content.

## Current Architecture

```
Agent Creation (agent_creation.py)
  ↓
get_type_playbook(role) → {filename: content}
  ↓
Write to /agents/{slug}/memory/_playbook-*.md
  ↓
[At execution time]
  ↓
load_context() → scan memory/ → read all _playbook* files → concatenate
  ↓
Inject full text into system prompt
```

**Problems:**
1. All playbooks loaded regardless of task relevance
2. Full content in prompt (~1,200 tokens for Marketing, will grow)
3. No metadata (descriptions, tags) for intelligent loading
4. Filesystem scan is blind — can't filter by context

## Proposed Architecture

```
Agent Creation (agent_creation.py)
  ↓
get_type_playbook(role) → {filename: {description, tags, content}}
  ↓
Write to /agents/{slug}/memory/_playbook-*.md (content only, same as now)
  ↓
[At execution time]
  ↓
load_context(task_type=...) 
  ↓
Build playbook index (all playbooks → one-line descriptions)
  ↓
Match task_type → relevant playbook tags
  ↓
Load FULL content only for relevant playbooks
  ↓
System prompt = AGENT.md + playbook index + relevant playbook content
```

**Token impact:**
- Before: ~1,200 tokens (all 3 playbooks loaded)
- After: ~200 tokens (index) + ~400-600 tokens (1-2 relevant playbooks)
- Savings: 40-60% per execution

## What This Framework Governs

For ALL agent types, the playbook framework provides:

| Concern | Current | Proposed |
|---------|---------|----------|
| **What playbooks exist** | Filesystem scan | Registry with metadata |
| **What gets loaded** | Everything | Task-relevant subset |
| **How much prompt space** | Full content always | Index + relevant content |
| **How playbooks are described** | Filename only | Description + tags |
| **Cross-agent consistency** | Same code, different files | Same framework, explicit registry |

## Per-Agent Playbook Catalog (Planned)

| Agent Role (ADR-176) | Playbooks | Tags |
|-----------|-----------|------|
| **Researcher** | outputs, research | research, investigation, web_search |
| **Analyst** | outputs | synthesis, patterns, cross-domain |
| **Writer** | outputs, formats | drafting, formatting, audience |
| **Tracker** | outputs | monitoring, tracking, signals |
| **Designer** | visual | visual, image, video, chart, mermaid |
| **Thinking Partner** | — | orchestration (no playbooks — deterministic executors) |
| **Slack Bot** | outputs | platform, digest |
| **Notion Bot** | outputs | platform, digest |
| **GitHub Bot** | outputs | platform, digest |

## Implementation Phases

### Phase 1: Framework + metadata (IMPLEMENTED)
1. `PLAYBOOK_METADATA` registry — description + tags per playbook file
2. `TASK_OUTPUT_PLAYBOOK_ROUTING` — maps task `output_kind` (4 values) to relevant tags (ADR-166, was `TASK_PLAYBOOK_ROUTING` keyed on the old 2-value `task_class`)
3. `load_context(output_kind=...)` — selective playbook loading based on output_kind
4. `get_playbook_index()` — short index always in prompt (~55-85 tokens)
5. `get_relevant_playbooks(agent_type, output_kind=...)` — full content only for tag-matched playbooks. Returns `{}` for `system_maintenance` (no LLM, no playbooks needed).
6. `ensure_seeded()` — retroactive seeding of missing playbooks from type registry
7. `task_pipeline.py` — passes `output_kind` from TASK.md to `load_context()`

Key files: `agent_framework.py` (registry), `workspace.py` (loading), `task_pipeline.py` (routing)

### Phase 2: Per-agent playbook refinement
1. Review and refine each agent type's playbooks for their specific domain
2. Add visual playbooks to agents that have asset capabilities
3. Test with real task executions

### Phase 3: Playbook evolution (deferred)
1. Playbooks evolve via feedback — TP/user corrections update playbook content
2. Version history for playbooks (same as AGENT.md versioning)
3. Cross-agent playbook sharing (common patterns extracted to shared playbooks)

## Naming Convention

- `_playbook-{topic}.md` — agent-level methodology file
- `_` prefix = infrastructure (not user-facing in workspace explorer)
- Topics: `outputs`, `formats`, `visual`, `research`, `tracking`
- Tags: map to task classes and capability categories

The `_playbook` convention is already established (ADR-143). The framework adds metadata without changing the file naming.

## Relationship to Other Concepts

| Layer | What it governs | Fixed or evolves? | Scope |
|-------|----------------|-------------------|-------|
| **Capabilities** | WHAT an agent can do (chart, image, video) | Fixed per type | Agent type |
| **Playbooks** | HOW an agent uses its capabilities | Evolves with feedback | Agent type, loaded per task class |
| **SKILL.md** | HOW to call the render API | Fixed (skill interface) | Render service |
| **DELIVERABLE.md** | WHAT quality the output must meet | Per task, evolves with feedback | Task instance |
| **Step instructions** | WHEN to do what during execution | Fixed per task type | Task type |
| **Process steps** | WHO does what in sequence | Fixed per task type | Task type (multi-agent) |

Playbooks fill the gap between capabilities and step instructions: the agent knows it CAN produce images (capability) and SHOULD produce a deliverable (step instruction), but the playbook tells it HOW to make good decisions for its domain.

## Capability × Playbook Matrix

Not all agents need all playbooks. Capabilities determine what playbooks are relevant:

| Agent Class | Capabilities | Playbooks | Visual Production? |
|------------|-------------|-----------|-------------------|
| **Researchers** (CI, Market) | chart, mermaid | outputs, research | No — data viz only |
| **Trackers** (Ops, BizDev) | chart (or none) | outputs | No |
| **Producers** (Marketing) | chart, mermaid, image, video | outputs, formats, visual | **Yes** — full visual suite |
| **Synthesizers** (Executive) | chart, mermaid | outputs, formats | No — data viz only |
| **Bots** (Slack, Notion) | none | outputs | No |

Axiom 3 in action: only production-class agents get visual playbooks and image/video capabilities.
