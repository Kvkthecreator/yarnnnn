# Workspace State Surface

**Status:** Implemented (ADR-165 v8)
**Date:** 2026-04-09
**Governing ADR:** [ADR-165 v8](../adr/ADR-165-workspace-state-surface.md)
**Extends:** [SURFACE-ARCHITECTURE](./SURFACE-ARCHITECTURE.md)

---

## Thesis

`/chat` is the TP workspace. It has **two structured modal surfaces**, opened independently:

1. **Workspace modal** — a read-only capability dashboard with four peer tabs, each mirroring a slice of TP's compact index. This is the ongoing inspection surface.
2. **Onboarding modal** — a one-time identity-capture form (wraps the existing `ContextSetup` component). This is the first-run ceremony.

Neither shares state, switcher, or trigger with the other. v7 tried to unify them behind a soft gate; v8 recognizes that they are different jobs and gives them different surfaces.

```
/chat
  ├── SurfaceIdentityHeader (H1 + [Workspace] button in actions slot)
  ├── ChatPanel (conversation column)
  │     ├── messages
  │     └── input row (PlusMenu + textarea + submit)
  ├── WorkspaceStateView (sibling, modal — only mounted while open)
  │     ├── backdrop (click-outside closes)
  │     ├── header ("Workspace" + optional reason + close)
  │     ├── tab bar — four peer tabs, always visible when modal is open
  │     │     [Eye] Readiness  [Bell] Attention  [History] Last session  [Activity] Activity
  │     └── active tab content (all read-only)
  └── OnboardingModal (sibling, modal — only mounted while open)
        ├── backdrop (click-outside closes)
        ├── header ("Tell me about yourself" + close)
        └── ContextSetup (links + files + notes)
```

---

## Workspace Modal (`WorkspaceStateView`)

### Default state

`/chat` loads with **no modal visible**. The surface header's "Workspace" button is the only persistent entry point for manual open. Modal mounts only while open; close = unmounted.

### Four tabs (read-only)

All four tabs are read-only glances at what TP already sees in `format_compact_index` (ADR-159). No write forms, no inline editors, no tool calls from the tab content. Tabs contain at most:
- Data visualization (counts, badges, lists)
- Link-outs to other surfaces (`/work`, `/agents`, `/context`)
- "Ask TP" buttons that drop a pre-filled prompt into the chat input (user reviews and presses send — no auto-send, no auto-tool-call)

#### 1. Readiness — `overview`

TP answering: *"Your workspace readiness — what your team can draw on right now."*

Sections:
- **Workspace** — Identity & Brand richness badges (Empty / Sparse / Rich), link-out to `/context`. Values are state descriptors, not to-do labels: "Empty", "Voice and tone defined", "Partially defined".
- **Team** — agent count by class, flagged-agents callout if any
- **Work** — active tasks count + stale tasks callout
- **Knowledge** — canonical context domains (one row per domain, file count + health badge)
- **Platforms** — connected integrations
- **Budget** — credits used / limit, exhausted warning if applicable

**Default tab on manual open.** When the user clicks "Workspace", this is what they see first.

TP opens via: `<!-- workspace-state: {"lead":"overview","reason":"Here's the lay of the land"} -->`

#### 2. Attention — `flags`

TP answering: *"Here are the things I want you to notice."*

Aggregates all gap / flag signals TP currently holds. Each signal is a card:
- **Identity empty** — "I don't know much about you yet" → Ask TP: opens Onboarding modal
- **No tasks yet** — "Nothing is running yet" → Ask TP: "Help me set up my first task"
- **Stale tasks** — "N tasks haven't run in a while" → link-out to `/work?filter=stale`
- **Budget exhausted** — "You've used all your credits this month" → link-out to billing
- **Agent health** — "Agent X is producing inconsistent output" (one card per flag) → link-out to `/agents?agent=X`
- **Inference gaps** — high-severity items from `detect_inference_gaps` (ADR-162) → Ask TP: prompt matching the gap
- **Recent uploads pending** — "N documents haven't been processed yet" → Ask TP: "Take a look at my recent uploads"

Empty state (when no flags): "Nothing worth flagging right now."

TP opens via: `<!-- workspace-state: {"lead":"flags","reason":"3 things worth a look"} -->`

#### 3. Last session — `recap`

TP answering: *"Here's what we talked about before."*

Surfaces TP's cross-session memory (currently invisible in the UI):
- **Shift notes** — AWARENESS.md preview (TP's notes written at session close)
- **Conversation summary** — rolling compaction from `/workspace/memory/conversation.md`
- **Recent sessions** — last 3-5 session entries (timestamp + one-line summary), click to jump back via session navigation

Empty state (new workspace): "This is our first conversation."

TP opens via: `<!-- workspace-state: {"lead":"recap","reason":"Picking up from last time"} -->`

#### 4. Activity — `activity`

TP answering: *"Here's what your workforce has been doing lately."*

Two compact sections in one scroll:
- **Recent runs** — last 5 completed or in-progress task runs, with status icons + relative time
- **Coming up** — next 3-5 scheduled runs

Click-through to `/work` for the full view. This tab is intentionally thin — `/work` is the destination; this tab is the glance.

Empty state (no activity): "Your team hasn't run anything yet."

TP opens via: `<!-- workspace-state: {"lead":"activity","reason":"3 ran overnight"} -->`

---

## Onboarding Modal (`OnboardingModal`)

### Purpose

First-run ceremony. Captures raw context (links + files + notes) so TP can infer identity, brand, and domains. One form, one submit, one dismiss.

### Opening paths

- **TP marker only.** `<!-- onboarding -->` on the first turn of a session when `workspace_state.identity == "empty"`.
- **No manual trigger.** No Overview button entry, no plus-menu entry, no slash command.

### Dismissal

- Close button, Esc key, backdrop click.
- After dismissal, returning users do not see the modal again unless TP emits the marker on a subsequent cold start (which should be rare — identity richness persists).
- If a user needs to add bulk context later, they use chat itself ("here's a new doc about our team...") — TP handles via `UpdateContext` in the single intelligence layer.

### Body

Wraps the existing `ContextSetup` component unchanged. The component takes `onSubmit(message)` which closes the modal and forwards the composed message to TP via `sendMessage`.

---

## TP→Client Marker Pattern

### Two markers, two parsers

```
<!-- workspace-state: {"lead":"<lead>","reason":"<short reason>"} -->
<!-- onboarding -->
```

Parser module: `web/lib/workspace-state-meta.ts`

- `parseWorkspaceStateMeta(content)` → `{ body, directive }` for the Workspace modal
- `parseOnboardingMeta(content)` → `{ body, present }` for the Onboarding modal
- `stripWorkspaceStateMeta(content)` + `stripOnboardingMeta(content)` — chainable strippers for render paths

Valid `lead` values: `overview | flags | recap | activity`. Invalid leads silently no-op. The v7 lead values (`context | briefing | recent | gaps`) are invalid in v8 — no backwards-compat shim (singular implementation).

### Stripping

Both markers are stripped from displayed content at two render sites in `ChatPanel`:

1. `<MarkdownRenderer content={msg.content} />` path
2. `<MessageBlocks blocks={msg.blocks} />` path → text-block branch in `InlineToolCall.tsx`

Both call chain: `stripOnboardingMeta(stripWorkspaceStateMeta(content))` on the content before passing it to `MarkdownRenderer`.

Neither marker is stripped from persisted content (`session_messages.content` in the database) — this means reloads re-fire the modal-open hooks from the latest assistant message, which is the desired behavior for session continuity.

### TP prompt rules

`api/agents/tp_prompts/onboarding.py`, "Workspace State Surface (ADR-165 v8)" section under `CONTEXT_AWARENESS`. See `api/prompts/CHANGELOG.md` for the v8 entry.

Ruleset:
- **First message of session, identity is empty** → emit `<!-- onboarding -->` (empty directive) plus a one-sentence text invitation
- **First message of session, fresh runs detected** → emit `<!-- workspace-state: {"lead":"activity","reason":"..."} -->`
- **First message of session, unread shift notes in AWARENESS.md** → emit `<!-- workspace-state: {"lead":"recap","reason":"..."} -->`
- **User asks "what's running" / "what's my team doing"** → emit `<!-- workspace-state: {"lead":"activity"} -->`
- **Gap detected (empty domain, stale task, inference gap, etc.)** → emit `<!-- workspace-state: {"lead":"flags","reason":"..."} -->`
- **User asks "what do you know about me" / "show me the state of things"** → emit `<!-- workspace-state: {"lead":"overview"} -->`

AT MOST ONE marker per message. Never both `workspace-state` and `onboarding` in the same message. Steady-state silence is the correct outcome for most messages.

---

## Manual Override

### Workspace button

The surface header contains a single button **"Workspace"** with `LayoutDashboard` icon, positioned in `SurfaceIdentityHeader.actions`. Clicking it toggles the Workspace modal. Default tab: `overview` ("Readiness").

No manual trigger for the Onboarding modal — the form is a first-run ceremony, not an ongoing interaction mode.

---

## Tab Bar

Four peer tabs, always visible when the Workspace modal is open (no soft gate, no `isEmpty` logic):

```
[ Eye ] Readiness   [ Bell ] Attention   [ History ] Last session   [ Activity ] Activity
```

These are NOT navigation tabs. They are four lenses on the same underlying workspace state, switched client-side (no TP call). The active tab uses the same black-segment styling as ADR-163's global ToggleBar.

---

## Component Plan

```
web/components/chat-surface/
  ChatSurface.tsx              — page-level controller; owns Workspace + Onboarding open state,
                                 parses both markers, renders both modals as siblings
  WorkspaceStateView.tsx       — Workspace modal: 4 read-only tabs, no forms, no isEmpty prop
  OnboardingModal.tsx          — Onboarding modal: thin shell wrapping ContextSetup
  ContextSetup.tsx             — unchanged (identity capture form)

web/lib/
  workspace-state-meta.ts      — TWO parsers: parseWorkspaceStateMeta + parseOnboardingMeta
```

### Files Deleted

```
web/components/home/DailyBriefing.tsx   — sole consumer was v7 WorkspaceStateView.
                                          Data (recent runs + coming up) rebuilt inline in
                                          the Team activity tab.
```

### Touched (not created)

- `web/components/tp/ChatPanel.tsx` — strips both markers before display
- `web/components/tp/InlineToolCall.tsx` — strips both markers from text-block render path
- `web/app/(authenticated)/chat/page.tsx` — unchanged (still passes agents, tasks, dataLoading, plusMenuActions)
- `api/agents/tp_prompts/onboarding.py` — v8 marker ruleset

---

## Guardrails

- Do not add draggable panes, docks, or floating windows.
- Do not introduce a third structured modal on `/chat` without an ADR.
- Do not mix write forms into the Workspace modal tabs. If a tab "needs" a form, that's a signal to carve out a new surface, not to add a form to an existing diagnostic tab.
- Do not let the Workspace modal call TP tools directly. All write intent routes through chat via "Ask TP" pre-fill buttons (user reviews + presses send).
- Do not use frontend heuristics to decide when to open either modal based on conversation state. TP decides via markers.
- Do not write markers to displayed message bodies — strip both via `stripWorkspaceStateMeta` + `stripOnboardingMeta` at every render site.
- Do not extend either marker to non-structured directives without an ADR. The markers are behavioral artifacts per execution discipline #10.
- Keep richer inspection in `/work`, `/agents`, and `/context`. The Workspace modal is a glance, not a destination.

---

## Acceptance Criteria

1. `/chat` loads with no modal visible for returning users with no marker — just the TP chat conversation.
2. New users (identity empty) see the Onboarding modal via TP's first-turn `<!-- onboarding -->` marker.
3. TP emitting a `<!-- workspace-state: ... -->` marker opens the Workspace modal in the requested tab, with the marker stripped from the displayed message body.
4. The "Workspace" button in the surface header opens the Workspace modal with the `overview` tab (Readiness) as default.
5. Clicking any of the four tabs switches the lens without any TP call.
6. The Workspace modal contains no write forms — the only action affordance is "Ask TP" pre-fill buttons in the `flags` (Attention) tab.
7. The Onboarding modal has no manual trigger — TP marker is the only open path.
8. `WorkspaceStateView` does NOT accept an `isEmpty` prop.
9. Both modals cannot be open simultaneously.
10. `DailyBriefing.tsx` is deleted.
11. TypeScript and production build pass.
12. No dual implementations: v7's `context` peer tab, `isEmpty` soft gate, `briefing/recent` redundancy, and `DailyBriefing.tsx` are all deleted. The v7 marker `lead` enum is gone — `context | briefing | recent | gaps` is no longer valid anywhere.
