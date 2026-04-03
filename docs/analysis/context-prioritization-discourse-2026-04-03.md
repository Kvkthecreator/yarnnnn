# Context Prioritization & Intelligent Retrieval — Discourse

> **Status**: Discourse (pre-decision). Assessing whether this is ADR-update or new ADR territory.
> **Date**: 2026-04-03
> **Authors**: KVK, Claude
> **Triggered by**: Karpathy "LLM Knowledge Bases" analysis revealing context window scaling as YARNNN's highest-severity architectural gap.
> **Related**: `karpathy-llm-knowledge-bases-2026-04-03.md` (Section 5), ADR-141 (task pipeline), ADR-151 (context domains), ADR-154 (execution boundary reform)

---

## 1. The Problem

YARNNN's context gathering is **scope-aware but retrieval-naive**. Tasks declare which domains they need (`context_reads`), but within each domain, retrieval is "give me the 20 most recent files, truncated to 3,000 chars each." This works today because workspaces are young. It won't work at scale.

### 1.1 Current Flow (What Exists)

```
gather_task_context()
  ├─ Read awareness.md           → full file, no truncation
  ├─ Read _tracker.md            → full file (entity index)
  ├─ Read domain files           → 20 most recent, 3,000 chars each
  │   └─ ORDER BY updated_at DESC, LIMIT 20
  ├─ Read AGENT.md               → identity only
  ├─ Read notes.md               → user standing instructions
  ├─ Read DELIVERABLE.md         → quality contract
  ├─ Read feedback.md            → last 3 entries
  └─ Read steering.md            → TP management notes
```

Key constants in `task_pipeline.py`:
- `max_files_per_domain = 20` (line 37)
- `max_content_per_file = 3000` chars (line 38)
- `max_entries = 3` for feedback (line 363)

### 1.2 Where It Breaks (Three Walls)

**Wall 1: Volume cap.** A competitive intelligence domain with 30 entities × 4 files each = 120 files. Agent sees 20. The other 100 are invisible — even if directly relevant to the task objective.

**Wall 2: Recency ≠ relevance.** A 3-month-old competitor profile is highly relevant to "how does Acme compare to Beta?" but gets pushed out by 20 newer files about other entities. The current sort is `ORDER BY updated_at DESC` with no concept of query-relevance.

**Wall 3: Stable knowledge tax.** Every execution re-reads AGENT.md, IDENTITY.md, notes.md — stable content unchanged across runs. Prompt caching helps with cost but these still consume context window space that could be used for dynamic, task-specific context.

### 1.3 Token Budget Reality

| Component | Current tokens | At scale (30 entities, 3 domains) |
|---|---|---|
| System prompt (cached) | 2,000-3,000 | Same |
| Awareness + tracker | 500-1,300 | 1,500-3,000 (larger trackers) |
| Domain files (per domain) | 5,000-15,000 | 15,000 × 3 = 45,000 (cap hit) |
| Identity + notes + deliverable | 1,000-2,000 | Same |
| Feedback + steering | 400-900 | Same |
| **Total** | **~10,000-22,000** | **~50,000-55,000** |

At 50K+ input tokens, we're using ~25% of Sonnet's 200K window. Not catastrophic, but the concern isn't the absolute number — it's that we're spending those tokens on the 20 most recent files rather than the 20 most relevant files.

---

## 2. What We Already Have (And What It Implies)

### 2.1 The Tracker Is Already an Index

`_tracker.md` is rebuilt deterministically after every execution. It contains:
```markdown
| Slug | Last Updated | Files | Status |
|------|-------------|-------|--------|
| acme-corp | 2026-03-28 | 4 | active |
| beta-inc | 2026-02-15 | 3 | stale |
| gamma-io | 2026-04-01 | 2 | active |
| delta-labs | 2026-03-20 | 1 | discovered |
```

The agent already sees this index in context. What it lacks is the ability to **use it for selective loading**. Today, the pipeline loads domain files, then the agent sees the tracker. It should be: agent (or pipeline) reads the tracker, then selectively loads only the relevant entities.

### 2.2 Task Objective Is Already Parsed

`parse_task_md()` extracts `objective` (deliverable, audience, format, purpose) and `success_criteria` from TASK.md. This structured objective could drive relevance scoring — but today it's only injected into the user message, not used for file selection.

### 2.3 Awareness.md Has "Next Cycle Focus"

The post-run domain scan writes a `## Next Cycle Focus` section to `awareness.md` that lists stale entities and suggested priorities. This is a pipeline-generated hint about what the agent should look at — but it's advisory text in context, not used for file selection.

### 2.4 Search Primitives Exist But Aren't Used Pre-Execution

`SearchWorkspace` and `QueryKnowledge` are available as agent tools during execution. Agents can search during their tool rounds. But the initial context gathering (before the first LLM call) is pure recency-ordered file dump. The agent gets bulk context, then can search for more during tool rounds — but can't influence what bulk context it receives.

---

## 3. Proposed Approach: Tracker-Driven Selective Loading

### 3.1 The Idea

Replace "load 20 most recent files from domain" with "load tracker + let objective drive entity selection." Two-phase context gathering:

**Phase 1 (deterministic, zero LLM):** Load lightweight context — tracker files, awareness.md, agent identity, task metadata. This gives the pipeline (or agent) a map of what exists without loading full content.

**Phase 2 (selective):** Based on task objective + tracker state, select which entities to load in full. Two options for how selection happens:

**Option A: Pipeline heuristic (deterministic).** Pattern-match task objective against entity slugs/names in tracker. If objective mentions "Acme" → load acme-corp files. If objective is "competitive landscape" → load all active entities but only `profile.md` (skip signals.md, product.md). If objective is "signal monitoring" → load all `signals.md` files, skip profiles.

**Option B: Haiku pre-selection (cheap LLM).** Pass tracker + objective to Haiku. Ask: "Which entities are relevant to this task? Return a list of entity slugs and which files to load." Cost: ~500 input tokens + 200 output tokens on Haiku = ~$0.0005. Then load only the selected files.

**Option C: Agent-driven (current tools, different flow).** Don't pre-load domain files at all. Give agent the tracker + awareness + identity. Let the agent use `ReadWorkspace` and `QueryKnowledge` tools to pull what it needs. This is essentially Karpathy's pattern: "read the index, then research the answers."

### 3.2 Assessment of Each Option

| Option | Cost | Latency | Accuracy | Complexity |
|---|---|---|---|---|
| **A: Pipeline heuristic** | Zero | Zero added | Low-medium (string matching misses semantic relevance) | Low — regex/fuzzy match against tracker |
| **B: Haiku pre-selection** | ~$0.0005/run | +1-2s | High (LLM understands objective → entity relevance) | Medium — new LLM call in pipeline, prompt engineering |
| **C: Agent-driven** | Zero pre-load, but more tool rounds | +5-15s (more rounds) | High (agent optimizes its own retrieval) | Low code change, but increases tool round budget |

### 3.3 Recommendation: Hybrid A+C

**Phase 1: Deterministic pre-load** (Option A, cheap, immediate)
- Always load: awareness.md, _tracker.md, AGENT.md, DELIVERABLE.md, feedback, steering
- Always load: synthesis files (`_landscape.md`, `_overview.md`) — these are cross-entity summaries
- For entity files: use task `context_reads` + `context_writes` declarations, plus match objective keywords against tracker entity slugs
- If objective mentions specific entities → load those entities' files (all files per entity)
- If objective is general (e.g., "weekly competitive brief") → load only `profile.md` per entity (skip signals, product, strategy) up to `max_files_per_domain`

**Phase 2: Agent-driven deep retrieval** (Option C, accurate, flexible)
- Agent starts with tracker + synthesis + matched entity files
- Agent uses `ReadWorkspace` / `QueryKnowledge` tools to pull additional files as needed
- Increase tool round budget slightly for context-heavy tasks (already exists: `_BOOTSTRAP_ROUND_MULTIPLIER = 2`)

This is a **refactor of `_gather_context_domains()`**, not a new system. The function signature stays the same. The behavior changes from "dump 20 most recent" to "load matched entities + synthesis, let agent pull more."

---

## 4. Implementation Sketch

### 4.1 Changes to `_gather_context_domains()`

```python
# Current (naive):
async def _gather_context_domains(client, user_id, domains, max_files=20, max_content=3000):
    for domain in domains:
        files = query(path LIKE domain/%, ORDER BY updated_at DESC, LIMIT max_files)
        sections.append(format(files))

# Proposed (tracker-driven):
async def _gather_context_domains(client, user_id, domains, task_info, max_files=20, max_content=3000):
    for domain in domains:
        # Always load synthesis files (cross-entity summaries)
        synthesis = load_synthesis_file(domain)

        # Match objective against tracker entities
        tracker = load_tracker(domain)
        matched_entities = match_entities(tracker, task_info.get("objective", {}))

        if matched_entities:
            # Selective: load matched entity files
            files = query(path LIKE domain/{entity}/%, for entity in matched_entities)
        else:
            # Fallback: load recent profile.md files (summary per entity)
            files = query(path LIKE domain/%/profile.md, ORDER BY updated_at DESC, LIMIT max_files)

        sections.append(format(synthesis + files))
```

### 4.2 Entity Matching (Simple Heuristic)

```python
def match_entities(tracker_entries, objective):
    """Match task objective text against entity names/slugs in tracker."""
    objective_text = " ".join([
        objective.get("deliverable", ""),
        objective.get("audience", ""),
        objective.get("purpose", ""),
    ]).lower()

    matched = []
    for entity in tracker_entries:
        # Direct slug/name match
        if entity.slug in objective_text or entity.name.lower() in objective_text:
            matched.append(entity.slug)

    # If no direct matches, return empty → fallback to profile-only loading
    return matched
```

### 4.3 What Stays the Same

- Task declaration model (`context_reads`, `context_writes`) — unchanged
- `_tracker.md` structure and rebuild logic — unchanged
- `awareness.md` structure — unchanged
- Agent tool primitives (SearchWorkspace, QueryKnowledge, ReadWorkspace) — unchanged
- Post-run domain scan — unchanged
- Token truncation limits — unchanged (may relax `max_content_per_file` since fewer files loaded)

---

## 5. ADR Decision: Update vs New

### 5.1 Assessment

This is a **refactor of an existing function** (`_gather_context_domains`) within the existing task pipeline (ADR-141). It doesn't change:
- The execution architecture (ADR-141)
- The domain registry (ADR-151, ADR-152)
- The tracker convention (ADR-154)
- The tool primitives available to agents
- The post-run scan behavior

It does change:
- How files are selected within a domain (recency → objective-matched + synthesis-first)
- The information density of pre-loaded context (fewer files but more relevant)
- Potentially the tool round pattern (agents may use more ReadWorkspace calls)

### 5.2 Recommendation: ADR-154 Update (Execution Boundary Reform)

ADR-154 already governs the "who/what/how" priority model for context gathering and the tracker/awareness conventions. This is a refinement of the "what" layer — making domain file selection smarter. I'd frame it as:

**ADR-154 Phase 2: Tracker-Driven Context Selection**
- Phase 1 (implemented): Execution boundary reform — who/what/how file separation, tracker scans, awareness.md
- Phase 2 (proposed): Selective entity loading — objective-matched entities + synthesis-first + agent-driven deep retrieval

This avoids ADR proliferation while clearly marking the evolution. The change is scoped to `_gather_context_domains()` and its callers, which are already within ADR-154's boundary.

### 5.3 If It Grows

If during implementation the change expands beyond `_gather_context_domains()` — for example, if we add Haiku pre-selection (Option B) or restructure how agents interact with tools for retrieval — that's ADR territory. A new ADR (e.g., "ADR-158: Intelligent Context Retrieval") would be warranted if:
- A new LLM call is added to the pipeline (Haiku pre-selection)
- Agent tool round patterns are fundamentally restructured
- A new "retrieval mode" is added to task types
- Semantic search replaces full-text search as the primary retrieval method

For the deterministic heuristic (Option A) + existing agent tools (Option C), ADR-154 update is sufficient.

---

## 6. Sequencing

| Step | Scope | Effort | Dependencies |
|---|---|---|---|
| 1. Refactor `_gather_context_domains()` to accept `task_info` | `task_pipeline.py` | Small | None |
| 2. Add `match_entities()` heuristic | New function in `task_pipeline.py` | Small | Step 1 |
| 3. Synthesis-first loading | `_gather_context_domains()` + `directory_registry.py` | Small | Step 1 |
| 4. Profile-only fallback for general objectives | `_gather_context_domains()` | Small | Steps 1-2 |
| 5. Verify tool round budget is sufficient for agent-driven retrieval | `task_pipeline.py` constants | Trivial | Observation after steps 1-4 |
| 6. Update ADR-154 with Phase 2 | `docs/adr/` | Documentation | Steps 1-5 |

Total estimated effort: **Small refactor** — 2-3 functions changed, no schema changes, no new services, no new LLM calls, no migration needed.

---

## 7. Future Considerations (Not In Scope)

For reference, not for this pass:

**Haiku pre-selection (Option B):** If the heuristic proves too crude (misses semantic matches like "how does our pricing stack up" → should match competitor entities but no entity name appears in objective), add a cheap Haiku call to do entity selection. Defer until we have evidence the heuristic is insufficient.

**Prompt caching for stable context:** Anthropic's prompt caching already applies to the system prompt. Could be extended to cache the synthesis files + agent identity block across runs (these change infrequently). Would require structuring the message to put stable content in cacheable positions.

**Context window compression:** Instead of truncating files to 3,000 chars, use a summarization pass (Haiku) to compress domain files to key facts. More token-efficient but adds latency + cost. Karpathy's "LLM compiles summaries" is essentially this — but YARNNN's synthesis files already serve this role for cross-entity knowledge.

**Finetuning / knowledge distillation:** Karpathy's forward-looking suggestion. Not viable with Claude API today (no finetuning endpoint). Track for when/if Anthropic offers it. Alternative: use accumulated workspace as training data for a smaller model that handles the "known facts" layer, with Sonnet reserved for novel reasoning.

**Image-native context:** Extending `_gather_context_domains()` to include `content_url` for vision API integration. Separate concern from retrieval prioritization — depends on multimodal pipeline work (ADR-157 Phase 2+).