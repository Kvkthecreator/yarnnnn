# Chat Artifact Surface

**Status:** First refactor in progress
**Date:** 2026-04-08
**Governing ADR:** [ADR-165](../adr/ADR-165-chat-artifact-surface.md)
**Extends:** [SURFACE-ARCHITECTURE v8](./SURFACE-ARCHITECTURE.md)

---

## Thesis

`/chat` should feel like a dedicated TP chat product, not a dashboard beside chat and not a desktop full of windows.

The corrected model is:

```
Chat console
  + one active structured artifact
  + visible artifact tabs
```

The artifact tabs let product logic choose what matters now while still giving the user direct navigation.

---

## Surface Model

### Global Navigation

The global nav keeps ADR-163's four top-level surfaces:

```
Chat | Work | Agents | Context
```

It uses a pill-tab treatment: strong active segment, muted inactive segments, and consistent icon + label spacing.

### Chat Artifact Navigation

Inside `/chat`, a second pill-tab switcher selects the one active artifact:

```
Daily Briefing | Recent Work | Context Gaps | TP Console
```

For new users, the first tab becomes:

```
Get Started | Daily Briefing | Recent Work | Context Gaps | TP Console
```

Default selection:

- New user: `Get Started`
- Returning user: `Daily Briefing`
- User-selected tab: preserved during the session unless onboarding state changes

### Rendering Rule

Only one artifact renders at a time.

The artifact is inline with the chat surface, above the TP console. Selecting `TP Console` hides the artifact and leaves chat as the sole visible content.

No artifact is a floating window. No artifact can overlap another artifact.

---

## Artifact Inventory

### Get Started

Source:

- `ContextSetup`

Behavior:

- Shown first for new users.
- Renders inline as the active artifact.
- Submitting context sends the composed message to TP.

### Daily Briefing

Source:

- `DailyBriefing`

Behavior:

- Default artifact for returning users.
- Force-expanded when rendered as a chat artifact so local collapsed state does not hide the main content.

### Recent Work

Source:

- `useAgentsAndTasks()`

Behavior:

- Shows the most recently updated tasks.
- Keeps the card compact and links out to `/work` later when detail actions are added.

### Context Gaps

Source:

- Current first cut uses agents/tasks readiness.
- Later cuts should use ADR-162 inference metadata and workspace readiness endpoints.

Behavior:

- Shows missing task coverage and high-level context readiness.
- Links out to `/context` later when detail actions are added.

### TP Console

Source:

- `ChatPanel`

Behavior:

- Hides the structured artifact and gives the full surface to chat.
- Uses the same plus-menu actions as the previous `/chat` implementation.

---

## Component Plan

```
web/components/chat-surface/
  ChatSurface.tsx
  ChatArtifactTabs.tsx
  ChatArtifactCard.tsx
  chatArtifactTypes.ts
  artifacts/
    OnboardingArtifact.tsx
    DailyBriefingArtifact.tsx
    RecentWorkArtifact.tsx
    ContextGapsArtifact.tsx
```

`/chat` owns data loading and TP history as before, then passes data into `ChatSurface`.

The old `web/components/command-desk/` package is removed.

---

## Guardrails

- Do not add draggable panes.
- Do not add a dock.
- Do not show more than one artifact at a time.
- Do not place cards inside cards unless the nested card is existing domain content that has not been refactored yet.
- Keep user-facing copy direct. Do not describe the UI to the user.
- Keep richer inspection in `/work`, `/agents`, and `/context`.

---

## Acceptance Criteria

1. `/chat` has one centered chat surface, not multiple scattered windows.
2. Artifact tabs are visible and navigable.
3. Logic defaults to onboarding for new users and daily briefing for returning users.
4. Selecting `TP Console` shows chat without a structured artifact.
5. Global nav and chat artifact tabs share the same pill-tab language.
6. TypeScript and production build pass.
