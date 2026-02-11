# ADR-043: Streaming Process Visibility (Claude Code UX)

> **Status**: Proposed
> **Created**: 2025-02-11
> **Related**: ADR-037 (Chat-First Surface), ADR-038 (Claude Code Architecture Mapping)

---

## Context

ADR-037 established chat as the primary surface. However, the current implementation uses a **blocking request-response pattern**:

```
User Input → [waiting...] → Final Response
```

This creates several UX problems:
1. **Black box execution** — User doesn't see what TP is doing
2. **No progress visibility** — Multi-step operations feel stalled
3. **Anxiety during waits** — Is it working? Did it fail?
4. **Lost teaching moments** — User doesn't learn what tools exist or how they work

### The Claude Code Model

Claude Code demonstrates a superior pattern:

```
User: "sync slack and create weekly update"

TP: Let me help with that...

📋 Planning:
  ☐ Check Slack connection
  ☐ Sync latest messages
  ☐ Create deliverable

▶ List ✓ platforms
  → Found slack (connected)

▶ Execute ⏳ platform.sync(slack)
  → Started sync job abc123

▶ Write ✓ deliverable
  → Created "Weekly Update" (weekly)

Done! I've synced your Slack and created a weekly update deliverable...
```

**Key UX characteristics:**
1. **Thinking visible** — User sees the plan before execution
2. **Tool calls surfaced** — Each primitive shown as it executes
3. **Progressive results** — Outcomes appear as they complete
4. **Status indicators** — Clear success/pending/failed states
5. **Expandable details** — Collapse by default, expand on interest

---

## Decision

Adopt **Streaming Process Visibility** — expose TP's thinking and tool execution inline in the chat stream.

### 1. Multi-Message Streaming

Instead of one final message, stream multiple message "chunks":

```typescript
// Current: Single message accumulates
{ role: 'assistant', content: 'Final complete response...' }

// New: Multiple message events
{ type: 'thinking', content: 'Let me check your platforms...' }
{ type: 'tool_start', tool: 'List', input: { ref: 'platform:*' } }
{ type: 'tool_result', tool: 'List', success: true, preview: '3 platforms' }
{ type: 'thinking', content: 'Now syncing Slack...' }
{ type: 'tool_start', tool: 'Execute', input: { action: 'platform.sync' } }
{ type: 'tool_result', tool: 'Execute', success: true, preview: 'Job started' }
{ type: 'response', content: 'Done! I synced Slack and...' }
```

### 2. Visual Tool Call Components

Each tool call renders as an inline card:

```
┌─────────────────────────────────────────┐
│ ▶ Execute                          ✓    │
│   platform.sync(slack)                  │
│   └─ Started sync job abc123           │
└─────────────────────────────────────────┘
```

**States:**
- `⏳` Pending (animated spinner)
- `✓` Success (green checkmark)
- `✗` Failed (red X, shows error on expand)

**Interaction:**
- Collapsed by default (single line)
- Click to expand full input/output
- Failed tools auto-expand

### 3. Todo/Plan Display

When TP uses Todo primitive, show inline checklist:

```
┌─────────────────────────────────────────┐
│ 📋 Plan                                  │
│ ✓ Check Slack connection                │
│ ● Sync latest messages                  │  ← in progress
│ ○ Create deliverable                    │
└─────────────────────────────────────────┘
```

**Updates in real-time** as todos complete.

### 4. Thinking Indicator

Show when TP is processing (not just "typing"):

```
┌─────────────────────────────────────────┐
│ 💭 Thinking...                          │
│ Analyzing your request                  │
└─────────────────────────────────────────┘
```

Transitions to tool cards as they execute.

---

## Architecture

### API Changes

The `/api/chat` endpoint already streams SSE. Enhance event types:

```typescript
// Existing events
type ChatEvent =
  | { type: 'content', content: string }      // Text streaming
  | { type: 'tool_use', tool_name: string, tool_input: any }
  | { type: 'tool_result', tool_name: string, result: any }
  | { type: 'done' }
  | { type: 'error', message: string }

// New events for visibility
type ChatEvent =
  | { type: 'thinking', content: string }     // Thinking text (before tools)
  | { type: 'plan', todos: TodoItem[] }       // Todo plan snapshot
  | { type: 'plan_update', todo_id: string, status: string }
  | { type: 'tool_start', tool: string, input: any }
  | { type: 'tool_complete', tool: string, success: boolean, preview: string }
  | { type: 'response', content: string }     // Final response text
```

### Frontend State

```typescript
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';

  // New: structured content blocks
  blocks: MessageBlock[];
}

type MessageBlock =
  | { type: 'text', content: string }
  | { type: 'thinking', content: string }
  | { type: 'plan', todos: TodoItem[] }
  | { type: 'tool_call', tool: string, input: any, status: 'pending' | 'success' | 'failed', result?: any }
  | { type: 'clarify', options: string[] }
```

### Rendering

```tsx
function AssistantMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="space-y-2">
      {message.blocks.map((block, i) => {
        switch (block.type) {
          case 'thinking':
            return <ThinkingBlock key={i} content={block.content} />;
          case 'plan':
            return <PlanBlock key={i} todos={block.todos} />;
          case 'tool_call':
            return <ToolCallCard key={i} {...block} />;
          case 'text':
            return <TextBlock key={i} content={block.content} />;
          case 'clarify':
            return <ClarifyBlock key={i} options={block.options} />;
        }
      })}
    </div>
  );
}
```

---

## Visual Design

### Tool Call Card

```
Default (collapsed):
┌──────────────────────────────────────┐
│ ▶ List  platforms                 ✓  │
└──────────────────────────────────────┘

Expanded:
┌──────────────────────────────────────┐
│ ▼ List  platforms                 ✓  │
├──────────────────────────────────────┤
│ Input: { ref: "platform:*" }         │
│ Result: [                            │
│   { provider: "slack", ... },        │
│   { provider: "gmail", ... }         │
│ ]                                    │
└──────────────────────────────────────┘

Failed (auto-expanded):
┌──────────────────────────────────────┐
│ ▼ Execute  platform.sync          ✗  │
├──────────────────────────────────────┤
│ Error: Connection timeout            │
│ [Retry] [Details]                    │
└──────────────────────────────────────┘
```

### Plan/Todo Block

```
┌──────────────────────────────────────┐
│ 📋 Working on it...                  │
├──────────────────────────────────────┤
│ ✓ Check platform connections         │
│ ● Sync Slack messages                │  ← spinner
│ ○ Create weekly update               │
│ ○ Generate first draft               │
└──────────────────────────────────────┘
```

### Thinking Block

```
┌──────────────────────────────────────┐
│ 💭 Let me check your integrations    │
│    and find the relevant channels... │
└──────────────────────────────────────┘
```

Subtle styling: muted text, no border, fades after tools start.

---

## Implementation Phases

### Phase 1: Tool Call Visibility
- Enhance SSE to emit `tool_start` and `tool_complete` events
- Create `ToolCallCard` component with collapsed/expanded states
- Render tool calls inline in message stream

### Phase 2: Thinking Display
- Emit `thinking` events before tool execution
- Create `ThinkingBlock` component
- Show thinking as TP processes

### Phase 3: Plan/Todo Integration
- Connect Todo primitive to `plan` event emission
- Create `PlanBlock` component with checkbox UI
- Real-time updates as todos complete

### Phase 4: Polish
- Animations for state transitions
- Auto-scroll behavior refinement
- Mobile responsiveness
- Accessibility (screen reader support)

---

## Consequences

### What This Enables

| Capability | Benefit |
|------------|---------|
| **Transparency** | User sees exactly what TP does |
| **Trust building** | Visible work builds confidence |
| **Debugging** | Failed tools immediately visible |
| **Learning** | Users discover primitives organically |
| **Engagement** | Process visibility keeps attention |

### What This Requires

| Requirement | Implementation |
|-------------|----------------|
| **API changes** | New SSE event types |
| **New components** | ToolCallCard, PlanBlock, ThinkingBlock |
| **State restructure** | Message blocks instead of single content |
| **Design system** | Consistent card/badge styling |

### What This Preserves

- Existing primitives unchanged
- Backend API structure unchanged
- SSE streaming foundation reused
- Chat-first architecture (ADR-037) reinforced

---

## Alternatives Considered

### 1. Status Bar Only
Show tool execution in a status bar, not inline.

**Rejected**: Loses the narrative flow; doesn't build understanding.

### 2. Separate "Activity" Panel
Show tool calls in a side panel.

**Rejected**: Fragments attention; Claude Code proves inline works better.

### 3. Post-Hoc Summary
Show tool summary after completion.

**Rejected**: Loses the real-time engagement that builds trust.

---

## References

- [Claude Code](https://claude.ai/code) — Reference implementation
- [ADR-037: Chat-First Surface Architecture](./ADR-037-chat-first-surface-architecture.md)
- [ADR-038: Claude Code Architecture Mapping](./ADR-038-claude-code-architecture-mapping.md)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)

---

*This ADR establishes Streaming Process Visibility as the UX pattern for TP interactions, following Claude Code's proven model of transparent, inline tool execution display.*
