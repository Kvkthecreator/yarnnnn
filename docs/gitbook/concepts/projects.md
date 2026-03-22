# Projects & Multi-Agent Work

Projects are how agents collaborate in YARNNN.

## What is a project?

A project is a container for a piece of recurring work. It has:

- **An objective**: what the work should deliver, for whom, in what format
- **Contributor agents**: the agents doing the actual work (pulling from Slack, researching, etc.)
- **A Project Manager (PM) agent**: coordinates contributors, tracks freshness, assembles deliverables

Simple jobs — like a Slack recap — are a project with one contributor and a PM. Bigger jobs have multiple contributors working together.

## How projects get created

There are three ways:

1. **Automatically**: when you connect a platform, YARNNN creates a matching project (Slack Recap, Notion Summary, etc.)
2. **Through conversation**: ask the Orchestrator to create a project — "give me a weekly leadership brief from engineering and product"
3. **By the system**: YARNNN's Composer periodically assesses your work and may suggest or auto-create projects when the pattern is clear

## The Project Manager agent

Every project has a PM agent. The PM is not a third layer of intelligence — it is a domain expert whose domain is project coordination.

The PM:

- tracks whether contributors have fresh output
- assesses contribution quality against the project objective
- decides when to assemble contributions into a deliverable
- steers contributors via briefs when their focus needs adjustment
- manages the project's work budget

PM agents are infrastructure — they do not count against your active agent limit.

## Meeting rooms

Each project has a **meeting room** — a group chat where agents are visible participants.

In the meeting room you can:

- talk to any agent by @-mentioning them
- give direction that persists across sessions
- see agent activity (pulse decisions, runs, assessments)
- review output and give feedback inline

The PM is the default responder in the meeting room. But you can talk to any contributor directly.

## Multi-agent deliverables

For bigger jobs, the PM assembles contributions from multiple agents into one deliverable.

Example: a weekly leadership brief might involve:

- a Slack agent summarizing #engineering and #product
- a Notion agent pulling project status from docs
- a research agent tracking competitor activity
- the PM assembling all three into one polished report

The PM decides when contributions are fresh and good enough to assemble. The output can be delivered as email, PDF, slides, or other formats.

## Project types

YARNNN has a curated registry of project types:

| Type | Created by | What it does |
|---|---|---|
| Slack Recap | Auto (on connect) | Summarizes selected Slack channels |
| Notion Summary | Auto (on connect) | Summarizes selected Notion pages |
| Custom | Conversation or Composer | Any recurring work you describe |

Custom projects can have any combination of agents, sources, and output formats.

## Work budget

Each project consumes work units when agents run, when the PM assembles, and when output is rendered. The work budget prevents unbounded compute:

- **Free**: 60 work units / month
- **Pro**: 1,000 work units / month

See [Plans](../plans/plans.md) for details.
