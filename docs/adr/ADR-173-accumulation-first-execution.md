# ADR-173: Accumulation-First Execution

**Date:** 2026-04-10
**Status:** Implemented (Phase 1 + Phase 2 + Phase 3 — prompt layer + manifest injection + generation_gaps handoff)
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

### What Phase 2 Added (Manifest Injection — Implemented)

Phase 2 closes the loop mechanically for all task modes except `produces_deliverable` (which already gets the full compose brief via ADR-170's generation_brief).

1. **`TaskWorkspace.get_prior_state_brief()`** — reads `outputs/latest/manifest.json` + lists `outputs/latest/` to discover existing assets (hero images, charts). Builds a compact brief (~300-500 tokens) including: prior run timestamp, asset inventory ("Hero image: EXISTS — reuse, do not regenerate"), and a ~2000-char excerpt of `outputs/latest/output.md`. Returns `""` on first run (graceful degradation to full generation).

2. **`build_task_execution_prompt()` gains `prior_state_brief` param** — injected into user message after `generation_brief` / goal-mode `prior_output`. Empty string is a no-op.

3. **Extended to all non-`produces_deliverable` modes** — `accumulates_context`, `external_action`, `system_maintenance` tasks all receive the brief. Goal mode still gets `prior_output` (full text, "you are revising"). `produces_deliverable` with `page_structure` gets the full ADR-170 compose brief. `produces_deliverable` without `page_structure` now also gets `prior_state_brief` as a fallback.

The prompt changes (Phase 1) establish the behavioral expectation. The manifest injection (Phase 2) makes it mechanically available — agents receive concrete prior-state signal, not just an instruction to look for it.

### What Phase 3 Added (Forward-Looking Handoff via generation_gaps — Implemented)

Phase 3 closes the run-to-run handoff loop via a structured `generation_gaps` field in `sys_manifest.json`.

**`api/services/compose/manifest.py`** — `SysManifest` gains `generation_gaps: dict[str, str]`. Keys are section slugs and asset keys from `page_structure`; values are `"<status>:<reason>"` strings (e.g. `"skipped:section-current"`, `"missing:no-source-data"`, `"produced:forced"`). Written this run, read by next run.

**`api/services/compose/assembly.py`** — `build_post_generation_manifest()` receives `prior_manifest` and `revision_scope`. Computes `generation_gaps` by iterating `page_structure`: sections produced this run are classified by why (`forced`, `stale`, `delta`, `first-run`); sections in `current_sections` are `skipped:section-current`; sections absent from both are `missing:no-source-data` (or `missing:section-current` if a prior section record exists but no source data was found). Derivative assets declared in `page_structure` that weren't produced are classified as `missing:asset-not-produced`.

**`api/services/task_workspace.py`** — `get_prior_state_brief()` now reads `outputs/latest/sys_manifest.json` in addition to `manifest.json`. Surfaces `generation_gaps` as human-readable lines: "Pending from prior run (produce these): ..." for `missing:` entries and "Current from prior run (reuse/skip unless stale): ..." for `skipped:` entries. Non-fatal: parse failure degrades to the Phase 2 brief.

Note: Explicit `outputs/v{N}/` version numbering (aligned with `agent_runs.run_number`) remains a future refinement — dated folders (`outputs/2026-04-10T1400/`) continue to serve as the snapshot mechanism for now.

---

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Implemented (2026-04-10) | Prompt layer — accumulation-first guidance in task pipeline + TP |
| Phase 2 | ✅ Implemented (2026-04-10) | Manifest injection — `TaskWorkspace.get_prior_state_brief()` + wired into all non-`produces_deliverable` task modes via `prior_state_brief` param |
| Phase 3 | ✅ Implemented (2026-04-10) | `generation_gaps` field in `SysManifest` — forward-looking handoff dict written each run, consumed by next run via `get_prior_state_brief()` |

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
