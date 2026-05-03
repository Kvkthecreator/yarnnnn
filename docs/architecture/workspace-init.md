# Workspace Initialization

**Status:** Canonical (2026-05-03)
**Supersedes:** `docs/design/SHARED-CONTEXT-WORKFLOW.md`, `docs/design/ONBOARDING-TP-AWARENESS.md`, `docs/design/USER-JOURNEY.md` (archived)
**ADRs:** 205, 206, 207, 209, 219, 223, 226, 244

---

## What initialization does

`services.workspace_init.initialize_workspace()` is the single function that bootstraps a workspace. It runs in three situations:

| Trigger | Code path |
|---------|-----------|
| First login (no agents exist) | `GET /api/workspace/state` lazy-scaffold gate |
| L2 workspace reset | `DELETE /account/workspace` reinit phase |
| L4 full account reset | `DELETE /account/reset` reinit phase |

It is idempotent — each phase checks before writing.

---

## The 5 phases

### Phase 1 — YARNNN agent row

Creates one `agents` row with `role='thinking_partner'`, `origin='system_bootstrap'`. This is the sole infrastructure row at signup per ADR-205.

Production roles (researcher, analyst, writer, tracker, designer, reporting) are lazy-created on first dispatch. Platform integration capability bundles are connection-bound — they materialize at OAuth connect, not signup.

### Phase 2 — Kernel-seeded skeleton files

Writes these files via `UserMemory.write` (→ `authored_substrate.write_revision`, attributed `system:workspace_init`):

**Authored shared context** (`/workspace/context/_shared/`):

| File | Purpose | Notes |
|------|---------|-------|
| `MANDATE.md` | Workspace north star — Primary Action + success criteria + boundary conditions | Hard gate: `ManageRecurrence(create)` blocked until non-skeleton |
| `IDENTITY.md` | Who the operator is | Inflated with browser timezone if `X-Timezone` header present |
| `BRAND.md` | Visual style and voice | Empty skeleton; inference populates |
| `AUTONOMY.md` | Delegation ceiling for AI judgment (level, ceiling_cents, never_auto) | `manual` default; operator authors |
| `PRECEDENT.md` | Durable interpretations and boundary-case decisions | Accumulates over time; not prompted at signup |

**NOT seeded:** `CONVENTIONS.md` — this file is program-scoped, not kernel-scoped. See below.

**YARNNN working memory** (`/workspace/memory/`):

| File | Purpose |
|------|---------|
| `awareness.md` | Shift handoff notes across sessions |
| `_playbook.md` | Orchestration playbook (team composition, capability discipline) |
| `style.md` | Inferred style from edit patterns |
| `notes.md` | Extracted stable facts |

**Reviewer substrate** (`/workspace/review/`):

| File | Purpose |
|------|---------|
| `IDENTITY.md` | Who the Reviewer seat is (role-level, static) |
| `principles.md` | Declared judgment framework (operator-editable) |
| `OCCUPANT.md` | Current seat occupant — seeded via `review_rotation.rotate_occupant()` |
| `handoffs.md` | Append-only occupant-rotation log |
| `calibration.md` | Auto-generated judgments-vs-outcomes trail |

### Phase 3 — Workspace narrative session

Creates a `chat_sessions` row (type=`thinking_partner`, no `agent_id`, no `task_slug`). This is the workspace-scoped narrative log that all autonomous writers (task pipeline, reviewer verdicts, back-office, MCP) target from day one. Without it, narrative entries before the operator opens `/chat` are lost permanently.

### Phase 4 — Signup balance audit trail

Writes a `signup_grant` row to `balance_transactions` ($3.00 per ADR-172 schema DEFAULT). Only runs on fresh init (`already_initialized=False`).

### Phase 5 — Reference-workspace fork (optional)

When `program_slug` is provided, delegates to `services.programs.fork_reference_workspace()`. Walks the bundle's `reference-workspace/` directory and writes files honoring three-tier categorization (ADR-223 §5):

| Tier | Rule |
|------|-----|
| `canon` | Re-applied on every fork; operator edits preserved as prior revisions per ADR-209 |
| `authored` | Applied only when operator file is still skeleton; operator-authored content preserved |
| `placeholder` | Applied on first fork only; never overwritten |

---

## CONVENTIONS.md — program-scoped, not kernel-scoped

`CONVENTIONS.md` is present only when a program bundle forks it. For example, the alpha-trader bundle ships `CONVENTIONS.md` with `tier: canon` declaring proposal envelope rules, vocabulary discipline, and time conventions specific to trading.

Generic workspaces do not have a CONVENTIONS.md. That is correct — the file only means something when a program defines it.

The headless base prompt references it conditionally:
> "Program-specific conventions (if present): `ReadFile(path="/workspace/context/_shared/CONVENTIONS.md")` — only exists on program workspaces; skip if absent."

**Do not prompt operators to author CONVENTIONS.md.** Do not seed it at init.

---

## PRECEDENT.md — accumulates, not authored upfront

`PRECEDENT.md` starts as a skeleton at signup. It accumulates durable interpretations — boundary-case decisions that should shape future behavior workspace-wide. YARNNN writes to it when a specific edge case warrants a permanent ruling:

```
WriteFile(scope="workspace", path="context/_shared/PRECEDENT.md",
          content="### <slug>\n- Scope: ...\n- Rule: ...\n- Why: ...\n",
          mode="append")
```

It is read by `dispatch_helpers.gather_task_context()` and injected into every headless task execution context. Do not prompt operators to fill it upfront.

---

## Back-office tasks — trigger-materialized, not signup-scaffolded

Per ADR-206, zero operational tasks are scaffolded at signup. Back-office tasks materialize via `services.back_office.materialize_back_office_task()` on trigger:

| Task | Trigger |
|------|---------|
| `back-office-proposal-cleanup` | First `ProposeAction` call |
| `back-office-outcome-reconciliation` | First commerce or trading platform connect |
| `back-office-reviewer-calibration` | Same as outcome-reconciliation |
| `back-office-reviewer-reflection` | Same as outcome-reconciliation |

`materialize_back_office_task` lives in `services.back_office` (relocated 2026-05-03 from `workspace_init.py` — it is lifecycle management, not initialization).

---

## First-run user flow

```
1. OAuth / magic-link → /auth/callback
2. Supabase session established
3. GET /api/workspace/state
   → Server: zero agents? → initialize_workspace()
   → activation_state == "none" && no active program?
     → redirect /settings?tab=workspace&first_run=1
   → otherwise → HOME_ROUTE (/chat)
4. /settings?tab=workspace (first_run=1)
   → Operator picks a program (or skips → chat)
5. POST /api/programs/activate (if program picked)
   → fork_reference_workspace() runs
   → activation_state → "post_fork_pre_author"
6. GET /api/workspace/state again on redirect to /chat
   → ACTIVATION_OVERLAY engages (walks authored-tier files in bundle order)
7. Operator authors MANDATE + other authored files via YARNNN
   → activation_state → "operational"
   → ManageRecurrence(create) hard gate unblocked
8. YARNNN scaffolds first recurrences + fires them immediately
```

**Without program activation** (generic workspace):
- Operator lands on `/chat` directly after first login
- YARNNN's Mandate-first elicitation engages (from `onboarding.py` CONTEXT_AWARENESS)
- Operator authors MANDATE in conversation → `WriteFile(scope="workspace", path="context/_shared/MANDATE.md", ...)`
- YARNNN then elicits identity → `InferWorkspace()` or `InferContext(target="identity")`
- Tasks created after Mandate is non-skeleton

---

## Skeleton detection — single implementation

Three callers previously had diverging skeleton-detection heuristics. As of 2026-05-03 all three delegate to `services.workspace_utils.is_skeleton_content()`:

- `services.workspace_init` — fork idempotency (`authored` tier only re-applied when skeleton)
- `routes/workspace._classify_file_state` — Settings → Workspace substrate status panel
- `services.working_memory._classify_activation_state` — MANDATE.md skeleton → `post_fork_pre_author`

---

## Key files

| File | Role |
|------|-----|
| `api/services/workspace_init.py` | `initialize_workspace()` — the 5-phase init function |
| `api/services/workspace_paths.py` | Canonical path constants; `SHARED_CONTEXT_FILES` (kernel-seeded set) |
| `api/services/workspace_utils.py` | `is_skeleton_content()` + `classify_file_state()` — shared heuristics |
| `api/services/programs.py` | `fork_reference_workspace()`, `_strip_tier_frontmatter()`, `parse_active_program_slug()` |
| `api/services/back_office/__init__.py` | `materialize_back_office_task()` — trigger-based back-office lifecycle |
| `api/routes/workspace.py` | `GET /api/workspace/state` — lazy scaffold + activation state surface |
| `api/routes/account.py` | `DELETE /account/workspace` (L2) and `DELETE /account/reset` (L4) — purge + reinit |
| `web/app/auth/callback/page.tsx` | First-run redirect gate |
| `web/components/settings/WorkspaceSection.tsx` | Settings → Workspace surface (program lifecycle + substrate status) |
