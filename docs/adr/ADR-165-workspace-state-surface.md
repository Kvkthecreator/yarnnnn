# ADR-165: Workspace State Surface

**Status:** Accepted (v6)
**Date:** 2026-04-08
**Authors:** KVK, Claude
**Extends:** ADR-163 (Surface Restructure), ADR-164 (Back Office Tasks - TP as Agent)
**Related:** ADR-156 (Single Intelligence Layer), ADR-159 (Filesystem-as-Memory), ADR-161 (Daily Update Anchor), ADR-162 (Inference Hardening)
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

That separation remains correct. The issue has always been the internal layout of `/chat`.

This ADR has gone through four prior iterations, each fixing a smaller piece of the wrong frame:

- **v1** — multi-window "Command Desk" with floating panes. Visually scattered. Rejected after first build.
- **v2** — collapsed to one inline `ChatArtifactCard` with pill tabs above the chat scroller.
- **v3** — pill tabs aligned with global nav language.
- **v4** — artifacts pushed inside `ChatPanel` via `topContent` slot to remove the page-level border.

By v4 the page was visually coherent but the underlying decomposition was still wrong. The ADR described "product logic chooses the default artifact" but the implementation was a permanent tab strip + 38vh card that consumed the top of the page on every load. The four artifacts (Onboarding, Daily Briefing, Recent Work, Context Gaps) were treated as siblings in a navigation switcher, when in reality three of them read from the same data and answer adjacent questions about workspace state, and the fourth (Onboarding) is a one-time gate with a fundamentally different lifecycle.

The user-correct anchor is: **one single surface for the multitude of scenarios and data, with surfacing logic ("helpers like tabs or FAB") supplementary to it and secondary.**

---

## Decision

`/chat` is a **TP chat product**. The workspace state surface is a single **modal** component, opened by TP via a marker directive or by the user via a manual override icon — not a permanent dashboard, not an inline overlay above the conversation.

### Principles

- **Chat is the page.** No always-on artifact strip, no permanent dashboard, no inline overlay competing with the message stream. The default visual weight of `/chat` is the conversation.
- **One surface for all workspace-state scenarios.** Onboarding, daily briefing, recent work, and coverage gaps are not four artifacts — they are four lead views of the same single component.
- **TP is the surface opener (single intelligence layer per ADR-156).** The frontend never guesses when to show workspace state. TP decides, based on signals already in its working memory (workspace_state, recent_uploads, gap detection), and emits a directive the chat client executes. The frontend has **no cold-start auto-open** in v6 — discovery is TP's job, not the client's.
- **Manual override is supplementary.** A small icon next to the chat input toggles the modal. On manual open, the lead view is computed deterministically from current data — no TP call needed.
- **Modal, not overlay.** The surface renders as a true modal: backdrop, Esc key, body scroll lock, click-outside dismiss. Closed = gone. The user is never confused about whether the surface is "still there" stuck above stale messages.
- **The marker pattern reuses ADR-162's HTML-comment precedent.** Same parser approach (`parseInferenceMeta` → `parseWorkspaceStateMeta`), same rendering convention (strip from displayed body), same philosophy (inline metadata in TP's stream is the right channel for TP→client directives).

### Surface Model

```
/chat page
  ├── ChatPanel (full height, max-w-3xl)
  │    ├── messages (rolling window — the page IS the conversation)
  │    └── input row
  │          ├── PlusMenu (+) — owns "Update my context" action
  │          ├── textarea
  │          ├── inputRowAddon — workspace state toggle icon
  │          └── submit
  └── WorkspaceStateView (sibling, modal — only mounted while open)
       ├── backdrop (click-outside closes)
       ├── header (title + reason + close button)
       ├── lens switcher (briefing | recent | gaps — hidden in empty/gate state)
       └── active lead view content
```

### Lead Views

| Lead | Purpose | Opens when |
|---|---|---|
| `empty` | ContextSetup gate — workspace has no identity yet | TP emits `lead=empty` on the first turn for an empty workspace, OR user clicks "Update my context" in plus menu |
| `briefing` | What changed since the user was last here | TP detects fresh runs since last session close and emits `lead=briefing` |
| `recent` | What tasks are currently running | User asks "what's running" / "show me my work" → TP emits `lead=recent` |
| `gaps` | Coverage gaps — domain agents without tasks, missing context | TP detects empty domains feeding active tasks, OR `detect_inference_gaps` returns high-severity items, and emits `lead=gaps` |

**There is no frontend cold-start auto-open in v6.** Every modal open is either a TP marker or a user action. New-user discovery happens through TP's first response — TP's onboarding prompt (`api/agents/tp_prompts/onboarding.py`, "Workspace State Surface" section) already includes the rule "First message of a session, identity is empty → emit `lead=empty`."

### TP→Client Marker

TP appends an HTML comment as the LAST line of an assistant message:

```
<!-- workspace-state: {"lead":"<lead>","reason":"<short reason>"} -->
```

The chat client parses the marker via `parseWorkspaceStateMeta()`, opens `WorkspaceStateView` with the requested lead, and strips the comment from the message body before rendering. Same pattern as ADR-162's `inference-meta` marker.

TP's prompt (`api/agents/tp_prompts/onboarding.py`, "Workspace State Surface" section) defines the tight ruleset for when to emit the marker. Key constraints:

- AT MOST ONE marker per message
- Marker is supplementary — text response is the answer
- Empty markers / steady-state silence are correct outcomes (most messages emit nothing)
- The user manually opens the surface for everything else

### Manual Override

The chat input row includes a small icon (`LayoutPanelTop`) next to the submit button. Clicking it toggles `WorkspaceStateView` open/closed. On manual open the lead view is computed deterministically:

1. If workspace is empty → `empty`
2. Else if domain agents exist without tasks → `gaps`
3. Else if there are tasks → `briefing`
4. Else → `recent`

Manual opens never call TP — they're frontend-only.

### Lens Switcher

Once the surface is open in `briefing`, `recent`, or `gaps`, a small lens switcher at the top lets the user reframe the same workspace state through a different lens. The lens switcher is NOT a navigation tab strip — it's three lenses on the same underlying data. The `empty` lead view hides the lens switcher (gate behavior).

### Non-Goals

- No floating windows, no draggable panes, no dock
- No always-on artifact strip
- No frontend heuristics for "is this user new" / "should we show the briefing today" — TP owns those decisions
- No duplicate implementation of `/work`, `/agents`, or `/context` — full inspection still belongs to those surfaces
- No new top-level surface — `/chat` keeps its place in ADR-163's four

---

## Implementation

Detailed implementation notes live in `docs/design/WORKSPACE-STATE-SURFACE.md`.

### File Layout

```
web/components/chat-surface/
  ChatSurface.tsx              — page-level controller; owns open state, parses markers, renders WorkspaceStateView
  WorkspaceStateView.tsx       — single component, all four lead views as internal state branches

web/lib/
  workspace-state-meta.ts      — parser + stripper for the workspace-state HTML comment marker
```

### Files Deleted (Singular Implementation)

```
web/components/chat-surface/
  ChatArtifactCard.tsx          (legacy v4 — wrong decomposition)
  ChatArtifactTabs.tsx          (legacy v4)
  chatArtifactTypes.ts          (legacy v4)
  artifacts/                    (entire directory)
    ContextGapsArtifact.tsx
    DailyBriefingArtifact.tsx
    OnboardingArtifact.tsx
    RecentWorkArtifact.tsx
```

### TP Prompt Update

`api/agents/tp_prompts/onboarding.py` gains a "Workspace State Surface (ADR-165 v5)" section under `CONTEXT_AWARENESS`. See `api/prompts/CHANGELOG.md` entry `[2026.04.08.3]`.

### Chat Column Width

Independent fix landed in the same commit: `/chat` page wrapper changes from `max-w-5xl` (1024px) to `max-w-3xl` (768px). This brings the chat column to industry standard / Claude Code parity. The textarea inherits the cap.

### ChatPanel Changes

- Strips the workspace-state marker from displayed assistant message content via `stripWorkspaceStateMeta()` (both `MarkdownRenderer` and `MessageBlocks` text-block rendering paths)
- Accepts new `inputRowAddon` prop — rendered between the textarea and the submit button
- **v6:** `topContent` prop deleted entirely (it was only used by the v5 inline-overlay path; the v6 modal renders as a sibling of `ChatPanel`, not inside the message scroller). `emptyState` prop is preserved — it's still used by `/work` and `/agents` via `ThreePanelLayout` to show contextual "select something" guidance in the slide-in chat panel. The `/chat` surface no longer passes an empty state; TP's first response is the greeting there.

### v6 Modal Mechanics

- Backdrop: `bg-foreground/40 backdrop-blur-sm`, click-outside dismisses
- Esc key closes (window-level keydown listener mounted while open)
- Body scroll lock while open (saves and restores `document.body.style.overflow`)
- Centered, `max-w-2xl`, `max-h-[60vh]` content area, `py-[10vh]` viewport offset for breathing room
- Animated in via Tailwind `animate-in fade-in zoom-in-95` — same motion grammar used elsewhere in the app
- No external dependency added — built with a plain `fixed inset-0` div + ARIA `role="dialog"` / `aria-modal="true"`. The codebase has no Radix Dialog primitive, and the surface is simple enough that adding one for a single use site would be over-engineering

---

## Consequences

### Positive

- `/chat` reads as a TP chat product. The default visual weight is the conversation, exactly like Claude Code or ChatGPT.
- The surface is surfaced when relevant, hidden when not. Steady-state silence is the correct outcome.
- The single intelligence layer (ADR-156) is preserved end-to-end — TP decides, frontend executes.
- ADR-162's gap detection finally drives a UI behavior (auto-opening the gaps lead) instead of just rendering captions.
- Adding a new lead view in the future is one branch in `WorkspaceStateView` + one valid value in the marker enum + one TP prompt rule. No new component, no new tab, no new file.

### Costs

- TP must learn the new ruleset. The initial ruleset is intentionally tight to keep behavior predictable. The first month of usage will reveal whether the ruleset needs tuning.
- The marker is a behavioral artifact (per execution discipline #10). Adding more directive types in the future means more parser entries — must be kept disciplined.
- Manual override discoverability depends on the input-row icon being noticed. The cold-start gate (empty workspace auto-opens) handles new-user discovery; for returning users with no fresh activity the icon is silent until they explore.

### Mitigations

- Marker ruleset is owned by `api/agents/tp_prompts/onboarding.py` — version-controlled and tracked in `api/prompts/CHANGELOG.md` like every other prompt change.
- The marker JSON is validated by `parseWorkspaceStateMeta()`; invalid leads silently no-op (the modal stays closed).
- New-user discovery is now TP's responsibility — the prompt rule "first message of a session, identity is empty → emit `lead=empty`" ensures every cold-start user sees the modal on their very first turn, even though the frontend no longer auto-opens. The discovery moment moved from "page mount" to "TP's first reply," which is the correct seam: TP greets, TP opens the gate.

---

## Revision History

| Date | Version | Change |
|---|---|---|
| 2026-04-08 | **v6** | **Surface promoted to a true modal (backdrop, Esc, body scroll lock, click-outside dismiss). Frontend cold-start auto-open removed — discovery is TP's job, the prompt's existing "first turn, empty identity → emit `lead=empty`" rule handles new users on TP's first reply instead of on page mount. `CHAT_EMPTY_STATE` stub deleted (TP's greeting is the empty state on `/chat`). `isNewUser` prop dropped from ChatSurface. `topContent` prop deleted from ChatPanel (was only used by the v5 inline overlay). `emptyState` prop preserved on ChatPanel for `/work` and `/agents` slide-in chat use cases. Marker schema, parser, and TP prompt unchanged. No new dependencies (modal built with plain fixed-position div + ARIA dialog attributes).** |
| 2026-04-08 | v5 | Single workspace state surface, TP-directed open via HTML-comment marker. Four lead views as internal state of one component. Chat column capped to max-w-3xl. Legacy artifact files deleted. ADR + design doc renamed from "chat artifact surface" → "workspace state surface". |
| 2026-04-08 | v4 | Clarifies that artifacts and artifact tabs render inside the TP chat surface, not above a separate bordered chat panel. |
| 2026-04-08 | v3 | Clarifies that TP Console is the base chat surface, not an artifact tab. Global nav keeps its original sizing while adopting the black active segment. |
| 2026-04-08 | v2 | Replaces the multi-window command desk with a single chat artifact surface: one primary chat console plus one active artifact selected by tabs. |
| 2026-04-08 | v1 | Initial command-desk proposal. Rejected after first implementation because multiple floating windows were visually unintuitive. |
