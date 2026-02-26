# Context Engineering Scorecard: YARNNN vs Agent Skills Framework

**Date**: 2026-02-26
**Source**: [Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) (10.7k stars, MIT)
**Method**: Cross-analysis of 8 framework skills against YARNNN codebase (ADRs, agent code, primitives, sync pipeline)

---

## Overview

The Agent Skills for Context Engineering repo codifies 13 skills across four categories (Foundational, Architectural, Operational, Development) representing community consensus on production agent architecture. This document maps each skill's core principles against YARNNN's current implementation, scores alignment, and identifies where YARNNN leads, matches, or lags the framework.

**Scoring**: 🟢 Strong alignment | 🟡 Partial alignment | 🔴 Gap | ⭐ YARNNN exceeds framework

---

## 1. Context Fundamentals

The framework defines context as "the complete state available to a language model at inference time" and emphasizes treating it as a finite resource with diminishing returns. Core principles: progressive disclosure, informativity over exhaustiveness, position-aware placement.

| Principle | YARNNN Implementation | Score |
|---|---|---|
| **Context as finite resource** | Working memory capped at ~2,000 tokens. Platform content never injected into prompt. Lazy evaluation via Search primitive. | ⭐ |
| **Progressive disclosure** | Four-layer model (Memory → Activity → Context → Work) loads incrementally. TP fetches platform content on demand, not preloaded. | 🟢 |
| **Informativity over exhaustiveness** | Working memory: max 20 known facts, 5 deliverables, 10 activity events, 3 session summaries. Strict caps prevent bloat. | 🟢 |
| **Position-aware placement** | Working memory injected at system prompt level (beginning of context). Recent sessions and system summary at end of working memory block. | 🟡 |
| **File-system-based access** | Not applicable — YARNNN uses DB-backed primitives (Search/Read) rather than filesystem. Functionally equivalent but different mechanism. | 🟢 |

**Assessment**: YARNNN's four-layer model with lazy evaluation is a textbook implementation of progressive disclosure. The framework recommends placing critical info at beginning/end of context; YARNNN places working memory at the system prompt (beginning) which is attention-favored, but doesn't explicitly optimize for recency bias at the end of conversation history.

---

## 2. Context Degradation

The framework identifies five failure modes: lost-in-middle, context poisoning, context distraction, context confusion, and context clash. It notes degradation typically begins at 8K-16K tokens despite larger windows.

| Failure Mode | YARNNN Mitigation | Score |
|---|---|---|
| **Lost-in-middle** | Working memory at system prompt position (attention-favored). Session compaction at 80% utilization (ADR-067). Tool result truncation prevents middle-context bloat. | 🟢 |
| **Context poisoning** | Memory confidence scoring (user_stated > conversation > feedback > pattern). Higher-confidence facts never overwritten by lower sources. | 🟢 |
| **Context distraction** | Platform content excluded from prompt entirely. Only fetched on demand via Search. Max 20 known facts prevents irrelevant accumulation. | ⭐ |
| **Context confusion** | Single TP agent with one system prompt. No conflicting multi-agent instructions. Skill detection injects additive prompts, not replacements. | 🟢 |
| **Context clash** | Memory priority system resolves conflicts (user_stated=10, conversation=5, feedback=3, pattern=1). Temporal validity via `updated_at` on `user_context`. | 🟡 |

**Assessment**: YARNNN's architecture is naturally resistant to most degradation patterns because it keeps the context window lean. The biggest vulnerability is context clash — the `user_context` table tracks `updated_at` but doesn't implement the framework's recommended temporal validity intervals (`valid_from` / `valid_until`). Stale facts could persist if the user's situation changes without explicit correction.

---

## 3. Context Compression

The framework describes three approaches (anchored iterative, opaque, regenerative) and emphasizes measuring tokens-per-task rather than tokens-per-request. It flags artifact trail as the universal weakness.

| Strategy | YARNNN Implementation | Score |
|---|---|---|
| **Compaction trigger** | 80% of 50K budget (40K threshold) triggers in-session compaction (ADR-067). | 🟢 |
| **Anchored iterative summarization** | Session compaction generates summary block prepended as assistant content. Existing compaction reused (not regenerated). | 🟢 |
| **Structured summary sections** | Nightly session summaries are 2-4 sentence prose. No structured sections (intent, files modified, decisions, next steps). | 🟡 |
| **Artifact trail** | No explicit file/artifact tracking in compression. Tool result history lost on compaction. | 🔴 |
| **Tokens-per-task optimization** | Not measured. No metrics on total tokens from task start to completion. | 🔴 |
| **Probe-based evaluation** | No compression quality evaluation framework. | 🔴 |

**Assessment**: YARNNN implements the right compaction mechanics but lacks the framework's quality measurement. The artifact trail gap is significant — when TP compacts a long session, the trail of which platform content was searched, which deliverables were referenced, and what tool outputs were produced gets compressed into generic prose. The framework specifically warns this is the universal weakness and recommends separate artifact indices.

---

## 4. Memory Systems

The framework compares production memory architectures (Mem0, Zep, Letta, LangMem, filesystem) and defines five memory layers: working, short-term, long-term, entity, temporal KG.

| Layer | YARNNN Implementation | Score |
|---|---|---|
| **Working memory** | `build_working_memory()` injects ~2K tokens at system prompt. Profile, preferences, known facts, deliverables, platforms, sessions, system summary. | 🟢 |
| **Short-term (session)** | Message history in `chat_messages`. Compaction at 80%. Session summaries bridge sessions. | 🟢 |
| **Long-term (cross-session)** | `user_context` table with confidence scoring. Nightly extraction from conversations, feedback, patterns. | 🟢 |
| **Entity memory** | No entity registry. Facts stored as flat key-value pairs (`fact:*`). No entity relationships or graph structure. | 🟡 |
| **Temporal KG** | No temporal validity intervals. `updated_at` tracks last write but not validity windows. No `valid_from` / `valid_until`. | 🔴 |
| **Retrieval strategy** | Text search (ILIKE) + pgvector semantic search on `platform_content`. No graph traversal or entity-based retrieval. | 🟡 |
| **Consolidation** | Nightly memory extraction with confidence-based priority resolution. No explicit invalidation strategy — facts accumulate. | 🟡 |

**Assessment**: YARNNN's memory system aligns with the framework's recommendation to "start simple, add complexity only when retrieval fails." The `user_context` key-value model with confidence scoring is a pragmatic Level 2 (vector store equivalent) in the framework's progression. The framework's benchmark data shows simple filesystem approaches (74% LoCoMo) outperform complex systems (Mem0 at 68.5%), which validates YARNNN's approach. However, temporal validity is a real gap — the framework shows Zep's temporal KG achieves 94.8% DMR accuracy vs ~60-70% for vector baselines, suggesting YARNNN's flat model may struggle with facts that change over time.

---

## 5. Tool Design

The framework emphasizes the consolidation principle ("if engineers can't choose the right tool, agents can't either"), minimal architectures, and error messages designed for agent recovery.

| Principle | YARNNN Implementation | Score |
|---|---|---|
| **Consolidation principle** | Seven primitives (Search, Read, List, Write, Edit, Execute, Todo) cover all operations. Clean separation with no overlapping tools. | ⭐ |
| **Tool count** | 7 core primitives + platform-specific tools. Well within the framework's 10-20 recommendation. | 🟢 |
| **Description quality** | Primitives have detailed descriptions with scope enums, usage patterns, and examples. ADR-065 provides explicit access order rules. | 🟢 |
| **Response format optimization** | Tool result truncation with configurable limits (`max_items`, `max_content_len`, `max_depth`). Different limits for platform vs standard tools. | 🟢 |
| **Error recovery design** | Not assessed in detail but `_truncate_tool_result()` indicates awareness. Search returns empty → TP surfaces to user. | 🟡 |
| **Architectural reduction** | ADR-076 eliminated MCP gateway in favor of direct API clients. ADR-048 removed redundant platform.send/search from Execute. Continuous simplification. | ⭐ |

**Assessment**: YARNNN's primitive-based tool design is one of its strongest context engineering features. The seven-primitive model with scope-based Search is exactly the consolidation the framework advocates. The progression from MCP gateway (ADR-050) → direct clients (ADR-076) → removing redundant actions (ADR-048) shows an architectural reduction trajectory that aligns with the framework's evidence that "minimal architectures often outperform sophisticated multi-tool systems."

---

## 6. Multi-Agent Patterns

The framework describes three patterns (supervisor/orchestrator, peer-to-peer, hierarchical) with context isolation as the primary design principle.

| Pattern | YARNNN Implementation | Score |
|---|---|---|
| **Architecture choice** | Single-agent (TP) with async backend orchestration. No multi-agent loop. | 🟡 |
| **Context isolation** | Four independent scheduled jobs share data via DB tables, not context passing. Each operates in clean context. | ⭐ |
| **Headless TP mode** | Deliverable execution reuses TP agent in non-streaming mode. Same primitives, different behavioral constraints. | 🟢 |
| **Coordination** | Pure data dependency through shared tables. No inter-job calling. Platform sync → platform_content → signal processing → deliverables. | 🟢 |
| **Telephone game avoidance** | Single agent means no supervisor paraphrasing. Deliverable output goes directly to user. | ⭐ |

**Assessment**: YARNNN sidesteps multi-agent complexity entirely by using a single TP agent with async backend orchestration. This is arguably superior to the framework's multi-agent patterns for YARNNN's use case. The framework warns about supervisor bottlenecks, telephone game problems, and coordination overhead — none of which apply. The four independent scheduled jobs achieve context isolation through data dependency (shared tables) without any of the multi-agent failure modes. The framework's own data shows token usage explains 80% of performance variance, and YARNNN's single-agent model minimizes tokens by avoiding inter-agent communication entirely.

---

## 7. Context Optimization

The framework describes four strategies: compaction, observation masking, KV-cache optimization, and context partitioning.

| Strategy | YARNNN Implementation | Score |
|---|---|---|
| **Compaction** | In-session compaction at 80% (ADR-067). Nightly session summaries. Incremental merge (reuse existing compaction). | 🟢 |
| **Observation masking** | Tool result truncation (`max_items=5, max_content_len=200`). Platform tools get higher limits. Search returns snippets with refs for downstream Read. | 🟢 |
| **KV-cache optimization** | Not implemented at application level. Relies on Anthropic API's internal caching. | 🟡 |
| **Context partitioning** | Async jobs partition work across independent processes. TP handles user interaction; scheduler handles background execution. | 🟢 |
| **Token budget monitoring** | No explicit token counting during sessions. Compaction trigger is based on message count heuristic, not actual token measurement. | 🟡 |

**Assessment**: YARNNN implements 3 of 4 optimization strategies effectively. The KV-cache gap is low-priority since Anthropic's API handles this server-side with prompt caching. The more actionable gap is explicit token budget monitoring — the framework recommends tracking actual token usage during development and triggering compaction based on measured utilization rather than heuristics.

---

## Summary Scorecard

| Skill Area | ⭐ Exceeds | 🟢 Strong | 🟡 Partial | 🔴 Gap |
|---|---|---|---|---|
| Context Fundamentals | 1 | 3 | 1 | 0 |
| Context Degradation | 1 | 3 | 1 | 0 |
| Context Compression | 0 | 2 | 1 | 3 |
| Memory Systems | 0 | 3 | 3 | 1 |
| Tool Design | 2 | 2 | 1 | 0 |
| Multi-Agent Patterns | 2 | 2 | 1 | 0 |
| Context Optimization | 0 | 3 | 2 | 0 |
| **Totals** | **6** | **18** | **10** | **4** |

**Overall**: YARNNN scores strongly on fundamentals, tool design, and architectural patterns. Primary gaps cluster around compression quality measurement and temporal memory validity.

---

## Where YARNNN Leads the Framework

1. **Lazy evaluation architecture**: The framework recommends progressive disclosure; YARNNN implements a more aggressive variant where platform content is *never* in the prompt. This is a stronger position than the framework's examples.

2. **Architectural reduction trajectory**: ADR-050 → ADR-076 → ADR-048 shows continuous simplification that exceeds the framework's static recommendations.

3. **Unified content layer with selective retention**: The `retained` flag + TTL model (ADR-072) is a novel accumulation strategy not covered by the framework. Content starts ephemeral and gets promoted to permanent only when referenced by execution — this is an elegant signal-driven retention model.

4. **Single-agent with async orchestration**: Avoids all multi-agent failure modes while achieving the framework's context isolation goals through data dependency.

5. **Confidence-scored memory**: The four-tier priority system (user_stated > conversation > feedback > pattern) provides more nuanced conflict resolution than the framework's temporal approach alone.
