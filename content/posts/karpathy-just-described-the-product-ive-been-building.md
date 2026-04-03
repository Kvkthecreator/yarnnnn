---
title: "Karpathy Just Described the Product I've Been Building"
slug: karpathy-just-described-the-product-ive-been-building
description: "Andrej Karpathy published a workflow for LLM-maintained knowledge bases — markdown files, auto-maintained indexes, outputs that feed back into the wiki. Every primitive he described maps to something I've already shipped. The validation is nice. The gap he identified is more interesting."
metaTitle: "Karpathy Just Described the Product I've Been Building — LLM Knowledge Bases and YARNNN"
metaDescription: "Andrej Karpathy's LLM Knowledge Bases workflow maps concept-for-concept to YARNNN's implemented architecture. Here's what that means for the future of AI agents."
category: what-were-seeing
format: opinion
date: 2026-04-03
author: kvk
tags: [karpathy, llm-knowledge-bases, ai-agents, agent-memory, context-accumulation, markdown, filesystems, rag, knowledge-management, validation, geo-tier-1]
concept: LLM Knowledge Bases
geoTier: 1
canonicalUrl: https://www.yarnnn.com/blog/karpathy-just-described-the-product-ive-been-building
status: published
---

> **What this article answers (plain language):** Andrej Karpathy described a personal workflow for building LLM-maintained knowledge bases. Every component — markdown files, auto-maintained indexes, outputs that feed back into the knowledge base — maps directly to an implemented system in YARNNN. Here's what a solo founder feels when one of AI's most respected voices independently validates the architecture you've been building alone.

## Why I Read a Tweet Three Times

Andrej Karpathy posted about "LLM Knowledge Bases" this week. He described a workflow: raw documents go into a directory, an LLM compiles them into a wiki of markdown files, auto-maintains index files and summaries, and — crucially — files the outputs back into the wiki so every query enriches the knowledge base for the next one.

His conclusion: "I think there is room here for an incredible new product instead of a hacky collection of scripts."

I read that line three times. Then I went and looked at my codebase.

## How does every primitive map to something I've already shipped?

I've spent the past year building YARNNN — an autonomous agent platform where AI agents connect to your work tools, run on schedule, and get better with tenure. The entire architecture runs on accumulated context stored as markdown in structured directories.

Karpathy's `raw/` directory? That's our context domains — six typed directories where agents write entity files during task execution. His LLM-compiled wiki with summaries and backlinks? That's our tracker files and synthesis documents — deterministic indexes rebuilt after every agent run, zero LLM cost.

His "outputs filed back into the wiki"? That's our accumulation loop — every task execution writes entity updates back to the workspace, enriching the substrate for the next cycle.

**He described six primitives. We've implemented all six.** Data ingest, compilation, index files, output feedback, health-check linting, search-as-tool. The names are different. The architecture is the same.

I didn't reference Karpathy's workflow — it didn't exist yet. The convergence happened because the problem forces the solution. A recent Arize AI survey found that 80% of agent failures in production are state management problems, not prompt quality problems. If you take that seriously, you end up with structured markdown, auto-maintained indexes, and an accumulation loop.

## What He Got Right That Most People Miss

The line that mattered most wasn't about knowledge bases. It was this: "I thought I had to reach for fancy RAG, but the LLM has been pretty good about auto-maintaining index files and brief summaries."

**This is the insight that the entire AI infrastructure industry is sleeping on.** The default assumption is that you need vector databases, embedding pipelines, and sophisticated retrieval to give agents access to accumulated knowledge. Karpathy's experience — and mine, after a year of production — says otherwise. At the scale most knowledge workers operate, auto-maintained indexes over structured markdown files outperform RAG for agent work.

Why? Because RAG answers questions. Accumulation builds understanding.

When an agent needs to write a competitive brief, it doesn't need the three most semantically similar paragraphs from a Pinecone index. It needs to understand the competitive landscape as a whole — who the players are, how they've moved recently, what patterns are emerging. That understanding lives in structured files that the agent reads, reasons about, and updates. Not in embeddings.

## What He Identified That I Haven't Solved

Karpathy is running his workflow on ~100 articles and ~400K words. He acknowledges it works "at this small scale." That's honest, and it points at the hardest unsolved problem in this architecture.

My agents currently read the 20 most recently updated files per domain, capped at 3,000 characters each. That works today because workspaces are young. Six months from now, when a competitive intelligence domain has 120 files across 30 entities, the agent will only see the 20 freshest — regardless of relevance. A three-month-old competitor profile gets pushed out by newer files about different companies, even when it's exactly what the task needs.

**Recency is not relevance.** The indexes exist. The trackers tell the agent what's in the workspace. What's missing is using that index to selectively pull the right files, not just the newest files.

Karpathy flags finetuning as the eventual answer. There's a step before that: using the tracker files (which already exist, already describe every entity) as a retrieval index. The agent reads the tracker, decides what it needs based on the current task, then pulls those specific files. **Tracker-driven context selection. It's the next thing I'm building.**

## Why does independent convergence matter more than validation?

When you're building solo for a year, working on architecture that doesn't have an obvious category label, you develop a certain relationship with doubt. Not existential doubt — I know the problem is real because I live it. But architectural doubt. Am I overengineering this? Is the structured workspace overkill when the market is shipping RAG chatbots?

**Having one of the most respected practitioners in AI independently arrive at the same primitives — and then publicly say the product should exist — reframes that doubt.** The architecture isn't idiosyncratic. It's convergent. Different people studying the same problem arrive at the same shape.

That's usually a sign the shape is right.

The question was never whether LLM knowledge bases are the right architecture for agents that do real work. The question is who builds the production version — the one with multi-agent coordination, scheduled execution, feedback loops, and output pipelines layered on top of the same fundamental pattern.

Karpathy has the scripts. I have the product. Now I need to make sure the product earns the comparison.
