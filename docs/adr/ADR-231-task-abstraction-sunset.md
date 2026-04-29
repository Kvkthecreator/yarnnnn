# ADR-231: Task Abstraction Sunset — Mandate-Driven Invocations as the Sole Work Model

> **Status**: **Proposed** (2026-04-28). Architecture-only ratification; phased implementation deferred to Phase commits 1–N (see §Implementation Phases).
> **Date**: 2026-04-28
> **Authors**: KVK, Claude
> **Dimensional classification**: **Trigger** (Axiom 4) primary, **Substrate** (Axiom 1) + **Mechanism** (Axiom 5) + **Channel** (Axiom 6) secondary.
> **Ratifies for implementation**: FOUNDATIONS v6.8 Axiom 9 (invocation as atom; task as legibility wrapper) + [invocation-and-narrative.md](../architecture/invocation-and-narrative.md) — finishes the implementation that ADR-219 deliberately left short of substrate dissolution.
> **Supersedes**: ADR-138 (Agents as Work Units → tasks-as-units framing dissolves; agents survive as Identity layer per Axiom 2; work units dissolve into invocations), ADR-149 (Task Lifecycle Architecture → most lifecycle actions dissolve into frontmatter edits + filesystem operations; DELIVERABLE.md survives only for `produces_deliverable` shapes), ADR-161 (Daily Update Anchor → essential-task framing dissolves; daily-update becomes a recurrence declaration on the workspace narrative root), ADR-166 (Registry Coherence — `output_kind` 4-value enum → enum dissolves; shape is implied by substrate location), ADR-167 v2 (List/Detail Surfaces → `/work` becomes filter-over-narrative per ADR-219, not a task-table-backed surface).
> **Amends**: ADR-207 (Primary-Action-Centric Workflow — Mandate hard gate preserved; capability gating preserved; TASK_TYPES registry sunset is finished here), ADR-195 v2 (Money-Truth Substrate — outcome reconciliation moves from `back-office-outcome-reconciliation` task to a recurrence declaration on `_shared/back-office.yaml`; substrate semantics unchanged), ADR-209 (Authored Substrate — every recurrence-declaration `.yaml` write is attributed; no new attribution plumbing).
> **Preserves**: FOUNDATIONS v6.8 axioms (1–8 unchanged; Axiom 9 finally implemented end-to-end), ADR-141 (execution mechanism layers unchanged; invocation is one cycle through them), ADR-194 v2 (Reviewer substrate at `/workspace/review/` unchanged; reactive pulse unchanged; verdict surfacing via narrative unchanged), ADR-205 (chat-first triggering, run-now-default — *now becomes the genuine default* rather than the exception), ADR-219 (narrative as universal log — narrative entries continue to be the single legibility surface; task slug stays as one filter axis among others), ADR-222 (OS framing — kernel boundary preserved; bundles + reference-workspaces unchanged), ADR-230 (persona/program registry unification — operates cleanly atop this substrate change).
> **Triggered by**: A multi-turn architectural discourse (this session, 2026-04-28) that surfaced the gap between Axiom 9 canon (ratified 2026-04-25 by ADR-219) and current implementation. The canon says tasks are nameplate-pulse-contract legibility wrappers over invocation patterns. The implementation still treats tasks as a parallel substrate: dedicated DB table, dedicated filesystem (`/tasks/{slug}/`), heavyweight primitive surface (`ManageTask` with 9 actions), and — critically — a TP default behavior that creates a task for almost every operator request rather than firing immediate invocations. Every alpha-trader E2E test ends with a pile of fragmented tasks-with-schedules instead of immediate-work-with-files.

---

## Context

### The gap between Axiom 9 canon and current implementation

FOUNDATIONS v6.8 Axiom 9 (2026-04-25) named four commitments:

1. **Invocation** = one cycle through the six dimensions; the atom of action.
2. **Pulse** = the actor-scoped wrapper around Axiom 4 Trigger.
3. **Narrative** = single chat-shaped log of every invocation.
4. **Task** = a *legibility wrapper* (nameplate + pulse + contract) over a category of recurring invocations — *not* a parallel substrate.

[ADR-219](./ADR-219-invocation-narrative-implementation.md) (2026-04-25 → 2026-04-26) implemented commitments 1–3: `session_messages` became the narrative substrate, `write_narrative_entry` became the single write path, every invocation emits exactly one narrative entry. ADR-219 explicitly preserved task schema: *"Amends ADR-138 (tasks reframed as legibility wrappers; schema unchanged)."* The canon was made enforceable for narrative; the canon was *not* made enforceable for the task abstraction itself.

The result is drift between canon and code. Canon says tasks label invocations; code makes tasks the unit of work. Canon says `/work` is a filter-over-narrative; code backs `/work` with a `tasks` table query. Canon says inline-to-task graduation is a nameplate-attach (no substrate migration); code requires creating a `tasks` row and a `/tasks/{slug}/` filesystem tree before any work can fire.

The drift is observable in three concrete places:

- **TP default behavior**: When an operator says "give me a competitive teardown of Acme Corp," current TP creates a task — `ManageTask(action="create", title="Acme Corp teardown", mode="goal", ...)` — rather than firing an immediate invocation that produces a file. Every operator request scaffolds a task because that is the path of least resistance the primitive surface offers.
- **Task fragmentation in E2E tests**: Alpha-trader E2E runs end with 8–14 fragmented tasks, each with its own `/tasks/{slug}/` tree, its own DELIVERABLE.md, its own schedule. The operator-facing "operation" is theoretically one cohesive thing; in substrate it is a pile of namespaced sub-projects.
- **Substrate split between domains and tasks**: Per ADR-151/152/158, context domains live at `/workspace/context/{domain}/` (workspace-scoped, shared across all tasks). Per legacy task model, task outputs live at `/tasks/{slug}/outputs/` (task-scoped). For `accumulates_context` tasks, the *real* output is the domain files — the `/tasks/{slug}/outputs/` directory contains a CHANGELOG markdown the operator never reads. The substrate split papers over a shape difference: tasks that accumulate domain state are not the same shape as tasks that produce discrete artifacts.

### What persistence actually forces

A common defense of the current task abstraction is that "persistence requires it." This ADR rejects that framing. YARNNN's persistence requirements are met by primitives that *already exist* in the codebase, independent of the task abstraction:

| Requirement | Met by | ADR reference |
|---|---|---|
| Recurrence (cron-shaped scheduling) | A scheduler that queries declarative state | ADR-141 (mechanical scheduling) |
| Long-running artifacts that evolve | Filesystem versioning with attribution | ADR-209 (Authored Substrate) |
| Multi-actor attribution | `authored_by` taxonomy on every write | ADR-209 |
| Closed-loop feedback over time | `_feedback.md` siblings to artifacts/domains | ADR-181 (source-agnostic feedback) |
| Operator observability | Narrative as universal log; `/work` as filter | Axiom 9 + ADR-219 |
| Mandate as standing intent | `/workspace/context/_shared/MANDATE.md` | ADR-207 |

Every persistence requirement YARNNN distinguishes from Claude Code is satisfied by primitives that already exist outside the task abstraction. The task abstraction therefore is not load-bearing for persistence — it is load-bearing for one specific concept: **a stable nameplate over a recurring invocation pattern when the operator wants a labeled handle**. That use case survives this ADR. Everything else dissolves.

### Architecture vs GTM separation

This ADR ratifies an *architectural* commitment. It does not ratify a GTM positioning. The architecture supports two distinct narratives without modification:

- **Mandate-driven autonomous operations** (ADR-207, alpha-trader): operator authors MANDATE.md; TP fires invocations under operator's standing intent and Reviewer's principles; cockpit speaks the operation's vocabulary (ADR-228 four-face cockpit).
- **Persistent Claude Code** (no mandate, no recurrence): operator chats; TP fires invocations immediately; outputs land in filesystem; recurrence is opt-in via explicit operator request ("do that every Monday").

Both modes run on the same substrate (filesystem-native) and the same dispatch (mandate optional, invocations always-immediate). The mandate is *optional but powerful when authored*. The GTM narrative chooses which mode to lead with; the architecture supports either.

### Strategic context: why finishing the migration is overdue

YARNNN's structural moat against incumbent LLM providers (Claude Code, ChatGPT scheduled tasks, Gemini Workspace, etc.) is not "scheduled AI workflows" — that is the table-stakes feature every provider is shipping. YARNNN's moat is **persistent operator-authored substrate** + **a singleton persona-bearing judgment seat (Reviewer)** + **mandate-driven autonomous execution**. None of these are in the LLM providers' surface area; all of them are filesystem-native. The task abstraction is an Era 1 artifact from when YARNNN was framed as an "agent framework with recurring autonomous work" — a framing that competes with LLM providers on similar-but-better terms (and loses on distribution, capital, speed). The Era 2 framing (operations-as-service per ADR-207, ADR-222 OS framing, ADR-228 cockpit-as-operation) is the defensible position; this ADR finishes the substrate migration into Era 2.

---

## Decision

### D1 — Invocation is the default; tasks are the exception (graduation-shaped)

TP's default behavior, encoded in `yarnnn_prompts/`, becomes:

> When the operator addresses you, fire an invocation that does the work *now*. Write outputs to natural-home substrate. Emit a narrative entry. Done. Create a recurrence declaration *only* when the operator's intent is explicitly recurring ("do that every Monday", "track this domain weekly", "produce this brief on a schedule") or when goal-mode bounding is explicitly intended.

This is a TP prompt rewrite + a primitive-surface narrowing. `ManageTask(action="create")` becomes a graduation primitive (not a default-creation primitive); its prompt-level guidance instructs TP to use it *only* when recurrence is genuinely intended, never as a scaffold for one-off work.

Inline action → recurrence graduation is the affordance flow Axiom 9 §4 describes:

- Inline action: operator says "pull today's revenue" → TP invokes `get_revenue` via primitive → narrative entry → done. No nameplate, no persistent pulse, no `/tasks/{slug}/` directory.
- Recurrence graduation: operator says "do that every morning" → TP creates a recurrence declaration via `UpdateContext(target=...)` writing a `.yaml` file at the natural location → next firing carries the slug in its narrative entry, scheduler fires it again per cron.
- Recurrence dissolution: operator says "stop doing that" → TP edits the declaration's `paused: true` (or removes the file entirely) → no new firings; historical narrative entries unchanged.

The transition is a frontmatter-edit operation, not a substrate migration. This is the Axiom 9 model finally enforced.

### D2 — `/tasks/{slug}/` filesystem dissolves; substrate moves to natural homes

The dedicated `/tasks/{slug}/` filesystem tree is deleted. Each kind of work writes to its natural-home substrate:

| Work shape | Output substrate (post-D2) |
|---|---|
| Recurring deliverable (e.g., weekly market report) | `/workspace/reports/{slug}/{date}/output.md` + composed HTML |
| One-off deliverable (e.g., on-demand competitive teardown) | `/workspace/reports/{operator-named-slug}-{date}.md` (or operator-specified path) |
| Domain accumulation (e.g., competitor tracking) | `/workspace/context/{domain}/{entity}/*.md` (already canonical per ADR-151/152) |
| External action (e.g., trade submit, slack-respond) | Platform event + outcome ledger entry in `/workspace/context/{domain}/_performance.md` (already canonical per ADR-195 v2) |
| Back-office maintenance | Audit log at `/workspace/_shared/back-office-audit.md` (or domain-scoped audit per executor) |

**Feedback substrate moves with the artifact** (resolves the ADR-181 scope drift the prior task audit surfaced):

- For deliverables: `/workspace/reports/{slug}/_feedback.md` (per-report-slug feedback)
- For domains: `/workspace/context/{domain}/_feedback.md` (per-domain feedback — already canonical per ADR-181)
- For external actions: outcome reconciliation at `_performance.md` per ADR-195 (no separate feedback file; outcomes are the feedback signal)

**Run-log substrate (where it survives) moves to natural homes**:

- For recurring deliverables: `/workspace/reports/{slug}/_run_log.md` (append-only execution history)
- For domain accumulation: domain `_run_log.md` (append-only; already partial in some domains)
- For external actions: narrative entries are the run log (no separate file)
- For back-office: `_shared/back-office-audit.md` (single index, append-only)

### D3 — Recurrence declarations are `.yaml` files at natural-home locations

Format-by-shape principle (ratified as canonical):

| Data shape | Format | Examples |
|---|---|---|
| Operator-authored prose | `.md` | `MANDATE.md`, `IDENTITY.md`, `_domain.md` (narrative content), `BRAND.md` |
| Pure machine config | `.yaml` | Recurrence declarations, capability config, schedule indexes |
| Audit / append-only logs | `.md` | `decisions.md`, `_run_log.md`, `_feedback.md`, narrative entries |
| Structured machine state | `.json` | `manifest.json`, `sys_manifest.json` |
| Tabular data at scale | `.csv` / `.tsv` | (future, when entity counts justify) |
| Composed deliverables | `.html` / `.pdf` | Render service output |
| Code / executors / scripts | `.py` / `.sh` / `.js` | Back-office executors, render skills |

Recurrence declarations specifically are `.yaml`, not `.md`-with-frontmatter. This removes the awkwardness of "markdown body that's empty because the file is pure config." Concrete shapes:

**Domain recurrence** (`/workspace/context/competitors/_recurring.yaml`):
```yaml
recurrences:
  - slug: competitors-weekly-scan
    schedule: "0 9 * * 1"
    agent: researcher
    objective: "Weekly competitive moves, pricing, funding signals"
    paused: false
    context_reads: [signals]
    context_writes: [competitors]
```

**Deliverable recurrence** (`/workspace/reports/market-weekly/_spec.yaml`):
```yaml
report:
  slug: market-weekly
  display_name: "Weekly Market Report"
  output_path: "/workspace/reports/market-weekly/{date}/output.md"
  recurring:
    schedule: "0 9 * * 1"
    paused: false
  agents: [analyst, writer]
  deliverable:
    audience: "Operator"
    page_structure: [headlines, by-domain, action-items]
    quality_criteria: [...]
  context_reads: [competitors, market]
```

**External action recurrence** (`/workspace/operations/slack-standup/_action.yaml`):
```yaml
action:
  slug: slack-standup
  display_name: "Daily Slack Standup"
  recurring:
    schedule: "0 9 * * 1-5"
    paused: false
  target_capability: write_slack
  target_channel: "#standup"
  template_path: "_template.md"
  context_reads: [team-status]
```

**Back-office index** (`/workspace/_shared/back-office.yaml` — single file, list of jobs):
```yaml
back_office_jobs:
  - executor: services.back_office.workspace_cleanup
    schedule: "0 0 * * *"
    paused: false
  - executor: services.back_office.outcome_reconciliation
    schedule: "0 4 * * *"
    paused: false
  - executor: services.back_office.narrative_digest
    schedule: "0 6 * * *"
    paused: false
```

**One-off operator-narrative intent** (optional, alongside any of the above): `_intent.md` carries operator-authored prose about *why* the recurrence exists. Read by humans + LLMs; never parsed by the dispatcher.

### D4 — `tasks` DB table dissolves to a thin scheduling index (or is removed entirely)

Two paths under consideration; the migration phases pick one before lock:

**Path A (full removal)**: `tasks` table dropped via migration. Scheduler walks the filesystem (`/workspace/**/_*.yaml`, `/workspace/_shared/back-office.yaml`) every minute, parses recurrence declarations, computes `next_run_at` in-memory, fires due invocations. Pros: singular substrate (filesystem only). Cons: filesystem walk per minute scales poorly with workspace count; needs index materialization.

**Path B (thin scheduling index)**: `tasks` table reduced to `(user_id, declaration_path, slug, next_run_at, last_run_at, paused)` — five columns, all derivative of filesystem state. Scheduler queries the table for `WHERE next_run_at <= now() AND NOT paused`; on every recurrence-declaration write, the index is updated as a side-effect of `UpdateContext` writing the `.yaml`. Pros: efficient at scale. Cons: maintains two substrates (filesystem authoritative; table derivative).

Path B is the working assumption for Phase 1 because it preserves scheduler performance without compromising filesystem-as-truth (the table is invalidatable from filesystem at any time). Path A is a future migration once filesystem walking is acceptable at scale.

Either way, the following columns/concepts dissolve from the current `tasks` table: `title`, `type_key`, `mode`, `output_kind`, `schedule` (moves to filesystem), `delivery` (already in TASK.md → moves to recurrence yaml), `essential` (per ADR-161, dissolves with the daily-update reframing in D6).

### D5 — `ManageTask` primitive dissolves; replaced by narrowed surface

The current `ManageTask` primitive carries 9 actions (create / trigger / update / pause / resume / archive / evaluate / steer / complete). Post-D5 surface:

| Old action | Replaced by | Notes |
|---|---|---|
| `create` (with schedule) | `UpdateContext(target=...)` writing recurrence `.yaml` | Recurrence creation is a substrate-write, not a privileged primitive |
| `create` (without schedule, one-shot) | Direct invocation firing via TP's normal tool surface | One-shot work is just an invocation; no creation step |
| `trigger` | `FireInvocation(declaration_path)` (new lightweight primitive) | Manual fire of a recurrence declaration |
| `update` (schedule/cadence change) | `UpdateContext(target=...)` editing recurrence `.yaml` | Frontmatter edit |
| `pause` / `resume` | `UpdateContext(target=...)` flipping `paused: bool` | Frontmatter edit |
| `archive` | `UpdateContext(target=...)` deleting the `.yaml` (or moving to `_archive/`) | Filesystem operation |
| `evaluate` | (deferred to ADR-232 Path B per prior agent-reframing audit) | Currently mechanical; persona-shaped evaluation deferred |
| `steer` | `UpdateContext(target=...)` editing `_intent.md` or `_steering.md` adjacent to declaration | Frontmatter/prose edit |
| `complete` (goal-mode) | Filesystem operation: archive declaration on completion event | No special primitive |

Net surface reduction: **`ManageTask` deleted entirely**. Replaced by one new primitive (`FireInvocation`) and existing `UpdateContext`. `UpdateContext` already exists per ADR-207 + ADR-216; this ADR widens its targets to include recurrence-declaration paths.

### D6 — Daily-update reframing: workspace narrative root, not essential task

ADR-161 introduced `daily-update` as an essential anchor task with a hard-coded `essential: true` flag preventing archive/auto-pause. Under this ADR, daily-update becomes:

- A recurrence declaration at `/workspace/_shared/daily-update.yaml`
- Output to `/workspace/reports/daily-update/{date}/output.html` (per the ADR-228 four-face cockpit pulling from this path)
- Empty-state template logic (zero-LLM fallback per ADR-161) preserved as a special case in the dispatcher
- The `essential: true` flag dissolves; if the operator deletes the recurrence declaration, daily-update stops firing (the cockpit's empty-state surface handles the absence gracefully)

This sharpens the Axiom 9 framing: daily-update is a *heartbeat-pulsed periodic invocation* with a recurrence wrapper, not a special category of task. The cockpit-as-operation framing (ADR-228) already treats it as one piece of substrate among others; this ADR removes the special-case scaffolding.

### D7 — `/work` surface = filter-over-narrative + recurrence-list view

`/work` ratifies its ADR-219-defined shape: it is *not* a tasks-table query. It is the narrative filtered by recurrence-declaration slug, plus a sidebar listing all active recurrence declarations (for pause/resume/inspection). Concrete reshape:

- **List mode**: walks `/workspace/**/_*.yaml` (or queries the thin scheduling index from D4 Path B) for active recurrence declarations. Groups by shape (Reports / Trackers / Actions / Maintenance) per ADR-167 v2 list-mode kind filtering.
- **Detail mode**: for a selected declaration, shows narrative entries filtered by that declaration's slug + the latest output (if `produces_deliverable` shape) + edit affordances for the `.yaml`.
- **Inline action history**: a separate filter on `/work` lists narrative entries with no task slug (one-shot invocations). Operator can graduate any of these to a recurrence declaration via a "graduate to recurring" affordance.

The frontend rewrite is contained: the data source changes, the URL structure stays.

### D8 — Operator vocabulary: shape-specific, not "task"-flat

Surface labels stop calling all four shapes "task":

- `produces_deliverable` recurrences → **Reports** (or Briefings, Updates — operator-named)
- `accumulates_context` recurrences → **Trackers** (or Watches, Domains)
- `external_action` recurrences → **Actions** (or Integrations, Write-backs)
- `system_maintenance` recurrences → **System** (or Maintenance — generally hidden from operator surface)

Code-level naming (the `output_kind` enum, registry key) dissolves entirely per D2 — shape is implied by substrate location. Frontend labels speak the operator vocabulary.

### D9 — Working-scratch convention is per-declaration, not per-Agent (2026-04-29 amendment)

Mid-invocation ephemeral state — the kind that today lives at `/tasks/{slug}/working/` per ADR-127 — is *invocation-scoped*, not Agent-scoped. Multiple invocations of the same Agent against different recurrence declarations should not share scratch space. The convention:

- **Working scratch path**: `<declaration_dir>/working/` adjacent to the recurrence YAML.
  - Deliverables: `/workspace/reports/{slug}/working/`
  - Accumulation: `/workspace/context/{domain}/working/{recurrence-slug}/` (sub-keyed by recurrence slug because multiple recurrences share the domain dir)
  - Action: `/workspace/operations/{slug}/working/`
  - Maintenance: `/workspace/_shared/working/{back-office-slug}/`
- **TTL**: 24h (preserved from ADR-127). The unified scheduler's ephemeral-cleanup job (per ADR-164) is extended to walk these new locations.
- **Not Agent-scoped**: `/agents/{slug}/working/` is *not* canonical for invocation scratch. `/agents/{slug}/` carries cross-firing memory only (style, accumulated thesis, learned preferences per ADR-117). Agents that need invocation-local scratch use the declaration-adjacent path.

Rationale: a custom Agent that's assigned to multiple recurrence declarations (e.g., one researcher Agent driving both `competitors-weekly-scan` and `market-monthly-scan`) needs separate scratch per firing. Per-Agent scratch would conflate the two streams.

### D10 — Run-log discipline: declaration-scoped vs Agent-scoped (2026-04-29 amendment)

Two distinct execution-history substrates, each with a fixed scope:

- **Declaration `_run_log.md`** = the canonical execution history *for this recurrence*. Lives adjacent to the YAML declaration. Append-only, every firing leaves an entry. Operator reads to see "what happened on this report's last 5 runs." ADR-209 attribution carries who fired (System / TP / Reviewer / custom Agent).
- **Agent `/agents/{slug}/memory/*.md`** = cross-firing learning *for this Agent identity*. Style distillation (per ADR-117), accumulated thesis (per ADR-106), learned preferences. Updated by the Agent itself across firings. **Not** a run log — only durable cognitive shifts land here.

Operator-facing question routing:
- "What did this report's last 3 runs do?" → declaration's `_run_log.md`
- "How is this Agent's reasoning evolving over time?" → Agent's `/agents/{slug}/memory/`
- "Show me everything Agent X did this week" → narrative filtered by `agent:<slug>` (per D11)

The discipline rule: **Agent code never writes to declaration-adjacent files for cross-firing-learning purposes; Agent code writes to its own `/agents/{slug}/` for that.** Declaration-adjacent files are append-only execution history + invocation-time feedback only.

### D11 — Per-Agent narrative filter affordance is universal (2026-04-29 amendment)

The narrative filter affordances (per ADR-219) extend to **all persona-bearing Agents equally** — TP/Reviewer (singleton-systemic) and operator-authored custom domain Agents. Specifically:

- `/chat` rendering: every narrative entry carries `metadata.author_agent_id` (or equivalent) per ADR-219 D1. Frontend filter chip "this Agent only" works for any Agent slug.
- `/agents/{slug}` detail view: narrative filtered by that Agent's slug — operator sees "what has this Agent been doing." Same affordance for systemic and custom.
- Aggregation: digest rendering (per ADR-221 narrative-digest) groups by Identity equally — `agent:<custom-slug>` is a peer Identity to `reviewer:<…>`.

No special-cased rendering for systemic vs custom Agents at the narrative layer. The Identity field is opaque to the renderer; only the rendering weight (material/routine/housekeeping per ADR-219 D2) drives visual treatment.

### D12 — Per-declaration cost ceiling (2026-04-29 amendment)

Recurrence declarations may carry an optional `max_balance_cents:` field bounding LLM spend per firing or per period. This is finer-grained than workspace-level autonomy ceiling (per ADR-217) — it caps a specific recurring stream so a misconfigured Agent or runaway loop doesn't drain workspace balance.

Two shapes:

```yaml
recurring:
  schedule: "0 9 * * 1"
  max_balance_cents_per_firing: 50    # cap per single invocation
  # OR
  max_balance_cents_per_week: 500     # cap aggregate over a rolling window
```

Enforcement: the dispatcher checks token-usage forecasts against the cap before firing. If forecast exceeds cap, the firing is skipped + a `system:cost-gate` narrative entry surfaces with an actionable message ("Agent X recurrence Y skipped: would exceed declared per-firing budget. Edit `_recurring.yaml` to raise the cap or reduce `context_reads`."). Operator can then steer.

This decision is **deferred to a follow-on commit** (post-atomic-cutover). The schema is reserved here; the enforcement plumbing lands once the dispatcher exists. Workspace-level autonomy ceiling (per ADR-217) provides the global safety net in the interim.

---

## Implementation Phases

This ADR ratifies architecture only. Implementation is multi-phase to preserve green state per Singular Implementation rule 1 (no parallel paths during migration). Each phase lands in a green build with passing tests.

### Phase 1 — TP behavioral inversion (no schema changes, low risk)

**Scope**: Rewrite `yarnnn_prompts/` to encode invocation-first default per D1. `ManageTask(create)` prompt-level guidance narrowed: "Use only when recurrence is explicitly intended." TP defaults to firing invocations and writing files for one-off work.

**LOC estimate**: ~400 (prompt rewrites + CHANGELOG).

**Risk**: Low. No schema/code changes; behavioral shift via prompt only. Reversible via prompt rollback.

**Validation**: Three operator scenarios from prior discourse (alpha-trader adds daily market scan; operator with no mandate requests one-off teardown; operator pauses recurring report for 2 weeks) — all should pass without TP creating spurious tasks.

### Phase 2 — Format-by-shape principle ratified; new YAML recurrence shapes accepted

**Scope**: Dispatcher (currently `task_pipeline.py`, will rename to `invocation_dispatcher.py` in Phase 3) gains the ability to read `.yaml` recurrence declarations as a parallel input alongside existing `tasks` table. New writes go to YAML; existing `tasks` rows continue to fire. **This is the only phase with parallel paths permitted** — Phase 3 removes the old path entirely. Phase 2 exists to validate the new YAML shape against real workloads before commit-to-cutover.

**LOC estimate**: ~600 (YAML parser, dispatcher dual-source, format docs).

**Risk**: Medium. Permits dual-source temporarily — must be sharply time-bounded (Phase 2 lands and Phase 3 lands within the same week).

**Validation**: Test gate that all four shapes (deliverable, tracker, action, maintenance) execute correctly from YAML declarations. Green-state requirement.

### Phase 3 — `tasks` table cutover; old path deletion

**Scope**: Migrate all existing `tasks` rows (alpha-trader bundle reference-workspace, kvk's workspace, any test data) into recurrence-declaration `.yaml` files at natural-home locations. Drop the heavy columns (`title`, `type_key`, `mode`, `output_kind`, `delivery`, `schedule`) per D4. Either drop the table entirely (Path A) or shrink to thin scheduling index (Path B). `task_pipeline.py` rewritten as `invocation_dispatcher.py` (~200 LOC vs current 4,204 LOC). `ManageTask` primitive deleted; `FireInvocation` added; `UpdateContext` targets widened to recurrence declarations.

**LOC estimate**: ~3,000 deletions (task_pipeline.py shrinkage + manage_task.py deletion + task_workspace.py deletion + task_types.py deletion + task_derivation.py rewrite) + ~500 additions (invocation_dispatcher.py + FireInvocation primitive + recurrence parser + migration script).

**Risk**: High. Largest single commit window. Requires comprehensive test coverage before cutover. Migration script must be idempotent and reversible.

**Validation**: All recurrence declarations fire correctly. All existing `/tasks/{slug}/` filesystem trees migrated to natural-home substrate. Test gate: zero references to `tasks` table reads outside the thin scheduling index (or zero references at all under Path A).

### Phase 4 — Frontend reshape

**Scope**: `/work` surface rewritten per D7 — filter-over-narrative + recurrence-list. `/api/tasks/*` routes deleted; replaced by `/api/recurring` walker. Operator vocabulary updated per D8. ManageTaskModal dies; new RecurrenceModal scaffolds shape-specific affordances.

**LOC estimate**: ~800 frontend (component rewrites) + ~300 backend (route changes).

**Risk**: Medium. Frontend-only after Phase 3 completes; behavioral parity must be tested against operator scenarios.

**Validation**: Operator can author, edit, pause, resume, archive recurrence declarations from `/work`. Inline-action history visible. Graduation affordance ("graduate to recurring") functional.

### Phase 5 — Documentation + ADR amendments

**Scope**: Update CLAUDE.md, FOUNDATIONS.md (Axiom 9 implementation status flipped to Implemented), GLOSSARY.md, SERVICE-MODEL.md. Apply amendment banners to ADRs 138, 149, 161, 166, 167. Update prompt CHANGELOG. Final grep gate ensuring no live-code references to deleted symbols.

**LOC estimate**: ~500 (docs).

**Risk**: Low.

**Validation**: Grep gate passes.

---

## Operator Scenario Validation

All three scenarios stress-tested during discourse (2026-04-28); recorded here as ADR validation evidence.

### Scenario 1: alpha-trader operator adds a daily market scan

Operator chats: *"TP, add a daily market scan covering S&P sectors."*

Expected flow:
1. TP checks `/workspace/context/market/` — exists or creates the domain folder.
2. TP writes `/workspace/context/market/_recurring.yaml` (or appends to existing) via `UpdateContext`:
   ```yaml
   recurrences:
     - slug: market-scan-daily
       schedule: "0 7 * * *"
       agent: researcher
       objective: "Daily S&P sector pricing + news sweep"
       paused: false
   ```
3. Optional: TP updates `_domain.md` prose noting "Daily scan added 2026-04-28" via `UpdateContext`.
4. Narrative entry: *"TP added market-scan-daily recurrence to /workspace/context/market/_recurring.yaml"* (Identity: `yarnnn`, weight: routine).
5. Scheduler picks up the new declaration on next minute; fires per cron starting next 07:00.

**Verdict**: clean. No `tasks` row created. No `/tasks/{slug}/` filesystem. No `ManageTask(create)` invocation. Single `UpdateContext` write + narrative emission.

### Scenario 2: operator with no mandate wants a one-off competitive teardown

Operator chats: *"TP, give me a competitive teardown of [Company X]."*

Expected flow:
1. TP fires invocation directly (single Sonnet call with tool-use rounds): gathers public info, drafts teardown.
2. Output written to `/workspace/reports/teardown-company-x-2026-04-28.md` (operator can specify path or accept default).
3. Narrative entry: *"TP produced teardown of Company X at /workspace/reports/teardown-company-x-2026-04-28.md"* (Identity: `yarnnn`, weight: material).
4. Operator reads, gives feedback in chat → TP writes feedback to `/workspace/reports/_feedback.md` adjacent.

**Verdict**: clean. No task wrapper. Pure invocation. Closer to Claude Code's mental model than current YARNNN. Mandate-not-authored is fine; no MANDATE.md gate triggers because no recurrence is being created.

### Scenario 3: operator pauses a recurring report for 2 weeks

Operator chats: *"TP, pause my weekly market report for 2 weeks."*

Expected flow:
1. TP locates the recurrence declaration at `/workspace/reports/market-weekly/_spec.yaml`.
2. TP edits via `UpdateContext`:
   ```yaml
   report:
     recurring:
       paused: true
       paused_until: "2026-05-12"  # operator-derived
   ```
3. ADR-209 captures the revision with `authored_by: yarnnn:sonnet-v6` + message *"Paused weekly market report until 2026-05-12 per operator request"*.
4. Scheduler sees `paused: true` and skips this declaration.
5. Narrative entry: *"TP paused market-weekly until 2026-05-12"* (Identity: `yarnnn`, weight: routine).
6. On 2026-05-12, scheduler resumes (operator can also un-pause manually via chat or frontend).

**Verdict**: clean. No `ManageTask(action="pause")` primitive needed. Frontmatter edit + scheduler respect.

All three scenarios validate the architecture. None require the heavyweight task abstraction.

---

## What dissolves vs what survives

### Dissolves

- `tasks` DB table heavy columns (Path B) or entire table (Path A)
- `/tasks/{slug}/` filesystem tree
- `task_pipeline.py` (4,204 LOC → ~200 LOC `invocation_dispatcher.py`)
- `task_workspace.py` (319 LOC, deleted)
- `task_types.py` (1,836 LOC, deleted — ADR-207 P4b already dissolved its dispatch authority; this ADR finishes the deletion)
- `task_derivation.py` (334 LOC, rewritten to walk recurrence declarations)
- `ManageTask` primitive (1,498 LOC in `manage_task.py`, deleted)
- `output_kind` enum (4-value classification dies; shape implied by location)
- `mode` field on `tasks` table (synced with TASK.md per ADR-178; both die)
- `essential` field on `tasks` table (ADR-161 reframing per D6)
- `/api/tasks/*` routes (1,578 LOC in `routes/tasks.py`, replaced by ~200 LOC `routes/recurring.py` walker)
- `TASK.md` + `DELIVERABLE.md` as separate files at task scope (collapse into recurrence-declaration `.yaml` + optional `_intent.md` prose)

**Total dissolution**: ~9,800 LOC across 7 files; ~700 LOC additions (new dispatcher, new primitives, migration script, frontend reshape). Net deletion: ~9,100 LOC.

### Survives

- All ADR-209 substrate machinery (authored revisions, content-addressed blobs, parent-pointer history)
- `unified_scheduler.py` (510 LOC, sharply simplified to ~250 LOC)
- Compose engine (ADR-213) — unchanged, just consumed by `produce-report` invocations directly
- Reviewer dispatch chain (ADR-194 v2) — entirely unchanged
- Mandate (ADR-207) — central; recurrence declarations fire under mandate context
- Domains (ADR-151/152) — central; recurrence declarations live alongside domain substrate
- Narrative as universal log (ADR-219) — every recurrence-declaration firing emits a narrative entry per the existing single write path
- Bundle reference-workspaces (ADR-222/223/224/226) — bundles ship recurrence declarations in their reference-workspace alongside other substrate
- Persona/program registry (ADR-230) — operates cleanly atop this substrate change
- Capability gating (ADR-207 P3) — `required_capabilities` declared in recurrence YAML, gate enforced at dispatch
- Authored substrate attribution (ADR-209) — every recurrence-yaml write is attributed

---

## Open Questions

1. **Path A vs Path B for `tasks` table**: full removal vs thin scheduling index. Locking decision deferred to Phase 3 commit; depends on filesystem-walk performance at expected workspace counts. Working assumption: Path B (thin index) for Phase 3, with Path A as a follow-on once the index is small enough to query negligibly.

2. **Goal-mode work without recurrence**: a one-shot deliverable with iteration ("draft me a board deck for Tuesday; I'll give feedback over 3 cycles") doesn't fit pure recurrence framing. Working assumption: this is *still* an inline action with iterative narrative entries; the operator's feedback writes adjacent `_feedback.md`; no recurrence-declaration wrapper. If the iteration becomes a stable pattern (operator does this monthly), it graduates to a monthly recurrence. Open question: does goal-mode need its own affordance (a "track this iteration as a goal" graduation primitive) or does inline-with-feedback handle it cleanly? Phase 4 frontend work tests this.

3. **Migration of existing TASK.md content**: alpha-trader bundle reference-workspace ships TASK.md files per ADR-223. These migrate to `_recurring.yaml` + `_intent.md` shapes per D3. Bundle versioning (ADR-223 schema) does not bump because this is a content-format change not a schema change. Migration script for kvk's workspace + any test workspaces required in Phase 3.

4. **Inline action narrative weight**: ADR-219 distinguishes material / routine / housekeeping. One-off invocations producing files are typically material; one-off invocations that just answer a question (no file written) are typically routine. Default policy needs ratification. Working assumption: file-producing → material; chat-only → routine; backed-by-recurrence → routine (already labeled).

5. **Feedback file consolidation per natural home**: per-domain feedback already exists (ADR-181 + audit recommendation). Per-report feedback (`/workspace/reports/{slug}/_feedback.md`) is new under D2. Open question: do reports need *per-report* feedback or is a workspace-level `/workspace/reports/_feedback.md` sufficient for low-volume operators? Working assumption: per-report for any recurring report; workspace-level for one-off reports. Tested in Phase 4.

6. **ADR-219 narrative entry shape interaction**: ADR-219 D1 widened `session_messages` role enum to include `agent` and `external`. Recurrence-declaration firings under this ADR carry `task_slug` in `metadata` per ADR-219. No further schema change needed. Open question: does the narrative entry shape need a new field for "recurrence declaration path" (vs current `task_slug`)? Working assumption: no — `task_slug` becomes "recurrence declaration slug" in vocabulary; storage shape unchanged.

7. **Dual-source phase boundary**: Phase 2 permits dual-source dispatch (tasks table + YAML declarations) for validation. Singular Implementation rule 1 forbids parallel approaches; Phase 2 violates this temporarily. Hard time-bound: Phase 2 lands and Phase 3 lands in the same week (or Phase 2 reverts). Open question: is the dual-source phase actually necessary, or can Phase 2 + 3 be a single atomic commit? Working assumption: atomic if test surface permits; staged otherwise.

---

## Relationship to existing canon

### Supersedes

- **ADR-138** (Agents as Work Units, 2026-04-XX) — the "tasks-as-work-units" framing dissolves. Agents survive as Identity layer per Axiom 2; work units dissolve into invocations per Axiom 9. ADR-138's contribution to making projects→tasks→agents the canonical hierarchy is preserved structurally (workspace → agents → invocations); the unit terminology shifts to invocations.
- **ADR-149** (Task Lifecycle Architecture, 2026-04-XX) — most lifecycle actions dissolve into substrate operations per D5. DELIVERABLE.md survives only as part of `produces_deliverable` recurrence declarations (collapsed into `_spec.yaml`).
- **ADR-161** (Daily Update Anchor, 2026-04-XX) — essential-task framing dissolves per D6. Daily-update becomes a recurrence declaration; empty-state template logic preserved as dispatcher special-case.
- **ADR-166** (Registry Coherence — output_kind 4-value enum) — enum dissolves; shape implied by substrate location. The four-shape *concept* (deliverable/context/action/maintenance) survives as operator vocabulary (D8); the *enum classification* dies.
- **ADR-167 v2** (List/Detail Surfaces) — `/work` data source re-articulated as filter-over-narrative + recurrence-list per D7. URL structure preserved per ADR-219 commitment.

### Amends

- **ADR-207** (Primary-Action-Centric Workflow) — Mandate hard gate preserved; capability gating preserved; TASK_TYPES registry sunset is *finished* under D5 (delete `task_types.py` entirely). Bundle reference-workspaces still ship "what to scaffold" but as `.yaml` recurrence declarations rather than TASK.md files.
- **ADR-195 v2** (Money-Truth Substrate) — `back-office-outcome-reconciliation` task becomes an entry in `/workspace/_shared/back-office.yaml` per D3. Substrate semantics (`_performance.md` per domain, ledger format, idempotency) entirely unchanged.
- **ADR-209** (Authored Substrate) — every recurrence-declaration `.yaml` write is attributed via existing `write_revision` plumbing. No new attribution work.
- **ADR-219** (Invocation/Narrative Implementation) — ADR-219 explicitly preserved task schema "for now"; this ADR finishes the implementation by dissolving the schema. The narrative substrate, single write path, and weight gradient ratified by ADR-219 are entirely preserved.

### Preserves

- FOUNDATIONS v6.8 axioms 1–8 unchanged
- ADR-141 (execution mechanism layers — invocation is one cycle through them)
- ADR-194 v2 (Reviewer substrate at `/workspace/review/` — entirely untouched)
- ADR-205 (chat-first triggering, run-now-default — *now becomes the genuine default* rather than the practiced exception)
- ADR-216 (orchestration vs judgment — chat surface is plumbing per ADR-231 reframing companion ADR-232; this ADR makes the chat surface's invocation-firing behavior cleaner without changing the chat surface's classification)
- ADR-222 (OS framing — kernel boundary preserved; bundles unchanged)
- ADR-225 (compositor layer — operates on recurrence declarations and natural-home substrate without modification)
- ADR-226 (reference-workspace activation — bundle fork operation unchanged; bundle template content shifts from TASK.md to recurrence YAML in Phase 3)
- ADR-228 (cockpit-as-operation — cockpit faces read from natural-home substrate per ADR-228's existing design; no change required)
- ADR-229 (judgment-first dispatch — Reviewer's reactive pulse on proposals entirely unchanged)
- ADR-230 (persona/program registry unification — bundles ship recurrence declarations under the unified registry)

### Downstream ADR (already discoursed; not yet drafted)

**ADR-232 (proposed): YARNNN Surface/Seat Reframing — Chat as Plumbing, Reviewer Renamed.** A separate architectural ADR finishes the agent-reframing work that was deferred from this session's earlier discourse. ADR-232 lands cleanly atop ADR-231's substrate work because (a) it's primarily about persona/surface naming, not work substrate, and (b) the renamed Thinking Partner (formerly Reviewer) reasons against a substrate that's been simplified by ADR-231 (no more `/tasks/{slug}/` to walk; recurrence declarations and natural-home outputs are easier to reason against).

---

## Verification gates

Each phase ships with a test gate. Gates:

- **Phase 1 gate**: TP prompt rewrite passes operator-scenario walkthroughs (3 scenarios above) without spurious task creation. Manual review against alpha-trader E2E expected behavior.
- **Phase 2 gate**: dispatcher reads YAML declarations correctly; all four shapes execute end-to-end from YAML; existing `tasks` table rows continue to fire (dual-source).
- **Phase 3 gate**: zero live-code references to `task_pipeline.execute_task`, `ManageTask`, `task_types.TASK_TYPES`, `task_workspace.*`. Migration script idempotent. All operator scenarios pass under the new dispatcher only.
- **Phase 4 gate**: frontend renders `/work` from new data source; pause/resume/archive affordances functional; inline-to-recurrence graduation affordance functional.
- **Phase 5 gate**: grep gate passes; CLAUDE.md / FOUNDATIONS / GLOSSARY / SERVICE-MODEL / ADR amendments all reference the post-ADR-231 vocabulary.

---

## Strategic note (recorded for posterity, not architectural commitment)

This ADR is architectural. The GTM positioning conversation is separate and ongoing (per content/STRATEGY.md and recent alpha bundle work). The architecture supports two distinct narratives:

- **Mandate-driven autonomous operations**: operator authors MANDATE.md; TP runs the operation under operator's standing intent and Reviewer's principles. Cockpit speaks operation-vocabulary. This is the alpha-trader bundle's framing.
- **Persistent Claude Code**: operator chats; TP fires invocations immediately; outputs land in filesystem; recurrence is opt-in via explicit operator request. No mandate required.

Both modes run on the same Path Y architecture. The mandate is *optional but powerful when authored*. The choice of GTM lead — operations-first or chat-first — is a positioning decision, not an architectural one. ADR-231 makes that flexibility structural.

The competitive moat against incumbent LLM providers is filesystem-native persistence + persona-bearing judgment seat (Reviewer) + mandate-driven autonomous execution under operator-authored standing intent. None of these are in the LLM providers' surface area; all of them survive this ADR. The task abstraction was an Era 1 artifact (when YARNNN was framed as agent framework with recurring autonomous work — a tasks-as-service framing competing with LLM providers on similar-but-better terms). Era 2 (operations-as-service per ADR-207, ADR-222 OS framing, ADR-228 cockpit-as-operation) is the defensible position; this ADR finishes the substrate migration into Era 2.

---

## Revision History

| Date | Version | Change |
|---|---|---|
| 2026-04-28 | 1.0 | Initial Proposed status. Ratifies invocation-first default, recurrence declarations as natural-home YAML, task abstraction sunset, format-by-shape principle. Phased implementation deferred. |
| 2026-04-29 | 1.1 | Added D9 (per-declaration working-scratch convention), D10 (run-log discipline — declaration-scoped vs Agent-scoped), D11 (per-Agent narrative filter affordance is universal — systemic + custom), D12 (per-declaration cost ceiling, schema reserved, enforcement deferred). All four amendments resolve multi-agent autonomy concerns surfaced during the architectural-discourse audit before atomic cutover. |
| 2026-04-29 | 1.2 | **Phase 3.2.a Implemented**: `api/services/recurrence_paths.py` ships path-resolution layer mapping `RecurrenceDeclaration → natural-home substrate paths` per D2/D9/D10. Pure-function module: `resolve_substrate_root`, `resolve_output_path` (DELIVERABLE only — others raise/return audit-log), `resolve_output_folder`, `resolve_run_log_path`, `resolve_feedback_path`, `resolve_intent_path`, `resolve_steering_path`, `resolve_working_scratch_path`, `resolve_paths` aggregate with `ResolvedPaths` dataclass. Test gate `api/test_adr231_recurrence.py` extended to 58/58 — 32 new path-resolution tests covering all 4 shapes × every path kind. Phase 3.2.a is the substrate-mapping foundation for Phase 3.2.b's dispatcher rewrite (next session): every `tw.read(...)`/`tw.write(...)` call site in the dispatcher resolves through this module rather than slug-rooted I/O. **Phase 3.2.b queued**: dispatcher YAML-native body deferred to a fresh-context session so the 800-LOC port from `task_pipeline.execute_task` lands clean. Per the cutover plan at `docs/analysis/adr-231-phase-3-cutover-plan-2026-04-29.md`. |
| 2026-04-29 | 1.7 | **Phase 3.6.a.1 Implemented**: `api/routes/tasks.py` `POST /api/tasks/{slug}/run` migrated. The single direct `task_pipeline.execute_task` call site in this file now routes through `walk_workspace_recurrences` → `services.invocation_dispatcher.dispatch(decl)`. `TaskRunTriggered` response shape preserved for the frontend. 404 with migration-script hint when slug doesn't resolve. 85/85 still green. **Status of remaining 3.6 sub-phases (queued, full-context next session)**: 3.6.a.2 (routes/agents.py + trigger_dispatch.py — walk recurrences for agent assignment), 3.6.a.3 (routes/{chat,workspace,system,account,integrations}.py — read-side migrations), 3.6.a.4 (mcp_server/server.py), 3.6.b.1–b.4 (service layer: trigger_dispatch + delivery + compose + agent_creation + working_memory + mcp_composition + repurpose + update_context cleanup), 3.6.c.1 (alpha_ops scripts). After 3.6 completes, Phase 3.7 atomic deletion of ~9,800 LOC across `task_pipeline.py` + `manage_task.py` + `task_workspace.py` + `task_types.py` + `task_derivation.py`. Then 3.8 (frontend full rename `/api/tasks` → `/api/recurrences`, `Task` → `Recurrence`) + 3.9 (ADR amendments, CLAUDE.md sync, final grep gate). |
| 2026-04-29 | 1.6 | **Phase 3.5 Implemented**: data migration script `api/scripts/migrate_to_recurrence_declarations.py` ships + applied live. Migrated **19/19 active task rows** across alpha-trader (10) + alpha-trader-2 (9) into 12 YAML declarations at natural-home locations: 8 single-decl files (DELIVERABLE `_spec.yaml` × 6, ACTION `_action.yaml` × 2), 2 multi-decl `/workspace/context/trading/_recurring.yaml` (one per persona, each with 2 ACCUMULATION entries), 2 `/workspace/_shared/back-office.yaml` (4 entries each — outcome-reconciliation, reviewer-reflection, reviewer-calibration, proposal-cleanup). Every YAML write attributed via ADR-209 `write_revision` with `authored_by="system:adr-231-migration"`. `tasks.declaration_path` populated for every active row. Script supports `--dry-run` (default), `--apply`, `--archive-legacy` flags. Idempotent + reversible (every revision retained per ADR-209). Final step per user: `materialize_scheduling_index` sweep. Smoke verification: `psql` confirms all 19 rows carry the expected natural-home `declaration_path`. Per cutover plan §3.5. The legacy `/tasks/{slug}/TASK.md` files **survive** — `--archive-legacy` not applied yet because Phase 3.6 caller migrations still read them; the archive flag will be applied as part of 3.7 atomic deletion. |
| 2026-04-29 | 1.5 | **Phase 3.4 Implemented**: migration 164 applied to production DB. `tasks` table is now formally the thin scheduling index per ADR-231 D4 Path B. Schema changes: `DROP COLUMN mode` (was added by 132), `DROP COLUMN essential` (was added by 141), `ADD COLUMN declaration_path TEXT`, `ADD COLUMN paused BOOLEAN NOT NULL DEFAULT FALSE`. `tasks_status_check` tightened to `(active|completed|archived)` — `paused` enum value migrated to the explicit `paused` flag. `idx_tasks_next_run` refreshed with the `paused = false` filter. Table COMMENT documents Path B intent. Same-commit caller patch in `api/routes/tasks.py`: `update_task` maps `request.status="paused"` → `paused=true, status='active'` (the API surface accepts paused as a status string until 3.8 frontend rename); essential-task archive guard removed (per D6, daily-update is no longer essential-flagged — operator-deletes-YAML stops the recurrence). 85/85 still green. `docs/database/MIGRATIONS.md` extended with the 164 entry. Singular Implementation: legacy columns are gone, no parallel mode/essential paths survive in the DB layer; routes/tasks.py paused-handling is a one-spot mapping from the legacy API surface to the new flag (tightens further in 3.8 when the frontend stops sending status="paused"). |
| 2026-04-29 | 1.4 | **Phase 3.3 Implemented**: scheduler walks recurrence YAML declarations. New `api/services/scheduling.py` (~270 LOC) — `compute_next_run_at(decl, last_run_at, now)` (paused/paused_until aware), `materialize_scheduling_index(client, user_id)` (filesystem→tasks index sync, idempotent, drops stale rows), `get_due_declarations(client, now)` (returns parsed declarations for due index rows; YAML is truth, table is index), `claim_task_run` (CAS atomic claim against `tasks.next_run_at`), `record_task_run` (post-dispatch index update). `api/jobs/unified_scheduler.py` rewritten (510 → 270 LOC): `get_due_tasks` + `execute_due_tasks` DELETED; new `dispatch_due_invocations` walks YAML declarations and routes through `services.invocation_dispatcher.dispatch(decl)`. CAS guard preserved. `api/services/primitives/update_context.py` `_handle_recurrence` post-write hook calls `materialize_scheduling_index` so the index stays current after every YAML edit (best-effort; index is reconstructable from filesystem). **Bug fix in same commit**: `services.schedule_utils._calculate_from_dict` previously imported `calculate_next_pulse_from_schedule` from `jobs.unified_scheduler` — circular layering (services depending on jobs). Inlined the body into `schedule_utils` (its proper home — pure timing math, no scheduler dependency). Per discipline rule 10 (architectural fit). 85/85 passing in `api/test_adr231_recurrence.py` (8 new scheduling tests covering paused / paused_until / no-schedule / active-schedule / CAS-success / CAS-fail / CAS-no-baseline). Singular Implementation honored: legacy slug-keyed dispatch path is gone from the scheduler — only the new YAML-walker path exists. |
| 2026-04-29 | 1.3 | **Phase 3.2.b Implemented**: `api/services/invocation_dispatcher.py` body fully rewritten. The Phase 2 thin adapter (slug-based delegation to `task_pipeline.execute_task`) is replaced with a YAML-native pipeline that takes a `RecurrenceDeclaration` and routes by shape. Four dispatch branches: `_dispatch_generative` (DELIVERABLE + ACCUMULATION) — Sonnet generation, natural-home output substrate, agent-attributed writes via `services.authored_substrate.write_revision`; `_dispatch_action` — delegates to generative (platform write IS the work); `_dispatch_maintenance` — dotted-path `executor:` invocation, appends to shared `/workspace/_shared/back-office-audit.md` per D2 (audit log doubles as run log per D10). Empty-state branches (ADR-161 daily-update, ADR-204 maintain-overview) preserved as inline keyed cases. **Chat-as-layer posture hardened**: every invocation emits exactly one narrative entry per ADR-219 with shape-aware Identity (`role='agent'` for persona work, `role='system'` for dispatcher / cost-gate / failure / back-office). Provenance entries link operator-clickable substrate paths. Capability gate (ADR-207 P3) + balance gate (ADR-172) at dispatch entry — narrative surfaces skip reason. `services.recurrence_paths.resolve_paths(decl)` from 3.2.a drives every path. `UserMemory.write` (which routes through ADR-209) is the substrate-write primitive — no slug-rooted `TaskWorkspace` calls in the dispatcher. Test gate extended to 77/77 (19 new dispatcher pure-helper tests on top of 58). **What survives**: ADR-209 attribution, ADR-219 narrative single write path, ADR-194 v2 Reviewer chain, ADR-228 cockpit, ADR-141 layers. **What's deferred to 3.6.b**: section partials + sys_manifest, `_post_run_domain_scan` (awareness.md), prior-output / revision-scope injection — all currently slug-rooted, reshape to natural-home paths when compose/assembly callers migrate. Singular Implementation honored at the call-site boundary: `FireInvocation` routes exclusively through the new dispatcher; legacy `task_pipeline.execute_task` survives only for not-yet-migrated routes (deletion in 3.7). |
