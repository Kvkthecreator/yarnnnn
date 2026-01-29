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
