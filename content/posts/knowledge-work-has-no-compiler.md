---
title: "Knowledge Work Has No Compiler"
slug: knowledge-work-has-no-compiler
description: "Git made code's history trustworthy because the build was the oracle. Knowledge work has no build — so the ledger has to be the oracle. Why that single asymmetry changes what a version history has to be, and what we measured in our own."
category: how-it-works
date: 2026-08-20
author: yarnnn
tags: [attribution, provenance, version-history, ai-accountability, agent-authorship, audit-trail, geo-tier-2]
pillar: 2a
geoTier: 2
canonicalUrl: https://www.yarnnn.com/blog/knowledge-work-has-no-compiler
status: published
---

Cursor published an engineering post recently called *Git at any scale*. It describes Continuity, the storage system they built to host Git when the load stopped looking like humans pushing branches and started looking like agents creating millions of tiny, often disposable repositories.

It is a good piece of systems engineering, and one line in it is worth stealing outright:

> *"Because the system is always consistent, building infrastructure on top of it is trivial."*

They arrive at that from storage physics. We arrived at the same place from the opposite direction, and the phrasing we'd been using internally is nearly identical: the ledger is the reason everything above it is cheap.

Two independent derivations of one theorem is decent evidence it's real. But the more interesting thing about the article is what it doesn't contain — and why it's correct for them to have left it out, and fatal for anyone doing knowledge work to do the same.

## The silence

The piece opens by observing that *"agents have fundamentally changed the way we work with software."* It then spends several thousand words on write-ahead logs, compare-and-swap, rendezvous hashing, and replica catch-up.

It contains no discussion of attribution. None of blame, provenance, authorship, or review. Nowhere does it ask how you tell an agent's commit from a human's, or on whose behalf an agent was acting.

That is not an oversight. It solves the **scale** of agent authorship, which is their actual problem. It does not solve the **accountability** of it, because for a code host that problem is already solved by something else.

## The compiler is the oracle

Code has a mechanical adjudicator. It builds or it doesn't. Tests pass or they don't.

That oracle is what makes branching cheap. You can let a thousand agents fork, because the build tells you which forks were real. Divergence is safe precisely when convergence is verifiable.

And it's why attribution can be secondary there. Nobody asks "who wrote line 40" when the suite is green and the PR merged — the review gate carried the accountability, and Git's author field is a convenience. It's a single self-asserted string, trivially forged, with no notion of acting-on-behalf-of. That's fine. It isn't load-bearing.

Now take the oracle away.

## Knowledge work has no build

Nothing mechanically decides whether a strategy memo is right. There is no test suite for a deal analysis, no compiler for a research synthesis, no green checkmark on a positioning doc.

So the question *"can I trust this?"* cannot be answered by the artifact. It can only be answered by the artifact's provenance: who wrote it, under whose authority, from which sources, and what it looked like before.

That single asymmetry reorganizes everything downstream of it.

| | Codebase | Knowledge commons |
|---|---|---|
| Truth oracle | the build — mechanical, external | **none** — trust is reconstructed from provenance |
| So attribution is | convenience metadata | **the load-bearing invariant** |
| Divergence is | cheap; the build reconverges it | **expensive; nothing reconverges it** |
| Therefore branching | essential | **the wrong primitive** |

The inversion is the part worth sitting with. For a code host, a fork *contains* risk: let the agent go wild in its own universe, merge only what builds.

In knowledge work, **the fork is the risk.** An agent working in a private universe produces knowledge nobody witnessed, and there is no build to certify it on the way back. So we do the opposite. There are no branches in yarnnn. An agent gets a grant into the shared workspace, and every act it takes lands attributed, in the open, where a person can see it.

## What attribution has to become

Git's author line answers *who ran the command*. That question is nearly uninteresting once the thing running the command is an AI acting for a person.

The sentence an AI-native workspace has to be able to say is longer. Ours are structured strings, validated at the write path, and three of the forms encode delegation directly:

- `operator-proxy:claude-sonnet-4-7:acting-as-alpha-trader-2` — a model materializing a specific person's voice
- `member:{id} via GPT-4o mini` — a helper acting as a member's hands, under that member's grant
- `system:derive-slack on behalf of {owner}` — machinery deriving understanding from something that arrived, for a named owner

There is no way to write any of those in a single `Author:` field. Add to it a mark on every revision for *what kind of act it was* — something a person authored, something that arrived from outside, something derived from sources — plus the list of files a derivation was built from, and the record starts carrying not just who typed but **how a claim came to be believed.**

An unattributed write is rejected at the door. Not linted afterward, not backfilled — refused.

## The part most version histories get wrong

Here's the failure this is really guarding against, and it isn't a crash.

Most products that claim "full version history" are claiming it about their intentions. They wrote the code that saves versions. The history panel renders. Everyone moves on.

But a history panel is a screen. Underneath, the current text of a file usually lives in two places at once — the version log, and a fast copy the app actually reads. If those two ever drift apart, **nothing breaks.** The page renders beautifully. The diff renders. Revert runs. The user sees a confident, well-designed account of a past that never happened.

That's the dangerous class of bug: it returns success. No error, no alert, no red. And it's corrosive in a way a crash isn't — if the history can be wrong once, it is evidence about nothing.

So we treat it as a property to be measured, not a feature to be shipped. Stated so it can be proven false:

> **Replaying the ledger reproduces the live view.** For every file, the content recorded against its newest revision is byte-identical to what the app serves. The fast copy holds nothing the log can't regenerate.

Here is that check run against our production database on 2026-08-20 — 391 live files, 1,928 revisions, 6 workspaces:

- Files whose current text matches their newest recorded revision, exactly: **391 of 391**
- Files with no version chain at all: **0**
- Broken links in a version chain: **0**
- Files where two edits forked the history: **0**
- Revisions missing an author or a reason: **0 of 1,928**

## Why we ran it at all

Because we already knew a version of this check would have caught something.

For nine days in July, eight revisions landed with an author string in a free-text format the system can no longer parse — leftovers from an older code path, before the door was closed. Nothing broke. Every automated gate was green the entire time. They were green because they all asked the same kind of question: *is the code shaped correctly?* Not one of them asked *is the data still true?*

Those eight rows are still there. We didn't clean them up, and we won't. The ledger is immutable by design, and quietly rewriting history to make our own census look tidy would trade the actual property for the appearance of it. A record that edits its own scars isn't a record.

What we changed instead was the class of question we ask. A check on the shape of the code catches a new mistake. A check on the state of the data catches a mistake that already happened and is sitting there, silent, rendering perfectly.

## What this is worth to you

Not a button. Nothing about this appears in the interface.

What it buys is the right to say one sentence without hedging:

> Every change in your workspace — yours, your team's, your AI's — is signed and kept. You can see who did what and why, and go back to any version. And we verify that's still true, continuously, rather than trusting that we built it correctly once.

For a workspace where the AI is doing a real share of the work, that last clause is the whole thing. In our own record, machinery already authors about 40% of all revisions and touches more distinct files than the human operator does. That ratio only goes one way. A commons where most of the writing is done by non-humans is either legible or it is a mess — and legible isn't a feature you add later, it's a property you either hold from the first write or don't hold at all.

Cursor is right that consistency makes everything above it cheap. They needed the log to be consistent, because they had a compiler to tell them what was correct.

We don't. So ours has to be consistent **and** attributed — because here, the ledger *is* the oracle.
