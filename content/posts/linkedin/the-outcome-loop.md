# The Outcome Loop: How An AI Reviewer Learns From Real P&L

Autonomous AI improves only as much as its outcome loop is closed.

The loop has five steps: an agent proposes an action, the reviewer judges it, the action executes, the real-world result gets observed, the reviewer's calibration adjusts. Each step is a piece of architecture. Skipping any of them produces autonomous AI that can fire actions but can't learn from them.

**The five steps**

→ Propose. An agent produces an action it thinks should fire. Structured proposal: what action, what reasoning, what expected outcome, what confidence. Written to substrate.
→ Judge. The reviewer reads the proposal, the operator's mandate and principles, the recent performance, the relevant context. Emits verdict: approve, reject, or defer.
→ Execute. Approved actions fire. The trading order goes to the broker. The campaign launches. The action produces a real-world consequence.
→ Observe. The system reads the real-world outcome from the platform. The trade closed at $X. The campaign generated Y conversions. Outcome data flows back into the substrate as money-truth.
→ Calibrate. The reviewer reads recent outcomes when judging future proposals. Outcomes that suggest principles are too aggressive or conservative produce signals the reviewer can act on.

Loop closed. The next proposal benefits from what the last action taught the system.

**How this differs from RLHF**

RLHF retrains the model. The outcome loop adjusts the substrate the model reads.

RLHF requires labeled feedback at training time. The outcome loop runs continuously at inference time.

RLHF is opaque to the operator. The outcome loop is fully legible — the operator can read the principles, the decisions, the outcomes.

RLHF is centralized at the model lab. The outcome loop is per-workspace and per-operator.

The two patterns aren't competing — they operate at different layers.

**Why the loop is mostly missing today**

Most AI products execute consequential actions in-line, not via proposals. They have no operator-authored principles file. They don't observe outcomes structurally. Their reviewer can't read performance.

Each missing piece is fixable but requires architectural commitment, not feature work. The outcome loop is the consequence of having the underlying architecture, not a separate feature.

**Why the pattern will spread**

Operators trying to deploy autonomous AI will eventually all need this loop. The products that ship it have the property operators want. The products that don't will continue to be signal generators with autonomy theater.

If you're building autonomous AI, build the outcome loop. It's the difference between AI that fires actions and AI that fires actions and learns from them.

Full essay: yarnnn.com/blog/the-outcome-loop

#AIAgents #AutonomousAgents #AILearning #AIFeedback #MoneyTruth

---

YARNNN is an agent-native operating system for autonomous knowledge work.
