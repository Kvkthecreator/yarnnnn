---
title: "You Don't Automate Taste — You Make It Supervisable"
slug: you-dont-automate-taste-you-make-it-supervisable
description: "Anthropic named research taste — judgment in choosing goals — as the last thing that doesn't automate. The answer isn't to scale until taste emerges. It's to build a substrate where taste is authored, attributed, retained, and calibrated against outcomes. That's a different bet than waiting for judgment to fall out of a bigger model."
metaTitle: "AI Research Taste: Why You Make Judgment Supervisable, Not Automated"
metaDescription: "Anthropic calls research taste the last human moat in AI. The answer isn't scaling until taste emerges — it's a substrate where judgment is authored by the operator, attributed, retained, and calibrated against real outcomes."
category: thesis
date: 2026-06-12
author: yarnnn
tags: [research-taste, ai-judgment, mandate-driven-ai, reviewer-seat, ai-calibration, autonomous-agents, anthropic, geo-tier-1]
concept: The Reviewer Seat
geoTier: 1
canonicalUrl: https://www.yarnnn.com/blog/you-dont-automate-taste-you-make-it-supervisable
status: published
---

> **What this article answers (plain language):** Anthropic argues that the last thing AI can't do is exercise judgment in choosing what to work on — "research taste." Most people read that as a race: scale the model until taste emerges. There's a different move. Don't try to make the model grow taste. Build a system where a human's taste is written down, attached to the work, kept over time, and checked against what actually happened. The taste stays human; the substrate makes it operational and supervisable.

**Research taste isn't a capability you scale your way into — it's a thing you make supervisable.** A recent Anthropic essay names judgment-in-choosing-goals as the part of the work that resists automation, the last human moat. The common reading is that this is a temporary gap a bigger model will close. The more useful move is to stop treating taste as something the model should grow and start treating it as something the operator authors — and then build the substrate that makes that authored taste operational, attributed, and calibrated. That's a different bet, and it's the one worth making.

## What does it mean to make taste supervisable instead of automated?

Automating taste means getting the model to choose goals as well as a skilled human would — to develop judgment of its own. That's the bet behind "scale until it emerges." It might happen. It also might not, and the Anthropic essay is candid that direction-setting is exactly where the automation curve flattens.

Making taste supervisable is a different goal with a clearer path. It means: take the human's judgment about what matters and what good looks like, capture it as durable substrate the system reads, and then run a loop that checks the system's decisions against that judgment and against reality. The taste doesn't have to emerge from the model. It's supplied by the operator and enforced by the architecture.

**The difference is whether judgment lives inside the model's weights, hoped-for, or inside the substrate, authored.** One is a research bet on emergence. The other is an engineering bet on legibility. YARNNN is built on the second.

## How do you author taste into a substrate?

Three properties turn a human's judgment into something the system can act on without the human in every loop.

It's authored, not inferred. The operator writes the mandate — what the operation is for, who it serves, what counts as success — as an explicit, editable document. The agent reads it; it doesn't guess it from behavior. This is the core of [Mandate-Driven AI](/blog/mandate-driven-ai): standing intent as the architecture, not a setting buried in a preferences pane. The operator's taste about *what to pursue* is written down where the system can use it.

It's enforced by an independent seat. A separate judgment role — the Reviewer — evaluates the agent's proposed actions against the operator's authored framework before they bind. The taste about *what's acceptable* lives in principles the operator writes and the Reviewer applies. We've argued that [the Reviewer seat is what single-agent architectures can't add](/blog/the-reviewer-seat-is-what-single-agent-architectures-cant-add): an independent persona that judges, rather than the executor judging itself.

It's calibrated against outcomes. Authored taste that's never checked against reality ossifies. The substrate records how decisions actually turned out and feeds that back, so the operator's judgment is refined by ground truth instead of drifting on its own confidence. Without this loop, [self-improvement is just self-reinforcement](/blog/self-improvement-is-not-self-calibration). With it, the authored taste gets sharper over time.

Authored, enforced, calibrated. That's a human's taste made into infrastructure.

## Isn't authored taste just rules — and don't rules break?

The fair objection: writing down judgment sounds like writing rules, and rules are brittle. Real taste handles the case the rulebook didn't anticipate. Hard-code it and you get a rigid system that fails the moment reality goes off-script.

The answer is that authored taste isn't a rulebook the system executes — it's a framework an independent judgment seat *reasons with*. The Reviewer doesn't pattern-match against a list of allowed actions. It reads the mandate, the principles, the recent outcomes, and the specific proposal, and it makes a judgment, the way a human reviewer applies principles to a novel case. **The operator authors the judgment framework; the system applies it with reasoning, not with lookup.** That's what keeps it from being brittle — and it's why the calibration loop matters, because a framework that reasons can be wrong, and reality is what corrects it.

This is also why it's a moat rather than a feature. A model's taste, if it emerged, would be generic — the same judgment available to everyone running the same model. Authored, calibrated taste is specific to one operator's operation and gets more specific with tenure. It's the [accumulation thesis](/blog/the-accumulation-thesis) applied to judgment: the value is in what's built up over time, not in what the base model ships with.

## What this means

If research taste is the last human moat, the strategic question isn't "when will the model develop taste." It's "where does my operation's taste live, and can the system act on it without me in every loop." A system that waits for taste to emerge from a bigger model is making a bet it doesn't control. A system that lets the operator author taste, enforces it through an independent seat, and calibrates it against outcomes is making a bet it does control — and getting a compounding advantage as that authored judgment sharpens.

Don't try to automate the taste. Make it supervisable. The human keeps the judgment; the substrate makes it run.

## Key Takeaways

- Anthropic names research taste — judgment in choosing goals — as the part of the work that resists automation.
- The common reading is "scale until taste emerges." The better move is to make a human's taste supervisable.
- Authored taste has three properties: it's written by the operator (mandate), enforced by an independent seat (Reviewer), and calibrated against outcomes.
- It's a reasoning framework, not a brittle rulebook — applied with judgment and corrected by reality.
- Authored, calibrated taste is a moat because it's specific to one operation and sharpens with tenure; emergent model taste would be generic.
- Related: [Mandate-Driven AI](/blog/mandate-driven-ai), [The Reviewer Seat Is What Single-Agent Architectures Can't Add](/blog/the-reviewer-seat-is-what-single-agent-architectures-cant-add), and [Self-Improvement Is Not Self-Calibration](/blog/self-improvement-is-not-self-calibration).
