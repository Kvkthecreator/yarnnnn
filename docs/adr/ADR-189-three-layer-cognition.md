# ADR-189: Three-Layer Cognition — YARNNN, Specialists, Agents

> **Status**: Proposed
> **Date**: 2026-04-17
> **Authors**: KVK, Claude
> **Supersedes**: ADR-140 (Agent Workforce Model — pre-scaffolded ICP roster) in full; ADR-176 Decision 1 (Hospital Principle — fixed 9-agent signup roster)
> **Amends**: ADR-117 (Agent Feedback Substrate — identity-layer split), ADR-164 (Back Office Tasks — TP renamed to YARNNN at user-facing layer), ADR-186 (TP Prompt Profiles — file and class renames)
> **Ratifies**: `docs/architecture/GLOSSARY.md` as canonical terminology source
> **Triggered by**: Audit of ADR-188 domain-agnostic framework surfacing incoherence between registry-layer contextuality and signup-layer fixed roster

---

## Context

### The audit finding

ADR-188 reframed registries as template libraries: "universal roles, contextual application." This was the correct move at the registry layer. But it left a structural incoherence unaddressed: the registry layer now says "roster composition is contextual per workspace," while `workspace_init.py` still scaffolds a fixed nine-agent roster at signup per ADR-176 Decision 1. The two layers disagree.

The disagreement surfaces as four observable ICP leaks:

1. **Pre-scaffolded Commerce and Trading bots** appear in roster code even for users who never connect those platforms.
2. **Directory registry entity templates** bias toward the original ICP archetypes, causing an asymmetry between "registered" and "unknown" domains.
3. **TP's task catalog** primes through a pre-scaffolded roster that assumes ICP work patterns.
4. **"Revenue as moat proof"** (Axiom 4) is asserted as universal but is in fact an ICP-scoped claim.

Leaks 1–3 dissolve if the signup-scaffolded identity layer is removed. Leak 4 requires a separate documentation scope edit and is handled in a follow-on commit, not this ADR.

### The deeper observation

Behind the audit leaks sits a structural question: **the six specialist roles are being asked to carry identity they cannot carry.**

A Specialist with `domain: None` can accumulate role-scoped stylistic preferences (per ADR-117) — "this user prefers em-dashes, punchy leads, no hedging." It cannot accumulate domain expertise, because domain assignment is per-task and ephemeral. A Specialist is not the persistent domain-cognitive entity FOUNDATIONS Axiom 3 describes. It is a palette element.

Conflating Specialists (role-cognition) with Agents (domain-cognition) and with YARNNN (meta-cognition) produces:

- A user who lands on `/agents` at signup and sees nine entries they did not create, named after roles they don't recognize as "theirs."
- A mental model where "Agent" means three different things depending on which entry is under discussion.
- A positioning claim ("persistent agents, not session threads" — ESSENCE Stable Element 1) that is only partially true at Day 0.

### The positioning reframe

The audit finding and the identity conflation share a product-level consequence: YARNNN currently positions as **"agent team for hire"** — the user arrives, specialists are provisioned, trust is delegated. After ADR-189, YARNNN positions as **"authored team"** — the user arrives, describes work, Agents emerge through that conversation, authorship is the immediate signal.

Authorship is a stronger moat than quality at Day 0:

- **Quality moat** (team gets better at its job, revenue proves it) compounds slowly and depends on revenue trajectory — which does not exist in the first session.
- **Authorship moat** ("these Agents are mine, I built them, switching means rebuilding") compounds from the first Agent created, before any revenue tick.

This matches the retention mechanism of Lovable, Cursor, Claude Code, and Notion — the authored artifact *is* the switching cost. It also matches the ICP (content product operators are creators; they author).

---

## Decision

### The three-layer cognition model

YARNNN has three layers of cognition with distinct scopes, substrates, and developmental axes. Each layer has exactly one name.

| Layer | Name | Scope | Substrate | Develops along |
|-------|------|-------|-----------|----------------|
| 1 | **YARNNN** | Workspace-level (meta-cognition) | `/workspace/IDENTITY.md`, `/workspace/BRAND.md`, compact index, session memory | Judgment about user's attention, workforce health, orchestration |
| 2 | **Specialist** | Role-level (role-cognition) | ADR-117 role-keyed style distillation | Stylistic preference across all tasks using the specialist |
| 3 | **Agent** | Domain-level (domain-cognition) | `/agents/{slug}/AGENT.md` + accumulated Domain context | Domain knowledge, user-created identity, tenure |

**YARNNN** is the product and the conversational super-agent. The user addresses YARNNN directly. There is no separate name for the conversational layer.

**Specialists** are the six role-typed capabilities YARNNN draws from when drafting a Team for a task: Researcher, Analyst, Writer, Tracker, Designer, Reporting. They are infrastructure. Users do not address Specialists, do not see them on `/agents`, and cannot create or delete them.

**Agents** are identity-explicit, user-created, domain-scoped workers. They appear on `/agents`. Each is created by the user through conversation with YARNNN. An Agent has an AGENT.md, a slug, a domain assignment, and a developmental trajectory. Agents are the only entities the user supervises as persistent workers.

**Platform Bots** (Slack Bot, Notion Bot, GitHub Bot, Commerce Bot, Trading Bot) remain a distinct fourth class — mechanical, API-scoped, activated on connection. Unchanged from ADR-158 / ADR-183 / ADR-187.

### The authored-team principle

Authorship is the primary product experience. The user's relationship to their Agents is ownership, not delegation. This has three concrete consequences:

1. **Signup scaffolds no Agents.** A brand-new workspace contains YARNNN (the super-agent the user addresses), the six Specialists (palette, not user-visible entries), and zero Agents. Platform Bots activate on connection.
2. **`/agents` empty state shows zero entries.** The empty state's primary CTA is conversational: "Tell YARNNN what you want to track, produce, or monitor." No roster, no pre-populated catalog.
3. **Agents are created through conversation, not through a form.** The user describes work; YARNNN infers what Agent identity emerges; the user confirms. Form-based agent creation is not introduced.

### Glossary discipline as first-class artifact

Terminology drift across ADRs, prompts, and surfaces has been a standing source of confusion (ADR-168 addressed the primitive-layer drift; the identity-layer drift is addressed here). ADR-189 ratifies `docs/architecture/GLOSSARY.md` as canonical. Every ADR, prompt, surface string, and marketing artifact must use glossary terms. Drift triggers a correction PR.

The glossary establishes:

- Four entity terms (YARNNN, Agent, Specialist, Team) with one concept each.
- Four verb terms (Create, Draft, Evolve, Scaffold) with actor × object × cardinality discipline.
- A retired-terms table (TP, Thinking Partner, Roster, Hire, Compose, Author, Craft — banned in new work).
- An exceptions table for DB slugs and historical ADRs where retired terms persist by necessity.

See `docs/architecture/GLOSSARY.md` for the full vocabulary. That document is the source of truth — this ADR ratifies it and reserves the right of future ADRs to extend it.

---

## What changes

### Phase 1 — Documentation foundation (no code)

| File | Change |
|------|--------|
| `docs/architecture/GLOSSARY.md` | **New, canonical.** Ratified by this ADR. |
| `docs/architecture/naming-conventions.md` | Banner added pointing to GLOSSARY.md. Full content retired (contents now inaccurate re: TP → YARNNN). |
| `docs/architecture/FOUNDATIONS.md` | Axiom 1 updated: "TP is an agent" → "YARNNN is the meta-cognitive agent" with three-layer framing. Axiom 3 updated: identity split made explicit (Workspace / Specialist / Agent). Axiom 5 title updated: "TP's Compositional Capability" → "YARNNN's Compositional Capability." |
| `docs/ESSENCE.md` | Stable Element 1 reworded: "Persistent agents, not session threads" → "Agents built around your work, not generic assistants." Canonical Positioning reworded per glossary product-promise one-liners. |
| `docs/NARRATIVE.md` | Beat 3 ("Meet the Product") reworded to describe the authored-team experience. Review all six beats for drift against the glossary. |

### Phase 2 — Signup-surface UX (pragmatic implementation, 2026-04-17)

The literal ADR text proposed "zero Agent rows inserted at signup." Implementation audit revealed this would require a pipeline refactor — `task_pipeline.py` resolves Specialists via `agents` table lookups by `role`, so removing the rows would break dispatch. The pragmatic implementation preserves the DB-level scaffolding (infrastructure remains dispatchable) while delivering the authored-team UX at the API/frontend layer via the existing `origin` field.

| File | Change |
|------|--------|
| `api/routes/agents.py` `list_agents()` | Added `.neq("origin", "system_bootstrap")` filter. User-facing list now excludes all scaffolded infrastructure (YARNNN, Specialists, Platform Bots). User-authored Agents (`origin='user_configured'` or `'coordinator_created'`) are the only entries. |
| `web/components/agents/AgentRosterSurface.tsx` | Empty state rewritten as the canonical first-run surface. Headline: "Your team starts here." CTA: "Talk to YARNNN." Ratifies the authored-team thesis at the surface. |
| `api/services/workspace_init.py` | **No change.** Continues scaffolding YARNNN + 6 Specialists + 3 Platform Bots at signup. These rows are infrastructure, required for pipeline dispatch. The UX treats them as invisible (backend filter). |
| `api/services/agent_framework.py` | **No change to DEFAULT_ROSTER.** The six Specialist templates, TP template, and Platform Bot templates remain as signup scaffolding. Their *semantic* role is now "YARNNN's palette + infrastructure," enforced by the `origin` filter rather than by DB absence. |
| Migration | No DB migration needed. Existing workspaces' scaffolded agents have `origin='system_bootstrap'` and are now invisible on `/agents`. Any user-authored Agents (origin `user_configured`/`coordinator_created`) continue to appear. |

**Why this is preferable to the literal ADR text:**

1. **Pipeline safety.** `task_pipeline.py` lines 1956–1959 and 2669–2670 resolve agents by `slug` OR `role` via `agents` table queries. Removing infrastructure rows would break this dispatch without a broader refactor.
2. **Back-office task integrity.** YARNNN owns `back-office-agent-hygiene` and `back-office-workspace-cleanup`. The DB row is the task's agent owner — removing it breaks ADR-164.
3. **Platform Bot lifecycle.** Platform Bots are "activated on connection" per ADR-158/183/187. The activation pattern assumes the row exists at signup (paused state). Preserved.
4. **Zero risk of data migration.** Existing test workspaces' infrastructure rows continue to work exactly as before. The only change is what renders on `/agents`.

The authored-team thesis is fully delivered:
- User sees zero Agents on `/agents` at signup.
- User creates Agents by chatting with YARNNN (via `ManageAgent`, which writes `origin='user_configured'`).
- Authorship moat compounds from first user-created Agent.
- Infrastructure is invisible.

**Deferred from Phase 2:**
- `agents.title = 'Thinking Partner'` → user-visible label. Deferred to a future UX polish commit. Frontend display mapping in `web/lib/agent-identity.ts` can surface "YARNNN" without touching the DB title or slug (`thinking-partner` is preserved by glossary exception).
- Workspace path migration (`/agents/thinking-partner/` → `/agents/yarnnn/`). Not needed — the slug is derived from title, and the title change is deferred.

### Phase 3 — Rename pass (code, mechanical)

User-facing "TP" and "Thinking Partner" are retired. Internal DB slug `thinking_partner` persists (exception per glossary).

| Rename | From → To |
|--------|-----------|
| Python class | `ThinkingPartner` → `Yarnnn` |
| File | `api/agents/thinking_partner.py` → `api/agents/yarnnn.py` |
| Directory | `api/agents/tp_prompts/` → `api/agents/yarnnn_prompts/` |
| Architecture doc | `docs/architecture/TP-DESIGN-PRINCIPLES.md` → `YARNNN-DESIGN-PRINCIPLES.md` |
| Prompt text | Every occurrence of "TP" / "Thinking Partner" in active prompts → "YARNNN" |
| Surface strings | Every user-facing "TP" or "Thinking Partner" → "YARNNN" |

The rename pass is a single commit (singular implementation discipline — no staged rollout). The `thinking_partner` DB role slug is untouched.

### Phase 4 — Glossary enforcement sweep

Grep all active docs, prompts, and code comments for retired terms (TP, Thinking Partner user-facing, Roster, Hire, Compose-a-team, Author-an-agent, Craft). Replace or retire every occurrence. Confirm zero retired-term hits in active paths before closing the phase.

Scope: `api/agents/tp_prompts/` (now `yarnnn_prompts/`), `api/services/commands.py`, `api/services/agent_creation.py`, `docs/architecture/`, `docs/adr/` (only ADRs from 189 onward — historical ADRs are exempt per glossary), `docs/design/`, `docs/features/`, `CLAUDE.md`, `web/` surface strings.

### Phase 5 — ADR archival pass

After Phases 1–4 land, superseded ADRs that now have zero live implementation hooks are archived to `docs/adr/archive/`. Candidates:

- **ADR-140** (Agent Workforce Model — ICP roster): Already fully superseded by ADR-176 + ADR-189. Archive.
- **ADR-175** (Generic Roster Model — never implemented): Archive with note.
- **ADR-176 Decision 1** (Hospital Principle — fixed roster): The ADR as a whole stands (other decisions — universal specialist roles, two-namespace rule, capability split — remain active). Only Decision 1 is superseded; ADR-176 gets an amendment banner but is not archived.
- **Additional archival candidates** to be identified during the Phase 5 sweep: ADRs whose entire scope has been absorbed by later ADRs and which have no live file references in the codebase.

Archival discipline: moved file gets a banner on Line 1 pointing to the superseding ADR. Original path gets no redirect — the `README.md` index in `docs/adr/` is updated to link to the archive path. This matches the existing pattern for superseded ADRs already in `docs/adr/archive/`.

---

## What doesn't change

- **The execution pipeline** (ADR-141). `task_pipeline.py` reads TASK.md at runtime. Unchanged.
- **The primitive matrix** (ADR-168). ManageAgent, ManageTask, WriteFile, etc. — no signature changes.
- **Task schema and data model** (ADR-138). `tasks` table, TASK.md format, `mode` and `output_kind` fields — unchanged.
- **Context domain structure** (ADR-151, ADR-176 Decision 5). `/workspace/context/{domain}/` created on demand, unchanged.
- **Back-office tasks** (ADR-164). YARNNN (formerly TP) still owns `back-office-agent-hygiene` and `back-office-workspace-cleanup`. The agent identity for the executor is renamed but the task mechanics are unchanged.
- **Platform Bot lifecycle** (ADR-158, ADR-183, ADR-187). Bots activate on connection, own temporal context directories. Unchanged.
- **Feedback distillation mechanics** (ADR-117). The *mechanism* is unchanged; the *framing* shifts — role-keyed distillation is now explicitly "Specialist memory" (stylistic), domain-scoped accumulation is now explicitly "Agent identity" (domain expertise).
- **The DB role slug `thinking_partner`.** Retained per glossary exception.
- **ADR-176 Decisions 2–5.** Universal specialist roles, work-first onboarding entry points, capability split (accumulation vs. production), workspace directory model — all remain in force.

---

## Consequences

### Positive

- **Authorship moat compounds from Day 1.** The user's first Agent is theirs. Switching cost begins immediately, before revenue trajectory exists as a quality signal.
- **Three ICP audit leaks dissolve.** With no signup-scaffolded identity layer, there is no surface for ICP-biased pre-scaffolding to leak through. The registry becomes a pure template library (completing ADR-188's arc).
- **Cognitive model simplifies.** One word per concept. Three layers with distinct scopes. No more "Agent" ambiguity across TP vs specialist vs authored worker.
- **Positioning aligns with ICP reality.** Content product operators are creators. "Authored team" matches their mental model; "team for hire" did not.
- **Follow-on ADRs become easier to write.** Glossary discipline eliminates a standing class of terminology drift that has recurred across ADRs 117, 140, 164, 176, 186, 188.

### Costs

- **`/agents` empty-state UX must be genuinely good.** The zero-Agent first-run is now the default, not an edge case. If the chat-to-create flow is slow or confusing, the product appears empty rather than empty-but-inviting.
- **Positioning rewrite has marketing surface area.** ESSENCE, NARRATIVE, and at least two surface strings per page change. Not trivial.
- **Rename commit touches many files.** Phase 3 is mechanically simple but wide — high coordination cost, low per-file complexity. Single commit discipline (no staged rollout) mitigates drift but concentrates risk.
- **Historical ADRs retain retired terms.** A new reader of ADRs 140–188 will see "TP" and "Thinking Partner" and must understand these map to YARNNN. Glossary's Exceptions table covers this, but it's additional cognitive load for archive readers.

### Deferred

- **Revenue-as-moat scope edit** (audit leak 4). Scoping Axiom 4's "Revenue as Moat Proof" section to ICP-specific users is a separate documentation commit, not in this ADR's scope.
- **Multi-user workspace naming.** When workspaces become shared (teams), the authorship claim ("these Agents are mine") becomes "these Agents are ours." Glossary terms are workspace-scoped as written and should survive the transition, but explicit multi-user vocabulary is a future ADR.
- **`/agents/yarnnn/` vs. `/workspace/yarnnn/` location.** YARNNN (the super-agent) has identity files and memory. Whether those live under `/agents/` (which is now "user-created workers only") or under `/workspace/` (meta-cognitive identity) is an implementation question for Phase 2. Not resolved in this ADR. Current direction: `/agents/thinking-partner/` persists at the filesystem layer by the glossary exception principle (matches DB slug).
- **ADR-164 TP class taxonomy.** ADR-164 added `meta-cognitive` as a class in Python AGENT_TEMPLATES. That class label survives this ADR — YARNNN is still `meta-cognitive`. Class system itself is unchanged.

---

## Resolved discretionary calls (2026-04-17)

1. **Product promise one-liner.** Primary: *"Describe your work. Create the agents that do it."* Secondary short form: *"Your work, your agents."* The third earlier candidate ("The agent team you build by chatting") is dropped as too close to adjacent-category copy. GLOSSARY.md updated accordingly.
2. **Empty-state framing.** Zero-Agent first-run is the default, not an edge case. Phase 2 implementation treats the empty `/agents` page as the canonical first-run surface. No soft fallback — a singular-implementation discipline choice. If UX signal indicates the empty state underperforms, the response is to improve the conversational onboarding in chat, not to reintroduce a scaffolded roster.

## Open questions

1. **Does the Specialist palette ever surface to users?** Proposed default: no. Specialists are pure infrastructure, never user-addressed. But there may be a case for making them visible as read-only "what YARNNN can do for you" reference — for transparency, not configuration. This ADR defaults to "no" and leaves the question open for a future UX ADR if need emerges.
2. **How does an Agent's role change over time?** An Agent created to track competitors might, over time, also need to produce weekly briefs. Today this is solved by assigning multiple tasks with different Specialist teams. Whether an Agent's *identity* ever gains direct Specialist capabilities (blurring the three-layer split) is a deeper product question worth surfacing before it surprises us.
3. **How does the authored-team framing interact with shared workspaces (multi-user)?** "I authored this Agent" becomes "we authored this Agent." Ownership attribution gets fuzzier. Likely fine, but worth explicit treatment in the multi-user ADR.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-17 | v1 — Initial proposal. Three-layer cognition ratified. GLOSSARY.md ratified. Supersedes ADR-140 in full and ADR-176 Decision 1. Five-phase implementation plan including ADR archival pass. |
