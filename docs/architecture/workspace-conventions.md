# Architecture: Workspace Conventions

**Status:** Canonical (v1 — expected to evolve)
**Date:** 2026-03-11
**Related:**
- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — governing ADR
- [Naming Conventions](naming-conventions.md) — broader naming system
- [Agent Execution Model](agent-execution-model.md) — how agents interact with workspace

---

## Overview

Every YARNNN agent has a **workspace** — a virtual filesystem of human-readable files backed by Postgres (`workspace_files` table). The path conventions defined here are the schema. New agent capabilities extend paths, not database tables.

This document is the canonical reference for workspace path conventions. The ADR-106 Workspace Convention Spec section contains the design rationale; this document is the implementation reference.

---

## Industry Alignment

YARNNN's workspace conventions deliberately mirror Claude Code's filesystem model where applicable. This is a forward bet on agent-to-agent interop — as MCP resources, A2A Agent Cards, and cross-platform agent communication mature, YARNNN agents will speak a common language.

| Purpose | Claude Code | YARNNN | Rationale |
|---------|------------|--------|-----------|
| Identity + instructions | `CLAUDE.md` | `AGENT.md` | Capitalized, root-level, discoverable |
| Memory directory | `.claude/memory/` | `memory/` | Topic-scoped, unbounded |
| Default memory | `.claude/memory/MEMORY.md` | `memory/observations.md` | Semantic name > generic name |
| Topic memory | `.claude/memory/{topic}.md` | `memory/{topic}.md` | Same pattern |
| Settings/config | `.claude/settings.json` | DB columns (not workspace) | Config ≠ intelligence |
| Event hooks | `.claude/hooks/` | (future) `hooks/` | Phase 3 |

**YARNNN-unique files** (no Claude Code equivalent):
- `thesis.md` — self-evolving domain understanding. This is the core differentiator: agents that build persistent theses.
- `working/{topic}.md` — intermediate research notes that persist across tool rounds within a run.
- `runs/v{N}.md` — versioned output history for self-reference and improvement.

---

## Path Tree

```
/agents/{agent_slug}/
│
├── AGENT.md                    # Identity + behavioral instructions
│                               # Like CLAUDE.md — the entry point
│                               # User-writable, agent-readable
│                               # Maps to: agent_instructions column (Phase 2 migration)
│
├── thesis.md                   # Agent's current domain understanding
│                               # Self-evolving — agent updates after each run
│                               # YARNNN-unique differentiator
│
├── memory/                     # Topic-scoped persistent memory
│   ├── observations.md         # Timestamped observations from review passes
│   ├── preferences.md          # Learned preferences from user edit patterns
│   └── {topic}.md              # Agent-created topic files (unbounded)
│
├── working/                    # Intermediate research (per-run scratch space)
│   └── {topic}.md              # Research notes, saved queries, evidence
│
├── runs/                       # Immutable output history
│   └── v{N}.md                 # Output + metadata per execution
│
└── references/                 # (future) Cross-agent references
    └── {ref}.md                # Cached content from other agents/sources
```

### Knowledge Base (shared, read-only for agents)

```
/knowledge/
├── slack/
│   └── {channel_name}/
│       └── {date}.md           # Daily content snapshots
├── gmail/
│   └── {label}/
│       └── {date}.md
├── notion/
│   └── {page_name}.md
├── calendar/
│   └── {date}.md
└── yarnnn/                     # Agent outputs (always retained)
    └── {agent_slug}-v{N}.md
```

### User-Level (global)

```
/workspace.md                   # Global user context
/preferences.md                 # User-level learned preferences
```

---

## File Semantics

### Identity: AGENT.md

The agent's root identity file. Mirrors `CLAUDE.md` — a single discoverable file that defines who this agent is and how it should behave.

**Contains:**
- Behavioral instructions (tone, focus areas, audience)
- Targeting directives (what to prioritize within sources)
- Format preferences (structure, length, style)

**Who writes:** User (via UI instructions editor, future workspace browser)
**Who reads:** Agent (loaded first in `load_context()`)

**Maps to:** Currently `agent_instructions` column on `agents` table. Phase 2 will migrate to reading from workspace file as source of truth.

### Domain Understanding: thesis.md

The agent's accumulated understanding of its domain. This is what makes reasoning agents (analyst, researcher, coordinator) improve with tenure.

**Contains:**
- The agent's current framing of its domain
- Key entities, relationships, and patterns it has identified
- What it considers significant vs noise

**Who writes:** Agent (updated after each generation run)
**Who reads:** Agent (loaded in `load_context()`, used as starting point for investigation)

**No Claude Code equivalent.** This is YARNNN's core intelligence primitive.

### Memory: memory/

Topic-scoped persistent memory. Mirrors Claude Code's `.claude/memory/` directory.

**Why a directory, not a single file:**
- Single `memory.md` grows unbounded — becomes noise
- Topic-scoped files let agents compartmentalize knowledge
- Agents can create memory files on any topic they deem worth remembering
- `load_context()` reads all memory files, newest contributions at top

**Standard files:**
| File | Written by | Contains |
|------|-----------|----------|
| `observations.md` | Agent (via `record_observation()`) | Timestamped review pass observations |
| `preferences.md` | Feedback engine (system) | Learned preferences from user edit patterns |
| `{topic}.md` | Agent (via WriteWorkspace) | Agent-determined topic memory |

### Research: working/

Intermediate research notes. Ephemeral within a run lifecycle — agents write here during investigation, read back during generation.

**Distinction from memory/:** Working notes are process artifacts. Memory is distilled knowledge. An agent might write `working/competitor-analysis.md` during research, then distill findings into `memory/competitive-landscape.md` for long-term retention.

### Output History: runs/

Immutable record of each execution's output. Agents can read their past runs to avoid repetition and build on prior work.

**Written by:** Orchestration pipeline (after generation completes)
**Naming:** `v{N}.md` where N is the sequential version number

---

## Conventions for New Files

When extending the workspace with new file types:

1. **Use existing directories first.** Don't create new top-level directories unless the content doesn't fit `memory/`, `working/`, `runs/`, or `references/`.
2. **Use `.md` extension.** All workspace content is Markdown. LLMs are pre-trained on Markdown. Exception: structured data files (future `agent-card.json`).
3. **Use lowercase-kebab-case** for user/agent-created files (`competitive-landscape.md`, not `CompetitiveLandscape.md`).
4. **Capitalize identity files** (`AGENT.md`, future `README.md`). These signal "this is an entry point."
5. **Date-stamp temporal content** (`2026-03-11.md` for daily snapshots in knowledge base).

---

## Access Patterns

### Agent → Workspace (via primitives)

| Primitive | Operation | Typical paths |
|-----------|-----------|---------------|
| ReadWorkspace | Read file content | `AGENT.md`, `thesis.md`, `memory/observations.md` |
| WriteWorkspace | Create/overwrite file | `thesis.md`, `memory/{topic}.md`, `working/{topic}.md` |
| SearchWorkspace | Full-text search | Query across all workspace files |
| ListWorkspace | Directory listing | `memory/`, `working/`, `runs/` |
| QueryKnowledge | Search knowledge base | `/knowledge/` (shared, cross-agent) |

### System → Workspace (via AgentWorkspace class)

| Caller | Operation | Path |
|--------|-----------|------|
| `proactive_review.py` | Append observation | `memory/observations.md` |
| `agent_execution.py` | Save run output | `runs/v{N}.md` |
| Feedback engine (future) | Write preferences | `memory/preferences.md` |
| Perception pipeline (future) | Write knowledge | `/knowledge/{platform}/{resource}/{date}.md` |

---

## Evolution Path

### Phase 2 (planned)
- Perception pipeline writes to `/knowledge/` instead of (or alongside) `platform_content` table
- `agent_instructions` column migrated to `AGENT.md` as source of truth
- `user_memory` KV pairs migrated to `/workspace.md` and `/preferences.md`

### Phase 3 (planned)
- `hooks/` directory for agent-level event triggers
- `agent-card.json` for A2A interop (auto-generated from AGENT.md + thesis)
- MCP resource URI mapping: `workspace://agents/{slug}/AGENT.md`
- Workspace browser UI for inspecting/editing agent state

### Future (speculative)
- `references/` for cross-agent cached content
- Cloud storage backend (S3/GCS) via abstraction layer swap
- Agent-to-agent workspace sharing protocols

---

## References

- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — governing ADR with convention spec
- [ADR-101: Agent Intelligence Model](../adr/ADR-101-agent-intelligence-model.md) — four-layer model mapped to workspace
- [Naming Conventions](naming-conventions.md) — broader YARNNN naming system
- [Agent Execution Model](agent-execution-model.md) — how orchestration invokes agents
