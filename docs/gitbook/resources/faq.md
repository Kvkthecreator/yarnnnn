# Frequently Asked Questions

## General

### What is YARNNN?

YARNNN is an autonomous AI work system that connects to your tools (Slack, Gmail, Notion, Google Calendar), accumulates context, and produces supervised agents on your behalf.

### How is YARNNN different from ChatGPT or Claude?

Most chat tools are prompt-by-prompt and session-centric. YARNNN is system-centric: it runs configured specialists in the background, keeps version history, and improves from execution feedback over time.

### What kind of work can YARNNN do?

YARNNN supports seven agent types:

- `digest`
- `brief`
- `status`
- `watch`
- `deep_research`
- `coordinator`
- `custom`

## Setup & Integrations

### Which platforms does YARNNN support?

Slack, Gmail, Notion, and Google Calendar.

### Can YARNNN post in Slack, send emails, or edit Notion pages?

No. Integrations are read-only for context ingestion.

### Can I control what YARNNN can see?

Yes. You choose sources per platform (channels/labels/pages), and you can update selections at any time.

## Agents

### Do agents have version history?

Yes. Every generation creates an immutable agent version you can review, approve, reject, and compare over time.

### How do agents improve over time?

Each specialist uses prior version feedback and memory to adapt future output. Consistent edits become persistent behavior.

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
