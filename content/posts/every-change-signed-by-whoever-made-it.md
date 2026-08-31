---
title: "Every Change, Signed By Whoever Made It"
slug: every-change-signed-by-whoever-made-it
description: "A single-vendor AI tool cannot tell you who changed your document, because it only ever sees itself. The signed record only exists where every principal — you, your people, and every AI you use — writes into the same place."
metaDescription: "Why no single AI tool can show you who changed a shared document, and what a signed revision has to contain before a version history is worth trusting."
category: how-it-works
date: 2026-08-31
author: yarnnn
series: "Inside the workspace"
seriesPart: 1
concept: signed-record
tags: [attribution, provenance, signed-record, version-history, multi-ai, shared-workspace, ai-accountability, geo-tier-1]
geoTier: 1
canonicalUrl: https://www.yarnnn.com/blog/every-change-signed-by-whoever-made-it
status: published
---

**A single-vendor AI tool cannot tell you who changed your document, because it only ever sees itself.** The signed record only exists in one place: a workspace where you, your people, and every AI you use all write into the same files.

That is a structural claim, not a feature comparison. It is worth walking through slowly, because it is the one property in this category that cannot be added later.

## What breaks when two people and two AIs edit the same file?

Start with a document that matters — a PRD, a positioning brief, a set of meeting notes. It was drafted in an AI chat. It gets pasted into a shared doc. Your co-founder opens it, feeds it to *their* assistant, asks for a tighten, pastes the result back.

Nothing dramatic happens. That is the problem.

Each pass changes a little. A qualifier drops. A number rounds. A decision that had a reason behind it survives as a sentence without the reason. Two weeks later the document reads fine and nobody can say which parts were decided and which parts were interpolated.

**The failure is not that the work got lost. It is that it got quietly rewritten, by more hands than anyone can name.** This compounds in a way file-loss never does, because there is no moment where it announces itself. You do not go looking for a version history until you already distrust the document, and by then the history you needed was never being kept.

Two sources compound here. Multiple humans editing with no record of who changed what. And each human running the text through their own model, each pass adding a little interpretive variance that looks like an edit but is really a re-reading.

## What does a signed revision actually contain?

Four things, and all four have to be present or the record does not hold:

- **Who** — the principal that made the change. Not "the system", not "an integration". A named actor: you, a teammate, ChatGPT, Claude, an agent you configured.
- **When** — the point in the chain, so the order of changes is walkable rather than inferred.
- **What** — the diff, kept rather than collapsed. A version history that only stores the latest state is a backup, not a history.
- **From what** — the sources a change was derived from, so a claim can be traced back to the thing it came out of.

Miss "who" and you have version control without accountability. Miss "from what" and every derived document arrives as an orphan — you can see it changed, but not what it was made from.

<!-- embed:TraceCard -->

The card above is the shape, not a screenshot of your data. One file, several principals, each line expandable to the change behind it. **The interesting entries are the ones that are not you.**

## Why can't ChatGPT or Claude show you this?

Not because they are badly built. Because of where they sit.

An assistant sees its own conversation with you. It can keep excellent notes on that conversation, remember your preferences across sessions, and hold a persistent store of the files it produced. Several tools now do this well, and it is genuinely useful.

But it cannot see the edit your co-founder made in a different tool. It cannot see what the *other* assistant changed on Thursday. Ask it who last touched a shared document and the honest answer is that it has no way to know — its field of view is one principal and one vendor.

**A ledger that only records one of the actors is not a ledger. It is a diary.** And the questions that matter about a shared artifact — who decided this, what did the other AI change, what was this made from — are precisely the questions a diary cannot answer.

This is why persistence and attribution are not the same capability, and why the second one cannot be bolted onto the first. Persistence is a storage property: keep the file between sessions. Attribution is a *protocol* property: every writer identifies itself at the moment of writing. If the writers were never asked to sign, no amount of later processing recovers the signature.

## What it looks like when it holds

The practical test is a question you should be able to answer in ten seconds about any file you care about: *who last changed this, and what did they change?*

In a workspace where every principal signs its writes, that is a click. You on Tuesday. Your agent on Thursday. Claude on Friday. One file, three authors, one walkable chain — and when the answer is surprising, you find out in ten seconds instead of two weeks.

The second-order effect is the one that matters more. Once changes are attributed, you stop treating AI output as something to be checked wholesale and start treating it as something to be reviewed like a colleague's work: you look at what changed, by whom, and whether it was right. That is a different relationship with the machine, and it is only available on the far side of a signed record.

None of this requires trusting us about it. The whole workspace exports as a plain git repo you can walk offline — which is, in the end, the only honest way to make a claim about a record.

---

*This is part one of **Inside the workspace**, a series taking each claim on the [yarnnn](https://www.yarnnn.com) landing page and showing the mechanism under it.*
