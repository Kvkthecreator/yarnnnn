# Proactive Autonomy — Next-Generation Deliverable Types

**Date**: 2026-02-19
**Status**: Working draft — strategic discourse
**Context**: Continuation of discourse on TP agent architecture and what it enables beyond current deliverable types

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

## The TP Agent Execution Model

The right execution model for these types is **TP running autonomously with a task brief**.

```
deliverable_brief = {
  "task": "...",         # What to produce
  "context_keys": [...], # Which memory keys to inject
  "tools_allowed": [...],# Which platform tools TP can call
  "time_window": "...",  # Lookback window for platform queries
  "output_format": "...",# email_draft | slack_message | structured_brief
  "delivery": {...},     # Where to send after user review (optional gate)
}
```

TP receives the brief as its system prompt, calls tools autonomously to gather what it needs, reasons across the data, produces the output, and captures it as a deliverable version. No human in the loop during execution — but optionally gated before delivery.

This is not a major architectural leap from where TP already is. The changes required:

1. **Output capture path** — TP currently streams to a chat session. An autonomous run needs to write to `deliverable_versions` instead. This is a new execution mode, not a new agent.

2. **Trigger/condition layer** — A lightweight periodic job (or webhook) that evaluates whether conditions for proactive deliverables are met. Runs on a short interval (e.g., hourly), evaluates each user's active proactive deliverables, fires execution when triggered.

3. **Review gate UX** — For action-producing deliverables (draft emails, stakeholder updates), the detail page needs an "Approve & Send" path distinct from the current passive delivery model.

4. **Cost model** — TP with 4-6 tool calls per autonomous run is materially more expensive than the current single-LLM-call pipeline. This needs to be priced or rate-limited at the deliverable level.

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
