# ADR-087: Deliverable Scoped Context

**Status:** Fully Implemented (2026-03-04). Goal-mode behavioral differentiation deferred (see Phase 3 note).
**Date:** 2026-03-02 (v1), 2026-03-03 (v2 rewrite, v3 naming revision), 2026-03-04 (primitive additions + ADR-091 frontend)
**Authors:** Kevin Kim, Claude (analysis)
**References:**
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md) — one agent, two modes; this ADR bridges them via scoped context
- [ADR-072: Unified Content Layer](ADR-072-unified-content-layer-tp-execution-pipeline.md) — platform_content as filesystem; deliverables as views
- [ADR-064: Unified Memory Service](ADR-064-unified-memory-service.md) — implicit memory via nightly cron; this ADR adds deliverable-scoped memory
- [ADR-067: Session Compaction](ADR-067-session-compaction-architecture.md) — session boundaries and summaries; this ADR routes them per deliverable
- [ADR-038: Filesystem as Context](ADR-038-filesystem-as-context.md) — platform sync as "automated git pull"
- [ADR-088: Trigger Dispatch](ADR-088-input-gateway-work-serialization.md) — `dispatch_trigger()` routes background triggers to generation vs memory update (Step 2, follows this ADR)
- [Pre-ADR Analysis](../analysis/workspace-architecture-analysis-2026-03-02.md) — v1-v5 analysis, OpenClaw comparison, ghost entity discovery
- [Development Landscape](../analysis/workspace-architecture-landscape.md) — sequencing and track dependencies

---

## Context

YARNNN has two execution modes (ADR-080): TP chat (streaming, multi-turn, user-facing) and headless generation (background, tool-limited, deliverable pipeline). Both operate on the same deliverable data, but they cannot see each other's work.

The missing concept: **per-deliverable memory and instructions** — separate from platform content (raw input) and from global user memory (cross-deliverable preferences).

### Naming convention

This ADR adopts market-aligned naming to reduce conceptual drift as the AI agent landscape evolves:

| Market term | YARNNN term | Maps to |
|-------------|------------|---------|
| **Memory** (accumulated knowledge retained across sessions) | `deliverable_memory` | OpenClaw MEMORY.md, Claude Code CLAUDE.md context sections |
| **Instructions** (how the agent should behave in a given context) | `deliverable_instructions` | OpenClaw AGENTS.md, Cowork skills, Claude Code CLAUDE.md rules |
| **Tools** (capabilities the agent can invoke) | Primitives (existing, intentionally distinct) | Claude Code tools, OpenClaw tool layer |
| **Context** (assembled prompt input per turn) | Working memory injection (existing) | OpenClaw `resolveBootstrapContextForRun()`, Claude Code context assembly |

**Naming debt (resolved):** `user_context` table → renamed to `user_memory` in the same migration window as this ADR (separate commit, applied first).

### How this relates to platform content

`platform_content` is raw input — Slack messages, emails, Notion pages. It's user-scoped, not deliverable-scoped. Multiple deliverables read from the same platform content via their `sources` JSONB.

`deliverable_memory` is the agent's derived understanding of this specific work. When the agent reads Slack messages and learns "the team is concerned about Q2 deadline" — that observation lives in deliverable memory. Platform content is the source; deliverable memory is the interpretation.

`deliverable_instructions` is the user's explicit direction for this specific work. "Use formal tone." "Focus on trends." These are relatively stable, user-authored. They sit alongside existing instruction fields (`template_structure`, `type_config`, `recipient_context`) which are already part of the instructions layer but named from a configuration mental model.

### What already exists but isn't wired

The frontend already sends `surface_context.deliverableId` when the user is on a deliverable review page. The backend receives it but never uses it for session scoping or working memory injection. The plumbing exists; the connections don't.

### Why not the `projects` table?

The `projects` table exists as a ghost entity (migration 001, indexed, RLS'd, FK'd — zero rows). Activating it requires building a new product surface before validating whether scoped context improves output quality. Wrong sequencing pre-PMF. Clean activation path exists from this ADR if needed later.

---

## Decision

### Two new fields on deliverables

Each deliverable gets two fields that complete it as a self-contained unit of work:

**`deliverable_instructions`** (TEXT) — user-authored behavioral directives for this specific deliverable. How the agent should approach this work. Relatively stable, edited directly by the user.

**`deliverable_memory`** (JSONB) — system-accumulated knowledge about this deliverable. Session summaries, feedback patterns, learned preferences, observations. Grows over time, compacted periodically.

Sessions get a lightweight `deliverable_id` FK as a routing key for memory accumulation.

### Schema changes

**3 new columns on `deliverables`:**

| Column | Type | Purpose |
|---|---|---|
| `deliverable_instructions` | `TEXT DEFAULT ''` | User-authored instructions for this deliverable (the skills layer) |
| `deliverable_memory` | `JSONB DEFAULT '{}'` | System-accumulated knowledge (the memory layer) |
| `mode` | `TEXT DEFAULT 'recurring'` | `'recurring'` \| `'goal'` |

**1 new column on `chat_sessions`:**

| Column | Type | Purpose |
|---|---|---|
| `deliverable_id` | `UUID NULL FK deliverables(id) ON DELETE SET NULL` | Routing key for memory accumulation |

**0 schema changes to `user_memory`** (renamed from `user_context` in same migration window). Global user memory stays global.

**0 changes to session creation RPC.** `deliverable_id` set on session row at creation time.

### deliverable_instructions

Plain text (or markdown). The user writes this directly — like editing CLAUDE.md or AGENTS.md. Examples:

```
Use formal tone for this board report.
Always include an executive summary section.
Focus on trend analysis rather than raw numbers.
The audience is the executive team — assume business context, not technical.
```

This is separate from `template_structure` (output format) and `type_config` (type-specific settings) which are structural, not behavioral. `deliverable_instructions` captures the behavioral "how should the agent think about this work" layer.

**Partial consolidation (2026-03-09):** `recipient_context` is now surfaced alongside `deliverable_instructions` in the structured Instructions panel (moved from Settings). `template_structure.format_notes` is surfaced for `custom` type deliverables. The panel includes a live prompt preview showing the composed agent context. `type_config` remains in Settings as it controls type-specific execution parameters.

### deliverable_memory structure

```json
{
  "observations": [
    {"date": "2026-03-02", "source": "signal", "note": "Spike in #engineering mentions of Q2 deadline"}
  ],
  "goal": {
    "description": "Prepare board meeting materials for March 15",
    "status": "in_progress",
    "milestones": ["Research complete", "Draft v1", "Final review"]
  }
}
```

Stored as JSONB for structured appends. Rendered as markdown for prompt injection — the same pattern `format_for_prompt()` in `working_memory.py` already uses.

**What is NOT in this JSONB** (and why):
- `instructions` — live in `deliverable_instructions` (TEXT). User-authored, directly editable.
- `session_summaries` — queried at read time from `chat_sessions` via `deliverable_id` FK. No duplication needed.
- `feedback_patterns` — removed. The approval-gate feedback model was superseded by YARNNN's conversational iteration model: users refine output through TP chat and `deliverable_instructions`, not through post-hoc edit-diff analysis. Learning happens in conversation, not in review stamps.

### Scoping behavior

When a deliverable is active (user is chatting in deliverable context):

- **Working memory** (`build_working_memory`): Includes `deliverable_instructions` and `deliverable_memory` as new sections. Two field reads from the deliverable dict.
- **Session creation**: `deliverable_id` set on the session row as a routing key.
- **Memory writes**: Global facts → `user_memory` (unchanged). Deliverable observations → `deliverable_memory` (JSONB append, future — signals/agent only).
- **Headless execution** (`_build_headless_system_prompt`): Includes both fields from the deliverable dict. Already loaded — no new queries.

When no deliverable is active: all behavior unchanged. Fully backwards-compatible.

---

## Implementation Phases

### Phase 1: Schema + Read Paths (Backend only) — IMPLEMENTED (2026-03-03)

Migration 084: `user_context` → `user_memory` rename (naming debt, separate commit)
Migration 085: ADR-087 columns:
- `ALTER TABLE deliverables ADD COLUMN deliverable_instructions TEXT DEFAULT ''`
- `ALTER TABLE deliverables ADD COLUMN deliverable_memory JSONB DEFAULT '{}'`
- `ALTER TABLE deliverables ADD COLUMN mode TEXT DEFAULT 'recurring'`
- `ALTER TABLE chat_sessions ADD COLUMN deliverable_id UUID REFERENCES deliverables(id) ON DELETE SET NULL`

Wiring (all implemented):
- `POST /chat`: Extract `deliverable_id` from `surface_context`, set on session row, pass deliverable to `build_working_memory()`
- `build_working_memory()`: Accept optional deliverable dict, include `deliverable_instructions` and `deliverable_memory` as new sections via `_extract_deliverable_scope()`
- `_build_headless_system_prompt()`: Include both fields from the deliverable dict
- `unified_scheduler.py`: SELECT list updated to include new columns

**Validation:** TP sessions in deliverable context get scoped instructions + memory. Headless execution sees both. Global sessions unchanged.

### Phase 2: Backend Processing Cleanup + Scoped Session Reads — IMPLEMENTED (2026-03-03)

Architectural reassessment during Phase 2 planning led to significant simplification:

**Deleted (governance-era artifacts, superseded by conversational iteration model):**
- `process_feedback()` + `_analyze_edit_patterns()` — edit-diff heuristics wrote crude patterns to global `user_memory`. Replaced by: users refine output through TP chat + `deliverable_instructions`. Learning happens in conversation, not review stamps.
- `process_patterns()` + `_detect_activity_patterns()` — activity log pattern detection wrote marginal observations ("runs deliverables on Mondays") to `user_memory`. Speculative inference, not worth complexity.
- `process_feedback()` caller in `deliverables.py` — approval-gate trigger removed.
- `process_patterns()` caller in `unified_scheduler.py` — nightly pattern detection removed.

**Domain separation (backend processing):**
- **Platform sync**: `platform_sync_scheduler.py` → `platform_worker.py` → `platform_content`. Unchanged, clean.
- **Scheduled generation**: `unified_scheduler.py` deliverable loop → `execute_deliverable_generation()`. Unchanged, clean.
- **Signal processing**: Hourly in `unified_scheduler.py`. Unchanged. Future: revisit alongside activity patterns if needed.
- **User memory extraction**: `memory.py` scoped explicitly as user_memory service. `process_conversation()` extracts stable personal facts → `user_memory` rows. Nightly cron.
- **Session continuity**: `session_continuity.py` (new). `generate_session_summary()` moved out of `memory.py`. Chat-layer feature, not memory concern. Writes to `chat_sessions.summary`.

**Scoped session reads:**
- `_extract_deliverable_scope()` queries `chat_sessions` by `deliverable_id` FK at read time for scoped session history. No JSONB duplication of session summaries.
- `deliverable_memory` JSONB simplified to: `observations` + `goal` only.

**Size management:**
- ~500 token budget for deliverable scope section, enforced at render time in `format_for_prompt()`.
- Observations capped at last 5. No compaction needed for current JSONB schema.

**Deferred:**
- `dispatch_trigger()` / ADR-088 — defer until event triggers fire at volume.
- Nightly cron session summary changes — none needed (read-at-query replaces write-at-cron).

**Validation:** Backend processing has clean domain boundaries. Dead code removed per Discipline 2 (singular implementation). Session continuity separated from memory extraction.

### Phase 3: Frontend + Goal Mode — IMPLEMENTED (2026-03-04, ADR-091; Instructions panel upgraded 2026-03-09)

- Deliverable workspace page (`/deliverables/[id]`): scoped TP chat dominant left, collapsible right panel
- Panel tabs: Versions, Memory (observations + goal viewer), Instructions (structured editor), Sessions
- Instructions panel consolidates: Behavior directives (`deliverable_instructions`), Audience (`recipient_context`, moved from Settings), Output Format (`template_structure.format_notes`, custom type only), and a live Prompt Preview showing the composed agent context
- Mode field present on deliverable and visible in UI header badge
- Workspace chat entry point from dashboard Deliverables panel tab

**Validation:** Users can view and edit deliverable instructions across structured sections, see exactly what the agent receives via prompt preview, read accumulated memory, and chat in scoped TP sessions that inject `deliverable_instructions` + `deliverable_memory` into working memory.

**Deferred (not blocking):** Goal-mode behavioral differentiation — `mode='goal'` deliverables currently behave identically to `mode='recurring'` (same schedule fields, same generation pipeline). Distinct goal-mode lifecycle (schedule-less, milestone progression, completion state) is a future product decision. The `mode` field, schema, and UI label are in place; only the behavioral branching remains.

---

## Backend Function Changes

| Function | File | Change | Phase |
|---|---|---|---|
| POST /chat handler | routes/chat.py | Extract deliverable_id from surface_context, set on session, pass deliverable to build_working_memory | 1 |
| `build_working_memory()` | services/working_memory.py | Accept optional deliverable dict, include deliverable_instructions + deliverable_memory sections | 1 |
| `_build_headless_system_prompt()` | services/deliverable_execution.py | Include deliverable_instructions + deliverable_memory in prompt | 1 |
| `_extract_deliverable_scope()` | services/working_memory.py | Query chat_sessions by deliverable_id FK for scoped session history (replaces JSONB read) | 2 |
| `process_feedback()` | services/memory.py | **DELETED** — governance-era artifact, superseded by conversational iteration | 2 |
| `process_patterns()` | services/memory.py | **DELETED** — marginal value activity pattern detection | 2 |
| `generate_session_summary()` | services/session_continuity.py | **MOVED** from memory.py — chat-layer feature, not memory concern | 2 |
| `memory.py` | services/memory.py | Scoped explicitly as user_memory service: process_conversation + get_for_prompt only | 2 |

**What does NOT change:** `user_memory` table schema, `_write_memory()` signature, `get_or_create_chat_session` RPC, execution_strategies.py, platform_worker.py, platform_sync_scheduler.py, primitives/registry.py, thinking_partner.py (system prompt), deliverable_pipeline.py (type prompts), platform_content.py.

---

## Consequences

### Positive

- TP and headless execution see each other's work — the core quality unlock
- Clear separation: instructions (user-authored, stable) vs memory (system-accumulated, growing)
- Market-aligned naming reduces conceptual drift as landscape evolves
- Simplest schema change: 3 columns on deliverables, 1 FK on sessions, 0 new tables
- Fully backwards-compatible: empty fields = current behavior

### Negative

- Semantic overloading: "deliverable" covers recurring outputs and goal workspaces. Mitigated by UI labeling.
- 1:1 coupling: shared context across deliverables would be duplicated. Acceptable pre-PMF.
- JSONB concurrency on `deliverable_memory`: last-write-wins. Mitigated by temporal separation. See [ADR-088](ADR-088-input-gateway-work-serialization.md) for future serialization.
- Size management: `deliverable_memory` grows indefinitely. Needs compaction strategy.

### Neutral

- `user_memory` table unchanged (naming debt resolved — renamed from `user_context` in migration 084)
- `projects` ghost entity remains. Clean activation path exists.
- Existing instruction fields (`template_structure`, `type_config`, `recipient_context`) unchanged. Future consolidation possible.

---

## Naming Convention Reference

For consistency across future ADRs and code:

| Concept | Field/table name | NOT |
|---------|-----------------|-----|
| Per-deliverable behavioral directives | `deliverable_instructions` | ~~work_context~~, ~~skills~~, ~~config~~ |
| Per-deliverable accumulated knowledge | `deliverable_memory` | ~~work_context~~, ~~context~~, ~~history~~ |
| Global user knowledge | `user_memory` (table — renamed from `user_context` in migration 084) | — |
| Raw platform input | `platform_content` (table) | — |
| Assembled prompt input | Working memory (function output) | — |
| Agent capabilities | Primitives (intentionally distinct from market "tools") | — |

---

## Incremental Path Beyond This ADR

| Step | Trigger | Migration |
|------|---------|-----------|
| **This ADR** | Now | `deliverable_instructions` TEXT + `deliverable_memory` JSONB on deliverables |
| **D2 (typed files)** | JSONB unwieldy or new file types needed | `deliverable_memory` sections → rows in `workspace_files` table. `deliverable_instructions` stays as TEXT. |
| **D3 (workspace entity)** | N:1 workspace:deliverable needed | Activate `projects` or create `workspaces`. Move `sources` to workspace level. |

---

## Alternatives Considered

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| **v1: FK-scoping on user_context** | Reuses existing table | Partial unique indexes, RPC changes, constraint migration | Wrong paradigm — relational scoping, not context document |
| **Single `work_context` JSONB** | One field | Conflates instructions (user-authored) and memory (system-accumulated) | Naming blur leads to conceptual blur |
| **Activate projects table** | Clean container | Zero UI, wrong sequencing pre-PMF | Build later if N:1 needed |
| **Status quo** | Zero work | TP and headless remain blind to each other | Quality gap compounds |

---

## Risk Assessment

| Risk | Mitigation | Severity |
|---|---|---|
| Semantic overloading of 'deliverable' | UI labels: "Workspace" for goal mode | Low |
| deliverable_memory size growth | Cap injection at ~500 tokens. Compaction strategy. | Medium |
| JSONB concurrency | Temporal separation. ADR-088 for future serialization. | Low (one user) |
| Instruction fields fragmentation (template_structure + type_config + deliverable_instructions) | Document as future consolidation. Not blocking. | Low |
| Working memory token budget | Enforce budget with sub-allocation. ~500 tokens for scoped context. | Medium |

---

## Documentation Impact

| Document | Required Update | Phase |
|----------|----------------|-------|
| `docs/database/SCHEMA.md` | Add deliverable_instructions, deliverable_memory, mode; add chat_sessions.deliverable_id | 1 |
| `docs/architecture/agent-execution-model.md` | Add TP↔headless bridge via scoped instructions + memory | 1 |
| `docs/features/memory.md` | Add deliverable-scoped memory concept | 2 |
| `docs/features/sessions.md` | Add deliverable_id routing key | 1 |
| `docs/architecture/deliverables.md` | Add mode, deliverable_instructions, deliverable_memory, goal-mode lifecycle | 3 |
| `CLAUDE.md` | Add ADR-087 to key ADR references, add naming convention | 1 |
| `api/prompts/CHANGELOG.md` | Phase 4 extraction prompt change | 4 |

---

## References

- [Pre-ADR Analysis](../analysis/workspace-architecture-analysis-2026-03-02.md) — v1-v5 analysis, OpenClaw comparison
- [Development Landscape](../analysis/workspace-architecture-landscape.md) — sequencing and dependencies
- [ESSENCE.md](../ESSENCE.md) — domain model
- [ADR-038: Filesystem as Context](ADR-038-filesystem-as-context.md) — foundational model
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md) — the execution model this bridges
