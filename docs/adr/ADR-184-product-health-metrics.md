# ADR-184: Product Health Metrics — Revenue as First-Class Perception

> **Status**: Proposed
> **Date**: 2026-04-15
> **Related**: ADR-183 (Commerce Substrate — provides the data), ADR-159 (Filesystem-as-Memory — compact index pattern), ADR-161 (Daily Update — heartbeat artifact), ADR-162 (Inference Hardening — gap detection pattern), ADR-181 (Feedback Layer — actuation model), ADR-171/172 (Token Spend — platform billing, distinct from content commerce)
> **Extends**: FOUNDATIONS.md Axiom 4 (Value Comes from Accumulated Attention)

---

## Context

### The metrics gap

YARNNN currently measures **system health** — are agents running, are tasks executing, is the workspace accumulating? These are operational metrics. They tell you whether the machine is working. They don't tell you whether the machine is producing value.

| What we measure today | What it tells you |
|---|---|
| Agent approval rate | Are outputs good enough to deliver? |
| Task run frequency | Is the scheduler working? |
| Token spend | How much does the machine cost? |
| Entity coverage | Is the workspace accumulating? |
| Agent confidence | Does the agent think its output is good? |

None of these answer: **Is the user's content product growing?**

### Why this matters for the product thesis

The agent-native thesis (`09-agent-native-product-thesis.md`) makes a specific claim:

> "Revenue is the moat proof. If quality genuinely improves, subscribers notice, retention rises, revenue grows. Switching to any other tool means starting from zero, quality drops, revenue declines."

This claim is structurally unfalsifiable without product health metrics. If YARNNN can't observe revenue, subscriber growth, churn, or engagement, it can't:

1. **Prove the moat** — "switching costs measured in revenue" requires revenue measurement
2. **Close the quality loop** — agent output quality should correlate with subscriber behavior. Without metrics, quality assessment is circular (agents judge agents)
3. **Enrich the daily update** — the heartbeat artifact (ADR-161) should tell users "your business grew" not just "your agents ran"
4. **Enable TP product judgment** — TP currently manages agents and tasks. With product metrics, TP can reason about the business: "your competitive brief lost 2 subscribers this week — let me evaluate the last 3 outputs"

### The reframe

From **"are agents healthy?"** to **"is the user's product growing?"**

Agent health is an internal signal. Product health is the user-facing signal. The user doesn't care whether the Analyst agent has a 85% approval rate — they care whether their newsletter gained subscribers and revenue this month.

Agent health serves product health. Not the other way around.

---

## Decisions (all locked)

### 1. Three-tier metrics hierarchy

| Tier | What it measures | Who consumes it | Where it lives |
|---|---|---|---|
| **Product** (new) | Revenue, subscribers, churn, engagement, growth | User (daily update, dashboard), TP (product judgment) | `/workspace/context/revenue/`, `/workspace/context/customers/` |
| **Task** (exists) | Run history, output quality, mode state, deliverable spec adherence | TP (task management), User (work surface) | `/tasks/{slug}/` (run log, feedback, reflections) |
| **Agent** (exists) | Approval rate, run frequency, confidence, memory depth | TP (workforce health), User (agent roster) | `/agents/{slug}/memory/` (reflections, directives) |

**Read direction**: Product metrics are upstream. Task quality drives product metrics. Agent health drives task quality. The hierarchy is:

```
Product health (revenue, subscribers, churn)
  ↑ driven by
Task quality (output adherence, delivery success, feedback)
  ↑ driven by
Agent health (approval rate, confidence, memory depth)
```

TP observes all three tiers. Working memory (ADR-159) surfaces all three in the compact index.

### 2. Product health signals in working memory

Working memory's compact index (ADR-159) currently surfaces:

- Workspace state (identity, brand, domain count, document count)
- Agent roster (names, roles, statuses)
- Task list (names, modes, schedules, last run)
- Recent activity (task runs, feedback events)

Product health adds a new section:

```markdown
## Product Health
- **MRR**: $228 (+15% MoM)
- **Active subscribers**: 12 (3 new, 0 churned this month)
- **Products**: 2 active (Competitive Brief — $19/mo, Market Report — $49/quarter)
- **Revenue trend**: ↑ 4 consecutive months
- **Churn rate**: 0% (last 30 days)
```

This section is injected when a commerce provider is connected AND revenue data exists. When no commerce connection: section omitted entirely (no empty state). When connected but no revenue yet: minimal signal ("Commerce connected, no products created yet").

**Cost**: Zero LLM. Pure SQL aggregation from workspace context files (written by Commerce Bot via ADR-183 `commerce-digest` task). Same mechanical injection pattern as existing working memory signals.

### 3. Daily update enrichment

The daily update (ADR-161) is the heartbeat artifact. Currently it surfaces:

- Task execution results ("what your agents did")
- Workspace state changes ("what's new in your context")
- TP observations ("what I noticed")

With product health, the daily update adds:

- **Revenue snapshot**: "Your products earned $228 MRR across 12 active subscribers"
- **Growth signal**: "3 new subscribers this week, 0 churned"
- **Product-level callouts**: "Competitive Brief has 8 subscribers at $19/mo = $152 MRR"
- **Correlation signals**: "Market Report gained 2 subscribers the week you added the trend charts section"

These signals come from the `revenue/` and `customers/` context domains (ADR-183). The daily update task's `context_reads` gains `revenue` and `customers`. No new LLM call — same generation pipeline, richer context.

**The shift**: The daily update moves from "here's what your agents did" (activity report) to "here's how your business is doing" (business report). Agent activity is still included but subordinated to business outcomes.

### 4. TP product judgment capability

TP currently reasons about:
- Workspace state ("your context is thin in market/ — should we create a track-market task?")
- Task health ("this task hasn't run in 5 days, should we check?")
- Agent health ("Writer has low confidence for 3 consecutive runs")

Product health gives TP a new reasoning domain:

- **Revenue correlation**: "Your competitive brief lost 2 subscribers since the format change. Want me to evaluate recent outputs?"
- **Growth opportunities**: "Market Report has the highest LTV ($49/quarter). Should we increase its scope?"
- **Churn response**: "A subscriber cancelled after the last delivery. I'll review the output quality."
- **Product creation**: "Your research on {topic} is deep enough to package as a paid report. Want me to set that up?"

**Implementation**: Product health signals in working memory (Decision 2) are sufficient. TP already reasons about whatever working memory contains. No new TP prompt section needed — the signals in the compact index are enough for TP to form product-level judgments.

### 5. Feedback loop closure: product metrics as quality signal

ADR-181 established source-agnostic feedback. Product metrics become a fourth feedback source:

| Source | Mechanism | Signal type |
|---|---|---|
| User | Chat → UpdateContext | Explicit correction |
| System verification | Post-run deterministic checks | Entity staleness, coverage gaps |
| TP evaluation | ManageTask evaluate | Quality judgment |
| **Product metrics** (new) | Commerce digest → revenue/churn correlation | Implicit quality signal |

**How it works**: The `commerce-digest` task (ADR-183) writes revenue and subscriber data to context domains. When a `produces_deliverable` task's linked product shows negative signals (subscriber churn, declining engagement), the system can surface this as a feedback entry:

```markdown
## Product Signal (2026-04-15 09:00, source: product_metrics)
- Competitive Brief: 2 subscribers cancelled in 7 days following output delivery
- Action: review output quality | severity: medium
```

**Not automatic actuation**. Product metric signals are surfaced to TP via daily update and working memory. TP decides whether to evaluate, steer, or flag for user. Product metrics are too noisy for automatic actuation (correlation ≠ causation — a subscriber might cancel for reasons unrelated to output quality).

**Exception**: If churn rate exceeds a threshold (e.g., >20% of subscribers in 30 days), the signal severity escalates to `high` and TP proactively raises it in the next chat interaction.

### 6. The moat metric

A single composite signal that captures accumulated team value:

```
Accumulated Team Value = f(
    revenue_trajectory,      # MRR growth rate (3-month trend)
    tenure_months,           # How long the workspace has been active
    context_depth,           # Total entities across all context domains
    feedback_incorporation,  # Ratio of feedback entries to deliverable iterations
    delivery_consistency     # Successful delivery rate over last 30 days
)
```

**This is not a score displayed to users.** It's an internal signal for:
- TP reasoning ("your accumulated team value is high — switching tools would cost you ~$X/month in re-learning")
- Investor narrative ("average workspace accumulated team value grows at X% per month")
- Retention prediction ("workspaces with accumulated value > Y have Z% retention")

The formula is deliberately simple and transparent. It doesn't require ML — it's a weighted combination of observable signals. Weights are tunable based on empirical correlation with retention.

**Deferred**: actual weight calibration. Need 50+ active workspaces with commerce data to calibrate. Until then, the component signals are individually useful even without the composite.

### 7. Metrics surface in UI

Product health surfaces through existing surfaces, not a new one:

| Surface | What shows | How |
|---|---|---|
| **Chat** (daily briefing) | Revenue snapshot, growth signals, correlation callouts | Daily update task reads `revenue/` + `customers/` domains |
| **Work** (task detail) | Per-task product link — subscriber count, revenue attributed to this task's product | `**Commerce:**` field in TASK.md, resolved live from commerce API |
| **Agents** (roster) | No change — agent health stays agent-scoped | Agent health is internal signal |
| **Context** (filesystem) | `revenue/` and `customers/` domains browseable | Existing filesystem browser |
| **Settings** (billing) | YARNNN platform spend (ADR-172) — NOT content product revenue | Keep platform billing separate from content commerce |

**No new `/analytics` or `/revenue` surface.** Revenue is context, not a separate destination. It lives in the workspace filesystem and surfaces through existing patterns (daily update, TP awareness, context browser). Same principle as all other context — it's not a dashboard, it's accumulated intelligence that informs agent work.

---

## What Does Not Change

- Agent health metrics (approval rate, confidence, reflections) — preserved as Tier 3 internal signals
- Task health metrics (run history, feedback, mode state) — preserved as Tier 2 operational signals
- Token spend metering (ADR-171) — platform billing is distinct from content commerce
- Balance model (ADR-172) — YARNNN's own billing unchanged
- Working memory architecture (ADR-159) — product health is a new section, not a new pattern
- Daily update pipeline (ADR-161) — enriched context, same execution path
- Feedback layer (ADR-181) — product metrics are a new source, same processing tiers

---

## Implementation Phases

### Phase 1: Working memory + daily update enrichment

**Prerequisite**: ADR-183 Phase 1 (commerce-digest task writing to `revenue/` and `customers/` domains).

- `working_memory.py`: new `_get_product_health_summary()` function, reads from `revenue/_tracker.md`
- Compact index gains `## Product Health` section (conditional on commerce connection)
- Daily update task's `context_reads` gains `revenue`, `customers`
- Daily update generation prompt gains "Business Health" section guidance

**Cost**: Zero additional LLM. Pure file reads + string formatting for working memory. Daily update already runs — richer context doesn't add a call.

### Phase 2: TP product awareness

**Prerequisite**: Phase 1.

- TP prompt gains product-level reasoning examples in tools guidance (not a new section — organic extension of existing task/agent awareness)
- Product-metric feedback entries written by `commerce-digest` post-run (parallel to ADR-181 system verification)
- Churn threshold escalation logic (>20% in 30 days → high severity → TP proactive raise)

**Cost**: Zero additional LLM for feedback entries (deterministic). Churn escalation is a working memory flag, not a call.

### Phase 3: Moat metric computation

**Prerequisite**: Phase 2 + 50 active workspaces with commerce data (empirical calibration).

- `accumulated_value.py`: composite signal computation from observable metrics
- Value signal in working memory (TP can reference)
- Admin dashboard (internal): per-workspace accumulated value for retention analysis
- Investor reporting: aggregate accumulated value growth curves

**Cost**: Zero LLM. Pure computation from existing data.

### Phase 4: UI surface enrichment (deferred)

**Prerequisite**: Phase 1-2 validated.

- Work detail: product link rendering (subscriber count, revenue)
- Chat briefing: structured revenue cards in daily update HTML
- Context browser: revenue/customers domain with entity-level drill-down

---

## Relationship to ADR-183

ADR-183 provides the **data infrastructure** (commerce connection, context domains, Commerce Bot, task types). ADR-184 provides the **intelligence layer** (what the system does with that data).

```
ADR-183 (Commerce Substrate)          ADR-184 (Product Health Metrics)
┌────────────────────────────┐        ┌──────────────────────────────┐
│ Commerce connection        │        │ Working memory enrichment    │
│ Commerce Bot + digest task │───────→│ Daily update enrichment      │
│ revenue/ + customers/      │        │ TP product judgment          │
│ Webhook → workspace writes │        │ Feedback loop closure        │
│ Delivery to subscribers    │        │ Moat metric computation      │
└────────────────────────────┘        └──────────────────────────────┘
        DATA                                   INTELLIGENCE
```

ADR-183 can ship without ADR-184 (agents can see commerce data, just not reason about it systemically). ADR-184 cannot ship without ADR-183 (nothing to reason about without the data).

---

## Revision History

| Date | Change |
|---|---|
| 2026-04-15 | v1.0 — Initial proposal. All decisions locked. Three-tier metrics hierarchy, product health in working memory, daily update enrichment, TP product judgment, product-metric feedback source, moat metric, UI through existing surfaces. |
