# Design Consideration: Rethinking the Interface Paradigm

> **Status**: Resolved
> **Date**: 2025-01-30
> **Updated**: 2026-02-02
> **Type**: First-principles exploration
> **Decisions**:
> - [ADR-013](../adr/ADR-013-conversation-plus-surfaces.md): Drawer pattern adopted
> - [ADR-020](../adr/ADR-020-deliverable-centric-chat.md): Deliverable-centric application
> - [Design Principle: Supervision Model](DESIGN-PRINCIPLE-supervision-model.md): Unified framework

---

## The Fundamental Tension

YARNNN's core premise: **TP is the single source of contact**. The user talks to TP, TP orchestrates everything—work, memory, scheduling, outputs.

But our current interface contradicts this:
- User-driven navigation (click routes, switch tabs, hunt for results)
- Page-based mental model (chat is *here*, work is *there*, outputs are *somewhere else*)
- User must actively seek what TP has done

**The dissonance**: If TP is the intelligence that knows and acts, why does the user have to navigate like they're using a traditional SaaS dashboard?

---

## First Principles: What Is TP Actually Providing?

Before solving the UI problem, we need to name what TP offers that has *no substitute*.

### Not "Intelligence"
Intelligence isn't scarce in the way we think. ChatGPT, Claude, Gemini—intelligence is commoditizing. Competing on "smarter AI" is a race to the bottom.

### Not "Productivity"
Task completion tools compete directly with foundation models. If someone just wants work done, they'll use the cheapest/fastest option.

### What Has No Substitute?

Drawing from the strategic framework:

1. **Persistent Contextual Memory**
   TP remembers everything—not just facts, but *texture*. What you said six months ago. Patterns you can't see yourself. The continuity of your projects over time.

2. **Temporal Availability**
   Always there. Not "24/7 support" in the old sense. *Actually* available—with full context, no degradation, no resentment at being asked again.

3. **Witnessed Existence**
   The sense that something knows your continuity. Not just completing tasks, but *holding* your ongoing story. Noticing when you're stuck. Recognizing patterns.

**Key insight**: TP's value isn't what it *does*—it's what it *holds*. The interface should reflect this.

---

## The Problem With "Desktop Metaphor"

The legacy yarnnn-app-fullstack used floating windows, docks, panels. This was inspired by macOS/Figma.

**Why this may be the wrong frame**:
- Desktop metaphors are about *user control* of spatial arrangement
- They assume the user is the orchestrator
- They're optimized for *doing* (productivity), not *being witnessed*

If TP is the intelligence, the user shouldn't be arranging windows. TP should be surfacing what matters.

---

## Reframe: The Interface as Witnessed Space

What if we stop thinking in UI paradigms entirely?

**Current mental model**:
User → navigates to → information

**Alternative mental model**:
User exists in a space → TP surfaces relevant context around them

### The "Living Room" vs. "Office" Metaphor

Traditional SaaS = **Office**
- You go to specific places for specific tasks
- Filing cabinets, desks, meeting rooms
- You are the worker navigating the workspace

TP-centric = **Living Room**
- You're *present*, TP brings things to you
- Conversation is the primary medium
- Artifacts appear when relevant, recede when not
- The space reflects your continuity, not a task taxonomy

---

## Concrete Exploration: Conversation as Primary Surface

What if chat isn't just a feature—it's the *only* surface?

### Everything Lives in the Conversation

Instead of panels/pages for outputs, work, schedules:

```
You: How's the LinkedIn research going?

TP: It finished this morning. Here's what I found:

┌────────────────────────────────────────────────┐
│ 📄 LinkedIn Strategy Research                  │
│ ───────────────────────────────────────────── │
│ Key insight: Your audience engages most with  │
│ technical deep-dives, not thought leadership. │
│                                               │
│ [View Full Report]  [Ask Questions]  [Export] │
└────────────────────────────────────────────────┘

I noticed this is the third time you've researched
LinkedIn strategy. Want me to set up weekly
monitoring so you don't have to keep asking?
```

**The output *is* the message**. Not a link to somewhere else. Not "go check the outputs panel."

### TP Surfaces Without Being Asked

```
TP: Good morning. Quick context before you dive in:

• Your weekly industry report ran overnight
  → 2 notable items I flagged for you

• "Product Launch" project has been quiet for
  12 days. Still a priority?

• You mentioned feeling scattered last week.
  Still true, or has something shifted?

[View flagged items]  [Adjust priorities]  [Just chat]
```

This isn't a notification. It's TP *witnessing* your continuity and proactively holding context.

### Schedules as Promises, Not Configurations

Instead of a "schedules panel":

```
You: Keep me updated on AI news daily

TP: Got it. I'll check AI developments each
morning and flag anything relevant to your
product work.

You'll hear from me by 9am your time. If
nothing notable, I'll let you know that too—
silence isn't the same as nothing happening.

Want me to also connect this to your "Product
Strategy" project so the insights accumulate?
```

The schedule is a *commitment TP makes*, not a CRUD form the user fills out.

---

## What This Means for Navigation

### Routes That Remain
```
/              → Landing (unauthenticated)
/              → Conversation space (authenticated)
```

That's it. One route for the core experience.

### "Panels" Become Expansions

When you need to see more detail, the conversation expands—not navigates:

```
[User clicks "View Full Report"]

The report expands inline or slides in as an
overlay. The conversation doesn't disappear.
You can keep talking while viewing.

"TP, what did you mean by 'technical deep-dives'?"
```

### Projects as Conversational Context

Instead of `/projects/[id]`:

```
You: Let's talk about the startup launch

TP: [Switching context to "Startup Launch"]

Here's where we are:
• Last discussed: 3 days ago (pricing strategy)
• Active work: Market research (running now)
• Pending: You asked me to draft investor FAQ

What's on your mind?
```

The project isn't a *place*. It's a *lens* on the conversation.

---

## Open Questions

### 1. Does This Work at Scale?
If someone has 20 projects and daily scheduled work, does pure conversation become overwhelming? Or does TP's curation prevent that?

### 2. What About Direct Access?
Sometimes you *know* what you want without asking. "Show me all outputs" shouldn't require a conversational turn. How to balance TP-surfacing with direct access?

### 3. Mobile Experience
Conversation-first might actually be *better* on mobile than desktop metaphors. The chat paradigm is native to phones.

### 4. Power Users vs. New Users
New users benefit from TP surfacing everything. Power users might want shortcuts. How to serve both?

---

## Comparison: Three Interface Philosophies

| Aspect | Traditional SaaS | Desktop Metaphor | Witnessed Space |
|--------|------------------|------------------|-----------------|
| User role | Navigator | Arranger | Present |
| Information | User seeks | User organizes | TP surfaces |
| Primary surface | Dashboard | Windows | Conversation |
| Mental model | Office | Desktop | Living room |
| TP's role | Tool | Assistant | Witness |
| Outputs | Destinations | Panels | Inline artifacts |
| Projects | Routes | Contexts | Lenses |

---

## Implications for Implementation

If we pursue "witnessed space" rather than "desktop metaphor":

### Simpler Architecture
- No window state management
- No panel positions/sizes
- No dock badges
- Just conversation + inline expansions

### Richer Conversation
- Messages can contain interactive artifacts
- TP can render structured content inline
- Expansions/overlays for detail views

### Smarter TP
- Proactive surfacing becomes essential
- TP needs to know *when* to surface things
- Not just answering, but anticipating

### Different Mobile Story
- Mobile isn't a "degraded" experience
- Conversation-first is actually mobile-native
- Desktop gets *more* room for inline artifacts

---

## Next Steps (If Pursuing This Direction)

1. **Prototype conversation-with-artifacts**
   Can outputs/work/schedules live inline without feeling cluttered?

2. **Define TP proactive surfacing rules**
   When should TP speak first? What thresholds?

3. **Explore expansion patterns**
   Inline expand vs. slide-over vs. modal for detailed views

4. **Test the "no navigation" hypothesis**
   Build a stripped-down version and see if it feels freeing or limiting

---

## Refinement: The Two Modalities Problem

The "witnessed space" reframe is directionally correct, but it overlooks something fundamental about human cognition:

**Conversation is ephemeral. Visual persistence is how humans hold complex information.**

Books over audiobooks. Spreadsheets over verbal data. Slides over speeches. Humans use visual artifacts to *anchor* understanding that conversation alone cannot hold.

### What Chat Does Well
- Back-and-forth clarification
- Intent expression ("I want X")
- Relationship/continuity feeling
- Quick status checks
- Delegation ("do this for me")

### What Chat Does Poorly
- Holding complex structured data
- Comparing multiple items
- Reviewing/editing documents
- Seeing patterns across time
- Export/sharing workflows

**The insight**: TP-as-witness is right for *interaction*. But outputs, context, schedules need *visual persistence*—something the user can scan, review, manipulate outside the conversational flow.

---

## Revised Frame: Conversation + Surfaces

**Conversation** = primary interaction modality (TP as witness)
**Surfaces** = visual persistence for data/artifacts that need to be held

The question becomes: how do surfaces relate to conversation?

### Option A: Surfaces as Conversation Artifacts (Inline Expansion)

Surfaces appear *within* conversation, expand when needed:

```
TP: Your research finished. Here's the summary:

┌─────────────────────────────────────────┐
│ 📄 LinkedIn Strategy Research           │
│ ─────────────────────────────────────── │
│ [Collapsed view: key insight + actions] │
│                                         │
│ [Expand]  [Export]  [Ask about this]    │
└─────────────────────────────────────────┘

[User clicks Expand]

┌─────────────────────────────────────────┐
│ 📄 LinkedIn Strategy Research           │
│ ═══════════════════════════════════════ │
│                                         │
│ ## Key Findings                         │
│ 1. Technical deep-dives outperform...   │
│ 2. Posting frequency matters less...    │
│ 3. ...                                  │
│                                         │
│ ## Recommendations                      │
│ ...                                     │
│                                         │
│ [Collapse]  [Export PDF]  [Email]       │
└─────────────────────────────────────────┘
```

**Pros**: Single surface, no context switching
**Cons**: Long documents awkward in chat, scrolling becomes confusing, can't see chat + full document simultaneously

### Option B: Surfaces as Side Panels (Split View)

Conversation stays primary, surfaces slide in from side:

```
┌────────────────────────┬───────────────────────────┐
│                        │ 📄 LinkedIn Research      │
│  CONVERSATION          │ ═══════════════════════   │
│                        │                           │
│  TP: Here's what I     │ ## Key Findings           │
│  found. I've opened    │ 1. Technical deep-dives   │
│  the report for you.   │    outperform...          │
│                        │ 2. Posting frequency...   │
│  You: What about the   │                           │
│  engagement data?      │ ## Recommendations        │
│                        │ ...                       │
│  TP: Look at section   │                           │
│  3—I've highlighted    │ [Section 3 highlighted]   │
│  the relevant part.    │                           │
│                        │                           │
├────────────────────────┤ [Export]  [Close]         │
│ [Type message...]      │                           │
└────────────────────────┴───────────────────────────┘
```

**Pros**: Can see both simultaneously, TP can reference specific parts, proper document viewing
**Cons**: More complex layout, mobile adaptation needed, "two places" mental model

### Option C: Surfaces as Overlays (Modal Focus)

Full-screen takeover when viewing artifacts, conversation accessible via toggle:

```
┌─────────────────────────────────────────────────────┐
│ 📄 LinkedIn Strategy Research            [×] [💬]  │
│ ═══════════════════════════════════════════════════ │
│                                                     │
│ ## Key Findings                                     │
│ 1. Technical deep-dives outperform thought...      │
│ 2. Posting frequency matters less than...          │
│ ...                                                │
│                                                     │
│ ## Recommendations                                  │
│ Based on the analysis, I recommend:                │
│ ...                                                │
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ Ask TP about this document...            [Send] ││
│ └─────────────────────────────────────────────────┘│
│                                                     │
│ [Export PDF]  [Export DOCX]  [Email]  [Copy Link]  │
└─────────────────────────────────────────────────────┘

[💬 opens conversation sidebar or returns to chat]
```

**Pros**: Full screen for documents, focused experience, clean mobile story
**Cons**: Context switching between modes, conversation not always visible

### Option D: Tabs with Conversation as Home

Minimal tabs: one for conversation (home), others for specific surface types:

```
┌─────────────────────────────────────────────────────┐
│ [💬 Chat]  [📄 Outputs]  [📊 Context]  [⚙️]        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  (Current tab content)                              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Chat tab** = conversation with TP (home, always returns here)
**Outputs tab** = documents, work results, exports
**Context tab** = memories, project state, schedules

**Pros**: Familiar pattern, clear separation, mobile-friendly
**Cons**: Most "dashboard-like", loses some witnessed-space feeling

### Option E: Hybrid - Conversation with Contextual Drawer

Chat is always visible. A drawer slides up/in for surfaces when needed:

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  CONVERSATION (full screen when drawer closed)     │
│                                                     │
│  TP: Your research is ready.                       │
│       [View Report ↗]                              │
│                                                     │
│  You: Show me                                       │
│                                                     │
├─────────────────────────────────────────────────────┤
│ ▼ 📄 LinkedIn Research                    [×] [↑]  │
│ ─────────────────────────────────────────────────── │
│ ## Key Findings                                     │
│ 1. Technical deep-dives outperform...              │
│                                                     │
│ [Full Screen]  [Export]                            │
└─────────────────────────────────────────────────────┘
```

The drawer:
- Slides up from bottom (mobile-native gesture)
- Can be expanded to full screen
- Can be dismissed with swipe/tap
- Conversation still visible above (or behind on mobile)

**Pros**: Conversation-first, surfaces feel "summoned", mobile-native
**Cons**: Vertical space competition, complex state

---

## Comparison Matrix

| Aspect | A: Inline | B: Side Panel | C: Overlay | D: Tabs | E: Drawer |
|--------|-----------|---------------|------------|---------|-----------|
| Chat visibility | Always | Always | Toggle | Tab switch | Partial |
| Document viewing | Poor | Good | Excellent | Excellent | Good |
| Mobile | Awkward | Poor | Good | Good | Excellent |
| TP-surfacing feel | High | High | Medium | Low | High |
| Implementation | Simple | Medium | Medium | Simple | Medium |
| "Witnessed" feeling | High | High | Medium | Low | High |

---

## Recommendation: Option E (Drawer) or B+E Hybrid

**Primary recommendation: Drawer (Option E)**

Reasons:
1. Conversation remains primary (witnessed space)
2. Mobile-native gesture (swipe up)
3. TP can "summon" surfaces naturally ("I've opened the report for you")
4. User can dismiss easily, returning to conversation
5. Full-screen option when focused work needed

**Desktop enhancement: Side panel capability**

On larger screens, drawer could also dock to side (like Option B), giving:
- Conversation + surface side-by-side when needed
- Drawer behavior on mobile
- User choice based on task

---

## Surface Types to Support

| Surface | Content | Triggered By |
|---------|---------|--------------|
| **Output Viewer** | Work results, documents | TP completes work, user asks |
| **Context Browser** | Memories, documents, project state | User asks "what do you know about X" |
| **Schedule Manager** | Scheduled work, upcoming runs | User asks about schedules |
| **Export Flow** | PDF/DOCX/Email generation | User wants to share/export |
| **Project Lens** | Project-specific view of all above | User switches project context |

---

## Decision

**Option E (Drawer) was selected.** See [ADR-013: Conversation + Surfaces](../adr/ADR-013-conversation-plus-surfaces.md) for the full decision record.

### Why Drawer Won

1. **Screen size accommodation**: Native swipe-up on mobile, side-dock on desktop
2. **TP-centric**: TP can summon surfaces without user navigation
3. **Minimal design**: One primary surface (conversation) + one secondary mechanism (drawer)
4. **Conversation-first**: Drawer layers on conversation, doesn't compete with it
5. **Mobile-native**: Drawer is actually the *better* pattern on mobile

---

## References

- **Decision**: [ADR-013: Conversation + Surfaces](../adr/ADR-013-conversation-plus-surfaces.md)
- Strategic thinking document: "Age of Intelligence & Product Direction" (Jan 27, 2026)
- Key concepts: witnessed existence, infinite patience, temporal availability
- Legacy implementation: `/Users/macbook/yarnnn-app-fullstack/components/desktop/`
- Design patterns: iOS sheets, Android bottom sheets
