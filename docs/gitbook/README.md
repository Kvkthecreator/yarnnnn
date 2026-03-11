# YARNNN — AI That Works While You Don't

YARNNN is an AI work agent that connects to your everyday tools, learns how you work, and produces real output on your behalf — automatically, on a schedule, improving over time.

## The problem

You spend hours every week on repetitive knowledge work: summarizing Slack threads, prepping for meetings, writing status updates, and staying on top of email. AI chatbots can help, but only when you remember to open them, paste context, and prompt from scratch.

## How YARNNN is different

YARNNN is not a chatbot you talk to when you need help. It's an autonomous AI work system that continuously syncs your work context and runs specialist agents in the background.

| Traditional AI tools | YARNNN |
|---|---|
| You paste context every time | Connects to your tools and stays up to date |
| Forgets everything between sessions | Accumulates memory and context over time |
| You do the work, AI assists | AI does the work, you supervise |
| On-demand only | Runs on schedule or by intelligent trigger |

## What you can do with YARNNN

- Generate recurring digests, briefs, and status updates automatically
- Run proactive or reactive specialists that surface signal when it matters
- Ask context-grounded questions across Slack, Gmail, Notion, and Calendar
- Trigger agents from YARNNN, Claude, or ChatGPT via MCP connector
- Improve quality over time as agents learn from your edits

## How it works

1. Connect your tools
2. Configure agents (type + mode + sources)
3. Review and supervise outputs
4. Let each specialist improve through execution history

## Get started

- [Quickstart guide](getting-started/quickstart.md)
- [What are agents?](concepts/what-are-agents.md)
- [Agent types and modes](concepts/agent-types-and-modes.md)
- [Versioning & sync](resources/versioning.md)

## Maintainer note

To refresh GitBook changelog/version metadata from recent commits:

```bash
python3 scripts/sync_gitbook.py
```
