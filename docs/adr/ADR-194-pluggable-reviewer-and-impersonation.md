# ADR-194: Reviewer Layer + Operator Impersonation

> **Status**: Phase 1 + Phase 2a Implemented 2026-04-19 (substrate scaffold + audit-trail wiring shipped). Phases 2b–4 Proposed.
> **Date**: 2026-04-17 (v1) / 2026-04-19 (v2 rewrite)
> **Authors**: KVK, Claude
> **Extends**: ADR-189 (Three-Layer Cognition), ADR-191 (Polymath Operator ICP), ADR-192 (Write Primitive Coverage Expansion), ADR-193 (ProposeAction + Approval Loop)
> **Depended on by**: ADR-195 v2 (Money-Truth Substrate — Reviewer consumes `_performance.md`), ADR-196 (Autonomous Decision Loop — signal emits proposals, Reviewer decides), ADR-197 (surface archetypes — approval surface)
> **Supersedes**: ADR-194 v1 (2026-04-17) — retracted. v1 framed Reviewer as an abstraction with a `Reviewer` ABC and `REVIEWER-POLICY.md` policy file. Both violate FOUNDATIONS Axiom 1 (Substrate — filesystem is the persistence layer) and the "singular implementation" discipline. v2 reframes Reviewer as a structurally separate fourth cognitive layer per FOUNDATIONS v6.0 Axiom 2 (Identity — four cognitive layers), with the layer's *distinctness* located in Purpose + Trigger (Axioms 3 + 4) rather than Identity — which is why the seat is interchangeable between human and AI without architectural change.

---

## Context

### Why v1 is retracted

ADR-194 v1 (2026-04-17) framed the Reviewer as a pluggable abstraction — a `Reviewer` ABC with three implementations (Human / AI / Impersonation), gated by a `REVIEWER-POLICY.md` config file declaring which implementation handles which proposal type. That design was reasonable under the ADR-189 three-layer cognition model, but it conflicts with two later architectural commitments:

1. **FOUNDATIONS Axiom 1 (v6.0): Substrate — filesystem is the persistence layer.** A `Reviewer` ABC is an in-memory abstraction that holds no filesystem state; a `REVIEWER-POLICY.md` file that only the ABC's dispatcher reads is a policy container parallel to `task_types.py` task definitions. Both are violations — policy for which agent reviews which proposal type belongs in task context files, not in a parallel config container.

2. **FOUNDATIONS Axiom 2 (v6.0): Identity — four cognitive layers.** Reviewer is its own cognitive layer, not a plug-in slot over the other three. The three "implementations" of v1 are actually three identities that can fill the same structural seat — the seat itself is the layer. Crucially (v6.0 clarification): the Reviewer layer's *distinctness* is not in its Identity but in its **Purpose + Trigger cell** — independent judgment (Purpose) over proposed-write events (reactive Trigger). This is why swapping human ↔ AI in the seat requires no architectural change: Identity is the swappable axis; the distinguishing dimensions (Substrate, Purpose, Trigger, Mechanism, Channel) are all preserved.

v2 replaces v1 entirely. No dual versions; v1 file is overwritten. The pre-v2 draft lives only in git history (commits before `HEAD~N`).

### The problem ADR-194 closes (unchanged from v1)

ADR-193 shipped the approval loop but hardcoded the reviewer to the human user. `action_proposals.status = "pending"` → `/api/proposals/{id}/approve` → `ExecuteProposal` assumes a person clicks the button.

This blocks three distinct needs:

1. **Autonomy progression.** We cannot close the loop on every step if the human is the only reviewer permitted. The long-term product is "supervise, don't operate" — that requires structural room for AI to fill the approval seat on low-stakes reversible writes once track records have accumulated.

2. **Alpha stress-testing.** ADR-191 commits to conglomerate alpha across ≥4 structurally different domains. Onboarding real friends onto half-built infrastructure is premature. We need a way for founders (KVK + Claude) to act as designated operator personas — run the trader's workspace, run the e-commerce workspace — so the system gets stress-tested before real operators onboard.

3. **Objectivity.** The stated intuition from the architectural discourse: a good approval layer has the property of an independent audit team. A reviewer that is just another YARNNN-managed agent in the same workspace shares YARNNN's priors. An agent reviewing its own output or YARNNN reviewing its own proposal is not audit — it's self-assessment. The audit property requires structural independence.

### The key insight

**Reviewer is a structurally separate cognitive layer.** Not an abstraction the other layers plug into — a layer of its own. Its defining property is *the independent judgment seat*: a structural slot that holds approval authority and is interchangeable between a human user and an AI system without any architectural change. The seat is the layer; the filler is the identity.

This framing is the joint at which money-reasoning lives. Under ADR-195 v2, money-truth accumulates at `/workspace/context/{domain}/_performance.md`. The Reviewer is the consumer with the right scope — workspace-wide, across-domain — to reason about proposed writes in capital-EV terms against accumulated track records. Specialists have role-scope, Agents have domain-scope, YARNNN has orchestration-scope. None of those three natively hold *"the operator's capital position across all domains + accumulated approval judgment"* as a view. The Reviewer layer exists to hold it.

---

## Decision

### 1. Reviewer is the fourth cognitive layer

FOUNDATIONS Axiom 2 names four cognitive layers (previously three, prior to ADR-194):

- **YARNNN** (meta-cognitive, workspace scope) — composes the future.
- **Specialist** (role-cognitive, role scope) — styles the craft.
- **Agent** (domain-cognitive, domain scope) — executes the work.
- **Reviewer** (review-cognitive, workspace scope, across all proposals) — occupies the independent judgment seat.

One Reviewer per workspace. Scaffolded at signup alongside YARNNN. Its **sole purpose** is to review proposed writes created by ADR-193's `ProposeAction`. It does not compose, does not own tasks (it executes the `review-proposal` reactive task when a proposal is created), does not create Agents, does not supervise the workforce. The narrow scope is the load-bearing property.

### 2. Reviewer filesystem home — `/workspace/review/`

Per Axiom 1 (Substrate), the Reviewer's state lives in files.

```
/workspace/review/
  IDENTITY.md       # Who this Reviewer is. Opens with its one-line identity
                    # ("I am the independent judgment seat — yours or the
                    # system's"), declares scope (gates proposed writes for
                    # this workspace), declares reasoning posture (EV over
                    # rules). Edited rarely; mostly static.

  principles.md     # Declared review framework. User-editable. Captures
                    # the operator's preferences for review — how strict
                    # to be on irreversible writes, what to prioritize in
                    # ambiguous cases, which capital horizons matter.
                    # Seeded with a sensible default at signup; user can
                    # edit via Context surface or conversation with YARNNN.

  decisions.md      # Rolling append-only log of every review decision the
                    # Reviewer has made. Format: timestamped entry per
                    # decision with proposal_id, action_type, decision
                    # (approve/reject/defer), reasoning, and whether
                    # human or AI filled the seat. This IS the audit
                    # trail — no sibling table.
```

**Write discipline**: `IDENTITY.md` is static after scaffolding. `principles.md` is user-edited. `decisions.md` is append-only, written by whichever identity filled the seat for a given review. Nothing else writes to `/workspace/review/`.

### 3. Three identities, one seat

The Reviewer seat can be filled by one of three identities. Identity is chosen per-proposal at `ProposeAction` creation time based on task context and the proposal's reversibility.

**Human Reviewer (default for irreversible writes)**
- The user clicks approve / modify / reject on the proposal card in chat.
- The approval UX is unchanged from ADR-193 — this is simply the human filling the seat.
- `decisions.md` entry records `reviewer_identity: human:<user_id>`.

**AI Reviewer (default for reversible low-stakes writes, once track records accumulate)**
- A `thinking_partner`-class agent scoped to `/workspace/review/` — *not* a new agent role, a scoping of the existing meta-cognitive role to the review concern.
- Invoked as a reactive task (`review-proposal`) when a proposal is created.
- Reads: the proposal, the task's context files (`_risk.md`, `_operator_profile.md`, `_performance.md` for the domain), `principles.md`, recent `decisions.md` entries.
- Reasons in capital-EV terms (see §5).
- Calls `ExecuteProposal` (approve), `RejectProposal` (reject), or writes a defer note to `decisions.md` and leaves the proposal pending for human.
- `decisions.md` entry records `reviewer_identity: ai:thinking-partner-v<N>`.

**Impersonation Reviewer (admin-only, alpha stress-testing)**
- When an admin (KVK/Claude) is acting as a persona workspace (gated by `users.can_impersonate` + `workspaces.impersonation_persona`), all approval UX in that workspace is attributed to the admin *as* the persona.
- The human operator and the admin-as-persona fill the seat identically — same UX, same `decisions.md` write, different `reviewer_identity` tag.
- `decisions.md` entry records `reviewer_identity: impersonated:<admin_user_id>-as-<persona_slug>`.

**All three identities operate through the same flow.** Proposal created → `review-proposal` reactive task fires → task pipeline dispatches to the reviewer identity declared in task context → reviewer reads files, reasons, writes `decisions.md`, calls `ExecuteProposal` / `RejectProposal` / defers. The difference is who fills the seat, not how the seat is implemented.

### 4. No `Reviewer` ABC. No `REVIEWER-POLICY.md`.

Retracted from v1. Under Axiom 1 (Substrate), policy for *which identity reviews which proposal type* is declared in the task type definition for `review-proposal`, not in a parallel config file. The task type declares:

- Which agent identity runs the task (Human via approval UX, AI via the `thinking_partner`-scoped reviewer agent)
- What context the task reads (proposal + `_risk.md` + `_operator_profile.md` + `_performance.md` + `principles.md`)
- What decision categories are allowed (approve / reject / defer)

Task type definitions already live in `api/services/task_types.py` (a registry per ADR-188's "registries as template libraries" principle). Adding `review-proposal` as a task type uses existing machinery; it does not invent a new policy container.

Per-proposal routing decisions (which identity handles *this* proposal) are data on the proposal itself. `action_proposals` gains lean metadata (reversibility tag — already present; target-reviewer hint — new) that task dispatch reads. No parallel policy file.

### 5. AI Reviewer prompt shape (v1) — Capital-EV reasoning

The AI Reviewer is shaped around expected-value reasoning, not rule-checking. Risk rules (`_risk.md`) are the floor; capital-EV is the target.

Prompt contract (lives in `api/agents/tp_prompts/reviewer.py` when Phase 3 lands):

```
You are the independent judgment seat for this operator's workspace.
You are reviewing a proposed action. You have four documents:

1. _risk.md              — the operator's declared hard floors. Non-negotiable.
2. _operator_profile.md  — the operator's declared strategy, edge, style.
3. _performance.md       — accumulated track record of similar actions.
4. principles.md         — the operator's declared review framework.

Reason in expected-value terms:
- What's the upside if this action works out?
- What's the downside if it doesn't?
- Is the upside/downside ratio asymmetric?
- Given the operator's track record on similar actions, is this
  inside their edge or outside it?

Return one of:
- approve — EV is clearly positive AND within declared edge AND below
  the auto-approve threshold for this domain
- reject  — EV is clearly negative OR violates _risk.md OR is outside
  operator's declared strategy
- defer   — EV is ambiguous, stakes are high enough to warrant human
  judgment, or this is an edge case the operator hasn't seen before

Always write reasoning to decisions.md. Brevity is fine; substance is required.
```

Model: Claude Sonnet. Temperature 0. Output structured via tool-use. Phase 3.

An AI Reviewer without outcome history collapses into rule-checking. This is why ADR-194 and ADR-195 ship as a pair: without `_performance.md` populated, the AI identity has no track record to reason against.

### 6. Impersonation substrate

Admin-only god-mode for alpha stress-testing. Not a tenant-isolation bypass — an explicit marking that a workspace is a test persona.

**Schema changes:**

```sql
ALTER TABLE workspaces
  ADD COLUMN impersonation_persona text NULL;
    -- When set (e.g., "day-trader-alpha"), marks the workspace as a test
    -- persona. Visible in UI chrome banner. Nullable — normal workspaces
    -- are NULL.

ALTER TABLE users
  ADD COLUMN can_impersonate boolean NOT NULL DEFAULT false;
    -- Admin flag. Only can_impersonate = true users can switch into
    -- persona workspaces.
```

**Endpoints:**
- `POST /api/admin/impersonate/{workspace_id}` — gated on `user.can_impersonate`. Sets session cookie to treat `workspace_id` as current. Returns the persona's compact index to orient the admin.
- `POST /api/admin/impersonate/clear` — drops back to admin's own workspace.

**Audit:** every action during impersonation logs `acting_as_persona=<slug>` in `activity_log.metadata`. Proposals executed during impersonation write `reviewer_identity: impersonated:<admin_user_id>-as-<persona_slug>` to `decisions.md`.

**Seeding:** 2–4 persona workspaces matching `DOMAIN-STRESS-MATRIX.md` alpha domains. Each seeded with:
- `/workspace/IDENTITY.md` from DOMAIN-STRESS-MATRIX Identity-shape row
- `/workspace/context/{domain}/_operator_profile.md` with declared strategy
- `/workspace/context/{domain}/_risk.md` with reasonable defaults
- `/workspace/review/{IDENTITY,principles}.md` scaffolded
- Platform connections unset (admin connects real sandbox: Alpaca paper, LS sandbox)

Impersonation is **Phase 2** of this ADR — not in the initial substrate scaffold commit.

### 7. `action_proposals` schema additions (Phase 2+)

Two optional columns to support reviewer-identity tagging. Neither is required for Phase 1.

```sql
ALTER TABLE action_proposals
  ADD COLUMN reviewer_identity text,
      -- Set at review time. Format:
      --   "human:<user_id>"  |  "ai:thinking-partner-v<N>"  |
      --   "impersonated:<admin_user_id>-as-<persona_slug>"
  ADD COLUMN reviewer_reasoning text;
      -- Brief summary of the reasoning (for quick proposal-card display).
      -- Full reasoning always written to /workspace/review/decisions.md.
```

`action_proposals` remains an ephemeral-queue row (per Axiom 1, permitted row kind 4). Reviewer-identity tagging is metadata on the queue entry, not accumulation substrate. The accumulation substrate for review judgment is `decisions.md`.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Capital-Gain Alignment | Notes |
|--------|--------|------------------------|-------|
| **E-commerce** | **Helps** | Yes, directly | AI Reviewer can fill the seat for low-value reversible writes (discount codes under $500, routine product updates) without operator babysitting, once `_performance.md` accumulates a track record. Impersonation lets us stress-test LS integration without burning a real operator's trust. |
| **Day trader** | **Helps** | Yes, directly | AI Reviewer adds capital-EV reasoning on top of `_risk.md` rules. "You're already 40% tech-concentrated, this tech trade is outside your edge" is a reviewer-layer judgment, not a risk-rule. Human still fills the seat for all trading writes by default. |
| **AI influencer** (scheduled) | Forward-helps | Yes, enabling | When content-publishing domain lights up, brand-voice checks become a natural AI Reviewer case. Same substrate, same flow. |
| **International trader** (scheduled) | Forward-helps | Yes, enabling | Compliance / counterparty-risk checks map cleanly to the same Reviewer pattern. |

No domain hurt. No verticalization — Reviewer is a workspace-scope structural layer, not a domain feature. Gate passes.

---

## Implementation sequence

Four phases. Phase 1 ships in the current commit cycle (alongside this ADR). Phases 2–4 are subsequent cycles.

| # | Phase | Scope | Status |
|---|-------|-------|--------|
| 1 | Reviewer substrate scaffold | `/workspace/review/IDENTITY.md` + `principles.md` templates seeded at signup via `workspace_init.py` Phase 5. `decisions.md` not scaffolded — created on first write. No review-proposal task. No AI reviewer agent invocation. This is the filesystem substrate only. | **Implemented 2026-04-19** |
| 2a | Audit-trail wiring | `reviewer_identity` + `reviewer_reasoning` columns added to `action_proposals` (migration 152). `services/reviewer_audit.py` provides `append_decision` — appends a delimited decision block to `/workspace/review/decisions.md` per approval or rejection. `ExecuteProposal` + `RejectProposal` primitives accept `reviewer_identity` + `reviewer_reasoning`; default to `human:<user_id>` for frontend flows. `/api/proposals/{id}/approve` + `/reject` routes populate identity automatically. No new task type yet. | **Implemented 2026-04-19** |
| 2b | `review-proposal` reactive task type + impersonation | Task type in `task_types.py` firing on proposal creation (enables AI Reviewer invocation path). Impersonation substrate (workspace column + user flag + admin endpoints). Persona-workspace seeding. | Proposed |
| 3 | AI Reviewer agent (capital-EV prompt) | `thinking_partner`-class agent scoped to `/workspace/review/` via task dispatch. Prompt v1 per §5. Reads `_performance.md` (requires ADR-195 Phase 2, already shipped). Auto-approve thresholds read from `principles.md`. | Proposed |
| 4 | Calibration + escalation tuning | Judgment-calibration metric (approve/reject accuracy vs. downstream outcome attribution). Feedback actuation on drifted calibration. Escalation rules for edge cases. | Proposed |

---

## Migration notes (v1 → v2)

No code shipped from v1 (v1 was Proposed only, never Implemented). Migration is doc-only:

- v1 ADR file overwritten by v2 (this file).
- GLOSSARY.md v1.2 rewrites the Reviewer, `/workspace/review/`, Outcome, `_performance.md`, Money-Truth, Capital-EV entries (done in the same commit cycle as this ADR).
- FOUNDATIONS.md v6.0 (superseding the v5.1 rewrite) names the six-dimensional model: Axiom 1 (Substrate), Axiom 2 (Identity — four layers, including Reviewer), Axiom 3 (Purpose), Axiom 4 (Trigger), Axiom 5 (Mechanism), Axiom 6 (Channel), Axiom 7 (Recursion), Axiom 8 (Money-Truth). ADR-194 v2 is dimensionally classified as Identity + Purpose + Trigger.
- No SQL migration needed for v2 (Phase 1 is filesystem-only).

---

## Open questions (deferred to implementation)

1. **Where does `reviewer_identity` get chosen?** v2 Phase 2 answer: by the `review-proposal` task type definition reading proposal reversibility + domain. Explicit mapping TBD during Phase 2.
2. **`decisions.md` rotation.** If `decisions.md` grows unbounded, we rotate to `decisions-{year}.md`. Threshold TBD — defer until we see real growth.
3. **User override of AI reviewer decisions.** If the AI approves a proposal and the user disagrees, the write has already executed. Does the user's post-hoc objection write a feedback entry? Yes — per ADR-181, user correction on an executed action is a feedback entry. Deferred to Phase 3.
4. **Reviewer self-assessment.** The Reviewer's judgment calibration is measured against reconciled outcomes. The mechanism for writing that self-assessment (probably `/workspace/review/calibration.md`) is Phase 4.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-17 | v1 — Initial draft. Reviewer abstraction (Human / AI / Impersonation), REVIEWER-POLICY.md, impersonation substrate with persona workspaces, AI reviewer shaped around EV-reasoning (depends on ADR-195 for track-record). Renumbered original ADR-194 (surface archetypes) → ADR-197 and original ADR-195 (autonomous decision loop) → ADR-196. |
| 2026-04-19 | v2 — **Full rewrite.** Reviewer reframed from pluggable abstraction to structurally separate fourth cognitive layer. Under FOUNDATIONS v5.1 (which pre-dated the v6.0 renumber), the citations were Axiom 0 (filesystem) + Axiom 1 (four layers). `Reviewer` ABC dropped. `REVIEWER-POLICY.md` dropped — routing lives in `review-proposal` task type per ADR-188. Reviewer filesystem home established at `/workspace/review/` (IDENTITY.md + principles.md + decisions.md). Three identities (Human / AI / Impersonation) reframed as identities filling the same seat, not pluggable implementations. Phased sequence sharpened: Phase 1 = substrate scaffold only (shipped this cycle); Phase 2+ = reactive task, impersonation endpoints, AI reviewer agent. v1 file overwritten — singular-implementation discipline. |
| 2026-04-19 | v2.1 — **Phase 1 Implemented.** `DEFAULT_REVIEW_IDENTITY_MD` + `DEFAULT_REVIEW_PRINCIPLES_MD` templates added to `api/services/agent_framework.py` (alongside existing `DEFAULT_IDENTITY_MD` / `DEFAULT_BRAND_MD` / etc). `workspace_init.py` Phase 3 loop extended to scaffold `/workspace/review/IDENTITY.md` + `/workspace/review/principles.md` at signup — same substrate, same upsert pattern, same idempotency (only written if absent). `decisions.md` NOT scaffolded — created on first review write (Phase 2+). IDENTITY template asserts the independence property ("I sit outside YARNNN's cognition so review is not self-assessment"); principles template gives operator-editable auto-approve thresholds + default posture ("skeptical over permissive") + escalation signal for thin-track-record domains. Templates are ~4KB total — lightweight. No runtime behavior change yet — the Reviewer does not run until Phase 2 (reactive `review-proposal` task). Existing test workspaces are NOT auto-backfilled; next signup onward gets the Reviewer substrate. |
| 2026-04-19 | v2.2 — **Phase 2a Implemented.** Phase 2 split into 2a (audit-trail wiring — shippable standalone) and 2b (review-proposal task + impersonation — bigger scope, deferred). 2a ships: migration 152 adds `reviewer_identity` + `reviewer_reasoning` columns to `action_proposals`. New module `api/services/reviewer_audit.py` — single public function `append_decision` that reads `/workspace/review/decisions.md`, appends a delimited `--- decision ---` block with machine-readable fields + markdown reasoning, and upserts via the workspace_files pattern (same path as `risk_gate.py`). First write seeds a header; subsequent writes append. `ExecuteProposal` + `RejectProposal` primitives accept `reviewer_identity` + `reviewer_reasoning` (default `human:<user_id>`), persist to the row at approve/reject time, and call `append_decision` after status commit. Audit writes never block flow — failures log. `/api/proposals/{id}/approve` + `/reject` routes pass the auth'd user's identity automatically. Now every completed approval or rejection — whether from frontend, chat LLM, or primitive caller — leaves an audit trail in the Reviewer's filesystem home. |
| 2026-04-20 | v2.3 — **Alignment pass for FOUNDATIONS v6.0.** No behavior change. Axiom citations re-numbered under the dimensional model: "Axiom 0 (filesystem is substrate)" → "Axiom 1 (Substrate)"; "Axiom 1 (four layers)" → "Axiom 2 (Identity)". Context §1 now names the v6.0 clarification that the Reviewer layer's *distinctness* lives in Purpose + Trigger (Axioms 3 + 4), which is why the seat is interchangeable between human and AI without architectural change — only Identity varies; all other dimensions are preserved. Migration-notes section updated to reflect v6.0's eight-axiom map and ADR-194's primary dimensions (Identity + Purpose + Trigger). Audit of mid-cycle references to "v5.1" now noted as the pre-renumber framing. |
