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
| `/workspace/context/_shared/PRECEDENT.md` | Via tool reads (in compact index key files per commit `fd4917a`) | Operator-authored — durable interpretations / boundary-case resolutions |
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
| `/workspace/context/_shared/PRECEDENT.md` | Reviewer agent (v4 prompt, `reviewer_agent.py`) | Operator-authored (commit `fd4917a`). Durable interpretations / boundary-case rules. Overrides conflicting clauses in `principles.md` — precedent always wins when the two disagree. |
| `/workspace/context/_shared/AUTONOMY.md` | Dispatcher (`review_proposal_dispatch.py` + `review_policy.py::load_autonomy`) | Operator-authored (ADR-217). Declares the delegation ceiling — NOT read by the Reviewer agent itself; enforced by the dispatcher before invocation. |
| `/workspace/context/{domain}/_operator_profile.md` | Reviewer agent | Operator-authored. Strategy + style context. |
| `/workspace/context/{domain}/_risk.md` | Reviewer agent | Operator-authored. Hard floors. |
| `/workspace/context/{domain}/_money_truth.md` | Reviewer agent | Reconciler-generated (ADR-195 v2). Track record. |
| The proposal itself | Reviewer agent | `action_proposals` row passed in by dispatcher. |

**Persona**: operator-authored in `/workspace/review/IDENTITY.md`. Platform provides a generic default at signup (neutral skeptical baseline); operator overwrites to embody a specific character (Simons, Buffett, Deming, etc.). The Reviewer agent reads this file as the *opening* section of its user message, so persona shapes reasoning from the first token.

**Prompt composition** (in `api/agents/reviewer_agent.py`):

```
System prompt (fixed, platform-authored, v4):
  _SYSTEM_PROMPT
    - "You are the independent judgment seat..."
    - Substrate list (IDENTITY, principles, PRECEDENT, risk, operator_profile, performance, proposal)
    - Persona vs framework vs substrate separation
    - Autonomy delegation (ADR-217): dispatcher enforces ceiling;
      framework (principles + precedent) can narrow never widen
    - Precedent hierarchy: precedent wins over conflicting principles
    - Decision categories (approve/reject/defer)
    - Reasoning expectations (upside/downside, asymmetry, edge fit)
User message (dynamic, dispatcher-assembled):
  1. ## /workspace/review/IDENTITY.md — Your persona
  2. ## Proposed action
  3. ## /workspace/review/principles.md
  4. ## /workspace/context/_shared/PRECEDENT.md — Operator-declared durable interpretations
  5. ## Operator profile (if present)
  6. ## _risk.md (if trading)
  7. ## _money_truth.md (if domain has track record)
  8. ## Instruction (call return_review_decision tool once)
```

Order is load-bearing: persona → framework (principles + precedent) → substrate. PRECEDENT lands between principles and substrate so operator interpretations filter substrate reasoning. Changes defer/approve boundaries legibly across different personas + across workspaces with different precedent accumulation.

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

#### 3.2.1 Partition discipline: what belongs in `principles.md` vs. persona-frame

> **This subsection is the singular enforcement home for the principles ↔ persona-frame partition.** When you are about to add content to `/workspace/review/principles.md` (in a bundle template, in a per-workspace seed, or in a doc that prescribes principles content), this is the test. When you are about to add content to a `_compute_*` section of `api/agents/reviewer_agent.py`'s persona-frame, this is the test. Other canon files (`reviewer-substrate.md`, ADR-194 v2, ADR-217, ADR-293, ADR-295, ADR-303) defer to this clause on the partition question — they describe the seat, the autonomy gating, the self-amendment capability, the posture taxonomy, but the *content boundary between principles.md and the persona-frame* is governed here.

**The one-line statement** (already canonized at §4.2 line 227 and §3.2 substrate table):
> **`principles.md` is the rule-set the persona applies.** Persona is *how to reason*; mandate is *why we exist*; autonomy is *how far decisions bind*; principles is *what the rules of judgment are*.

**The four-field rule shape.** Every rule declared in `principles.md` must have:

1. **Name** — a stable identifier for the rule (e.g. `voice-fingerprint-match`, `anti-slop`, `text-continuity`, `entity-continuity`, `cadence-on-pace`).
2. **Substrate it reads against** — the file path or signal the rule evaluates (`_voice.md`, `entities/{slug}.md::What's been established`, `_preferences.yaml::cadence` × `_signal.md::last-ship-date`, etc.). A rule with no substrate-anchor is floating. Note (post-2026-05-29 collapse): "floating" no longer means "move it to the persona-frame" — the frame holds only principal-shift + action-grammar. A floating clause is either a model-runtime-interface concern (→ minimal frame) or substrate pedagogy (→ `_workspace_guide.md`); it is not reasoning-posture-for-the-frame, because that category was retired.
3. **Pass condition** — what state of that substrate means the rule passes.
4. **Verdict on fail** — `approve` (the rule isn't load-bearing for this verdict shape) / `defer` (with directive shape — what the operator-facing directive should contain) / `reject` (unconditional) / `propose` (Reviewer must emit an action_proposal).

A `principles.md` rule that does not fit this shape is mis-placed content — it belongs elsewhere per the boundary below.

**What belongs in `principles.md` vs. the minimal frame — bright-line content boundary (INVERTED 2026-05-29 by the persona-frame collapse, ADR-306).**

> **Prior framing (pre-2026-05-29), now superseded**: an earlier version of this boundary placed self-amendment discipline, anti-patterns, the fiduciary principle, the posture taxonomy, cadence-trifecta, wake-context discipline, write-authority, and voice in the persona-frame `_compute_*` sections, treating them all as "reasoning posture" that did NOT belong in principles.md. The persona-frame collapse (`2026-05-29-persona-frame-collapse-ablation.md`) found that most of those are either **rules of judgment** (they fit the four-field shape → they ARE principles.md content) or **substrate pedagogy** (→ `_workspace_guide.md`, ADR-281) or **code-enforced** (→ no prose needed). The system-authored frame collapsed to the MINIMAL two-thing shape below. The boundary is re-stated accordingly.

The system-authored **minimal frame** (`api/agents/reviewer_agent.py::_compute_minimal_frame`, ~3.5K chars) carries ONLY two things — neither of which is the operator's to declare:

| In the minimal frame (system-authored, irreducible) | Why it cannot live in substrate |
|---|---|
| **Principal-shift** — "you are installed judgment acting on behalf, not an assistant awaiting instruction" | Corrects the *model's trained assistant prior*. A model reading IDENTITY.md through its assistant prior becomes "a helpful assistant playing the persona." This is a property of installing judgment over an assistant-trained model — not an operator declaration. |
| **Action-grammar** — tool-call-IS-action + anti-confabulation + read-fresh-not-cached + close-cycle-with-verdict-or-standing-intent | The agent↔runtime interface contract (how tool calls relate to reality), not data the agent reasons over. The cc8e0ab fix, proven load-bearing. |

**Everything else is `principles.md` (rules of judgment) or `_workspace_guide.md` (substrate pedagogy) or code (gates):**

| Concern | Canonical home (post-collapse) | Why |
|---|---|---|
| When the Reviewer may amend operator-canon (the four evidence patterns) | **`principles.md`** | A rule of judgment: name (calibration-drift / near-miss / substrate-gap / cadence), substrate-anchor (ground-truth file), pass-condition (threshold met), verdict (amend / defer). Numeric thresholds in `_principles.yaml` (ADR-254). |
| Anti-patterns — when NOT to amend operator-canon | **`principles.md`** | Rules of judgment (when NOT to act). The autonomy-safety discipline lives here, rendered every wake under "## principles.md". |
| Fiduciary principle + counterweight | **`principles.md`** | The active-vs-passive judgment rule. |
| Independence (judgment vs producer-agreement) + reason-before-autonomy-filter + precedent-hierarchy | **`principles.md`** (posture) + **code** (the dispatcher applies AUTONOMY post-verdict regardless of prose) | Independence is a rule of judgment; the AUTONOMY-application mechanism is code-enforced. |
| When to Clarify vs decide | **`principles.md`** | A rule of judgment. (The anti-enumerate-options sliver — fighting the assistant prior — is the one bit in the minimal frame.) |
| Posture taxonomy (P1–P5) + standing-intent every-cycle contract | **code** (dispatcher synthesizes P4/P5 fallback) + **minimal frame** (the model-facing rule compresses to "close every cycle with a verdict or a standing_intent write") | The cycle-exit shape is a Reviewer↔dispatcher runtime concern; the dispatcher half is code, the model half is one line in the frame's action-grammar. |
| Cadence-trifecta / wake-context / pulse-files / preferences semantics | **`_workspace_guide.md`** (ADR-281 substrate pedagogy) + **the envelope's labeled headers** | The model reads `_pace.yaml`/`_autonomy.yaml`/`## Wake context` from the envelope under their own headers; the workspace guide teaches what each is for. The frame does not re-narrate them. |
| Write authority + locks | **code** (`DEFAULT_REVIEWER_WRITE_LOCKS` + `_is_path_locked_for_reviewer`) | Enforced by the lock-set; the tool result reports a lock. No prose enumeration needed (one sentence in the frame notes locks exist). |
| Voice and narration | **minimal frame** (action-grammar) | First-person + narrate-your-direction is part of the interface contract. |
| Calibration loop | **`principles.md`** (the loop's rule) + ADR-195 reconciler (the mechanism) | |
| Workspace-lifecycle phase gates | **`AUTONOMY.md`** + per-program tuning | Operator-declared lifecycle policy. |

**Conflict-resolution rule.** When two reads disagree on a verdict:

1. `PRECEDENT.md` > `principles.md` — operator-declared durable interpretations override the framework.
2. **`principles.md` is authoritative for rules of judgment** (including self-amendment evidence-patterns + anti-patterns + independence). The minimal frame does NOT carry these — it carries only principal-shift + action-grammar — so there is no frame-vs-principles conflict on rules of judgment to resolve (the prior framing's "persona-frame > principles for reasoning-posture" rule is retired; the frame no longer holds reasoning-posture content).
3. `AUTONOMY.md` ceiling > `principles.md` *for delegation widening*. Principles can narrow delegation (add defer conditions) but never widen (ADR-217 D4). The ceiling is code-enforced.

**Bundle-template + per-workspace audit checklist.** Before editing a `docs/programs/{slug}/reference-workspace/review/principles.md` or forking it:

- Every section declares either (a) a rule with the four-field shape (now INCLUDING the self-amendment evidence-patterns + anti-patterns + independence + fiduciary rules), (b) the conflict-resolution rule, or (c) a brief workspace-lifecycle phase pointer. If it doesn't fit, it's mis-placed.
- Numeric thresholds live in `_principles.yaml` (ADR-254). Prose category declarations may live in principles.md; the numbers per program live in yaml.
- No section describes the **principal-shift** or the **action-grammar** — those are the minimal frame's two irreducible things. (This is the inverse of the prior checklist item.)

**Diagnostic test** (use this when uncertain): *Is this content (a) correcting the model's assistant prior, or (b) the agent↔runtime interface contract?* If yes → minimal frame. Otherwise: *does it name a rule with a substrate-anchor + pass-condition + verdict?* If yes → `principles.md`. *Does it teach what a substrate file is for?* → `_workspace_guide.md`. *Is it enforced by a gate?* → code, no prose. The persona-frame is NOT a home for anything that fits the latter three — that is the anti-rebloat constraint (FOUNDATIONS Derived Principle, added by the collapse).

---

#### 3.2.2 The composite prompt-governing substrate + composed-coherence discipline

> **This subsection names a category §3.2.1 does not cover.** §3.2.1 governs *partition* — the boundary between two members of the set so they don't overlap. This subsection governs *composed coherence* — whether the **assembled whole** tells one consistent story about what the Reviewer is and where its agency ends, **consistent with FOUNDATIONS**. Partition is "does each piece stay in its lane?"; composed coherence is "does the lane-respecting whole still hold together against the axioms?" A document set can pass §3.2.1 and fail §3.2.2: every piece in its lane, yet the assembled frame contradicts canon.

**The category.** The Reviewer's runtime behavior is governed not by one document but by a **dispersed set** — the operator's "CLAUDE.md, split intentionally across substrate." It is one auditable category with one owned property (coherence). Its members:

| Member | Authored by | Home | Class |
|---|---|---|---|
| `MANDATE.md` | operator | `context/_shared/` | operator-canon (why we exist) |
| `AUTONOMY.md` + `_autonomy.yaml` | operator | `context/_shared/` | operator-canon (how far decisions bind) |
| `_pace.yaml` | operator | `context/_shared/` | operator-canon (Trigger budget) |
| `_preferences.yaml` | operator | `context/_shared/` | operator-canon (deliverable cadence) |
| `IDENTITY.md` | operator (overwritable) | `review/` | persona (how to reason — character) |
| `principles.md` (+ `_principles.yaml`) | operator (overwritable) | `review/` | framework (what rules of judgment — §3.2.1) |
| `PRECEDENT.md` | operator | `context/_shared/` | operator-canon (durable interpretations) |
| program-specific (e.g. `_voice.md`, `_risk.md`, `_operator_profile.md`) | operator | program domain dirs | operator-canon (domain rules) |
| minimal frame `_compute_minimal_frame` | **system** (kernel) | `api/agents/reviewer_agent.py` | the two irreducible things — principal-shift (corrects the model's assistant prior) + action-grammar (agent↔runtime interface contract). NOT reasoning posture (that's principles.md post-2026-05-29 collapse). |

The last row is load-bearing and easy to forget: the **system-authored minimal frame is a member of the composite set**, assembled into the same effective prompt as the operator-authored documents. A coherence audit that reads only the operator's files misses the frame. Post-collapse the frame carries only principal-shift + action-grammar (~3.5K chars, down from ~36K); the rules of judgment it used to duplicate now live solely in `principles.md` (§3.2.1 inverted boundary).

**The composed-coherence property (what someone must own).** The assembled prompt must not contradict FOUNDATIONS. The two clauses most prone to violation, because they describe *what the Reviewer is and how it acts*:

- **Axiom 2** — the Reviewer is an **Agent** (judgment-bearing); execution machinery is **Orchestration**. The composite must not tell the Reviewer it *is* the executor.
- **Axiom 1 §4** — the Reviewer **directs**; the runtime **executes**; the **substrate revision is the channel** between them; the next wake reads what this wake wrote. The composite must not tell the Reviewer it performs-and-inline-observes an execution step the architecture routes elsewhere.

**Diagnostic test for composed coherence** (use when editing any member of the set): *Read the assembled frame as one document. Does it tell a single consistent story about (a) what the Reviewer is, (b) how it acts, (c) where its agency ends — and is that story consistent with Axiom 1 §4 + Axiom 2?* If two members imply different action-grammars (one says "you direct," another says "you execute / your hands / write directly"), the composite is incoherent even if each member individually respects §3.2.1's partition. The model will resolve the contradiction toward the more vivid/repeated grammar — usually the wrong one.

**Why this clause exists** (substrate-receipt): the 2026-05-29 finding [`docs/evaluations/2026-05-29-reviewer-action-grammar-framing-gap.md`](../evaluations/2026-05-29-reviewer-action-grammar-framing-gap.md) traced a Reviewer confabulation ("I attempted the write, it was gated, it queued" — with zero substrate-receipt) to exactly this failure: `_compute_voice_and_narration` already said "narrate your **direction**" (coherent), while `_compute_identity_and_purpose` said "the System Agent is your **hands**… Decide. Act." and `_compute_write_authority` said "write **directly**" (executor self-model). Each section passed §3.2.1; the **assembled** frame held two contradictory action-grammars, and the model role-played the executor one against the architecture. The fix reconciled all sections to the directs-not-executes grammar consistent with Axiom 1 §4 + Axiom 2.

**Maintenance rule.** Any edit to a member of the composite set — operator-canon *or* the system-authored persona-frame — must be checked against the composed-coherence diagnostic, not only against §3.2.1's partition diagnostic. The two are complementary gates; passing one does not imply the other. Future ADRs that reshape any composite member **must run the composed-coherence test in the same commit** — the discipline is enforced here, not re-derived.

**Operational enforcement (layered — structural + behavioral).** The composed-coherence diagnostic is backed by two gates so it cannot silently drift back to prose-only diligence (which the 2026-05-29 finding proved insufficient — the confabulation survived into a *validated* session):

1. **Structural gate (Hat-A, every commit)** — `api/test_reviewer_formalization.py::test_persona_frame_action_grammar_coherence` scans the assembled persona frame (`resolve_persona_frame_sections(_PERSONA_FRAME_SECTIONS)`) for the executor-self-model contradiction class. **Paired assertion**: banned executor grammar ("your hands", "write directly", "the doing") absent AND the directs-not-executes grammar present (so a *removed* fix fails too, not just an *added* regression). This catches structural reappearance of the contradiction in source. It does NOT — and cannot — judge prose coherence in general; it pins one named, axiom-anchored contradiction class.
2. **Behavioral gate (Hat-B, periodic)** — the eval suite's **confabulation cross-check** (`docs/evaluations/EVAL-SUITE-DISCIPLINE.md` §6.2): for every action the Reviewer *narrates having taken*, verify a substrate-receipt; a narrated action with no receipt is a confabulation finding. This catches behavioral reappearance even if the structural grammar is clean. Only a live wake + transcript-vs-receipt read can do this; it is not expressible as a code gate.

The two are complementary: structural is cheap and runs on every commit but only catches known-grammar regressions; behavioral is expensive and periodic but catches novel confabulation the grammar scan would miss. Neither subsumes the other.

---

### 3.3 User-authored domain Agents (instance persona-bearing Agents)

**Purpose**: operator-authored specialists for domain-scoped work (e.g. "competitive-intel researcher", "weekly-report writer"). Zero-to-many per workspace. Dispatched by tasks that name them in their `## Team` section.

**Substrate reads at reasoning time** (per ADR-216 D9):

| File | Read at | Source |
|------|---------|--------|
| `/agents/{slug}/AGENT.md` | Task pipeline (`task_pipeline.py::gather_task_context`) | Operator-authored. **Single-file persona + framework convention**: domain Agents are single-domain, so persona (character) and framework (directives) share one file. This is deliberately different from Reviewer's IDENTITY/principles split. |
| `/agents/{slug}/memory/*.md` | Task pipeline | Agent-accumulated working memory. |
| `/workspace/context/{domain}/` files | Task pipeline (if `context_reads` declares the domain) | Shared accumulated context. |
| `/workspace/context/_shared/*.md` | Task pipeline (compact-index + on-demand ReadFile for MANDATE/AUTONOMY/IDENTITY/BRAND/CONVENTIONS) | Operator-authored standing declarations (same as YARNNN/Reviewer see). |
| `/workspace/context/_shared/PRECEDENT.md` | Task pipeline (`gather_task_context` §4b — injected as "Operator Precedent" section when non-empty) | Operator-authored durable interpretations. Forces production roles to honor operator-declared boundary-case rules across task runs. |

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
| PRECEDENT.md | 2026-04-24 shared-governance hardening | Durable interpretations and boundary-case rules that should compound across future decisions. |

Both YARNNN (orchestration) and Reviewer (judgment) read these. They are the operator's standing intent and bind every agent.

### 4.2 Distinct substrate (agent-specific)

**Reviewer-bound** under `/workspace/review/`:

| File | ADR | Author | Content |
|------|-----|--------|---------|
| IDENTITY.md | ADR-216 | Operator | The persona the seat embodies. |
| principles.md | ADR-194 v2 + ADR-217 | Operator | The framework the persona applies — the rule-set, not the reasoning posture. See §3.2.1 for the partition-discipline clause (singular enforcement home). |
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

The operator's standing declarations under `_shared/` are **read by every agent**. No agent ever writes to them directly — operator writes via YARNNN chat + `UpdateContext` primitive (targets: `mandate`, `identity`, `brand`, `autonomy`, `precedent`, plus legacy paths).

The Reviewer's seat substrate under `/workspace/review/` is **read by the Reviewer agent and its dispatcher only**. Rotation primitive writes to OCCUPANT + handoffs. Reviewer agent writes to decisions. Back-office task writes to calibration. IDENTITY + principles are operator-authored and revision-chained.

Domain Agent substrate under `/agents/{slug}/` is **read by task pipeline when dispatching that agent**. Operator writes AGENT.md via chat; agent writes its own memory during runs.

**The invariant that makes this work**: file placement follows authorship + scope. Operator-authored workspace-scoped = `_shared/`. Operator-authored seat-bound = `/workspace/review/IDENTITY.md` + `/workspace/review/principles.md`. Operator-authored agent-bound = `/agents/{slug}/AGENT.md`. Seat-generated = decisions + calibration + rotation files. Agent-generated = agent memory.

**Content boundary within the seat-bound files** (the partition that companion §3.2.1 enforces): `IDENTITY.md` = persona (how the seat reasons); `principles.md` = rule-set the persona applies (the framework). Reasoning-posture content (self-amendment discipline, anti-patterns, fiduciary principle, posture taxonomy, standing-intent contract, cadence-trifecta, wake-context discipline, write authority, voice/narration) lives in `api/agents/reviewer_agent.py` persona-frame `_compute_*` sections — single home, code-local. The seat-bound prose files describe *who* and *what rules*; the persona-frame describes *how to reason*. See §3.2.1 for the four-field rule shape and the diagnostic test.

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
- **Shared governance hardening** (commit `fd4917a`, 2026-04-24) — `PRECEDENT.md` under `/workspace/context/_shared/` as operator-authored durable interpretation substrate. Read by YARNNN (compact index), Reviewer (v4 prompt), task pipeline (`gather_task_context`).
- **`persona-reflection.md`** (canon doc, 2026-04-24) — Reviewer as living accumulator. Precedent and reflection together close the "framework evolves with reality" gap: precedent is operator-sided; reflection (future ADR-218) is persona-sided. Both accumulate inside MANDATE + AUTONOMY boundaries.

This doc supersedes the scattered "how does agent X compose" language that accumulated across the above ADRs. Those ADRs remain authoritative as decision records; this doc is the running architectural reference.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-24 | v1 — initial. Consolidates composition knowledge across ADRs 106/117/141/159/168/186/194v2/205–217. Documents two-layer model, per-agent composition for YARNNN + Reviewer + domain Agents, operator-Reviewer symmetry, and versioning discipline. Written alongside ADR-217 Commit 4. |
