# ADR-231 Runtime Context Plan

> **Status**: Planning artifact (not an ADR). Companion to ADR-231 v1.1. Read before Phase 3.3-3.9 caller migrations + frontend reshape + final grep gate.
> **Date**: 2026-04-29 (v1.1 revision: explicit (trigger-class × shape) axiomatic grouping + execution-session handoff section)
> **Authors**: KVK, Claude
> **Purpose**: Specify the runtime context, session, prompt assembly, and narrative-emission machinery that comes online once the task abstraction is dissolved. The atomic cutover changes the **substrate**; this doc specifies the **runtime layer** that operates on that substrate.

---

## Handoff to execution session — read this first

This section is the prescriptive checklist for the Claude Code session executing Phases 3.3-3.9 of the ADR-231 atomic cutover.

**Pre-execution reads (in order):**

1. `docs/adr/ADR-231-task-abstraction-sunset.md` — architectural decisions D1-D12 (the *what*)
2. **This doc** — runtime-layer specification (the *how* + per-strategy contracts)
3. `docs/architecture/invocation-and-narrative.md` — FOUNDATIONS Axiom 9 canon (preserved)
4. `docs/adr/ADR-219-invocation-narrative-implementation.md` — narrative emission canon (preserved)
5. `docs/adr/ADR-209-authored-substrate.md` — revision attribution (preserved; revision posture amendments per §9 below)
6. `docs/adr/ADR-159-layered-context-strategy.md` — compact index canon (extended; v2 spec per §4 below)
7. `docs/adr/ADR-186-yarnnn-prompt-profiles.md` — surface profiles (extended; mapping per §5 below)

**Phase-by-phase contracts (what each remaining commit must satisfy):**

| Phase | Contract source | Key invariants |
|---|---|---|
| 3.3 — Scheduler migration | §3 envelope tables; §8 narrative emission | Scheduler queries `walk_workspace_recurrences` not `tasks` table; due declarations dispatch via `invocation_dispatcher.dispatch`; cleanup walks new working-scratch paths (§6) |
| 3.4 — DB migration 159+ | §11 cross-shape invariants | Drop `tasks.{title, type_key, mode, output_kind, delivery, essential}`; add `tasks.declaration_path`; thin scheduling index only |
| 3.5 — Data migration script | §3 envelope tables (target paths) | Walk existing tasks rows + `/tasks/{slug}/TASK.md` → write YAML at natural homes per shape; idempotent; ADR-209 attributed (`authored_by: system:adr-231-migration`) |
| 3.6 — Caller migrations + compact index v2 | §4 compact-index spec; §5 surface profiles | `working_memory.format_compact_index` rewritten per §4 (recurrence-walker-keyed, ≤1500 token bound); `working_memory._format_entity_index` rewritten per §5 (5 entity sub-profiles); ~30 production callers migrated |
| 3.7 — Legacy file deletions | §11 invariant 10 | Final grep gate: zero live-code references to `task_pipeline`, `manage_task`, `task_workspace`, `task_types`, `task_derivation` |
| 3.8 — Frontend reshape | §5 surface profile mapping | `/api/tasks/*` → `/api/recurring/*`; `/work` surface filter-over-narrative + recurrence-list per ADR-231 D7 |
| 3.9 — ADR amendments + grep gate | §11 regression-test inventory | Supersede banners on ADR-138/149/161/166/167; FOUNDATIONS Axiom 9 status flip; `api/test_adr231_runtime_invariants.py` asserts all 10 cross-shape invariants |

**Prompt rewrites (Phase 3.6, dimension owned by execution session):**

The four prompt files in `api/agents/yarnnn_prompts/` need full rewrites per §5 + §7 + §9:
- `base.py` — vocabulary update (drop "tasks are work units"; reframe around recurrence declarations)
- `behaviors.py` — full rewrite; 18KB of task-era ManageTask/TASK.md guidance retired; replaced with declaration-shape-aware behaviors
- `entity.py` — split into 5 sub-profiles per shape (deliverable/accumulation/action/maintenance/agent), each with its own preamble
- `onboarding.py` — task-creation references replaced with recurrence-graduation flow per ADR-231 D1
- Update `api/prompts/CHANGELOG.md` per BEHAVIORAL ARTIFACTS discipline

**Stop conditions (where execution session should pause and discourse):**

- If §3 envelope token estimates exceed by >50% in real-workspace measurement → halt and consult before proceeding (signals a context-budget design issue)
- If any §11 invariant proves untestable → halt; the invariant is wrong, not the test
- If §10 cost-gate plumbing requires schema changes beyond the deferred enforcement scope → halt and discourse (D12 enforcement is post-cutover by design)

**Single source of truth**: this doc. ADR-231 is the architectural decision; this doc is the engineering specification. Don't add a parallel runtime spec elsewhere — amend this one.

---

## Axiomatic grouping (the load-bearing claim)

The architecturally-load-bearing classification for prompt strategy is **(trigger-class × shape)** — a 2-tuple that determines context envelope, read pattern, and narrative weight.

| Axis | Values | What it determines |
|---|---|---|
| **Trigger-class** | `addressed` (operator chats) / `scheduled` (cron-pulsed) / `reactive` (event-pulsed) / `heartbeat` (liveness ping) | When the invocation fires; therefore *what kind of context envelope* it needs |
| **Shape** | `deliverable` / `accumulation` / `action` / `maintenance` (per ADR-231 D8) | What the work produces; therefore *what substrate it reads + writes* |

**Why output-kind alone isn't enough**: the same shape (e.g., `deliverable`) needs fundamentally different prompt strategy when the operator is *chatting about* a recurring report vs when the *scheduler is firing* it. The first needs compact-index + 10-msg history + entity preamble; the second needs declaration + run-log + prior output. Output-kind alone collapses these into one strategy and gets the context envelope wrong.

**Why pulse-class alone isn't enough**: the same trigger-class (e.g., `scheduled`) needs different envelopes per shape — accumulation reads domain entity inventory, deliverable reads prior output, action reads action template. Pulse-class alone collapses these.

**The 2-tuple is the minimum sufficient grouping.** Ten cells, six distinct prompt strategies (the matrix below collapses some cells into shared strategies):

| Cell | Strategy | Profile/branch | Envelope summary |
|---|---|---|---|
| `addressed × workspace` | A | `workspace` profile | Compact index + 10-msg conversation history |
| `addressed × deliverable` | B | `entity:deliverable` | A + spec.yaml + recent run-log + last delivered output preview |
| `addressed × accumulation` | C | `entity:accumulation` | A + recurring entry + domain entity inventory snapshot |
| `addressed × action` | D | `entity:action` | A + action template + last 10 fires |
| `addressed × agent` (non-shape; entity is an Agent identity) | E | `entity:agent` | A + AGENT.md + recent narrative authored by this Agent |
| `addressed × reviewer` | F | `entity:reviewer` | A + review/IDENTITY.md + principles.md + last 5 decisions.md |
| `scheduled × deliverable` | G | dispatcher generative branch | declaration + intent + run-log + feedback (last 3) + steering + prior output + AGENT.md + context_reads |
| `scheduled × accumulation` | H | dispatcher generative branch | declaration + run-log + domain entity inventory + AGENT.md + context_reads |
| `reactive × action` | I | dispatcher action branch | declaration + template + AGENT.md + ProposeAction shape required |
| `scheduled × maintenance` | J | dispatcher maintenance branch | executor dotted path — **NO LLM call** |

Strategies G + H share the dispatcher's generative implementation (per Phase 3.2.b commit) but with shape-specific envelope. Strategies B-F are the entity-profile variants (Phase 3.6 work). Strategy A is the workspace profile (Phase 3.6 update of compact index source).

Operator's framing — "invocations by type drive prompt strategy" — is correct. The *type* is precisely this 2-tuple. Type 1 (output-kind alone) gets it wrong. Type 2 (pulse-class alone) gets it wrong. Type 3 (trigger-class × shape) is the right grain.

This is now the load-bearing classification for **A4** (axiom 4 below) and underlies §3, §5, §7 of this plan.

---

## Audit findings (objective, code-grounded)

The prompt + context + session layer is heavily task-era keyed. Every touch point identified in the prior architectural discourse has not caught up to the substrate change.

| Surface | Current state | Drift severity |
|---|---|---|
| `working_memory.py::format_compact_index` (L1107) | Pulls `active_tasks` from `tasks` DB table (`_get_active_tasks_sync` L490). Renders "Active tasks (N):" block at L1182. | **High** — compact index is entirely tasks-table-keyed; no recurrence-walker awareness. |
| `working_memory.py::_format_entity_index` (L1030) | Looks up specific task in `active_tasks` for freshness info. | **High** — entity profile depends on task-table query. |
| `yarnnn_prompts/base.py` | Line 60: "Tasks are the work units. Agents and production roles are assigned to tasks via the `## Team` section in TASK.md." | **Medium** — vocabulary drift; reframing needed but no functional break. |
| `yarnnn_prompts/behaviors.py` | 18KB of guidance keyed off ManageTask actions (`task` feedback target, `task_slug`, `/tasks/{slug}/TASK.md` reads, `ManageTask(action="trigger/update/pause")`). | **High** — behavioral guidance directs TP to task-era primitive shapes that don't exist post-cutover. |
| `yarnnn_prompts/entity.py` | "Task-specific feedback → UpdateContext(target='task', task_slug=...)"; `ManageTask(task_slug=...).action='evaluate/steer/complete'` examples. | **High** — entity profile is fundamentally task-scoped. |
| `yarnnn_prompts/onboarding.py` | L304 "For each created task, call ManageTask(task_slug='...', action='trigger')"; L492-493 "ReadFile(path='/tasks/{slug}/TASK.md')". | **High** — onboarding flow assumes task creation as primary scaffolding act. |
| `task_pipeline.py::build_task_execution_prompt` (L1416) | Per-shape conditional generation prompt. 3 call sites within task_pipeline (L2091, 2749, 4085). | **High** — prompt assembly logic lives inside the file being deleted; must migrate to invocation_dispatcher. |
| `chat.py` conversation compaction | 10-message rolling window; older → `/workspace/memory/conversation.md`. | **Low** — workspace-scoped, no task references in compaction logic itself. Verify with grep gate. |

**Conclusion:** the task abstraction's removal at the substrate layer (Phase 3.4-3.7) is necessary but not sufficient. Without an explicit runtime-layer migration plan, the dispatcher will fire invocations against substrate that exists, but the *operator-facing language* (compact index, prompt guidance, surface profiles) will direct YARNNN toward primitives and paths that no longer exist. The post-cutover system would be functionally working but conversationally broken.

---

## Eight axioms (first-principled, derived from audit)

The runtime context layer is governed by eight axioms. Six are already canonical; two are new principles emerging from this audit.

| # | Axiom | Status | Source |
|---|---|---|---|
| **A1** | Filesystem is the persistence substrate. No DB-row-as-state. Everything that persists across invocations lives in `workspace_files`. | Canonical | FOUNDATIONS Axiom 0 |
| **A2** | Each invocation declares its read scope. Recurrence declaration's `context_reads` field bounds token budget per firing. No implicit reads. | Canonical (preserved through cutover) | ADR-151/207 + ADR-231 D3 |
| **A3** | Cross-firing continuity lives in a recent-N compaction file adjacent to the artifact. The declaration's `_run_log.md` is the canonical "what happened in last 5 firings" substrate. Reading this gives an Agent its memory of prior firings without re-reading entire history. | **New (this plan)** | ADR-231 D10 + this doc |
| **A4** | Type-gated prompt assembly. The classification is **(trigger-class × shape)** — see "Axiomatic grouping" section above. 10 cells collapse to 6 distinct prompt strategies (A-J in the cell matrix). No monolithic prompt that handles all cases via deep conditionals. | **New (this plan)** | This doc §"Axiomatic grouping" |
| **A5** | Authored substrate IS the audit trail. Revision history (ADR-209) provides meta-awareness for free. No separate audit logging. | Canonical | ADR-209 |
| **A6** | Compact index is workspace-state-summary, not memory. Index lists pointers (paths + metadata); the LLM reads on demand. Bounded ≤1500 tokens regardless of workspace density. | Canonical (path/source updated) | ADR-159 |
| **A7** | Conversation history is rolling-window-with-filesystem-overflow. Last 10 messages in prompt, older compacts to `conversation.md`. No alternative session storage. | Canonical (preserved) | ADR-221 |
| **A8** | Narrative emission is the universal observability surface. Every invocation lands one entry in `session_messages` via `write_narrative_entry`. No alternative logging. | Canonical | ADR-219 |

**Operator's proposal validation**: the user's framing — "skills-on-Claude + filesystem-native + authored-substrate-as-meta-awareness" — maps cleanly onto A1+A3+A5+A6. Their "type-gated prompt strategies" maps onto A4. Their "10-message rolling session" maps onto A7. Their "compaction summary in directory itself" is precisely A3. **No conflicts; the proposal is the operator-vocabulary version of these axioms.**

---

## Per-shape context envelopes

The dispatcher must carry shape-specific envelopes. Same dispatcher entry point, four internal context-assembly paths. Token budgets are estimates; production runs may vary by content density.

| Field | DELIVERABLE | ACCUMULATION | ACTION | MAINTENANCE |
|---|---|---|---|---|
| **Declaration source** | `/workspace/reports/{slug}/_spec.yaml` | `/workspace/context/{domain}/_recurring.yaml` (entry by slug) | `/workspace/operations/{slug}/_action.yaml` | `/workspace/_shared/back-office.yaml` (entry by slug) |
| **Operator narrative** | adjacent `_intent.md` (optional) | adjacent `_intent.md` (optional) | adjacent `_intent.md` (optional) | n/a |
| **Cross-firing memory** | adjacent `_run_log.md` (recent N=5 entries) | adjacent `_run_log.md` per recurrence | adjacent `_run_log.md` (recent N=10 fires) | n/a (logs to `/workspace/_shared/back-office-audit.md`) |
| **Feedback** | adjacent `_feedback.md` (last 3 entries injected) | domain-level `_feedback.md` | n/a (outcomes via `_performance.md`) | n/a |
| **Steering** | adjacent `_steering.md` (operator's one-shot focus) | adjacent `_steering.md` per recurrence | n/a | n/a |
| **Context reads (declared)** | `context_reads:` domains read into prompt | `context_reads:` domains | `context_reads:` domains + portfolio + signals | n/a |
| **Prior output** | `outputs/latest/output.md` from prior firing | n/a (output IS the domain files) | n/a (output is platform event) | n/a |
| **Agent identity** | `/agents/{slug}/AGENT.md` (Agent persona + style.md) | `/agents/{slug}/AGENT.md` | `/agents/{slug}/AGENT.md` | n/a (deterministic Python executor) |
| **Token estimate (per firing)** | ~6-12K input | ~4-8K input | ~3-6K input | <1K (no LLM) |
| **Output target path** | `/workspace/reports/{slug}/{date}/output.md` + composed HTML | domain entity files in `/workspace/context/{domain}/{entity}/` | platform write event + `_performance.md` ledger entry | side-effect log to `/workspace/_shared/back-office-audit.md` |
| **Working scratch** (D9) | `/workspace/reports/{slug}/working/` (24h TTL) | `/workspace/context/{domain}/working/{recurrence-slug}/` | `/workspace/operations/{slug}/working/` | `/workspace/_shared/working/{back-office-slug}/` |
| **Cost gate** (D12) | `max_balance_cents_per_firing` from declaration | same | same | n/a (deterministic) |
| **Narrative emission** | `weight: material`, `summary: "Delivered {report-name} ({sections})"` | `weight: routine`, `summary: "Updated {N} entities in {domain}"` | `weight: material` (proposal-shaped) or `routine` (executed) | `weight: housekeeping`, rolled into daily digest |

This table is the dispatcher's contract. Phase 3.2 dispatcher rewrite implements one branch per shape, each branch reads exactly the files in its column, generates a prompt with exactly that envelope, calls Claude, writes to the declared output target, emits one narrative entry, returns.

---

## Compact index v2 specification

Replaces the tasks-table-keyed compact index in `working_memory.py::format_compact_index`. The v2 index walks the recurrence walker (`recurrence.walk_workspace_recurrences`) instead.

**Format (workspace profile):**

```
Workspace: {operator-display-name}
Mandate: {first-line of MANDATE.md or "(empty — not authored)"}
Activation: {none | post_fork_pre_author | operational}

Active recurrences (N):
  {shape-icon} {slug:<24} schedule={cron}  next={time}  agent={slug}  paused={bool}
  ... (top 8, sorted by next-run-at)
  {if N>8} ... +{N-8} more (see /work)

Domains ({M}):
  {domain-slug:<20} entities={count}  last-updated={time}
  ... (top 5)

Agents ({P}):
  reviewer (Reviewer)  pending-proposals={count}
  {custom-agent-slug:<20} role={role}  last-fired={time}
  ... (top 5)

Recent narrative (last 24h, material+routine):
  {time} {identity} → {one-line summary}
  ... (top 5)

Recent authorship (last 7d):
  {N} writes to {hottest-path} by {top-author}
  Most-edited file: {path} ({revision-count} revisions in last week)
```

**Bounded-token guarantee:** workspace state breakdown by activity level:
- Empty workspace (post-fork-pre-author): ~150 tokens
- Active workspace (alpha-trader steady-state, ~6 recurrences, 2 domains, 5 agents): ~450 tokens
- Busy workspace (50 recurrences across 12 domains, 15 custom Agents): top-N capping ensures ≤1200 tokens

**Entity profile compact-index variant** (`_format_entity_index`): scoped index when YARNNN is on `/work/{slug}` or `/agents/{slug}`. Replace task-row freshness lookup with declaration-walker freshness. Format compresses to ~250 tokens (single-recurrence detail + adjacent feedback summary + last 3 narrative entries for this slug).

---

## Surface profile mapping (post-cutover)

ADR-186 introduced `workspace` and `entity` profiles. Post-cutover the entity profile splits by shape (4 sub-profiles) because each shape's substrate envelope differs materially.

| Surface URL | Profile | Entity preamble |
|---|---|---|
| `/chat` | workspace | None (or activation overlay if state==post_fork_pre_author) |
| `/work/{slug}` (deliverable) | entity:deliverable | `_spec.yaml` summary + `_intent.md` + last 5 entries from `_run_log.md` + last delivered output preview |
| `/work/{slug}` (accumulation) | entity:accumulation | `_recurring.yaml` entry summary + entity inventory snapshot for the domain |
| `/work/{slug}` (action) | entity:action | `_action.yaml` summary + last 10 fires from `_run_log.md` |
| `/work/{slug}` (maintenance) | entity:maintenance | back-office entry summary + last 7d audit lines |
| `/agents/{slug}` (custom domain Agent) | entity:agent | AGENT.md + style.md + last 5 narrative entries authored by this Agent |
| `/agents/reviewer` | entity:reviewer | review/IDENTITY.md + principles.md + last 5 decisions.md entries (preserved as-is from ADR-194 v2) |

The profile selector (`api/routes/chat.py::resolve_profile` per ADR-186) extends to dispatch on URL shape pattern. Single dispatcher, 7 outputs.

---

## Working scratch + run-log conventions (D9 + D10 detailed)

### Working scratch (D9)

| Shape | Scratch path | Owner | TTL | Cleanup hook |
|---|---|---|---|---|
| Deliverable | `/workspace/reports/{slug}/working/` | Recurrence (per-firing) | 24h | scheduler ephemeral-cleanup cron |
| Accumulation | `/workspace/context/{domain}/working/{recurrence-slug}/` | Recurrence (per-firing) | 24h | same |
| Action | `/workspace/operations/{slug}/working/` | Recurrence (per-firing) | 24h | same |
| Maintenance | `/workspace/_shared/working/{back-office-slug}/` | Recurrence (per-firing) | 24h | same |
| Agent cross-firing | `/agents/{slug}/working/` — **NOT canonical** | — | — | — |

`/agents/{slug}/working/` is explicitly NOT a canonical scratch. Agents that need invocation-local scratch use the declaration-adjacent path. This honors D9 (no per-Agent conflation).

Scheduler extension: `unified_scheduler.py::ephemeral-cleanup` job extends its walk pattern from `/tasks/*/working/` to `(/workspace/reports/*/working/, /workspace/context/*/working/*, /workspace/operations/*/working/, /workspace/_shared/working/*)`.

### Run-log discipline (D10)

Two distinct substrates, both append-only, fixed scopes:

**Declaration `_run_log.md`** (canonical execution history per recurrence):
- Path: adjacent to declaration YAML — `<declaration-dir>/_run_log.md`
- Format: timestamp + identity + summary + provenance pointer (per ADR-219 narrative-entry shape, mirrored locally)
- Cap: rolling N=5 (deliverable), N=20 (accumulation, action), N=50 (maintenance) — older entries truncated, NOT archived
- Author: dispatcher writes via `authored_substrate.write_revision` after every firing
- Reader: dispatcher reads on next firing (cross-firing continuity per A3)

**Agent `/agents/{slug}/memory/*.md`** (cross-firing learning):
- Path: agent-scoped (preserves ADR-106)
- Files: `AGENT.md` (identity declaration), `style.md` (distilled style preferences per ADR-117), `thesis.md` (accumulated domain understanding)
- Author: Agent writes via `WriteFile` (headless mode) when learning crosses firings
- Reader: dispatcher loads as part of every firing's prompt envelope

**Discipline rule (codified in dispatcher tests):** Agent-side write paths must NOT include `/workspace/reports/`, `/workspace/context/`, `/workspace/operations/`, or `/workspace/_shared/`. Agent-side reads MAY include these (they're reading the work substrate). Dispatcher-side writes MAY include these (it's owning the work substrate). The split is "Agent owns identity, dispatcher owns execution history."

---

## Per-shape prompt assembly

The dispatcher builds prompts using a shared base + shape-specific envelope. Reused base content stays cached (Anthropic prompt caching); shape-specific content is dynamic.

**Shared base (cached, ~3K tokens):**
- BASE_PROMPT (yarnnn_prompts/base.py — vocabulary, tone, primitive rules)
- TOOLS_CORE (yarnnn_prompts/tools_core.py — primitive surface)

**Shape-specific envelope (dynamic, varies):**

| Shape | Envelope sections (in order) |
|---|---|
| DELIVERABLE | (1) Declaration metadata block, (2) operator intent (`_intent.md`), (3) deliverable contract (`_spec.yaml::deliverable`), (4) recent feedback (last 3 from `_feedback.md`), (5) steering (`_steering.md`), (6) prior output preview (`outputs/latest/`), (7) Agent identity (`/agents/{agent_slug}/AGENT.md`), (8) declared context reads, (9) accumulation-first posture reminder |
| ACCUMULATION | (1) Declaration metadata, (2) operator intent, (3) recent run log (last 5), (4) domain entity inventory (slugs + last-updated), (5) Agent identity, (6) declared context reads, (7) entity-creation rules from domain `_domain.md` |
| ACTION | (1) Declaration metadata, (2) operator intent, (3) action template (`_template.md`), (4) target capability (e.g., `write_slack`), (5) Agent identity, (6) declared context reads, (7) ProposeAction shape required (gates Reviewer) |
| MAINTENANCE | (1) Declaration metadata, (2) executor dotted path. NO LLM call — deterministic Python execution. |

**Cross-shape consistency invariants:** every dispatcher branch (a) emits exactly one narrative entry, (b) writes via `authored_substrate.write_revision` (no direct `workspace_files` mutation), (c) honors the `paused: true` flag and `paused_until` time gate before any compute, (d) checks `max_balance_cents_*` (D12 schema; enforcement deferred but plumbing present), (e) runs the post-run domain scan + actuation rules (per ADR-181) where applicable.

---

## Narrative emission audit

Every dispatcher branch must call `write_narrative_entry` exactly once before returning. Exhaustive enumeration:

| Branch | weight | system_card | Notes |
|---|---|---|---|
| Deliverable success | material | `task_complete` (preserved label) | summary = "Delivered {display_name} ({date})" |
| Deliverable failure | routine | `task_failed` | summary = "Failed to deliver {display_name}: {error_class}" |
| Deliverable cost-gate-skip | routine | `cost_gate_skip` | summary = "Skipped {display_name}: would exceed declared per-firing budget" |
| Accumulation success | routine | `domain_updated` | summary = "Updated {N} entities in {domain}" |
| Accumulation failure | routine | `domain_update_failed` | (small writes, low operator-impact) |
| Action proposed | material | `proposal_emitted` | summary = "Proposed {action_type} for Reviewer judgment" |
| Action executed | material | `proposal_executed` | summary = "Executed {action_type}: {outcome}" |
| Action failure | routine | `action_failed` | platform-write failures |
| Maintenance success | housekeeping | `back_office_run` | rolled into daily digest by `narrative_digest` cron |
| Maintenance failure | routine | `back_office_failed` | unrolled (visible in chat) |
| Paused-skip (any shape) | housekeeping | `pause_skip` | rolled into digest |

**No quiet branches.** Regression test: post-cutover, `api/test_adr231_narrative_completeness.py` instruments the dispatcher with a counter and asserts the counter increments by exactly 1 per dispatch invocation across all 11 branches.

---

## Authored-substrate revision posture (prompt amendments)

Per A5 + ADR-209, prompts that direct TP to "check revisions before trusting accumulated state" need their file-path examples updated:

| Old example | New example |
|---|---|
| `ListRevisions(path="/tasks/{slug}/TASK.md")` | `ListRevisions(path="/workspace/reports/{slug}/_spec.yaml")` |
| `ListRevisions(path="/tasks/{slug}/memory/feedback.md")` | `ListRevisions(path="/workspace/reports/{slug}/_feedback.md")` (or domain) |
| `ReadRevision(path="/tasks/{slug}/DELIVERABLE.md", offset=-1)` | `ReadRevision(path="/workspace/reports/{slug}/_spec.yaml", offset=-1)` (deliverable contract is the YAML's `deliverable:` block) |

Locations to update: `tools_core.py::TOOLS_CORE` (revision-aware reading section), `behaviors.py` (entire file, given task-era saturation), `entity.py` (full rewrite for shape-specific entity profiles).

---

## Cost ceiling plumbing (D12)

Even though D12 enforcement is deferred, the dispatcher plumbs the schema fields *now* so Phase 3.2 doesn't need to be revisited when enforcement lands.

**Schema reads (forecast-side):**
1. Dispatcher reads `recurring.max_balance_cents_per_firing` and `recurring.max_balance_cents_per_week` from declaration.
2. If absent: log "no cost cap declared", proceed.
3. If present: compute forecast (deferred placeholder: `forecast = 0`; future commit fills in per-shape token estimate × per-token cost).
4. Compare forecast to cap. If exceeded: emit `cost_gate_skip` narrative entry, return `{success: False, error: "cost_gate"}`. Do not call Claude.

**Schema reads (post-firing-side):**
1. After successful firing, write actual `balance_cents_consumed` to `_run_log.md` entry.
2. Aggregate across recent N entries to maintain rolling-window forecast for next firing.

The "forecast = 0" placeholder ensures the gate never trips during the migration window. Future commit replaces with real estimation.

---

## Cross-shape invariants (regression-test inventory)

Post-cutover regression test (`api/test_adr231_runtime_invariants.py`) asserts:

1. Compact index always ≤1500 tokens regardless of workspace state (empty / steady / busy).
2. Every dispatcher firing emits exactly one narrative entry (counter == 1 per invocation, no quiet paths).
3. Working-scratch directory created at firing-start and cleaned at TTL.
4. `_run_log.md` rolling cap honored (N=5/20/50 per shape; older entries truncated).
5. `paused: true` declarations are not fired by scheduler.
6. `paused_until` future-timestamp declarations are not fired before that time.
7. Agent-side write paths exclude work-substrate paths (D10 discipline).
8. Authored substrate revision attribution: every write carries `authored_by` matching dispatcher's identity.
9. Per-shape envelope token estimates within ±20% of table above.
10. No live-code references to `task_pipeline`, `manage_task`, `task_workspace`, `task_types`, `task_derivation` (ADR-231 final grep gate).

---

## Where the operator's proposal aligns / refines / extends

The user's overarching framing was: "skills-on-Claude + filesystem-native + authored-substrate-as-meta-awareness, with type-gated prompts and 10-message rolling sessions."

| Operator proposal element | This plan's instantiation |
|---|---|
| 10-message rolling session | A7 + ADR-221 (preserved unchanged) |
| Invocations classified by type drive prompt strategies | A4 (new principle) + per-shape envelope tables above |
| Filesystem-native referencing | A1 + A2 (canonical, preserved) |
| Authored substrate as meta-awareness | A5 + revision posture amendments above |
| "Compaction summary in directory itself" | A3 (new principle) + `_run_log.md` recent-N cap + cross-firing continuity rules |
| Tight context windows gated by invocation type | per-shape envelope tables (token estimates per shape, bounded explicitly) |
| Best-of-multiple-worlds: persistence + tight windows | filesystem persists; envelope bounds reads; revision history adds free meta-awareness |

**No conflicts.** The plan is the engineering articulation of the operator's framing.

---

## Execution-session reading order

1. ADR-231 v1.1 — the architectural decisions (D1-D12).
2. This plan — the runtime-layer specification (axioms + envelopes + invariants).
3. ADR-219 — narrative emission canon (preserved).
4. ADR-209 — authored substrate (preserved; revision posture amendments per this plan).
5. ADR-159 — compact index (preserved; v2 specification per this plan).
6. ADR-186 — surface profiles (extended per this plan).

Then begin Phase 3.2 dispatcher rewrite with the per-shape envelope table as the contract, Phase 3.3 scheduler migration with the recurrence walker as the source, Phase 3.4 DB migration to drop heavy task columns, etc.

---

## Revision history

| Date | Change |
|---|---|
| 2026-04-29 | v1 — Initial planning artifact. Eight axioms (A1-A8, with A3 + A4 new). Per-shape envelope tables. Compact index v2. Surface profile mapping. Working-scratch/run-log conventions. Narrative emission audit. Cost ceiling plumbing. Cross-shape invariants + regression test inventory. Operator-proposal alignment confirmed. |
| 2026-04-29 | v1.1 — Two surgical amendments after operator discourse: (1) "Handoff to execution session" section added at top — prescriptive reading order, phase-by-phase contracts, prompt-rewrite scope, stop conditions; (2) "Axiomatic grouping" section added — explicit (trigger-class × shape) 2-tuple as the load-bearing classification for A4, with 10-cell matrix collapsing to 6 distinct prompt strategies (A-J). Underlying tables (§3, §5, §7) unchanged; the 2-tuple framing is the explicit articulation of what was implicit. No conflicts with v1 content; pure clarification. |
