# ADR-152: Unified Directory Registry — Single Source of Truth for Workspace Filesystem

> **⚠ Amended by [ADR-205](ADR-205-primitive-collapse.md) (2026-04-22).** `WORKSPACE_DIRECTORIES` no longer drives signup-time directory pre-creation. It becomes a naming-convention reference consulted when tasks first write to a domain. Directories materialize at first-write, not at signup. Registry shape unchanged; signup-time creation hook removed.
>
> **⚠ Further amended by [ADR-206](ADR-206-operation-first-scaffolding.md) (2026-04-22).** Adds `_shared/` as a named directory type under `/workspace/context/`. Files previously at workspace root (`IDENTITY.md`, `BRAND.md`, `CONVENTIONS.md`) relocate to `/workspace/context/_shared/`. The underscore-prefix convention extends: `_shared/` (authored cross-domain context), `_tracker.md` (domain-scoped materialized view), `_playbook-*.md` (agent-scoped playbooks), `_performance.md` (money-truth per domain). Post-ADR-206, `/workspace/` root contains only operational folders (`/tasks/`, `/agents/`, `/context/`, `/memory/`, `/review/`, `/working/`, `/uploads/`) — no loose files at root.
>
> **⚠ Further amended by [ADR-224](ADR-224-kernel-program-boundary-refactor.md) (2026-04-27).** Kernel `WORKSPACE_DIRECTORIES` now holds only kernel-universal directories (uploads, _shared, generic knowledge-work domains, capability-bundle-owned slack/notion/github). Program-specific directories (trading, portfolio, customers, revenue) move to program bundle MANIFEST.yaml `context_domains[]` declarations and surface through `bundle_reader` fallback in `get_directory()` / `get_synthesis_content()` / `has_entity_tracker()` / `get_authored_substrate()`. The boundary is enforced by `test_adr224_kernel_boundary.py`.

**Status:** Proposed
**Date:** 2026-03-31
**Supersedes:** ADR-151 `CONTEXT_DOMAINS` (absorbed into unified registry)
**Amended by:** ADR-205 (registry is naming-convention reference only), ADR-206 (`_shared/` directory type added; workspace-root files relocate under `/context/_shared/`), ADR-224 (kernel-universal vs program-specific split — program-specific directories move to program bundle MANIFEST.yaml)
**Extends:** ADR-149 (task lifecycle), ADR-151 (shared context domains)

---

## Context

ADR-151 established `/workspace/context/` with `CONTEXT_DOMAINS` governing 6 context domains. But the workspace has three types of content directories that need governance:

1. **uploads/** — user-contributed reference material (was: `documents/`)
2. **context/** — agent-accumulated intelligence substrate (6 domains)
3. **outputs/** — agent-produced synthesized deliverables (NEW)

Having `CONTEXT_DOMAINS` govern only context/ creates fragmentation — uploads and outputs have no registry, no conventions, no scaffolding. The "documents" naming conflates user uploads with system-produced documents.

Additionally, two fundamentally different task work patterns exist:
- **Context maintenance** — update-context steps that maintain `/workspace/context/{domain}/`
- **Synthesis & output** — derive-output steps that produce documents to `/workspace/outputs/{category}/`

These need different DELIVERABLE.md templates and different evaluation criteria, unified under one registry.

## Decision

### Unified Directory Registry

One registry governs ALL workspace content directories. Replaces `CONTEXT_DOMAINS` with `WORKSPACE_DIRECTORIES`.

Three directory types:

| Type | Path | Managed by | Purpose |
|---|---|---|---|
| `user_contributed` | `uploads/` | User | Uploaded reference material |
| `context` | `context/{domain}/` | Agent (via tasks) | Accumulated intelligence substrate |
| `output` | `outputs/{category}/` | Agent (via tasks) | Synthesized deliverable documents |

### Workspace Filesystem (Final)

```
/workspace/
├── IDENTITY.md                     # User identity
├── BRAND.md                        # Output style
├── uploads/                        # USER-CONTRIBUTED (renamed from documents/)
│   ├── ir-deck-march-2026.md
│   └── product-roadmap.md
├── context/                        # ACCUMULATED SUBSTRATE (agent-maintained)
│   ├── competitors/
│   ├── market/
│   ├── relationships/
│   ├── projects/
│   ├── content/
│   ├── signals/
│   └── assets/
├── outputs/                        # SYNTHESIZED DELIVERABLES (agent-produced)
│   ├── reports/
│   ├── briefs/
│   └── assets/
├── notes.md
└── preferences.md
```

### documents/ → uploads/ Rename

`documents/` renamed to `uploads/` because:
- Removes ambiguity: "documents" could mean user uploads OR system-produced docs
- `uploads/` clearly signals: "things the user put here"
- `outputs/` clearly signals: "things the system produced"
- The pair (uploads ↔ outputs) is immediately comprehensible

### Task Type Registry — output_category

Task types gain `output_category` field declaring where synthesized outputs get promoted:

```python
"competitive-intel-brief": {
    "context_reads": ["competitors"],
    "context_writes": ["competitors", "signals"],
    "output_category": "briefs",           # ← NEW: promoted to /workspace/outputs/briefs/
    "process": [
        {"step": "update-context", ...},
        {"step": "derive-output", ...},
    ],
}

"stakeholder-update": {
    "context_reads": ["competitors", "market", "projects", "relationships"],
    "context_writes": ["projects", "signals"],
    "output_category": "reports",          # ← NEW: promoted to /workspace/outputs/reports/
    ...
}
```

Tasks without `output_category` (context-only tasks, or tasks where output stays task-scoped) don't promote — output remains in `/tasks/{slug}/outputs/`.

### DELIVERABLE.md Bifurcation

For context-maintenance tasks (only update-context step, no derive-output):
```markdown
# Context Quality Specification

## Coverage
- Minimum 3 competitor profiles maintained
- Each profile: overview, signals, product, strategy sections populated

## Freshness
- Entity files updated within last 30 days
- Signal log entries within last 7 days

## Depth
- Each competitor has at least 5 signal entries
- Strategic assessment reflects latest findings
```

For synthesis tasks (has derive-output step):
```markdown
# Deliverable Specification

## Expected Output
- Format: HTML document, 2000-3000 words
- Layout: Executive Summary → Key Findings → Analysis → Implications

## Expected Assets
- Trend chart, comparison chart, positioning diagram

## Quality Criteria
- Every claim has inline citation
- Emphasis on what changed since last cycle

## Audience
Leadership team. Board-level polish.
```

The task type registry's `default_deliverable` already contains this — the builder just needs to produce the right template based on whether the task has a derive-output step.

---

## Phases

### Phase 1: Registry + Rename + Output Categories
- `domain_registry.py` → `directory_registry.py` with `WORKSPACE_DIRECTORIES`
- `documents/` → `uploads/` in all code references
- `output_category` field on task types
- Update all callers (7 files import from domain_registry)
- Update workspace-conventions.md, registry-matrix.md, CLAUDE.md

### Phase 2: Output Promotion in Pipeline
- After derive-output step, promote output to `/workspace/outputs/{category}/`
- Naming: `{task-slug}-{date}.md` (or `.html`)
- Promotion is conditional on `output_category` being set
- Task-scoped output still saved (dual write: task outputs/ + workspace outputs/)

### Phase 3: DELIVERABLE.md Template Bifurcation
- `build_deliverable_md_from_type()` produces context-quality spec for context-only tasks
- Produces document-quality spec for synthesis tasks
- Detection: task type has derive-output step → synthesis template; otherwise → context template

---

## Key Files

| Concern | Location |
|---|---|
| Directory registry | `api/services/directory_registry.py` (replaces domain_registry.py) |
| Task type registry | `api/services/task_types.py` (gains output_category) |
| Workspace conventions | `docs/architecture/workspace-conventions.md` |
| Registry matrix | `docs/architecture/registry-matrix.md` |
