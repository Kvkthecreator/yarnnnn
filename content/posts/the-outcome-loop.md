---
title: "The Outcome Loop: How An AI Reviewer Learns From Real P&L"
slug: the-outcome-loop
description: "An autonomous AI is only as good as its ability to learn from outcomes. The outcome loop — proposed action, verdict, execution, real-world result, calibration — is the closed circuit that makes AI judgment improve over time."
metaTitle: "AI Outcome Loop: How Autonomous Agents Learn From Real Results"
metaDescription: "The outcome loop is the closed circuit that connects AI verdicts to real-world results and back to AI calibration. Without it, autonomous AI plateaus. With it, the system improves over time on the metrics that matter."
category: how-it-works
date: 2026-04-11
author: yarnnn
tags: [ai-outcomes, ai-feedback-loop, autonomous-agents, ai-learning, money-truth, ai-reviewer, geo-tier-2]
concept: Money-Truth Substrate
series: Money-Truth
seriesPart: 2
geoTier: 2
canonicalUrl: https://www.yarnnn.com/blog/the-outcome-loop
status: published
---

> **What this article answers (plain language):** The outcome loop is the closed circuit that connects AI proposals to real-world results and back to AI calibration. Five steps: propose, judge, execute, observe, calibrate. Without it, autonomous AI plateaus. With it, AI judgment improves on the metrics that matter.

**Autonomous AI improves only as much as its outcome loop is closed.** The loop has five steps: an agent proposes an action, the reviewer judges it, the action executes, the real-world result gets observed, and the reviewer's calibration adjusts. Each step is a piece of architecture. Skipping any of them produces autonomous AI that can fire actions but can't learn from them. Closing all five produces autonomous AI that gets meaningfully better over time, on the metrics that actually matter.

This is a follow-on to [Money-Truth As A File](/blog/money-truth-as-a-file-not-a-dashboard). That post argued performance has to live in the substrate; this one walks through the full loop that performance enables.

## The Five Steps

The closed outcome loop, in order:

**1. Propose.** An agent (the trading signal generator, the campaign creator, the email drafter) produces an action it thinks should fire. The proposal is structured: what action, what reasoning, what expected outcome, what confidence. Proposals are written to substrate, not silently consumed by the next step.

**2. Judge.** The reviewer agent reads the proposal, the operator's mandate and principles, the recent performance from `_performance.md`, the relevant context. The reviewer emits a verdict: approve, reject, or defer. The verdict is logged with reasoning. Judgment happens in a structured way that the operator can audit.

**3. Execute.** Approved actions fire. The trading order goes to the broker. The campaign launches. The email sends. The action produces a real-world consequence. The execution is logged with attribution to the proposal and the verdict.

**4. Observe.** The system reads the real-world outcome from the platform. The trade closed at $X. The campaign generated Y conversions. The email got Z opens and W clicks. The outcome data flows back into the substrate as money-truth, attributed to the originating action.

**5. Calibrate.** The reviewer reads recent outcomes when judging future proposals. Outcomes that suggest the principles are too aggressive, too conservative, or pattern-mismatched produce signals the reviewer can act on. The reviewer can flag for operator attention; the operator can update principles. The next round of judgments reflects the calibration.

Loop closed. The next proposal benefits from what the last action taught the system.

## What Each Step Has To Look Like

The five steps sound abstract; they have specific architectural requirements:

**Propose** has to produce structured proposals, not in-line decisions. If an agent decides to fire an action and just fires it, there's no proposal record for the reviewer to gate. The discipline: any consequential action goes through `propose_action` first, never direct execution.

**Judge** has to read from operator-authored substrate, not from session context. The reviewer reads `principles.md`, `MANDATE.md`, `_performance.md`. The reviewer doesn't make up judgment criteria — it applies criteria the operator wrote. Without this, verdicts are inconsistent and uncalibratable.

**Execute** has to record attribution. Every executed action is linked back to the proposal and the verdict that approved it. Without this attribution, outcome data can't be traced back to the decision that produced it, and calibration breaks.

**Observe** has to be deterministic and zero-LLM. The outcome reconciler is platform-API plumbing — it pulls executed-action data from the source-of-truth system (broker, payments processor, analytics platform) and writes structured outcome data to the substrate. No model in this loop. The data has to be reliable.

**Calibrate** has to flow through the reviewer's reading of substrate. The reviewer reads `_performance.md` on every verdict; the reviewer can write decisions that reference recent outcomes; the operator can audit decisions and edit principles. Calibration is mediated by the reviewer-as-substrate-reader, not by a separate ML retraining loop.

Each step has its own architectural commitment. Skipping any of them — letting agents execute without proposals, letting the reviewer reason without operator-authored substrate, letting outcomes go unattributed — breaks the loop.

## What Makes This Different From RLHF

The outcome loop sounds adjacent to reinforcement learning from human feedback, but the architecture is different in important ways:

**RLHF retrains the model.** The outcome loop adjusts the substrate the model reads.

**RLHF requires labeled feedback at training time.** The outcome loop runs continuously at inference time, reading recent outcomes from the substrate.

**RLHF produces a new model checkpoint.** The outcome loop produces updated principles and calibration in the substrate; the model is unchanged.

**RLHF is opaque to the operator.** The outcome loop is fully legible — the operator can read the principles, the decisions, the outcomes, and trace the calibration trail.

**RLHF is centralized at the model lab.** The outcome loop is per-workspace and per-operator.

The two patterns aren't competing — they operate at different layers. RLHF makes the underlying model better at language and reasoning. The outcome loop makes the application's behavior better at the specific operator's specific operation. **The operator gets the benefit of both.**

## Why The Loop Is Mostly Missing Today

Most AI products don't have the outcome loop because they don't ship the architectural pieces:

**Most products execute consequential actions in-line, not via proposals.** The agent decides, the agent fires. There's no gate, no record, no review.

**Most products don't have an operator-authored principles file.** The model uses prompt-engineered judgment that varies session-to-session. There's nothing to calibrate against.

**Most products don't observe outcomes structurally.** Performance data lives in dashboards (see [Money-Truth As A File](/blog/money-truth-as-a-file-not-a-dashboard)). The AI doesn't read it.

**Most products don't have a reviewer that reads performance.** Even when performance is available, the reviewer's behavior is fixed at deploy time, not adjusted based on recent outcomes.

Each missing piece is fixable but requires architectural commitment, not feature work. The reason the loop is missing isn't lack of demand — it's that the prerequisite architecture (proposals, principles, money-truth, reviewer) hasn't been built. **The outcome loop is the consequence of having the underlying architecture, not a separate feature.**

## What This Looks Like For An Operator

A concrete example: an operator runs an autonomous trading operation. The signal generator proposes "long AAPL at $185, target $195, stop $180." The reviewer reads the proposal, the operator's principles ("require 2:1 reward-to-risk minimum, max 5% position size, no overnight holds during earnings week"), the recent performance ("3 wins last week, 1 loss, all within target volatility"). The reviewer approves.

The order executes via the broker. The trade closes Friday at $192 (partial win). The outcome reconciler runs Saturday morning, reads the broker's execution history, updates `_performance.md` with the new data point.

Monday morning, the signal generator proposes another trade. The reviewer reads the updated performance ("4 of 5 last week, average win 0.8R, average loss 0.6R, on-target volatility"). The principles still apply, but the reviewer's prompt context now includes the empirical update. If recent performance suggested the principles were too aggressive, the reviewer would flag this in its decision log; the operator could read the log and tighten the conviction threshold.

The operator's accumulated judgment encoded in principles, plus the reviewer's continuous reading of money-truth, produces autonomous behavior that improves over time without retraining anything. **The model is constant. The operation gets better.**

## Why This Pattern Will Spread

Operators trying to deploy autonomous AI will eventually all need this loop. The products that ship it have the property the operators want (autonomous behavior that learns from outcomes); the products that don't ship it have the property operators don't want (autonomous behavior that fires actions blindly).

The loop is non-trivial to build but each piece exists in isolation in current products. The synthesis — proposal architecture, reviewer agent with operator-authored substrate, money-truth reconciliation, calibration flow — is the work. Once it's built, the product crosses a quality threshold that's recognizable to operators immediately.

If you're building autonomous AI, build the outcome loop. **It's the difference between AI that fires actions and AI that fires actions and learns from them.** The first is impressive briefly. The second is what operators stay with.

## Key Takeaways

- The outcome loop has five steps: propose, judge, execute, observe, calibrate.
- Each step requires specific architectural commitments — proposals, operator-authored principles, attributed execution, deterministic outcome reconciliation, reviewer-mediated calibration.
- It's adjacent to RLHF but operates at a different layer (substrate, not model weights).
- Most current products are missing multiple steps because the prerequisite architecture isn't built.
- Building the loop is the difference between blindly autonomous AI and autonomous AI that learns from results.
- For why money-truth has to live in the substrate, read [Money-Truth As A File, Not A Dashboard](/blog/money-truth-as-a-file-not-a-dashboard). For why the reviewer is the load-bearing piece, read [Name Your Reviewer](/blog/name-your-reviewer).
