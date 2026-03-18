# Agent Modes

**Status:** Canonical
**Date:** 2026-03-04 (updated 2026-03-17 for ADR-109/ADR-118: Scope × Role × Trigger framework)
**Related:**
- [ADR-092: Agent Intelligence & Mode Taxonomy](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) — implementation contracts
- [Agent Framework: Scope × Role × Trigger](../architecture/agent-framework.md) — canonical taxonomy (ADR-109, axis renamed per ADR-118)

This document is the user-facing and product framing for agent modes (internally: **triggers** in the Scope × Role × Trigger framework). For implementation contracts, see ADR-092. For how triggers relate to scope and role, see the [Agent Framework](../architecture/agent-framework.md).

---

## What modes are

Every agent has a **mode** — its execution character. Mode determines not just *when* a agent runs, but *how it decides* when to run and what kind of intelligence it applies.

Think of modes as the personality of a specialist agent. A clockwork assistant shows up every Monday without fail. An on-call assistant waits for the right conditions to accumulate. A proactive advisor notices things on your behalf and reaches out when something's worth surfacing. A coordinator keeps watch over a whole domain and dispatches work when needed.

All modes share the same foundation: each agent has its own `agent_instructions` (how it should behave) and `agent_memory` (what it has learned). This is what makes each agent a specialist rather than a generic template — and what makes it get better over time.

---

## The five modes

### Recurring — Clockwork

> "Show up reliably. Do the same job, better each time."

The default mode. A recurring agent runs on a fixed schedule — daily, weekly, biweekly, monthly, or a custom cron expression. Every scheduled run produces a new version. No judgment call: if the time has come, it runs.

**Memory role:** Accumulates learned preferences from prior runs — what the user edits, what formats work, what context tends to be most relevant. Each generation is better-informed than the last.

**Best for:** Work products where regularity is the value. You want it there every Monday whether or not anything significant happened, because consistency is itself useful.

*Examples:* Weekly #engineering digest. Daily inbox brief. Monthly board update prep.

---

### Goal — Project

> "Work toward a clear objective. Stop when it's done."

A goal agent runs on a schedule, but it tracks progress toward a stated completion point. After each generation, it assesses whether the goal has been met. When it determines the goal is complete, it stops running — no more versions, no more noise.

**Memory role:** Maintains a structured goal record: description, status, milestones, and a completion assessment written after each generation. When `status = complete`, the agent pauses itself.

**Best for:** Time-bounded work with a clear end. You don't want a weekly "competitor research" agent running forever — you want it to run until it's covered the ground you specified.

*Examples:* "Research and brief me on these 4 competitors — stop when each has been covered." "Prepare board materials for Q1 — stop after the board meeting date."

---

### Reactive — On-call

> "Watch. Accumulate. Act when the picture is complete."

A reactive agent doesn't run on a schedule. It watches a configured source for events. When events arrive, it doesn't generate immediately — instead, it writes a brief agent-authored observation to its memory. When enough observations have accumulated (a configurable threshold, default 5), it generates a version and clears its observation queue.

This means a reactive agent is always aware of what's happening in its domain, but only produces output when there's enough to say something meaningful.

**Memory role:** `observations` array — each entry is a brief note the agent authored from an incoming event. Not raw platform data — the agent's own interpretation. Cleared after each generation.

**Best for:** Event-driven domains where individual events are noise but patterns are signal. You want a brief when 5 relevant things have accumulated, not after every single mention.

*Examples:* "Watch #product-feedback. When enough relevant threads have accumulated, draft a summary." "Watch Gmail threads tagged [client]. Brief me when a pattern of activity has built up."

---

### Proactive — Living Specialist

> "Stay aware. Surface things before you're asked."

A proactive agent doesn't wait for a schedule or an event. It runs on a slow periodic review cadence — configurable, typically daily or slower. On each review cycle, the agent reads its sources and its own accumulated memory, then decides: is there something worth generating? If yes, it produces a version. If not, it records an observation and goes back to sleep. If conditions are unusually quiet, it can schedule itself to check back later.

Most review cycles produce no version. This is by design — the agent stays informed without generating noise.

**Memory role:** A running `review_log` — the agent's own self-authored assessments from each review cycle. Over time, this log captures the agent's evolving understanding of its domain: what's normal, what's significant, what the user has responded to.

**Best for:** Standing-order intelligence work where you want a specialist keeping watch and surfacing things when they're actually worth surfacing. Not a fixed schedule — timely signal.

*Examples:* "Keep tabs on competitive developments and brief me when something significant happens." "Monitor team communication patterns and surface relationship issues before they become problems." "Watch my calendar context and give me prep when it looks like I need it — not on a fixed schedule."

**Key difference from recurring:** Recurring shows up on time no matter what. Proactive shows up when it judges the moment is right.

**Key difference from reactive:** Reactive waits for a specific configured event type to arrive. Proactive has standing instructions for a domain and uses its own judgment to decide what counts as signal.

---

### Coordinator — Meta-Specialist

> "Watch the whole domain. Dispatch the right work at the right time."

A coordinator agent is a proactive specialist with one additional capability: it can create new agents on your behalf and advance the schedule of existing ones when conditions warrant.

A coordinator runs on a slow review cadence. When it finds something in its domain that needs attention, it decides: does an existing agent handle this? If yes, it advances that agent's schedule to run now. If not, it creates a new one-time agent and executes it — then logs what it created so it doesn't do it again for the same event.

This is YARNNN doing work on your behalf that you didn't explicitly configure. You tell the coordinator what domain it's responsible for; it handles the rest.

**Memory role:** A `review_log` (like proactive) plus a `created_agents` deduplication log. The log prevents the coordinator from creating duplicate agents for the same underlying event.

**Best for:** Domains where the right response to a signal is a specific piece of work — not just a summary. Calendar coordination, relationship management, project monitoring.

*Examples:* "Watch my calendar. When I have an upcoming meeting with external attendees I haven't corresponded with recently, create a meeting prep brief." "Watch for Gmail threads with clients that have gone quiet. Draft a follow-up when you see one." "Monitor project Slack channels. When you see signs of a blocker or a stalled decision, create a status brief."

**What makes a coordinator different from signal processing (dissolved):** Signal processing was invisible infrastructure that scanned everything for all users. A coordinator is a agent you configure with specific instructions for a specific domain. You can see its review log. You can edit its instructions. You can pause it. Multiple coordinators are multiple independent specialists — each accountable for its own scope.

---

## Choosing a mode

| If you want... | Use |
|----------------|-----|
| Reliable, scheduled output — same time every week | `recurring` |
| Output toward a defined objective, then stop | `goal` |
| Output triggered by accumulated events, not schedule | `reactive` |
| A specialist that watches its domain and acts when warranted | `proactive` |
| A specialist that creates and triggers other agents for you | `coordinator` |

---

## What all modes share

Regardless of mode, every agent carries four layers of knowledge (ADR-101):

- **Skills** — skill-specific format and structure (e.g., a digest always leads with highlights, a synthesize agent always has cross-source connections). Built into the skill's prompt template and primitive set (ADR-109).
- **Directives** — your behavioral instructions and audience context. "Use formal tone." "The audience is the exec team." Set via the Instructions panel or TP chat.
- **Memory** — what the agent has observed and decided. Structured differently per mode (observations, goals, review log — see ADR-092), but always accumulating per specialist.
- **Feedback** — what it learned from your edits. When you modify a delivered version, the edit patterns feed into future generations as "learned preferences."

Every agent also:

- Produces **versioned, immutable output** — every generation is a permanent record you can review.
- **Sleeps** between executions — zero resource cost when not running.
- Runs the same **headless agent** under the hood — same intelligence as TP, same primitive access, scoped to background execution.

The mode shapes how the agent decides *when* to act. The four knowledge layers shape *how* it acts.

---

## The "living agent" experience

Coordinator and proactive agents together enable what feels like a living agent: something that watches your world, notices things, and surfaces work before you ask for it.

This is not an always-on background process. It's a network of sleeping specialists that wake up at the right time, assess their domain, act if warranted, and go back to sleep. The quality of each specialist's output compounds with every execution — because each one carries forward everything it has learned about its specific job.

That compounding per specialist — not per conversation, not per session, but per agent — is the core of YARNNN's model.

---

## Skill × Trigger — Natural pairings (ADR-109)

Skills and triggers are orthogonal — any combination is valid — but some pairings are the natural home for each skill:

| Skill | Natural triggers | Notes |
|-------|-----------------|-------|
| `digest` | recurring, reactive | Platform synthesis. Slack digests pair naturally with reactive (accumulate-then-generate). Calendar digests pair with recurring. |
| `prepare` | recurring, coordinator, goal | Daily meeting prep is recurring. Calendar-triggered prep works as coordinator children. Standalone prep works as goal. |
| `monitor` | proactive, reactive | Proactive for open-ended domain monitoring. Reactive for threshold-based event watch. |
| `research` | goal | Investigation has a defined end. Runs until the research objective is complete. |
| `synthesize` | recurring, proactive | Recurring for scheduled status updates. Proactive for self-directed intelligence (Proactive Insights). |
| `orchestrate` | coordinator | The orchestrate skill makes the coordinator trigger discoverable. |
| `act` | reactive, proactive | Event-driven actions (reactive) or self-initiated actions when warranted (proactive). Future. |

**The key insight:** trigger answers *when/how* an agent decides to act. Skill answers *what it does*. Scope (auto-inferred) answers *what it knows*. These are independent dimensions. A `digest` can be recurring or reactive. A `prepare` can be coordinator-triggered or goal-driven. The names don't imply a trigger or scope.
