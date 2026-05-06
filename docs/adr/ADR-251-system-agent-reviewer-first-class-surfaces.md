# ADR-251: System Agent + Reviewer as First-Class Surfaces — Roster Reinstated

> **Status**: Proposed
> **Date**: 2026-05-06
> **Authors**: KVK, Claude
> **Supersedes**: ADR-241 D1 (roster deletion — reversed with justification; see below)
> **Amends**: ADR-241 D2 (YARNNN detail view → System Agent detail view), ADR-247 D1 (YARNNN as system name preserved; "System Agent" is the entity name within the cockpit surface, not the brand), LAYER-MAPPING.md, GLOSSARY.md, FOUNDATIONS.md Axiom 2 Identity table
> **Dimensional classification**: **Identity** (Axiom 2) primary — names the two systemic entities correctly; **Channel** (Axiom 6) secondary — reinstates roster as the canonical entry point for the Agents surface

---

## Context

### The naming problem ADR-241 left open

ADR-241 collapsed the Agents roster and defaulted the surface to `?agent=yarnnn`. The rationale was correct at the time: with no user-authored domain Agents and the Reviewer collapsed under YARNNN, a two-card roster was empty ceremony.

ADR-247 retired "Thinking Partner" as a user-facing name, replacing it with "YARNNN." ADR-249 sharpened the framing: YARNNN is the system — executor and narrator. The Reviewer is the operator's judgment function.

What remained unresolved: the entity the operator addresses through the chat surface has no distinct name as a *cockpit entity*. Calling it "YARNNN" conflates the brand with the entity. The brand is the product. The entity in the cockpit is the **System Agent** — the conversational surface of the orchestration layer.

Similarly: the Reviewer has been either invisible (ADR-241 collapsed it) or mishoused (Principles and Autonomy tabs under the System surface, where they architecturally don't belong). Autonomy is the operator's delegation *to the Reviewer*. Principles is the Reviewer's judgment framework. Both belong to the Reviewer entity, not to the system surface.

### Why "System Agent" and not "YARNNN"

"YARNNN" is the brand and the product. It is not the name of the entity the operator interacts with in the cockpit. The entity is the system — the orchestration surface that executes, routes, and narrates. Calling the entity "YARNNN" creates a naming collision: the operator doesn't know if they're addressing the product or a sub-entity.

"System Agent" is precise: it names what it is (the system's conversational surface), it implies its role (agent of the system, not an independent judgment entity), and it distinguishes it clearly from the Reviewer (the operator's judgment agent).

"Thinking Partner" is retired. That framing described an era of co-reasoning that ended with ADR-231 (mandate-driven invocations) and ADR-249 (executor/narrator posture). The operator does not co-reason with the system; they declare intent and the system executes.

**Brand clarity**: YARNNN remains the product brand everywhere. The System Agent speaks as the YARNNN brand. The entity name "System Agent" is the cockpit label — what the operator sees on the Agents surface. In chat, the system speaks as "YARNNN." There is no contradiction: the brand and the cockpit entity label serve different registers.

### Why the roster returns

ADR-241 deleted the roster because it was empty ceremony: one YARNNN card, one Reviewer card, no domain agents. The ceremony was hollow because the Reviewer was misframed as a roster peer when it was being collapsed under YARNNN's detail view.

Now the Reviewer is first-class. The roster makes sense:

```
┌─ SYSTEM ──────────────────┐  ┌─ REVIEWER ────────────────┐
│ System Agent              │  │ [Operator's persona name] │
│ Executor & Narrator       │  │ Your judgment seat        │
└───────────────────────────┘  └───────────────────────────┘

Your Agents  ── (user-authored domain agents — currently empty)
```

Two structurally distinct entities with different roles, different substrate homes, different development axes. A roster is the right surface.

### Why Autonomy + Principles + heartbeat belong under the Reviewer

**Autonomy** (`AUTONOMY.md`) = the operator's delegation ceiling to the Reviewer seat. It governs what the Reviewer can auto-execute, at what ceiling, under what never-auto constraints. It is the Reviewer's operating mandate, not YARNNN's configuration.

**Principles** (`principles.md`) = the Reviewer's judgment framework. The framework the Reviewer applies when evaluating proposals. Completely Reviewer-owned.

**Heartbeat cadence** = how frequently the Reviewer's back-office reflection runs. This is the Reviewer's operational rhythm, declared in `back-office.yaml` as `back-office-reviewer-reflection` schedule. The operator should see this on the Reviewer's surface and understand it as the Reviewer's cadence, not a system setting.

Currently all three live under the System Agent surface. This is an Identity violation (Axiom 2): content authored *for the Reviewer seat* is housed *under the system surface*. Moving them to the Reviewer surface is the correct Axiom 2 alignment.

**Mandate** moves to the System Agent surface: the Mandate is the operator's declared intent that the system reads and executes against. It is correctly scoped to the system surface — the system reads the mandate, the Reviewer applies principles *within* the mandate's declared scope.

---

## Decisions

### D1: Entity rename — "System Agent" is the cockpit entity name for the orchestration surface

The entity previously called "Thinking Partner" and subsequently referred to as "YARNNN" in the cockpit is renamed **System Agent** as a cockpit label.

**What changes:**
- `display_name` in `SYSTEMIC_AGENTS` registry: `"YARNNN"` → `"System Agent"`
- `shortLabel` in `ROLE_META['thinking_partner']`: `'YARNNN'` → `'System'`
- `displayName` in `ROLE_META['thinking_partner']`: `'YARNNN'` → `'System Agent'`
- URL param: `?agent=yarnnn` → `?agent=system` (with `?agent=yarnnn` as bookmark-safety redirect)
- `THINKING_PARTNER_ROUTE` constant → `SYSTEM_AGENT_ROUTE = '/agents?agent=system'`
- `CLASS_LABELS['meta-cognitive']`: `'YARNNN'` → `'System Agent'`
- Taglines: "Orchestrates your workforce" → "Executes declared work. Narrates what happened."
- All user-facing tab labels, taglines, descriptions referencing "TP" or "Thinking Partner" → "System Agent" or "the system"
- `web/components/tp/` directory: rename to `web/components/system/` — these are the system surface's chat components, not "TP" components

**What does NOT change (DB/data-compat exceptions):**
- `agents.role` DB value: `thinking_partner` — glossary exception, migration 142 constraint, never surfaced outside DB internals
- `agent_class` enum value: `meta-cognitive` — data-compat slug; maps to "System Agent" at the display layer
- `agents.slug` in DB: `thinking-partner` — filesystem path convention for the agent's memory substrate
- All historical ADRs referencing "Thinking Partner" or "YARNNN" as entity name — frozen artifacts, not rewritten
- `api/agents/yarnnn.py` filename and `YarnnnAgent` class name — internal code identifiers, no user visibility
- `TPContext`, `useTP`, `TPProvider` — React context internals; rename deferred (high churn, zero user visibility)
- `authored_by` string prefix `yarnnn:` in revision records — data format, immutable per ADR-209

**Why `meta-cognitive` stays as the internal class enum**: it is a data-compat slug that crosses Python + API response + TS type union + revision record `authored_by` layers. The human-readable concept is "System Agent"; the internal enum is pragmatic. GLOSSARY exception table documents this.

### D2: Roster reinstated — two systemic cards + domain agents section

`/agents` with no query param renders the roster (not a redirect). Roster has three sections:

1. **Systemic** (always two cards, fixed order):
   - System Agent card — label "System Agent", tagline "Executes declared work. Narrates what happened.", links to `?agent=system`
   - Reviewer card — label is the **operator's authored persona name** from `/workspace/review/IDENTITY.md` (first `# ` heading), falling back to "Reviewer" if skeleton. Links to `?agent=reviewer`

2. **Your Agents** (user-authored, zero-to-many):
   - Empty state when none exist: "No agents yet. Ask the System Agent to create one."
   - Cards when exist: existing `AgentCard` shape unchanged

ADR-241's rationale (roster was empty ceremony) is superseded: with Reviewer as first-class and its substrate correctly housed there, the two systemic cards have distinct, meaningful content. The roster is not ceremony — it is the canonical entry point to two different entities.

### D3: System Agent detail (`?agent=system`) — tabs

Tabs: **Identity** · **Mandate** · **Back Office**

- **Identity**: what the System Agent is — its operating contract, orchestration role, how to address it. Replaces current `AgentRoleBlock` content for `meta-cognitive`.
- **Mandate**: `MANDATE.md` — the operator's declared primary intent. The System Agent reads and executes against this. Correct house: the system surfaces the mandate it serves.
- **Back Office**: execution telemetry from `execution_events` — recent runs, cost today vs ceiling, back-office job status (narrative-digest, proposal-cleanup, outcome-reconciliation). Links to `/backend` for full log.

**Removed from System Agent surface**: Autonomy tab and Principles tab. Both migrate to Reviewer.

### D4: Reviewer detail (`?agent=reviewer`) — tabs

Tabs: **Identity** · **Principles** · **Autonomy** · **Track Record** · **Decisions**

- **Identity**: `/workspace/review/IDENTITY.md` — operator's authored persona. Shows persona name, current occupant type (human/AI from `OCCUPANT.md`).
- **Principles**: `/workspace/review/principles.md` — the judgment framework. Moved from System Agent surface. Edit via chat.
- **Autonomy**: `/workspace/context/_shared/AUTONOMY.md` — delegation ceiling + levels + never_auto. **Also shows heartbeat cadence** (read from `back-office.yaml` entries for `back-office-reviewer-reflection` and `back-office-reviewer-calibration` — schedule string + last-run timestamp from `execution_events`). Edit via chat.
- **Track Record**: `/workspace/review/calibration.md` — 7d/30d/90d approval rates, accuracy vs outcomes. Currently no surface; this is the first dedicated surface for the Reviewer's performance data.
- **Decisions**: `/workspace/review/decisions.md` stream — the running verdict log. Currently on `/work` (DecisionsStream component, ADR-241 D3). Migrates back to Reviewer where it architecturally belongs. The `/work` Decisions tab is **deleted** (singular implementation).

`?agent=reviewer` redirect (ADR-241 D3: `reviewer → yarnnn&tab=principles`) is **deleted**. `?agent=reviewer` now renders `ReviewerDetail` directly.

### D5: Autonomy tab — heartbeat cadence section

The Autonomy tab on the Reviewer surface gains a read-only cadence section below the AUTONOMY.md content:

```
Reviewer cadence
  Reflection:   daily 07:00 UTC
  Calibration:  daily 06:00 UTC
  Last run:     2026-05-06 07:02 UTC (verdict: no_change)
  Next run:     2026-05-07 07:00 UTC

  [Edit cadence via chat →]
```

Data source: `GET /api/reviewer/cadence` — new lightweight endpoint that reads `back-office.yaml` for `back-office-reviewer-reflection` and `back-office-reviewer-calibration` schedule strings, and queries `execution_events` for the last successful run of each. Returns `{reflection_schedule, calibration_schedule, last_reflection_at, last_calibration_at, last_reflection_verdict}`.

Edit is chat-routed: clicking "Edit cadence via chat →" opens chat with pre-filled message "I want to change how often my Reviewer reflects — currently daily at 07:00 UTC."

### D6: Deep-link updates

All cross-surface links update to reflect the new URLs:

| Old link | New link | File |
|----------|----------|------|
| `/agents?agent=yarnnn&tab=autonomy` | `/agents?agent=reviewer&tab=autonomy` | `CockpitHeader.tsx` |
| `/agents?agent=reviewer` | `/agents?agent=reviewer` | `PerformanceFace.tsx`, `TrackingFace.tsx` (already correct target, no change) |
| `THINKING_PARTNER_ROUTE` | `SYSTEM_AGENT_ROUTE` | `web/lib/routes.ts` + all consumers |

### D7: Bookmark-safety redirects

- `?agent=yarnnn` → redirect to `?agent=system` (ADR-241 declared `yarnnn` as canonical; old bookmarks must not 404)
- `?agent=thinking-partner` → redirect to `?agent=system` (older bookmarks)
- `?agent=reviewer` → renders `ReviewerDetail` directly (no redirect; this is now the canonical URL)
- `?agent=yarnnn&tab=principles` → redirect to `?agent=reviewer&tab=principles`
- `?agent=yarnnn&tab=autonomy` → redirect to `?agent=reviewer&tab=autonomy`

---

## What This ADR Does NOT Do

- Does not implement Reviewer conversational mode (Mode 3, ADR-249 D7) — scoped to follow-on ADR-252
- Does not add Reviewer-initiated proposals — scoped to follow-on ADR-253
- Does not rename `TPContext`, `useTP`, `TPProvider` React internals — deferred, zero user visibility
- Does not rename `api/agents/yarnnn.py` or `YarnnnAgent` class — internal code, deferred
- Does not change DB schema — `agents.role='thinking_partner'` stays as glossary exception
- Does not change `meta-cognitive` enum value — data-compat, stays
- Does not change `authored_by` prefix `yarnnn:` in revision records — immutable per ADR-209

---

## Implementation Plan

### Commit 1 — Backend: display_name + new `/api/reviewer/cadence` endpoint
- `api/services/orchestration.py`: `display_name: "System Agent"` in `SYSTEMIC_AGENTS`
- `api/routes/agents.py`: Reviewer pseudo-agent `title: "Reviewer"` (already correct)
- New `GET /api/reviewer/cadence` endpoint in `api/routes/agents.py` — reads back-office.yaml + queries `execution_events`
- `api/prompts/CHANGELOG.md` entry

### Commit 2 — Frontend identity + routes
- `web/lib/agent-identity.ts`: `thinking_partner` display → "System Agent", `meta-cognitive` label → "System Agent", taglines updated
- `web/lib/routes.ts`: `THINKING_PARTNER_ROUTE` → `SYSTEM_AGENT_ROUTE = '/agents?agent=system'`; update all consumers
- `web/lib/constants/agents.ts`: `thinking_partner: 'System Agent'`
- `web/types/index.ts`: no enum changes (data-compat)

### Commit 3 — Agents page: roster reinstated + routing
- `web/app/(authenticated)/agents/page.tsx`: roster landing (no redirect when no param), bookmark-safety redirects for `?agent=yarnnn` and `?agent=thinking-partner`
- New `AgentRosterSurface.tsx` — three-section roster (Systemic + Your Agents), `useReviewerPersona()` hook for Reviewer card name
- `web/components/agents/AgentContentView.tsx`: delete `reviewer` → `yarnnn&tab=principles` redirect; `meta-cognitive` → `SystemDetail`

### Commit 4 — System Agent detail view
- `SystemDetail` component (rename/rewrite from `YarnnnDetail`): tabs Identity · Mandate · Back Office
- Remove Autonomy and Principles tabs from System Agent
- `BackOfficeTab` component: reads `/api/reviewer/cadence` + recent execution events

### Commit 5 — Reviewer detail view
- `ReviewerDetail` component: tabs Identity · Principles · Autonomy · Track Record · Decisions
- Migrate `PrinciplesTab` from System Agent → Reviewer (same component, new home)
- Migrate `AutonomyTab` from System Agent → Reviewer + add cadence section calling `/api/reviewer/cadence`
- New `TrackRecordTab`: renders `/workspace/review/calibration.md` via `WorkspaceFileView`
- Migrate `DecisionsStream` from `/work` Decisions tab → Reviewer Decisions tab; delete `/work` Decisions tab

### Commit 6 — Deep-links + tagline cleanup
- `CockpitHeader.tsx`: `AUTONOMY_EDIT_HREF` → `/agents?agent=reviewer&tab=autonomy`
- `AutonomyTab.tsx` tagline: remove "TP" → "the Reviewer"
- `PrinciplesTab.tsx` tagline: remove "TP" → "the Reviewer"
- `AgentAvatar.tsx`: "TP Avatar — The Orchestrator" → "System Agent avatar"
- `WorkspaceTree.tsx`: `yarnnn:` authored_by label `'TP'` → `'System'`
- `IsometricRoom.tsx` comments: `TP` → `System Agent`

### Commit 7 — Doc sync + test gate
- Update `GLOSSARY.md`: System Agent entry, retire `meta-cognitive` as user-facing, retire TP/Thinking Partner
- Update `LAYER-MAPPING.md`: System Agent in entity table
- Update `FOUNDATIONS.md` Axiom 2 Identity table
- Update `CLAUDE.md` ADR index entry for ADR-251
- Test gate: `api/test_adr251_system_reviewer_surfaces.py`

---

## Test Gate

`api/test_adr251_system_reviewer_surfaces.py`:

1. `SYSTEMIC_AGENTS['thinking_partner']['display_name']` == "System Agent" in `orchestration.py`
2. No user-facing "Thinking Partner" or "YARNNN" (as agent entity label) in `web/components/agents/` display strings
3. No user-facing "TP" as label in `web/components/agents/` or `web/components/tp/` display strings
4. `SYSTEM_AGENT_ROUTE` constant exists in `web/lib/routes.ts`, value contains `agent=system`
5. `THINKING_PARTNER_ROUTE` constant deleted from `web/lib/routes.ts`
6. `?agent=reviewer` renders `ReviewerDetail` — no redirect to `yarnnn`
7. `GET /api/reviewer/cadence` endpoint exists and returns `reflection_schedule`, `calibration_schedule`
8. `DecisionsStream` does not appear in `web/components/work/` (migrated to Reviewer)
9. `CockpitHeader.tsx` autonomy link points to `?agent=reviewer&tab=autonomy` not `?agent=yarnnn`
10. `GLOSSARY.md` contains "System Agent" entry; does not list TP as a current term

---

## Relationship to Existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-241 | D1 (roster deletion) superseded — roster reinstated with justification. D2 (YARNNN detail as tab-based) amended — renamed to System Agent, tabs restructured. D3 (Decisions on /work) reversed — Decisions migrates to Reviewer. |
| ADR-247 | D1 (YARNNN as system name) preserved — YARNNN is the brand and the chat voice; "System Agent" is the cockpit entity label. No contradiction. D2 (Reviewer persona name in verdicts) preserved and extended to roster card. |
| ADR-249 | D2 (YARNNN as executor/narrator) preserved and expressed in the System Agent detail Identity tab. D7 (Reviewer Mode 3) out of scope — follow-on ADR-252. |
| ADR-248 | D5 (YARNNN pause-awareness in compact index) preserved. Heartbeat cadence surface (D1/D2 schedule YAML) now surfaced in Reviewer Autonomy tab via `/api/reviewer/cadence`. |
| ADR-194 v2 | Reviewer substrate (`/workspace/review/`) unchanged. Autonomy + Principles now correctly housed under Reviewer surface instead of System Agent surface. |
| ADR-217 | `AUTONOMY.md` path unchanged. Now correctly surfaced under Reviewer, not System Agent. |

---

## Revision history

| Date | Change |
|------|--------|
| 2026-05-06 | v1 — Initial draft. Roster reinstated, System Agent named, Reviewer first-class, Autonomy+Principles migrated to Reviewer, heartbeat cadence surfaced. |
