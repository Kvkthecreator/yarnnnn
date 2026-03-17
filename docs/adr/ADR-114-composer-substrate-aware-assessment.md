# ADR-114: Composer Substrate-Aware Assessment

**Status:** Phases 1-3 Implemented, Phase 4 Proposed
**Date:** 2026-03-16
**Builds on:** ADR-111 (Agent Composer), ADR-107 (Knowledge Filesystem), FOUNDATIONS.md Axiom 2 (Recursive Perception)

## Context

ADR-111 shipped a working Composer: heartbeat fires, coverage gaps are detected, lifecycle decisions execute, LLM assessment runs when heuristics warrant it. The system works.

But the Composer's assessment substrate is **platform-metadata-centric**, not **recursive-substrate-aware**. Every signal it reasons over today is about platforms, agents, and runs — not the accumulated knowledge those agents have produced.

### What Composer Sees Today (v1.0)

```
heartbeat_data_query() produces:
├── connected_platforms          ← platform connections
├── agents (active/paused)       ← agent metadata
├── skills_present               ← set of skill types
├── platforms_with_digest        ← source coverage
├── stale_agents                 ← run timing
├── maturity signals             ← runs, approval_rate, edit_trend
├── feedback                     ← count of recent feedback events
└── tier limits                  ← can_create boolean
```

Every field is metadata *about* the system, not the system's accumulated knowledge itself. The LLM prompt (`_build_composer_prompt`) passes this same metadata. The heuristics (`should_composer_act`) gate on platform count, skill coverage, run counts, and approval rates.

### What Composer Should See (FOUNDATIONS Axiom 2)

FOUNDATIONS.md establishes that the perception substrate is recursive — the enduring value is in accumulated `/knowledge/` files, workspace state, and reflexive feedback, not raw platform connections. ADR-107 moved agent outputs from flat `platform_content` rows to structured `/knowledge/` files with content classes, versioning, and provenance.

For Composer to fulfill its doctrinal role as "TP's meta-cognitive judgment layer" (FOUNDATIONS Axiom 5), it should reason over:

1. **Knowledge corpus signals** — counts and classes of `/knowledge/` artifacts (digests, analyses, research, briefs, insights)
2. **Growth patterns** — are digests accumulating? Is research being produced? Are insights emerging from synthesis?
3. **Recency/staleness of knowledge** — not just "when did the agent last run" but "is the knowledge corpus fresh?"
4. **Uploaded documents / user contributions** — files the user placed in workspace
5. **Recurring themes** — topics that appear across multiple agents' outputs or TP conversations
6. **Cross-agent dependence chains** — which agents consume other agents' outputs?
7. **Knowledge gaps** — domains well-covered by digests but lacking analysis; platforms syncing but no knowledge being extracted

### Why This Matters

Without substrate awareness, Composer can only make **structural decisions** (does a digest exist for Slack?) but not **substantive decisions** (the user's workspace has 50 digests but zero analyses — the system is perceiving but not reasoning). The progression from Phase 6 (Compose) to Phase 7 (Compound) in VALUE-CHAIN.md requires this: second-order agents that reason over first-order outputs.

The LLM already demonstrated this gap: when asked about cross_platform_opportunity, it correctly observed that digests are nascent. But it made that judgment from run counts and approval rates — not from reading the actual knowledge produced. A substrate-aware Composer would see "4 digest runs produced 4 `/knowledge/digests/` files covering Slack channels #daily-work, #fyi, #vc and Notion pages about frontend development" and make a far more informed decision about what synthesis agent would be valuable.

## Decision

### Principle: Composer Prompt Versioning

Composer's system prompt and assessment data model are now **versioned artifacts** with the same rigor as the Orchestrator prompt. Changes require:

1. Version bump in `COMPOSER_SYSTEM_PROMPT` header comment
2. Entry in `api/prompts/CHANGELOG.md` under Composer section
3. Expected behavior change documented

**Rationale:** Every word in the Composer prompt now dictates autonomous orchestration decisions. A single heuristic change can create duplicate agents (as we saw with coverage detection) or suppress valuable scaffolding. The prompt IS the product for this layer.

### Phase 1: Knowledge Corpus Signals (Data Query Extension)

Extend `heartbeat_data_query()` to include workspace/knowledge signals alongside existing platform metadata:

```python
# New signals added to assessment dict
"knowledge": {
    "total_files": 12,           # workspace_files under /knowledge/
    "by_class": {
        "digests": 8,            # /knowledge/digests/
        "analyses": 0,           # /knowledge/analyses/
        "research": 2,           # /knowledge/research/
        "briefs": 0,             # /knowledge/briefs/
        "insights": 0,           # /knowledge/insights/
    },
    "latest_at": "2026-03-16T09:00:00Z",
    "agents_producing": ["Slack Recap", "Notion Summary"],
    "agents_consuming": [],      # agents that read /knowledge/
},
"workspace": {
    "user_files": 3,             # non-agent, non-knowledge files uploaded by user
    "agent_files": 5,            # /agents/*/AGENT.md, thesis.md, memory/
},
```

**Cost model:** Single `workspace_files` count query with path prefix grouping. Zero LLM cost. Same cheap-first principle.

### Phase 2: Substrate-Aware Heuristics

New `should_composer_act()` triggers based on knowledge signals:

| Trigger | Condition | Action |
|---------|-----------|--------|
| `knowledge_gap_analysis` | 10+ digest files, 0 analysis files | Propose analyst agent |
| `knowledge_gap_research` | User uploaded docs OR topics repeated in digests, 0 research files | Propose research agent |
| `stale_knowledge` | Most recent /knowledge/ file >7 days old, agents active | Investigate — agents running but not producing knowledge |
| `knowledge_asymmetry` | One platform producing 80%+ of knowledge, others idle | Suggest rebalancing or investigation |
| `user_substrate_signal` | User uploaded files to workspace | Assess whether a research or analysis agent would serve these files |

### Phase 3: LLM Prompt Substrate Injection

Update `_build_composer_prompt()` to include knowledge corpus summary alongside platform metadata:

```
## Knowledge Corpus
- Digests: 8 files (latest: 2 hours ago)
- Analyses: 0 files
- Research: 2 files (latest: 3 days ago)
- Briefs: 0 files
- Insights: 0 files
- User-uploaded files: 3

## Knowledge Production
- Slack Recap → produces digests (2/day)
- Notion Summary → produces digests (1/day)
- No agent consumes /knowledge/ yet
```

This gives the LLM the signal to reason about *what the system has learned*, not just *what infrastructure exists*.

### Phase 4: Composer Prompt v2.0

Update `COMPOSER_SYSTEM_PROMPT` principles:

```diff
- You assess the user's connected platforms, existing agents, and work patterns
- to identify gaps in their agent workforce.
+ You assess the user's knowledge substrate — accumulated agent outputs,
+ platform connections, workspace files, and work patterns — to identify gaps
+ in their cognitive workforce.

  ## Principles
- - Start with highest-value agents: platform digests before cross-platform
-   synthesis before research
+ - Start with highest-value agents: digests (perception) → synthesis
+   (cross-cutting themes) → analysis (deep reasoning) → research (external
+   knowledge). Each layer builds on accumulated outputs from the layer below.
+ - Reason over the knowledge corpus, not just platform metadata. An agent that
+   runs but produces no knowledge is underperforming even if approval is high.
```

## Implementation Notes

- **Phase 1 is zero-cost:** Single DB query on `workspace_files` with path-prefix counts
- **Phase 2 adds no LLM calls:** New heuristics are pure logic, same as existing `should_composer_act()`
- **Phase 3/4 are prompt changes only:** Same Haiku model, same token budget, richer context
- **Backwards compatible:** All existing heuristics and lifecycle logic remain unchanged. New signals are additive.
- **Stale doc cleanup:** FOUNDATIONS.md Axiom 2 references `platform_content (platform="yarnnn")` — update to reference `/knowledge/` filesystem per ADR-107

### Implementation Status (2026-03-16)

**Phases 1-3 implemented** in `api/services/composer.py`:
- Phase 1: `heartbeat_data_query()` step 9 queries `/knowledge/` files by content class. Returns `knowledge.by_class`, `knowledge.latest_at`, `knowledge.agents_producing`. Version files excluded via regex.
- Phase 2: Three heuristics in `should_composer_act()`: `knowledge_gap_analysis` (10+ digests, 0 analyses), `stale_knowledge` (>7d), `knowledge_asymmetry` (80%+ digests). All route to LLM assessment.
- Phase 3: `_build_composer_prompt()` includes "Knowledge Corpus" section. LLM sees accumulated outputs.
- `knowledge_gap_research` deferred (needs keyword extraction — Open Question 2).
- `agents_consuming` deferred (needs provenance tracking — Open Question 3).
- Event-driven heartbeat also shipped (separate commit): `maybe_trigger_heartbeat()` fires after agent delivery and platform sync.

**Phase 4 partially addressed by ADR-115** — `COMPOSER_SYSTEM_PROMPT` v1.2 reframed from "assess platforms and agents" to "assess knowledge substrate" with workspace-density-aware eagerness principles. Full v2.0 prompt rewrite deferred until density model proves out in production.

## Relationship to Existing Architecture

| Component | Current | After ADR-114 |
|-----------|---------|---------------|
| `heartbeat_data_query()` | Platform + agent metadata only | + knowledge corpus signals |
| `should_composer_act()` | Platform coverage, run counts, maturity | + knowledge gap detection |
| `_build_composer_prompt()` | Platform/agent summary | + knowledge corpus summary |
| `COMPOSER_SYSTEM_PROMPT` | "assess platforms and agents" | "assess knowledge substrate" |
| Agent execution | Writes to `/knowledge/` (ADR-107) | Unchanged |
| `QueryKnowledge` primitive | Agents search `/knowledge/` | Unchanged |

Composer does NOT need direct platform access. It reads the *accumulated results* of platform perception — which is exactly the recursive model FOUNDATIONS Axiom 2 describes.

## Open Questions

1. **Frequency of knowledge query:** Should the workspace_files count be cached per-heartbeat, or is the query cheap enough to run every cycle?
2. **Theme extraction:** Phase 2 mentions "topics repeated in digests" — this requires either keyword extraction from recent /knowledge/ files or a lightweight embedding query. Defer to Phase 3?
3. **Cross-agent consumption tracking:** How do we know which agents read /knowledge/ vs raw platform_content? Need provenance tracking in workspace reads. **CRITICAL — resolved by [ADR-116](ADR-116-agent-identity-inter-agent-knowledge.md) Phase 5:** consumption log tracks agent-to-agent references, Composer builds dependency graph for supply chain reasoning (orphaned producers, missing producers, stale dependencies).

## References

- ADR-107: Knowledge Filesystem Architecture
- ADR-111: Agent Composer
- FOUNDATIONS.md: Axioms 2 (Recursive Perception) and 5 (TP's Compositional Capability)
- VALUE-CHAIN.md: Phase 7 (Compound)
