---
title: "Agent Protocol Stack Thread — Part 1"
source: agent-protocol-stack-the-missing-layer
platform: twitter
format: thread
date: 2026-03-16
author: kvk
status: ready
---

**Tweet 1 (Hook):**
MCP connects agents to tools. A2A connects agents to each other. But no protocol exists for how agents transfer *understanding*.

That's the most important layer in the stack. And nobody's building it.

🧵

**Tweet 2 (SKILL.md hook):**
I started thinking about this after studying a repo full of SKILL.md files — markdown docs that describe capabilities to Claude Code.

They work. But they're transitional. A human writes instructions that get injected into a prompt. That doesn't scale past hundreds of skills.

**Tweet 3 (Protocol landscape):**
The protocol stack is converging fast:

→ MCP (Anthropic): agent-to-tool
→ A2A (Google → Linux Foundation): agent-to-agent
→ ACP (IBM): merged into A2A

Transport is settled. Identity is converging. Tool access is converging.

But stack them up and you see the gap.

**Tweet 4 (The gap):**
When one agent hands work to another, how does the receiving agent get the *understanding* the sending agent accumulated?

Today's answer: serialize it as text, stuff it into a prompt, hope the model reconstructs the intent.

That's lossy, unversioned, and not computable.

**Tweet 5 (Why A2A doesn't solve it):**
A2A handles task handoff — "analyze Q4 revenue trends" with structured parameters and a callback URL.

That's a work order, not a transfer of understanding.

Intelligence transfer would pass what the agent already *knows* — with provenance, confidence levels, and version history.

**Tweet 6 (The punchline):**
Without intelligence transfer, every agent handoff starts from near-zero.

The agents can talk to each other. They just can't think together.

The system is interoperable at the protocol layer but amnesiac at the intelligence layer.

**Tweet 7 (What's needed):**
The requirements are becoming clear:

→ Structured, not serialized (queryable fields, not text dumps)
→ Versioned, not snapshot (how understanding changed over time)
→ Portable across architectures
→ Composable across agents

Same properties that made HTTP work for docs and git work for code.

**Tweet 8 (Close):**
MCP and A2A are converging fast. The protocol stack is solidifying. Whatever fills this intelligence transfer layer needs to be designed alongside them, not bolted on after.

Wrote more about this: yarnnn.com/blog/agent-protocol-stack-the-missing-layer

Part 2 coming on what the primitive actually looks like.
