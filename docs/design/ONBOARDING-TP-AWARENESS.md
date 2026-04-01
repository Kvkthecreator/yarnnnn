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

Two separate concerns:

### Concern 1: TP Prompt Guidance (NOT mechanical rules)

See `docs/architecture/TP-DESIGN-PRINCIPLES.md` — TP judges, we don't hardcode.

The onboarding prompt (`onboarding.py`) provides:
- **Context**: workspace readiness signals (already in working memory)
- **Priorities**: identity → brand → tasks (already stated)
- **Philosophy**: one thing at a time, don't overwhelm (already stated)

What to tune:
- Strengthen the "one thing" emphasis — TP sometimes suggests multiple gaps
- Add the "viewing" context awareness to onboarding guidance
- Ensure task catalog is current (15 atomic types: 7 tracking + 8 synthesis)
- Trust TP judgment for edge cases (user jumps ahead = let them)

### Concern 2: UX Surfacing (chips + action cards, flowing INTO TP)

Empty state action cards / suggestion chips in the chat panel. These are UI elements that trigger TP conversations — NOT TP's judgment encoded in UI.

| Workspace State | Suggestion Chips | What happens on click |
|---|---|---|
| identity empty | "Tell me about yourself" | Sends message to TP → TP handles |
| identity sparse | "Tell me more about your work" | Sends message to TP → TP handles |
| brand empty | "Set up your output style" | Sends message to TP → TP handles |
| tasks == 0 | "What should I track?" | Sends message to TP → TP handles |
| operational | "What's new?" / context-specific | Sends message to TP → TP handles |

**Chips + action cards + chat = one fluid flow.** (See TP-DESIGN-PRINCIPLES.md)

1. Chip starts the conversation ("Tell me about myself")
2. Action card appears with guided input (URL field, file upload, text)
3. User provides input through the card
4. Input flows to TP as a message → TP processes with full judgment
5. TP responds with confirmation + next suggestion

Action cards are INPUT SURFACES, not forms. They feed into TP, not around it.

**Identity setup action card:**
- Paste URL field (LinkedIn, company website)
- Upload file button (pitch deck, one-pager)
- Text area ("just describe your work")
- All inputs flow to TP → `UpdateContext(target="identity")`

**Task creation action card:**
- Description field ("what do you want to track?")
- Flows to TP → TP infers type_key → `CreateTask(...)`

### Concern 3: Viewing-aware suggestions

When user browses Files tab, the chips can be contextual:
- Viewing empty context/ → "What should I track for you?"
- Viewing IDENTITY.md → "Want to update your identity?"
- Viewing a task → task-specific chips (run, evaluate, etc.)

This is frontend logic reading navigation state + context_readiness → choosing which conversation-starter chips to show. TP still makes all decisions.

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
