# Conversation-First Onboarding Design

**Date:** 2026-02-02
**Status:** Draft
**Related:** ADR-018 (Deliverables), ADR-020 (TP Scaffolding), ONBOARDING_STARTER_PROMPTS.md

---

## Problem Statement

The current onboarding flow (5-step wizard) front-loads cognitive burden:
- Users must know what "type" of deliverable they want
- Must configure details before seeing any value
- Wizard-first approach contradicts the product's core value prop: "we learn and adapt"

The prior starter prompt design had the right insight: encourage users to share/dump context first, then extract structure. This document specifies how to implement that approach for the deliverables product.

---

## Design Principles

1. **Show, don't tell** — Demonstrate that YARNNN understands and learns by extracting structure from messy input
2. **Value before configuration** — Get to first draft before asking for schedule details
3. **Progressive disclosure** — Start simple, refine later
4. **Two paths, one goal** — Conversation for exploration, wizard for power users

---

## User Experience

### Cold Start Empty State

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│            What do you need to produce regularly?                   │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  Paste an example, describe it, or just tell me what you     │  │
│  │  need to deliver...                                           │  │
│  │                                                               │  │
│  │                                                        [Send] │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Quick starts:                                                      │
│  ┌──────────────────────┐ ┌──────────────────────┐                 │
│  │ "Weekly status       │ │ "Monthly update for  │                 │
│  │  report for my       │ │  my investors"       │                 │
│  │  manager"            │ │                      │                 │
│  └──────────────────────┘ └──────────────────────┘                 │
│                                                                     │
│  ─────────────────────── or ───────────────────────                │
│                                                                     │
│  [ I know exactly what I need → Use step-by-step setup ]           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Conversation Flow Examples

**Example 1: User describes in plain text**

```
User: I need to send my manager weekly updates on what I've been working on

TP: I can set that up for you! A few quick questions:

1. What's your manager's name? (helps me personalize the tone)
2. What day/time works best for delivery? (I'll have drafts ready)

Or if you have a past example you could paste, I can match that style exactly.

User: Her name is Sarah. Friday mornings work best.

TP: Perfect! I've created "Weekly Status Update for Sarah" -
scheduled for Fridays at 9am.

[Tool Result Card: Deliverable Created ✓]
  Weekly Status Update for Sarah
  Status Report • Every Friday at 9:00 AM
  [View & Configure] [Generate First Draft]

Want me to generate the first draft now? I'll ask you about this
week's work and create something you can review.
```

**Example 2: User pastes an old example**

```
User: [pastes 500 words of a previous status report]

TP: I can see this is a weekly engineering status report. Here's
what I noticed:

📋 **Structure extracted:**
- Executive summary (2-3 sentences)
- Accomplishments (bullet points with project names)
- Blockers & risks
- Next week's priorities

📝 **Style notes:**
- Professional but conversational tone
- Uses specific metrics where available
- Includes ticket/PR references

Who receives this report, and when do you usually send it?

User: Goes to my manager David, every Monday

TP: Got it! I've created "Weekly Engineering Update for David"
matching this structure.

[Tool Result Card: Deliverable Created ✓]
  Weekly Engineering Update for David
  Status Report • Every Monday at 9:00 AM
  [View & Configure] [Generate First Draft]

The first draft will follow your existing format. Ready to
generate one now?
```

**Example 3: User clicks quick start**

```
[User clicks "Weekly status report for my manager"]

TP: Let's set that up!

Who's your manager? And what day/time works best for having
the draft ready?

(I'll create a standard status report format - you can always
refine it after seeing the first draft)
```

---

## Technical Implementation

### 1. Frontend: OnboardingChatView Component

New component that replaces the empty state in DeliverablesDashboard for cold-start users.

```typescript
// web/components/deliverables/OnboardingChatView.tsx

interface OnboardingChatViewProps {
  onDeliverableCreated: (deliverableId: string) => void;
  onUseWizard: () => void;
}

export function OnboardingChatView({
  onDeliverableCreated,
  onUseWizard
}: OnboardingChatViewProps) {
  // Uses existing useChat hook
  // Watches for tool_result with deliverable creation
  // Calls onDeliverableCreated when detected

  return (
    <div className="...">
      {/* Header: "What do you need to produce regularly?" */}
      {/* Chat messages area */}
      {/* Input area with paste support */}
      {/* Quick start chips */}
      {/* "Use step-by-step setup" link */}
    </div>
  );
}
```

### 2. Backend: Onboarding-Aware System Prompt

Add onboarding context to TP's system prompt when user has no deliverables.

```python
# In thinking_partner.py

ONBOARDING_CONTEXT = """
## Current Context: New User Onboarding

This user has no deliverables set up yet. Your goal is to help them
create their first recurring deliverable through conversation.

**Approach:**
1. If they paste content, analyze it and extract:
   - Document type (status report, update, brief, etc.)
   - Structure (sections, format, typical length)
   - Tone and style markers
   - Any clues about recipient or schedule

2. If they describe what they need, ask 1-2 clarifying questions:
   - Who receives it? (name and relationship)
   - When should drafts be ready?

3. Once you have enough information, use `create_deliverable` to
   set it up. Don't wait for perfect information - defaults are fine.

4. After creation, offer to generate the first draft immediately
   using `run_deliverable`.

**Key behaviors:**
- Be concise - 2-3 sentences per response max
- Extract structure from examples rather than asking users to define it
- Use sensible defaults (weekly, Monday 9am, professional tone)
- Get to first value (created deliverable) within 2-3 exchanges

**Quick start prompts the user might click:**
- "Weekly status report for my manager"
- "Monthly update for my investors"
- "Bi-weekly competitive brief"

Respond to these by asking for recipient name and preferred timing.
"""
```

### 3. Dashboard Integration

Modify DeliverablesDashboard to detect cold start and show appropriate view.

```typescript
// web/components/deliverables/DeliverablesDashboard.tsx

export function DeliverablesDashboard({ onCreateNew }: Props) {
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [showOnboardingChat, setShowOnboardingChat] = useState(false);

  // ... existing load logic

  // Cold start: no deliverables
  if (!loading && deliverables.length === 0) {
    if (showOnboardingChat) {
      return (
        <OnboardingChatView
          onDeliverableCreated={(id) => {
            setShowOnboardingChat(false);
            loadDeliverables(); // Refresh to show new deliverable
          }}
          onUseWizard={() => {
            setShowOnboardingChat(false);
            onCreateNew(); // Opens existing wizard
          }}
        />
      );
    }

    // Default: show onboarding chat view
    return (
      <OnboardingChatView
        onDeliverableCreated={...}
        onUseWizard={...}
      />
    );
  }

  // ... existing dashboard with deliverables
}
```

### 4. Quick Start Prompts

Pre-defined prompts that users can click to start conversation.

```typescript
const QUICK_START_PROMPTS = [
  {
    label: "Weekly status report for my manager",
    prompt: "I need to send my manager weekly updates on what I've been working on",
  },
  {
    label: "Monthly investor update",
    prompt: "I need to send monthly updates to my investors about company progress",
  },
  {
    label: "Bi-weekly competitive brief",
    prompt: "I want to track my competitors and get a bi-weekly summary of what they're doing",
  },
];
```

### 5. Content Extraction (Future Enhancement)

For pasted content, add a dedicated extraction step before creating deliverable.

```python
# In project_tools.py

ANALYZE_DELIVERABLE_EXAMPLE_TOOL = {
    "name": "analyze_deliverable_example",
    "description": """Analyze a pasted document to extract deliverable structure.

Use this when a user pastes an example of something they produce regularly.
Extract: type, sections, tone, typical length, any schedule/recipient clues.

Returns structured analysis that can inform create_deliverable.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The pasted document content"
            }
        },
        "required": ["content"]
    }
}
```

This is optional - TP can do this analysis inline without a dedicated tool.

---

## Migration Path

### Phase 1: MVP (This Implementation)
- OnboardingChatView component
- Modified empty state in dashboard
- Onboarding context in TP system prompt
- Quick start prompts
- Existing create_deliverable tool handles creation

### Phase 2: Refinements
- analyze_deliverable_example tool for better extraction
- Remember user preferences from onboarding
- Smooth transition to dashboard after first deliverable
- "Add another" flow after first success

### Phase 3: Full Integration
- Unified chat experience (onboarding + ongoing use)
- Context-aware prompts based on existing deliverables
- TP proactively suggests new deliverables based on conversation patterns

---

## Success Metrics

| Metric | Current (Wizard) | Target (Chat-First) |
|--------|------------------|---------------------|
| First deliverable creation rate | TBD | +20% |
| Time to first deliverable | 5+ min | < 2 min |
| Wizard abandonment | TBD | N/A (optional path) |
| First draft generation rate | TBD | +30% |

---

## Open Questions

1. **Session persistence**: Should onboarding chat history persist if user leaves and returns?
   - Recommendation: Yes, use daily session scope (existing behavior)

2. **Wizard deprecation**: Should we eventually remove the wizard entirely?
   - Recommendation: Keep as "Advanced setup" for power users

3. **Mobile experience**: How does this work on smaller screens?
   - Recommendation: Full-screen chat view, similar to existing FloatingChatPanel mobile mode

---

## References

- [ONBOARDING_STARTER_PROMPTS.md](./ONBOARDING_STARTER_PROMPTS.md) - Prior onboarding design
- [ADR-018: Recurring Deliverables](../adr/ADR-018-recurring-deliverables.md)
- [ADR-020: Deliverable-Centric Chat](../adr/ADR-020-deliverable-centric-chat.md)
- [YARNNN_CLAUDE_CODE_BUILD_BRIEF.md](../development/YARNNN_CLAUDE_CODE_BUILD_BRIEF.md)
