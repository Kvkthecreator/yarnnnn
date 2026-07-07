# Continuity Audit Spec

Spec for the Reviewer's continuity check. Used at every `pre-ship-audit` recurrence fire and as a sub-check inside `corpus-coherence-check`.

## Purpose

Detect unacknowledged contradictions between a draft and prior published corpus. Specifically catches:
1. Direct factual contradiction (draft asserts X; prior published piece asserted ¬X).
2. Position drift without acknowledgment (draft takes stance Y; operator's prior stance was Z; draft does not bridge).
3. Thread abandonment (draft introduces a continuation of a prior thread but contradicts the thread's prior direction).

## What "continuity break" means

Continuity break is **structural**, not stylistic. The operator's voice may evolve; the operator's positions may evolve. What matters is whether the evolution is *acknowledged*. Examples:

**Continuity-preserving (no break):**
- *"I previously argued that strong types prevent bugs. Six months of working with TypeScript at scale has changed my view; here's why."*
- *"In [last newsletter], I called X overrated. Recent product launches have changed the picture; here's an updated assessment."*

**Continuity-breaking (flag):**
- *"Strong types prevent bugs."* (when 4 weeks ago the operator argued strong types are theatrical and the new piece doesn't acknowledge the prior stance)
- *"X is overrated."* → *"X is the most important development of the year."* (without bridge)

## Inputs

- The draft content at `/workspace/operation/authored/{piece-slug}/content.md`.
- The corpus: all published pieces in `/workspace/operation/authored/{*}/content.md` where status is `published`.
- Optional: revision lineage per ADR-209 (`ListRevisions` for each piece) to understand operator's evolution within a piece.

## Output structure

The Reviewer writes findings to `/workspace/agents/alpha-author/judgment_log.md` plus structured continuity-state to the draft's profile.md `Continuity Threads` section.

Each audit result includes:

```yaml
piece_slug: <slug>
audit_timestamp: 2026-05-15T14:32:00Z
continuity_check: pass | fail | mixed
threads_extended:
  - prior_piece: <slug>
    excerpt: "..."
    extension_type: continuation | refinement | reversal-acknowledged | reversal-unacknowledged
contradictions_detected:
  - prior_piece: <slug>
    prior_position: "..."
    draft_position: "..."
    bridge_present: true | false
    suggested_bridge: <if bridge_present false> proposed acknowledgment wording for operator
overall_verdict: approve | defer | reject
defer_directive: <if defer> specific bridge or acknowledgment needed
```

## How to compute "thread extends from"

The Reviewer reads the draft and identifies references to prior pieces in three ways:
1. **Explicit link**: draft hyperlinks or names a prior piece.
2. **Topical match**: draft addresses a topic the operator has published on within the last 90 days.
3. **Position match**: draft takes a position that overlaps materially with a prior position.

For (2) and (3), the Reviewer surfaces the connection even when not explicitly linked — operator may choose to add the link or to acknowledge the connection inline.

## Relationship to entity-continuity

Continuity-audit (this spec) covers **text-level** contradiction — draft contradicts a prior piece's textual claim. **Entity-continuity** (see `/workspace/operation/specs/entity-continuity.md`) is one layer below — draft contradicts an entity's `What's been established` canonical-facts section in `entities/{slug}.md`, even if the draft never explicitly references the prior text.

The two compose at every `pre-ship-audit`:

1. **Entity-continuity runs first** when entity references are detected in the draft. The Reviewer reads matching `entities/{slug}.md` files and audits the draft's treatment against `What's been established`. Hard reject on unbridged established-fact contradiction. Defer on implicit close of an `What's open` question.
2. **Continuity-audit (this spec) runs after** for cross-piece textual continuity — does the draft contradict prior published pieces' positions, regardless of whether named entities are involved?

The Reviewer surfaces findings under distinct `audit_type` values (`continuity-audit` vs `entity-continuity`) in `judgment_log.md` so the operator can see which layer fired. Both can fire on the same draft.

## Quality criteria

- Reviewer does NOT rewrite contradictions — only locates them and proposes bridge wording for operator's authoring choice.
- For each contradiction, both excerpts (prior and draft) are quoted verbatim. No paraphrase.
- When the operator's prior position is in revision lineage (not yet published, or revised post-publication), the Reviewer references the most recent published revision.
- Bridge suggestions are optional — the Reviewer's role is to surface, not to author. Operator may write their own bridge or argue the contradiction is intentional (in which case operator declares `continuity_override: true` in piece profile.md with reasoning).
- Entity-continuity findings (when applicable) cite the entity slug + the specific `What's been established` line being contradicted, per `entity-continuity.md` spec. No vague "this contradicts the canonical Sarah" — the Reviewer cites the entity file + line.
