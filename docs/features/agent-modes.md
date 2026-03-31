# Agent Modes

**Status:** Canonical (updated 2026-03-20 for ADR-126: Agent Pulse)
**Date:** 2026-03-04 (updated 2026-03-20 for ADR-126)
**Related:**
- [ADR-126: Agent Pulse](../adr/ADR-126-agent-pulse.md) — autonomous awareness engine (supersedes proactive/coordinator as distinct modes)
- [ADR-092: Agent Intelligence & Mode Taxonomy](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) — original implementation contracts (partially superseded by ADR-126)
- [Agent Framework: Scope × Role × Trigger](../architecture/agent-framework.md) — canonical taxonomy (ADR-109)

This document is the user-facing and product framing for agent modes. ADR-126 reframes modes: **all agents have a pulse** (autonomous sense→decide cycle). The "proactive" and "coordinator" modes dissolve — their self-assessment capability generalizes to all agents via the pulse. PM agents handle coordination via their specialized Tier 3 pulse.

---

## What modes are

Every agent has a **mode** — its execution character. Mode determines not just *when* a agent runs, but *how it decides* when to run and what kind of intelligence it applies.

> **ADR-126 evolution:** All agents now have a **pulse** — an autonomous sense→decide cycle that fires on a cadence. The pulse is upstream of execution: the agent senses its domain, decides whether to act, and only generates when warranted. Mode shapes the pulse's default cadence and behavior, but every agent — including recurring ones — has the capacity to self-assess as it matures.

Think of modes as the starting personality of a specialist agent. A clockwork assistant starts by showing up every Monday without fail — but as it matures, it gains the awareness to skip runs when nothing changed, or to act early when something urgent appears. An on-call assistant waits for the right conditions to accumulate. Every agent develops toward greater awareness over time.

All modes share the same foundation: each agent has its own workspace (AGENT.md, memory, observations) that accumulates domain knowledge. This is what makes each agent a specialist rather than a generic template — and what makes it get better over time.

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

> **ADR-126 note:** The proactive mode's core capability — self-assessment before generation — is generalized to ALL agents via the pulse (Tier 2: agent self-assessment). Associate+ agents in any mode can self-assess. The "proactive" label remains for agents whose primary character is domain monitoring rather than scheduled production.

> "Stay aware. Surface things before you're asked."

A proactive agent's pulse fires frequently (every cycle). On each pulse, the agent reads its domain and its own accumulated memory, then decides: is there something worth generating? If yes, it produces a run. If not, it records an observation and continues sensing.

Most pulses produce no run. This is by design — the agent stays informed without generating noise.

**Memory role:** A running `review_log` — the agent's own self-authored assessments from each pulse cycle. Over time, this log captures the agent's evolving understanding of its domain: what's normal, what's significant, what the user has responded to.

**Best for:** Standing-order intelligence work where you want a specialist keeping watch and surfacing things when they're actually worth surfacing. Not a fixed schedule — timely signal.

*Examples:* "Keep tabs on competitive developments and brief me when something significant happens." "Monitor team communication patterns and surface relationship issues before they become problems."

**Key difference from recurring:** Recurring starts with schedule-driven pulses (training wheels). Proactive starts with judgment-driven pulses from day one.

**Key difference from reactive:** Reactive waits for a specific configured event type to arrive. Proactive has standing instructions for a domain and uses its own judgment to decide what counts as signal.

---

### Coordinator — Dissolved into PM (ADR-126)

> **ADR-126:** The coordinator mode is dissolved. Its coordination capabilities are now the domain of **PM agents** — project-level coordinators created by Composer. PM agents have a specialized **coordination pulse** (Tier 3) that senses project state, steers contributors, triggers assembly, and manages delivery.
>
> What coordinator mode used to do (create child agents, advance schedules) is now split:
> - **Agent creation** → Composer capability (TP portfolio-level decisions)
> - **Schedule advancement** → PM pulse (advance_contributor action)
> - **Domain monitoring** → Proactive mode (any agent can monitor its domain)
>
> Existing coordinator agents in the database are functionally equivalent to proactive agents. They retain their mode label but pulse like proactive agents.

---

## Choosing a mode

| If you want... | Use |
|----------------|-----|
| Reliable, scheduled output — same time every week | `recurring` |
| Output toward a defined objective, then stop | `goal` |
| Output triggered by accumulated events, not schedule | `reactive` |
| A specialist that watches its domain and acts when warranted | `proactive` |

> **Note:** All modes gain pulse awareness as agents mature. A recurring agent that reaches associate seniority will self-assess before generating (skipping runs when nothing changed). The mode is the starting character — the pulse evolves it.

---

## What all modes share

Regardless of mode, every agent carries four layers of knowledge (ADR-101):

- **Roles** — role-specific format and structure (e.g., a digest always leads with highlights, a synthesize agent always has cross-source connections). Built into the role's prompt template and primitive set (ADR-109).
- **Directives** — your behavioral instructions and audience context. "Use formal tone." "The audience is the exec team." Set via the Instructions panel or TP chat.
- **Memory** — what the agent has observed and decided. Structured differently per mode (observations, goals, review log — see ADR-092), but always accumulating per specialist.
- **Feedback** — what it learned from your edits. When you modify a delivered version, the edit patterns feed into future generations as "learned preferences."

Every agent also:

- Produces **versioned, immutable output** — every generation is a permanent record you can review.
- **Sleeps** between executions — zero resource cost when not running.
- Runs the same **headless agent** under the hood — same intelligence as TP, same primitive access, scoped to background execution.
- Produces a **reflection** each run (ADR-128, ADR-149) — agents append a `## Agent Reflection` block to output, which is extracted, appended to `memory/reflections.md` (rolling 5 recent), and stripped before delivery. This reflection extraction/stripping phase is part of the headless execution pipeline.

The mode shapes how the agent decides *when* to act. The four knowledge layers shape *how* it acts.

---

## The "living agent" experience

The pulse (ADR-126) is what gives agents life. Every agent — not just proactive ones — has an autonomous sense→decide cycle. The visible effect: you can watch agents thinking, not just producing.

In a project meeting room, the timeline shows:
```
09:00  slack-recap pulsed: observe — "No new activity in #engineering"
14:00  slack-recap pulsed: generate — "47 messages, 3 escalation threads"
14:03  slack-recap run #8 complete
14:05  PM pulsed: assemble — "Both contributors fresh"
```

This is a network of sensing specialists that check their domains, act when warranted, and rest when not. The quality of each specialist's output compounds with every pulse — because each one carries forward everything it has learned about its specific job.

That compounding per specialist — not per conversation, not per session, but per agent — is the core of YARNNN's model.

---

## Role × Trigger — Natural pairings (ADR-109)

Roles and triggers are orthogonal — any combination is valid — but some pairings are the natural home for each role:

| Role | Natural triggers | Notes |
|-------|-----------------|-------|
| `digest` | recurring, reactive | Platform synthesis. Slack digests pair naturally with reactive (accumulate-then-generate). Calendar digests pair with recurring. |
| `prepare` | recurring, coordinator, goal | Daily meeting prep is recurring. Calendar-triggered prep works as coordinator children. Standalone prep works as goal. |
| `monitor` | proactive, reactive | Proactive for open-ended domain monitoring. Reactive for threshold-based event watch. |
| `research` | goal | Investigation has a defined end. Runs until the research objective is complete. |
| `synthesize` | recurring, proactive | Recurring for scheduled status updates. Proactive for self-directed intelligence (Proactive Insights). |
| `orchestrate` | coordinator | The orchestrate role makes the coordinator trigger discoverable. |
| `act` | reactive, proactive | Event-driven actions (reactive) or self-initiated actions when warranted (proactive). Future. |

**The key insight:** trigger answers *when/how* an agent decides to act. Role answers *what it does*. Scope (auto-inferred) answers *what it knows*. These are independent dimensions. A `digest` can be recurring or reactive. A `prepare` can be coordinator-triggered or goal-driven. The names don't imply a trigger or scope.
