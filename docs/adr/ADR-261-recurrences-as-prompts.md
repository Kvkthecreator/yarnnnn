# ADR-261: Recurrences as Prompts — Single Execution Shape

> **⚠ D7 (six universal specialist roles) narrowed by [ADR-272](ADR-272-identity-collapse-system-agent-and-specialist.md) (2026-05-14).** The DispatchSpecialist primitive + headless tool surface infrastructure stay (mechanism preserved across REVIEWER_PRIMITIVES + CHAT_PRIMITIVES + HEADLESS_PRIMITIVES). VALID_SPECIALIST_ROLES narrows from 6 roles to 1 — `designer` only — per the ADR-272 Specialist Survival Test. The Reviewer does investigation, analysis, prose drafting, accumulation, and cross-domain synthesis inline using its own tool surface; designer survives as an escape hatch for asset rendering where tool surface (RuntimeDispatch), output size (binary assets), and latency (10-60s renders) genuinely warrant a sub-context.

**Status**: Fully Implemented 2026-05-10 (Phases B + C + D atomic on PR #9). D1 unified `{slug, schedule, prompt}` schema + D2 single canonical file + D3 walker-based scheduler + D4 Schedule primitive + D5 AUTONOMY rederive + D6 workspace_init simplification (back-office package deleted) + D7 specialists-as-tools (DispatchSpecialist primitive in REVIEWER_PRIMITIVES + CHAT/HEADLESS; **narrowed to designer-only role by ADR-272**) + D8 task_types registry dissolved + D9 Authored Substrate continuity all landed.
**Companion ADRs (atomic together)**:
- ADR-260 — Real-Time Reviewer Loop: Cron is a Nudge, Continuation is Not a Trigger
- ADR-262 — Output Topology and Specs: Filesystem-Native Output Without Registries

**Supersedes**:
- ADR-138 §"Tasks are WHAT" (recurrences as discrete pre-defined work units with output_kind dispatch) — recurrences become prompts, output_kind dissolves as a recurrence-level discriminator.
- ADR-166 (output_kind 4-value enum + per-kind dispatch) — collapses; what survives moves under ADR-262 as filesystem topology conventions.
- ADR-178 (Route A vs Route B task creation) — both routes were keyed on recurrence shape; with one shape, the routes dissolve into "operator authors a prompt."
- ADR-231 §"per-shape natural-home paths" + `recurrence_paths.py` + RecurrenceShape enum — paths are prompt-named (per ADR-262); shape dispatch deleted.
- ADR-161 (essential daily-update at signup) — daily-update becomes an ordinary recurrence in `_recurrences.yaml`; "essential" flag deleted.
- ADR-164 (back-office tasks materialized on trigger, with task pipeline `thinking_partner` dispatch + `executor:` directive) — back-office work is recurrences whose prompts direct maintenance; no separate dispatch path.
- ADR-188 §"task type registry as curated template library" + `task_types.py::TASK_TYPES` registry — fully deleted; ADR-262 establishes the replacement model.

**Amends**:
- ADR-176 (work-first agent model — six specialist roles + thinking_partner + 3 platform-bots) — preserved as **tools the Reviewer's loop calls**, not parallel execution paths. Specialists' identities + capability splits unchanged at the role level; their invocation shape changes from "headless pipeline" to "Reviewer-directed sub-LLM-call at real-time runtime, identical to Claude Code sub-agents."
- ADR-080 + ADR-141 (`headless` permission mode + task pipeline as Layer 2 generation) — `headless` survives as **a runtime characteristic of LLM calls** (non-streaming, curated tool surface, no live operator). It no longer denotes a separate execution path. Reviewer's loop dispatches specialist roles using `headless`-mode LLM calls when appropriate; that's the only place the mode survives.
- ADR-226 (reference-workspace activation, three-tier `canon | authored | placeholder` frontmatter) — three-tier system dissolves; every authored substrate file is markdown the operator owns. Bundle activation copies bundle's `reference-workspace/` and seeds bundle's recurrences into workspace's `_recurrences.yaml`.
- ADR-258 (revised) (Reviewer curated `REVIEWER_PRIMITIVES`) — `Schedule` primitive added; `ManageRecurrence` renamed to `Schedule` and reshaped per §3 below.

**Preserves**:
- FOUNDATIONS Axioms 1, 2, 4, 5, 6.
- ADR-194 v2 Reviewer substrate.
- ADR-195 v2 money-truth substrate.
- ADR-209 Authored Substrate (every revision attributed and retained — load-bearing for cross-session continuity per ADR-260 D1).
- ADR-247 three-party narrative model.
- ADR-259 Feed surface vocabulary.

---

## 1. Why this ADR

ADR-260 ratifies the real-time Reviewer loop and three-trigger model. But the deeper change underneath ADR-260 is: **what is a recurrence?** Today a recurrence is a discrete pre-defined work unit with an `output_kind` (`accumulates_context | produces_deliverable | external_action | system_maintenance`), shape-specific declaration files (`_spec.yaml`, `_recurring.yaml`, `_action.yaml`, `back-office.yaml`), shape-specific natural-home paths (per ADR-231), and shape-specific task pipeline dispatch.

Under the real-time-loop framing, this taxonomy is wrong-shaped. A recurrence is no longer "a pipeline that produces substrate." It is **a self-scheduled wake-up — for the Reviewer (or operator) — that hands the Reviewer a prompt at the scheduled time.** The Reviewer's real-time loop runs at that moment, doing whatever the prompt asks (which might involve firing tools, writing substrate, ProposeActions, etc.).

This is a unifying collapse. Every cron entry is the same shape: `slug + schedule + prompt`. There are no four kinds; there is one kind. Output_kind, shape-specific files, shape-specific paths, shape-specific dispatch — all dissolve.

The shift gears YARNNN's architecture toward Claude Code / Claude Cowork **at the framework level**, not just at the loop level: framework prescribes minimally, operator (or program bundle) authors the prompts that encode intent. ADR-262 (companion) addresses how prompts encode filesystem-native multi-file structured output without re-implementing the registries we just deleted.

---

## 2. Decision

### D1 — Recurrences are prompts. One shape.

A **recurrence** is a record with three load-bearing fields:

```yaml
- slug: morning-reflection
  schedule: "0 7 * * *"
  prompt: |
    Reflect on yesterday's decisions against your principles. Look at decisions.md
    and _performance.md. If patterns warrant adjustment, ProposeAction with full
    revised file content. Default outcome is no_change.
```

`slug` identifies the recurrence (stable across runs; used in audit trails, feed entries, and operator chat references). `schedule` is a cron expression. `prompt` is the message handed to the Reviewer at the scheduled time as the addressed-equivalent envelope.

There are no other top-level fields required. Optional metadata (e.g., `description`, `paused: true`, `created_by`) MAY exist for operator legibility or system bookkeeping but does not affect execution shape.

**`output_kind` is deleted as a recurrence-level field.** The four-shape model (accumulates_context / produces_deliverable / external_action / system_maintenance) was structural because each shape implied a different pipeline. Under one execution shape (Reviewer's loop), shape is a property of *what the Reviewer's prompt directs*, not of the recurrence record. A "deliverable" recurrence is one whose prompt asks the Reviewer to write a report. An "accumulation" recurrence is one whose prompt asks the Reviewer to refresh tickers. There is no schema-level distinction.

### D2 — Recurrences live in one canonical place

All recurrences for a workspace live in `/workspace/_recurrences.yaml`, a flat list. There is no `back-office.yaml`, no per-domain `_recurring.yaml`, no per-deliverable `_spec.yaml`, no per-action `_action.yaml`. The entire scheduled-work surface of a workspace is one file an operator can read in 30 seconds.

```yaml
# /workspace/_recurrences.yaml
- slug: morning-reflection
  schedule: "0 7 * * *"
  prompt: "Reflect on yesterday's decisions ..."

- slug: signal-evaluation
  schedule: "0 * 9-16 * 1-5"
  prompt: "Evaluate the universe against signals IH-1 through IH-5 ..."

- slug: track-universe
  schedule: "0 */4 * * *"
  prompt: "Refresh fundamentals for tickers in /workspace/context/trading/_universe.yaml ..."

- slug: outcome-reconciliation
  schedule: "0 5 * * *"
  prompt: "Reconcile yesterday's executed proposals against platform events ..."

- slug: weekly-market-conditions
  schedule: "0 8 * * 1"
  prompt: "Produce the weekly market-conditions report. Follow the spec at /workspace/specs/market-conditions.md ..."
```

The path `/workspace/_recurrences.yaml` is canonical. (Implementation detail — could be `_shared/_recurrences.yaml` if path semantics demand; the load-bearing fact is *one canonical file*, not multiple registries.)

### D3 — One scheduler, one job, parallel concurrent Reviewer sessions

The scheduler's only responsibility is: walk due recurrences and invoke the Reviewer for each. Pseudocode:

```
for each recurrence in /workspace/_recurrences.yaml that is due and not paused:
  spawn invoke_reviewer(
    trigger="scheduled",
    context={"prompt": recurrence.prompt, "slug": recurrence.slug, ...}
  )  # concurrent, not awaited serially
```

No dispatch by output_kind. No path resolution. No template-string expansion. The recurrence's `prompt` is what reaches the Reviewer.

**Architectural guarantees (committed by this ADR):**

1. **Parallel concurrent Reviewer sessions.** When multiple recurrences are simultaneously due (e.g., a workspace has 8 recurrences all firing at 7am UTC), all of them invoke a Reviewer session concurrently. There is no serial back-pressure that delays later recurrences while an earlier one's session is running. Each Reviewer session is independent; they share workspace substrate but not session state.
2. **Sub-minute scheduling precision is supported.** Recurrences scheduled at `0 7 * * *` fire at 07:00:00, not "sometime in the 07:00–07:05 window." The architecture does not commit operators to coarse cadences as a side-effect of polling-cron implementation.
3. **No head-of-line blocking from slow sessions.** A 90-second-long Reviewer session for one recurrence does not delay other recurrences' fires. Concurrency model + scheduling mechanism are responsible for this.

**Implementation shape (chosen at code-PR time per first-principles, not legacy):**

The current 5-minute Render Cron Job is wrong-shaped under the parallelism + precision guarantees above — a 5-minute polling interval blocks sub-minute precision, and serial within-cycle dispatch creates head-of-line blocking. Three implementation candidates resolve all three guarantees; one is chosen at implementation time:

- **(α) Per-recurrence Render Cron Jobs.** Each recurrence's `schedule` becomes its own Render cron entry firing the Reviewer with that prompt. Concurrent by default (Render fires each cron independently). Sub-minute precision native (Render cron honors arbitrary cron expressions). Cost: one Render cron per recurrence (Render's pricing on cron count would need verification).
- **(β) `pg_cron`.** Postgres-native cron. Each recurrence is a row in a `cron.job` table; `pg_cron` fires them at scheduled times. Concurrent because each fire is its own session. Sub-minute precision native. Avoids Render cron count concerns.
- **(γ) Single long-running scheduler service.** A persistent process that maintains an in-memory due-list and fires recurrences at exact times via async dispatch. Concurrent by spawning sessions, not awaiting them. Sub-minute precision native. Adds operational overhead (persistent process vs cron jobs).

Each candidate satisfies the three architectural guarantees. The implementation PR picks one; the choice is a deployment-shape decision, not an architectural one. What this ADR commits is the guarantees, not the mechanism.

### D4 — `Schedule` primitive (renames `ManageRecurrence`)

The Reviewer's tool surface gains the `Schedule` primitive in `REVIEWER_PRIMITIVES` (per ADR-258 revised's curated subset). This primitive is the canonical way to author / modify / pause / resume / archive recurrences:

```python
Schedule(
  action: "create" | "update" | "pause" | "resume" | "archive",
  slug: str,
  schedule: str | None,    # cron expression; required for create
  prompt: str | None,       # required for create
)
```

**Both the operator and the Reviewer call `Schedule`.** Operator-via-chat routes through YARNNN's chat surface, which calls `Schedule` per the ADR-235 D1.c `ManageRecurrence` precedent (now renamed). Reviewer calls `Schedule` directly during its real-time loop when it needs to schedule its own future wake-ups. Same primitive, same path, same audit trail (per ADR-209: `authored_by="reviewer:{occupant}"` or `authored_by="operator"` recorded on the revision).

**There is no separate "infrastructure scaffolding" concept.** A recurrence is a Reviewer-scheduled future wake-up; scheduling one is an ordinary action. The Reviewer's authority to use `Schedule` is structurally safe because every wake-up runs another bounded session that itself passes through AUTONOMY for capital gates.

The current `ManageRecurrence` primitive (`api/services/primitives/manage_recurrence.py::handle_manage_recurrence`) is renamed to `Schedule` (`api/services/primitives/schedule.py::handle_schedule`). Per the singular-implementation rule, `ManageRecurrence` is deleted; no alias is preserved. Per the rename protocol (CLAUDE.md item 7b), grep for `ManageRecurrence` and `manage_recurrence` across all docs and code paths is mandatory in the code PR.

### D5 — AUTONOMY rederived from first principles

AUTONOMY's only job is to gate **consequential actions** the Reviewer takes within a session. Consequential = capital-moving + irreversible-external-write (submit trade, post to Slack, send email, etc.). Everything else (reads, scheduling self-wakeups via `Schedule`, writing to own substrate, ProposeAction queueing for operator review) is unrestricted because it's all observable + reversible via the revision chain.

The new `_autonomy.yaml` shape:

```yaml
# /workspace/context/_shared/_autonomy.yaml
default:
  delegation: bounded   # manual | bounded | autonomous
  ceiling_cents: 20000   # used when bounded; ignored otherwise

domains:
  trading:
    delegation: bounded
    ceiling_cents: 20000
  commerce:
    delegation: manual

paused_until: null
pause_reason: null
```

**Delegation enum**: `manual` queues every consequential action for operator approval. `bounded` auto-approves up to `ceiling_cents`, queues above. `autonomous` auto-approves everything (operator opt-in for full autonomy).

**Deleted fields** (folded or dissolved):
- `auto_approve_below_cents` — folded into `ceiling_cents` under `bounded` delegation.
- `never_auto` — folded into `manual` delegation.
- `heartbeat_triggers` — gone with ADR-260 D4.
- All other fields the legacy schema accumulated — none survive without explicit justification.

**`paused_until`** + **`pause_reason`** survive as the time-based pause mechanism (per ADR-248 D3 + D4 commitments). When non-null, AUTONOMY is effectively `manual` regardless of declared `delegation`. Reviewer can write these fields via `WriteFile` to its own substrate during a reflection session (ADR-248 D4 mechanism — preserved).

### D6 — Workspace initialization simplifies

`workspace_init.py` reshapes per ADR-205 + ADR-206 simplification carried forward:

1. **At signup, no program activated**: scaffold skeleton authored substrate (`MANDATE.md`, `IDENTITY.md`, `BRAND.md`, `AUTONOMY.md` per D5 shape, `principles.md` for review seat) and an empty `/workspace/_recurrences.yaml`. The workspace is structurally minimal — no daily-update, no back-office tasks. Operator's first chat with the Reviewer authored their first recurrence (or doesn't, if they prefer addressed-only operation).

2. **At program activation** (per ADR-226's bundle-fork mechanism, with the three-tier system dissolved per this ADR): copy the bundle's `reference-workspace/` files into the workspace, AND merge the bundle's `recurrences.yaml` entries into the workspace's `_recurrences.yaml`. From that moment, the workspace is operational. The Reviewer wakes (addressed by the operator, or by the first scheduled cron fire) and runs.

3. **Daily-update is no longer essential** (per ADR-161 supersession). It's an ordinary recurrence the operator may opt into via chat or that a program bundle may seed. There is no special-case `essential: true` flag, no special skip path in archive logic.

4. **Back-office tasks dissolve** (per ADR-164 supersession). What was previously `back-office-agent-hygiene`, `back-office-workspace-cleanup`, `back-office-outcome-reconciliation`, etc. — all are recurrence entries in `_recurrences.yaml` whose prompts direct the Reviewer to do the maintenance work. Same shape as everything else. The `task_pipeline.py::_execute_tp_task` dispatch on `agent.role == 'thinking_partner'` and the `executor:` YAML directive are deleted.

5. **`workspace_init.py` net diff**: ~70% of current code deletes. Phase 1-5 numbered phases collapse to "skeleton substrate + (optional) bundle fork + (optional) bundle recurrence merge."

### D7 — Specialists are tools the Reviewer's loop calls

ADR-176's six specialist roles + thinking_partner + 3 platform-bots survive. Their identity (role, scope, capabilities, persona) is preserved.

What changes is **how they're invoked**: the headless task pipeline (ADR-141 Layer 2) is deleted. There is no separate execution path for "headless agents producing sections that compose into deliverables." Instead, specialists run as Claude-Code-sub-agent-shaped sub-LLM-calls.

**Roles in specialist execution** (preserves ADR-257's deterministic System Agent):

| Actor | Role | Why |
|---|---|---|
| **Reviewer** | Judges + sequences specialists at high level. Names specialist invocations as discrete steps in its real-time loop ("fire researcher with this brief; then writer with the researcher's output"). | Judgment + high-level sequencing live with the principles-grounded Reviewer. |
| **System Agent** | Deterministic dispatcher. Receives the Reviewer's named-step direction and dispatches a focused-prompt specialist sub-LLM-call. Narrates the dispatch in the feed. Returns specialist's output to the Reviewer's loop. | Per ADR-257, System Agent is deterministic — no LLM judgment in execution path. Dispatch is mechanical: take the Reviewer's structured direction, invoke the specialist's `headless` LLM call, return the output. |
| **Specialist** (researcher / analyst / writer / tracker / designer / reporting) | Sub-LLM-call with **focused prompt**, narrow tool surface (`headless` mode, ADR-080 runtime characteristic), and the Reviewer-supplied brief as input. Produces markdown output. | Focused prompt = no prompt-pressure dilution. Specialists run with their own context window — same shape as Claude Code sub-agents. |

**Why this preserves separation of concerns** (the third-opinion concern, 2026-05-08): the Reviewer's context window is not polluted with specialist tool-use loops. The Reviewer's prompt-pressure stays focused on judgment. Specialists operate in their own contexts with their own tools. The deterministic System Agent is the boundary between them — it dispatches one specialist sub-call per Reviewer-named step, returns output, awaits the Reviewer's next direction.

**The specialist sub-LLM-call shape:**
- Triggered by the Reviewer's loop calling a primitive like `DispatchSpecialist(role="researcher", brief="...")` or by the recurrence prompt naming a specialist sequence as named steps.
- The System Agent (deterministic) receives the call, composes the specialist's prompt from: the Reviewer-supplied brief + the specialist's role-specific prompt fragment + relevant substrate refs.
- The sub-LLM-call runs in `headless` mode — non-streaming, curated tool surface, no operator-presence assumption.
- The specialist's output (markdown text) returns to the Reviewer's loop as the result of the dispatch primitive. The Reviewer reads the result and decides next.

**This makes specialist execution identical in shape to Claude Code sub-agents.** Whether triggered from a human operator's feed turn or from a scheduled recurrence's cron fire, the specialist runs the same way. Only the prompt at that runtime moment differs.

`headless` permission mode survives as the LLM-runtime characteristic for specialist sub-calls. The mode does not denote a separate execution path; it denotes a kind of LLM call.

### D8 — `task_types.py` registry dissolves

The entire `task_types.py` registry — including `TASK_TYPES`, `TASK_OUTPUT_PLAYBOOK_ROUTING`, `STEP_INSTRUCTIONS`, `output_category` per type, etc. — is deleted. ADR-262 establishes the replacement: filesystem topology conventions (Layer A — universal, declared in CONVENTIONS.md) + semantic specs (Layer B — operator-authored markdown the recurrence prompts cite).

The registry was carrying both mechanical (where things land) and semantic (what they contain) load. Both relocate per ADR-262. There is no curated-template-library survival — operators (or program bundles) author recurrence prompts directly; bundles ship example prompts in their `recurrences.yaml`.

### D9 — Cross-session continuity uses Authored Substrate (ADR-209)

When a recurrence fires the Reviewer at a later time, the new session reads the head revisions of relevant substrate, sees prior revisions' authored messages (`reviewer:{occupant}` / `agent:{slug}` / `system:{actor}` with the `message` field describing what changed and why), and knows what its prior selves did. There is no parallel "session continuation state" in code or in DB.

The revision log *is* the continuation record. This works because:
- Every Reviewer-fired action via the System Agent attributes the resulting substrate write (per ADR-209's enforcement at the substrate write boundary).
- Specialists' substrate writes attribute as `agent:{slug}`.
- The Reviewer's own writes (e.g., to `decisions.md`) attribute as `reviewer:{occupant}`.
- A waking Reviewer reading `/workspace/review/decisions.md` head revision sees the prior decisions verbatim. Reading the parent revision's `message` shows what triggered them.

This commitment is restated in ADR-260 D1 and is load-bearing for the architecture. The implementation plumbing is already in place per ADR-209 Phase 1-5; this ADR just commits to its semantic role.

---

## 3. Primitive surface (the new Schedule primitive)

### Signature

```python
Schedule(
  action: Literal["create", "update", "pause", "resume", "archive"],
  slug: str,
  schedule: str | None = None,    # cron expression; required for create
  prompt: str | None = None,        # required for create
)
```

### Semantics

- `create`: append a new entry to `/workspace/_recurrences.yaml`. Both `schedule` and `prompt` required. `slug` must be unique (enforced; collision returns error).
- `update`: modify an existing entry. Any subset of `schedule`, `prompt` may be provided; unprovided fields preserved.
- `pause`: set the entry's `paused: true`. Scheduler skips it on next walk.
- `resume`: set `paused: false`.
- `archive`: remove the entry from `_recurrences.yaml` (the revision log preserves history per ADR-209).

### Authorship

- Operator-via-chat: routes through YARNNN's chat surface. `authored_by="operator"` on the resulting `_recurrences.yaml` revision.
- Reviewer-mid-loop: Reviewer calls `Schedule` directly during its tool-use loop. `authored_by="reviewer:{occupant}"`.
- Bundle activation: program-bundle fork merges bundle recurrences into `_recurrences.yaml`. `authored_by="system:bundle-fork"`.

All three paths produce the same substrate writes through the same primitive. Per singular-implementation, no separate paths exist.

### Tool registry placement

`Schedule` is added to:
- `CHAT_PRIMITIVES` (per the chat-mode tool surface — operator's YARNNN can invoke it).
- `REVIEWER_PRIMITIVES` (per ADR-258 revised's curated subset — Reviewer can invoke it during real-time loops).
- `HEADLESS_PRIMITIVES` is unchanged (specialists do not schedule recurrences; they produce content).

The primitive is added to `docs/architecture/primitives-matrix.md` per the canonical doc convention.

---

## 4. What gets deleted

| Component | Reason |
|---|---|
| `output_kind` field on tasks/recurrences | D1 — one execution shape |
| `RecurrenceShape` enum + dispatch logic in `invocation_dispatcher.py` | D1 |
| `recurrence_paths.py` natural-home logic | D1 — paths are prompt-named (per ADR-262) |
| `_spec.yaml` (deliverable declaration files) | D2 — one canonical recurrence list |
| `_recurring.yaml` per-domain | D2 |
| `_action.yaml` per-action | D2 |
| `back-office.yaml` | D2 |
| `task_types.py` (`TASK_TYPES` registry) | D8 — full registry dissolved per ADR-262 |
| `TASK_OUTPUT_PLAYBOOK_ROUTING` | D8 |
| `STEP_INSTRUCTIONS` | D8 |
| `output_category` field on task type entries | D8 |
| `step_instructions` per task type | D8 |
| `task_pipeline.py::_execute_tp_task` dispatch on `thinking_partner` role | D6 — back-office work is recurrences with maintenance prompts |
| `executor:` directive in TASK.md process steps | D6 |
| `back-office-agent-hygiene` + `back-office-workspace-cleanup` + `back-office-outcome-reconciliation` etc. as task types | D6 — collapse to recurrences |
| `essential: true` flag on tasks | D6 — daily-update is not special |
| ADR-161 daily-update-at-signup scaffolding logic in `workspace_init.py` | D6 |
| ADR-164 back-office task materialization in `workspace_init.py` and `services/back_office/` | D6 |
| `dispatch_helpers.py` (most of it — survives only what supports recurrence-prompt invocation) | D3 — scheduler simplifies |
| `RecurrencePost`-like structured-output enforcement at the dispatch layer | D1 — output shape is in the prompt (per ADR-262) |
| `ManageRecurrence` primitive (renamed) | D4 — `Schedule` replaces it |
| `_autonomy.yaml::auto_approve_below_cents` field | D5 — folded into `ceiling_cents` |
| `_autonomy.yaml::never_auto` field | D5 — folded into `manual` delegation |
| Three-tier `canon | authored | placeholder` frontmatter system in bundle reference-workspaces (per ADR-226) | D6 amend — every authored substrate file is just markdown |
| `headless` mode as a separate execution path | D7 — survives only as LLM-call runtime characteristic |
| `task_pipeline.py` Layer 2 generation logic for non-tp tasks | D7 — specialist invocation is a tool call from Reviewer's loop |
| ADR-178 Route A vs Route B distinction | Sup. — recurrences are prompts; operator authors what they author |

The deletion list is intentionally large. This is the cost of the unifying collapse. The benefit is the *substantial* reduction in conceptual surface — the system has one execution shape, one cron use, one recurrence shape, one primitive for scheduling.

---

## 5. What this fixes (validation)

### 5.1 The screenshot, completing ADR-260's resolution

Operator: *"help me put in a trade and make money"*

Under ADR-260 + ADR-261:

1. Reviewer wakes (addressed). Reads MANDATE, IDENTITY, principles, current substrate.
2. Sees no `signal-evaluation` recurrence in `_recurrences.yaml`.
3. Calls `Schedule(action="create", slug="signal-evaluation", schedule="0 * 9-16 * 1-5", prompt="Evaluate the universe against signals IH-1 through IH-5 on fresh 1Hour bars. Write findings to /workspace/context/trading/signals/.")`.
4. System Agent narrates: *"Scheduled signal-evaluation on Reviewer's direction."*
5. Reviewer calls `FireInvocation(slug="signal-evaluation")` — the recurrence is now scheduled, but the Reviewer also wants to fire it once immediately to get fresh data.
6. System Agent narrates: *"Firing signal-evaluation on Reviewer's direction."* Streaming-status shows progress.
7. The fired invocation is structurally a sub-loop: Reviewer's loop pauses, a new Reviewer invocation begins with the recurrence's prompt as `addressed`-equivalent envelope, runs synchronously to completion, writes substrate, returns control to the outer loop's flow. (Or — alternative implementation: `FireInvocation` runs the recurrence's prompt as a directly-executed step rather than as a fresh Reviewer invocation. Implementation detail; both shapes preserve the visible UX commitment.)
8. Substrate written. System Agent narrates: *"signal-evaluation complete. Wrote to /workspace/context/trading/signals/. 3 signals fired."*
9. Reviewer reads. Decides. Proposes the trade. Closes session.

The screenshot's case resolves *because* the Reviewer can schedule its own future wake-ups *and* fire one in real-time during the same session. Both authorities flow from one primitive (`Schedule` for scheduling; `FireInvocation` for immediate execution).

### 5.2 Example: alpha-trader workspace at activation

After bundle activation, `/workspace/_recurrences.yaml` looks like this (seeded by bundle):

```yaml
- slug: morning-reflection
  schedule: "0 7 * * *"
  prompt: |
    Reflect on yesterday's decisions against your principles. Read decisions.md
    (last 7 days) and _performance.md. If patterns warrant adjustment, ProposeAction
    with full revised file content. Default outcome is no_change.

- slug: morning-calibration
  schedule: "0 6 * * *"
  prompt: |
    Calibrate against money-truth. Read _performance.md for last 7d/30d/90d
    windows. If realized P&L diverges materially from your declared edge, raise
    a calibration concern in decisions.md.

- slug: signal-evaluation
  schedule: "0 * 9-16 * 1-5"
  prompt: |
    Evaluate the universe against signals IH-1 through IH-5 on fresh 1Hour bars.
    For each ticker in /workspace/context/trading/_universe.yaml, check entry
    conditions. For any signal whose conditions are met, ProposeAction with
    sizing math.

- slug: track-universe
  schedule: "0 */4 * * *"
  prompt: |
    Refresh fundamentals for tickers in /workspace/context/trading/_universe.yaml.
    For each ticker, write a current snapshot to /workspace/context/trading/{ticker}.yaml
    following the schema in /workspace/specs/ticker-snapshot.md.

- slug: outcome-reconciliation
  schedule: "0 5 * * *"
  prompt: |
    Reconcile yesterday's executed proposals against platform events. Read
    platform_connections for trading. Update /workspace/context/trading/_performance.md
    with realized P&L per the schema in /workspace/specs/performance-rollup.md.

- slug: weekly-review
  schedule: "0 8 * * 1"
  prompt: |
    Produce the weekly market-conditions and strategy-review report. Follow the
    spec at /workspace/specs/weekly-review.md. Compose the result via the
    compose primitive.
```

Six recurrences. One file. An operator reading this understands the entire scheduled-work surface in 30 seconds. Compare to the legacy: six task type entries spread across `task_types.py`, six declaration files in different paths, separate dispatch logic per `output_kind`, separate paths per shape.

### 5.3 The "what does hourly cron mean" question (revisited)

Resolved per D1 + D3. Hourly cron entries are recurrences whose work the operator wants done hourly — the work is whatever the prompt says. The Reviewer is awake when the work is being done.

A lightweight hourly recurrence (`track-universe` refreshing 25 ticker fundamentals) completes in seconds. A heavyweight daily recurrence (`weekly-review` producing a multi-section report) takes minutes. Both are recurrences; both wake the Reviewer; the Reviewer's loop adapts to the prompt's shape. There is no architectural distinction, only a prompt-content distinction.

---

## 6. Open question: `FireInvocation` semantics

`FireInvocation(slug)` exists today as a Reviewer primitive that triggers a recurrence to run. Under the unified model, two implementation shapes are possible:

- **(α) Inline execution** — `FireInvocation` runs the recurrence's prompt as a directly-executed sub-step within the current Reviewer session. The current Reviewer's loop continues with the recurrence's substrate writes available. No nested Reviewer invocation; the Reviewer is the same invocation, the prompt is just a sub-prompt.
- **(β) Nested invocation** — `FireInvocation` triggers a fresh Reviewer invocation with `trigger="scheduled"` and the recurrence's prompt. The current Reviewer's loop blocks until the nested invocation completes; control returns with the substrate available.

The visible UX commitment (per ADR-260 D6) is identical in both shapes — operator sees the System Agent narrate the firing, then progress, then completion, then Reviewer reads.

This ADR does NOT pick. The implementation PR resolves this. The reason it's open: α is leaner (one LLM context, no nested system prompt construction), β is structurally cleaner (every recurrence-fire goes through the same code path whether triggered by cron or by mid-loop `FireInvocation`). A small bench at code time will reveal which is actually simpler to maintain.

What this ADR commits is: the *outcome* is the same. The Reviewer-after-fire reads the substrate the recurrence-prompt wrote, and the loop continues.

---

## 7. Out of scope (deferred)

- **`FireInvocation` α vs β shape** — resolved at implementation time per §6.
- **Schedule primitive UX surface in operator chat** — operator can author recurrences via chat today (YARNNN routes through `Schedule`); a richer modal surface (Cowork-shaped scheduled-task creation UI) is a follow-on.
- **Cross-workspace recurrence sharing / templates** — alpha operators get bundle-shipped recurrences via activation. A "recurrence library" or "share my recurrences with another operator" surface is not in scope.
- **Recurrence dependency graphs** — operators today implicitly chain recurrences via prompts that reference other recurrences' outputs. A first-class dependency declaration is not in scope.
- **`headless` mode primitive surface tightening** — ADR-080's headless permission mode survives as runtime characteristic; further tightening of which primitives are accessible in `headless` mode is deferred.

---

## 8. Implementation plan (sketch — exact commits TBD in code PR)

This ADR's code changes land in a follow-on PR atomic with ADR-260 and ADR-262 code changes. High-level phases:

1. **Recurrence model**: introduce `/workspace/_recurrences.yaml` schema; `Schedule` primitive replaces `ManageRecurrence`. Migration: walk existing tasks DB + per-shape declaration files, project to `_recurrences.yaml`. (One-time, irreversible per singular-implementation.)
2. **Scheduler**: shrink `unified_scheduler.py` to recurrence-walker that wakes Reviewer with prompt.
3. **Task pipeline removal**: delete `task_pipeline.py`, `task_workspace.py`, `task_types.py`, `task_derivation.py`, `recurrence_paths.py`, `dispatch_helpers.py` (most), `back_office/` directory. Specialist invocation reshapes as a tool call from Reviewer's loop.
4. **AUTONOMY rederive**: rewrite `_autonomy.yaml` schema; update reference workspaces; `review_policy.py::load_autonomy` simplified.
5. **Workspace init simplify**: per D6.
6. **Bundle activation simplify**: three-tier dissolves; bundle-fork merges recurrences into workspace's `_recurrences.yaml`.
7. **Validation**: alpha-trader workspace activates cleanly; sample recurrences fire; screenshot scenario resolves end-to-end.

CHANGELOG entry per the prompt-change protocol. Test gate: regression tests assert one `_recurrences.yaml` is the only recurrence substrate, `output_kind` does not appear in active code, `Schedule` is the only recurrence-CRUD primitive, alpha-trader bundle activation produces a workspace with the expected recurrences.

---

## 9. The principle, restated

A recurrence is a self-scheduled wake-up for the Reviewer with a prompt. One file lists them. One primitive manages them. One scheduler walks them. The Reviewer's real-time loop runs whatever the prompt directs. Output_kind, shape-specific dispatch, shape-specific paths, separate execution paths — all dissolve. The system has one execution shape.

This is YARNNN gearing toward Claude Code at the framework level: minimal prescription, operator-authored intent, real-time agent execution. Program bundles ship the specifics. The framework holds the shape.
