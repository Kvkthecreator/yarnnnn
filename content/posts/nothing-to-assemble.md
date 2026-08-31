---
title: "Nothing To Assemble"
slug: nothing-to-assemble
description: "Most AI tooling asks you to build the workspace before you can use it — pick a framework, wire the integrations, define the agents. Chat, slides, files and agents should already be there, on the same record."
metaDescription: "Why most AI tooling makes you assemble a workspace before you can use one, and what ships differently when chat, slides, files and agents share a file system."
category: how-it-works
date: 2026-09-12
author: yarnnn
series: "Inside the workspace"
seriesPart: 6
concept: assembled-workspace
tags: [ai-workspace, agent-frameworks, no-setup, ai-apps, shared-file-system, ai-agents, geo-tier-2]
geoTier: 2
canonicalUrl: https://www.yarnnn.com/blog/nothing-to-assemble
status: published
---

**Most AI tooling asks you to build the workspace before you can use one.** Pick a framework, wire the integrations, define the agents, decide where state lives. The assembly is presented as flexibility. Mostly it is unfinished work handed to the customer.

## What does "set up your AI workspace" usually mean?

It means a sequence like this. Choose an orchestration framework. Connect a vector store. Add the connectors for the tools you already pay for. Write the agent definitions. Decide how files are persisted, then discover that decision was load-bearing and revisit it.

Every step is reasonable. The sum is a small infrastructure project standing between a person and the work they wanted to do — and the people with the most to gain from AI colleagues are exactly the people with the least appetite for a small infrastructure project.

There is also a subtler cost. **When you assemble the workspace yourself, the pieces do not share a record — they share a bus.** Chat holds conversations. The store holds embeddings. Files sit somewhere else. Nothing has a common notion of *this artifact, and who changed it*, because you wired transports rather than a substrate.

## What ships assembled

The alternative is that the apps arrive already sharing one file system. Not integrations between four products. Four surfaces onto one record.

<!-- embed:ChatReplica -->

Chat, grounded in your own files, with agents you name and whichever engine suits the job. What comes out of it does not die in the scroll — replies land as real files.

<!-- embed:StudioReplica -->

Studio, where you compose on the canvas or ask in the built-in chat, and both land as the same signed revision. The deck carries its own history: who changed what, and why.

<!-- embed:FilesReplica -->

Files — the record underneath everything else. You, your people, and every AI you connect write into the same place, every write carrying a name.

<!-- embed:AgentsReplica -->

Agents you configure and name, working on your files. Worth being exact here: an agent you address at your desk works *as you*, and its edits are attributed to you. It is your hands, not a separate colleague on the ledger. Pretending otherwise would put a name on the record that did not earn it.

## Why do the four apps share one file system?

Because the alternative is drift, and drift is the thing this whole workspace exists to prevent.

If chat has its own store and the deck editor has another, the same fact ends up in two places with no relationship between them. Fix it in one, and the other is now quietly wrong. Nothing tells you. That is exactly the failure the record is supposed to catch, reintroduced by the architecture of the tool meant to catch it.

**One file system means a correction is made once and is true everywhere, because there is only one place for it to be true.** The four apps are not integrated. They are views.

That is also why the assembly-required approach struggles to add attribution later. Attribution is a property of the moment of writing — every writer identifies itself as it writes. Bolt four systems together after the fact and there is no single moment of writing to attach a signature to.

## What you don't have to wire together

No vector store to provision. No orchestration layer to choose. No decision about where state lives, because state is files and files are the product.

Connecting an AI is the one setup step, and it is the connector the assistant already speaks — not an export, not a scheduled sync.

The honest boundary: assembled means fewer choices, and fewer choices means some things you cannot arrange your own way. If you want to define the persistence layer yourself, a framework is the right tool and you should use one. This is for everyone else — the people for whom the workspace is not the project.

## Does assembled mean closed?

It would, if the assembly were the lock. It is a fair suspicion — "batteries included" has historically been how products make leaving expensive.

So the boundary matters. The AI side is open by design: you connect the assistants you already use over the connector they already speak, and adding a second or third costs nothing. Nothing here works only if you also adopt our model, our agent format, or our editor.

And the exit is real rather than rhetorical. The whole workspace exports as a standard git repository with the full revision history as real commits — readable on a machine we have nothing to do with. **An assembled product with a plain-text exit is a convenience; an assembled product without one is a trap.** The difference is entirely in whether you can walk out with the record, so that is the thing to check before adopting anything in this category, including this.

---

*Part six of **Inside the workspace**. The record underneath all four apps is [part one](https://www.yarnnn.com/blog/every-change-signed-by-whoever-made-it).*
