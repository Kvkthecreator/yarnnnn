# ADR-155: Workspace-Wide Inference & Onboarding Experience

**Status:** Proposed
**Date:** 2026-04-02
**Supersedes:** ADR-113 (Auto Source Selection — onboarding flow), ADR-132 (Work-First Onboarding — never implemented)
**Extends:** ADR-144 (Inference-First Shared Context), ADR-151 (Shared Context Domains), ADR-152 (Unified Directory Registry)
**Analysis:** `docs/analysis/inference-cascade-architecture-2026-04-02.md`

## Context

Bootstrap task execution is disproportionately expensive ($1-3 per first run) because agents start from empty context domains and discover entities through broad WebSearch. But much of what they "discover" is conventional wisdom the system could infer from workspace identity context.

Separately, the current onboarding flow (ADR-144) is conversational — TP nudges the user through identity → brand → tasks one at a time via suggestion chips. This works but is invisible: the user doesn't see their workspace taking shape.

## Decision

**Workspace-wide inference**: When the user provides identity context, the system infers and scaffolds ALL context domains simultaneously — competitors, market, relationships, projects, content. Not one domain at a time. The entire workspace materializes from a single rich identity input.

**Context page as onboarding surface**: After signup, the user lands on `/context` with the TP inference component front and center. Empty states on `/tasks` and activity surfaces during this phase. The user provides identity (text, URLs, docs) and watches their workspace build in real time — folders appearing, entity stubs populating, domain structure emerging.

**Workspace maturity as routing signal**: The TP's `context_readiness` signal (identity: empty|sparse|rich) determines which surface is the "home" and what empty states show. Not a binary `is_onboarding` flag — graduated maturity.

## Architecture

### Three-Phase Workspace Maturity

| Phase | Identity | Domains | Tasks | Home Route | TP Posture |
|-------|----------|---------|-------|------------|------------|
| **Setup** | empty/sparse | empty | 0 | `/context` | Inference-first: "Tell me about your work" |
| **Scaffolded** | rich | seeded (inferred stubs) | 0 | `/context` | Task suggestion: "Ready to set up tracking?" |
| **Active** | rich | populated (researched) | 1+ | `/tasks` | Normal operation |

### Inference Cascade

```
User provides identity context (text, URL, doc)
    ↓
Level 1: UpdateContext(target="identity") → IDENTITY.md (existing)
    ↓
Level 2: Workspace inference (NEW) — Haiku reads IDENTITY.md + BRAND.md
    → Infers ALL domains: which entities should exist, what's known
    → Writes scaffolding plan to workspace
    ↓
Level 3: Domain scaffolding (NEW) — creates entity stubs across all domains
    → /workspace/context/competitors/cursor/profile.md (inferred stub)
    → /workspace/context/market/ai-coding-tools/analysis.md (inferred stub)
    → /workspace/context/relationships/investors/tracker.md (empty, staged)
    → _tracker.md and _landscape.md per domain
    ↓
Level 4: Task creation (existing) — tasks start warm, not cold
    → Bootstrap research validates/deepens inferred entities
    → 4-6 targeted searches instead of 16 broad ones
```

### Inference Strictness (Derivative Effect Principle)

The higher upstream the inference, the bigger the derivative effects — both positive and negative. Bad inference at L2 cascades into wrong entities, wasted research, misleading outputs.

**Safeguard 1: Source tagging**
Every inferred entity carries a source tag:
- `source: inferred` — derived from identity context, not yet researched
- `source: user_stated` — user explicitly mentioned this entity
- `source: researched` — agent verified via WebSearch

**Safeguard 2: Explicit gap markers**
Entity stubs explicitly state what's known vs unknown:
```markdown
# Cursor
## Overview
AI-powered code editor by Anysphere. [Inferred from workspace identity]

## Pricing
[Needs research]

## Recent Developments
[Needs research]
```

**Safeguard 3: TP surfaces inferences**
After scaffolding, TP summarizes: "Based on your identity, I've set up 5 domains with 12 entities. Here's what I inferred — want to adjust before research begins?"

**Safeguard 4: Research validates**
Bootstrap task directive shifts from "discover entities" to "validate inferred entities, fill gaps, flag any I missed." Research confirms or corrects, never blindly trusts inference.

### Continuous Re-Assessment

Inference isn't one-shot. Every significant context event triggers re-assessment:

| Event | Re-assessment |
|-------|---------------|
| Platform connection (Slack, Notion) | Scan channel names/topics → scaffold new entities |
| Document upload | Extract entities mentioned → slot into domains |
| TP conversation | User mentions new competitor/initiative → scaffold |
| Task completion | Domain health changes → assess gaps |
| Identity update | Full workspace re-inference |

### UX: The Magic Moment

**Setup phase layout** (`/context` as landing):
```
┌─────────────────────────────────────────────────────┐
│  yarnnn                                             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │                                             │    │
│  │  "Tell me about yourself and your work.     │    │
│  │   I'll build your workspace from there."    │    │
│  │                                             │    │
│  │  [Text area / URL input / file drop]        │    │
│  │                                             │    │
│  │  ────────────────────────────────────────    │    │
│  │  Or share:  [LinkedIn]  [Website]  [Doc]    │    │
│  │                                             │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  (TP chat — wide, centered, inference-first)        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**After identity submitted** (live scaffolding):
```
┌─────────────────────────────────────────────────────┐
│  yarnnn                          Building workspace │
├──────────────────┬──────────────────────────────────┤
│  Workspace       │  TP Chat                         │
│                  │                                  │
│  ▸ Identity ✓    │  "Great — I can see you're in    │
│  ▸ Brand         │  dev tools, competing with       │
│  ▾ Domains       │  Cursor. Setting up your         │
│    ✓ Competitors │  workspace now..."               │
│      cursor      │                                  │
│      copilot     │  ◉ Setting up competitors...     │
│      codeium     │  ◉ Scaffolding market domains... │
│    ◉ Market...   │  ○ Relationships                 │
│    ○ Relations   │  ○ Projects                      │
│    ○ Projects    │                                  │
│                  │  "Found 4 competitors and 2      │
│                  │  market segments. Want to adjust  │
│                  │  before I start research?"        │
│                  │                                  │
└──────────────────┴──────────────────────────────────┘
```

The left panel shows workspace structure materializing in real time. The TP narrates what it's doing. Progressive build — folders appear one by one as inference runs.

**Empty states during setup phase:**

| Surface | Empty State |
|---------|-------------|
| `/tasks` | "Your workspace is being set up. Head to Context to get started." (link) |
| Activity | "No activity yet. Set up your workspace to begin." |
| Task detail | N/A (no tasks exist) |

### AWARENESS.md — Inference State

AWARENESS.md at workspace level carries inference state alongside TP's shift notes:

```markdown
## Workspace Inference State
Last inference: 2026-04-02 from identity update

### Scaffolded Domains
- competitors: 4 entities (cursor, copilot, codeium, tabnine) — source: inferred
- market: 2 segments (ai-coding-tools, developer-productivity) — source: inferred
- relationships: investor category created — source: inferred

### Pending Validation
- All inferred entities awaiting first research cycle
- No specific investor names — needs user input or research

## TP Notes
User is a founder, raising Series A. Focus on competitive positioning
and fundraising materials.
```

## Cost Impact

| Scenario | Before | After | Savings |
|----------|--------|-------|---------|
| Identity inference | $0.01 | $0.02 (+domain inference) | -$0.01 |
| Domain scaffolding | $0 | $0.01 (stub creation) | -$0.01 |
| Bootstrap research (per task) | $1.00-2.60 | $0.30-0.40 | **60-85%** |
| Steady-state run | $0.30-0.57 | $0.20-0.30 | **30-50%** |

Invest ~$0.03 upstream to save ~$1.00+ downstream per task.

## Implementation Phases

### Phase 1: TP-Driven Domain Scaffolding (Implemented, revised 2026-04-02)

**Original**: `workspace_inference.py` — shadow Haiku inference call triggered as backend side-effect after UpdateContext. Eliminated during audit — violated single-intelligence-layer principle.

**Revised**: `ManageDomains` primitive — TP decides WHAT entities to scaffold, backend handles HOW (templates, files, trackers). One tool call, no shadow LLM.

Flow: TP processes identity → reasons about entities → calls `ManageDomains({entities: [...]})` → backend creates stubs with `<!-- source: inferred -->` + `[Needs research]` gaps → TP narrates result.

Key files:
- `api/services/primitives/scaffold.py` — ManageDomains handler
- `api/services/directory_registry.py` — `get_entity_stub_content()` template enrichment
- `api/agents/tp_prompts/onboarding.py` — scaffolding guidance for TP

Deleted: `api/services/workspace_inference.py` (shadow inference), backend cascade trigger in `update_context.py`.

### Phase 2: Maturity-Aware Surfaces (Implemented)
- `/workspace/nav` returns `readiness` object with phase (setup|scaffolded|active)
- `/context` during setup phase: ContextSetup component as hero content (centered, no skip options)
- `/tasks` during setup: empty state with "Set up workspace" link to `/context`
- No auto-redirects — user navigates freely, maturity informs in-page UI
- Post-purge: one-time redirect to `/context` (intentional)

### Phase 3: TP Notification Channel + FAB Ambient Awareness (Implemented)
All system side effects surface through the TP chat — inline notification cards in the stream when chat is open, FAB badge when closed.

Notification-worthy tools: UpdateContext, CreateTask, ManageDomains, ManageTask (evaluate/complete).

Key files:
- `web/contexts/TPContext.tsx` — detection + queue + flush
- `web/components/tp/NotificationCard.tsx` — inline card component
- `web/components/desk/ChatDrawer.tsx` — FAB badge overlay

Design doc: `docs/design/TP-NOTIFICATION-CHANNEL.md`

### Phase 4: Deferred — Existing Flow Sufficient

No new triggers needed. The TP + UpdateContext + ManageDomains path covers all context evolution:

| Event | How it's handled |
|-------|-----------------|
| User mentions new competitor | TP calls UpdateContext(identity) + ManageDomains |
| Document upload | TP extracts context → UpdateContext + ManageDomains |
| Platform connection | Landscape metadata only — not entity-level signal |
| Re-scaffolding after identity change | TP calls ManageDomains again (idempotent) |

### Architectural Audit (2026-04-02)

Audited all separate LLM calls for "shadow TP" pattern:

| Service | Model | Verdict |
|---------|-------|---------|
| ~~workspace_inference.py~~ | ~~Haiku~~ | **Eliminated** — was shadow TP making domain decisions |
| context_inference.py | Sonnet | **Legitimate** — TP's explicit tool for identity/brand merge |
| composer.py | Haiku | **Legitimate** — periodic autonomous assessment (ADR-111), separate execution mode |
| task_deliverable_inference.py | Sonnet | **Legitimate** — mechanical feedback→spec transformation |
| memory.py | Haiku | **Legitimate** — nightly cron fact extraction |
| session_continuity.py | Haiku | **Legitimate** — mechanical session summarization |
| manage_task.py (evaluate) | Haiku | **Legitimate** — TP-initiated via primitive |

**What "re-inference" actually means**: When the user updates identity (directly or via TP), `run_workspace_inference()` fires again. It's already idempotent:
- Existing researched entities (`<!-- source: researched -->`) are NOT overwritten
- Existing inferred stubs ARE replaced with fresh inference (may discover new entities)
- New entities from updated identity get added as new stubs
- Tracker rebuilds from filesystem scan (includes both old and new entities)

**What's worth doing later** (not now):
- **Post-research state upgrade**: When a bootstrap task validates inferred entities, the source tag should upgrade from `<!-- source: inferred -->` to `<!-- source: researched -->`. This lets re-inference know which entities are confirmed. Currently the agent would need to do this via WriteWorkspace — could be automated in the task pipeline post-run.
- **Inference drift detection**: If identity changes significantly (user pivots), stale inferred entities that are no longer relevant should be flagged. Not deletd — flagged for user review.

These are refinements to Phase 1 quality, not new trigger infrastructure.

## Impacted Files

| File | Impact |
|------|--------|
| `api/services/primitives/update_context.py` | Trigger inference cascade on identity write |
| `api/services/workspace_inference.py` | NEW — workspace-wide inference engine |
| `api/services/working_memory.py` | Extended context_readiness (inference_state) |
| `api/agents/tp_prompts/onboarding.py` | Inference surfacing, maturity-aware guidance |
| `web/lib/routes.ts` | Maturity-based home route |
| `web/app/(authenticated)/context/page.tsx` | Setup phase layout, live scaffolding UI |
| `web/app/(authenticated)/tasks/page.tsx` | Empty state during setup phase |
| `docs/design/ONBOARDING-TP-AWARENESS.md` | Superseded by inference-first flow |
| `docs/design/SHARED-CONTEXT-WORKFLOW.md` | Extended with cascade behavior |
| `docs/features/context.md` | Updated for setup phase role |

## Superseded

- **ADR-113** (Auto Source Selection) — onboarding flow. Platform connections no longer drive onboarding; identity inference does.
- **ADR-132** (Work-First Onboarding) — never implemented. Intent is preserved (work structure from user input) but mechanism changes (inference cascade, not onboarding form).
- **ONBOARDING-TP-AWARENESS.md** — chip-based progression. Replaced by inference-first context page.
