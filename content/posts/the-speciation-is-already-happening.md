---
title: "The Speciation Is Already Happening"
slug: the-speciation-is-already-happening
description: "LLMs are monolithic today — one model tries to do everything. But the jagged edges are showing. The domains nobody benchmarks are exactly where models fail hardest, and that's where speciation begins."
category: opinion
format: reflection
date: 2026-03-27
author: kvk
tags: [ai-agents, llm-speciation, jagged-frontier, ai-evaluation, model-specialization, agent-architecture, context-accumulation, autonomous-agents, geo-tier-1]
metaDescription: "LLMs are monolithic — one model for every task. But AI's jagged frontier means models fail hardest in domains nobody evaluates. The future isn't better monoliths. It's speciation — and persistent agents are the selection pressure."
concept: Accumulated Intelligence
geoTier: 1
canonicalUrl: https://www.yarnnn.com/blog/the-speciation-is-already-happening
status: published
---

**LLMs are monolithic today — one model tries to write your code, plan your wedding, diagnose your rash, and draft your board memo.** The same weights, the same training, the same architecture. We talk about GPT-5 and Claude 4 like they're the finish line. They're not. They're the last generation before the split.

The split I mean is speciation. Not fine-tuning. Not prompting tricks. A genuine divergence where different AI systems evolve different capabilities because they're under different selection pressures. And the pressure that matters most isn't benchmarks — it's the work nobody's measuring.

## Why do jagged edges matter more than benchmarks?

Ethan Mollick coined the term "jagged frontier" to describe how AI capabilities aren't a clean line. A model that writes beautiful prose might fail at basic arithmetic. One that crushes coding benchmarks might produce tone-deaf client communication. **The frontier isn't advancing evenly — it's spiking in some domains and cratering in others.**

Here's what I think the industry is missing: the domains where models fail hardest are the ones nobody evaluates. There's no HumanEval for "did this weekly report actually help the VP make a decision?" No MMLU subscore for "does this agent understand that your client hates bullet points?" The jagged edges aren't random. They're systematic — they appear precisely where standardized evaluation doesn't reach.

This matters because the entire LLM improvement cycle is benchmark-driven. Models get better at what gets measured. Code generation improves because SWE-bench exists. Math improves because MATH and GSM8K exist. But the vast middle of knowledge work — the recurring, contextual, judgment-heavy tasks that most professionals actually spend their days on — has no benchmark. So it has no selection pressure. So it doesn't improve.

## What does speciation look like in practice?

I think we're about to see AI systems diverge along three axes.

**Axis 1: Session vs. tenure.** Some AI will stay session-based — brilliant per-interaction, stateless by design. ChatGPT, Claude, Gemini. They'll keep getting better at the sharp spikes of the jagged frontier. Code, math, reasoning, creative writing. The evaluated domains.

Other AI will develop tenure — persistent systems that accumulate context over weeks and months. These won't compete on benchmarks because benchmarks are single-session by definition. They'll compete on output quality in domains where context compounds. Your agent's 90th run on your weekly client briefing will be qualitatively different from its first, not because the model improved, but because the context did.

**Axis 2: General vs. domain-native.** The monolithic model tries to be equally good at everything. But a model that's been accumulating context from your Slack, your Notion, your meeting notes for three months isn't general anymore. It's become domain-native — not through training, but through context. It knows your acronyms, your stakeholders, your communication preferences. That's a form of specialization that no amount of RLHF produces.

**Axis 3: Evaluated vs. unevaluated.** The biggest split. AI systems optimized for benchmark performance will keep winning benchmarks. AI systems optimized for unevaluated domains — the messy, contextual, judgment-heavy work — will have to find different fitness signals. User feedback. Edit distance over time. Approval rates. Whether the human actually used the output or rewrote it from scratch.

**This is where the speciation thesis connects to what we're building at YARNNN.** Our agents live in the unevaluated domain. There's no benchmark for "did this research briefing actually save the consultant two hours?" The only fitness signal is whether the output gets better over time — and that requires accumulated context, feedback loops, and persistent identity.

## Why won't better monoliths solve this?

The counterargument is obvious: just make the monolith smarter. GPT-5 will be better at everything, including the jagged edges. Eventually the frontier smooths out.

I don't think it will. Here's why: **the jagged edges in knowledge work aren't capability gaps — they're context gaps.** A model can be infinitely capable and still produce generic output if it doesn't know your domain. The problem isn't that Claude can't write a good client update. It's that Claude doesn't know your clients.

No amount of model improvement fixes that. It's not a training problem. It's a runtime problem. The context has to come from somewhere — either from the user re-explaining everything every session, or from a persistent system that accumulates it over time.

The monolith gets sharper spikes. The persistent agent fills in the valleys. Different selection pressures. Different evolutionary paths. Speciation.

I think we'll look back at 2025-2026 as the moment the split became visible. The last years of the monolithic era — when we still believed one model would do everything for everyone. The future is more interesting than that. It's specialized, contextual, and accumulated. And the domains that matter most are the ones nobody's benchmarking yet.

*Kevin Kim is the founder of [YARNNN](https://www.yarnnn.com), a platform for developmental AI agents that accumulate context and improve with tenure.*
