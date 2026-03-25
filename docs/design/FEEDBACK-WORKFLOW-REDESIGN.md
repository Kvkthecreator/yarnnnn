# Feedback Workflow Redesign — Agent + Task Model

**Date:** 2026-03-26
**Status:** Proposed
**Depends on:** ADR-138 (Agents as Work Units), ADR-139 (Surface Architecture), ADR-143 (Feedback Substrate)
**Problem:** Email feedback button links to `/agents/{id}` which is now a read-only identity page. No way to give feedback on specific output.

---

## Current State (Broken)

1. Agent runs → output delivered via email
2. Email has "Reply with feedback" button
3. Button links to `/agents/{agent_id}` (legacy: agent detail page had chat)
4. Agent detail page is now identity-only (no chat, no output view)
5. **Result:** feedback button is a dead end

## The Design Question

In the agent+task model, output belongs to **tasks** but learning belongs to **agents**. Feedback bridges both:

| What changes | Where it lives | Who learns |
|-------------|---------------|------------|
| Output quality critique | Task page (output visible) | Agent memory |
| Focus adjustment | TASK.md (task definition) | Task criteria |
| Style/tone preference | Agent memory (preferences.md) | Agent |
| Delivery adjustment | TASK.md (delivery config) | Task |

## Proposed Flow

### Email feedback link

```
"Reply with feedback" → /tasks/{task_slug}?run={run_id}
```

- Opens task page with the specific output displayed
- Task-scoped chat is right there for immediate feedback
- TP has task context injected (knows which output, which agent)

### Feedback routing

When user gives feedback in task-scoped chat:
1. TP reads the feedback intent
2. **If about output quality/content** → writes to agent's `memory/feedback.md` (agent learns for next run)
3. **If about task focus/scope** → updates TASK.md objective/criteria
4. **If about delivery/format** → updates TASK.md delivery config
5. **If about style/tone** → writes to agent's `memory/preferences.md`

### Agent page role in feedback

The agent page (`/agents/{slug}`) becomes the **feedback history viewer**:
- Shows accumulated `memory/feedback.md` (what users have told this agent)
- Shows `memory/preferences.md` (learned style/tone preferences)
- Shows `memory/self_assessment.md` (agent's own quality observations)

But the agent page is NOT where feedback is given. Feedback happens on the **task page**.

---

## Implementation

### 1. Fix email feedback URL

**File:** `api/services/delivery.py` (email template)

Change:
```python
# Old: links to agent page
feedback_url = f"{FRONTEND_URL}/agents/{agent_id}"

# New: links to task page with output context
feedback_url = f"{FRONTEND_URL}/tasks/{task_slug}?run={run_id}"
```

### 2. Task page: handle `?run={run_id}` query param

When task page loads with `?run=` param:
- Load that specific output (not just latest)
- Auto-show the output tab
- Chat placeholder changes to "Give feedback on this output..."

### 3. TP feedback routing (task-scoped)

When user gives feedback in task chat, TP should:
- Recognize feedback intent vs steering intent
- Write to appropriate workspace file (agent memory vs task config)
- Confirm what was updated

This may need a `WriteAgentFeedback` primitive or extension of existing primitives.

### 4. Agent page: feedback history section

Replace or augment the current memory browser with a dedicated "Feedback" section showing:
- Recent feedback entries from `memory/feedback.md`
- Learned preferences from `memory/preferences.md`
- Self-assessment trend

---

## Files to Modify

| File | Change |
|------|--------|
| `api/services/delivery.py` | Email feedback URL: `/agents/{id}` → `/tasks/{slug}?run={id}` |
| `web/app/(authenticated)/tasks/[slug]/page.tsx` | Handle `?run=` query param |
| `api/agents/tp_prompts/task_scope.py` | Add feedback routing guidance to preamble |
| `web/app/(authenticated)/agents/[id]/page.tsx` | Add feedback history section |
| `api/services/task_pipeline.py` | Pass task_slug to delivery function |

---

## Open Questions

1. Should feedback on output auto-trigger a re-run? (Like "this is wrong, redo it" → TriggerTask)
2. Should there be a structured feedback form (rating + text) or just freeform chat?
3. How does edit-distance tracking work in the task model? (Previously it was on agent_runs)
