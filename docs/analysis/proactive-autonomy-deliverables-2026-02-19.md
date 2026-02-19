# Proactive Autonomy — Next-Generation Deliverable Types

**Date**: 2026-02-19
**Status**: Superseded by ADR-068 — retained for strategic context and ideation record
**See**: [ADR-068: Signal-Emergent Deliverables](../adr/ADR-068-signal-emergent-deliverables.md) for the architectural decision
**Note**: The "TP agent running autonomously with a task brief" framing in this doc was architecturally incorrect — it violates the Path A/B boundary (ADR-061). The correct model is the orchestrator's Signal Processing phase (Path B). The examples and use cases remain valid; the mechanism was wrong.

---

## The Reframe

Current deliverables are **pull-based pipelines**: user configures sources, system fetches on schedule, LLM summarizes, delivers. The user has to think to set them up. The output is a competent summary of what happened.

That's not the real product. The real product is an agent that already knows your world and takes initiative on work you'd otherwise have to think to ask for.

This is a shift from:
> "Summarize my Slack channels every Monday"

To:
> "Notice what matters in my work and act on it before I notice I need to"

The primitives are already in the architecture:
- **Memory layer** (`user_context`) — knows who you are, your role, your commitments, your communication style
- **Activity log** — tracks patterns across platforms over time
- **Context layer** — live access to Slack, Gmail, Notion, Calendar
- **TP agent** — has tools, has reasoning, knows your context

The deliverable types just haven't caught up to what the infrastructure enables.

---

## Two Classes of Proactive Deliverable

### Class 1: Pattern-Aware Alerts
The system tracks state across time and surfaces deviations from your normal patterns. No schedule needed — triggered when the pattern is detected.

**Relationship drift alert**
> "You haven't responded to [client] in 11 days. Based on your history with them, this is unusual. Here's a draft catch-up email."

Requires: Gmail thread history, memory of relationship cadence, draft generation. The agent needs to know what "unusual" means for *you* specifically — a silence that's normal with one contact is a red flag with another.

**Momentum digest — what fell through the cracks**
> "Three threads went quiet this week that were active last week: the design review with Ana, the API proposal with Marcus, the Q1 roadmap. Here's what fell off and suggested next actions."

Requires: Cross-platform activity delta (Slack + Gmail + Notion), week-over-week comparison, judgment about what was "in-flight" vs. intentionally parked.

**Conflict detection**
> "Your Notion roadmap says X is Q1 priority but your Slack activity this week shows you've been pulled onto Y almost entirely. Want me to flag this to your team or update the roadmap?"

Requires: Notion page content + Slack activity signal + memory of stated priorities. The agent has to hold two things simultaneously — what you *said* your priorities are and what you're *actually* doing — and surface the gap.

---

### Class 2: Anticipatory Drafts
The system notices upcoming obligations and prepares for them before you think to ask.

**Pre-meeting intelligence brief — with commitment tracking**
> "You're meeting Sarah tomorrow at 2pm. Last time you met (Feb 5), you committed to sharing the pricing proposal. You haven't sent it. Here's a draft email with the proposal attached, and a brief on what to expect from the meeting."

This is qualitatively different from "Meeting Prep" as currently scoped. It's not just context retrieval — it's the agent holding your commitments against your actions and flagging the delta.

Requires: Calendar event → get attendees → search email history with those attendees → search memory for past commitments → generate prep brief + draft follow-up.

**Stakeholder update, auto-initiated**
> "It's been 6 days since your last update to the team. Based on your typical cadence and this week's activity, I've drafted a weekly update. Review before I send?"

The user didn't ask for this. The system knows the pattern (weekly update every Friday) and the content (what happened in Slack + Notion this week) and drafts it before they think to ask.

Requires: Activity log pattern detection, multi-platform context fetch, draft generation, user review gate before delivery.

---

## What Makes This Architecturally Different

These aren't harder summaries. They require capabilities the current pipeline doesn't have:

**1. State comparison across time**
Drift detection and momentum tracking require comparing current state against a past baseline. The current executor fetches a snapshot and summarizes it. It has no concept of "what changed relative to last week" beyond the `delta` scope mode (which is not yet fully implemented).

**2. Cross-signal correlation**
Conflict detection requires holding Notion content and Slack activity simultaneously and reasoning about the relationship between them. Single-platform strategies can't do this — it requires a reasoning agent with access to multiple sources in the same context window.

**3. Commitment tracking**
Meeting prep with commitment tracking requires reading past emails/messages, extracting what was promised, checking if it was delivered, and surfacing the gap. This is a multi-step reasoning task, not context assembly. It needs the agent to run inference across sources, not just retrieve them.

**4. Trigger-based rather than schedule-based**
Most of these fire when a condition is met, not on a calendar schedule. Relationship drift fires when silence exceeds a threshold. Conflict detection fires when pattern divergence exceeds a threshold. This requires a different execution model — event-driven or periodic-check rather than cron.

**5. Action outputs, not just report outputs**
These deliverables produce things that can be *sent or acted on*, not just read. A draft email isn't just a summary — it's ready to go if the user approves. This means the delivery model needs a review-before-send gate that currently doesn't exist as a first-class UX pattern.

---

## Execution Model — Architectural Correction

**The "TP running autonomously with a task brief" framing in the original draft was wrong.** TP is Path A (conversational, real-time, session-scoped). It does not generate deliverable content — that is Path B (ADR-061).

The correct execution model is the **orchestrator's Signal Processing phase** (ADR-068):

```
Cron fires
  → Signal extraction pass over Layer 3 (what happened in user's world)
  → Orchestration agent reasons: what does this warrant?
  → Creates signal_emergent deliverable (origin=signal_emergent, trigger_type=manual)
  → Queues execution using existing DeliverableAgent + execution strategies
  → Version surfaces to user with governance=manual (review gate)
```

The "task brief" concept maps to the signal summary fed to the orchestration agent — structured behavioral signal extracted from platform data, not raw content. The orchestration agent is not TP. It is the same DeliverableAgent that handles all Path B execution, operating over a richer context input.

The changes required (from ADR-068):

1. **Signal extraction pass** — Deterministic read of `filesystem_items` metadata producing a structured behavioral signal summary (no LLM needed for extraction).

2. **Signal processing function** — Single LLM call (orchestration agent) reasoning over signal summary + user memory + recent activity. Produces: trigger existing deliverable, create signal-emergent deliverable, or nothing.

3. **`origin` field on `deliverables`** — Distinguishes `user_configured` | `analyst_suggested` | `signal_emergent`. One schema addition.

4. **Review gate** — Already exists. `governance=manual` → version lands as `staged`, user reviews before delivery. No new UX pattern needed.

---

## Proposed Sequence

**Phase 1 — Validate the execution model** (before new types)
Wire one existing deliverable type (Gmail Inbox Brief is the best candidate) to run as a TP agent session instead of the dumb pipeline. Confirm: output capture works, cost is acceptable, execution completes within timeout.

**Phase 2 — First proactive type**
Meeting Prep with commitment tracking. This is the most contained: calendar event is a clear trigger, the fetch chain is bounded (calendar → email history with attendees → memory), and the output is a brief the user reads, not an action they approve.

**Phase 3 — Action-producing types**
Relationship drift alert with draft email. Requires the review-before-send UX gate. This is where the "agent drafts, human approves" pattern becomes explicit product behavior.

**Phase 4 — Cross-signal types**
Conflict detection, momentum digest. These require the state comparison infrastructure and are the highest-complexity/highest-value types.

---

## What This Product Actually Is

These deliverable types make the product something different from what's currently in the market:

- **Not a chat assistant** — doesn't wait to be asked
- **Not a summary tool** — doesn't just report what happened
- **Not a notification system** — doesn't just alert, it acts or drafts

It's closer to a chief of staff that has read access to everything, has internalized your patterns, and surfaces the work that would otherwise fall through the cracks or require you to think to ask for it.

The four-layer model (Memory / Activity / Context / Work) was the right architectural bet. The memory layer is what makes proactive deliverables personal rather than generic. Without knowing your commitment cadence with a specific person, relationship drift is just silence. With it, the agent can make a judgment call.

The gap between current deliverables and this vision is real but it's a product roadmap gap, not an architectural one. The primitives are there.

---

## Open Questions

1. **Trigger model** — hourly cron evaluating conditions vs. event-driven webhooks from platforms. Cron is simpler to build; webhooks are lower-latency but require platform push subscriptions.

2. **Cost ceiling per user** — what's the acceptable monthly cost for a user with 5 active proactive deliverables, each running TP with 4-6 tool calls? Needs a number before Phase 1.

3. **Review gate vs. full autonomy** — is the review gate always required for action-producing deliverables, or does the user opt into full autonomy per deliverable? This is partly a trust/liability question, not just a UX one.

4. **Memory write-back** — when TP runs a proactive deliverable and makes judgments ("this contact relationship is drifting"), should that judgment be written back to memory? This would make subsequent runs more accurate but complicates the memory model.
