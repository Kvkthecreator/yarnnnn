# Onboarding & YARNNN Awareness — Design Brief

**Status:** Active (v5 — cockpit-aligned cold-start; `/chat`-modal flow preserved for re-entry only)
**Date:** 2026-04-21
**Supersedes:** v4 (2026-04-09, `/chat`-modal cold-start flow) — cold-start portion superseded; re-entry modal flow preserved.
**Depends on:** [SURFACE-CONTRACTS.md](SURFACE-CONTRACTS.md) (ADR-215, per-tab contracts + Chat empty-state cold-start behavior), [WORKSPACE-STATE-SURFACE.md](WORKSPACE-STATE-SURFACE.md), [ADR-203](../adr/ADR-203-first-run-guidance-layer.md) (first-run guidance layer), ADR-155 (workspace inference), ADR-165 v7 (workspace state surface)

---

## The Model: Cockpit cold-start + `/chat`-modal re-entry

Onboarding has two entry points now, each aligned with the operator's actual landing behavior:

| Entry point | Triggered by | Surface | Flow |
|---|---|---|---|
| **Cold-start** (new signup) | Auth callback redirects to `HOME_ROUTE = /overview` (ADR-199); OverviewSurface detects semantic day-zero | `/overview` with ambient rail open + `OverviewEmptyState` rendered | Structured greeting + three first-move cards; YARNNN greets in rail; operator converses inline |
| **Re-entry** (existing operator adds context later) | Operator opens WorkspaceStateView modal from `/chat` surface-header toggle | `/chat` with `WorkspaceStateView` modal | Modal's `context` peer tab renders `ContextSetup`; same form-based URL + file + notes capture as v4 |

**Two namespaces, never confuse them:**

- **`workspace_state.identity`** (backend compact index): `empty | sparse | rich`. Classifies IDENTITY.md richness. YARNNN reads it.
- **`lead`** (client marker payload): `overview | flags | recap | activity`. Names the WorkspaceStateView modal tab. YARNNN writes it when appropriate for `/chat` re-entry.

**Cold-start on `/overview` does NOT emit a modal marker.** ADR-203 made this explicit: when the current surface is `/overview` and identity is `empty`, YARNNN greets the operator directly in the ambient rail + the Overview surface's own `OverviewEmptyState` component renders a structured greeting. No modal opens — the cockpit itself is the onboarding surface.

```
# Cold-start (new signup) — ADR-203 flow
Sign up → auth callback → /overview (HOME_ROUTE)
  → OverviewSurface.detectSemanticDayZero() returns true
  → OverviewEmptyState renders: 4-section structured greeting
     (welcome / what's here / what's missing / three first moves)
  → ambient YARNNN rail opens by default with seeded first-session prompt
  → operator submits draft or clicks a first-move card →
     rail seeds purpose-specific prompt → YARNNN greets + offers
     describe-work / walk-cockpit / connect-platform
  → YARNNN scaffolds via UpdateContext + ManageDomains as user describes
  → semantic day-zero flips to false once operator authors anything
     (agent with origin != 'system_bootstrap', or task with !essential)

# Re-entry (existing operator) — v4 modal flow preserved
User clicks Workspace button on /chat header, OR YARNNN detects
fresh runs / unread shift notes / coverage gaps / explicit ask
  → YARNNN emits <!-- workspace-state: {"lead":"<tab>"} -->
  → WorkspaceStateView modal opens with that tab active
  → "Add context" (context peer tab) remains the re-entry path for
     continued identity enrichment
```

### Two namespaces, never confuse them

- **`workspace_state.identity`** (backend compact index) is `empty | sparse | rich`. It classifies IDENTITY.md richness. TP reads it.
- **`lead`** (client marker payload) is `context | briefing | recent | gaps`. It names the tab the client opens. TP writes it.

"empty" is what TP reads *about* identity. "context" is the lens name the user clicks. TP never emits `lead=empty` — that value doesn't exist in the frontend enum.

No separate onboarding page. No separate empty state. No second entry point.
The `/chat` empty state is just a chat prompt — onboarding only appears when TP
(or the user via the plus menu) opens the modal.

### Why Fold Onboarding Into the Modal

1. **Same signal drives all facets.** `workspace_state` is computed once per turn
   in `working_memory.py`. "Is this a new user?" is just `identity == "empty"` —
   the same dict TP reads to decide whether to surface briefing, gaps, or recent
   work. Having a separate onboarding component would mean a second derivation
   of the same signal.

2. **TP owns discovery.** ADR-165 v6 moved discovery responsibility entirely
   to TP via the marker pattern. The frontend no longer auto-opens anything on
   cold start. TP's onboarding prompt emits `lead=context` on the first turn when
   `workspace_state.identity == "empty"`. One code path, one decision-maker.

3. **Re-entry works for free.** Users who want to add context later — after
   onboarding is "done" — open the workspace state modal and click the
   "Add context" peer tab, landing in the same `context` lens that served cold
   start. Onboarding and context updates are the same action served by the
   same lens; there is no distinction because there is no separate "onboarding
   phase" in the data model.

4. **Single comprehensive surface.** The modal is already the one structured
   surface on `/chat`. Putting onboarding anywhere else would mean two surfaces
   showing workspace-state information, which is exactly what ADR-165 collapsed.

---

## Cold-Start Flow (ADR-203 — cockpit-native)

### 1. Auth callback → /overview

New users redirect from auth callback to `HOME_ROUTE = /overview` (per ADR-199).
No interstitial, no wizard. The Overview surface renders immediately.

### Legacy note: pre-ADR-203 flow (/chat landing) superseded

The v4 flow redirected new users to `/chat` and used a TP-emitted marker to
open the WorkspaceStateView modal with `ContextSetup` soft-gated. That flow
is superseded for new signups by the ADR-203 cockpit-native cold-start below.
The `/chat`-modal machinery remains in place for re-entry (existing operators
coming back to add more context).

### 2. OverviewSurface detects semantic day-zero

`OverviewSurface.detectSemanticDayZero()` reads `/api/agents`, `/api/tasks`,
`/api/proposals` and filters out the scaffold:

- Agents with `origin === 'system_bootstrap'` don't count (signup-scaffolded YARNNN + Specialists + Platform Bots)
- Tasks with `essential === true` don't count (back-office + daily-update heartbeat)
- Pending proposals always count

If all three filtered categories are empty, semantic day-zero is true — the
workspace is provisioned but the operator hasn't authored anything yet. This
is the common new-signup state post-ADR-189.

The surface renders `OverviewEmptyState` (four-section structured greeting)
instead of the three-pane `NEEDS ME / SINCE LAST LOOK / SNAPSHOT` layout.

### 3. Ambient YARNNN rail opens by default with a seeded prompt

Overview page wires `ThreePanelLayout.chat.defaultOpen = true` when semantic
day-zero resolves. A `draftSeed` is placed in the composer with the first-
session prompt: *"I just signed up — help me understand what YARNNN is and
what I should do first..."*

The seed is NOT auto-sent. The operator sees it, edits or submits as-is.
This respects operator agency — YARNNN has introduced itself via the
OverviewEmptyState content + the ambient rail; the operator remains the
first-mover on actual conversation.

### 4. YARNNN cockpit-first-run prompt branch

When YARNNN receives the first user message AND `workspace_state.identity == "empty"`
AND current surface is `/overview`, the onboarding prompt (`yarnnn_prompts/onboarding.py`)
instructs: *greet warmly, name Overview's structure briefly, offer three
options — describe-work / walk-cockpit / connect-platform — harmonize with
(don't repeat) the OverviewEmptyState content, let the operator pick.*

YARNNN does NOT emit a modal marker in this flow. The modal is not the
cold-start surface on `/overview`.

TP writes a greeting line plus the marker:

```
Welcome — tell me a bit about you and I'll get your team set up.

<!-- workspace-state: {"lead":"context","reason":"Tell me about your work to get started"} -->
```

### 5. YARNNN scaffolds the workspace as the conversation produces content

Same scaffold pipeline as v4, reached via rail conversation instead of modal
form submission:

1. `UpdateContext(target="identity")` — scaffolds IDENTITY.md from inferred content (as operator describes work, uploads docs, pastes URLs in the rail)
2. `ManageDomains({entities: [...]})` — scaffolds context domain folders
3. `ManageTask(action="create", ...)` — creates initial tracking tasks for populated domains
4. `ManageTask(action="trigger")` — triggers first runs immediately

Once the operator authors anything (an agent with `origin !== 'system_bootstrap'`,
or a task with `essential !== true`), `detectSemanticDayZero()` returns false
on next `/overview` load. Overview reverts to its normal three-pane layout.
The rail returns to default-closed. Cold-start is permanently past for this
workspace.

### (Legacy) /chat modal cold-start — v4 only

The section below describes the v4 `/chat`-modal cold-start flow. Retained as
reference; not executed for new signups post-ADR-203. The *modal machinery*
(WorkspaceStateView + ContextSetup) is preserved for re-entry (§Re-Entry below).

<details>
<summary>v4 cold-start flow (superseded)</summary>

`ChatSurface` parses the marker, opens `WorkspaceStateView` with `lead="context"`,
which renders `<ContextSetup embedded />` as the active lens content. The lens
switcher is hidden because `isEmpty === true` (soft gate), so the new user stays
focused on capture.

`ContextSetup` offers three inputs:

| Section | Input | What happens |
|---|---|---|
| **Links** | Paste URLs (company site, LinkedIn) | Composed into TP message — TP fetches + infers identity |
| **Files** | Upload PDF, DOCX, TXT, MD | Uploaded via `api.documents.upload`, referenced in TP message |
| **Notes** | Free-text textarea | Composed into TP message |

On submit, all inputs compose into a single TP message, the modal closes, and
the message is sent to TP via `onContextSubmit`.

</details>

---

## Re-Entry: The "Add context" peer tab

After onboarding is complete, users can add more context at any time by opening
the workspace state modal (via the surface-header toggle on `/chat`) and clicking
the **"Add context"** tab — the fourth peer lens alongside What changed / Running /
Coverage. The same `ContextSetup` component renders inside. Same inputs, same flow,
same result.

This is intentional: **onboarding and context updates are the same action, served
by the same lens.** There is no "onboarding phase" that ends. Identity enrichment is
continuous. Users who learn the modal once know how to add context forever.

v7 deleted the previous plus-menu "Update my context" action as redundant — the
peer tab is always visible in the switcher whenever the modal is open (except during
cold-start soft gate), so there is no need for a second discoverability path.
Singular implementation: one surface, one way in.

---

## TP Prompt Guidance

`api/agents/tp_prompts/onboarding.py` provides the marker contract and decision
rules for when to emit each lead value. Key points:

- **First message of a session, `workspace_state.identity == "empty"`** → emit `lead=context`
- **Fresh runs since last close** → emit `lead=briefing`
- **User asks "what's running"** → emit `lead=recent`
- **Coverage gaps detected** → emit `lead=gaps`
- **User explicitly wants to add more context after onboarding** → emit `lead=context`
- **Never more than one marker per message**
- **Steady state with nothing new → silence (no marker)**

TP reads `workspace_state.identity` (`empty | sparse | rich`) from the compact
index and judges. The prompt sets priorities, not mechanical rules.

**Namespace discipline:** `workspace_state.identity` is backend dict-field state; `lead`
is the frontend tab name. `empty` is a value TP reads about identity; `context` is a value
TP writes as a marker. TP never emits `lead=empty`.

**ADR-155 principle:** No shadow intelligence. When the user provides identity,
TP — not a backend service — decides what entities to scaffold. TP may scaffold
3 competitors for one user and 0 for another, based on what it learned.

---

## What Changed

### v4 → v5 (2026-04-21, ADR-203 — cockpit-native cold-start)

| v4 (/chat-modal cold-start) | v5 (/overview cold-start, /chat modal for re-entry) |
|---|---|
| New signup redirected to `/chat` | New signup redirected to `/overview` (HOME_ROUTE per ADR-199) |
| TP emitted `lead=context` marker to open modal | Overview surface detects semantic day-zero + renders `OverviewEmptyState` + opens ambient rail with seeded prompt; YARNNN greets in rail |
| `ContextSetup` form (URLs/files/notes) was the primary capture surface | Rail conversation is the primary capture surface (YARNNN reads uploads/URLs from rail input directly); `ContextSetup` preserved for modal re-entry only |
| Soft gate: switcher hidden until workspace had tasks | Semantic day-zero: the Overview surface itself replaces panes with the greeting; no modal involved |
| Day-zero triggered by `workspace_state.identity == "empty"` | Day-zero triggered by structurally-scaffolded + operator-has-not-acted (origin/essential filters) |
| Cold-start surface = `/chat` | Cold-start surface = `/overview` |

The modal (`WorkspaceStateView` + `ContextSetup`) stays for re-entry — operator
comes back later, clicks Workspace button on `/chat`, opens "Add context" peer
tab, same form-based capture.

### v3 → v4 (2026-04-09, ADR-165 v7 — `empty` lens dissolved)

| v3 (ContextSetup as `empty` lead) | v4 (ContextSetup as `context` peer lens) |
|---|---|
| Four leads: `empty | briefing | recent | gaps` | Four peer leads: `context | briefing | recent | gaps` |
| `empty` was special — switcher hidden exclusively for this lens | `context` is a peer tab; switcher hidden only when `isEmpty` (soft gate) |
| Re-entry via plus-menu "Update my context" action (opens `lead=empty`) | Re-entry via "Add context" peer tab in lens switcher (no plus-menu action) |
| Gate was coupled to lens identity | Gate decoupled — driven by `isEmpty` workspace-state boolean |
| Two concerns in one name (visual + gate) | Two concerns cleanly separated |

### v2 → v3 (2026-04-09, ADR-165 v6 consolidation)

| v2 (ContextSetup as /chat empty state) | v3 (ContextSetup as modal `empty` lead) |
|---|---|
| `/chat` empty state rendered `ContextSetup` inline | `/chat` empty state is a neutral chat prompt |
| Two implicit trigger sites (empty state + plus menu) | One trigger site — modal `empty` lead |
| Modal was for briefing/recent/gaps; onboarding was separate | Modal is for all four facets including onboarding |
| Frontend decided when to show onboarding (empty state detection) | TP decides via marker; frontend executes |
| "New user" was a frontend concept | "New user" dissolves — `identity == "empty"` is just a facet |

### v1 → v2 (2026-04-04)

| v1 (/context setup-phase hero) | v2 (/chat empty state) |
|---|---|
| `/context` detected setup phase, rendered ContextSetup as hero | Auth callback redirected new users to `/chat` |
| Two onboarding paths (context hero + agents chat panel) | One onboarding path (/chat empty state) |

---

## ContextSetup Usage (Canonical)

`ContextSetup` has **exactly one consumer** in the entire frontend:

| Consumer | Path | Role |
|---|---|---|
| `WorkspaceStateView` | `context` peer lens view | Identity capture on cold start (soft-gated) + re-entry via "Add context" peer tab |

It is not imported anywhere else. Previously also rendered as:
- `/context` setup hero (v1 — removed in v2)
- `/chat` inline empty state (v2 — removed in v3)
- `/agents` chat panel empty state (removed in v2)
- The `empty` lead of the modal (v3 — replaced in v7 by the `context` peer lens)

All four prior placements removed. `ContextSetup` is now structurally a private component of `WorkspaceStateView`, co-located under `web/components/chat-surface/`.

---

## References

- `web/components/chat-surface/WorkspaceStateView.tsx` — the single modal (ADR-165 v7)
- `web/components/chat-surface/ContextSetup.tsx` — identity capture component (sole consumer: `WorkspaceStateView` `context` peer lens)
- `web/components/chat-surface/ChatSurface.tsx` — modal open/close, marker parsing, surface-header toggle
- `web/lib/workspace-state-meta.ts` — marker parser (valid leads: `context | briefing | recent | gaps`)
- `api/agents/tp_prompts/onboarding.py` — TP marker guidance + onboarding flow
- `api/services/working_memory.py` — `workspace_state` dict construction + `format_compact_index()`
- `web/app/auth/callback/page.tsx` — new user detection + `/chat` redirect
- `docs/design/WORKSPACE-STATE-SURFACE.md` — full modal design
- `docs/adr/ADR-165-workspace-state-surface.md` — v7 design decision
