# Platform-First User Flows

> **Status**: Design Document
> **Created**: 2026-02-09
> **Related ADRs**: ADR-031, ADR-032, ADR-033, ADR-034

---

## Current State Analysis

After reviewing the codebase, here's the current state of platform-first implementation:

### What's Built ✅

| Component | Location | Platform-First? |
|-----------|----------|-----------------|
| `IdleSurface` | Dashboard | ✅ Shows `PlatformCardGrid` |
| `PlatformCardGrid` | Dashboard | ✅ Shows connected platforms |
| `PlatformDetailPanel` | Slide-out drawer | ✅ Platform drill-down |
| `PlatformDetailSurface` | Full view | ✅ Deep platform management |
| `PlatformOnboardingPrompt` | Cold-start | ✅ Platform-first onboarding |
| `DeliverableCreateWizard` | Modal | ✅ Destination-first (4 steps) |
| `DestinationSelector` | Wizard step 1 | ✅ Platform as first question |
| Backend integrations | API | ✅ Platform-centric drafts |

### The Gap 🔄

The **TP conversation flow** doesn't match the **UI wizard flow**:

| Aspect | UI Wizard (ADR-032) | TP Conversation (Current) |
|--------|---------------------|---------------------------|
| First question | "Where does this go?" | "What do you need?" |
| Platform | Step 1 (required) | Not asked early |
| Destination | Required, prominent | Optional, buried |
| Mental model | Platform → Content → Schedule | Content → maybe destination |

**Root cause**: The TP prompt was designed before ADR-031/032/033 platform-first pivot. It still uses a generic content-first approach.

---

## User Flows Design

### Flow 1: Dashboard → Platform → Deliverable

This is the **primary platform-first path** and is already well-implemented:

```
Dashboard (IdleSurface)
    │
    ├── PlatformCardGrid (forest view)
    │   └── Click platform card
    │       └── PlatformDetailPanel (slide-out)
    │           ├── Resources list
    │           ├── Deliverables targeting this platform
    │           ├── Context from this platform
    │           └── [Create Deliverable] → Wizard with platform pre-filled
    │
    └── [+ New Deliverable] button
        └── DeliverableCreateWizard
            └── Step 1: DestinationSelector (platform-first)
```

**Status**: ✅ Complete

### Flow 2: Dashboard → Quick Create (Generic)

```
Dashboard
    │
    └── [+ New Deliverable]
        └── DeliverableCreateWizard
            ├── Step 1: Destination (choose platform + target)
            ├── Step 2: Type + Title
            ├── Step 3: Sources (auto-suggest from platform)
            └── Step 4: Schedule
```

**Status**: ✅ Complete

### Flow 3: Platform View → Create Deliverable

```
PlatformDetailSurface (e.g., /dashboard?surface=platform-detail&platform=slack)
    │
    └── [+ Create Deliverable for Slack]
        └── DeliverableCreateWizard
            └── Step 1: Skipped (platform pre-filled)
            └── Step 2: Type + Title
            └── ...
```

**Status**: ✅ Complete - Uses `initialDestination` prop

### Flow 4: TP Conversation → Create Deliverable 🔄

This is the **gap**. Current TP flow:

```
User: "I need to send a weekly status report to my manager"

TP (current): "I can help! What should it include?"
              → Generic content-first approach
              → Destination asked late or not at all
```

**Expected platform-first flow**:

```
User: "I need to send a weekly status report to my manager"

TP (platform-first):
    1. "Where should this be delivered?"
       → [Gmail] [Slack] [Notion]

    2. (User selects Gmail)
       "Great, I'll draft it as an email. What's your manager's email?"

    3. "What should the status report cover?"
       → [Your Slack channels] [Your Notion docs] [Everything]

    4. "When should I draft it?"
       → [Weekly - Fridays 4pm]

    5. TP uses create_deliverable tool with:
       - destination: { platform: "gmail", format: "draft", target: "manager@company.com" }
       - sources: [...inferred from conversation]
```

**Status**: ❌ Not implemented

---

## Implementation Plan

### Phase A: TP Platform-First Prompts

Update `api/agents/thinking_partner.py`:

1. **Update system prompt** to emphasize platform-first:
```python
SYSTEM_PROMPT = """
You are Thinking Partner (TP), the user's AI collaborator for
recurring deliverables.

IMPORTANT: When users describe recurring work, ask "where should
this be delivered?" first. The destination platform (Slack, Gmail,
Notion) shapes everything else.

User's connected platforms: {connected_platforms}
"""
```

2. **Update create_deliverable examples** to show platform-first:
```python
# In TOOL_USE_EXAMPLES
"""
User: I need to send weekly updates to my team

TP: Where should these updates go?

User: Slack, in our #team-updates channel

TP: Perfect. I'll set up a Weekly Update that drafts to #team-updates every Friday.
    [uses create_deliverable with destination first]
"""
```

3. **Add platform detection** to TP reasoning:
- If user mentions "email" → suggest Gmail
- If user mentions "channel" or "Slack" → suggest Slack
- If user mentions "page" or "doc" → suggest Notion

### Phase B: TP Tool Update

Update `api/services/project_tools.py`:

1. **Make destination required** in CREATE_DELIVERABLE_TOOL:
```python
CREATE_DELIVERABLE_TOOL = {
    "name": "create_deliverable",
    "input_schema": {
        "required": ["title", "deliverable_type", "frequency", "destination"],  # Add destination
        "properties": {
            "destination": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "enum": ["gmail", "slack", "notion", "download"]},
                    "format": {"type": "string"},
                    "target": {"type": "string", "description": "Channel, email, or page"}
                },
                "required": ["platform"]
            },
            ...
        }
    }
}
```

2. **Update handle_create_deliverable** to use destination:
```python
async def handle_create_deliverable(args: dict, auth: UserClient) -> dict:
    destination = args.get("destination", {"platform": "download", "format": "markdown"})
    # ... create with destination
```

### Phase C: Inline Platform Chips

Add platform selection chips to TP chat when context matches:

```typescript
// web/components/chat/PlatformSelectionChips.tsx
function PlatformSelectionChips({ onSelect }: Props) {
  return (
    <div className="flex gap-2 mt-2">
      <button onClick={() => onSelect('gmail')}>
        <GmailIcon /> Gmail
      </button>
      <button onClick={() => onSelect('slack')}>
        <SlackIcon /> Slack
      </button>
      <button onClick={() => onSelect('notion')}>
        <NotionIcon /> Notion
      </button>
    </div>
  );
}
```

TP can render these when it detects the user is describing a deliverable:
```
TP: "Where should this be delivered?"
    [Gmail chip] [Slack chip] [Notion chip]
```

### Phase D: Platform-Aware Suggestions

When destination is selected, auto-suggest relevant sources:

1. **Gmail destination** → "Would you like to include context from your Slack channels?"
2. **Slack channel destination** → "I can pull from your linked Notion pages"
3. **Notion destination** → "Should I synthesize from your email and Slack?"

---

## User Journey Map

### New User Journey (Platform-First)

```
1. Sign up
   └── PlatformOnboardingPrompt: "Connect your tools"
       ├── Connect Slack → OAuth
       ├── Connect Gmail → OAuth
       └── Connect Notion → OAuth

2. Dashboard (IdleSurface)
   └── PlatformCardGrid shows connected platforms
       └── Each card shows: resources, activity, deliverables

3. Create first deliverable
   Option A: Click platform card → "Create deliverable for Slack"
   Option B: Click "+ New Deliverable" → Wizard starts with destination
   Option C: Chat with TP → "I need a weekly update to #leadership"
            → TP asks: "Where should this go?" (platform-first)

4. Review and approve
   └── Draft appears in platform (Gmail Drafts, Slack DM, Notion)
   └── User reviews, edits, sends

5. Iterate
   └── Quality improves via feedback loop
   └── User can escalate to auto-send after trust is built
```

### Existing User Journey (Maintain Compatibility)

```
1. Login
   └── Dashboard shows:
       ├── PlatformCardGrid (forest view)
       ├── Upcoming Schedule (next deliverables)
       └── Attention Queue (drafts to review)

2. Daily workflow
   ├── Check attention queue → review staged drafts
   ├── Click platform card → see platform-specific activity
   └── Chat with TP for ad-hoc help

3. Create new deliverable
   └── Same as new user, but sources auto-suggested
       from existing platform resources
```

---

## Component Responsibility Map

| Component | Responsibility | Platform-First Role |
|-----------|---------------|---------------------|
| `IdleSurface` | Dashboard home | Shows `PlatformCardGrid` prominently |
| `PlatformCardGrid` | Forest view of platforms | Entry point to platform-specific flows |
| `PlatformDetailPanel` | Quick platform drill-down | Shows deliverables + context for one platform |
| `PlatformDetailSurface` | Full platform management | Deep platform view for power users |
| `DeliverableCreateWizard` | Guided creation | Step 1 = Destination (platform-first) |
| `DestinationSelector` | Platform + target selection | Core platform-first component |
| `FloatingChat` + TP | Conversational interaction | Should use platform-first prompts |
| `PlatformOnboardingPrompt` | Cold-start onboarding | Leads with platform connection |

---

## Success Criteria

1. **New user activation**: >60% connect at least one platform in first session
2. **Destination completion**: >90% of new deliverables have destination set
3. **Platform coverage**: >50% of users connect 2+ platforms within 7 days
4. **TP platform-first**: When users describe recurring work, TP asks "where" before "what"

---

## Next Steps

1. **Immediate**: Update TP system prompt to emphasize platform-first
2. **Short-term**: Add destination to CREATE_DELIVERABLE_TOOL required params
3. **Medium-term**: Add platform selection chips to TP chat UI
4. **Long-term**: Context auto-suggestion based on selected platform

---

## References

- [ADR-031: Platform-Native Deliverables](../adr/ADR-031-platform-native-deliverables.md)
- [ADR-032: Platform-Native Frontend Architecture](../adr/ADR-032-platform-native-frontend-architecture.md)
- [ADR-033: Platform-Centric UI Architecture](../adr/ADR-033-platform-centric-ui-architecture.md)
- [ADR-034: Emergent Context Domains](../adr/ADR-034-emergent-context-domains.md)
