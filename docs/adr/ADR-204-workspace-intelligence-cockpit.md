# ADR-204: Workspace Intelligence Cockpit — Overview as Synthesis Surface

> **Status**: Phase 1 Implemented (2026-04-22)
> **Date**: 2026-04-21
> **Authors**: KVK, Claude
> **Extends**: ADR-199 (Overview surface), ADR-198 v2 (cockpit service model), ADR-203 (first-run guidance layer)
> **Draws from**: ADR-141 (task pipeline), ADR-149 (task lifecycle), ADR-161 (deterministic empty-state), ADR-164 (back-office tasks), ADR-166 (output_kind registry), ADR-177 (section-kind rendering), ADR-182 (pre-gather optimization), ADR-195 v2 (outcome substrate), ADR-202 (external channel discipline)
> **Depends on**: ADR-195 Phases 1–3 (Implemented — `_performance_summary.md` written by outcome reconciliation)

---

## Context

ADR-199 established Overview's three-pane cockpit: **NeedsMe** (Queue), **SinceLastLook** (Briefing), **Snapshot** (Dashboard-snippet tiles). These three panes answer operator-present questions: "what needs my decision?", "what changed since I was last here?", "what's the headline state?"

What none of them answer: **"what does this workspace know, and what does that mean for my work?"**

The workspace accumulates intelligence across runs — domain synthesis files, entity trackers, outcome ledgers, agent performance signals. Today this accumulated intelligence is invisible on Overview. The three panes surface ephemeral state (proposals, recent runs, snapshot headlines); they do not synthesize the persistent knowledge substrate.

The operator's framing: Overview should act as a **BI/Palantir-like intelligence cockpit** — a workspace-unique synthesis of the context filesystem that is domain-agnostic (works regardless of what domains the workspace has accumulated), task-agnostic (not a task list), and evolves as the workspace matures. Critically: no two operators' cockpits should look alike, because no two workspaces accumulate the same knowledge mix.

### Why this requires a task, not a reactive query

The synthesis is non-trivial — it requires reading multiple domain synthesis files, aggregating outcome data, and composing a coherent narrative across them. Doing it reactively on every Overview page load would:
1. Block rendering on LLM latency (300–2000ms)
2. Cost tokens on every visit (at scale: unsustainable)
3. Produce inconsistent output for the same underlying state

The right model: a scheduled `maintain-overview` task produces the cockpit artifact once per day and persists it. Overview reads the cached artifact.

### How this fits the existing architecture

The `produces_deliverable` task pattern (ADR-141, ADR-149) already provides everything needed:
- Task owns `/tasks/{slug}/` directory with TASK.md, DELIVERABLE.md, outputs
- Pipeline composes HTML artifact via render service + writes rich `sys_manifest.json` with section metadata
- Frontend reads artifact via existing `/api/tasks/{slug}/latest-output` endpoint
- `DeliverableMiddle` renders iframe + `SectionProvenanceStrip` from manifest sections

`maintain-overview` is not new infrastructure. It is a new task using the existing pipeline.

---

## Decision

### 1. Overview gains a fourth pane: Workspace Intelligence Card

The existing three panes (NeedsMe, SinceLastLook, Snapshot) are preserved unchanged. A fourth pane — **Intelligence Card** — is added below Snapshot.

The Intelligence Card renders the `maintain-overview` task's latest output artifact: iframe of `output.html` + `SectionProvenanceStrip` from `sys_manifest.json` section metadata. Same primitives as `DeliverableMiddle` on the Work surface.

**Demarcation between panes — explicit and load-bearing:**

| Pane | Temporal frame | Data source | Question answered |
|------|--------------|-------------|-------------------|
| NeedsMe | Present (ephemeral) | `action_proposals` table | What needs my decision right now? |
| SinceLastLook | Session-relative | `agent_runs`, `decisions.md` tail | What happened since I was last here? |
| Snapshot | Present state | `_performance_summary.md`, counts | What's the headline state? |
| **Intelligence Card** | **Persistent / trending** | **`maintain-overview` task output** | **What does this workspace know, and what does that mean?** |

SinceLastLook is session-relative ("since your last visit") and surfaces agent runs + reviewer decisions. The Intelligence Card is substrate-relative ("what has accumulated over time") and surfaces domain knowledge depth, entity coverage, outcome trends, and cross-domain synthesis. No data overlap. Temporal frames are orthogonal, not competing.

### 2. `maintain-overview` task: `output_kind: produces_deliverable`, Reporting agent

A new task is seeded at workspace creation with the following properties:

```
slug:         maintain-overview
type_key:     maintain-overview
output_kind:  produces_deliverable
mode:         recurring
schedule:     daily at 06:00 local (see §6 on scheduling offset)
essential:    true
delivery:     none  (internal artifact, not email-delivered)
agent:        reporting  (the synthesizer role — cross-domain composition)
```

**Why `produces_deliverable` and not `system_maintenance`:**
The backend distinction is meaningful. `system_maintenance` tasks take the TP executor path: no LLM call, no `agent_runs` row, no HTML compose pipeline, no rich `sys_manifest.json` with sections array. `produces_deliverable` takes the full generation path: LLM call, compose pipeline, `output.html`, rich `sys_manifest.json`. The cockpit artifact needs `output.html` (iframe) and `sys_manifest.json` (SectionProvenanceStrip). Therefore `produces_deliverable` is the correct classification.

The four existing back-office tasks (`agent-hygiene`, `workspace-cleanup`, `proposal-cleanup`, `outcome-reconciliation`) remain `system_maintenance`. They are deterministic operational mutations — the correct type for zero-LLM Python executors.

**Why Reporting agent (not TP executor, not a custom Haiku executor):**
The Reporting agent (`role=reporting`) is the cross-domain synthesizer in the workspace roster. Its identity — accumulated context, AGENT.md instructions, memory of prior synthesis work — is precisely what a cockpit intelligence task should draw on. Using the standard `produces_deliverable` generation path means:
- The Reporting agent's workspace (`/agents/reporting/`) provides identity context and accumulated synthesis heuristics
- `agent_runs` history is created — the cockpit task's execution history is visible on the Work surface under the Reporting agent
- The pre-gather phase (ADR-182) pre-loads domain synthesis files and outcome data before the generation call, reducing tool loop overhead
- No custom executor module required — the task type's step instructions guide the Reporting agent's behavior

The balance check and `agent_runs` row creation (which Model A / TP executor avoided) are acceptable here: maintain-overview is a substantive synthesis task, not a deterministic housekeeping function. Its costs belong on the operator's balance, and its run history provides audit trail.

See §Alternatives for Model A (TP executor + Haiku) as the prepared cost-fallback with explicit revert criteria.

### 3. DELIVERABLE.md: composition intent + agnostic section catalog

**Design shift from fixed-sections to catalog-driven composition:**

Most `produces_deliverable` tasks declare a fixed `page_structure` (e.g., `daily-update` always has "Top Priority / What Happened / What Changed / What's Next"). Fixed sections work when the output format is standardized and the workspace shape doesn't affect the template.

`maintain-overview` is different: its output must reflect what *this workspace specifically knows*. A trader's cockpit should surface portfolio health and P&L trends. A content operator's cockpit should surface topic coverage and publishing cadence. A general-purpose workspace with three research domains should surface domain depth and entity freshness. Pre-declaring four fixed sections would produce the wrong output for most workspaces — empty `metric-cards` for operators with no outcomes, empty `status-matrix` for day-zero workspaces, identical shell for structurally different workspaces.

**The catalog approach:** DELIVERABLE.md declares a **superset catalog** of (title, section-kind) pairs — the full library of sections a cockpit might need. The generating agent reads the catalog, assesses the current workspace substrate, and emits the **subset** that is grounded in actual accumulated data. Unproduced sections are absent from the output; they do not appear as empty shells.

**Pipeline compatibility (verified against source):**

- `parse_draft_into_sections()` (assembly.py:528): Non-closed parser. LLM-emitted sections matching catalog titles get the declared kind. LLM-emitted sections *not* in the catalog get `kind="narrative"` by default (graceful fallback). Declared-but-not-produced sections get empty content (suppressed by the empty-section suppression rule). No allow-list enforcement.
- `_render_section_to_html()` (render/compose.py:1399): Unknown kinds fall through to markdown fallback with `data-kind="{kind}"` attribute. Open renderer.
- `KIND_LABELS` (DeliverableMiddle.tsx:60): `KIND_LABELS[section.kind] ?? section.kind` — unknown kinds display as raw kind string. Open map, graceful UI degradation.

The pipeline requires `page_structure` to be non-empty to parse sections at all (`if not page_structure: return {}`). The catalog satisfies this — it is the `page_structure`. The agent produces a subset; the parser finds the matching entries; the render service dispatches on kind.

**DELIVERABLE.md scaffold (written at task creation, updated by inference over time):**

```markdown
## Composition Intent

You are composing the Workspace Intelligence Cockpit — a daily synthesis of this workspace's
accumulated knowledge, presented as an intelligence surface for the operator.

Your output must reflect what THIS workspace actually knows. Do not produce sections for which
you have no grounded data. Every section you emit must be rooted in actual accumulated context
(domain files, entity trackers, outcome data, agent performance). An absent section is honest.
An empty section is noise.

## Available Section Catalog

Choose the subset appropriate to this workspace's current state. Use these exact titles
so the compose pipeline can assign the correct render kind.

| Title | kind | Emit when |
|-------|------|-----------|
| Workspace Synthesis | narrative | Always — 2–3 sentences on overall state |
| Outcome Performance | metric-cards | Commerce or trading platform connected + outcomes recorded |
| Domain Health | status-matrix | ≥2 context domains with entities in `_tracker.md` |
| Workforce State | metric-cards | ≥1 flagged agent OR ≥1 stale task (2× cadence overdue) |
| Key Entities | entity-grid | One domain dominates (≥5 entities) and warrants surfacing |
| Signals & Trends | timeline | Structural changes: new domain, entity additions, coverage shifts |
| Recommended Actions | checklist | Clear operator-actionable next steps emerge from synthesis |

Maximum 5 sections total (including Workspace Synthesis). Fewer is better if data doesn't
support more. Quality contract: every data claim must be derivable from the files you read.

## Archetype Framing Hints

**Trading workspace** (portfolio/ or trading/ domain active):
  Lead with Outcome Performance. Frame Workspace Synthesis around risk/opportunity.
  Workforce State secondary. Domain Health for instrument coverage depth.

**Commerce workspace** (customers/ or revenue/ domain active):
  Lead with Outcome Performance. Frame Workspace Synthesis around growth/churn.
  Key Entities for top products or customers if ≥5.

**Content workspace** (content_research/ or signals/ domain active):
  Lead with Domain Health. Signals & Trends for publishing cadence.
  Frame Workspace Synthesis around knowledge gaps and content opportunities.

**Multi-domain workspace** (3+ active domains, no clear vertical):
  Lead with Domain Health. Workspace Synthesis frames knowledge breadth and depth.
  Recommended Actions if clear gaps emerge across domains.

**Nascent workspace** (day-zero or near-zero entity accumulation):
  Workspace Synthesis only. Honest: "Your workspace is warming up —
  synthesis will deepen as your agents run." No empty structural sections.

## Section Suppression

Do not emit a section if the supporting data is absent or trivial.
The cockpit should be honest about what the workspace knows, not optimistic about what it will know.
```

**Catalog evolution:** DELIVERABLE.md evolves via `infer_task_deliverable_preferences()` (ADR-149, ADR-178) — after sufficient runs, the inference engine distills recurring patterns from the run history into operator-confirmed preferences. A trader workspace whose cockpit consistently leads with Outcome Performance will have that preference distilled into DELIVERABLE.md, narrowing the agent's decision space over time. The catalog shrinks as the workspace matures; cold-start uses the full catalog.

### 4. Archetype classification — no new system

Archetype detection is read from the existing `workspace_state` dict (`working_memory.py`), extended with two new fields:

```python
workspace_state = {
    # ... existing fields (tasks_active, agents_flagged, balance_usd, ...) ...
    "domain_entity_counts": {"competitors": 7, "portfolio": 12},  # NEW — per active domain
    "outcome_connected": True,   # NEW — any commerce/trading platform connected
}
```

These two fields give the Reporting agent sufficient signal to apply archetype framing hints from the catalog. No classification function. No DB column. No persisted archetype label. The agent reads workspace state at generation time and makes its own judgment — which is exactly what a synthesis agent should do.

### 5. Scheduling: daily offset after outcome-reconciliation

`maintain-overview` runs at **06:00 local** daily. `back-office-outcome-reconciliation` runs at **02:00 local**. The 4-hour offset ensures `_performance_summary.md` is current before the cockpit reads it.

This is a scheduling offset, not a dependency graph. The current scheduler (`unified_scheduler.py`) dispatches tasks by `next_run_at <= now`. A per-task daily time can be achieved via cron expression in the task's `schedule` field (e.g., `"0 6 * * *"` with user timezone applied). The existing `calculate_next_pulse_from_schedule()` supports cron expressions via `croniter`.

**Scheduler infrastructure: already supports cron strings (verified).** `calculate_next_run_at()` in `schedule_utils.py` detects cron expressions via `_looks_like_cron()` (any 5–7 whitespace-separated parts) and routes to the croniter-backed calculator with timezone awareness. `"0 6 * * *"` passes through correctly.

**Implementation note:** `_create_essential_back_office_task()` hardcodes `schedule: "daily"` in both the DB insert and the `calculate_next_run_at()` call — it is not parameterized. `maintain-overview` also writes DELIVERABLE.md (like `_create_essential_daily_update()`), uses a non-TP agent, and requires a custom cron schedule. Phase 5c should add a new `_create_essential_deliverable_task(client, user_id, type_key, slug, title, schedule, agent_slugs, user_timezone)` helper that accepts a schedule string and delegates to `calculate_next_run_at(schedule, ...)`. No scheduler changes are needed.

### 6. Seeding at workspace creation — Phase 5c

`workspace_init.py` Phase 5 currently scaffolds `daily-update` (Phase 5a) + four back-office tasks (Phase 5b). `maintain-overview` is added as **Phase 5c**:

```python
# Phase 5c — workspace intelligence task
await _create_essential_task(
    client, user_id,
    type_key="maintain-overview",
    slug="maintain-overview",
    title="Workspace Intelligence",
    schedule="0 6 * * *",   # 06:00 local via cron, timezone applied at runtime
    essential=True,
    delivery="none",
    agent_slug="reporting",
)
```

`essential=True` — the Intelligence Card on Overview is a core cockpit surface. Archiving maintain-overview would break the cockpit. Same reasoning as `daily-update`. The `essential` flag prevents archive + auto-pause.

DELIVERABLE.md is scaffolded at creation time with the catalog above. The catalog is static at scaffold time; archetype hints are applied at generation time by the agent. DELIVERABLE.md evolves via preference inference after sufficient runs (ADR-149).

### 7. Empty-state: day-zero short-circuit

If the workspace is semantically empty at execution time (no accumulated entities across any domain, no outcome data, no flagged agents) — reuse the existing `_is_workspace_empty_for_daily_update()` helper to detect this state. When true:

- Emit a deterministic "warming up" template without an LLM call (analogous to ADR-161 daily-update empty-state branch)
- Template: `## Workspace Synthesis\n\nYour workspace is warming up. Synthesis will deepen as your agents run and accumulate context. Tell YARNNN what you want to track or produce to get started.`
- Write to output folder as usual; Overview renders it as the Intelligence Card with no SectionProvenanceStrip (single section, no provenance needed)

This preserves the ADR-161 principle: essential tasks must produce an artifact on every run, but that artifact may be a deterministic template when there's nothing substantive to synthesize.

### 8. ADR-198 I2 clarification

ADR-198 Invariant I2: **"No surface embeds foreign substrate."**

The Intelligence Card embeds `maintain-overview`'s HTML artifact via iframe. This does not violate I2, with explicit clarification:

I2 was designed to prevent Overview from embedding *peer-surface* substrate — competitor profiles (Context's domain), task output detail (Work's domain), agent memory (Team's domain). Embedding peer-surface substrate collapses surface boundaries.

`maintain-overview` is not peer-surface substrate. It is a purpose-built artifact for Overview's exclusive consumption (`delivery: none`, single consumer). It is Overview's own content, produced by a task whose sole purpose is maintaining the cockpit intelligence pane.

**Amended I2:** *"No surface embeds foreign peer-surface substrate. A surface may render its own purpose-built task-output artifacts, provided the task's `delivery: none` and its sole consumer is that surface."*

### 9. Frontend: reuse existing task-output primitives

No new API endpoints. No new rendering infrastructure. The Intelligence Card reuses:

- **Data fetch:** `GET /api/tasks/maintain-overview` (TaskDetail) + latest output from `sys_manifest.json` — same as Work surface
- **Render:** Extract `<TaskOutputCard />` as a shared sub-component from `DeliverableMiddle` (iframe + SectionProvenanceStrip). Intelligence Card uses it directly.
- **Empty state:** Latest output absent (day-zero) or `sys_manifest.json.created_at` > 48h (execution failure) → placeholder card: "Synthesis pending — runs at 06:00"

`TaskOutputCard` extraction is the only new React component. It is a thin wrapper around the iframe + SectionProvenanceStrip already implemented in `DeliverableMiddle`.

`KIND_LABELS` in `DeliverableMiddle.tsx` is already an open map (`?? section.kind` fallback at line 60). Any section kind the agent emits — including kinds not in the current map — displays gracefully with the raw kind string as the label. No frontend change needed for catalog-driven section kinds.

---

## Implementation plan

### Phase 1

**Backend:**

| File | Change |
|------|--------|
| `api/services/task_types.py` | Add `maintain-overview` task type: `output_kind: produces_deliverable`, `surface_type: workspace-intelligence`, `page_structure` = full catalog (title + kind pairs), step instructions for Reporting agent |
| `api/services/workspace_init.py` | Phase 5c: add `_create_essential_deliverable_task(client, user_id, type_key, slug, title, schedule, agent_slugs, user_timezone)` helper; call it for `maintain-overview` with `schedule="0 6 * * *"`. Scaffold TASK.md + DELIVERABLE.md at signup. |
| `api/services/working_memory.py` | Add `domain_entity_counts` + `outcome_connected` to `workspace_state` dict |
| `api/services/task_pipeline.py` | Add `_is_workspace_empty_for_maintain_overview()` or reuse existing helper; empty-state short-circuit branch analogous to ADR-161 |
| `api/prompts/CHANGELOG.md` | Entry for maintain-overview task type + step instruction |

**Frontend:**

| File | Change |
|------|--------|
| `web/components/work/details/DeliverableMiddle.tsx` | Extract `<TaskOutputCard />` sub-component (iframe + SectionProvenanceStrip) |
| `web/components/overview/IntelligenceCard.tsx` | New component: fetch maintain-overview latest output, render TaskOutputCard, empty-state |
| `web/components/overview/OverviewSurface.tsx` | Add `<IntelligenceCard />` below `<SnapshotPane />` |

### Phase 2 (future ADR)

- Lazy refresh: if `sys_manifest.json.created_at` > 6h, trigger async re-execution on Overview load
- DELIVERABLE.md preference inference: after ≥5 runs, `infer_task_deliverable_preferences()` distills recurring section patterns into operator-confirmed preferences

---

## What this does NOT change

- Three existing Overview panes — unchanged in behavior, data, and position
- Four existing back-office tasks — unchanged, still `system_maintenance`
- `daily-update` — unchanged (briefing artifact, email-delivered, distinct consumer)
- `DeliverableMiddle` — additive sub-component extraction only
- No new DB tables, no new columns, no schema migration

---

## Alternatives considered

**A. TP executor + custom Haiku call (Model A) — prepared cost-fallback**

Model A was the initial design: maintain-overview assigned to TP (`role=thinking_partner`), `_execute_tp_task()` calls a `maintain_overview.py` executor, Phase A deterministic skeleton + Phase B Haiku narrative call inside the executor, no `agent_runs` row, no balance charge, ~$0.0015/day.

**Why Model B (Reporting agent) was chosen instead:** The Reporting agent's identity and accumulated synthesis context is the right instrument for a cockpit intelligence task. Model A would require a custom executor replicating the context-gathering phase the pipeline already provides, and would lose the `agent_runs` audit trail. Model B is structurally correct; the cost difference between Sonnet and Haiku is not a blocking concern at current scale.

**Revert to Model A if:** Post-scale testing shows maintain-overview's Sonnet token cost is material relative to the operator's overall balance consumption. Revert criteria: maintain-overview costs > 20% of an operator's daily balance on average.

**Switch points for Model A revert:**
1. Change agent assignment from `reporting` to `thinking_partner` in TASK.md
2. Add `executor: services.back_office.maintain_overview` to TASK.md process step
3. Write `api/services/back_office/maintain_overview.py` with Phase A skeleton + Phase B Haiku call (no agent_runs row, no balance check, executor returns `{"output_markdown": ..., "structured": {...}}`)
4. The compose pipeline (`_compose_and_persist()`) still runs — `_execute_tp_task()` persists output, compose is called separately, or the executor calls the render service directly
5. Model switch does not require schema changes or frontend changes

**B. Reactive per-visit synthesis query**
Rejected: per-visit LLM call adds 300–2000ms latency + unsustainable at scale.

**C. `system_maintenance` with executor writing HTML directly**
Rejected: duplicates the compose pipeline inside an executor module. Two parallel paths for HTML production. Violates singular-implementation discipline.

**D. Extend SinceLastLookPane to include domain synthesis**
Rejected: conflates session-relative briefing with substrate-persistent intelligence. The temporal demarcation between the two panes is load-bearing for Overview's information architecture.

**E. Single meta-task replacing all four back-office tasks + synthesis**
Rejected: blast-radius risk. Outcome reconciliation calls external APIs (Alpaca, LS); failure there must not block agent hygiene or workspace cleanup. Independent failure modes are a feature.

**F. Fixed four-section DELIVERABLE.md**
Rejected: workspace shape varies too much across operators. Fixed sections produce empty shells for workspaces without matching data (e.g., `metric-cards` for operators with no outcomes platform). Catalog-driven agnostic composition produces a cockpit that reflects actual accumulated knowledge rather than a template skeleton.

---

## Directional theme: cockpit as seed, not endpoint

The DELIVERABLE.md catalog and archetype framing hints are a **seed** — a reasonable day-one cockpit for a workspace that hasn't told us anything specific yet. The seed provides grounded initial structure; it is not the final shape.

The long-term direction is a **user-customizable BI dashboard**: the operator shapes the cockpit over time — adding, removing, or reordering sections, defining their own section kinds, pinning metrics relevant to their specific work, surfacing the signals they care about most. The current agnostic-catalog + archetype-framing approach is architected to support this: the catalog is a superset that evolves via inference (ADR-149), the section kinds are open (render pipeline accepts any kind string), and the workspace_state dict is extensible. Nothing in this ADR forecloses operator-driven customization; everything here is the substrate that customization would build on.

This is not a committed roadmap item — no scaffolding, no new surfaces, no new primitives for customization are in scope for Phase 1 or Phase 2. The directional theme informs design choices now: we do not hardcode section shapes, we do not enforce an allow-list, and we do not treat the catalog as a permanent schema.

**On other task types:** Each `produces_deliverable` task has its own seed — `daily-update`'s current four sections are its seed, with its own evolution path. The question of how any specific task's seed evolves is a per-task decision made when there's operator signal to act on. No generalization call is needed now.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Notes |
|--------|--------|-------|
| **Day trader (alpha-trader)** | **Helps** | Cockpit shows portfolio domain health, instrument coverage, P&L trends. Palantir-like intelligence without leaving Overview. |
| **E-commerce** | **Helps** | Cockpit shows customer/revenue domain health, product entity coverage, revenue momentum. |
| **AI influencer** (scheduled) | Forward-helps | Content domain synthesis, topic coverage depth, publishing opportunity signals. |
| **International trader** (scheduled) | Forward-helps | Logistics/counterparty domain health, compliance coverage, cross-domain risk narrative. |

Domain-agnostic by construction: the section catalog covers all operator types; the agent selects the appropriate subset. No verticalization in the structure — archetype framing lives in the DELIVERABLE.md hints and the agent's judgment, not in the pipeline.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-21 | v1 — Initial proposal. Workspace Intelligence Card as fourth Overview pane. `maintain-overview` task (`output_kind: produces_deliverable`, Reporting agent). Domain-agnostic archetype classification via `workspace_state`. ADR-198 I2 amended. Six open questions in §OQ for alignment. |
| 2026-04-21 | v2 — Two substantive changes from alignment: (1) OQ-2 resolved to Model B (Reporting agent, standard pipeline) — Model A (TP executor + Haiku) documented as prepared cost-fallback with explicit revert criteria and switch points. (2) OQ-4 resolved: fixed section set replaced with catalog-driven agnostic composition — DELIVERABLE.md declares a superset catalog; Reporting agent chooses the subset appropriate to the workspace. Pipeline compatibility verified (parse_draft_into_sections open parser, render service unknown-kind fallback, KIND_LABELS graceful degradation). Discourse point added on whether agnostic section pattern generalizes beyond maintain-overview. All other OQs from v1 resolved. |
| 2026-04-21 | v2.1 — Implementation gate verified: `calculate_next_run_at()` already supports cron strings via `_looks_like_cron()` + croniter path — no scheduler enhancement needed. Implementation note updated: Phase 5c requires a new `_create_essential_deliverable_task()` helper (existing back-office helper hardcodes `"daily"`; maintain-overview also writes DELIVERABLE.md and uses non-TP agent). |
| 2026-04-21 | v2.2 — Philosophy update (no decision change): "fixed-template vs workspace-adaptive" framing removed. Replaced with directional theme: DELIVERABLE.md catalog + archetype hints are a seed, not an endpoint. Long-term direction is user-customizable BI dashboard — open section kinds, inference-driven evolution, operator-shaped cockpit. No new scaffolding in scope. Discourse point on daily-update generalization dissolved — each task has its own seed with its own evolution path; no generalization call needed now. |
| 2026-04-22 | **Phase 1 Implemented** — Backend: `maintain-overview` task type in `task_types.py` (output_kind=produces_deliverable, 7-entry page_structure catalog, workspace-intelligence step instruction, custom_deliverable_md with full catalog + archetype framing hints); `_create_essential_deliverable_task()` helper in `workspace_init.py` (cron schedule support); Phase 5c seeds maintain-overview at signup (06:00 local); `workspace_state` in `working_memory.py` gains `domain_entity_counts` + `outcome_connected`; empty-state branch in `task_pipeline.py` writes warming-up artifact at zero LLM cost. Frontend: `TaskOutputCard` extracted from `DeliverableMiddle` (shared iframe+SectionProvenanceStrip primitive); `IntelligenceCard.tsx` created (fetch + render + empty states); `OverviewSurface.tsx` wired. Minor deviation from ADR: `custom_deliverable_md` field added to task type registry as an extension point for catalog-driven tasks — not an architectural change, consistent with ADR-188 "registries as template libraries." |
