# Workspace State Surface

**Status:** Implemented (ADR-165 v5)
**Date:** 2026-04-08
**Governing ADR:** [ADR-165 v5](../adr/ADR-165-workspace-state-surface.md)
**Extends:** [SURFACE-ARCHITECTURE v8](./SURFACE-ARCHITECTURE.md)

---

## Thesis

`/chat` is a TP chat product. Workspace state is one single surface that opens on demand — controlled by TP via a marker directive, or by the user via the input-row icon. There is no permanent dashboard above the conversation.

This is the inversion of v4. v4 treated workspace state as four sibling artifacts in an always-on tab strip. v5 treats it as **one component with four lead views**, opened only when relevant.

```
/chat
  └── ChatPanel
        ├── topContent (rendered ONLY when surface.open === true)
        │     └── WorkspaceStateView
        │           ├── header (title + reason + close button)
        │           ├── lens switcher (briefing | recent | gaps — hidden in empty/gate state)
        │           └── active lead view (one of: empty, briefing, recent, gaps)
        ├── messages
        └── input row
              ├── PlusMenu (+) — owns "Update my context" action
              ├── textarea (capped at max-w-3xl by parent)
              ├── inputRowAddon — workspace state toggle icon
              └── submit
```

---

## Surface Model

### Default state

`/chat` loads with **no surface visible**. The page is just the TP chat conversation. The input row has a small icon (`LayoutPanelTop`) next to the submit button — the only persistent visual indicator that the surface exists.

The two paths that open the surface are:

1. **TP directive** — TP appends a workspace-state HTML comment to its assistant message. The chat client parses it, opens `WorkspaceStateView` in the requested lead view, and strips the comment before rendering.
2. **Manual override** — User clicks the input-row icon. The component computes the lead view deterministically from current data and opens. No TP call.

### Cold-start gate

For new users (no tasks, no messages), the surface auto-opens on page load with `lead='empty'`. This is the only frontend-driven open — TP hasn't had a chance to emit a marker yet because no message has been sent. Once TP responds to the user's first message, TP owns the surface from then on.

---

## Lead Views

### `empty` — ContextSetup gate

Source: `web/components/tp/ContextSetup.tsx`

Wraps `ContextSetup` in `embedded` mode. Hides the lens switcher (gates the user on identity capture). Submitting context closes the surface and sends the composed message to TP.

Auto-opens when:
- Workspace is empty AND no messages yet (cold start)
- TP emits `lead=empty`
- User clicks "Update my context" in the plus menu

### `briefing` — What changed

Source: `web/components/home/DailyBriefing.tsx`

Wraps `DailyBriefing` with `forceExpanded`. Shows what changed since the user was last here (sourced from agents+tasks via `useAgentsAndTasks()`).

Auto-opens when:
- TP detects fresh runs since last session close (TP reads its AWARENESS.md vs. current `last_run` timestamps in the workspace index)

### `recent` — Running

Source: top 6 tasks by `updated_at` from `useAgentsAndTasks()`

Compact list with task title, mode badge, owning agent, and last-run relative time.

Auto-opens when:
- User asks "what's running" / "what's my team doing" / "show me my work"

### `gaps` — Coverage

Source: agents/tasks readiness check (domain agents without tasks, count of `accumulates_context` tasks)

Surfaces missing work coverage. Links into `/agents` and `/work` for follow-through.

Auto-opens when:
- TP detects an empty domain feeding an active task
- TP runs `detect_inference_gaps` (ADR-162 sub-phase A) and gets high-severity items
- Workspace index shows `Gap: no tasks`

---

## TP Marker Pattern

### Format

```
<!-- workspace-state: {"lead":"<lead>","reason":"<short reason>"} -->
```

The marker MUST be the last line of TP's assistant message. The JSON must be on a single line. The `reason` must be ≤ 60 characters and human-readable.

### Parser

`web/lib/workspace-state-meta.ts`

- `parseWorkspaceStateMeta(content)` → `{ body, directive }`. Same approach as ADR-162's `parseInferenceMeta`.
- `stripWorkspaceStateMeta(content)` → convenience wrapper for inline render sites.
- Valid leads: `empty | briefing | recent | gaps`. Invalid leads silently no-op.

### Stripping

The marker is stripped from displayed content at two render sites in `ChatPanel`:

1. The `<MarkdownRenderer content={msg.content} />` path (line ~168 in `ChatPanel.tsx`)
2. The `<MessageBlocks blocks={msg.blocks} />` path → text-block branch in `InlineToolCall.tsx`

Both call `stripWorkspaceStateMeta()` on the content before passing it to `MarkdownRenderer`.

The marker is NOT stripped from persisted content (`session_messages.content` in the database) — this means reloads will re-fire the surface-open hook from the latest assistant message, which is the desired behavior for session continuity.

### TP prompt rules

`api/agents/tp_prompts/onboarding.py`, "Workspace State Surface (ADR-165 v5)" section under `CONTEXT_AWARENESS`. See `api/prompts/CHANGELOG.md` entry `[2026.04.08.3]`.

Tight initial ruleset:
- First message of session + identity empty → `lead=empty`
- First message of session + fresh runs detected → `lead=briefing`
- User asks "what's running" → `lead=recent`
- Gap detected (empty domain feeding active task / `detect_inference_gaps` high-severity) → `lead=gaps`

AT MOST ONE marker per message. Steady-state silence is the correct outcome for most messages.

---

## Manual Override

### Input-row icon

A small icon (`LayoutPanelTop` from lucide-react) lives in the chat input row, between the textarea and the submit button. Clicking it toggles the surface open/closed.

### Deterministic lead computation

When the user opens the surface manually, `WorkspaceStateView` computes the lead view from current data — no TP call:

```ts
function computeLead(isEmpty, agents, tasks) {
  if (isEmpty) return 'empty';
  if (domainAgentsWithoutTasks.length > 0) return 'gaps';
  if (tasks.length > 0) return 'briefing';
  return 'recent';
}
```

### Plus-menu "Update my context"

The plus-menu action is owned by `ChatSurface` itself (not the page), since `ContextSetup` is the surface's empty-lead view. Clicking it opens the surface with `lead=empty` regardless of current workspace state — useful for adding to context after onboarding is complete.

---

## Lens Switcher

Once the surface is open in `briefing`, `recent`, or `gaps`, three lens buttons at the top let the user reframe the same workspace state:

```
[ Newspaper ] What changed   [ ClipboardList ] Running   [ Compass ] Coverage
```

These are NOT navigation tabs. They are three lenses on the same underlying workspace state, switched client-side (no TP call). The active lens uses the same black-segment styling as ADR-163's global ToggleBar.

The lens switcher is **hidden** in the `empty` lead view — the gate behavior is exclusive.

---

## Component Plan

```
web/components/chat-surface/
  ChatSurface.tsx              — page-level controller; owns open state, parses markers, renders WorkspaceStateView
  WorkspaceStateView.tsx       — single component, all four lead views as internal state branches

web/lib/
  workspace-state-meta.ts      — marker parser + stripper
```

### Files Deleted

```
web/components/chat-surface/
  ChatArtifactCard.tsx          (legacy v4)
  ChatArtifactTabs.tsx          (legacy v4)
  chatArtifactTypes.ts          (legacy v4)
  artifacts/                    (entire directory removed)
    ContextGapsArtifact.tsx
    DailyBriefingArtifact.tsx
    OnboardingArtifact.tsx
    RecentWorkArtifact.tsx
```

### Touched (not created)

- `web/components/tp/ChatPanel.tsx` — strips marker before display, accepts new `inputRowAddon` prop
- `web/components/tp/InlineToolCall.tsx` — strips marker from text-block render path
- `web/app/(authenticated)/chat/page.tsx` — passes only first-party plus menu actions, removes the `update-context` no-op (now owned by ChatSurface)
- `api/agents/tp_prompts/onboarding.py` — "Workspace State Surface" ruleset added to `CONTEXT_AWARENESS`

---

## Guardrails

- Do not add draggable panes, docks, or floating windows.
- Do not introduce a second concurrent structured surface — there is one `WorkspaceStateView`, opened or closed.
- Do not use frontend heuristics to decide when to open the surface based on conversation state. TP decides. The only frontend-side opens are: cold-start gate (empty workspace, no messages) and manual override (user clicks the icon).
- Do not write the marker to displayed message bodies — strip via `stripWorkspaceStateMeta` at every render site.
- Do not extend the marker to non-workspace-state directives without an ADR. The marker is a behavioral artifact and adding directive types to the same channel needs explicit decision.
- Keep richer inspection in `/work`, `/agents`, and `/context`. The workspace state surface is a glance, not a destination.

---

## Acceptance Criteria

1. `/chat` loads with no surface visible for returning users with no marker — just the TP chat conversation.
2. New users (empty workspace, no messages) see the `empty` lead view auto-open as the cold-start gate.
3. TP emitting a `<!-- workspace-state: ... -->` marker opens the surface in the requested lead view, with the marker stripped from the displayed message body.
4. The input-row icon toggles the surface open/closed; manual opens compute the lead view deterministically.
5. The plus menu's "Update my context" action opens the surface in the `empty` lead view regardless of workspace state.
6. The chat input column is capped to `max-w-3xl` (768px) — Claude Code parity.
7. The lens switcher is hidden in the `empty` lead view and visible in the other three.
8. TypeScript and production build pass.
9. ADR-165 v4 artifact files (`ChatArtifactCard`, `ChatArtifactTabs`, `chatArtifactTypes`, four `artifacts/*.tsx`) are deleted in the same commit. No dual implementations.
