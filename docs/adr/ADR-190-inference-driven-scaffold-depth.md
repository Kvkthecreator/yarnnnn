# ADR-190: Inference-Driven Scaffold Depth

> **Status**: Proposed
> **Date**: 2026-04-17
> **Authors**: KVK, Claude
> **Extends**: ADR-144 (Inference-First Shared Context), ADR-149 (Task Lifecycle), ADR-151 (Shared Context Domains), ADR-178 (Task Creation Routes), ADR-189 (Three-Layer Cognition)
> **Sunsets for onboarding flow**: `OnboardingModal` auto-trigger, standalone `ContextSetup` and `TaskSetup` modal surfaces

---

## Context

### The observation

ADR-189 ratified the authored-team model: zero Agents at signup; the user builds the team through conversation with YARNNN. The first implementation exposed a tension.

Prior to ADR-189, two modal surfaces (`OnboardingModal` wrapping `ContextSetup`, `TaskSetupModal` wrapping `TaskSetup`) collected *rich inputs* — file drops, URL pastes, multi-line notes — and composed them into messages that seeded upstream inference (ADR-144). The inference produced populated `IDENTITY.md`, `BRAND.md`, and named-entity extraction, which in turn shaped the first Agent's domain and the first task's DELIVERABLE.md.

ADR-189 Phase 1 left these modals in place but sunset their marker-gated auto-trigger. The remaining question was whether to preserve them as deliberately-invoked surfaces or dissolve them entirely.

The audit finding that forced the decision: **if we dissolve them and leave only a text composer, we lose the rich-input signal, which means the scaffold that follows the user's first act is shallower, which means the first Agent feels generic, which breaks the trust arc the authored-team thesis depends on.**

### The principle

**The scaffold that follows a user's first act is as deep as the inference signal from that act allows.**

- Text-only input → shallow scaffold: generic domain folders, generic Agent persona, follow-up questions to fill the gaps.
- Rich input (files + URLs + text combined in one submission) → deep scaffold: entity-populated domain folders, Agent shaped to the user's specific language, task with a realistic DELIVERABLE.md and seeded `_tracker.md`.

The system's job is to encourage the richest input possible at the first moment. Not to replace the rich-input affordances with a thinner surface; to build them into the surface the user is already on (chat).

Corollary: **specificity is the trust mechanism.** YARNNN's response to a rich input must *name the specific entities, files, and schedule it scaffolded*. Generic confirmations ("I've set up competitive tracking") break trust. Specific confirmations ("I saw Anthropic, OpenAI, and Google in your deck — tracking all three, brief lands Monday 9am") build it.

---

## Decision

### 1. Rich inputs live inside the chat composer

The chat composer becomes the single input surface for authorship. It supports:

- **File drop** (same size limits as the prior ContextSetup: 20 MB docs, 5 MB images; PDF/MD/DOCX/TXT for text inference)
- **URL paste** with validation and accumulation (one or many)
- **Text** (always)

A single chat submission can carry any combination. The composer visually shows what's attached before send.

**ContextSetup and TaskSetup modals are sunset as components of the onboarding/first-act flow.** Their affordances migrate into the composer. Whether the underlying React components persist for invocation in *other* flows (commands, non-onboarding workspace surfaces) is deferred — see "Deferred" below.

### 2. One first-act pipeline: Inference → Scaffold Pass → Visible Preview

When a user submits a rich input, YARNNN runs a single deep pipeline:

```
USER INPUT (files + URLs + text)
        │
        ▼
UPSTREAM INFERENCE (single LLM call; ADR-144 + entity extraction)
    emits: {identity: ..., brand: ..., entities: [{domain, name, ...}, ...], work_intent: ...}
        │
        ▼
SCAFFOLD PASS (primitive batch — one confirmation, not many)
    • UpdateContext(target=identity) — populate IDENTITY.md
    • UpdateContext(target=brand)    — populate BRAND.md
    • ManageDomains(create)          — context domain(s) from entity groups
    • WriteFile                      — entity subfolder skeletons + _tracker.md seed
    • ManageAgent(create)            — first Agent (origin=user_configured)
    • ManageTask(create)             — first task + DELIVERABLE.md
        │
        ▼
VISIBLE PREVIEW (chat stream artifact)
    Named entities, named files, named schedule. Confirm-or-adjust affordance.
```

The pipeline runs **atomically** — all scaffold primitives execute in one turn, then the preview renders. This is the Lovable pattern ("build first, refine after"). User confirmation applies to the *result*, not to each step.

### 3. Entity extraction piggybacks the existing inference call

`infer_shared_context()` already runs one Sonnet call to produce identity + brand output. It gains a third output field: `entities`. No second LLM call; the existing prompt is extended to emit structured entity data.

Output contract:

```python
{
    "identity": {...},        # existing (ADR-144)
    "brand": {...},           # existing (ADR-144)
    "entities": [             # NEW (ADR-190)
        {
            "domain": "competitors",        # canonical domain key from registry, or TP-composed
            "name": "Anthropic",            # user's own language
            "slug": "anthropic",            # filesystem-safe
            "hints": ["ai-safety", "claude"],  # optional tags for _tracker.md seed
        },
        ...
    ],
    "work_intent": {          # NEW (ADR-190)
        "kind": "recurring" | "goal" | "reactive",
        "deliverable_type": "brief" | "digest" | "monitor" | ...,  # nullable
        "cadence": "daily" | "weekly" | "monthly" | "on-demand",   # nullable
    },
}
```

The inference prompt gains explicit guidance on entity extraction (which domains are user-sovereign vs. platform-bot-owned per ADR-158) and on work-intent classification.

### 4. Scaffold pass is orchestrated, not inline

`_handle_shared_context()` in `api/services/primitives/shared_context.py` today writes identity/brand. It extends to orchestrate the full scaffold pass:

1. Write IDENTITY.md and BRAND.md (existing).
2. For each entity group in `entities`, ensure the context domain exists (idempotent via `ManageDomains(action="create")`) and write entity subfolders with templated skeletons.
3. If `work_intent` is present, call `ManageAgent(create)` with a title composed from the dominant entity group + work intent, then `ManageTask(create)` with a DELIVERABLE.md shaped by the deliverable_type.
4. Return a structured scaffold report for the chat stream to render.

The scaffold report flows back through YARNNN's response as a typed artifact (not prose), rendered in the chat UI as a tree preview + confirm/adjust buttons.

### 5. First-turn empty-state surfaces rich inputs as defaults

`ChatSurface.tsx` empty-state renders:

- **One-line welcome** from YARNNN (hardcoded, deterministic, zero LLM cost).
- **One-line subline** that names the rich-input path (doc, URL, description).
- **Four chips** below the composer:
  - Two rich-input prompts (upload doc / paste URL) that prepare the composer to receive that affordance.
  - Two intent-text prompts (track recurring / build recurring report) that seed composer text.
- **Placeholder text** hints at rich input: *"Type, drop a file, or paste a link..."*

No modal. No wizard. The chips are the zero-typing affordance. The composer is the always-there affordance.

---

## What changes

| File / surface | Change |
|----------------|--------|
| `web/components/chat-surface/ChatSurface.tsx` | Empty state: welcome + subline + 4 chips + rich placeholder. Stale `title="Thinking Partner"` → `"YARNNN"`. Remove `OnboardingModal` auto-trigger (already deferred to marker-gated but marker goes away under this ADR). |
| `web/components/chat-surface/ChatPanel.tsx` + composer | File-drop affordance, URL-paste validation + accumulation. (Implementation phase.) |
| `web/components/onboarding/OnboardingModal.tsx`, `web/components/onboarding/ContextSetup.tsx` | Sunset from first-act flow. Components may persist as library for deferred use elsewhere — not removed from codebase in this ADR. |
| `web/components/work/TaskSetupModal.tsx`, `web/components/work/TaskSetup.tsx` | Same — sunset from first-act flow, components preserved pending deferred decision. |
| `api/services/context_inference.py` | `infer_shared_context()` prompt extended. Output schema gains `entities` and `work_intent`. Eval harness (ADR-162 sub-phase C) fixtures updated. |
| `api/services/primitives/shared_context.py` (`_handle_shared_context`) | Orchestrates scaffold pass: domains + entity subfolders + Agent + task. Returns structured scaffold report. |
| `api/services/primitives/manage_domains.py` | Accepts entity-seeded domain creation (idempotent). May already support; verify. |
| `docs/adr/ADR-190-inference-driven-scaffold-depth.md` | This document. |

---

## What doesn't change

- **Primitive atomicity (ADR-168).** `ManageAgent`, `ManageTask`, `ManageDomains`, `UpdateContext`, `WriteFile` remain atomic. The scaffold pass calls them in sequence within one orchestrator; no compound primitive is introduced.
- **DB schema.** No migrations.
- **Execution pipeline (ADR-141).** Task pipeline reads TASK.md as before; unaffected.
- **Directory registry (ADR-152, ADR-188).** Template library of domain archetypes. Entity extraction hydrates the structure the registry describes; no structural change.
- **DB slug `thinking_partner`** and other glossary exceptions — preserved.
- **Infrastructure scaffolding at signup.** YARNNN, Specialists, and Platform Bots remain scaffolded (per ADR-189 Phase 2 pragmatic implementation) because pipeline dispatch depends on them.

---

## Consequences

### Positive

1. **Trust anchors in specificity.** YARNNN's response to a rich input names the user's own entities, files, and schedule. This is the authorship moment the authored-team thesis depends on.
2. **Singular implementation.** One input surface (chat composer with rich affordances). One pipeline (inference → scaffold pass). One artifact type (scaffold preview). Dual paths (modal + chat) collapse to one.
3. **Scaffold depth scales with input richness.** Users who upload docs get full scaffolds. Users who type sparse text get minimal scaffolds plus targeted follow-up questions. The system matches its output to the signal it has.
4. **Empty-state chips do behavioral work.** Chips nudge users toward high-density inputs (upload a doc, paste a URL) rather than asking open-ended questions that produce thin text.
5. **First Agent is a visible authorship moment.** The scaffold preview renders as an artifact in the chat stream — named entities, named files, named schedule — and the user confirms/adjusts. The "team grows" feeling is tangible.

### Costs

1. **Inference reliability matters more.** If entity extraction fails or hallucinates, the scaffold pass creates junk entities. Mitigation: ADR-162 sub-phase A gap detection runs post-inference and flags low-confidence extractions; scaffold pass treats those as text-only input (shallow scaffold) rather than creating noise.
2. **Atomic scaffold harder to undo.** Executing everything up-front and asking for post-hoc confirmation means mistakes require rollback. Mitigation: confirm/adjust UI in scaffold preview includes a single "Start over" action that archives the just-created Agent + task + any created entity files. Not a destructive undo — archival only.
3. **Chat composer complexity.** File drop + URL paste + multi-artifact composition is more to build than a text input. Scoped to one commit with clear component boundaries.

### Deferred

- **Modal reuse in non-onboarding flows.** Whether `ContextSetup` / `TaskSetup` components are re-invoked elsewhere (slash commands, workspace surface actions, explicit "add more context" paths) is a later decision. Components remain in the codebase, detached from auto-trigger logic.
- **Multi-user workspace scaffolding.** When workspaces become shared, the "first act" model needs to handle multi-user authorship attribution. Not addressed here.

---

## Implementation sequence (six commits)

| Commit | Scope |
|--------|-------|
| 1 (this ADR + Brief 1) | ADR-190 document + ChatSurface empty state copy/chips + stale title fix. Zero pipeline change. |
| 2 | Chat composer rich inputs: file drop + URL accumulation + multi-artifact submit. OnboardingModal and TaskSetupModal auto-trigger removed. Modals detached (components preserved). |
| 3 | Inference pipeline extension: `infer_shared_context()` output schema + prompt + eval fixtures. |
| 4 | Scaffold pass orchestration: `_handle_shared_context()` extended. Structured scaffold report artifact type added to stream events. Frontend artifact card renders tree preview. |
| 5 | Workspace init cleanup: `DEFAULT_BRAND_MD` → 2-line skeleton, `DEFAULT_AWARENESS_MD` → 2-line skeleton (audit says it's already minimal; verify). `WORKSPACE.md` manifest deleted (`_build_workspace_manifest` + `update_workspace_manifest` removed, prompt references stripped). |
| 6 | Empty-state consistency across `/work` (fix stale "TP" reference in WorkListSurface), `/agents` (already ADR-189 compliant), `/context` (complete plus-menu handlers, match shared CTA pattern). |

Each commit stands on its own (green build, tests pass). Commits 3 and 4 compose; 2 and 5 are independent.

---

## Open questions

1. **Scaffold preview artifact format.** Tree render or flat list? How does "confirm vs. adjust" surface — buttons, chat follow-up, both? Resolve during commit 4.
2. **Inference prompt length budget.** Extending the prompt with entity extraction guidance adds tokens. ADR-162 eval harness will measure regression risk. Decide on caching strategy during commit 3.
3. **Chip interactions.** Rich-input chips (upload, URL) either (a) focus the composer with hint text, (b) actually trigger file picker / URL field, or (c) seed a prompt text. Likely (b) for upload, (a) or (b) for URL. Resolve during commit 2.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-17 | v1 — Initial proposal. Extends ADR-144/149/151/178/189. Dissolves ContextSetup/TaskSetup modals from the onboarding flow; rich inputs migrate into the chat composer. Inference extended with entity extraction + work-intent. Scaffold pass orchestrates identity + brand + domains + entities + Agent + task atomically. Six-commit implementation plan. |
