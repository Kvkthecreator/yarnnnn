---
title: "AI Agent Protocols Are Converging. The Most Important Layer Is Still Missing."
slug: agent-protocol-stack-the-missing-layer
description: "MCP standardizes how agents talk to tools. A2A standardizes how agents talk to each other. But no protocol exists for how agents transfer understanding."
platform: x-article
date: 2026-03-16
author: kvk
voice: kevin
source: agent-protocol-stack-the-missing-layer
status: ready
---

*This is Part 1 of "The Agent Protocol Stack" — a two-part series on the converging standards for agent communication, and the layer nobody's building yet.*

The protocol stack for AI agents is missing its most important layer. MCP handles agent-to-tool communication. A2A handles agent-to-agent task handoff. But neither solves the harder problem: how does one agent transfer what it understands — not just what it's been told — to another agent?

I started thinking about this after studying a GitHub repo full of SKILL.md files. These are structured markdown documents that describe capabilities to Claude Code and similar agent tools — essentially instruction manuals that get injected into prompts at runtime. They work. PM frameworks, writing guides, domain expertise, all packaged as files an agent can read before doing a task.

But the more I looked at them, the more I saw the same pattern I've been watching for a year: a transitional primitive. Something that solves a real problem today but carries the obvious seeds of its own obsolescence.

## Why is SKILL.md transitional?

SKILL.md moves the prompting problem up one abstraction level without solving it. Instead of a human writing a prompt, a human writes a markdown file that gets prompted. The capability description is still authored by a person, still static, still unable to adapt to what the receiving agent actually needs in a given context.

This is exactly how web pages worked before search engines. In the early web, if you wanted someone to find your content, you wrote a description of it and submitted it to a directory. Yahoo maintained the taxonomy. Humans curated the listings.

It worked — until it didn't, because the web grew faster than any human taxonomy could track.

SKILL.md has the same structural limitation. It requires a human to anticipate what an agent will need to know, write it down in advance, and maintain it as capabilities evolve. That scales fine for dozens of skills. It breaks at thousands.

The question isn't whether SKILL.md works — it does. The question is what replaces it when the number of agents and capabilities outgrows human curation. And that question leads somewhere more interesting than a better file format.

## What does the current protocol stack actually look like?

The industry moved fast here. Three standards emerged in roughly 18 months, and they're converging into a coherent stack.

MCP (Anthropic, 2024) standardizes agent-to-tool communication. How an agent discovers and calls external data sources, APIs, and resources. Think of it as USB-C for AI — a universal connector between an agent and the things it needs to interact with. Widely adopted. The plumbing layer.

A2A (Google, April 2025, now Linux Foundation) standardizes agent-to-agent communication. How agents discover each other, declare capabilities via Agent Cards (lightweight JSON self-descriptions), hand off tasks, and manage task lifecycle over HTTP/SSE/JSON-RPC. IBM's ACP protocol merged into A2A under Linux Foundation governance. The handshake layer.

MCP and A2A are designed to complement each other, not compete. MCP handles the vertical connection (agent to tool). A2A handles the horizontal connection (agent to agent). Together they give you a world where agents can find each other, describe what they do, pass tasks back and forth, and access external data — all through open standards.

That's a real achievement. Two years ago, none of this existed. Every agent framework was a walled garden with proprietary communication patterns. Now there's a credible path to interoperability.

But stack them up and you see the gap.

## Where's the understanding layer?

Here's the stack as it exists today:

Physical transport — settled (HTTP, SSE, JSON-RPC).
Agent identity and handshake — converging (A2A Agent Cards, capability discovery).
Tool and data access — converging (MCP resources, tool definitions).
Skill and capability description — transitional (SKILL.md, Agent Cards, prompt injection).
Intelligence transfer — open. Nothing here.

The first three layers solve logistics — how to connect, how to find each other, how to pass tasks and data. These are necessary, and the fact that they're converging on open standards is good for the ecosystem.

But logistics isn't the hard problem. The hard problem is: when one agent hands work to another, how does the receiving agent get the understanding that the sending agent accumulated?

Today the answer is: dump it into a prompt. Serialize whatever context seems relevant as text, stuff it into the next agent's input, and hope the model reconstructs the intent.

This is lossy, unversioned, and not computable. The receiving agent can read it the way you'd read a stranger's notes — you get the words, but you don't get the understanding behind them.

## Why is this distinct from what A2A solves?

A2A handles task handoff. Agent A says "analyze Q4 revenue trends" and passes it to Agent B with structured parameters, expected output format, and a callback URL.

That's valuable. But it's a work order, not a transfer of understanding.

Intelligence transfer would pass the structured context that makes the work meaningful. Not just "analyze Q4 revenue" but: here's what Agent A already knows about the client's revenue patterns, here are the anomalies it flagged in Q3, here's the stakeholder's communication style and what they care about, here's the confidence level on each data point, and here's what's uncertain and needs investigation.

That's not a task spec. That's a transfer of accumulated understanding — with provenance, versioning, and enough structure that the receiving agent can reason over it, not just read it.

The distinction matters because without intelligence transfer, every agent handoff starts from near-zero. Agent B has to rebuild context that Agent A already had. Multiply that across a network of collaborating agents and you get a system that's interoperable at the protocol layer but amnesiac at the intelligence layer. The agents can talk to each other. They just can't think together.

## What would an intelligence transfer layer need?

I don't have a spec. Nobody does — that's the point. But the requirements are starting to come into focus:

Structured, not serialized. The context object can't be a text dump. It needs schema — fields a receiving agent can query, filter, and reason over programmatically. What's known vs. uncertain. What's observed vs. inferred. What's fresh vs. stale.

Versioned, not snapshot. Understanding evolves. A transfer layer needs to convey not just current state but how that state was reached — what changed, what was revised, what was learned from feedback. Think git commits, not file copies.

Portable across agent architectures. The context object can't assume the receiving agent uses the same model, the same prompting strategy, or the same memory architecture. It needs to be legible to any sufficiently capable agent, regardless of implementation.

Composable. Multiple agents contributing to the same task need to merge their understanding without conflicts destroying signal. This is the merge problem from distributed systems, applied to knowledge.

These aren't exotic requirements. They're the same properties that made HTTP work for documents (structured, addressable, cacheable, composable) and git work for code (versioned, diffable, mergeable, portable). The intelligence transfer layer needs the same kind of design discipline applied to agent understanding.

## Why does this matter now?

The window is narrow. MCP and A2A are converging fast. The protocol stack is solidifying. Whatever fills the intelligence transfer layer needs to be designed alongside these standards, not bolted on after they've calcified.

And the economic case is straightforward. Every time an agent handoff loses context, someone — a human or another agent — has to rebuild it. That's wasted compute, wasted time, and degraded output quality. An intelligence transfer protocol that preserves even 50% of accumulated context across handoffs would be transformative for multi-agent systems.

The SKILL.md files I started with will keep working for a while. So will prompt injection, context window stuffing, and all the other duct-tape solutions we use today to move understanding between agents. But they're all transitional. The question is whether someone builds the real layer before the stack solidifies without it.

*In Part 2: What the primitive for intelligence transfer might actually look like — and why the answer might be closer to a git commit than a database query.*

---

*Originally published at [yarnnn.com/blog/agent-protocol-stack-the-missing-layer](https://www.yarnnn.com/blog/agent-protocol-stack-the-missing-layer)*
