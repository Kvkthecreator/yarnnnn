# ADR-206: Operation-First Scaffolding — Intent / Deliverables / Operation as Three Cockpit Layers

> **Status**: Proposed
> **Date**: 2026-04-22
> **Authors**: KVK, Claude
> **Triggered by**: Alpha-1 playbook audit — the alpha personas (`alpha-trader`, `alpha-commerce`) revealed that the operator's value proposition is an autonomous money-generating *operation* with a supervised approval loop, not a collection of AI-produced reports or deliverables. Previous framings (ADR-205 F2's "deliverable-first", ADR-176's "authored team") under-weighted this.
> **Supersedes / amends**: ADR-205 §Frontend Phase 4+5 "F2 Overview→Work merge" framing — the BriefingStrip composition stays but the *primary* `/work` surface becomes a deliverables-first view of operation state, not a task-first view. Workspace-root seeding of `IDENTITY.md` + `BRAND.md` + `CONVENTIONS.md` is moved into `/workspace/context/_shared/`. Signup-scaffolded essential tasks collapse further: only YARNNN the agent persists at signup; daily-update + every back-office-* task materializes lazily on trigger conditions.
> **Amends**: ADR-152 (Unified Directory Registry — adds `_shared/` as a named directory type under `/workspace/context/`); ADR-161 (Daily Update Anchor — "essential heartbeat at signup" dissolves; daily-update becomes an opt-in scaffolded through YARNNN conversation).
> **Reaffirms**: ADR-194 v2 (Reviewer as the fourth cognitive layer with per-proposal capital-EV evaluation); ADR-195 v2 (money-truth in `_performance.md`); ADR-198 v2 (cockpit archetypes — surface vocabulary is unchanged, composition shifts).
> **Extends**: ADR-189 (Three-Layer Cognition — this ADR adds a three-layer *operator-facing* view distinct from the three-layer *cognition* view; the two are orthogonal).

---

## Context

### The Alpha-1 reading

Two alpha personas are specified in full at `docs/alpha/ALPHA-1-PLAYBOOK.md`:

- **`alpha-trader`** — Jim-Simons-inspired systematic retail trader. $25k paper Alpaca. 5–8 declared signals with per-signal rules, risk limits, expectancy tracking. Every trade must have signal attribution. AI Reviewer evaluates proposals against the capital-EV ladder (rule compliance → risk compliance → signal expectancy → sizing math → portfolio diversification). All trades land in the cockpit Queue for human approval. `_performance.md` carries per-signal P&L, win rate, expectancy, Sharpe.
- **`alpha-commerce`** — Korea↔USA dual-directional arbitrage operator. $10k operating budget. 15–30 SKUs in rotation. Declared sourcing / pricing / retirement rules with margin floors, turnover thresholds, FX regime filters. Every product proposal must have rule attribution. Reviewer gates on landed-margin compliance. `_performance.md` carries per-direction + per-SKU attribution.

**What these personas want from YARNNN is not a report.** It is an autonomous money-generating operation with declared rules, run systematically, with the operator supervising via approve/reject on proposed actions, and with money-truth reconciled back into substrate so the system learns which rules are compounding edge and which are decaying.

Key phrases from the playbook:

- *"YARNNN's role is not to help me trade better — it's to help me not drift from the systematic discipline when emotions argue otherwise."* (trader IDENTITY.md)
- *"Propose, never stock autonomously."* (commerce IDENTITY.md)
- *"My edge is not intuition, speed, or conviction — it's measurable."* (trader)
- *"The Reviewer's job is to confirm a proposed trade matches a declared signal's entry rules and that expected value given the signal's track record is positive."* (trader principles.md)

**The loop the playbook describes, made explicit:**

```
Intent (authored rules) → Operation (proposes) → Reviewer (capital-EV gate) →
  → Deliverable (Queue entry surfaces to operator) → Operator (approves/rejects) →
    → Execution (order fires / SKU listed) → Money-truth reconciles →
      → Intent (refined as rules decay or prove out)
```

That is the product. Reports, briefs, and dashboards are *artifacts the operation produces*, not the point of the operation.

### The problem with previous framings

- **ADR-176 "authored team"** framed the moat around the operator authoring agent identities. True but incomplete: the agents serve work; the work is the operation; the operation is what the operator actually authored.
- **ADR-189 "authored-team moat at the list surface"** used the `origin` filter to hide infrastructure. Correct UX move; still frames agents as the first-class object.
- **ADR-205 "primitive collapse + Briefing-strip on /work"** dissolved signup scaffolding cleanly. But its F2 framing leaned toward deliverables-as-primary (Briefing panes above task list). Closer to right, still under-weights the *operation* the deliverables come from.

**The missing lens**: the operator lives in a three-layer ontology. They declare *intent*, they consume *deliverables*, and they drill into *operation* only when a deliverable looks wrong. All three are first-class. The cockpit has surfaced (1) and (3) reasonably but under-surfaced (2) as a cohesive layer.

### Relationship to ADR-189

ADR-189 describes a **three-layer cognition** model: YARNNN (meta-cognitive) + Specialists (role-cognitive) + Agents (domain-cognitive) + Reviewer (per ADR-194, fourth cognitive layer). That taxonomy is about *who acts*.

This ADR describes a **three-layer operator view**: Intent + Deliverables + Operation. That taxonomy is about *what the operator interacts with*. The two are orthogonal and both hold.

---

## Decision

### The three operator-facing layers

| Layer | What it is | Where it lives (filesystem) | Cockpit surface |
|-------|-----------|------------------------------|-----------------|
| **Intent / Objective** | Authored declarations: who the operator is, what rules they're running, what limits they enforce, what success criteria they're measuring against. First-class because it calibrates everything downstream — the operation, the Reviewer, the success metrics. | `/workspace/context/_shared/IDENTITY.md` + `/workspace/context/_shared/BRAND.md` + `/workspace/context/_shared/CONVENTIONS.md` + `/workspace/context/{domain}/_operator_profile.md` + `/workspace/context/{domain}/_risk.md` + `/workspace/review/principles.md` | `/context` + top of `/work` (intent-snapshot card) |
| **Deliverables** | Externalized outputs of the operation. Proposals awaiting review (primary — the Queue), pre-market briefs, weekly performance reviews, `_performance.md` snapshots, retirement recommendations, reconciliation summaries. First-class because it's what the operator *sees and acts on*. | `/tasks/{slug}/outputs/{date}/` + cockpit Queue (action_proposals) + `/workspace/context/{domain}/_performance.md` | `/work` list-mode (primary) + `/review` (Reviewer-authored deliverables) |
| **Operation** | Execution substrate: tasks, agents, reconcilers, scheduler. Second-class. Operators drill into operation details only when a deliverable is surprising. | `agents` table + `tasks` table + `/workspace/context/{domain}/*.md` (accumulated state) + scheduler + Reviewer machinery | `/work` detail-mode + `/team` (deemphasized) |

The loop:

```
Intent (authored in _shared + domain + review) → Operation (scheduled tasks run) →
  Deliverables (proposals, briefs, reviews, performance snapshots surface on /work) →
    Operator (approves/rejects proposals, reads briefs in /chat, refines rules via chat) →
      Intent (refined) → Operation (next cycle)
```

### Signup scaffolding

**Textually present, structurally empty.** A brand-new workspace contains exactly:

| Artifact | Location | State at signup |
|----------|----------|------------------|
| YARNNN | `agents` table, 1 row | role=`thinking_partner`, origin=`system_bootstrap` |
| Workspace identity | `/workspace/context/_shared/IDENTITY.md` | Empty skeleton |
| Workspace brand | `/workspace/context/_shared/BRAND.md` | Empty skeleton |
| Workspace conventions | `/workspace/context/_shared/CONVENTIONS.md` | Seed minimal content (agent-readable filesystem rules) |
| YARNNN memory | `/workspace/memory/awareness.md`, `_playbook.md`, `style.md`, `notes.md` | Empty skeletons |
| Reviewer substrate | `/workspace/review/IDENTITY.md`, `/workspace/review/principles.md` | Empty skeletons (ADR-194) |

**That's it.** No tasks. No context domain directories. No agent roster. No daily-update. No back-office-anything. Signup creates the *shape* of a workspace and nothing of its *operation*.

Migration implications:
- `workspace_init.py` Phase 5 (essential tasks) collapses to zero tasks.
- `workspace_init.py` Phase 3 (workspace files) re-targets `_shared/` nested paths instead of workspace root.
- Migration writes any existing `/workspace/IDENTITY.md` + `/workspace/BRAND.md` + `/workspace/CONVENTIONS.md` to their new `/workspace/context/_shared/*` locations and deletes the originals.

### First-conversation posture (YARNNN)

YARNNN's first-turn objective: **elicit the operation**. Three questions, conversationally:

1. **What operation do you want to run?** (trading / commerce / content / other — domain)
2. **What platform carries the money-truth?** (Alpaca / Lemon Squeezy / Shopify / Stripe / Substack / etc.)
3. **What are your declared rules, risk limits, and principles?** (rich-input acceptance — paste text, upload docs, link references; inferred into structured files per ADR-190)

Once those three answers exist, scaffolding fires:

1. Platform connection → Platform Bot row materializes (ADR-205 lazy creation).
2. `_operator_profile.md` + `_risk.md` + `principles.md` seeded via inference from the operator's rich input.
3. Context domain directory materializes on first write (ADR-205 directory registry collapse).
4. Operational tasks materialize: `track-{domain}` (accumulate market/platform state), `evaluate-{domain}` (rule evaluation over accumulated state), `propose-{domain}` (ProposeAction emission), `reconcile-{domain}` (money-truth reconciliation — may be a back-office task per §"back-office auto-materialize" below), `weekly-review-{domain}` (per-rule attribution report). These are **YARNNN-composed per-operation**, not pre-registered in `workspace_init`.
5. Reviewer's principles.md populated with the domain's capital-EV framework (signal attribution → rule compliance → expectancy → sizing → diversification for trader; margin attribution → rule compliance → turnover → FX regime for commerce).
6. Loop starts. First proposal reaches the cockpit Queue. First operator decision happens.

**The first-run wow moment** is not "YARNNN made you a report." It's **"an operation the operator authored is now running, and a first proposal is awaiting their approval."** That's the inflection the alpha playbook anticipates.

### Back-office tasks — materialize on trigger, never at signup

The four existing back-office tasks become trigger-materialized:

| Task | Materializes when | Visible to operator? |
|------|-------------------|-----------------------|
| `back-office-workspace-cleanup` | Dissolves as a task row entirely. Runs as pure scheduler cron (no `tasks` table presence). | No — pure plumbing. |
| `back-office-proposal-cleanup` | Materializes on first proposal creation in the workspace. | `/settings/system` diagnostic view only. Filtered from `/api/tasks` operator responses. |
| `back-office-agent-hygiene` | Materializes when `>=1` user-authored agent has `>=5` runs. | `/settings/system` only. |
| `back-office-outcome-reconciliation` | Materializes on first platform connection that emits money-truth (commerce / trading). | `/settings/system` only. |

`/api/tasks` default list response excludes tasks whose slug prefix is `back-office-`. A new query param `include_system=true` returns them for the `/settings/system` diagnostic surface.

### `daily-update` — opt-in, not essential

ADR-161's framing of `daily-update` as the essential heartbeat artifact was built on the assumption that operators needed a morning email to feel the service was alive. Post-ADR-205 + ADR-206, that assumption is wrong: the operation running IS what makes the service feel alive.

New semantics:
- Signup does not scaffold `daily-update`.
- When the operation starts producing deliverables, YARNNN offers in chat: *"Want me to email you a daily summary of what happened overnight?"*
- If the operator says yes, YARNNN creates the `daily-update` task via `ManageTask(action="create")`. Standard task lifecycle.
- If the operator says no or defers, nothing is scaffolded.
- The `essential` flag on `daily-update` is removed — it's just a task like any other once created.

### CRUD split — create via modal, manage via chat, direct action via surface click

| Operation | Surface | Rationale |
|-----------|---------|-----------|
| **Create** (task, agent authoring, signal/rule/SKU definition) | Modal (`CreateTaskModal`, `AuthorAgentModal`, `CreateRuleModal`) | High-precision, well-specified. Operator knows what they want. Modal = structured + fast. |
| **Read** (any substrate, any surface) | Direct surface view | Deliverables and intent artifacts render on `/work`, `/context`, `/review`. No conversation required. |
| **Update** (edit rule thresholds, rewrite AGENT.md, adjust risk limits, tune principles.md) | Chat + YARNNN | Judgment-shaped. YARNNN asks "why", reads `_performance.md` with the operator, suggests alternatives. |
| **Delete / archive / pause** | Chat + YARNNN, with confirmation | Irreversibility warrants conversation. YARNNN writes deletion attribution to `memory/awareness.md`. |
| **Approve / reject proposal** (money-bearing actions) | Direct click on cockpit Queue / `/work` | Not CRUD. Surface-level action on a deliverable. YARNNN observes (compact index shows the decision). |

**YARNNN is always observing, never mandatory as mediator.** Every click, every approval, every file edit becomes context YARNNN sees in the compact index (ADR-159). The operator never leaves YARNNN's awareness. But routing every operator action through chat would create friction for no benefit; direct surface actions on deliverables (approve a proposal, click to pause a task from settings) are faster and YARNNN still sees them.

### Reviewer's role in the loop — hardening

The Reviewer (ADR-194 v2, fourth cognitive layer) is the **per-proposal capital-EV gate** between operation and operator attention. It runs automatically via the `review-proposal` reactive task fired by `handle_propose_action` post-insert. For each proposal:

1. **Read** `_operator_profile.md` (rules) + `_risk.md` (limits) + `_performance.md` (EV state) + `principles.md` (calibration framework).
2. **Execute** the domain-specific check ladder (6-check Simons ladder for trader; margin-compliance ladder for commerce; each domain declares its own via `principles.md`).
3. **Emit** one of `approve` / `reject` / `defer` with structured reasoning and confidence.
4. **Write** the decision to `/workspace/review/decisions.md` (append-only audit trail).

Outcome handling:

- **`approve`** + principles.md authorizes auto-approve under this rule's threshold → proposal executes immediately. Queue entry shows "auto-approved by Reviewer, executed at {timestamp}".
- **`approve`** + no auto-approve policy → defer to human; Queue entry shows "Reviewer recommends approve: {reasoning}".
- **`reject`** → proposal is filtered out of Queue entirely. Operator never sees rejected proposals unless they drill into `/review`. Discipline automated.
- **`defer`** → Queue entry shows "Reviewer wants your input: {reasoning}". Operator decides.

For Alpha-1, `principles.md` defaults to no auto-approve on any rule — the Reviewer is observe-and-recommend. This ADR does not change that; it ratifies the role.

**The Reviewer's two-facing value:**

- **To the operation**: discipline enforcer. Rule-violating proposals never surface to the operator.
- **To the operator**: structured-reasoning companion. Every Queue entry includes the Reviewer's evaluation chain, which is the operator's own declared discipline made readable.

### The chat boundary — what belongs in chat, what belongs on surfaces

| Kind of thing | Surface |
|---------------|---------|
| Declaring intent (rules, signals, sourcing, principles) | Chat (rich input → inference → `_shared/*` + `_operator_profile.md` + `_risk.md` + `principles.md`) |
| Refining intent (edit thresholds, adjust limits, retire rules) | Chat (judgment-shaped) |
| Reading intent | `/context` (structured render) |
| Reading deliverables | `/work` list + `/review` (scannable, actionable) |
| Approving / rejecting deliverables (proposals) | Direct click on Queue |
| Discussing a specific deliverable ("why was this flagged?") | Chat + YARNNN (with that deliverable as context) |
| Creating a new task | Modal (CreateTaskModal) |
| Updating / deleting a task | Chat + YARNNN |
| Reading operation state (runs, agent status) | `/work` detail + `/team` |
| Pausing / resuming infrastructure | `/settings/system` |

**Rule of thumb**: direct surface action for *high-precision actions on a known artifact*. Chat for *judgment-shaped or context-rich actions*. YARNNN observes all of it regardless.

---

## What changes (scope for the implementation ADR-206 unlocks)

This ADR is a proposal, not an implementation. Implementation lands in subsequent commits. Scope:

### Phase 1 — Substrate (backend)

1. **Relocate `IDENTITY.md` + `BRAND.md` + `CONVENTIONS.md`** from `/workspace/` root to `/workspace/context/_shared/`. Migration 155 reads existing `workspace_files` rows at root paths and writes them to nested paths, then deletes originals. Update every read/write site: `working_memory.py`, `primitives/shared_context.py`, `context_inference.py`, `workspace.py`, `workspace_init.py`. Single-commit rename discipline.
2. **Relocate YARNNN working-memory files** (`AWARENESS.md`, `_playbook.md`, `style.md`, `notes.md`) from `/workspace/` root to `/workspace/memory/`. Migration pattern same as above.
3. **Collapse `workspace_init.py` Phase 5 to zero tasks.** Delete scaffolding calls for `daily-update`, `back-office-*`, `maintain-overview`. Phase 3 retargets `_shared/` + `memory/` paths.
4. **Back-office auto-materialize.**
   - `back-office-workspace-cleanup`: dissolve from `tasks` table. Runs as a scheduler cron function.
   - `back-office-proposal-cleanup`: materialize in `handle_propose_action` on first proposal.
   - `back-office-agent-hygiene`: materialize when threshold hit (checked by a lightweight scheduler probe).
   - `back-office-outcome-reconciliation`: materialize on platform connect (commerce/trading) in `routes/integrations.py`.
5. **`/api/tasks` filter.** Default response excludes tasks whose slug starts with `back-office-`. New query param `include_system=true` restores them.
6. **`daily-update` essential flag removed.** Migration 155 also sets `essential=false` on existing daily-update rows.
7. **ADR-162 directory registry amendment.** `WORKSPACE_DIRECTORIES` gains a `_shared` entry marking the shared authored-context folder. `AGENT.md` / task / agent docs updated to read from new paths.

### Phase 2 — Prompt layer

1. **YARNNN first-turn posture rewrite** in `yarnnn_prompts/onboarding.py`. Replace "elicit identity + first deliverable" framing with "elicit operation (domain + platform + rules)." Eliciting the three artifacts (`_operator_profile.md`, `_risk.md`, `principles.md`) is the gateway to the loop.
2. **Working memory re-render.** `format_compact_index()` surfaces intent + deliverables + operation as three labeled sections. Currently conflates them.
3. **Tool guidance** (`tools.py`, `tools_core.py`) updated to reflect intent/deliverables/operation framing and the CRUD split rule.

### Phase 3 — Frontend

1. **`/work` list-mode reshape.** Primary pane becomes deliverables-first: proposals awaiting review (cockpit Queue / NeedsMe) + latest briefs + upcoming scheduled outputs + `_performance.md` delta snapshot. Tasks appear as *scheduled producers of deliverables*, grouped by deliverable-kind, not by slug. BriefingStrip composition survives but its ordering re-prioritizes NeedsMe + `_performance.md` snapshot to the top.
2. **`/context` list-mode re-organization.** Group by the three concerns: `_shared/` (workspace identity) / domain contexts / `/review/` (Reviewer substrate). Intent artifacts are first-class, not mixed with accumulated domain entities.
3. **`CreateTaskModal`** (ADR-205 F3 deferred) ships as the explicit-intent create surface. Fields: title, output_kind, mode, context, optional schedule, optional sources.
4. **`AuthorAgentModal`** + **`CreateRuleModal`** (new) — create flows for agent authoring and rule/signal/SKU declaration. Update / delete flows route through chat.
5. **`/settings/system`** — diagnostic view of back-office plumbing (last run, next scheduled, pause toggle). Not nav-primary.
6. **`/overview` redirect stub removed after one release cycle** (pending bookmark decay).

### Phase 4 — Docs

1. **FOUNDATIONS.md**: add a Corollary under Axiom 3 (Purpose) naming the three-layer operator view — Intent / Deliverables / Operation. The operator-facing view complements the four-layer cognition view (Axiom 2).
2. **GLOSSARY.md**: add `Intent`, `Deliverable`, `Operation`, `Loop` as canonical operator-facing terms.
3. **`docs/architecture/workspace-conventions.md`**: update path conventions for `_shared/` + `memory/` relocation.
4. **`docs/architecture/primitives-matrix.md`**: note that `ManageTask(action="create")` and `ManageAgent(action="create")` are the modal-backed create paths; update / delete remain chat-first per §CRUD split.

---

## What doesn't change

- **FOUNDATIONS v6.0 axioms.** All eight preserved. New corollary added under Axiom 3.
- **ADR-168 primitive matrix.** No primitive added, no primitive removed.
- **ADR-141 execution pipeline.** The pipeline still dispatches as before; only *what tasks exist* and *when they materialize* changes.
- **ADR-194 Reviewer seat.** Role hardened and made explicit in the loop; no structural change.
- **ADR-195 money-truth substrate.** Unchanged.
- **ADR-189 three-layer cognition model.** Preserved. This ADR adds an orthogonal three-layer operator view.
- **ADR-205 backend (Architecture Y lazy scaffolding).** Preserved. This ADR extends the scaffolding collapse further (essential tasks, `_shared/` relocation) but keeps the lazy-ensure helpers and migration pattern.
- **Chat as first tab (ADR-205 F1).** Unchanged.
- **BriefingStrip (ADR-205 F2).** Composition preserved; pane ordering re-prioritizes post-implementation.
- **User-authored Agents.** Unchanged.

---

## Consequences

### Positive

- **Cockpit reads the way operators think.** Intent (what I declared) → Deliverables (what I see and act on) → Operation (how it runs, drill-down only). No more confusion between "tasks I scheduled" and "what's happening on my behalf."
- **First-run wow moment is the loop starting**, not a pre-baked report. Matches the alpha playbook's value prop: operator authors → operation runs → proposal reaches operator → operator decides → edge compounds.
- **Reviewer's role becomes operator-legible.** The Reviewer is not a gate bureaucracy; it's the operator's own declared discipline made executable and auditable.
- **Signup surface genuinely empty.** 0 essential tasks, 0 context domain directories, 0 Specialists. Only YARNNN + the `_shared/` authored-context skeletons. The workspace is the operator's to author.
- **Back-office invisibility.** Plumbing materializes on trigger, surfaces only in `/settings/system`. Operator attention stays on the operation, not on YARNNN's internal maintenance.
- **CRUD split aligns with cognitive weight.** Create = precise modal; update/delete = judgment via chat; approve = direct surface click. Each mode where it belongs.
- **Substrate hygiene improves.** `/workspace/` root contains only operational folders (`/tasks/`, `/agents/`, `/context/`, `/memory/`, `/review/`, `/working/`, `/uploads/`). Authored shared context nests correctly under `/context/_shared/`.

### Costs

- **Migration 155 touches many read/write sites.** `IDENTITY.md` + `BRAND.md` + `CONVENTIONS.md` + `AWARENESS.md` + `_playbook.md` + `style.md` + `notes.md` path moves, plus the ~10 reader sites in `working_memory.py`, `context_inference.py`, `shared_context.py`, `workspace.py`, `workspace_init.py`. Singular-implementation discipline: single commit, no dual-read compatibility.
- **Existing alpha workspaces (alpha-trader, alpha-commerce) need re-seeding.** The playbook personas are authored around `/workspace/IDENTITY.md` at the root. Post-ADR-206 they live at `/workspace/context/_shared/IDENTITY.md`. Migration 155 handles the move. Downstream: every alpha-operations doc that cites the old path needs a grep-update.
- **First-conversation posture rewrite is substantial.** The operation-elicitation flow must elicit three artifacts conversationally before scaffolding fires. TP-prompt authoring + test iteration. Alpha-1 is the real test harness for this; validation loop is tight.
- **`/api/tasks` filter default + query param** is a contract change. Frontend consumers (admin pages, `/work`, `/settings/system`) must opt in via `include_system=true` where they want plumbing visibility.
- **`daily-update`'s loss of essential status** requires a migration flag flip + awareness across the cockpit Briefing pane (which currently relies on daily-update existing to show "your last morning brief").
- **Modal authoring work (CreateTaskModal, AuthorAgentModal, CreateRuleModal) is non-trivial**. Deferred from ADR-205 F3; now explicit scope.

### Deferred

- **Auto-approve thresholds in `principles.md`.** For Alpha-1 every proposal defers. Post-Alpha-1, operators can declare auto-approve-below-threshold rules. The Reviewer supports it today; this is a principles.md authoring concern, not an architecture gap.
- **Multi-domain operations in one workspace.** An operator running both trading and commerce simultaneously. Architecturally supported (context domains are independent), but the cockpit surface design for "which operation am I looking at?" deserves its own ADR once the dual-domain use case emerges.
- **Operation versioning / hypothesis tracking.** When an operator retires Signal 2 and adds Signal 6, the historical performance of the operation-as-configured-before is interesting analytically. Track via `_operator_profile.md` version history (`/history/_operator_profile-v{N}.md` per ADR-119). Not a new ADR, a discipline.
- **External channel delivery of Queue items.** Email digest of pending approvals? Push notification? ADR-202's pointer discipline applies; implementation is a follow-up.

---

## Dimensional classification (FOUNDATIONS v6.0)

Primary: **Purpose** (Axiom 3) — the operator's ontology becomes first-class; intent + deliverables + operation is a Purpose-layer articulation. New Corollary under Axiom 3 added.

Secondary:
- **Substrate** (Axiom 1) — `_shared/` relocation + back-office materialization-on-trigger.
- **Channel** (Axiom 6) — CRUD split routes direct actions to surfaces, judgment actions to chat; same underlying substrate, different Channel cells.
- **Identity** (Axiom 2) — Reviewer role hardening makes the fourth cognitive layer's in-loop function explicit.

---

## Open questions

1. **Single-domain vs. multi-domain workspaces at alpha scale.** `alpha-trader` and `alpha-commerce` run as *separate workspaces* per the playbook. Is that the right default long-term, or should one workspace eventually host multiple operations? Post-Alpha-1 decision.
2. **Proposal streaming.** Some operations fire many proposals rapidly (intraday signal evaluation). The cockpit Queue pattern works well for 3–10 pending items but degrades at 50+. Pagination + Reviewer-filtered default view handles most cases; extreme cases may warrant per-domain Queue segmentation.
3. **`_shared/` file authoring surface.** Today, operators edit `_shared/IDENTITY.md` via chat (YARNNN writes via `UpdateContext`). Should `/context` have an inline editor for `_shared/*` files? (F4 `ManageContextModal` from ADR-205 covers this — yes.)
4. **Attribution for operator actions vs. YARNNN actions.** Current session auth tags everything `human:<user_id>`. Post-ADR-205 + ADR-206, YARNNN writes to `_shared/*` on the operator's behalf; direct editor writes via modal also tag `human:<user_id>`. Operator-vs-YARNNN attribution needs a session-metadata flag if it becomes forensically interesting. Not blocking for alpha.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-22 | v1 — Initial proposal. Three-layer operator view (Intent / Deliverables / Operation). Operation-first scaffolding. `_shared/` relocation. Back-office auto-materialize. CRUD split. Reviewer role hardening. Supersedes ADR-205 F2's "deliverable-first" framing; amends ADR-152 (`_shared/` directory type) and ADR-161 (daily-update opt-in). |
| 2026-04-22 | v1.1 — **Phase 1 backend shipped.** File relocations via migration 155 (IDENTITY/BRAND/CONVENTIONS → `/workspace/context/_shared/`, AWARENESS/_playbook/style/notes → `/workspace/memory/`). `workspace_init.py` Phase 5 collapsed to zero operational tasks; `daily-update` + all `back-office-*` + `maintain-overview` no longer scaffolded at signup. `daily-update` loses `essential` flag. `workspace_paths.py` constants module added. Back-office auto-materialize wired: `back-office-proposal-cleanup` in `handle_propose_action`; `back-office-outcome-reconciliation` in commerce + trading OAuth connect; `back-office-agent-hygiene` via hourly scheduler probe at ≥5-run threshold. `GET /api/tasks` filters `back-office-*` from default response (`include_system=true` param restores). `materialize_back_office_task()` helper is the single entry point for on-trigger materialization. All 17 touched modules compile cleanly. Phases 2 (prompt layer) + 3 (frontend) deferred to follow-up sessions. |
