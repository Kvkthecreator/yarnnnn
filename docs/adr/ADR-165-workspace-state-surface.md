# ADR-165: Workspace State Surface

**Status:** Accepted (v8)
**Date:** 2026-04-08 (v6), amended 2026-04-09 (v7), rewritten 2026-04-09 (v8)
**Authors:** KVK, Claude
**Extends:** ADR-163 (Surface Restructure), ADR-164 (Back Office Tasks - TP as Agent)
**Related:** ADR-156 (Single Intelligence Layer), ADR-159 (Filesystem-as-Memory), ADR-161 (Daily Update Anchor), ADR-162 (Inference Hardening)
**Implementation:** `web/components/chat-surface/` and `/chat`

> **v8 (2026-04-09):** Onboarding and workspace-state inspection split into **two
> separate modals**. v7's "four peer tabs including Add context" conflated a
> read-only diagnostic dashboard with a write form; the soft gate was the symptom.
> The **Workspace** modal is purely diagnostic — four read-only tabs mirroring what
> TP sees in its compact index (`Readiness | Attention | Last session | Activity`).
> The **Onboarding** modal is a separate surface with its own lifecycle, opened by
> TP's first-turn marker on cold start or by no one else. No soft gate, no
> `isEmpty` prop on the workspace modal, no write forms mixed into diagnostic tabs.
> Tab labels frame capability, not profile completeness (framing renamed 2026-04-15).
> Singular implementation. See v8 delta at bottom of Revision History.

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

This ADR has gone through seven prior iterations, each fixing a smaller piece of the wrong frame:

- **v1** — multi-window "Command Desk" with floating panes. Visually scattered. Rejected after first build.
- **v2** — collapsed to one inline `ChatArtifactCard` with pill tabs above the chat scroller.
- **v3** — pill tabs aligned with global nav language.
- **v4** — artifacts pushed inside `ChatPanel` via `topContent` slot to remove the page-level border.
- **v5** — single component, four lead views, TP-directed marker.
- **v6** — promoted to a true modal (backdrop, Esc, body scroll lock).
- **v7** — `empty` lens value dissolved into a peer `context` tab, soft gate decoupled from lens identity.

By v7 the modal was behaviorally coherent but still structurally wrong. The `context` peer tab was a write form (identity capture) living inside a switcher whose other three tabs (briefing, recent, gaps) were read-only diagnostics. The `isEmpty` soft gate that hid the switcher on cold start was the symptom: the author's instinct was telling them that showing three empty diagnostic tabs next to a capture form felt wrong, but the fix was to hide the switcher instead of recognizing that the capture form didn't belong in the switcher at all.

**Two jobs, one modal** — that's the category error v8 corrects. Onboarding is a one-time ceremony with its own lifecycle. Workspace-state inspection is a steady-state diagnostic surface the user opens to check on things. They happen in the same page, but they are not the same surface.

The user-correct anchor is: **`/chat` is the TP workspace. Its structured surfaces are read-only mirrors of what TP already sees (compact index) plus one separate write surface for onboarding capture. Diagnostic and capture never share a switcher.**

---

## Decision

`/chat` is a **TP chat product** with **two structured modals**, opened independently:

1. **Workspace modal** (`WorkspaceStateView`) — a read-only capability dashboard with four peer tabs, each mirroring a slice of TP's compact index. Opened by TP via a marker directive or by the user via a manual override button in the surface header. Default visual weight of `/chat` is the conversation, not this modal.
2. **Onboarding modal** (`OnboardingModal`) — a first-run ceremony that wraps the identity-capture form (`ContextSetup`). Opened by TP via a separate marker on the first turn of a cold-start workspace. No manual trigger. Once dismissed, it does not return — the user interacts with TP via chat for subsequent context updates.

### Principles

- **Chat is the page.** No always-on artifact strip, no permanent dashboard, no inline overlay competing with the message stream. The default visual weight of `/chat` is the conversation.
- **Diagnostic and capture are different surfaces.** The Workspace modal is purely read-only — it shows what TP sees. The Onboarding modal is purely write — it captures raw context for TP to infer from. They do not share a switcher, they do not share a trigger, they do not share state.
- **Tabs mirror TP's compact index.** The four Workspace tabs map directly to the signals TP reads every message in `format_compact_index` (ADR-159): workspace readiness / attention signals / session continuity / activity. The UI is an honest visualization of what TP already knows — nothing more, nothing less.
- **TP is the surface opener (single intelligence layer per ADR-156).** The frontend never guesses when to show either modal. TP decides, based on signals already in its working memory, and emits a directive the chat client executes. The frontend has no cold-start auto-open logic.
- **Manual override is supplementary — and only for the Workspace modal.** A button in the surface header (`SurfaceIdentityHeader.actions`) toggles the Workspace modal. On manual open, the first tab (`Readiness`) is the default. The Onboarding modal has no manual trigger.
- **Modal, not overlay.** Both surfaces render as true modals: backdrop, Esc key, body scroll lock, click-outside dismiss. Closed = gone.
- **Capability framing, TP's POV.** Tab labels frame operational readiness, not profile completeness (`Readiness`, `Attention`, `Last session`, `Activity`). No technical language (no `lead`, no `gaps`, no `briefing`), no CRUD vocabulary.
- **The marker pattern reuses ADR-162's HTML-comment precedent.** Two separate markers, two parsers, two modals: `workspace-state` (workspace) and `onboarding` (onboarding). Same rendering convention (strip from displayed body), same philosophy (inline metadata in TP's stream is the right channel for TP→client directives).

### Surface Model

```
/chat page
  ├── SurfaceIdentityHeader (H1 + Workspace toggle in actions slot)
  ├── ChatPanel (conversation column, max-w-3xl)
  │    ├── messages (rolling window — the page IS the conversation)
  │    └── input row (PlusMenu + textarea + submit)
  ├── WorkspaceStateView (sibling, modal — only mounted while open)
  │    ├── backdrop (click-outside closes)
  │    ├── header (title "Workspace" + reason + close button)
  │    ├── tab bar — four peer tabs, always visible when modal is open
  │    │     [Eye] Readiness  [Bell] Attention  [History] Last session  [Activity] Activity
  │    └── active tab content (four read-only views — no forms)
  └── OnboardingModal (sibling, modal — only mounted while open)
       ├── backdrop (click-outside closes)
       ├── header (title "Tell me about yourself" + close button)
       └── ContextSetup (identity capture: links + files + notes)
```

### Workspace Modal — Four Tabs

Each tab is a read-only mirror of a slice of TP's `format_compact_index` output. No write forms, no action buttons that mutate state inside the tab content. Navigation actions (link-out to `/work`, `/agents`, `/context`) and "Tell TP" buttons (which pre-fill the chat input without sending) are allowed — but they route through chat or through other surfaces, preserving the single intelligence layer.

#### 1. Readiness — `overview`

**Question:** "What can my team draw on right now?"

Data surfaced (all from `format_compact_index`):
- Workspace section: Identity + Brand richness badges (`Empty | Sparse | Rich`). Value labels are state descriptors, not to-do items: "Empty", "Voice and tone defined", "Partially defined".
- Workforce count (domain agents + bots, any flagged)
- Work (active tasks + stale tasks counts)
- Knowledge (canonical context domains with per-domain file counts, recent uploads)
- Platforms connected
- Budget (credits used / limit, exhausted flag)

No action buttons in the tab. Link-outs to `/context`, `/agents`, `/work` for follow-through.

**Default tab on manual open.** This is the default for the "Workspace" button — click it, see operational readiness.

**TP opens via:** `<!-- workspace-state: {"lead":"overview","reason":"..."} -->` on explicit user ask ("show me the state of things").

#### 2. Attention — `flags`

**Question:** "Is there anything TP wants me to notice?"

Aggregates all gap / flag signals TP currently holds:
- Identity empty — nudge to capture (routes to opening Onboarding modal)
- No tasks yet — nudge to create
- Stale tasks (N haven't run in 2x schedule)
- Budget exhausted
- Agent health flags (from `agents_flagged`)
- Inference gaps (from `detect_inference_gaps`, ADR-162 sub-phase A)
- Recent uploads pending processing (ADR-162 sub-phase B)

Each signal is a card with a one-line description and an optional **"Ask TP"** button that sends a pre-composed prompt to TP (auto-send on click, using the same `sendMessage` path as plus-menu actions). The modal closes and the user sees TP's response streaming into the conversation. "Ask TP" is the only action affordance in the entire Workspace modal, and its effect is to route back to chat — the single intelligence layer.

**TP opens via:** `<!-- workspace-state: {"lead":"flags","reason":"3 stale tasks"} -->` when gap severity warrants attention.

#### 3. Last session — `recap`

**Question:** "What did TP and I talk about before?"

Surfaces TP's cross-session memory:
- Shift notes — AWARENESS.md preview (TP's notes from prior session closes)
- Conversation summary — rolling compaction from `/workspace/memory/conversation.md`
- Recent sessions list (last 3-5 with timestamps + one-line summary, click to jump back via session navigation)

Read-only. No write form, no "forget this" action inside the tab.

**TP opens via:** `<!-- workspace-state: {"lead":"recap","reason":"Picking up from last time"} -->` on returning-user first turn when AWARENESS.md has unread shift notes.

#### 4. Activity — `activity`

**Question:** "What has my workforce been doing lately?"

Merges the former v7 `briefing` + `recent` tabs (they were redundant — both read tasks + last_run_at and answered adjacent questions). Two compact sections in one scroll:
- **Recent runs** — last 5 completed or in-progress task runs, with status icons + relative time
- **Coming up** — next 3-5 scheduled runs

Click-through to `/work` for the full view. This tab is intentionally thin — `/work` is the destination; this tab is the glance.

**TP opens via:** `<!-- workspace-state: {"lead":"activity","reason":"3 ran overnight"} -->` after fresh runs the user hasn't seen yet, or on explicit ask ("what's running").

### Onboarding Modal — Single Surface

Wraps the existing `ContextSetup` component unchanged. One form, one submit, one dismiss. On submit, composes links + files + notes into a single message to TP, TP handles context inference via `UpdateContext` and `ManageDomains` as it does today.

**TP opens via:** `<!-- onboarding -->` (empty directive — just the presence of the marker) on the first turn of a session when `workspace_state.identity == "empty"`. No `lead` field needed — the modal has only one surface.

**Not opened by:** the Workspace button, the plus menu, any other user action. Returning users who want to add context to the workspace do so through chat (just type what you want TP to know, or use `+` → Attach file, which drops the file into the next message).

### Marker Channels (two, not one)

Two HTML-comment markers, two parsers, two modals. Keeping them separate prevents the conflation v7 fell into.

```
<!-- workspace-state: {"lead":"<lead>","reason":"<short reason>"} -->
<!-- onboarding -->
```

Valid `lead` values for the Workspace modal: `overview | flags | recap | activity`. Tab labels in the UI are the capability-framed versions (`Readiness | Attention | Last session | Activity`); the JSON enum is a short machine-readable keyword that TP emits reliably. Invalid leads silently no-op.

The parser module exports two functions: `parseWorkspaceStateMeta` and `parseOnboardingMeta`. Both are called from `ChatSurface` on each new assistant message, and both strip their marker from the displayed body. At most one of each marker per message; TP is instructed to never emit both.

### Manual Override

The surface header contains a single button labeled **"Workspace"** with an icon (`LayoutDashboard`). Clicking it toggles the Workspace modal. The default tab on manual open is `overview` ("Readiness") — the operational readiness view.

No manual trigger for the Onboarding modal. No plus-menu entry for either.

### Non-Goals

- No floating windows, no draggable panes, no dock
- No always-on artifact strip
- No frontend heuristics for "is this user new" — TP owns the onboarding decision via the marker
- No duplicate implementation of `/work`, `/agents`, or `/context` — full inspection still belongs to those surfaces
- No new top-level surface — `/chat` keeps its place in ADR-163's four
- No write forms in the Workspace modal — diagnostic only
- No `isEmpty` prop on `WorkspaceStateView` — the soft gate is gone; the Onboarding modal handles the cold-start case

---

## Implementation

Detailed implementation notes live in `docs/design/WORKSPACE-STATE-SURFACE.md`.

### File Layout (v8)

```
web/components/chat-surface/
  ChatSurface.tsx              — page-level controller; owns both modal open states,
                                 parses both markers, renders Workspace + Onboarding modals
  WorkspaceStateView.tsx       — Workspace modal: 4 read-only tabs, no forms, no isEmpty prop
  OnboardingModal.tsx          — Onboarding modal: wraps ContextSetup, single surface
  ContextSetup.tsx             — identity capture form (unchanged, now consumed only by OnboardingModal)

web/lib/
  workspace-state-meta.ts      — TWO parsers: parseWorkspaceStateMeta + parseOnboardingMeta
                                 and TWO strippers: stripWorkspaceStateMeta + stripOnboardingMeta
```

### Files Deleted in v8

```
web/components/home/DailyBriefing.tsx   — sole consumer was v7 WorkspaceStateView's briefing lead.
                                          Merged inline into the "Activity" tab.
```

### TP Prompt Update (v8)

`api/agents/tp_prompts/onboarding.py` "Workspace State Surface" section rewritten:
- Marker ruleset split: `workspace-state` marker (4 leads: `overview | flags | recap | activity`) and new `onboarding` marker (empty directive).
- Tab labels in the TP prompt reference the capability-framed names (`Readiness`, `Attention`, `Last session`, `Activity`) so TP's `reason` field matches user-facing language.
- Cold-start first-turn rule now emits `<!-- onboarding -->` instead of the v7 `<!-- workspace-state: {"lead":"context"} -->`.
- Gap-detection rule emits `lead=flags` (was `lead=gaps`); fresh-runs rule emits `lead=activity` (was `lead=briefing`); explicit-ask rule emits `lead=activity` (was `lead=recent`); show-me-state rule emits `lead=overview`.

See `api/prompts/CHANGELOG.md` entry for the v8 delta.

### Chat Column Width

Unchanged from v6: `/chat` page wrapper is capped at `max-w-3xl` (768px).

### ChatPanel Changes (v8)

- `ChatPanel.tsx` strips **both** markers from displayed assistant message content: `stripWorkspaceStateMeta()` AND `stripOnboardingMeta()`. Both strippers are idempotent and safe to chain.
- Applied at both rendering paths (MarkdownRenderer + MessageBlocks text-block branch).
- `inputRowAddon` prop unchanged (preserved for other callers).

### Modal Mechanics (shared between Workspace and Onboarding)

Both modals use the same plain-div `role="dialog" aria-modal="true"` pattern:

- Backdrop: `bg-foreground/40 backdrop-blur-sm`, click-outside dismisses
- Esc key closes (window-level keydown listener mounted while open)
- Body scroll lock while open (saves and restores `document.body.style.overflow`)
- Centered, `max-w-2xl`, `max-h-[60vh]` content area, `py-[10vh]` viewport offset
- Animated via Tailwind `animate-in fade-in zoom-in-95`

Both modals are never open simultaneously — `ChatSurface` state machine enforces exclusivity.

### Workspace Toggle Button Placement

The toggle button sits in `SurfaceIdentityHeader.actions` alongside the page identity (unchanged placement from ADR-167 v5). Label text: `Workspace`. Icon: `LayoutDashboard`.

---

## Consequences

### Positive

- `/chat` reads as a TP chat product. The default visual weight is the conversation, exactly like Claude Code or ChatGPT.
- Diagnostic and capture are now honest about being different jobs. The Workspace modal can't accidentally feel like a form; the Onboarding modal can't accidentally feel like a dashboard. Users don't have to parse "why are my tabs hidden?" on first visit.
- The single intelligence layer (ADR-156) is preserved end-to-end — TP decides, frontend executes. The Workspace modal routes all write intent back through chat ("Ask TP" buttons drop pre-filled prompts, never auto-send or call tools directly).
- Tab labels frame operational readiness. A user sees "Readiness / Attention / Last session / Activity" and understands capability state, not profile completeness.
- The Workspace tabs map 1:1 to `format_compact_index` sections, so the UI is a direct visualization of what TP sees each message. When new signals land in the compact index (future ADR), the corresponding tab gets richer; there's a clear contract for where new data surfaces.
- Adding a new diagnostic tab in the future is one branch in `WorkspaceStateView` + one valid value in the `lead` enum + one TP prompt rule. Onboarding stays out of this growth path — separate lifecycle, separate surface.

### Costs

- TP must learn the new marker schema. The v7 → v8 enum change (`context | briefing | recent | gaps` → `overview | flags | recap | activity` + new `onboarding` marker) is a breaking change to the marker channel — any persisted v7 markers in `session_messages.content` will silently no-op on parse (invalid lead). This is acceptable because the marker is a transient directive, not reference data.
- Two markers instead of one means two parsers, two stripper calls, slightly more cognitive load in `ChatPanel` render paths. Mitigated by keeping both parsers in the same `workspace-state-meta.ts` module with a shared shape.
- The Onboarding modal has no manual trigger, which means returning users cannot re-open the "Tell me about yourself" form after dismissing it. This is intentional — re-entry for context updates is chat itself ("here's a new doc about our team..." → TP handles via `UpdateContext`). But if a user bounces off the form the first time and wants to come back, they'll need to know to type.

### Mitigations

- Marker ruleset owned by `api/agents/tp_prompts/onboarding.py` — version-controlled, tracked in `api/prompts/CHANGELOG.md`, single source of truth.
- Both parsers validate marker shape; invalid markers silently no-op.
- Cold-start discovery moves to TP's first reply (prompt rule "first turn, empty identity → emit `<!-- onboarding -->`"). This is the correct seam: TP greets, TP opens the surface. Every new user sees the Onboarding modal on their first assistant message.
- If a returning user needs to re-enter onboarding-style bulk capture, they can say "let me give you a bunch of context" and TP will guide them through chat — the single intelligence layer handles it without needing a dedicated form. The form is a first-run convenience, not an ongoing interaction mode.

---

## Revision History

| Date | Version | Change |
|---|---|---|
| 2026-04-09 | **v8** | **Onboarding and workspace-state inspection split into two separate modals. The v7 "four peer tabs including Add context" design conflated a read-only diagnostic dashboard with a write form; the `isEmpty` soft gate was the symptom of that category error. v8 corrects it: `WorkspaceStateView` is the Overview modal with four read-only tabs (`What I know`, `Heads up`, `Last time`, `Team activity`), each mirroring a slice of `format_compact_index`. `OnboardingModal` is a new sibling modal wrapping the existing `ContextSetup` form unchanged. Marker enum changed: `context | briefing | recent | gaps` → `overview | flags | recap | activity`, and a new `<!-- onboarding -->` marker drives the Onboarding modal. Two markers, two parsers, two modals — never conflated. `isEmpty` prop deleted from `WorkspaceStateView`. The soft-gate switcher-hide is gone; tabs are always visible when the Overview modal is open. Default tab on manual open is `overview` (honest "show me the state" answer, not a computed lead). `WorkspaceStateView`'s `briefing` + `recent` tabs merged into one `activity` tab (they were redundant — both read tasks+last_run and answered adjacent questions). `gaps` tab expanded to `flags` which aggregates all six gap signals from the compact index (identity empty, no tasks, stale tasks, budget exhausted, agent health, inference gaps, recent uploads). New `recap` tab surfaces TP's cross-session memory (AWARENESS.md + conversation summary + recent sessions) — continuity is now first-class UI. `ContextSetup` component unchanged (still takes `onSubmit(message)`, still `embedded` mode, just moves consumer from `WorkspaceStateView` to `OnboardingModal`). `DailyBriefing.tsx` DELETED — v7's only consumer was `WorkspaceStateView`'s briefing lead; v8 rebuilds the same data directly in the `activity` tab. TP prompt `api/agents/tp_prompts/onboarding.py` "Workspace State Surface" section rewritten for v8 marker schema and layperson tab labels. Overview button label changed from "Workspace state" to "Overview", icon changed from `LayoutPanelTop` to `LayoutDashboard`. No plus-menu entry for either modal. No `isEmpty` logic anywhere. Singular implementation: one surface per job, one modal per lifecycle, no soft gates. See `api/prompts/CHANGELOG.md` for prompt entry.** |
| 2026-04-09 | v7 | **`empty` lens value dissolved into `context` peer tab. Gate behavior decoupled from lens identity — the cold-start switcher-hide is now driven by `isEmpty` (workspace-state boolean) alone, not by a special lens value. Four peer tabs in the switcher: What changed / Running / Coverage / Add context (`Sparkles` icon). `WorkspaceStateLead` union updated in `workspace-state-meta.ts` and `WorkspaceStateView.tsx` — `'empty'` removed, `'context'` added. `VALID_LEADS` set updated. `computeLead()` cold-start branch returns `'context'` instead of `'empty'`. `EmptyLead` component renamed to `ContextLead`. Soft-gate expression changed from `activeLens !== 'empty' && !isEmpty` to just `!isEmpty`. Plus-menu "Update my context" action deleted in `ChatSurface.tsx` (along with the `openWithLead` callback and `Settings2` import) — the peer tab is the only re-entry path now. Singular implementation: one surface, one way in, one uniform component. TP prompt updated in `api/agents/tp_prompts/onboarding.py`: marker `lead` enum changed, "two namespaces" explainer added to prevent conflation between the backend `workspace_state.identity` dict field (`empty | sparse | rich` — stays) and the client lens value (`context` — new). Fifth marker rule added: user wants to add more context after onboarding → emit `lead=context`. Prompt version note bumped v5 → v7. Backend fixtures in `test_recent_commits.py` UNCHANGED (they reference `workspace_state.identity = "empty"` which is the dict-field namespace, unrelated to the lens rename). See `api/prompts/CHANGELOG.md` entry `[2026.04.09.3]`.** |
| 2026-04-08 | **v6** | **Surface promoted to a true modal (backdrop, Esc, body scroll lock, click-outside dismiss). Frontend cold-start auto-open removed — discovery is TP's job, the prompt's existing "first turn, empty identity → emit `lead=empty`" rule handles new users on TP's first reply instead of on page mount. `CHAT_EMPTY_STATE` stub deleted (TP's greeting is the empty state on `/chat`). `isNewUser` prop dropped from ChatSurface. `topContent` prop deleted from ChatPanel (was only used by the v5 inline overlay). `emptyState` prop preserved on ChatPanel for `/work` and `/agents` slide-in chat use cases. Toggle icon repositioned to immediately right of the `+` button (left-side affordance group), not next to the submit button. Marker schema, parser, and TP prompt unchanged. No new dependencies (modal built with plain fixed-position div + ARIA dialog attributes). Singular-implementation purge: deleted ~2,100 lines of pre-ADR-163 orphan code — `web/components/desk/` (6 files), `web/components/surfaces/` (3 files), `web/components/PlatformOnboardingPrompt.tsx`, `web/hooks/usePlatformOnboardingState.ts`, plus the matching barrel export — none of which were reachable from any live route after the four-surface restructure.** |
| 2026-04-08 | v5 | Single workspace state surface, TP-directed open via HTML-comment marker. Four lead views as internal state of one component. Chat column capped to max-w-3xl. Legacy artifact files deleted. ADR + design doc renamed from "chat artifact surface" → "workspace state surface". |
| 2026-04-08 | v4 | Clarifies that artifacts and artifact tabs render inside the TP chat surface, not above a separate bordered chat panel. |
| 2026-04-08 | v3 | Clarifies that TP Console is the base chat surface, not an artifact tab. Global nav keeps its original sizing while adopting the black active segment. |
| 2026-04-08 | v2 | Replaces the multi-window command desk with a single chat artifact surface: one primary chat console plus one active artifact selected by tabs. |
| 2026-04-08 | v1 | Initial command-desk proposal. Rejected after first implementation because multiple floating windows were visually unintuitive. |
