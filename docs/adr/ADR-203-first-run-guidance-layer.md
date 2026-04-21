# ADR-203: First-Run Guidance Layer — Overview as the Cold-Start Surface

> **Status**: Proposed (Phase 1 implementation shipping in same commit cycle)
> **Date**: 2026-04-21
> **Authors**: KVK, Claude
> **Extends**: ADR-198 v2 (cockpit service model), ADR-199 (Overview surface), ADR-189 (signup scaffolding), ADR-165 v7 (WorkspaceStateView modal — pre-cockpit onboarding surface)
> **Supersedes** (in part): the cold-start portions of `docs/design/ONBOARDING-TP-AWARENESS.md` v4 — specifically, the `/chat` landing + TP-marker-opens-modal flow. The modal itself (WorkspaceStateView) stays for re-entry scenarios; the *cold-start entry point* moves to Overview.
> **Triggered by**: Alpha-1 observation `2026-04-21-alpha-trader-cockpit-first-run-semantically-empty.md` — first real signal from the alpha, surfaced on Day 1 of operational use.

---

## Context

ADR-199 moved `HOME_ROUTE` from `/chat` to `/overview`. The cockpit nav + ambient rail shipped cleanly. But one structural piece was left behind in the transition: **the first-run guidance flow.**

Pre-cockpit (per `ONBOARDING-TP-AWARENESS.md` v4): cold-start users landed on `/chat`; the first TP turn emitted a `<!-- workspace-state: {"lead":"context"} -->` marker; the frontend opened `WorkspaceStateView` with `ContextSetup` soft-gated; the user described their work; TP scaffolded identity + domains + tasks.

Post-cockpit: cold-start users land on `/overview`. The marker-based onboarding never fires because nobody is on `/chat` at cold-start. Overview has an `OverviewEmptyState` component, but it only activates when the workspace is **structurally empty** (zero agents, zero active tasks, zero proposals). Post-ADR-189, every YARNNN signup scaffolds 12 agents (YARNNN + 6 Specialists + 5 Platform Bots + various roles) + 5 essential back-office tasks. No signup is structurally empty. Therefore `OverviewEmptyState` never activates. Therefore cold-start users land on a cockpit that reports "Nothing needs you right now · 5 tasks active across 0 agents · Book — · Context: Competitors."

This is what the triggering observation surfaced. It reads as contradictory to any operator who doesn't know YARNNN's internals.

### The two-layer problem this ADR resolves

**Layer 1 — detection:** "Is this workspace semantically empty (operator hasn't done anything yet) even though it's structurally scaffolded?" Today: not detected. The empty-state threshold is structural-only.

**Layer 2 — guidance:** "Once detected as semantically empty, what does the surface *do* to guide the operator?" Today: two CTA buttons leading nowhere structured (Describe / Connect). No YARNNN conversation, no first-move clarity.

### Axiomatic grounding

Per FOUNDATIONS v6.0:

- **Axiom 2 (Identity)** — "operator" is a distinct cognitive consumer. Surfaces must speak to them, not to the engineer-reader.
- **Axiom 3 (Purpose)** — surfaces answer the operator's *why*, not the substrate's *what*. "Nothing needs you right now" is substrate-vocabulary; "Your workforce is waiting — tell me what you want to track" is operator-vocabulary.
- **Axiom 6 (Channel)** — the cockpit is the operator's primary Channel. If it doesn't greet the operator at first-run, it has failed Channel legibility.
- **Derived Principle 12** — *Channel legibility gates autonomy*. An operator who can't read the cockpit on Day 1 cannot trust it to run autonomously on Day 30.

### Why this is an ADR, not a component patch

Three separate surfaces (`OverviewSurface`, `SnapshotPane`, `OverviewEmptyState`), one shared vocabulary source (YARNNN prompts), one shared detection threshold (`detectDayZero`), one shared mental model (cockpit as cold-start surface) — the fix spans all of them coherently. Patching one in isolation would leave the others drifted. The ADR names the pattern and commits the vocabulary.

---

## Decision

### 1. Semantic day-zero detection (replaces structural threshold)

Current `OverviewSurface.detectDayZero()` returns true only when `!hasAgents && !hasActiveTasks && !hasPendingProposals`. Replaced by:

```python
# (semantically empty — operator hasn't acted yet, regardless of scaffold state)
is_semantic_day_zero =
  (no operator-authored agents — all existing agents are origin=system_bootstrap)
  AND (no non-essential tasks — only back-office + daily-update are active)
  AND (no pending proposals)
  AND (no tracking or context-writing that wasn't pre-scaffolded — _performance.md absent or empty frontmatter)
```

Structural empty remains as a separate pre-semantic state (*"workspace has nothing at all"* — e.g., failed signup mid-scaffold). Handled separately or considered broken state; not the common case.

Implementation: `OverviewSurface.detectSemanticDayZero()`. Reads via existing `api.agents.list()`, `api.tasks.list()`, `api.proposals.list()`. Adds origin filtering on agents (`origin !== 'system_bootstrap'`) and essential filtering on tasks (`!essential`).

### 2. Overview is the cold-start landing surface

Auth callback redirects new users to `HOME_ROUTE = /overview` (unchanged — already ADR-199). When `/overview` detects semantic day-zero, it renders the first-run guidance instead of the three-pane `NEEDS ME / SINCE LAST LOOK / SNAPSHOT` layout.

This supersedes `ONBOARDING-TP-AWARENESS.md` v4's `/chat`-based cold-start flow. The `WorkspaceStateView` modal remains for *re-entry* (post-onboarding "add more context" case), accessed from the surface-header toggle on any cockpit destination. It is no longer the cold-start entry point.

### 3. Ambient YARNNN rail opens by default on cold-start

ADR-199 set `defaultOpen: false` for the ambient rail on `/overview`. For cold-start (semantic day-zero), override to `defaultOpen: true` with a pre-seeded first-session prompt.

The seeded prompt is NOT auto-sent. It appears in the composer as a draftSeed so the operator sees what will be asked and can edit or submit. This respects operator agency — YARNNN introduces itself, invites the operator to describe their work, but the operator remains the first-mover.

### 4. Operator-vocabulary content discipline on Overview

Four surface-content changes specifically for semantic-day-zero state:

#### 4a. Rewrite OverviewEmptyState to teach, not list CTAs

Current: two buttons ("Describe my work" / "Connect a platform") + one-line tagline.

New: structured introduction to the cockpit from YARNNN's perspective. Four short sections:

1. **"Welcome — here's what's here."** One sentence about what the cockpit is (*"This is your workforce control surface. Your agents live here; you supervise them from here."*)
2. **"What's already scaffolded."** Honest naming of what the operator has *without having done anything yet* (*"12 agents are waiting for you: YARNNN (your meta-cognitive partner), six Specialists (Researcher, Analyst, Writer, Tracker, Designer, Reporting), and five platform bots ready to activate when you connect Slack, Notion, GitHub, Alpaca, or Lemon Squeezy."*)
3. **"What's missing."** What the operator needs to provide (*"You haven't described your work yet, so we haven't authored any domain-specific agents. Tell YARNNN what you want to track, produce, or monitor in the rail on the right."*)
4. **"Three concrete first moves."** Three cards — each one a click that seeds the rail with a purpose-specific prompt, not a generic CTA. Cards: *Tell YARNNN about your work* / *Connect a platform first* / *Walk me through the cockpit*.

#### 4b. Snapshot tile copy for semantic-day-zero

When day-zero is true, Snapshot tiles render teaching copy instead of empty values:

- Book tile: *"No trades yet. Fires when you approve your first signal trigger."* (trader persona) or *"No revenue yet. Fires when your first connected platform records a sale."* (commerce persona)
- Workforce tile: *"YARNNN + 6 Specialists ready. Authored agents appear here as you create them."*
- Context tile: *"No context yet. YARNNN creates context domains as you describe your work."*

This requires Snapshot to know the persona kind. Initial implementation: read from `platform_connections` (if trading → trader copy; if commerce → commerce copy; if neither/both → neutral copy).

#### 4c. Scaffolded-file render banner

File viewer in Context surface (when rendering a file with the `Directory scaffold: <name>` metadata tag) shows a persistent info-banner at the top of the file content:

> **This file is maintained by the `{task-or-agent-that-populates-it}` task.** It'll populate after your first reconciliation cycle. You don't need to edit this file — agents fill it based on your connected platforms and declared rules.

Requires a mapping from scaffold-origin to populating-task. For Alpha-1 personas:

- `portfolio/summary.md` → populated by `portfolio-summary` task (not yet wired; write "Will populate after your first Alpaca reconciliation" as placeholder)
- `trading/{ticker}.md` → populated by `track-universe` task
- `revenue/summary.md` → populated by commerce reconciler
- *Generic fallback:* *"Maintained by YARNNN. Will populate as your agents run."*

#### 4d. System-task exclusion from operator-visible counts

"5 active tasks across 0 agents" counts back-office tasks + daily-update. On Overview (and anywhere summarizing workforce activity for the operator), exclude `essential=true` tasks + `origin=system_bootstrap` agents from the visible counts. Internal counts (for verify.py, system telemetry, admin views) remain unfiltered.

Net effect: on cold-start, Overview says "0 active tasks — YARNNN is on standby" rather than "5 active tasks across 0 agents."

### 5. YARNNN onboarding prompt extended for cockpit-first-run

`api/agents/yarnnn_prompts/onboarding.py` currently guides TP's marker emissions for the `/chat`-modal flow. Extended to include a cockpit-first-run branch:

*When the first user message of a session arrives AND `workspace_state.identity == "empty"` AND the current surface is `/overview`:*

- Do not emit a modal marker (modal is not the cold-start surface anymore)
- Greet warmly, name what's scaffolded, name what's missing, offer three concrete first moves (mirroring the OverviewEmptyState content)
- Offer to either (a) take a voice-description of the user's work, (b) walk through the cockpit surface by surface, or (c) begin with a platform connection
- The text YARNNN emits should harmonize with what OverviewEmptyState rendered so the operator isn't reading two disjoint greetings

Prompt-profile-awareness (ADR-186) already flows the current surface to YARNNN's prompt. The cockpit-first-run branch triggers when surface=`/overview` AND `workspace_state.identity == "empty"` AND no prior session turn exists.

The existing marker flow for `/chat` re-entry + re-engagement scenarios is preserved — this is additive, not a replacement for the modal-based re-entry path.

---

## Implementation plan (Phase 1 — this commit cycle)

Frontend-only. No backend changes, no new API endpoints.

### Files to modify

- `web/components/overview/OverviewSurface.tsx`
  - Rename `detectDayZero()` → `detectSemanticDayZero()` with new threshold (filter `origin=system_bootstrap` agents, filter `essential=true` tasks)
  - Rail `defaultOpen` becomes dynamic: `true` when semantic day-zero, `false` otherwise
  - Seeded draft on first-run: *"I just signed up — help me understand what YARNNN is and what I should do first."*

- `web/components/overview/OverviewEmptyState.tsx` — full rewrite per §4a. Four-section structured introduction with three concrete first-move cards.

- `web/components/overview/SnapshotPane.tsx` — tile copy branches on day-zero state + persona kind (read `platform_connections` via existing endpoints to detect trader/commerce).

- `web/app/(authenticated)/overview/page.tsx` — pass semantic-day-zero signal down to ThreePanelLayout's `defaultOpen` + draftSeed config so the rail opens pre-seeded on cold-start.

### Files to touch (lighter)

- `web/components/overview/OverviewSurface.tsx` — `NeedsMePane` + `SinceLastLookPane` suppress their own empty-state copy when semantic day-zero is true (OverviewEmptyState owns the space instead). Already the shape for structural day-zero; extend to semantic.

- `api/agents/yarnnn_prompts/onboarding.py` — prompt extension per §5. CHANGELOG entry.

### Files NOT touched this phase (future Phase 2)

- Scaffolded-file render banner (§4c) — touches file-viewer component, broader scope. Backlog as component-patch follow-up. Logs as observation-cluster candidate.
- `WorkspaceStateView` re-entry flow — unchanged. Modal still exists for operators who want to revisit context capture post-onboarding.
- Auth callback logic — unchanged. HOME_ROUTE already `/overview`.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Notes |
|---|---|---|
| **Day trader (alpha-trader)** | **Helps directly** | First-run UX is the triggering observation. Operator lands on Overview and gets a legible greeting from YARNNN + three concrete moves instead of contradictory emptiness. |
| **E-commerce (alpha-commerce)** | **Helps directly** | Same pattern; persona-appropriate tile copy (revenue-framed instead of P&L-framed). |
| **AI influencer** (scheduled) | Forward-helps | Surface vocabulary discipline generalizes. Persona-specific tile copy is the extension point. |
| **International trader** (scheduled) | Forward-helps | Same structural pattern. |

No domain hurt. No verticalization (pattern is agnostic; persona-specificity lives in the copy branches, driven by `platform_connections` data). Anti-verticalization gate passes.

---

## What this supersedes vs preserves

### Supersedes

- **`docs/design/ONBOARDING-TP-AWARENESS.md` v4 cold-start flow.** Cold-start entry point moves from `/chat`-modal to `/overview`-rail. Doc will update to v5 in the same commit.
- **`OverviewSurface.detectDayZero()` structural threshold.** Replaced by `detectSemanticDayZero()` with origin/essential filtering.

### Preserves

- **`WorkspaceStateView` modal.** Still the right surface for re-entry ("add more context" on Day N).
- **`ContextSetup` component.** Still the identity-capture input surface inside the modal for re-entry flows.
- **Marker pattern (`<!-- workspace-state: {"lead":"..."} -->`).** Still used by TP to open the modal on `/chat` for steady-state users who want to revisit workspace state.
- **Auth callback → `HOME_ROUTE` redirect.** Already `/overview` post-ADR-199.
- **Ambient rail infrastructure.** `ThreePanelLayout` unchanged. Only the `defaultOpen` config at `/overview` changes.

---

## Open questions (resolvable during Phase 1 implementation)

1. **Semantic day-zero edge cases.** What about a user who authored one agent then never came back for two weeks? Is that "day-zero" or "inactive"? Leaning: day-zero only fires when *no* non-scaffolded activity ever. Once an operator has authored anything, day-zero is permanently past for that workspace.
2. **Persona detection beyond trading/commerce.** When alpha-influencer + alpha-intl-trader come online in future phases, tile copy branches grow. Acceptable for now; revisit at Alpha-1.5.
3. **Rail-draft sent vs. not sent.** Seeded prompt lives in composer; user edits or submits. Does YARNNN *also* emit a proactive greeting on first turn? Leaning: YES — the cockpit-first-run prompt branch (§5) has YARNNN speak first in response to surface context, before the user submits anything. The seeded draft is the *user's* ready response.
4. **Tile copy persona-detection timing.** First-session before any platform connects: no persona signal. Default to neutral "describe your work" copy; persona-specific copy kicks in once one platform_connection exists.

---

## What this unblocks

- **Alpha-1 operator onboarding friction eliminated** for KVK + future alpha friends. First real ICP signal becomes unblocked.
- **Observation note `2026-04-21-alpha-trader-cockpit-first-run-semantically-empty.md`** transitions from "open friction" to "resolved by ADR-203 Phase 1."
- **ONBOARDING-TP-AWARENESS.md** can advance to v5 with the cockpit-aligned cold-start model documented canonically.
- **B-product first week signal** (empty or thin) gets captured in a cockpit that actually greets the operator rather than confuses them.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-21 | v1 — Initial proposal. Semantic-day-zero detection + Overview as cold-start surface + ambient rail default-open + operator-vocabulary tile copy + YARNNN cockpit-first-run prompt. Triggered by the first Alpha-1 observation. Phase 1 implementation shipping in same commit cycle. |
