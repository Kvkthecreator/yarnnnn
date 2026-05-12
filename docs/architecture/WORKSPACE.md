---
title: Workspace (Architecture)
counterpart: docs/design/WORKSPACE.md
scope: conceptual — substrate, files, layers, bootstrap, autonomy threshold
status: Canonical
last_updated: 2026-05-12
---

# Workspace — Architecture

**Counterpart (design):** [docs/design/WORKSPACE.md](../design/WORKSPACE.md) — operator-facing surface contracts for the same substrate
**Supersedes:** `docs/architecture/workspace-init.md` (merged) · `docs/architecture/workspace-conventions.md` (merged) · `docs/design/SHARED-CONTEXT-WORKFLOW.md` · `docs/design/ONBOARDING-TP-AWARENESS.md` · `docs/design/USER-JOURNEY.md`
**ADRs:** 106 · 119 · 138 · 142 · 149 · 151 · 152 · 154 · 170 · 194 · 205 · 206 · 207 · 209 · 217 · 219 · 222 · 223 · 226 · 231 · 244 · 251 · 253 · 254 · 255

This doc answers six questions, in order:

0. **Which layer is what?** — the four-layer model (kernel · workspace · program · agent), plus where user-account concerns live (they're not workspace).
1. **What files exist in a workspace, who owns each path, and what's the lifecycle?** — the spatial inventory.
2. **What gets seeded when, by which trigger?** — the temporal bootstrap sequence.
3. **What does autonomous operation actually require?** — the autonomy threshold.
4. **How does the closed autonomy loop actually run?** — the loop trace.
5. **What specifically breaks at cold-start when a prerequisite is missing?** — the failure-mode catalog.

For the operator-facing view of these same files (per-tab contracts, CRUD shapes, affordances), see [docs/design/WORKSPACE.md](../design/WORKSPACE.md). For how agents *read* this substrate at reasoning time (prompt assembly, profile selection, cockpit awareness), see [docs/architecture/agent-composition.md](agent-composition.md) — that doc is the orthogonal counterpart on the prompt side.

---

## 0. Layer model

YARNNN is an agent-native operating system per [ADR-222](../adr/ADR-222-agent-native-operating-system-framing.md). The substrate splits across four layers; user-account concerns are a fifth orthogonal channel that doesn't touch workspace substrate at all.

| Layer | What's authored here | Who owns it | Cold-start dependency |
|---|---|---|---|
| **User account** | billing, email, notification prefs | the human, across all their workspaces | none — orthogonal to autonomy |
| **Kernel (workspace-universal)** | MANDATE · IDENTITY · BRAND · AUTONOMY · PRECEDENT · Reviewer principles · Reviewer occupant identity · `_locks.yaml` · YARNNN working memory | operator (authored content) + system (skeletons, audit trails) | MANDATE non-skeleton + AUTONOMY delegated + Reviewer principles authored = autonomy threshold |
| **Program (kernel + program bundle)** | CONVENTIONS · `_operator_profile` · `_risk` · `_universe` · specs · `_recurrences.yaml` · domain folders | program bundle (shipped) + operator (authored-tier overwrite) | bundle forked + authored-tier files overwritten = operational |
| **Agent** | Reviewer substrate (`/workspace/review/*`); user-authored agents would have `AGENT.md` + `memory/` | each agent owns its identity; system writes audit trails | Reviewer occupant declared + principles authored = judgment loop closeable |

**Why IDENTITY and BRAND are workspace-scoped, not user-account-scoped.** The same human can run two workspaces with two distinct operating postures — alpha-trader in one, alpha-prediction in another. IDENTITY is "who the operator is *in this workspace*"; BRAND is "the voice the workforce writes in." Both are workspace-shaping configuration that every agent reads, not biographical facts about the human. Per [ADR-205](../adr/ADR-205-workspace-primitive-collapse.md).

**Why CONVENTIONS is program-scoped, not kernel-seeded.** CONVENTIONS only means something when a program defines vocabulary, time conventions, proposal envelope rules. A generic workspace doesn't need it; the alpha-trader bundle ships it as `tier: canon` with trading-specific rules. The headless base prompt reads it conditionally — present in program workspaces, skipped in generic ones.

**Why agent substrate is currently Reviewer-only.** The Reviewer is the sole *systemic* persona-bearing agent per [ADR-251](../adr/ADR-251-system-agent-reviewer-first-class-surfaces.md). User-authored domain agents are zero-to-many per workspace; when they exist they get `/workspace/agents/{slug}/AGENT.md` + `memory/`. Production roles (researcher, analyst, writer, tracker, designer, reporting) and platform integrations are Orchestration, not Agents — they don't have substrate per [ADR-216](../adr/ADR-216-orchestration-surface-vs-judgment-persona.md).

---

## 1. Spatial inventory — what files exist and who owns them

YARNNN's workspace is a **virtual filesystem of human-readable files** backed by Postgres (`workspace_files` table). Path conventions are the schema. New capabilities extend paths, not database tables. Every mutation produces a content-addressed revision with `authored_by` attribution per [ADR-209](../adr/ADR-209-authored-substrate.md).

### Three top-level roots

| Root | Scope | Owner | Purpose |
|---|---|---|---|
| `/workspace/` | Workspace-level | Operator + System Agent | Identity, conventions, uploads, accumulated context, performance, Reviewer substrate |
| `/workspace/agents/{slug}/` | Per-agent | Agent itself + system audit | WHO — persistent agent identity + memory (currently only Reviewer at `/workspace/review/`; domain agents at `/workspace/agents/{slug}/`) |
| `/workspace/{reports,operations}/{slug}/` | Per-recurrence | System | WHAT — recurrence declarations + run logs + outputs per [ADR-231](../adr/ADR-231-task-abstraction-sunset.md) D2 |

**Dissolved roots** (preserved here for orientation; do not write to them):
- `/knowledge/` — dissolved into `/platforms/` then into `/workspace/context/` per ADR-142 + ADR-153
- `/memory/` — merged into `/workspace/memory/` per ADR-206
- `/user_shared/` — dissolved into session-scoped uploads per ADR-142
- `/platforms/` — DEPRECATED per ADR-153; platform data flows through tracking tasks into `/workspace/context/` domains
- `/tasks/{slug}/` — DELETED per ADR-231 D2; replaced by per-shape natural homes (`reports/{slug}/`, `operations/{slug}/`, `context/{domain}/_recurring.yaml`, `_shared/back-office.yaml`)

### `/workspace/` — full tree

```
/workspace/
├── context/
│   ├── _shared/                    ← kernel-authored standing configuration
│   │   ├── MANDATE.md              ← Workspace north star + success criteria + boundaries [K]
│   │   ├── IDENTITY.md             ← Who the operator is in this workspace [K]
│   │   ├── BRAND.md                ← Output voice / visual style [K]
│   │   ├── AUTONOMY.md             ← Prose delegation documentation (human/LLM read only) [K]
│   │   ├── _autonomy.yaml          ← Machine-parsed delegation config (ADR-254) [K]
│   │   ├── PRECEDENT.md            ← Durable interpretations / boundary cases [K]
│   │   ├── CONVENTIONS.md          ← Program-specific structural rules (not kernel-seeded) [P]
│   │   ├── _locks.yaml             ← Operator-authored Reviewer write-path locks (ADR-258) [K, optional]
│   │   ├── back-office.yaml        ← MAINTENANCE recurrence declarations (ADR-231) [P]
│   │   └── back-office-audit.md    ← Append-only back-office audit log [P]
│   ├── {domain}/                   ← accumulated intelligence per domain (ADR-151)
│   │   ├── _tracker.md             ← System: per-entity freshness registry (hidden)
│   │   ├── _recurring.yaml         ← ACCUMULATION recurrence declarations for this domain (ADR-231)
│   │   ├── _performance.md         ← Money-truth per domain (ADR-195) [SYS]
│   │   ├── _feedback.md            ← Source-agnostic feedback (ADR-181)
│   │   ├── _run_log.md             ← Recurrence run log
│   │   ├── {entity-slug}/          ← Per-entity folder
│   │   │   ├── profile.md
│   │   │   ├── signals.md
│   │   │   └── ...
│   │   ├── assets/                 ← Domain-level visual assets (ADR-157)
│   │   └── landscape.md            ← Cross-entity synthesis (agent-written)
│   ├── _performance_summary.md     ← Cross-domain rolling-window money-truth (ADR-195 P3) [SYS]
│   ├── slack/  notion/  github/    ← Platform-bot temporal observations (ADR-158)
│   └── signals/                    ← Cross-domain temporal signal log (no tracker)
├── memory/                         ← YARNNN working memory (ADR-206 relocation)
│   ├── awareness.md                ← Shift handoff notes (cross-session)
│   ├── _playbook.md                ← Orchestration playbook (hidden)
│   ├── style.md                    ← Inferred style from edit patterns
│   └── notes.md                    ← YARNNN-extracted facts and standing instructions
├── review/                         ← Reviewer substrate (ADR-194 v2)
│   ├── IDENTITY.md                 ← Reviewer occupant identity (operator-authored persona)
│   ├── principles.md               ← Declared judgment framework (operator-editable, ADR-253)
│   ├── _principles.yaml            ← Machine-parsed thresholds (ADR-254)
│   ├── OCCUPANT.md                 ← Current seat occupant (rotates)
│   ├── handoffs.md                 ← Append-only occupant-rotation log
│   ├── decisions.md                ← Append-only verdict trail (ADR-194 Phase 2a)
│   └── calibration.md              ← Auto-generated judgments-vs-outcomes
├── agents/{slug}/                  ← User-authored domain agents only (zero-to-many)
│   ├── AGENT.md
│   ├── memory/
│   │   └── playbook-*.md
│   └── style.md
├── reports/{slug}/                 ← DELIVERABLE-shape recurrences (ADR-231 D2)
│   ├── _spec.yaml                  ← Recurrence declaration
│   ├── _feedback.md
│   ├── _run_log.md
│   └── {date}/output.md            ← Per-firing output (replacive; latest is canonical)
├── operations/{slug}/              ← ACTION-shape recurrences (ADR-231 D2)
│   ├── _action.yaml
│   └── _run_log.md
├── uploads/                        ← User-uploaded reference material (permanent)
│   └── {slugified-name}.md
├── _recurrences.yaml               ← Operator-authored top-level recurrence index (ADR-261)
└── working/                        ← Ephemeral scratch (24h TTL)
```

**Legend.** `[K]` = kernel-seeded at signup. `[P]` = program-supplied (only present when a program bundle is forked). `[SYS]` = system-written aggregate. Unmarked paths accumulate from work.

### File naming convention (ADR-156)

One glance tells you ownership:

| Convention | Meaning | Writer | Visible in explorer? |
|---|---|---|---|
| **UPPERCASE.md** | Charter / identity — defines who/what/why | Operator + System Agent | Yes |
| **lowercase.md** | Content — notes, feedback, synthesis, runs | Operator + System Agent + agents | Yes |
| **_prefixed.md/yaml** | System infrastructure — derived, pipeline-managed | Pipeline / system | No (hidden) |

**Frontend rule:** any file whose name starts with `_` is hidden from the operator's filesystem explorer. One rule, no exceptions.

### File ownership / lifecycle classification

Eight categories cover the operator-relevant universe:

| Code | Meaning | Examples |
|---|---|---|
| **K-S** | Kernel-seeded skeleton (every workspace, empty initially) | `/workspace/context/_shared/MANDATE.md`, `/workspace/memory/awareness.md`, `/workspace/review/principles.md` |
| **K-A** | Kernel-seeded but operator-authored on first edit (skeleton → rich) | Most `[K]` files above transition K-S → K-A on operator edit |
| **P-C** | Program-bundle canon (forked verbatim, operator typically doesn't edit) | Alpha-trader's `_autonomy.yaml` (`tier: canon`), CONVENTIONS.md |
| **P-A** | Program-bundle authored (forked as template, operator MUST overwrite) | `_operator_profile.md`, `_risk.md`, `_universe.yaml`, `_principles.yaml` |
| **P-P** | Program-bundle placeholder (empty skeleton in bundle, fills from work) | Per-ticker `{ticker}.yaml`, signal fires, `_performance.md` |
| **AGT** | Agent-scoped (currently only Reviewer + user-authored agents) | `/workspace/review/decisions.md`, `/workspace/agents/{slug}/AGENT.md` |
| **MEM** | YARNNN memory (system-written, operator may read) | `/workspace/memory/style.md`, `notes.md` |
| **SYS** | System-written aggregates (performance, calibration, audit, run logs) | `_performance.md`, `decisions.md`, `_run_log.md`, `back-office-audit.md`, `reports/{slug}/{date}/output.md` |

### Lifecycle column on `workspace_files` (ADR-119)

| Value | Meaning |
|---|---|
| `active` | Normal operational file |
| `permanent` | User-curated, never auto-cleaned (e.g. `/workspace/uploads/`) |
| `ephemeral` | Temporary — auto-cleaned after TTL (e.g. `/working/` 24h) |
| `delivered` | Output that has been delivered |
| `archived` | Previous version kept for history |

### Conventions for new files

1. Use existing directories first. Don't create new top-level roots.
2. Use `.md` for content, `.yaml` for machine-parsed config, `.json` only for manifests (ADR-254 format discipline).
3. UPPERCASE for charter/identity (`AGENT.md`, `TASK.md` legacy, `IDENTITY.md`, `MANDATE.md`).
4. lowercase-kebab-case for user/agent-created content files.
5. `_prefix` for system infrastructure (hidden from explorer).
6. Date-stamp temporal content (`2026-03-25/` for daily outputs).
7. Prefer folders as boundaries — new coordination needs become subfolders, not new tables.
8. Accumulated context goes in `/workspace/context/{domain}/`. New domains must be added to the directory registry per ADR-151; no ad-hoc context folders.

---

## 2. Temporal bootstrap — what gets seeded when

`services.workspace_init.initialize_workspace()` is the single function that bootstraps a workspace. It runs in three situations:

| Trigger | Code path |
|---|---|
| First login (no agents exist) | `GET /api/workspace/state` lazy-scaffold gate |
| L2 workspace reset | `DELETE /account/workspace` reinit phase |
| L4 full account reset | `DELETE /account/reset` reinit phase |

It is idempotent — each phase checks before writing.

### Phase 1 — System Agent row

Creates one `agents` row with `role='thinking_partner'`, `origin='system_bootstrap'`. This is the sole infrastructure row at signup per [ADR-205](../adr/ADR-205-workspace-primitive-collapse.md).

Production roles (researcher, analyst, writer, tracker, designer, reporting) are lazy-created on first dispatch. Platform integration capability bundles are connection-bound — they materialize at OAuth connect, not signup.

### Phase 2 — Kernel-seeded skeleton files

Writes the files marked `[K]` in the inventory above via `UserMemory.write` (→ `authored_substrate.write_revision`, attributed `system:workspace_init`). The full kernel set is enumerated in [`api/services/workspace_paths.py::SHARED_CONTEXT_FILES`](../../api/services/workspace_paths.py).

**Note:** `CONVENTIONS.md` is *not* in this set. It is program-scoped — only written when a program bundle forks it. See §3 below for the program-activation flow.

`PRECEDENT.md` starts as a skeleton at signup but is not prompted upfront. It accumulates durable interpretations over time, written by the System Agent or Reviewer when a boundary-case decision warrants a permanent ruling:

```python
WriteFile(scope="workspace", path="context/_shared/PRECEDENT.md",
          content="### <slug>\n- Scope: ...\n- Rule: ...\n- Why: ...\n",
          mode="append")
```

`dispatch_helpers.gather_task_context()` reads it and injects into every headless task execution context.

### Phase 3 — Workspace narrative session

Creates a `chat_sessions` row (type=`thinking_partner`, no `agent_id`, no `task_slug`). This is the workspace-scoped narrative log that all autonomous writers (task pipeline, reviewer verdicts, back-office, MCP) target from day one. Without it, narrative entries before the operator opens `/chat` would be lost permanently.

### Phase 4 — Signup balance audit trail

Writes a `signup_grant` row to `balance_transactions` ($3.00 per ADR-172 schema DEFAULT). Only runs on fresh init (`already_initialized=False`).

### Phase 5 — Reference-workspace fork (optional)

When `program_slug` is provided, delegates to `services.programs.fork_reference_workspace()`. Walks the bundle's `reference-workspace/` directory and writes files honoring three-tier categorization (ADR-223 §5):

| Tier | Rule |
|---|---|
| `canon` | Re-applied on every fork; operator edits preserved as prior revisions per ADR-209 |
| `authored` | Applied only when operator file is still skeleton; operator-authored content preserved |
| `placeholder` | Applied on first fork only; never overwritten |

This phase is what turns a kernel-only workspace into a program-shaped one. Phases 1–4 are kernel-universal; Phase 5 is optional and reversible (`POST /api/programs/deactivate` strips the program marker but preserves operator-authored content per [ADR-244](../adr/ADR-244-workspace-settings-surface.md)).

### Scheduling index — materialized at fork time

The `tasks` table is a thin scheduling index over `/workspace/_recurrences.yaml` per ADR-261 D3. The YAML is truth; the table holds `next_run_at` + `last_run_at` per `(user_id, slug)` so the scheduler can do fast due-time queries with CAS atomic claims. The two writers of the canonical YAML each call `services.scheduling.materialize_scheduling_index()` immediately after the write:

- `services.programs.fork_reference_workspace` — bundle activation (signup, `/api/programs/activate`, L2/L4 reset reinit). When the fork touches `_recurrences.yaml`, the index is built before the function returns.
- `services.primitives.schedule.handle_schedule` — operator-driven mutations via `Schedule(action=create|update|pause|resume|archive)`. The post-write materialize syncs schedule changes, applies `paused` flips, and drops index rows whose recurrence was archived.

The materialize call is idempotent and safe to invoke from either site. A freshly-activated workspace has a coherent scheduling index the moment the activation HTTP call returns.

### Back-office tasks — trigger-materialized, not signup-scaffolded

Per ADR-206, zero operational tasks are scaffolded at signup. Back-office tasks materialize via `services.back_office.materialize_back_office_task()` on trigger:

| Task | Trigger |
|---|---|
| `back-office-proposal-cleanup` | First `ProposeAction` call |
| `back-office-outcome-reconciliation` | First commerce or trading platform connect |
| `back-office-reviewer-calibration` | Same as outcome-reconciliation |
| `back-office-reviewer-reflection` | Same as outcome-reconciliation |

`materialize_back_office_task` lives in `services.back_office` (relocated 2026-05-03 from `workspace_init.py` — it is lifecycle management, not initialization).

### Skeleton detection — single implementation

Three callers previously had diverging skeleton-detection heuristics. As of 2026-05-03 all three delegate to `services.workspace_utils.is_skeleton_content()`:

- `services.workspace_init` — fork idempotency (`authored` tier only re-applied when skeleton)
- `routes/workspace._classify_file_state` — `/workspace` surface substrate status panel
- `services.working_memory._classify_activation_state` — MANDATE.md skeleton → `post_fork_pre_author`

### First-run user flow

```
1. OAuth / magic-link → /auth/callback
2. Supabase session established
3. GET /api/workspace/state
   → Server: zero agents? → initialize_workspace()
   → activation_state == "none" && no active program?
     → redirect /workspace?first_run=1
   → otherwise → HOME_ROUTE (/chat)
4. /workspace (first_run=1)
   → Operator picks a program (or skips → chat)
5. POST /api/programs/activate (if program picked)
   → fork_reference_workspace() runs
   → activation_state → "post_fork_pre_author"
6. Operator authors authored-tier files via YARNNN chat or direct substrate edit
   → activation_state → "operational"
   → Schedule(create) hard gate unblocked
7. YARNNN scaffolds first recurrences + fires them immediately
```

**Without program activation** (generic workspace): operator lands on `/chat` directly, YARNNN's Mandate-first elicitation engages (from `onboarding.py` `CONTEXT_AWARENESS`), operator authors MANDATE in conversation. Recurrences can be created once MANDATE is non-skeleton.

---

## 3. Autonomy threshold — what does autonomous operation actually require?

A workspace is "autonomous" when it can fire scheduled work without operator intervention and the Reviewer can adjudicate proposals within delegated bounds. Three load-bearing conditions, none independently sufficient:

### Condition A — MANDATE non-skeleton (workspace minimum)

MANDATE.md must declare a Primary Action and success criteria per [ADR-207](../adr/ADR-207-primary-action-centric-workflow.md). Until non-skeleton:

- `Schedule(action='create', ...)` returns an error (hard gate at primitive layer)
- YARNNN's CONTEXT_AWARENESS prompt prioritizes mandate elicitation
- No recurrences fire; the workspace is in "knowledge mode" only

The mandate gate is the architectural floor for autonomous operation. It exists because firing recurrences without a declared mandate produces work that can't be evaluated against any standard.

### Condition B — Autonomy delegated (operator authorization)

`AUTONOMY.md` + `_autonomy.yaml` must declare a delegation level beyond `manual` per [ADR-217](../adr/ADR-217-autonomy-ceiling-substrate.md). The four levels:

| Level | Behavior |
|---|---|
| `manual` | Every proposal routes to operator queue; nothing auto-executes |
| `bounded` | Proposals under `ceiling_cents` auto-execute if Reviewer approves; over-ceiling route to queue |
| `autonomous` | Reviewer's approval is execution; queue is bypass-only |
| (paused) | Time-bounded circuit breaker via `paused_until` (ADR-248) |

Autonomy is *operator-authored, not system-default*. A workspace with delegation=`manual` and a non-skeleton MANDATE is still partially autonomous (recurrences fire and produce proposals) — it's just that consequential actions still wait for the operator.

### Condition C — Reviewer principles authored (judgment loop closeable)

`/workspace/review/principles.md` + `_principles.yaml` must declare the evaluation framework the Reviewer applies per [ADR-253](../adr/ADR-253-reviewer-substrate-native-agent.md). The Reviewer is the sole independent judgment seat per [ADR-194 v2](../adr/ADR-194-reviewer-layer-and-operator-impersonation.md) — without authored principles, the Reviewer falls back to a generic default that can't evaluate domain-shaped proposals (capital risk, brand fit, customer-segment alignment, etc.).

The Reviewer occupant identity (`/workspace/review/IDENTITY.md`) is also load-bearing — it embodies the persona that *applies* the principles (Simons, Buffett, Deming, or operator-authored original). Same seat, swappable occupant per ADR-194 v2.

### Program-activated minimum (additional)

When a program bundle is active, the bundle's `tier: authored` files must be overwritten — the bundle ships skeleton templates that the operator MUST customize:

- alpha-trader: `_operator_profile.md`, `_risk.md`, `_universe.yaml`, Reviewer `_principles.yaml`
- alpha-commerce: equivalents (when activated)

These are surfaced one-by-one through the ACTIVATION_OVERLAY (`api/agents/prompts/chat/activation.py`) when activation_state is `post_fork_pre_author`.

### Activation state machine

Per ADR-244 + ADR-226, `workspace_state.activation_state` enum:

| State | Meaning | What's true |
|---|---|---|
| `none` | No program activated; kernel-only | Generic workspace; Schedule gate depends only on MANDATE |
| `post_fork_pre_author` | Program forked but authored-tier files still skeleton | Activation overlay engaged; recurrences blocked until authored files filled |
| `operational` | All authored-tier files non-skeleton | Recurrences fire; autonomous loop available |

`active_program_slug` is a separate signal — derived from MANDATE.md's program-marker heading line per ADR-244. The two enums together describe the workspace's autonomy posture.

---

## 4. The autonomy loop

Once the autonomy threshold is met (§3), the workspace runs a closed loop: trigger wakes Reviewer → Reviewer reads substrate + assembles prompt → tool-use loop produces verdict → dispatcher gates execution against autonomy policy → outcome lands in substrate → next cycle reads it. This section traces the loop end-to-end. Prompt-assembly mechanics live in [agent-composition.md](agent-composition.md); what follows is the substrate-and-dispatch view.

### 4.1 Triggers — two shapes (post ADR-263 D2)

Per [ADR-263 D2](../adr/ADR-263-recurrence-mode-mechanical-vs-judgment.md) the Reviewer trigger taxonomy collapsed from four to two. `proposal | reflection | heartbeat | addressed` (ADR-256 original) → `reactive | addressed` (ADR-260 → ADR-263).

| Trigger | Entry point | When | Pre-loaded context |
|---|---|---|---|
| `reactive` | `services/review_proposal_dispatch.py::on_proposal_created` | An `action_proposals` row is inserted (operator/agent proposes an action) | Proposal row + domain substrate (`_performance.md`, `principles.md`, `IDENTITY.md`, `PRECEDENT.md`, `_risk.md`, `_operator_profile.md`) |
| `reactive` | `services/invocation_dispatcher.py::dispatch` when `recurrence.mode == "judgment"` | A judgment-mode recurrence fires on its cron | Recurrence prompt + signal files + workspace_state + last 7d `decisions.md` |
| `addressed` | `agents/yarnnn.py::execute_stream_with_tools` chat-executor flow | Operator addresses YARNNN in chat with a turn that requires judgment | All pre-loaded substrate + operator message + conversation window |
| (not a trigger) | `services/invocation_dispatcher.py::_dispatch_mechanical` | A `mechanical`-mode recurrence fires on its cron (e.g. `SyncPlatformState`) | No Reviewer invocation — pure deterministic Python writes substrate; the next reactive/addressed wake reads what mechanical wrote |

Mechanical-mode recurrences are not a trigger — they're substrate sensors per [ADR-264](../adr/ADR-264-substrate-canonical-world.md) that keep the substrate the Reviewer reads fresh between Loop wake-ups.

### 4.2 Substrate reads on wake

On wake the Reviewer receives a pre-loaded context bundle assembled by the dispatcher. Once inside the tool-use loop it can call `ReadFile` to fetch any other substrate path on demand. The pre-loaded set:

| File | Role at reasoning time |
|---|---|
| `/workspace/review/IDENTITY.md` | Persona embodiment — operator-authored character traits framing judgment. Empty → neutral skeptical baseline. |
| `/workspace/review/principles.md` | Framework constraints — operator's stated evaluation thresholds in prose. Empty → "no declared framework" fallback. |
| `/workspace/review/_principles.yaml` | Machine-parsed thresholds. Loaded at *dispatch* time (not Reviewer reasoning) via `services.review_policy.load_principles()`. |
| `/workspace/context/_shared/MANDATE.md` | Operation's primary intent — the reason the Reviewer exists. |
| `/workspace/context/_shared/AUTONOMY.md` | Prose delegation declaration (legibility for human/LLM; not parsed). |
| `/workspace/context/_shared/_autonomy.yaml` | Machine-parsed delegation policy. Loaded at *dispatch* time via `services.review_policy.load_autonomy()` — drives `should_auto_execute_verdict()`. |
| `/workspace/context/_shared/PRECEDENT.md` | Durable interpretations / boundary-case rulings. Filters reasoning over substrate; overrides principles per prompt framing. |
| `/workspace/context/{domain}/_performance.md` | Money-truth track record per domain (rolling 7d/30d/90d, ADR-195 v2 Phase 3). |
| `/workspace/context/{domain}/_operator_profile.md` | Domain strategy + operator style. Program-supplied for active programs. |
| `/workspace/context/{domain}/_risk.md` | Hard floors / risk envelope. Trading-specific; ceiling enforcement source per ADR-192. |
| `/workspace/review/decisions.md` | Reviewer's own prior verdicts. Not pre-loaded; available via on-demand `ReadFile` for self-consistency review. |

### 4.3 Prompt assembly + tool-use loop

See [agent-composition.md §Reviewer prompt assembly](agent-composition.md) for the canonical assembly mechanics. In summary: system prompt is a platform-fixed `_PERSONA_FRAME` + auto-generated cockpit-awareness section from `cockpit_awareness.py` (composed at module load from path constants + `REVIEWER_PRIMITIVES` registry — never drifts from runtime). User message is dispatcher-assembled with persona → framework (principles + precedent) → substrate → trigger-specific framing.

Bounded loop: Sonnet (proposal-arrival reactive) = 3 rounds max; Haiku (recurrence-fire reactive + addressed) = 12 rounds max. The Reviewer closes by calling `ReturnVerdict`. Per-round prompt nudges enforce convergence.

### 4.4 Verdict dispatch

The Reviewer emits a `ReviewerOutput` TypedDict — `{verdict, reasoning, confidence, actions_taken, proposals?, evidence_summary?, directives?}`. Verdict types: `approve | reject | defer | stand_down` (proposal/recurrence) or `no_change | narrow | relax | character_note | pause_autonomy` (reflection recurrence). Dispatch routing per ADR-229 D1:

**Approve** → `services.review_policy.should_auto_execute_verdict()` reads `_autonomy.yaml` and decides:
- **Pause active** (`paused_until > now`) → advisory queue, regardless of delegation
- **`delegation: manual`** → advisory queue (operator must click Approve)
- **`delegation: autonomous`** → `handle_execute_proposal` fires the platform tool
- **`delegation: bounded`** → ceiling check against `proposal.estimated_cents` vs `ceiling_cents`; under → execute; over → advisory queue
- **Missing `ceiling_cents` on bounded** → advisory queue ("no ceiling_cents set")
- **Missing `estimated_cents` on proposal** → advisory queue ("no estimated value") — this is the trading-specific failure mode when `_risk.md` is skeleton

**Reject** → `handle_reject_proposal` marks proposal `status="rejected"`; not autonomy-gated (Reviewer's narrowing is always binding).

**Defer** → records observation entry; if `directives` array present, the dispatcher executes each directive (`fire_invocation` / `write_file` to `/workspace/review/*` / `clarify`) per [ADR-253 D2](../adr/ADR-253-reviewer-substrate-native-agent.md).

**Stand_down** → observation entry only; loop closes with no action.

Every verdict appends to `/workspace/review/decisions.md` via `services.reviewer_audit.append_decision()` with `authored_by="reviewer:{occupant}"` per ADR-209.

### 4.5 Outcome reconciliation + calibration recursion

Execution side-effects land at the platform (broker, commerce provider, Slack, etc.). The loop closes through two back-office paths:

**Outcome reconciliation** — daily `back-office-outcome-reconciliation` recurrence calls `services.outcomes.ledger.fold_outcome_candidates()`. Reads `last_reconciled_at` from the domain's `_performance.md` frontmatter, fetches platform events since, writes:
- `/workspace/context/{domain}/_performance.md` — rolling 7d/30d/90d totals, processed-event-keys (idempotency), by-action breakdown, recent narrative
- `/workspace/context/_performance_summary.md` — cross-domain rollup (`services.outcomes.ledger.write_performance_summary()` line 710)

High-impact outcomes (above `_principles.yaml::high_impact_threshold_cents`) additionally route to `/workspace/context/{domain}/_feedback.md` per [ADR-181 Phase 5a](../adr/ADR-181-source-agnostic-feedback-layer.md).

**Reviewer calibration** — periodic `back-office-reviewer-reflection` recurrence (judgment mode) wakes the Reviewer with prior decisions + `_performance_summary.md`. Reviewer's verdict types are different here (`no_change | narrow | relax | character_note | pause_autonomy`). Verdicts can mutate `principles.md` or write `paused_until` to `_autonomy.yaml` per [ADR-248 D3](../adr/ADR-248-reviewer-periodic-pulse.md) as a time-bounded circuit breaker.

**Closure.** Next reactive/addressed wake reads the updated `_performance.md` + calibrated `principles.md`. The substrate IS the bus per [FOUNDATIONS Axiom 1 fourth sub-clause](FOUNDATIONS.md) — there is no parallel control-flow channel between cycles. Mechanical-mode recurrences sit at the deterministic end of this same architecture, keeping external state mirrored into substrate between wake-ups.

---

## 5. Cold-start failure modes

Definitive catalog: for each prerequisite, what specifically breaks at runtime and how to recover. This is the foundation for testing playbooks — every row below is a testable assertion.

| Prerequisite | If missing / skeleton | Severity | Recovery |
|---|---|---|---|
| **MANDATE.md skeleton** | Reviewer wakes with neutral frame; cockpit shows "mandate needed" CTA; recurrences not auto-fired (Schedule gate). Reviewer still adjudicates evidence — no auto-execution because no operation context. | **Operational blocker for autonomy** | Author MANDATE.md (via chat or direct edit) — Schedule gate unblocks once non-skeleton |
| **IDENTITY.md skeleton** | Reviewer defaults to neutral skeptical baseline (`reviewer_agent.py:438`). Verdicts render but lack persona voice. | Non-blocking (acceptable cold-start) | Operator authors persona later via chat |
| **principles.md skeleton** | Reviewer has no framework. User message says "no declared framework." Verdict renders on EV grounds against MANDATE + `_performance.md` only. | Non-blocking | Framework builds over time via reflection-recurrence calibration |
| **_principles.yaml empty/missing** | `services.review_policy.load_principles()` returns `{}`. High-impact threshold detection skipped → all outcomes treated as routine, no high-impact feedback routing per ADR-181. | Non-blocking | Authored by operator or system at activation |
| **AUTONOMY.md skeleton (prose only)** | Documentation gap; not load-bearing. Gate reads `_autonomy.yaml`. | Non-blocking | Author for legibility |
| **`_autonomy.yaml` skeleton / missing** | `load_autonomy()` returns `{}` → `should_auto_execute_verdict()` defaults to `delegation="manual"` → **every approve verdict becomes advisory**. Reviewer adjudicates, nothing auto-executes. | **CRITICAL — disables autonomy entirely** | Author `_autonomy.yaml` with `delegation: bounded` (+ `ceiling_cents`) or `autonomous` |
| **`_autonomy.yaml` `delegation: manual`** | Every approve verdict routes to operator-approval queue (by design). | By design | Change to `bounded` or `autonomous` when ready |
| **`_autonomy.yaml` `paused_until > now`** | Gate returns False before delegation check; circuit-breaker mode. | By design (ADR-248 D3) | Wait for expiry or manual unpause |
| **Reviewer OCCUPANT.md never authored** | No failure — OCCUPANT.md is metadata, not gating. Reviewer wakes normally; IDENTITY + principles drive persona. | No impact | None needed |
| **Program bundle active + `_operator_profile.md` skeleton** | Reviewer wakes without domain strategy context. Verdicts lack strategy framework. Activation overlay engaged per ADR-226. | Non-blocking but degraded judgment | Author via activation overlay walkthrough |
| **Program bundle active + `_risk.md` skeleton (trading)** | Proposal value estimation returns None → ceiling check fails → **trading autonomy disabled per-domain** even with `_autonomy.yaml: autonomous`. | **CRITICAL for trading workspaces** | Author `_risk.md` before trading recurrences fire |
| **All four (MANDATE + AUTONOMY + principles + `_operator_profile`) skeleton** | Reviewer judges on `_performance.md` only; if also empty, defers. No auto-execution. Activation overlay is recovery path. | Critical | Activation overlay walkthrough or chat-driven authoring |

**The single load-bearing fact about autonomy:** even with everything else authored, `_autonomy.yaml` missing or skeleton silently routes every Reviewer approval to the operator-approval queue. Reviewer judgment is correct; nothing happens automatically. **This is the first thing a cold-start playbook must verify.**

For trading workspaces specifically: `_autonomy.yaml` authored AND `_risk.md` authored are both required for the autonomous loop to actually fire trades. Either alone is insufficient.

---

## 6. Key files

| File | Role |
|---|---|
| [api/services/workspace_init.py](../../api/services/workspace_init.py) | `initialize_workspace()` — the 5-phase init function |
| [api/services/workspace_paths.py](../../api/services/workspace_paths.py) | Canonical path constants; `SHARED_CONTEXT_FILES` (kernel-seeded set); `DEFAULT_REVIEWER_WRITE_LOCKS` |
| [api/services/workspace_utils.py](../../api/services/workspace_utils.py) | `is_skeleton_content()` + `classify_file_state()` — shared heuristics |
| [api/services/programs.py](../../api/services/programs.py) | `fork_reference_workspace()`, `_strip_tier_frontmatter()`, `parse_active_program_slug()`, `strip_program_marker_from_mandate()` |
| [api/services/scheduling.py](../../api/services/scheduling.py) | `materialize_scheduling_index()` — idempotent recurrences-YAML → `tasks`-index sync |
| [api/services/primitives/schedule.py](../../api/services/primitives/schedule.py) | `handle_schedule()` — operator-driven recurrence mutations |
| [api/services/back_office/__init__.py](../../api/services/back_office/__init__.py) | `materialize_back_office_task()` — trigger-based back-office lifecycle |
| [api/routes/workspace.py](../../api/routes/workspace.py) | `GET /api/workspace/state` — lazy scaffold + activation state surface |
| [api/routes/account.py](../../api/routes/account.py) | `DELETE /account/workspace` (L2) and `DELETE /account/reset` (L4) — purge + reinit |
| [web/app/auth/callback/page.tsx](../../web/app/auth/callback/page.tsx) | First-run redirect gate |
| [web/components/settings/WorkspaceSection.tsx](../../web/components/settings/WorkspaceSection.tsx) | `/workspace` surface (program lifecycle + substrate status) |

## 7. Related

- [docs/design/WORKSPACE.md](../design/WORKSPACE.md) — operator-facing surface contracts (the design counterpart to this doc)
- [docs/architecture/agent-composition.md](agent-composition.md) — **how agents read this substrate at reasoning time** (prompt assembly, profile selection, cockpit awareness). Orthogonal counterpart to this doc on the prompt side.
- [docs/architecture/FOUNDATIONS.md](FOUNDATIONS.md) — axioms (Substrate, Identity, Purpose, Trigger, Mechanism, Channel); v8.4 hardening on substrate-as-the-bus + operator-as-one-principal-with-two-embodiments
- [docs/architecture/SERVICE-MODEL.md](SERVICE-MODEL.md) — end-to-end service model
- [docs/architecture/authored-substrate.md](authored-substrate.md) — ADR-209 deep dive (revision chain, attribution)
- [docs/architecture/compositor.md](compositor.md) — kernel/program seam for surface composition
- [docs/architecture/reviewer-substrate.md](reviewer-substrate.md) — Reviewer-specific file inventory
- [docs/programs/README.md](../programs/README.md) — program bundle registry
