# ADR-186: TP Prompt Profiles — Surface-Aware Behavioral Assembly

**Status:** Implementing
**Date:** 2026-04-16
**Supersedes:** None (net new)
**Extends:** ADR-059 (Modular Prompt Architecture), ADR-080 (Unified Agent Modes), ADR-159 (Filesystem-as-Memory), ADR-164 (TP as Agent), ADR-168 (Primitive Matrix)
**Related:** ADR-023 (Surface Context), ADR-144 (Inference-First Shared Context), ADR-156 (Single Intelligence Layer)

---

## Context

TP's system prompt is assembled from 6 modules in `tp_prompts/` as a monolith: every behavioral section is injected on every turn regardless of what the user is doing. A user managing a specific task receives the same ~10K token prompt as a user onboarding for the first time — including the full task type catalog, onboarding recipe, agent creation guidance, and domain scaffolding instructions.

This creates three problems:

1. **Signal dilution.** Relevant behavioral guidance (~400 tokens) is buried in ~8K of irrelevant guidance. TP must mentally filter past onboarding instructions when the user is giving task feedback, and past feedback routing tables when the user is setting up their workspace.

2. **Contradictions.** The monolith serves every scenario simultaneously. Guidance for one scenario interferes with another (e.g., `behaviors.py` says "memory is passive, nightly cron extracts" while `onboarding.py` says "save facts proactively via UpdateContext" — the latter is correct post-ADR-156).

3. **Token waste.** ~40% of the system prompt is irrelevant on any given turn. At Sonnet pricing ($3/MTok input), this costs ~$0.02/turn in unnecessary input tokens. Across active users and multi-turn sessions, this accumulates.

The system already has the infrastructure for surface-aware behavior — `DeskSurface` types flow from frontend to backend, `load_surface_content()` injects entity-specific context, and `task_scope.py` defines a task-specific behavioral preamble that was never wired in. The missing piece is using the surface to select which behavioral sections TP receives.

---

## Decision

### Two prompt profiles: `workspace` and `entity`

TP's system prompt is assembled from a **prompt profile** determined by the user's current surface. The profile selects which behavioral sections are included. Primitive tool definitions remain constant across profiles — behavioral guidance determines when TP reaches for them, not tool availability.

**Two axes, one profile axis:**

| Axis | Values | Already handled by |
|---|---|---|
| **Runtime** (transport) | `conversational` / `autonomous` | ADR-080 mode registries (CHAT_PRIMITIVES / HEADLESS_PRIMITIVES). Separate codepath — `task_pipeline.py` has its own prompt builder. |
| **Scope** (attention) | `workspace` / `entity` | **This ADR.** Determines which behavioral prompt sections are assembled. |

The runtime axis is orthogonal and already solved. This ADR only addresses the scope axis within conversational (chat) mode.

### Profile definitions

#### `workspace` — workspace-wide conversational scope

**When:** User is on `/chat` without entity focus, or browsing general surfaces.

**Surface triggers:** `idle`, `agent-list`, `platform-list`, `document-list`, `context-browser`, `workspace-explorer`, `document-viewer`, or no surface context.

**Behavioral sections included:**
- Base identity + tone (`base.py` — shared)
- Workspace behaviors: onboarding priority, task type catalog, team composition guidance, agent creation, domain scaffolding recipe, profile/brand awareness
- Full tool documentation including creation guidance
- Platform tools
- Context awareness (identity → brand → tasks priority)

**Compact index shape:** Full workspace overview — all tasks, all domains, all health signals, surface context.

**Token budget:** ~6-7K static + ~500 compact index = ~7K total system prompt.

#### `entity` — entity-scoped conversational scope

**When:** User is viewing a specific task, agent, or agent run.

**Surface triggers:** `task-detail`, `agent-detail`, `agent-review`.

**Behavioral sections included:**
- Base identity + tone (`base.py` — shared)
- Entity behaviors: feedback routing (domain/agent/task layers), evaluate/steer/complete guidance, agent workspace management, accumulation-first for the scoped entity
- Core tool documentation (entity operations, UpdateContext targets, ManageTask actions — no creation guidance, no task type catalog)
- Platform tools
- Entity-specific preamble: TASK.md content, run log, output preview, assigned agent (the `task_scope.py` content, finally wired in)

**Compact index shape:** Scoped — this entity's run history, its context domains, its feedback entries, plus a one-line workspace summary for escape-hatch awareness.

**Token budget:** ~3-4K static + ~300 scoped index + ~1-2K entity preamble = ~5-6K total system prompt.

### Profile resolution

Declarative mapping with safe default and logging:

```python
SURFACE_PROFILES: dict[str, str] = {
    "task-detail": "entity",
    "agent-detail": "entity",
    "agent-review": "entity",
}

def resolve_profile(surface: Optional[SurfaceContext]) -> str:
    if not surface:
        return "workspace"
    profile = SURFACE_PROFILES.get(surface.type, "workspace")
    logger.info(f"[TP:PROFILE] surface={surface.type} → profile={profile}")
    return profile
```

Default is `workspace` — new surface types get the full prompt unless explicitly mapped. The failure mode is "too much context" not "missing context."

### What does NOT change

- **Primitive registries.** CHAT_PRIMITIVES and HEADLESS_PRIMITIVES are unchanged. Both profiles get the same 14 chat tools. TP uses judgment about which to call based on behavioral guidance, not tool availability.
- **Headless execution.** `task_pipeline.py` has its own prompt builder (`build_task_execution_prompt()`). This ADR does not touch it.
- **Back-office TP tasks.** `_execute_tp_task()` runs deterministic Python executors. No prompt involved.
- **Working memory data gathering.** `build_working_memory()` queries remain the same. Only `format_compact_index()` gains profile awareness for rendering.

---

## Implementation

### Phase 1: Prompt module restructure + fix pass

Restructure `tp_prompts/` from scenario-mixed modules to profile-aligned modules:

**Current structure (scenario-mixed):**
```
tp_prompts/
  __init__.py       # build_system_prompt() — monolithic assembly
  base.py           # identity + tone (shared)
  behaviors.py      # mixed: agent workspace mgmt + onboarding behaviors + resilience
  onboarding.py     # mixed: context awareness + task catalog + domain scaffolding
  platforms.py      # platform tools (shared)
  task_scope.py     # entity preamble (DEAD CODE — never imported)
  tools.py          # mixed: tool docs + workforce model + creation routes + feedback routing
```

**New structure (profile-aligned):**
```
tp_prompts/
  __init__.py       # build_system_prompt(profile=...) — profile-aware assembly
  base.py           # identity + tone (SHARED — both profiles)
  platforms.py      # platform tools (SHARED — both profiles)
  tools_core.py     # core tool docs: primitives, refs, domain terms (SHARED)
  workspace.py      # WORKSPACE PROFILE: onboarding, task catalog, team composition,
                     #   agent creation, domain scaffolding, profile/brand awareness,
                     #   exploration behaviors
  entity.py         # ENTITY PROFILE: feedback routing, evaluate/steer/complete,
                     #   agent workspace management, entity-scoped behaviors,
                     #   accumulation-first for scoped entity
  task_scope.py     # entity preamble builder (REVIVED — used by entity profile)
```

**Fix pass (rolled into restructure):**
1. Fix ReadFile/SearchFiles/ListFiles references in chat prompt — these are headless-only tools. Replace with entity-layer equivalents or working memory guidance.
2. Fix memory guidance contradiction — delete "nightly cron extracts" (behaviors.py), align with ADR-156 (TP writes facts in-session).
3. Update agent type references — replace ADR-130 types (briefer/monitor/drafter/planner/scout) with ADR-176 roster (researcher/analyst/writer/tracker/designer/reporting).
4. Fix ManageAgent example — use valid role and parameters.
5. Modernize agent workspace management — replace EditEntity patterns with UpdateContext(target="agent") and file-based patterns where appropriate.
6. Update primitives-matrix.md — RuntimeDispatch is in CHAT_PRIMITIVES (14 tools, not 13). Sync doc with code.

### Phase 2: Profile resolver + compact index

1. Add `resolve_profile()` to `chat.py` with declarative SURFACE_PROFILES mapping and logging.
2. Pass profile through to `build_system_prompt()`.
3. Add `profile` parameter to `format_compact_index()` in `working_memory.py`:
   - `workspace`: current full rendering (unchanged)
   - `entity`: scoped rendering — entity health, entity domains, entity run history, one-line workspace summary
4. Wire `task_scope.py` preamble into entity profile assembly (revive dead code).

### Phase 3: Documentation

1. Update `TP-DESIGN-PRINCIPLES.md` — add profiles to the awareness architecture.
2. Update `primitives-matrix.md` — fix chat tool count, add note about profile-invariant primitive set.
3. Update `CLAUDE.md` ADR index.
4. Update `api/prompts/CHANGELOG.md`.

---

## Consequences

### Benefits
- **~40% token reduction** for entity-scoped conversations (most common scoped interaction).
- **~3x signal density improvement** — relevant behavioral guidance is front-and-center, not buried.
- **Contradictions eliminated** — profile isolation prevents cross-scenario interference.
- **Dead code revived** — `task_scope.py` gets wired in after being defined but never imported.
- **Developer maintainability** — prompt changes are scoped to a profile, not a monolith. Easier to reason about which behavioral sections affect which user scenarios.

### Risks
- **Profile boundary crossed mid-conversation.** User on a task page says "create a new task." The entity profile doesn't include task creation guidance. Mitigation: TP still has `ManageTask(action="create")` in its tool set — it can create tasks without catalog guidance. If this proves insufficient, the workspace profile's creation guidance can be selectively included. The default-to-workspace fallback means this is "slightly less guided" not "blocked."
- **Logging overhead.** Profile resolution logging adds one log line per chat message. Negligible cost, high diagnostic value for future evaluation.

### Future considerations
- **Evaluation framework.** Profile effectiveness should be evaluated by comparing feedback routing accuracy and first-try success rates across profiles. Scoped separately from this ADR.
- **Headless prompt profiles.** `task_pipeline.py`'s `build_task_execution_prompt()` could benefit from similar profile-awareness (e.g., accumulates_context vs produces_deliverable tasks get different behavioral guidance). Scoped separately — investigate after this ADR lands.
- **Profile-aware prompt caching.** If most entity-scoped conversations use the same ~4K static prompt, cache hit rates improve vs. the current ~10K monolith that changes shape per turn.
