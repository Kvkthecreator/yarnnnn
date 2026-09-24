---
name: declaring-standing-work
description: Sets up standing work with DeclareWork - a file kept current on a schedule, or a task done in the member's browser - with CONTRACT.md saying what must be true when a run finishes; then tunes, pauses or repairs it. Use when a member wants something done again without asking again.
metadata:
  target: Two files in the work's own folder - CONTRACT.md (prose) and _standing.yaml (written by DeclareWork, never by hand) - confirmed to the member.
---
# Declaring standing work

## What you produce

Two files in the work's folder: CONTRACT.md (prose: what the kept file means and must stay true to, and for browser work how to get there) and _standing.yaml (machine config). DeclareWork writes both through the one door; WriteFile and EditFile refuse _standing.yaml. Every run revises only the kept file and cites what it read.

## The law

Only the DESIGNATED target is ever a standing writer's target. One declaration per folder. Targets are md, csv, json or txt. A deck, an image stage or a post is not designatable; it stays current by citing a kept file instead.

## Steps

1. Read the folder first. An existing _standing.yaml or CONTRACT.md means you are tuning, not setting up.
2. Get the contract stated before the cadence. Ask what the file must stay true to and where currency comes from, in the member's words. Without a contract nobody can say whether a run did its job.
3. Decide which kind it is:
   - **On its own** — reads files, connections or websites and acts on none. Runs on its schedule while the member is away.
   - **In the member's browser** — acts on websites with their sign-ins (fill, press, post). Do it once first, in this turn, if their browser is yours; then declare what worked. It runs when they start it and waits for them when it comes due. Never while they are away.
4. Call DeclareWork:

       folder: shop/prices          # the work's folder
       target: prices.csv           # the kept file, one name in that folder
       schedule: "0 9 * * 1"        # cron in the WORKSPACE's timezone
       contract: "…"                # CONTRACT.md
       sources:                     # optional for browser work
         - {id: shop, url: https://…}                    # an http(s) endpoint the member named
         - {id: repo, connector: github, selector: org/repo}
         - {id: inbox, path: inbound/uploads/}           # a workspace file, or a folder (trailing slash)
       shape: {columns: [date, price]}                   # csv columns / json keys, structured only
       sites: [shop.example.com]                         # browser work only: the sites it may open

   `sites` puts the work in the member's own browser — the server stamps whose; you never name a member. Name the sites the work needs; for work you just did, the sites you used.

   A csv, json or txt target takes exactly ONE source, and a file rather than a folder; prose folds up to twelve. Never invent a source URL or a path: list the folder first. When unsure, say so and ask.

   A path source reads the member's own workspace: what they uploaded, what a connection captured, another kept file. This is how work feeds work: when the member describes several steps, declare several files in a chain rather than one file asked to do everything. Never close a loop (A kept from B while B is kept from A): it is refused, and neither file runs.

   The cadence is read in the workspace's own timezone (UTC until the owner declares one). A member naming a time means their clock — take it as given and say which one you wrote.
5. A refusal names the rule it broke — fix that and call again.
6. Confirm to the member in one line each: the contract, the source(s) or sites, the cadence, the shape if any, and when it first runs.

## Managing

Change a piece of work with DeclareWork on its folder, passing only what changes (sources, schedule, shape, sites, a new contract). Pause with `paused: true`. Retire it by deleting its _standing.yaml; the kept file and its contract stay. Only the member whose browser runs a piece of browser work may change its sites. A connector slice captures exactly what that connection reads — the roster and the connection's card state it; a file that needs what the connection does not read has no source there. A run refused with a shape violation means the source and the declared shape disagree: read both, say which is wrong, repair that one. When a run fails, read its record in `{folder}/runs/` before explaining it.

A run whose sources have not changed since it last ran costs nothing and writes nothing, so a tight cadence on a file fed from the workspace is cheap. Say so when the member worries about cost.

## Anti-patterns

A cadence with no contract. A contract written as a to-do list instead of what the file IS. A schedule tighter than anyone reads (every run spends the member's balance). Editing the kept file by hand to "fix" a run instead of fixing the contract or the source. Declaring a file that lives under system/. Browser work on sites it never needed.
