# ADR-018: Recurring Agents Product Pivot

**Status:** Accepted
**Date:** 2026-02-01
**Supersedes:** ADR-017 (extends, doesn't replace)
**Companion Docs:**
- `docs/strategy/YARNNN_STRATEGIC_DIRECTION.md`
- `docs/development/YARNNN_CLAUDE_CODE_BUILD_BRIEF.md`

## Context

YARNNN is pivoting from a general-purpose "context-aware AI work platform" to a **recurring agents product**. Strategic rationale is documented in the companion strategy document. This ADR captures the architectural decisions.

## Decision

### Core Concept

A **Agent** is a recurring commitment to produce something for someone on a schedule. Each execution produces a **AgentVersion** with draft content, user edits captured as feedback, and quality metrics.

### Data Model

New entities:
- `agents` - the recurring commitment (title, recipient, schedule, sources, template)
- `agent_runs` - each execution (draft, final, edit diff, feedback categories, edit distance)

Extended entities:
- `work_tickets` - add `depends_on_work_id`, `chain_output_as_memory`, `agent_id`, `pipeline_step`
- `memories` - add source types: `agent_output`, `agent_feedback`

### Execution Pipeline

3-step chained agent pipeline per agent execution:

1. **Gather** (research agent) → collect context from sources → output saved as memory
2. **Synthesize** (content agent) → produce agent using accumulated context + learned preferences
3. **Stage** → format, set status, notify user

Work chaining via `depends_on_work_id` ensures sequential execution within a pipeline run.

### Feedback Engine

Core differentiator. When user edits staged agent before approval:
1. Compute structured diff (draft vs. final)
2. Categorize edits: additions, deletions, restructures, rewrites
3. Store as `agent_feedback` memory
4. Include in future synthesis context

Quality metric: `edit_distance_score` (0.0 = no edits, 1.0 = complete rewrite). Should decrease over versions.

### Frontend

Primary surface shifts from Projects to **Agents Dashboard**:
- Upcoming agents
- Staged awaiting review
- Quality trends

Onboarding is agent-first: "What do you deliver?" not "Create a project"

## Consequences

### Positive
- Concrete, measurable value prop ("your 10th delivery is better than your 1st")
- Natural context accumulation through agent production
- Positions for A2A infrastructure without requiring users to understand it
- Feedback loop creates switching cost moat

### Negative
- Narrower initial scope than "general AI work platform"
- Requires users to have recurring agent commitments
- First-delivery quality is critical (no feedback loop yet)

### Technical Debt Addressed
- Work chaining closes the "no dependencies" gap identified in codebase assessment
- Output-to-memory conversion closes the "outputs don't feed context" gap

## Implementation

See `docs/development/IMPLEMENTATION_PLAN.md` for phased execution plan.
