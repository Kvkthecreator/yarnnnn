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
# "archive") for declared preferences. Reviewer never writes — operator-
# authored substrate, included in DEFAULT_REVIEWER_WRITE_LOCKS below.
SHARED_PREFERENCES_PATH = "context/_shared/_preferences.yaml"

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

REVIEW_FILES = (
    REVIEW_IDENTITY_PATH,
    REVIEW_PRINCIPLES_PATH,
    REVIEW_JUDGMENT_LOG_PATH,
    REVIEW_OCCUPANT_PATH,
    REVIEW_HANDOFFS_PATH,
    REVIEW_CALIBRATION_PATH,
)

# ADR-258 (revised 2026-05-08): default lock set for Reviewer writes.
# Encodes the Reviewer / Operator authorship boundary — like a human
# supervisor who reads but doesn't rewrite the operator's foundational
# declarations (mandate, autonomy ceiling, identity, brand, conventions,
# durable interpretations).
#
# ADR-280 (2026-05-15): this constant contains ONLY kernel-universal locks —
# paths present in every workspace regardless of program. Program-specific
# locks (e.g., trading's `_operator_profile.md` + `_risk.md`, commerce's
# equivalents) are now declared by bundles in MANIFEST.yaml's
# `substrate_abi.path_zones` block (role: operator-canon → locked) and
# composed at runtime by `services/primitives/workspace.py::_is_path_locked_for_reviewer`.
# This honors FOUNDATIONS Derived Principle 16 (kernel-program boundary):
# the kernel encodes universals; programs declare program-specific contracts.
#
# The composition order at runtime:
#   1. DEFAULT_REVIEWER_WRITE_LOCKS (this constant — kernel-universal)
#   2. Workspace guide frontmatter `path_zones` with role='operator-canon'
#      (services/workspace_guide.py + services/bundle_reader.py)
#   3. Legacy operator overrides in /workspace/_shared/_locks.yaml
#      (locked_paths additions, unlocked_paths overrides)
#
# When the Reviewer's WriteFile is rejected, the Reviewer can:
#   - Surface a Clarify to the operator ("I'd like to update X — approve?")
#   - Note the suggestion in its own notes.md / reflections.md (workbench)
#   - Continue reasoning and let the operator act
DEFAULT_REVIEWER_WRITE_LOCKS = (
    SHARED_MANDATE_PATH,
    SHARED_AUTONOMY_PATH,
    SHARED_AUTONOMY_YAML_PATH,
    SHARED_IDENTITY_PATH,
    SHARED_BRAND_PATH,
    SHARED_CONVENTIONS_PATH,
    SHARED_PRECEDENT_PATH,
    SHARED_PREFERENCES_PATH,  # ADR-275: operator-declared deliverable cadence preferences
    "context/_shared/_locks.yaml",  # operator-authored lock policy itself
)
