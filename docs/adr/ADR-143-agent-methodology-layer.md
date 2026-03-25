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

### 4. Feedback Consolidation — One File, One Signal

**Problem:** Agent memory had 5 files competing for the same job ("make the agent better next time"): preferences.md, observations.md, supervisor-notes.md, review-log.md, and the proposed feedback.md. Too many files without clarity.

**Decision:** Consolidate all correction signals into a single `feedback.md`. Each file has one clear owner and one clear reader:

| File | Writer | Reader | Purpose |
|------|--------|--------|---------|
| `methodology-*.md` | Seeded at creation; TP updates | Agent | How to produce (craft baseline) |
| `feedback.md` | TP (conversational + edit-based) | Agent | What to change next time |
| `self_assessment.md` | Agent (post-run) | TP | How agent thinks it did |

**Deleted (absorbed into feedback.md):**
- `preferences.md` — taste rules derived from edits
- `supervisor-notes.md` — Composer coaching
- `observations.md` — runtime notes
- `review-log.md` — approval/rejection history

**feedback.md format:** Append-at-top with rolling 10-entry cap (same pattern as self_assessment.md):

```markdown
# Feedback History
<!-- Most recent first. Max 10 entries. TP writes, agent reads. -->

## Run 14 (2026-03-25)
- Approved without changes. Current approach is working.

## Run 13 (2026-03-24)
- User edited: moved executive summary above detailed analysis
- User edited: removed competitor pricing section
- User edited: added "Next Steps" section at end
- User said: "Keep it under 2 pages next time"
```

**Triggers for writing feedback.md:**

| Trigger | Writer | Mechanism |
|---------|--------|-----------|
| User edits agent output | `feedback_distillation.py` | PATCH /api/agents/{id}/runs/{run} → compute edit_categories → format as entry → append |
| User approves without edits | `feedback_distillation.py` | Same endpoint → brief positive entry |
| User rejects / requests re-run | `feedback_distillation.py` | Same endpoint → negative entry |
| User gives feedback in conversation | TP via `WriteAgentFeedback` primitive | TP detects feedback intent → writes to agent's feedback.md |

### 5. TP as Feedback Supervisor

TP is the only entity that sees both agent output and user reaction. TP's role in the feedback loop:

- **Conversational feedback:** When user says "that report was too long" or "I liked the charts", TP writes to the relevant agent's feedback.md via `WriteAgentFeedback` primitive.
- **Orchestration knowledge:** TP's own methodology lives in its system prompt (`api/agents/tp_prompts/*.py`), not in workspace files. TP is infrastructure, not workforce (ADR-140).
- **Methodology updates:** Future — TP can overwrite methodology-*.md when it observes repeated structural patterns in feedback.md.

### 6. Task-Level Application

Tasks don't carry their own methodology. Instead:
- Task TASK.md carries the *what* (objective, format, audience)
- Agent methodology carries the *how* (production patterns for that format type)
- The agent reads both at execution time and applies methodology to task requirements

### 7. Scalability

- `methodology-*.md`: Overwritten (not appended), bounded size. Auto-versioned to `/history/` (5 versions).
- `feedback.md`: Append-at-top, capped at 10 entries. Old entries drop off naturally.
- `self_assessment.md`: Append-at-top, capped at 5 entries.

No compaction needed. All files stay bounded.

## Implementation Plan

### Phase 1: Seed + Read (Implemented)
1. ~~Add `methodology` to `AGENT_TYPES` registry entries~~
2. ~~Update `agent_creation.py` to seed methodology files at creation~~
3. ~~Verify `load_context()` auto-reads them~~
4. ~~Update `load_context()` to label methodology distinctly~~

### Phase 2: Feedback Consolidation (This Phase)
1. Rewrite `feedback_distillation.py` — all edit signals → `feedback.md` append-at-top
2. Delete `preferences.md`, `observations.md`, `supervisor-notes.md`, `review-log.md` write paths
3. Clean all read paths in `agent_execution.py`, `task_pipeline.py`, `workspace.py`
4. Add `WriteAgentFeedback` primitive for TP conversational feedback
5. Update TP prompt with feedback behavior
6. Clean frontend types and components

### Phase 3: TP Feedback Intelligence (Future)
1. TP observes patterns across feedback.md entries → updates methodology-*.md
2. TP prompt includes agent feedback summaries when reviewing agent work

## Consequences

- Agent memory: 3 files with clear ownership (methodology, feedback, self-assessment) instead of 6 overlapping files
- Feedback is the conversation — user's most natural signal path captured via TP
- Edit-based feedback preserved as mechanical fallback
- No new tables, no new registries — workspace files only
- Scalability: all files bounded (overwrite or capped append)
