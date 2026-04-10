# ADR-149: Task Lifecycle Architecture — TP as Context Manager

**Status:** Phase 1-5 Implemented (Phase 6 frontend deferred)  
**Date:** 2026-03-31  
**Supersedes:** Portions of ADR-145 (task type registry stays, execution model evolves)  
**Extends:** ADR-138 (agents as work units), ADR-140 (agent workforce model), ADR-141 (unified execution), ADR-144 (inference-first shared context), ADR-146 (primitive hardening)

---

## Context

ADR-138 established the Agent → Task hierarchy: agents are WHO (identity, capabilities), tasks are WHAT (objective, cadence, delivery). ADR-145 added the task type registry with deterministic process definitions. ADR-141 built the mechanical execution pipeline.

What's missing: **task mode is decorative** (`recurring`/`goal`/`reactive` column exists but affects nothing), **deliverable quality expectations are loosely scaffolded** (success criteria as a flat list), **user feedback routes to agents not tasks**, **the pipeline is single-agent per step with no orchestrative awareness of the final deliverable**, and **TP has no post-run management loop**. The pipeline runs, outputs accumulate, nobody evaluates.

Additionally, **agent self-assessment exists but is disconnected** — agents produce `## Contributor Assessment` blocks (ADR-128: mandate, domain fitness, context currency, output confidence) that get stripped before delivery and written to `/agents/{slug}/memory/self_assessment.md`. But TP never reads these for task-level decisions. The evaluation loop is open.

The result: tasks execute on schedule but don't improve. User edits don't inform future runs at the task level. Goal tasks never self-complete. Agent reflections are written and ignored at the task level. The system generates but doesn't manage.

## Decision

### Core Thesis: TP is a Context Manager

TP's role is managing what's in the filesystem — where feedback goes, what gets refined, when work progresses. Every primitive is a filesystem write with judgment about *what* to write and *where*.

Four architectural commitments:

1. **Two registries stay fixed and deterministic.** Agent registry (AGENT_TYPES) defines capabilities and methodology per worker. Task type registry (TASK_TYPES) defines process steps and output specs per work type. Neither changes at runtime. They are TP's scaffolding knowledge — the equivalent of SKILL.md files.

2. **Task instances are living knowledge objects.** A task isn't a scheduling row — it's a managed filesystem with a quality contract, feedback history, deliverable spec (including expected assets), and TP management notes. The filesystem IS the system state.

3. **Mode is TP's management posture, not pipeline configuration.** The pipeline stays mechanical (read files, execute steps, save output). Mode informs TP's judgment: when to deliver, when to evaluate, when to steer, when to complete.

4. **Feedback is the single gateway for all external signals. Evaluation is the single gateway for all internal signals.** User corrections (feedback) and TP quality judgments (evaluation) both write to `memory/feedback.md` — same file, distinguished by source tag. The consuming side (DELIVERABLE.md inference) reads all entries equally.

### Terminology Unification

Three distinct concepts, system-wide:

| Term | Definition | Scope | Actor | Target file |
|---|---|---|---|---|
| **Feedback** | User corrections routed to appropriate scope (edits, conversation) | Workspace / Agent / Task | User → TP routes | `feedback.md` at appropriate scope |
| **Evaluation** | TP judges task output against DELIVERABLE.md quality spec | Task | TP | `/tasks/{slug}/memory/feedback.md` (source: `evaluation`) |
| **Reflection** | Agent self-assesses its own fitness and confidence post-run | Agent | Agent | `/agents/{slug}/memory/reflections.md` |

**Renames (code + filesystem):**

| Current | Renamed | Reason |
|---|---|---|
| `## Contributor Assessment` (output block) | `## Agent Reflection` | Assessment is ambiguous — reflection is self-directed |
| `_extract_contributor_assessment()` | `_extract_agent_reflection()` | Align with terminology |
| `_append_self_assessment()` | `_append_agent_reflection()` | Align with terminology |
| `_ASSESSMENT_POSTAMBLE` | `_REFLECTION_POSTAMBLE` | Align with terminology |
| `/agents/{slug}/memory/self_assessment.md` | `/agents/{slug}/memory/reflections.md` | Clear distinction from evaluation |
| `contributor_assessment` (variable names) | `agent_reflection` | Align with terminology |

**Evaluation** is always TP's judgment, at task scope, against DELIVERABLE.md.  
**Reflection** is always the agent's self-awareness, at agent scope, for identity development.  
**Feedback** is always user signal, routed by TP to the appropriate scope.

No concept overlap. No ambiguity.

---

### Task Filesystem (Canonical Structure)

Extends workspace-conventions.md v5 (ADR-142/143). The task filesystem is the complete working state of a task — no hidden DB columns driving behavior.

```
/tasks/{slug}/
├── TASK.md                    # Charter: objective, process, type_key, mode, schedule
├── DELIVERABLE.md             # Quality contract: output spec + assets + inferred preferences
├── memory/
│   ├── run_log.md             # Execution history (append-only, exists today)
│   ├── feedback.md            # Task-level signals (user feedback + TP evaluations)
│   └── steering.md            # TP's management notes for next cycle
├── outputs/
│   ├── latest/                # Current deliverable (mode-dependent semantics)
│   │   ├── output.md          # Primary content
│   │   ├── output.html        # Composed HTML
│   │   ├── manifest.json      # Run metadata, asset manifest, delivery status
│   │   └── assets/            # Rendered assets (charts, diagrams, images)
│   │       ├── chart-1.svg    # Named by type + sequence
│   │       ├── diagram-1.svg
│   │       └── asset-manifest.json  # Asset inventory with render metadata
│   └── {date}/                # Run history (timestamped folders, same structure)
└── working/                   # Ephemeral scratch (24h TTL)
```

**Mode determines `outputs/` semantics:**

| Mode | `latest/` behavior | `{date}/` behavior |
|---|---|---|
| **Recurring** | Pointer to most recent run (overwritten each cycle) | Each run creates a new dated folder. Full archive. |
| **Goal** | THE evolving deliverable (revised in-place each cycle) | Revision history (v1, v2, v3 snapshots) |
| **Reactive** | Last triggered output (overwritten per trigger) | Each trigger creates a dated folder. Sparse archive. |

**Filesystem conventions per mode** are documented in TASK.md itself:

```markdown
# Weekly Competitive Briefing

**Mode:** recurring
**Filesystem:** Each run produces new output in outputs/{date}/. Latest always points to most recent.
```

---

### DELIVERABLE.md — First-Class Quality Contract (Including Assets)

DELIVERABLE.md is to task quality what IDENTITY.md is to user context — a living document that starts from scaffolding and tightens through inference from user behavior.

**It specifies outputs AND assets together.** Assets (charts, diagrams, images) are not an afterthought of rendering — they are part of the deliverable specification.

**Initial scaffold** (from task type registry at creation):

```markdown
# Deliverable Specification

## Expected Output
- Format: HTML document, 2000-3000 words
- Layout: Executive summary → Key Findings → Analysis → Implications → Sources

## Expected Assets
- Trend chart: at least 1 chart visualizing quantified trend data (line or bar)
- Comparison chart: at least 1 chart comparing competitors/categories (bar or radar)
- Positioning diagram: 1 mermaid diagram showing competitive positioning or market map
- Data tables: raw data backing charts preserved as markdown tables below each chart

## Quality Criteria
- Every claim has inline source citation
- Minimum 3 competitors analyzed per cycle
- Forward-looking implications, not just historical reporting
- Charts must have labeled axes, legends, and a 1-sentence interpretation

## Audience
Leadership team. Board-level polish. Assume they've read last week's report.

## User Preferences (inferred)
<!-- Populated by feedback inference. Empty at creation. -->
```

The task type registry provides the structured spec:

```python
# In TASK_TYPES registry (task_types.py):
"competitive-intel-brief": {
    "process": [...],
    "default_deliverable": {
        "output": {
            "format": "html",
            "word_count": "2000-3000",
            "layout": ["Executive summary", "Key Findings", "Analysis", "Implications", "Sources"],
        },
        "assets": [
            {"type": "chart", "subtype": "trend", "min_count": 1, "description": "Quantified trend data"},
            {"type": "chart", "subtype": "comparison", "min_count": 1, "description": "Competitor comparison"},
            {"type": "mermaid", "subtype": "positioning", "min_count": 1, "description": "Market positioning map"},
        ],
        "quality_criteria": [
            "Every claim has inline source citation",
            "Minimum 3 competitors analyzed",
            "Forward-looking implications",
        ],
    },
}
```

`build_deliverable_md_from_type()` generates DELIVERABLE.md from this structured spec at task creation.

---

### Process as Deliverable-Driven Multi-Agent Orchestration

The process definition in TASK_TYPES is already multi-agent (ordered steps with different agent types). ADR-149 makes the process **reflexive to the deliverable spec** — every agent in the chain knows what the final output should look like.

Each process step's prompt context includes DELIVERABLE.md:
- **Research steps**: "Your output feeds the final deliverable described in DELIVERABLE.md. Include data tables and quantifiable findings that can become charts."
- **Compose steps**: "Produce the final deliverable matching DELIVERABLE.md spec — format, assets, quality criteria."
- **All steps**: steering.md and feedback.md injected as additional context

The asset rendering pipeline (`render_inline_assets`) runs post-generation on the final step's output, converting inline mermaid → SVG and data tables → charts per DELIVERABLE.md's Expected Assets section.

---

### Evaluation Architecture — Feedback + Evaluation as Unified Pipeline

#### Three Concepts, Clean Separation

**Feedback** (user → system): User edits an output or says something in conversation. TP captures it and routes to the right scope via `UpdateContext`.

**Evaluation** (TP → system): After a task run completes, TP reads the output against DELIVERABLE.md and produces a quality judgment. This is the post-run management loop.

**Reflection** (agent → agent): The agent self-assesses during generation (ADR-128). This stays at agent scope for identity development. Renamed from "contributor assessment" / "self-assessment" for clarity.

#### Evaluation Triggers by Mode

Every task run completes by writing a structured run result to the workspace. What happens next depends on mode:

**Goal mode — Evaluation after every run (mandatory)**
```
Pipeline completes → writes run result to outputs/ + run_log.md
    ↓
TP evaluation triggered (synchronous — part of the execution flow)
    ↓
ManageTask(action="evaluate"): TP reads output + DELIVERABLE.md
    ↓
Decision:
    ├── Criteria met → ManageTask(action="complete") → final delivery → task done
    ├── Gaps found → ManageTask(action="steer") → write steering.md → next run incorporates
    └── Uncertain → TP escalates to user ("Should I keep refining or deliver?")
    ↓
Evaluation written to memory/feedback.md (source: evaluation)
    ↓
Next run reads updated steering.md + feedback.md → closes the loop
```

**Recurring mode — Evaluation periodic (TP heartbeat) + after user edits**
```
Pipeline completes → writes run result → auto-delivers
    ↓
TP evaluates on heartbeat (not every run — cost-conscious)
    OR: user edits the output → triggers TP evaluation
    ↓
ManageTask(action="evaluate"): TP reads recent outputs + DELIVERABLE.md + edit history
    ↓
Assessment: quality trajectory (improving? degrading? stable?)
    ├── Stable → no action, evaluation logged
    ├── Degrading → ManageTask(action="steer") → steering.md for next cycle
    └── Improving → trigger DELIVERABLE.md inference (tighten the spec)
    ↓
Evaluation written to memory/feedback.md (source: evaluation)
```

**Reactive mode — No evaluation (dispatch and done)**
```
Pipeline completes → delivers immediately → next_run_at cleared
    ↓
No TP evaluation triggered
    ↓
But: if user edits the delivered output, those edits still accumulate in feedback.md
    → next trigger benefits from inferred preferences
```

#### Unified Write Target

Both feedback and evaluation write to the same file: `/tasks/{slug}/memory/feedback.md`. Entries are tagged:

```markdown
## User Feedback (2026-03-31 14:00, source: user_edit)
- Shortened executive summary from 8 to 3 sentences
- Added competitor Acme Corp section

## Evaluation (2026-03-31 09:15, source: evaluation)
- Criteria: 2/3 met. Missing: forward-looking implications
- Asset coverage: 2/3 (missing positioning diagram)
- Quality: stable. No intervention needed beyond steering.

## User Feedback (2026-03-28 10:00, source: user_conversation)
- "Charts need better axis labels" — routed from chat
```

DELIVERABLE.md inference reads all entries regardless of source. The distinction is provenance (who said it), not treatment (what we do with it).

#### Agent Reflection (Renamed, Preserved)

Agent reflection (formerly "contributor assessment" / "self-assessment") continues at agent scope:

- Pipeline extracts `## Agent Reflection` block from agent output
- Writes to `/agents/{slug}/memory/reflections.md` (rolling 5 entries)
- Agent reads this on subsequent runs for self-awareness
- **Not used for task-level decisions** — that's evaluation's job

This is a clean separation: reflection = agent identity development (how I'm growing as a researcher). Evaluation = task quality management (does this brief meet its spec).

---

### Primitive Architecture

#### UpdateContext (ADR-146 — Extended)

Already supports five targets. `target="task"` handler extended:

```python
UpdateContext(
    target="task",
    task_slug="weekly-briefing",
    text="Charts need axis labels and a one-sentence interpretation",
    feedback_target="deliverable",  # → memory/feedback.md → inference → DELIVERABLE.md
)
```

Same primitive for user feedback routing AND TP evaluation writes:

```python
# User feedback (routed by TP):
UpdateContext(target="task", task_slug="...", text="Too long, cut exec summary", feedback_target="deliverable")

# TP evaluation (written by TP after ManageTask evaluate):
UpdateContext(target="task", task_slug="...", text="2/3 criteria met. Missing: implications.", feedback_target="deliverable")
```

**`feedback_target` enum update:**
- Current: `criteria`, `objective`, `output_spec`, `run_log`
- Extended: + `deliverable` — writes to `memory/feedback.md` (primary path for all quality signals)
- The existing targets (`criteria`, `objective`, `output_spec`) are preserved for direct TASK.md mutations when TP needs to change the charter itself (rare).

#### ManageTask (ADR-146 — Extended)

Existing actions: `trigger`, `update`, `pause`, `resume`.

New actions:

| Action | What TP does | When triggered |
|---|---|---|
| `evaluate` | Read latest output + DELIVERABLE.md → quality judgment → write to feedback.md | Goal: every run. Recurring: heartbeat/post-edit. Reactive: never. |
| `steer` | Write cycle-specific guidance to `memory/steering.md` | After evaluation finds gaps. TP judgment. |
| `complete` | Mark task done, final delivery, clear scheduling | Goal: criteria met. Manual: user request. |

**Evaluate implementation**: LLM call (Haiku for cost) comparing output against DELIVERABLE.md. Returns structured assessment: `{criteria_met: "2/3", gaps: ["missing implications"], asset_coverage: "2/3", quality_trend: "stable"}`. Auto-writes to `memory/feedback.md` with `source: evaluation`.

---

### Pipeline Changes

The pipeline (ADR-141 `execute_task()` + `_execute_pipeline()`) stays mechanical. Changes are what it reads and how it writes.

#### New Context Injection (All Modes)

```python
# After reading TASK.md (existing):
deliverable_spec = await tw.read("DELIVERABLE.md")     # Quality contract + asset spec
steering_notes = await tw.read("memory/steering.md")     # TP's cycle-specific guidance
task_feedback = await tw.read("memory/feedback.md")      # Recent corrections + evaluations

# Injected into build_task_execution_prompt():
# - DELIVERABLE.md → system prompt: "Output must match this specification"
# - steering.md → user message: "For this specific run, also consider..."
# - feedback.md (last 3 entries) → user message: "Recent corrections to incorporate"
```

#### Mode-Specific Output Write Strategy

```python
mode = task_info.get("mode", "recurring")

if mode == "recurring":
    await tw.save_output(draft, agent_slug, date_folder=date_folder)
    await tw.write("outputs/latest/output.md", draft)  # Overwrite latest

elif mode == "goal":
    prior = await tw.read("outputs/latest/output.md")
    if prior:
        await tw.write(f"outputs/{date_folder}/output.md", prior)  # Archive prior version
    await tw.write("outputs/latest/output.md", draft)  # Update latest (THE deliverable)

elif mode == "reactive":
    await tw.save_output(draft, agent_slug, date_folder=date_folder)
    await tw.write("outputs/latest/output.md", draft)
```

#### Goal Mode: Prior Output as Primary Context

```python
if mode == "goal":
    prior_output = await tw.read("outputs/latest/output.md")
    if prior_output:
        goal_context = (
            "## Prior Output (YOUR PRIMARY INPUT)\n"
            "You are revising this deliverable. Improve based on steering notes "
            "and feedback. Build on what exists — do not start from scratch.\n\n"
            f"{prior_output[:8000]}\n"
        )
```

#### Asset Manifest

After `render_inline_assets()`, rendered assets cataloged for evaluation:

```python
asset_manifest = {
    "rendered_at": now.isoformat(),
    "assets": [
        {"type": "chart", "subtype": "bar", "path": "assets/chart-1.svg"},
        {"type": "mermaid", "subtype": "flowchart", "path": "assets/diagram-1.svg"},
    ],
    "expected": deliverable_spec_assets,  # From DELIVERABLE.md
    "coverage": "2/3",
}
await tw.write(f"outputs/{folder}/assets/asset-manifest.json", json.dumps(asset_manifest))
```

---

### Feedback Inference — Task Deliverable Scope

Same pattern as `context_inference.py` (ADR-144), scoped to task deliverable quality.

```python
# api/services/task_deliverable_inference.py (new)

async def infer_task_deliverable_preferences(
    client, user_id: str, task_slug: str
) -> str | None:
    """Read task feedback.md → infer patterns → merge into DELIVERABLE.md.
    
    Called by TP (via judgment after evaluation, or after feedback accumulation).
    Not a mechanical cron — TP decides when enough signal has accumulated.
    """
```

TP triggers this after feedback accumulates — not on every edit, but when TP judges there's enough new signal.

---

### Complete Flow (Example: Goal-Mode Due Diligence Report)

```
Day 1: Task created (goal mode)
├── TP reads type registry → scaffolds TASK.md + DELIVERABLE.md
├── DELIVERABLE.md: comprehensive report, 3 criteria, 2 expected assets
├── Pipeline executes: research → compose → render → save to outputs/latest/
├── TP evaluation (mandatory for goal mode):
│   ManageTask(action="evaluate") → "1/3 criteria met. Missing: financial analysis, risk assessment"
│   ManageTask(action="steer") → steering.md: "Next run: focus on financial data and risk factors"
└── Evaluation written to feedback.md (source: evaluation)

Day 3: Pipeline runs again
├── Reads: DELIVERABLE.md + steering.md + prior output (goal mode: revision)
├── Agent revises: adds financial analysis, deepens risk section
├── TP evaluation: "2/3 criteria met. Missing: risk mitigation recommendations"
├── TP steers: "Next run: add concrete mitigation strategies for top 3 risks"
└── feedback.md grows (evaluation entries accumulate)

Day 5: Pipeline runs again
├── Agent revises: adds mitigation strategies, all criteria addressed
├── TP evaluation: "3/3 criteria met. Asset coverage 2/2. Ready for delivery."
├── ManageTask(action="complete") → status=completed, final delivery triggered
└── Task done. No more scheduled runs.
```

---

## Terminology Migration (Clean Slate)

Pre-users, we are aggressive about terminology purity. DB data wipe is acceptable.

### Code Renames

| File | Current | Renamed |
|---|---|---|
| `api/services/agent_pipeline.py` | `_ASSESSMENT_POSTAMBLE` | `_REFLECTION_POSTAMBLE` |
| `api/services/agent_pipeline.py` | `_CRITERIA_EVAL_SECTION` | stays (this is injected into reflection prompt, criteria eval is accurate) |
| `api/services/agent_execution.py` | `_extract_contributor_assessment()` | `_extract_agent_reflection()` |
| `api/services/agent_execution.py` | `_append_self_assessment()` | `_append_agent_reflection()` |
| `api/services/agent_execution.py` | `_ASSESSMENT_BLOCK_RE` | `_REFLECTION_BLOCK_RE` |
| `api/services/agent_execution.py` | `_ASSESSMENT_FIELDS_RE` | `_REFLECTION_FIELDS_RE` |
| `api/services/task_pipeline.py` | `contributor_assessment` (variable) | `agent_reflection` |
| `api/services/agent_creation.py` | `self_assessment.md` seed | `reflections.md` seed |
| `api/services/workspace.py` | `self_assessment.md` references | `reflections.md` references |
| `api/services/composer.py` | assessment references | reflection references |

### Filesystem Renames

| Current path | Renamed path |
|---|---|
| `/agents/{slug}/memory/self_assessment.md` | `/agents/{slug}/memory/reflections.md` |

### Output Block Rename

| Current | Renamed |
|---|---|
| `## Contributor Assessment` | `## Agent Reflection` |

---

## Phases

### Phase 1: Terminology Unification + Task Filesystem
- Rename assessment → reflection across all code (see table above)
- Rename `self_assessment.md` → `reflections.md` in workspace
- Add DELIVERABLE.md generation to task scaffold (`build_deliverable_md_from_type()`)
- `default_deliverable` field in TASK_TYPES registry
- Seed `memory/steering.md` (empty) and `memory/feedback.md` (empty) at creation
- Clean slate existing test data if needed for filesystem migration

### Phase 2: Pipeline Reads DELIVERABLE.md + Mode-Aware Output
- Task pipeline reads DELIVERABLE.md + steering.md + feedback.md as execution context
- Goal mode: inject prior output as primary context, write to `latest/` (revise pattern)
- Recurring mode: new `{date}/` folder + overwrite `latest/` (append pattern)
- Reactive mode: `{date}/` + overwrite `latest/`, clear `next_run_at`
- Asset manifest written to output folders after `render_inline_assets()`
- Process steps receive DELIVERABLE.md context (deliverable-driven orchestration)

### Phase 3: Evaluation Architecture
- ManageTask `action="evaluate"` — TP reads output + DELIVERABLE.md → writes to feedback.md
- ManageTask `action="steer"` — writes to steering.md
- ManageTask `action="complete"` — marks goal task done, triggers final delivery
- Evaluation triggers: goal=every run, recurring=heartbeat/post-edit, reactive=never
- TP prompt: mode-aware evaluation guidance

### Phase 4: Feedback Routing + Evaluation via UpdateContext
- Extend `_handle_task_feedback()`: `feedback_target="deliverable"` → `memory/feedback.md`
- User feedback and TP evaluations both route through UpdateContext(target="task")
- Same primitive, same file, distinguished by source tag in entry
- TP prompt: feedback scope classification guidance

### Phase 5: Task Deliverable Inference
- `task_deliverable_inference.py` — feedback.md → DELIVERABLE.md inference
- Same architecture as `context_inference.py` (ADR-144), task-scoped
- TP triggers after feedback accumulation (judgment, not cron)
- DELIVERABLE.md "User Preferences (inferred)" section evolves

### Phase 6: Frontend Surfacing
- Task detail page: DELIVERABLE.md visible and editable
- Feedback history visible (user edits + TP evaluations, distinguished by source)
- Mode-specific UI: goal tasks show criteria progress; recurring show quality trajectory
- Asset coverage indicator from asset-manifest.json
- Steering notes visible

### Phase 7: Accumulation-First Execution (ADR-173)

Phase 7 extends the prior-output injection model from goal mode to all task modes. Currently `prior_output` is injected only for goal tasks ("You are revising this deliverable"). Phases 7a-7c generalize this to recurring and reactive tasks using `sys_manifest.json` as the mediating artifact.

**Phase 7a (Prompt layer — implemented 2026-04-10):**
- Task pipeline system prompt gains explicit "Accumulation-First Execution" section stating: read workspace before generating, check `outputs/latest/` before calling RuntimeDispatch, produce the delta not the full regeneration.
- TP gains search-first posture: scan workspace before proposing task triggers or generating content.
- See: `api/services/task_pipeline.py` (`build_task_execution_prompt`), `api/agents/tp_prompts/tools.py`, `api/agents/tp_prompts/base.py`.

**Phase 7b (Manifest injection — proposed):**
- `_build_prior_output_brief()` in `task_pipeline.py` reads `outputs/latest/sys_manifest.json`, calls staleness detection from compose substrate, formats a ~800-token generation brief summarizing: what sections exist, which are stale, what assets are present.
- Brief injected into `build_task_execution_prompt()` for ALL task modes (not just goal).
- `TaskWorkspace.get_latest_manifest()` helper for structured manifest access.
- Graceful degradation: no manifest = fall back to current full-generation behavior.

**Phase 7c (Forward-looking handoff — proposed):**
- `sys_manifest.json` gains `generation_gaps` field: what DELIVERABLE.md declared that wasn't produced, with reasons (asset-already-exists, section-current, skipped-no-source-data).
- This is the handoff note to the next run — the next cycle reads it to understand what its predecessor decided to skip and why.
- `awareness.md` references the manifest path, so the agent locates it without folder scanning.

---

## Documentation Impact

### Critical (Update alongside implementation)

| Document | What changes |
|---|---|
| `docs/architecture/workspace-conventions.md` | Extend `/tasks/{slug}/` structure: DELIVERABLE.md, memory/feedback.md, memory/steering.md, outputs/latest/, asset manifests, mode-dependent semantics. Rename self_assessment.md → reflections.md in agent section. |
| `docs/architecture/SERVICE-MODEL.md` | Add DELIVERABLE.md as entity. Update execution flow (Layer 2: pipeline reads new files; Layer 3: TP evaluation loop). Add evaluation/feedback/reflection terminology definitions. |
| `docs/architecture/task-type-orchestration.md` | Document DELIVERABLE.md seeding from registry, asset spec handling, deliverable-driven process steps, mode-aware output storage. |
| `docs/architecture/agent-execution-model.md` | Rename assessment → reflection. Add post-run evaluation flow. Describe TP management loop. |
| `api/prompts/CHANGELOG.md` | New entries for: reflection rename in prompts, DELIVERABLE.md injection, evaluation prompt, steering context injection. |

### High (Update after adoption)

| Document | What changes |
|---|---|
| `docs/features/task-types.md` | Add DELIVERABLE.md asset specs to each task type definition. Document how types seed deliverable contracts. |
| `docs/architecture/FOUNDATIONS.md` | Extend Axiom 2 (Perception) to describe task-level feedback loop. Add evaluation as named concept in intelligence layers. |
| `docs/design/FEEDBACK-WORKFLOW-REDESIGN.md` | Validate against ADR-149. Promote to `docs/architecture/feedback-architecture.md`. Add evaluation as second signal source alongside user feedback. |
| `docs/architecture/supervision-model.md` | Update TP supervisory role: evaluation triggers, mode-aware management posture. |

### Medium (Terminology sweep)

| Document | What changes |
|---|---|
| `docs/ESSENCE.md` | Minor — verify task lifecycle language, add evaluation concept if missing. |
| `docs/features/memory.md` | Clarify agent memory (reflections.md) vs. task memory (feedback.md). |
| `docs/features/agent-modes.md` | Clarify mode is on tasks not agents (ADR-138). Mode-as-posture framing. |
| `docs/architecture/agents.md` | Rename assessment → reflection in agent identity section. |

### No Change Needed

- `docs/NARRATIVE.md` — remains conceptually valid
- `docs/architecture/README.md` — index only
- Integration docs, privacy docs, blog docs

---

## Consequences

### Positive
- Tasks improve with tenure — the core product promise, now structurally supported
- Mode becomes meaningful — distinct lifecycle semantics with explicit evaluation triggers
- Feedback + evaluation unified — single pipeline, single target file, different sources
- Assets are first-class — specified in DELIVERABLE.md, tracked per-run, refinable through feedback
- Terminology is clean — reflection (agent), evaluation (TP/task), feedback (user) — no ambiguity
- TP empowered as context manager — judgment-based routing, not hardcoded workflows
- Filesystem-first — all state visible, inspectable, self-documenting per-task

### Negative
- More LLM calls — evaluation (Haiku per goal run, periodic for recurring) + inference add cost
- TP prompt complexity — mode-aware evaluation + feedback scope routing requires careful prompting
- DELIVERABLE.md drift — mitigated by 10-preference cap + contradiction removal in inference

### Risks
- TP feedback scope judgment could misroute. Mitigation: start conservative (edit-based → task scope; conversational → agent scope), expand with testing.
- Goal completion assessment unreliable for subjective criteria. Mitigation: TP escalates to user when uncertain.
- Asset coverage tracking creates false expectations. Mitigation: asset specs from type registry (tested), not user invention.

---

## Key Files

| Concern | Location |
|---|---|
| Task type registry (extended: `default_deliverable`) | `api/services/task_types.py` |
| Agent type registry (unchanged) | `api/services/agent_framework.py` |
| Task pipeline (extended: reads DELIVERABLE.md, mode-aware output) | `api/services/task_pipeline.py` |
| Task workspace (extended: `latest/` semantics) | `api/services/task_workspace.py` |
| DELIVERABLE.md scaffold | `api/services/task_types.py` (`build_deliverable_md_from_type()`) |
| Task deliverable inference (new) | `api/services/task_deliverable_inference.py` |
| ManageTask primitive (extended: evaluate, steer, complete) | `api/services/primitives/manage_task.py` |
| UpdateContext (extended: feedback_target="deliverable") | `api/services/primitives/update_context.py` |
| Agent reflection extraction (renamed) | `api/services/agent_execution.py` |
| Agent reflection prompt (renamed) | `api/services/agent_pipeline.py` |
| Feedback distillation (agent-level, preserved) | `api/services/feedback_distillation.py` |
| Asset rendering (unchanged) | `api/services/render_assets.py` |
| TP prompt (mode-aware management + evaluation) | `api/agents/thinking_partner.py` |
| Workspace conventions (extended) | `docs/architecture/workspace-conventions.md` |

## Relationship to Existing ADRs

- **ADR-128** (Multi-Agent Coherence): Agent self-assessment renamed to "reflection." Preserved for agent identity development. Task-level evaluation is a new, higher-level layer. Clean scope separation: reflection = agent, evaluation = task.
- **ADR-138** (Agents as Work Units): Preserved. Agent → Task hierarchy unchanged.
- **ADR-140** (Agent Workforce): Preserved. Agent registry stays fixed.
- **ADR-141** (Unified Execution): Extended. Pipeline reads DELIVERABLE.md, steering.md, feedback.md. Mode-aware output write strategy. Process steps gain deliverable-awareness.
- **ADR-144** (Inference-First Shared Context): Pattern extended to third scope. Workspace (IDENTITY.md) → Agent (feedback.md) → Task (DELIVERABLE.md).
- **ADR-145** (Task Type Registry): Extended. Registry gains `default_deliverable` field.
- **ADR-146** (Primitive Hardening): Extended. ManageTask gains `evaluate`, `steer`, `complete`. UpdateContext `feedback_target="deliverable"` routes to `memory/feedback.md`. No new primitives — P1-P5 upheld.
- **ADR-148** (Output Artifact Architecture): Preserved. Asset manifest adds structured tracking for TP evaluation.
