# Output & Delivery Architecture — Domain Separation

> Design document. Not an ADR yet — exploratory framing for architectural clarity.
> Date: 2026-03-29

## The Problem

The current system conflates three distinct concerns into one pipeline step:
1. **What was produced** (output)
2. **Where it goes** (delivery)
3. **How multiple outputs combine** (composition)

This creates confusion because the spectrum of "output + delivery" is enormous:

| One end | Other end |
|---------|-----------|
| Slack digest → instant post to #channel | Quarterly board deck combining 5 agent reports |
| Single-agent, single-output, immediate | Multi-agent, multi-output, scheduled, composed |

These are not the same architectural concern. Treating them as one creates mixed responsibilities.

---

## The Human Analogy

Your insight: *agents (humans) do work (tasks). They work together. But output sharing is different.*

A human knowledge worker:
1. **Produces** work artifacts — a research memo, a data pull, a draft
2. **Stores** them — in a folder, a drive, a repo (the canonical record)
3. **Shares** them — email to the team, Slack message, print for a meeting
4. **Combines** them — assembles multiple artifacts into a presentation, a report package, a board deck

Steps 1-2 are about the work. Steps 3-4 are about distribution. Critically:
- The memo exists whether or not it's shared
- Sharing the same memo to Slack and email are two deliveries of one output
- Combining the memo with three other memos into a deck is a new artifact (composition), not a delivery

---

## Four Domains

### Domain 1: Output (the artifact)

**What it is**: The thing a task produces. A markdown document, a data table, an HTML report. The canonical record of work done.

**Where it lives**: `/tasks/{slug}/outputs/{date}/output.md` + `manifest.json`

**Properties**:
- Always preserved in the app (browsable, versioned)
- Belongs to one task
- Produced by one or more agents (via task process steps)
- Immutable once generated (new runs create new versions, never overwrite)
- Frontend surfaces this in the task detail page

**Current status**: This works today. Task pipeline generates, saves to workspace, done.

### Domain 2: Delivery (the transport)

**What it is**: Moving an output (or composed artifact) to an external destination. Infrastructure, not intelligence.

**Where config lives**: On the task or on a delivery schedule (see below)

**Properties**:
- A side-effect of output, not the output itself
- Can happen 0, 1, or N times for the same output
- Can be immediate (on generation) or scheduled (deferred)
- Can target: email, Slack channel, Notion page, GitHub issue, webhook
- Is a log entry, not a first-class entity — "this output was delivered to X at time Y"
- Frontend surfaces delivery status as metadata on the output (not as a separate entity)

**Transport types** (current + future):

| Type | Mechanism | Latency | Example |
|------|-----------|---------|---------|
| Email | Resend API | Immediate or scheduled | Weekly brief to founder's inbox |
| Slack post | Slack API | Immediate | Daily recap to #team-updates |
| Notion page | Notion API | Immediate | Research report as child page |
| GitHub issue | GitHub API | Immediate | Engineering recap as issue |
| In-app only | None | N/A | Output stays in YARNNN, user browses |
| Webhook | HTTP POST | Immediate | Push to external system |

**Current status**: Works for immediate single-destination delivery. Missing: scheduled delivery, multi-destination from one output, delivery independent of generation timing.

### Domain 3: Composition (combining outputs)

**What it is**: A new artifact assembled from multiple task outputs. A roll-up, a digest, a presentation that pulls from several sources.

**Properties**:
- Input: multiple outputs (from different tasks, potentially different time periods)
- Output: a new composed artifact (lives in its own location)
- Has its own schedule (independent of task schedules)
- Has its own delivery config
- May involve LLM (summarize + combine) or be mechanical (concatenate sections)

**Examples**:

| Composition | Inputs | Output | Schedule |
|-------------|--------|--------|----------|
| Weekly Executive Summary | 3 task outputs from the week | 1 email with combined highlights | Every Friday 9am |
| Monthly Board Deck | 4 monthly reports | 1 PDF/PPTX | 1st of month |
| Daily Standup Digest | All task outputs from last 24h | 1 Slack message | Daily 8:30am |

**Current status**: Does not exist. This is the gap. Today, each task delivers independently — there's no way to say "combine these 3 outputs into one email."

### Domain 4: Surfacing (what the app shows)

**What it is**: How the frontend presents outputs, deliveries, and compositions to the user.

**Properties**:
- Independent of delivery — the app shows everything, delivery is optional external push
- Hierarchical: task → outputs → delivery status
- Cross-task views: "what was produced this week across all tasks"
- Composition preview: see the roll-up before it's delivered

**Surfacing concerns**:

| View | What it shows | Current status |
|------|--------------|----------------|
| Task detail → Output tab | Single task's output history | Exists |
| Task detail → Process tab | Multi-step execution progress | Exists |
| Workfloor dashboard | Recent outputs across all tasks | Partial |
| Output delivery log | Where each output was sent | In manifest, not surfaced well |
| Roll-up / digest view | Composed multi-task artifact | Does not exist |
| Delivery schedule view | When is the next delivery, what will it include | Does not exist |

---

## Relationships Between Domains

```
┌─────────────────────────────────────────────────────────┐
│                    GENERATION                            │
│                                                          │
│  Task A ──→ Output A₁ (stored in workspace)             │
│  Task B ──→ Output B₁ (stored in workspace)             │
│  Task C ──→ Output C₁ (stored in workspace)             │
│                                                          │
│  Each output is a first-class artifact.                  │
│  Always preserved. Always browsable in app.              │
└────────┬──────────────┬──────────────┬──────────────────┘
         │              │              │
         ▼              ▼              ▼
┌─────────────────────────────────────────────────────────┐
│                    SURFACING (app)                        │
│                                                          │
│  Task A page: Output A₁ (full content, versioned)       │
│  Task B page: Output B₁                                  │
│  Task C page: Output C₁                                  │
│  Workfloor: "3 outputs this week"                        │
│                                                          │
│  This is always available, independent of delivery.      │
└─────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌─────────────────────────────────────────────────────────┐
│              DELIVERY (per-output, optional)              │
│                                                          │
│  Output A₁ ──→ email (immediate, on generation)         │
│  Output B₁ ──→ slack:#channel (immediate)               │
│  Output C₁ ──→ (no delivery configured — app only)      │
│                                                          │
│  Each delivery is a transport event, logged.             │
│  Same output can deliver to multiple destinations.       │
└─────────────────────────────────────────────────────────┘

         SEPARATELY:

┌─────────────────────────────────────────────────────────┐
│              COMPOSITION (cross-output, scheduled)        │
│                                                          │
│  "Weekly Summary" composition:                           │
│    Reads: Output A₁ + B₁ + C₁ (from this week)         │
│    Produces: Composed artifact (digest/roll-up)          │
│    Delivers: 1 email, every Friday 9am                   │
│                                                          │
│  Composition is itself an output-like artifact.          │
│  It has its own delivery config.                         │
└─────────────────────────────────────────────────────────┘
```

---

## The Spectrum, Unified

Your observation about the spectrum from "Slack reply" to "board presentation":

| Behavior | Output | Delivery | Composition |
|----------|--------|----------|-------------|
| Slack daily recap | 1 task, 1 output | Immediate to #channel | None |
| Weekly email brief | 1 task, 1 output | Immediate to email | None |
| Monthly research report | 1 task, multi-step process | Immediate to email as PDF | None |
| Weekly executive summary | 3 tasks, 3 outputs | 1 email (Friday 9am) | Roll-up: combine 3 outputs |
| Quarterly board deck | 5 tasks, 5 outputs | 1 email + 1 Notion page | Roll-up + render as PPTX |
| Slack bot reply | 1 task (reactive), 1 output | Immediate to Slack thread | None |

The left column (simple) needs only Domain 1 + 2. The right column (complex) needs Domain 1 + 2 + 3.

Every case preserves outputs in the app (Domain 4) regardless of delivery.

---

## Key Design Decisions (Open)

### D.1: Should delivery be decoupled from task execution?

**Current**: `execute_task()` generates AND delivers in one function call.
**Proposed**: `execute_task()` generates and saves output. Delivery is a separate concern that reads outputs and transports them.

**Trade-off**: Decoupling enables scheduled delivery and roll-ups. Coupling is simpler for the "generate and email immediately" case which is 90% of current usage.

**Recommendation**: Decouple conceptually (delivery config separate from generation), but keep immediate delivery as the default path. Scheduled/batched delivery is an addition, not a replacement.

### D.2: Where does composition live?

Options:
- **A. As a task type** — "Weekly Roll-up" is a task in the registry that reads other task outputs instead of generating from scratch. Fits existing task pipeline. But it's a meta-task (reads outputs, not platform content).
- **B. As a scheduler job** — Independent cron that queries recent outputs, composes, delivers. Clean separation but new infrastructure.
- **C. As a TP capability** — User says "send me a weekly summary of all my tasks." TP creates the composition. Most flexible but requires TP to be involved.

**Recommendation**: Option A — composition as a task type. It fits the existing model (task with schedule + delivery), just with a different input source (other outputs instead of platform content). No new infrastructure needed.

### D.3: Should delivery have its own schedule?

**Current**: Delivery happens at generation time. No independent schedule.
**Proposed**: Delivery can be "immediate" (current) or "scheduled" (e.g., "deliver every Friday at 9am").

**Recommendation**: Start with immediate (current behavior). Add scheduled delivery only when composition/roll-ups are implemented, since that's the primary use case for deferred delivery.

### D.4: How should the frontend separate output vs. delivery?

**Current**: Task detail page shows output content + delivery status mixed together.
**Proposed**:
- Output tab shows the artifact (always, regardless of delivery)
- Delivery status is metadata on the output (badge: "delivered to email", "not delivered", "pending")
- Workfloor shows outputs as first-class items, with delivery status as secondary info

---

## What This Means for the "Bot" Concept

ADR-140 defines `slack_bot` and `notion_bot` as agent types. Under this framing:

- A Slack bot is an **agent whose perception is scoped to Slack** (reads Slack deeply)
- It is NOT a delivery mechanism. Delivery to Slack is a transport configuration on a task
- A task assigned to a Slack bot might deliver to email, not Slack — the agent's domain and the delivery destination are independent

This resolves the confusion: agents have expertise (domain), tasks have objectives (work), delivery has destinations (transport). Three orthogonal axes.

---

## Implementation Sequence (if we proceed)

1. **Clarify frontend surfacing** — Output tab always shows canonical artifact. Delivery status as metadata badge. No changes to backend needed.
2. **Decouple delivery conceptually** — Extract delivery config from TASK.md into a cleaner model (still task-owned, but structured: `destination`, `timing`, `format`).
3. **Add composition task type** — "Roll-up" as a task type in the registry that reads recent outputs from specified tasks and composes a digest.
4. **Add scheduled delivery** — For composition tasks that should deliver on a different schedule than they generate.
