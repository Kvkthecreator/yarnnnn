# ADR-194: Pluggable Reviewer + Operator Impersonation

> **Status**: Proposed (2026-04-19)
> **Date**: 2026-04-19
> **Authors**: KVK, Claude
> **Extends**: ADR-189 (Three-Layer Cognition), ADR-191 (Polymath Operator ICP), ADR-192 (Write Primitive Coverage Expansion), ADR-193 (ProposeAction + Approval Loop)
> **Depended on by**: ADR-195 (Outcome Attribution — AI Reviewer consumes track record), ADR-196 (Autonomous Decision Loop — signal emits proposals, reviewer decides), ADR-197 (Operator Control Room surfaces)
> **Supersedes (sequencing)**: The pre-2026-04-17 handoff plan slated ADR-194 as "Surface archetypes" and ADR-195 as "Autonomous decision loop." Both are renumbered: ADR-194 becomes Pluggable Reviewer + Impersonation (this doc), ADR-195 becomes Outcome Attribution, ADR-196 becomes the autonomous decision loop, ADR-197 becomes surface archetypes / control room. Reason: FOUNDATIONS Axiom 7 (Money-Truth) promotes capital attribution to a first-class substrate, and the reviewer abstraction is the joint where money-reasoning lives.

---

## Context

### The problem ADR-194 closes

ADR-193 shipped the approval loop but hardcoded one reviewer shape: **the human user**. `action_proposals.status = "pending"` → `/api/proposals/{id}/approve` → `ExecuteProposal` assumes a person clicks the button.

This blocks three distinct needs:

1. **Autonomy progression.** We cannot close the loop without a human at every step if the human is the only reviewer allowed. The long-term product is "supervise, don't operate" — that requires an AI reviewer for low-stakes, high-confidence actions.

2. **Alpha stress-testing.** ADR-191 commits to conglomerate alpha (≥4 structurally different domains). Onboarding real friends onto half-built infrastructure is premature. We need a way for founders (KVK + Claude) to *act as* designated operator personas — run the trader's workspace, run the e-commerce workspace — so the system gets stress-tested before real operators touch it.

3. **Mixed-policy approvals.** Different write primitives have different risk profiles. A $50 discount code is not a $50K trade. The architecture must accept per-domain, per-primitive reviewer policy: "AI auto-approves reversible commerce writes below $500; human approves all trading writes." Hardcoding human-only prevents this.

### The architectural insight

**The reviewer is an abstraction, not a role.** The approval loop's contract is "given a pending proposal, return approve / reject / modify with reasoning." Nothing in that contract requires the reviewer to be human. Treating reviewer as a pluggable layer unlocks:

- **Human reviewer** — ADR-193's current behavior, unchanged in spirit
- **AI reviewer** — senior-operator reasoning in capital-EV terms (not just risk-rule compliance)
- **Impersonation reviewer** — admin god-mode for alpha simulation

All three go through one interface. Policy (which reviewer runs which proposal) is workspace-configurable.

### Why EV-reasoning, not just rule-checking

The AI reviewer's shape matters structurally. If we design it as "read `_risk.md`, enforce rules" it becomes a redundant compliance gate that adds nothing the risk-gate primitive (ADR-192) doesn't already do. The right shape is **senior-operator reasoning**:

- Reads proposal + `/workspace/context/{domain}/_risk.md` (the floor) + `/workspace/context/{domain}/_operator_profile.md` (the operator's declared strategy) + `/workspace/context/{domain}/_performance.md` (accumulated track record — populated by ADR-195)
- Reasons in expected-value terms: *given the operator's current book, their declared strategy, and their track record on similar actions, does this proposal have asymmetric upside?*
- Returns structured decision: `approve | reject | defer` with reasoning text that explains the EV judgment

This is why ADR-194 depends on ADR-195. An AI reviewer without outcome attribution has no track record to reason against; it collapses back into rule-checking. The two ADRs ship together as a pair.

---

## Decision

### 1. Reviewer as an abstraction

New module `api/services/reviewers/` with an ABC and three concrete implementations.

```python
# api/services/reviewers/base.py

class ReviewerDecision(TypedDict):
    decision: Literal["approve", "reject", "defer"]
    reasoning: str
    modified_inputs: dict | None  # for "approve with modifications"


class Reviewer(ABC):
    reviewer_type: str  # "human" | "ai" | "impersonated"

    @abstractmethod
    async def review(
        self,
        proposal: ActionProposal,
        workspace_context: WorkspaceContext,
    ) -> ReviewerDecision | None:
        """
        Return None if this reviewer defers to another (e.g., AI defers
        to human on high-stakes). Return a ReviewerDecision otherwise.
        """
```

Implementations:
- `HumanReviewer` — wraps the existing `/api/proposals/{id}/approve` UX. Returns `None` until the user clicks (i.e., synchronous request/response at the HTTP boundary, not at the review call).
- `AIReviewer` — reads proposal + domain context files, calls Sonnet with an EV-reasoning prompt, returns a decision. Auto-approve threshold is per-domain policy.
- `ImpersonatingReviewer` — admin-only wrapper. When `workspace.impersonation_persona` is set and `request.user.can_impersonate = true`, all proposals in that workspace flow through a review prompt the admin (KVK / Claude via chat) answers *as the persona*.

### 2. Reviewer policy per domain

A new workspace file `/workspace/REVIEWER-POLICY.md` declares which reviewer handles which kind of proposal. Default template:

```yaml
# /workspace/REVIEWER-POLICY.md (scaffolded at signup)
default_reviewer: human
policies:
  - match: {action_type_prefix: "trading."}
    reviewer: human
    notes: Irreversible. Always human.
  - match: {action_type_prefix: "commerce.", reversibility: "reversible"}
    reviewer: ai
    ai_auto_approve_below_cents: 50000  # $500
    notes: AI auto-approves low-value reversible writes.
  - match: {action_type_prefix: "commerce.", reversibility: "irreversible"}
    reviewer: human
  - match: {action_type_prefix: "email."}
    reviewer: human
    notes: Customer-facing copy. Always human until we've built brand-voice alignment scoring.
```

YARNNN can edit this file via `UpdateContext(target="workspace", file="REVIEWER-POLICY.md")`. Users can edit via the workspace surface. Parser is strict YAML-in-markdown, same pattern as `_risk.md`.

### 3. Impersonation substrate

Admin-only god-mode for alpha stress-testing. Not a tenant-isolation bypass — an explicit marking that a workspace is a test persona.

**Schema changes:**
- `workspaces.impersonation_persona` — nullable text. When set (e.g., `"day-trader-alpha"`, `"ecommerce-alpha"`), marks this workspace as a persona test account. Visible in UI chrome.
- `users.can_impersonate` — boolean, default false. Admin flag. Only `can_impersonate = true` users can switch into persona workspaces.

**Endpoint:**
- `POST /api/admin/impersonate/{workspace_id}` — if `user.can_impersonate`, sets session cookie to treat `workspace_id` as current. Returns the persona's compact index as a stage-setter.
- `POST /api/admin/impersonate/clear` — drops back to admin's own workspace.

**Audit:** every session action during impersonation logs `acting_as_persona=<slug>` in `activity_log.metadata`. Proposals executed during impersonation record `reviewer_type="impersonated"`, `reviewer_identity="kvk-as-day-trader-alpha"`.

**Seeding:** on system bootstrap, create 2-4 persona workspaces matching `DOMAIN-STRESS-MATRIX.md` alpha domains. Each seeded with:
- `/workspace/IDENTITY.md` from the DOMAIN-STRESS-MATRIX Identity-shape row
- `/workspace/context/{domain}/_operator_profile.md` with declared strategy
- `/workspace/context/{domain}/_risk.md` with reasonable defaults
- `/workspace/REVIEWER-POLICY.md` with domain-appropriate defaults
- Platform connections unset (admin connects real sandbox accounts: Alpaca paper, LS sandbox)

### 4. Schema changes on `action_proposals`

Two new columns:

```sql
ALTER TABLE action_proposals
  ADD COLUMN reviewer_type text,  -- "human" | "ai" | "impersonated"
  ADD COLUMN reviewer_identity text,  -- user_id / ai-model-slug / "kvk-as-<persona>"
  ADD COLUMN reviewer_reasoning text;  -- EV analysis for AI; empty for human
```

Populated at approval time. Backfill: existing rows set `reviewer_type = "human"`, `reviewer_identity = approved_by`.

### 5. AI reviewer prompt shape (v1)

Lives at `api/services/reviewers/ai_prompts.py`. Key contract:

```
You are a senior operator reviewing a proposed action in the operator's
account. You have three documents to draw on:

1. _risk.md — hard floors the operator declared. These are non-negotiable.
2. _operator_profile.md — the operator's declared strategy, edge, style.
3. _performance.md — accumulated track record of similar actions.

Reason in expected-value terms:
- What's the upside if this action works out?
- What's the downside if it doesn't?
- Is the upside / downside ratio asymmetric?
- Given the operator's track record on similar actions, is this inside
  their edge or outside it?

Return one of:
- approve  — if EV is clearly positive AND proposal is within declared
  edge AND is below the auto-approve threshold for this domain
- reject  — if EV is clearly negative OR violates _risk.md OR is outside
  operator's declared strategy
- defer  — if EV is ambiguous, stakes are high enough to warrant human
  judgment, or this is an edge case the operator hasn't seen before

Always include reasoning. Brevity is fine; substance is required.
```

Model: Claude Sonnet. Temperature 0. Output structured via tool-use.

### 6. Changes to `ExecuteProposal`

`ExecuteProposal` already accepts an optional `approver_identity`. Extended to accept `reviewer_type` and `reviewer_reasoning`:

```python
ExecuteProposal(
    proposal_id: str,
    modified_inputs: dict | None = None,
    reviewer_type: str = "human",
    reviewer_identity: str | None = None,
    reviewer_reasoning: str = "",
)
```

Called by:
- Human approval UX (unchanged UX; backend fills `reviewer_type="human"`)
- AI reviewer worker (new — see Phase 3)
- Impersonation UX (admin clicks approve in persona workspace; backend sets `reviewer_type="impersonated"`, `reviewer_identity="<admin-user-id>-as-<persona-slug>"`)

### 7. Routing proposals through the reviewer layer

New service `api/services/reviewer_router.py`:

```python
async def route_proposal(
    proposal: ActionProposal,
    auth: AuthContext,
) -> None:
    policy = load_reviewer_policy(proposal.workspace_id)
    reviewer = resolve_reviewer(policy, proposal)  # Human / AI / Impersonating

    if isinstance(reviewer, HumanReviewer):
        # No-op at proposal creation time. Human clicks approve later
        # via existing /api/proposals/{id}/approve route.
        return

    if isinstance(reviewer, ImpersonatingReviewer):
        # Same as Human, but UI chrome shows persona banner so admin
        # knows they're acting as a persona.
        return

    if isinstance(reviewer, AIReviewer):
        # Dispatched synchronously (~3-5s) or async via back-office task
        # (see Phase 3). v1 inline; v2 may move to queue.
        decision = await reviewer.review(proposal, workspace_context)
        if decision["decision"] == "approve":
            await ExecuteProposal(
                proposal_id=proposal.id,
                modified_inputs=decision.get("modified_inputs"),
                reviewer_type="ai",
                reviewer_identity="ai-reviewer-sonnet-v1",
                reviewer_reasoning=decision["reasoning"],
            )
        elif decision["decision"] == "reject":
            await RejectProposal(
                proposal_id=proposal.id,
                reason=decision["reasoning"],
            )
        # "defer" = leave pending for human; no-op.
```

Called from `handle_propose_action` after the row lands. Failure of the reviewer layer (AI timeout, prompt error) degrades gracefully: proposal stays pending, logged as "AI reviewer unavailable — human fallback."

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Capital-Gain Alignment | Notes |
|--------|--------|----------------------|-------|
| **E-commerce** | **Helps** | **Yes, directly** | AI reviewer can auto-approve low-value reversible writes (discount codes under $500, routine product updates) without operator babysitting. Impersonation lets us stress-test LS integration without burning a real operator's trust. |
| **Day trader** | **Helps** | **Yes, directly** | AI reviewer adds capital-EV reasoning on top of `_risk.md` rules. "You're already 40% tech-concentrated, this tech trade is outside your edge" is a reviewer-layer judgment, not a risk-rule. Human still required on all trading writes by default. |
| **AI influencer** (scheduled) | **Forward-helps** | **Yes, enabling** | When content-publishing domain lights up, brand-voice reviewer becomes a natural AI reviewer implementation. |
| **International trader** (scheduled) | **Forward-helps** | **Yes, enabling** | Compliance / counterparty-risk checks map cleanly to AI reviewer pattern. |

No domain hurt. No verticalization — the abstraction is generic and policy is per-workspace. Gate passes.

---

## Implementation sequence

Four phases, each commits green. Phase 1-2 can land without ADR-195; Phase 3 requires ADR-195 Phase 1 (for track-record reads) or degrades to rule-only reasoning.

| # | Phase | Scope |
|---|-------|-------|
| 1 | Reviewer abstraction + HumanReviewer refactor | `Reviewer` ABC, `HumanReviewer`, `reviewer_type` + `reviewer_identity` columns + backfill, `reviewer_router.route_proposal()` wired into `handle_propose_action`. No behavior change for existing flows. |
| 2 | Impersonation substrate | `workspaces.impersonation_persona`, `users.can_impersonate`, admin impersonation endpoints, 2 seeded persona workspaces (day-trader-alpha, ecommerce-alpha), UI chrome banner when impersonating. |
| 3 | AIReviewer (rule-only v0) | `AIReviewer` class, prompt v0 (reads `_risk.md` + `_operator_profile.md` only; no track record yet), REVIEWER-POLICY.md parser + scaffold, ai-reviewer worker invoked by `reviewer_router`. Default policy: AI disabled until user opts in per domain. |
| 4 | AIReviewer v1 (EV-reasoning) | Prompt v1 reads `_performance.md` (depends on ADR-195 Phase 4). EV-reasoning promoted from rule-check to senior-operator reasoning. Auto-approve threshold enforcement. |

---

## Open questions (deferred to implementation)

1. **AI reviewer inline vs async.** Phase 3 runs synchronously in `handle_propose_action`. If latency becomes a problem (3-5s per proposal), move to a back-office task that sweeps pending proposals. Deferred until observed.
2. **Reviewer policy conflict resolution.** If two rules in REVIEWER-POLICY.md match a proposal, which wins? v1 uses first-match-wins, documented.
3. **Impersonation audit trail depth.** Current plan: log `acting_as_persona` in activity_log. Sufficient for v1. Forensic replay deferred.
4. **Per-agent reviewer policy.** v1 is per-domain via workspace file. If per-agent policy becomes necessary, extend REVIEWER-POLICY.md with agent-slug match. Deferred until demand.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-19 | v1 — Initial draft. Reviewer abstraction (Human / AI / Impersonation), REVIEWER-POLICY.md, impersonation substrate with persona workspaces, AI reviewer shaped around EV-reasoning (depends on ADR-195 for track-record). Renumbers original ADR-194 (surface archetypes) → ADR-197 and original ADR-195 (autonomous decision loop) → ADR-196. |
