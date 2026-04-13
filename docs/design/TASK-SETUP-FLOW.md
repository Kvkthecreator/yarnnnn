# Task Setup Flow — Structured Intent Capture for Task Creation

**Version:** v1.0 (2026-04-13)
**Status:** Canonical
**Governed by:** [ADR-178](../adr/ADR-178-task-creation-routes.md) — Task Creation Routes
**Parallel pattern:** [SHARED-CONTEXT-WORKFLOW.md](./SHARED-CONTEXT-WORKFLOW.md) — identity/brand capture via ContextSetup

---

## Design Thesis

**Inference is the method for both context and task creation.**

`ContextSetup` (identity onboarding) and `TaskSetup` (task creation) are the same interaction shape applied to two different domains:

| | ContextSetup | TaskSetup |
|---|---|---|
| **Intent** | "Tell me about yourself" | "What do you want to work on?" |
| **Structured signals** | None — everything inferred | Route, surface, mode, cadence, delivery |
| **Raw materials** | Links, files, notes about the user | Links, files, notes about the work domain |
| **TP action** | `UpdateContext(target="identity")` → `infer_shared_context()` | `ManageTask(action="create")` with inferred params |
| **Output** | IDENTITY.md populated | Task + DELIVERABLE.md scaffolded |
| **Gap detection** | One Clarify if high-severity gap | One question if `type_key` or entities unclear |

The critical insight: structured fields (mode, cadence, delivery) cannot be inferred from raw materials — they are **decisions the user makes**. Raw materials (competitor URLs, a brief PDF, a list of entities) cannot be replaced by structured fields — they are **domain scope** that seeds the task's context domain and DELIVERABLE.md. Both are required for a high-accuracy task creation.

---

## Why This Exists

The prior "Start new work" entry point sent a blank message to TP: `"I want to create a task. What do you suggest based on my context?"` This forced TP into 3–4 clarifying rounds before it had enough signal to call `ManageTask`. For context capture (ContextSetup), the same problem was solved by collecting raw materials upfront and composing a rich message. TaskSetup applies that same fix to task creation.

**The four gaps in the old path:**
1. TP doesn't know if the user wants an output or to track a domain (Route A vs B)
2. TP doesn't know the surface type (report vs deck vs dashboard) — drives the entire compose pipeline
3. TP doesn't know mode (recurring vs goal) — determines scheduling, evaluation, completion
4. TP doesn't know the domain entities or scope — requires back-and-forth unless materials are provided upfront

---

## Two Routes

### Route B — Context-Driven ("Track something")

**User intent anchor:** a domain or entity set they want monitored.
> "Track these 5 competitors." "Watch our GitHub for changes." "Keep tabs on relationships."

**What TP needs:**
- Which context domain (`competitors`, `market`, `relationships`, `projects`, custom)
- Entity scope — what specifically (which competitors? which people?)
- Cadence — how often
- Sources — web search only, or platform-connected (Slack/Notion/GitHub)

**Raw materials that seed it:**
- Links to competitor/market sites → TP creates initial entity profiles
- Files (CRM export, contact list, competitive analysis) → extracted entities
- Notes naming specific entities → `focus` parameter on `ManageTask`

**TP output:** `ManageTask(action="create", type_key="track-*", focus=..., schedule=..., sources=...)`
Mode is always `recurring` — context accumulation is open-ended by nature.

---

### Route A — Output-Driven ("Get a deliverable")

**User intent anchor:** an output format they want to receive.
> "I want a weekly competitive brief." "I need a monthly board deck." "Set up a recurring blog post."

**What TP needs:**
- Surface type — `report` / `deck` / `dashboard` / `digest` (drives compose pipeline)
- Mode — `recurring` (runs forever on a schedule) vs `goal` (bounded: a launch, a board date, a meeting)
- Cadence — daily / weekly / monthly (only for recurring)
- Delivery — email vs in-app

**Raw materials that sharpen it:**
- Links to example reports/decks they want to emulate → shapes `page_structure`
- Files (existing brief, prior deck, reference doc) → shapes DELIVERABLE.md expected output
- Notes describing the scope/format → `objective.deliverable` and `objective.format`

**TP output:** `ManageTask(action="create", type_key=..., mode=..., schedule=..., delivery=..., page_structure=...)`

---

## Component: `TaskSetup`

**Location:** `web/components/chat-surface/TaskSetup.tsx`
**Sibling to:** `ContextSetup.tsx` (same directory, same interaction shape)

### Screen 0 — Route selection

Two full-width tap cards. Tapping one advances to Screen 1.

```
┌─────────────────────────────────────┐
│  Track something                    │
│  Competitors, markets, relationships│
│  channels, signals                  │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│  Get a deliverable                  │
│  Report, deck, digest, blog post,   │
│  dashboard                          │
└─────────────────────────────────────┘
```

### Screen 1B — Route B (Track)

```
Domain        [Competitors] [Market] [Relationships] [Projects] [Custom]

How often     [Daily] [Weekly] [Monthly]

Sources       [✓ Web search] [ Slack] [ Notion] [ GitHub]

── Material injection (same as ContextSetup) ──────────────────
Links         [competitor sites, market pages, GitHub repos to seed entities]
Files         [CRM export, contact list, existing competitive analysis]
Notes         "Track Cursor, Linear, Notion. Focused on pricing + product."
────────────────────────────────────────────────────────────────

[Set up tracking →]
```

**Composed message template (Route B):**
```
I want to track [domain] — specifically: [notes/entity description].
Cadence: [weekly]. Sources: [web search, slack].
[If links:] Please fetch these to discover and create initial entity profiles: [url list]
[If files:] I've uploaded context to seed this domain: [file list]
```

### Screen 1A — Route A (Deliverable)

```
Surface       [Report] [Deck] [Dashboard] [Digest]

Mode          [Recurring — runs on a schedule]
              [One-time — has a completion event]

Cadence       [Daily] [Weekly] [Monthly]   ← only shown for Recurring

Delivery      [Email me] [View in app]

── Material injection ─────────────────────────────────────────
Links         [example reports to emulate, reference sources]
Files         [existing brief, prior deck, template, reference doc]
Notes         "Weekly competitive brief. 2 pages max. Focus on pricing."
────────────────────────────────────────────────────────────────

[Set up deliverable →]
```

**Composed message template (Route A):**
```
I want a [surface] — [notes/description].
Mode: [recurring, weekly / one-time goal].
Delivery: [email / in-app only].
[If links:] Reference materials — fetch each and use to shape DELIVERABLE.md: [url list]
[If files:] I've uploaded reference materials: [file list]
```

---

## Message Composition Logic

The composed message always contains:
1. **Route signal** — explicit "I want to track" vs "I want a deliverable" so TP can route without guessing
2. **All structured decisions** — mode, cadence, surface, delivery stated literally (no inference burden)
3. **Raw materials** — same injection as ContextSetup: links phrased so TP fetches them, files listed so TP reads them from uploads, notes as plain text
4. **No questions asked** — the composed message is a complete intent statement; TP should be able to call `ManageTask(create)` in the same turn without clarifying

If the user provides zero raw materials (no links, files, notes), the structured fields alone are sufficient for TP to pick a `type_key` and create the task. The materials upgrade accuracy but aren't required.

---

## Entry Points

| Surface | Trigger | Pre-loaded context |
|---|---|---|
| `/chat` plus-menu | "Start new work" | None (cold start) |
| Heads Up flag | "Suggest work for them" | Idle agent names injected into notes placeholder |
| `/work` (future) | "New task" button | Could pre-set `output_kind` filter as route hint |

---

## What This Is NOT

- **Not a form that creates the task directly.** The composed message goes to TP, which calls `ManageTask`. TP remains the single creation path — this component just gives it better inputs.
- **Not a full task editor.** Advanced fields (custom `page_structure`, `success_criteria`, `context_reads`) are TP's job after creation via evaluate/steer. Setup captures the minimum viable signal.
- **Not gated.** The existing plain-text chat path still works. TaskSetup is a better entry point, not the only one.

---

## Relationship to ContextSetup

Both components share:
- The same material injection layer (links + files + notes)
- The same `api.documents.upload()` call for file handling
- The same "compose → `onSubmit(message)` → `sendMessage()`" closing pattern

They differ in:
- TaskSetup has Screen 0 (route selection) and Screen 1 (structured fields) before the material layer
- The composed message template is task-shaped, not identity-shaped
- The TP action triggered is `ManageTask(create)`, not `UpdateContext(target="identity")`

Future consideration: a single `IntentSetup` parent could house both flows with a top-level split ("Tell me about yourself" vs "Set up some work"). Not implemented now — wait for real usage signal.

---

## Revision History

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-04-13 | Initial — two-route structured capture with material injection |
