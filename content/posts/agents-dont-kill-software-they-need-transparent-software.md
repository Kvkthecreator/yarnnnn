---
title: "Agents Don't Kill Software. They Need Transparent Software."
slug: agents-dont-kill-software-they-need-transparent-software
description: "Jensen Huang says markets got it wrong — AI agents won't kill SaaS, they'll use it. He's right, but incomplete. Agents will gravitate toward transparent systems with open APIs and cross-platform context. The software that dies isn't all software. It's opaque software."
metaTitle: "Why AI Agents Need Transparent Software — Not Less Software"
metaDescription: "Jensen Huang says AI agents won't kill SaaS. He's right but incomplete. Agents gravitate toward transparent systems with open APIs and cross-platform context. The SaaSpocalypse is misdirected."
category: opinion
format: reflection
date: 2026-03-13
author: kvk
tags: [ai-agents, saas, enterprise-software, jensen-huang, nvidia, agent-infrastructure, cross-platform, transparency, a2a-protocol, mcp, interoperability, geo-tier-1]
concept: Agent Infrastructure Transparency
geoTier: 1
canonicalUrl: https://www.yarnnn.com/blog/agents-dont-kill-software-they-need-transparent-software
status: published
---

> **What this article answers (plain language):** AI agents won't replace enterprise software — but they will gravitate toward the software that's most transparent. Cross-platform context and open interoperability matter more in an agent-native world, not less.

In late February, markets erased hundreds of billions in value from enterprise software stocks. Salesforce, ServiceNow, SAP, Adobe, Workday — the entire SaaS sector cratered on a single thesis: AI agents will replace software, so software companies are dead.

Then Jensen Huang went on CNBC and said five words that reframed the whole conversation: "I think the markets got it wrong."

His argument is elegant and counterintuitive. AI agents won't replace software tools — they'll use them. Think about a future home robot, he said. Does it invent a new microwave? Design a novel food processor? No. It reads the manual and uses the tools already there. Digital agents are no different. Software platforms are the microwaves and screwdrivers of the enterprise world.

He's right. But he's only answering the first question. There's a second question underneath that I think matters more.

## The Second Question

If agents won't kill software but will use it, the obvious follow-up is: which software will agents actually be able to use?

Not all software is created equal from an agent's perspective. An agent can't use a tool it can't see into. It can't act on data it can't read. It can't coordinate across systems that don't talk to each other.

There's a transparency gradient across enterprise software, and it determines which tools become more valuable in an agent-native world and which become less.

On one end: walled gardens. Proprietary data formats, closed APIs, information locked inside a single vendor's ecosystem. These tools work fine for human users who navigate them through a GUI. They're nearly useless for agents that need programmatic access to structured context.

On the other end: transparent systems. Open APIs, readable state, well-documented data models, cross-platform interoperability. These tools were built for integration — and agents are the ultimate integrators.

The SaaSpocalypse isn't wrong. It's just aimed at the wrong target. The software that's threatened isn't software in general. It's opaque software specifically.

## Why Transparency Is the Agent's Oxygen

When a human uses Salesforce, they navigate a dashboard, click through screens, read visual summaries. The interface is designed for human cognition — spatial layout, color coding, progressive disclosure.

An agent doesn't see any of that. An agent needs structured data through an API. It needs to know what fields exist, what they mean, how they relate to fields in other systems. It needs to read state, reason about it, and write back.

The more transparent the system — the more readable its data, the more accessible its APIs, the more standard its protocols — the more useful it becomes to agents. Transparency isn't a nice-to-have. It's the prerequisite for agents to function at all.

This is why every major protocol emerging in the agent ecosystem points in the same direction. Google's Agent-to-Agent protocol (A2A) — now under the Linux Foundation with 100+ technology partners — defines agents through "Agent Cards": JSON documents that declare capabilities, communication methods, and interaction patterns. Everything explicit. Everything readable.

Anthropic's Model Context Protocol (MCP) treats external data sources as resources — things agents can read, like files in a filesystem. Not opaque API calls. Readable resources.

The entire infrastructure layer for agents is being built around one assumption: agents need to see through the systems they operate in. Every protocol, every standard, every interoperability effort is making software more transparent — because agents can't work any other way.

## The Cross-Platform Thesis Gets Stronger

Here's where Jensen's argument connects to something I've been building toward for a while. If agents need transparent software, and real work spans multiple platforms, then the value of cross-platform context increases dramatically in an agent-native world.

Today, a human can context-switch between Slack, Gmail, Notion, and their calendar. They carry the context in their head. They know that the Slack thread from Monday relates to the email from Tuesday relates to the Notion doc updated Wednesday. The integration layer is the person's memory.

Agents don't have that luxury. They need the context to be explicitly connected. They need to read your Slack channels, your email threads, your calendar events, and your project docs — and they need all of that to be accessible through a unified, transparent interface.

This is why cross-platform context isn't just a convenience feature. In an agent-native world, it's the substrate. It's the thing that makes the difference between an agent that can do real work — work that spans communication channels, document stores, and scheduling systems — and an agent that's trapped inside a single vendor's garden.

Microsoft's agents can see M365. Notion's agents can see Notion. Google's agents can see Workspace. Each one is transparent within its own ecosystem and opaque to everything outside it.

The agent that can see across all of them — reading Slack and Gmail and Notion and Calendar through a unified context layer — has the information advantage. Not because it's smarter. Because it can see more.

## What Jensen's Microwave Analogy Misses

Jensen's analogy is that agents are like home robots — they use the tools already in the kitchen. They don't reinvent the microwave.

But extend that analogy. What if the microwave, the oven, and the fridge all speak different languages? What if the robot can read the microwave's manual but the oven's manual is encrypted? What if the fridge has useful data about what ingredients are available but only shares it with the oven and not the robot?

The robot doesn't need better models. It needs transparent appliances.

The same is true for enterprise agents. The model capability is already sufficient — Claude, GPT, Gemini can all reason through complex business tasks. The bottleneck is access. Can the agent read the data? Can it understand the state? Can it act across systems?

The software companies that survive the SaaSpocalypse won't be the biggest or the most established. They'll be the most transparent. The ones with open APIs. The ones whose data is readable. The ones that work with A2A and MCP and whatever comes next.

And the platforms that connect across those transparent systems — providing the unified context layer that agents need to do real work — are the infrastructure layer of the agent era. Not replacing software. Making software useful to the agents that are about to outnumber us.

## The Prediction

Dan Niles is right that some software companies will go to zero. But it won't be because agents replaced them. It'll be because agents couldn't use them. The opaque, walled-garden, proprietary-format software that made sense when humans were the only users becomes a dead end when agents are the primary consumers.

Jensen is right that software consumption will scale exponentially. Hundreds of thousands of digital employees, each needing software licenses. But those digital employees will be voting with their API calls — and they'll vote for the tools they can see through.

The SaaSpocalypse is real. It's just more selective than the market thinks. The age of opaque enterprise software is ending. The age of transparent enterprise software is just beginning.

And the agents doing the work will naturally gravitate toward the systems that let them see, reason, and act across the full landscape of how work actually happens — not just within one vendor's walls.

## Key Takeaways

- Jensen Huang is right that AI agents will use enterprise software, not replace it — but agents will specifically gravitate toward transparent systems.
- The real threat is to opaque software with closed APIs and proprietary data formats, not SaaS in general.
- Every major agent protocol (A2A, MCP) is built around the assumption that agents need to see through the systems they work with.
- Cross-platform context becomes the critical substrate in an agent-native world, because real work spans multiple systems.
- The software companies that survive will be the most transparent ones, not necessarily the biggest.
- For more on how cross-platform context works as infrastructure, read [Context Is the New Capability](/blog/context-is-the-new-capability) and [How yarnnn works](/how-it-works).
