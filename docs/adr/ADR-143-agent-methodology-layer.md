# ADR-143: Agent Methodology Layer

**Status:** Proposed
**Date:** 2026-03-25
**Extends:** ADR-106 (workspace), ADR-117 (feedback substrate), ADR-128 (coherence protocol), ADR-140 (workforce model)
**Informed by:** Anthropic's "Harness Design for Long-Running Apps" (2026-03-24)

## Context

Agents currently have identity (AGENT.md), taste preferences (memory/preferences.md), and self-assessment (memory/self_assessment.md). What's missing is **craft knowledge** — how an agent produces specific output formats well.

A research agent knows *what* to investigate (AGENT.md) and *what the user likes* (preferences.md), but not *how to structure a research report* or *when to use charts vs tables*. This craft knowledge is implicit in the LLM's general capabilities, producing generic outputs.

The Anthropic harness design article identifies this gap: their evaluator needed explicit, concrete criteria to produce quality assessments. Generic LLM judgment approved mediocre work. The same applies to generation — generic LLM knowledge produces generic outputs.

### The Human Analogy

A senior employee accumulates methodology over time:
- **Taste** (preferences.md): "My manager prefers concise slides" — what the audience wants
- **Craft** (methodology): "Presentations work best as problem-solution-evidence" — how to produce well
- **Self-awareness** (self_assessment.md): "I'm strong on market data, weak on competitive analysis" — what I'm good at

All three are agent-level knowledge, independent of any specific task. Tasks *apply* this knowledge; feedback *refines* it.

## Decision

### 1. Methodology Files — Flat in memory/

Each agent type gets seeded methodology files at creation:

```
/agents/{slug}/
  ├── AGENT.md                           ← identity (axis 1)
  ├── memory/
  │   ├── preferences.md                 ← taste (from user edits)
  │   ├── self_assessment.md             ← self-awareness (rolling 5)
  │   ├── methodology-outputs.md         ← NEW: how to produce deliverables
  │   ├── methodology-research.md        ← NEW: how to investigate (research/marketing only)
  │   └── observations.md, goal.md, ...  ← existing
```

Files are flat in `memory/` (not a subdirectory) so existing `load_context()` auto-loads them with zero code changes.

### 2. Naming Convention

`methodology-{topic}.md` — the `methodology-` prefix makes them identifiable for future tooling. Topics are agent-type-specific:

| Agent Type | Methodology Files | Rationale |
|-----------|-------------------|-----------|
| `research` | `methodology-outputs.md`, `methodology-research.md` | Produces reports + does investigation |
| `content` | `methodology-outputs.md`, `methodology-formats.md` | Produces deliverables in multiple formats |
| `marketing` | `methodology-outputs.md`, `methodology-research.md` | GTM analysis + market reports |
| `crm` | `methodology-outputs.md` | Relationship briefs, meeting prep |
| `slack_bot` | `methodology-outputs.md` | Recaps, summaries |
| `notion_bot` | `methodology-outputs.md` | Knowledge base updates |

Every agent gets `methodology-outputs.md` (how to structure and deliver output). Agents with investigation capabilities also get `methodology-research.md`.

### 3. Seed Content — Type-Specific Defaults

Seeded at agent creation from `AGENT_TYPES` registry. The seed is a starting point — it evolves through feedback.

**methodology-outputs.md** (per-type defaults):
- Research: structured analysis with evidence sections, executive summary, data visualization heuristics
- Content: deliverable formatting patterns, slide/report/document structure, asset integration guidance
- Marketing: GTM report structure, competitive positioning format, market signal organization
- CRM: relationship brief format, meeting prep structure, follow-up tracking
- Slack bot: recap format, thread summary patterns, alert structure
- Notion bot: page update patterns, knowledge organization

**methodology-research.md** (research + marketing):
- Source evaluation hierarchy
- Investigation depth heuristics (when to go deeper vs synthesize)
- Evidence citation patterns
- Cross-reference strategies

### 4. Evolution via Feedback — Append-at-Top with Cap

Methodology files follow the **overwrite** pattern (like preferences.md), not the append pattern (like self_assessment.md). Rationale: methodology represents "current best understanding of how to produce well" — same as preferences represents "current best understanding of what user wants."

When feedback distillation runs, it classifies signals:
- **Taste signals** → `preferences.md` (what to include/exclude, tone, length)
- **Craft signals** → `methodology-outputs.md` (structural changes, format adjustments, visual usage patterns)

Classification heuristic:
- User adds/removes content sections → taste (preferences.md)
- User restructures output format, changes heading hierarchy, moves sections → craft (methodology-outputs.md)
- User adds/removes charts, changes visualization approach → craft (methodology-outputs.md)
- User changes wording/tone → taste (preferences.md)

### 5. TP Methodology — Deferred

TP is intentionally stateless per session. Its "methodology" is its system prompt + primitive definitions, which are code-level artifacts. TP methodology evolution would mean the system prompt adapts per user — this is architecturally different and should be a separate ADR if pursued.

For now, TP's orchestration knowledge (how to decompose tasks, which agents to assign) remains in its prompt. This is consistent with ADR-140's treatment of TP as infrastructure, not a workforce agent.

### 6. Task-Level Application

Tasks don't carry their own methodology. Instead:
- Task TASK.md carries the *what* (objective, format, audience)
- Agent methodology carries the *how* (production patterns for that format type)
- The agent reads both at execution time and applies methodology to task requirements

This matches the human analogy: you know how to make presentations (methodology), and each presentation has specific requirements (task). The methodology is yours; the task is assigned.

### 7. Scalability — Why Overwrite Works Long-Term

Methodology files are **overwritten** (not appended), so they don't grow unboundedly. Each overwrite captures the current-best methodology, not a log. The `_archive_to_history()` mechanism (ADR-119 Phase 3) preserves up to 5 previous versions automatically.

This means:
- File size stays bounded (methodology is a document, not a log)
- History is preserved (5 versions in `/history/`)
- No compaction needed — overwrite IS compaction

## Implementation Plan

### Phase 1: Seed + Read (this ADR)
1. Add `default_methodology` to `AGENT_TYPES` registry entries
2. Update `agent_creation.py` to seed methodology files at creation
3. Verify `load_context()` auto-reads them (zero code change expected)
4. Update `_build_headless_system_prompt()` to label methodology distinctly in context

### Phase 2: Evolve (future)
1. Extend `feedback_distillation.py` with taste/craft classification
2. Craft signals write to `methodology-outputs.md` (overwrite)
3. Self-assessment can note methodology gaps ("I used tables but charts would have been better")

### Phase 3: TP Awareness (future)
1. TP prompt includes agent methodology summaries when assigning tasks
2. TP can suggest methodology refinements based on cross-agent patterns

## Consequences

- Agents produce more structured, format-aware outputs from first run
- Feedback loop differentiates "what to say" from "how to say it"
- No new tables, no new registries — methodology is workspace files
- `load_context()` works unchanged — methodology auto-injected
- Scalability: overwrite pattern + archive keeps files bounded
