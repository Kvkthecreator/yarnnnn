# Surface Architecture — The Cockpit

**Version:** v15.0 (2026-04-20)
**Status:** Canonical
**Governed by:** [ADR-198 v2](../adr/ADR-198-surface-archetypes.md) — The Cockpit: Operator-Centric Service Model + Surface Archetypes
**Grounded in:** [FOUNDATIONS v6.0](../architecture/FOUNDATIONS.md) — Axiom 2 (Identity), Axiom 3 (Purpose), Axiom 6 (Channel), Derived Principle 12 (Channel legibility gates autonomy)
**Supersedes:** v14.0 (`Chat | Work | Files | Agents`) and all prior versions — singular implementation, no dual nav models.

---

## Design Thesis

**YARNNN is a cockpit, not a report factory.**

The operator works *inside* YARNNN. Five Purpose-labeled destinations + ambient YARNNN rail. Navigation organizes by operator *why*, not by Substrate.

| Priority | Destination | Route | Purpose (the operator's *why*) | Primary substrate |
|---|---|---|---|---|
| 1 | **Overview** | `/overview` (HOME) | "What's going on? What needs me?" | Temporal + Performance snapshot + Queue + Reviewer alerts |
| 2 | **Team** | `/team` | "Let me check on my agents." | `/agents/*` — roster + identity + supervision |
| 3 | **Work** | `/work` | "Let me check the work." | `/tasks/*` — schedules + status + outputs |
| 4 | **Context** | `/context` | "What does my workspace know?" | `/workspace/context/*` + `/workspace/uploads/*` |
| 5 | **Review** | `/review` | "Who decided what, why?" | `/workspace/review/*` + task `feedback.md` |

**YARNNN (the super-agent) is ambient, not a destination.** A persistent rail is available on every surface; `/chat` is the expanded-focus form of the rail. Chat-as-a-tab dissolves. Operators don't *travel to* YARNNN; YARNNN is *with them*. Surface-aware prompt profiles (ADR-186) flow surface metadata into YARNNN's prompt automatically.

**Team and Work are peer destinations.** Agents and tasks are many-to-many — one agent runs several tasks; one complex task involves several agents. "Check my agents" (identity) and "check the work" (activity) are two distinct operator Purposes, not one. Collapsing them forces awkward sub-modes; separating them respects the two mental models.

**External distribution is derivative.** Email, Slack cross-posts, PDF exports flow from cockpit-approved surfaces via post-compose distribution per ADR-185. Pointer-notifications (push/SMS) deep-link back to cockpit; they do not duplicate interaction affordances.

**`produces_deliverable` outputs a surface, not a document.** The task output folder (`/tasks/{slug}/outputs/`) remains substrate per Axiom 1. What changes is the operator's consumption Channel — the surface IS the deliverable; PDFs and emails are derivatives.

---

## Archetype Patterns (Channel-vocabulary inside destinations)

Each destination composes from one or more **archetype patterns**. The five archetypes are the Channel-dimension vocabulary (Axiom 6) for classifying what a given pane is *doing*. They are not nav entries; they are patterns destinations compose.

| # | Archetype | Substrate read | Purpose | Reading shape |
|---|---|---|---|---|
| 1 | **Document** | A composed output file | Consume a deliverable | One-shot read, rendered HTML or markdown |
| 2 | **Dashboard** | Live state of a Substrate slice | See what the state *is right now* | Continuous; refreshed on visit |
| 3 | **Queue** | Pending addressed-to-operator items | Act on what's awaiting | Actionable entries with approve/reject/defer |
| 4 | **Briefing** | Curated selection + pointers | Receive periodic summary | Periodic push (email) or home read |
| 5 | **Stream** | Append-only log | Audit chronologically | Newest at top, append-only |

### Archetype invariants

Each archetype carries invariants. Violations trigger redesign.

**Document.** Read-only operator-side (edits via YARNNN rail feedback). One document = one Substrate file. Stable URLs (Briefing points *at* Documents).

**Dashboard.** Always live Substrate read (no cached snapshots unless Substrate itself is snapshot-regenerated). No action affordances — a dashboard that sprouts "Approve" buttons becomes a Queue. Grouping/filtering is surface's job; data shape is Substrate's.

**Queue.** Every entry has pending status. Every entry has action affordance. Resolution writes audit entry to a Stream (`decisions.md`, `feedback.md`, activity log).

**Briefing.** Periodic by Trigger (Axiom 4 periodic sub-shape). **Composed by selection, not duplication** — pointers + headlines from other archetypes, not a re-render. This is the explicit rejection of ADR-195 v2 Phase 4 as originally drafted.

**Stream.** Append-only Substrate (no historical-entry mutations). Chronological ordering. Always historical content (projections belong elsewhere).

---

## Design Invariants

Three surface-level rules. These are cockpit discipline; violations trigger redesign.

**I1 — No surface holds state.** Every surface reads files (Axiom 1). Pagination, filtering, sort state live in URL query params or client state, never in server-side session state. The substrate is authoritative.

**I2 — No surface embeds foreign substrate.** Overview links to Team/Work/Review; it does not embed their content. Cross-substrate references are always links, never embeds. This prevents the "briefing absorbs performance" category error (ADR-195 v2 Phase 4 rejected for this reason).

**I3 — Every surface has exactly one primary cognitive consumer.** If two cognitive layers need the same data, they get two views with layer-appropriate framing. The Reviewer's view of `_performance.md` (reasoning substrate, headless) is not the operator's view of `_performance.md` (supervisory dashboard). Same file, two affordances.

---

## Route Map

```
/overview                         Overview (HOME)
  ?since=<iso>                    optional — defaults to last-login

/team                             Team roster
/team/{slug}                      agent detail — identity, tasks owned, health, memory

/work                             Task list (filterable)
/work/{slug}                      task detail — output, schedule, feedback, run log

/context                          Workspace browser
/context/{path}                   domain / entity / file detail

/review                           Reviewer surface
/review/{proposal_id}             decision detail

/chat                             Expanded YARNNN conversation (ambient rail expanded)

/settings                         Account, billing, integrations, system diagnostics
```

All deep-links are stable URLs. The ambient YARNNN rail is available at all routes via the surface shell.

---

## Destination 1 — Overview

**Route:** `/overview` (HOME)
**Purpose:** "What's going on? What needs me?"
**Consumer:** Operator
**Rhythm:** On-login + real-time reactive
**Archetypes composed:** Briefing (since-last-look) + Queue (pending proposals) + Dashboard-snippets (linked, not embedded)

### What it shows

Three panes reading distinct substrates. Panes are **linked, not embedded** (I2 discipline).

1. **Since last look** — temporal changes since previous session
   - Agent runs completed (count + most recent) — deep-link to Work/task-detail
   - Reviewer decisions made (count + recent; human vs AI breakdown) — deep-link to Review
   - External deliveries sent (emails, Slack posts)
   - Platform events reconciled (Alpaca fills, LS orders)

2. **Needs me** — reactive attention
   - Queue: pending `action_proposals` (badge = count; inline ProposalCards for top ~3; "See all N" link)
   - Reviewer alerts: AI Reviewer deferred decisions awaiting human judgment
   - Platform alerts: connection failures, token refresh needed, rate limits hit

3. **Snapshot** — at-a-glance state (Dashboard-snippets)
   - Book headline: total P&L + revenue across domains — links to Context per-domain `_performance.md`
   - Workforce headline: N agents active, M tasks running today — links to Team
   - Context headline: freshest domain + last-accumulated entity — links to Context

### Empty states

- **Day zero:** "Your workforce is here. Connect a platform or describe your work to activate it." + chips for identity setup + platform connect + task creation. Matches ADR-161 heartbeat discipline.
- **No changes since last look:** "Quiet day. Last run was {agent} at {time} — {outcome}." + pointers. Never silent.

### What it does NOT do

- Does not render weekly reports or rich deliverable content (that's Work/task-detail per I2)
- Does not render full `_performance.md` content (linked via Context, not embedded)
- Does not render the Reviewer's full decisions history (that's Review per I2)

Overview is the front door, not the whole house.

---

## Destination 2 — Team

**Route:** `/team`
**Purpose:** "Let me check on my agents."
**Consumer:** Operator (supervising)
**Rhythm:** Steady-state
**Archetypes composed:** Dashboard (roster + health) + Document (agent detail: AGENT.md) + Stream (per-agent run log + reflections)

### What it shows

**Roster.** Agents grouped by class (domain stewards / synthesizer / platform bots / meta-cognitive). Each card shows:
- Display name + domain
- Active task count
- Last run freshness
- Approval rate (when `version_count >= 5`)
- Status indicator (active / paused / archived)

Click → `/team/{slug}`.

### Agent detail

- **Identity card** — AGENT.md rendered, class, domain, tenure
- **Tasks owned** — list with mode + schedule + last run + cross-link to `/work/{slug}`
- **Health** — recent reflection, approval rate, last feedback distillation
- **Memory excerpts** — `memory/reflections.md` (recent) + `memory/directives.md`
- **Actions** — edit identity (via YARNNN rail), pause / resume / archive (direct surface actions)

---

## Destination 3 — Work

**Route:** `/work`
**Purpose:** "Let me check the work."
**Consumer:** Operator (supervising) + Agents (reading task context headlessly)
**Rhythm:** Steady-state (daily check)
**Archetypes composed:** Dashboard (task list) + Document (task detail output) + Stream (run log + feedback)

### What it shows

**Task list.** Filterable by:
- `output_kind` chips (accumulates_context / produces_deliverable / external_action / system_maintenance)
- Agent (cross-link from Team)
- Status (active / paused / completed)
- Schedule (today / this week / stale)

Each row: title + mode badge + next run + last run + owning agent (cross-link to Team).

### Task detail

- **Charter** — TASK.md + DELIVERABLE.md (when `produces_deliverable`)
- **Current output (Document archetype)** — for `produces_deliverable`, renders the latest output surface inline (cockpit-native, not PDF). For `accumulates_context`, entity grid. For `external_action`, last action log. For `system_maintenance`, status report.
- **Schedule** — next run, mode, cadence
- **Run history (Stream archetype)** — last N runs with outcomes
- **Feedback (Stream archetype)** — task `feedback.md` + pending user feedback inline
- **Actions** — edit via YARNNN rail, trigger manually, pause / resume, complete (goal mode)

### Cross-links to Team

Every task detail surfaces its assigned agent(s) prominently with click-through to `/team/{slug}`. Agent detail surfaces that agent's tasks with click-through to `/work/{slug}`. Team and Work are peer destinations with relational navigation.

---

## Destination 4 — Context

**Route:** `/context`
**Purpose:** "What does my workspace know?"
**Consumer:** Operator (exploring) + Agents (reading accumulated context headlessly)
**Rhythm:** On-demand (power users visit daily; casual operators occasionally)
**Archetypes composed:** Dashboard (file browser, domain entity grid, uploads view)

### What it shows

Workspace filesystem browser with three roots:
- `/workspace/context/*` — accumulated domain entities (competitors, customers, trading, revenue, etc.)
- `/workspace/uploads/*` — user-contributed documents
- `/workspace/{IDENTITY,BRAND,notes,style,awareness}.md` — workspace-level identity + preferences

Each domain directory shows:
- Entity grid (per-entity subfolders with tracker metadata)
- Synthesis files (`_`-prefixed cross-entity summaries like `_performance.md`, `_risk.md`, `_tracker.md`)
- Task provenance ("Written by: track-competitors · weekly")

Inferred files render with `<!-- inference-meta: ... -->` source provenance captions per ADR-162.

### What it does NOT do

- No Queue (no operator decisions live here)
- No Briefing (not periodic)
- No direct inline edit forms — edits flow through YARNNN rail per ADR-104 (Agents-as-write-path)

---

## Destination 5 — Review

**Route:** `/review`
**Purpose:** "Who decided what, why? Is the Reviewer calibrated?"
**Consumer:** Operator supervising the Reviewer
**Rhythm:** Rolling; consulted when curious or calibrating
**Archetypes composed:** Dashboard (Reviewer identity + principles) + Stream (decisions log) + Queue-tail (recent resolutions)

### What it shows

**Reviewer identity card** — `/workspace/review/IDENTITY.md` rendered
**Principles** — `/workspace/review/principles.md` rendered; edited via YARNNN rail, not inline form
**Decisions feed (Stream)** — rolling log from `/workspace/review/decisions.md`
  - Each decision: proposal summary, decision (approve / reject / defer), reasoning, reviewer identity tag (`human:` / `ai:` / `impersonated:`)
  - Filter by identity tag / domain / outcome
  - Click → `/review/{proposal_id}` — full detail: proposal inputs, reviewer reasoning, outcome reconciliation when reconciled

### Impersonation visibility

Impersonated workspaces (admin acting as persona) show:
- Top banner: "Impersonating: {persona} — all actions attributed to {admin}-as-{persona}"
- `decisions.md` entries rendered with `impersonated:` tag visibly distinguished

---

## Ambient YARNNN Rail

YARNNN is present on every surface. Not a tab, not a page — an always-reachable affordance.

### Rail shape

- Right-rail collapsible panel (keyboard shortcut to toggle)
- Width: collapsed (icon only, 48px) / expanded (conversation, ~400px)
- State persists per-surface and per-session
- Surface metadata flows automatically into YARNNN's prompt (ADR-186 prompt profiles)

### Three interaction modes

1. **Quick-ask** — operator types a question; YARNNN responds in-rail without breaking surface context
2. **Expand to `/chat`** — for long conversations, exploration, complex tasking; keyboard shortcut or button
3. **Passive context** — rail can surface YARNNN-initiated ambient messages (e.g., "I noticed 3 new signals in trading/ — want to track them?") as subtle notifications

### `/chat` as the expanded form

- Same conversation substrate as the rail (session continuity preserved)
- Full-height surface for focused work
- Accessible from the rail's "expand" action or directly via URL
- Not listed in the primary nav — operators reach it via the rail

### What YARNNN is NOT

- Not a reporting surface (Overview is where state is seen)
- Not a decision surface (Queue on Overview or Review is where decisions land)
- Not a data-editing form (operator edits via YARNNN conversation which routes through primitives per ADR-104)

YARNNN is the conversation with the meta-cognitive agent. Period.

---

## Mode Collapse (schema preserved, surface simplified)

The schema preserves three task modes (`recurring | goal | reactive`) because the execution layer needs the distinction (ADR-149). The cockpit surface shows two labels — **`Recurring`** and **`One-time`** (`goal` and `reactive` both map to "One-time"). The `WorkModeBadge` component is the single place modes are rendered; `taskModeLabel()` in `web/types/index.ts` is the canonical helper. Unchanged from prior versions.

---

## What the Cockpit Replaces

| Old surface (v14) | New destination (v15) | Notes |
|---|---|---|
| `/chat` (primary nav tab) | Ambient YARNNN rail on every surface + `/chat` as expanded form | Chat-as-a-destination dissolves; YARNNN is ambient |
| `/work` (task list + detail) | `/work` — preserved (tasks-as-activity surface) | Route unchanged; scope clarified to tasks only (no agent roster) |
| `/agents` (roster + detail) | `/team` (agents-as-identity surface) | Rename to operator-native vocabulary; NARRATIVE-aligned |
| `/context` (filesystem browser) | `/context` — preserved | Route unchanged; minor scope tightening |
| `/activity` (deleted in v11) | Overview "Since last look" + Team per-agent + Work per-task + Review per-decision | Already deleted in v14; cockpit distributes further |
| `/orchestrator` (deleted in v11) | Overview (the new HOME) | Already deleted in v14 |
| Workspace-state modal (ADR-165) | Overview renders workspace state natively | Modal becomes unnecessary; state is the surface |
| Daily-update "briefing dashboard" on `/chat` | Overview "Since last look" pane | Moved to the destination that owns temporal state |

---

## External Distribution Discipline

External Channels (email, Slack, PDF, Notion write-back) are **derivatives** of cockpit-approved work per ADR-185. Four rules:

1. **Expository pointer pattern for periodic external emails.** Daily-update, weekly reports, campaign briefs emitted to external stakeholders carry *legible summary content* + *deep-link pointers* back to cockpit. Neither pure-pointer (too thin) nor full-replacement (violates singular implementation).

2. **Pointer-only for alerts.** Push notifications, SMS alerts for time-sensitive events deep-link into cockpit Queue or Overview. Approval/rejection happens *in cockpit*, not via SMS reply.

3. **Full content for external audiences.** Weekly report to CFO, Slack digest to #team — these go to consumers who don't have operator identity. Full PDF/HTML content is the right Channel shape. The operator reviewed the surface in cockpit first; the external delivery is post-approval.

4. **No replacement UX.** External Channels never duplicate cockpit's interaction affordances. An "Approve via email" link that takes a destructive action via GET is forbidden. Links always route through cockpit's auth + approval flow.

---

## Implementation Sequence (each phase ships green)

| # | Phase / ADR | Scope |
|---|---|---|
| 1 | **ADR-198 v2 + this doc (SURFACE-ARCHITECTURE v15)** | Canonization. Doc-only. (Current commit cycle.) |
| 2 | **ADR-199 — Overview surface** | `/overview` route. Since-last-look + snapshot + queue + alerts. Absorbs `/chat`-as-home. |
| 3 | **ADR-200 — Review surface** | `/review` route. Reviewer identity + principles + decisions log. Unblocks Principle 12 for Reviewer layer. |
| 4 | **ADR-201 — Team + Work separation + ambient YARNNN rail** | Rename `/agents` → `/team`. Preserve `/work` with tightened scope. Cross-link agent↔task detail. Ambient rail across all surfaces. Deprecate `/chat` as primary nav destination. |
| 5 | **ADR-202 — External Channel discipline** | Daily-update stripped of embedded performance. Alert specs pointer-only. `produces_deliverable` external-distribution as derivative step. |

Each ADR stands alone, each green-on-ship, singular-implementation throughout.

---

## Related Design Docs

| Doc | Relevance under v15 |
|---|---|
| [AGENT-AND-TASK-SURFACE-PATTERNS.md](./AGENT-AND-TASK-SURFACE-PATTERNS.md) | Still canonical for no-task-state patterns + shell rules. Applies inside Team + Work. |
| [FEEDBACK-WORKFLOW-REDESIGN.md](./FEEDBACK-WORKFLOW-REDESIGN.md) | Feedback flows in cockpit surfaces per I1 (substrate-authoritative). |
| [TASK-OUTPUT-SURFACE-CONTRACT.md](./TASK-OUTPUT-SURFACE-CONTRACT.md) | Contract for how `produces_deliverable` outputs compose inside Work task-detail. May need amendment for cockpit surface-primacy. |
| [SURFACE-ACTION-MAPPING.md](./SURFACE-ACTION-MAPPING.md) | Surface → primitive mapping. Updated per-surface in ADRs 199–202. |
| [SURFACE-DISPLAY-MAP.md](./SURFACE-DISPLAY-MAP.md) | Likely needs rewrite under cockpit nav. Scoped to ADR-201. |
| [USER-JOURNEY.md](./USER-JOURNEY.md) | Rewrite to reflect cockpit-primary operator journey. Scoped to standalone v15 edit. |
| [HEADLESS-PROMPT-PROFILES.md](./HEADLESS-PROMPT-PROFILES.md) | Unchanged — prompt profiles align with cockpit surfaces automatically. |

---

## Revision History

| Version | Date | Change |
|---|---|---|
| v15.0 | 2026-04-20 | **Full rewrite to cockpit model.** ADR-198 v2 ratified. Nav model `Chat \| Work \| Files \| Agents` replaced by **Overview / Team / Work / Context / Review** + ambient YARNNN rail. Five operator-native destinations (Team and Work as peer destinations — agents-as-identity vs tasks-as-activity). Five archetype patterns (Document / Dashboard / Queue / Briefing / Stream) compose inside destinations. Three invariants (I1/I2/I3) made explicit. External Channel discipline ratified (expository pointers, pointer-only alerts, no replacement UX). Implementation phased across ADRs 199–202. Singular implementation — v14 removed; no dual nav model preserved. |
| v14.0 | 2026-04-16 | (Superseded) Nav: Chat / Work / Files / Agents; Work task-scoped; Files workspace-scoped. |
| v13.0 and earlier | 2026-04-16 and prior | (Superseded) Various iterations of the four-surface nav; see git history. |
