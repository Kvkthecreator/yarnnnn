# ADR-670 — The conversation leads: an index, the object, and its supervision

> **Status**: **Accepted** (2026-09-26; operator, on the assessment: *"yes, aligned in full. would like to delegate
> implementation details as we're aligned. ensure singular streamlined discipline with code and docs, scoping in
> deletion and clean-up of code where warranted to avoid future ambiguity"*). Implementation status in §5.
> **Date**: 2026-09-26
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Channel** — how the work an agent does is shown to the member who is
> directing it. No substrate, grant or schema change; every rail reads a store that already exists.
> **Gate**: `api/test_adr670_the_conversation_leads.py`.

**Amends** — ADR-297 D17 (boot restores last-session windows; with nothing to restore it now opens Chat, D1) ·
[PANES.md](../design/PANES.md) §6 (Chat composes a `side`; the Supervisor joins the table) and §11 (the chat-drawer
exemption is deleted with the drawer) · [APP-BUILDER-UX.md](../design/APP-BUILDER-UX.md) §2.2 (band 3 is composed
by the frame, D2). **Completes** — ADR-454 D3 and ADR-632, which retired the chat drawer but left its region
(`main-rail`), its kernel row (`chat-drawer`) and its docs standing (D8). **Preserves** — ADR-438's invariants (one
window manager; window = surface; the frame lives *inside* a surface) · ADR-454's seam rule (a conversation about
one open artifact lives in that artifact's app; everything else in Chat) · ADR-453 D4 / ADR-457 (Properties is the
resting tab in the authoring apps) · ADR-666 D7 (a chat turn's steps render inline, once; `RunView` is the one
rendering of a run) · ADR-637 (attention has one cursor, advanced by visiting) · ADR-644 (one reach structure).

## 1. The problem

Every agentic product that shipped in 2026 made the same inversion, and YARNNN has not made it.

| | Grok Bot (xAI, Aug 2026) | Claude Cowork (→ "one Claude", Sep 16) | Muse (Meta, Sep 2026) |
|---|---|---|---|
| What is central | the thread with a bot; left rail is a **roster of agents** | the conversation | one ongoing chat |
| The agent's work | its own live screen, take-over | **right rail**: Progress · Project (files touched) · Context (reach) | activity log, live browser widget |
| What needs you | a queue of drafts to approve | Allow/Deny, a mode dial | **approvals as a dialog, never a chat message** |
| Depth | roster → thread → screen | list → task → artifact | chat, queues one tap away |

Sources: x.ai/news/introducing-grok-bot · support.claude.com (Cowork get-started, scheduled tasks, projects, live
artifacts) · techcrunch.com 2026-09-16 (chat and Cowork merged) · testingcatalog.com and mindstudio.ai on Muse.
Layout details beyond the primary pages are from secondary write-ups; the post-merge Cowork rail is undocumented.

The shared shape is **index · object · supervision**: what exists and what needs me on the left, the one thing I am
working with in the centre, and what the agent is doing about it on the right.

YARNNN, read on 2026-09-26 at `9de93ef`:

- **The agent is a guest in the app.** In Slides/Blogger/Images/Text, Chat is a tab behind Properties
  (`StudioSurface.tsx:762`, `TextEditor.tsx:215`). In the Supervisor, the conversation is a fixed 440px column
  (`SupervisorSurface.tsx:290`). Chat composes **no side at all** (PANES §6).
- **Where an agent's work shows is five places**: step rows inside a turn (`StreamSteps`), `RunView` in the
  Supervisor, the run tray, Notifications → Activity, Reach → Crossed. None of them sits beside the conversation that
  caused the work.
- **What needs me is three derivations**: the bell's To do (proposals + mentions, `AttentionCenter.tsx:207`), the
  Supervisor's needs-you (`GET /api/supervisor/state` → `services/supervisor_state.py`, a wrapper over
  `list_mentions` alone), and runs waiting on the viewer (the run tray, the Supervisor's runs band). The three disagree
  by construction: the bell never shows a waiting run; the Supervisor never shows a pending proposal.
- **The first layer carries everything.** The Supervisor paints claim · minder · running · needs-you · work · recent ·
  its conversation on one screen. Deeper layers exist (`?supervisor.work=`, `?agents.agent=`, `?chat.detail=`) but
  each surface invented its own; there is no stated grammar.
- **Login lands on nothing.** `/desktop` restores last-session windows; a member with none gets an empty wallpaper
  whose first-time branch cannot fire (`Desktop.tsx:52-66` requires the kept set to be exactly `['chat']`; the Dock
  seeds nine surfaces).
- **The retired drawer still stands**: the `main-rail` region is mounted empty (`ShellCompositor.tsx:129`), the
  `chat-drawer` kernel row is served (`kernel_surfaces.py:1061`) and seeded (`useComposition.ts:79`), and
  `compositor.md:73-113`, PANES §11 and three docstrings still describe it.

## 2. Decisions

### D1 — Boot: nothing to restore opens Chat

Login still boots to `/desktop` and still restores last-session windows (ADR-297 D17 stands for everything it
restores). **When the hydrated window set is empty at boot, the shell foregrounds Chat** — the surface a member acts
from (ADR-435's own reason). Closing every window mid-session still shows the concise "nothing open" state; that is a
choice the member made, not a boot.

**Deleted**: `useIsFirstTime` and the first-time branch of the Desktop empty state, with its catalog keys in every
locale. Chat's own empty state already states the ADR-411 contract (conversations are private; the workspace is the
shared memory; the work lands in files).

### D2 — One frame: index · object · supervision

The agentic surfaces compose PANES' existing model and nothing new:

```
┌ rail: INDEX ─────┬ canvas: OBJECT ─────────┬ side: SUPERVISION ─────┐
│ Needs you (n)    │ the conversation        │ what it made           │
│ who (agent faces)│  — or one piece of work │ what it ran            │
│ the list         │  — or one run (Trace)   │                        │
└──────────────────┴─────────────────────────┴────────────────────────┘
```

`rail` and `side` are chrome through `usePaneSlot`; the canvas never yields; the ladder folds them (PANES §2). There
is no second layout primitive, no new threshold, and no `md:`/`lg:` in a pane's classes. An app keeps its three
bands (APP-BUILDER-UX §2.2): bands 1 and 2 stay the fixed strips above; **band 3 is this frame**.

It applies now to **Chat** and the **Supervisor**. The authoring apps keep their shape (their canvas is the artifact,
their side is Properties · Chat, D7).

### D3 — The supervision side: what it made, what it ran

Two sections, each read from a store that already exists. A section with nothing to show is absent. With both absent,
the side shows one sentence rather than folding away, so the conversation does not jump when the first file lands.

- **Made here** — the files this conversation's turns wrote, newest first, deduplicated by path. Source: the lane's
  messages' `metadata.artifacts`, the very list `ArtifactCard` renders. Opening one follows the one file-open rule
  (ADR-438). No new read.
- **Runs** — runs whose `lane_id` is this conversation **and whose `trigger` is not `chat`**, rendered by `RunView`,
  read from `useRuns`. A chat-triggered run's steps are already inline in its turn (ADR-666 D7); showing them again
  in the side would be the second rendering D7 forbids.

**Refused, named so no one adds them**: a numbered *plan* (no plan primitive exists; a UI-invented checklist is a
claim without a receipt) · a *reach* panel (ADR-644: the one reach structure, rendered at Reach) · a duplicate of the
turn's steps.

### D4 — The index: needs you, who, the list

Chat's lane list gains two strips above its recents:

- **Needs you** — the one queue (D5), capped, each row opening its object.
- **Who** — the agents as faces, from the roster the lane list already receives (`LaneData`). A face is the existing
  who-filter made visible (Grok Bot's roster); choosing it filters the list, and with no conversation yet it starts
  one. No second roster read.

### D5 — One needs-you derivation

`web/lib/attention/useNeedsYou.ts` is **the one client reader** of *what is waiting on me*. It composes three sources:

- pending proposals (`api.proposals.list`)
- unresolved mentions (`api.mentions.list`)
- runs whose `state` is `waiting` and whose `waiting_on` names the viewer (`useRuns`, no second fetch)

It follows the `useRuns` shape: one module-level store, shared by every mount. Every mount reads it:

- the bell's To do (`AttentionCenter`)
- Notifications → To do
- Chat's index
- the Supervisor's index

Resolving a mention stays ADR-637's cursor, and visiting advances it.

**Deleted**:
- `services/supervisor_state.py`, `GET /api/supervisor/state` and its client method
- the Supervisor's own `NeedsYouSection`
- the bell's private proposals + mentions fetch (the bell keeps its timeline and limits reads, which are not "needs you")

Approvals never render as a message in a conversation (the Muse rule). This already holds: proposals live in the queue.

### D6 — One drill grammar: Index → Object → Trace

- **Index**: what is here and what needs me. It is never the place a thing is read in full.
- **Object**: one thing — a conversation, a piece of work, a file, an agent.
- **Trace**: one occurrence of its work — a run, opened full.

Each level is one parameter in the surface's namespace (compositor.md, `?{slug}.{key}`). The level's crumb is set
through `useWindowCrumb`, so the locator strip is the spine: the root crumb returns to the index, and there is no
per-surface back bar. `?{slug}.run=<id>` is the Trace level in every surface that has runs, and renders `RunView` in
the canvas.

**The Supervisor's layers**:

| Layer | rail (index) | canvas (object) | side (supervision) |
|---|---|---|---|
| index | Needs you + the roster of work | the Supervisor's setup conversation (ADR-667 D1) | running now · recently (`RunView`) |
| a work opened (`?supervisor.work=`) | unchanged | that work's own conversation | its runs · its sources · Run now / Pause |
| Trace (`?supervisor.run=`) | unchanged | the run in full | unchanged |

- `StandingDetail` is split between the canvas and the side; it is not kept as a second whole-pane rendering.
- The Supervisor's `lg:` classes are deleted for the ladder (the PANES §11 violation).

### D7 — The authoring apps: Properties rests, a working turn shows

Properties stays the resting tab. When the bound lane has a turn in flight and Chat is not the showing tab, the Chat
tab's label carries a live mark. The mark reads the lane's own busy state, not a second store. Nothing else about the
authoring apps changes.

### D8 — Deletions that end the drawer

Removed together, with the gates that named them updated in the same commit:

- the `main-rail` region: the `ShellCompositor` mount, `types.ts`, `ChromeRegistry` prose
- the `chat-drawer` kernel row and its client seed
- PANES §11's drawer exemption
- `compositor.md`'s drawer sections
- the drawer wording in `ShellChromeContext`
- the stale Supervisor Desk comment in `app/(authenticated)/layout.tsx`

Two corrections ride with it:
- `DOCK_BAND` (`TopBarSurface.tsx:93`) is corrected to the live Dock roster: it still maps `studio` and lacks five
  live surfaces.
- WORKSPACE.md's inventory gains the Supervisor.

## 3. What this does NOT do

- No sidebar for the shell.
- No change to the Dock's contents.
- No change to the window manager or the layout modes.
- No live computer view: browser work runs in the member's own Chrome, which is its own view (ADR-662 D15).
- No replay beyond what `RunView` already renders from `steps`.
- No change to how an agent speaks, so no prompt change.

## 4. Gate

`api/test_adr670_the_conversation_leads.py` reads the code, not the product. Each arm is proven RED by falsifying
the code it guards:

- the deleted names are gone: `main-rail`, `chat-drawer`, `supervisor_state`, `useIsFirstTime`, `NeedsYouSection`
- `useNeedsYou` is the only module that calls `api.mentions.list` or `api.proposals.list`
- the supervision side reads `useRuns` and filters out `trigger === 'chat'`
- the Supervisor carries no `lg:`/`md:` class
- the boot foregrounds `chat` on an empty hydrated set

A click-pass drives both surfaces at the ladder's four rungs.

## 5. Implementation status

- [ ] D1 boot · D8 deletions (shell)
- [ ] D2–D5 Chat frame, supervision side, index, `useNeedsYou`
- [ ] D6 Supervisor into the frame, `supervisor_state` deleted
- [ ] D7 the live mark on the authoring apps' Chat tab
- [ ] Click-pass at the four rungs
