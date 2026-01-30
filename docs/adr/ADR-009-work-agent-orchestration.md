# ADR-009: Work and Agent Orchestration

**Status**: Draft for Discussion
**Date**: 2026-01-30
**Supersedes**: None (new architecture)

---

## Context

YARNNN's core thesis is that AI agents can do real work when given persistent context. We have:
- Memory system (ADR-005): unified, semantic, user+project scoped
- Document pipeline (ADR-008): ingest context from files
- Thinking Partner (ADR-007): conversational assistant with tools

What's missing: **the ability to hand off work to agents and receive outputs asynchronously**.

The AI landscape is rapidly evolving toward agentic systems that work autonomously. The architecture must support:
1. Work that happens when users aren't looking
2. Proactive delivery of completed work
3. Continuous/recurring work cycles
4. Multiple specialized agents with different capabilities
5. Human oversight without blocking execution

This is not an MVP feature list—it's foundational infrastructure for agent-driven work.

---

## First Principles

### Principle 1: Work is Asynchronous by Default

Users should be able to request work and walk away. The mental model:
- "Create a weekly competitor report" → set and forget
- "Research this topic" → come back later for results
- "Generate content based on my context" → delivered when ready

**Implication**: Work execution is decoupled from user sessions. Agents run in the background.

### Principle 2: Push, Not Just Pull

Users shouldn't have to check for results. The system reaches out:
- Email: "Your research report is ready"
- In-app notification: "Content draft completed"
- Digest: "This week: 3 reports generated, 2 pending review"

**Implication**: Delivery channels (email, push, in-app) are first-class. User preferences control timing and method.

### Principle 3: Time is a First-Class Dimension

Work isn't just "do this now." It includes:
- **Scheduled**: "Every Monday at 9am"
- **Triggered**: "When new context is added"
- **Continuous**: "Keep monitoring and report changes"
- **Deferred**: "Do this tonight when I'm not working"

**Implication**: Scheduling infrastructure is core, not an add-on.

### Principle 4: Agents are Specialists, Orchestration is Separate

Each agent type has a focused capability:
- Research: investigate, synthesize, monitor
- Content: write, edit, adapt voice
- Reporting: structure, visualize, summarize

Orchestration decides: which agent, when, with what context, delivering how.

**Implication**: Agent interfaces are clean and single-purpose. Orchestration layer handles routing, scheduling, delivery.

### Principle 5: Human Oversight Without Blocking

Agents can work autonomously, but humans stay in control:
- Outputs are reviewable before "publishing"
- Users can approve, reject, or request revision
- High-stakes work can require approval gates
- Low-stakes work can auto-approve based on confidence

**Implication**: Supervision is configurable per work type, not one-size-fits-all.

### Principle 6: Provenance is Non-Negotiable

Every output traces back to:
- Which context (memories, documents) informed it
- Which agent produced it
- What parameters/instructions were given
- What the reasoning chain was

**Implication**: Audit trail is built into the data model, not retrofitted.

---

## Core Concepts

### Work Intent

What the user wants to accomplish. Captures:
- **Goal**: What outcome they want
- **Agent type**: Which specialist to use
- **Parameters**: Customization (scope, depth, format)
- **Timing**: When/how often
- **Delivery**: How to notify when complete

```
WorkIntent {
  id, user_id, project_id
  goal: text                    # "Weekly competitor analysis"
  agent_type: enum              # research, content, reporting
  parameters: jsonb             # agent-specific config
  schedule: ScheduleConfig?     # null = one-shot
  delivery: DeliveryConfig      # email, in-app, digest
  created_at
}
```

### Work Execution

A single run of work against an intent. Tracks:
- **Status**: pending → running → completed/failed
- **Context snapshot**: What memories/docs were used
- **Outputs**: What was produced
- **Metrics**: Tokens, duration, cost

```
WorkExecution {
  id, intent_id, user_id, project_id
  status: enum                  # pending, running, completed, failed
  started_at, completed_at
  context_snapshot: jsonb       # memory_ids, document_ids used
  error_message: text?
  token_usage: jsonb
  cycle_number: int             # for recurring: 1st, 2nd, 3rd run
}
```

### Work Output

What an agent produces. Can be text, file, or structured data.

```
WorkOutput {
  id, execution_id, user_id, project_id
  output_type: enum             # summary, report, draft, file
  title: text
  content: text?                # for text outputs
  file_url: text?               # for file outputs (PDF, PPTX)
  file_format: text?
  confidence: float             # agent's confidence 0-1
  source_refs: jsonb            # which memories/chunks informed this
  supervision_status: enum      # pending_review, approved, rejected, auto_approved
  created_at
}
```

### Schedule

For recurring work. Defines cadence and next run.

```
Schedule {
  id, intent_id, user_id, project_id
  frequency: enum               # daily, weekly, biweekly, monthly, custom
  cron_expression: text?        # for custom
  preferred_time: time          # user's preferred delivery time
  timezone: text
  enabled: boolean
  next_run_at: timestamptz
  last_run_at: timestamptz
  last_execution_id: uuid?
}
```

### Delivery Preference

How users want to receive work outputs.

```
DeliveryPreference {
  user_id
  channel: enum                 # email, in_app, digest, push
  enabled: boolean
  timing: enum                  # immediate, batched, daily_digest
  quiet_hours_start: time?
  quiet_hours_end: time?
}
```

---

## Orchestration Flow

### 1. Work Creation

```
User requests work (via UI, TP, or API)
    ↓
Create WorkIntent with parameters
    ↓
If schedule specified:
    Create Schedule, calculate next_run_at
    ↓
Create WorkExecution (status: pending)
    ↓
Queue for processing
```

### 2. Work Processing (Background)

```
Queue processor claims pending execution
    ↓
Load context:
    - User memories (project_id IS NULL)
    - Project memories (if project_id)
    - Relevant chunks (semantic search on goal)
    ↓
Snapshot context (store IDs for provenance)
    ↓
Route to agent based on agent_type
    ↓
Agent executes:
    - Receives task + context bundle
    - Calls LLM with appropriate prompt
    - Produces structured output
    ↓
Create WorkOutput(s)
    ↓
Update WorkExecution status
    ↓
Trigger delivery
```

### 3. Delivery

```
WorkExecution completes
    ↓
Check user's DeliveryPreference
    ↓
If immediate + email enabled:
    Send email via Resend
    ↓
If batched:
    Queue for next batch window
    ↓
If daily_digest:
    Aggregate into digest job
    ↓
Create in-app notification regardless
```

### 4. Scheduled Work

```
Cron job runs (every minute or via pg_cron)
    ↓
Find Schedules where next_run_at <= NOW()
    ↓
For each:
    Create new WorkExecution
    Update next_run_at
    ↓
Executions processed by queue processor
```

---

## Agent Interface

All agents implement the same interface:

```python
class BaseWorkAgent:
    """Specialist agent for producing work outputs."""

    async def execute(
        self,
        task: str,                    # What to do
        context: ContextBundle,       # Memories + documents
        parameters: dict,             # Agent-specific config
    ) -> list[WorkOutputResult]:
        """
        Execute work and return outputs.

        Returns list because one execution may produce multiple outputs
        (e.g., research produces findings + recommendations).
        """
        pass

@dataclass
class WorkOutputResult:
    output_type: str              # summary, finding, draft, file
    title: str
    content: str | None           # for text
    file_path: str | None         # for generated files
    confidence: float             # 0-1
    source_refs: list[str]        # memory/chunk IDs used
```

### Agent Types

**ResearchAgent**
- Input: research question, scope (broad/focused), depth (quick/thorough)
- Output: findings, insights, recommendations
- Uses: web search tools, context synthesis

**ContentAgent**
- Input: content brief, format (article/copy/email), tone
- Output: drafts, variations
- Uses: user voice from memories, style preferences

**ReportingAgent**
- Input: report type, data scope, format (PDF/PPTX/markdown)
- Output: formatted reports, visualizations
- Uses: structured data from context, templates

---

## Supervision Model

Not all work needs human review. Configurable per intent:

### Auto-Approve
- Low-stakes outputs
- Agent confidence > threshold
- Recurring reports user has approved before

### Require Review
- First run of new intent
- Agent confidence < threshold
- High-stakes outputs (external-facing content)

### Supervision States
```
pending_review → approved     (user accepts)
              → rejected      (user discards)
              → revision_requested (user wants changes)

auto_approved                 (skipped review based on rules)
```

### Revision Loop
```
User requests revision with feedback
    ↓
Create new WorkExecution for same intent
    ↓
Include revision feedback in agent context
    ↓
Agent produces updated output
    ↓
New output enters supervision flow
```

---

## Thinking Partner Integration

TP can initiate work (already has tools per ADR-007). Extended capabilities:

### TP as Work Initiator
```
User: "Can you research competitors in the AI assistant space?"
    ↓
TP recognizes work request
    ↓
TP uses tool: create_work_intent(
    goal="Research competitors in AI assistant space",
    agent_type="research",
    parameters={scope: "focused", depth: "thorough"}
)
    ↓
Returns: "I've started a research task. I'll let you know when it's ready,
          or you can check the Work tab."
```

### TP as Work Reviewer
```
Research completes, user asks TP about it
    ↓
TP uses tool: get_recent_outputs(project_id)
    ↓
TP summarizes: "Your competitor research found 5 main players..."
```

---

## Proactive Features

Building on companion AI patterns for push-based engagement:

### Work Digest
- Daily/weekly email summarizing completed work
- Pending items needing review
- Upcoming scheduled work

### Completion Notifications
- "Your research report is ready" (email/push)
- Respects user's quiet hours
- Batching for users who prefer fewer interruptions

### Stale Work Detection
- Scheduled work that hasn't run (disabled, erroring)
- Outputs pending review for too long
- Intents that haven't produced outputs

---

## Data Model Summary

### New Tables

| Table | Purpose |
|-------|---------|
| `work_intents` | What user wants to accomplish |
| `work_executions` | Individual runs of work |
| `work_outputs` | Agent-produced deliverables |
| `work_schedules` | Recurring work configuration |
| `delivery_preferences` | User notification settings |
| `work_notifications` | Delivery tracking |

### Existing Table Changes

| Table | Changes |
|-------|---------|
| `users` | Add `preferred_notification_time`, `timezone` |
| `workspaces` | Add aggregate limits (outputs/month for billing) |

---

## Queue Architecture

### Option A: Database Queue (Recommended for Start)
- `work_executions` table with `status = 'pending'`
- Cron job polls and claims with `FOR UPDATE SKIP LOCKED`
- Simple, no additional infrastructure

### Option B: External Queue (Future Scale)
- Redis/SQS for high-volume
- Separate worker processes
- Better for horizontal scaling

### Recommendation
Start with database queue. Migrate to external queue only when:
- Processing latency becomes issue
- Need multiple concurrent workers
- Volume exceeds what single process handles

---

## Implementation Phases

### Phase 1: Core Infrastructure (Partial)
- [x] Using existing `work_tickets` table (maps to work_intents concept)
- [x] Using existing `work_outputs` table
- [ ] Queue processor (database-based)
- [ ] Basic Research agent implementation

### Phase 2: TP Integration ✅
- [x] TP tools for work creation (`create_work`)
- [x] TP tools for work listing (`list_work`)
- [x] TP tools for status retrieval (`get_work_status`)
- [ ] Conversational work management refinements

### Phase 3: Scheduling
- [ ] work_schedules table
- [ ] Cron job for scheduled work
- [ ] Schedule management UI

### Phase 4: Delivery
- [ ] delivery_preferences table
- [ ] Email notifications (Resend)
- [ ] In-app notification center

### Phase 5: Supervision
- [ ] Supervision states and transitions
- [ ] Review UI
- [ ] Revision loop

### Phase 6: Additional Agents
- [ ] Content agent
- [ ] Reporting agent (with file generation)

---

## Open Questions for Discussion

1. **Intent vs Execution naming**: Is "intent" the right word? Alternatives: work_request, work_task, work_order

2. **Output ownership**: Should outputs belong to project or user? (Currently: project, with user fallback for global work)

3. **Confidence thresholds**: What confidence level triggers auto-approve vs require-review?

4. **Digest frequency**: Daily default? User-configurable?

5. **TP's role**: Should TP be able to approve outputs on user's behalf? Or always require human review?

6. **Cost tracking**: Track token usage per execution? Per user? For billing purposes?

---

## References

- ADR-005: Unified Memory with Embeddings
- ADR-007: Thinking Partner Project Authority
- ADR-008: Document Pipeline
- Legacy yarnnn-app-fullstack: work_tickets, recipes, supervision patterns
- chat_companion: push delivery, scheduling, silence detection patterns
- ESSENCE.md: Core domain model

---

## Decision

**Pending discussion.** This ADR proposes foundational architecture for:
- Asynchronous agent work
- Push-based delivery
- Scheduled/recurring work
- Configurable supervision
- Full provenance

The architecture prioritizes correctness and extensibility over speed-to-implement, recognizing that this infrastructure will underpin all future agent capabilities.
