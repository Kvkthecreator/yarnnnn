---
title: "Agent Protocol Stack — LinkedIn"
source: agent-protocol-stack-the-missing-layer
platform: linkedin
format: native-post
date: 2026-03-16
author: kvk
voice: kevin
status: ready
---

MCP connects agents to tools. A2A connects agents to each other. But no protocol exists for how agents transfer understanding.

That's the gap nobody's talking about.

I spent the last few weeks studying how the AI agent protocol stack is converging. MCP (Anthropic, 2024) standardized agent-to-tool communication. A2A (Google, now Linux Foundation) standardized agent-to-agent task handoff. IBM's ACP merged into A2A. In 18 months, we went from every framework being a walled garden to a credible path to interoperability.

But stack them up and you see what's missing.

When one agent hands work to another — say, "analyze Q4 revenue trends" — A2A gives you the task handoff: structured parameters, expected output, callback URL. What it doesn't give you is the understanding the first agent already accumulated. The client's revenue patterns, the anomalies flagged in Q3, the stakeholder's communication preferences.

Today's answer is to serialize context as text and stuff it into the next agent's prompt. That's lossy, unversioned, and not computable. The receiving agent reads it the way you'd read a stranger's notes — you get the words, but not the understanding behind them.

The result: agents that can coordinate but can't compound. Every handoff starts from near-zero. The system is interoperable at the protocol layer but amnesiac at the intelligence layer.

I think this is the most important unsolved problem in multi-agent AI right now. Not better models. Not better task routing. A structured, versioned way to transfer what an agent has learned — with provenance, confidence levels, and enough structure to be computable.

Wrote more about it on the yarnnn blog if you're interested.

What's the worst "context loss" you've seen in an AI handoff?

#AIAgents #MCP #A2A #AgentProtocol
