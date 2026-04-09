# Onboarding & TP Awareness — Design Brief

**Status:** Active (v4 — `empty` lens dissolved into `context` peer tab)
**Date:** 2026-04-09
**Supersedes:** v3 (2026-04-09, ContextSetup as `empty` lead inside modal)
**Depends on:** [SURFACE-ARCHITECTURE.md](SURFACE-ARCHITECTURE.md), [WORKSPACE-STATE-SURFACE.md](WORKSPACE-STATE-SURFACE.md), ADR-155 (workspace inference), ADR-165 v7 (workspace state surface)

---

## The Model: Onboarding Is a Peer Tab, Not a Gate

Onboarding is not a separate page, not a separate component, not a separate empty state, and — as of v7 — not even a special lens value. It is the `context` peer lens of the **workspace state modal**, alongside briefing / recent / gaps. The same modal, the same switcher, the same component.

**One signal (`workspace_state`), one mirror (`WorkspaceStateView`), four peer facets
(`context | briefing | recent | gaps`), TP directs.** Cold start is simply the moment
when `workspace_state.identity == "empty"` AND the workspace has no tasks — the frontend
hides the switcher (soft gate) so the new user has a single focused decision to make.
The lens value itself (`context`) is uniform across cold start and re-entry.

```
Sign up → auth callback → /chat
  → first TP turn reads workspace_state.identity (dict field: empty|sparse|rich)
  → if empty: TP emits <!-- workspace-state: {"lead":"context", ...} -->
  → modal opens with ContextSetup rendered; switcher hidden because isEmpty
  → user submits URLs / files / notes → composed TP message
  → TP scaffolds via UpdateContext + ManageDomains
  → modal closes, normal chat continues
  → next time modal opens: switcher shows all four peer tabs
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

## Cold-Start Flow

### 1. Auth callback → /chat

New users (0 tasks) redirect from auth callback to `/chat`. No interstitial,
no wizard. The chat opens with no messages and a neutral input prompt.

### 2. First TP turn emits the marker

TP's onboarding prompt ([`api/agents/tp_prompts/onboarding.py`](../../api/agents/tp_prompts/onboarding.py))
instructs: *"First message of a session, `workspace_state.identity == "empty"` →
emit `lead=context` with `reason="Tell me about your work to get started"`.
Pair with a one-sentence text invitation."*

TP writes a greeting line plus the marker:

```
Welcome — tell me a bit about you and I'll get your team set up.

<!-- workspace-state: {"lead":"context","reason":"Tell me about your work to get started"} -->
```

### 3. Modal opens with ContextSetup

`ChatSurface` parses the marker, opens `WorkspaceStateView` with `lead="context"`,
which renders `<ContextSetup embedded />` as the active lens content. The lens
switcher is hidden because `isEmpty === true` (soft gate), so the new user stays
focused on capture. The gate is driven by workspace state, not by the lens value —
once the workspace has any tasks, the same `context` lens becomes a peer tab in
the visible switcher.

`ContextSetup` offers three inputs:

| Section | Input | What happens |
|---|---|---|
| **Links** | Paste URLs (company site, LinkedIn) | Composed into TP message — TP fetches + infers identity |
| **Files** | Upload PDF, DOCX, TXT, MD | Uploaded via `api.documents.upload`, referenced in TP message |
| **Notes** | Free-text textarea | Composed into TP message |

On submit, all inputs compose into a single TP message, the modal closes, and
the message is sent to TP via `onContextSubmit`.

### 4. TP scaffolds the workspace

TP receives the composed message and calls:

1. `UpdateContext(target="identity")` — scaffolds IDENTITY.md from inferred content
2. `ManageDomains({entities: [...]})` — scaffolds context domain folders
3. `ManageTask(action="create", ...)` — creates initial tracking tasks for populated domains
4. `ManageTask(action="trigger")` — triggers first runs immediately

Normal chat continues from here. The modal does not auto-reopen.

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
