# ADR-211: Reviewer Substrate — Phase 4 Completion

> **Status**: Implemented 2026-04-23 (five atomic commits 49bfeb3 / 5fb0b69 / bcdeaae / af9cf44 / b0a93e4). Vocabulary updated same-day per [ADR-212](ADR-212-layer-mapping-correction.md): the Reviewer is a systemic **Agent** (not "layer"); earlier text referring to "Reviewer layer" is superseded by LAYER-MAPPING.md but preserved verbatim as historical artifact.
> **Date**: 2026-04-23
> **Authors**: KVK, Claude
> **Extends**: ADR-194 v2 (Reviewer Layer — implementation record through Phase 3)
> **Ratifies**: Canonical target specified in [reviewer-substrate.md](../architecture/reviewer-substrate.md) v1 (2026-04-23)
> **Upstream canon**: [THESIS.md](../architecture/THESIS.md) commitment 2 (Independent judgment), FOUNDATIONS Derived Principle 14 (Roles persist; occupants rotate)

---

## Context

ADR-194 v2 specified the Reviewer layer across four phases and shipped Phases 1 + 2a + 2b + 3 between 2026-04-19 and 2026-04-20. That implementation landed three of the seven files that `docs/architecture/reviewer-substrate.md` now specifies as the canonical target for the Reviewer seat's filesystem substrate. The remaining four files — OCCUPANT.md, modes.md, handoffs.md, calibration.md — plus the prospective-attribution contract with chat surfaces and the occupant rotation protocol, are roadmap items under ADR-194 v2 Phase 4.

This ADR scopes Phase 4 as a **bounded coordinated landing**: all four files + rotation infrastructure + attribution contract + the principles-vs-modes split + the calibration loop, shipped together rather than piecemeal. This ADR is the decision record for that bounded scope; it does not land code. Code implementation follows in a dedicated sprint when the founder is ready to spend the cycle.

### Why one coordinated landing

The four files are architecturally interdependent:

- **OCCUPANT.md** declares the current seat occupant. Without it, Principle 14 (Roles persist; occupants rotate) is asserted but not enforceable — occupant is inferred retrospectively from `decisions.md` `reviewer_identity` fields, not declared prospectively.
- **modes.md** declares the operational modes (autonomy level × scope × on-behalf posture) the seat operates under. Without it, operational config is smuggled into `principles.md` (today: `auto_approve_below_cents` lives there but is operationally-mode-shaped, not principle-shaped).
- **handoffs.md** logs occupant rotations. Without it, the seat's occupancy history is not auditable end-to-end — you can reconstruct "who filled the seat at time X" only by reading `decisions.md` for that time range.
- **calibration.md** is the money-truth → future-judgment loop at the reviewer-seat level. Without it, the seat cannot calibrate against outcomes over time; judgment quality is asserted, not measured.

Shipping any one of these in isolation produces a partial system: OCCUPANT.md without rotation protocol is declarative ceremony; modes.md without dispatch reading from it is unused config; handoffs.md without rotation events is an empty file; calibration.md without decisions-to-outcomes cross-reference is a stub. The four must land together for the substrate to be functional.

### Why this is a proposal-form ADR

Several design decisions in this scope deserve deliberate attention rather than auto-mode execution:

1. **The principles-vs-modes split** — where does `auto_approve_below_cents` live? Today it's in `principles.md`. Is it an operator principle (declared tolerance) or an operational mode (tunable threshold)?
2. **Rotation protocol** — what triggers a rotation? Operator-initiated only, or does the system auto-rotate under conditions (AI confidence drop, human unavailability)?
3. **Chat surfacing** — the prospective-attribution contract invariants (I1–I4 in reviewer-substrate.md) specify UI behavior. What's the minimum UX footprint that satisfies them without overbuilding?
4. **Calibration cadence** — `calibration.md` is rebuilt from decisions × outcomes. Daily? Weekly? On every outcome reconciliation?

This ADR resolves each decision below. Implementation then follows the ADR, not the other way around.

---

## Decision

### D1 — OCCUPANT.md: canonical current-occupant declaration

**Path**: `/workspace/review/OCCUPANT.md`

**Content shape** (YAML frontmatter + optional narrative body):

```markdown
---
occupant: human:<user_id>
occupant_class: human
activated_at: <ISO-8601>
activated_by: system  # or human:<user_id> on rotation
config:
  # For AI occupants: confidence threshold, etc.
  # For human occupants: availability hints (future).
  # Empty at signup.
---

# Review Seat — Current Occupant

<!-- Narrative description of who currently fills the seat and any
     operator notes about the current configuration. Edited rarely. -->
```

**Scaffolded at signup** in `workspace_init.py`: file is created with `occupant: human:<user_id>`, `activated_at: <signup_time>`, `activated_by: system`, empty config. Narrative body is a short default pointing the operator at `reviewer-substrate.md` for the seat's architecture.

**Occupant-class enum**: `human`, `ai`, `external`, `impersonated`. Each class has a specific identity-string format per reviewer-substrate.md §"OCCUPANT.md":
- `human:<user_id>`
- `ai:<model>-<version>` (e.g., `ai:reviewer-sonnet-v1`)
- `external:<service>-<identifier>`
- `impersonated:<admin_user_id>-as-<persona_slug>`

**Write discipline**: the file is written by `workspace_init.py` at signup, and by the rotation protocol (D3) on every rotation. Never written by the reviewer occupant itself during verdict rendering — occupants do not declare themselves into the seat; they are declared into the seat by rotation.

### D2 — modes.md: operational modes declaration

**Path**: `/workspace/review/modes.md`

**The split from principles.md**: operational thresholds move; declarative framework stays.

**Moves to modes.md**:
- `auto_approve_below_cents` per domain — this is operational configuration, not principle
- `never_auto_approve` per domain — same (operational gate, not declared belief)
- autonomy level per domain
- scope per domain (which domains the current occupant has authority over)
- on-behalf posture per domain

**Stays in principles.md**:
- Narrative declaration of review posture (*"skeptical over permissive"*, *"asymmetric losses deserve more scrutiny"*)
- Decision category definitions (what approve/reject/defer *mean* in this workspace's terms)
- The operator's declared framework for how they want to be judged on behalf of

**`high_impact_threshold_cents` per domain** — arguably either. **Decision**: stays in `principles.md` because it declares a *principle* about what's high-impact enough to route to task-level feedback per ADR-195 Phase 5; it is not an operational mode of the seat itself.

**Content shape** (YAML frontmatter per-domain + optional narrative body):

```markdown
---
# Per-domain operational modes. Domain key matches context domain slug.
trading:
  autonomy_level: bounded_autonomous
  scope: [trading]
  on_behalf_posture: recommend
  auto_approve_below_cents: 0
  never_auto_approve: [submit_order, submit_bracket_order, submit_trailing_stop]

commerce:
  autonomy_level: assisted
  scope: [commerce]
  on_behalf_posture: shortlist
  auto_approve_below_cents: 50000
  never_auto_approve: [issue_refund]
---

# Review Seat — Operational Modes

<!-- Declared operational configuration for the seat. Edited by the
     operator to tune autonomy per domain. See reviewer-substrate.md
     §"Operational modes vocabulary" for semantics. -->
```

**Scaffolded at signup** with commented-out defaults. The operator uncomments and tunes.

**Write discipline**: operator-edited via Context surface or chat with YARNNN. Never written by occupants.

**Autonomy level enum** (per reviewer-substrate.md): `manual`, `assisted`, `bounded_autonomous`, `autonomous`. These are positions on a continuum, per domain.

**On-behalf posture enum**: `silent_defer`, `recommend`, `shortlist`.

### D3 — handoffs.md: rotation history

**Path**: `/workspace/review/handoffs.md`

**Content shape** (append-only markdown log):

```markdown
# Review Seat — Occupant Rotation Log

## 2026-04-23T14:30:00Z — system scaffold

- **From**: (none)
- **To**: `human:<user_id>`
- **Trigger**: signup
- **Authorized by**: system
- **Decisions.md range**: starts here

## 2026-05-15T10:00:00Z — operator enables AI occupant for commerce

- **From**: `human:<user_id>`
- **To**: `ai:reviewer-sonnet-v1` (scope: commerce only)
- **Trigger**: operator via chat
- **Authorized by**: `human:<user_id>`
- **Reason**: "Trying AI review on small commerce proposals to build calibration"
- **Decisions.md range**: from 2026-05-15T10:00:00Z onward for commerce proposals
```

**Write discipline**: appended by the rotation protocol (D4) every time OCCUPANT.md changes. No other writer.

**Write path**: goes through Authored Substrate (`authored_by: system` or `authored_by: human:<user_id>` depending on who authorized the rotation).

### D4 — Occupant rotation protocol

**The rotation operation**: change the current occupant of the Reviewer seat. A rotation is a three-step atomic operation:

1. Read current OCCUPANT.md (source of truth for who was filling the seat).
2. Write new OCCUPANT.md with the new occupant identity, activated_at timestamp, and any occupant-class-specific config.
3. Append a handoffs.md entry recording from/to/trigger/authorized-by/reason.

**Triggers**:

- **Operator-initiated** (chat command): `/review rotate-to <occupant-identity>`. YARNNN receives the command, validates the target occupant class is supported, and performs the rotation as `authored_by: human:<user_id>`. **Primary trigger.**
- **System-scaffold** (signup only): workspace_init.py scaffolds `human:<user_id>` as initial occupant with `authored_by: system`.
- **System-fallback** (optional, deferred): if an AI occupant fails N consecutive verdicts, system auto-rotates back to human and emits a chat notification. **Deferred to a later phase** — initial implementation supports operator-initiated rotation only. Auto-rotation requires calibration-gated decisions and is premature before the calibration loop (D6) has data.

**Authorization model**:

- Operator may rotate freely between occupant classes they have access to.
- `impersonated:*` occupants require `users.can_impersonate` (already in schema per migration 153).
- `external:*` occupants require admin-provisioned adapter configuration (out of scope for Phase 4 initial landing; supported at the substrate level but no external adapters exist today).

**No rotation ABC or abstract protocol class** — the rotation is a substrate write through Authored Substrate. Per Principle 14, rotation is a file write, not a dependency injection.

### D5 — Dispatch reads OCCUPANT.md + modes.md at verdict time

**Current behavior** (Phase 3): dispatch reads `principles.md`, checks `is_eligible_for_auto_approve` using operational thresholds embedded in principles, and routes to AI occupant function if eligible.

**Phase 4 behavior**: dispatch reads:
1. `OCCUPANT.md` — who currently occupies the seat
2. `modes.md` — what operational mode applies to this proposal's domain
3. `principles.md` — declarative framework (as reasoning input for the occupant)

Dispatch routing based on occupant class:
- `human:*` — write observe-only entry to decisions.md; leave proposal pending for human UX
- `ai:*` — invoke corresponding AI occupant function (today: `reviewer_agent.review_proposal`); pass principles + modes + performance + risk + operator_profile as context
- `external:*` — invoke the adapter (Phase 4 does not ship adapters; structural path only)
- `impersonated:*` — treat as `human:*` with admin-persona audit tag (existing Phase 2b behavior)

`review_principles.py` renames to `review_policy.py` or similar? **Decision: rename to `review_policy.py`** and split into two parsers:
- `load_principles()` — narrative framework from principles.md (reasoning input)
- `load_modes()` — operational config from modes.md (dispatch gating)
- Backward compat: `is_eligible_for_auto_approve` function preserved but now reads modes.md, not principles.md

### D6 — calibration.md: the money-truth → future-judgment loop

**Path**: `/workspace/review/calibration.md`

**Generator**: a new back-office task `back-office-reviewer-calibration` runs after each outcome reconciliation cycle (ADR-195 Phase 3 produces `_performance.md` updates; this task reads those updates and cross-references with `decisions.md`).

**Content**: rolling-window summaries per occupant, per verdict category (approve/reject/defer), against reconciled outcomes. Shape:

```markdown
---
last_calibrated_at: <ISO-8601>
windows:
  rolling_7d:
    by_occupant:
      "human:<user_id>":
        total_verdicts: N
        approvals_realized_positive: N
        approvals_realized_negative: N
        rejections_later_proven_correct: N  # if operator manually approved after AI rejected, and outcome was bad
        defer_rate: X.XX
      "ai:reviewer-sonnet-v1":
        # same shape
    ...
  rolling_30d: ...
  rolling_90d: ...
---

# Review Seat — Calibration

<!-- Auto-generated. Do not edit. Read by AI occupants as prior context
     for future verdicts; read by operator when evaluating whether to
     rotate, tighten, or loosen modes. -->

## Last 7 days

[rendered narrative]

## Last 30 days

[rendered narrative]

## Last 90 days

[rendered narrative]
```

**Cadence**: regenerated on every `back-office-outcome-reconciliation` cycle run (ADR-195 Phase 3 defaults this to daily). **Not event-triggered** per-outcome to avoid thrash.

**Consumer**: AI occupants read their own calibration section as prior context. Operator reads the full file when making rotation or modes decisions. Frontend surfaces calibration summary on `/review` page.

**Idempotent**: rebuilt from scratch each cycle. No partial updates. No append pattern.

### D7 — Prospective-attribution contract (chat + UI invariants I1–I4)

Per reviewer-substrate.md §"The prospective-attribution contract":

- **I1**: Any surface displaying a pending proposal displays the current occupant identity alongside it. Implementation: `ProposalCard` component reads OCCUPANT.md at render time (or more likely, the proposal payload gains a `current_occupant` field populated by the API layer).
- **I2**: When a verdict renders, the verdict card displays the occupant identity inline. Implementation: verdict card already has `reviewer_identity` from Phase 2b; display it prominently rather than in audit-detail.
- **I3**: When OCCUPANT.md changes, chat emits a handoff event. Implementation: rotation protocol (D4) emits a chat notification on handoff; treated as a first-class event in the Stream surface per ADR-198.
- **I4**: Operator has a single chat command path to inspect OCCUPANT.md + modes.md + recent handoffs.md. Implementation: `/review status` slash command (or equivalent) returns a compact summary.

**Minimum UX footprint for Phase 4**: I1 + I2 only. I3 (chat notifications on rotation) and I4 (inspect command) are specified here but deferred to a Phase 4.1 sub-sprint if Phase 4 main scope proves large.

### D8 — Workspace init scaffolds all Phase 4 files

`workspace_init.py` Phase 2 extends `workspace_files` dict to include:

- `REVIEW_OCCUPANT_PATH: (DEFAULT_REVIEW_OCCUPANT_MD, "Reviewer seat current occupant — scaffolded to human:<user_id>")`
- `REVIEW_MODES_PATH: (DEFAULT_REVIEW_MODES_MD, "Reviewer seat operational modes — operator-editable")`
- `REVIEW_HANDOFFS_PATH: (DEFAULT_REVIEW_HANDOFFS_MD, "Reviewer seat rotation history")`
- `REVIEW_CALIBRATION_PATH: (DEFAULT_REVIEW_CALIBRATION_MD, "Reviewer seat calibration trail (auto-generated)")`

`workspace_paths.py` gains the four new constants. `agent_framework.py` gains the four new DEFAULT_REVIEW_*_MD constants.

Scaffolding is idempotent (existing workspace_init.py pattern): file written only if path doesn't exist.

### D9 — No class restructure; no agents-table changes; no /workspace/judgment/ restructure

Per the Option 2 feasibility audit (2026-04-23), the production-vs-judgment layer distinction is already structurally expressed in code through scope, substrate, trigger, and development axis. Creating a `reviewer` class in `AGENT_TEMPLATES` or adding an agents-table entry would:
- Violate Principle 14 by coupling the seat to an agent class
- Add ceremony without architectural substance
- Surface the Reviewer as an agent on `/agents` (wrong — the seat is not an agent)

Therefore Phase 4 does **not** include:
- A new `reviewer` class in `AGENT_TEMPLATES`
- A new row in the `agents` table
- A migration to the `agents.role` constraint
- A restructure to `/workspace/judgment/review/` (no second judgment archetype exists to justify the path nesting; restructure becomes warranted only if/when a second archetype ships)

### D10 — ADR-194 v2 status update on Phase 4 landing

When Phase 4 implementation lands:
- ADR-194 v2 Status line updates to "Phases 1 + 2a + 2b + 3 + 4 Implemented."
- ADR-194 v2 gains a final revision history row documenting the Phase 4 landing and pointing at this ADR as the scope record.
- No retroactive edits to ADR-194 v2 Decision sections — ADRs are historical artifacts; Phase 4 additions live in this ADR.

---

## Implementation sequence (when the sprint runs)

Recommended order for the dedicated sprint:

1. **Substrate scaffolding** (D1 + D2 + D3 + D8): add four new path constants, four DEFAULT_*_MD strings, four entries in `workspace_init.py`. Low risk, no behavior change yet.

2. **Principles-vs-modes split** (D5 partial): rename `review_principles.py` → `review_policy.py`, add `load_modes()` parser, migrate `is_eligible_for_auto_approve` to read from modes.md. Update the default-content files so new signups ship with modes.md populated and principles.md narrative-only.

3. **Dispatch refactor** (D5): update `review_proposal_dispatch.py` to read OCCUPANT.md + modes.md at verdict time. Route based on occupant class. Retains existing Phase 3 behavior as the `ai:*` branch.

4. **Rotation protocol** (D4): implement the three-step rotation primitive (read OCCUPANT → write new OCCUPANT → append handoffs). Hook to chat command (`/review rotate-to ...`). Signup path (already scaffolds via D8) emits initial handoffs entry.

5. **Calibration loop** (D6): add `back-office-reviewer-calibration` task to task_types registry. Implement generator in `services/back_office/reviewer_calibration.py` that reads decisions.md × all domain `_performance.md` files and produces calibration.md. Schedule to run after `back-office-outcome-reconciliation`.

6. **Prospective attribution UI** (D7): extend `action_proposals` API response with `current_occupant` field. Update ProposalCard frontend to display occupant identity in both pending and rendered-verdict states. Defer I3 + I4 to Phase 4.1 if scope warrants.

7. **Test coverage**: before and after each step. `test_recent_commits.py` regression gate. New tests for rotation protocol idempotency and calibration.md generation against known fixture data.

8. **ADR-194 v2 status update** (D10): update status line and add revision history row on final commit.

---

## Impact table

| Change | Files touched | Migration needed | Frontend impact |
|---|---|---|---|
| D1 OCCUPANT.md | workspace_paths.py, agent_framework.py, workspace_init.py | No | Yes (I1/I2) |
| D2 modes.md | workspace_paths.py, agent_framework.py, workspace_init.py | No | Minor (display on /review) |
| D3 handoffs.md | workspace_paths.py, agent_framework.py, workspace_init.py | No | Yes (I3, deferred) |
| D4 rotation protocol | New `services/review_rotation.py`, chat command hook | No | Yes (I3 deferred) |
| D5 dispatch refactor | review_proposal_dispatch.py, review_principles.py → review_policy.py | No | No |
| D6 calibration | New `services/back_office/reviewer_calibration.py`, task_types.py, workspace_paths.py | No | Minor (display on /review) |
| D7 attribution | API route for `action_proposals`, ProposalCard component | No | Yes |
| D8 init scaffold | workspace_init.py | No | No |
| D9 no-class | N/A | No | No |
| D10 ADR update | ADR-194 v2 | No | No |

**No DB migrations.** All state lives in files. `action_proposals.reviewer_identity` + `action_proposals.reviewer_reasoning` columns (migrations 152/153) already exist and are sufficient.

---

## Non-goals (explicitly out of scope for Phase 4)

- **Second judgment-layer archetype** (Auditor, Advocate, etc.). Phase 4 is Reviewer-only. The `/workspace/judgment/*/` restructure remains deferred until a second archetype is warranted.
- **External adapter implementations**. Phase 4 ships the structural path for `external:*` occupants but no actual adapters; `external:*` in OCCUPANT.md is accepted by the parser but no dispatch path exists until an adapter ships.
- **Auto-rotation on calibration signals**. Phase 4 supports operator-initiated rotation only. Auto-rotation (rotating back to human when AI confidence drops, rotating to AI when threshold is met) requires the calibration loop to have operational data first. Defer to a later phase.
- **Frontend-heavy attribution surfaces**. I3 (chat rotation notifications) and I4 (inspect command) are specified in the canon but can defer to Phase 4.1 if Phase 4 main scope pressure warrants.
- **New agent class, agent-table entry, or path restructure** (see D9).

---

## Relationship to other ADRs

- **ADR-194 v2** — Phase 4 is the final phase of that ADR. This ADR scopes it.
- **ADR-195 v2** — Phase 4's calibration loop consumes `_performance.md` produced by ADR-195's reconciliation task.
- **ADR-198** — I3 chat rotation notifications land in the Stream archetype.
- **ADR-209** — all writes to `/workspace/review/` (existing + new) flow through Authored Substrate with `authored_by` attribution.
- **THESIS.md** — this ADR implements commitment 2 (Independent judgment) more completely than ADR-194 v2 alone.
- **FOUNDATIONS Principle 14** — becomes structurally enforceable once OCCUPANT.md + rotation protocol (D4) land.

---

## Open questions (for the implementation sprint)

1. **Rotation command exact shape** — `/review rotate-to <identity>` assumed above, but the chat primitive surface may warrant something structured. Decide during implementation.
2. **Calibration rendering** — the `rolling_7d` / `rolling_30d` / `rolling_90d` windows per occupant may need narrative rendering beyond frontmatter aggregates. Spec as implementation proceeds.
3. **Migration path for existing workspaces** — workspaces scaffolded before Phase 4 land do not have OCCUPANT.md / modes.md / handoffs.md / calibration.md. Does workspace_init's idempotent scaffold handle this on next login, or does a one-time migration script need to run? **Recommendation**: idempotent scaffold handles it; no migration script.
4. **Retroactive calibration** — when calibration.md first generates, does it process all historical decisions × outcomes, or only from Phase 4 landing forward? **Recommendation**: only forward, to avoid retroactive signals from a time when the modes substrate didn't exist.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-23 | v1 — Proposed. Scopes Phase 4 of ADR-194 v2 as bounded coordinated landing: OCCUPANT + modes + handoffs + calibration + rotation protocol + dispatch refactor + prospective-attribution contract. Canonical target is reviewer-substrate.md. No class restructure per Option 2 feasibility audit. Implementation deferred to dedicated sprint. |
