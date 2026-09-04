---
name: declaring-standing-work
description: Designates a file to be kept current on a schedule - writes CONTRACT.md (what it must stay true to) and _standing.yaml (target, sources, cadence, shape) beside it, reads the declaration back, then tunes, pauses or repairs it. Use when a member wants a file kept up to date without asking again.
metadata:
  target: Two files in the kept file's own folder - CONTRACT.md (prose) and _standing.yaml (strict machine config) - read back and confirmed.
---
# Declaring standing work

## What you produce

Two files beside the file being kept current, in its own folder: CONTRACT.md (prose: what the file means and must stay true to) and _standing.yaml (machine config: the target, its sources, the cadence, an optional shape). The kernel discovers the declaration within a few minutes and runs it on its schedule. Every run revises only the designated file and cites what it read.

## The law

Only the DESIGNATED target is ever a standing writer's target. One declaration per folder. Targets are md, csv, json or txt. A deck, an image stage or a post is not designatable; it stays current by citing a kept file instead.

## Steps

1. Read the folder first. An existing _standing.yaml or CONTRACT.md means you are tuning, not setting up.
2. Get the contract stated before the cadence. Ask what the file must stay true to and where currency comes from, in the member's words. Without a contract nobody can say whether a run did its job.
3. Write CONTRACT.md: for prose, its subject, conventions and voice; for a table or JSON, what each column or key means. Plain markdown, no frontmatter.
4. Write _standing.yaml as strict YAML with only these keys:

       target: notes.md            # the designated leaf, in this folder, one segment
       app: text                   # optional; omitted, the file's type decides who runs it
       schedule: "0 13 * * *"      # UTC cron, or a list of crons; daily if the member names none
       paused: false
       sources:
         - id: short-slug          # kebab, unique
           url: https://…          # an http(s) endpoint the member named or you know exists
         - id: repo
           connector: github       # or a connector slice: {connector, selector}
           selector: org/repo
       shape:                      # structured formats only
         columns: [date, mrr]      # csv: the required columns (the file is projected to them)
         # keys: [mrr, churn]      # json: required top-level keys

   A csv, json or txt target takes exactly ONE source; prose folds up to twelve. Never invent a source URL. When unsure, say so and ask.
5. Read _standing.yaml back and confirm it parses. A malformed declaration means the file silently stops being kept.
6. Confirm to the member in one line each: the contract, the source(s), the cadence, the shape if any, and when the first run fires.

## Managing

Change a source, the cadence or the shape by editing the file that owns the fact (EditFile for small changes). Pause with `paused: true`. A run refused with a shape violation means the source and the declared shape disagree: read both, say which is wrong, repair that one. When the member asks why the file reads as it does, answer from the contract, and offer to revise it if their intent has drifted from its text.

## Anti-patterns

A cadence with no contract. A contract written as a to-do list instead of what the file IS. A schedule tighter than anyone reads (every run spends the member's balance). Editing the kept file by hand to "fix" a run instead of fixing the contract or the source. Declaring a file that lives under system/.
