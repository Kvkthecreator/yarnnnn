# ADR-001: Keep Memory Simple for MVP

**Status**: Accepted
**Date**: 2026-01-28
**Authors**: Claude + KVK

## Context

YARNNN v5 is a fresh rebuild after v4 became over-engineered. Two sibling projects (`yarnnn-app-fullstack` and `chat_companion`) have sophisticated memory/context systems:

**yarnnn-app-fullstack** implements:
- Block state machine (PROPOSED→ACCEPTED→LOCKED→CONSTANT)
- User approval workflows for every block
- Versioning with parent_block_id
- Workspace-scoped cross-basket memory
- Anchor vocabulary for semantic retrieval

**chat_companion** implements:
- Three-tier memory (working/active/core)
- LLM extraction with deduplication
- Importance scoring (0.0-1.0)
- Temporal expiry (expires_at)
- pgvector embeddings for semantic search
- Background async extraction

Both systems are sophisticated but were built to solve problems we haven't validated yet.

## Decision

**Keep the blocks table simple for MVP:**

```sql
blocks (
    id, content, block_type, metadata,
    project_id, created_at, updated_at
)
```

No state machines, no approval workflows, no embeddings, no expiry.

**Rationale:**
1. We don't have users yet - we don't know what memory problems they'll have
2. Agent quality depends on context loading, not memory governance
3. Simple blocks can always be extended; complex schemas are hard to simplify
4. v4's block governance added friction without proven value

## Consequences

### Positive
- Faster to build and iterate
- Simpler mental model for developers
- Easy to add columns later (importance_score, expires_at, embedding)
- Focus stays on core value: context → agents → outputs

### Negative
- No user control over what persists (all blocks are "accepted")
- No deduplication - same content can be added twice
- No semantic search - retrieval is project-scoped only
- No temporal decay - old context treated same as new

### Neutral
- May need migration later if memory refinement is needed
- Pattern learnings from sibling repos are documented for future reference

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| Full state machine | User control, versioning | Complexity, unproven need | Over-engineering for MVP |
| Add importance_score now | Future-proof | Extra column to maintain | YAGNI - add when needed |
| Add pgvector now | Semantic search | Dependency, complexity | No retrieval problems yet |
| Three-tier memory | Temporal awareness | Complex queries | Overkill for project-scoped context |

## When to Revisit

Revisit this decision when:
1. Users report "agent used wrong/outdated context"
2. Projects have 100+ blocks and retrieval quality degrades
3. Cross-project memory becomes a requested feature
4. Semantic search becomes necessary for agent quality

## References

- [ESSENCE.md](../ESSENCE.md) - Domain model specification
- [analysis/MEMORY_PATTERNS.md](../analysis/MEMORY_PATTERNS.md) - Cross-repo analysis
- yarnnn-app-fullstack: `work-platform/api/src/app/memory/blocks/lifecycle.py`
- chat_companion: `api/api/src/app/services/context.py`
