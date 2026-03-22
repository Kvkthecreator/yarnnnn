# Frequently Asked Questions

## General

### What is YARNNN?

YARNNN is an AI agent platform for recurring knowledge work. It connects to your tools, runs persistent agents in the background that deliver real work on schedule, and improves through supervision and accumulated feedback.

### How is YARNNN different from ChatGPT or Claude?

Chat tools are session-based — they help in the moment but reset when you close the tab. YARNNN is system-based: it maintains synced context from your work tools, runs agents on schedule without you, and learns from your feedback over time. The output gets better the longer it runs.

### What kind of work can YARNNN do?

Common work patterns include:

- weekly team updates and recaps
- competitor monitoring and research
- cross-platform status reports
- rendered deliverables (PDF, slides, spreadsheets)

### What does "autonomous" mean here?

Agents run in the background on schedule — you don't need to prompt them. They pull fresh context from your connected tools, produce work, and deliver it. You review and redirect when needed. Over time, they require less supervision.

## Setup & Integrations

### Which platforms does YARNNN support?

Slack and Notion.

### Can YARNNN post in Slack or edit Notion pages?

Source integrations are read-only for context ingestion. Delivery is separate: YARNNN can send outputs to destinations you configure, but it does not silently modify the source systems it reads from.

### Can I control what YARNNN can see?

Yes. YARNNN starts with smart defaults after connection, and you can refine source coverage at any time.

## Agents & Projects

### Do I have to create agents manually?

No. When you connect a platform, YARNNN automatically creates a project with agents matched to your workflow. You can also create projects through conversation — just describe what you need in plain language.

### What are projects?

Projects are how agents collaborate. A project has an objective, one or more contributor agents, and a Project Manager agent that coordinates their work and assembles deliverables. Simple jobs (like a Slack recap) are a project with one agent. Bigger jobs have multiple agents working together.

### Can I talk to agents directly?

Yes. Each project has a meeting room where you can talk to any agent. Give direction, ask questions, or redirect focus. Your instructions persist across sessions — agents remember what you told them.

### How do agents improve over time?

Each agent learns from prior runs, edits, and your direct feedback. They also accumulate domain knowledge — understanding your team, projects, and communication patterns more deeply with each cycle.

### What output formats are available?

Agents can produce plain text, email-ready content, PDFs, slide decks (PPTX), spreadsheets (XLSX), charts, and more. The format depends on the job.

### Do agents have run history?

Yes. Every generation creates a run you can inspect and review over time.

## Privacy & Security

### Who can see my data?

Only your authenticated account. Data is user-scoped and isolated.

### Does YARNNN train external models on my data?

No. User data is used to power that user's YARNNN experience.

## Plans

### Where can I see current limits?

Check [Plans](../plans/plans.md). Limits are versioned and may evolve with product updates.

### What are work units?

Work units measure autonomous work — agent runs, report assemblies, and rendered output. Free includes 60/month, Pro includes 1,000/month. Messages (conversations with agents) are counted separately.

### Can I upgrade or downgrade later?

Yes. Plan changes can be handled from billing/subscription flows.
