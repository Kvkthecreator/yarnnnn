# Architecture Discourse Summary — AI-Native Shell, Workbench, and Capability Platform

> **Provenance**: authored by the operator (KVK) in an external discourse
> session (2026-07-06), brought into the repo verbatim as the discourse base
> for **ADR-413**, which cross-checks it against ratified canon and ratifies
> the genuinely new decisions. Read ADR-413 for the canon-checked version —
> this document is preserved as-written; where its phrasing diverges from
> ratified mechanics (e.g. the chat-context nuance, the workspace tree), the
> divergence is recorded in ADR-413 §5, not edited here.

## Purpose

This document summarizes the architectural conclusions reached during discussion around ADR-412 and the future interaction model of yarnnn.

While the discussion began around information architecture ("Three Altitudes, Three Chromes"), it evolved into defining a broader AI-native operating model.

The central realization is that yarnnn is not building another AI chat application.

It is building an operating environment for AI work.

---

# 1. Freddie is the AI-Native Shell

Freddie should not be understood as another assistant or another chat.

Freddie represents the operating layer of the workspace.

Its responsibility is to make the workspace function.

Examples include:

- orchestration
- governance
- scheduling
- permissions
- memory maintenance
- background execution
- notifications
- workspace health
- autonomous coordination

Users do not "work inside Freddie."

Instead:

Freddie operates the environment in which work happens.

The closest analogy is an operating system shell (macOS, Finder, Spotlight), not ChatGPT.

Freddie should therefore feel infrastructural rather than conversational.

---

# 2. Chat is the Cognitive Workbench

The opposite of the shell is the Workbench.

Internally this surface represents:

The cognitive workspace where humans collaborate with AI in real time.

Examples include:

- brainstorming
- writing
- coding
- research
- debugging
- reasoning
- planning
- iteration

Although the architectural concept is the Workbench, the product surface may simply be called:

Chat

This distinction is intentional.

Internally:

Workbench.

User-facing:

Chat.

Users already understand what "Chat" means, while the underlying architecture remains broader than conversation alone.

---

# 3. Chat becomes a dedicated product surface

Rather than Freddie housing multiple conversations inside the shell, Chat becomes its own first-class surface.

Chat is where users maintain multiple ongoing work threads.

Each conversation represents a piece of work.

Examples:

Landing Page

Architecture ADR

Research Notes

Marketing Strategy

Investor Deck

Each conversation operates against the same shared workspace rather than owning isolated context.

---

# 4. Work organizes conversations

Information Architecture remains work-first.

Chats are organized around the work being performed.

Not around providers.

Not around models.

Example:

Landing Page (Claude Sonnet)

Architecture ADR (GPT-5)

Research Notes (Gemini)

Marketing Strategy (GPT-5)

The work is the identity.

The selected model remains visible through metadata such as badges or chips.

Users remember:

"The investor deck."

Not:

"The GPT conversation."

This reinforces ADR-412's principle:

Organize by work.

---

# 5. Model selection is intentionally explicit

This is separate from Information Architecture.

Creating work and organizing work are different design problems.

When creating a new chat, the user should intentionally select the model they wish to work with.

This is one of yarnnn's product differentiators.

Rather than hiding providers behind automatic routing, yarnnn embraces the growing AI ecosystem.

Examples:

New Chat

Choose Model

- GPT-5
- Claude Sonnet
- Gemini
- DeepSeek

...

The platform may recommend models.

It should not automatically conceal them.

Recommendations increase clarity.

They do not replace user agency.

Examples:

"I'm starting a research project."

Suggested:

Claude Sonnet

Gemini

GPT-5

The user still chooses.

---

# 6. The AI ecosystem should become more visible, not less

One goal of yarnnn is becoming the home for the rapidly expanding AI ecosystem.

The product should help users discover:

- models
- providers
- capabilities
- workflows
- templates
- best practices

Rather than abstracting everything away, yarnnn should help users intentionally compose the best AI stack for their work.

Possible future experiences include:

- model recommendations
- workflow templates
- capability comparisons
- provider explainers
- curated starting points
- side-by-side experimentation

The platform celebrates choice instead of hiding it.

---

# 7. The workspace is the center of the system

Unlike most AI products, conversations do not own context.

Instead:

Workspace

├── Files

├── Memory

├── Tasks

├── Agents

├── Chats

Everything operates against the same durable workspace.

Chats.

Agents.

Freddie.

Memory.

Files.

All become different interfaces into the same shared substrate.

This inversion is one of yarnnn's strongest architectural differentiators.

---

# 8. LiteLLM is infrastructure, not platform architecture

LiteLLM remains an excellent implementation for language providers.

However it should not become the platform abstraction.

The reason is that many future AI systems are not language models.

Examples:

Seedance

Higgsfield

Runway

ElevenLabs

Figma

Browser automation

Computer Use

Search systems

These require different integrations.

Therefore LiteLLM is simply:

The language-provider adapter.

Not the architecture itself.

---

# 9. Introduce a Capability Layer

The broader architecture evolves into three distinct layers.

User Intent

↓

Capability

↓

Provider

These represent three independent concerns.

---

## User Intent

"I want a landing page."

"I need research."

"I need a hero video."

"I need voiceover."

---

## Capability

Language

Images

Video

Audio

Code

Browser

Design

Search

Memory

Computer Use

Capabilities describe what kind of work is being requested.

---

## Provider

GPT

Claude

Gemini

Flux

Midjourney

Seedance

Higgsfield

Runway

ElevenLabs

etc.

Providers are the concrete implementations of capabilities.

---

# 10. Provider adapters

Each capability can expose one or more provider adapters.

Examples:

Language

LiteLLM

↓

GPT

Claude

Gemini

DeepSeek

Images

↓

Flux

Imagen

Midjourney

Ideogram

Video

↓

Seedance

Higgsfield

Runway

Kling

Audio

↓

ElevenLabs

Cartesia

OpenAI Voice

Design

↓

Figma

MCP integrations

The architecture therefore scales without forcing every AI system into an LLM abstraction.

---

# 11. This strengthens the Chat surface

Capability abstraction does not replace Chat.

It strengthens it.

A single work thread may include:

- reasoning
- coding
- image generation
- video generation
- browser actions
- design edits
- voice generation

The conversation remains continuous.

Only the invoked capabilities change.

From the user's perspective:

They stay in one work thread.

The platform coordinates multiple capabilities behind the scenes.

---

# 12. Three independent organizing principles

One of the clearest outcomes of this discussion is separating three independent concepts.

## Work

How users organize.

Examples:

Landing Page

Research

Marketing

Architecture

---

## Capability

What users want to accomplish.

Examples:

Language

Images

Video

Code

Audio

Browser

---

## Provider

Which implementation the user chooses.

Examples:

Claude

GPT

Gemini

Seedance

Higgsfield

Runway

These should never be collapsed into one abstraction.

Each serves a different purpose.

---

# 13. Emerging philosophy

Several broader principles emerged.

## Placement teaches ontology.

Users infer what something is by where it lives.

Chrome defines understanding.

---

## Organize by work.

The work is the enduring identity.

Models are metadata.

---

## User agency matters.

Model choice is a product feature.

Recommendations are valuable.

Automatic concealment is not the goal.

---

## Capabilities outlive providers.

Providers will continue changing.

Capabilities remain relatively stable.

Architecture should therefore organize around capabilities rather than specific providers.

---

## The workspace is the source of truth.

Chats.

Agents.

Freddie.

Files.

Memory.

All become interfaces into one shared workspace.

Nothing owns the workspace.

Everything participates in it.

---

# Updated conceptual model

AI Shell (Freddie)

↓

Operates the Workspace

↓

Workspace

(shared filesystem, memory, tasks, artifacts)

↓

Chat (Workbench)

Real-time human + AI collaboration

Multiple ongoing work threads

↓

Capabilities

Language

Images

Video

Audio

Code

Browser

Design

Search

Memory

↓

Provider Adapters

Language (LiteLLM)

Images

Video

Audio

Design

↓

Providers

GPT

Claude

Gemini

Seedance

Higgsfield

Runway

ElevenLabs

etc.

---

# Overall Direction

The discussion ultimately reframed yarnnn from being "a place to access many AI models" into something more fundamental.

yarnnn becomes an AI-native operating environment where:

- Freddie operates the workspace.
- The Workspace provides persistent shared memory and artifacts.
- Chat serves as the cognitive workbench for real-time collaboration.
- Capabilities describe what kind of work is being requested.
- Providers are explicit tools that users intentionally choose.
- All work is organized around purpose rather than implementation.

This separation creates a platform that can naturally expand beyond language models while preserving user agency, maintaining a work-centric information architecture, and positioning yarnnn as the operating environment where users intentionally compose and manage their AI ecosystem rather than simply consuming a single AI service.

# Addendum — The Workspace Runtime and Provider Execution Contract

## Context

A further realization emerged while discussing how external language models should be connected to yarnnn.

The original discussion focused on an "Execution Envelope."

While useful, this framing still places the prompt at the center of the architecture.

A stronger mental model is to think of every provider as joining a **Workspace Runtime**.

The prompt is simply today's transport mechanism for expressing that runtime.

The runtime itself is the architectural primitive.

---

# 1. Stop thinking in prompts

The architectural question is not:

> "What prompt should every model receive?"
>

Instead it becomes:

> "What execution environment does every reasoning engine enter?"
>

This shifts the center of gravity away from prompt engineering and toward runtime construction.

The model is not pretending a filesystem exists.

It is executing inside one.

---

# 2. The workspace is mounted, not described

The most important realization is distinguishing between describing a workspace and mounting one.

Instead of saying:

"You have access to files."

The runtime should establish:

"You are operating inside a mounted workspace."

This is conceptually much closer to:

- current working directory (cwd)
- mounted filesystem
- environment variables
- process permissions

than to traditional prompt engineering.

The workspace becomes the execution environment.

---

# 3. The mount should remain extremely small

The mount itself should not become a large system prompt.

Its purpose is only to establish the runtime.

Conceptually something as small as the following may be sufficient:

"You are operating inside a persistent yarnnn workspace. The workspace is the durable source of truth. Use filesystem operations to read, create, update, and organize persistent knowledge. Do not rely on conversation history for durable state."

This is not behavioral prompting.

It is environment declaration.

Everything else should emerge from the runtime itself.

---

# 4. The filesystem teaches the model

The primary teacher should not be the prompt.

It should be the filesystem API.

Examples:

read()

write()

list()

move()

search()

As models repeatedly use these primitives they naturally construct the correct mental model:

The workspace is persistent.

The conversation is transient.

The prompt simply introduces this reality.

The runtime reinforces it.

---

# 5. The runtime should resemble a Unix process

A useful analogy is launching a process on Linux or Unix.

Processes are not told lengthy stories about their environment.

They simply inherit one.

Examples include:

Current Working Directory

Mounted Filesystem

Environment Variables

Permissions

Standard Input / Output

The process discovers its world through these primitives.

External AI providers should experience yarnnn similarly.

---

# 6. A Workspace Manifest

Rather than imagining one large system prompt, yarnnn should conceptually construct a Workspace Manifest.

For example:

workspace

- mounted
- workspace identifier
- current directory

persistence

- filesystem is durable
- conversation is transient

capabilities

- filesystem
- search
- memory
- tasks

identity

- collaborator
- Freddie
- domain agent

This is runtime metadata.

Not conversational instruction.

Today's APIs may serialize this into a system prompt, but architecturally it remains runtime configuration.

---

# 7. Separate runtime from behavior

One of the most important architectural separations is:

Workspace Runtime

↓

Behavior

The runtime answers:

Where am I?

What exists?

What persists?

What can I access?

Behavior answers:

How should I work?

Writing style

Reasoning style

Formatting

Domain expertise

These should remain independent systems.

---

# 8. Skills belong to behavior

Skills should not establish the runtime.

Instead they extend behavior.

Conceptually:

Workspace Runtime

↓

Capability Manifest

↓

Skill Packs

↓

Conversation

Examples include:

architecture.md

research.md

copywriting.md

marketing.md

These are modular behavioral extensions.

They are not responsible for mounting the workspace.

---

# 9. LiteLLM remains transport

LiteLLM should remain responsible for:

- authentication
- provider normalization
- streaming
- provider parameters
- request transport

It should not become responsible for constructing workspace context.

Workspace construction belongs entirely to yarnnn.

Every language provider should receive the same runtime regardless of destination.

---

# 10. The long-term architecture

The execution stack increasingly resembles an operating system launching a process.

Workspace Runtime

↓

Workspace Manifest

↓

Capability Manifest

↓

Behavior

↓

Conversation

↓

Provider Adapter

↓

Reasoning Engine

This order is significant.

Conversation becomes the final input rather than the architectural center.

---

# 11. A new architectural principle

One broader principle emerged from this discussion.

Do not prompt models into believing they have a workspace.

Launch them into one.

The prompt is merely today's compatibility layer for expressing a runtime that future AI execution environments may eventually support natively.

This keeps yarnnn's architecture independent of current provider APIs while remaining fully implementable using today's language-model interfaces.
