"""
Workspace path constants (ADR-206).

Single source of truth for canonical workspace file paths. Callers pass these
to UserMemory (AgentWorkspace is agent-scoped; these are workspace-scoped).

Post-ADR-206 layout:

    /workspace/
      ├── context/
      │   ├── _shared/              ← authored shared context (new under ADR-206)
      │   │   ├── IDENTITY.md
      │   │   ├── BRAND.md
      │   │   └── CONVENTIONS.md
      │   └── {domain}/             ← accumulated domain context (ADR-151)
      ├── memory/                   ← YARNNN working memory (ADR-206 relocation)
      │   ├── awareness.md
      │   ├── _playbook.md
      │   ├── style.md
      │   └── notes.md
      ├── review/                   ← Reviewer substrate (ADR-194)
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
SHARED_IDENTITY_PATH = "context/_shared/IDENTITY.md"
SHARED_BRAND_PATH = "context/_shared/BRAND.md"
SHARED_CONVENTIONS_PATH = "context/_shared/CONVENTIONS.md"

SHARED_CONTEXT_FILES = (
    SHARED_IDENTITY_PATH,
    SHARED_BRAND_PATH,
    SHARED_CONVENTIONS_PATH,
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
# -----------------------------------------------------------------------------
REVIEW_IDENTITY_PATH = "review/IDENTITY.md"
REVIEW_PRINCIPLES_PATH = "review/principles.md"
REVIEW_DECISIONS_PATH = "review/decisions.md"
