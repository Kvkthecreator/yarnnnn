"""
Workspace path constants (ADR-206).

Single source of truth for canonical workspace file paths. Callers pass these
to UserMemory (AgentWorkspace is agent-scoped; these are workspace-scoped).

Post-ADR-206 layout:

    /workspace/
      ├── context/
      │   ├── _shared/              ← authored shared context (ADR-206 + ADR-207 MANDATE)
      │   │   ├── MANDATE.md        ← workspace's CLAUDE.md equivalent (ADR-207 D2)
      │   │   ├── IDENTITY.md
      │   │   ├── BRAND.md
      │   │   └── CONVENTIONS.md
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
      │   ├── modes.md              ← operational modes (autonomy × scope × posture)
      │   ├── decisions.md          ← append-only verdict trail
      │   ├── handoffs.md           ← append-only occupant-rotation log
      │   └── calibration.md        ← auto-generated judgments-vs-outcomes trail
      ├── tasks/                    ← task substrate (ADR-138)
      ├── agents/                   ← agent substrate (ADR-106)
      ├── uploads/                  ← user-contributed reference material (ADR-152)
      └── working/                  ← ephemeral scratch (ADR-119)

Post-ADR-206 root contains only folders — no loose .md files at root. IDENTITY,
BRAND, CONVENTIONS moved under `context/_shared/` because they are *authored
shared context readable by all agents and tasks*. Awareness, playbook, style,
notes moved under `memory/` because they are *YARNNN's own working memory*.
"""

# -----------------------------------------------------------------------------
# Authored shared context (`/workspace/context/_shared/`)
# -----------------------------------------------------------------------------
SHARED_MANDATE_PATH = "context/_shared/MANDATE.md"
SHARED_IDENTITY_PATH = "context/_shared/IDENTITY.md"
SHARED_BRAND_PATH = "context/_shared/BRAND.md"
SHARED_CONVENTIONS_PATH = "context/_shared/CONVENTIONS.md"
# ADR-217: Workspace-scoped autonomy delegation. Sibling to MANDATE/IDENTITY/
# BRAND/CONVENTIONS. Operator-authored; read by Reviewer dispatcher (replaces
# the deleted review/modes.md) and task pipeline capability gate.
SHARED_AUTONOMY_PATH = "context/_shared/AUTONOMY.md"

SHARED_CONTEXT_FILES = (
    SHARED_MANDATE_PATH,
    SHARED_IDENTITY_PATH,
    SHARED_BRAND_PATH,
    SHARED_CONVENTIONS_PATH,
    SHARED_AUTONOMY_PATH,
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
