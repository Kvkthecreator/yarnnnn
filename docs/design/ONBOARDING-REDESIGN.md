# Onboarding Redesign — Issue List & Next Session Handoff

> **Status**: Open — needs implementation in next session
> **Date**: 2026-03-24
> **Context**: This session built ADR-130/133/134/135/136 infrastructure. Onboarding is the remaining broken surface.
> **Evidence**: `/projects/yarnnn-ai-startup` — template-interpolated charter files, no inference, generic PM handoff.

---

## What's Broken (Observed)

### 1. Inference Never Fires (or Fires Empty)

`enrich_scaffold_params()` calls `infer_project_spec()` but the result doesn't reach `scaffold_project()`. Evidence: PROJECT.md contains "yarnnn - AI startup update" (template default) not an inferred objective.

**Root cause**: Either:
- Haiku call failed silently (API key limits, model error)
- `document_ids` empty (upload → scaffold timing)
- Overrides dict not threaded correctly through the call chain
- `infer_topic_type()` fallback always wins over LLM inference

**Fix**: Add logging to `enrich_scaffold_params()`, verify the Haiku call is reached, ensure overrides propagate.

### 2. Onboarding Asks the Wrong Question First

Step 1: "How is your work structured? Single or multi?" — this is a structural question about the user's workflow BEFORE the system understands what the user does.

**The right flow**: User shares context first (files + description) → system infers structure → system presents: "Here's what I understand about your work. I'll set up these projects."

The "single vs multi" step should be **removed** or moved to after inference.

### 3. Document Upload Disconnected from Inference

Files upload via `api.documents.upload()` (async). By the time onboarding submits, the document processing may not be complete. Even if complete, `enrich_scaffold_params()` reads `filesystem_documents.content` which may be empty (content stored separately from chunks).

**Fix**: Either:
- Wait for document processing before enabling submit
- Read document content directly from the uploaded file in the onboarding flow (not from DB)
- Or use a synchronous extraction path for onboarding docs

### 4. Single Scope → Single Project (Too Rigid)

If user uploads a pitch deck that mentions competitive landscape, product roadmap, and investor relations — that's 3 potential projects, not 1. The current flow maps 1 scope entry → 1 project.

**The right flow**: Document inference should extract MULTIPLE work scopes from uploaded content, present them for confirmation, then scaffold multiple projects.

### 5. PM Handoff is Template Text

PM's first chat message: "Project created: yarnnn - AI startup. Objective: yarnnn - AI startup update."

This is useless — it's just template interpolation, not intelligent handoff. The PM should receive the actual user context (what they described, what files they uploaded, what the inference found).

### 6. PM First Pulse Has No Actionable Context

PM reads PROJECT.md which says "Stay on top of yarnnn - AI startup activity" with generic success criteria. PM can't make intelligent coordination decisions because the charter files are empty templates.

**This is downstream of problems 1-5** — if inference works correctly, PM gets rich charter files and can coordinate intelligently.

---

## Proposed Redesign

### Step 1: Share Context (Primary)

```
"Share what you're working on"

[Drop zone: files, docs, pitch decks]
[Text area: "or describe your work"]
[Both are optional but at least one required]
```

No "single vs multi" question. Just context gathering.

### Step 2: Inference (Single LLM Call)

System reads ALL uploaded docs + text description. Single Sonnet call (not Haiku — this is worth the quality):

```
Input: 3 uploaded PDFs + "I run an AI startup called yarnnn"
Output: {
  "work_scopes": [
    {
      "name": "Competitive Intelligence",
      "objective": "Weekly AI competitor tracking",
      "success_criteria": ["Cover top 5 competitors", ...],
      "team": [{"role": "scout"}],
      "cadence": "weekly"
    },
    {
      "name": "Product Development",
      "objective": "Track internal progress and blockers",
      "team": [{"role": "briefer"}],
      "cadence": "daily"
    }
  ],
  "brand": {
    "name": "yarnnn",
    "tone": "Technical, concise"
  },
  "user_context": "Solo founder building AI agent platform"
}
```

### Step 3: Confirm (User Approves)

```
"Here's what I'll set up:"

☑ Competitive Intelligence (weekly, Scout agent)
☑ Product Development (daily, Briefer agent)

[Edit] [Add another] [Get Started →]
```

User can edit, add, remove before confirming. This is a confirmation step, not a configuration step.

### Step 4: Scaffold

`scaffold_project()` per confirmed scope with rich overrides from inference.

### Step 5: Brand (Optional, Inline)

Brand basics captured from inference or user input. Saved to `/workspace/BRAND.md`.

---

## Implementation Sequence (Next Session)

1. **Remove Step 1** (single/multi question) — go straight to context gathering
2. **Build inference endpoint** — single Sonnet call that reads docs + text → multiple scopes
3. **Build confirmation UI** — show inferred scopes, let user edit/confirm
4. **Wire to scaffold_project()** with full overrides (objective, criteria, output spec, team)
5. **Verify PM receives rich context** — charter files populated, handoff message meaningful

---

## What's Working (Don't Break)

- Charter file structure (ADR-136): PROJECT.md + TEAM.md + PROCESS.md ✓
- `scaffold_project()` accepts overrides (objective, team, criteria, output spec) ✓
- PM handoff message via `pm_announce()` ✓
- PM prompt reads charter files ✓
- Cadence enforcement ✓
- File upload infrastructure (`useFileAttachments`, `api.documents.upload()`) ✓
- PM coordination pipeline (Tier 3 + chat messages) ✓
- Compose engine + delivery ✓

The infrastructure is solid. The onboarding flow that FEEDS it is broken.

---

## Files to Touch

| File | Change |
|------|--------|
| `web/app/onboarding/page.tsx` | Remove step 1, redesign step 2 as context gathering + confirmation |
| `api/services/project_inference.py` | Replace Haiku with Sonnet, multi-scope output, read doc content directly |
| `api/routes/memory.py` | Update onboarding endpoint for new flow |
| `web/lib/api/client.ts` | Update API client for new endpoint shape |

---

## Hooks Discipline Reminder (for next session)

1. Singular implementation — delete current 3-step onboarding, replace with 2-step (share → confirm)
2. Docs alongside code — update ADR-132, this doc
3. Check ADRs — ADR-132 (onboarding), ADR-136 (charter files)
4. Prompt changes — inference prompt is behavioral artifact, needs CHANGELOG entry
5. Git — commit per logical unit
