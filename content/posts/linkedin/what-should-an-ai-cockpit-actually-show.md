# What Should An AI Cockpit Actually Show?

Most AI products call themselves "AI workspaces" but show you a chat transcript and a history sidebar.

That's not a cockpit. That's a transcript viewer.

A real cockpit for autonomous AI shows the state of the operation — what the operator is trying to accomplish, where the operation actually stands right now, how it's performing over time, what's pending. Four faces, all live, all answering questions the operator actually has when they sit down at the workspace.

**Why "chat plus history" isn't a cockpit**

The chat-shaped UI is borrowed from messaging apps where the primary action is conversation and the primary state is "what was said."

For autonomous AI, this shape is wrong. The operator's primary question when they return isn't "what did I say last time" — it's "what's the state of my operation."

Specific failures:

→ Doesn't surface autonomous activity (the AI did something while the operator was asleep — buried in chat)
→ Doesn't show standing state (current mandate, autonomy level, risk envelope)
→ Doesn't show performance (how has the operation been going)
→ Doesn't show what's pending (proposals waiting, scheduled work, blocked items)

The operator returns and has to reconstruct the state of their operation from a chat transcript. UI failure dressed up as conversational design.

**The four faces**

→ Mandate. What's the operator's standing intent? What's the autonomy posture? Empty mandate = nothing autonomous runs.
→ Money truth. Where does the operation stand right now? For trading: account value, open positions, recent P&L. For commerce: revenue, subscribers. Live external truth from the platforms.
→ Performance. How is the operation trending over time? Realized P&L over rolling windows. Win rate. Reviewer calibration metrics.
→ Tracking. What's pending? What's running? Proposal queue, recurring activity schedule, recent outcomes that need attention.

Together these answer the operator's actual return-to-workspace questions. Chat exists separately, as one tab among others, not as the primary view.

**Why programs configure faces, not layout**

Different operations have different shapes. A trading operation cares about positions and P&L. A commerce operation cares about subscribers and revenue. The cockpit has to flex without becoming arbitrarily configurable.

The pattern that works: the four faces are kernel-level (every operation has them); what fills each face is program-level (the active program supplies the bindings).

Operators get a recognizable cockpit shape across programs while each program supplies the right specific content for its domain. Programs don't reshape the cockpit; they fill it.

**Why this matters**

AI products that organize the UI around chat will keep producing operators who can't tell what their AI is actually doing between sessions. AI products that organize the UI around the operation's four faces will produce operators who can run autonomous operations confidently because they always know where they stand.

If you're designing an AI product for autonomous use cases, design the cockpit before you design the chat.

Full essay: yarnnn.com/blog/what-should-an-ai-cockpit-actually-show

#AIAgents #AICockpit #AutonomousAgents #ProductDesign #AIWorkspace

---

YARNNN is an agent-native operating system for autonomous knowledge work.
