# ADR-133: Workspace Context Architecture

> **Status**: Implementing
> **Date**: 2026-03-23
> **Authors**: KVK, Claude
> **Supersedes**: `/memory/` as user context path (ADR-108), `/brand/default/` as brand path
> **Extends**: ADR-106 (Workspace Architecture), ADR-132 (Work-First Onboarding)

---

## Context

User context is scattered across disconnected locations with no clear hierarchy:

- `/memory/MEMORY.md` — profile (name, company, role)
- `/memory/preferences.md` — per-platform tone/verbosity (2 fields per platform)
- `/memory/notes.md` — TP-accumulated facts and instructions
- `/brand/default/BRAND.md` — brand identity

Agents running within projects **cannot access user context** — they read their project scope (`/projects/{slug}/`) and agent scope (`/agents/{slug}/`), but not `/memory/`. This means an agent created for "Competitive Watch" doesn't know it works for an AI agent platform company.

Additionally, `preferences.md` is redundant — tone belongs in brand, per-platform style is unnecessary with audience-driven tone from project objectives.

## Decision

### Two-scope context model

**Workspace scope** (`/workspace/`) — who the user is. Stable. Changed by user directly. Read by TP, Composer, and all agents at execution time. Shared across all projects.

**Project scope** (`/projects/{slug}/`) — what this specific work is. Contains only project-unique data. Changed by PM and agents during execution.

### Workspace: two files

```
/workspace/
  IDENTITY.md   — who you are (name, company, role, industry, summary)
  BRAND.md      — how outputs look and sound (colors, typography, tone, voice)
```

- `preferences.md` dissolved — tone absorbed by BRAND.md, verbosity is an IDENTITY.md field if needed
- `notes.md` stays at `/memory/notes.md` — TP-accumulated knowledge, not user identity

### No project seeding — agents read workspace directly

Workspace files are NOT copied into projects. Agents read `/workspace/IDENTITY.md` and `/workspace/BRAND.md` directly at execution time. This avoids duplication, divergence, and stale snapshots.

Projects contain only project-unique data:

```
/projects/{slug}/
  PROJECT.md     — objective, contributors, delivery (unique per project)
  memory/        — PM state, work plan, assessments (unique per project)
  contributions/ — agent outputs (unique per project)
  assembly/      — composed deliverables (unique per project)
```

### Context reads at execution time

```
Agent execution reads:
  /workspace/IDENTITY.md    — who they work for (shared, always current)
  /workspace/BRAND.md       — output styling (shared, always current)
  /projects/{slug}/PROJECT.md — what to produce (project-specific)
/workspace/BRAND.md    → seeded into → /projects/{slug}/BRAND.md
```

Agents read project-level files. No runtime hierarchy crossing. Projects are self-contained execution contexts.

### Axioms

1. **Context has layers with different lifecycles** — identity (stable), projects (semi-stable), agent knowledge (accumulating), platform data (refreshing), activity (ephemeral)
2. **Every execution context must be self-contained** — agents at 3am in a cron need everything in their project scope
3. **Context flows down, never up** — user identity → project → agent. No reaching up at runtime.
4. **Two scopes only** — workspace (user-level) and project (execution-level). No intermediate layers.

## Migration

| Old Path | New Path | Notes |
|---|---|---|
| `/memory/MEMORY.md` | `/workspace/IDENTITY.md` | Profile data |
| `/memory/preferences.md` | Dissolved | Tone → BRAND.md, verbosity → IDENTITY.md |
| `/brand/default/BRAND.md` | `/workspace/BRAND.md` | Brand template |
| `/memory/notes.md` | `/memory/notes.md` | Unchanged — TP-accumulated knowledge |

## Revision History

| Date | Change |
|------|--------|
| 2026-03-23 | v1 — Initial: two-scope model, preferences dissolved, project seeding |
| 2026-03-23 | v1.1 — Removed project seeding. Agents read /workspace/ directly at execution time. No IDENTITY.md or BRAND.md in project folders. Projects contain only project-unique data. |
