# Feedback Workflow — Three-Layer Model

**Date:** 2026-03-26 (original), 2026-04-03 (revised to three-layer)
**Status:** Implemented (ADR-156: three-layer routing)
**Depends on:** ADR-138 (Agents as Work Units), ADR-156 (Single Intelligence Layer)

---

## Principle: Three Layers of Feedback

Feedback routes to three layers: WHAT the workspace tracks, WHO produces output, HOW output is produced.

| Layer | What changes | Target | Persistence | Read by | Example |
|-------|-------------|--------|-------------|---------|---------|
| **Domain** | What entities the workspace tracks | ManageDomains(add/remove) | Permanent, cross-task | All tasks via context_reads | "Don't track Tabnine", "Add Anthropic" |
| **Agent-core** | How the agent produces output (style, tone) | `/agents/{slug}/memory/feedback.md` | Permanent, cross-task | Agent on every run via load_context() | "Use formal tone", "Great charts" |
| **Task-specific** | What this task focuses on and outputs | `/tasks/{slug}/memory/feedback.md` + TASK.md | Per-task only | Agent on this task's runs | "Focus on pricing", "Add a chart" |

**Domain** changes affect what exists in the workspace. **Agent** feedback shapes the person. **Task** feedback shapes the work.

## Entry Points (All → TP Chat)

1. **Email "Reply with feedback"** → `/tasks/{slug}` → task-scoped TP
2. **Task page chat** → user types feedback → TP routes
3. **Workfloor chat** → agent feedback only (no task context)

No background jobs. No edit-distance extraction. Feedback is always explicit, always through TP.

## Primitives (ADR-146 consolidated)

### ManageDomains (domain layer)
```
ManageDomains(action="remove", domain="competitors", slug="tabnine")
ManageDomains(action="add", domain="competitors", slug="anthropic", name="Anthropic")
```

### UpdateContext(target="agent") (agent layer)
**Writes to:** `/agents/{slug}/memory/feedback.md`
**Scope:** Cross-task — applies to all tasks this agent works on
```
UpdateContext(target="agent", agent_slug="research-agent", text="Use shorter executive summaries")
```

### UpdateContext(target="task") (task layer)
**Writes to:** `/tasks/{slug}/memory/feedback.md` or TASK.md sections
**Scope:** Per-task — only affects this task's future runs

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
