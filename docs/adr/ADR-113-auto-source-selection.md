# ADR-113: Auto Source Selection

> **Status**: Implemented (OAuth → auto-discover → smart defaults → sync → bootstrap project)
> **Date**: 2026-03-16
> **Supersedes**: Portions of ADR-057 (source selection as prerequisite)
> **Related**: ADR-079 (Smart Defaults), ADR-110 (Onboarding Bootstrap), ADR-111 (Agent Composer), ADR-112 (Sync Efficiency)

---

## Context

YARNNN's current onboarding flow requires users to manually select sources (Slack channels, Gmail labels, Notion pages) after connecting a platform, before any sync or agent creation can happen:

```
Connect platform → Redirect to context page → Select sources → Trigger import → Wait for sync → Bootstrap agent
```

This creates three problems:

1. **Cold start friction**: Users must make curation decisions about sources they haven't seen value from yet. "Pick your Slack channels" is a meaningless choice before YARNNN has demonstrated it does anything useful.

2. **Delayed time-to-first-value**: The manual selection step adds a decision-point dropout. Users who connect a platform but don't complete source selection get stuck in a dead state — platform connected but nothing happening.

3. **Misaligned with autonomous model**: YARNNN's product direction is autonomous agents (ADR-111 Composer, ADR-110 Bootstrap). Requiring manual curation as a *prerequisite* contradicts the thesis that YARNNN handles knowledge work autonomously.

## Decision

**Make source selection automatic by default, manual as refinement.**

After OAuth completes:
1. Discover landscape inline in the callback
2. Auto-select sources via `compute_smart_defaults()` (ADR-079, already exists)
3. Kick off first sync immediately (BackgroundTask)
4. Redirect to `/dashboard` (not `/context/{platform}`)
5. Bootstrap agent creation happens naturally when sync completes (ADR-110)

Manual source curation moves from **prerequisite** to **optional refinement** on context pages. Users can add/remove sources at any time after they've already seen first value.

## Flow Change

### Before (v4 — ADR-057)
```
OAuth → Redirect to /context/{platform} → Manual source selection → Import → Sync → Bootstrap
                    ↑ USER BLOCKS HERE
```

### After (v5 — this ADR)
```
OAuth → Auto-discover → Auto-select → Start sync → Redirect to /dashboard → Bootstrap on sync complete
         (inline)        (smart defaults)  (background)    (user sees progress)   (automatic)
```

## Implementation

### 1. OAuth callback (`api/routes/integrations.py`)

After storing tokens, before redirect:
- Call `discover_landscape()` for the provider
- Call `compute_smart_defaults()` with tier limits
- Store landscape + selected_sources in `platform_connections`
- Kick off platform sync as BackgroundTask

### 2. OAuth redirect (`api/integrations/core/oauth.py`)

Change default redirect from `/orchestrator` to `/dashboard`. The dashboard already handles the transitional state (platforms connected, agents pending).

### 3. Dashboard page (`web/app/(authenticated)/dashboard/page.tsx`)

- Empty state: platform cards trigger OAuth directly (already the case)
- Transitional state: reframe from "Select sources to sync" to show sync progress / "your platforms are syncing"
- Remove the prerequisite language about source selection
- Add "Connect more platforms" option

### 4. Context pages (unchanged role, reframed language)

Context pages remain for source refinement:
- Show auto-selected sources with ability to add/remove
- No longer the first-time entry point after connection
- Users discover this when they want to customize, not during onboarding

### 5. Onboarding docs

Update `USER_FLOW_ONBOARDING_V4.md` → V5 reflecting auto-selection.

### 6. Improved `compute_smart_defaults()` heuristics

Since auto-selection is now the primary path (not a fallback), the heuristics were upgraded from simple single-signal sorting to multi-signal scoring. All signals come from existing landscape metadata — zero extra API calls.

**Slack** (was: sort by `num_members`; now: multi-signal score):
- Base: member count (normalized, minor factor — 0-2 points)
- Boost: channel name matches work patterns like `team-`, `eng-`, `product-`, `incident`, `standup` (+3)
- Boost: purpose/topic text contains work keywords like "project", "deploy", "decisions" (+2)
- Penalty: channel name matches noise patterns like `random`, `social`, `watercooler`, `fun` (-5)
- Penalty: purpose/topic text contains noise keywords (-3)
- Penalty: private channels with <3 members (-1, likely DM-like)

**Notion** (was: sort by `last_edited` with Untitled penalty; now: multi-signal score):
- Boost: databases over pages (+3 — databases are usually project trackers, wikis, meeting notes)
- Boost: workspace-level pages (+2 — top-level pages are typically org-important)
- Penalty: Untitled or empty-name pages (-3)
- Tiebreaker: `last_edited` recency

**Gmail** — unchanged (INBOX > SENT > STARRED > user labels, skip noise). Already well-tuned.

**Calendar** — unchanged (select all). Tiny data volume, no filtering needed.

## Costs

- **First sync may include suboptimal sources**: Smart defaults use heuristics (name patterns, purpose text, recency) not user intent. Mitigation: defaults are good enough for first value; user can refine after. Heuristics are tuned to prefer work channels over noise.
- **Landscape discovery adds latency to OAuth callback**: ~1-3 seconds for API calls. Acceptable — user is already waiting for redirect.
- **Slightly higher initial sync cost**: Syncing auto-selected sources that user might later remove. Cost is marginal (platform API reads are cheap, ADR-112 efficiency controls are in place).

## Not Changed

- Context page source selection UI — still works, just not the first-time entry point
- Platform sync worker — syncs whatever's in `selected_sources`, agnostic to how they got there
- Bootstrap logic — still triggered by sync completion, unchanged
- Tier limits — still enforced by `compute_smart_defaults()` max_sources parameter
- Agent quality filtering — the agent decides what's important within synced content (skill prompts, signals, instructions)
