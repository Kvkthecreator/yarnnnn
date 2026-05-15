---
title: "Programs Are More Than Skills"
slug: programs-are-more-than-skills
description: "Skills (the agentskills.io standard used by Claude Code, Hermes, and the wider open-source agent ecosystem) are composable single-purpose procedural units. Programs are a higher-order structure: a manifest, a reference workspace, a composition manifest, capability specs. The difference is what makes installable applications possible in an agent OS."
metaTitle: "Agent OS Programs vs Skills: Why Bundle Discipline Matters"
metaDescription: "Skills are reusable procedural units. Programs are bundled applications: manifest + reference workspace + composition manifest + capability specs. Programs are how an agent OS becomes an ecosystem."
category: how-it-works
date: 2026-06-04
author: kvk
tags: [agent-os, programs, skills, agentskills-io, hermes-agent, claude-code, geo-tier-2]
concept: Program Bundle
series: The Agent Operating System
seriesPart: 4
geoTier: 2
canonicalUrl: https://www.yarnnn.com/blog/programs-are-more-than-skills
status: published
---

> **What this article answers (plain language):** Skills are the unit of procedural memory that's converged across Claude Code, Hermes Agent, and the wider open-source ecosystem (the agentskills.io standard). Programs are a higher-order structure that bundles a manifest, a reference workspace, a composition manifest, and capability specs into an installable, uninstallable, updatable application. The shift from skills to programs is what makes an agent OS into an ecosystem.

**Skills are great. They're not enough.** The agentskills.io standard has converged across Claude Code, Hermes Agent, and most of the open-source agent ecosystem — a folder of `SKILL.md` files plus optional scripts that any agent can read and apply. Hermes' Reflective Phase writes them. Claude Code reads them. The standard is real and useful. What it isn't is sufficient for shipping an entire opinionated agent operation. For that you need programs — the agent OS equivalent of `.app` bundles. Programs ship more than procedure; they ship a workspace shape, a cockpit configuration, capability declarations, and a composition manifest that tells the rest of the system how the program should be presented to the operator.

This is a build-in-public observation from the past few months of shipping our first program (alpha-trader). I expected programs to be "skills + some templates." They turned out to be a structurally different unit. The difference is what lets the agent OS become an ecosystem instead of a feature inventory.

## What skills actually are

A skill in the agentskills.io sense is a folder containing:

- `SKILL.md` — a human-readable description of the procedure (when to use it, prerequisites, expected inputs, expected outputs)
- Optional scripts the agent can execute (Python, shell, etc.)
- Optional supporting files (templates, examples, reference data)

The skill is composable. Any agent can read the SKILL.md, understand what the skill does, and decide whether to invoke it for a given task. Skills are the procedural memory layer of agent systems — they encode "here's how to do this kind of work" in a format any agent can pick up.

This pattern is genuinely well-designed. The convergence across Claude Code, Hermes, and the open-source ecosystem is real and worth celebrating. Skills work for what they're for: portable, composable, reusable procedural knowledge that crosses agent boundaries.

What skills don't do: ship an entire opinionated cockpit, declare what platform integrations are required, define a default agent roster, prescribe the substrate layout for a domain, or specify how the surfaces of the operator's UI should compose when this skill is in use.

For all of those, you need a program.

## What a program actually is

A program in our agent OS is a bundle of four things at the path `/programs/{program-slug}/`:

**MANIFEST.yaml.** Machine-readable program identity. Slug, version, status (active/reference/deferred), required platform integrations (e.g. Alpaca for alpha-trader, Lemon Squeezy for alpha-commerce), declared capabilities, default agent roster, lifecycle phases (observation → paper → live, for example).

**README.md.** Human-readable program prose. What the program does, who it's for, how it differs from other programs.

**SURFACES.yaml.** Composition manifest. Declares how the cockpit should render when this program is active — which faces appear, what each face binds to in the substrate, what task types appear in the operator's work surface. The compositor reads this on every render to assemble the operator-visible cockpit.

**reference-workspace/.** The bundle's starter substrate. Files tagged by tier — `canon` (program ships authoritative version), `authored` (operator must overwrite via guided conversation at activation), `placeholder` (empty, accumulates from work). On activation, this substrate forks into the operator's workspace.

That's the whole program: four pieces of declarative content, no executable code shipped from the bundle. The kernel does the work. The program just declares.

## What this enables that skills don't

A skill is a unit of procedural knowledge. A program is a unit of opinionated operational shape. The difference matters because operators don't think in procedures — they think in operations.

**Programs ship a cockpit shape, not just procedures.** When an operator activates alpha-trader, their cockpit reshapes to show four faces (mandate, money truth, performance, tracking). When they activate alpha-commerce, the same four faces bind to different substrate. The compositor reads each program's SURFACES.yaml and renders accordingly. A skill can't do this — it's the wrong scope.

**Programs ship capability declarations.** A program declares what platform integrations it needs to function (Alpaca for trading, Stripe for commerce). The kernel checks active platform connections against the program's declared capabilities and either runs the program in operational mode or in knowledge mode (read-only, advisory) when a capability is missing. Skills don't have this layer.

**Programs ship default agent rosters.** A program can declare "this operation needs a researcher, an analyst, and a designer in addition to the standard roster." The activation flow ensures those agents exist with appropriate scope. Skills are agent-agnostic; they don't care who's running them.

**Programs are installable, uninstallable, updatable as a unit.** Activate alpha-trader: the bundle's reference workspace forks into yours, the cockpit reshapes, the agent roster is verified. Deactivate it: the framing leaves, your accumulated data stays. Update the program: canon-tier files re-apply, authored-tier files preserved. Skills don't have this lifecycle — they accumulate but don't have an "uninstall" semantic.

These properties together turn the agent OS into an ecosystem. Anyone can write a program: the trader's program, the marketer's program, the fundraiser's program, the consultant's program. Each ships an opinionated cockpit shape, a starter substrate, and the capability requirements to run it. The OS is the platform; programs are what get built on top.

## Why skills aren't going away

I want to be clear: programs don't replace skills. They sit at a different layer.

Skills are great for: procedural knowledge that's reusable across operations, capabilities that don't need their own cockpit shape, lightweight automations the operator wants to invoke directly, anything where the unit of value is "knowing how to do X."

Programs are great for: shipping an entire opinionated operation, packaging domain expertise as an installable unit, reshaping the cockpit to match a specific use case, distributing capability requirements + substrate layout + agent roster + UI configuration as a coherent bundle.

In our system both exist. Programs reference skills. Skills are invoked by agents inside programs. The skills layer is the procedural commons; the programs layer is the opinionated operational shape that builds on it.

## What this predicts for the agent ecosystem

The current open-source agent wave has settled the skills layer. The agentskills.io standard, the SKILL.md convention, the skill-folders-as-procedural-memory pattern — all converged. Future products will mostly agree on this layer.

The programs layer is open. Most current agent platforms don't have it. They have settings, configurations, templates, prompt presets — but they don't have installable, uninstallable, updatable units that ship cockpit shapes alongside capability declarations and starter substrate.

The first agent platforms to ship a real programs layer — meaning a manifest spec, a composition manifest spec, a reference-workspace fork mechanic, an activation/deactivation lifecycle — will be the ones third parties build on. That's where the agent OS becomes an ecosystem.

Skills made the agent ecosystem composable at the procedure level. Programs make it composable at the operation level. **That's the next layer up, and it's where the platform competition is going.**

## Key Takeaways

- Skills are reusable procedural units (agentskills.io, SKILL.md). They're great for what they're for.
- Programs are higher-order: manifest + reference workspace + composition manifest + capability specs.
- Programs ship an opinionated cockpit shape, capability declarations, default rosters, and starter substrate.
- Programs are installable, uninstallable, and updatable as a unit. Skills accumulate but don't have that lifecycle.
- Skills don't go away — programs sit on top of them at a different layer.
- The first platforms to ship a real programs layer will be the ones third parties build on.
- For the broader frame, read [What Counts as a Program in an Agent OS?](/blog/what-counts-as-a-program-in-an-agent-os) and [The Agent OS Is Real](/blog/the-agent-os-is-real).
