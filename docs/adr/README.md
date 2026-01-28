# Architecture Decision Records

ADRs document significant architectural decisions made during development.

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](ADR-001-memory-simplicity.md) | Keep Memory Simple for MVP | Accepted | 2026-01-28 |

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
