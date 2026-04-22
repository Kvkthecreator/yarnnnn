# ADR-205: Workspace Primitive Collapse — YARNNN as Sole Persistent Identity, Emergent Scaffolding, Chat-First Triggering

> **Status**: Proposed
> **Date**: 2026-04-22
> **Authors**: KVK, Claude
> **Supersedes**: ADR-189 Phase 2 (pragmatic preservation of infrastructure `agents` rows — now reversed); ADR-204 (Workspace Intelligence Cockpit — subject matter dissolves, see "Consequences → ADR-204 re-scope")
> **Amends**: ADR-152 (Unified Directory Registry — becomes naming-convention reference, no pre-creation); ADR-161 (Daily Update Anchor — preserved as task, owner is YARNNN the entity, not YARNNN-the-agent-row); ADR-176 (Work-First Agent Model — Decision 4 "capability split" survives as code-level dispatch, no longer as roster composition); ADR-188 (Domain-Agnostic Framework — completes Phase 3+ by collapsing AGENT_TEMPLATES from scaffolding manifest to dispatch-time lookup)
> **Preserves**: FOUNDATIONS v6.0 (all 8 axioms unchanged); ADR-141 execution pipeline; ADR-168 primitive matrix; ADR-189 three-layer cognition model + authored-team moat + GLOSSARY discipline; ADR-194 Reviewer seat as purpose-trigger construct; ADR-181 feedback layer; ADR-195 money-truth substrate

---

## Context

### The accumulation pattern

ADR-189 correctly framed three-layer cognition (YARNNN · Specialist · Agent) and committed to the authored-team moat: signup scaffolds no Agents, users author their team through conversation. Phase 2 then preserved the pre-existing DB scaffolding (YARNNN row + 6 Specialist rows + 3 Platform Bot rows) as "invisible infrastructure" filtered at the list endpoint via `origin='system_bootstrap'`. The reason was pragmatic: `task_pipeline.py` dispatches Specialists by `agents` table lookup on `role`, and removing the rows would break dispatch without a broader refactor.

That pragmatic preservation is the seed of a broader accumulation. Each of the following is individually defensible and collectively heavy:

1. **Infrastructure rows** (10 agents scaffolded per workspace at signup) — invisible at the list surface but real in the database, memory of `agent_runs`, workspace files, and downstream joins.
2. **Pre-registered workspace directories** (ADR-152 `WORKSPACE_DIRECTORIES`: competitors/market/relationships/projects/content/signals) — created as structural scaffolding even when no task ever writes to them.
3. **Schedule-first task creation** (`tasks.schedule` NOT NULL-defaulted, `next_run_at` is the primary execution index) — forces the user to think about cadence before seeing whether the work produces anything useful. "Run now" is a secondary verb on an already-created task.
4. **Workspace intelligence cockpit** (ADR-204) — added intelligence cards and lazy refresh to surface a workspace whose subject matter was itself scaffolded. The cockpit makes a heavy workspace legible; it does not address the heaviness.
5. **Non-agnostic directory assumptions** — even after ADR-188 reframed registries as template libraries, the naming assumptions (e.g., `competitors/`, `signals/`) encode ICP-specific mental models users do not universally share.

The user-facing consequence: a brand-new workspace contains more pre-baked structure than user-produced substance. The "agent team for hire" → "authored team" framing of ADR-189 survives at the list surface, but the backing reality is still pre-shaped. Users encountering the service for the first time confront scaffolding they did not author, and scheduling they did not request, before any work has produced output.

### The first-principles re-read

The user's operating question: *are workspace init, agent scaffolding, pre-registered domains, and schedule-first tasks getting us closer to our foundations or further?*

Tested against FOUNDATIONS v6.0 axioms:

- **Axiom 1 (Substrate — filesystem is what persists).** Pre-scaffolded directories and infrastructure rows *add to* the substrate without task-driven cause. A substrate populated before work exists is a weaker commitment to Axiom 1, not a stronger one.
- **Axiom 2 (Identity — four cognitive layers).** Four layers (YARNNN, Specialist, Agent, Reviewer) does not require four persistent DB-row categories. Specialists are role-cognition; they are palette elements that do not accumulate identity; they do not require persistent rows to exercise their function at dispatch time.
- **Axiom 3 (Purpose).** Pre-registered domains pre-suppose purpose. Purpose is meant to emerge from user intent, not from a framework-level registry.
- **Axiom 4 (Trigger).** `schedule` and `run-now` are both triggers. Privileging `schedule` as the default primary trigger is a framework-level opinion about *when* work should happen — one that runs counter to how users actually validate work the first time.
- **Axiom 5 (Mechanism).** Unchanged by this ADR.
- **Axiom 6 (Channel).** Unchanged by this ADR.
- **Axiom 7 (Recursion).** Unchanged.
- **Axiom 8 (Money-Truth).** Unchanged.

The collapse proposed here brings the system closer to Axioms 1, 2, 3, 4. The remaining axioms are preserved in full.

### The product reframe

ADR-189 committed to *authorship as moat*. The authored-team framing stated the user's Agents are theirs. ADR-205 extends the same framing to the workspace substrate itself:

- **Workspaces are authored, not scaffolded.** Onboarding obtains context for YARNNN to reason with. Workspaces grow their directories, agents, and task catalog from that context through conversation and explicit affordances. A zero-task workspace is the default first-run state, paired with a deterministic daily-update heartbeat that works even when empty (ADR-161).
- **The verb is "run," not "schedule."** Tasks default to immediate execution. Scheduling is an annotation that converts a run-now task into a recurring task. This matches how users validate work: they try it once, see the output, then decide whether to recur it.
- **Explicit affordances coexist with chat.** Chat handles ambiguity and intent. Modals handle CRUD the user already knows they want (create task, manage context, connect platform). ADR-105's directive-vs-configuration split extends here.

---

## Decision

### Entities that persist at signup

A brand-new workspace contains:

1. **YARNNN** — one persistent identity. Owns back-office tasks, addresses the user in chat, holds `/workspace/IDENTITY.md` + `/workspace/BRAND.md` (seeded by onboarding context injection). Structurally: one row in a new `workspace_identity` table (see "What changes" below), not a row in `agents`.
2. **The daily-update task** (ADR-161, preserved) — essential, deterministic empty-state, owned by YARNNN the entity.
3. **Back-office tasks** (ADR-164, preserved) — `back-office-agent-hygiene`, `back-office-workspace-cleanup`, owned by YARNNN the entity.
4. **Reviewer substrate** (ADR-194, preserved) — `/workspace/review/` files. No persistent agent row; Reviewer is a purpose-trigger seat, not an identity row.

That is the entire signup surface. No Specialist rows. No Platform Bot rows. No pre-registered context domain directories. No `/agents/{role}/` folders for roles the user has not authored.

### Specialists collapse into code-level dispatch

Specialists (Researcher, Analyst, Writer, Tracker, Designer, Reporting) are role templates in `AGENT_TEMPLATES`, consulted by `task_pipeline.py` at dispatch time. They are **not** rows in the `agents` table. ADR-189's role-keyed style distillation (ADR-117 Specialist memory) is preserved as a workspace-scoped file at `/workspace/specialists/{role}/style.md`, not as a per-agent-row memory blob.

Pipeline dispatch is refactored to resolve Specialists by reading `AGENT_TEMPLATES[role]` directly, not by querying `agents WHERE role=X AND origin='system_bootstrap'`. This is the deferred refactor ADR-189 Phase 2 explicitly identified as blocking the full collapse.

### Platform Bots become connection-bound capability bundles

Slack Bot, Notion Bot, GitHub Bot, Commerce Bot, Trading Bot are not rows in `agents`. They are capability bundles keyed on `platform_connections` rows. When a user connects a platform, the corresponding capability bundle activates; when disconnected, it deactivates. Tool surface, task type eligibility, and context domain ownership (per ADR-158) all key on the presence of an active `platform_connections` row for that platform, not on a paused agent row.

This reframe matches Platform Bot semantics accurately: they are not persistent specialists that develop identity over time; they are mechanical, platform-scoped tool surfaces whose lifecycle is strictly bound to an OAuth/API-key connection.

### Workspace directories become emergent

ADR-152's `WORKSPACE_DIRECTORIES` registry is amended: it no longer drives signup-time directory pre-creation. It becomes a naming-convention reference consulted when tasks first write to a domain. Directories are created at first-write, not at signup.

The six ICP-flavored domain names (competitors, market, relationships, projects, content, signals) persist in the registry as *naming suggestions* YARNNN draws from when a task asks to track a new domain. A workspace that never tracks competitors will never contain a `competitors/` directory. A workspace tracking domains the registry does not name (e.g., `regulators/`, `podcasts/`) uses those names directly; the registry is a default, not a constraint.

ADR-188 Phase 2 (read `_domain.md` first, registry fallback) already enabled this at the read path. ADR-205 completes the arc at the write path.

### Chat-first triggering

`tasks.schedule` becomes nullable (migration 154). Task creation semantics:

- **Default path (no schedule provided):** task is created and immediately triggered via `ManageTask(action="trigger")`. User sees output on completion.
- **Scheduled path (schedule provided):** task is created with `next_run_at` set; no immediate trigger. User waits for the scheduled run.

The API contract for `POST /api/tasks` (via `ManageTask._handle_create`) changes to accept `schedule` as optional and to trigger immediately when absent. Frontend task creation UI defaults to "Run now" as primary CTA with "Schedule" as secondary; a task can be converted from one-off to recurring post-run by adding a schedule.

This does not change `mode` semantics (per ADR-149 + ADR-178): `recurring` | `goal` | `reactive` remain the three management postures. What changes is that a `recurring` task's first run is immediate; subsequent runs follow the schedule.

### Explicit modal affordances

Chat remains the primary surface for ambiguous intent. Two new modals land as explicit CRUD affordances:

1. **`CreateTaskModal`** — `output_kind` selector, mode selector, context-injection field, optional schedule, optional source selection. Submits to `POST /api/tasks`. Replaces the chat-only task creation flow for users who arrive with a clear ask.
2. **`ManageContextModal`** — edit `/workspace/IDENTITY.md`, `/workspace/BRAND.md`, and upload documents to `/workspace/uploads/`. Complements ADR-144's inference-first context update path. Not a replacement for inference-driven updates; an explicit alternative for deliberate user edits.

These sit alongside chat. The user can do the same actions by asking YARNNN; the modals exist for users who already know what they want.

### Onboarding re-scope

Onboarding's sole purpose is **context injection**. It is a single dedicated flow — no workspace scaffolding, no agent pre-creation, no directory initialization. The flow obtains:

- Workspace identity (seeds `/workspace/IDENTITY.md`).
- Brand context (seeds `/workspace/BRAND.md`).
- Optional document uploads (land in `/workspace/uploads/`).
- Optional first-task intent (triggers `CreateTaskModal` flow if user describes a task).

No Specialist rows are created. No Platform Bots are activated (connection happens later, when the user connects a platform). No context domain directories are created. The workspace is textually present (IDENTITY + BRAND + uploads) and structurally empty.

---

## What changes

### Phase 1 — Schema & infrastructure row collapse

| File / Artifact | Change |
|-----------------|--------|
| Migration 154 | New. (a) Create `workspace_identity` table (one row per workspace: `workspace_id`, `identity_path`, `brand_path`, `created_at`). (b) Make `tasks.schedule` nullable. (c) Drop all `agents` rows where `origin='system_bootstrap'` AND `role IN ('thinking_partner', 'researcher', 'analyst', 'writer', 'tracker', 'designer', 'reporting', 'slack_bot', 'notion_bot', 'github_bot', 'commerce_bot', 'trading_bot')`. User-authored Agents (other `origin` values) untouched. |
| `api/services/workspace_init.py` | Phase 5 collapses to: create `workspace_identity` row, scaffold `/workspace/IDENTITY.md` + `/workspace/BRAND.md` (empty with frontmatter), scaffold `/workspace/review/` (ADR-194), create daily-update task + back-office-agent-hygiene + back-office-workspace-cleanup (owned by `workspace_identity`, not by an agent row). Remove all Specialist, Platform Bot, and YARNNN-as-agent-row creation calls. |
| `api/services/agent_framework.py` | `DEFAULT_ROSTER` deleted. `AGENT_TEMPLATES` retained as dispatch-time lookup. `get_agent_slug()` remains for user-authored Agents. |
| `api/services/task_pipeline.py` | Specialist dispatch rewritten: resolve by `AGENT_TEMPLATES[role]` directly, not by `agents` table query. YARNNN task dispatch (back-office + daily-update) rewritten: resolve owner from `workspace_identity`, not from an agents row. User-authored Agent dispatch unchanged. |
| `api/services/directory_registry.py` | `WORKSPACE_DIRECTORIES` retained as naming-convention reference. Remove any callers that pre-create directories at signup. Domain first-write path unchanged (creates directory on demand, reads `_domain.md` first per ADR-188). |

### Phase 2 — Chat-first triggering

| File | Change |
|------|--------|
| `api/services/primitives/manage_task.py` | `_handle_create()` accepts optional `schedule`. When absent, immediately calls `_handle_trigger()` for the newly-created task. When present, sets `next_run_at` per schedule. |
| `api/routes/tasks.py` | `POST /api/tasks` schema: `schedule` becomes optional. Response includes `triggered_immediately: bool` when no schedule was provided. |
| `api/jobs/unified_scheduler.py` | Unchanged — still reads `tasks` where `next_run_at IS NOT NULL AND next_run_at <= now()`. Tasks without schedule simply never match. |
| Migration 154 (continued) | `tasks.schedule` nullable (covered in Phase 1 migration). |

### Phase 3 — Platform Bot capability bundles

| File | Change |
|------|--------|
| `api/services/platform_tools.py` | Tool surface continues to be keyed on active platform connections. No change to tool definitions. |
| `api/services/task_pipeline.py` | Platform Bot task dispatch: resolve tool access from `platform_connections` for the relevant platform, not from an agents row. Task-type eligibility check: platform-bot-owned task types are eligible only if corresponding `platform_connections` row is active. |
| `api/services/task_types.py` | Task type definitions unchanged. `owner_agent` field reinterpreted: where the value is a Platform Bot role slug, the executor resolves to "the capability bundle bound to that platform's active connection." |
| `api/routes/integrations.py` | Connect endpoints no longer call `activate_platform_bot_agent()`. Connect == capability activation directly. Disconnect == capability deactivation. |

### Phase 4 — Explicit modal affordances (frontend)

| File | Change |
|------|--------|
| `web/components/work/CreateTaskModal.tsx` | New. Full task creation form: output_kind, mode, context injection, optional schedule, optional sources. |
| `web/components/context/ManageContextModal.tsx` | New. IDENTITY.md + BRAND.md editor with inline-save. Document upload widget. |
| `web/app/(authenticated)/work/page.tsx` | "New task" primary CTA opens CreateTaskModal. Chat-based creation path still reachable via YARNNN chat. |
| `web/app/(authenticated)/chat/page.tsx` | Chat empty state adds explicit "Create a task" and "Manage context" secondary CTAs alongside conversation starter. |

### Phase 5 — Onboarding re-scope

| File | Change |
|------|--------|
| `web/components/onboarding/*` | Flow collapses to: (1) workspace identity (name, mandate, audience), (2) brand (tone, references), (3) optional document uploads, (4) optional first-task intent. On submit: writes IDENTITY.md + BRAND.md + uploads; if first-task intent provided, opens CreateTaskModal pre-filled. No Specialist scaffolding, no directory pre-creation. |
| `api/routes/onboarding.py` (or equivalent) | Submits context to `UpdateSharedContext` (ADR-144), writes files, returns workspace ID. No agent creation calls. |

### Phase 6 — ADR-204 re-scope

ADR-204 (Workspace Intelligence Cockpit) is amended: its subject matter shrinks because the workspace it surfaces is lighter. Specifically:

- **IntelligenceCard** no longer surfaces Specialist rows or Platform Bot rows (they do not exist). Surfaces: user-authored Agents (count + recent activity), Tasks (count by mode, recent runs), Domains (materialized directories under `/workspace/context/`).
- **TaskOutputCard** unchanged — tasks still produce outputs.
- **Lazy refresh** unchanged.
- **Deliverable preference inference** (ADR-204 Phase 2) unchanged — per-task DELIVERABLE.md inference per ADR-178 is preserved.

No ADR-204 functionality is deleted; the cockpit's object graph shrinks because the underlying substrate shrinks.

### Phase 7 — Documentation sweep

| File | Change |
|------|--------|
| `docs/architecture/FOUNDATIONS.md` | No axiom change. Add a note under Axiom 1 that "substrate grows from work, not from signup scaffolding" — an explicit corollary. Add a note under Axiom 4 that "run-now is the default trigger; schedule is an annotation." |
| `docs/architecture/GLOSSARY.md` | Add "Workspace Identity" (the single persistent entity at signup, owned by YARNNN-the-product). Reaffirm that "YARNNN" is the product name and the meta-cognitive entity; no separate agent row represents it. |
| `docs/architecture/registry-matrix.md` | Note that AGENT_TEMPLATES is a dispatch-time template library; Platform Bots are connection-bound capability bundles. WORKSPACE_DIRECTORIES is a naming-convention reference. |
| `docs/adr/ADR-152` | Add amendment banner: "Amended by ADR-205 — registry is naming-convention reference, no signup-time directory pre-creation." |
| `docs/adr/ADR-161` | Add amendment banner: "Amended by ADR-205 — daily-update task is owned by the workspace identity, not by an agent row." |
| `docs/adr/ADR-176` | Add amendment banner: "Amended by ADR-205 — Decision 4 capability split survives as code-level dispatch; roster composition does not persist as DB rows." |
| `docs/adr/ADR-188` | Add note: "Completed by ADR-205 — Phase 3+ (domain-agnostic directory pre-creation collapse) is the ADR-205 Phase 1 directory registry amendment." |
| `docs/adr/ADR-189` | Add amendment banner: "Phase 2 pragmatic preservation of infrastructure agents rows is reversed by ADR-205. Three-layer cognition model and authored-team moat preserved." |
| `docs/adr/ADR-204` | Add amendment banner per Phase 6 above. |
| `CLAUDE.md` | Add ADR-205 to the ADR index. Update "File Locations" where applicable. Update the `agents` table description (roles scaffolded at signup → user-authored only; YARNNN the entity lives in `workspace_identity`). |
| `api/prompts/CHANGELOG.md` | Entry for prompt changes (below). |

### Phase 8 — Prompt updates

| File | Change |
|------|--------|
| `api/agents/yarnnn_prompts/workspace.py` | Remove references to a pre-scaffolded team. Rework "your team" framing to "Agents the user has authored." Chat-first + run-now framing added to task creation guidance. |
| `api/agents/yarnnn_prompts/entity.py` | Minor — task entity preamble already describes the specific task; no structural change. |
| `api/agents/yarnnn_prompts/onboarding.py` | Rewrite to reflect context-injection-only purpose. Remove any references to scaffolding agents or domains. |
| `api/prompts/CHANGELOG.md` | Entry: "YARNNN prompts rewritten to reflect authored-team moat at the substrate layer: no pre-scaffolded Specialists or Platform Bots; directories emerge from task writes; tasks trigger immediately by default." |

---

## What doesn't change

- **FOUNDATIONS v6.0 axioms.** All eight preserved. Axiom 1 and 4 get clarifying corollaries (see Phase 7).
- **ADR-141 execution pipeline.** The pipeline's mechanical-then-judgment split is preserved. What changes is *who* the pipeline dispatches to and *how it resolves them*, not the pipeline shape.
- **ADR-168 primitive matrix.** All primitives retain their signatures. `ManageTask(action="create")` gains optional `schedule`; no other primitive changes.
- **ADR-189 three-layer cognition.** YARNNN · Specialist · Agent · Reviewer remain the four cognitive layers. The change is that Specialists no longer require persistent rows to exist as a layer; they are a code-level palette.
- **ADR-194 Reviewer seat.** Unchanged — was always substrate + dispatch, never an agents row.
- **ADR-181 feedback layer.** Unchanged.
- **ADR-195 money-truth substrate.** Unchanged.
- **ADR-161 daily-update.** The task persists. The owner is the workspace identity entity, not an agent row. Empty-state deterministic template unchanged.
- **ADR-164 back-office tasks.** The two tasks persist. Owner same as daily-update. Scheduler dispatch unchanged.
- **User-authored Agents.** Unchanged. They remain `agents` table rows with `origin='user_configured'` or similar. Their AGENT.md + memory + domain assignments unchanged.
- **Primitive surface.** No primitive added, no primitive removed.

---

## Consequences

### Positive

- **Workspace substrate matches Axiom 1.** What persists reflects what the user has produced, not what the framework pre-baked. Fresh workspaces are textually present (IDENTITY + BRAND + uploads) and structurally empty (zero user-authored Agents, zero domain directories, zero user-authored Tasks — daily-update and back-office tasks aside).
- **Onboarding is about one thing.** Context injection. The flow can be short, focused, and low-friction. Users complete it without encountering scaffolding they didn't ask for.
- **Chat-first + run-now matches how users validate work.** Users see output before deciding on cadence. Scheduling is a post-validation annotation.
- **Platform Bot lifecycle is honest.** Connection-bound capability is what Platform Bots actually are. Representing them as paused-by-default agent rows was misleading.
- **Code surface shrinks.** `DEFAULT_ROSTER` deleted. A class of signup-time agent-creation code deleted. A class of `origin='system_bootstrap'` filter logic deleted. Directory pre-creation logic deleted.
- **ADR-188's arc completes.** "Registries as template libraries" now holds at both read and write paths, at both the task type layer and the directory layer and the agent layer.
- **ADR-189's authored-team moat strengthens.** Not only does the user see zero unsolicited Agents at the list surface — the underlying substrate genuinely contains zero unsolicited Agents. The claim is structurally true, not filter-true.

### Costs

- **Migration risk.** Dropping infrastructure rows on existing workspaces requires care. Any code path that joins `agents` tables to resolve Specialists or Platform Bots must be refactored first (Phase 1 task_pipeline rewrite). Migration 154 runs last in the phase sequence.
- **Pipeline dispatch refactor is non-trivial.** `task_pipeline.py` has two known lookup sites for Specialists (lines ~1956 and ~2669 per ADR-189 audit). Back-office task dispatch also uses owner-agent resolution. All must be rewritten to resolve from `workspace_identity` + `AGENT_TEMPLATES` before the migration drops the rows.
- **ADR-204 cockpit re-scope is visible.** The intelligence cards surface less because less exists. If users were deriving comfort from seeing "10 agents" in their workspace (even if invisible-by-filter), that comfort is removed. The authored-team framing makes this the correct trade.
- **Frontend modals are net-new work.** CreateTaskModal and ManageContextModal are new components with their own state, validation, and API wiring.
- **Prompt rewrites require care.** `yarnnn_prompts/workspace.py` and `yarnnn_prompts/onboarding.py` carry substantial framing about team composition that needs to change without breaking the authored-team thesis or the six Specialist roles YARNNN still draws from at dispatch time.
- **Test infrastructure churn.** Fixtures that assume scaffolded rows will break. `test_recent_commits.py` and any integration tests that assert on the agents table shape need updates.

### Deferred

- **`/workspace/specialists/{role}/style.md` migration.** ADR-117 Specialist memory currently writes to per-row `agent_memory` JSONB on scaffolded rows. Those rows will be dropped. Migrating existing Specialist style distillation to workspace-scoped files is a follow-on commit — for clean-slate implementation (no production data today), the data is simply dropped with the rows.
- **Multi-workspace shared context.** When workspaces become shared (ADR-189 open question 3), authorship attribution on the substrate becomes multi-author. Not in scope here.
- **Pricing / tier implications.** ADR-172 dissolved tier gates. Removing 10 scaffolded rows per workspace per signup has minor infrastructure cost implications (less DB overhead); not a monetization-layer decision.
- **Platform Bot capability bundle registry.** The connection-keyed lookup is straightforward for the current five platforms. A future platform integration ADR may formalize the registry shape; for now it lives implicitly in `platform_tools.py` + `task_types.py` + `platform_connections`.

---

## Dimensional classification (FOUNDATIONS v6.0)

This ADR is primarily about **Substrate** (Axiom 1) — what persists at signup. Secondary dimensions:

- **Identity** (Axiom 2) — refines how Specialists and Platform Bots occupy the identity space (code-level templates and connection-bound bundles respectively, not persistent rows).
- **Trigger** (Axiom 4) — refines the default trigger for new tasks (run-now vs. schedule).
- **Purpose** (Axiom 3) — preserved; the collapse makes Purpose more clearly user-driven because less purpose is framework-pre-baked.
- **Channel** (Axiom 6) — introduces explicit modal channels for CRUD alongside chat. Channel legibility (Derived Principle 12) is respected: explicit modals are high-legibility, chat is for judgment-shaped intent.

---

## Open questions

1. **Does YARNNN-the-entity need a filesystem identity at `/workspace/yarnnn/` or does it live purely at `/workspace/`?** Current direction: `/workspace/IDENTITY.md` + `/workspace/BRAND.md` are workspace-scoped; YARNNN is the entity that operates over them; there is no `/workspace/yarnnn/AGENT.md`. This keeps Axiom 1 clean — the workspace IS YARNNN's substrate. Open for revision during Phase 1 implementation.
2. **Does the user ever need to see the Specialist palette?** ADR-189 open question 1 still stands. Default: no. This ADR does not change that default.
3. **How are Platform Bot capability bundles exposed in surface UI?** Likely as a status affordance on the integrations page ("Slack Bot: active" / "Commerce Bot: inactive — connect Lemon Squeezy to activate"). Not via `/agents`. Frontend detail deferred to Phase 4 implementation.
4. **Is there value in exposing `/workspace/specialists/{role}/style.md` to the user?** Transparency into role-keyed stylistic preferences YARNNN has accumulated. Probably yes via Context surface, but out of scope for this ADR.

---

## Implementation Notes — Architecture Y (2026-04-22)

The literal ADR text above specifies Architecture X: a new `workspace_identity`
table for YARNNN, Specialists that never persist as `agents` rows, and
Platform Bots keyed on `platform_connections` with no `agents` row at all.
Implementation surfaced a schema-level constraint that made Architecture X
substantially more invasive than the ADR's thesis required:

**The `agent_runs` FK.** `agent_runs.agent_id` is `NOT NULL REFERENCES agents(id) ON DELETE CASCADE`,
and eight other tables carry similar FKs (`agent_context_log`, `agent_export_preferences`,
`agent_proposals`, `agent_source_runs`, `destination_delivery_log`, `chat_sessions`,
`event_trigger_log`, `trigger_event_log`). Removing Specialist and Platform Bot rows entirely
would require either (a) making `agent_runs.agent_id` nullable plus adding an `executor_role`
text column, or (b) refactoring every FK-dependent table to track executor identity differently.
Either path is a large schema surgery, much larger than the semantic intent of the ADR.

**Architecture Y — lazy scaffolding within the existing `agents` table.**
Instead of a separate `workspace_identity` table and never-persisted Specialists, Architecture Y
keeps the single `agents` table but collapses *when* infrastructure rows come into being:

| Entity | When the row exists |
|--------|---------------------|
| YARNNN | One per workspace, scaffolded at signup (the heartbeat requires it). `role='thinking_partner'`, `origin='system_bootstrap'`. |
| Specialist (Researcher / Analyst / Writer / Tracker / Designer / Reporting) | Lazy-created on first dispatch via `ensure_infrastructure_agent(user_id, role)`. Zero rows for roles the user never exercises. |
| Platform Bot (Slack / Notion / GitHub / Commerce / Trading) | Created on OAuth connect via `ensure_infrastructure_agent`. Deleted on OAuth disconnect via `delete_platform_bot`. Row lifecycle === connection lifecycle. |
| User-authored Agent | Created when the user authors one. Unchanged by ADR-205. |

Architecture Y delivers the same Substrate-axiom commitment as Architecture X: rows materialize
through user action (first dispatch, platform connect, agent authorship), not through signup
scaffolding. What's different is the vehicle — a classification helper + lazy-ensure helpers
sitting in front of the existing table — instead of a parallel table and an FK-restructuring
migration. The semantic claim of ADR-205 — "substrate grows from work, not from signup
scaffolding" — holds in full.

### What Y preserves vs. what X would have required

| Commitment | Architecture X | Architecture Y (shipped) |
|------------|----------------|--------------------------|
| Signup scaffolds only YARNNN | ✓ | ✓ |
| Specialists never pre-seeded | ✓ | ✓ (lazy-created on first dispatch) |
| Platform Bots bound to connection lifecycle | ✓ (keyed on `platform_connections`) | ✓ (row created on connect, deleted on disconnect) |
| No separate `workspace_identity` table needed | ✗ (requires new table) | ✓ |
| `agent_runs` schema unchanged | ✗ (requires nullable agent_id + executor_role) | ✓ |
| FK-dependent tables (8 of them) unchanged | ✗ | ✓ |
| `user-facing /agents` list unchanged (already filtered by `origin != 'system_bootstrap'` per ADR-189) | ✓ | ✓ |

### Why this is still ADR-205, not a weaker version

ADR-205's thesis is about *when and why substrate comes into being*, not about *which table
holds the rows*. The table choice is a storage-layer decision; the substrate-growth decision
is at the conceptual layer. Architecture Y makes the same conceptual decision — lazy/connection-bound
scaffolding replaces eager signup scaffolding — using the existing storage primitive.

### Mapping ADR-205 phase deliverables to Y

| Phase | ADR text (X-form) | Y implementation |
|-------|-------------------|------------------|
| Phase 1 — Migration 154 | `CREATE TABLE workspace_identity`, backfill, `DELETE agents` | `DELETE agents WHERE origin='system_bootstrap' AND role <> 'thinking_partner'` + dedupe + backfill one YARNNN per workspace. No new table. |
| Phase 1 — workspace_init.py | Create `workspace_identity` row + IDENTITY/BRAND + daily-update + back-office + review/ | Create one YARNNN agent row + (unchanged) IDENTITY/BRAND/AWARENESS/review/ + daily-update + back-office + maintain-overview. Scaffolded directory pre-creation retained until ADR-205 Phase 1 directory-registry collapse ships. |
| Phase 1 — task_pipeline.py | Specialist dispatch reads `AGENT_TEMPLATES` directly | Specialist dispatch reads the roster map first, then calls `ensure_infrastructure_agent()` on miss. Equivalent outcome; template lookup happens inside `ensure`. |
| Phase 2 — chat-first triggering | `tasks.schedule` nullable + `ManageTask._handle_create` immediate trigger when schedule absent | `tasks.schedule` was already nullable; `_handle_create` branch added (no forced `schedule = "weekly"` fallback). `should_run_now` gains `not schedule and mode != 'reactive'`. |
| Phase 3 — Platform Bot capability bundles | Keyed on `platform_connections`, no `agents` rows | Row created on connect via `ensure_infrastructure_agent()`; deleted on disconnect via `delete_platform_bot()`. Behaviourally equivalent — the connection is still the single lifecycle authority; the row is just where we record the identity. |
| Phase 4+ — Frontend modals, onboarding re-scope | Per ADR text | Deferred to a follow-up session per the user-confirmed backend-only scope for this implementation. |
| Phase 6 — ADR-204 re-scope | Per ADR text | Not strictly required because the origin-filter at `list_agents()` (ADR-189 Phase 2) still hides infrastructure from the user-facing surface. Cockpit Intelligence Cards continue to work; they just surface fewer rows because fewer rows exist. |
| Phase 7 — Docs sweep | Per ADR text | ADR-152/161/176/188/189/204 amendment banners already landed in the documentation commit; CLAUDE.md updated. |
| Phase 8 — Prompt updates | Per ADR text | tools.py + tools_core.py framing updated; onboarding.py adds chat-first creation note. |

### Frontend Phase 4+5 — concrete spec (aligned 2026-04-22)

Post-backend-ship UX decisions (user confirmed 2026-04-22). Frontend work breaks into five
sequenced pieces, ordered by leverage-per-effort:

**F1. `HOME_ROUTE` flip to `/chat`** (smallest, highest leverage)

ADR-205 dissolves most of the substrate that makes `/work` valuable as a landing page —
a brand-new workspace has zero user-authored Agents and zero user-authored Tasks, so
`/work` renders near-empty. The user's first meaningful action must be conversational:
describe what they want to track/produce/monitor. Chat is the authoring surface;
landing on Chat re-aligns with ADR-189's authored-team moat.

- `web/lib/routes.ts`: `HOME_ROUTE = "/chat"` (currently `/work`).
- `/chat` empty-state becomes the canonical first-run surface with explicit suggestion chips
  (aligns with ADR-144 cold-start suggestions already in place).

**F2. Overview → Work merge** (medium)

User-aligned: the Overview functionality **survives as a Briefing strip inside `/work`**,
not as a separate surface. The Briefing strip occupies the top of `/work` list-mode and
surfaces ADR-198 Briefing archetype content as **pointers, not embedded widgets**:

- Recent outputs (pointer → output detail)
- Pending proposals (pointer → `/review`)
- Upcoming runs (task + next_run_at)
- Reviewer decisions (pointer → `/workspace/review/decisions.md`)

What dissolves from ADR-204 cockpit: workforce-health cards (IntelligenceCard surfacing
the roster). Substrate is now ~1 row at signup; health-of-roster is not a real surface
area until the user authors agents. TaskOutputCard + lazy refresh + deliverable preference
inference (ADR-204 Phase 2) survive unchanged.

- Delete `/overview` as a standalone route.
- Extract Briefing strip as `web/components/work/BriefingStrip.tsx`.
- `/work` list-mode renders `<BriefingStrip />` above the task list.

**F3. `CreateTaskModal`** (medium-small)

Explicit-intent CRUD affordance alongside chat. Fields per ADR-205 §Phase 4:

- Title (required)
- `output_kind` selector (4 values per ADR-166)
- `mode` selector (recurring / goal / reactive per ADR-149)
- Context injection (free text)
- Schedule (optional — empty = run-now, matches chat-first trigger)
- Sources (optional, filtered by active `platform_connections`)

Submits to `POST /api/tasks` via `ManageTask._handle_create`. Opens from `/work` "New task"
primary CTA and from a chat mention (`@new-task` or similar chip).

**F4. `ManageContextModal`** (small)

Explicit edit surface for `/workspace/IDENTITY.md` + `/workspace/BRAND.md` + uploads.
Alongside ADR-144's inference-first context update path. Not a replacement for
inference-driven updates — an explicit alternative for deliberate user edits.

**F5. Onboarding re-scope** (small — verified minimal change needed)

Audit findings: the onboarding flow is already minimal and ADR-205-compliant. `OnboardingModal`
wraps `ContextSetup` (identity/brand/uploads capture). No roster/scaffold language. TP triggers
the modal via `<!-- onboarding -->` marker when `workspace_state.identity == "empty"`. Post-submit
forwards to TP via `sendMessage` which calls `UpdateContext + ManageDomains`.

The only F5 change shipped: `auth/callback/page.tsx` comment updated to reference ADR-205 instead
of ADR-144/163 (reflects the YARNNN-only signup scaffolding + Specialist lazy creation).

The "optional first-task intent field" sub-item of F5 is deferred with F3 (CreateTaskModal),
since it depends on that modal existing to route the intent through.

**Layout rule (applies to all of F1–F5):**

- Chat: single panel, full width (authoring surface, no list+detail confusion).
- Work list-mode: single panel with Briefing strip at top.
- Work detail-mode: two panels (list + detail, ADR-167 pattern preserved).
- Agents: one panel in list, two panels in detail (ADR-167 preserved).

Chat being single-panel is the load-bearing asymmetry — Cursor/Linear/Claude Code all share
this pattern: the authoring surface is undivided; inspection surfaces are master-detail.

### What remains proposed (not implemented in this commit)

- **Phase 4 pieces F1–F5** above. F1 lands in the same implementation cycle as this ADR.
  F2–F5 ship in follow-up session(s).
- **`/workspace/specialists/{role}/style.md` as ADR-117 Specialist memory location.** For now,
  Specialist memory continues to live on the (now lazy) agent row via the existing `agent_memory`
  JSONB / workspace AGENT.md pattern. No user-authored content exists on the dropped rows,
  so no migration was needed.

### Verification

Post-migration state (2026-04-22 05:13 UTC):
- 11 workspaces, 11 `agents` rows (1 YARNNN per workspace, all `role='thinking_partner'`, all `origin='system_bootstrap'`).
- Pre-migration: 38 rows (6 Specialists × 3 workspaces + 3 bots × 3 workspaces + 2 commerce/trading + 2 TP + stragglers). Post-migration: 11 rows. All 31 Specialist/Bot rows dropped; 9 YARNNN backfilled for workspaces lacking one; no dedupes needed.
- All modified files compile cleanly (`python3 -m py_compile` on 9 touched modules).
- Test workspaces remain functional: YARNNN addresses user in chat, daily-update + back-office + maintain-overview tasks continue to dispatch (maintain-overview's Reporting Specialist will lazy-materialize on first dispatch).

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-22 | v1 — Initial proposal. Infrastructure row collapse, chat-first triggering, emergent directory scaffolding, explicit modal affordances, ADR-204 re-scope. Supersedes ADR-189 Phase 2. Amends ADR-152, ADR-161, ADR-176, ADR-188, ADR-204. Preserves FOUNDATIONS v6.0, ADR-141, ADR-168, ADR-189 three-layer cognition, ADR-194, ADR-181, ADR-195. |
| 2026-04-22 | v1.1 — Backend implementation landed (Architecture Y — lazy scaffolding within the existing `agents` table rather than a separate `workspace_identity` table). Migration 154 applied. Implementation Notes section added above documenting the pivot and its equivalence to the ADR thesis. Frontend modals + onboarding re-scope deferred to a follow-up commit. |
| 2026-04-22 | v1.2 — Frontend F1 shipped: HOME_ROUTE flipped to `/chat`, ToggleBar nav reordered to `Chat \| Work \| Files \| Team \| Review`, Overview tab removed from nav. |
| 2026-04-22 | v1.3 — Frontend F2 + F5 shipped: (F2) Overview→Work merge — four Briefing panes (NeedsMePane, SinceLastLookPane, SnapshotPane, IntelligenceCard) relocated from `web/components/overview/` to `web/components/work/briefing/`; new `BriefingStrip` composition mounted above `WorkListSurface` in /work list-mode; `OverviewSurface` + `OverviewEmptyState` deleted; `/overview/page.tsx` becomes a redirect stub to `/work`; `OVERVIEW_ROUTE` constant deleted; middleware comment + ToggleBar comment updated. (F5) onboarding flow audited — already ADR-205-compliant; only the auth/callback comment needed refreshing. F3 (CreateTaskModal) + F4 (ManageContextModal) deferred for downstream consideration. |
