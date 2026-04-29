# ADR-233: Shape-Driven Invocation Lifecycle — Prompt, Prior Output, Domain Synthesis

> **Status**: **Proposed** (2026-04-29). Three independently-shippable phases.
> **Date**: 2026-04-29
> **Authors**: KVK, Claude
> **Dimensional classification**: **Mechanism** (Axiom 5) primary, **Substrate** (Axiom 1) + **Trigger** (Axiom 4) secondary.
> **Extends**: ADR-231 (Task Abstraction Sunset — promotes `RecurrenceShape` from a routing classifier to the **lifecycle classifier** for invocation prompt + context strategy + filesystem compaction).
> **Amends**: ADR-173 (Accumulation-First Execution — mechanizes prior-output injection for recurring DELIVERABLE invocations, not just goal-mode revisions), ADR-186 (Prompt Profiles — extends the profile axis from 2 chat profiles to 5 unified profiles: `chat/workspace`, `chat/entity`, `headless/deliverable`, `headless/accumulation`, `headless/action`. The `yarnnn_prompts/` directory is renamed to `prompts/` with `chat/` + `headless/` subdirectories — one prompt home, one CHANGELOG, one resolver).
> **Preserves**: FOUNDATIONS axioms 1–8, ADR-141 (three execution layers), ADR-194 v2 (Reviewer substrate), ADR-209 (Authored Substrate), ADR-219 (narrative as universal log), ADR-231 (recurrence-walker substrate, natural-home paths, four-shape dispatch).

---

## Context

ADR-231 successfully collapsed the task abstraction. `RecurrenceShape` (DELIVERABLE | ACCUMULATION | ACTION | MAINTENANCE) is now the canonical classifier the dispatcher routes on — but only for **routing decisions**: which `_dispatch_*` function fires, where output lands on disk, what tool surface is exposed.

Three observable gaps remain where the shape *should* drive behavior but doesn't:

### Gap 1 — Cognitive posture is shape-blind

`api/services/dispatch_helpers.py::build_task_execution_prompt()` (lines 652–878) assembles one prompt template for every generative invocation. Variation is weak:

- Output token cap varies by `output_kind` (deliverable=4000, accumulation=8000)
- Tool surface is restricted in the dispatcher for DELIVERABLE (WriteFile + RuntimeDispatch only)
- A `step_instruction` string from YAML is appended

But the cognitive posture the LLM brings to the work is identical for all shapes. An ACCUMULATION invocation ("scan the world, update entity trackers") and a DELIVERABLE invocation ("compose a formatted report from accumulated state") are different cognitive jobs. The current prompt asks the LLM to figure out which job it's doing from the gathered context.

### Gap 2 — Prior-output injection is goal-mode-only

`build_task_execution_prompt()` line 826 gates prior-output injection on `task_mode == "goal"`. Recurring DELIVERABLE invocations — the steady-state case — never see their own prior output, so accumulation-first execution (ADR-173) degrades to "regenerate from scratch every cycle, only the gathered context is reused."

`task_mode` is a vestigial signal post-ADR-231 (mode dropped from `tasks` table in migration 164). The shape-classifier is the right gate: every DELIVERABLE invocation should see the latest output at `/workspace/reports/{slug}/{latest}/output.md` if one exists.

### Gap 3 — Domain synthesis is conventional, not produced

Workspace conventions reference `/workspace/context/{domain}/landscape.md` as the per-domain synthesis file (overwrite each cycle). But there's no shape whose contract is "produce the synthesis." ACCUMULATION invocations write entity files and trackers; DELIVERABLE invocations read raw entity files up to a token budget. Cross-domain reasoning re-reads raw entities every cycle.

A domain-level synthesis written by ACCUMULATION as a deliberate output (not just a side-effect convention) becomes the filesystem-native equivalent of session compaction — and it lets DELIVERABLE invocations pull a 1–2K-token brief instead of paging entities.

---

## Decision

`RecurrenceShape` becomes the **lifecycle classifier** for headless invocations, governing four lifecycle aspects:

| Aspect | Today | After ADR-233 |
|--------|-------|--------------|
| **Dispatch routing** | Shape-driven | Unchanged |
| **Output paths** | Shape-driven | Unchanged |
| **Tool surface** | Shape-driven (partial) | Unchanged |
| **Cognitive posture (prompt)** | Uniform | **Shape-driven** (Phase 1) |
| **Prior-output injection** | `task_mode='goal'` only | **DELIVERABLE shape always** (Phase 2) |
| **Domain synthesis** | Convention only | **ACCUMULATION shape contract** (Phase 3) |

### Three decisions

**D1 — Unified prompt profile structure across chat and headless callers.** The `api/agents/yarnnn_prompts/` directory is renamed to `api/agents/prompts/` with two subdirectories: `chat/` (existing ADR-186 workspace + entity profiles, plus ADR-226 activation overlay) and `headless/` (three new shape-keyed profiles: `deliverable.py`, `accumulation.py`, `action.py`). MAINTENANCE has no LLM call, no profile.

A single `build_prompt(profile_key, ...)` entry point in `prompts/__init__.py` resolves to the right assembler. `_BASE_BLOCK` (shared output rules, workspace conventions, tool usage, accumulation-first posture, empty-context handling) lives in `prompts/base.py` and is composed by every profile that needs it. `tools_core.py` stays as the shared tool-usage guidance module (already in this position).

Five profiles total: `chat/workspace`, `chat/entity`, `headless/deliverable`, `headless/accumulation`, `headless/action`. One CHANGELOG (`api/prompts/CHANGELOG.md` per existing convention — single source for all behavioral injections). One resolver. The chat-vs-headless split lives below the resolver, not in parallel sibling directories.

Singular implementation: the monolithic `build_task_execution_prompt()` body is **deleted**; the parallel-directory pattern (`yarnnn_prompts/` for chat + a new `headless_prompts/` sibling) is **rejected** before it lands. ADR-233 is the one rename window — taking it once now is cheaper than taking it later when more callers reference `yarnnn_prompts.*`.

`build_task_execution_prompt()` in `dispatch_helpers.py` is rewritten to call `build_prompt("headless/" + decl.shape.value.lower(), ...)`. Signature changes from `(task_info, agent, ...)` to `(decl, agent, ...)`. The `task_mode` parameter is **deleted**.

**D2 — Prior-output injection is shape-gated, not mode-gated.** `_load_prior_output(decl)` reads `/workspace/reports/{slug}/{latest_date}/output.md` when `decl.shape == DELIVERABLE`. The `task_mode == "goal"` branch in `build_task_execution_prompt()` is **deleted**. Mode is a YARNNN-side concern (recurring/goal/reactive in YARNNN's vocabulary); shape is the dispatch-side fact.

**D3 — `landscape.md` is an ACCUMULATION-shape contract, not a convention.** Every ACCUMULATION invocation produces *both* entity updates *and* a domain synthesis file at `/workspace/context/{domain}/landscape.md`. The synthesis is the primary artifact DELIVERABLE invocations read; raw entities become the secondary read for objective-targeted detail.

---

## Implementation Phases

Each phase is independently shippable, independently testable, independently reversible.

### Phase 1 — Unified prompt profile structure (chat + headless under one home)

**Directory rename** (atomic with the rest of Phase 1, single commit):
- `api/agents/yarnnn_prompts/` → `api/agents/prompts/`
- Existing files relocate: `__init__.py`, `tools_core.py`, `base.py`, `platforms.py`, `onboarding.py`, `task_scope.py`, `activation.py` stay at `prompts/` root if shared, or move into `prompts/chat/` if chat-specific.
- New subdirectories: `prompts/chat/` (workspace + entity + activation), `prompts/headless/` (deliverable + accumulation + action).
- All callers (chat path: `api/agents/yarnnn.py`, `api/routes/chat.py::resolve_profile`, `api/routes/chat.py::SURFACE_PROFILES`; headless path: rewired in this phase) update their imports from `yarnnn_prompts.*` to `prompts.*` in the **same commit**. No transitional re-exports — singular implementation rule 1.

**Files created** (3 + 1 entry):
- `api/agents/prompts/headless/deliverable.py` — `DELIVERABLE_POSTURE`: "Read the deliverable spec → read prior output → identify the gap → produce the gap. Output is replacive."
- `api/agents/prompts/headless/accumulation.py` — `ACCUMULATION_POSTURE`: "Read existing entities + landscape → scan for new/changed → update entities additively → rewrite landscape.md as synthesis. Output is additive." (Phase 3 hardens this contract.)
- `api/agents/prompts/headless/action.py` — `ACTION_POSTURE`: "Read mandate + risk + state → propose action with reasoning + confidence → emit proposal, do not execute. The proposal is the work."
- `api/agents/prompts/__init__.py` (existing, extended) — adds `build_prompt(profile_key: str, ...)` resolver dispatching on the five-key namespace. Existing `build_system_prompt()` chat-path entry point is preserved as a thin wrapper that calls `build_prompt("chat/<profile>", ...)` so chat surfaces don't change shape.

**Files modified** (3):
- `api/services/dispatch_helpers.py::build_task_execution_prompt()` — **rewritten** to call `build_prompt("headless/" + decl.shape.value.lower(), ...)`. Signature changes from `(task_info, agent, ...)` to `(decl, agent, ...)`. The `task_mode` parameter is **deleted**. The dispatcher's synthetic `task_info` bridge in `invocation_dispatcher.py` shrinks accordingly.
- `api/services/invocation_dispatcher.py::_dispatch_generative()` — passes `decl` directly instead of synthesized `task_info`. Tool overrides remain shape-driven as today.
- `api/routes/chat.py::resolve_profile()` — return value updates from `"workspace"` / `"entity"` to `"chat/workspace"` / `"chat/entity"` so it composes with the new five-key namespace. `SURFACE_PROFILES` dict values updated.

**Files deleted**:
- The empty old `api/agents/yarnnn_prompts/` directory after move.

**Test gate**:
- `api/test_adr233_phase1_shape_prompts.py` — for each of the three generative shapes, assert (a) the posture string appears in the assembled system prompt, (b) the static cache split point is preserved (cached `_BASE_BLOCK` precedes posture/dynamic content), (c) `task_mode='goal'` no longer alters prompt content (regression guard for the deleted branch), (d) chat profiles still resolve via `build_prompt("chat/workspace")` / `build_prompt("chat/entity")` and produce byte-identical output to pre-rename for the same inputs (regression guard for the rename).
- Final grep gate: `grep -r "yarnnn_prompts" api/ docs/` returns zero hits in live code (allowed in historical ADR text only).

**Singular implementation discipline**:
- The ~225-line monolithic `build_task_execution_prompt()` body is **replaced**, not extended. The `task_mode == "goal"` branch is **deleted** in this phase (Phase 2 reintroduces prior-output injection on the shape axis). No dual templates, no fallback to legacy prompt. Parallel directory pattern (`yarnnn_prompts/` + new `headless_prompts/`) is **rejected** before landing. One prompt home, one CHANGELOG, one resolver.

**LOC delta**: ~+280 added (3 posture files + resolver extension), ~−180 deleted (monolithic prompt body), plus ~80 lines of import updates across callers, net ~+180.

**Prompt CHANGELOG entry**: `[2026.MM.DD.N]` — "ADR-233 Phase 1 — unified prompt profile structure. `yarnnn_prompts/` → `prompts/{chat,headless}/`. Three new headless profiles (deliverable / accumulation / action). `task_mode` parameter dropped; cognitive posture now shape-keyed."

---

### Phase 2 — DELIVERABLE prior-output injection

**Hardening note (2026-04-29):** Phase 2's original framing — "DELIVERABLE shape always injects prior output" — is generalized to a uniform principle: **every generative shape pre-reads its natural-home folder before writing.** The benchmark against Cowork (folder-as-context) and ADR-173 (Accumulation-First Execution) revealed that "read your folder before you write to it" is the load-bearing principle; gating on DELIVERABLE alone is a special case that would force a Phase 2.5 to extend it to ACCUMULATION/ACTION. Singular implementation rule 1 says ship the principle once, not the special case three times. The natural-home paths are already canon per ADR-231 D2 (DELIVERABLE → `/workspace/reports/{slug}/{latest}/`, ACCUMULATION → `/workspace/context/{domain}/`, ACTION → `/workspace/operations/{slug}/`). The principle is "read what you're about to write atop"; the path resolution is already declared by `recurrence_paths.py`.

**Files modified** (4):
- `api/services/dispatch_helpers.py` — add `_load_natural_home_brief(client, user_id, decl) -> NaturalHomeBrief | None`. The brief is shape-keyed:
  - DELIVERABLE: latest `output.md` (capped ~8K chars; ADR-173 prior-output pattern). When absent: returns `None` and posture frames as "first run."
  - ACCUMULATION: domain-folder index (entity slugs + last-modified + landscape.md if present, capped ~4K chars). When absent: returns `None` and posture frames as "first accumulation pass into this domain."
  - ACTION: latest action proposal in `/workspace/operations/{slug}/` (if any unresolved) + `_action.yaml` recurrence declaration. Used as "what's already pending/in-flight?" signal so reactive ACTIONs don't double-propose. When absent: returns `None`.
  - MAINTENANCE: never called (no LLM, no posture).
  - Reads through `recurrence_paths.py` helpers — no inline path strings; ADR-231 D2/D9/D10 path resolution stays the single source of truth.
- `api/services/recurrence_paths.py` — extend with shape-aware natural-home read helpers if any are missing (likely already present from ADR-231 Phase 3.2.a; audit during implementation).
- `api/agents/prompts/headless/deliverable.py::DELIVERABLE_POSTURE` — gains `## Prior Output (your starting point)` section. When prior exists: "You are revising a recurring deliverable. The prior output is below. Read it first; preserve sections whose source data has not changed; update only the gap." When no prior: "First run of this recurrence. Compose from gathered context."
- `api/agents/prompts/headless/accumulation.py::ACCUMULATION_POSTURE` — gains `## Domain State (what you've accumulated so far)` section. When folder exists: "You are extending a domain you've worked in before. The current entity inventory is below. Update existing entities additively; add new entities for genuinely new subjects." When absent: "First accumulation pass into this domain."
- `api/agents/prompts/headless/action.py::ACTION_POSTURE` — gains `## Pending Operations` section. When proposals/state exist: "Active proposals or unresolved state below. Do not duplicate; either reference, supersede, or stand down." When absent: "No pending state for this operation."

**Files NOT modified** (intentional):
- `invocation_dispatcher.py` — Phase 2 lives entirely inside the prompt-build path, not dispatch.
- `_dispatch_generative` — no flow change; natural-home brief is loaded inside `build_prompt`.

**Test gate**:
- `api/test_adr233_phase2_natural_home_preread.py` — six cases (one per shape × prior-exists/absent):
  - DELIVERABLE + prior `output.md` exists → posture contains prior-output excerpt.
  - DELIVERABLE + no prior → posture contains "First run" framing.
  - ACCUMULATION + domain folder exists with entities → posture contains entity inventory excerpt.
  - ACCUMULATION + empty domain → posture contains "First accumulation pass" framing.
  - ACTION + pending proposal exists → posture contains pending-state notice.
  - ACTION + no pending state → posture contains "No pending state" framing.
- All path reads route through `recurrence_paths.py` (assert via mock) — no inline strings.

**Token impact**: DELIVERABLE +3–6K (existing pattern). ACCUMULATION +1–3K (entity inventory, intentionally compact — full entities are ad-hoc reads via ReadFile if the agent needs them). ACTION +0.5–1K. All cache-friendly (post-cache marker, dynamic content).

**Cost note**: DELIVERABLE delta-generation savings unchanged from original framing (~50% output-token reduction at second invocation onward). ACCUMULATION savings come from cleaner additive writes (less duplication of existing entities) — measured by `_post_run_domain_scan` entity-churn metric. ACTION savings come from preventing duplicate proposals — measured by Reviewer rejection rate.

**LOC delta**: ~+150 added (helper + three posture extensions + tests).

**Prompt CHANGELOG entry**: `[2026.MM.DD.N]` — "ADR-233 Phase 2 — natural-home pre-read across all generative shapes. DELIVERABLE reads prior output, ACCUMULATION reads domain inventory, ACTION reads pending state. `task_mode='goal'` revision pattern subsumed."

---

### Phase 3 — Domain synthesis as ACCUMULATION contract

> **Status: deferred for fresh discussion post-Phase-1 implementation.** The cold-start failure mode (R3 — first synthesis flows into first downstream report unverified before any feedback arrives) and the synthesis-quality drift question warrant their own design pass. Phase 1 will surface what the ACCUMULATION posture looks like in practice; Phase 3 will be re-scoped from observed reality, not pre-design. Description below is the original draft, retained for reference only.

**Files modified** (2):
- `api/agents/prompts/headless/accumulation.py::ACCUMULATION_POSTURE` — output contract gains required dual-artifact:
  ```
  Your output is TWO artifacts:
  1. Entity updates — write to /workspace/context/{domain}/{entity-slug}/profile.md and signals.md per conventions
  2. Domain synthesis — REWRITE /workspace/context/{domain}/landscape.md as a 600–1200-word executive summary:
     - Current state of the domain (what's known)
     - Material changes since the prior synthesis (what's new)
     - Watchlist (what's worth tracking)
     - Cross-entity patterns (what threads connect entities)
  The synthesis is what other agents read first. Write it as if explaining the domain to a colleague who has 90 seconds.
  ```
- `api/services/dispatch_helpers.py::_gather_context_domains()` — synthesis-first read order is **enforced**: for each `context_reads` domain, read `landscape.md` first (full), then per-entity files filtered by objective match, capped per existing budget. The current "synthesis-first" comment ([dispatch_helpers.py:274](api/services/dispatch_helpers.py:274)) is partially true; this phase makes it the contract.

**Files NOT modified** (intentional):
- No registry changes — `landscape.md` was already conventional. Phase 3 promotes convention to contract via the prompt; no code-side schema change.
- No migration — first ACCUMULATION invocation post-Phase-3 produces the synthesis. Domains without `landscape.md` degrade gracefully (read returns empty, posture says "first synthesis pass").

**Test gate**:
- `api/test_adr233_phase3_domain_synthesis.py` — two cases:
  - ACCUMULATION posture string contains "REWRITE /workspace/context/{domain}/landscape.md" instruction
  - `_gather_context_domains` reads landscape.md first when present, falls through to entities when absent

**Operator-visible effect**: After ~1 cycle of every accumulation recurrence, every domain has a synthesis file. Cross-domain DELIVERABLE invocations (`revenue-report`, `weekly-brief`) read syntheses instead of paging entities — input tokens drop ~30–50% on multi-domain reports. Manually checked via `/files` after the change.

**LOC delta**: ~+40 added (prompt strings + read-order enforcement).

**Prompt CHANGELOG entry**: `[2026.MM.DD.N]` — "ADR-233 Phase 3 — ACCUMULATION shape produces dual artifact (entities + landscape.md synthesis); `_gather_context_domains` reads synthesis first."

---

## Out of scope

- **Chat-side prompt changes**: ADR-186 (workspace/entity profiles) is the orthogonal axis and is unchanged.
- **MAINTENANCE shape**: dotted executor, no LLM, no posture needed.
- **Ratcheting**: not adding seniority gates, growth metrics, or compounding logic in this ADR. Out of scope for prompt refinements.
- **Cross-domain synthesis**: per-domain `landscape.md` is the unit; cross-domain summary remains a DELIVERABLE-shape concern (e.g., `weekly-brief`).
- **Synthesis quality evaluation**: deferred. Operator + feedback loop drive quality across cycles; no eval harness in this ADR.

---

## Singular implementation discipline (per ADR-231 §11 invariant 10)

- Phase 1 deletes the monolithic `build_task_execution_prompt` body and the `task_mode` parameter. No dual templates.
- Phase 2 deletes the `task_mode == "goal"` branch in the new structure. Prior-output injection is shape-gated, period.
- Phase 3 promotes a convention to a contract via prompt; no parallel paths.
- After all three phases ship, grep gate: `grep -r "task_mode" api/` should return zero hits in dispatch path code (acceptable in `tasks` table query glue if any survives migration 164).

---

## Verification gates per phase

| Phase | Test file | Manual smoke |
|-------|-----------|-------------|
| 1 | `test_adr233_phase1_shape_prompts.py` | Fire one each of DELIVERABLE / ACCUMULATION / ACTION manually via `POST /api/recurrences/{slug}/run`; verify posture in run log |
| 2 | `test_adr233_phase2_prior_output.py` | Fire a DELIVERABLE recurrence twice; verify second run's prompt contains first run's output |
| 3 | `test_adr233_phase3_domain_synthesis.py` | Fire one ACCUMULATION recurrence; verify `landscape.md` appears at `/workspace/context/{domain}/landscape.md` |

---

## Frontend impact

**None.** ADR-233 is entirely backend prompt + context refinement. No API contract changes. No schema changes. No new endpoints.

This is intentional: the operator-visible output is "the recurring report gets better over time" and "the domain pages have an executive summary at the top." Both surface naturally in existing UI without frontend work.

---

## Phase ordering rationale

Phase 1 (shape postures) is foundation — Phase 2 hangs prior-output injection on the DELIVERABLE posture string; Phase 3 hangs the synthesis contract on the ACCUMULATION posture string. Without Phase 1, Phases 2 and 3 would be patches on the monolithic prompt — that's the dual-path failure mode ADR-231 §11 invariant 10 forbids.

Phases 2 and 3 are independent of each other and could ship in either order or in parallel commits.

---

## Risks

**R1 — Prompt regression on shape transition.** Splitting a working monolithic prompt into four shape-specific assemblers risks losing tested-good language. Mitigation: Phase 1 lifts the existing `## Output Rules`, `## Workspace Conventions`, `## Accumulation-First Execution`, `## Tool Usage`, `## Visual Assets`, `## Empty Context Handling` sections verbatim into `_BASE_BLOCK` shared by all postures. Only the "what cognitive job is this" framing differentiates between shapes.

**R2 — Prior-output token cost.** Phase 2 adds ~3–6K input tokens to DELIVERABLE steady-state. Mitigation: capped at 8000 chars (existing slice), cache-friendly placement (post-cache marker → no cache invalidation), expected output-token reduction more than offsets.

**R3 — Synthesis quality drift.** Phase 3 asks the LLM to write a 600–1200-word synthesis as part of every accumulation cycle. Bad syntheses corrupt downstream deliverables. Mitigation: ACCUMULATION feedback loop (per ADR-181 source-agnostic feedback) lets operator correct synthesis quality; correction propagates to next cycle. No batch backfill — first synthesis pass is "first draft," next cycle reads its own prior synthesis (Phase 2 mechanic generalized to ACCUMULATION via the dual-artifact contract).

---

## Closing note

ADR-231 collapsed the substrate. ADR-233 finishes the cognitive posture work that ADR-231 deferred. After all three phases, `RecurrenceShape` is the lifecycle classifier in full: dispatch + paths + tools + prompt + prior-output + synthesis-contract. One classifier, one set of operator-legible work shapes, zero remaining places where the cognitive posture is shape-blind.

The frontend can move ahead in parallel.
