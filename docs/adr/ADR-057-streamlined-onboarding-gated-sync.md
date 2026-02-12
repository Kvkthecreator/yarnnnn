# ADR-057: Streamlined Onboarding with Gated Sync

**Status**: Accepted
**Date**: 2026-02-13
**Related**: ADR-053 (Platform Sync Monetization), ADR-056 (Per-Source Sync)

## Context

The current onboarding flow has multiple steps:
1. User sees welcome screen with "Connect Slack, Gmail, or Notion" link
2. User navigates to `/settings?tab=integrations`
3. User connects platform via OAuth
4. User is redirected back to settings
5. User must navigate to `/context/[platform]` to select sources
6. User selects sources and saves
7. User is prompted to import now or wait for scheduled sync

This flow is **too fragmented**. Users lose momentum navigating between settings, context pages, and the dashboard. The value proposition isn't immediately clear.

### What We Want

Per ADR-053, we want to:
- **Entice connections** with actual sync value (gated by tier limits)
- **Reduce decision paralysis** with "pick 1 source" for free tier
- **Demonstrate immediate value** by syncing as soon as a source is selected
- **Streamline the journey** from signup → first conversation with context

## Decision

### 1. One-Click Connect from Dashboard

Replace the current "Connect Slack, Gmail, or Notion" link with **inline connect buttons** that start OAuth directly:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Welcome to yarnnn                           │
│                                                                 │
│  I'm your Thinking Partner. Connect a platform to get started. │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │  Slack   │ │  Gmail   │ │  Notion  │ │ Calendar │          │
│  │ Connect  │ │ Connect  │ │ Connect  │ │ Connect  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                 │
│  Free plan: 1 source per platform, syncs 2x daily              │
│                                                                 │
│  [Skip for now]                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key change**: Buttons call `api.integrations.getAuthorizationUrl(provider)` directly, no navigation to settings required.

### 2. Post-OAuth Source Selection Modal

After OAuth callback, instead of redirecting to `/context/[platform]`, show an **inline modal** on the dashboard:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Slack Connected ✓                           │
│                                                                 │
│  Pick 1 channel to start building context:                      │
│                                                                 │
│  ○ #general              127 members                            │
│  ○ #engineering          45 members                             │
│  ○ #product-updates      89 members                             │
│  ○ #random               200 members                            │
│                                                                 │
│  Free tier: 1 channel. Upgrade for more.                       │
│                                                                 │
│  [Skip] [Start Syncing →]                                      │
└─────────────────────────────────────────────────────────────────┘
```

**Key behaviors**:
- Shows up to 10 most-populated resources from landscape discovery
- Free tier: can only select 1
- Starter/Pro: can select multiple up to tier limit
- "Start Syncing" triggers immediate foreground import

### 3. Immediate Foreground Sync

When user clicks "Start Syncing":
1. Modal shows sync progress: "Importing last 7 days from #engineering..."
2. Sync runs in foreground (blocking, ~10-30 seconds typically)
3. On completion, modal dismisses and shows success banner
4. User can immediately start chatting with TP having context

This creates the **"aha moment"** quickly - user connects → picks channel → sees context available → chats with TP that knows their work.

### 4. Connected Platforms in Welcome Screen

After first platform is connected, welcome screen changes:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Welcome to yarnnn                           │
│                                                                 │
│  I'm your Thinking Partner with context from:                   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ● Slack  #engineering  127 items · synced 2 min ago     │   │
│  │   [Manage] [+ Add channel]                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │  Gmail   │ │  Notion  │ │ Calendar │                        │
│  │ Connect  │ │ Connect  │ │ Connect  │                        │
│  └──────────┘ └──────────┘ └──────────┘                        │
│                                                                 │
│  [Create a deliverable] [What can you do?]                     │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight**: Connected platforms are **promoted** above unconnected ones, showing actual value (items synced, recency).

### 5. Gated Sync That Entices

The sync IS the value. Free tier gets:
- **Actual sync** (not a placeholder or demo)
- **Actual context** in TP conversations
- **Limited to 1 source** per platform (clear upgrade lever)

When user tries to add a 2nd source:
```
┌─────────────────────────────────────────────────────────────────┐
│  You've reached your free tier limit (1 channel)               │
│                                                                 │
│  Upgrade to Starter ($9/mo) for:                               │
│  • 5 Slack channels                                             │
│  • 5 Gmail labels                                               │
│  • 4x daily sync (vs 2x)                                        │
│                                                                 │
│  [Maybe later] [Upgrade →]                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation

### Phase 1: Dashboard Connect Buttons

1. Update `PlatformSyncStatus.tsx` to include connect buttons for unconnected platforms
2. Add OAuth initiation directly from dashboard (no navigation)
3. Handle OAuth callback with `?provider=X&status=success` to trigger source selection modal

### Phase 2: Source Selection Modal

1. Create `SourceSelectionModal.tsx` component
2. Fetch landscape on modal open
3. Enforce tier limits in selection
4. Trigger foreground import on "Start Syncing"

### Phase 3: Foreground Import with Progress

1. Create `/api/integrations/import-foreground` endpoint
2. Runs import synchronously (with timeout protection)
3. Returns progress updates via streaming or polling

### Phase 4: Enhanced Welcome Screen

1. Update `ChatFirstDesk.tsx` welcome section
2. Show connected platforms with stats
3. Promote "Add more sources" for connected platforms

## Migration

- Existing users: No change needed (they can use /context pages)
- New users: Get streamlined flow by default
- No breaking changes to existing flows

## Alternatives Considered

### A. Keep Navigation to /context

**Pro**: Simpler implementation
**Con**: Loses momentum, higher drop-off

### B. Full-page Wizard

**Pro**: More guided
**Con**: Feels heavy, blocks main UI

### C. Background-only Sync

**Pro**: Non-blocking
**Con**: User doesn't see value immediately

## Metrics

Track:
- Time from signup to first platform connection
- Time from connection to first TP conversation with context
- Conversion rate: free → starter after hitting limits
- Drop-off rate at source selection step

## Open Questions

1. Should we auto-select the most popular source for free tier users?
2. How long to wait for foreground sync before timing out and switching to background?
3. Should "Skip for now" still show on subsequent visits?