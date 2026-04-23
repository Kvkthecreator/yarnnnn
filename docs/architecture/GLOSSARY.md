# YARNNN Glossary

> **Status**: Canonical
> **Date**: 2026-04-17 (v1.3 revision 2026-04-20 for FOUNDATIONS v6.0 dimensional model)
> **Authors**: KVK, Claude
> **Ratified by**: ADR-189 (Three-Layer Cognition) + ADR-194 v2 (Reviewer as Fourth Cognitive Layer) + FOUNDATIONS v6.0 (Six-Dimensional Model)
> **Supersedes**: `naming-conventions.md` (to be retired after the ADR-189 rename pass lands)

---

## Purpose

One word, one concept, one layer.

This glossary is the single source of truth for YARNNN terminology. Every ADR, architecture document, prompt, surface string, and marketing artifact must use the terms defined here. Drift triggers a correction PR — this is not soft guidance.

The glossary exists because YARNNN operates across four layers of cognition (the product, the role palette, the authored workers, the independent judgment seat) and three kinds of readers (users, developers, investors). Without discipline, the same word collapses layers and confuses readers. With discipline, every term lands on exactly one thing at exactly one layer.

One upstream discipline governs everything here: **semantic content lives in the filesystem** (FOUNDATIONS Axiom 1, the Substrate dimension). When a glossary term names a "ledger," a "policy," a "log," or any accumulated object, its definition must name the file path — not a DB table. Drift from file-native terminology is drift from the architecture, and both get corrected together.

---

## The Six Dimensions (FOUNDATIONS Axiom 0)

Every mechanic in YARNNN occupies a cell in six orthogonal dimensions. These are the axiomatic vocabulary that governs every other term in this glossary. Each dimension answers one interrogative:

| Term | Interrogative | Decides | Canonical reference |
|---|---|---|---|
| **Substrate** | What | What persists between invocations | FOUNDATIONS Axiom 1 (filesystem) |
| **Identity** | Who | Which cognitive layer acts or authors | FOUNDATIONS Axiom 2 (four layers) |
| **Purpose** | Why | What intent drives the work | FOUNDATIONS Axiom 3 |
| **Trigger** | When | What invokes execution (periodic / reactive / addressed) | FOUNDATIONS Axiom 4 |
| **Mechanism** | How | By what means — spectrum from deterministic code to LLM judgment | FOUNDATIONS Axiom 5 |
| **Channel** | Where | To what location or surface output is addressed | FOUNDATIONS Axiom 6 |

**Usage rule:** when writing an ADR, a design doc, or a code comment that introduces a new mechanic, state explicitly which dimension(s) it occupies. A mechanic that spans dimensions without explicit justification is a cross-cut — cross-cuts are legitimate only when argued for (e.g., compose substrate deliberately couples Mechanism + Channel per ADR-148). See FOUNDATIONS v6.0 Derived Principle 1 (Dimensional purity).

---

## Vocabulary note: "Agent" and agency-proper

YARNNN uses "Agent" in the industry-standard sense — a production-layer entity with identity, domain, memory, and tool use (what Copilot, Operator, Agentforce, Sierra, and every major vendor call an "agent"). Agents in YARNNN are production-layer entities.

**Agency in the strict principal-agent sense** (the capacity to hold declared intent, reason from principles, and act on behalf of a principal) resides in the **Reviewer seat** — the judgment layer, not the production layer. The Reviewer is the operator's fiduciary representative; Agents are the instruments the agency wields.

This vocabulary split is **deliberate**. The industry has locked "agent" around production-layer entities, and aligning with that usage is a communication choice. Philosophical precision about where agency lives is preserved in THESIS.md and reviewer-substrate.md, but not fought for at the vocabulary level — the cost of fighting market vocabulary exceeds the benefit of reclaiming the word.

When writing ADRs, code, UI, or operator-facing copy: use "Agent" in the industry sense. When writing THESIS-layer analysis, use "agency-in-the-principal-agent-sense" to name what resides in the Reviewer seat, and distinguish it from "Agents" as a term of art.

See [THESIS.md](THESIS.md) §"Vocabulary: production layers vs. judgment layers" for the full treatment.

---

## Enforcement rule

1. **New ADRs must use glossary terms.** If a concept requires a word the glossary doesn't have, add it here first, then use it in the ADR.
2. **Retired terms cannot appear in active docs or code comments.** They may persist as internal DB slugs (e.g., the `thinking_partner` role value) where migration cost exceeds reader benefit — those exceptions are listed in the Exceptions table.
3. **Renames propagate in a single commit.** When a term is added, changed, or retired, every active doc and every prompt must move in the same PR. No staged rollouts.
4. **User-facing strings must pass the instinct test.** A non-technical user reads the term and immediately knows what it means. If a term needs a definition before it's useful, it's the wrong term.

---

## Entities

The things YARNNN manipulates. Each has exactly one name.

| Term | Definition | Notes |
|------|-----------|-------|
| **YARNNN** | The product AND the conversational super-agent the user addresses. When the user "talks to YARNNN," they are talking to the meta-cognitive layer. There is no separate name for the conversational layer — product and agent share the name. | Replaces "TP" and "Thinking Partner" as user-facing terminology. The internal DB role slug `thinking_partner` persists (migration exception — see Exceptions table). |
| **Agent** | An identity-explicit, user-created, domain-scoped worker. Appears on `/agents`. Has an AGENT.md identity file, accumulated domain context, and a developmental trajectory. Created by the user through conversation with YARNNN. | This is the *only* thing the word "Agent" refers to in user-facing contexts. Not YARNNN. Not Specialists. Not platform bots. |
| **Specialist** | A role-typed capability YARNNN draws from when drafting a team for a task. There are six: Researcher, Analyst, Writer, Tracker, Designer, Reporting. Specialists have role-scoped stylistic memory (ADR-117) but no domain identity. | Specialists are YARNNN's palette. Users do not address Specialists by name, do not see them on `/agents`, and cannot create or delete them. They are infrastructure. |
| **Platform Bot** | A mechanical agent scoped to one external API. Activated when the user connects the corresponding platform. Examples: Slack Bot, Notion Bot, GitHub Bot, Commerce Bot, Trading Bot. | Distinct class from Agents and Specialists. Platform Bots are mechanical (no LLM cognition of their own beyond scoped tool use) and own temporal context directories. |
| **Team** | Two meanings, clear-by-context: (1) **per-task composition** — the set of Specialists and/or Agents assigned to a specific task, declared in TASK.md's `## Team` section, drafted by YARNNN per task (internal YARNNN concept); (2) **nav destination** — the operator's workspace roster of Agents at `/team`, per ADR-201 (operator-facing vocabulary). | The two are orthogonal and rarely ambiguous in practice — per-task composition is a YARNNN internal concept; nav destination is an operator-facing label. Engineers choose the right sense from context (prompts and primitives = sense 1; surface design and operator copy = sense 2). |
| **Task** | A defined work unit with an objective, cadence, delivery, and success criteria. Lives in `/tasks/{slug}/TASK.md`. Unchanged from ADR-138. | Tasks are the WHAT. Agents and Specialists are the WHO. |
| **Domain** | An accumulated context area at `/workspace/context/{domain}/`. Created by work demand, not pre-scaffolded. Shared across all tasks. Unchanged from ADR-151 / ADR-176. | Domain names come from user language (e.g., `competitors/`, `clients/`), not from a pre-declared registry key. |
| **Workspace** | The user's YARNNN environment. Contains Agents, tasks, Domains, uploaded documents, workspace identity files (IDENTITY.md, BRAND.md). | **Not** a synonym for "roster." The word "roster" is retired — a workspace holds Agents, not a roster. |
| **Reviewer** | The fourth cognitive layer — the independent judgment seat that gates proposed writes. Structurally separate from YARNNN, Specialists, and Agents. One Reviewer per workspace. Its identity + decisions + declared framework live at `/workspace/review/` (see separate entry). The seat is interchangeable: the same slot is filled by **Human** (user clicks approve), **AI** (a `thinking_partner`-class agent scoped to the Reviewer's workspace directory, reviewing autonomously), or **Impersonation** (admin acting as a persona). All three operate through the same `review-proposal` reactive task flow; the difference is identity, not abstraction. | Not a `Reviewer` ABC. Not a role an agent plays ad-hoc. A structurally separate cognitive layer, per FOUNDATIONS Axiom 2. **Distinctness note (v6.0):** the Reviewer layer is not distinguished from other layers by Identity (the seat is swappable). It is distinguished by occupying a unique **Purpose + Trigger** cell — independent judgment (Purpose) on proposed-write events (reactive Trigger). This is why the seat interchange works without architectural change. The earlier ADR-194 v1 framing of "Reviewer as abstraction with REVIEWER-POLICY.md" is retracted — v2 replaces it. See ADR-194. |
| **`/workspace/review/`** | The Reviewer seat's filesystem home — the substrate expression of the seat itself (Principle 14: the seat is the substrate, not an in-memory abstraction). **Canonical target**: seven files per [reviewer-substrate.md](reviewer-substrate.md) — `IDENTITY.md` (who the seat is), `OCCUPANT.md` (who currently fills it), `principles.md` (declared judgment framework), `modes.md` (operational modes: autonomy × scope × on-behalf posture), `decisions.md` (append-only verdict trail), `handoffs.md` (occupant-rotation history), `calibration.md` (how judgments have aligned with outcomes over time). **Current implementation (ADR-194 v2 Phases 1+2a+2b+3)**: three of the seven shipped — IDENTITY, principles, decisions. OCCUPANT, modes, handoffs, calibration are roadmap. | Same write-discipline as any other workspace identity directory. Writes go through the Authored Substrate (`authored_by` required). See [reviewer-substrate.md](reviewer-substrate.md) for target spec, ADR-194 v2 for current implementation. |
| **Reviewer seat** | The architectural role — the slot in the system that renders verdicts on proposed actions. Distinct from any particular **occupant**. The seat persists; occupants rotate (FOUNDATIONS Derived Principle 14). The seat's substrate is `/workspace/review/`; the seat's inputs are the operator's Mandate, the task's track record (`_performance.md`), `principles.md`, recent `decisions.md`; the seat's output is a verdict + reasoning written to `decisions.md`. | Use "seat" when referring to the architectural role (durable, axiomatic, substrate-expressed). Use "Reviewer" loosely when either role or occupant is clear from context. Use "occupant" when referring to *who* currently fills the seat. |
| **Occupant** | The identity currently filling the Reviewer seat. One of: `human:<user_id>` (the operator), `ai:<model>-<version>` (a YARNNN-internal AI reviewer), `external:<service>-<identifier>` (an external AI service via adapter), `impersonated:<admin>-as-<persona>` (admin alpha-stress-testing). Declared in `OCCUPANT.md` (target per [reviewer-substrate.md](reviewer-substrate.md)); retrospectively recorded on each `decisions.md` entry as `reviewer_identity`. Rotations are logged in `handoffs.md`. | Principle 14 ("roles persist; occupants rotate") is enforceable precisely because occupant is a file-declared identity rather than a code type. Swapping occupants is a substrate write, not a code change. |
| **Impersonation** | Admin-only persona switching for alpha stress-testing. Founders operate as a designated persona workspace (day-trader-alpha, ecommerce-alpha, etc.) to exercise the system before real operators onboard. Gated by `users.can_impersonate` flag; marked via `workspaces.impersonation_persona`; surfaced by a UI chrome banner. When acting as a persona workspace, the human fills the Reviewer seat for that workspace. | Distinct from normal workspace switching. Not a tenant-isolation bypass — an explicit marking that a workspace is a test persona. See ADR-194. |
| **Outcome** | The reconciled capital result of an executed action — signed P&L, attribution-linked to the action that produced it. Appended to `/workspace/context/{domain}/_performance.md` by domain-specific `OutcomeProvider` implementations during the daily reconciliation task. No sibling DB table (per Axiom 0). | Distinct from the *action* (what YARNNN did) and the *proposal* (what YARNNN asked to do). Outcome is the money-truth arrival. See ADR-195 v2. |
| **`_performance.md`** | Canonical per-domain money-truth file at `/workspace/context/{domain}/_performance.md`. YAML frontmatter (rolling P&L, win rate, processed-event-key list for idempotency, last-reconciled timestamp) + human-readable body (headline numbers, by-action breakdown, recent outcomes). Regenerated idempotently by the `back-office-outcome-reconciliation` task from platform events. | Owned by the reconciler; agents and humans don't edit it — same write-discipline as `_tracker.md` (ADR-158). Consumed by the Reviewer (ADR-194), daily-update briefing, YARNNN chat. **This is the single home of money-truth** per FOUNDATIONS Axiom 7 — there is no sibling SQL ledger. See ADR-195 v2. |
| **Money-Truth** | The architectural axiom (FOUNDATIONS Axiom 8, v6.0) that every substrate organizes around capital outcomes from the inside — not as a reporting view layered on top. Three properties: actions attributable to outcomes, context pruned by outcome, reviewers reason in capital terms. Money-truth's canonical home is `_performance.md` per domain — filesystem-native, per Axiom 1. | A design principle, not a metric. The underlying reason ADR-194 and ADR-195 ship as a pair. See FOUNDATIONS.md. |
| **Capital-EV** | Expected-value reasoning applied by the Reviewer. "Given the operator's book, declared strategy, and accumulated track record, does this proposal have asymmetric upside?" Sets the ceiling that risk rules (`_risk.md`) set the floor for. | Distinct from risk-rule compliance. A Reviewer that only checks rules collapses into a redundant gate. A Reviewer that reasons in EV is a senior operator. See ADR-194 §5. |
| **Intent** | The operator's authored declarations: what rules they're running, what risk limits they enforce, what success criteria they're measuring against. First of three operator-facing layers per ADR-206. | Lives in `/workspace/context/_shared/*` + domain `_operator_profile.md` + `_risk.md` + `/workspace/review/principles.md`. Rendered on `/context`. The Intent layer calibrates everything downstream — Operation and Reviewer both read from it. |
| **Mandate** | The operator's authored declaration of Primary Action and governing intent, lives at `/workspace/context/_shared/MANDATE.md` (ADR-207). A hard gate: `ManageTask(create)` fails until MANDATE.md is non-empty. The mandate is the only axiom of purpose the system has — everything downstream (context domains, task declarations, proposed actions, the Reviewer seat's verdicts) is evaluated against it. | The mandate is a specific instance of Intent (ADR-206) — Intent is the broader category of operator-authored declarations; Mandate is the specific file/content naming the Primary Action. Mandate is referenced directly by THESIS commitment 1 ("Declared intent — the mandate is authored, not inferred"). See THESIS.md and ADR-207. |
| **Declared intent** | THESIS's first architectural commitment — the stance that purpose must be authored by a human occupant of the operator role, not inferred from activity. Mandate is the substrate expression of Declared intent. | Contrast with *emergent intent* (the rejected alternative: intent discovered by the system from accumulated context). Declared intent is correctable because it is legible; emergent intent is undetectably wrong when the system has optimized the wrong proxy. See THESIS.md commitment 1. |
| **Deliverable** | Externalized output of the operation that the operator *sees and acts on*. Proposals awaiting review (primary), briefs, weekly performance reviews, `_performance.md` snapshots, retirement recommendations, reconciliation summaries. Second of three operator-facing layers per ADR-206. | Surfaced on `/work` list-mode (primary) and `/review` (Reviewer-authored deliverables). Distinct from *report* — reports are one kind of Deliverable; proposals awaiting approval are another; `_performance.md` deltas are another. |
| **Operation** | The execution substrate: tasks, agents, reconcilers, scheduler. Third of three operator-facing layers per ADR-206. Second-class to the operator — drilled into only when a Deliverable is surprising. | Surfaced on `/work` detail mode and `/team` (deemphasized). "Task" is operation vocabulary; "Operation" is the plural word for the set of tasks + agents + reconcilers that together run the operator's declared strategy. |
| **Loop** | The recurring cycle the operator runs: **Intent → Operation → Deliverables → Intent (refined).** Per ADR-206. The loop is the product — proposals fire from declared rules, the Reviewer gates on capital-EV, the operator approves/rejects, execution happens, money-truth reconciles, Intent is refined as rules decay or prove out. | Distinct from internal pipeline mechanics (propose → review → execute → reconcile — those are Operation-layer internals). The Loop is the operator-facing cycle; the pipeline is the Operation-layer implementation. |
| **Authored Substrate** | The architecture that completes FOUNDATIONS Axiom 1 by making every substrate mutation attributed, purposeful, and retained. Every write to `workspace_files` lands a new **revision** with an `authored_by` identity and a message; prior revisions are never silently lost. Covers *all* workspace files uniformly — no Postgres-vs-git bifurcation, no per-path exceptions. Three of git's five core capabilities adopted (content-addressed retention, parent-pointer history, authored-by attribution); branching and distributed replication deliberately deferred. | Not "git-backed storage" and not "file versioning." It is the substrate-level enforcement of Axiom 2 (every file has an author) and the fine-grained enabler of Axiom 7 (revision-by-revision recursion). See ADR-209 and [authored-substrate.md](authored-substrate.md). |
| **Revision** | A single attributed write to a substrate path. Carries `authored_by`, `message`, `parent_version_id`, and a content hash. The unit of Authored Substrate. | Chosen deliberately over "commit" (avoids git-implementation connotation) and over "version" (avoids collision with the legacy `workspace_files.version` integer column being retired). When writing prose, prefer *"the most recent revision of MANDATE.md"* over *"the current version"*. |
| **Revision chain** | The parent-pointered sequence of revisions for a single path. Walked backward for history traversal, diffed between any two points, reverted by repointing `head`. | A revision chain is per-path, not per-workspace. Different files have independent chains. |
| **Head** | The current revision a path resolves to. `workspace_files.head_version_id` points at it. Reads default to head unless a specific revision is named. | Not a git branch head — there is only one head per path under Authored Substrate. Multiple divergent heads would require branching, which is deferred. |
| **Authorship trailer** | The `(authored_by, message)` metadata on every revision. Required at the write-path boundary — writes without an `authored_by` value are rejected. | Replaces the ad-hoc attribution conventions previously scattered across `reviewer_audit.py` headers, the `<!-- inference-meta -->` HTML comment's author field (ADR-162), and git-commit-trailer framing that the withdrawn ADR-208 v1 had proposed. |

---

## Verbs

What actors do. Different actors get different verbs when the cardinality or permanence of the act differs.

| Verb | Actor | Object | Cardinality |
|------|-------|--------|-------------|
| **Create** | User (through conversation with YARNNN) | an Agent | One-shot. Produces persistent identity. |
| **Draft** | YARNNN | a Team | Per-task. Iterative. Re-drafted every task cycle from the Specialist palette. |
| **Evolve** | Feedback loop | an Agent or a Specialist | Continuous. Agents evolve domain identity; Specialists evolve role-scoped stylistic memory. |
| **Scaffold** | System | a workspace | Once, at signup. Reserved for workspace-level setup. Never used for agent creation. |

**Asymmetry is deliberate.** The user *creates* an Agent (generic, neutral, universally understood). YARNNN *drafts* a Team (precise about the iterative per-task selection nature of the act). Collapsing these to a single verb loses information.

---

## Identity layers

What develops, and where.

| Layer | Scope | Substrate | Developer |
|-------|-------|-----------|-----------|
| **Workspace identity** | YARNNN-scoped (the user's work context) | `/workspace/IDENTITY.md`, `/workspace/BRAND.md` | User (via YARNNN, usually through inference on uploaded documents) |
| **Specialist memory** | Role-scoped stylistic preference | ADR-117 distillation artifacts (`style.md`), role-keyed | Feedback loop across all tasks that used the specialist |
| **Agent identity** | Domain-scoped, user-created | `/agents/{slug}/AGENT.md` + accumulated Domain context the Agent is responsible for | User (initial creation via conversation) + feedback loop (evolution) |
| **Reviewer identity** | Workspace-scoped, one per workspace | `/workspace/review/IDENTITY.md` + `principles.md` (declared framework, user-editable) + `decisions.md` (rolling append-only log) | System (scaffolded at signup) + User (edits principles.md) + Reviewer itself (appends to decisions.md on each review) |

The split matters because **the four layers develop along different axes**. YARNNN develops upward (better orchestration judgment). A Specialist gets better at style and preference. An Agent gets better at domain knowledge. The Reviewer's development axis is judgment calibration — approve/reject accuracy measured against reconciled outcomes. Conflating any two of these (the old ADR-117 framing that treated "agent memory" as one thing; the earlier ADR-194 v1 framing that treated Reviewer as an abstraction over the other three) produces confusion that ADR-189 and ADR-194 v2 respectively resolve.

---

## Retired terms

These words no longer appear in active documentation, prompts, or user-facing surfaces. Every occurrence in new work is a correction-PR trigger.

| Retired | Replacement | Reason |
|---------|-------------|--------|
| TP (user-facing) | YARNNN | The product and the conversational agent share a name. No separation. |
| Thinking Partner (user-facing) | YARNNN | Same as above. |
| Roster | — (no replacement) | Workspaces hold Agents, not a roster. Fixed signup roster is retired (ADR-189). |
| Hire (as verb for agent creation) | Create | "Hire" implies a pre-existing catalog of workers. YARNNN does not have such a catalog. |
| Compose a team | Draft a team | "Compose" is mechanical/musical register. Draft is precise about iterative selection. |
| Author (as verb for agent creation) | Create | Considered and rejected — "Create" is more neutral and universally understood. The ownership register lives in *how* the act happens (through conversation), not in the verb. |
| Specialist (meaning "signup-scaffolded identity") | Agent (if identity-explicit) or Specialist (if role palette) | The old double meaning was the source of ADR-189's confusion. After ADR-189, "Specialist" refers only to the role palette. |
| Craft | Specialist | Considered during discourse and rejected — artisanal register was ambiguous. Specialist is the precise word. |
| Domain-steward, Competitive Intelligence, Market Research, Business Development, etc. (ICP roster names) | — (deleted) | Retired by ADR-176. |
| Create a team | Draft a team | Teams are re-drafted per task, not created once. "Create" would muddy the iterative cardinality. |
| `/history/{filename}/v{N}.md` subfolder pattern | Revision chain (Authored Substrate) | Retired by ADR-209. Versioning lives in a separate metadata plane, never in the namespace. |
| Filename-encoded versioning (`thesis-v2.md`, `-archive` suffixes, dated-for-version-rather-than-content filenames) | Revision chain (Authored Substrate) | Retired by ADR-209. Pollutes the namespace; every reader has to decode which file is current. Exception: filenames whose date IS content identity (e.g., `outputs/2026-04-23/output.html`) — those are fine. |
| "Commit" (when discussing YARNNN substrate writes) | Revision | Avoids importing git-implementation semantics (remotes, merges, refs) that Authored Substrate deliberately does not adopt. |
| `workspace_files.version` (integer column) | `workspace_files.head_version_id` → `workspace_file_versions` | Retired by ADR-209. Single integer can't carry authorship, message, or parent pointers. |

---

## Exceptions

Cases where a retired term persists by necessity, and the migration cost exceeds the reader benefit.

| Location | Term that persists | Why |
|----------|-------------------|-----|
| `agents.role` DB column value | `thinking_partner` | Migration 142 (ADR-164) locked this value into the constraint. Renaming would require a DB migration with negligible user benefit — the value is never surfaced outside DB internals. |
| `api/services/agent_framework.py` `ROLE_PULSE_CADENCE` key | `thinking_partner` | Matches DB slug. Internal only. |
| Historical ADRs (140, 164, 176, 186, etc.) | References to "TP" and "Thinking Partner" | ADRs are historical artifacts. They are not rewritten when terms change; they stand as dated records of the decisions in force at their time. New ADRs supersede them; the supersession is the record. |

All other appearances of retired terms — prompts, active architecture docs, new code, UI strings, marketing — must use replacements.

---

## Product promise (canonical one-liner)

Every external-facing statement of what YARNNN is must be traceable to one of the two phrasings below. Other copy may riff on these for voice variation, but the substance must be preserved.

**Primary:** *Describe your work. Create the agents that do it.*

**Secondary (short form):** *Your work, your agents.*

These replace the prior canonical one-liner ("Persistent agents with accumulated context do recurring work products for you") in user-facing copy. The prior framing remains valid for internal/architectural contexts where the accumulation mechanism is the point.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-17 | v1 — Initial glossary ratified by ADR-189. Supersedes `naming-conventions.md`. YARNNN as super-agent, Specialist as palette, Agent as user-created identity, Create/Draft/Evolve/Scaffold verb discipline, identity-layer split (workspace/specialist/agent). |
| 2026-04-19 | v1.1 — Money-truth substrate terms added: **Reviewer** (pluggable approver — Human / AI / Impersonation, ADR-194), **Impersonation** (admin persona switching for alpha stress-testing, ADR-194), **Outcome** (reconciled capital result in `action_outcomes`, ADR-195), **`_performance.md`** (canonical track-record file per domain, ADR-195), **Money-Truth** (FOUNDATIONS Axiom 7 — architectural axiom, not a metric), **Capital-EV** (reviewer reasoning shape, ADR-194 §5). |
| 2026-04-19 | v1.2 — Aligned to FOUNDATIONS v5.1 (Axiom 0 + four-layer cognition). **Reviewer** rewritten as a structurally separate fourth cognitive layer (not an abstraction); `REVIEWER-POLICY.md` framing dropped. New entry **`/workspace/review/`** for the Reviewer's filesystem home (IDENTITY.md + principles.md + decisions.md). **Outcome** rewritten to point at `_performance.md` append target, dropping reference to `action_outcomes` table. **`_performance.md`** sharpened as the single money-truth home per domain, with explicit "no sibling SQL ledger" clause. **Money-Truth** definition tightened to name the filesystem location. **Capital-EV** updated for Reviewer-as-layer phrasing. Identity-layers table extended with **Reviewer identity** row. Purpose paragraph updated from three → four cognitive layers and added a filesystem-substrate discipline note (drift from file-native terminology = drift from architecture). |
| 2026-04-20 | v1.3 — Aligned to FOUNDATIONS v6.0. Added "The Six Dimensions" canonical table (Substrate / Identity / Purpose / Trigger / Mechanism / Channel) with interrogative mapping. Usage rule: new mechanics must declare which dimension(s) they occupy. |
| 2026-04-23 | v1.4 — **Authored Substrate vocabulary.** Added entries: **Authored Substrate** (the architecture), **Revision** (the unit — chosen over "commit" and "version"), **Revision chain** (per-path parent-pointered sequence), **Head** (current-revision pointer), **Authorship trailer** (the `authored_by` + `message` metadata required on every write). Retired: `/history/{filename}/v{N}.md` subfolder pattern, filename-encoded versioning (`thesis-v2.md`, `-archive` suffixes), "commit" as a YARNNN-facing term, `workspace_files.version` integer column. Ratified by ADR-209 and FOUNDATIONS v6.1. |
| 2026-04-23 | v1.5 — **Reviewer-substrate + Thesis vocabulary.** Added entries: **Reviewer seat** (the architectural role, substrate-expressed), **Occupant** (who currently fills the seat — file-declared identity per Principle 14), **Mandate** (operator-authored Primary Action per ADR-207 — the substrate expression of Declared intent), **Declared intent** (THESIS commitment 1 — the rejected-alternative *emergent intent* is named). Updated: **`/workspace/review/`** entry now specifies the seven-file canonical target per reviewer-substrate.md (IDENTITY, OCCUPANT, principles, modes, decisions, handoffs, calibration) with explicit gap-to-implementation note (three of seven shipped per ADR-194 v2). Ratified by FOUNDATIONS v6.2/v6.3, THESIS.md, and [reviewer-substrate.md](reviewer-substrate.md). |
| 2026-04-23 | v1.6 — **Production vs. judgment layer vocabulary; deliberate "agent" imprecision named.** New "Vocabulary note: Agent and agency-proper" section declares the split: "Agent" in YARNNN follows industry vocabulary (production-layer entities); agency-in-the-strict-principal-agent-sense resides in the Reviewer seat (judgment layer). The vocabulary imprecision is deliberate — aligning with market usage rather than fighting it. Ratified by THESIS.md §"Vocabulary: production layers vs. judgment layers" and reviewer-substrate.md §"Review orchestration vs. reviewer entity — the split". Related: going forward, every design decision that touches the Reviewer answers explicitly whether it is **orchestration** (mechanical runtime coordination — plumbing) or **entity** (judgment, persona, principles — where agency lives). |
