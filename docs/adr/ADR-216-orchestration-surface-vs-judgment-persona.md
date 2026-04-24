# ADR-216: Orchestration Surface vs Judgment Persona — YARNNN Reclassification, Reviewer Persona Wiring

> **Status**: Proposed — staged implementation across five commits (this ADR is Commit 1).
> **Date**: 2026-04-24
> **Authors**: KVK, Claude
> **Dimensional classification**: **Identity** (Axiom 2) primary, **Channel** (Axiom 6) secondary.
> **Supersedes**: The ADR-212 D1 classification of YARNNN as a "systemic meta-cognitive Agent." YARNNN is reclassified to **orchestration surface**, not a persona-bearing Agent.
> **Amends**: ADR-194 v2 (Reviewer seat now explicitly persona-bearing, read at reasoning time), ADR-205 (signup-scaffold semantics unchanged but reframed), ADR-212 (flip mapping preserved for Reviewer + domain Agents; YARNNN moves out of the Agent category), ADR-214 (Agents roster retains YARNNN as a visible surface card but classified as orchestration-surface, not persona-bearing).

---

## Context

ADR-212 (2026-04-23) landed the sharp layer flip: **Agents** are judgment-bearing entities holding standing intent; **Orchestration** is production machinery. Under that flip, three entities were classified as Agents: YARNNN (systemic meta-cognitive), Reviewer (systemic judgment seat), and user-authored domain Agents (instance).

A subsequent stress-test of that classification surfaced two inconsistencies:

**Inconsistency 1 — YARNNN's classification is category-mixed.** YARNNN-the-Agent does mechanical orchestration work (compose system prompts, route surfaces to profiles, dispatch primitives, write compact indices, write session summaries, handle mandate elicitation) *and* judgment work (decide what Agent/task to create, read principles, evaluate proposals for the chat surface). By classifying YARNNN as an Agent peer to Reviewer, the two-layer model collapsed: judgment decisions got tangled with mechanical plumbing, and mechanical decisions got persona flavor they don't need. The chat surface being the single entry point made this feel inevitable — an interlocutor needs coherence, and coherence was read as persona — but the two concerns (coherence vs. persona) are distinct.

**Inconsistency 2 — Persona content is scaffolded but not read at reasoning time.**
An audit of three files (`api/agents/reviewer_agent.py`, `api/services/review_proposal_dispatch.py`, `api/agents/yarnnn_prompts/base.py`) confirmed that `/workspace/review/IDENTITY.md` — the Reviewer's declared persona content, scaffolded at signup per ADR-211 — is **not read** by the AI Reviewer's reasoning path. `review_proposal()` takes `principles_md`, `performance_md`, `risk_md`, `operator_profile_md` but no `identity_md`. `review_proposal_dispatch.py` assembles the same four files. Authoring a persona (e.g. Jim-Simons-character) into IDENTITY.md today changes nothing about how the Reviewer reasons. The persona-embodiment mechanism the architecture implies does not exist in code.

The combination of the two inconsistencies means the platform's substantive proposition — *"the Reviewer is persona-bearing and the persona is operator-authored"* — is currently an aspiration, not an implementation. The mechanism needed is a reclassification (YARNNN out of the Agent category, Reviewer remains the sole systemic Agent) paired with a wiring fix (IDENTITY.md read at reasoning time).

---

## Decision

### D1 — Two-layer taxonomy is canonical

Every concept in YARNNN occupies exactly one of two layers:

- **Orchestration layer**: mechanical, opinion-less, substrate-writing infrastructure. Schedules tasks, routes capabilities, composes prompts, dispatches runs, writes substrate, fetches platform data, handles compose/delivery. Sits in Mechanism (Axiom 5) at the deterministic end and Channel (Axiom 6) where user-facing. Not persona-bearing. Performance-fungible (swap one orchestrator for another and the work executes the same way).

- **Judgment layer**: persona-bearing Agents holding standing intent on behalf of the operator. Reason from principles, render judgments, self-improve along a persona-specific calibration axis. Sits in Identity (Axiom 2). **Not** performance-fungible — swap a Simons-persona for a Buffett-persona and outcomes diverge. That divergence is the point.

No hybrid classification. No "mostly orchestration but also judgment" category. An entity is in one layer; if it does work in both, it is split into two entities.

### D2 — YARNNN is reclassified as orchestration surface

YARNNN is the **conversational surface of the orchestrator**, not a persona-bearing Agent. Specifically:

- YARNNN holds **fixed-voice interlocutor style** (for chat coherence), not **persona** (for judgment bias). Persona implies operator-authorable character applied to judgment decisions. YARNNN has neither — its voice is platform-authored, it does not hold judgment, it routes judgment questions to the judgment layer.
- The Python `agents` table row with `role='thinking_partner'` is **retained** as a pragmatic substrate for chat-surface state and continuity. The row's existence does not make YARNNN a persona-bearing Agent any more than a PostgreSQL `sessions` table makes a session an Agent. The row is implementation; the classification is architectural.
- YARNNN surfaces in the `/agents` roster as a visible card (per ADR-214) but is explicitly labeled as **orchestration surface**, not as a persona-bearing Agent peer to Reviewer and domain Agents. Frontend visual treatment may remain identical; the labeling and the prompt content must make the classification legible.
- The `yarnnn_prompts/base.py` `BASE_PROMPT` — "You are YARNNN — the user's super-agent" — stays fixed-voice at the platform level. There is **no** workspace-authored YARNNN IDENTITY file. This is correct-by-design, not a gap.

### D3 — Reviewer is the sole systemic Agent

Under the refined taxonomy, the systemic Agent roster has exactly one member at signup:

- **Reviewer** — sole systemic Agent. Persona-bearing. `/workspace/review/IDENTITY.md` declares the persona; `/workspace/review/principles.md` declares the evaluation framework the persona applies; `modes.md` declares per-domain autonomy posture; `_performance.md`, `_risk.md`, and `_operator_profile.md` provide the substrate the persona reasons against.

User-authored domain Agents remain instance Agents (zero-to-many per workspace), persona-bearing via `/agents/{slug}/AGENT.md` + `/agents/{slug}/IDENTITY.md` per ADR-106 and ADR-117. Their persona-read path is audited in Commit 4.

Future systemic Agents (Auditor, Advocate, Custodian per ADR-212 D1 forward-looking note) will be added as additional persona-bearing members when their role emerges. YARNNN is **not** among them — it sits in the orchestration layer.

### D4 — Persona is a first-class substrate concept; IDENTITY.md is read at reasoning time

For every persona-bearing Agent, the operator-authored `IDENTITY.md` file at that Agent's canonical path is read at reasoning time and injected into the Agent's system/user prompt as the persona declaration. Specifically:

- **Reviewer**: `/workspace/review/IDENTITY.md` is read by `review_proposal_dispatch.py` and passed to `review_proposal(identity_md=...)`. The Reviewer's user message opens with the persona section, then the principles framework, then the substrate the persona reasons against. Commit 2 implements this.
- **User-authored domain Agents**: `/agents/{slug}/IDENTITY.md` is read at dispatch time by the task pipeline and injected into the agent's system prompt. Commit 4 verifies or wires this.
- **YARNNN**: not applicable. YARNNN is orchestration surface; there is no workspace-authored YARNNN IDENTITY file. The `BASE_PROMPT` in `yarnnn_prompts/base.py` is platform-authored fixed-voice and that is the correct behavior.

Default IDENTITY.md content (scaffolded at signup) is generic ("I am the independent judgment seat"). Operators overwrite the file to declare a specific persona (Simons, Buffett, Cialdini, Deming, or operator-authored original). The overwrite is the persona-embodiment primitive.

### D5 — "Persona" becomes canonical vocabulary

GLOSSARY.md gains a first-class **Persona** entry:

> **Persona** — operator-authored judgment character for a persona-bearing Agent. Embodied in `IDENTITY.md` at the Agent's canonical path. Read at reasoning time. Distinct from *principles* (the framework the persona applies) and *role* (the seat's structural function). Swappable per workspace: one workspace's Reviewer can embody Simons, another's can embody Buffett, with identical seat structure and distinct output distributions.

CLAUDE.md's Key terminology block is rewritten under this vocabulary. ADR-212's term "judgment-bearing" is preserved but paired with "persona-bearing" in the canonical definition — every persona-bearing entity is judgment-bearing, but persona is the operator-authorable aspect.

### D6 — Staged five-commit implementation

This ADR is Commit 1 — ratification only, docs only. The remaining commits are:

- **Commit 2**: Reviewer persona wiring. `review_proposal_dispatch.py` reads `/workspace/review/IDENTITY.md`; `reviewer_agent.py::review_proposal()` accepts `identity_md` parameter; `_build_user_message()` injects the persona section at the top. Bump `REVIEWER_MODEL_IDENTITY` from `v1` to `v2`. Update `api/prompts/CHANGELOG.md`. ~30 lines across 3 files.
- **Commit 3**: Vocabulary unification. CLAUDE.md Key terminology block rewrite. GLOSSARY.md Persona entry. Fix the stale `tp_prompts/` → `yarnnn_prompts/` references that never propagated from ADR-189. `DEFAULT_REVIEW_IDENTITY_MD` gets a visible operator-instruction header noting that the file is overwritten to embody a persona. `AGENT_TEMPLATES` entries get clarified docstrings distinguishing orchestration-surface (YARNNN) from persona-bearing Agents (Reviewer + future systemic Agents). No code rename — vocabulary only.
- **Commit 4**: Persona reads for user-authored domain Agents. Audit the task pipeline + agent execution paths. If `/agents/{slug}/IDENTITY.md` is already read, document it. If not, wire it with the same pattern used in Commit 2 for Reviewer.
- **Commit 5**: `scaffold_trader.py` updates. Upsert `/workspace/review/IDENTITY.md` with Simons-persona content. Activate `modes.md` trading block. Move IDENTITY + BRAND writes to DB upserts at `/workspace/context/_shared/` paths. Replace `trading-bot` agent_slug with production-role + `required_capabilities` per ADR-207. Run the scaffold. Verify a first E2E cycle produces Simons-character Reviewer reasoning in `decisions.md`.

Each commit lands independently green. No partial refactor lives in `main` at any point.

### D7 — Non-goals

This ADR does not:

- Rewrite the task pipeline, primitive matrix, or substrate model.
- Change the Reviewer's rotation primitive, OCCUPANT.md, or handoffs.md semantics (ADR-194 v2 Phase 2b + ADR-211 remain authoritative).
- Rename Python modules. Clarity comes via docstrings + vocabulary; renames are deferred to a future commit if needed.
- Change the `/agents` cockpit surface structure (ADR-214 four-tab nav stands). YARNNN continues to render as a card; its classification change is in the content, not the chrome.
- Deprecate `thinking_partner` as a Python class string. The enum slug stays as a stable data-compatibility key (same pattern as `specialist` / `platform-bot` in ADR-212 D1 enum-slug exceptions).

### D8 — Historical ADR preservation

ADR-212's "YARNNN is a systemic meta-cognitive Agent" classification is preserved verbatim in ADR-212. ADR-216 supersedes that specific classification but does not rewrite ADR-212's historical text. Future readers of ADR-212 see the "Supersedes" banner in ADR-216 and the amendment note added to ADR-212's status line.

### D9 — Domain Agent persona convention: single-file AGENT.md

Audit of `api/services/task_pipeline.py` (Commit 4, 2026-04-24) confirmed that user-authored domain Agents use a single-file convention for persona + directives: `/agents/{slug}/AGENT.md`. The file is seeded at agent creation from the `agent_instructions` DB column (operator-authored via YARNNN chat), read at dispatch time at three execution-path sites (`task_pipeline.py:1930`, `:2606`, `:3931`), and passed into the agent pipeline as `agent_instructions`.

This is **deliberately different from the Reviewer's split**. The Reviewer has two files — `/workspace/review/IDENTITY.md` (persona) + `/workspace/review/principles.md` (framework) — because the Reviewer evaluates proposals across multiple domains; persona (*how* it reasons) and framework (*what* it checks) have distinct edit cadences and orthogonal authoring workflows.

Domain Agents are single-domain by design. Their AGENT.md conflates persona and framework into one authored artifact, because for a domain-scoped Agent the two concepts don't have edit-cadence orthogonality — the operator authors the Agent as a single entity with character + directives combined. Splitting AGENT.md into IDENTITY.md + FRAMEWORK.md for domain Agents would be spurious uniformity.

**The invariant that survives both conventions**: every persona-bearing Agent has its persona content read at reasoning time from an operator-authored file at its canonical path. For Reviewer that file is IDENTITY.md; for domain Agents that file is AGENT.md. The persona-read-at-reasoning-time mechanism holds uniformly.

Commit 4 also adds a short clarifying comment to `task_pipeline.py` above the first AGENT.md read site noting this convention and cross-referencing ADR-216 D9.

---

## Dimensional test

Under FOUNDATIONS v6.0 six-axis model, the reclassification resolves cleanly:

| Entity | Primary axis | Secondary axis | Persona? |
|---|---|---|---|
| **Orchestrator** (task pipeline, scheduler, compose engine, primitive dispatch) | Mechanism (Axiom 5, deterministic end) | Substrate (Axiom 1) | No |
| **YARNNN chat surface** | Channel (Axiom 6) | Mechanism (Axiom 5) | No — fixed-voice interlocutor, platform-authored |
| **Reviewer** | Identity (Axiom 2) | Purpose (Axiom 3 — gate the irreversible) + Trigger (Axiom 4 — reactive to ProposeAction) | **Yes** — workspace-authored in `/workspace/review/IDENTITY.md` |
| **User-authored domain Agents** | Identity (Axiom 2) | Purpose (Axiom 3 — operator-declared role) | **Yes** — workspace-authored in `/agents/{slug}/IDENTITY.md` |
| **Production roles** (researcher, analyst, writer, tracker, designer, reporting) | Mechanism (Axiom 5) | Substrate (Axiom 1 — capability bundles in `AGENT_TEMPLATES`) | No |
| **Platform integrations** | Mechanism (Axiom 5) | Channel (Axiom 6 — external API surface) | No |

Pre-ADR-216, the table had YARNNN in the Identity column alongside Reviewer. The mixed classification was the tell: an entity cannot hold Identity (persona-bearing judgment) and Channel (mechanical chat surface) simultaneously without category violation. ADR-216 resolves the violation by moving YARNNN out of Identity.

---

## Consequences

### What this unlocks

1. **The scaffold protocol becomes pure and domain-agnostic.** Every workspace gets: one orchestration surface (YARNNN chat — platform-provided, no persona), one Reviewer (persona-bearing, operator-authored IDENTITY + principles + modes), N domain Agents (persona-bearing, operator-authored). The platform provides plumbing; the operator authors mind. For alpha-trader, the Reviewer IDENTITY embodies Simons; for alpha-commerce, it embodies a commerce judgment character of the operator's choosing; for future workspaces, whoever the operator declares.

2. **The platform pitch becomes honest.** Pre-ADR-216, the claim "YARNNN is a platform for operational work using Agents" was partially true: Reviewer and domain Agents were Agents in the strong sense, but YARNNN-the-Agent shared the stage and diluted the claim. Post-ADR-216, the claim is unambiguous: the operator owns 100% of the judgment surface via persona-authored Agents; YARNNN-the-surface is how they drive the orchestrator.

3. **Self-improvement attribution becomes legible.** "Did the Reviewer get smarter" is answerable when the Reviewer is the sole systemic judgment locus with a persona-bearing IDENTITY. Pre-ADR-216 the question was conflated with "did YARNNN get smarter" because both were classified as judgment-layer Agents. Post-ADR-216, only persona-bearing Agents have the question, and it maps cleanly to calibration data in `decisions.md` + `_performance.md`.

4. **Persona becomes an explicit product affordance.** Future work can build a persona catalog ("Simons Reviewer," "Buffett Reviewer," "Deming Reviewer" as operator-selectable starting templates), a persona-transplant primitive (copy an IDENTITY.md from one workspace to another), a persona-diff view (show the operator how their authored persona differs from generic default). None of these primitives make sense pre-ADR-216 because the persona concept was not first-class.

### What this costs

1. **Three ADRs now carry "superseded" or "amended" markers** for their classification of YARNNN. ADR-212 most visibly. The markers are cheap; the reasoning chain stays readable.

2. **Vocabulary churn in Commit 3.** ~20 files touched for docstring and doc-text updates. Reviewable as a single grep-and-replace commit with per-change justification. No behavior change.

3. **Frontend may need a visual distinction.** The `/agents` roster shows three kinds of things now: orchestration surface (YARNNN), systemic persona-bearing Agent (Reviewer), instance persona-bearing Agents (domain). Visually today they all look like Agent cards. Commit 3 adds a one-line label or icon treatment to make the category legible; this is surface polish, not architecture.

### What remains open (not this ADR)

1. **Domain Agent persona-read wiring** may or may not already exist — Commit 4 audits and either documents or wires.

2. **Persona catalog as a product surface** — out of scope for this ADR. Architecturally enabled by ADR-216; product design deferred.

3. **Orchestration-as-a-separate-named-module** — the Python code has `orchestration.py`, `task_pipeline.py`, `agent_creation.py`, etc. ADR-216 clarifies what lives in these modules (orchestration layer) without renaming. If the layer separation grows load-bearing in code, a future ADR can propose renames; for now, ADR-216 is conceptual.

---

## Alternatives considered

### Alt 1 — Leave YARNNN as an Agent, just wire the IDENTITY.md read

The smallest possible fix. Rejected because it preserves the category violation. If YARNNN remains an Agent and reads a workspace-authored IDENTITY.md, then the platform asks operators to author a YARNNN persona — which (a) mixes chat-surface voice with judgment persona, confusing operators about what they're authoring, and (b) gives the platform's chat surface a workspace-specific flavor that the operator now owns the responsibility for maintaining. The reframe question surfaced exactly this cost and rejected Alt 1.

### Alt 2 — Remove the YARNNN agent row entirely

The maximalist version of the reframe. Delete the `thinking_partner` `agents` table row, treat the chat surface as pure stateless orchestration. Rejected because it discards pragmatic benefits of the row (chat-session scoping, YARNNN's name appearing in activity logs and audit trails, consistency with how other Agents are addressed in session_messages). ADR-216 retains the row as implementation substrate without making the row determine the architectural classification.

### Alt 3 — Keep persona implicit (in principles.md only) and don't wire IDENTITY.md

What the code does today. Rejected in the preceding conversation with the operator as conflating principles (framework) with persona (character). A framework is applicable by any competent actor; a persona is the character that applies the framework. If the Reviewer is persona-bearing, the persona file has to be read; if IDENTITY.md exists in substrate but isn't read, it's scaffolding theater.

### Alt 4 — Drop `IDENTITY.md` and use a single persona file

Merge IDENTITY.md and principles.md into one file per Agent. Rejected because the two concepts have distinct edit cadences and authoring modes. IDENTITY.md is operator-declared character (changes rarely, deliberately). principles.md is the evaluation framework (edits more frequently as the operator tunes). Merging them couples two editing workflows that should stay orthogonal; the revision history per file is more legible when they are separate.

---

## Cross-references

- **ADR-194 v2** — Reviewer seat interchangeability. ADR-216 extends the interchangeable-seat model by making explicit that the *persona content* flows through seat rotations (OCCUPANT.md changes; IDENTITY.md does not, unless the operator chooses to rewrite it).
- **ADR-205** — Signup-scaffold collapse to YARNNN-only. ADR-216 amends the interpretation: at signup, the workspace has one orchestration surface (YARNNN) and one persona-bearing systemic Agent (Reviewer, scaffolded with generic default IDENTITY). ADR-205 code behavior unchanged.
- **ADR-207** — Primary-Action / Mandate / Capabilities. ADR-216 is orthogonal; the capability-declaration model applies to orchestration dispatch regardless of how persona is wired.
- **ADR-211** — Reviewer substrate Phase 4 (modes, calibration, handoffs). ADR-216 completes the Phase 4 substrate vision by wiring the IDENTITY file the phase scaffolded.
- **ADR-212** — Layer Mapping Correction. ADR-216 refines ADR-212 D1 by moving YARNNN from the Agent class to the orchestration class. Reviewer and domain Agents remain in the Agent class.
- **ADR-214** — Agents Page Consolidation. ADR-216 keeps ADR-214's four-tab nav and the Agents roster layout. Reclassifies the YARNNN card's semantic identity within the roster (orchestration surface vs persona-bearing Agent).
- **FOUNDATIONS v6.0 Axiom 2** (Identity). ADR-216 clarifies that not every `agents` table row with `role='thinking_partner'` sits in the Identity axis — YARNNN as orchestration surface sits in Channel + Mechanism. Axiom 2 is about persona-bearing judgment, not about Python class strings.

---

## Implementation status

- **Commit 1** (this ADR): Implemented 2026-04-24 (commit `5edc289`).
- **Commit 2** (Reviewer persona wiring): Implemented 2026-04-24 (commit `2f6b49f`). `reviewer_agent.py::review_proposal()` now accepts `identity_md`; `_build_user_message()` opens with the persona section; `_SYSTEM_PROMPT` names IDENTITY.md as substrate item 1. `review_proposal_dispatch.py` reads `/workspace/review/IDENTITY.md` and passes it through. `REVIEWER_MODEL_IDENTITY` bumped v1 → v2.
- **Commit 3** (Vocabulary unification): Implemented 2026-04-24 (commit `898fdf6`). CLAUDE.md Key terminology rewritten; GLOSSARY.md adds Persona row + reclassifies YARNNN in the Entities table; `orchestration.py` docstrings + `DEFAULT_REVIEW_IDENTITY_MD` gain operator-instruction header; stale `tp_prompts/` + `thinking_partner.py` paths in CLAUDE.md File Locations table corrected to `yarnnn_prompts/` + `yarnnn.py` (ADR-189 propagation that never completed).
- **Commit 4** (Domain Agent persona reads): Implemented 2026-04-24 (commit `94714b5`). Audit confirmed domain Agents use single-file `AGENT.md` convention for persona + framework (read at 3 sites in `task_pipeline.py`). D9 added to this ADR documenting the convention and its rationale (domain Agents are single-domain; persona and framework do not have edit-cadence orthogonality). `task_pipeline.py` gains a clarifying comment cross-referencing D9.
- **Commit 5** (scaffold_trader.py + E2E proof): Implemented 2026-04-24. `scaffold_trader.py` rewritten to consume the ADR-216 mechanism end-to-end. (1) Seven substrate files now upserted via singular DB-upsert path (no dual `/api/memory/user/*` route — ADR-206 _shared/ alignment). (2) Reviewer persona `/workspace/review/IDENTITY.md` overwrites the generic default with a Simons-character declaration — the first real test of the ADR-216 Commit 2 wiring. (3) Reviewer `modes.md` activates the `trading` block with `autonomy_level: manual` (per §3A.4 Auto-approve=NONE), routing the Reviewer dispatcher to observe-and-recommend. (4) Tasks drop the retired `trading-bot` agent_slug; assign `tracker` / `analyst` / `writer` production roles and declare `required_capabilities: [read_trading, write_trading]` per ADR-207 P4a. Dry-run verified: seven files + six tasks compose cleanly. E2E execution against alpha-trader persona is the validation that the full ADR-216 reframe produces persona-shaped Reviewer reasoning in `decisions.md`.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-24 | v1 — initial draft. Four load-bearing decisions (D1 two-layer taxonomy, D2 YARNNN reclassification, D3 Reviewer as sole systemic Agent, D4 persona is first-class substrate read at reasoning time). D5 vocabulary. D6 staged implementation. D7 non-goals. D8 historical ADR preservation. Dimensional test, consequences, alternatives. |
