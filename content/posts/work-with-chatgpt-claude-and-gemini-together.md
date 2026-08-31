---
title: "Working With ChatGPT, Claude and Gemini On The Same Files"
slug: work-with-chatgpt-claude-and-gemini-together
description: "Using three AIs today means three copies of your work in three places. The fix isn't picking one — it's giving all three the same files to write into, under their own names."
metaDescription: "How to work with ChatGPT, Claude and Gemini on one shared set of files instead of three separate copies — and what changes when an AI writes instead of replies."
category: how-it-works
date: 2026-09-02
author: yarnnn
series: "Inside the workspace"
seriesPart: 2
concept: multi-principal
tags: [chatgpt, claude, gemini, multi-llm, cross-llm-workspace, shared-workspace, mcp, ai-collaboration, geo-tier-1]
geoTier: 1
canonicalUrl: https://www.yarnnn.com/blog/work-with-chatgpt-claude-and-gemini-together
status: published
---

**Using three AIs today means keeping three copies of your work in three places.** The fix is not picking a favourite. It is giving all three the same files to write into.

Most people who work seriously with AI already use more than one. One model for drafting, another for reasoning through something hard, a third because it is the one on the phone. That is a rational way to work. The tooling just has not caught up to it.

## Why does using more than one AI fragment your work?

Because each one is a walled room with a good memory.

Every assistant now keeps some persistent notion of your work — memories, projects, uploaded files, a workspace of its own. Each does it well. Each does it **only for itself**. Nothing you build up in one is visible to another.

So the person becomes the transport layer. You paste the brief from one into the other. You re-explain the constraint you already explained on Monday. You keep a mental index of which conversation holds the good version of the deck.

**Every AI keeps its own copy of your work. You don't.** That is the whole asymmetry, and adding a fourth tool with better folders makes it worse, not better — it is a fourth copy, with better folders.

The workaround people reach for is a shared doc. It half-works. It gives every actor the same *location*, and locations are cheap. What it does not give is a shared record: the doc does not know which of the three assistants rewrote the second paragraph, and neither do you.

## What does "the same files" actually mean?

It means one file system that every principal writes into directly — not a sync, not an export, not a paste.

<!-- embed:IntegrationHub -->

The shape is simple. Your sources on one side. The AI you already use on the other. One workspace in the middle that both write into, where a file has one identity rather than three drifting near-copies.

Concretely, three things have to be true:

1. **One address per file.** Not "the version in the Claude project and the version in the ChatGPT canvas". One path, one current state, one history.
2. **The AI writes, not just replies.** A reply is scrollback. A write is a file with a name that survives the session.
3. **Every write is signed.** When ChatGPT changes a file, the record says ChatGPT changed it — not "updated by the system", and not silently attributed to you.

The third one is what makes the first two safe. Sharing one file between three models without attribution is not collaboration, it is an unlit room where everyone is holding a pen.

## How do you connect one?

Through the connector the assistant already speaks. No exports, no scheduled sync, no third copy.

<!-- embed:ConnectReplica -->

The moment worth watching is the second half. You attach the connector, and the first foreign write lands in the ledger already labelled — the resolved name of the thing that wrote it, not a raw token. **From that point on, the assistant is a participant in your workspace rather than a place your work goes to disappear.**

Adding the second and third assistant costs nothing extra, which is the point. An AI connection is not a seat: it is another principal on files you already own.

## What changes when the AI writes instead of replies?

The obvious change is that you stop ferrying. The deeper one is that continuity stops being your job.

When work lands as a file rather than as a message, the next session — with the same model or a different one — starts from the file. You do not re-explain the constraint, because the constraint is written down where every principal can read it. The context is not in any model's memory. It is in your workspace, and the models come to it.

That inverts a dependency that most people have not noticed they accepted. Right now, switching models means losing the accumulated context you built inside one. When the record lives outside every model, switching is just changing which principal you asked. **The model becomes replaceable, and the record becomes the thing you own** — which is the correct way round, given how often the models change.

It also makes disagreement useful. Two assistants working the same file, each signing its edits, produce something you can actually read: not one blended answer, but a visible difference between two readings, with names on both. That is closer to how a team works than anything a single-vendor chat can offer.

---

*Part two of **Inside the workspace**. Part one covers the [signed record](https://www.yarnnn.com/blog/every-change-signed-by-whoever-made-it) that makes any of this safe.*
