# Architecture Decision Records

ADRs document significant architectural decisions made during development.

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](ADR-001-memory-simplicity.md) | Keep Memory Simple for MVP | Accepted | 2026-01-28 |
| [002](ADR-002-scheduling-first-class.md) | Scheduling as First-Class Feature | Accepted | 2026-01-28 |
| [003](ADR-003-context-memory-architecture.md) | Context & Memory Architecture | Superseded by 005 | 2025-01-29 |
| [004](ADR-004-two-layer-memory-architecture.md) | Two-Layer Memory Architecture | Superseded by 005 | 2025-01-29 |
| [005](ADR-005-unified-memory-with-embeddings.md) | **Unified Memory with Embeddings** | **Implemented** | 2026-01-29 |
| [006](ADR-006-session-message-architecture.md) | Session and Message Architecture | Implemented | 2026-01-29 |
| [007](ADR-007-thinking-partner-project-authority.md) | Thinking Partner Project Authority | Implemented | 2026-01-29 |
| [008](ADR-008-document-pipeline.md) | Document Pipeline Architecture | Implemented | 2026-01-29 |
| [009](ADR-009-work-agent-orchestration.md) | Work and Agent Orchestration | Implemented (Phase 1) | 2026-01-30 |
| [010](ADR-010-thinking-partner-architecture.md) | Thinking Partner as Primary Interface | Draft | 2026-01-30 |
| [011](ADR-011-frontend-navigation-architecture.md) | Frontend Navigation Architecture | Implemented | 2026-01-30 |
| [013](ADR-013-conversation-plus-surfaces.md) | Conversation + Surfaces Architecture | Implemented | 2026-02-01 |
| [014](ADR-014-topbar-minimal-chrome.md) | TopBar Minimal Chrome | Implemented | 2026-02-01 |
| [015](ADR-015-unified-context-model.md) | Unified Context Model | Implemented | 2026-02-01 |
| [016](ADR-016-work-agents-and-artifacts.md) | Work Agents and Artifacts | Draft | 2026-01-30 |
| [017](ADR-017-unified-work-model.md) | Unified Work Model | Implemented | 2026-01-31 |
| [018](ADR-018-recurring-deliverables.md) | Recurring Deliverables Product Pivot | Accepted | 2026-02-01 |
| [019](ADR-019-deliverable-types.md) | Deliverable Types System | Proposed | 2026-02-02 |
| [020](ADR-020-deliverable-centric-chat.md) | Deliverable-Centric Chat | Implemented | 2026-02-02 |
| [021](ADR-021-review-first-supervision-ux.md) | Review-First Supervision UX | Implemented | 2026-02-02 |
| [022](ADR-022-tab-based-supervision-architecture.md) | Tab-Based Supervision Architecture | Draft | 2026-02-02 |
| [023](ADR-023-supervisor-desk-architecture.md) | Supervisor Desk Architecture | Implemented | 2026-02-03 |
| [024](ADR-024-context-classification-layer.md) | Context Classification Layer | Implemented | 2026-02-04 |
| [025](ADR-025-claude-code-agentic-alignment.md) | **Claude Code Agentic Alignment** | **Proposed** | 2026-02-05 |

## Template

```markdown
# ADR-NNN: Title

**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXX
**Date**: YYYY-MM-DD
**Authors**: [names]

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?

### Positive
- ...

### Negative
- ...

### Neutral
- ...

## Alternatives Considered

What other options were evaluated?

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| ... | ... | ... | ... |

## References

- Links to related docs, issues, or external resources
```

## When to Write an ADR

- Choosing between competing libraries or frameworks
- Changing established patterns
- Making trade-offs with long-term implications
- Decisions that would be hard to reverse
- Anything you'd want to explain to a new team member

## Numbering

- Sequential: 001, 002, 003...
- Don't reuse numbers even if an ADR is deprecated
- Reference superseding ADRs in the status line
