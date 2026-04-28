# ADR-217: Workspace Autonomy Substrate — Single Authoring Mouth for Delegation

> **Status**: Proposed — staged implementation across three commits (this ADR, substrate+wiring, scaffold migration). **D5 dispatch ordering amended 2026-04-28 by [ADR-229](./ADR-229-judgment-first-dispatch-and-generative-defer.md)**: `is_eligible_for_auto_approve` renamed to `should_auto_execute_verdict` and runs as a *post-judgment binding gate*, not a pre-judgment dispatch gate. Reviewer renders verdicts on merits; AUTONOMY filters whether the verdict binds. Narrowing-only invariant (D4) preserved.
> **Date**: 2026-04-24
> **Authors**: KVK, Claude
> **Dimensional classification**: **Purpose** (Axiom 3) primary, **Substrate** (Axiom 1) + **Mechanism** (Axiom 5) secondary.
> **Supersedes**: `/workspace/review/modes.md` as the home of autonomy declaration. File deleted; its role absorbed by `/workspace/context/_shared/AUTONOMY.md` under the principal-authorship model.
> **Amends**: ADR-194 v2 (Reviewer seat substrate — modes.md removed from seat canon), ADR-211 (Reviewer Phase 4 — modes.md deprecated as Reviewer-owned file), ADR-216 (persona-wiring extended to read workspace autonomy).
> **Amended by**: ADR-229 (gate inversion; `is_eligible_for_auto_approve` → `should_auto_execute_verdict` with verdict parameter).

---

## Context

The 2026-04-24 alpha-trader E2E validation of ADR-216 Commit 2 persona-wiring surfaced a governance conflict the AI Reviewer correctly identified in its own verdict:

- `/workspace/review/modes.md` declared `autonomy_level: bounded_autonomous` + `auto_approve_below_cents: 2000000`.
- `/workspace/review/principles.md` declared "Auto-approve = NONE for Alpha-1" as a principle.
- `/workspace/context/_shared/MANDATE.md` declared an amended Autonomy scope clause permitting bounded autonomy on paper.

Three files, three mouths, one conceptual concern (how autonomous is the AI allowed to be on my behalf). The Reviewer resolved the conflict by deferring to the strictest — architecturally correct under its persona (Simons refuses to override declared rules) but symptomatic of a deeper architectural issue: **autonomy is being authored in multiple places with no canonical source**.

Operator instinct confirmed the diagnosis: the right shape is a single workspace-level autonomy substrate, not three levers requiring symmetric updates. More subtly, the current placement of modes.md under `/workspace/review/` is an **authorship-vs-readership category mistake** — it's shaped around "what the Reviewer reads" rather than "what the operator authors." The Reviewer reading a file does not make that file the Reviewer's to own.

### What makes modes.md's current location wrong

`/workspace/review/` files fall into two categories:

1. **Seat-bound operator authorship** — IDENTITY.md (persona the seat embodies), principles.md (framework the seat applies). Operator-authored; structurally bound to the seat because rotating the seat changes the persona and framework.
2. **Seat-generated output** — decisions.md (verdict trail), OCCUPANT.md + handoffs.md (rotation state), calibration.md (track record).

modes.md fits neither. It is not seat-bound: rotating the Reviewer seat should not change how autonomous the AI is allowed to be on the operator's behalf. The operator's standing intent ("up to $20K on paper") is unchanged by which occupant fills the seat. A new occupant inherits the same delegation. It is also not seat-generated; the operator authors it.

Putting autonomy under `/workspace/review/` amounts to "the Reviewer authorizing itself." Proper principal-agent architecture: the principal (operator) authors the delegation; the agent (Reviewer persona) executes within it.

### What makes AUTONOMY belong under `_shared/`

`/workspace/context/_shared/` is the canonical home for operator-authored standing declarations per ADR-206:

- IDENTITY.md — who the operator is.
- BRAND.md — how the operation presents.
- CONVENTIONS.md — filesystem and behavioral conventions for the workspace.
- MANDATE.md — the Primary Action declaration (ADR-207).

All four: operator-authored, workspace-scoped, read by every agent that needs them, survive seat rotation, edit cadence independent of any agent's substrate. AUTONOMY belongs in the same cluster — delegation is the fifth workspace-wide standing declaration.

---

## Decision

### D1 — Autonomy is workspace-scoped and operator-authored

Autonomy is the operator's standing intent about how much judgment authority the AI carries on their behalf. It is:

- **Workspace-scoped**: one AUTONOMY.md per workspace. Not per-task, not per-agent, not per-occupant.
- **Operator-authored**: only the operator (or their authorized delegate via YARNNN chat using `UpdateContext`) writes it. No agent writes autonomy on the operator's behalf — that would be the servant writing their own permission slip.
- **Domain-aware**: a single file declares defaults + per-domain overrides. One workspace can have bounded-autonomous trading and manual commerce without fragmenting authorship across files.
- **Purpose-axis** (FOUNDATIONS Axiom 3): autonomy encodes *what the operator intends the AI to decide on their behalf*. The Purpose-axis declaration flows through Mechanism (how the machinery executes within that permission).

Task `mode` (recurring / goal / reactive) stays as **temporal behavior only** — when the task fires. Task `required_capabilities` in TASK.md stays as **tool permission only** — what tools the task may invoke. Neither declares autonomy; both are orthogonal to it. The effective autonomy of any task is: `AUTONOMY.md permits for the domain` AND `task.required_capabilities are granted by platform_connections`. Both conditions must hold.

### D2 — Canonical location: `/workspace/context/_shared/AUTONOMY.md`

Sibling to MANDATE.md, IDENTITY.md, BRAND.md, CONVENTIONS.md. Scaffolded at workspace signup with a generic default (manual across all domains). Operator authors specific delegation as confidence grows. Revision chain via ADR-209 Authored Substrate preserves full tuning history.

Canonical schema (YAML frontmatter + operator narrative):

```markdown
---
# Workspace autonomy declaration (ADR-217). Read at reasoning time by the
# Reviewer dispatcher and at execution time by the task pipeline capability
# gate. Operator-authored; no agent writes here. Edit via YARNNN chat
# (UpdateContext target=autonomy) or directly via Files tab.

default:
  level: manual                 # manual | assisted | bounded_autonomous | autonomous
  # ceiling_cents: 0            # threshold for bounded_autonomous (omit for manual/assisted/autonomous)
  # never_auto: []              # action_type substrings that always require human approval

domains:
  # Per-domain overrides. Each key is a context domain slug (trading,
  # commerce, email, etc.). Keys present here override `default` for that
  # domain. Domains absent here use `default`.

  # Example — uncomment and tune to activate:
  # trading:
  #   level: bounded_autonomous
  #   ceiling_cents: 2000000      # $20,000 notional ceiling per trade
  #   never_auto: [cancel_order]
---

# Autonomy — how I delegate judgment authority to the AI

<!-- Narrative body: operator-authored commentary on why this autonomy
     posture exists, what confidence state justifies it, what would
     trigger re-tightening. This reads alongside the frontmatter by the
     Reviewer persona — narrative context informs how the persona
     reasons about the raw delegation. -->
```

Narrative + frontmatter. Frontmatter is the machine-readable policy; narrative is the operator-to-AI explanation of *why* the policy is what it is (which helps a persona-aware Reviewer reason about edge cases the policy doesn't explicitly cover).

### D3 — modes.md dissolves

`/workspace/review/modes.md` is deleted. Its role — per-domain autonomy configuration — is absorbed entirely by AUTONOMY.md. Singular implementation: one authoring mouth, one file, one read-path. No dual path. No shim.

**What modes.md carried and where it moves**:

| modes.md field | Destination |
|---|---|
| `autonomy_level` | `AUTONOMY.md` frontmatter `domains.<domain>.level` (or `default.level`) |
| `scope` | Dropped — redundant with the domain key itself |
| `on_behalf_posture` | Dropped — Reviewer's posture derives from IDENTITY.md persona + principles.md framework. Operational posture is not a separate declaration. |
| `auto_approve_below_cents` | `AUTONOMY.md` frontmatter `domains.<domain>.ceiling_cents` |
| `never_auto_approve` | `AUTONOMY.md` frontmatter `domains.<domain>.never_auto` |

`on_behalf_posture` dissolution is deliberate: the Reviewer persona decides how it presents verdicts (recommend-only vs act-on-behalf) based on its IDENTITY declaration and the active domain's autonomy level. There is no third per-domain knob. The Simons persona with `level: bounded_autonomous` acts within its delegation; the same persona with `level: manual` defers. Same persona, different delegation — that's the Purpose axis doing its job.

### D4 — principles.md loses its operational policy section

Under ADR-194 v2 + ADR-211, principles.md was shaped to carry both:

- **Principles** (framework invariants) — "every proposal needs signal attribution," "conviction-based sizing is out of vocabulary," etc.
- **Operational policy** — "Auto-approve = NONE for Alpha-1."

ADR-217 splits these cleanly. principles.md keeps **principles only** — the declared framework the persona applies. Operational policy moves to AUTONOMY.md in full.

**Narrowing condition preservation**: principles.md CAN add *narrowing* defer conditions on top of the autonomy ceiling. Example: "Even when AUTONOMY.md permits bounded auto-approve, defer any proposal if `_performance.md` for the signal has fewer than 20 realized trades." This is a principle (framework invariant authored by the operator as the persona's discipline) that layers on top of the raw autonomy grant. **The servant can be more conservative than the master permits, never more permissive.** This rule is explicit in the Reviewer's persona prompt per Commit 2 of this ADR.

Existing principles.md files authored under ADR-194 v2 that carry operational policy (e.g. the current alpha-trader scaffold's "Auto-approve = NONE for Alpha-1" clause) require operator migration: the operational language moves to AUTONOMY.md; principles.md retains the framework. Migration happens at the workspace level (scaffold update) plus a one-time note in the ADR-217 Phase 3 scaffold pass.

### D5 — Reviewer dispatcher reads AUTONOMY.md; modes.md path deleted

`api/services/review_policy.py::load_modes()` is renamed to `load_autonomy()` and reads `/workspace/context/_shared/AUTONOMY.md`. `REVIEW_MODES_PATH` + `MODES_PATH` constants deleted. The parser's domain-aware YAML shape is preserved with `default` as a new top-level key meaning "applies when no per-domain override exists."

`is_eligible_for_auto_approve()` signature unchanged (takes a domain-scoped policy dict). Its reasoning unchanged. The only structural change is where the dict comes from. `modes_for_domain(autonomy, context_domain)` becomes `autonomy_for_domain(autonomy, context_domain)` with the same fallback-to-default semantics, now explicit via the `default` key rather than implicit via empty dict.

ADR-216 Commit 2 persona-aware Reviewer prompt gains a sentence: *"The workspace's autonomy delegation is declared in `/workspace/context/_shared/AUTONOMY.md`. Your principles can narrow this (add defer conditions) but never widen it. When a principle and the raw delegation conflict on auto-approve eligibility, apply the stricter."*

### D6 — Chat-surface autonomous-action notifications (operator visibility)

When autonomy permits the AI to act without human click, a `role='system'` message lands in the workspace's active chat thread immediately after the action executes. Same mechanism as ADR-212 unified chat thread's `role='reviewer'` messages. Content:

- What action was taken (action_type + inputs summary).
- Which proposal was approved (proposal_id + Reviewer verdict).
- Which Reviewer identity made the call (`ai:reviewer-sonnet-v2`, `human:<user_id>`, etc.).
- Outcome reference (platform order id, external system pointer).
- One-line confidence tell (e.g. "Within $3,390 of the $20,000 ceiling").

Same message also lands in the daily-update briefing under a dedicated "Autonomous actions" section (ADR-198 Briefing archetype). Together the chat inline stream + daily digest give the operator continuous and retrospective visibility into what the AI did on their behalf. Operator can always ask YARNNN "what did you approve yesterday?" and get a substrate-grounded answer by reading the chat thread or briefing.

Frontend work for the chat-surface notifications lands in a follow-on commit (Phase 4, post-ADR-217). This ADR ratifies the contract; the substrate write happens in Phase 2 along with the backend wire-up.

### D7 — No task-level autonomy override

Tasks cannot declare per-task autonomy overrides. A task that needs stricter-than-workspace autonomy is really operating in a different domain; the operator authors that in AUTONOMY.md as a finer-grained domain override. This keeps authoring in one place.

The pragmatic exception if ever needed: a task's `required_capabilities` list already gives permission-level control ("this task can't submit orders because `write_trading` is not granted"). That's adequate for most task-level narrowing without introducing an autonomy axis.

### D8 — Seat rotation does not touch AUTONOMY.md

OCCUPANT.md rotation (human ↔ AI ↔ external) under ADR-194 v2 Phase 2b explicitly does not modify AUTONOMY.md. Delegation is operator-to-role, not operator-to-occupant. A new occupant inherits the existing delegation ceiling. If the operator wants to tighten or loosen autonomy coincident with a rotation (reasonable pattern: "I'm switching to a less calibrated persona, let me lower the ceiling"), that's a separate explicit edit to AUTONOMY.md before the rotation.

---

## Dimensional test

Under FOUNDATIONS v6.0 six-axis model:

| Concept | Primary axis | Secondary axis | Substrate home |
|---|---|---|---|
| **Autonomy delegation** (AUTONOMY.md) | Purpose (Axiom 3) — operator's standing intent about AI judgment authority | Substrate (Axiom 1) — authored substrate, revision-chained | `/workspace/context/_shared/` |
| **Reviewer persona** (IDENTITY.md) | Identity (Axiom 2) — who the seat embodies | Substrate (Axiom 1) | `/workspace/review/` |
| **Reviewer framework** (principles.md) | Purpose (Axiom 3) — what checks the persona applies | Substrate (Axiom 1) | `/workspace/review/` |
| **Task temporal behavior** (task.mode) | Trigger (Axiom 4) — when work fires | Mechanism (Axiom 5) | `tasks` table + TASK.md |
| **Task tool permission** (required_capabilities) | Mechanism (Axiom 5) — what tools the task may invoke | Channel (Axiom 6) — platform connection gates | TASK.md |

The three persona-bearing reads (AUTONOMY, IDENTITY, principles) fall on different primary axes — they are not redundant. AUTONOMY is the operator's intent (Purpose); IDENTITY is the judgment character (Identity); principles is the applied framework (Purpose, but at the agent level). Collapsing any two into a single file would conflate axes and lose revision-chain legibility.

---

## Consequences

### What this unlocks

1. **Singular authoring mouth for delegation.** One file to edit when tuning autonomy. No more "did I update modes and principles and MANDATE?" checklist. The operator's mental model matches the substrate.
2. **Cleaner seat-rotation semantics.** Swapping Reviewer occupants (human ↔ AI, AI-model version updates, impersonated admins) never risks touching autonomy. The delegation is structurally separated from the seat.
3. **Symmetric with MANDATE pattern.** Both MANDATE.md and AUTONOMY.md are under `_shared/`, both are operator-authored standing declarations, both are read by every agent that needs them, both are edited via YARNNN chat with `UpdateContext` targeting their specific file. Same authoring surface, same cadence.
4. **Enables chat-inline autonomous-action visibility (D6).** The operator can follow along in the chat stream as autonomous actions execute, not just retrospectively. This is what lets bold autonomy feel safe — visibility is continuous, not retrospective-only.
5. **principles.md clarifies.** Principle-vs-policy separation lets the Reviewer's persona declare framework invariants independent of delegation ceilings. Both evolve independently; their interaction is declaratively transparent.

### What this costs

1. **Migration of existing workspaces.** Every workspace with a modes.md needs a one-time conversion to AUTONOMY.md. Scripted migration in Phase 3 handles it.
2. **ADR-194 v2 + ADR-211 amendment.** Reviewer substrate's seven-file canon shrinks to six (modes.md deleted). Docstrings and references across those ADRs need updating in the same commit.
3. **principles.md editing surface.** Today the alpha-trader principles.md carries an Auto-approve policy section that becomes operational-policy-leak under ADR-217. The scaffold update deletes that section and moves its content to AUTONOMY.md.
4. **Parser compatibility.** The new `default` top-level key requires a tiny parser update. The modes.md parser already does per-domain; adding "default" as a reserved domain name covers it.

### What remains unchanged

- FOUNDATIONS v6.0 axioms.
- ADR-168 primitives matrix.
- ADR-141 task execution pipeline.
- ADR-205 workspace scaffold collapse (AUTONOMY.md becomes the fifth `_shared/` file at signup, alongside MANDATE + IDENTITY + BRAND + CONVENTIONS).
- ADR-209 Authored Substrate — AUTONOMY.md is revision-chained like any other `_shared/` file.
- ADR-212 YARNNN-as-orchestration-surface classification. YARNNN reads AUTONOMY.md the same way it reads MANDATE.md — informs chat reasoning about what the AI is authorized to do on the operator's behalf. This is not "YARNNN having persona"; it's YARNNN knowing the workspace's delegation boundaries to route chat appropriately.
- ADR-216 YARNNN/Reviewer/domain-Agent taxonomy. AUTONOMY.md is operator-authored, not persona-bearing; fits cleanly into the operator-intent-substrate category alongside MANDATE.

---

## Alternatives considered

### Alt 1 — Collapse IDENTITY + AUTONOMY + principles into one file

Tempting: one substrate file per agent carrying all three concerns. Rejected because:

- **Different edit cadences.** IDENTITY rotates rarely (persona change), AUTONOMY tunes frequently (confidence calibration), principles evolve occasionally (framework refinement). Revision chains per-file give legible history; collapsed file loses per-concept attribution.
- **Different authorship authorities.** All three are operator-authored today, but the architecture shouldn't assume so forever. Principles in particular might admit co-authored templates in the future (regulatory bodies, third-party risk teams). Collapsed file precludes this.
- **Different read-sites at different times.** Task pipeline capability gate needs AUTONOMY only; Reviewer at reasoning time needs all three; a future Auditor might need principles only. Separate files are composable.

### Alt 2 — Keep modes.md but remove operational-policy from principles

Smallest-possible-change path. Rejected because:

- **Preserves authorship category mistake.** modes.md still lives under `/workspace/review/` declaring operator intent, which perpetuates the "servant writing own permission slip" architectural tell.
- **Doesn't unify with MANDATE pattern.** MANDATE lives in `_shared/` because it's operator-authored standing declaration. Autonomy is the same category. Keeping modes.md in review/ while MANDATE is in `_shared/` is asymmetric for no good reason.
- **Doesn't close the E2E conflict source.** The original conflict was "three mouths with no canonical source." Alt 2 reduces to two mouths but doesn't elevate any one of them to canonical.

### Alt 3 — Make autonomy per-task

Tasks declare their own autonomy in TASK.md. Rejected because:

- **Contradicts operator mental model.** Operators think "how autonomous is my AI?", not "how autonomous is each of my 17 tasks?" Per-task autonomy fragments the operator's standing intent into micro-decisions they don't naturally author.
- **Multiplies governance conflict risk.** 17 tasks × 4 autonomy levels = 68 combinatorial states to track. The operator can't reason about that; the Reviewer's conflict-resolution becomes combinatorially worse.
- **Task `mode` is temporal, not authority-carrying** (ADR-138 + ADR-217 D1). Conflating temporal behavior with authorization re-creates the pre-ADR-216 YARNNN-as-Agent category mixing.

### Alt 4 — Put AUTONOMY in `/workspace/review/` anyway

"The Reviewer reads it; put it near its reader" logic. Rejected because authorship-vs-readership category mistake (covered in Context section). Placement follows authorship, not read-path. Git-style revision chains make cross-directory reads free — there's no performance cost to placement that matches authorship.

---

## Implementation — three-commit staging

### Commit 1 (this ADR): ratification, docs only

- ADR-217 landing with the eight decisions locked in.
- ADR-194 v2 status banner amended: "modes.md removed from Reviewer substrate canon per ADR-217 — autonomy now workspace-scoped under `_shared/`."
- ADR-211 status banner amended: same note.

### Commit 2: substrate + wiring

- `api/services/workspace_paths.py` — add `SHARED_AUTONOMY_PATH = "context/_shared/AUTONOMY.md"` and `AUTONOMY_PATH = "/workspace/" + SHARED_AUTONOMY_PATH`. Remove `REVIEW_MODES_PATH` + `MODES_PATH`.
- `api/services/review_policy.py` — rename `load_modes()` → `load_autonomy()`, rename `modes_for_domain()` → `autonomy_for_domain()`. Update `_parse_keyed_yaml` to treat `default:` as the fallback key (domains without per-domain overrides get the default policy). `is_eligible_for_auto_approve` unchanged.
- `api/services/review_proposal_dispatch.py` — rename `modes = load_modes(...)` → `autonomy = load_autonomy(...)`, call site updates.
- `api/agents/reviewer_agent.py` — _SYSTEM_PROMPT gains: "The workspace's autonomy delegation is declared in /workspace/context/_shared/AUTONOMY.md. Your principles can narrow this but never widen it. When a principle and raw delegation conflict on auto-approve eligibility, apply the stricter."
- `api/services/orchestration.py` — `DEFAULT_REVIEW_MODES_MD` deleted. `DEFAULT_AUTONOMY_MD` added (generic manual-everywhere template with commented-out per-domain examples).
- `api/services/workspace_init.py` — Phase 2 workspace files set gains `SHARED_AUTONOMY_PATH` scaffold; removes `REVIEW_MODES_PATH` scaffold.
- `api/services/primitives/update_context.py` — extend `target` options to include `"autonomy"`, routing to AUTONOMY.md.
- `api/prompts/CHANGELOG.md` entry documenting the file rename + path change.

### Commit 3: scaffold + persona migration

- `api/scripts/alpha_ops/scaffold_trader.py` — `REVIEWER_MODES_MD` deleted. New `REVIEWER_AUTONOMY_MD` constant (operator-authored trading-domain override; still bounded_autonomous + $20K ceiling + never_auto: [cancel_order]). Substrate file list swaps modes.md → AUTONOMY.md.
- `scaffold_trader.py` — `PRINCIPLES_MD` content edit: remove Auto-approve policy section (moves to AUTONOMY.md), keep the six-check framework + tone + anti-override discipline + Simons-persona narrative.
- `docs/alpha/personas/alpha-trader/MANDATE.md` — Autonomy scope clause updated to reference AUTONOMY.md as the canonical delegation source ("see `/workspace/context/_shared/AUTONOMY.md` for the specific per-domain ceilings"), removes the inline modes.md reference.
- `docs/alpha/ALPHA-1-PLAYBOOK.md` §3A.4 — note the principles-vs-autonomy split; principles.md is the framework, AUTONOMY.md is the delegation.
- Observation log entry recording the migration path.

---

## Cross-references

- **ADR-194 v2** — Reviewer seat interchangeability. ADR-217 extends by confirming seat rotation never modifies autonomy delegation.
- **ADR-205** — Signup-scaffold collapse. ADR-217 adds AUTONOMY.md to the `_shared/` scaffold set; Reviewer substrate scaffold loses modes.md.
- **ADR-206** — `_shared/` relocation. ADR-217 extends the `_shared/` semantics: operator-authored workspace-scoped standing declarations. AUTONOMY is the fifth such declaration.
- **ADR-207** — Primary Action + Mandate + Capabilities. MANDATE + AUTONOMY are the two complementary operator-intent substrates: MANDATE declares *what* the operation runs; AUTONOMY declares *how autonomously*.
- **ADR-209** — Authored Substrate. AUTONOMY.md is revision-chained like any `_shared/` file; every tuning lands as a revision with `authored_by=operator`.
- **ADR-211** — Reviewer substrate Phase 4. ADR-217 deletes modes.md from that seven-file canon (now six files).
- **ADR-212** — Layer mapping. Autonomy's Purpose-axis classification fits cleanly under this taxonomy.
- **ADR-216** — YARNNN reclassification + persona wiring. ADR-217 extends Commit 2's Reviewer prompt to read AUTONOMY.md alongside IDENTITY + principles. YARNNN chat surface also reads it (for autonomous-action visibility).
- **FOUNDATIONS v6.0 Axiom 3** (Purpose). Autonomy is the canonical Purpose-axis declaration for AI judgment delegation.

---

## Implementation status

- **Commit 1** (this ADR): Proposed.
- **Commit 2** (substrate + wiring): Pending.
- **Commit 3** (scaffold migration + persona content update): Pending.
- **Follow-on (not this ADR)**: Frontend chat-inline autonomous-action messages (Phase 4 per D6) + canon doc `docs/architecture/agent-composition.md` (separate effort documenting how agent prompts + substrate compose).

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-24 | v1 — initial draft. Eight decisions (D1 workspace scope, D2 canonical location, D3 modes.md dissolution, D4 principles.md split, D5 dispatcher rewire, D6 chat-inline visibility, D7 no task-level override, D8 rotation preserves autonomy). Three-commit staging. Four alternatives considered and rejected. Dimensional test confirms Purpose/Identity/Purpose axis separation for AUTONOMY/IDENTITY/principles — non-collapsible. |
