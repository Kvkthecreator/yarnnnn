# Meeting Prep (skill: `prepare`, scope: `cross_platform`)

**Date:** 2026-03-06 (updated 2026-03-12 for ADR-109 terminology)
**Status:** Pass 3 validated (prompt v3)
**Related:** [Agent Skills Reference](agent-types.md), [Agent Framework](../architecture/agent-framework.md), [Quality Testing](../development/agent-quality-testing.md)
**Template:** Meeting Prep (scope: cross_platform, skill: prepare, trigger: recurring)

---

## Overview

Auto Meeting Prep runs every morning, reads the user's Google Calendar, and sends a prep briefing for the day's meetings. Each meeting gets classified by type, and prep depth adapts accordingly. Cross-platform context from Slack, Gmail, and Notion is surfaced for attendee research and topic background.

---

## Calendar dependency

- **Requires Google Calendar** — the agent will not produce useful output without it
- Calendar sync window: -7 days to +14 days (ADR-077)
- Calendar content TTL: 2 days in `platform_content`
- Google OAuth provides both Gmail and Calendar under one `platform="google"` connection

---

## Roll-up window

**Today + early tomorrow** — all meetings from now through end of next calendar day.

- Covers today's full schedule (main value)
- Covers tomorrow morning before the next delivery arrives (no gap between daily deliveries)
- Past versions context prevents re-prepping the same meeting twice
- Output header states the exact window: "Your meetings for Thu Mar 6 – Fri Mar 7 morning"

---

## Meeting classification

The agent classifies each meeting from calendar event metadata and adapts prep depth:

| Classification | Signals | Prep depth |
|---------------|---------|------------|
| **Recurring internal** | "weekly sync", "1:1", "standup", same attendees as before | Brief — what changed since last time, open items from Slack/Notion, decisions needed |
| **External / new contact** | Unfamiliar attendees, "intro", "kickoff" | Thorough — research person/company, relevant email threads, prior Slack/Notion mentions |
| **Large group / all-hands** | Many attendees, "town hall", "all-hands" | Structured — agenda items, key decisions, what user might contribute |
| **Low-stakes / routine** | Casual catch-up, social, no agenda | Minimal — "No specific prep needed. Quick context: [1-2 notes if any]" |

---

## Cross-platform context

The prep is powered by `CrossPlatformStrategy` — sources include calendar plus all other connected platforms:

- **Slack:** attendee mentions in channels, relevant thread discussions
- **Gmail:** recent email threads with attendees, action items
- **Notion:** docs related to meeting topics, recent edits

This is the differentiator — no calendar app alone can surface "what you discussed with this person in Slack last week."

---

## Scheduling

- **Frequency:** Daily only (fixed)
- **Delivery:** Morning, user's timezone (configurable delivery time, default 08:00)
- **Scheduler:** `unified_scheduler.py` — same path as all recurring agents
- **Freshness:** 24-hour freshness requirement (daily batch, not reactive)

---

## Constraints

- **One per user** — enforced at creation time via skill flow duplicate guard
- **Daily only** — no weekly/monthly option (meeting prep is inherently daily)
- **Google Calendar required** — skill checks for connection before creating

---

## Architecture

| Component | File | Notes |
|-----------|------|-------|
| Prompt | `api/services/agent_pipeline.py` | TYPE_PROMPTS["brief"] v3, meeting classification + tool use + BAD/GOOD examples |
| Prompt builder | `api/services/agent_pipeline.py` | `build_type_prompt` brief branch — computes `today_date`, `date_range` |
| Skill flow | `api/services/skills.py` | Auto meeting prep skill — calendar check, delivery time, auto-sources |
| Config schema | `api/routes/agents.py` | `BriefConfig` — `delivery_time` only |
| Type classification | `api/routes/agents.py` | `cross_platform` binding, `scheduled` temporal pattern |
| Execution strategy | `api/services/execution_strategies.py` | `CrossPlatformStrategy` (shared with Work Summary) |
| Scheduler | `api/jobs/unified_scheduler.py` | Standard daily frequency handling |
| Delivery | `api/services/delivery.py` | Email via Resend (generic pipeline) |
| UI starter card | `web/components/desk/ChatFirstDesk.tsx` | "Auto Meeting Prep" card |
| Type label | `web/lib/constants/agents.ts` | `brief: 'Auto Meeting Prep'` |
