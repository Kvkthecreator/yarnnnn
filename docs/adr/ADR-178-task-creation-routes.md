# ADR-178: Task Creation Routes — Context-Driven and Output-Driven Scaffolding

**Date:** 2026-04-13
**Status:** Proposed
**Authors:** KVK, Claude
**Extends:** ADR-149 (Task Lifecycle — DELIVERABLE.md as quality contract), ADR-173 (Accumulation-First Execution), ADR-176 (Work-First Agent Model)
**Evolves:** ManageTask(action="create") in ADR-168 (Primitive Matrix)

---

## Context

Today, `ManageTask(action="create")` has one primary creation path: provide a `type_key` from the registry, and the task is scaffolded from the registry definition — TASK.md, DELIVERABLE.md, agent assignment, context domain setup. A secondary path exists for fully custom tasks (provide `agent_slug` + objective directly).

The type-key path is clean but assumes the user's intent maps to an existing registry entry. In practice, user intent arrives in two distinct shapes that the current single path doesn't differentiate:

**Shape 1 — Output-driven:** The user has a clear deliverable in mind. "I want a weekly competitive brief." "I want to maintain a blog." "I want a standing deck for investor updates." The *output* is the anchor. The user knows what they want to receive; the platform works backward to determine what context the task needs and which agents should produce it. DELIVERABLE.md is rich and specific from day one. Context domains are inferred from the deliverable's requirements.

**Shape 2 — Context-driven:** The user has existing context or an ongoing tracking need. "I'm monitoring five competitors." "I want to track our market." "Keep a pulse on relationships across my Slack." The *input domain* is the anchor. The user knows what they're watching; the platform works forward to determine what outputs can be derived from that accumulated context. Context domain scaffolding is the primary artifact. DELIVERABLE.md may be thin at creation and thickens as outputs are produced and evaluated.

Both routes arrive at the same destination — a task with TASK.md, DELIVERABLE.md, assigned agents, context domain scaffolding, and scheduling — but the scaffolding emphasis and the TP conversation path are different. The originator (TP via conversation, user via UI catalog, user via natural language) doesn't determine the route; the *intent shape* does.

This distinction also has direct implications for:
- **DELIVERABLE.md richness at creation**: output-driven tasks start with a complete spec; context-driven tasks start with criteria and grow the spec from produced outputs
- **Task mode defaults**: output-driven tasks default to `recurring` or `goal` depending on whether the deliverable is open-ended or bounded; context-driven tasks almost always start `recurring`
- **Team composition**: output-driven tasks may need production-phase specialists (Designer) alongside accumulation-phase specialists; context-driven tasks start with accumulation specialists only
- **Frontend scaffolding surface**: output-driven creation should show a DELIVERABLE.md preview at creation time; context-driven creation should show domain scope configuration

---

## Decision

### Two named creation routes

Task creation has two named routes. The route is determined by TP (or the UI) based on the nature of the user's intent. Both routes use `ManageTask(action="create")` — the primitive is unchanged. The route shapes what inputs TP provides.

---

#### Route A: Output-Driven

**Trigger signal:** User expresses a desired deliverable. Keywords: "I want", "give me", "send me", "maintain a", "produce", "keep updated". Output noun is present: brief, report, deck, digest, blog, newsletter, tracker, dashboard.

**TP behavior:** Reverse-engineer the deliverable. What context does it need? What cadence makes sense? What agents can produce it? Who is the audience?

**Scaffolding emphasis:**
- `type_key` from registry if a match exists (preferred path — registry has opinionated DELIVERABLE.md stubs, page_structure, team composition)
- If no registry match: TP constructs a `page_structure` from the described output format, derives `context_reads` from content requirements, defaults team to Writer + one domain specialist appropriate to the content
- DELIVERABLE.md is **rich at creation**: `Expected Output` section filled with format, word count, surface type, section kinds; `Expected Assets` filled if output warrants charts/images; `Quality Criteria` filled from TP's read of success conditions in the user's statement
- Mode defaults: `recurring` if open-ended cadence, `goal` if bounded deliverable ("until the product launches", "for the board meeting")
- `page_structure` in TASK.md: populated at creation for `produces_deliverable` tasks

**ManageTask call shape (TP):**
```
ManageTask(
  action="create",
  title="Weekly Competitive Brief",
  type_key="competitive-brief",          # registry match
  mode="recurring",
  schedule="weekly",
  delivery="email: kevin@...",
  team=["researcher", "analyst", "writer"],  # may override registry default
  page_structure=[...],                  # may override registry page_structure
)
```

**DELIVERABLE.md at creation:**
```markdown
# Deliverable Specification

## Expected Output
- Format: HTML report
- Surface: report
- Sections: Executive Summary (narrative), Competitor Profiles (entity-grid),
  Signal Timeline (timeline), Strategic Implications (callout)
- Word count: 800–1200 words

## Expected Assets
- Competitor favicons (entity-grid): fetched via fetch-asset skill
- Trend chart if pricing/market data present: trend-chart kind

## Quality Criteria
- Every competitor claim has a source and recency date
- Executive summary ≤ 3 sentences, leads with the week's most significant change
- Strategic implications section present on every run

## Audience
Internal — founder/operator

## User Preferences (inferred)
<!-- Populated by feedback inference after evaluation cycles. Empty at creation. -->
```

---

#### Route B: Context-Driven

**Trigger signal:** User expresses a domain they're monitoring or a data source they're maintaining. Keywords: "track", "monitor", "watch", "keep tabs on", "follow", "maintain intelligence on". Domain noun is present: competitors, market, relationships, signals, channels, repos.

**TP behavior:** Identify the domain. What entities are being tracked? What platform sources feed this domain? Is there an existing context domain to extend, or a new one to scaffold? What outputs could this context eventually produce?

**Scaffolding emphasis:**
- `type_key` from registry if a tracking type matches (track-competitors, track-market, track-relationships, slack-digest, notion-digest, github-digest)
- `context_writes` is the primary field — domain scaffolding is the deliverable
- DELIVERABLE.md is **thin at creation**: `Expected Output` describes context files to maintain, not a surface output; `Quality Criteria` focused on data freshness, entity coverage, citation hygiene
- Mode is always `recurring` — context accumulation is open-ended
- `page_structure` in TASK.md: absent or empty (no surface output declared yet; outputs are context files)
- Outputs-from-context are suggested as a follow-up: "Once I've tracked these competitors for a few weeks, I can produce a weekly brief from this context — want me to set that up too?" This is a separate `produces_deliverable` task creation, not bundled into the tracking task

**ManageTask call shape (TP):**
```
ManageTask(
  action="create",
  title="Track Competitors",
  type_key="track-competitors",
  mode="recurring",
  schedule="weekly",
  team=["researcher"],
)
```

**DELIVERABLE.md at creation:**
```markdown
# Deliverable Specification

## Expected Output
- Format: context files
- Paths: /workspace/context/competitors/{entity}/profile.md,
         /workspace/context/competitors/{entity}/signals.md,
         /workspace/context/competitors/landscape.md
- Entities: minimum 3 maintained profiles

## Expected Assets
- Competitor favicons: /workspace/context/competitors/assets/{slug}-favicon.png

## Quality Criteria
- Minimum 3 competitor profiles maintained and updated within 30 days
- Every finding has a source and recency date
- Landscape synthesis updated each cycle

## Audience
Internal — feeds produces_deliverable tasks (competitive-brief, market-report)

## User Preferences (inferred)
<!-- Populated by feedback inference after evaluation cycles. Empty at creation. -->
```

---

### Route determination: TP judgment, not form fields

TP determines the route from conversational context. No new primitive input, no explicit route parameter. The distinction is TP's read of whether the user's intent anchors on *what they want to receive* (output-driven) or *what they want to track* (context-driven).

When intent is ambiguous, TP defaults to **output-driven** and asks one clarifying question: "Is this something you want delivered on a schedule, or more of an ongoing intelligence feed?"

Both routes can co-exist for related work: a user may have a `track-competitors` context task (Route B) *and* a `competitive-brief` deliverable task (Route A) that reads from `context_reads: ["competitors"]`. TP manages this composition explicitly. The tracking task feeds the deliverable task. They are separate tasks, not one combined task.

---

### DELIVERABLE.md as first-class surface (Phase 6 activation)

This ADR activates ADR-149 Phase 6, which was deferred. DELIVERABLE.md moves from a backend execution artifact to a **user-visible, living quality contract** surfaced in the work detail view.

**Why now:** The two-route distinction makes DELIVERABLE.md's richness visible and meaningful. An output-driven task's DELIVERABLE.md tells the user exactly what they're getting before the first run. A context-driven task's DELIVERABLE.md tells the user what data quality they can expect. In both cases, seeing the spec at task creation time grounds expectations and makes the task feel concrete rather than abstract.

**What Phase 6 means in practice:**

1. **API exposure:** `GET /api/tasks/{slug}` TaskDetail response includes `deliverable_spec` — the parsed DELIVERABLE.md content as a structured object
2. **Frontend Quality Contract panel:** DeliverableMiddle gains a collapsible "Quality Contract" section showing Expected Output, Quality Criteria, and User Preferences (inferred). Updated in real-time as inference runs.
3. **Creation-time preview:** During task creation (TP chat), TP shows a brief DELIVERABLE.md summary inline in the chat response so the user can see what quality contract they're agreeing to before confirming creation
4. **Auto-inference trigger:** After `ManageTask(action="evaluate")`, if `memory/feedback.md` has ≥ 2 entries since the last inference run, TP calls `infer_task_deliverable_preferences()` as the next step in the same evaluate turn. TP judgment, not a background pipeline cron.

---

### Task mode and the creation routes

Mode is a **task property** — it lives in both `tasks.mode` (DB scheduling index) and TASK.md `**Mode:**` (execution contract). These must be identical at all times. `_handle_update()` in `manage_task.py` is responsible for syncing both on every mode change.

Route implications:
- **Output-driven, open-ended deliverable** → `recurring` (auto-deliver each cycle)
- **Output-driven, bounded deliverable** → `goal` (TP evaluates → steers → completes when done)
- **Context-driven** → always `recurring` (accumulation is open-ended by nature)
- **Reactive** → set explicitly when the task should fire on platform events, not schedule

The mode is set at creation and is mutable. When TP changes mode (e.g., switching a recurring brief to goal mode for a specific initiative), `ManageTask(action="update", mode="goal")` patches *both* the DB row and TASK.md `**Mode:**` field in the same operation.

**Critical invariant:** `tasks.mode` (DB) == TASK.md `**Mode:**` field at all times. Any code path that modifies mode must update both atomically.

---

### Frontend implications

The two routes have distinct frontend expressions across the work surface:

**Task creation (TP chat):**
- Route A (output-driven): TP response includes inline DELIVERABLE.md summary — "Here's what I'll produce each week: [spec preview]"
- Route B (context-driven): TP response describes the domain being tracked and suggests a future deliverable task — "I'll track these 5 competitors weekly. When you want a brief from this context, say the word."

**Work detail page (`/work?task={slug}`):**
- `produces_deliverable` tasks (Route A): DeliverableMiddle shows output preview + Quality Contract panel (DELIVERABLE.md) + section provenance strip (sys_manifest)
- `accumulates_context` tasks (Route B): TrackingMiddle shows domain folder link + entity count + last-run CHANGELOG + Quality Contract panel (DELIVERABLE.md, context-focused spec)

**Task card on work list:**
- Route A tasks: subtitle is the deliverable description from `objective.deliverable`
- Route B tasks: subtitle is the domain being tracked with entity count

**Agent card on `/agents`:**
- Agent cards show assigned tasks grouped by route type: "Producing" (output-driven) / "Tracking" (context-driven)
- This makes visible the agent's two roles: production and accumulation

---

## Impact Radius

### ADRs with status implications

| ADR | Relationship |
|-----|-------------|
| ADR-149 | Extended — Phase 6 (DELIVERABLE.md frontend surface) now active. Auto-inference trigger defined (TP-initiated, post-evaluate, ≥2 entries since last inference). |
| ADR-173 | Extended — accumulation-first principle now applies at creation time: context-driven tasks accumulate before producing; output-driven tasks declare what they'll produce before accumulating context |
| ADR-176 | Extended — team composition defaults now tied to route type: Route A may include Designer; Route B is accumulation specialists only |
| ADR-168 | Extended — ManageTask(action="create") input schema now has two well-defined calling patterns (Route A vs Route B), not just two paths (type_key vs agent_slug) |
| ADR-177 | Extended — output-driven tasks with page_structure declared at creation feed directly into the compose substrate's generation brief; the section kinds declared at creation become the compose contract |

### Documents needing updates (Phase B+ implementation)

| Document | Update |
|----------|--------|
| `api/services/primitives/manage_task.py` | `_handle_create` — add inline DELIVERABLE.md summary in return response for TP to surface. `_handle_update` — sync `**Mode:**` in TASK.md on mode change (Phase B mode sync fix). |
| `api/services/primitives/manage_task.py` | `_handle_evaluate` — after evaluation, call `infer_task_deliverable_preferences()` if feedback entry count ≥ 2 since last inference |
| `api/routes/tasks.py` | `TaskDetail` response — add `deliverable_spec` field (parsed DELIVERABLE.md as structured object) |
| `web/components/work/details/DeliverableMiddle.tsx` | Add Quality Contract panel (Phase C frontend) |
| `web/components/work/details/TrackingMiddle.tsx` | Add Quality Contract panel for context tasks (Phase C frontend) |
| `web/types/index.ts` | Add `deliverable_spec` to TaskDetail type |
| `docs/features/agent-modes.md` | Rewrite: mode is task property, three modes only, sync invariant |
| `CLAUDE.md` | Add ADR-178 entry |

---

## Rejected Alternatives

### A: Single "intent" field on ManageTask(create) that selects the route

An explicit `intent: "output" | "context"` parameter was considered. Rejected because TP already reads intent from conversation — forcing an explicit parameter would require TP to first identify intent, then encode it in a field that ManageTask ignores structurally (both routes produce the same TASK.md output). The distinction is in what TP provides, not in a new primitive flag.

### B: Separate primitives for context-task creation vs deliverable-task creation

Splitting creation into `ManageContextTask` and `ManageDeliverableTask` was considered (similar to how `accumulates_context` and `produces_deliverable` are distinct output_kinds). Rejected because ADR-168 deliberately folded CreateTask into ManageTask for symmetry and because the two routes share 90% of the same scaffolding logic. The distinction is a calling convention, not a structural divergence.

### C: DELIVERABLE.md auto-inference on feedback count in the pipeline (without TP)

Post-run inference trigger (if feedback ≥ 2, run inference in execute_task) was considered. Rejected: ADR-156 — TP is the single intelligence layer. Pipeline triggering inference is a second intelligence path, which violates the architectural principle. Feedback entries may be contradictory, resolved by steering, or insufficient context for meaningful inference. TP's evaluate turn is the right moment — TP has conversation context and can judge whether inference is warranted.
