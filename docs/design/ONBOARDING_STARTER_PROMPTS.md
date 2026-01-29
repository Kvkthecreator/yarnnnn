# Onboarding & Starter Prompts Design

**Date:** 2026-01-29
**Status:** Approved
**Related:** ADR-008 (Document Pipeline), FRONTEND_DOCUMENT_INTEGRATION.md

---

## Industry Research Summary

### How Major Players Handle Onboarding

| Pattern | ChatGPT | Claude | Gemini | Notion AI |
|---------|---------|--------|--------|-----------|
| Starter prompts | ✅ 4 cards | ❌ | ✅ 4 cards | ✅ |
| Onboarding survey | ❌ | ❌ | ❌ | ✅ |
| File upload for context | ✅ | ✅ Projects | ✅ | ✅ Workspace |
| Paste/bulk import | ❌ | ❌ | ❌ | ❌ |
| Memory from chat | ✅ Automatic | ❌ | ❌ | ✅ Agent page |
| Explicit "remember" | ✅ | ❌ | ❌ | ✅ |

### Key Industry Patterns

1. **Empty State with Suggested Prompts** (ChatGPT, Gemini)
   - 4 cards showcasing different capabilities
   - Clear header greeting the user
   - Prompts chosen to show breadth of use cases

2. **ChatGPT Memory** ([OpenAI](https://openai.com/index/memory-and-new-controls-for-chatgpt/))
   - Dual mechanism: explicit "remember this" + automatic learning from chats
   - Memory evolves with interactions, not tied to specific chats
   - Users can view/delete memories in settings

3. **Notion's Personalization** ([Candu Blog](https://www.candu.ai/blog/how-notion-crafts-a-personalized-onboarding-experience-6-lessons-to-guide-new-users))
   - Onboarding survey tailors template selection
   - Agent personalization page acts as "memory bank"
   - Context from existing workspace content

4. **Empty State Best Practices** ([Mobbin](https://mobbin.com/glossary/empty-state))
   - Visual cue prompting user to take action
   - Action buttons for immediate resolution
   - New users "almost guaranteed to fail" without thoughtful empty state

---

## YARNNN's Approach

### Core Differentiator

YARNNN is **relationship-oriented** - the TP is YOUR thinking partner, not a generic assistant. Context persists meaningfully and compounds over time.

**Our framing:**
> "Help me get to know you so I can think WITH you better"

**vs ChatGPT's implicit:**
> "Here are things I can do"

### Unique Features

1. **Paste modal** - Quick context dump (no one else has this)
2. **Automatic memory extraction** - Like ChatGPT, but structured
3. **Project organization** - Like Claude Projects, with memory extraction

---

## Approved Design

### Cold Start Empty State

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Welcome! I'm your Thinking Partner.                        │
│                                                             │
│  The more I know about you and your work,                   │
│  the better I can help you think.                           │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 📄 Upload   │  │ 📋 Paste    │  │ 💬 Just     │         │
│  │ a document  │  │ some text   │  │ start       │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  Or try a conversation starter:                             │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ "I'm working on..."                                   │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ "Help me think through a decision"                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Design Decisions

1. **Simpler copy** - Fewer words, more action
2. **3 equal CTAs** - Not a complex hierarchy
3. **2 starter prompts** - Less overwhelming than 4
4. **No "skip" button** - All paths lead to value

### Behaviors

| Action | Result |
|--------|--------|
| Upload a document | Opens file picker → triggers existing drag-drop upload flow |
| Paste some text | Opens paste modal → bulk import API |
| Just start | Focuses chat input, hides welcome |
| Starter prompt | Pre-fills input with prompt text |

---

## State Detection

```typescript
type OnboardingState =
  | "cold_start"      // No memories, no documents, no chat history
  | "minimal_context" // <3 memories, no recent chat
  | "active"          // Has context, ready to chat

async function getOnboardingState(userId: string): Promise<OnboardingState> {
  const [memoryCount, documentCount, recentChat] = await Promise.all([
    api.userMemories.count(),
    api.documents.count(),
    api.chat.hasRecentSession() // within last 7 days
  ]);

  if (memoryCount === 0 && documentCount === 0) return "cold_start";
  if (memoryCount < 3 && !recentChat) return "minimal_context";
  return "active";
}
```

### UI by State

| State | UI |
|-------|-----|
| cold_start | Full welcome with 3 CTAs + 2 starter prompts |
| minimal_context | Subtle banner: "I don't know much about you yet" |
| active | Normal chat, optional contextual starters |

---

## Starter Prompts

### Static Prompts (Cold Start)

```typescript
const COLD_START_PROMPTS = [
  "I'm working on...",
  "Help me think through a decision",
];
```

### Dynamic Prompts (Active Users)

```typescript
async function getStarterPrompts(userId: string, projectId?: string): Promise<string[]> {
  const prompts: string[] = [];

  // Project-specific
  if (projectId) {
    const project = await api.projects.get(projectId);
    prompts.push(`What should I focus on for ${project.name}?`);
  }

  // Recent documents
  const recentDocs = await api.documents.list({ limit: 1 });
  if (recentDocs.length > 0) {
    prompts.push(`Help me apply insights from ${recentDocs[0].filename}`);
  }

  // General thinking
  prompts.push("Help me think through a decision I'm facing");

  return prompts.slice(0, 2);
}
```

---

## Paste Modal (Bulk Import)

```
┌─────────────────────────────────────────────────────────────┐
│  📋 Paste Context                                      [X]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Paste meeting notes, project briefs, or any text that      │
│  helps me understand your work.                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                     │    │
│  │  [Large textarea]                                   │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  This will be processed to extract key information.         │
│                                                             │
│                              [Cancel]  [Import Context]     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Backend:** Uses existing `/api/memories/bulk-import` endpoint.

---

## Implementation Phases

### Phase 1: Cold Start Welcome
- [ ] Create `WelcomePrompt.tsx` component
- [ ] Add `useOnboardingState` hook
- [ ] Integrate into Chat component (replace empty state)
- [ ] Connect upload CTA to existing flow

### Phase 2: Paste Modal
- [ ] Create `BulkImportModal.tsx` component
- [ ] Integrate with bulk-import API
- [ ] Show processing feedback
- [ ] Transition to chat after import

### Phase 3: Starter Prompts
- [ ] Add click-to-fill behavior
- [ ] Dynamic prompts for active users
- [ ] API endpoint for personalized suggestions

### Phase 4: Polish
- [ ] Dismissible state with localStorage
- [ ] Animate transitions
- [ ] Mobile optimization

---

## Success Metrics

| Metric | Description |
|--------|-------------|
| First-message rate | % of new users who send a message |
| Context density D1 | Average memories after first session |
| Starter prompt usage | % sessions starting with suggestion |
| Upload conversion | % of users who upload in first session |

---

## References

- [OpenAI Memory Feature](https://openai.com/index/memory-and-new-controls-for-chatgpt/)
- [OpenAI Memory FAQ](https://help.openai.com/en/articles/8590148-memory-faq)
- [Empty State UI Pattern - Mobbin](https://mobbin.com/glossary/empty-state)
- [Notion Personalized Onboarding](https://www.candu.ai/blog/how-notion-crafts-a-personalized-onboarding-experience-6-lessons-to-guide-new-users)
- [Notion 3.0 AI Agents](https://www.notion.com/blog/introducing-notion-3-0)
- [Claude vs ChatGPT - Zapier](https://zapier.com/blog/claude-vs-chatgpt/)
