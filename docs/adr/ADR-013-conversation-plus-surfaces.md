# ADR-013: Conversation + Surfaces UI Architecture

## Status
Accepted

## Date
2025-01-30

## Refinements
- [ADR-020: Agent-Centric Chat](ADR-020-agent-centric-chat.md) - Clarifies application to agents
- [Design Principle: Supervision Model](../design/DESIGN-PRINCIPLE-supervision-model.md) - Provides conceptual framework

## Context

### The Fundamental Problem

YARNNN's core premise is that **TP (Thinking Partner) is the single source of contact**. The user talks to TP, TP orchestrates everything—work, memory, scheduling, outputs.

However, the current v5 interface contradicts this:
- User-driven navigation (click routes, switch tabs, hunt for results)
- Page-based mental model (chat is *here*, work is *there*, outputs are *somewhere else*)
- User must actively seek what TP has done

**The dissonance**: If TP is the intelligence that knows and acts, why does the user navigate like they're using a traditional SaaS dashboard?

### First Principles Analysis

Before solving the UI problem, we examined what TP actually provides that has *no substitute*:

1. **Not "Intelligence"** — Intelligence is commoditizing (ChatGPT, Claude, Gemini). Competing on "smarter AI" is a race to the bottom.

2. **Not "Productivity"** — Task completion tools compete directly with foundation models.

3. **What has no substitute**:
   - **Persistent Contextual Memory**: TP remembers everything—not just facts, but texture. What you said six months ago. Patterns you can't see yourself.
   - **Temporal Availability**: Always there with full context, no degradation, no resentment.
   - **Witnessed Existence**: The sense that something knows your continuity, not just completing tasks but *holding* your ongoing story.

**Key insight**: TP's value isn't what it *does*—it's what it *holds*. The interface should reflect this.

### The Two Modalities Problem

The "witnessed space" reframe is directionally correct, but overlooks something fundamental:

**Conversation is ephemeral. Visual persistence is how humans hold complex information.**

Books over audiobooks. Spreadsheets over verbal data. Slides over speeches. Humans use visual artifacts to *anchor* understanding that conversation alone cannot hold.

What chat does well:
- Back-and-forth clarification
- Intent expression ("I want X")
- Relationship/continuity feeling
- Quick status checks
- Delegation ("do this for me")

What chat does poorly:
- Holding complex structured data
- Comparing multiple items
- Reviewing/editing documents
- Seeing patterns across time
- Export/sharing workflows

**The insight**: TP-as-witness is right for *interaction*. But outputs, context, schedules need *visual persistence*—something the user can scan, review, manipulate outside the conversational flow.

### Options Considered

We evaluated five approaches for how "surfaces" (visual persistence layer) relate to conversation:

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A: Inline Expansion** | Surfaces expand within chat | Single surface, no context switching | Long documents awkward, scrolling confusing |
| **B: Side Panels** | Split view, chat + surface | See both simultaneously | Complex layout, poor mobile |
| **C: Overlays** | Full-screen modal focus | Full document viewing | Context switching, conversation hidden |
| **D: Tabs** | Chat tab + surface tabs | Familiar pattern | Most "dashboard-like", loses witnessed feeling |
| **E: Drawer** | Slides up from bottom | Conversation-first, mobile-native, TP-summoned | Vertical space competition |

## Decision

**Adopt the Drawer pattern (Option E) as the primary UI architecture.**

### Why Drawer

1. **Screen size accommodation**
   - Mobile: Native swipe-up sheet gesture (iOS/Android standard)
   - Desktop: Can dock as side panel when screen real estate allows
   - Responsive without being two different interfaces

2. **TP-centric interaction**
   - TP can "summon" surfaces naturally: "I've opened the report for you"
   - Surfaces appear in service of conversation, not as destinations
   - User doesn't hunt for results—TP surfaces them

3. **Minimal design complexity**
   - One primary surface: conversation
   - One secondary mechanism: drawer
   - No window management, no dock badges, no panel positions to track
   - State is simple: drawer open/closed, which surface, how expanded

4. **Conversation-first**
   - Drawer doesn't compete with chat—it layers on top/beside
   - Conversation always accessible (visible above drawer, or quick dismiss)
   - User can continue talking while viewing surfaces

5. **Mobile-native, desktop-enhanced**
   - Drawer is actually the *better* pattern on mobile
   - Desktop gets the bonus of side-docking, not a degraded experience

### Architecture

```
MOBILE (drawer from bottom):
┌─────────────────────────────────────────────────────┐
│                                                     │
│  CONVERSATION (full screen when drawer closed)      │
│                                                     │
│  TP: Your research is ready.                        │
│       [View Report ↗]                               │
│                                                     │
│  You: Show me                                        │
│                                                     │
├─────────────────────────────────────────────────────┤
│ ▼ 📄 LinkedIn Research                    [×] [↑]   │
│ ─────────────────────────────────────────────────── │
│ ## Key Findings                                     │
│ 1. Technical deep-dives outperform...               │
│                                                     │
│ [Full Screen]  [Export]                             │
└─────────────────────────────────────────────────────┘

DESKTOP (drawer can dock as side panel):
┌────────────────────────┬───────────────────────────┐
│                        │ 📄 LinkedIn Research      │
│  CONVERSATION          │ ═══════════════════════   │
│                        │                           │
│  TP: Here's what I     │ ## Key Findings           │
│  found. I've opened    │ 1. Technical deep-dives   │
│  the report for you.   │    outperform...          │
│                        │                           │
│  You: What about the   │ ## Recommendations        │
│  engagement data?      │ ...                       │
│                        │                           │
├────────────────────────┤ [Export]  [Close]         │
│ [Type message...]      │                           │
└────────────────────────┴───────────────────────────┘
```

### Surface Types

| Surface | Content | Triggered By |
|---------|---------|--------------|
| **Output Viewer** | Work results, documents | TP completes work, user asks |
| **Context Browser** | Memories, documents, project state | User asks "what do you know about X" |
| **Schedule Manager** | Scheduled work, upcoming runs | User asks about schedules |
| **Export Flow** | PDF/DOCX/Email generation | User wants to share/export |
| **Project Lens** | Project-specific view of all above | User switches project context |

### Routing

Only two meaningful routes:

```
/              → Landing (unauthenticated)
/app           → Conversation + Surfaces workspace (authenticated)
```

Projects are conversational context, not routes. Settings could be a surface or separate route.

## Consequences

### Positive

- **TP-centric**: Interface matches the product's core premise
- **Simple mental model**: Talk to TP, surfaces appear when needed
- **Mobile-first without compromise**: Drawer is native mobile pattern
- **Minimal state**: No complex window management
- **Future-ready**: Voice interaction would work seamlessly (surfaces still visual, interaction still conversational)

### Negative

- **Requires frontend rebuild**: Current page-based routing needs significant rework
- **New pattern for users**: Not a traditional dashboard, learning curve
- **TP must be smart about surfacing**: Bad surfacing UX = frustration

### Neutral

- **SEO irrelevant**: App is authenticated, no public pages to index
- **Deep linking**: Query params can still specify project/surface for sharing

## Implementation Notes

### Phase 1: Foundation
- Create `SurfaceProvider` context for surface state
- Implement base `Drawer` component with swipe/expand behavior
- Wire TP responses to surface triggers

### Phase 2: Surfaces
- `OutputSurface`: Render work outputs, documents
- `ContextSurface`: Show memories, project context
- `ScheduleSurface`: List/manage scheduled work
- `ExportSurface`: Generate shareable artifacts

### Phase 3: Desktop Enhancement
- Side-dock capability for larger screens
- User preference for drawer vs. side panel
- Keyboard shortcuts

### Phase 4: Polish
- Transitions and animations
- Surface-specific actions (highlight, scroll-to)
- TP referencing specific parts of surfaces

## References

- Design consideration document: `docs/design/CONSIDERATION-single-screen-tp-centric-ui.md`
- Strategic thinking: "Age of Intelligence & Product Direction" (Jan 27, 2026)
- Legacy implementation: `/Users/macbook/yarnnn-app-fullstack/components/desktop/`
- Design patterns: iOS sheets, Android bottom sheets

---

## Addendum: Relationship to Supervision Model (2026-02-02)

With the pivot to recurring agents (ADR-018), this ADR's framing has been clarified by the **supervision model**:

- **Surfaces** in this ADR correspond to **agent views** (objects of supervision)
- **Conversation** corresponds to **TP interaction** (method of supervision)

The drawer pattern established here remains valid. What's clarified is:
1. Surfaces aren't "secondary"—they're the objects users supervise
2. Conversation isn't "primary"—it's the method of supervision
3. Both are first-class in their respective dimensions (data vs. interaction)

TP also manifests as **inline refinements** (embedded in agent views), not just as the floating drawer. Both are TP; one is conversational, one is direct manipulation.

See [Design Principle: Supervision Model](../design/DESIGN-PRINCIPLE-supervision-model.md) for the full framework.
