# Workspace State Surface

**Status:** Implemented (ADR-165 v7)
**Date:** 2026-04-09
**Governing ADR:** [ADR-165 v7](../adr/ADR-165-workspace-state-surface.md)
**Extends:** [SURFACE-ARCHITECTURE](./SURFACE-ARCHITECTURE.md)

---

## Thesis

`/chat` is a TP chat product. Workspace state is one single surface that opens on demand — controlled by TP via a marker directive, or by the user via the surface-header toggle. There is no permanent dashboard above the conversation.

v4 treated workspace state as four sibling artifacts in an always-on tab strip. v5 collapsed them into **one component with four lead views**, opened only when relevant. v6 promoted the surface to a true modal. **v7 (2026-04-09)** dissolved the special `empty` lead value into a peer `context` tab and decoupled gate behavior from lens identity — there are now four peer tabs and one uniform soft gate driven by `isEmpty`.

```
/chat
  ├── PageHeader (breadcrumb chrome)
  ├── SurfaceIdentityHeader (H1 + workspace state toggle)
  ├── ChatPanel (conversation column)
  │     ├── messages
  │     └── input row (PlusMenu + textarea + submit)
  └── WorkspaceStateView (sibling modal — only mounted while open)
        ├── backdrop (click-outside closes)
        ├── header (title + reason + close button)
        ├── lens switcher — four peer tabs (hidden only when isEmpty === true)
        │     [Newspaper] What changed  [ClipboardList] Running  [Compass] Coverage  [Sparkles] Add context
        └── active lead view (one of: context, briefing, recent, gaps)
```

---

## Surface Model

### Default state

`/chat` loads with **no surface visible**. The page is just the TP chat conversation. The surface-header "Workspace state" button (with `LayoutPanelTop` icon) is the only persistent visual indicator that the modal exists.

The two paths that open the surface are:

1. **TP directive** — TP appends a workspace-state HTML comment to its assistant message. The chat client parses it, opens `WorkspaceStateView` in the requested lead view, and strips the comment before rendering.
2. **Manual override** — User clicks the surface-header toggle button. The component computes the lead view deterministically from current data and opens. No TP call.

### Soft gate (cold start, v7)

When the workspace has no tasks (`isEmpty === true`), the modal can still be opened via TP's marker or the manual toggle — but the lens switcher is **hidden**. The user sees only the `context` lens (ContextSetup) because the other three lenses (briefing / recent / gaps) have nothing meaningful to show against an empty workspace. This is the soft gate: one focused decision, no misleading empty tabs.

Once the workspace has any content, the switcher shows and `context` becomes a peer tab like the other three. The gate is a property of workspace state (`isEmpty`), not a property of the `context` lens value.

### Two namespaces, don't conflate (v7)

- `workspace_state.identity` (backend compact index): `empty | sparse | rich` — classifies IDENTITY.md richness. This is what TP *reads*.
- `lead` (client marker value): `context | briefing | recent | gaps` — names the tab the client *opens*. TP never emits `lead=empty`.

---

## Lead Views

### `context` — ContextSetup (identity capture + re-entry)

Source: `web/components/chat-surface/ContextSetup.tsx`

Wraps `ContextSetup` in `embedded` mode. On cold start (`isEmpty === true`) this renders under a hidden switcher (soft gate). Once workspace has content, it's a peer lens like the other three — reachable via the "Add context" tab in the switcher. Submitting context closes the surface and sends the composed message to TP.

Opens when:
- TP emits `lead=context` (cold start: first turn for empty workspace; or re-entry: user explicitly wants to add more context)
- User clicks the "Add context" peer tab in the lens switcher

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
- Valid leads: `context | briefing | recent | gaps`. Invalid leads silently no-op. Legacy `empty` from pre-v7 markers is invalid and silently dropped — there is no migration shim (singular implementation).

### Stripping

The marker is stripped from displayed content at two render sites in `ChatPanel`:

1. The `<MarkdownRenderer content={msg.content} />` path (line ~168 in `ChatPanel.tsx`)
2. The `<MessageBlocks blocks={msg.blocks} />` path → text-block branch in `InlineToolCall.tsx`

Both call `stripWorkspaceStateMeta()` on the content before passing it to `MarkdownRenderer`.

The marker is NOT stripped from persisted content (`session_messages.content` in the database) — this means reloads will re-fire the surface-open hook from the latest assistant message, which is the desired behavior for session continuity.

### TP prompt rules

`api/agents/tp_prompts/onboarding.py`, "Workspace State Surface (ADR-165 v7)" section under `CONTEXT_AWARENESS`. See `api/prompts/CHANGELOG.md` entry `[2026.04.09.3]`.

Ruleset:
- First message of session + `workspace_state.identity == "empty"` → `lead=context`
- First message of session + fresh runs detected → `lead=briefing`
- User asks "what's running" → `lead=recent`
- Gap detected (empty domain feeding active task / `detect_inference_gaps` high-severity) → `lead=gaps`
- User wants to add more context after onboarding (rare — usually routed through direct `UpdateContext` call instead) → `lead=context`

AT MOST ONE marker per message. Steady-state silence is the correct outcome for most messages.

---

## Manual Override

### Surface-header toggle

The "Workspace state" button with `LayoutPanelTop` icon lives in the `SurfaceIdentityHeader` actions slot on `/chat` (ADR-167 v5 — moved here from the chat input row). Clicking it toggles the surface open/closed.

### Deterministic lead computation

When the user opens the surface manually, `WorkspaceStateView` computes the lead view from current data — no TP call:

```ts
function computeLead(isEmpty, agents, tasks) {
  if (isEmpty) return 'context';              // cold-start default — only capture is meaningful
  if (domainAgentsWithoutTasks.length > 0) return 'gaps';
  if (tasks.length > 0) return 'briefing';
  return 'recent';
}
```

### No plus-menu redundancy (v7)

The previous v5/v6 design added an "Update my context" action to the plus menu as a re-entry path. **v7 deleted this** — the `context` peer tab is always visible in the lens switcher when the modal is open (unless cold-start soft-gated), so plus-menu redundancy is unnecessary. One surface, one way in.

---

## Lens Switcher

Four peer lens buttons at the top of the modal let the user reframe the same workspace state:

```
[ Newspaper ] What changed   [ ClipboardList ] Running   [ Compass ] Coverage   [ Sparkles ] Add context
```

These are NOT navigation tabs. They are four lenses on the same underlying workspace state, switched client-side (no TP call). The active lens uses the same black-segment styling as ADR-163's global ToggleBar.

The lens switcher is **hidden** only when `isEmpty === true` — the cold-start soft gate. Visibility is driven by workspace state, not by the active lens value (v7 decoupling).

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
2. New users (empty workspace, no messages) see the `context` lens open via TP's first-turn marker as the cold-start soft gate (switcher hidden because `isEmpty`).
3. TP emitting a `<!-- workspace-state: ... -->` marker opens the surface in the requested lead view, with the marker stripped from the displayed message body.
4. The surface-header toggle button opens the surface; manual opens compute the lead view deterministically from data.
5. When the workspace has any content, the lens switcher shows all four peer tabs — including "Add context" — and clicking any tab switches the lens without any TP call.
6. The chat input column is capped to `max-w-3xl` (768px) — Claude Code parity.
7. The lens switcher is hidden **only** when `isEmpty === true` (soft gate driven by workspace state, not by lens identity).
8. TypeScript and production build pass.
9. No dual implementations: `ChatArtifactCard`, `ChatArtifactTabs`, `chatArtifactTypes`, four `artifacts/*.tsx` (v4), and the plus-menu "Update my context" action (v5/v6) are all deleted.
