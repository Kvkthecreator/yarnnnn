# ADR-207: Primary-Action-Centric Workflow — Mandate, Loop, Capabilities

> **Status**: **Phases 1–5 Implemented** (2026-04-22, commits 49496c0 / d1334eb / 352f8b9 / 0be70e6 / 01fd609 / 3353eb9 / d6a6a53). Phase 6 (alpha persona re-author + E2E re-run) mandate-authoring artifacts landed (d6a6a53); E2E re-run pending.
> **Date**: 2026-04-22
> **Authors**: KVK, Claude
> **Triggered by**: Alpha-trader E2E (2026-04-22, docs/alpha/observations/2026-04-22-adr206-trader-e2e-*.md) — substrate + prompt layers validated, but the E2E exposed that ADR-206's three-layer Intent/Deliverables/Operation model left the *center of gravity* undefined. The operator-facing consolidation came from realizing every operator workspace has exactly one **Primary Action class** (the external write that moves value) and everything else exists in service of it.
> **Supersedes**: ADR-166 output_kind classification (enum survives as self-declaration value, not a classification key); ADR-188 task_types as template library (TASK_TYPES no longer dispatch-authoritative; 11 bot-dispatched entries deleted; 21 remain as frozen seed-template library).
> **Extends / refines**: ADR-206 three-layer operator view (Intent preserved; Deliverables reframed as task sub-parts, not a first-class layer; Operation preserved).
> **Amends**: ADR-149 DELIVERABLE.md (semantics unchanged; reframed as "a task's output contract", not an independent layer); ADR-194 Reviewer (unchanged structurally; role in the Loop made explicit); ADR-195 Money-Truth (unchanged; role in the Loop made explicit); ADR-205 Platform Bots (**finished — bots deleted as agent entities under P4a (commit 0be70e6), migration 157 dropped all bot rows + updated agents_role_check, capability gating replaces the bot abstraction**).

## Implementation status (2026-04-22)

| Phase | Commit | Status | Summary |
|---|---|---|---|
| 1 — ADR ratification | — | ✅ Landed | This document |
| 2 — Mandate hard gate | d1334eb | ✅ Landed | `SHARED_MANDATE_PATH`, `_handle_mandate`, `ManageTask(create)` mandate_required gate, migration 156, onboarding prompt rewrite |
| 3 — Capability gate | 352f8b9 | ✅ Landed | `platform_connection_requirement` on every CAPABILITIES entry; `capability_available()` + `unavailable_capabilities()`; `parse_task_md` reads `**Required Capabilities:**`; dispatch-time gate in `execute_task` |
| 4a — Platform Bots → Capabilities | 0be70e6 | ✅ Landed | 5 bot roles deleted from AGENT_TEMPLATES + LEGACY_ROLE_MAP + `classify_role`; `delete_platform_bot` gone; routes/integrations + routes/account bot lifecycle removed; 11 bot-dispatched TASK_TYPES entries + STEP_INSTRUCTIONS deleted; migration 157 drops bot agent rows + updates `agents_role_check` |
| 4b — TASK_TYPES not dispatch-authoritative | 3353eb9 | ✅ Landed | All registry fallbacks in `task_pipeline.py` deleted; ManageTask schema gains 7 self-declaration fields (output_kind, context_reads/writes, required_capabilities, emits_proposal, process_steps, deliverable_md); `_handle_update` type_key change path removed; `/api/tasks/types` endpoints deleted + frontend client `listTypes`/`getType` removed; YARNNN workspace prompt rewritten around self-declaration primary |
| 5 — Derivation helper + prompt | 01fd609 | ✅ Landed | `api/services/task_derivation.py::build_derivation_report()`; auto-refresh on mandate write + task create; YARNNN workspace prompt "Derivation-First Scaffolding" section; loop-role classification (sensor/proposer/reviewer/reconciler/learner/decision-support) |
| 6 — Alpha persona re-author | d6a6a53 | 🟡 Partial | `docs/alpha/personas/alpha-trader/MANDATE.md` + `docs/alpha/personas/alpha-commerce/MANDATE.md` authored; E2E-EXECUTION-CONTRACT v2 updated to start with Mandate authoring. **E2E re-run pending.** |

**Follow-on work (not blocking):** full TASK_TYPES deletion once operators migrate off `type_key` convenience + back-office templates move inline to `workspace_init.py`. CreateTaskModal full self-declaration UI (current change is stop-fetching-types only). See commit 3353eb9 CHANGELOG for details.

---

## Context

### What the alpha-trader E2E taught

The E2E validated the ADR-205/206 substrate and prompt changes. YARNNN's operation-first posture propagated. Scaffolding worked. But the E2E surfaced a deeper architectural ambiguity ADR-206 didn't resolve:

- The three co-equal layers (Intent / Deliverables / Operation) didn't tell us which of the three is the *center*. In practice, nothing "dictates" anything else — they sit beside each other.
- Task types (`track-competitors`, `pre-market-brief`, `slack-digest`, etc.) describe common shapes but constrain composition — alpha-trader's `signal-evaluation` wasn't in the registry and had to be created ad-hoc.
- Platform Bots-as-agent-rows (ADR-205 Architecture Y) worked but conflated *who can act* with *what the operator can do*.
- No file carries the operation's north star. `IDENTITY.md` is who-the-operator-is; `BRAND.md` is how-outputs-look. Nothing is what-the-workspace-is-running.
- Deliverables were overloaded as both "things the operator sees" (briefs, reviews) and "things that trigger execution" (proposals). Different roles, same word.

### The consolidation

Every operator workspace in YARNNN's ICP has exactly one **Primary Action class** — the external write that moves value:

| Operator | Primary Action |
|---|---|
| alpha-trader | submit / cancel order on Alpaca |
| alpha-commerce | list / update product, send campaign, issue refund |
| Newsletter operator | publish post, send email |
| Ad buyer | create / pause campaign |

Primary Actions are structurally alike: external platform writes, rule-governable, value-moving, asymmetrically losable. They are the center of gravity. Every other mechanic in the workspace — rules, proposals, reviews, approvals, execution, reconciliation, refinement — exists in service of Primary Action performance.

This reframe is falsifiable. A workspace with no Primary Action is not YARNNN's ICP (it's a research workspace, a notebook, a Claude Code project — not a money-generating operation). An operator whose Primary Action's capability isn't connected has a *Knowledge-mode* workspace — no execution, but the same loop structure minus the closing arrow.

### The Loop is prompt strategy, not pipeline architecture

**Load-bearing clarification.** The seven-arrow Loop (D3 below) is YARNNN's **cognitive framework + prompt strategy**, not an engineered state machine. No pipeline orchestrator enforces "now we're at arrow 3, next is arrow 4." No code-level Loop-awareness exists in any primitive or dispatcher.

Instead, the architecture is:

- **Context** — the filesystem (workspace_files, `_performance.md`, `decisions.md`, `_shared/*`, per-task TASK.md/DELIVERABLE.md/awareness.md)
- **Primitives** — unbiased substrate operations (ManageTask, UpdateContext, ProposeAction, WriteFile, ReadFile, Clarify, RuntimeDispatch, etc.) — none of them know about the Loop
- **Configuration** — `MANDATE.md`, `RULES` (operator_profile + risk + review/principles) — operator-authored intent that frames reasoning
- **Conversation** — chat is where YARNNN carries the Loop as its reasoning scaffold

When YARNNN reasons about what to do next, it uses the Loop metaphor to structure its thinking: *"The operator just authored rules; next we need a Proposer — is one scaffolded? If not, create one. When it fires, its output needs the Verdict arrow, which means Reviewer gating — is principles.md authored? And so on."* The Loop is a conceptual scaffold for reasoning, made visible through chat responses, filesystem reads/writes, and eventually the cockpit Queue.

**This is the same pattern as Claude Code.** Claude Code doesn't have a pipeline for "now we plan, now we implement, now we review." It has context (the codebase + CLAUDE.md), primitives (Read, Write, Edit, Bash, Agent, etc.), and the operator's conversation. The coding workflow emerges from those four ingredients without a code-level state machine enforcing phases.

YARNNN adopts this exact posture:
- YARNNN's substrate does not dictate workflow.
- YARNNN's primitives do not assume a workflow.
- YARNNN's chat prompts + MANDATE.md carry the workflow.
- The filesystem accumulates the workflow's state.

What remains code-enforced under ADR-207:
- **The MANDATE.md hard gate** (D2) — operator must author Mandate before task scaffolding. Prevents ungrounded workflow drift.
- **Task self-declaration** (D7) — each TASK.md declares what it reads/writes/needs; pipeline dispatches from declarations.
- **Capabilities gating** (D5) — primitive dispatch checks `required_capabilities` against active `platform_connections`.
- **Reviewer routing** (ADR-194, unchanged) — proposal insert fires `review-proposal` task; Reviewer reads principles.md + _performance.md.

Everything else — "how YARNNN knows we're ready to propose," "when a weekly-review triggers rule refinement," "whether a Mandate revision is overdue" — is **chat-level reasoning over the filesystem**, not pipeline logic.

**Consequence for ADR-207 scope:** the Loop narrative (D3) describes the *conceptual shape* of the workflow for documentation + prompt authoring purposes. Implementation scope is D1, D2, D4, D5, D6, D7, D8 — each of which is primitive-level, agnostic work. No "Loop orchestrator" gets built because none is needed.

### Relationship to FOUNDATIONS and prior ADRs

This ADR is a cohesive synthesis, not a rewrite of axioms. FOUNDATIONS v6.0 (six-dimensional model + Axiom 8 money-truth) is fully preserved. ADR-206's Intent layer survives (what the operator declares: Mandate, rules, risk, principles). ADR-194's Reviewer is the Identity-layer cell that gates proposals. ADR-195's `_performance.md` is the money-truth substrate that closes the loop.

What changes: the operator-facing workflow is made explicit as a 7-arrow loop pivoting on Primary Action; Deliverables stop being a first-class layer; the `TASK_TYPES` registry dissolves into per-task self-declaration; Platform Bots complete their collapse into capabilities.

---

## Decision

### D1 — Primary Action as architectural pivot

Every operator workspace in YARNNN's ICP has exactly one Primary Action class, declared in the workspace's Mandate. All other mechanics exist in service of Primary Action performance.

Structurally:
- External platform write (crosses a boundary into a system of record)
- Rule-governable (declaratively specifiable entry/exit/sizing conditions)
- Value-moving (money, inventory, audience, compliance posture)
- Asymmetrically losable (a wrong action has capital cost; a missed action has opportunity cost)

### D2 — Mandate as the workspace's north-star file

Add `/workspace/context/_shared/MANDATE.md`. Peer of IDENTITY.md, BRAND.md, CONVENTIONS.md.

**Contract:**
- Declares the workspace's Primary Action class.
- Declares operation-level success criteria (Sharpe ≥ 1.0, blended margin ≥ 22%, net subscriber add, etc. — domain-specific).
- Declares boundary conditions (paper vs live, capital base, universe, execution hours, max leverage).
- **No forced revision frequency.** Like `CLAUDE.md` in a codebase — revised when the operator decides, and the revision itself is the artifact. No quarterly cadence, no auto-prompted review.
- Scaffolded at signup as empty skeleton.
- Authored via `UpdateContext(target="mandate")` during first-turn operation elicitation.

**Hard gate:** no task scaffolding until MANDATE.md is non-empty. Enforced at the primitive layer, not the prompt. `ManageTask(action="create")` returns an error when the caller's workspace has an empty MANDATE.md. `CreateTaskModal` checks the same precondition and surfaces "author your mandate first" instead of rendering the form.

### D3 — The Loop (seven substrate writes; no invented actors)

Every arrow is a substrate write that a named layer performs. Only the layers already in the architecture appear: Operator (human), YARNNN (meta-cognitive, Axiom 2), Agent (domain-cognitive, Axiom 2), Reviewer (Axiom 2), Capability (new-in-ADR-207, bound to `platform_connections`). No invented actors like "Proposer", "Sensor", "Reconciler", "Learner" — those are informal descriptions of what an Agent or YARNNN happens to be doing in a particular arrow.

| # | Arrow | Substrate | Performed by | Trigger | Mechanism |
|---|-------|-----------|--------------|---------|-----------|
| 1 | **MANDATE** | `/workspace/context/_shared/MANDATE.md` | Operator (YARNNN assists via inference) | Addressed | Judgment |
| 2 | **RULES** | domain `_operator_profile.md` + `_risk.md` + `review/principles.md` | Operator (YARNNN assists) | Addressed | Judgment |
| 3 | **PROPOSAL** | `action_proposals` row + `/tasks/{slug}/working/trigger_context.md` | Agent (domain agent evaluating rules against accumulated context) | Periodic or Reactive | Judgment |
| 4 | **VERDICT** | `/workspace/review/decisions.md` (append-only) | Reviewer (AI, human, or impersonation — Axiom 2 fourth layer) | Reactive | Judgment calibrated by principles.md |
| 5 | **APPROVAL** | `action_proposals.status ∈ {approved, rejected}` | Operator (Addressed), or Reviewer if policy permits auto-approve | Addressed or Reactive | Deterministic once policy evaluated |
| 6 | **ACTION** | external platform write + `activity_log` append | Capability (bound to active `platform_connections`) | Reactive | Deterministic (capability → platform API) |
| 7 | **OUTCOME** | `/workspace/context/{domain}/_performance.md` | YARNNN (via `back-office-outcome-reconciliation` task) | Periodic (daily) | Deterministic (idempotent event-key append — ADR-195) |

**Recursion (Axiom 7):** Next Rule revision reads Outcome. Decay flags, retirement candidates, threshold adjustments. No special "Learner" role; an Agent or YARNNN does this during a weekly-style task, and the operator ratifies the proposed Rule delta via Addressed mechanic.

### D4 — Deliverables are sub-parts of tasks, not a first-class layer

The word "Deliverable" names *what a task produces*. Every task has a deliverable. DELIVERABLE.md (ADR-149) is preserved as the task's output contract. There is no separate Deliverables layer, no separate Deliverable primitive, no Deliverable-declaration step distinct from task scaffolding.

Concretely:
- A task that emits proposals (PROPOSAL arrow): its deliverable is the `action_proposals` row.
- A task that accumulates context (Sensor-style): its deliverable is the written context file(s).
- A task that produces a briefing or review (Instrument-style): its deliverable is the markdown artifact under `/tasks/{slug}/outputs/`.
- A task that reconciles outcomes: its deliverable is the `_performance.md` update.

Task scaffolding therefore becomes: "given the Primary Action and Rules, which tasks orbit the loop — one per loop-role the workspace needs." The operator confirms the task set. DELIVERABLE.md per task captures *that specific task's* output contract.

ADR-206's "Deliverables as operator surface" framing is refined: what surfaces to the operator is the **outputs of tasks** (proposals in the Queue, briefings on /work, performance snapshots in context) — not a separate Deliverables layer. The `/work` surface filters and orders task outputs; it isn't showing a different substrate.

### D5 — Platform Bots dissolve into Capabilities

Finish the collapse ADR-205 started. Platform Bots (`slack_bot`, `notion_bot`, `github_bot`, `commerce_bot`, `trading_bot`) are no longer `agents` table rows. They are capability bundles attached to active `platform_connections`.

Concretely:
- Delete `slack_bot`, `notion_bot`, `github_bot`, `commerce_bot`, `trading_bot` from `agents_role_check` constraint + `AGENT_TEMPLATES`.
- Extend existing `CAPABILITIES` dict in `api/services/agent_framework.py` (already has `read_slack`, `read_notion`, etc.) so every capability declares its `platform_connection_requirement` (platform name + status).
- Tasks declare `required_capabilities: ["submit_order", "get_account"]` in TASK.md. Dispatch resolves the capability via the CAPABILITIES registry → primitive handler + platform_connection predicate.
- Migration 156: drop bot agent rows across all workspaces. Preserve `platform_connections` rows untouched. Reconnect flow doesn't create an agent; it activates capabilities.

**Who invokes capabilities.** YARNNN, authored Agents, or task pipelines (via the task's `required_capabilities` declaration). Capabilities are not entities — they are primitive handlers gated on connection state.

### D6 — Two-mode service: Operational and Knowledge

After Mandate is authored, YARNNN evaluates:

- **Operational mode** — the Primary Action class declared in Mandate maps to at least one active capability in `CAPABILITIES` whose `platform_connection_requirement` is satisfied by an active `platform_connections` row. The Loop can close. Full service.
- **Knowledge mode** — no such capability match. YARNNN surfaces the gap: *"Your Mandate's Primary Action requires an Alpaca connection — connect it to run operationally, or I can continue as a research/knowledge workspace."* If the operator declines to connect, the workspace runs in Knowledge mode: PROPOSAL + VERDICT arrows still work (operator gets recommendations), but APPROVAL, ACTION, OUTCOME arrows are vestigial (no real execution, no money-truth).

Detection is synchronous at each Mandate edit and at each task-scaffold request. No stored "mode" flag — it is a computed property of `(MANDATE.md Primary Action declaration) × (active CAPABILITIES)`.

**UX implication**: Knowledge-mode workspaces render without the cockpit Queue's "approve to execute" affordance — proposals are advisory only. Otherwise identical surface.

### D7 — Task self-declaration; TASK_TYPES registry dissolves

Delete `api/services/task_types.py::TASK_TYPES` entirely. Keep `task_types.py` file only as a parsing module for TASK.md (read self-declared metadata). No concrete type registry.

Every task's TASK.md declares, in YAML-style frontmatter or `**Key:**` lines:

- `schedule` — cron expression, cadence keyword, or null (null = reactive/event-triggered)
- `context_reads` — list of workspace paths the task reads from
- `context_writes` — list of workspace paths the task writes to
- `emits_proposal` — bool (true ⇒ task calls ProposeAction)
- `required_capabilities` — list of capability names needed at dispatch time
- `output_spec` — the task's DELIVERABLE.md contract

Pipeline dispatches from these declarations. Surface filters from these declarations:
- Cockpit Queue: proposals from tasks where `emits_proposal: true`, with `action_proposals.status = pending`.
- `/work` list: tasks whose `output_spec` targets user-visible artifacts.
- `/settings/system`: tasks with workspace-wide scope and no `output_spec` (hygiene).

**No inference from a task-type key. No classification layer.** Readers derive role from what the task declares it does.

**Legacy cleanup:** Existing alpha persona operator profiles referenced concrete type keys (`track-universe`, `pre-market-brief`, etc.). Those strings become informal labels only. Any code or prompt branch conditioning on `type_key` equals a specific value is deleted.

### D8 — Derivation from filesystem graph

When YARNNN scaffolds tasks after Mandate + Rules are authored, it uses a derivation function over the filesystem:

```
def derive_task_set(mandate_primary_action, rules_set, existing_tasks) -> proposed_tasks:
    # 1. Primary Action needs a Proposer task — an Agent that evaluates Rules
    #    against accumulated context and calls ProposeAction when triggered.
    # 2. Proposer reads context paths (rules reference per-signal state, per-SKU
    #    state, etc.). Those paths must be maintained — by Sensor-style tasks.
    # 3. Primary Action outcomes need reconciliation — back-office-outcome-reconciliation
    #    per domain, already materialized on platform-connect per ADR-205/206.
    # 4. Operator wants decision-support — weekly/daily instruments that read
    #    _performance.md and accumulated context.
    # Return the minimum task set, labeled by loop-role for operator confirmation.
```

This is not a new primitive; it's a function YARNNN calls before emitting `ManageTask(create)`. The derivation output is shown to the operator for confirmation. Over-scaffolding (the `track-universe-2` duplicate from Obs 05-1 E2E) and under-scaffolding are equally visible.

---

## The Mandate file — specification

`/workspace/context/_shared/MANDATE.md`

**Structure** (guidance; YARNNN-inferred content per workspace):

```markdown
# Mandate

## Primary Action
<One sentence: the external write that moves value in this workspace.>

## Success Criteria
- <Operation-level metric 1>
- <Operation-level metric 2>
- <Discipline invariant (e.g. "zero discretionary trades")>

## Boundary Conditions
- <Scope limit 1: e.g. paper account throughout Alpha-1>
- <Scope limit 2: e.g. $25k notional capital base>
- <Scope limit 3: e.g. US large-cap equities + sector ETFs>
- <Execution bounds: e.g. 1.0x leverage max>

## Revision Protocol
<Optional. When the operator wants to revise, they revise. No cadence
enforced. This section can note circumstances the operator considers
material enough to revisit, but it is operator-declared, not system-prompted.>
```

**Authoring flow:**
1. `workspace_init` (ADR-206 Phase 1) seeds an empty MANDATE.md skeleton at signup alongside the other `_shared/*` files.
2. YARNNN's first-turn posture prompt (ADR-206 Phase 2) leads with Mandate elicitation — the prior "What operation do you want to run?" now explicitly routes to Mandate authorship.
3. Operator describes the operation. YARNNN infers via new `UpdateContext(target="mandate")` and writes MANDATE.md.
4. Any subsequent turn that attempts `ManageTask(create)` with an empty MANDATE.md returns an error. YARNNN surfaces the block gracefully: *"Let's get your mandate authored first — it's what all your tasks will serve."*

**Write target.** `UpdateContext(target="mandate")` writes to the ADR-206 path. Extends the existing UpdateContext targets (ADR-144 + ADR-156 + ADR-206) — a new case, not a new primitive.

---

## Capabilities — consolidated with existing registry

`api/services/agent_framework.py::CAPABILITIES` already exists (line 1101). It enumerates `web_search`, `read_slack`, `read_notion`, `submit_order`, etc. ADR-207 extends it — does not create a parallel registry.

Each capability gains a declared `platform_connection_requirement`:

```python
CAPABILITIES: dict[str, dict[str, Any]] = {
    "web_search": {
        "category": "tool",
        "runtime": "internal",
        "tool": "WebSearch",
        "platform_connection_requirement": None,  # no platform needed
    },
    "read_slack": {
        "category": "tool",
        "runtime": "external:slack",
        "tool": "platform_slack_*",
        "platform_connection_requirement": {
            "platform": "slack",
            "status": "active",
        },
    },
    "submit_order": {
        "category": "tool",
        "runtime": "external:trading",
        "tool": "platform_trading_submit_order",
        "platform_connection_requirement": {
            "platform": "trading",
            "status": "active",
        },
    },
    # ... etc
}

def capability_available(user_id: str, capability_name: str, client) -> bool:
    """Check whether a capability can fire for this user right now."""
    cap = CAPABILITIES.get(capability_name)
    if not cap:
        return False
    req = cap.get("platform_connection_requirement")
    if req is None:
        return True
    row = client.table("platform_connections").select("id").eq(
        "user_id", user_id
    ).eq("platform", req["platform"]).eq("status", req["status"]).limit(1).execute()
    return bool(row.data)
```

**Consumers:**
- Task dispatch: before invoking a task's `required_capabilities`, check each is available; fail gracefully with "missing capability X — connect Y" if not.
- Two-mode detection (D6): `capability_available()` against the Primary Action's required capability determines Operational vs Knowledge mode.
- YARNNN prompt: compact index surfaces unavailable capabilities, so YARNNN can recommend connections.

**Agent roster cleanup:** the 5 bot roles (`slack_bot`, `notion_bot`, `github_bot`, `commerce_bot`, `trading_bot`) delete from `AGENT_TEMPLATES` and `agents_role_check`. Migration 156 removes existing bot rows.

---

## What changes (implementation phases)

### Phase 1 — ADR ratification only (this commit)

The ADR itself lands. Cross-ADR amendment banners updated. No code changes.

### Phase 2 — Mandate + UpdateContext target + hard gate

1. `api/services/workspace_init.py` Phase 2 seeds empty MANDATE.md at `/workspace/context/_shared/MANDATE.md`.
2. `api/services/workspace_paths.py` exports `SHARED_MANDATE_PATH = "context/_shared/MANDATE.md"`.
3. `api/services/primitives/update_context.py` adds `target="mandate"` case — inference-capable, writes to `SHARED_MANDATE_PATH`.
4. `api/services/primitives/manage_task.py::_handle_create` checks for non-empty MANDATE.md before accepting; returns `error="mandate_required"` if empty. Same check in `CreateTaskModal` frontend.
5. Migration 156 backfills empty MANDATE.md for existing workspaces.
6. YARNNN prompt update: first-turn posture elicits Mandate; subsequent turns surface unauthored-mandate gracefully.
7. CHANGELOG entry.

### Phase 3 — Platform Bots → Capabilities

1. Extend `CAPABILITIES` entries with `platform_connection_requirement`.
2. Add `capability_available()` helper.
3. `api/services/task_pipeline.py` checks `required_capabilities` at dispatch.
4. Remove bot role rows at `workspace_init` (already done for new workspaces post-ADR-205; Migration 156 backfills for existing).
5. Delete bot roles from `AGENT_TEMPLATES` and `agents_role_check`.
6. Update routes/integrations.py and routes/account.py — no more bot-row create/delete on connect/disconnect; just `platform_connections` lifecycle.
7. Two-mode detection surfaces in compact index + workspace_state.
8. CHANGELOG entry.

### Phase 4 — TASK_TYPES sunset + self-declaration

1. Delete `TASK_TYPES` dict from `api/services/task_types.py`.
2. Remove all `type_key` branch conditioning from pipeline, prompts, routes.
3. Migration 157: parse existing TASK.md files; add self-declaration frontmatter where missing; no row change.
4. Pipeline dispatches from TASK.md declarations only.
5. Surface filters (cockpit Queue, `/work` list, `/settings/system`) derive from declarations.
6. CHANGELOG entry.

### Phase 5 — Derivation function + YARNNN prompt guidance

1. Implement `derive_task_set()` helper.
2. YARNNN prompt: after Mandate + Rules confirmed, call derivation, show operator the proposed task set, confirm before any `ManageTask(create)`.
3. Over-scaffolding and under-scaffolding become visible per the derivation contract.

### Phase 6 — Alpha persona migration

1. Re-read alpha-trader and alpha-commerce IDENTITY.md + operator_profile.md + principles.md against the new frame.
2. Author MANDATE.md for each persona via the new authoring flow.
3. Re-run E2E per updated `docs/alpha/E2E-EXECUTION-CONTRACT.md` (contract updated to start with Mandate authoring).

---

## Supersedes / amends summary

| ADR | Relationship | Reason |
|---|---|---|
| ADR-166 | **Superseded** | output_kind classification enum dissolves; tasks self-declare |
| ADR-188 | **Superseded** | task_types as template library → types dissolve entirely |
| ADR-149 | **Amended** | DELIVERABLE.md semantics preserved; reframed as task output contract, not a separate layer |
| ADR-194 | **Amended** | Reviewer's role in the Loop made explicit (arrow 4 — VERDICT) |
| ADR-195 | **Amended** | Money-truth's role in the Loop made explicit (arrow 7 — OUTCOME) |
| ADR-205 | **Amended** | Bot dissolution finished — bots become pure capabilities, not agent rows |
| ADR-206 | **Refined** | Three-layer view preserved conceptually; Deliverables reframed as task sub-parts; Mandate added as workspace-wide north star; Loop made explicit |

---

## What doesn't change

- **FOUNDATIONS v6.0 axioms.** All eight preserved. The Loop is expressible in axiom vocabulary — each arrow occupies a Substrate/Identity/Purpose/Trigger/Mechanism/Channel cell.
- **ADR-168 primitive matrix.** No primitive added or removed except the `target="mandate"` case on UpdateContext.
- **ADR-141 execution pipeline.** Unchanged at its core — pipeline still reads TASK.md and dispatches. What changes is what TASK.md declares.
- **Reviewer substrate (ADR-194).** Decisions.md format unchanged; principles.md authoring flow unchanged.
- **Money-truth substrate (ADR-195).** `_performance.md` format unchanged; daily reconciliation unchanged.
- **ADR-159 compact index.** Shape unchanged; content gains Mandate awareness + capability-mode signal.
- **User-authored Agents.** Unchanged. Agent creation flow untouched.

---

## Consequences

### Positive

- **Operator workflow has a named center.** Mandate + Primary Action anchor everything. No more "which layer dictates what?" ambiguity.
- **The Loop is legible.** Seven substrate writes, each performed by a named existing layer. No invented actors. No parallel workflows.
- **Two-mode service is honest about capability gaps.** Workspaces without the hands to execute become Knowledge-mode gracefully instead of looking broken.
- **Task type registry dissolves.** One less constraint on composition; one more consistent surface for reasoning. Any shape of task any operator needs is composable per-TASK.md.
- **Platform Bot ontology resolves.** Bots were never "who acts" — they were "what the operator can do." Reframing as capabilities matches that truth and eliminates a class of mental-model errors.
- **Deliverables stop overloading.** No more conflation of "the brief the operator reads" with "the proposal that triggers execution." Tasks produce outputs; outputs carry semantics from the task that produced them.
- **Derivation + operator-confirmed scaffolding eliminates over-scaffolding drift.** The alpha-trader E2E's duplicate `track-universe-2` and redundant-task risks both disappear.
- **ADR count net decreases as understanding increases.** ADR-207 supersedes ADR-166 + ADR-188 and refines ADR-206 + amends ADR-205/149/194/195 — one ADR consolidates what previously spanned five.
- **Claude Code pattern alignment.** The chat-centric Loop matches how Claude Code structures a coding session: context (codebase + CLAUDE.md) + primitives (Read/Write/Edit/Bash/Agent) + configuration (CLAUDE.md) + conversation, without a pipeline orchestrator enforcing phases. YARNNN adopts the same ingredients (context = filesystem; primitives = ManageTask/UpdateContext/ProposeAction/etc.; configuration = MANDATE.md; conversation = chat). The workflow emerges from the ingredients rather than being imposed on them. This is the deepest simplification in the ADR — the architecture stops pretending to orchestrate a Loop and instead just provides substrate + tools for YARNNN's prompt strategy to enact one.

### Costs

- **Substantial migration footprint.** Phases 2–5 touch `workspace_init.py`, `workspace_paths.py`, `UpdateContext`, `ManageTask`, `task_pipeline.py`, the CAPABILITIES registry, `agents_role_check`, bot role deletion, TASK_TYPES deletion, prompt updates, two migrations (156 + 157), and frontend preconditions on CreateTaskModal.
- **Alpha persona re-authoring.** Both alpha-trader and alpha-commerce need MANDATE.md authored via the new flow; existing IDENTITY.md content may overlap and need teasing apart.
- **E2E re-run.** The previous E2E's substrate is no longer representative — a clean re-run after Phases 1–5 is needed to validate the reframe end-to-end.
- **Two-mode UX detail.** The Knowledge-mode surface needs intentional design (hide Queue's execute affordance, label proposals as advisory, etc.) — modest but real frontend work.
- **Obs 07 (silent hang) is not fixed by this ADR.** Still requires the orphan-reaping + watchdog fix as a separate commit. Unblocking the E2E re-run is gated on it.
- **Loss of task-type-level prompt cold-start.** YARNNN no longer has a concrete type's `default_objective` + `default_title` to reach for. Prompt must reason from Mandate + Rules every time. Slightly higher per-turn LLM burden; smaller scaffold graph; cleaner semantics.

### Deferred

- **`Learner` role formalization.** The Loop's recursion arrow (Outcome → Rule refinement) is performed by whichever task reads `_performance.md` and emits rule-delta proposals. Not a new archetype; a Rule-authoring pattern. Concrete guidance in a follow-up ADR once patterns settle.
- **Multi-operator (teams) Mandate authoring.** When a workspace has multiple humans, Mandate becomes a shared commitment. Governance of multi-author MANDATE.md is out of scope here; future ADR.
- **Cross-workspace capabilities** (the same operator running multiple Mandates in parallel workspaces). Currently each workspace has one Mandate; if demand emerges for multi-mandate per workspace, revisit.
- **Auto-Mandate revision prompts.** ADR-207 explicitly says no forced revision cadence. If operator signal later suggests revision prompts are valuable, add as opt-in.

---

## Dimensional classification (FOUNDATIONS v6.0)

Primary: **Purpose** (Axiom 3) — Mandate is the strongest Purpose-layer declaration the system has; the Loop is a Purpose-ordered sequence.

Secondary:
- **Substrate** (Axiom 1) — Mandate.md joins the `_shared/` substrate; capabilities read platform_connections substrate; each arrow in the Loop is a substrate write.
- **Identity** (Axiom 2) — the Loop uses only the existing four cognitive layers; bot dissolution cleans the Identity ontology.
- **Trigger** (Axiom 4) — each arrow's trigger sub-shape (Addressed / Periodic / Reactive) is explicit.
- **Mechanism** (Axiom 5) — the Loop traverses the full mechanism spectrum (Addressed judgment at Mandate; deterministic at OUTCOME).
- **Money-truth** (Axiom 8) — Primary Action is the source of every money-truth event; OUTCOME is its substrate home.

---

## Open questions

The chat-centric Loop clarification (see §"The Loop is prompt strategy, not pipeline architecture" above) collapses most of the questions that were open in v1. They dissolve because each one assumed the Loop was a code-level structure requiring enforcement. With the Loop living in prompt strategy + filesystem state + conversation, each question becomes a chat-level reasoning concern rather than an architectural gap:

| Prior question | Collapse under chat-centric framing |
|---|---|
| Does every workspace have a Primary Action? | If MANDATE.md declares one, yes. If not, the workspace is Knowledge-mode (proposals advisory-only). YARNNN detects this at chat-time; no architectural enforcement beyond Mandate existence. |
| Does the Learner arrow need a named task? | No. Rule refinement is whichever task the operator scaffolds that reads `_performance.md` and writes Rule-delta proposals — typically a weekly-review instrument, but YARNNN can also do it conversationally when the operator asks "how's my operation performing?" |
| Knowledge-mode Queue semantics? | YARNNN surfaces it conversationally: *"you're in Knowledge mode; proposals are advisory until Alpaca connects."* Proposals still emit, Reviewer still evaluates, decisions still log. No primitive-layer branching. |
| Mandate granularity? | Chat-level constraint. If an operator declares two Primary Actions, YARNNN pushes back conversationally or recommends splitting into two workspaces. No primitive enforcement. |

**Remaining genuine open questions** (not chat-collapsible):

1. **Workspace-level file versioning** — **RESOLVED by [ADR-209](ADR-209-authored-substrate.md) (2026-04-23).** When the operator revises authored files (MANDATE.md, IDENTITY.md, BRAND.md, CONVENTIONS.md, `_operator_profile.md`, `_risk.md`, `review/principles.md`), the prior state was lost under ADR-207's initial scope — this open question flagged the need for substrate-level versioning. ADR-209 (Authored Substrate) is the resolution. It does NOT ship literal git (ADR-208 v1 was withdrawn); it ships three substrate-level invariants — content-addressed retention, parent-pointer history, authored-by attribution — applied uniformly to every file in `workspace_files`, not just the seven authored paths. Operator revisions to MANDATE.md become new revisions in a parent-pointered chain, attributed to `authored_by='operator'`, always retrievable. Branches and distributed replication (the two git capabilities alpha doesn't need) are deferred as cheaply-recoverable extensions. See ADR-209 and [authored-substrate.md](../architecture/authored-substrate.md) for the full architecture.
2. **Capability availability in the compact index.** The two-mode detection (D6) is a computed property. Should it also surface in YARNNN's compact index every turn, so YARNNN reasons about connection gaps without re-computing? Probably yes — cheap signal, valuable framing. Part of the P2 compact-index update.
3. **Pre-existing alpha-trader `trading-operator` Agent (from the E2E).** YARNNN authored this during the E2E as a stand-in for "operator spec lives somewhere." Under ADR-207, the operator spec lives in MANDATE.md + `_operator_profile.md`. Is the `trading-operator` Agent still needed, or does it dissolve? Likely: dissolves — it was a workaround for missing primitives (Obs 03). Confirm at Phase 6 alpha re-author.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-22 | v1 — Initial proposal. Primary Action as pivot, Mandate as workspace north-star file, seven-arrow Loop using only existing Axiom 2 layers (no invented actors), Deliverables reframed as task sub-parts, Platform Bots → Capabilities completion, two-mode service (Operational / Knowledge), TASK_TYPES registry full sunset with task self-declaration, derivation from filesystem graph. Supersedes ADR-166 + ADR-188; refines ADR-206; amends ADR-149/194/195/205. Implementation plan in six phases. |
| 2026-04-22 | v1.1 — **Chat-centric Loop clarification** added as new §"The Loop is prompt strategy, not pipeline architecture" early in the ADR. Makes explicit: the seven-arrow Loop is YARNNN's cognitive framework + prompt strategy, not a code-level orchestrator. Primitives remain unbiased. Implementation scope is D1/D2/D4-D8; no Loop orchestrator gets built. Pattern aligns with Claude Code (context + primitives + configuration + conversation, no pipeline). Open Questions section rewritten — most of the v1 questions collapse under chat-centric framing; three genuine open questions remain (Mandate revision history semantics, capability-availability in compact index, fate of the E2E-scaffolded trading-operator Agent). Claude Code pattern alignment added to Consequences §Positive. |
| 2026-04-22 | v1.2 — **File versioning explicitly deferred to ADR-208.** Operator feedback: commit to full git-ify approach rather than ship preemptive middle-ground file versioning that would be superseded by a real git backend in the same cycle. ADR-207 P2 Mandate implementation no longer folds in `workspace_file_versions` table or preserve-on-write hooks. Overwrites are acceptable until ADR-208 lands. Open question #1 rewritten accordingly to point at ADR-208. Singular-implementation discipline: we draft ADR-208 before we implement any versioning substrate so the methodology doesn't churn. |
| 2026-04-23 | v1.3 — **Open question #1 resolved via [ADR-209](ADR-209-authored-substrate.md) (Authored Substrate), not ADR-208.** After discourse on git-inspired vs. literal git, ADR-208 v1 was withdrawn and replaced by ADR-209. ADR-209 adopts three of git's five capabilities (content-addressed retention, parent-pointer history, authored-by attribution) natively in Postgres, applied universally to every `workspace_files` entry (not just the seven operator-authored paths). Branches + distributed replication deferred as cheaply-recoverable. Open question #1 pointer updated from ADR-208 → ADR-209. No change to ADR-207's core Mandate/Loop/Capabilities decisions; the versioning dependency simply landed on a better substrate-level design than the withdrawn git-backend approach. |
