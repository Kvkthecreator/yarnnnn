# Onboarding & TP Singular Awareness — Design Brief

**Status:** Next priority  
**Date:** 2026-04-01  
**Depends on:** Workspace init (shipped), TP prompts (updated), context_readiness (working)

---

## The Principle

TP should have **singular awareness** of the workspace state and nudge ONE thing at a time. Not a list of gaps. Not multiple suggestions. One clear next step.

The progression:
```
1. IDENTITY (who are you?) → UpdateContext(target=identity)
2. BRAND (how should outputs look?) → UpdateContext(target=brand)  
3. TASKS (what work to do?) → CreateTask(type_key=...)
```

Each step gates the next. TP doesn't mention tasks until identity is meaningful. Doesn't mention brand until identity is set.

This mirrors the "viewing" concept: TP sees workspace state → knows exactly where the user is in the progression → suggests the ONE next thing.

---

## Current State

### What Works
- `context_readiness` in working memory: identity/brand/docs/tasks richness (empty|sparse|rich)
- `onboarding.py` prompt: priority order, one-suggestion-at-a-time guidance
- `UpdateContext` primitive: unified identity/brand/memory/agent/task updates
- Inference merge: identity/brand content enriched via LLM, not overwritten

### What's Missing
1. **No formal gating**: onboarding.py says "meaningful identity before tasks" but no enforcement
2. **No session tracking**: can't tell "already suggested identity this session"
3. **No readiness feedback from UpdateContext**: TP doesn't know if identity went from empty→sparse or sparse→rich after an update
4. **No singular next-step logic**: TP sees ALL gaps simultaneously, must use judgment to pick one
5. **No "viewing" integration**: the navigation context (what file user is browsing) doesn't influence onboarding nudges

---

## Proposed Design

### Step 1: Harden the onboarding prompt

Make the rules explicit and mechanical:

```
## Onboarding State Machine

READ context_readiness from working memory.

IF identity == "empty":
  → Your ONE job: learn about the user. Ask about their role, company, domain.
  → DO NOT mention brand, tasks, or anything else.
  → When they share info, call UpdateContext(target="identity").

ELSE IF identity == "sparse":  
  → Identity exists but thin. Ask to enrich: what industry? what's your focus area?
  → DO NOT suggest tasks yet.

ELSE IF brand == "empty":
  → Identity is set. Now suggest brand: "Want to set up how your outputs look? 
    Share your website or describe your communication style."
  → ONE suggestion. Don't list other gaps.

ELSE IF tasks == 0:
  → Identity + brand set. Now suggest tasks from the catalog.
  → Start with context tasks: "What do you want me to track?"
  → Use the task type catalog in working memory.

ELSE:
  → Workspace is set up. Normal operation.
```

### Step 2: UpdateContext returns readiness

After writing identity/brand, return the new readiness classification:

```python
# In handle_update_context():
result = {
    "success": True,
    "target": target,
    "readiness": _classify_richness(new_content),  # "sparse" or "rich"
    "message": f"Updated {target}. Readiness: {readiness}.",
}
```

TP sees this → knows whether to suggest enriching more or move to next gap.

### Step 3: Empty state action cards

Frontend suggestion chips map to the current onboarding state:

| State | Chip text | TP action |
|---|---|---|
| identity empty | "Tell me about yourself" | UpdateContext(target=identity) |
| identity sparse | "Tell me more about your work" | UpdateContext(target=identity) |
| brand empty | "Set up your output style" | UpdateContext(target=brand) |
| tasks == 0 | "What should I track for you?" | CreateTask conversation |
| operational | "What's new?" / "How are my tasks doing?" | Normal conversation |

Chips change based on `context_readiness` — always showing the ONE next step.

### Step 4: Viewing-aware nudges

When user is browsing the Files tab:
- Viewing empty context/competitors/ → "Want to start tracking competitors?"
- Viewing IDENTITY.md (sparse) → "This could use more detail. Tell me about your industry."
- Viewing empty tasks/ → "Ready to create your first task?"

The navigation context enables contextual, non-generic nudges.

---

## Implementation Priority

1. **Harden onboarding prompt** (TP prompt change — medium effort, high value)
2. **UpdateContext readiness feedback** (small backend change)
3. **Frontend chips from context_readiness** (frontend change)
4. **Viewing-aware nudges** (requires navigation context integration with onboarding logic)

---

## References
- `api/agents/tp_prompts/onboarding.py` — current onboarding guidance
- `api/services/working_memory.py` — context_readiness signals
- `api/services/primitives/update_context.py` — UpdateContext handler
- `docs/design/WORKSPACE-EXPLORER-UI.md` — navigation context design
