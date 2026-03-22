# How YARNNN Works

YARNNN is built around a simple product loop:

`connect → sync → first agents → feedback → better agents`

## 1. Connect

You connect Slack, Gmail, Notion, or Google Calendar through OAuth.

YARNNN gets read-only access so it can understand your work context, not act inside those tools.

## 2. Perceive

After connection, YARNNN discovers the available sources and syncs the selected coverage into its shared context layer.

This is the raw substrate:

- Slack messages
- Gmail threads
- Notion pages and databases
- Calendar events
- uploaded files and documents

## 3. Bootstrap

YARNNN does not expect you to configure everything manually before seeing value.

After the first sync, it creates a matching project with agents for the platform you connected. That gives you a real work product quickly instead of leaving you on an empty dashboard.

For example:

- Connect Slack → YARNNN creates a Slack Recap project with a digest agent
- Connect Gmail → YARNNN creates a Gmail Digest project
- Connect Notion → YARNNN creates a Notion Summary project

Each project includes a Project Manager agent that coordinates delivery.

## 4. Supervise

You review what the system produces.

- keep it as-is when it is good
- edit when it misses the mark
- talk to agents directly in their meeting room to redirect their focus

This is the trust model. YARNNN starts supervised and improves from real feedback.

## 5. Accumulate

YARNNN gets better because it accumulates more than raw platform data.

Over time it builds on:

- synced platform context
- prior agent runs
- your edits and follow-up direction
- standing preferences and instructions
- agent domain knowledge and self-assessments

That accumulation is what lets later output feel specific instead of generic.

## 6. Compose

The system periodically evaluates what attention your work seems to need.

That can lead to:

- refining an existing agent
- suggesting a new project
- automatically scaffolding additional agents when the pattern is obvious

This is how the system moves from one starter project to a small workforce of useful specialists.

## Two kinds of interaction

YARNNN has two primary interaction modes:

- **Meeting rooms**: each project has a meeting room where you can talk to any agent directly — give direction, ask questions, or adjust focus. Your instructions persist across sessions.
- **Global orchestrator**: a conversational layer for system-wide questions, creating new projects, and supervising the overall workforce.

Meeting rooms are where most day-to-day interaction happens. The orchestrator is for bigger-picture decisions.

## Agents work together

For bigger jobs, multiple agents collaborate within a [project](projects.md).

One agent might pull from Slack, another from Gmail, another does research — then the Project Manager agent assembles their contributions into one polished deliverable. You get a finished product, not fragments.

This coordination happens automatically. The PM agent tracks contribution freshness, assesses quality, and decides when to assemble.
