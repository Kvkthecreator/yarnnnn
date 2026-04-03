# Karpathy's "LLM Knowledge Bases" — Cross-Analysis with YARNNN

> **Status**: Analysis complete. Verified against YARNNN codebase.
> **Date**: 2026-04-03
> **Authors**: KVK, Claude
> **Source**: [Karpathy tweet](https://x.com/karpathy/status/2039805659525644595) — "LLM Knowledge Bases"
> **Context**: Karpathy described a personal workflow for building LLM-maintained knowledge bases, concluding: "I think there is room here for an incredible new product instead of a hacky collection of scripts." Every primitive he describes maps to an implemented YARNNN subsystem.

---

## 1. What Karpathy Described

A workflow for using LLMs to build personal knowledge bases stored as markdown + images:

| Step | His workflow | Description |
|---|---|---|
| **Data ingest** | Raw documents → `raw/` directory | Articles, papers, repos, datasets, images indexed as source material |
| **Compilation** | LLM "compiles" a wiki from `raw/` | Collection of `.md` files in directory structure. Summaries, backlinks, concept articles, cross-links. LLM writes and maintains all data — human rarely touches it. |
| **IDE / Frontend** | Obsidian as viewer | View raw data, compiled wiki, derived visualizations. Marp for slides. |
| **Q&A** | Agent queries against wiki | Complex questions researched against ~100 articles / ~400K words. No fancy RAG needed — LLM auto-maintains index files + brief summaries at small scale. |
| **Output → feedback** | Outputs filed back into wiki | "My own explorations and queries always add up in the knowledge base." |
| **Linting** | LLM health checks | Find inconsistencies, impute missing data, discover connections, suggest further questions. |
| **Tooling** | Custom CLIs (search engine, etc.) | Handed to LLM as tools for larger queries. |
| **Future** | Finetuning | "Synthetic data generation + finetuning to have your LLM know the data in its weights instead of just context windows." |

His concluding line: **"I think there is room here for an incredible new product instead of a hacky collection of scripts."**

---

## 2. Concept-by-Concept Mapping to YARNNN

Every concept Karpathy described has a direct, implemented counterpart in YARNNN — often more sophisticated than his script-based version.

### 2.1 Data Ingest: `raw/` → Context Domains

Karpathy indexes source documents into a `raw/` directory. YARNNN's equivalent is the **context domain architecture** (ADR-151, ADR-152).

| Karpathy | YARNNN |
|---|---|
| `raw/` directory | `/workspace/context/{domain}/` — 6 domains: competitors, market, relationships, projects, content_research, signals |
| Manual file placement (Obsidian Web Clipper) | **Automated perception**: platform sync (Slack, Notion) writes structured summaries; agents write entity files during task execution via `_post_run_domain_scan()` |
| Static files | **Entity-structured directories**: per-entity subfolders with templated files (`get_entity_stub_content()` in `directory_registry.py`) |

Key files:
- `api/services/directory_registry.py` — `WORKSPACE_DIRECTORIES` (6 domains, entity templates, synthesis files)
- `api/services/task_pipeline.py` — `_post_run_domain_scan()` (writes entity updates back to context)

Key difference: Karpathy's ingest is manual. YARNNN's is continuous and automated — agents discover entities during execution and create structured files using domain-specific templates.

### 2.2 Compilation: LLM → Wiki

Karpathy's LLM "compiles" summaries, backlinks, and concept articles from raw data. YARNNN does this through three mechanisms:

**1. Entity tracker files** (`_tracker.md`) — deterministic, zero LLM cost:
```python
# directory_registry.py → build_tracker_md()
# Materialized view: | Slug | Last Updated | Files | Status |
# Domain health summary: total, active, stale, discovered counts
# Rebuilt after every task execution — pipeline responsibility, not LLM
```

**2. Synthesis files** (`_landscape.md`, `_overview.md`) — LLM-maintained cross-entity analysis:
```python
# Each context domain has a synthesis_file + synthesis_template
# Agents update these when cross-entity patterns emerge during task execution
# e.g., competitors/_landscape.md = cross-competitor positioning analysis
```

**3. Agent identity files** — accumulated understanding per agent:
```
/agents/{slug}/
  AGENT.md              # Identity + domain expertise (like CLAUDE.md)
  thesis.md             # Running domain understanding (LLM-maintained)
  memory/
    preferences.md      # Distilled from user edit feedback (ADR-117)
    reflections.md      # Self-assessment of recent outputs (ADR-128)
```

Key difference: Karpathy maintains one flat wiki. YARNNN maintains **per-agent + per-domain + per-task** structured knowledge with explicit lifecycle management (ephemeral → active → archived).

### 2.3 Index Files: Auto-Maintained Summaries

Karpathy: "I thought I had to reach for fancy RAG, but the LLM has been pretty good about auto-maintaining index files and brief summaries."

YARNNN validates this exact insight. The `_tracker.md` files serve the same purpose — but are deterministic (zero LLM cost):

```python
# task_pipeline.py → _post_run_domain_scan()
# After EVERY task execution:
# 1. Scan entity-bearing domains → rebuild _tracker.md
# 2. Update task awareness.md with cycle state (phase, scope, entities touched)
# 3. Append to signal log (/workspace/context/signals/{date}.md)
# All deterministic — no LLM calls needed
```

Every agent run refreshes the "index" of accumulated knowledge. The next run reads `_tracker.md` first to understand what exists before diving into domain files. Same pattern as Karpathy's LLM reading index files before answering questions.

Key file: `api/services/task_pipeline.py` lines 102-360 (`_post_run_domain_scan`)

### 2.4 Outputs Add Up: The Accumulation Loop

Karpathy: "I end up filing the outputs back into the wiki to enhance it for further queries. So my own explorations and queries always add up."

This is YARNNN's **accumulation thesis** (originated ADR-072, evolved into ADR-151):

```
Task execution cycle:
  1. gather_task_context() → reads _tracker.md + domain files + feedback
  2. Agent generates output (competitive brief, market analysis, etc.)
  3. save_output() → /tasks/{slug}/outputs/{date}/output.md + manifest.json
  4. _post_run_domain_scan() → writes entity updates BACK to /workspace/context/
  5. Rebuilds _tracker.md with updated freshness

Next cycle reads the enriched context → produces better output → writes more back
```

The critical shared insight: **knowledge is an accumulating asset, not a stateless query**. Each execution enriches the substrate for the next one.

Key files:
- `api/services/task_pipeline.py` — `gather_task_context()` (reads), `_post_run_domain_scan()` (writes back)
- `api/services/task_workspace.py` — `save_output()` (output persistence)

### 2.5 Linting: Health Checks on Knowledge

Karpathy runs "health checks" to find inconsistencies, impute missing data, and discover connections. YARNNN has three implemented mechanisms:

**1. Feedback distillation** (ADR-117): User edits to agent outputs are analyzed (`compute_edit_metrics()` in `feedback_engine.py`), categorized (additions, deletions, rewrites), and distilled into `memory/feedback.md` for the task. Next execution reads this and adjusts.

**2. Agent self-reflection** (ADR-128): After generating output, agents produce a self-assessment appended to `memory/reflections.md` — rolling window of 5 recent entries. Extracted from output, stripped before delivery.

**3. Staleness detection** (ADR-154): Pipeline deterministically detects stale entities using schedule-based thresholds (weekly task → entity stale after 10 days). Writes staleness flags to `_tracker.md`. Agent sees "stale" entities and prioritizes refreshing them.

**4. Context inference** (ADR-144): `infer_shared_context()` in `context_inference.py` processes documents, URLs, and free text to update `IDENTITY.md` or `BRAND.md` — essentially "recompiling" the workspace identity from new data.

Key files:
- `api/services/feedback_engine.py` — `compute_edit_metrics()`, `categorize_edits()`
- `api/services/feedback_distillation.py` — `distill_feedback_to_workspace()`
- `api/services/context_inference.py` — `infer_shared_context()`

### 2.6 Search: Querying the Knowledge Base

Karpathy vibe-coded "a small and naive search engine over the wiki, which I both use directly (in a web ui), but more often I want to hand it off to an LLM via CLI as a tool." YARNNN has this at two levels:

**Full-text search** (Postgres RPC, available to agents as tool):
```python
# workspace.py → search()
# RPC: search_workspace(p_user_id, p_query, p_path_prefix, p_limit)
# Returns: path, summary, content[:500], rank, updated_at
```

**Semantic search** (embedding-based, domain-scoped):
```sql
-- search_memories(): hybrid score = 70% cosine similarity + 30% importance
-- Domain scoping: specified domain + default domain (always-accessible)
-- Model: text-embedding-3-small (1536 dimensions)
```

**Agent-facing primitives**: `SearchWorkspace` and `QueryKnowledge` tools exposed to agents during execution, scoped by domain. Agents can search during tool rounds (up to 5-12 rounds depending on scope).

Key files:
- `api/services/workspace.py` — `search()` method
- `api/services/primitives/workspace.py` — `SearchWorkspace`, `QueryKnowledge` tool definitions

---

## 3. What YARNNN Has That Karpathy's Workflow Doesn't

| Capability | Karpathy | YARNNN |
|---|---|---|
| **Multi-agent** | One human directing one LLM | Multiple specialized agents (8 pre-scaffolded per workspace), each with own workspace + shared context domains |
| **Automated scheduling** | Manual (human runs queries) | Cron-based task scheduling via `unified_scheduler.py`, tasks declare cadence |
| **Feedback loop** | Manual (human reviews and re-prompts) | Automated: edit metrics → feedback distillation → `memory/feedback.md` → next-run injection |
| **Output pipeline** | Markdown files viewed in Obsidian | Agent draft → output folder + manifest → render service (8 skills: PDF, PPTX, charts, etc.) → delivery (email, Slack) |
| **Platform perception** | Manual (Obsidian Web Clipper + hotkey) | Continuous platform sync (Slack, Notion, GitHub) with structured extraction |
| **Context domains** | Flat wiki directory | 6 typed domains with entity templates, trackers, synthesis files, assets folders |
| **Team coordination** | N/A | Cross-agent workspace reading (ADR-116), TP orchestration for multi-agent work |
| **Cost awareness** | Unbounded (every query = full LLM call) | Cached system prompts (~90% savings on tool rounds), deterministic index files (zero LLM), truncation limits |

---

## 4. What Karpathy's Workflow Has That YARNNN Should Consider

| Capability | Karpathy | YARNNN gap | Severity |
|---|---|---|---|
| **Image-native knowledge** | Downloads images locally, LLM references them directly as context | Workspace is text-native. Agents produce images (RuntimeDispatch) but never reason about them as input. `_gather_context_domains()` doesn't select `content_url`. No vision API integration in agent execution pipeline. ADR-157 adds `assets/` folders but they're output-only, not input. | **Medium** — matters for visual domains (brand, competitive positioning), less for text-heavy analysis |
| **Local-first** | Everything in local `~/` directory, works offline | Cloud-dependent (Supabase, Render, Claude API). No offline mode. | **Low** — different product model (personal tool vs team SaaS) |
| **Obsidian as IDE** | Rich viewer for markdown + images + slides + plugins | Dashboard is functional but doesn't match Obsidian's rendering quality or plugin ecosystem | **Low** — YARNNN's value is in the agents, not the viewer |
| **Radical simplicity** | No database, no cloud, no infrastructure | 4 Render services, Supabase, S3, Docker | **Low** — complexity is justified by multi-agent + scheduling + delivery |
| **Context window scaling** | Notes desire for "synthetic data generation + finetuning to have your LLM know the data in its weights" | All context is prompt-injected. At scale, hits token budget walls. Current limits: 20 files/domain × 3,000 chars/file. No intelligent retrieval — just recency ordering within declared domains. | **High** — see Section 5 |

---

## 5. The Context Window Problem (Detailed)

Karpathy's wiki is ~100 articles / ~400K words. He acknowledges this works "at this ~small scale" and flags the desire for finetuning when it grows. YARNNN faces the same wall but with a more structured path to address it.

### 5.1 Current Token Budget

YARNNN's context gathering (`gather_task_context()` in `task_pipeline.py`) assembles:

| Component | Typical tokens | Hard limits |
|---|---|---|
| System prompt (cached) | 2,000-3,000 | Cached after first round (~90% savings) |
| Task awareness.md | 200-500 | Full file, no truncation |
| Domain _tracker.md (per domain) | 300-800 | Full file, no truncation |
| Domain files (per domain) | 5,000-15,000 | `max_files_per_domain=20`, `max_content_per_file=3000` chars |
| Agent AGENT.md | 500-1,000 | Identity only (ADR-154 thinning) |
| User notes.md | 100-300 | Full file |
| DELIVERABLE.md | 200-500 | Full file |
| Feedback (last 3) | 300-600 | `max_entries=3` |
| Steering notes | 100-300 | Full file |
| **Total input (cold)** | **~10,000-22,000** | — |
| **Total input (2 domains)** | **~15,000-35,000** | — |

Model: `claude-sonnet-4-20250514` (200K context window). Currently using ~10-17% of available window.

### 5.2 Where It Breaks

The current approach works because workspaces are young. As they accumulate:

**Scenario: Competitive intelligence domain with 30 entities**
- 30 entities × 4 files each (profile.md, signals.md, product.md, strategy.md) = 120 files
- `max_files_per_domain=20` means agent sees only the 20 most recently updated
- The other 100 files are invisible — even if highly relevant to the current task
- A task asking "how does Acme's pricing compare to Beta's?" might not see Beta's profile if it was updated 3 weeks ago

**Scenario: Signal log after 6 months**
- Daily entries × 180 days = 180 files in signals domain
- Agent sees last 20 days of signals — missing the seasonal pattern from 3 months ago

**Scenario: Cross-domain synthesis**
- Executive reporting task reads competitors + market + relationships
- 20 files × 3 domains × 3,000 chars = ~180K chars = ~45K tokens just for domain context
- Approaches the practical limit (need room for system prompt + output)

### 5.3 Three Walls

**Wall 1: Volume.** 20 files per domain is a hard cap. At 100+ entities per domain, most knowledge is invisible during any given execution.

**Wall 2: Relevance.** Recency ≠ relevance. A 3-month-old competitor profile is highly relevant to a competitive analysis task, even if 20 newer files exist. Current retrieval has no concept of query-relevance — it's pure recency within declared domains.

**Wall 3: Stable knowledge tax.** Every execution re-reads AGENT.md, IDENTITY.md, notes.md — stable content that hasn't changed. These consume tokens that could be used for dynamic, task-specific context. (Prompt caching partially addresses this, but the tokens still count against the window for reasoning.)

### 5.4 Karpathy's Observation Applied to YARNNN

Karpathy's key insight: "I thought I had to reach for fancy RAG, but the LLM has been pretty good about auto-maintaining index files and brief summaries."

YARNNN already has the index files (`_tracker.md`). What's missing is the second step: **using the index to selectively read only what's relevant**, rather than dumping the 20 most recent files. This is the retrieval + context prioritization opportunity explored in the companion discourse: `docs/analysis/context-prioritization-discourse-2026-04-03.md`.

---

## 6. Strategic Implication

Karpathy independently arrived at the same primitives YARNNN has been building through 150+ ADRs: markdown-as-knowledge-substrate, auto-maintained indexes, accumulating outputs, health-check linting, search-as-tool. This is strong external validation from one of the most respected practitioners in AI.

**Positioning opportunity**: YARNNN can credibly position as the productized version of this workflow — with multi-agent coordination, automated scheduling, feedback loops, and a production output pipeline layered on top of the same fundamental architecture.

**The gap**: Karpathy's workflow is radically simple (local files, one LLM, Obsidian). YARNNN's is operationally complex (cloud services, Postgres, Docker). The question is whether the added sophistication (multi-agent, feedback distillation, render pipeline) justifies the complexity for the target user. For knowledge workers who need recurring, improving outputs — yes. For a researcher building a personal wiki — Karpathy's scripts win on simplicity.

**The tell**: Karpathy's call for "an incredible new product" suggests even he recognizes the script approach doesn't scale. YARNNN's architectural investments (entity structure, lifecycle management, domain registries, deterministic index maintenance) are exactly what's needed to make this pattern production-grade.