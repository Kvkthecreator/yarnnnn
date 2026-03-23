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

**Workspace scope** (`/workspace/`) — who the user is. Stable. Changed by user directly. Read by TP and Composer. Seeded into projects at scaffold time.

**Project scope** (`/projects/{slug}/`) — what this work is. Self-contained execution context. Changed by PM and agents. Read by agents during execution.

### Workspace: two files

```
/workspace/
  IDENTITY.md   — who you are (name, company, role, industry, summary)
  BRAND.md      — how outputs look and sound (colors, typography, tone, voice)
```

- `preferences.md` dissolved — tone absorbed by BRAND.md, verbosity is an IDENTITY.md field if needed
- `notes.md` stays at `/memory/notes.md` — TP-accumulated knowledge, not user identity

### Project seeding

`scaffold_project()` copies workspace files into each new project:

```
/projects/{slug}/
  PROJECT.md     — objective, contributors, delivery
  IDENTITY.md    — snapshot of workspace IDENTITY.md at creation time
  BRAND.md       — snapshot of workspace BRAND.md at creation time
  memory/        — PM state
  ...
```

### Context flows down, never up

```
/workspace/IDENTITY.md → seeded into → /projects/{slug}/IDENTITY.md
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
