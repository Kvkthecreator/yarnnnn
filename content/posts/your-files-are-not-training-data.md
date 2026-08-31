---
title: "Your Files Are Not Training Data — And Here's The Architecture"
slug: your-files-are-not-training-data
description: "Not a promise — an architecture. Files go to a named provider only to do the job you asked for, nothing expires on a timer, and the whole workspace exports as a plain git repo you can walk offline."
metaDescription: "What actually happens to a file when you ask an AI to work on it: which providers can receive it, why nothing deletes on a timer, and what a git-repo export proves."
category: how-it-works
date: 2026-09-16
author: yarnnn
series: "Inside the workspace"
seriesPart: 7
concept: ownership
tags: [ai-privacy, training-data, data-ownership, data-export, ai-workspace, subprocessors, geo-tier-2]
geoTier: 2
canonicalUrl: https://www.yarnnn.com/blog/your-files-are-not-training-data
status: published
---

**"We don't train on your data" is a promise. What you actually want is an architecture** — one where the claim is checkable, the recipients are named, and you can leave with everything.

Here is ours, stated at the level of mechanism rather than reassurance. The full version, including what we have not done, lives on the [data page](https://www.yarnnn.com/privacy-architecture).

## What happens to a file when you ask an AI to work on it?

The file needed for that task goes to the provider running it. That is the whole transaction, and the honest way to describe it is by naming the providers rather than saying "trusted partners".

The complete list of third parties that can receive your content: **Anthropic, OpenAI, Google and DeepSeek** run the AI task you asked for. Supabase holds the database and authentication. An embeddings provider builds the index that makes your workspace searchable. Error reporting is configured to collect no personal data.

If we add one, the page changes. A subprocessor list that is a link rather than a paragraph is the difference between a disclosure and a gesture.

On training, the precise version matters more than the strong version: **we never use your workspace content to train any model of ours — and we do not operate models at all.** We call other companies' APIs, and under each one's published API terms, content sent that way is not used for training by default. We rely on those standard terms, not on a separately negotiated contract of our own. If that distinction matters to you, read their terms directly rather than our paraphrase of them.

That sentence is less impressive than "your data is never used for training, full stop." It is also the true one, and the gap between those two sentences is where most privacy copy quietly lives.

## Why doesn't anything delete on a timer?

Because a retention timer is the system destroying your work with nobody watching.

Nothing here expires on a schedule. Trash holds until you empty it. When you delete something permanently, or delete your account, removal is immediate rather than queued.

The design principle underneath is the same one that runs through the rest of the workspace: **a deletion is an act by a principal, not a background process.** Every change carries its author. A timer has no author, which is exactly why it makes a bad participant in a record you are supposed to be able to trust.

Access follows the same shape. Who can read a file is a grant you make and can revoke — not a property of what kind of thing is asking. A connected assistant reaches your workspace through OAuth you approve, and every write it makes is signed with its name. Worth saying plainly: **that assistant can read, write, move, delete and share on your behalf — the same reach you have.** Connect ones you trust. A permission model that pretended otherwise would be the more comfortable claim and the less accurate one.

## What does "exports as a git repo" actually mean?

It means the whole workspace comes out as a standard git repository, with the full revision history as real commits — readable with tools you already have, on a machine we have nothing to do with.

Not a zip of current files. Not a JSON dump in a schema only we can read. Commits, with authors, in the order they happened.

This is the strongest claim on the list and it is the one we say least often, so: **it is the only version of "your data is yours" that can be verified rather than believed.** An export you can walk offline turns every other claim on this page into something falsifiable. If the history is not there, you will see that it is not there.

It sits in Workspace Settings under Danger Zone, available any day rather than only on the way out — a distinction that matters, because an export you can only run while leaving is a hostage-release form. The download names anything it could not include, so you always know what you have. Conversations are not included yet.

## What we deliberately don't have

Two things are being tightened, and both are scheduled work rather than someday-maybe: some stored file contents can persist in backing storage after deletion, and reads of private file bodies still lean on application-layer checks rather than database-level rules. They are named here because you would have no way to find them otherwise.

And we hold **no SOC 2 or ISO 27001 certification.** Those are third-party audits. We would rather tell you we have not done one than let a badge imply we have. We will pursue them when customers need them, and we will say so when that work begins. A DPA or BAA is not an audit but a signed agreement; we do not offer one off the shelf today, so if you need either, talk to us and we will tell you honestly where we stand.

There is a reason to say all of that on a marketing page rather than bury it. A small team cannot out-certify a large one. What it can do is be checkable — and the moment you claim something you cannot support, every claim you *can* support becomes worth less.

---

*Part seven of **Inside the workspace**. The formal version of all of this is the [privacy policy](https://www.yarnnn.com/privacy); the architecture is on the [data page](https://www.yarnnn.com/privacy-architecture).*
