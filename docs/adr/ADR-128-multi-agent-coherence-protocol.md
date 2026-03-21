# ADR-128: Multi-Agent Coherence Protocol

> **Status**: Proposed
> **Date**: 2026-03-21
> **Authors**: KVK, Claude
> **Scope**: How intelligence flows between conversation, filesystem, and agent cognition substrates
> **Related**: ADR-106 (workspace), ADR-120 (project execution), ADR-121 (PM intelligence), ADR-124 (meeting room), ADR-126 (agent pulse)
> **Extends**: FOUNDATIONS.md Axiom 2 (recursive perception), Axiom 3 (developing entities)

---

## Context

YARNNN's PM cognitive model v1.0 introduced layered prerequisite reasoning — PM agents evaluate commitment → structure → context → quality → readiness and persist their assessment. This surfaced a deeper architectural gap: the platform has three intelligence substrates (conversation, filesystem, agent cognition) that operate as parallel silos. Intelligence doesn't flow between them systematically.

**The result**: A user directive in the meeting room evaporates on session rotation. Contributors generate without evaluating mandate fitness. PM sees output quality but not contributor cognitive state. The multi-agent system forgets between cycles instead of compounding.

## Decision

Establish the **coherence protocol** — rules for how intelligence flows between substrates so the system accumulates rather than forgets.

### Three Intelligence Substrates

1. **Conversation** — project sessions, chat messages, compaction. What was said. Append-only, compacts over time.
2. **Filesystem** — workspace files (AGENT.md, memory/, PROJECT.md, cognitive files). What agents know. Evolves with each pulse/run.
3. **Agent Cognition** — role prompts, pulse decisions, execution strategies. How agents think. Shaped by the filesystem.

These are peer substrates, not hierarchical.

### Four Coherence Flows

```
┌─────────────────────────────────────────────────────┐
│                  CONVERSATION                        │
│  (project sessions, chat messages, compaction)       │
│                                                      │
│  Flow 3: Agent self-writes directives ──────────┐   │
│  Flow 4: PM references persistent assessment ◄──┤   │
└───────────────────┬─────────────────────────────┘   │
                    │                                  │
                    │ Flow 3                           │
                    ▼                                  │
┌─────────────────────────────────────────────────┐   │
│                  FILESYSTEM                      │   │
│  (workspace files: AGENT.md, memory/, PROJECT.md)│   │
│                                                  │   │
│  memory/self_assessment.md  ◄── Flow 1           │   │
│  memory/directives.md       ◄── Flow 3           │   │
│  memory/project_assessment.md ── Flow 2 ──►      │   │
│                                     PM reads     │   │
└───────────────────┬─────────────────────────────┘   │
                    │                                  │
                    │ Flows 1, 2, 4                    │
                    ▼                                  │
┌─────────────────────────────────────────────────┐   │
│               AGENT COGNITION                    │   │
│  (role prompts, pulse, execution strategies)     │   │
│                                                  │   │
│  Flow 1: Contributor self-assessment in output   │   │
│  Flow 2: PM reads contributor assessments        │   │
│  Flow 4: Contributors read PM assessment    ─────┘   │
└──────────────────────────────────────────────────────┘
```

1. **Cognition → Filesystem (Flow 1)**: Contributors write self-assessments to `memory/self_assessment.md` after each run. Rolling history (5 recent).
2. **Filesystem → Cognition (Flow 2)**: PM reads contributor self-assessments during its pulse. Trajectory data informs steering.
3. **Conversation → Filesystem (Flow 3)**: Agents persist durable directives from chat to `memory/directives.md`. PM persists decisions to `memory/decisions.md`.
4. **Filesystem → Conversation (Flow 4)**: Contributors read PM's `project_assessment.md` during execution. They know the project's constraint layer.

---

## Contributor Cognitive Model

Analogous to PM's 5 prerequisite layers, contributors self-assess on 4 dimensions:

1. **Mandate** — what am I supposed to contribute? (PROJECT.md + PM brief)
2. **Domain Fitness** — does my scope/context cover the mandate?
3. **Context Currency** — is my input fresh and substantial enough?
4. **Output Confidence** — how well does this output address the mandate?

Assessment is produced as a `## Contributor Assessment` block in the agent's output, parsed and stripped before delivery, then appended to the rolling history.

---

## Design Decisions

### D1: Self-Assessment Semantics — Rolling History

Contributor `self_assessment.md` uses append semantics (5 most recent, newest first). PM assessment uses overwrite. Asymmetry is intentional: contributor assessments are evidence PM accumulates (trajectory); PM assessment is a directive contributors consume (snapshot).

### D2: Initialization — Seed at Scaffold Time

Cognitive files are seeded at creation time with explicit "not yet assessed" state. This gives PM clear signal on first pulse — "not yet assessed" ≠ "assessed as low confidence" ≠ "legacy agent." CRUD is clean: delete agent → workspace goes with it.

### D3: Assessment Format — Structured Markdown

Contributors use markdown with bold field names (`**Mandate**: ...`) — human-readable, regex-parseable for future UI. PM uses JSON (already implemented). Asymmetry avoids LLM compliance problems with JSON across diverse contributor roles.

### D4: Surfacing — Design for Future Cognitive Dashboard

Cognitive files are structured for future UI parsing. A Phase 6 "situation room" would surface PM constraint layers, contributor confidence trajectories, and flow activity. Meeting room conversation must NOT be a limiting factor in what we surface. Not scoped in this ADR.

---

## Workspace Files

### Agent workspace additions (`/agents/{slug}/memory/`)

| File | Semantics | Written by | Read by |
|------|-----------|-----------|---------|
| `self_assessment.md` | Rolling append, 5 recent | Agent after each run | PM during pulse, agent (last entry) |
| `directives.md` | Append | Agent-via-chat (WriteWorkspace) | Agent during headless run |

### Project workspace additions (`/projects/{slug}/memory/`)

| File | Semantics | Written by | Read by |
|------|-----------|-----------|---------|
| `project_assessment.md` | Overwrite | PM after each pulse | Contributors during headless run |
| `decisions.md` | Append | PM-via-chat (WriteWorkspace) | All project members |

---

## Implementation Phases

### Phase 0: Initialization Infrastructure
Seed cognitive files at scaffold/creation time. `agent_creation.py`, `project_registry.py`.

### Phase 1: Contributor Self-Assessment
mandate_context injection into 6 role prompts. Assessment extraction, stripping, rolling write in execution pipeline. `agent_pipeline.py`, `agent_execution.py`.

### Phase 2: PM Context Enrichment
PM reads contributor self-assessments + pulse metadata in `_load_pm_project_context()`. `agent_execution.py`.

### Phase 3: Chat Directive Persistence
Update CONTRIBUTOR_CHAT_PROMPT v3.0 and PM_CHAT_PROMPT v4.0 with WriteWorkspace guidance. `chat_agent.py`.

### Phase 4: Cross-Agent Assessment Visibility
Contributors read PM's project_assessment.md via `load_context()`. `workspace.py`, `agent_pipeline.py`.

### Phase 5: Documentation
This ADR + FOUNDATIONS.md + workspace-conventions.md + agent-framework.md + agent-execution-model.md + CLAUDE.md + CHANGELOG + design docs + feature docs.

### Phase 6: Cognitive Dashboard (Future)
Situation room view surfacing agent cognitive state. Not scoped here.

**Execution order**: Phase 0 + Phase 3 in parallel → Phase 1 → Phase 2 → Phase 4 → Phase 5.

---

## Relationship to FOUNDATIONS.md

| Axiom | How ADR-128 extends it |
|-------|----------------------|
| Axiom 2 (Recursive Perception) | Three intelligence substrates (conversation, filesystem, cognition) are formalized as peer perception layers. Four flows keep them coherent. |
| Axiom 3 (Developing Entities) | Cognitive files are developmental infrastructure — agents accumulate self-awareness (rolling assessments), not just outputs. |
| Axiom 4 (Accumulated Attention) | The coherence loop compounds: PM reads assessments → writes briefs → contributors read briefs → produce better output → assessments improve → PM steers less. |

---

## References

- [FOUNDATIONS.md](../architecture/FOUNDATIONS.md) — Axioms 2, 3, 4
- [workspace-conventions.md](../architecture/workspace-conventions.md) — file paths and semantics
- [agent-framework.md](../architecture/agent-framework.md) — cognitive architecture section
- [agent-execution-model.md](../architecture/agent-execution-model.md) — pipeline with assessment extraction
- [ADR-121](ADR-121-pm-intelligence-director.md) — PM intelligence model (prerequisite)
- [ADR-126](ADR-126-agent-pulse.md) — pulse model (prerequisite)
