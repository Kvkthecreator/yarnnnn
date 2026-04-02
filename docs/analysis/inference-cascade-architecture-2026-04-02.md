# Inference Cascade Architecture

**Date:** 2026-04-02
**Status:** Implemented (revised) — original backend inference eliminated, TP drives scaffolding via ScaffoldDomains primitive
**Relates to:** ADR-144 (Inference-First Context), ADR-151 (Context Domains), ADR-154 (Phase-Aware Execution), ADR-155 (Workspace Inference & Onboarding)

**Revision note (2026-04-02):** Original proposal had a separate Haiku inference service making domain decisions as a backend side-effect. Audit identified this as a "shadow TP" — violating the single-intelligence-layer principle. Revised: TP calls `ScaffoldDomains` primitive directly. Backend handles template application, TP handles judgment.

## Problem

Bootstrap task execution is disproportionately expensive. A first-run competitive-intelligence task consumed 840K input tokens ($2.62) because the agent started from zero — discovering entities, researching broadly, creating profiles from scratch. But much of what it "discovered" was conventional wisdom the system already knew or could infer from workspace context.

After infrastructure optimizations (prompt caching, microcompact, truncation) and self-directing execution loops (Next Cycle Directive), steady-state cost dropped to ~$0.57/run and is converging toward $0.30. But the bootstrap spike remains.

## Insight: Inference Should Cascade Downstream

The system has three inference levels, but they don't cascade:

```
Level 1: Workspace Identity (IDENTITY.md, BRAND.md)
         "We're a dev tools company building AI coding assistants"
         
Level 2: Context Domains (/workspace/context/competitors/, /market/)
         Entity profiles, trackers, synthesis files
         
Level 3: Task Execution
         Agent research, WebSearch, entity updates
```

**Today**: Level 1 and Level 2 are disconnected. The user tells the TP "we compete with Cursor" → IDENTITY.md gets updated. But the competitors domain stays empty until a task agent runs 8 WebSearches to "discover" that Cursor is a competitor.

**Proposed**: Level 1 inference cascades into Level 2 scaffolding. When IDENTITY.md says "dev tools, AI coding" — the system infers that the competitors domain should contain entities like Cursor, Copilot, Codeium. Entity stubs are pre-created with conventional-wisdom content. Bootstrap research then *validates and deepens* rather than *discovers*.

## The Derivative Effect Principle

The higher upstream the inference, the bigger the derivative effects — both positive and negative.

```
Good inference at L1:  → correct domain scaffolding → targeted research → good output
Bad inference at L1:   → wrong entities → wasted research → misleading output
```

This means **L1 inference must be the most careful**. Safeguards:

### Safeguard 1: Inference Produces Drafts, Not Facts

Entity stubs from inference should be tagged with confidence level:
- `source: inferred` — derived from workspace context, not researched
- `source: user_stated` — user explicitly mentioned this entity
- `source: researched` — agent verified via WebSearch

Bootstrap research validates inferred entities before treating them as established.

### Safeguard 2: The TP Surfaces What Was Inferred

When cascading inference creates domain structure, the TP should tell the user:
"Based on your identity, I've pre-populated your competitors domain with Cursor, Copilot, Codeium, Tabnine. Want me to adjust before research begins?"

This is the human-in-the-loop check at the point of highest leverage.

### Safeguard 3: Inferred Content States What It Doesn't Know

Entity stubs should explicitly mark gaps:
```markdown
# Cursor
## Overview
AI-powered code editor. [Inferred from workspace identity — not yet researched]

## Pricing
[Unknown — needs research]

## Recent Developments
[Unknown — needs research]
```

This gives the bootstrap agent a clear scope: "fill in the [Unknown] sections" rather than "research everything."

## Current Inference Pipeline (as-is)

### Level 1: UpdateSharedContext → IDENTITY.md / BRAND.md
- **Trigger**: TP calls UpdateContext(target="identity|brand", text=...)
- **Engine**: `context_inference.py` — Sonnet, merges with existing content
- **Sources**: user text, uploaded documents, fetched URLs
- **Safeguards**: merge (never overwrite), empty-check, error codes
- **What it doesn't do**: cascade into domain structure

### Level 1.5: Working Memory → Context Readiness
- **What**: `context_readiness` in working memory grades workspace maturity
  - `identity`: empty / sparse / rich
  - `brand`: empty / sparse / rich
  - `documents`: count
  - `tasks`: count
  - `context_domains`: count of non-empty domains
- **Used by**: TP prompt (CONTEXT_AWARENESS) — graduated guidance on what to suggest next
- **What it doesn't do**: trigger domain scaffolding

### Level 2: Task Creation → Domain Scaffolding
- **Current**: CreateTask scaffolds TASK.md, DELIVERABLE.md, awareness.md, memory files
- **Domain folders**: created by `_ensure_domain_folders()` — empty directory structure only
- **What it doesn't do**: infer initial domain content from workspace context

### Level 3: Task Execution → Agent Research
- **Current**: Agent reads empty domain, does 8-16 WebSearches to populate it
- **With directive loop**: Subsequent runs follow agent-authored Next Cycle Directive
- **Problem**: First run has no directive, no domain content — cold start

## Proposed: Workspace-Wide Inference (to-be)

The cascade is NOT per-domain — it's workspace-wide. When the user provides identity context, the system should infer and scaffold ALL domains simultaneously. This is a major workflow, not a background side-effect.

### The Magic Moment

When someone says "I'm a founder of a dev tools startup competing with Cursor, we're raising Series A" — the entire workspace materializes:

```
/workspace/context/
  competitors/    → cursor/, copilot/, codeium/ (inferred from industry)
  market/         → ai-coding-tools/, developer-productivity/ (inferred from product)
  relationships/  → investors/, advisors/ (inferred from "raising Series A")
  projects/       → fundraise/ (inferred from stage)
  content/        → pitch-deck/ (inferred from fundraising)
```

All at once. The user watches folders appear and stubs populate in real time. This IS the onboarding — not a form, not a wait, a live build.

### UX Consideration: Building on the Fly

The user is willing to wait for this — it's a feature, not a delay. The UI should show progressive scaffolding:
- Folders appearing one by one with brief descriptions
- Entity stubs populating with inferred content
- Explicit `[Needs research]` markers showing what's known vs unknown
- A summary: "I've set up 5 domains with 12 entities based on what you told me. Want to adjust?"

This same pattern extends beyond onboarding:
- User connects Slack → workspace re-assesses, scaffolds new structure from channel names/topics
- User uploads a doc → workspace extracts entities and slots them into domains
- User tells TP about a new initiative → new domain/entity structure materializes
- Task modifications → directory structure evolves visually

### Step 1: Workspace Inference Engine

When `UpdateContext(target="identity")` writes IDENTITY.md, trigger a **workspace-wide inference** (Haiku, cheap):

Input: IDENTITY.md + BRAND.md + any connected platforms
Output: Full domain scaffolding plan across ALL domains

```
Inferred workspace structure:
- competitors: [cursor, copilot, codeium, tabnine] (high confidence — user mentioned "competing with Cursor")
- market: [ai-coding-tools, developer-productivity] (medium confidence — inferred from product description)
- relationships: [investors, key-hires] (medium confidence — "raising Series A")
- projects: [series-a-fundraise] (high confidence — explicitly mentioned)
- content: [pitch-materials] (medium confidence — fundraising implies pitch deck needs)
```

**Cost**: ~$0.02-0.05 (single Haiku call with workspace context)

### Step 2: Scaffold All Domains

Execute the scaffolding plan — create entity stubs across all inferred domains:

```
/workspace/context/competitors/cursor/profile.md     → stub with conventional wisdom
/workspace/context/competitors/copilot/profile.md    → stub with known facts
/workspace/context/market/ai-coding-tools/analysis.md → stub with market framing
/workspace/context/relationships/investors/tracker.md → empty, marked for population
```

Stubs contain:
- What the system inferred (entity name, category, relation to user)
- Explicit `[Needs research]` markers on unknown sections
- Source tag: `source: inferred` vs `source: user_stated` vs `source: researched`

### Step 3: Directed Bootstrap

Bootstrap tasks now start warm:
- Domains aren't empty — they have inferred entity stubs
- awareness.md has directive: "Validate inferred entities, fill [Needs research] sections"
- Bootstrap scope is "verify and deepen" not "discover from scratch"
- Estimated rounds: 4-6 targeted searches (not 16 broad ones)

**Cost**: ~$0.30-0.40 (vs $2.62 from cold start)

### Step 4: Continuous Re-Assessment

Every significant new context triggers re-assessment:
- New platform connection → scan channel names/topics → scaffold new entities
- Document upload → extract entities mentioned → slot into domains
- TP conversation → user mentions new competitor/initiative → scaffold
- Task completion → domain health changes → assess gaps

AWARENESS.md at workspace level carries the inference state:

```markdown
## Workspace Inference State
Last inference: 2026-04-02 from IDENTITY.md update

### Scaffolded Domains
- competitors: 4 entities (cursor, copilot, codeium, tabnine) — source: inferred
- market: 2 segments — source: inferred
- relationships: investor category created — source: inferred

### Inference Gaps
- relationships: no specific investor names — needs user input or research
- content: pitch-deck stub created but no format/audience context — needs brand info

### Pending Validation
- All inferred entities awaiting first research cycle for verification
```

## Cost Impact Model

| Phase | Current Cost | With Cascade | Savings |
|-------|-------------|-------------|---------|
| Identity inference | ~$0.01 | ~$0.02 (+domain inference) | -$0.01 |
| Task creation | ~$0 | ~$0.01 (stub generation) | -$0.01 |
| Bootstrap research | ~$1.00-2.60 | ~$0.30-0.40 | **$0.60-2.20** |
| Steady-state run | ~$0.30-0.57 | ~$0.20-0.30 | $0.10-0.27 |

The cascade invests ~$0.03 upstream to save ~$1.00+ downstream.

## Implementation Sequence

1. **Domain inference in UpdateSharedContext** — when identity/brand updates, Haiku infers what domains should contain. Store as `_inferences.md` in workspace.
2. **Pre-scaffold in CreateTask** — read `_inferences.md`, create entity stubs for relevant domains.
3. **Directed bootstrap prompt** — awareness.md includes "validate inferred entities" directive.
4. **TP surfaces inferences** — working memory includes inference state so TP can say "I've inferred X, confirm?"

Each step is independently valuable. Step 1 alone gives the TP better awareness. Step 1+2 eliminates cold-start waste. Step 3+4 close the loop.

## Open Questions

- Should inference happen eagerly (on every identity update) or lazily (at task creation time)?
- How to handle inference drift — user pivots, identity changes, but stale inferences remain?
- Should inferred entities be visible in the workspace explorer before research validates them?

## Key Files

| File | Current Role | Proposed Addition |
|------|-------------|-------------------|
| `api/services/context_inference.py` | Identity/brand inference | + domain entity inference |
| `api/services/primitives/update_context.py` | UpdateContext handler | + cascade trigger on identity write |
| `api/services/primitives/task.py` | CreateTask handler | + read inferences, create stubs |
| `api/services/working_memory.py` | Context readiness signal | + domain inference state |
| `api/agents/tp_prompts/onboarding.py` | Context awareness prompt | + inference surfacing guidance |
