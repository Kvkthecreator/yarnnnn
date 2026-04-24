# Agent Composition — Prompts, Substrate, Versioning

> **Status**: Canonical.
> **Audience**: Engineers and operators touching prompts, agent substrate, or ADRs that reshape the agent layer.
> **Purpose**: Single reference for how YARNNN composes its agents — what each agent reads at reasoning time, how operator-authored substrate vs seat-owned substrate vs generated output separate cleanly, and how to version + document iterations so future refactors don't drift.

---

## 1. Why this doc exists

YARNNN's agent layer has iterated fast through ADR-186 (prompt profiles), ADR-194 v2 (Reviewer seat), ADR-211 (Reviewer Phase 4), ADR-212 (LAYER-MAPPING flip), ADR-216 (YARNNN reclassification + persona wiring), and ADR-217 (workspace autonomy split). Each ADR is the decision record for a specific change. None of them — nor the `api/prompts/CHANGELOG.md` that tracks prompt edits — serve as **"how does agent composition work today"**.

This doc is that reference. It answers:

- What files does each agent read, in what order, at what time?
- What's authored by the operator vs the seat itself vs the platform?
- What's shared between agents vs seat-bound?
- How do we version prompts and persona content?
- What discipline do we apply when a refactor changes the composition?

Reading order: §2 the two-layer model, §3 per-agent composition, §4 operator-vs-Reviewer symmetry, §5 versioning + iteration, §6 appendix references.

---

## 2. The two-layer model

Under FOUNDATIONS v6.0 + ADR-212 + ADR-216, every entity in YARNNN falls into one of two layers:

- **Orchestration layer** — mechanical, opinion-less, substrate-writing infrastructure. Schedules tasks, routes capabilities, composes prompts, dispatches runs, writes substrate, fetches platform data, handles compose/delivery, surfaces chat. Sits in Mechanism (Axiom 5) + Channel (Axiom 6). Not persona-bearing. Performance-fungible.
- **Judgment layer** — persona-bearing Agents holding standing intent on behalf of the operator. Reason from authored persona + framework + substrate. Sits in Identity (Axiom 2). NOT performance-fungible — persona change changes output distribution.

Two members of the orchestration layer that frequently get mistaken for the judgment layer:

- **YARNNN** (the chat-surface entity) — orchestration chat surface, not Agent (ADR-216 D2). Platform-fixed voice; no workspace-authored IDENTITY file. It *drives* the orchestrator; it doesn't carry persona.
- **Production roles** (researcher, analyst, writer, tracker, designer, reporting) — orchestration capability bundles, not Agents. No persona, no standing intent.

Members of the judgment layer:

- **Reviewer** (systemic) — one per workspace, persona-bearing, gates irreversible writes.
- **User-authored domain Agents** (instance) — zero-to-many per workspace, persona-bearing, operator-authored.
- Future systemic Agents (Auditor, Advocate, Custodian, etc. per ADR-212 D1 forward-looking note).

---

## 3. Per-agent composition

### 3.1 YARNNN (orchestration chat surface)

**Purpose**: conversational façade of the orchestrator. Operator drives the system through YARNNN.

**Substrate reads at reasoning time**:

| File | Read path | Source |
|------|-----------|--------|
| Compact index (ADR-159) | `working_memory.format_compact_index()` | Generated from workspace state at each turn |
| `/workspace/context/_shared/MANDATE.md` | Via tool reads | Operator-authored (ADR-207) |
| `/workspace/context/_shared/IDENTITY.md` | Via working memory + tool reads | Operator-authored (ADR-206) |
| `/workspace/context/_shared/BRAND.md` | Via tool reads | Operator-authored (ADR-206) |
| `/workspace/context/_shared/CONVENTIONS.md` | Via tool reads | Operator-authored (ADR-206) |
| `/workspace/context/_shared/AUTONOMY.md` | Via tool reads | Operator-authored (ADR-217) — informs chat reasoning about what the AI is authorized to do autonomously |
| `/workspace/memory/AWARENESS.md` + working memory files | Via working memory | YARNNN's own orchestration state |

**Persona**: none. `api/agents/yarnnn_prompts/base.py::BASE_PROMPT` declares the fixed-voice interlocutor identity. There is no workspace-authored YARNNN IDENTITY file per ADR-216 D2.

**Prompt composition** (per ADR-186 profile-aware assembly in `api/agents/yarnnn_prompts/__init__.py`):

```
System prompt (cached, platform-fixed):
  BASE_PROMPT ("You are YARNNN — the user's super-agent...")
  + {workspace | entity} profile behaviors
  + TOOLS_CORE (primitive docs, capabilities, workforce model)
  + PLATFORMS_SECTION (platform tools)
  + CONTEXT_AWARENESS (for workspace profile)
User message (dynamic):
  + {context} injection (compact index)
  + Entity preamble (for entity profile: TASK.md, run log, output)
  + User's turn content
```

**Profile selection** (ADR-186): `api/routes/chat.py::resolve_profile()` maps `DeskSurface.type` to `workspace` (full: onboarding, task catalog, creation) or `entity` (scoped: feedback routing, evaluate/steer/complete).

**Model**: Claude Sonnet 4.6, streaming.

---

### 3.2 Reviewer (systemic persona-bearing Agent)

**Purpose**: gates irreversible writes. Reads proposed actions + substrate + persona + framework, renders approve/reject/defer.

**Substrate reads at reasoning time** (per ADR-216 Commit 2 + ADR-217 Commit 2):

| File | Read at | Source |
|------|---------|--------|
| `/workspace/review/IDENTITY.md` | Reviewer agent (`reviewer_agent.py::_build_user_message`) | Operator-authored (ADR-216 D4). Declares the persona. |
| `/workspace/review/principles.md` | Reviewer agent | Operator-authored. Declares the framework (checks + narrowing conditions). |
| `/workspace/context/_shared/AUTONOMY.md` | Dispatcher (`review_proposal_dispatch.py` + `review_policy.py::load_autonomy`) | Operator-authored (ADR-217). Declares the delegation ceiling — NOT read by the Reviewer agent itself; enforced by the dispatcher before invocation. |
| `/workspace/context/{domain}/_operator_profile.md` | Reviewer agent | Operator-authored. Strategy + style context. |
| `/workspace/context/{domain}/_risk.md` | Reviewer agent | Operator-authored. Hard floors. |
| `/workspace/context/{domain}/_performance.md` | Reviewer agent | Reconciler-generated (ADR-195 v2). Track record. |
| The proposal itself | Reviewer agent | `action_proposals` row passed in by dispatcher. |

**Persona**: operator-authored in `/workspace/review/IDENTITY.md`. Platform provides a generic default at signup (neutral skeptical baseline); operator overwrites to embody a specific character (Simons, Buffett, Deming, etc.). The Reviewer agent reads this file as the *opening* section of its user message, so persona shapes reasoning from the first token.

**Prompt composition** (in `api/agents/reviewer_agent.py`):

```
System prompt (fixed, platform-authored):
  _SYSTEM_PROMPT
    - "You are the independent judgment seat..."
    - Substrate list (IDENTITY, principles, risk, operator_profile, performance, proposal)
    - Persona vs framework vs substrate separation
    - Autonomy delegation (ADR-217): dispatcher enforces ceiling;
      principles can narrow never widen
    - Decision categories (approve/reject/defer)
    - Reasoning expectations (upside/downside, asymmetry, edge fit)
User message (dynamic, dispatcher-assembled):
  1. ## /workspace/review/IDENTITY.md — Your persona
  2. ## Proposed action
  3. ## /workspace/review/principles.md
  4. ## Operator profile (if present)
  5. ## _risk.md (if trading)
  6. ## _performance.md (if domain has track record)
  7. ## Instruction (call return_review_decision tool once)
```

Order is load-bearing: persona first, framework second, substrate third. Changes defer/approve boundaries legibly across different personas.

**Eligibility gate** (runs before the Reviewer agent, in `review_proposal_dispatch.py`):

1. Resolve `context_domain` from `action_type`.
2. Load AUTONOMY.md via `review_policy.load_autonomy()`.
3. Resolve `autonomy_for_domain(autonomy, context_domain)` — returns per-domain policy or `default` fallback.
4. `is_eligible_for_auto_approve(autonomy_policy, action_type, estimated_cents, reversibility)` — returns `(eligible, reason)`.
5. If ineligible → observe-only path (decisions.md entry with `reviewer_identity="reviewer-layer:observed"`). Seat stays open for human occupant.
6. If eligible → AI Reviewer invocation + auto-execute on approve.

The Reviewer agent does NOT read AUTONOMY.md directly. The dispatcher enforces the ceiling; the Reviewer reasons on merits. This keeps persona reasoning unclouded by the delegation mechanics.

**Narrowing rule** (ADR-217 D4): principles.md can add defer conditions on top of the eligibility gate. The system prompt tells the persona explicitly: "Your principles can narrow delegation (add defer conditions) but never widen it. Apply the stricter."

**Seat rotation** (ADR-194 v2 + ADR-211): OCCUPANT.md + handoffs.md track who is currently filling the seat. `rotate_occupant()` is the single write path. Rotation does NOT touch IDENTITY.md, principles.md, or AUTONOMY.md — those are operator-authored content that survives seat changes.

**Model**: Claude Sonnet 4.6, forced-tool-call (`return_review_decision`), max 1024 output tokens.

**Identity string**: `REVIEWER_MODEL_IDENTITY` (currently `ai:reviewer-sonnet-v3`). Bumped on any material prompt change. Persisted on every decisions.md entry + action_proposals.reviewer_identity. Used for calibration cohort separation.

---

### 3.3 User-authored domain Agents (instance persona-bearing Agents)

**Purpose**: operator-authored specialists for domain-scoped work (e.g. "competitive-intel researcher", "weekly-report writer"). Zero-to-many per workspace. Dispatched by tasks that name them in their `## Team` section.

**Substrate reads at reasoning time** (per ADR-216 D9):

| File | Read at | Source |
|------|---------|--------|
| `/agents/{slug}/AGENT.md` | Task pipeline (`task_pipeline.py::gather_task_context`) | Operator-authored. **Single-file persona + framework convention**: domain Agents are single-domain, so persona (character) and framework (directives) share one file. This is deliberately different from Reviewer's IDENTITY/principles split. |
| `/agents/{slug}/memory/*.md` | Task pipeline | Agent-accumulated working memory. |
| `/workspace/context/{domain}/` files | Task pipeline (if `context_reads` declares the domain) | Shared accumulated context. |
| `/workspace/context/_shared/*.md` | Task pipeline | Operator-authored standing declarations (same as YARNNN/Reviewer see). |

**Persona**: operator-authored in AGENT.md (single-file convention per ADR-216 D9). Seeded from the agent's `agent_instructions` DB column at first dispatch.

**Prompt composition** (in `api/services/task_pipeline.py::build_task_execution_prompt`):

```
System prompt (assembled at dispatch):
  - Agent identity (AGENT.md)
  - Task-specific instructions (TASK.md process step)
  - Shared context (from workspace/_shared + declared domain reads)
  - Tool surface scoped by required_capabilities
User message:
  - Prior output (if task_mode implies replacement/update)
  - Current cycle instruction
  - Context bundle (gathered per context_reads declaration)
```

**Why the single-file convention**: domain Agents are single-domain by design. The operator authors the Agent as a single entity with character + directives combined. Splitting for its own sake would be spurious uniformity — there's no edit-cadence orthogonality to preserve (persona and framework change together when the operator re-authors the Agent). See ADR-216 D9 for the full rationale.

**Model**: Claude Sonnet 4.6 (headless mode, ADR-141 pipeline).

---

### 3.4 Production roles (orchestration capability bundles, NOT Agents)

**Purpose**: packaged production configurations dispatched by tasks. Six today: researcher, analyst, writer, tracker, designer, reporting.

**Substrate reads**: no persona files. Role-scoped prompt templates live in code (`api/services/orchestration.py::PRODUCTION_ROLES`). Dispatch-time capability gating via `required_capabilities` × `platform_connections`.

**Not persona-bearing** — no standing intent, no fiduciary weight. Performance-fungible. The `class` enum string is `specialist` as a data-compatibility slug per ADR-212 D1 exception.

Production roles are fully documented in `docs/architecture/agent-orchestration.md` + `orchestration.py` docstrings; this doc won't duplicate their shape.

---

## 4. Operator ↔ Reviewer symmetry

The operator (principal) and the Reviewer (agent) sit on opposite ends of the principal-agent relationship. Their substrate files mirror each other.

### 4.1 Shared substrate (both read)

Operator-authored standing declarations under `/workspace/context/_shared/`:

| File | ADR | What it declares |
|------|-----|------------------|
| MANDATE.md | ADR-207 | The Primary Action — what this workspace is running. |
| IDENTITY.md | ADR-206 | The operator's identity (role, company, timezone, summary). |
| BRAND.md | ADR-206 | Voice, tone, audience-facing presentation rules. |
| CONVENTIONS.md | ADR-206 | Filesystem + behavioral conventions. |
| AUTONOMY.md | ADR-217 | Delegation ceiling — how autonomously AI may act. |

Both YARNNN (orchestration) and Reviewer (judgment) read these. They are the operator's standing intent and bind every agent.

### 4.2 Distinct substrate (agent-specific)

**Reviewer-bound** under `/workspace/review/`:

| File | ADR | Author | Content |
|------|-----|--------|---------|
| IDENTITY.md | ADR-216 | Operator | The persona the seat embodies. |
| principles.md | ADR-194 v2 + ADR-217 | Operator | The framework the persona applies. |
| OCCUPANT.md | ADR-194 v2 Phase 2b | Rotation primitive | Who currently fills the seat. |
| handoffs.md | ADR-194 v2 Phase 2b | Rotation primitive | Rotation history (append-only). |
| decisions.md | ADR-194 v2 | Reviewer itself | Verdict trail (append-only). |
| calibration.md | ADR-211 | Back-office task | Per-occupant × verdict rolling windows. |

**YARNNN has no persona-bound substrate.** Its "working memory" under `/workspace/memory/` (AWARENESS, _playbook, style, notes) is orchestration accumulation, not persona.

**Domain Agent-bound** under `/agents/{slug}/`:

| File | ADR | Author | Content |
|------|-----|--------|---------|
| AGENT.md | ADR-216 D9 | Operator | Single-file persona + framework. |
| memory/*.md | ADR-106 | Agent itself | Per-agent working memory. |
| history/*.md | ADR-209 revision chain (absorbed) | Agent itself | Prior output versions (retained via revision chain, not via history folder). |

### 4.3 Asymmetry rule

The operator's standing declarations under `_shared/` are **read by every agent**. No agent ever writes to them directly — operator writes via YARNNN chat + `UpdateContext` primitive (targets: `mandate`, `identity`, `brand`, `autonomy`, plus legacy paths).

The Reviewer's seat substrate under `/workspace/review/` is **read by the Reviewer agent and its dispatcher only**. Rotation primitive writes to OCCUPANT + handoffs. Reviewer agent writes to decisions. Back-office task writes to calibration. IDENTITY + principles are operator-authored and revision-chained.

Domain Agent substrate under `/agents/{slug}/` is **read by task pipeline when dispatching that agent**. Operator writes AGENT.md via chat; agent writes its own memory during runs.

**The invariant that makes this work**: file placement follows authorship + scope. Operator-authored workspace-scoped = `_shared/`. Operator-authored seat-bound = `/workspace/review/IDENTITY.md` + `/workspace/review/principles.md`. Operator-authored agent-bound = `/agents/{slug}/AGENT.md`. Seat-generated = decisions + calibration + rotation files. Agent-generated = agent memory.

---

## 5. Versioning + iteration discipline

### 5.1 Prompt versioning

**Model-identity bumps**: every material prompt change increments the agent's identity string. For Reviewer, `REVIEWER_MODEL_IDENTITY` bumps v1 → v2 → v3 etc. The identity string lands on every verdict in decisions.md + action_proposals.reviewer_identity. This creates cohort separation for calibration analysis.

What triggers a bump:

- System prompt edit that changes reasoning style or decision boundaries.
- Tool definition change that alters what the agent can do.
- Model upgrade that changes capability class (e.g. Sonnet 4.5 → 4.6 → 4.7).

What doesn't:

- Typo fixes, comment edits, docstring changes.
- Downstream substrate-read changes that don't alter the prompt (though the ADR should note the substrate change).

### 5.2 CHANGELOG entries

Every prompt-touching change lands a `api/prompts/CHANGELOG.md` entry per CLAUDE.md Prompt Change Protocol. Entry format:

```markdown
## [YYYY.MM.DD.N] - Short title referencing ADR + what changed

Narrative summary. What changed, why, expected behavior delta.

### Changed
- Specific files + what changed.

### Expected behavior change
- Before vs after for typical workspaces.

### Migration
- What existing workspaces need to do (usually nothing; scaffold re-run if substrate).

### Related
- ADR references + dependent commits.
```

CHANGELOG is historical record. Never retroactively edit past entries — only add new ones that supersede.

### 5.3 ADR pattern for agent-layer changes

When an ADR touches agent composition (prompts, substrate, dispatcher wiring, primitive surface), it should:

1. **Cite this doc** (`docs/architecture/agent-composition.md`) as the canonical reference.
2. **Amend this doc in the same commit** — update the composition tables + asymmetry rules to reflect the new state. Don't leave composition documentation lagging behind decision records; future readers will hit the gap otherwise.
3. **Add CHANGELOG entry** per §5.2.
4. **Cross-reference in ADR frontmatter** with `Amends:` or `Supersedes:` against any prior ADRs whose composition claims this change invalidates.
5. **Update amended ADRs' status banners** with forward-pointing notes (ADR-194 v2 + ADR-211 status banners pointing to ADR-217 are the template).

### 5.4 Singular-implementation discipline for composition

Per CLAUDE.md: no dual paths. When ADR-217 moved autonomy from modes.md to AUTONOMY.md, the old path was deleted in the same commit window. No backwards-compat shim. Callers migrated, constants deleted, default scaffolds swapped.

This discipline is especially important at the composition layer because **dual paths at composition drift silently** — if both modes.md and AUTONOMY.md were readable, operators would edit one and expect the Reviewer to see the other, and debugging the mismatch is expensive. One file, one authoring mouth, one read path.

### 5.5 When to bump this doc itself

This doc itself needs a revision when:

- A new agent class joins the judgment layer (future Auditor, Advocate, etc.).
- Substrate placement shifts (a file moves from `/workspace/review/` to `/workspace/context/_shared/` or vice versa — this was ADR-217).
- The two-layer model itself is refined (unlikely but possible).
- A new versioning discipline is adopted (e.g. if we start tracking production-role identity strings too).

Minor edits (new ADR cross-references, CHANGELOG pointers, clarifying examples) don't need revision bumps — the doc is canon, not a versioned artifact.

---

## 6. Appendix — ADR reference map

Decisions that shaped the current agent composition, in order:

- **ADR-106** — Agent workspace architecture. Virtual filesystem over Postgres; agents interact via path-based operations.
- **ADR-117** — Feedback substrate. Edit history → style.md distillation.
- **ADR-141** — Unified execution architecture. Task pipeline, mechanical scheduling + LLM generation split.
- **ADR-159** — Filesystem-as-memory. Compact index + on-demand reads replace working-memory dumps.
- **ADR-168** — Primitives matrix. Two-axis canonical reference for all primitives.
- **ADR-186** — YARNNN prompt profiles. Workspace vs entity profile-aware assembly.
- **ADR-194 v2** — Reviewer Layer + operator impersonation. Reviewer seat as filesystem substrate.
- **ADR-205** — Workspace primitive collapse. YARNNN as sole persistent identity at signup.
- **ADR-206** — Operation-first scaffolding. `_shared/` relocation; intent/deliverables/operation three-layer view.
- **ADR-207** — Primary Action + MANDATE + capabilities. Mandate gate; capability-declarative tasks.
- **ADR-209** — Authored Substrate. Every file write revision-chained with authorship.
- **ADR-211** — Reviewer Phase 4 substrate. OCCUPANT + handoffs + modes (now deleted by ADR-217) + calibration.
- **ADR-212** — LAYER-MAPPING correction. Sharp Agent/Orchestration taxonomy.
- **ADR-216** — YARNNN reclassification + persona wiring. Orchestration vs judgment separation; persona read at reasoning time.
- **ADR-217** — Workspace autonomy substrate. Single authoring mouth for delegation; modes.md → AUTONOMY.md.

This doc supersedes the scattered "how does agent X compose" language that accumulated across the above ADRs. Those ADRs remain authoritative as decision records; this doc is the running architectural reference.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-24 | v1 — initial. Consolidates composition knowledge across ADRs 106/117/141/159/168/186/194v2/205–217. Documents two-layer model, per-agent composition for YARNNN + Reviewer + domain Agents, operator-Reviewer symmetry, and versioning discipline. Written alongside ADR-217 Commit 4. |
