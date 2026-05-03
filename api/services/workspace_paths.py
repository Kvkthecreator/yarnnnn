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
      │   ├── decisions.md          ← append-only verdict trail
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
# ADR-217: Workspace-scoped autonomy delegation. Operator-authored; read by
# Reviewer dispatcher and task pipeline capability gate.
SHARED_AUTONOMY_PATH = "context/_shared/AUTONOMY.md"
# Shared durable interpretations: operator-authored precedent that survives
# seat rotation and is readable by YARNNN, Reviewer, and domain Agents alike.
SHARED_PRECEDENT_PATH = "context/_shared/PRECEDENT.md"

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
REVIEW_PRINCIPLES_PATH = "review/principles.md"
REVIEW_DECISIONS_PATH = "review/decisions.md"
# Phase 4 (ADR-211) minus modes.md (ADR-217):
REVIEW_OCCUPANT_PATH = "review/OCCUPANT.md"
REVIEW_HANDOFFS_PATH = "review/handoffs.md"
REVIEW_CALIBRATION_PATH = "review/calibration.md"

REVIEW_FILES = (
    REVIEW_IDENTITY_PATH,
    REVIEW_PRINCIPLES_PATH,
    REVIEW_DECISIONS_PATH,
    REVIEW_OCCUPANT_PATH,
    REVIEW_HANDOFFS_PATH,
    REVIEW_CALIBRATION_PATH,
)
