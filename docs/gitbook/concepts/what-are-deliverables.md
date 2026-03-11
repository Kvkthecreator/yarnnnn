# What Are Agents?

Agents are autonomous work specialists that produce output for you in the background.

Instead of prompting from scratch each time, you configure a agent once and YARNNN runs it on schedule or by intelligent trigger.

## Core idea

You define:

1. **What** you want (`digest`, `brief`, `status`, `watch`, `deep_research`, `coordinator`, `custom`)
2. **How** it should act (`recurring`, `goal`, `reactive`, `proactive`, `coordinator`)
3. **Where** it should pull context from (Slack, Gmail, Notion, Calendar, documents)

After that, YARNNN produces versioned output and improves with each run.

## Why this is different from normal AI chat

- Chat gives you one response per prompt.
- Agents keep running over time.
- Agents maintain their own memory and execution history.
- You supervise outcomes instead of repeatedly operating prompts.

## Typical workflow

1. Generate
2. Review
3. Edit or approve
4. Learn from feedback
5. Run again with better context and behavior

## Example outcomes

- Weekly engineering digest
- Pre-meeting briefing
- Stakeholder status update
- Domain watch with threshold-triggered summaries
- Coordinator that dispatches follow-up agents automatically

## Versioned outputs

Every run creates a new immutable version. You can:

- compare quality over time
- approve/reject versions
- keep a full audit trail of what was generated and when

This is how YARNNN compounds quality instead of resetting every session.
