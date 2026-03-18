# Frequently Asked Questions

## General

### What is YARNNN?

YARNNN is an autonomous AI work system for recurring knowledge work. It connects to your tools, builds context over time, and runs supervised agents that deliver useful work in the background.

### How is YARNNN different from ChatGPT or Claude?

Chat tools are mostly session-centric. YARNNN is system-centric: it keeps synced work context, runs persistent agents, and improves work quality through supervision and accumulated feedback.

### What is the Thinking Partner?

The Thinking Partner is YARNNN's conversational control layer. In the product it may also be referred to as the Orchestrator. It helps you ask grounded questions, create agents, refine work, and inspect what the system is doing.

### What kind of work can YARNNN do?

Common work patterns include:

- recaps and digests
- meeting prep
- stakeholder status updates
- watch agents for themes or risks
- bounded research
- cross-platform synthesis

## Setup & Integrations

### Which platforms does YARNNN support?

Slack, Gmail, Notion, and Google Calendar.

### Can YARNNN post in Slack, send emails, or edit Notion pages?

Source integrations are read-only for context ingestion. Delivery is separate: YARNNN can send outputs to destinations you configure, but it does not silently modify the source systems it reads from.

### Can I control what YARNNN can see?

Yes. YARNNN starts with smart defaults after connection, and you can refine source coverage at any time.

## Agents

### Do I have to create agents manually?

Not always. Slack, Gmail, and Notion can bootstrap a starter agent after the first sync. You can also create or refine agents through the Thinking Partner. Calendar is primarily schedule context and becomes more valuable once paired with other sources.

### Do agents have run history?

Yes. Every generation creates a run you can inspect and review over time.

### How do agents improve over time?

Each agent learns from prior runs, edits, and instructions. Consistent feedback becomes future behavior.

### What execution modes are available?

- `recurring`
- `goal`
- `reactive`
- `proactive`
- `coordinator`

## Privacy & Security

### Who can see my data?

Only your authenticated account. Data is user-scoped and isolated.

### Does YARNNN train external models on my data?

No. User data is used to power that user's YARNNN experience.

## Plans

### Where can I see current limits?

Check [Plans](../plans/plans.md). Limits are versioned and may evolve with product updates.

### Can I upgrade or downgrade later?

Yes. Plan changes can be handled from billing/subscription flows.
