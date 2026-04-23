# ADR-212: Layer Mapping Correction — Agent vs. Orchestration Taxonomy

> **Status**: Implemented (2026-04-23, shipped in five atomic commits).
> **Date**: 2026-04-23
> **Authors**: KVK, Claude
> **Ratifies**: [LAYER-MAPPING.md](../architecture/LAYER-MAPPING.md) as authoritative taxonomy.
> **Supersedes**: The "Vocabulary: production layers vs. judgment layers" hedge in THESIS.md v1 (same-day earlier) + the GLOSSARY v1.6 "Vocabulary note: Agent and agency-proper" industry-alignment compromise.
> **Amends**: FOUNDATIONS Axiom 2 + Derived Principle 14.

---

## Context

The session of 2026-04-23 produced three architectural reframings in sequence:

1. **Morning** (commits `7446929` → `2c3a88e`): introduction of a "production vs. judgment layer" distinction inside FOUNDATIONS Axiom 2, acknowledging that *agency* in the strict principal-agent sense resides in the Reviewer seat (judgment layer) while the tech industry uses "agent" for production-layer entities.

2. **Midday** (commits `740e414` → `58592ff`): two module renames (`agent_framework.py` → `agent_registry.py` → `agent_orchestration.py`) driven by iterative naming audits that attempted to rename the orchestration-side module accurately.

3. **Afternoon** (this ADR's commits): the operator observed that the "production vs. judgment" framing, while philosophically accurate, carried a hedge that "we call production entities Agents because industry" — and that this hedge was causing the vocabulary to not land in practice. The operator pushed to **flip the mapping** and use "Agent" in the sharp principal-agent sense throughout internal canon and code.

The flip required answering: **what lives where under the sharp mapping?** The answer is ratified in [LAYER-MAPPING.md](../architecture/LAYER-MAPPING.md) and summarized below. This ADR is the decision record that preserves the reasoning chain.

---

## Decision

### D1 — The sharp mapping

Under FOUNDATIONS Axiom 2 (revised v6.6, same session):

- **Agents** are judgment-bearing entities: hold standing intent on behalf of a principal (the operator), reason from principles, render judgments or accumulated domain expertise with fiduciary weight. Identity-bearing per Axiom 2.
- **Orchestration** is production machinery: task pipeline, dispatch routing, capability bundles, back-office scheduling. Stateless infrastructure per Axiom 1. Not Identity-bearing. Runs under Agents.

Members under the flip:

| Class | Members today |
|---|---|
| **Agents** (judgment-bearing) | YARNNN (systemic meta-cognitive), Reviewer (systemic judgment seat), user-authored domain Agents (instance, zero-to-many). Future: Auditor, Advocate, Custodian, etc. |
| **Orchestration** (production machinery) | The Orchestrator (system-level dispatch), production roles (Researcher, Analyst, Writer, Tracker, Designer, Reporting — previously called "Specialists"), platform integrations (capability-gated union, replacing "Platform Bots" per ADR-207 P4a), task pipeline, back-office tasks, primitive dispatch. |

### D2 — Filesystem rule for Agents

**Systemic Agents** (one per workspace, scaffolded at signup) are path-named by role (no slug). Today: `/workspace/review/` (Reviewer), `/workspace/memory/` (YARNNN). Future archetypes: `/workspace/{role}/`.

**Instance Agents** (zero-to-many per workspace, user-authored) are slug-named: `/agents/{slug}/AGENT.md` + `/agents/{slug}/memory/`.

The path shape encodes the cardinality distinction. No slug collision is possible because the namespaces don't overlap.

### D3 — Registry restructure

Per the first-principles rewrite directive (no sed rename, structure from axioms):

- `AGENT_TEMPLATES` + `AGENT_TYPES` (pre-existing aliases) are DELETED. No back-compat shim.
- `SYSTEMIC_AGENTS` — Identity-bearing Agents scaffolded per workspace. Today holds `thinking_partner` (YARNNN). Future systemic archetypes register here. NOTE: Reviewer does NOT register here — its seat is substrate at `/workspace/review/`; only its scaffold-time defaults (DEFAULT_REVIEW_*_MD constants) live in the orchestration module as a workspace_init convenience.
- `PRODUCTION_ROLES` — orchestration capability bundles: researcher, analyst, writer, tracker, designer, executive (Reporting synthesizer).
- `ALL_ROLES` — union of the two. Used for class-agnostic lookups. Not a back-compat alias — answers a distinct question.
- Platform integrations are NOT a separate entity-level registry. ADR-207 P4a already dissolved "Platform Bot" as an agent class; platform-gated capabilities live in `CAPABILITIES` with `platform_connection_requirement` gates. A "platform integration" under the sharp mapping is the *union* of platform-gated capabilities sharing a `platform_connections` row.

### D4 — Module renames

**Renamed** (orchestration content, dropping the `agent_` prefix):

| Before | After | Rationale |
|---|---|---|
| `api/services/agent_orchestration.py` | `api/services/orchestration.py` | Orchestration registries + helpers. Zero Agent code — systemic-Agent *templates* are scaffold defaults, not Agent instances. |
| `docs/architecture/agent-orchestration.md` | `docs/architecture/orchestration.md` | Doc sibling. |
| `api/services/agent_pipeline.py` | `api/services/orchestration_prompts.py` | Holds production-role prompt templates. Orchestration content. |

**Kept** (operate on Agents, so `agent_` prefix is correct):

| File | Why kept |
|---|---|
| `api/services/agent_creation.py` | Creates Agent DB rows (YARNNN + user-authored instance Agents). Operates on Agents. |
| `api/services/agent_execution.py` | Runs Agents through the full generation pipeline. Operates on Agents. |
| `api/routes/agents.py` | API routes for user-authored Agents (`/agents` surface). Operates on Agents. |

**Deleted** (tombstone):

- `api/agents/integration/` — empty directory with only a tombstone `__init__.py` documenting the ADR-153+ADR-156 deletion of ContextImportAgent. Dead code.

### D5 — Doc rewrites

- **THESIS.md** §"Vocabulary: Agents and Orchestration" — rewritten. Drops the "we call production entities Agents because industry" hedge. States the sharp mapping.
- **FOUNDATIONS.md** Axiom 2 — rewritten. Previously described four cognitive layers with "production vs judgment" sub-classification; now states the Agent/Orchestration split directly. Axiom 1 prior framing (v6.x before this session) preserved in revision history.
- **FOUNDATIONS.md** Derived Principle 14 — retargeted. "Agent seats persist; occupants rotate" applies canonically to Agent seats; orchestration bundles have configurations to tune, not occupants to rotate.
- **GLOSSARY.md** — Entities table rewritten. New entries: Orchestrator (system machinery, NOT Agent), Production role (replaces Specialist), Platform integration (replaces Platform Bot as entity term — actually a capability-level union under ADR-207 P4a), Systemic Agent, Instance Agent. Retired-terms extended: Specialist as entity, Platform Bot, "production layer" / "judgment layer" as Axiom 2 sub-classification.
- **reviewer-substrate.md** — opening rewritten. Reviewer is named as an Agent (not "a layer that happens to be an Agent"). Cross-reference to LAYER-MAPPING added.
- **architecture/README.md** — "Thesis + Axioms + Taxonomy" section header added. LAYER-MAPPING.md listed as third canonical doc.

### D6 — Historical ADR preservation

Historical ADRs that reference `agent_framework.py`, `agent_registry.py`, `agent_orchestration.py`, `agent-framework.md`, `agent-registry.md`, `agent-orchestration.md`, `AGENT_TEMPLATES`, `AGENT_TYPES`, "Specialist" (as entity), or "Platform Bot" (as entity) are preserved verbatim. They are frozen artifacts of the decision moment. This ADR lists the affected historical ADRs (non-exhaustive):

- ADR-109, ADR-110, ADR-111, ADR-116, ADR-117, ADR-128, ADR-130, ADR-138, ADR-140, ADR-149, ADR-151, ADR-158, ADR-164, ADR-166, ADR-168, ADR-174, ADR-176, ADR-183, ADR-187, ADR-189, ADR-192, ADR-194, ADR-205, ADR-207, ADR-211.

New ADRs going forward use the sharp mapping.

### D7 — External product vocabulary unchanged

Under the sharp mapping, user-authored domain Agents (what operators see on `/agents`) ARE Agents. External UI, marketing copy, website, NARRATIVE.md, ESSENCE.md — all already aligned with the sharp meaning of "Agent." **No external vocabulary shift is required.** The canon correction is internal.

### D8 — DB schema preserved

- `agents.role` column continues to hold values like `thinking_partner`, `researcher`, `slack_bot`, etc. Migration cost exceeds reader benefit. GLOSSARY exception table tracks.
- No migrations in this ADR.

---

## Implementation trail (five atomic commits)

Shipped 2026-04-23:

| Commit | Scope | SHA |
|---|---|---|
| **A** | Canon doc flip — LAYER-MAPPING + THESIS + FOUNDATIONS + GLOSSARY + reviewer-substrate + architecture/README | `fef8fbe` |
| **B** | Registry rewrite + `agent_orchestration.py` → `orchestration.py` (+ doc rename) + all import sites | `c4194a1` |
| **C** | `agent_pipeline.py` → `orchestration_prompts.py` | `455fec3` |
| **D** | Delete empty `api/agents/integration/` | `e9dec28` |
| **E** | This ADR + CLAUDE.md update + CHANGELOG entry | (this commit) |

Each commit green-state reviewable, AST-verified, no behavioral changes.

---

## Non-goals (explicitly out of scope)

- **DB migrations.** `agents.role` string values persist; renaming is costly without reader benefit.
- **External UI / marketing / website.** Already aligned with the sharp meaning.
- **Historical ADR rewrites.** Frozen artifacts.
- **`api/services/agent_creation.py` / `agent_execution.py` renames.** Kept — they operate on Agents, so the `agent_` prefix is correct.

---

## Alternatives considered (and rejected)

### Alt 1 — Keep the industry-vocabulary compromise (earlier-same-day framing)

The THESIS v1 hedge said "we use industry's 'Agent' for production entities; agency proper lives in the judgment layer." This compromise was rejected because (a) every design decision touching the architecture during the session drifted toward the industry-compromise side, producing wrong naming in code, and (b) the operator observed that the vocabulary wasn't landing — the split-brain between philosophical claim and operational vocabulary was confusing.

### Alt 2 — Rename externally too (fight industry vocabulary)

Rejected because external product vocabulary (user-authored domain Agents on `/agents`) already ARE Agents under the sharp mapping. No external shift needed. The canon correction is internal only.

### Alt 3 — Split `orchestration.py` into `agent_types.py` + `orchestration_dispatch.py`

Considered and rejected. The orchestration module is coherent as a single file; splitting would add file-count churn without improving legibility. The internal registry split (SYSTEMIC_AGENTS / PRODUCTION_ROLES / ALL_ROLES) gives the same structural clarity.

### Alt 4 — Rename `agent_creation.py` → `orchestration_scaffolding.py` and `agent_execution.py` → `orchestration_execution.py`

Considered in the earlier-session naming audit and rejected after the operator's mid-execution feedback. These modules *operate on Agents* — they create Agents (DB rows) and run Agents (generation pipelines). The `agent_` prefix is correct under the sharp mapping. Renaming would have introduced drift.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-23 | v1 — Implemented across five atomic commits same day. LAYER-MAPPING.md is the authoritative taxonomy doc; this ADR is the decision record. |
