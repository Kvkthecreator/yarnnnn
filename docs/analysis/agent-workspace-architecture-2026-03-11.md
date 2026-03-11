# Agent Workspace Architecture — Design Discourse

**Date:** 2026-03-11
**Participants:** Kevin (founder), Claude (architect)
**Outcome:** ADR-106 — Agent Workspace Architecture
**Context:** Post ADR-103 (agentic terminology rename), investigating why Proactive Insights agent produced low-quality output with irrelevant content

---

## The Triggering Problem

The Proactive Insights agent (type: `deep_research`, mode: `proactive`) produced a v4 output that included a "Korean Government AI Beauty Program" as one of its weekly signals — content that appeared in the user's Gmail but had zero relevance to the agent's domain (YARNNN launch readiness, competitive landscape).

Root cause: the agent received a chronological dump of all platform content from configured sources (`get_content_summary_for_generation()`), then tried to find interesting patterns in that dump. The irrelevant content was included because it existed in a connected source, not because it was relevant to the agent's purpose.

---

## Discourse: Two Families of Agents

### The initial distinction: platform-anchored vs concept-anchored

**Platform-anchored agents** (digest, status, brief): their job is "tell me what happened on my platforms." The platform content dump IS the job — completeness matters, and the current pipeline is correct for these.

**Concept-anchored agents** (deep_research, watch, coordinator): their job is "reason about a domain using my platforms as one input among many." The concept is the anchor, not the platform.

### Refinement: "concept-anchored" is wrong

"Concept-anchored" implies a fixed concept. But the Proactive Insights agent's value is that it *discovers* what's worth paying attention to. It's not anchored to a concept — it's anchored to a reasoning process.

Better framing:

| Archetype | Job | Context need |
|---|---|---|
| **Reporter** | Faithfully summarize what happened | Platform dump (complete) |
| **Analyst** | Form judgments about what matters | Self-directed knowledge base search, memory-driven |
| **Researcher** | Investigate external topics grounded in internal context | Thesis-driven web + selective internal evidence |
| **Operator** | Execute recurring workflows | Structured data + action capabilities (future) |

**Reporter agents value coverage. Reasoning agents (analyst/researcher/operator) value judgment.**

### The intelligence model mismatch

The four-layer intelligence model (Skills / Directives / Memory / Feedback) works differently for each archetype:

- For reporters, layers 2-4 are *refinements on a complete input*. The dump IS the job.
- For reasoning agents, layers 2-4 should be *the primary intelligence* driving what the agent looks at. Currently they're injected alongside an unfiltered dump — competing with noise instead of directing the search.

### Pipeline inversion

The fix isn't adding a relevance filter to the dump. It's inverting the pipeline:

**Current (all agents):**
```
Gather everything → filter → generate
```

**Correct for reasoning agents:**
```
Agent reasons about its domain → agent queries for evidence → generate
```

The headless agent already has Search, Read, WebSearch primitives. The problem is that orchestration pre-loads a platform dump *before* the agent reasons, and the agent must dig through noise instead of querying selectively.

### Self-evolving anchors

For reasoning agents, the intelligence model layers should compound:

- **Run 1**: No memory, broad scan, broad output
- **Run 5**: Accumulated observations from 4 review passes. Noticed patterns.
- **Run 20**: Refined thesis. Knows what to look for, what user edits out.

The agent's accumulated memory IS the anchor. It evolves. But currently it doesn't compound because the context pipeline doesn't use it for filtering.

---

## Discourse: Context Management and the Filesystem Question

### The current data model's limitations

Current state:
- `platform_content`: flat table, ~508 rows for primary user, organized by platform/resource
- `agent_memory`: JSONB blob on agent record (currently `{}`)
- `user_memory`: 30 key-value pairs, heavily duplicated (6 variants of "prefers brief content")
- Agent outputs: `platform_content` rows with `platform="yarnnn"`
- No hierarchy, no workspace isolation, no agent-scoped working state

### The filesystem insight

Observation: Claude Code, OpenClaw, and emerging agent structures all use file-based configuration and memory:
- `CLAUDE.md`, `.claude/memory/`, hooks as files
- Claude Agent SDK exposes persistent memory as directories
- The industry is converging on file-based agent interfaces

If the agentic landscape converges on file-based interfaces for agent-to-agent communication, an agent platform whose internal representation is Postgres JSONB blobs is:
1. Opaque to external agents
2. Opaque to users
3. Non-portable
4. Non-composable

### Research: Industry evidence

**Sources consulted:**
- [AgentFS (Turso)](https://turso.tech/blog/agentfs) — SQLite-backed filesystem abstraction for agents
- [agent-vfs](https://github.com/johannesmichalke/agent-vfs) — Postgres-backed virtual filesystem, 16 POSIX-like operations
- [Arize: Agent Interfaces in 2026](https://arize.com/blog/agent-interfaces-in-2026-filesystem-vs-api-vs-database-what-actually-works/) — industry survey
- [Three-File Pattern](https://earezki.com/ai-news/2026-03-09-the-state-management-pattern-that-runs-our-5-agent-system-24-7/) — production 5-agent system on filesystem state
- [MCP 2026 Roadmap](http://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [A2A Protocol](https://a2a-protocol.org/latest/specification/) — Agent Cards at `.well-known/agent-card.json`
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview) — harness as OS, filesystem memory

**Key findings:**

1. **Industry convergence is real.** Multiple independent implementations (agent-vfs, AgentFS, Claude Code, Three-File Pattern) converge on filesystem semantics for agent state.

2. **LLMs are natively good at file operations.** Pre-trained on massive code that reads/writes files. Zero-shot competence. Letta achieved 74% on memory tasks with file storage.

3. **Protocols confirm the direction.** MCP: filesystem server is most-used reference implementation. A2A: Agent Cards as JSON files at `.well-known/`. Both under Linux Foundation.

4. **The critical distinction: interface vs infrastructure.** Arize survey: "These are separate concerns." Filesystem interface for agents, database infrastructure underneath. This is the emerging consensus.

5. **80% of agent production failures are state management, not prompt quality.** Human-readable state files allow diagnosis without specialized tools.

### Option analysis: B vs C

**Option B: Virtual filesystem over Postgres**
- Filesystem interface, database infrastructure
- Full-text + vector search built in
- ACID transactions
- Zero new infrastructure (same Supabase)
- Migration: additive, non-destructive
- Lock-in: medium (standard SQL, easy to migrate)

**Option C: Actual cloud filesystem (S3/GCS)**
- Maximum portability, unlimited scale
- No built-in search (need Elasticsearch/Pinecone)
- No ACID (eventual consistency, race conditions)
- New infrastructure, new auth model
- Migration: higher risk

**Decision: Option B now, Option C as planned migration path.**

Option B gives 95% of the value at 20% of the complexity. The abstraction layer (`AgentWorkspace` interface) makes the backing store swappable. YARNNN's scale (hundreds to low thousands of workspace items per agent) is well within Postgres's comfort zone for years.

The one trigger for Option C: if a major platform ships agent-to-agent communication requiring actual filesystem access. Currently A2A and MCP both work over HTTP — backing store is invisible to the protocol.

---

## The Decision

**YARNNN bets that agent intelligence should be stored as human-readable files in navigable workspaces, not as opaque database records.**

This makes agents inspectable, portable, and composable — and aligns with where Claude Code, MCP, and the broader agentic ecosystem are heading.

Implementation: virtual filesystem over Postgres (`workspace_files` table with path-based access), with a storage-agnostic abstraction layer that preserves optionality for future migration to cloud storage.

See: ADR-106 — Agent Workspace Architecture
