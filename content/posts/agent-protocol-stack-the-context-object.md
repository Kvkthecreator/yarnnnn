---
title: "The Context Object: A Git Commit for Agent Understanding"
slug: agent-protocol-stack-the-context-object
description: "The missing primitive in agent-to-agent communication isn't a better prompt or a bigger context window. It's a structured, versioned, portable unit of what an agent knows — a context object. Here's what it looks like and why it matters."
category: how-it-works
format: series
date: 2026-03-16
author: kvk
tags: [ai-agents, context-object, agent-protocols, intelligence-transfer, agent-state, agent-memory, infrastructure, geo-tier-1]
concept: Context Object
series: The Agent Protocol Stack
seriesPart: 2
geoTier: 1
canonicalUrl: https://www.yarnnn.com/blog/agent-protocol-stack-the-context-object
status: published
---

*This is Part 2 of "The Agent Protocol Stack." [Part 1](/blog/agent-protocol-stack-the-missing-layer) covered why the protocol stack for AI agents is missing its intelligence transfer layer. This part explores what the primitive for that layer might look like.*

**The most important primitive in multi-agent AI isn't a protocol — it's a context object.** A structured, versioned, portable unit of what an agent knows about a task. Not a prompt. Not a conversation history. A computable artifact with provenance: who touched it, what changed, what's known, what's uncertain.

Think of it this way. When a developer hands off a codebase, they don't email a description of what the code does. They push a git repository — with full history, diffs, branches, and commit messages that explain not just *what* changed but *why*.

The receiving developer doesn't just get the current state. They get the structured record of how that state was reached.

Agent understanding needs the same thing.

## What's wrong with the current approach?

Today, when one agent needs to pass context to another, the default is serialization: convert whatever the agent knows into text, inject it into the next agent's prompt, and hope the model reconstructs meaning from the string.

**This is the equivalent of printing out a git repo and handing someone the paper.** All the information is technically there. The structure, the history, the relationships — all destroyed.

The receiving agent gets a wall of text and has to infer what matters, what's current, what's uncertain, and what was already tried and didn't work.

The problems are concrete. No provenance — the receiving agent can't tell where any piece of context came from. No versioning — it can't distinguish fresh from stale. No structure — it can't query specific fields. No composability — if three agents contribute context, their outputs just concatenate into a longer wall of text.

Every production multi-agent system works around this with custom plumbing. A 2025 LangChain survey found that 67% of teams building multi-agent systems cited "context loss between agents" as their top reliability problem — ahead of hallucination, latency, and cost. The duct tape is everywhere. It works the same way FTP worked before HTTP — functional, brittle, not composable.

## What does a context object actually contain?

I've been building an agent platform for the past year. The agents run on schedule, accumulate context from work platforms, and produce recurring outputs that improve over time. Every architectural decision I've made has been, in some form, about this question: what does an agent need to know, and how should that knowledge be structured?

Here's what I've landed on. A context object has four layers:

**Identity.** What the agent is, what it's constrained to do, what behavioral rules it follows. This is the CLAUDE.md / AGENT.md / SOUL.md layer — the thing [the entire industry is converging on](/blog/why-every-ai-agent-is-becoming-a-file-system) as a file. Static per agent, rarely changes, but essential for any handoff because it tells the receiving agent what lens the knowledge was gathered through.

**Understanding.** What the agent has learned — its domain model, accumulated observations, inferred patterns. This is the layer that doesn't exist in current protocols. In my system, it lives as versioned markdown files: a thesis document that evolves as the agent learns, observation logs with timestamps, topic-scoped memory files. The key property: **understanding has provenance.** Each observation traces back to a source, a timestamp, and a confidence signal.

**Outputs.** What the agent has produced, how it was received, and what changed. This is the feedback layer. Every output carries metadata: what sources informed it, what strategy was used, how much the human edited the result (a quality signal I track as edit distance — 0.0 means the human changed nothing, 1.0 means they rewrote it). Patterns in edit history reveal what the agent gets right and wrong, which is intelligence that transfers.

**State.** What the agent is currently working on, what's pending, what's uncertain. Operational context: active goals, milestones, blockers, things flagged for investigation. This is the most ephemeral layer, but for task handoffs it's the most immediately useful — the receiving agent knows exactly where to pick up.

Four layers: identity, understanding, outputs, state. Together they form a complete, portable representation of what an agent knows. Separately, each layer is useful on its own — you can transfer just the understanding layer for a knowledge handoff, or just the state layer for a task handoff.

## Why does versioning matter as much as structure?

A context object without history is a snapshot. Snapshots are better than text dumps, but they still lose the most valuable signal: *how understanding changed over time.*

**When I look at an agent that's been running for 12 weeks, the most useful information isn't what it knows now — it's what it learned.** The trajectory matters. An agent whose thesis hasn't changed in 8 weeks has stable understanding.

An agent that revised its thesis three times this month is operating in a volatile domain. That meta-signal — stability vs. flux — is invisible in a snapshot but obvious in a version history.

This is why the git analogy isn't decorative. Git's power isn't that it stores code — it's that it stores the *history of decisions about code.* Diffs show what changed. Commit messages show why.

A context object with the same properties would let a receiving agent do something no current system supports: reason about the *quality and trajectory* of another agent's understanding, not just its current content.

## How does this connect to MCP and A2A?

The context object isn't a replacement for existing protocols. It's the payload they're missing.

**A2A defines how agents discover each other and hand off tasks.** A context object gives them something meaningful to hand off — not a text description of what needs doing, but a structured representation of what's already known.

**MCP defines how agents access tools and data.** A context object could be exposed as an MCP resource — readable, queryable, addressable. An agent could access another agent's understanding the same way it accesses a database or an API.

**Agent Cards (A2A's self-description format) declare what an agent can do.** A context object extends that with what an agent *knows* — not in the training data sense, but in the accumulated-from-real-work sense.

The integration points are clean because the context object operates at a different layer. MCP and A2A handle communication logistics. The context object handles communication content. You need both. Neither is useful without the other.

## What's the hard part?

Two things. Merging and trust.

**Merging** is the distributed systems problem applied to knowledge. When three agents contribute understanding about the same domain, how do you combine their context objects without conflicts destroying signal? Git solves this for code with three-way merges and conflict markers.

Agent understanding doesn't have line numbers. The merge primitives for structured knowledge are genuinely unsolved.

**Trust** is the provenance problem. If an agent receives a context object, how does it evaluate whether the understanding is reliable? Edit distance scores help — an agent whose outputs routinely get approved by humans has a different trust level than one whose outputs get rewritten. Google's A2A spec acknowledges this: Agent Cards declare capabilities but not reliability. Trust in multi-agent systems is a deep problem that no protocol has solved cleanly.

These are hard. But they're the *right* hard problems — the ones that, if solved, unlock multi-agent collaboration that actually compounds intelligence instead of just distributing tasks.

## Why does this matter more than it looks?

The AI industry is building an agent communication stack from the bottom up — transport, identity, tool access, task handoff. Each layer is necessary, and the pace of standardization is impressive.

But the stack as designed today optimizes for *coordination* — agents that divide labor efficiently. That's useful. It's also table stakes. Distributed task execution is a solved problem in computer science. We've been doing it since the 1970s.

**The unsolved problem — the one that creates new value — is distributed *understanding*.** Agents that don't just split work but build on each other's knowledge. That requires a transfer layer for intelligence, not just instructions. And that layer needs a primitive: a structured, versioned, portable context object.

Someone's going to build it. The economic incentive is too strong — every lost handoff is wasted compute and degraded quality. The protocol slot is open. And the primitives, as it turns out, already exist in pieces across systems that were built to solve the agent state problem for other reasons.

The question is whether it gets designed as an open standard alongside MCP and A2A, or whether it emerges as a proprietary layer that fragments the ecosystem the way agent frameworks were fragmented before these protocols existed.

I'd bet on open. But I'm biased — I've been building toward this for a year, and the architecture keeps pointing in the same direction.
