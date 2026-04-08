# ADR-165: Chat Artifact Surface

**Status:** Accepted
**Date:** 2026-04-08
**Authors:** KVK, Codex
**Extends:** ADR-163 (Surface Restructure), ADR-164 (Back Office Tasks - TP as Agent)
**Related:** ADR-161 (Daily Update Anchor), ADR-162 (Inference Hardening), ADR-159 (Filesystem-as-Memory)
**Implementation:** `web/components/chat-surface/` and `/chat`

---

## Context

ADR-163 established the four top-level destinations:

| Surface | Question |
|---|---|
| Chat | What should I do? What's happening? |
| Work | What is my workforce doing? |
| Agents | Who's on my team? |
| Context | What does my workspace know? |

That separation remains correct. The issue is the internal layout of `/chat`.

The first ADR-165 implementation tried to adapt the legacy full-stack repo's desktop metaphor: chat plus multiple floating windows for Daily Briefing, Recent Work, Context Gaps, and onboarding. That proved visually unintuitive. It made `/chat` feel like scattered panels rather than a single TP conversation surface.

The corrected model is closer to ChatGPT: chat is the dedicated primary surface, while structured UI appears as one focused artifact at a time.

---

## Decision

`/chat` becomes a **chat artifact surface**.

The page has one primary layer: the TP chat console. Structured objects such as onboarding, daily briefing, recent work, context gaps, and outputs render as one active artifact inline with the chat surface. A tab switcher lets the user navigate between available artifacts, while product logic chooses the default artifact.

This ADR does not add a fifth top-level destination, does not undo `/work`, `/agents`, or `/context`, and does not move the app to a desktop metaphor.

### Principles

- Chat is the single dedicated primary surface.
- Only one structured artifact is shown at a time.
- Product logic selects the default artifact: onboarding for new users, daily briefing for returning users.
- The user can override that default through visible tabs.
- Artifacts are inline by default, not scattered windows.
- A single sheet or detail view can be added later for long-form inspection, but not as the default layout.
- Full inspection still belongs to `/work`, `/agents`, and `/context`.

### Artifact Set

Initial artifacts:

| Artifact | Purpose | Source |
|---|---|---|
| Onboarding | First meaningful context capture | `ContextSetup` |
| Daily Briefing | What changed and what needs attention | `DailyBriefing` |
| Recent Work | Current and recent task state | `useAgentsAndTasks()` |
| Context Gaps | Missing context and workspace readiness | inferred from agents/tasks first, richer endpoints later |
| TP Console | Plain chat focus with no active artifact | `ChatPanel` |

### Navigation

The artifact switcher uses the same pill-tab language as the global `Chat | Work | Agents | Context` nav:

- Global nav switches top-level surfaces.
- Chat artifact tabs switch the one structured renderer inside `/chat`.
- Both use a clear active segment and muted inactive segments.

### Non-Goals

- No floating multi-window desktop.
- No draggable or resizable panes.
- No dock.
- No stacked pile of cards that competes with chat.
- No duplicate implementation of `/work`, `/agents`, or `/context`.

---

## Implementation Plan

Detailed implementation notes live in `docs/design/CHAT-ARTIFACT-SURFACE.md`.

Recommended phases:

1. Replace `web/components/command-desk/` with `web/components/chat-surface/`.
2. Render `/chat` through `ChatSurface`.
3. Convert the former window contents into artifact renderers.
4. Apply the pill-tab visual language to both the chat artifact switcher and global `ToggleBar`.
5. Keep `ContextSetup`, `DailyBriefing`, and `ChatPanel` as existing primitives where possible.
6. Add richer artifact data only after the base surface is visually coherent.

---

## Consequences

### Positive

- `/chat` reads as a coherent chat product instead of a desktop simulation.
- TP stays visually primary.
- Onboarding can remain dedicated without becoming a modal or separate route.
- Daily briefing, recent work, and context gaps stay discoverable without overlapping each other.
- The navigation model stays simple: top-level nav for surfaces, inner tabs for chat artifacts.

### Costs

- Only one structured artifact is visible at a time.
- Some cross-artifact relationships may need explicit links or summaries.
- Later tool-result surfacing needs a clear rule for which artifact becomes active.

### Mitigations

- Use product logic to select sensible defaults.
- Keep the artifact tabs visible so the user can navigate.
- Link from artifacts to `/work`, `/agents`, and `/context` for deeper inspection.
- Add a single detail sheet later if an artifact needs more space.

---

## Revision History

| Date | Version | Change |
|---|---|---|
| 2026-04-08 | v2 | Replaces the multi-window command desk with a single chat artifact surface: one primary chat console plus one active artifact selected by tabs. |
| 2026-04-08 | v1 | Initial command-desk proposal. Rejected after first implementation because multiple floating windows were visually unintuitive. |
