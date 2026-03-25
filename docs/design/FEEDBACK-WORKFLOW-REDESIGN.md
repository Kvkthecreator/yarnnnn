# Feedback Workflow — Two-Layer Model

**Date:** 2026-03-26
**Status:** Implementing
**Depends on:** ADR-138 (Agents as Work Units), ADR-139 (Surface Architecture), ADR-143 (Feedback Substrate)

---

## Principle: Two Layers of Feedback

Feedback separates into WHO learns vs WHAT changes:

| Layer | Target | Persistence | Read by | Example |
|-------|--------|-------------|---------|---------|
| **Agent-core** | `/agents/{slug}/memory/feedback.md` | Permanent, cross-task | Agent on every run | "Use formal tone", "Great charts" |
| **Task-specific** | `/tasks/{slug}/TASK.md` or `memory/run_log.md` | Per-task only | Agent on this task's runs | "Focus on pricing", "Add a chart" |

Agent-core feedback shapes the **person** (style, preferences, domain knowledge).
Task-specific feedback shapes the **work** (focus, criteria, format, delivery).

## Entry Points (All → TP Chat)

1. **Email "Reply with feedback"** → `/tasks/{slug}` → task-scoped TP
2. **Task page chat** → user types feedback → TP routes
3. **Workfloor chat** → agent feedback only (no task context)

No background jobs. No edit-distance extraction. Feedback is always explicit, always through TP.

## Primitives

### WriteAgentFeedback (exists — ADR-143)

**Available at:** workfloor + task page
**Writes to:** `/agents/{slug}/memory/feedback.md`
**Scope:** Core identity learning — applies to all tasks this agent works on

```
WriteAgentFeedback(
  agent_slug: "research-agent",
  feedback: "Use shorter executive summaries. 3 bullet points max."
)
```

### WriteTaskFeedback (new)

**Available at:** task page only
**Writes to:** TASK.md fields or `/tasks/{slug}/memory/run_log.md`
**Scope:** Task-specific — only affects this task's future runs

```
WriteTaskFeedback(
  task_slug: "weekly-competitive-briefing",
  feedback: "Focus on pricing changes this week",
  target: "criteria"  // "criteria" | "objective" | "output_spec" | "run_log"
)
```

## TP Routing Logic

When user gives feedback in task-scoped chat, TP determines:

| User says | TP action |
|-----------|-----------|
| "Too verbose" / "Use bullet points" | `WriteAgentFeedback` (style preference, cross-task) |
| "Focus on pricing this week" | `WriteTaskFeedback` (task criteria, this task only) |
| "Add a recommendations section" | `WriteTaskFeedback` (output spec, this task only) |
| "Great work on the charts" | `WriteAgentFeedback` (positive reinforcement, cross-task) |
| "This is wrong, redo it" | `WriteTaskFeedback` (run_log) + suggest `TriggerTask` |
| "Change delivery to Slack" | `WriteTaskFeedback` (delivery config) |

After significant feedback, TP asks: "Want me to run this task now with the updated focus?"

## What Dies

- `feedback_distillation.py` background cron (edit-distance-based) — keep `write_feedback_entry()` only
- `feedback_engine.py` edit metrics computation — dead
- Any auto-extract-from-edits logic — dead
- Nightly feedback extraction — dead

Feedback is conversational, explicit, and immediate. No background jobs.

## Files

| File | Change |
|------|--------|
| `api/services/primitives/workspace.py` | Add `WriteTaskFeedback` primitive |
| `api/services/primitives/registry.py` | Register `WriteTaskFeedback` |
| `api/agents/tp_prompts/task_scope.py` | Feedback routing guidance in preamble |
| `api/agents/tp_prompts/tools.py` | Document both feedback primitives |
| `api/services/platform_output.py` | Email feedback URL → `/tasks/{slug}` (done) |
