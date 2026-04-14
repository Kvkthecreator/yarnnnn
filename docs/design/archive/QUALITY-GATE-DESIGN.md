# Quality Gate Design — ADR-137 Phase 3

> **Status**: Designed, pending implementation
> **Date**: 2026-03-24

## Two-Tier Quality Gate

### Tier 1: Structural (Haiku, every cycle, ~$0.001)
- Success criteria checklist (required sections present?)
- Output spec structure matching (components in correct order?)
- Competitor/entity coverage (named entities from criteria found?)
- Word count / depth adequate
- Non-redundancy (similarity vs last delivery — skip if >85% same)
- Source citation presence

### Tier 2: Qualitative (Sonnet, every Nth cycle, ~$0.03)
- Analysis depth (insight vs summarization)
- Actionability (specific recommendations?)
- Audience tone match
- Logical consistency
- Source grounding (claims backed by evidence?)

### Frequency
- Weekly project: structural every week, qualitative monthly (every 4th)
- Daily project: structural daily, qualitative weekly (every 7th)

### On Failure
- Structural fail → steer contributor with specific feedback → retry (max 2)
- Qualitative fail → note in reflection → adjust briefs for next cycle
- Both fail → skip delivery, PM announces issue to chat

## Quality Dimensions

1. **Relevance** — addresses the objective
2. **Specificity** — real names, numbers, dates (not generic)
3. **Freshness** — information is current
4. **Completeness** — covers success criteria requirements
5. **Actionability** — user can act on findings
6. **Structure** — matches output spec
7. **Non-redundancy** — meaningfully different from last delivery
8. **Source grounding** — claims backed by evidence
