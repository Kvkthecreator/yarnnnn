# ADR-053: Platform Sync as Monetization Base Layer

> **Status**: Accepted
> **Date**: 2026-02-12
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-038 (Filesystem-as-Context), ADR-050 (MCP Gateway), LIMITS.md

---

## Context

### The Realization

Platform sync (Slack channels, Gmail labels, Notion pages, Calendar) is the **foundational layer** of YARNNN's value proposition:

1. **Sync IS context** - Per ADR-038, synced platform content feeds TP directly
2. **Sync cost is low** - No LLM calls, just API fetches + storage (~$0.003/user/day)
3. **Sync solves cold start** - New users have context immediately after connecting
4. **Sync enables monetization** - More sources = more value = upgrade path

### The Analogy

```
Claude Code : Filesystem :: YARNNN : Platform Integrations

Claude Code reads files → files ARE the context
YARNNN syncs platforms → synced content IS the context
```

Both are "git pull"-like operations - data movement, not intelligence.

### Current State

LIMITS.md defines generous free tier limits (5 Slack channels, 3 Gmail labels, etc.) but this:
- Creates decision paralysis for new users
- Delays time-to-value (more config before first conversation)
- Misses monetization opportunity at base layer

---

## Decision

### 1. Tighter Free Tier for Faster Onboarding

**Principle**: "1 source per platform" - enough to experience value, clear upgrade path.

| Resource | Old Free | New Free | Rationale |
|----------|----------|----------|-----------|
| Slack channels | 5 | **1** | Pick your most important channel |
| Gmail labels | 3 | **1** | Default to INBOX |
| Notion pages | 5 | **1** | One workspace page |
| Calendars | 3 | **1** | Primary calendar |
| Platforms | 3 | **2** | Pick 2 to start |

### 2. Revised Tier Structure

| Resource | Free | Starter ($9/mo) | Pro ($19/mo) |
|----------|------|-----------------|--------------|
| **Platforms** | 2 | 4 | 4 |
| **Slack channels** | 1 | 5 | 20 |
| **Gmail labels** | 1 | 5 | 15 |
| **Notion pages** | 1 | 5 | 25 |
| **Calendars** | 1 | 3 | 10 |
| **Sync frequency** | 2x/day | 4x/day | Hourly |
| **TP conversations** | 20/mo | 100/mo | Unlimited |
| **Deliverables** | 3 active | 10 active | Unlimited |

**Price Point Rationale:**
- **$9/mo Starter**: Solo users who want "enough" - comparable to Notion/Slack premium
- **$19/mo Pro**: Power users with multiple active projects - comparable to productivity tool bundles
- No Enterprise tier yet (defer until demand)

### 3. Sync Frequency by Tier

| Tier | Frequency | Schedule | Rationale |
|------|-----------|----------|-----------|
| Free | 2x/day | 8am, 6pm local | Morning + evening catch-up |
| Starter | 4x/day | Every 6 hours | Working hours coverage |
| Pro | Hourly | Every hour | Near real-time awareness |

**Why not real-time for Pro?**
- Hourly is sufficient for "what's happening" awareness
- Real-time adds webhook complexity without proportional value
- Can upgrade to webhooks later if demand exists

### 4. Counting Model: Synced Sources, Not Connections

**Decision**: Count **synced sources** (channels, labels, pages), not platform connections.

**Rationale**:
- A Slack "connection" without channels gives zero context
- Value scales with sources synced, not OAuth links
- Clearer mental model: "You can sync 1 Slack channel on free tier"

**Example**:
```
Free user connects Slack → can select 1 channel to sync
Free user connects Gmail → can select 1 label to sync (INBOX default)
Free user connects Notion → can select 1 page to sync
Free user connects Calendar → syncs 1 calendar (primary)

Total: 4 connections, 4 synced sources, 2 platform limit = must choose 2 platforms
```

---

## Onboarding Flow Impact

### Before (Current)

```
1. Sign up
2. Land on empty dashboard
3. "Connect your platforms" (4 options)
4. OAuth flow
5. "Select sources to sync" (multiple checkboxes)
6. Wait for first sync
7. Start chatting (finally has context)
```

**Problems**: Too many choices, delayed gratification, cold start

### After (Proposed)

```
1. Sign up
2. "Connect one platform to get started" (guided choice)
3. OAuth flow
4. "Pick your most important [channel/inbox/page]" (single selection)
5. Immediate sync (foreground, not background)
6. "Let's chat! I can see your [channel name] now."
7. Later: "Want more context? Connect another platform"
```

**Benefits**:
- Single choice at each step
- Immediate value demonstration
- Natural upgrade nudge

### Cold Start Solution

The "1 source immediate sync" approach solves cold start:

| Stage | Context Available |
|-------|-------------------|
| Sign up | None |
| After 1st connection | 1 channel/label/page of content |
| First TP conversation | "I see you have messages in #engineering about..." |

User experiences value in first conversation, not after configuring everything.

---

## Frontend Visibility Requirements

### Context Page Must Show Sync Status

Per earlier discussion, users need visibility into "what does YARNNN know?"

**Required UI Elements**:

1. **Sync status per source**
   ```
   #engineering
   ✅ Synced • 142 messages • Last sync: 2 hours ago
   ```

2. **Next sync indicator**
   ```
   Next sync in 4 hours (Upgrade to Starter for 4x/day)
   ```

3. **Content preview** (ADR-052)
   - Show recent synced items from `ephemeral_context`
   - Not memories - actual platform content

4. **Upgrade prompts at limits**
   ```
   ⚠️ You're using 1 of 1 Slack channels
   [Upgrade to Starter] for 5 channels
   ```

---

## Cost Analysis

### Per User Monthly Cost (Infrastructure)

| Tier | Sync Ops/Day | API Calls/Mo | Storage | Est. Cost |
|------|--------------|--------------|---------|-----------|
| Free | 2 | ~120 | ~5MB | $0.05/mo |
| Starter | 4 | ~500 | ~20MB | $0.15/mo |
| Pro | 24 | ~3000 | ~100MB | $0.50/mo |

**Margin Analysis**:
- Free: Acceptable loss leader
- Starter ($9): ~$8.85 margin = 98%
- Pro ($19): ~$18.50 margin = 97%

Sync-only (no LLM) makes this highly profitable at the infrastructure layer.

### LLM Costs (Separate)

TP conversations and deliverables consume LLM tokens:
- Average conversation: ~$0.02-0.05
- Average deliverable generation: ~$0.05-0.10

These are covered by conversation/deliverable limits per tier, not sync limits.

---

## Implementation Plan

### Phase 1: Update Limits (This ADR)

1. Update `LIMITS.md` with new tier structure
2. Update `api/services/platform_limits.py` with new values
3. Add `sync_frequency` to tier configuration

### Phase 2: Onboarding Flow

1. Redesign connection flow for "1 source" guided experience
2. Implement immediate foreground sync on first connection
3. Add "Connect another platform" prompt after first conversation

### Phase 3: Sync Scheduling

1. Implement tier-based sync frequency
2. Add "next sync" indicator to UI
3. Background scheduler respects tier limits

### Phase 4: Billing Integration

1. Stripe integration for Starter/Pro tiers
2. Upgrade/downgrade flows
3. Grace period for downgrades (keep sources, pause sync)

---

## Consequences

### Positive

1. **Faster onboarding** - Single choice at each step
2. **Clear value prop** - "More sources = more context = smarter TP"
3. **Natural monetization** - Upgrade when you hit limits
4. **Low infrastructure cost** - Sync is cheap, margins are high
5. **Cold start solved** - First conversation has context

### Negative

1. **Tighter free tier** - Some users may feel restricted
2. **Sync frequency complexity** - Different schedules per tier
3. **Migration needed** - Existing users may exceed new limits

### Mitigations

- **Free tier restriction**: Clear upgrade value prop, not paywalled core features
- **Sync complexity**: Abstract behind "freshness" concept in UI
- **Migration**: Grandfather existing users, apply limits to new signups only

---

## Alternatives Considered

### A. Keep Generous Free Tier

**Rejected**: Delays monetization, causes decision paralysis, no upgrade incentive.

### B. Real-time Sync for Pro

**Rejected**: Webhook complexity not worth it. Hourly is sufficient for "awareness" use case. Can add later if demanded.

### C. Count Connections, Not Sources

**Rejected**: A connection without synced sources provides no value. Sources are the value unit.

### D. Deliverable-based Monetization Only

**Rejected**: LLM costs are variable and harder to predict. Sync limits are predictable and low-cost to serve.

---

## Success Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| Time to first TP message | < 5 min | Fast onboarding |
| Free → Starter conversion | > 10% | Upgrade path works |
| Sync limit hits (free) | > 50% | Limits are meaningful |
| Churn after upgrade | < 5%/mo | Upgrade delivers value |

---

## See Also

- [ADR-038: Filesystem-as-Context](ADR-038-filesystem-as-context.md)
- [ADR-050: MCP Gateway Architecture](ADR-050-mcp-gateway-architecture.md)
- [ADR-052: Platform Context Surface](ADR-052-platform-context-surface.md)
- [LIMITS.md](../../monetization/LIMITS.md)
