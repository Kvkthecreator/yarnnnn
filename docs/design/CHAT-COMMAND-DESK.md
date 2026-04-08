# Chat Command Desk - Windowed TP Surface

**Status:** First cut implemented
**Date:** 2026-04-08
**Governing ADR:** [ADR-165](../adr/ADR-165-chat-command-desk-windowed-surface.md)
**Extends:** [SURFACE-ARCHITECTURE v8](./SURFACE-ARCHITECTURE.md)

**First implementation:** 2026-04-08, `web/components/command-desk/` and `web/app/(authenticated)/chat/page.tsx`

---

## Thesis

`/chat` should be the TP command desk, not a two-column dashboard with chat attached.

The current two-panel layout is serviceable:

```
Daily Briefing | TP Chat
```

The problem is that it makes TP feel like one panel among several. After ADR-164, TP is the meta-cognitive agent: it owns orchestration, workforce health, and back office tasks. The home surface should reflect that. The better metaphor is:

```
TP workspace layer
  + managed windows for onboarding, briefing, work, context, outputs, agents
```

This is not a new top-level IA. ADR-163's four surfaces stay:

```
Chat | Work | Agents | Context
```

Only the internal layout of `Chat` changes.

---

## User-Facing Model

### New User

The user lands on `/chat`.

Primary object:

- `Onboarding` window, focused and centered.

Supporting objects:

- TP chat remains present as the workspace layer.
- `Daily Briefing` can be minimized or deferred until setup has enough context.

Expected feeling:

> "I am setting up the workspace with TP, and the workspace is already there around me."

Not:

> "I am blocked by a setup modal before I can use the app."

### Returning User

The user lands on `/chat`.

Primary objects:

- `Daily Briefing` window, primary position.
- `Recent Work` window, secondary position.
- `Context Gaps` window, secondary or docked.
- TP chat remains persistent.

Expected feeling:

> "TP has my desk ready: what changed, what is running, and what needs my attention."

Not:

> "I am reading a dashboard and can chat if I need to."

---

## Layout Model

### Desktop

Desktop uses a managed window canvas.

```
+--------------------------------------------------------------------+
| yarnnn                       [Chat | Work | Agents | Context]      |
+--------------------------------------------------------------------+
| [Dock: Briefing Work Context Outputs Agents]                       |
+--------------------------------------------------------------------+
|                                                                    |
|  TP chat workspace layer                                           |
|  +----------------------------+  +----------------------------+     |
|  | Daily Briefing             |  | Recent Work                |     |
|  | ...                        |  | ...                        |     |
|  +----------------------------+  +----------------------------+     |
|                                                                    |
|  +----------------------------+                                    |
|  | Context Gaps               |                                    |
|  | ...                        |                                    |
|  +----------------------------+                                    |
|                                                                    |
|                                    [TP input / conversation]        |
+--------------------------------------------------------------------+
```

The exact visual position can change in implementation, but the rules should not:

- Chat is always available.
- Windows have deterministic defaults.
- Windows do not randomly obscure onboarding or critical task output.
- A closed window is recoverable through the dock/launcher.

### Tablet

Tablet should not use draggable floating windows by default.

Recommended fallback:

- TP chat remains the base layer.
- Windows become right-side sheets or a tabbed detail panel.
- Dock icons open one sheet at a time.

### Mobile

Mobile should be a single-column command view.

Recommended fallback:

- Top: compact dock / segmented control.
- Body: active window content.
- Bottom: TP input or a chat sheet trigger.

Do not attempt desktop-like dragging on mobile.

---

## Window Inventory

### Onboarding

Component source:

- `web/components/tp/ContextSetup.tsx`

Purpose:

- Capture the first meaningful user context.
- Explain the setup state by doing, not by marketing copy.

Default behavior:

- Opens focused for new users.
- Cannot be accidentally lost: if closed before completion, the dock shows a strong unfinished state.

### Daily Briefing

Component source:

- `web/components/home/DailyBriefing.tsx`

Purpose:

- Show the daily-update task output and compact activity.

Default behavior:

- Opens primary for returning users.
- Links to `/work?task=daily-update` for full inspection when available.

### Recent Work

Likely component source:

- New `web/components/command-desk/windows/RecentWorkWindow.tsx`
- Data from `useAgentsAndTasks()`

Purpose:

- Show active, queued, recently run, and TP-owned/back-office work.

Default behavior:

- Opens secondary for returning users.
- Pulses when TP creates, runs, pauses, resumes, or evaluates a task.
- Links to `/work` for full inspection.

### Context Gaps

Likely component source:

- New `web/components/command-desk/windows/ContextGapsWindow.tsx`
- Data from inference metadata and workspace readiness endpoints where available.

Purpose:

- Make missing context visible as a first-class attention object.

Default behavior:

- Opens secondary when gaps are known.
- Pulses when `UpdateContext` changes identity, brand, or workspace context.
- Offers "ask TP to fill this" actions.
- Links to `/context` for full inspection.

### Outputs

Likely component source:

- New `web/components/command-desk/windows/OutputsWindow.tsx`

Purpose:

- Show latest task outputs and artifacts without forcing the user into `/work`.

Default behavior:

- Closed by default if there are no recent outputs.
- Opens or pulses when a task run produces output.
- Links to `/work?task={slug}` for full history.

### Agents

Likely component source:

- New `web/components/command-desk/windows/AgentsWindow.tsx`
- Data from `useAgentsAndTasks()`

Purpose:

- Compact workforce health view, including TP as meta-cognitive agent.

Default behavior:

- Closed or minimized by default.
- Pulses for agent health/back-office events.
- Links to `/agents` for full roster and identity.

---

## Component Architecture

Add a new package:

```
web/components/command-desk/
  CommandDesk.tsx
  CommandDeskDock.tsx
  CommandDeskWindow.tsx
  commandDeskTypes.ts
  commandDeskLayout.ts
  windows/
    OnboardingWindow.tsx
    DailyBriefingWindow.tsx
    RecentWorkWindow.tsx
    ContextGapsWindow.tsx
    OutputsWindow.tsx
    AgentsWindow.tsx
```

### `CommandDesk`

Owns:

- Window registry.
- Open/closed/minimized/focused state.
- Deterministic initial layout.
- Responsive mode switch.
- Tool-result focus/pulse API.

Does not own:

- TP network transport.
- Task mutations.
- Workspace file browsing.

### `CommandDeskWindow`

Reusable shell:

- Title
- Icon
- Focus state
- Close/minimize controls
- Optional resize/drag on desktop only
- ARIA labels and keyboard-close support

Implementation constraint:

- Start with fixed deterministic positions.
- Add drag/resize only after the base command desk is useful.

### `CommandDeskDock`

Launcher:

- Shows all registered windows.
- Shows open/minimized/focused state.
- Shows pulse/badge state.

Dock item examples:

- Briefing
- Work
- Context
- Outputs
- Agents

### `commandDeskLayout.ts`

Pure helper for default layout:

```ts
type CommandDeskWindowId =
  | 'onboarding'
  | 'briefing'
  | 'recent-work'
  | 'context-gaps'
  | 'outputs'
  | 'agents';

function getInitialCommandDeskLayout(input: {
  isNewUser: boolean;
  hasTasks: boolean;
  hasKnownGaps: boolean;
  viewport: 'desktop' | 'tablet' | 'mobile';
}): CommandDeskLayout
```

Keep this deterministic and unit-testable.

---

## `/chat` Migration

Current route:

- `web/app/(authenticated)/chat/page.tsx`

Current responsibilities:

- Load TP history.
- Load agents/tasks.
- Decide new user vs returning user.
- Render `ContextSetup` full page for new users.
- Render `DailyBriefing` + fixed TP chat panel for returning users.

New route responsibilities:

- Load TP history.
- Load agents/tasks.
- Build plus menu actions.
- Pass data and callbacks into `CommandDesk`.

Pseudo-structure:

```tsx
export default function HomePage() {
  const { messages, sendMessage, isLoading, loadScopedHistory } = useTP();
  const { agents, tasks, loading: dataLoading } = useAgentsAndTasks({ pollInterval: 60_000 });

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  const isNewUser = !dataLoading && tasks.length === 0;

  return (
    <CommandDesk
      isNewUser={isNewUser}
      agents={agents}
      tasks={tasks}
      chat={{
        plusMenuActions,
        placeholder: 'Ask anything or type / ...',
        surfaceOverride: { type: 'chat' },
      }}
      onboarding={{
        onSubmit: (msg) => sendMessage(msg),
      }}
    />
  );
}
```

`ChatPanel` should be reused, not rewritten:

- `web/components/tp/ChatPanel.tsx`

`DailyBriefing` should be reused, not rewritten:

- `web/components/home/DailyBriefing.tsx`

---

## Tool-Result Integration

Initial integration should use existing TP client state.

Current relevant file:

- `web/contexts/TPContext.tsx`

Future extension:

- Add a lightweight command-desk event bridge, or let `CommandDesk` observe TP messages/tool result blocks.

Suggested local event model:

```ts
type CommandDeskEvent =
  | { type: 'task_created'; taskSlug?: string }
  | { type: 'task_updated'; taskSlug?: string }
  | { type: 'task_output_ready'; taskSlug?: string; outputId?: string }
  | { type: 'context_updated'; target?: 'identity' | 'brand' | 'workspace' }
  | { type: 'agent_health_changed'; agentSlug?: string };
```

Mapping:

| Event | Window behavior |
|---|---|
| `task_created` | pulse/open Recent Work |
| `task_updated` | pulse Recent Work |
| `task_output_ready` | pulse/open Outputs |
| `context_updated` | pulse/open Context Gaps |
| `agent_health_changed` | pulse Agents |

First cut can be manual and conservative:

- Pulse only for most events.
- Open only for onboarding completion and newly available task outputs.

---

## Phases

### Phase 0 - Documentation

Deliverables:

- `docs/adr/ADR-165-chat-command-desk-windowed-surface.md`
- `docs/design/CHAT-COMMAND-DESK.md`
- Small pointer in `docs/design/SURFACE-ARCHITECTURE.md`

### Phase 1 - Shell Only

Deliverables:

- `CommandDesk`
- `CommandDeskDock`
- `CommandDeskWindow`
- deterministic layout helper

Use placeholder window content first.

Acceptance:

- `/chat` can render a desktop command desk without changing TP transport.
- New user and returning user default layouts differ deterministically.
- Mobile fallback renders one active window at a time.

### Phase 2 - Migrate Existing Content

Deliverables:

- Onboarding window wraps `ContextSetup`.
- Daily Briefing window wraps `DailyBriefing`.
- Chat layer wraps `ChatPanel`.

Acceptance:

- Current onboarding flow still works.
- Returning users still see briefing content.
- Chat history and message send still work.

### Phase 3 - Work and Context Windows

Deliverables:

- Recent Work window.
- Context Gaps window.
- Links to `/work` and `/context`.

Acceptance:

- User can inspect active/recent work from `/chat`.
- User can see known context gaps or an honest empty state.

### Phase 4 - Tool Pulses

Deliverables:

- Tool-result to command-desk event mapping.
- Dock badges/pulses.
- Optional automatic focus for high-signal events.

Acceptance:

- Creating/running/updating work from TP visibly affects the Work window or dock item.
- Updating context visibly affects the Context Gaps window or dock item.

### Phase 5 - Persistence and Polish

Deliverables:

- Optional localStorage persistence for open/minimized/focused windows.
- Optional desktop drag/resize.
- Keyboard shortcuts.

Acceptance:

- Persistence never hides onboarding.
- Reset-to-default is possible.
- Mobile remains deterministic.

---

## Risks

### Risk: Desktop Chaos

If windows can be dragged and resized before the base layout is useful, the surface becomes a toy.

Mitigation:

- Fixed positions first.
- Drag/resize later.
- Always provide reset-to-default.

### Risk: Chat Becomes Hard to Find

If windows dominate the page, users may lose the primary TP channel.

Mitigation:

- Persistent chat input.
- Obvious TP layer.
- Dock/focus behavior that never fully traps the user in a window.

### Risk: Onboarding Can Be Dismissed Too Easily

If onboarding becomes just another closeable window, new users can strand themselves.

Mitigation:

- Onboarding window gets a strong unfinished dock state.
- Closing unfinished onboarding should minimize, not discard.
- Empty workspace defaults continue to reopen onboarding on next `/chat` visit.

### Risk: Duplicating Work/Context Surfaces

The command desk could recreate `/work` and `/context` badly.

Mitigation:

- Windows are summaries and launch points.
- Full inspection remains in `/work` and `/context`.
- Window content should answer "what needs attention now?", not provide every control.

---

## Implementation Notes

- Prefer reusing current components over copying legacy repo code.
- The legacy full-stack Desktop UI is a reference for the metaphor, not a source dependency.
- Keep the first implementation local to `/chat`.
- Do not alter API contracts unless tool-result events prove impossible to derive client-side.
- Keep window IDs stable; they will become persistence keys later.

---

## Acceptance Criteria for the First Useful Cut

1. New users see `ContextSetup` as a focused command-desk window, with chat still available.
2. Returning users see Daily Briefing plus at least one work/status window.
3. Chat send/history behavior is unchanged.
4. Mobile has a deterministic non-dragging fallback.
5. `/work`, `/agents`, and `/context` remain available as full surfaces.
6. Closing or minimizing windows never makes the workspace feel empty or broken.
