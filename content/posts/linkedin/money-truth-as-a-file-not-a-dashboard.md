# Money-Truth As A File, Not A Dashboard

Most AI products track performance in a dashboard the operator looks at. The dashboard is for humans. The AI doesn't read it.

This is fine for "AI assistant" use cases where humans make all the consequential decisions. It's catastrophic for autonomous AI operations, because it severs the loop between outcomes and AI behavior.

The fix: make performance a file the AI reads. Money-truth lives in the substrate, attributed and auditable. The reviewer agent reads it on every verdict.

**The two architectures**

Architecture A — dashboard. Performance metrics get computed and rendered in a UI panel. The operator sees them. The AI doesn't see them at all.

Architecture B — substrate file. Performance gets written to a file in the workspace (`/workspace/context/{domain}/_performance.md`). YAML frontmatter (rolling P&L, win rate, processed-event keys for idempotency) plus narrative body (headline numbers, action breakdown, recent wins/losses). Every actor that needs performance reads the file.

In architecture A, performance is presentation. In architecture B, performance is substrate. The difference looks small in the diagram and is enormous in the behavior.

**Why dashboards break autonomy**

In architecture A, the autonomous AI has no access to its own performance history. The reviewer agent emits a verdict based on operator principles, but it can't reason against "we lost three trades in a row last week" because the loss data lives in a chart the AI doesn't read.

Predictable failure modes:

→ Same-mistake repetition — the AI keeps approving the same kind of proposal even after a string of bad outcomes
→ Drift goes unnoticed — only signal is in metrics the AI doesn't read
→ Reviewer calibration is operator-mediated — only way to communicate "be more conservative" is operator edits to the principles file

Dashboards make humans informed. They don't make AI informed.

**What substrate enables**

→ Performance-aware verdicts. The reviewer reads "we lost 4 of last 6 paper trades, drawdown 2.1%" before deciding on the next proposal.
→ Calibration loop closure. The reviewer can flag "recent losses suggest the conviction threshold should rise."
→ Cross-actor coherence. The cockpit shows the same _performance.md the reviewer reads.
→ Audit completeness. Performance is attributed (who computed it, when, from what source data) and version-controlled.

**Why "money-truth" specifically**

Most AI performance metrics aren't money-truth. "User engagement increased" is squishy. "Model accuracy improved" is internal.

Money-truth is external, measurable, consequence-bearing. The trade either made money or lost money. The campaign either generated revenue or didn't. The sale either closed or didn't.

AI that can be held accountable to money-truth is AI that can actually improve.

Full essay: yarnnn.com/blog/money-truth-as-a-file-not-a-dashboard

#AIAgents #AutonomousAgents #AIPerformance #AIFeedback #AIAccountability

---

YARNNN is an agent-native operating system for autonomous knowledge work.
