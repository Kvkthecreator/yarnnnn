# ADR-165: Chat Command Desk - Windowed TP Surface

**Status:** Accepted
**Date:** 2026-04-08
**Authors:** KVK, Codex
**Extends:** ADR-163 (Surface Restructure), ADR-164 (Back Office Tasks - TP as Agent)
**Related:** ADR-161 (Daily Update Anchor), ADR-162 (Inference Hardening), ADR-159 (Filesystem-as-Memory)
**First implementation:** 2026-04-08, `web/components/command-desk/` and `/chat`

---

## Context

ADR-163 fixed the most urgent surface problem: the Agents page was trying to answer too many questions. The four top-level destinations now have clean responsibilities:

| Surface | Question |
|---|---|
| Chat | What should I do? What's happening? |
| Work | What is my workforce doing? |
| Agents | Who's on my team? |
| Context | What does my workspace know? |

That separation is still correct. The issue is narrower: the current `/chat` implementation uses a two-panel layout - briefing dashboard on the left, TP chat on the right. That layout is clear, but it weakens the product metaphor.

TP is no longer just a chat affordance. ADR-164 made TP a first-class agent: the meta-cognitive agent that owns orchestration, workforce health, and back office tasks. The `/chat` surface should express that. It should feel less like "a dashboard beside a chat panel" and more like "TP's command desk, where work, context, outputs, onboarding, and system state can be opened around the conversation."

The legacy full-stack repo explored this direction with a Desktop UI: chat as the wallpaper, and Context / Work / Outputs / Recipes / Schedule as floating windows. The implementation should not be copied wholesale, but the metaphor is useful. It better matches the way TP works: conversation stays continuous while artifacts, decisions, and workspace objects become inspectable windows.

---

## Decision

Introduce a new internal layout model for `/chat`: **Chat Command Desk**.

The top-level surface remains `/chat` under the ADR-163 four-surface model. This ADR does not add a fifth top-level destination, does not undo `/work`, `/agents`, or `/context`, and does not move the whole app to a desktop metaphor.

The change is scoped to the internal layout of `/chat`.

### 1. Chat becomes the workspace layer

The chat thread and input remain persistent, but they are no longer framed as the right half of a dashboard. They become the background workspace layer of the command desk.

This means:

- The user can always talk to TP.
- The page can still show dashboard-like content.
- The content appears as managed windows or cards above the chat workspace, not as a fixed competing panel.
- Tool results can focus, open, or pulse windows instead of only adding inline cards to the transcript.

### 2. Windows are managed, not chaotic

"Windowed" does not mean arbitrary desktop clutter. The command desk uses a managed window system with deterministic defaults.

Required behavior:

- Each window type has a default size and position.
- Initial layouts are deterministic for new and returning users.
- Focus is explicit: a focused window comes forward; the rest remain visible or minimized.
- Windows can be closed and reopened from a dock/launcher.
- Mobile and narrow screens fall back to tabs, sheets, or stacked panels.
- The system should persist only stable user choices once the base experience is proven.

Non-goal:

- No full freeform OS desktop.
- No hidden state that strands important onboarding or work behind closed windows.
- No replacement of `/work`, `/agents`, or `/context` in this ADR.

### 3. Default window set

Initial window types:

| Window | Purpose | Source |
|---|---|---|
| Onboarding | Dedicated setup flow for empty workspaces | `ContextSetup` |
| Daily Briefing | Workspace status and daily-update output | `DailyBriefing` / daily-update task |
| Recent Work | What the workforce is doing now | `tasks` from `useAgentsAndTasks()` |
| Context Gaps | Missing or stale context that TP can help fill | ADR-162 inference gaps + workspace readiness |
| Outputs | Latest task outputs or generated artifacts | task output metadata |
| Agents | Compact workforce roster / health | agents from `useAgentsAndTasks()` |

The first implementation may ship fewer windows if the shell is correct. The minimum useful cut is:

1. Onboarding
2. Daily Briefing
3. Recent Work
4. Chat

### 4. New user layout

For empty workspaces, the current `/chat` page already shows `ContextSetup` as a full-page onboarding component. The command desk keeps onboarding primary, but changes its frame:

- The Onboarding window opens focused and centered.
- Chat remains visible behind or beside it as the persistent TP workspace.
- The user understands that onboarding is part of the workspace, not a blocking route.
- When onboarding creates context or tasks, the relevant window can open or pulse.

### 5. Returning user layout

For returning users:

- Daily Briefing opens in the primary position.
- Recent Work and Context Gaps open as secondary windows or docked cards.
- Chat remains available as the persistent command channel.
- Work and Context windows link out to `/work` and `/context` for full inspection.

### 6. Tool-call surfacing

TP tool calls should be able to affect the command desk:

| Tool outcome | UI behavior |
|---|---|
| Task created or updated | Open/pulse Recent Work |
| Task run output available | Open/pulse Outputs |
| Context updated | Open/pulse Context Gaps or Context |
| Onboarding fields inferred | Open/pulse Onboarding or Daily Briefing |
| Agent health/back office result | Open/pulse Agents or Recent Work |

The first implementation can use local client-side events from existing `TPContext` tool result handling. It does not require a new backend API.

---

## Implementation Plan

Detailed design and sequencing live in `docs/design/CHAT-COMMAND-DESK.md`.

Recommended phases:

1. Create a command desk component package under `web/components/command-desk/`.
2. Implement a deterministic managed-window shell.
3. Migrate `/chat` from the two-panel layout to the command desk shell.
4. Wrap `ContextSetup` and `DailyBriefing` as first-class desk windows.
5. Add Recent Work and Context Gaps windows.
6. Add tool-result window focus/pulse integration.
7. Add optional persistence for window state after the interaction model stabilizes.

---

## Consequences

### Positive

- `/chat` better expresses TP as the meta-cognitive agent rather than a side panel.
- Onboarding can remain dedicated without becoming a separate route or a blocking modal.
- Daily briefing, work state, outputs, and context gaps can coexist without competing in one fixed dashboard column.
- ADR-163's four-surface model remains intact while `/chat` becomes a richer home surface.
- ADR-164 becomes more visible: TP-owned work can surface as part of the command desk.

### Costs

- More frontend state than a static two-panel layout.
- Window positioning and mobile fallback need careful constraints.
- Tool-result surfacing can become noisy if every event opens a window.
- The "Chat" label may become less literal if the command desk becomes the dominant product metaphor.

### Mitigations

- Start on `/chat` only.
- Use deterministic initial layouts.
- Prefer pulse/focus over automatic open for lower-priority events.
- Keep full inspection on `/work`, `/agents`, and `/context`.
- Revisit the nav label only after the prototype proves whether the surface is truly a "Desk" rather than "Chat".

---

## Non-Goals

- Do not move `/work`, `/agents`, or `/context` into windows in this ADR.
- Do not add a fifth top-level nav item.
- Do not remove the current `ChatPanel` or rewrite TP transport.
- Do not copy the legacy full-stack desktop implementation verbatim.
- Do not persist complex window state in the first cut.
- Do not make onboarding optional or easy to lose behind a closed window.

---

## Open Questions

1. Should the nav label remain `Chat`, or should a later ADR rename the surface to `Desk` if the command desk metaphor wins?
2. Which window should be primary for returning users: Daily Briefing or TP chat?
3. Should `/agents?agent=thinking-partner` become a special entry point into the command desk, or remain a normal identity page?
4. What is the minimum mobile experience: bottom-sheet windows, a tabbed drawer, or a single stacked feed?
5. Which tool events deserve automatic window opening versus pulse-only behavior?

---

## Revision History

| Date | Version | Change |
|---|---|---|
| 2026-04-08 | v1 | Initial proposal. Reframes `/chat` as a managed command desk: persistent TP workspace layer plus deterministic windows for onboarding, briefing, work, context gaps, outputs, and agents. |
