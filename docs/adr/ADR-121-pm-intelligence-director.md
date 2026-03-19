# ADR-121: PM as Project Intelligence Director

> **Status**: Phase 1 Implemented
> **Date**: 2026-03-19
> **Authors**: KVK, Claude
> **Extends**: ADR-120 (Project Execution & Work Budget)
> **Implements**: FOUNDATIONS.md Axiom 1 (PM developmental trajectory), Axiom 3 (agents develop inward)
> **Related**: ADR-117 (Feedback Substrate), ADR-118 (Skills), ADR-111 (Composer)

---

## Context

ADR-120 established PM as a logistics coordinator: check freshness → assemble when ready → enforce budget. Production validation (2026-03-19) proved the pipeline works end-to-end — PM correctly decided to assemble, RuntimeDispatch produced a 34.5KB PPTX, email delivered. The mechanics are sound.

**The problem**: The assembled output was qualitatively thin. All three test projects produced near-identical content because:
1. Contributors drew from the same platform content (same Slack/Notion corpus)
2. PM has no mechanism to assess contribution **quality**, only **freshness**
3. PM cannot steer contributors toward different aspects of the data
4. When the knowledge base is thin, PM just assembles what it has — it doesn't say "we need more data on X"

**The gap in FOUNDATIONS.md**: Axiom 1 says PM "accumulates project knowledge" and "a mature PM adapts timing, suggests contributor changes, and refines assembly format based on feedback history." But the current PM prompt and decision set only implements the logistics side. The **intelligence** side — reasoning about what the project needs, directing investigation, assessing whether contributions actually serve the intent — is unimplemented.

**Why this matters now**: The product's gravity has shifted from individual agents to projects. Users create projects to get composed deliverables. If the PM is purely logistical (fresh? → assemble), projects are just mechanical combinations of whatever agents happen to produce. The value proposition — agents that develop and improve — requires the PM to be an active intelligence that shapes what contributors produce, not just when they produce.

## Decision

### PM Evolves from Logistics Coordinator to Intelligence Director

The PM's role expands along two axes:

**Axis 1: Qualitative Assessment** — PM evaluates not just "is the contribution fresh?" but "does this contribution adequately serve the project intent?"

**Axis 2: Directive Steering** — PM can communicate specific focus areas, questions, or investigation priorities to contributors, shaping their next output rather than just triggering it.

### Separation: Mechanics vs. Intelligence

PM has two distinct concerns that evolve independently and must be version-controlled separately:

| Concern | What | Where | Versioning |
|---------|------|-------|------------|
| **Mechanics** | Decision routing, assembly pipeline, budget enforcement, workspace writes | `agent_execution.py`, `agent_pipeline.py`, primitives | Code versioning (git) |
| **Intelligence** | PM reasoning prompt, quality assessment criteria, steering heuristics, assembly composition prompt | `agent_pipeline.py` ROLE_PROMPTS["pm"], ASSEMBLY_COMPOSITION_PROMPT | Prompt versioning (CHANGELOG.md) |

This separation is critical because:
- Mechanics changes are testable, deterministic, and rarely regress
- Intelligence changes are qualitative, model-dependent, and require eval
- A prompt change should never require a code change and vice versa
- The PM prompt version must be tracked independently (like Composer: v1.0, v1.3, v2.0, v2.1)

### New PM Decision Actions

Current (ADR-120): `assemble`, `advance_contributor`, `wait`, `escalate`, `update_work_plan`

Added:

| Action | What | When |
|--------|------|------|
| `steer_contributor` | Advance a contributor with a specific directive — focus area, question, or investigation priority written to their project contribution brief | Contribution exists but doesn't adequately serve the intent; knowledge is thin on a specific topic |
| `request_investigation` | Ask a research-capable contributor (or request TP create one) to investigate a specific question scoped to the project | Project needs external data or deeper analysis that no current contributor provides |
| `assess_quality` | Evaluate current contributions against intent before deciding to assemble | Before every assembly — replaces the current "fresh = ready" logic |

### Steering Mechanism: Contribution Briefs

Today, contributors write to `/projects/{slug}/contributions/{agent-slug}/output.md`. The PM has no way to influence *what* they produce.

**New convention**: PM writes `/projects/{slug}/contributions/{agent-slug}/brief.md` — a project-scoped directive that the contributing agent's execution strategy reads and injects into its prompt. The brief contains:
- What the project needs from this contributor specifically
- Focus areas or questions to address
- What's missing from their last contribution
- How their output fits the larger assembly

This is the PM exercising domain expertise: "Cross-Platform Synthesis, last time you only covered Slack. The project intent requires cross-platform analysis — please also examine Notion activity around product decisions."

Contributing agents read their brief during context gathering (same as reading AGENT.md). The brief is additive — it augments, not replaces, the agent's own instructions.

### Quality Assessment: Intent-Contribution Alignment

Before assembling, PM evaluates each contribution against the project intent:

```
For each contributor:
  1. Read their latest output
  2. Score: does this output serve the project intent?
     - Coverage: does it address the aspects the intent requires?
     - Depth: is it substantive enough for the audience?
     - Differentiation: does it bring unique value vs. other contributors?
  3. Decision:
     - Sufficient → mark ready for assembly
     - Thin but usable → assemble with caveat
     - Inadequate → steer_contributor with specific guidance
```

This replaces the current binary "fresh/stale" check with a qualitative assessment that uses the PM's LLM reasoning.

### PM Prompt Versioning

The PM prompt is a versioned artifact, tracked in `api/prompts/CHANGELOG.md`:

| Version | Date | Description |
|---------|------|-------------|
| v1.0 | ADR-120 P1 | Logistics: freshness + assemble/wait/escalate |
| v1.1 | ADR-120 P4 | + intentions, budget awareness, work plan |
| v1.2 | 2026-03-19 | + CRITICAL JSON enforcement, resilient parsing |
| **v2.0** | This ADR | Intelligence Director: quality assessment, steering, investigation |

The PM prompt v2.0, assembly composition prompt, and contributor brief injection are all prompt changes that require CHANGELOG entries and independent evaluation.

### What PM Still Does NOT Do

- **Create or dissolve agents** — escalates to TP/Composer
- **Modify agent instructions** — writes briefs, not AGENT.md
- **Manage agents outside its project** — PM scope is strictly project-bounded
- **Override user intent** — PM refines execution, not purpose

## Implementation Phases

### Phase 1: Structural Foundation + Quality Assessment (Implemented 2026-03-19)
- PM prompt v3.0 (Intelligence Director) with `assess_quality` and `steer_contributor` actions
- Contribution brief convention (`/contributions/{slug}/brief.md`) — `write_brief()` + `read_brief()` on ProjectWorkspace
- Contributing agent execution reads brief during context gathering (injected as "PM Directive")
- `_handle_pm_decision()` routes new actions: `steer_contributor` (writes brief + advances agent), `assess_quality` (writes assessment + logs)
- PM receives contribution content excerpts (500 chars) in prompt context — enables quality reasoning
- Quality scoring in PM prompt: coverage, depth, differentiation against intent
- Assembly composition prompt v2.0 — intent-driven structure, quality notes, gap acknowledgment
- CHANGELOG entry [2026.03.19.5] for PM prompt v3.0 + assembly prompt v2.0

### Phase 2: Contribution Bridge + Assembly Gating + Work Plan Evolution (Implemented 2026-03-19)
- **Critical gap closed**: `_write_contribution_to_projects()` — agent output auto-written to `/projects/{slug}/contributions/{agent_slug}/output.md` after delivery. PM can now read actual content.
- Assembly gating: informational log when PM assembles without prior quality assessment (prompt-level guidance handles the loop)
- Work plan evolution: `focus_areas` per contributor persisted in `memory/work_plan.md`
- Cross-cycle learning: quality assessment → work plan → briefs → contributor output → re-assessment (all mechanical pieces now connected)

### Phase 3: Investigation & Expansion (Deferred)
- `request_investigation` action — PM writes investigation request, TP/Composer creates or assigns research agent
- **Deferred because**: No PM→Composer request path exists. PM can escalate (which Composer sees via heartbeat), but cannot directly request agent creation. Requires new Composer trigger type (`pm_investigation_request`). Will implement when escalation path proves inadequate in production.
- Cross-cycle learning — PM's observations about what makes good contributions feed back into briefs (partially addressed by Phase 2: quality_assessment.md → work_plan.md → briefs → contributor output)

### Phase 4: PM Developmental Trajectory (Deferred)
- Nascent PM: follows ADR-120 logistics (assemble when fresh)
- Associate PM: starts assessing quality, writes first briefs
- Senior PM: full intelligence director — steers, investigates, refines assembly format
- PM seniority derived from assembly feedback (user edits on assembled output)
- **Deferred because**: Feedback substrate (ADR-117) only tracks agent-level edits, not assembly-level. PM's assembled output goes through agent_runs dual-write as a PM run, so user edits on assemblies land on PM's preference profile — not attributed to contributing agents. Requires feedback attribution for assembled outputs before PM seniority can be meaningfully derived.

## Relationship to FOUNDATIONS.md

This ADR implements the already-stated but unimplemented aspects of Axiom 1:

> "A mature PM agent understands what its project needs — which contributions are stale, when to assemble, how to decompose the user's intent into executable work."

And extends it:

> A mature PM also understands *what quality of contribution serves the intent* — which aspects are underexplored, which contributors need guidance, and when the project needs investigation beyond what current contributors provide.

## Relationship to Existing Architecture

| Component | Impact |
|-----------|--------|
| `agent_pipeline.py` ROLE_PROMPTS["pm"] | v2.0 rewrite — intelligence actions + quality assessment |
| `agent_pipeline.py` ASSEMBLY_COMPOSITION_PROMPT | v2.0 — intent-aware, contribution quality metadata |
| `agent_execution.py` `_handle_pm_decision()` | New action routing: `steer_contributor`, `request_investigation`, `assess_quality` |
| `agent_execution.py` `_compose_assembly()` | Receives quality assessment context |
| Execution strategies | Read `/contributions/{slug}/brief.md` during context gathering |
| `workspace.py` ProjectWorkspace | `write_brief()`, `read_brief()` methods |
| `api/prompts/CHANGELOG.md` | PM prompt v2.0 entry, assembly prompt v2.0 entry |

## What This Does NOT Change

- Work budget mechanics (ADR-120 P3) — unchanged
- Composer's role — still creates/dissolves projects and agents
- Assembly pipeline mechanics — still contributions → compose → render → deliver
- Two-layer intelligence model — PM is still domain-cognitive, not a third layer
