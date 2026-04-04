# Agent Playbook Framework — Design Document

**Status:** Design
**Date:** 2026-04-04
**Related:** ADR-118 (skills/SKILL.md convention), ADR-140 (agent workforce), ADR-143 (methodology seeding)

## Problem

Agent playbooks (`_playbook-*.md`) are loaded in full into the system prompt on every execution. As playbooks grow (visual production, research methodology, output formatting), prompt token usage scales linearly. The Marketing agent already consumes ~1,200 tokens on playbooks alone.

Current load mechanism (`load_context()`) does a filesystem scan → read all `_playbook*` files → concatenate into system prompt. No filtering by task context, no summarization, no on-demand loading.

## Design Principles

### 1. Index in prompt, content on demand

Follow Claude Code's CLAUDE.md pattern: the system prompt contains a **short index** of available playbooks with one-line descriptions. The full playbook content is loaded only when relevant to the current task.

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

| Agent Type | Playbooks | Tags |
|-----------|-----------|------|
| **Competitive Intelligence** | outputs, research | synthesis, research, investigation |
| **Market Research** | outputs, research | synthesis, research, market |
| **Business Development** | outputs | synthesis, relationships |
| **Operations** | outputs | synthesis, projects, tracking |
| **Marketing & Creative** | outputs, formats, visual | synthesis, formatting, visual, image, video |
| **Executive Reporting** | outputs, formats | synthesis, formatting, cross-domain |
| **Slack Bot** | outputs | platform, digest |
| **Notion Bot** | outputs | platform, digest |

## Implementation Phases

### Phase 1: Framework + metadata (this scope)
1. Add `description` and `tags` to playbook definitions in agent_framework.py
2. Update `load_context()` to accept `task_type` parameter
3. Build playbook index (short descriptions) for system prompt
4. Load full content only for tag-matched playbooks
5. Document the framework in architecture docs

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

- **Capabilities** (agent_framework.py) — WHAT an agent can do (chart, image, video). Fixed per type.
- **Playbooks** (methodology) — HOW an agent uses its capabilities. Seeded per type, evolves with feedback.
- **SKILL.md** (render service) — HOW to call the render API. Technical interface docs.
- **DELIVERABLE.md** (per task) — WHAT quality the output must meet. Task-specific contract.
- **Step instructions** (task_types.py) — WHEN to do what during execution. Task-type-level.

Playbooks fill the gap between capabilities and step instructions: the agent knows it CAN produce images (capability) and SHOULD produce a deliverable (step instruction), but the playbook tells it HOW to make good visual decisions for its domain.
