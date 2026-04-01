# ADR-154: Execution Boundary Reform — Who / What / How File Separation

**Status:** Proposed  
**Date:** 2026-04-01  
**Author:** Kevin Kim  
**Supersedes:** Portions of ADR-106 (agent workspace files), ADR-117 (agent feedback/reflections), ADR-128 (agent cognitive files), ADR-149 (agent reflections.md location)  
**Extends:** ADR-138 (agents as work units), ADR-141 (unified execution), ADR-151 (context domains), ADR-152 (directory registry)

---

## Context

The workspace filesystem has accumulated files at three levels (agent, task, workspace) without a strict governing principle for which files belong where. This creates:

1. **Duplicate feedback files** — `memory/feedback.md` exists at both agent level and task level, both injected into prompts, with no clear precedence
2. **Agent files that are really execution state** — `reflections.md`, `thesis.md`, `working/*.md` are about task execution, not agent identity
3. **No cycle-to-cycle execution memory** — context tasks are told to "update entity files" but have no awareness of what they did last cycle, what's stale, or what to focus on next
4. **No domain entity management** — context domains have entity folder structures but no persistent registry of what entities exist, when they were last updated, or which are stale
5. **6+ dead agent files** — legacy migration artifacts (`goal.md`, `observations.md`, `review-log.md`, `created-agents.md`, `state.md`, `tasks.json`) that are written but never read

The root cause: files weren't assigned to levels based on a clear **who/what/how** principle.

---

## Decision

### Governing Principle: Who / What / How

Every workspace file belongs to exactly one of three concerns:

| Concern | Level | Role | Mutable by |
|---------|-------|------|------------|
| **WHO** (Agent) | `/agents/{slug}/` | Identity + methodology | User, TP, system (at creation) |
| **WHAT** (Domain) | `/workspace/context/{domain}/` | Accumulated intelligence substrate | Agent (via WriteWorkspace), pipeline (tracker) |
| **HOW** (Task) | `/tasks/{slug}/` | Work order + execution state + outputs | Pipeline, agent (during execution), TP (steering/feedback) |

If a file doesn't clearly belong to one concern, it shouldn't exist.

---

### Change 1: Agent Workspace Thinning

**After reform, agents own only identity:**

```
/agents/{slug}/
├── AGENT.md              # Identity + behavioral instructions
└── playbook-*.md         # Type-seeded methodology (e.g., playbook-outputs.md, playbook-research.md)
```

**Dissolved files:**

| File | Reason | Destination |
|------|--------|-------------|
| `thesis.md` | Redundant with domain synthesis files (`_landscape.md`, `_overview.md`) | Domain synthesis files ARE the thesis |
| `memory/reflections.md` | Execution state, not identity | → task `awareness.md` |
| `memory/feedback.md` | Per-task concern, not per-agent | → task `memory/feedback.md` (already exists, becomes sole location) |
| `memory/tasks.json` | Written but never read | Deleted |
| `memory/goal.md` | Legacy migration artifact, never read | Deleted |
| `memory/observations.md` | Legacy, superseded by feedback.md | Deleted |
| `memory/review-log.md` | Legacy, never read | Deleted |
| `memory/created-agents.md` | Legacy, coordinator mode dissolved | Deleted |
| `memory/state.md` | Legacy, never read | Deleted |
| `working/*.md` | Task execution scratch | → task `working/` (already exists) |

**Rationale:** An agent's identity is its AGENT.md (who it is) and playbooks (how it thinks). Everything else is either about the domain it works on (WHAT) or the task it's executing (HOW). When the same agent executes two different tasks, execution state should not bleed between them.

---

### Change 2: Domain Tracker (`_tracker.md`)

Each entity-bearing context domain gets a `_tracker.md` — a **pipeline-maintained materialized view** of domain contents.

```
/workspace/context/competitors/
├── _tracker.md            ← NEW: entity registry + freshness
├── _landscape.md          # Cross-entity synthesis (existing)
├── acme-corp/
│   ├── profile.md, signals.md, product.md, strategy.md
└── beta-inc/
    └── profile.md
```

#### Format

```markdown
# Entity Tracker

## Entities
| Slug | Name | Last Updated | Files | Status |
|------|------|-------------|-------|--------|
| acme-corp | Acme Corp | 2026-03-28 | profile, signals, product, strategy | active |
| beta-inc | Beta Inc | 2026-03-21 | profile | stale |
| gamma-ai | Gamma AI | — | — | discovered |

## Domain Health
- Total entities: 3
- Active (updated within cadence): 1
- Stale (overdue for update): 1
- Discovered (not yet profiled): 1
- Last synthesis update (_landscape.md): 2026-03-28
```

#### Lifecycle

- **Created by:** Pipeline, at domain scaffold time (when first context task is created for this domain). Starts with empty entity table.
- **Updated by:** Pipeline, **post-execution** of any context task that writes to this domain. Pipeline scans entity subfolders, diffs against tracker, updates timestamps/status/file counts.
- **Read by:** Pipeline, **pre-execution**. Injected into the agent's prompt so the agent knows what entities exist and which are stale.
- **Never written by:** The agent. The tracker is deterministic — derived from filesystem state, not LLM-generated.

#### Which domains get a tracker?

Only domains with `entity_type` set (i.e., entity-structured domains). Currently: `competitors`, `market`, `relationships`, `projects`, `content_research`. The `signals` domain (append-only temporal log, no entities) does NOT get a tracker.

#### Staleness calculation

An entity is "stale" if its most recent file update is older than the task's schedule cadence:
- weekly task → stale after 10 days
- monthly task → stale after 45 days
- daily task → stale after 3 days

The pipeline calculates this at scan time using the task's schedule from TASK.md.

---

### Change 3: Task Awareness (`awareness.md`)

Each task gets an `awareness.md` — the task's **cycle-to-cycle working memory**, analogous to TP's `AWARENESS.md` at workspace level.

```
/tasks/{slug}/
├── TASK.md
├── DELIVERABLE.md
├── awareness.md           ← NEW: cycle-to-cycle execution state
├── memory/
│   ├── run_log.md         # Audit trail (append-only, unchanged)
│   ├── feedback.md        # User corrections + TP evaluations (unchanged)
│   └── steering.md        # TP management notes (unchanged)
├── outputs/
└── working/
```

#### Format (context task example)

```markdown
# Task Awareness

## Last Cycle
- **Run:** 2026-03-28 09:00 UTC (v3)
- **Duration:** 45s, 6 tool rounds
- **Entities touched:** acme-corp (updated signals.md, product.md), gamma-ai (created profile.md)
- **Tools used:** WebSearch (2), ReadWorkspace (1), WriteWorkspace (3)
- **Agent reflection:** confidence=high, context_currency=good

## Domain State
- **Tracker snapshot:** 3 entities — 1 active, 1 stale (beta-inc), 1 discovered (gamma-ai → now profiled)
- **Synthesis file:** _landscape.md last updated 2026-03-28

## Next Cycle Focus
- beta-inc: stale (7 days since last update) — prioritize
- acme-corp: recent, low priority unless new signals detected
- gamma-ai: newly profiled, may need depth on product/strategy files
```

#### Format (synthesis task example)

```markdown
# Task Awareness

## Last Cycle
- **Run:** 2026-03-28 09:00 UTC (v2)
- **Duration:** 30s, 2 tool rounds
- **Output:** 2,400 words, 2 charts, 1 mermaid diagram
- **Agent reflection:** confidence=medium — competitors/beta-inc context was thin

## Context Quality
- competitors/: 3 entities, 1 stale
- signals/: 8 entries since last synthesis run

## Next Cycle Focus
- beta-inc context expected to be refreshed by track-competitors task
- Consider adding market/ domain to context reads if GTM angle requested
```

#### Lifecycle

- **Created by:** Pipeline, at task creation. Initialized with "First run — no prior cycles."
- **Updated by:** Pipeline, **post-execution**. Deterministic sections (run metadata, entities touched, tools used) written by pipeline. Agent reflection extracted from output and folded in (replaces current flow to agent `reflections.md`). "Next cycle focus" derived from domain tracker staleness.
- **Read by:** Pipeline, **pre-execution**. Injected into the agent's prompt as execution context.
- **Relationship to `run_log.md`:** `run_log.md` is the append-only audit trail (every run, forever). `awareness.md` is **current state only** — overwritten each cycle. run_log is git log; awareness is HEAD.

---

### Change 4: Pipeline Post-Run Domain Scan

Replace `_route_output_to_context_domains()` (currently just appends a signal summary) with a proper post-run scan:

```python
async def _post_run_domain_scan(client, user_id, task_slug, task_info, run_metadata):
    """Post-execution: scan domains, update trackers, update awareness."""
    
    # 1. For each domain in context_writes:
    #    - List entity subfolders in /workspace/context/{domain}/
    #    - Compare against _tracker.md
    #    - Update tracker with new/modified entities + timestamps
    
    # 2. Update task awareness.md with:
    #    - Run metadata (duration, tool rounds, tokens)
    #    - Entities touched (from WriteWorkspace calls logged during execution)
    #    - Agent reflection (extracted from output)
    #    - Next cycle focus (derived from tracker staleness)
    
    # 3. Append to run_log.md (existing, unchanged)
```

This is **deterministic** — no LLM calls. It reads filesystem state and writes structured metadata.

---

### Change 5: Task Type Registry Fixes

Stress-testing revealed missing `context_reads` for platform-signal-dependent domains:

| Task Type | Current `context_reads` | Fixed `context_reads` | Reason |
|-----------|------------------------|----------------------|--------|
| `track-relationships` | `["relationships"]` | `["relationships", "signals"]` | Needs Slack/Notion signals about contacts |
| `track-projects` | `["projects"]` | `["projects", "signals"]` | Needs platform signals about project activity |

---

### Change 6: Prompt Injection Simplification

**Current:** Pipeline gathers agent workspace context (AGENT.md, thesis.md, feedback, reflections, working notes, projects.json) + task files + domain files — overlapping, some redundant.

**After reform:**

| Prompt Section | Source | Level |
|---|---|---|
| System: Agent identity | AGENT.md | WHO |
| System: Methodology | playbook-*.md | WHO |
| System: Deliverable spec | DELIVERABLE.md | HOW (synthesis tasks only) |
| User: Task objective | TASK.md | HOW |
| User: Awareness | awareness.md | HOW |
| User: Domain tracker | _tracker.md (context tasks only) | WHAT |
| User: Accumulated context | /workspace/context/{domain}/ files | WHAT |
| User: Steering + feedback | steering.md, feedback.md | HOW |
| User: User context | IDENTITY.md, BRAND.md | Workspace |

No agent-level execution state in the prompt. Clean separation.

---

## Implementation Plan

### Phase 1: Domain Tracker + Awareness (foundation)

1. Add `_tracker.md` template to directory registry for entity-bearing domains
2. Create `_post_run_domain_scan()` replacing `_route_output_to_context_domains()`
3. Add `awareness.md` creation at task scaffold time
4. Update `awareness.md` in pipeline post-run
5. Inject `_tracker.md` + `awareness.md` into prompt via `gather_task_context()`

### Phase 2: Agent Workspace Thinning

1. Stop writing to agent `memory/reflections.md` — reflections go to task `awareness.md`
2. Stop writing to agent `memory/feedback.md` — task feedback.md is sole location
3. Stop reading agent `thesis.md` — domain synthesis files replace it
4. Remove agent `working/` reads from `load_context()` — task working/ is used instead
5. Delete dead files: `tasks.json`, `goal.md`, `observations.md`, `review-log.md`, `created-agents.md`, `state.md`

### Phase 3: Registry + Prompt Cleanup

1. Fix `context_reads` for `track-relationships` and `track-projects`
2. Simplify `gather_task_context()` — remove agent workspace context, add awareness + tracker
3. Simplify `build_task_execution_prompt()` — cleaner injection sections
4. Update `workspace-conventions.md` to v11

### Phase 4: Pipeline Tool Round Budget

1. Increase `max_tool_rounds` for context tasks (currently 5-6, needs 10-12)
2. Awareness.md "next cycle focus" limits scope — agent doesn't try to update everything, just the stale entities

---

## Consequences

### Positive
- **Agent files become trivially simple** — two files, both about identity
- **No execution state bleed** between tasks sharing the same agent
- **Deterministic entity management** — pipeline maintains tracker, not LLM
- **Cycle-to-cycle focus** — awareness.md tells the agent what's stale and what to prioritize
- **Prompt clarity** — each injection section comes from exactly one level (WHO/WHAT/HOW)
- **"Filesystem-as-product" enabled** — tracker provides visibility into accumulation health

### Negative
- **Migration work** — existing agent files need cleanup (Phase 2)
- **Post-run scan adds latency** — filesystem scan after every context task execution (mitigated: scan is just Postgres queries, sub-100ms)
- **awareness.md could grow** — needs same discipline as run_log (current-state-only, not append)

### Risks
- **Playbooks at agent level vs methodology at task level?** Currently playbooks are agent-level (WHO: how this type of agent thinks). This is correct — methodology is part of identity, not per-task. A Competitive Intelligence agent uses the same research methodology regardless of which task it's executing.
- **What if an agent has no tasks?** Agent still has AGENT.md + playbooks. It's a dormant identity. This is fine — agents are pre-scaffolded (ADR-140), many start without tasks.

---

## Relationship to Other ADRs

- **ADR-138** (Agents as Work Units): This ADR refines 138's "agents are WHO, tasks are WHAT" by enforcing it at the file level. 138 established the conceptual split; 154 cleans up the filesystem to match.
- **ADR-141** (Unified Execution): Pipeline changes (post-run scan, awareness update) extend 141's mechanical pipeline model.
- **ADR-149** (Task Lifecycle): Reflections move from agent to task. Task memory files (feedback, steering) preserved. DELIVERABLE.md unchanged.
- **ADR-151/152** (Domains/Registry): `_tracker.md` extends domain structure. Registry unchanged — tracker is a pipeline-maintained file, not a registry addition.
- **ADR-117** (Feedback Substrate): Agent-level feedback dissolved. Task-level feedback is sole location. Feedback distillation (nightly cron) would need to read from task feedback files instead of agent feedback files.

---

## File Layout Summary (After Reform)

```
/workspace/                          # User context + accumulated intelligence
├── IDENTITY.md, BRAND.md            # User identity + output style
├── AWARENESS.md                     # TP situational notes
├── preferences.md, notes.md         # Learned preferences, standing instructions
├── uploads/                         # User-uploaded reference material
├── outputs/                         # Promoted agent deliverables
│   ├── reports/, briefs/, content/
└── context/                         # ACCUMULATED CONTEXT (the product)
    ├── competitors/
    │   ├── _tracker.md              # Entity registry (pipeline-maintained)
    │   ├── _landscape.md            # Cross-entity synthesis (agent-written)
    │   └── {entity}/               # Per-entity files
    ├── market/
    │   ├── _tracker.md
    │   ├── _overview.md
    │   └── {entity}/
    ├── relationships/
    │   ├── _tracker.md
    │   ├── _portfolio.md
    │   └── {entity}/
    ├── projects/
    │   ├── _tracker.md
    │   ├── _status.md
    │   └── {entity}/
    ├── content_research/
    │   ├── _tracker.md
    │   └── {entity}/
    └── signals/                     # Cross-domain temporal log (no tracker)
        └── {date}.md

/agents/{slug}/                      # WHO — identity only
├── AGENT.md                         # Name, domain, personality, instructions
└── playbook-*.md                    # Type-seeded methodology

/tasks/{slug}/                       # HOW — work order + execution state
├── TASK.md                          # Charter: objective, process, schedule
├── DELIVERABLE.md                   # Quality contract (synthesis tasks)
├── awareness.md                     # Cycle-to-cycle execution state (pipeline-maintained)
├── memory/
│   ├── run_log.md                   # Audit trail (append-only)
│   ├── feedback.md                  # User corrections + TP evaluations
│   └── steering.md                  # TP management notes for next cycle
├── outputs/
│   ├── latest/                      # Current deliverable
│   └── {date}/                      # Run history
└── working/                         # Ephemeral scratch (24h TTL)
```
