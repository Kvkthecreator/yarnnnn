# Context Engineering: Gaps, Opportunities & Recommendations

**Date**: 2026-02-26
**Companion to**: `context-engineering-scorecard-2026-02-26.md`
**Source**: Cross-analysis of [Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) against YARNNN codebase

---

## Priority 1: Compression Quality & Artifact Trail

**The problem**: The framework identifies artifact trail (tracking which files/content were accessed, modified, or produced) as the universal weakness across all compression methods, scoring only 2.2-2.5/5.0. YARNNN's in-session compaction (ADR-067) generates prose summaries that lose the trail of which `platform_content` records were searched, which tool calls were made, and what intermediate results informed decisions.

**Why it matters for YARNNN**: The Thinking Partner handles long sessions where users iterate on deliverables, search across platforms, and make decisions based on specific Slack threads or Gmail messages. When compaction fires at 40K tokens, that provenance trail compresses into generic prose. If the user later asks "which Slack thread had that metric you mentioned?", the compacted context can't answer.

**Recommendation**: Implement a structured compaction format alongside prose summaries. When compaction triggers:

```
<compaction>
  <intent>User refining weekly digest for #engineering team</intent>
  <platform_refs>
    - slack:C01234567:1708900000.123 (thread about deployment metrics)
    - gmail:msg-abc123 (reply from Sarah re: quarterly targets)
  </platform_refs>
  <decisions>
    - Include deployment frequency chart (user approved)
    - Exclude incident count (user said "too negative")
  </decisions>
  <deliverable_state>digest v3 drafted, pending tone adjustment</deliverable_state>
  <next_steps>Apply casual tone, regenerate intro paragraph</next_steps>
</compaction>
```

This is the framework's "anchored iterative" approach with explicit artifact sections. The `platform_refs` section solves the provenance gap without carrying full content forward.

**Effort**: Medium. Modify `memory.generate_session_summary()` and the compaction path in `anthropic.py` to produce structured output. No schema changes needed — store structured compaction in `chat_sessions.compaction_summary` (already exists).

**Related ADR**: ADR-067 Phase 3 (in-session compaction).

---

## Priority 2: Temporal Memory Validity

**The problem**: YARNNN's `user_context` table stores facts as key-value pairs with `updated_at` timestamps but no validity intervals. The framework shows temporal knowledge graphs (Zep) achieve 94.8% accuracy on fact retrieval vs ~60-70% for flat stores, specifically because they model when facts *stop being true*.

**Why it matters for YARNNN**: Users' roles change, they move teams, projects end, preferences shift. A `fact:current_project=Atlas` written six months ago may no longer be true. The confidence system resolves *conflicting* writes but doesn't handle *stale* facts that were never contradicted — they persist indefinitely in working memory, consuming attention budget with potentially outdated information.

**Recommendation**: Add `valid_until` (nullable timestamp) to `user_context`. When the nightly memory extraction writes a new value for an existing key, set `valid_until=NOW()` on the old row rather than overwriting. This preserves history and enables:

1. Working memory builder filters to `valid_until IS NULL` (only current facts)
2. TP can query historical facts: "What project was I on in October?"
3. Consolidation job can flag facts older than 90 days without update for user review

**Effort**: Low-Medium. Schema migration to add `valid_until`. Modify `memory.py` extraction to invalidate-then-insert rather than upsert. Modify `working_memory.py` to filter on validity.

**Related ADR**: ADR-059 (simplified context model), ADR-064 (unified memory service).

---

## Priority 3: Token Budget Observability

**The problem**: The framework emphasizes measuring "tokens-per-task" (total tokens from task start to completion) rather than tokens-per-request, and recommends triggering compaction based on actual token measurement rather than heuristics. YARNNN's compaction trigger appears to be based on message count/length heuristics rather than precise token counting.

**Why it matters for YARNNN**: Without token-level observability, you can't answer: How much does a typical digest generation cost? Is the compaction threshold optimal? Are tool results consuming disproportionate context? The framework reports tool outputs can reach 83.9% of total context — YARNNN's truncation limits may or may not be well-calibrated without measurement.

**Recommendation**: Add lightweight token tracking to the streaming pipeline:

1. Track `prompt_tokens` and `completion_tokens` from Anthropic API responses (already returned in usage metadata)
2. Accumulate per-session totals in `chat_sessions` (add `total_prompt_tokens`, `total_completion_tokens`)
3. Track per-tool-call token contribution (measure tool result size before/after truncation)
4. Dashboard metric: tokens-per-task for deliverable generation, platform search, and general conversation

This data enables evidence-based tuning of truncation limits and compaction thresholds.

**Effort**: Low. Anthropic API already returns usage data. Add columns to `chat_sessions`, accumulate in streaming handler.

**Related ADR**: ADR-043 (streaming process visibility), ADR-072 (TP execution pipeline).

---

## Priority 4: Compression Quality Evaluation

**The problem**: The framework proposes probe-based evaluation for compression quality — functional tests that ask specific questions of compressed context to verify information survival. YARNNN has no mechanism to evaluate whether compaction preserves the right information.

**Why it matters for YARNNN**: Session compaction is a lossy operation. If compression quality degrades silently, users experience TP "forgetting" things discussed earlier in long sessions. This is invisible without measurement.

**Recommendation**: Implement a lightweight probe system for compaction quality:

1. When compaction fires, generate 3-5 probe questions from the truncated content (one LLM call)
2. Test whether the compacted summary can answer those probes (one LLM call)
3. Score and log results to `activity_log` (event_type: `compaction_quality`)
4. Alert if quality drops below threshold (e.g., <60% probe pass rate)

The framework suggests four probe types: recall ("What was the error?"), artifact ("Which files were modified?"), continuation ("What comes next?"), and decision ("Why did we choose X?"). Even implementing just recall + artifact probes would provide signal.

**Effort**: Medium. Requires two additional LLM calls per compaction event. Could be done async after compaction to avoid latency impact.

---

## Priority 5: Error Recovery in Tool Design

**The problem**: The framework emphasizes designing error messages for agent recovery, not just developer debugging. Each error should include what went wrong, how to correct it, and retry guidance. YARNNN's tool primitives handle errors but the recovery guidance aspect isn't fully developed.

**Why it matters for YARNNN**: When Search returns empty results or Read fails on a stale ref, TP needs clear guidance on fallback paths. ADR-065 defines the platform content access order (live tools → cached Search → surface to user), but this logic lives in ADR documentation rather than being encoded in tool error responses.

**Recommendation**: Enhance tool error responses with structured recovery hints:

```python
# Instead of:
{"error": "No results found"}

# Return:
{
  "error": "No platform_content matches for query 'deployment metrics'",
  "recovery": {
    "suggestion": "Try platform_slack_search for live results",
    "alternative": "Broaden query or check connected platforms",
    "freshness_note": "Last Slack sync: 3 hours ago"
  }
}
```

This encodes the ADR-065 access order into the tool responses themselves, making it part of the context rather than relying on system prompt instructions.

**Effort**: Low. Modify primitive return formatting in `api/services/primitives/`.

---

## Priority 6: Memory Consolidation Strategy

**The problem**: The framework recommends periodic memory consolidation with "invalidate but don't discard" semantics. YARNNN's `user_context` accumulates facts over time with confidence scoring, but has no explicit consolidation or review cycle.

**Why it matters for YARNNN**: Over months of use, `user_context` will accumulate hundreds of facts, many potentially outdated. The working memory builder caps at 20 known facts, but the selection criteria for which 20 to include isn't optimized — older, lower-confidence facts may crowd out recent, relevant ones.

**Recommendation**: Implement a monthly consolidation pass:

1. Surface facts with `confidence < 0.5` and `updated_at > 90 days ago` for user review
2. Auto-archive facts with `confidence = 'pattern'` (lowest tier) older than 180 days
3. Merge duplicate/overlapping facts (e.g., `fact:project=Atlas` and `fact:current_project=Atlas`)
4. Present consolidation summary to user: "I noticed some facts about you might be outdated. Want to review?"

**Effort**: Medium. New consolidation job + UI component for review. Pairs well with Priority 2 (temporal validity).

---

## Opportunities: Where YARNNN Can Teach the Framework

These aren't gaps — they're areas where YARNNN's approach is novel and could contribute back to the open-source community.

### 1. Signal-Driven Retention (ADR-072)

The framework's memory systems assume content is either cached or discarded based on TTL. YARNNN's `retained` flag model — where content starts ephemeral and gets promoted to permanent only when referenced by signal processing or deliverable execution — is a novel pattern not covered by any framework skill. This is effectively an "attention-driven retention" model: content that proves useful survives.

**Contribution opportunity**: Document this as a "selective retention" pattern for the framework's memory-systems skill.

### 2. Confidence-Tiered Memory Priority

The framework recommends temporal validity for conflict resolution. YARNNN uses a complementary approach: source-based confidence scoring where `user_stated` (10) always wins over `conversation` (5) over `feedback` (3) over `pattern` (1). This is orthogonal to temporal validity and could be combined.

**Contribution opportunity**: Propose a hybrid conflict resolution model (confidence × recency) for the memory-systems skill.

### 3. Four-Layer Separation with Activity Log

The framework's memory layers (working, short-term, long-term, entity, temporal) are all about user knowledge. YARNNN's Activity layer (ADR-063) is a distinct concept — it tracks system provenance ("what YARNNN has done") separately from user knowledge. This enables a class of questions ("When did you last sync Slack?") that pure knowledge-based memory can't answer.

**Contribution opportunity**: Propose an "operational memory" layer for the framework, distinct from user-knowledge memory.

### 4. Headless Agent Reuse

YARNNN runs the same TP agent in both interactive (streaming) and headless (deliverable execution) modes. The framework discusses multi-agent patterns but doesn't cover single-agent reuse across execution modes. This avoids the framework's "telephone game" problem entirely.

**Contribution opportunity**: Document "modal agent reuse" as an alternative to multi-agent delegation for scheduled work.

---

## Implementation Roadmap

| Priority | Description | Effort | Dependencies | Impact |
|---|---|---|---|---|
| P3 | Token budget observability | Low | None | Enables data-driven decisions for all other priorities |
| P5 | Error recovery in tools | Low | None | Immediate TP behavior improvement |
| P2 | Temporal memory validity | Low-Med | Schema migration | Prevents stale fact accumulation |
| P1 | Structured compaction | Medium | None (uses existing schema) | Preserves provenance across long sessions |
| P4 | Compression quality evaluation | Medium | P1 (structured compaction) | Quality assurance for compaction |
| P6 | Memory consolidation | Medium | P2 (temporal validity) | Long-term memory hygiene |

**Suggested sequence**: P3 → P5 → P2 → P1 → P4 → P6. Start with observability (P3) because it provides the measurement foundation for everything else. P5 is a quick win that immediately improves TP behavior. P2 and P1 are the core architectural improvements. P4 and P6 build on the earlier work.

---

## Sources

- [Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) — Primary framework (MIT, 10.7k stars)
- [Context Fundamentals Skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/skills/context-fundamentals/SKILL.md)
- [Memory Systems Skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/skills/memory-systems/SKILL.md)
- [Context Compression Skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/skills/context-compression/SKILL.md)
- [Tool Design Skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/skills/tool-design/SKILL.md)
- [Multi-Agent Patterns Skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/skills/multi-agent-patterns/SKILL.md)
- [Context Degradation Skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/skills/context-degradation/SKILL.md)
- [Context Optimization Skill](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/skills/context-optimization/SKILL.md)
- YARNNN ADRs: 043, 048, 050, 059, 063, 064, 065, 067, 072, 076, 077
