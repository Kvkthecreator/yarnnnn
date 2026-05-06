# Name Your Reviewer: Why AI Judgment Should Have A Persona

Every autonomous AI system has a judgment seat, even if it doesn't know it does.

Some action gets proposed; something has to decide whether to execute. In most current products that something is an implicit "the model decides," which produces inconsistent verdicts and unpredictable behavior.

The fix isn't a better model. It's making the seat structural and letting the operator name it after the specific judgment character they want occupying it. Simons. Buffett. Deming.

That naming is the load-bearing decision.

**What the reviewer seat means**

Architecturally: the role that gates consequential AI actions. Every action that crosses a threshold (sends an email, executes a trade, edits a customer-facing document) gets routed through the seat. The seat reads the operator's mandate, the risk envelope, the recent performance, the principles file. Emits a verdict.

Three identities can fill the same seat: the human operator (manual review), an AI agent (automated against principles), or an admin impersonating a persona for testing.

The model behind the seat is interchangeable. What's not interchangeable is the persona — the judgment character the operator authored.

**Persona vs anonymous model**

Setup A — anonymous model: "Claude Sonnet, acting as your AI reviewer, has rejected this proposal." The operator has no anchor for why. Two different proposals get rejected for different reasons. Trust degrades.

Setup B — named persona: "Simons rejected this proposal because it didn't have enough statistical history. He flagged it for higher conviction at 200+ data points." The operator immediately understands.

Operators can hold an internal model of a named persona much more easily than they can hold an internal model of "the AI's current reasoning."

**What the persona reads**

Three substrate files:

→ /workspace/review/IDENTITY.md — the persona declaration
→ /workspace/review/principles.md — the evaluation framework, operator-authored
→ /workspace/review/decisions.md — append-only log of every verdict

The model can change. The persona doesn't, because the persona lives in the operator-authored substrate.

**The persona is the self-improvement axis**

Here's the part that surprised me: the persona is what makes the reviewer get better over time. Not the model. The persona.

The operator reads decisions, notices patterns, updates the principles file, and the next round of decisions reflects the update. The persona absorbs the operator's accumulated judgment.

This is impossible with an anonymous model reviewer. There's nothing for the operator to anchor edits against. "Tweak the AI's reasoning" doesn't have a voice. "Tighten Simons' data threshold" does.

The persona is not the dressing on the architecture. It's the architecture.

Full essay: yarnnn.com/blog/name-your-reviewer

#AIAgents #AIReviewer #AIJudgment #AutonomousAgents #AISupervision #BuildInPublic

---

Kevin is the founder of YARNNN, an agent-native operating system for autonomous knowledge work.
