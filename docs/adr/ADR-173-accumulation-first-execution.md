# ADR-173: Accumulation-First Execution

**Date:** 2026-04-10
**Status:** Implemented (Phase 1 — prompt layer)
**Authors:** KVK, Claude
**Supersedes:** Nothing (names and formalizes an implicit principle across ADR-119, ADR-149, ADR-159, ADR-170)
**Extends:** ADR-119 (Workspace Filesystem Architecture), ADR-149 (Task Lifecycle / DELIVERABLE.md), ADR-159 (Filesystem-as-Memory), ADR-170 (Compose Substrate)

---

## Context

YARNNN's infrastructure was already built around accumulation: output folders accumulate by date (ADR-119), `sys_manifest.json` records section provenance with staleness signals (ADR-170), DELIVERABLE.md declares the quality target independent of any single run (ADR-149), and the compact index gives TP a filesystem-first view of the workspace (ADR-159).

What was missing was the explicit behavioral principle that unifies these mechanisms. Agents and TP were generating outputs without first reading what already existed — effectively starting from scratch each run. This meant:

- **Unnecessary regeneration cost.** Assets (hero images, charts) were re-generated every run even when the source data hadn't changed.
- **Output drift.** Full regeneration discards prior well-crafted sections and introduces variance.
- **Missed accumulation value.** The moat (ADR-072) requires that each cycle builds on the last. An agent that ignores prior output cannot compound quality.
- **TP proposing work that's already done.** Without reading the workspace first, TP would propose new task runs when a recent output was still current.

This ADR names and formalizes the principle. The infrastructure was ready; the prompt layer and behavioral guidance needed to reflect it.

---

## Decision

### The Governing Principle

> **Before producing anything, read the workspace. The gap between what exists and what DELIVERABLE.md requires is the only work to do.**

This single rule governs all generative behavior — task execution, TP responses, asset generation, and context updates. It applies equally to headless agents running scheduled tasks and to TP responding in conversation.

### Three Operational Axioms

**Axiom 1: The workspace holds current state.**
The filesystem is the agent's mind across runs. `outputs/latest/`, `sys_manifest.json`, domain context files, memory/*.md — these are not archives, they are the current understanding. An agent that ignores them is amnesiac.

**Axiom 2: DELIVERABLE.md is the convergence target.**
DELIVERABLE.md (ADR-149) declares *what the output should look like when done* — not what to do. The agent reads DELIVERABLE.md, reads the current output folder, computes the gap, and fills it. This is convergence toward a declared target state, not execution of a procedure.

**Axiom 3: The gap is the only work.**
A section that was accurate last run and whose source data hasn't changed should be preserved, not regenerated. A section with stale source data gets updated. A missing section gets written fresh. Delta generation, not full regeneration.

### How the Three Layers Apply the Principle

**Layer 2 (Task Pipeline — headless agents):**
Before generating output, agents receive:
1. DELIVERABLE.md — the quality target
2. Prior run awareness (from `awareness.md` — already injected, ADR-154)
3. Explicit prompt guidance: check `outputs/latest/` before generating; reuse existing assets; identify what's missing vs. stale vs. current

Agents are instructed: "The gap is the only work." They should call `ReadFile(path="outputs/latest/output.md")` when prior output is relevant, and check `outputs/latest/hero.png` exists before calling `RuntimeDispatch` for a hero image.

**Layer 3 (TP — conversational):**
Before proposing a task trigger or generating content on behalf of the user, TP should:
1. Scan the workspace for existing outputs (`SearchFiles`, `ListFiles`)
2. Read the prior output if recent (`ReadFile`)
3. Surface what exists — offer to update if stale, not silently regenerate
4. When the issue is focus rather than freshness, steer rather than re-run

**Both layers — asset generation:**
`RuntimeDispatch` is called only when an asset is absent or stale. The agent checks `outputs/latest/` for the asset before generating. If found, embed directly. If missing or source-changed, generate and embed the returned URL.

### Two Accumulation Patterns

**Context domains accumulate additively** (`/workspace/context/`):
Each run adds signal. Entity files grow richer. `_synthesis.md` files are rewritten to incorporate new findings. Nothing is discarded unless explicitly stale. Scope: append and merge.

**Task outputs converge replacively** (`/tasks/{slug}/outputs/latest/`):
Each run produces a new best version of the complete output. The output converges toward DELIVERABLE.md's quality target. Prior run snapshots are preserved in dated folders (`outputs/2026-04-10T1400/`). Scope: converge and replace latest, archive prior.

The `sys_manifest.json` at `outputs/latest/sys_manifest.json` bridges these patterns: it records what sources each section was derived from and when, enabling the agent to detect which sections are stale (source updated after manifest `created_at`) without full inspection.

---

## Architecture Integration

### Relationship to Existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-119 (Workspace Filesystem) | Provides the output folder structure and manifest convention that accumulation-first reads from |
| ADR-149 (Task Lifecycle / DELIVERABLE.md) | DELIVERABLE.md is the convergence target; prior output injection for goal mode is Phase 1 of this principle for one task mode |
| ADR-159 (Filesystem-as-Memory) | Compact index for TP is the same principle applied to conversational context; this ADR extends it to generative actions |
| ADR-170 (Compose Substrate) | `sys_manifest.json` and staleness detection already implement this principle for the compose layer; this ADR generalizes it to all execution layers |
| ADR-072 (Unified Content Layer / Accumulation Moat) | The moat thesis requires accumulation at the storage layer AND at the execution layer; this ADR closes the execution layer gap |

### What Phase 1 Changes (Prompt Layer)

Phase 1 is prompt-only. No schema changes, no new files, no new API endpoints.

**`api/services/task_pipeline.py`** — New "Accumulation-First Execution" section in `build_task_execution_prompt()`:
- States the principle explicitly
- Instructs agents to check `outputs/latest/` before generating
- Updates "Visual Assets" guidance: check if asset exists before calling `RuntimeDispatch`

**`api/agents/tp_prompts/tools.py`** — New "Accumulation-First — Read Before You Generate" section:
- Scan workspace before generating content or assets
- Read prior output and `sys_manifest.json` before proposing re-runs
- Steer rather than re-run when issue is focus not freshness

**`api/agents/tp_prompts/base.py`** — Updated "When to use tools":
- Adds "check what already exists" as a legitimate tool-use reason
- States the accumulation-first posture explicitly

### What Phase 2 Will Add (Manifest Injection)

Phase 2 (next sprint) closes the loop mechanically:

1. **`_build_prior_output_brief()`** in `task_pipeline.py` — reads `outputs/latest/sys_manifest.json`, calls `is_section_stale()` from compose substrate, formats a "generation brief" summarizing what exists, what's stale, and what's missing. Injected into `build_task_execution_prompt()` for all task modes (currently only goal mode gets prior output context).

2. **`TaskWorkspace.get_latest_manifest()`** — helper to parse `sys_manifest.json` into structured form for brief building.

3. **Extend to all modes** — currently `prior_output` is only injected for goal mode (ADR-149). Phase 2 extends the pattern to recurring and reactive modes: they receive the manifest brief, not the full prior output.

The Phase 1 prompt changes establish the behavioral expectation. Phase 2 makes it mechanically enforced.

### What Phase 3 Will Add (Output Versioning as Handoff)

Phase 3 formalizes the run-to-run handoff:

- `outputs/latest/sys_manifest.json` gains a `generation_gaps` field: what DELIVERABLE.md declared that wasn't produced (with reasons: asset-already-exists, section-current, skipped-no-source-data). This is a forward-looking handoff note to the next run.
- `outputs/v{N}/` snapshots are created before `latest/` is overwritten (currently, dated folders handle this; Phase 3 adds explicit version numbering aligned with `agent_runs.run_number`).
- `awareness.md` references the manifest path for the prior run, so the agent can locate it without scanning the folder.

---

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Implemented (2026-04-10) | Prompt layer — accumulation-first guidance in task pipeline + TP |
| Phase 2 | Proposed | Manifest injection — prior state brief for all task modes |
| Phase 3 | Proposed | Output versioning as forward-looking handoff artifact |

---

## Consequences

**Positive:**
- Agents stop regenerating what's already current — lower token cost per run
- Assets (hero images, charts) are reused across runs unless stale — no redundant render calls
- TP proposes targeted steering over full re-runs when output is recent and sources are stable
- Accumulation moat is realized at the execution layer, not just storage
- Output quality compounds: each cycle refines, not restarts

**Constraints:**
- Agents must have access to `outputs/latest/` during generation (already true in headless — task_slug is threaded through since ADR-173 Phase 1 / the RuntimeDispatch headless fix)
- Phase 2 manifest injection must not bloat token budget — brief should stay under ~800 tokens
- Graceful degradation required: first run has no manifest, no prior output — fall back to current full-generation behavior

**Risk: False staleness confidence.** If `sys_manifest.json` is missing or malformed, agents must degrade gracefully to full regeneration rather than producing a partial output. Defensive coding required in Phase 2.
