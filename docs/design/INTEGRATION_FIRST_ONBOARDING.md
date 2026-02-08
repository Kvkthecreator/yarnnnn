# Integration-First Onboarding Design

**Date:** 2026-02-08
**Status:** Draft
**Supersedes:** CONVERSATION_FIRST_ONBOARDING.md (conceptually—both paths still exist)
**Related:** INTEGRATION_FIRST_POSITIONING.md, ADR-030 (Context Extraction)

---

## Problem Statement

The current onboarding flow leads with "describe your deliverable" and treats integrations as an optional enhancement discovered later in Settings. This contradicts the supervision model:

- If users are supervisors, they shouldn't gather context manually
- The integration path delivers better outcomes (fresh context, less ongoing effort)
- Users who don't connect integrations experience yarnnn as a writing assistant, not a supervision system

The onboarding should reflect the fundamental value proposition: **connect your platforms, configure your deliverables, approve the drafts.**

---

## Design Principles

1. **Lead with integrations** — The recommended path is connecting platforms first
2. **Offer both paths** — Manual input still exists for users who prefer it
3. **Explain the trade-off** — Users should understand why integrations are recommended
4. **Value before complexity** — Show what's possible before asking for configuration details
5. **Natural progression** — Manual users should be prompted to connect integrations after first success

---

## The Choice Screen

When a new user lands on an empty dashboard, they see a choice:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                     How should yarnnn get context?                          │
│                                                                             │
│   ┌─────────────────────────────────┐  ┌─────────────────────────────────┐  │
│   │                                 │  │                                 │  │
│   │  Connect your platforms         │  │  Describe it yourself           │  │
│   │  (Recommended)                  │  │                                 │  │
│   │                                 │  │                                 │  │
│   │  ✓ Always fresh context         │  │  ✓ Start immediately            │  │
│   │  ✓ Less work over time          │  │  ✓ No permissions needed        │  │
│   │  ✓ yarnnn discovers patterns    │  │  ✓ You control what's seen      │  │
│   │                                 │  │                                 │  │
│   │  Requires one-time sign-in      │  │  You'll update context          │  │
│   │  per platform                   │  │  manually as things change      │  │
│   │                                 │  │                                 │  │
│   │  [Connect Slack]                │  │  [Start with an example]        │  │
│   │  [Connect Gmail]                │  │                                 │  │
│   │  [Connect Notion]               │  │                                 │  │
│   │                                 │  │                                 │  │
│   └─────────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Recommended badge** — Integration path is visually marked as recommended
2. **Pros listed for both** — Neither path is hidden or deprecated
3. **Trade-off visible** — The cost of each path is stated clearly
4. **Multiple integration options** — User can connect any/all platforms

---

## Path A: Connect Platforms (Recommended)

### Flow

```
1. User clicks [Connect Slack] / [Connect Gmail] / [Connect Notion]
   ↓
2. OAuth flow completes
   ↓
3. yarnnn shows what it can see:
   "Found 12 Slack channels, 3 Gmail labels, 8 Notion pages"
   ↓
4. User configures first deliverable:
   - What do you need to produce? (description)
   - Who receives it? (recipient)
   - When is it due? (schedule)
   - Which sources should inform it? (select from connected)
   ↓
5. yarnnn creates deliverable with integration sources pre-configured
   ↓
6. First draft generated from live context
   ↓
7. User lands in Review view (supervision mode from day one)
```

### Post-Connection UI

After at least one platform is connected:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Connected: Slack (12 channels)                    [+ Connect more]         │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  What recurring deliverable do you need?                                    │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  e.g., "Weekly status report for my manager Sarah, due Mondays"      │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Quick starts:                                                              │
│  [Weekly status report]  [Investor update]  [Client brief]                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Source Selection

After describing the deliverable:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Weekly Status Report for Sarah                                             │
│  Due: Every Monday at 9am                                                   │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Which sources should inform this deliverable?                              │
│                                                                             │
│  Slack:                                                                     │
│  [x] #engineering (high activity)                                           │
│  [x] #product (medium activity)                                             │
│  [ ] #random                                                                │
│  [ ] #general                                                               │
│                                                                             │
│  Time range: [Last 7 days ▾]                                                │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  [Back]                                          [Create & Generate Draft]  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Path B: Describe It Yourself (Alternative)

### Flow

```
1. User clicks [Start with an example]
   ↓
2. Conversation interface appears (existing OnboardingChatView)
   ↓
3. User describes deliverable or pastes example
   ↓
4. TP extracts structure, asks for recipient/schedule
   ↓
5. Deliverable created with sources = [] (empty, manual)
   ↓
6. First draft generated from provided context
   ↓
7. User reviews draft
   ↓
8. After approval: "Connect your platforms to get fresh context every cycle"
```

### Post-First-Approval Prompt

After the user approves their first manually-created deliverable:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ✓ Your first deliverable is approved!                                      │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Want fresh context every cycle?                                            │
│                                                                             │
│  Connect your platforms and yarnnn will pull context automatically—         │
│  no more copy-pasting.                                                      │
│                                                                             │
│  [Connect Slack]  [Connect Gmail]  [Connect Notion]                         │
│                                                                             │
│  [Maybe later]                                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### 1. Choice Screen Component

```typescript
// web/components/onboarding/OnboardingChoiceView.tsx

interface OnboardingChoiceViewProps {
  onConnectPlatform: (platform: 'slack' | 'gmail' | 'notion') => void;
  onStartManual: () => void;
}

export function OnboardingChoiceView({
  onConnectPlatform,
  onStartManual
}: OnboardingChoiceViewProps) {
  return (
    <div className="...">
      {/* Two-column choice layout */}
      {/* Integration path (left, recommended) */}
      {/* Manual path (right, alternative) */}
    </div>
  );
}
```

### 2. Post-Connection Deliverable Setup

```typescript
// web/components/onboarding/IntegrationDeliverableSetup.tsx

interface IntegrationDeliverableSetupProps {
  connectedIntegrations: Integration[];
  onCreateDeliverable: (config: DeliverableConfig) => void;
}

// Shows what's connected, allows describing deliverable,
// then selecting sources from connected platforms
```

### 3. Dashboard Integration

```typescript
// web/components/deliverables/DeliverablesDashboard.tsx

export function DeliverablesDashboard() {
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);

  // Cold start: no deliverables
  if (!loading && deliverables.length === 0) {
    // Check if any integrations connected
    if (integrations.length > 0) {
      // Show IntegrationDeliverableSetup
      return <IntegrationDeliverableSetup ... />;
    } else {
      // Show choice screen
      return <OnboardingChoiceView ... />;
    }
  }

  // ... existing dashboard
}
```

### 4. Backend: Integration-Aware TP Context

When TP is helping with onboarding and user has connected integrations:

```python
INTEGRATION_ONBOARDING_CONTEXT = """
## Current Context: New User with Connected Integrations

This user has connected the following platforms:
{connected_platforms}

Available resources:
{available_resources}

**Your goal:** Help them create their first recurring deliverable that
pulls context from their connected platforms.

**Approach:**
1. Ask what they need to produce regularly
2. Suggest which connected sources would inform it
3. Use `create_deliverable` with integration sources configured
4. Generate first draft from live context
5. Land them in review mode

**Key behaviors:**
- Reference their actual connected sources by name
- Suggest high-activity channels/docs as defaults
- Emphasize that context will be fresh every cycle
"""
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Integration connection rate (day 1) | ~10% | 40%+ |
| First deliverable with integration sources | ~5% | 50%+ |
| Time to first draft | 5+ min | < 3 min |
| User edits on first draft | Heavy | Light-moderate |
| Upgrade to integrations (manual starters) | N/A | 60% by day 7 |

---

## Migration Path

### Phase 1: Choice Screen (This Implementation)
- Add OnboardingChoiceView as new cold-start experience
- Keep existing conversation flow as "manual" path
- Add post-approval integration prompt

### Phase 2: Integration Setup Polish
- Source selection UI with activity indicators
- Scope configuration (time range, max items)
- Preview of what will be pulled

### Phase 3: Smart Defaults
- Auto-suggest sources based on deliverable type
- Learn which channels matter from approval patterns
- Proactive "you might want to add #design" suggestions

---

## Relationship to Existing Components

| Component | Status |
|-----------|--------|
| OnboardingChatView | Keep as manual path entry point |
| DeliverableWizard | Keep as advanced option (link from choice screen) |
| IntegrationImportModal | Reuse for source selection in new flow |
| Settings/Integrations | Still exists for adding more later |

---

## Open Questions

1. **Should we show integration benefits before or after OAuth?**
   - Before: Might convince more users to connect
   - After: Less friction, show value immediately

2. **What if OAuth fails?**
   - Graceful fallback to manual path
   - Retry option visible

3. **Multiple platforms or one at a time?**
   - Current design: Any/all
   - Alternative: Suggest one to start, prompt for more later

---

## Summary

The onboarding shift from "conversation-first" to "integration-first" reflects the fundamental positioning:

**Old onboarding:** Describe what you need → paste examples → review draft → (maybe) connect integrations later

**New onboarding:** Connect your platforms → configure scope → review draft with fresh context → supervise

Both paths lead to the same outcome (a deliverable being produced), but the integration path delivers the full supervision experience from day one.
