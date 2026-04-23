# Layer Mapping — Agent vs. Orchestration

> **Status**: Canonical (internal)
> **Date**: 2026-04-23 (ratified by operator same day)
> **Authors**: KVK, Claude
> **Scope**: The authoritative taxonomy for YARNNN's two-class cognitive-layer model. Names every entity, classifies it, and specifies where it lives in code and documentation.
> **Audience**: Internal. Frames code renames, ADR amendments, and canonical vocabulary. **Not a compromise with industry vocabulary** — this document corrects the earlier canon's vocabulary drift.
> **Supersedes**: the hedge in THESIS §"Vocabulary: production layers vs. judgment layers" v1 (same-day earlier) — this doc corrects that section's "we call production entities Agents because industry" compromise.

---

## Why this doc exists

The session of 2026-04-23 produced a sharpening of architectural vocabulary that the earlier canon (THESIS.md §"Vocabulary: production layers vs. judgment layers" + GLOSSARY v1.6) captured imperfectly. The earlier canon hedged: it acknowledged that *agency in the philosophical sense* lives in the judgment layer, but then said "we call production entities Agents anyway because industry." That hedge is rejected here.

This document replaces the hedged mapping with a sharp one:

- **Agents** = judgment-bearing entities. Fiduciary, principal-representing, hold standing intent, accumulate calibration. **Name belongs to them.**
- **Orchestration** = production machinery. Dispatch, coordination, capability-bundling, tool-use under instruction. **Not Agents.** Not fiduciary. No standing intent of their own.

External UI and marketing vocabulary ("Agents" as the personified workers the operator creates) remains **compatible** with the sharp mapping because those user-created workers ARE Agents in the sharp sense — they hold domain intent, they represent the operator, they accumulate memory. The canon realigns; the external product vocabulary does not need to shift.

---

## The Two Classes

### Agents (judgment layer)

**Definition**: entities that hold standing intent on behalf of a principal (the operator), reason from principles against inputs, and render judgments that carry fiduciary weight. Agents *use* tools and orchestration capabilities to do their work, but their essence is **judgment**, not **production**.

**Properties**:
- Persistent identity (AGENT.md or equivalent substrate home)
- Standing intent between invocations (the operator's declared principles live in their substrate)
- Fiduciary posture (act on behalf of the operator)
- Accumulate calibration / track record / expertise over tenure
- Reason from inputs and render reasoned outputs (verdicts, compositions, judgments)
- Seat-interchangeable at the occupant level (FOUNDATIONS Principle 14)

**Members of this class:**

| Agent | Substrate home | Role |
|---|---|---|
| **YARNNN** (the super-agent) | `/workspace/memory/` + AGENT.md implicit via role | The conversational meta-cognitive Agent the operator addresses. Composes team, scaffolds tasks, surfaces state. Fiduciary at the workspace level. |
| **Reviewer** | `/workspace/review/` (7 canonical files) | Judgment seat. Reads proposed actions, renders approve/reject/defer. Fiduciary at the proposal level. |
| **User-authored domain Agents** | `/agents/{slug}/AGENT.md` + `/agents/{slug}/memory/` | Persistent domain experts authored by the operator through YARNNN chat. Hold domain intent, accumulate domain context, represent the operator in a specific domain. |
| **Future judgment archetypes** | `/workspace/{archetype}/` (future) | Auditor (retrospective judgment), Advocate (counter-position), Custodian (drift detection), etc. Any future seat that holds standing intent and renders judgment. |

### Orchestration (production/dispatch layer)

**Definition**: the machinery that dispatches production work, bundles capabilities, and routes tasks to the right tool surface. Orchestration has no standing intent, no fiduciary relationship, no accumulated identity. It is stateless infrastructure that runs *under* Agents.

**Properties**:
- Stateless between invocations (per Axiom 1 — state lives in files, computation is stateless over them)
- No fiduciary posture
- Dispatches work; does not *render judgment on what work to do*
- Capability-bundling: packages tools + prompts + runtimes behind named roles
- Invoked by Agents (and by scheduled tasks) to get work done

**Members of this class:**

| Entity | What it is under sharp mapping | Why it's orchestration, not Agent |
|---|---|---|
| **The Orchestrator** (system machinery) | The task pipeline, dispatch routing, team composition logic, capability gating. | It runs; it does not judge. It is tooling YARNNN-the-Agent (and Reviewer, user-Agents) use to get production work dispatched. |
| **Specialists** (Researcher, Analyst, Writer, Tracker, Designer, Reporting) | Production-style capability bundles. "Researcher" = research-style-production capability; "Writer" = writing-style-production capability. | No persistent identity, no standing intent, no fiduciary relationship. They are pre-packaged production roles the Orchestrator dispatches against. |
| **Platform Bots** (Slack/Notion/GitHub/Commerce/Trading) | Integration-style capability bundles. "Slack Bot" = Slack-API-access capability bundled with platform-specific dispatch. | ADR-207 P4a already dissolved these as an agent class; this mapping formalizes the reclassification. |
| **Task pipeline, scheduler, primitive dispatch** | Core orchestration plumbing. | Runtime coordination. No judgment. |
| **Back-office tasks** (hygiene, cleanup, reconciliation, calibration-rebuild) | Scheduled orchestration work, deterministic. | They run; they do not judge. The calibration rebuild is orchestration machinery operating *on behalf of* the Reviewer Agent's substrate. |

### The split in one sentence

*Agents hold intent and render judgment. Orchestration runs under them, bundles capabilities, and dispatches production.*

---

## Specific clarifications (to prevent drift)

### 1. Agents use tools; that doesn't make them orchestration

A judge uses court records. A lawyer uses precedent. Neither becomes infrastructure because they use tools. The same applies here: the Reviewer Agent uses `chat_completion_with_tools`, reads `_performance.md`, writes `decisions.md` — all via Orchestration infrastructure. That's Agents-using-tools, not Agents-being-orchestration.

### 2. YARNNN splits cleanly into Agent and Orchestrator

The name "YARNNN" today covers two distinct things that this mapping separates:

- **YARNNN (the Agent)** — the conversational, personified, user-addressable fiduciary at the meta-cognitive layer. Holds memory, awareness, playbook, style. Reasons with the operator about team composition, task scaffolding, system state. Classified: **Agent**.
- **Orchestrator (the system machinery)** — the team composition logic, task pipeline, dispatch routing, capability gating, back-office scheduling. Classified: **Orchestration**.

**YARNNN-the-Agent uses the Orchestrator** the way a CEO uses staff. The CEO is a fiduciary (an agent); the staff is machinery. They are not the same thing.

The name used for the system-machinery side is **Orchestrator** (singular, system-level). It owns no persistent identity of its own. The name used for the Agent side is **YARNNN** (personified, user-addressable).

### 3. Specialists and Platform Bots are capability bundles, not Agents

Today the canon has been describing Specialists and Platform Bots as "agents" (production sense, industry-loose). Under the sharp mapping, they are **orchestration-layer capability bundles**:

- A "Specialist" is a packaged production role — templates, prompts, default instructions, tool surface — that the Orchestrator dispatches against when a task requires that style of production.
- A "Platform Bot" is a packaged integration role — platform API access, per-platform primitives, dispatch routing — that the Orchestrator invokes when a task requires that platform.

Neither holds standing intent. Neither represents the operator fiduciarily. Neither accumulates identity-level expertise over tenure. They are **tooling the Orchestrator uses**. The word "Specialist" and "Platform Bot" are retained as working terms for the orchestration-role concept; they are explicitly not Agents.

### 4. User-authored domain Agents ARE Agents

The personified domain workers the operator creates through YARNNN chat — these DO hold standing intent (AGENT.md), accumulate domain context, represent the operator in a specific domain. They are Agents in the sharp sense. They use Orchestration capabilities to do their work (they get dispatched through the task pipeline, they use Specialist tool bundles for production), but they are not themselves orchestration.

This keeps **external UI/marketing vocabulary aligned with the sharp mapping**: the "Agents" the operator sees on `/agents` ARE Agents. Zero shift needed in user-facing language.

### 5. "Agent" in industry vocabulary (LLM + tools + loop) maps to us how?

Industry's "agent" is closest to YARNNN's **Specialist** (orchestration capability bundle) — it's a packaged production role with tools and a prompt. Some industry "agents" are closer to our **Agent** class (ones that hold persistent intent — e.g., a "personal assistant agent" that remembers preferences), but most are production pipelines with longer loops.

The canon's earlier hedge said "we use the industry word." We now say: **we use the word in the sharp sense internally, and externally we describe the user-authored domain workers as Agents (which are Agents in the sharp sense anyway)**. The divergence is pedagogical, not compromise — industry's loose usage doesn't map cleanly, and attempting to honor it in canon was what caused the drift.

---

## What changes in code (proposed — awaiting operator confirmation)

### Renames (file-level)

| Today | Proposed | Rationale |
|---|---|---|
| `api/services/agent_orchestration.py` | `api/services/orchestration.py` | Drop "agent_" prefix. The file IS orchestration (production machinery, capability bundles, dispatch metadata). The word "agent" in the name was an artifact of the pre-flip vocabulary. |
| `api/agents/yarnnn.py` | `api/agents/yarnnn.py` (stays) + extract orchestration-side to `api/services/orchestrator.py` | YARNNN-the-Agent class stays. Orchestration logic inside YarnnnAgent (if any bleeds) gets extracted. |
| `api/services/agent_creation.py` | `api/services/orchestration_scaffolding.py` | This module scaffolds production-layer entities (Specialists, YARNNN bootstrap). It's orchestration-side. |
| `api/services/agent_execution.py` | `api/services/orchestration_execution.py` | This module is the full generation-to-delivery pipeline for production work. Orchestration. |
| `api/services/agent_pipeline.py` | `api/services/orchestration_prompts.py` | This module holds role-specific prompts and prompt assembly for production-style agents. Orchestration-side. |
| `api/agents/` directory | Keep Agent-class entities (yarnnn.py, reviewer_agent.py, chat_agent.py, base.py) | The directory is now explicitly "entities-that-are-Agents-in-the-sharp-sense." |
| `api/agents/integration/` | `api/orchestration/integration/` (future, if actual content) | Today it only has `__init__.py` — empty. Move or delete. |

### Doc renames

| Today | Proposed | Rationale |
|---|---|---|
| `docs/architecture/agent-orchestration.md` | `docs/architecture/orchestration.md` | Drop "agent-" prefix. The doc is about orchestration. |
| `docs/architecture/reviewer-substrate.md` | `docs/architecture/reviewer-substrate.md` (stays) | Already aligned — Reviewer is an Agent; the substrate doc is about the Reviewer Agent's canonical home. |
| `docs/architecture/authored-substrate.md` | `docs/architecture/authored-substrate.md` (stays) | Already aligned — write-path discipline, independent of layer class. |

### Class renames

| Today | Proposed | Rationale |
|---|---|---|
| `YarnnnAgent` | `YarnnnAgent` (stays) | YARNNN is an Agent. The name is accurate. |
| `ChatAgent` | `ChatAgent` (stays) | ADR-124's ChatAgent is a user-authored-Agent's conversational runtime. Accurate. |
| `ReviewerAgent` | `ReviewerAgent` (stays — the module name is accurate) | The module is the AI occupant implementation of the Reviewer Agent seat. Accurate. |
| `BaseAgent` | `BaseAgent` (stays) | Abstract base for Agent classes. Accurate. |
| Registry constants `AGENT_TEMPLATES`, `AGENT_TYPES` | Rename to `ROLE_TEMPLATES`, `ROLE_TYPES` or `CAPABILITY_BUNDLES` | These describe orchestration roles (Specialists, Platform Bots), not Agents. The `AGENT_` prefix is the vocabulary drift. |
| DB column `agents.role` | Stays (migration exception) | Schema-level strings are costly to migrate; stable working terms. GLOSSARY exception table tracks this. |

### Doc content updates

- **THESIS.md** `§Vocabulary` — rewrite. Drop the "we call production entities Agents because industry" hedge. Replace with the sharp mapping. State: *Agents are judgment-bearing, fiduciary, principal-representing entities. Orchestration is production machinery. External UI happens to align with the sharp mapping because user-authored Agents are Agents.*
- **GLOSSARY.md** — rewrite the Entities table. "Specialist" and "Platform Bot" move under an "Orchestration capability bundles" subsection. "Agent" definition sharpened. Add "Orchestrator" as a canonical term (system-machinery side of YARNNN).
- **FOUNDATIONS.md** — Axiom 2 rewords. Cognitive-layer taxonomy becomes **Agents** (first class; judgment-bearing; multiple members — YARNNN, Reviewer, user-authored domain Agents, future archetypes) vs **Orchestration** (not cognitive layer — production machinery under Agents). Principle 14 ("Roles persist; occupants rotate") refined to apply canonically to Agent seats.
- **reviewer-substrate.md** — retitle or re-frame. This doc is about the Reviewer **Agent**, not a "Reviewer layer" that is somehow not an Agent. Rename section headers where they say "Reviewer seat" to "Reviewer Agent seat" (seat vocab preserved — seat is the role, occupant is who fills it — but it's explicit now that the role is an Agent).
- **CLAUDE.md** — the system reminders + architecture overview section gets the sharp mapping.
- **ADR cross-references** — historical ADRs preserved; new ADR-212 (Layer Mapping Correction) authored as decision record.

### ADR-212 (Proposed)

Write a single ADR that:
- Records the vocabulary correction as a deliberate architectural decision
- Supersedes the hedge in THESIS v1 §Vocabulary
- Names the sharp mapping as canonical
- Lists the renames executed and the scope boundaries
- Preserves the historical ADRs that used the old vocabulary as frozen artifacts

---

## What does NOT change

- **External UI / marketing / website / NARRATIVE.md / ESSENCE.md** — "Agents" externally means what the operator sees on `/agents`. Under the sharp mapping those ARE Agents. No external vocabulary shift.
- **DB schema** — `agents` table name + `agents.role` column stay. Migration cost exceeds reader benefit; GLOSSARY exception table documents.
- **Public API shapes** — no endpoint renames. Response envelopes already enriched for Phase 4 (current_occupant field). No more shape changes.
- **ADRs already shipped** — historical artifacts preserve old vocabulary. Not rewritten.
- **`api/prompts/CHANGELOG.md` entries prior to this flip** — historical log. Preserved verbatim.

---

## Sequencing (atomic commits, in order)

Each commit lands independently reviewable and green (backend imports resolve, AST parses clean, no dual paths).

**Commit A — Canon doc flip.**
- New: `LAYER-MAPPING.md` (this doc, ratified)
- Rewrite: THESIS §Vocabulary, FOUNDATIONS Axiom 2 + Principle 14 wording, GLOSSARY entries, reviewer-substrate opening + section headers
- Update: `architecture/README.md` index
- No code touched.
- Outcome: canon layer internally coherent under sharp mapping.

**Commit B — YARNNN split (code).**
- Extract orchestration logic from `YarnnnAgent` into new `api/services/orchestrator.py` (team composition helpers, if any bleed past what's already in orchestration.py).
- `YarnnnAgent` class retains Agent identity + conversational-runtime logic.
- Update `CLAUDE.md` + any docs that describe YARNNN's split.
- Outcome: YARNNN-as-Agent clean from Orchestrator-as-machinery.

**Commit C — Orchestration module rename.**
- `api/services/agent_orchestration.py` → `api/services/orchestration.py` (third rename in the chain, final).
- `docs/architecture/agent-orchestration.md` → `docs/architecture/orchestration.md`.
- Rename registry constants: `AGENT_TEMPLATES` → `ORCHESTRATION_ROLES` (or `CAPABILITY_BUNDLES`; pick in drafting).
- Update all import sites + canon cross-refs.
- Outcome: orchestration-side modules explicitly named.

**Commit D — Service module renames.**
- `agent_creation.py` → `orchestration_scaffolding.py`
- `agent_execution.py` → `orchestration_execution.py`
- `agent_pipeline.py` → `orchestration_prompts.py`
- Update all import sites.
- Outcome: service-layer file names reflect orchestration-vs-agent split.

**Commit E — `/api/agents/` directory cleanup.**
- Move `api/agents/integration/` → `api/orchestration/integration/` (if non-empty) or delete (if empty).
- Confirm `api/agents/` contains only Agent-class entities.
- Outcome: directory boundary clean.

**Commit F — ADR-212 + final closeout.**
- Write ADR-212 "Layer Mapping Correction" as decision record.
- Amend ADR-194 v2, ADR-211 with status-note pointers to ADR-212 / LAYER-MAPPING.md.
- Update CLAUDE.md architecture overview section.
- Outcome: decision record preserved for future readers.

---

## Resolved questions (operator-confirmed 2026-04-23)

All five open questions resolved. Decisions locked for implementation.

**Q1 RESOLVED** — Registry structure. The `AGENT_TEMPLATES` constant is **not renamed** — it is **fully rewritten** per operator instruction ("revisited from first principles... re-write should be pure to the axioms and canon"). Split into three registries along the sharp mapping:

- `SYSTEMIC_AGENTS` — structural singular Agents (Identity layer). Today: `yarnnn`. Future: `auditor`, `advocate`, etc.
- `PRODUCTION_ROLES` — orchestration capability bundles for production work. Today: `researcher`, `analyst`, `writer`, `tracker`, `designer`, `reporting`.
- `PLATFORM_INTEGRATIONS` — orchestration capability bundles for platform APIs. Today: `slack`, `notion`, `github`, `commerce`, `trading`. (Aligns with ADR-207 P4a's dissolution of Platform Bots as agent class.)

Each name honestly describes what lives under it. Agents get their own registry (Identity layer); orchestration bundles get two registries (production vs. integration). No entry in any of the three registries carries personification — only `SYSTEMIC_AGENTS` entries carry Agent-class semantics, and those are explicitly Agents by definition.

**Q2 RESOLVED** — "Specialist" → **"production role"**. "Platform Bot" → **"platform integration"**. Per operator: no personification when under orchestration. Working terms for the capability-bundle concept.

- A production role has a *name* (Researcher, Analyst, Writer, etc.) that labels the bundle's content. "Researcher" is the name of a production-role bundle, not a personified worker.
- A platform integration has a *name* (Slack, Notion, etc.) that labels the API it wraps. "The Slack integration" is a capability-bundle, not a personified bot.

Going forward, any orchestration-layer entity is named without personification — the name describes what the bundle *does* or *wraps*, not an anthropomorphized actor.

**Q3 RESOLVED** — `/agents/{slug}/` stays for user-authored domain Agents. They are Agents in the sharp sense.

**Q4 RESOLVED** — `/workspace/review/` stays for the Reviewer Agent's substrate. Already aligned.

**Q5 RESOLVED** — YARNNN Agent's memory substrate stays at `/workspace/memory/*.md` (awareness, _playbook, style, notes). Canon documents that `/workspace/memory/` is YARNNN Agent's substrate home. `/workspace/yarnnn/` consolidation deferred — current layout is workable; vocabulary flip is the urgent thing.

---

## The filesystem rule (systemic-slot vs. instance Agents)

Falls out of Q3 + Q4 + Q5 taken together. Stated here for clarity:

**Structural rule**: *Systemic Agents (one per workspace, scaffolded at signup) are path-named by role. Instance Agents (many per workspace, user-authored) are path-named by slug.*

| Agent class | Cardinality | Path shape | Examples |
|---|---|---|---|
| Systemic Agent | exactly one per workspace | `/workspace/{role}/` or conventional home | `/workspace/review/` (Reviewer), `/workspace/memory/` (YARNNN) |
| Instance Agent | zero-to-many per workspace | `/agents/{slug}/` | `/agents/acme-competitor-tracker/`, `/agents/weekly-brief-writer/` |

The path shape encodes the cardinality distinction. Future systemic archetypes (Auditor, Advocate, etc.) would land at `/workspace/{role}/`. Future user-authored-entity-types would land at `/{type}/{slug}/`. This is enforceable at the filesystem layer — no slug-collision between systemic and instance Agents, because their namespaces don't overlap.

**Why no slug for systemic Agents**: because there's exactly one per workspace, a slug would add no disambiguation. The role name IS the address. Adding a slug would imply multiplicity that doesn't exist.

**Why slug for instance Agents**: because there are many per workspace, the slug IS the disambiguation. The role (Researcher, Analyst, etc.) is *what they are*; the slug is *which one they are*.

---

## Updated proposed renames (per Q1 + Q2 resolutions)

### Registry structure (`api/services/orchestration.py` — third-chain rename target)

**Fully rewritten (not sed-renamed)**:

```python
# SYSTEMIC_AGENTS — Identity layer, structural singular Agents per workspace.
SYSTEMIC_AGENTS = {
    "yarnnn": {
        "display_name": "YARNNN",
        "role_slug": "yarnnn",           # legacy: "thinking_partner"
        "class": "meta-cognitive",
        "capabilities": [...],
        "default_instructions": ...,
        # No personification note — YARNNN IS personified (user-addressable Agent)
    },
    # future systemic Agents land here:
    # "auditor": { ... },
}

# PRODUCTION_ROLES — orchestration capability bundles for production work.
# NOT Agents. No personification. Each bundle packages tools + prompts +
# runtime defaults for a specific style of production.
PRODUCTION_ROLES = {
    "researcher": { ... },
    "analyst": { ... },
    "writer": { ... },
    "tracker": { ... },
    "designer": { ... },
    "reporting": { ... },
}

# PLATFORM_INTEGRATIONS — orchestration capability bundles for platform
# APIs. Capability-gated by active platform_connections (ADR-207 P4a).
PLATFORM_INTEGRATIONS = {
    "slack": { ... },
    "notion": { ... },
    "github": { ... },
    "commerce": { ... },
    "trading": { ... },
}

# CAPABILITIES, RUNTIMES, PLAYBOOK_METADATA, TASK_OUTPUT_PLAYBOOK_ROUTING
# remain as lower-level orchestration primitives — unchanged in structure,
# updated only in docstrings to reflect sharp mapping.
```

**Migration consideration (code-level)**: every consumer of `AGENT_TEMPLATES` today reads by key (e.g., `AGENT_TEMPLATES["researcher"]`). Splitting requires consumers to route: callers asking about a production role read `PRODUCTION_ROLES`; callers asking about a platform integration read `PLATFORM_INTEGRATIONS`; callers asking about YARNNN read `SYSTEMIC_AGENTS`. A thin `resolve_orchestration_role(name)` helper can unify reads where the caller doesn't know which registry the name lives in. No backward-compat shim — one way to look up each role-class.

**DB exception**: `agents.role` column retains strings like `thinking_partner`, `researcher`, `slack_bot`, etc. These are legacy slugs — a DB migration would churn without reader benefit. GLOSSARY exception table tracks. New DB writes for systemic Agents use the new slugs (`yarnnn`); legacy rows may carry the old slug. Read path tolerates both via `LEGACY_ROLE_MAP`.

### Filesystem renames

| Today | Proposed | Rationale |
|---|---|---|
| `api/services/agent_orchestration.py` | `api/services/orchestration.py` | Third and final rename in the chain (agent_framework → agent_registry → agent_orchestration → orchestration). Drops "agent_" prefix entirely. |
| `docs/architecture/agent-orchestration.md` | `docs/architecture/orchestration.md` | Same. |
| `api/services/agent_creation.py` | `api/services/orchestration_scaffolding.py` | Creates production-layer entities via registries. |
| `api/services/agent_execution.py` | `api/services/orchestration_execution.py` | Runs the production-layer generation-to-delivery pipeline. |
| `api/services/agent_pipeline.py` | `api/services/orchestration_prompts.py` | Holds production-role prompt templates. |
| `api/agents/` | `api/agents/` (stays; holds only Agent-class entities) | Keeps YarnnnAgent, ReviewerAgent, ChatAgent, BaseAgent. |
| `api/agents/integration/` | Delete (empty today) | Nothing there; removes a dead directory. |
| `api/routes/agents.py` | `api/routes/agents.py` (stays) | This route surfaces user-authored domain Agents on `/agents` — they ARE Agents. |

### Class renames — None required

Agent-class entities keep their names. No class-level rename cascades.

### Doc content rewrites

- **THESIS.md** §"Vocabulary: production layers vs. judgment layers" — rewritten. Drop the "we call production entities Agents because industry" hedge. State the sharp mapping.
- **GLOSSARY.md** — Entities table rewritten. "Agent" sharpened. "Specialist" → renamed to "Production role" with retired-terms note. "Platform Bot" → "Platform integration" with retired-terms note. New entries: "Orchestration," "Production role," "Platform integration," "Systemic Agent," "Instance Agent."
- **FOUNDATIONS.md** Axiom 2 — rewords cognitive-layer taxonomy to **Agents** (Identity layer — YARNNN, Reviewer, user-authored domain Agents, future archetypes) vs **Orchestration** (production machinery under Agents). Principle 14 "Roles persist; occupants rotate" retargets to canonically apply to Agent seats.
- **reviewer-substrate.md** — retitle sections to call Reviewer an "Agent" (not a "layer" that happens to be an Agent). Seat vocabulary preserved (seat = role; occupant = who fills it).
- **CLAUDE.md** — architecture overview + system reminders updated.
- **api/prompts/CHANGELOG.md** — new entry `[2026.04.23.7]` records the full flip.

### ADR-212 — Layer Mapping Correction

Write a single new ADR that:
- Records the full vocabulary flip as a deliberate architectural decision
- Names LAYER-MAPPING.md (this doc) as the authoritative taxonomy
- Supersedes the hedge in THESIS §Vocabulary (v1 of the section)
- Lists the rename pass executed and the scope boundaries
- Preserves historical ADRs (109, 116, 128, 130, 138, 140, 149, 151, 158, 164, 166, 168, 174, 176, 183, 187, 189, 192, 194, 205, 207, 211) as frozen artifacts
- Notes DB-schema exception (agents.role column strings retained)

---

## Commit sequencing (revised per Q1/Q2 resolutions)

Six atomic commits. Each green-state reviewable. No dual paths.

**Commit A — Canon doc flip + LAYER-MAPPING ratification.**
- Ratify LAYER-MAPPING.md (this doc, minus the "awaiting operator review" language)
- Rewrite THESIS §Vocabulary, FOUNDATIONS Axiom 2 + Principle 14 wording, GLOSSARY Entities table (+ new entries for Orchestration / Production role / Platform integration / Systemic Agent / Instance Agent / retired-terms notes for Specialist and Platform Bot), reviewer-substrate section headers
- Update `architecture/README.md` index
- No code touched
- Outcome: canon layer internally coherent under sharp mapping

**Commit B — Registry rewrite (first-principles, not sed).**
- In `agent_orchestration.py`: rewrite `AGENT_TEMPLATES` as three registries (`SYSTEMIC_AGENTS` + `PRODUCTION_ROLES` + `PLATFORM_INTEGRATIONS`)
- Add `resolve_orchestration_role(name)` helper for unified lookup
- Update all consumers of `AGENT_TEMPLATES` to route to the right registry
- Update default content docstrings (reviewer defaults, YARNNN defaults) to reflect layer classification
- Outcome: registry structure reflects the sharp mapping; no backward-compat shim

**Commit C — Orchestration module rename (third-chain final).**
- `api/services/agent_orchestration.py` → `api/services/orchestration.py`
- `docs/architecture/agent-orchestration.md` → `docs/architecture/orchestration.md`
- Update all import sites + canon cross-refs
- Outcome: orchestration-side module explicitly named; end of the three-rename chain

**Commit D — Service module renames.**
- `agent_creation.py` → `orchestration_scaffolding.py`
- `agent_execution.py` → `orchestration_execution.py`
- `agent_pipeline.py` → `orchestration_prompts.py`
- Update all import sites
- Outcome: service-layer file names reflect orchestration-vs-agent split

**Commit E — `/api/agents/` directory cleanup + integration/ removal.**
- Delete empty `api/agents/integration/`
- Confirm `api/agents/` contains only Agent-class entities (yarnnn.py, reviewer_agent.py, chat_agent.py, base.py)
- Outcome: directory boundary clean

**Commit F — ADR-212 + final closeout.**
- Write ADR-212 "Layer Mapping Correction"
- Amend ADR-194 v2, ADR-211 with status-note pointers to ADR-212 / LAYER-MAPPING.md
- Update CLAUDE.md architecture overview section
- `api/prompts/CHANGELOG.md` entry `[2026.04.23.7]` landing the flip
- Outcome: decision record preserved for future readers

**Note on YARNNN split (previously Commit B in earlier sequencing)**: after reviewing the current code, the YARNNN-as-Agent class (YarnnnAgent) and the Orchestrator-as-machinery are *already* largely separated — YarnnnAgent lives in `api/agents/yarnnn.py` (Agent class) and the team-composition/dispatch logic lives in `task_pipeline.py` + `orchestration.py` (machinery). The split is real in code today; the canon just didn't name it. Commit A (canon doc flip) names the split. No code extraction needed in its own commit. If audit during execution reveals orchestration logic bleeding into YarnnnAgent, we extract in Commit C or D as part of the rename work.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-23 | v1 — Initial draft. Supersedes the hedge in THESIS §Vocabulary. |
| 2026-04-23 | v1.1 — Operator resolved Q1–Q5. Registry restructured into three (`SYSTEMIC_AGENTS` + `PRODUCTION_ROLES` + `PLATFORM_INTEGRATIONS`) per first-principles rewrite directive. "Specialist" → "production role"; "Platform Bot" → "platform integration". Structural-slot-vs-instance filesystem rule added. Commit sequencing revised to six atomic commits. YARNNN-split commit dissolved (the split is already real in code; canon names it). |
