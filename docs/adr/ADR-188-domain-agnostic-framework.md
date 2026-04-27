# ADR-188: Domain-Agnostic Framework — Registries as Template Libraries

> **⚠ Completed by [ADR-205](ADR-205-primitive-collapse.md) (2026-04-22).** The "registries as template libraries" thesis is extended to the agent roster layer and the workspace directory layer. `AGENT_TEMPLATES` becomes a dispatch-time palette (no persisted rows at signup) and `WORKSPACE_DIRECTORIES` becomes a naming-convention reference (no directory pre-creation at signup). ADR-188's arc — "framework-fixed primitives, contextual workspace config" — now holds at both read and write paths and across all three registries.
>
> **⚠ Superseded by [ADR-207](ADR-207-primary-action-centric-workflow.md) (2026-04-22).** ADR-188's "registries as template libraries" thesis is finished — `TASK_TYPES` dissolves entirely. Tasks no longer reference a concrete type key; they self-declare in TASK.md (`schedule`, `context_reads`, `context_writes`, `emits_proposal`, `required_capabilities`, `output_spec`). The task-type library becomes documentation (example shapes for reference), not code. Platform Bots — the last concrete-typed roster — also dissolve into pure Capabilities per ADR-207's D5.
>
> **⚠ Validated by [ADR-224](ADR-224-kernel-program-boundary-refactor.md) (2026-04-27).** The "registries are template libraries" principle is now structurally enforced in code, not just stated. ADR-224 deletes program-specific template residue from kernel registries (3 task types, 4 directories, 4 capabilities) and moves them to program bundle MANIFEST.yaml. `bundle_reader` provides point-of-use fallback at the few composition / scaffolding / display moments where bundles are consulted. Runtime dispatch path remains purely substrate-driven. Test gate `test_adr224_kernel_boundary.py` fails on regression. The OS framing's "kernel boundary is sacred" claim now holds in code as well as in docs.

> **Status**: Phases 1-4 Implemented, Phase 5 Complete (Phase 3+ agent/directory collapse completed by ADR-205)
> **Date**: 2026-04-17
> **Related**: ADR-138 (Agents as Work Units), ADR-141 (Unified Execution), ADR-145 (Task Type Registry), ADR-151/152 (Context Domains / Directory Registry), ADR-166 (Registry Coherence Pass), ADR-176 (Work-First Agent Model), ADR-183 (Commerce Substrate), ADR-187 (Trading Integration)
> **Supersedes**: ADR-176 "hospital principle" (fixed roster as non-negotiable)
> **Completed by**: ADR-205 (Primitive Collapse — agent roster and directory pre-creation dissolved)
> **Triggered by**: ADR-187 stress test — the trading integration revealed that every new user persona requires developer-authored registry entries, not TP-generated workspace configuration

---

## Context

### The observation

ADR-187 (Trading Integration) was designed as an end-to-end stress test of the agent framework. Building it surfaced a fundamental question: **if every new user persona (day-trader, lawyer, e-commerce operator, SNS influencer) requires a developer to hand-author task types, step instructions, context domains, and agent templates in Python registries, is the framework actually domain-agnostic?**

The answer is no. The framework's execution pipeline is agnostic — `task_pipeline.py` reads TASK.md, not the registry, at runtime. But the creation layer treats registries as exhaustive product definitions rather than template libraries. TP picks from a fixed catalog; it cannot compose novel task definitions, domain structures, or step instructions from first principles.

### The evidence

Consider five user personas and what each requires:

| Persona | Context domains needed | Task types needed | Agents needed |
|---|---|---|---|
| Day-trader | `trading/`, `portfolio/` | `trading-digest`, `trading-signal`, `trading-execute`, `portfolio-review` | Trading Bot |
| Lawyer | `cases/`, `precedents/`, `clients/` | `case-research`, `precedent-brief`, `client-update` | (universal specialists suffice) |
| E-commerce operator | `customers/`, `revenue/`, `inventory/`, `campaigns/` | `commerce-digest`, `inventory-alert`, `campaign-report` | Commerce Bot |
| SNS influencer | `audience/`, `content_calendar/`, `brand_deals/` | `content-plan`, `engagement-report`, `brand-outreach` | (universal specialists suffice) |
| Consultant | `clients/`, `engagements/`, `deliverables/` | `client-brief`, `engagement-tracker`, `weekly-report` | (universal specialists suffice) |

Three of five personas can use the existing universal specialist roster — Researcher, Analyst, Writer, Tracker, Designer are genuinely domain-agnostic. But **none** of the five can use the pre-defined context domains or task types without developer intervention. Each needs custom domains with custom entity structures, custom task definitions with domain-specific step instructions, and custom process configurations.

### What the code audit revealed

The pipeline is already 80% agnostic. Key findings:

| Concern | Creation-time coupling | Runtime coupling | TP-generated support |
|---|---|---|---|
| **Task definitions** (TASK_TYPES) | Yes — ManageTask reads registry | No — TASK.md is runtime source | Already works: custom tasks skip registry |
| **Step instructions** (STEP_INSTRUCTIONS) | No | Yes — pipeline reads registry, falls back to empty string | Partial: unknown steps get no guidance |
| **Context domains** (WORKSPACE_DIRECTORIES) | Yes — scaffold at signup | Partial — temporal flag lookup, defaults to canonical | Mostly works: custom domains default to canonical behavior |
| **Agent capabilities** (CAPABILITIES) | No | Yes — `has_capability()` checks registry | Partial: unknown types fall back to researcher defaults |
| **Agent roster** (DEFAULT_ROSTER) | Yes — signup scaffolding | No — agents table is runtime source | Full: ManageAgent creates custom agents |
| **output_kind** (4-value enum) | Declarable in TASK.md | Yes — pipeline branches on it | Already works: the 4 values are framework-level |

**The critical insight**: registries are coupled at creation time, not at execution time. The pipeline reads workspace files (TASK.md, AGENT.md), not Python dicts. The registries gate what TP can *create*, not what the pipeline can *execute*.

---

## Decision

### Registries become template libraries, not validation gates

The three registries (`TASK_TYPES`, `WORKSPACE_DIRECTORIES`, `AGENT_TEMPLATES`) are reframed from "the exhaustive set of valid types/domains/agents" to "a curated library of templates that TP can draw from — or compose beyond."

**What stays fixed (framework-level primitives):**
- `output_kind` taxonomy: `accumulates_context | produces_deliverable | external_action | system_maintenance` — these are the four shapes of work, genuinely universal
- Agent roles: `researcher | analyst | writer | tracker | designer | reporting | thinking_partner` + platform bots — these are universal cognitive functions
- Task modes: `recurring | goal | reactive` — temporal behavior of work
- The execution pipeline: gather → generate → compose → deliver

**What becomes extensible (workspace-level configuration):**
- Context domain names, entity structures, synthesis templates — defined per workspace
- Task type definitions: objective, step instructions, context_reads/writes — authored by TP or developer
- Agent identity specialization: AGENT.md content, domain assignment — configured per workspace
- Step instructions: embedded in TASK.md, not in a Python registry

### The "hospital principle" evolves

ADR-176 established the "hospital principle": a fixed roster because "these are the roles all knowledge work requires." The principle was correct about **roles** (Researcher, Analyst, Writer, Tracker, Designer are genuinely universal cognitive functions) but incorrect about **roster size and domain assignment**.

The evolved principle: **Universal roles, contextual application.** The 6 specialist roles + TP + platform bots are the framework's cognitive building blocks. Which specialists are scaffolded at signup, how many of each, and what domains they're assigned to — that's contextual, driven by the user's work description. A day-trader might get 2 Analysts and no Writer. A content creator might get 2 Writers and no Tracker.

### TP gains domain composition capability

TP's compositional capability (FOUNDATIONS Axiom 5) currently means "pick from the task catalog and scaffold." It evolves to mean "compose domain structures, task definitions, and step instructions from the user's work description using framework primitives."

This is a prompt evolution, not an infrastructure change. TP already has `ManageTask(action="create")` which supports custom tasks without registry lookup. TP already has `WriteFile` for creating workspace files. The gap is behavioral: TP doesn't know it *can* compose novel definitions, because its prompt presents the registry as the menu.

---

## What changes

### Phase 1: Step instructions move to TASK.md (infrastructure) — **Implemented 2026-04-17**

**Current**: Pipeline reads `STEP_INSTRUCTIONS[step_name]` from `task_types.py` at runtime.
**New**: Pipeline reads step instructions from the `## Process` section of TASK.md first. Falls back to registry if not found in TASK.md (backwards compatibility during migration).

This is the load-bearing infrastructure change. Once step instructions live in TASK.md, TP can author them for any domain — the pipeline doesn't care where they came from.

**Implementation details:**
- Single-step tasks: `execute_task()` now reads `process_steps[0].instruction` from parsed TASK.md and injects it into `objective["step_instruction"]` before `build_task_execution_prompt()` runs. Previously, single-step tasks never read the TASK.md process instruction.
- Multi-step tasks: `_execute_pipeline()` already had TASK.md-first, registry-fallback behavior (lines 2602-2606). No change needed.
- Bootstrap override: now only fires when TASK.md instruction is empty (`not step_instruction`), preserving TASK.md-authored bootstrap instructions.

**Files**: `api/services/task_pipeline.py`

### Phase 2: Domain metadata moves to workspace files (infrastructure) — **Implemented 2026-04-17**

**Current**: Pipeline reads `WORKSPACE_DIRECTORIES[domain_key]` for temporal flag and TTL.
**New**: Pipeline reads `_domain.md` metadata file from the domain folder first. Falls back to registry (defaults to canonical/non-temporal if neither exists).

Domain metadata file format:
```markdown
---
type: context
temporal: false
ttl_days: 30
entity_type: instrument
display_name: Trading
---

Market data, signals, and analysis for tracked financial instruments.
```

**Implementation details:**
- New `_read_domain_metadata_sync()` helper in `task_pipeline.py` reads `/workspace/context/{domain}/_domain.md`, parses YAML-style frontmatter, returns metadata dict.
- `_gather_context_domains()` now calls this helper first, merges with registry fallback: `domain_meta.get("temporal", domain_def.get("temporal", False))`.
- Zero cost for existing domains (registry lookup is instant, `_domain.md` read is one extra DB query only for domains not in registry or when `_domain.md` exists).
- Type coercion: `true/false` → bool, digits → int, everything else → string.

**Files**: `api/services/task_pipeline.py`

### Phase 3: TP prompt gains domain composition guidance (behavioral) — **Implemented 2026-04-17**

Three prompt files updated to shift TP from "pick from catalog" to "compose or pick from catalog":

**workspace.py** — "Task Type Catalog" → "Task Template Library." Two creation paths now both first-class (template-based AND composed). New "Composing Custom Tasks" section teaches TP the 4-step composition pattern: determine output_kind → choose team → define step instructions → declare context domains. "Creating Agents" updated: TP can create additional specialists for domain-focused work. Domain composition guidance added.

**tools.py** — Parallel task creation section updated. Work intent → template mapping condensed. Explicit "when NO template fits" guidance with composed example.

**onboarding.py** — Domain scaffolding no longer assumes fixed 5 domains. TP instructed to use domain names from the user's own language. Examples expanded beyond competitors/market to include cases (lawyer), clients (consultant), audience (influencer).

**Files**: `api/agents/tp_prompts/workspace.py`, `api/agents/tp_prompts/tools.py`, `api/agents/tp_prompts/onboarding.py`, `api/prompts/CHANGELOG.md`

### Phase 4: Default roster — contextual customization post-init — **Implemented 2026-04-17**

The default roster stays at init time (all specialists + TP + platform bots) because signup happens BEFORE the user describes their work. The behavioral change is: TP customizes the workspace during the onboarding conversation by creating domain-appropriate tasks, scaffolding novel context domains, and optionally creating additional specialist agents. `workspace_init.py` docstring updated to reflect the template library framing.

**Files**: `api/services/workspace_init.py` (docstring)

### Phase 5: Documentation alignment (narrative) — **Implemented 2026-04-17**

All canonical docs updated in the initial commit. See "Documentation impact" section below.

---

## What doesn't change

- **The execution pipeline** — `task_pipeline.py` already reads TASK.md at runtime. Zero changes to execution logic beyond the step-instruction read path.
- **The primitive surface** — All existing primitives work as-is. No new primitives needed.
- **The compose substrate** — HTML composition reads section kinds and surface types from task output, not from registries.
- **Platform integrations** — Slack, Notion, GitHub, Commerce, Trading connections and their API clients are unchanged. Platform bots are still scaffolded on connection.
- **The 4 output_kinds** — These are genuinely universal framework categories.
- **The agent role taxonomy** — The 6 specialist roles + TP + platform bots are genuinely universal cognitive functions.
- **Database schema** — No migrations. No new tables. No column changes.

---

## The agnosticism boundary

This decision explicitly defines what is framework (fixed, universal) and what is workspace (contextual, extensible):

| Layer | Examples | Who defines it | Mutability |
|---|---|---|---|
| **Framework primitives** | output_kind, agent roles, task modes, execution pipeline, primitives | Developer | Fixed — changes require code + ADR |
| **Template library** | TASK_TYPES, WORKSPACE_DIRECTORIES, AGENT_TEMPLATES, STEP_INSTRUCTIONS | Developer | Curated examples — TP can use or compose beyond |
| **Workspace configuration** | Context domain structure, task definitions, step instructions, agent assignments, TASK.md, _domain.md | TP (from user's work description) | Per-workspace, evolves with use |

The template library is the bridge: it encodes domain expertise (how to write good step instructions for a trading digest, what entity structure works for competitor tracking) that TP can learn from. But it's not a validation gate — TP can compose definitions that don't exist in the library.

---

## Relationship to ADR-187

ADR-187 (Trading Integration) becomes the last fully hand-authored domain integration. Its value is dual:

1. **Framework validation**: Trading exercises every framework primitive — all 4 output_kinds, platform bot ownership, context domain accumulation, multi-agent coordination, write-back with consequences. If the pipeline handles trading without special-casing, the framework is validated.

2. **Template exemplar**: The trading task types, step instructions, and domain structures become high-quality templates in the library. When TP needs to compose a novel domain (e.g., for a lawyer), it can reference the patterns established by trading, commerce, and the other hand-authored domains.

ADR-187's "What this validates" section should be updated to include a sixth item: **Domain composition proof** — after the infrastructure changes in this ADR, TP should be able to compose a novel domain (e.g., legal case tracking) of comparable quality to the hand-authored trading domain, using the trading templates as reference.

---

## Documentation impact

### FOUNDATIONS.md

**Axiom 3** ("Agents Are Developing Entities"): Clarify that "Type is deterministic, fixed at creation" refers to the agent role (researcher/analyst/writer/etc.), not the roster composition. Add: "The roster of agents in a workspace is contextual — TP scaffolds specialists based on the user's work description, drawing from the universal role taxonomy."

**Axiom 5** ("TP's Compositional Capability"): Extend to include domain composition — TP composes context domains, task definitions, and step instructions, not just agent/task assignments from a catalog.

**Axiom 6** ("Autonomy Is the Product Direction"): Update onboarding sequence to reflect that TP creates domain-appropriate agents (not a fixed roster) based on work description.

**Derived Principle 9**: Clarify that agent types (roles) are fixed framework primitives, but which agents are instantiated is workspace-contextual.

### SERVICE-MODEL.md

**Entity Model > Agents**: Change "Pre-scaffolded roster" to "Default roster" with note that TP customizes based on work description. Remove specific agent count ("9 agents") — replace with "universal specialist roles + platform bots."

**Entity Model > Tasks**: Add note that task types are a template library, not an exhaustive catalog. TP can compose custom task definitions.

**Entity Model > Workspace**: Add note that context domains are extensible — the directory registry provides templates, but TP can scaffold novel domains with custom entity structures.

**Execution Flow > How Work Gets Created**: Add note that TP can compose task definitions from first principles, not just select from catalog.

### ESSENCE.md

No changes required. The four stable elements (persistent agents, accumulated context, supervision, recurring work products) and the core thesis are abstract enough to accommodate this reframe. The value proposition ("Persistent agents with accumulated context do recurring work products for you") is strengthened, not changed.

### NARRATIVE.md

No changes required. The six narrative beats never prescribe specific agent types, task types, or context domains. Beat 3 ("Meet the Product") describes the experience ("You describe your work, it creates the right agents and tasks") which is exactly the domain-agnostic model.

### registry-matrix.md

Reframe header: "Default Template Library" instead of implicit "canonical matrix." Add intro paragraph: "These registries are curated templates. TP can use them as-is or compose novel definitions for domains not represented here."

### agent-types.md

Remove "Hospital principle: The 9-agent roster is fixed and non-configurable." Replace with: "Universal roles, contextual application. The specialist roles (Researcher, Analyst, Writer, Tracker, Designer) are universal cognitive functions. Which specialists are active and what domains they serve is determined by TP based on the user's work."

### ADR-176

Add resolved decision: "The hospital principle applies to the role taxonomy (universal cognitive functions), not the roster composition (which specialists are instantiated). ADR-188 clarifies this boundary."

---

## Cost model

No incremental infrastructure cost. The changes are:
- Two read-path modifications in task_pipeline.py (step instructions from TASK.md, domain metadata from _domain.md)
- One TP prompt section addition (~500 tokens)
- Documentation updates (zero runtime cost)

The compositional TP prompt may increase token usage per onboarding conversation by ~$0.02 (one additional Sonnet round for domain composition). This is a one-time cost per task creation, amortized over the task's lifetime.

---

## Risk assessment

**Risk: TP-generated step instructions may be lower quality than hand-authored ones.**
Mitigation: The template library persists as reference material. TP is instructed to study existing templates when composing novel definitions. The hand-authored domains (Slack, Notion, GitHub, Commerce, Trading) establish patterns TP can learn from. Quality can be evaluated empirically by comparing TP-composed definitions against hand-authored ones for a test persona.

**Risk: Domain structure drift across workspaces.**
Mitigation: The framework primitives (output_kind, roles, modes) constrain the solution space. A TP-composed "legal case tracking" task must still be one of the 4 output_kinds, must still assign one of the universal specialist roles, must still declare a mode. The structural envelope is fixed; the content is contextual.

**Risk: Debugging difficulty when task definitions vary per workspace.**
Mitigation: TASK.md is the single source of truth at runtime. Debugging "why did this task produce bad output?" always starts with reading TASK.md — same as today. The difference is that TASK.md may have been composed by TP rather than templated from a registry. The file is equally readable either way.

---

## Revision history

| Date | Change |
|---|---|
| 2026-04-17 | v1 — Initial decision. Triggered by ADR-187 stress test. Registries reframed as template libraries. Five-phase implementation. Documentation impact assessed. |
| 2026-04-17 | v1.1 — Phases 1-2 implemented. Step instructions read from TASK.md first (single-step gap fixed). Domain metadata read from `_domain.md` first. Both with registry fallback. |
| 2026-04-17 | v1.2 — Phases 3-5 implemented. TP prompt rewritten: task catalog → template library, composition guidance, domain-agnostic onboarding. workspace_init.py docstring updated. All 5 phases complete. |
