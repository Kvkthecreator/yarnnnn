"""
Workspace path constants (ADR-206 + workspace-init refactor 2026-05-03).

Single source of truth for canonical workspace file paths. Callers pass these
to UserMemory (AgentWorkspace is agent-scoped; these are workspace-scoped).

Post-ADR-206 layout:

    /workspace/
      ├── context/
      │   ├── _shared/              ← authored shared context + governance declarations
      │   │   ├── MANDATE.md        ← workspace's CLAUDE.md equivalent (ADR-207 D2)
      │   │   ├── IDENTITY.md
      │   │   ├── BRAND.md
      │   │   ├── AUTONOMY.md      ← delegation ceiling (ADR-217)
      │   │   ├── PRECEDENT.md     ← durable interpretations / boundary cases
      │   │   └── CONVENTIONS.md   ← program-scoped (NOT kernel-seeded; only present
      │   │                           when a program bundle forks it via reference-workspace/)
      │   └── {domain}/             ← accumulated domain context (ADR-151)
      ├── memory/                   ← YARNNN working memory (ADR-206 relocation)
      │   ├── awareness.md
      │   ├── _playbook.md
      │   ├── style.md
      │   └── notes.md
      ├── review/                   ← Reviewer substrate (ADR-194 + ADR-211 Phase 4)
      │   ├── IDENTITY.md           ← who the seat is (role-level, static)
      │   ├── OCCUPANT.md           ← who currently fills it (rotates via handoffs)
      │   ├── principles.md         ← declared judgment framework (narrative)
      │   ├── judgment_log.md      ← append-only judgment lineage (system-ledger, ADR-281 §5)
      │   ├── handoffs.md           ← append-only occupant-rotation log
      │   └── calibration.md        ← auto-generated judgments-vs-outcomes trail
      ├── agents/                   ← agent substrate (ADR-106)
      ├── reports/                  ← deliverable recurrence outputs (ADR-231)
      ├── operations/               ← action recurrence state (ADR-231)
      ├── uploads/                  ← user-contributed reference material (ADR-152)
      └── working/                  ← ephemeral scratch (ADR-119)

IDENTITY, BRAND, AUTONOMY, PRECEDENT are kernel-seeded at every workspace init.
CONVENTIONS.md is a valid writable path but is NOT seeded by the kernel — it is
program-scoped (program bundles like alpha-trader fork it via reference-workspace/
with tier:canon). Generic workspaces do not receive a CONVENTIONS skeleton.
Awareness, playbook, style, notes moved under `memory/` per ADR-206.
"""

# -----------------------------------------------------------------------------
# Authored shared context (`/workspace/context/_shared/`)
# -----------------------------------------------------------------------------
SHARED_MANDATE_PATH = "context/_shared/MANDATE.md"
SHARED_IDENTITY_PATH = "context/_shared/IDENTITY.md"
SHARED_BRAND_PATH = "context/_shared/BRAND.md"
# CONVENTIONS.md path constant kept for callers that need to reference or write
# it (bundle forks, editable-path allowlist in workspace.py). NOT in
# SHARED_CONTEXT_FILES — kernel does not seed it at init.
SHARED_CONVENTIONS_PATH = "context/_shared/CONVENTIONS.md"
# ADR-217 + ADR-254: Autonomy delegation.
# SHARED_AUTONOMY_PATH = prose documentation (LLM reads, human reads — not machine-parsed)
# SHARED_AUTONOMY_YAML_PATH = machine-parsed delegation config (yaml.safe_load)
SHARED_AUTONOMY_PATH = "context/_shared/AUTONOMY.md"          # prose doc — preserved for LLM reads
SHARED_AUTONOMY_YAML_PATH = "context/_shared/_autonomy.yaml"  # machine-parsed (ADR-254)
# Shared durable interpretations: operator-authored precedent that survives
# seat rotation and is readable by YARNNN, Reviewer, and domain Agents alike.
SHARED_PRECEDENT_PATH = "context/_shared/PRECEDENT.md"
# ADR-275: Operator-authored deliverable cadence preferences. Reviewer
# reads this every wake and authors Schedule(action="create"|"update"|
# "archive") for declared preferences.
# ADR-293: this file is OPERATIONAL substrate (Reviewer-writable subject
# to AUTONOMY-mode gating). The Reviewer maintains operator deliverable
# preferences on the operator's behalf; under `bounded` writes queue with
# operator diff-preview; under `autonomous` writes apply immediately with
# revision-chain capture. Previously locked-by-default per ADR-275; ADR-
# 293's first-principles test (governance only locks files that grant
# the Reviewer unauthorized authority) removes the lock — preferences
# refinement is operational maintenance, not authority grant.
SHARED_PREFERENCES_PATH = "context/_shared/_preferences.yaml"

# ADR-298 Phase 2 — operator-authored pace declaration. Pace is the operator's
# first-class dial for "how often the agent works" (ADR-298 D4 + D11 trifecta).
# Read at every reviewer wake via the governance envelope (ADR-276) so the
# Reviewer's Schedule() calls can pace-gate at declaration time per D5.
SHARED_PACE_PATH = "context/_shared/_pace.yaml"

# ADR-293: Compute-resource governance. Operator declares spending
# ceilings + recurrence-cadence floors that the scheduler enforces
# regardless of AUTONOMY mode. The Reviewer reads but cannot author —
# Reviewer-edit could escalate its own resource ceiling, granting itself
# authority the operator did not delegate. Governance file per the
# first-principles test.
SHARED_TOKEN_BUDGET_PATH = "context/_shared/_token_budget.yaml"

# Files the kernel seeds at every workspace init. CONVENTIONS.md is intentionally
# excluded — it is program-scoped, not kernel-scoped. See module docstring above.
SHARED_CONTEXT_FILES = (
    SHARED_MANDATE_PATH,
    SHARED_IDENTITY_PATH,
    SHARED_BRAND_PATH,
    SHARED_AUTONOMY_PATH,
    SHARED_PRECEDENT_PATH,
)


# -----------------------------------------------------------------------------
# YARNNN working memory (`/workspace/memory/`)
# -----------------------------------------------------------------------------
MEMORY_AWARENESS_PATH = "memory/awareness.md"
MEMORY_PLAYBOOK_PATH = "memory/_playbook.md"
MEMORY_STYLE_PATH = "memory/style.md"
MEMORY_NOTES_PATH = "memory/notes.md"

MEMORY_FILES = (
    MEMORY_AWARENESS_PATH,
    MEMORY_PLAYBOOK_PATH,
    MEMORY_STYLE_PATH,
    MEMORY_NOTES_PATH,
)


# -----------------------------------------------------------------------------
# Reviewer substrate (`/workspace/review/`, ADR-194 — unchanged by ADR-206)
# Phase 4 (ADR-211) reached seven files: IDENTITY + principles + decisions +
# OCCUPANT + modes + handoffs + calibration.
# ADR-217 (2026-04-24): modes.md removed — autonomy is operator-authored
# delegation and now lives at SHARED_AUTONOMY_PATH. Seat substrate shrinks
# to six files. Singular implementation — no dual path.
# -----------------------------------------------------------------------------
REVIEW_IDENTITY_PATH = "review/IDENTITY.md"
REVIEW_PRINCIPLES_PATH = "review/principles.md"          # prose (LLM reads)
REVIEW_PRINCIPLES_YAML_PATH = "review/_principles.yaml"  # machine-parsed thresholds (ADR-254)
REVIEW_JUDGMENT_LOG_PATH = "review/judgment_log.md"
# Phase 4 (ADR-211) minus modes.md (ADR-217):
REVIEW_OCCUPANT_PATH = "review/OCCUPANT.md"
REVIEW_HANDOFFS_PATH = "review/handoffs.md"
REVIEW_CALIBRATION_PATH = "review/calibration.md"
# ADR-284 (2026-05-17): Reviewer's forward-looking standing intent —
# `reviewer-workbench` role per ADR-281 §3. Single-writer (the Reviewer).
# Overwritable per judgment cycle; revision chain preserves history.
REVIEW_STANDING_INTENT_PATH = "review/standing_intent.md"

REVIEW_FILES = (
    REVIEW_IDENTITY_PATH,
    REVIEW_PRINCIPLES_PATH,
    REVIEW_JUDGMENT_LOG_PATH,
    REVIEW_OCCUPANT_PATH,
    REVIEW_HANDOFFS_PATH,
    REVIEW_CALIBRATION_PATH,
    REVIEW_STANDING_INTENT_PATH,
)

# Program-bundle-shipped capability library — Claude Code skills.md analog
# (per ADR-261 D6 + ADR-275). Bundles fork files into this directory at
# activation. The Reviewer reads individual specs on demand via ReadFile;
# the wake envelope surfaces a name+title inventory so the Reviewer knows
# which specs exist without paying the cost of pre-loading their bodies.
SPECS_PREFIX = "/workspace/specs/"

# ADR-293 (2026-05-19): governance file set — the ONLY paths locked from
# Reviewer runtime. Pre-ADR-293 this set contained 9 paths derived from a
# 4-layer composition (kernel defaults + workspace guide path_zones +
# bundle path_zones + _locks.yaml overrides). The first-principles test
# in ADR-293 D1 narrowed the lock to files whose Reviewer-edit could grant
# unauthorized authority: the delegation declaration + the compute-budget
# declaration. Everything else is OPERATIONAL — Reviewer-writable subject
# to AUTONOMY-mode gating (manual queues all, bounded queues with operator
# diff-preview, autonomous applies immediately with revision-chain capture).
#
# Singular Implementation: this is the SOLE lock source. No bundle-derived
# locks, no workspace-guide locks, no `_locks.yaml` overrides. The composition
# in `services/primitives/workspace.py::_is_path_locked_for_reviewer` collapses
# to one check: `path in DEFAULT_REVIEWER_WRITE_LOCKS`.
#
# Why these three (and only these three):
#   - AUTONOMY.md / _autonomy.yaml — Reviewer rewriting `delegation: bounded`
#     to `autonomous` grants itself unconditional auto-execute authority
#     the operator did not delegate. Lock is structurally load-bearing.
#   - _token_budget.yaml — Reviewer raising `daily_spend_ceiling_usd` from
#     $5 to $500 escalates its own compute resource ceiling. Lock is
#     structurally load-bearing.
#
# Why everything else is unlocked:
#   - MANDATE, IDENTITY, BRAND, CONVENTIONS, PRECEDENT, _operator_profile,
#     _risk, _universe, _preferences, _recurrences, principles, etc. — these
#     are operational content. Reviewer-edits change WHAT the operation does,
#     not WHETHER the Reviewer has unauthorized authority to do it. The
#     revision chain (ADR-209) is the audit trail; AUTONOMY mode is the
#     gating mechanism; the operator reviews diffs (under bounded) or revision
#     history (under autonomous). Same trust model as Claude Code editing the
#     project's CLAUDE.md.
DEFAULT_REVIEWER_WRITE_LOCKS = (
    SHARED_AUTONOMY_PATH,
    SHARED_AUTONOMY_YAML_PATH,
    SHARED_TOKEN_BUDGET_PATH,
    # ADR-275 D6 + D9 (2026-05-21 amendment): _preferences.yaml is operator's
    # declaration of deliverable cadence — bundle-fork honors at activation
    # (D9), Reviewer reconciles operator-authored changes via Schedule (D10).
    # The Reviewer reads but does not write this file; preference content is
    # the operator's authority. Closes pre-existing drift between ADR-275 D6
    # (which specified the lock) and the prior code state (which had it
    # unlocked).
    SHARED_PREFERENCES_PATH,
    # ADR-298 Phase 2: pace is operator-authored only. Reviewer reads pace
    # at every wake (governance envelope per ADR-276) and the Schedule
    # primitive pace-gates at declaration time (ADR-298 D5). The Reviewer
    # surfaces Clarify when its proposed recurrence would exceed the
    # declared pace; the operator decides whether to pause an existing
    # recurrence, upgrade pace, or skip. Reviewer never writes pace itself.
    SHARED_PACE_PATH,
)
