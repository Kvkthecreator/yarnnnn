# ADR-198: The Cockpit — Operator-Centric Service Model + Surface Archetypes

> **Status**: Proposed — canonizes service-model pivot + archetype vocabulary; implementation phased via ADRs 199–202
> **Date**: 2026-04-20 (v2 unifies two parallel v1 drafts — cockpit service-model pivot + five archetype patterns — into one canonical document)
> **Authors**: KVK, Claude
> **Extends**: FOUNDATIONS v6.0 (Axiom 0 dimensional model, Axiom 2 four cognitive layers, Axiom 3 Purpose, Axiom 6 Channel, Axiom 8 money-truth, Derived Principle 12 Channel legibility gates autonomy)
> **Supersedes**: ADR-163 (four-surface nav Chat/Work/Agents/Context); ADR-180 (Work/Context split — nav intent preserved, surface rewritten); ADR-195 v2 Phase 4 as originally drafted (daily-update absorbs-performance — rejected as dimensional conflation); ADR-194 v2 frontend hints (absorbed here); ADR-193 Phase 5 operational-pane deferral (concretely specified here)
> **Depended on by**: ADR-199 (Overview surface), ADR-200 (Review surface), ADR-201 (Work consolidation + ambient YARNNN rail), ADR-202 (external-Channel discipline); alpha onboarding (operators land on a legible cockpit from Day 1)

---

## Context

### The service-model question this ADR resolves

After FOUNDATIONS v6.0 landed the six-dimensional model, one question remained open for the front end: **what is YARNNN to the operator — a report factory or a cockpit?**

- **Report factory:** YARNNN produces deliverables (briefs, digests, reports) that the operator consumes *elsewhere* — in their email inbox, in Slack, in a PDF. The operator's workflow is: get the report, act on it, manage their business in other tools. YARNNN is a **document production system** with scheduled delivery.
- **Cockpit:** YARNNN is where the operator operates. The operator works *inside* YARNNN — reviews performance, decides on proposals, authors and supervises the team, inspects context. External distribution (email to stakeholders, Slack posts, PDF exports) is a **derivative Channel**, not the primary one. YARNNN is a **work-operation system** that can also produce documents when external parties need them.

The report-factory framing is the residue of document-first thinking — treat the agent as a drafter, the operator as a reviewer-of-documents, the output as a static artifact to ship. The cockpit framing commits to the operator as an *operator*, and the agents as the workforce they operate.

### Why the cockpit framing is service-model, not just UX

The distinction changes what we build and what we measure:

- **What we build.** Under report-factory, `produces_deliverable` task types output HTML → render → email-attach → ship. Operator consumption is off-system. Under cockpit, `produces_deliverable` composes an **operator-consumable surface inside YARNNN**; external distribution is a post-step, not the primary output shape.
- **What we measure.** Under report-factory, success = "did the email arrive, did the PDF render correctly." Under cockpit, success = "does the operator operate inside YARNNN daily, does accumulated context make their work noticeably better."
- **What we promise.** Under report-factory, the promise is "autonomous agents produce your work." Under cockpit, the promise is "your workforce runs here; you operate it." The second is defensible against the LLM providers in a way the first is not — because cockpit compounds (accumulated context + operational history + Reviewer decisions + performance reconciliation) while report-factory competes on document quality, which foundation models are rapidly commoditizing.

### Axiomatic grounding

The cockpit commitment derives from four axioms of FOUNDATIONS v6.0:

1. **Axiom 2 (Identity).** The operator is a distinct cognitive consumer with its own scope. Treating the operator as "someone who reads documents" undervalues their scope — they are the workforce's supervisor, not a document consumer.
2. **Axiom 3 (Purpose).** Navigation and surface design answer *why* the operator is here, not *what substrate* they're browsing. Organizing the front end by Substrate (Files/Agents/Tasks) is a category error — substrates are engineer mental models; operators come with Purposes.
3. **Axiom 6 (Channel).** Channels target consumers. The operator's Channel is "surfaces inside YARNNN." External consumers (CFO reading the weekly report, Slack channel receiving the digest) have their own Channels — those are derivative, not primary.
4. **Derived Principle 12 (Channel legibility gates autonomy).** An operator who can't *see* the workforce's state inside YARNNN cannot trust autonomous writes. Cockpit is the structural precondition for trusted autonomy.

### Stress test (six scenarios)

Before canonizing, the cockpit framing was stress-tested against six real operator scenarios. All six passed; three refinements emerged and are merged into §1 of this ADR below:

1. **Day trader pre-market** — cockpit wins over email-first framing decisively.
2. **E-commerce churn alert** — cockpit eliminates context-switching across email→chat→filesystem.
3. **Operator reads competitor knowledge** — no change; already cockpit-compliant.
4. **Weekly report to external CFO** — cockpit holds *if* external distribution is explicitly a derivative Channel (Refinement 1).
5. **Mobile trade alert** — cockpit holds *if* push/SMS/email are pointer-Channels, not replacement UX (Refinement 2).
6. **Alpha operator who wants email first** — cockpit holds *if* external emails are **expository pointers** with legible summary + deep-link (Refinement 3; ADR-161 already ratified this pattern).

---

## Decision

### 1. Service model: YARNNN is a cockpit, not a report factory

**The operator works inside YARNNN. External distribution is derivative.**

Three refinements that keep the commitment honest without becoming zealotry:

**Refinement 1 — Cockpit ≠ no external distribution.** External Channels are legitimate (Axiom 6 enumerates External platform + Foreign LLM consumers). They are **derivative outputs** of work the operator reviewed in cockpit, not primary outputs that replace cockpit. ADR-185 (Distribution Derivatives) is load-bearing here — every external distribution is a derivative of an operator-approved cockpit surface.

**Refinement 2 — Pointer-Channels legitimate; replacement-Channels forbidden.** Push notifications, SMS alerts, and email alerts for time-sensitive events (trade proposals, irreversible actions, critical errors) are allowed *if* they point to a cockpit surface. They are NOT allowed to duplicate cockpit's interaction affordances on another medium. Approving a proposal from SMS → rejected; it's replacement. Tapping an SMS link that deep-links into the cockpit's Queue pane where approval happens → allowed.

**Refinement 3 — External emails are expository pointers.** Daily-update email, weekly-report emails, and similar periodic external Channels carry **legible summary content** (numbers, headlines, critical proposals listed) + **deep-link pointers** back to cockpit surfaces. Neither pure-pointer (too thin) nor full-replacement (duplicates cockpit, violates singular implementation). Already ratified by ADR-161 for daily-update; ADR-198 extends the pattern to all external-Channel notifications.

### 2. Nav: Five destinations + ambient YARNNN rail

Operator-native vocabulary. Navigation organizes by Purpose — the operator's *why*, not the engineer's substrate taxonomy.

| Priority | Destination | Route | Purpose (the operator's *why*) | Primary substrate |
|---|---|---|---|---|
| 1 | **Overview** | `/overview` (HOME) | "What's going on? What needs me?" — mission-control home | Temporal (since-last-look) + Performance snapshot + Queue + Reviewer alerts |
| 2 | **Team** | `/team` | "Let me check on my agents." — roster + identity + supervision | `/agents/*` — the workforce identity surface |
| 3 | **Work** | `/work` | "Let me check the work." — tasks, schedules, what's producing | `/tasks/*` — the work-definition surface |
| 4 | **Context** | `/context` | "What does my workspace know?" — filesystem + domains + uploads | `/workspace/context/*` + `/workspace/uploads/*` — power-user surface |
| 5 | **Review** | `/review` | "Who decided what, why? Was it right?" — the judgment trail | `/workspace/review/*` + task `feedback.md` + Reviewer audit |

**YARNNN (the super-agent) is ambient, not a destination.** A persistent rail is available on every surface; `/chat` is the expanded-focus form of the rail. Chat-as-a-tab dissolves. Operators don't *travel to* YARNNN; YARNNN is *with them*. Surface-aware prompt profiles (ADR-186) flow surface metadata into YARNNN's prompt automatically.

**Why Team and Work are peer destinations** (not collapsed into one): agents and tasks are many-to-many (one agent runs several tasks; one complex task may involve several agents). "Let me check on my agents" and "let me check the work" are two different operator mental models — browse-by-identity vs browse-by-activity. Collapsing them forced awkward sub-modes (agent-centric / task-centric / context-centric views of one destination). Separating them respects the two Purposes. Cross-links are light: agent detail shows the agent's tasks (link); task detail shows the assigned agent (link). Substrate is already relational.

**Why these names** (not SaaS-dashboard vocabulary): each word is something an operator says naturally. "Let me check the Overview." "Open Team." "Check the Work." "Look in Context." "See the Review log." Every label survives the sentence test without coaching. SaaS-dashboard drift (Mission Control / Ledger / Chronicle / Workshop) was considered and rejected — those read as named product features rather than natural operator destinations. NARRATIVE v4.1's vocabulary rules (retire "dashboard" as reporting-view noun) stay enforced.

**Nav migration is lean.** Route names `/team`, `/work`, `/context`, `/review` either exist today or closely resemble existing routes (`/agents` → `/team`; `/work` unchanged; `/context` unchanged; `/review` new). `/overview` replaces `/chat`-as-home. `/chat` becomes the expanded form of the ambient rail.

### 3. Archetype patterns inside destinations

Each destination hosts one or more **archetype patterns** — characteristic read/interaction shapes that recur across destinations. The archetypes are the Channel-dimension vocabulary (Axiom 6) for classifying what a given pane or view is *doing*. They are not nav entries; they are patterns destinations compose.

| # | Archetype | Substrate read | Purpose | Reading shape |
|---|---|---|---|---|
| 1 | **Document** | A composed output file (`/tasks/{slug}/outputs/{date}/`) | Consume a deliverable | One-shot read, rendered HTML or markdown |
| 2 | **Dashboard** | Live state of a Substrate slice (`/workspace/context/{domain}/`, `_performance_summary.md`, agent roster) | See what the state *is right now* | Continuous; refreshed on every visit |
| 3 | **Queue** | Pending addressed-to-operator items (`action_proposals` rows) | Act on what's awaiting | List of actionable entries with approve/reject/defer affordance |
| 4 | **Briefing** | Curated selection across multiple Substrate files + pointers | Receive periodic summary with deep-links | Periodic push (email); read on demand (Overview home) |
| 5 | **Stream** | Append-only log files (`decisions.md`, `feedback.md`, run logs) | Audit what has happened, chronologically | Append-only, newest at top |

### Archetype invariants

Each archetype carries invariants that keep the dimensional separation clean. These are the cockpit discipline; violations trigger redesign.

**Document invariants.**
- D1: Read-only from the operator's side. Operator edits flow through feedback primitives (per ADR-181), not direct edit.
- D2: One document = one Substrate file (or a manifest addressing a set). No cross-file composition at read time — composition happens in Mechanism (the compose substrate per ADR-170), then the result is a single Substrate artifact.
- D3: Documents have stable URLs. Linking from Briefing points at a Document.

**Dashboard invariants.**
- Dash1: Always a live Substrate slice read. No cached or scheduled snapshot unless the Substrate itself is snapshot-regenerated (e.g., `_performance_summary.md` is regenerated by the daily reconciler; Dashboard is still live-reading the current file).
- Dash2: No action affordances. A dashboard that sprouts "Approve" buttons becomes a Queue — redesign as Queue, or pair with a separate Queue pane.
- Dash3: Grouping/filtering is the surface's job; data shape is Substrate's job.

**Queue invariants.**
- Q1: Every entry has a pending status. Resolved entries leave the Queue.
- Q2: Every entry has action affordances (approve / reject / defer / modify-then-approve). A Queue without actions is a Stream.
- Q3: Resolution writes an audit entry to a Stream archetype (`decisions.md` for review decisions, `feedback.md` for feedback resolution, activity log for others).

**Briefing invariants.**
- B1: Periodic by Trigger (per Axiom 4's periodic sub-shape). Daily cadence default; weekly extensions natural.
- B2: **Composed by selection, not by duplication.** Briefing content is *pointers + headline numbers* from other archetypes, not a re-render of their content. This is the explicit rejection of ADR-195 v2 Phase 4 as originally drafted.
- B3: Briefing has a legible Channel consumer (email for operator outside the app; Overview home for operator inside the app).

**Stream invariants.**
- S1: Append-only to Substrate. Mutations to historical entries are not permitted (edits would be a different archetype — hybrid violating Axiom 6).
- S2: Ordering is chronological. Grouping/filtering is permitted at the surface; reordering the underlying file is not.
- S3: Stream content is always historical — a Stream that shows a projection of the future is mis-archetyped.

### 4. Destination × Archetype mapping

Each destination hosts a characteristic mix of archetypes.

| Destination | Archetypes hosted | Notes |
|---|---|---|
| **Overview** | Briefing (since-last-look + snapshot headlines) + Queue (pending proposals) + Dashboard-snippets (P&L headline, workforce headline — linked, not embedded) | The only destination that composes multiple archetypes as peer panes. All cross-archetype references are links (I2 discipline). |
| **Team** | Dashboard (agent roster grouped by class + health tiles) + Document (agent detail: AGENT.md + memory excerpts) + Stream (per-agent run log + reflections) | Agents-as-identity surface. Supervision actions (pause / resume / archive / edit-via-YARNNN-rail) live here. |
| **Work** | Dashboard (task list filterable by `output_kind` / agent / status / schedule) + Document (task detail — `produces_deliverable` output rendered inline per §6) + Stream (per-task run log + feedback) | Tasks-as-activity surface. Trigger / pause / resume / evaluate / complete actions live here. |
| **Context** | Dashboard (domain entity grid + file browser + uploads) | Pure substrate-browse surface. No Queue (no operator decisions live here); no Briefing (not periodic). Edits flow through YARNNN rail, not inline forms. |
| **Review** | Dashboard (Reviewer IDENTITY + principles) + Stream (decisions log) + Queue-tail (recently-resolved decisions, optional filter) | The Reviewer's surface. Impersonation chrome (ADR-194 v2) lives here when active. |
| Email (external) | Briefing only | Daily-update and weekly-report emails are Briefings per §1 Refinement 3. Never Queue (no approval-via-email), never Document (content is legible summary + deep-link, not the full doc). |

### 5. Design invariants (three surface-level rules)

Three invariants any surface must satisfy. These are the cockpit discipline at the pane/view level.

**I1 — No surface holds state.** Every surface reads files (Axiom 1). Pagination, filtering, sort state lives in URL query params or client state, never in server-side session state. The substrate is authoritative.

**I2 — No surface embeds foreign substrate.** Overview links to Work; it does not embed Work's Document content. Overview links to Review; it does not embed the decisions log. Cross-substrate references are always links, never embeds. This prevents the "briefing absorbs performance" category error (ADR-195 v2 Phase 4 as originally drafted — rejected for this reason).

**I3 — Every surface has exactly one primary cognitive consumer.** If two cognitive layers need the same data, they get two views of it with layer-appropriate framing. The Reviewer's view of `_performance.md` (reasoning substrate, headless) is not the operator's view of `_performance.md` (supervisory dashboard). Same file, two affordances.

### 6. What `produces_deliverable` means under cockpit

Pre-cockpit: `produces_deliverable` = "emit an HTML output, render to file, email-deliver or PDF-export as primary Channel."

Post-cockpit: `produces_deliverable` = **"compose an operator-consumable surface inside YARNNN; external distribution is a derivative."**

Concrete consequences for the compose pipeline:

- **Compose substrate (ADR-170 / ADR-177) remains unchanged** in core function — it still takes filesystem state + task type structure and produces a composed output. What changes is that the composed output is a **Document archetype surface** (live, linked, editable-by-feedback), not a static HTML document staged for email.
- **Task output folder (`/tasks/{slug}/outputs/{date}/`) remains canonical** per Axiom 1. The Document archetype renders *from* the output folder; the output folder IS the persistent artifact.
- **Export-to-PDF/email becomes a derivative step** per ADR-185. When a task's `## Delivery` section names external recipients, a post-compose distribution runs: render PDF, attach to expository Briefing email, deliver. This is not the primary output — it's what ships to external consumers after operator-approval of the cockpit Document surface.
- **Operator feedback on deliverables flows into ADR-181 source-agnostic feedback** at the cockpit Document surface, not at the email. The operator reads in cockpit, edits/comments via YARNNN rail, feedback routes through `UpdateContext(target="task", feedback_target="deliverable")`. Email is for external readers who don't have operator identity.

### 7. Ambient YARNNN rail (design commitment)

YARNNN is present on every surface as a right-rail panel that:
- Expands/collapses via keyboard shortcut or tab-click (collapsed: icon only, ~48px; expanded: conversation, ~400px)
- Carries surface-aware context into YARNNN's prompt (ADR-186 prompt profiles already handle surface metadata)
- Supports quick-asks that don't break operator's surface context
- Deep-links into `/chat` when a conversation wants more room

`/chat` is the **expanded-focus form** of the ambient rail. Same conversation substrate; same session continuity. Not a primary nav destination — operators reach it via the rail's expand action or direct URL. Listed in settings/help, not in top-level nav.

### 8. What this supersedes

- **ADR-163 (four-surface nav Chat/Work/Agents/Context)** — nav replaced by **Overview / Team / Work / Context / Review** + ambient rail. `Chat` as a nav tab dissolves. `Agents` renames to `Team` (NARRATIVE-aligned operator vocabulary). `Work` and `Context` keep their names with clearer Purpose-scoped definitions. `Review` is new. `Overview` replaces `/chat`-as-home.
- **ADR-180 (Work/Context surface split)** — the nav intent (task-scoped vs workspace-scoped) is preserved; the surface organization is rewritten under cockpit framing. Team hosts agents-as-identity; Work hosts tasks-as-activity; Context stays workspace-scoped as the filesystem browser.
- **ADR-195 v2 Phase 4 as originally drafted** — formally rejected. Performance is read via Work's Dashboard archetype (per-task `_performance.md`) and an Overview snapshot tile; daily-update Briefing links to those destinations rather than embedding their content. Phase 4 is rewritten as "Overview snapshot + Briefing pointers" in ADR-199 (Overview surface).
- **ADR-194 v2 frontend hints** — the impersonation chrome, Reviewer identity card, decisions history are all absorbed into the Review destination. ADR-194 stays focused on the cognitive-layer substrate; the surface is ADR-198's domain.
- **ADR-193 Phase 5 operational-pane deferral** — concretely specified as the Queue archetype of Overview.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Capital-Gain Alignment | Notes |
|--------|--------|------------------------|-------|
| **E-commerce** | **Helps** | Yes, directly | Overview shows overnight orders + refund proposals + revenue snapshot. Work hosts agents (Writer for campaigns, Tracker for churn signals) and their tasks. Context shows customers/ and revenue/ domains. Review audits past AI-Reviewer campaign approvals. Cockpit replaces "check Lemon Squeezy dashboard + read YARNNN email + click into each proposal" context-switching. |
| **Day trader** | **Helps** | Yes, directly | Pre-market Overview shows overnight P&L + current positions + pending bracket orders needing approval. Work hosts trading agents. Context shows trading/ domain with per-instrument entities. Review shows AI Reviewer's EV calibration over time. This is THE use case cockpit was designed for. |
| **AI influencer** (scheduled) | Forward-helps | Yes, enabling | Overview surfaces content-performance trends + pending campaign proposals. Work hosts content-production agents. Context shows audience/ and content/ domains. Review for brand-deal decisions. |
| **International trader** (scheduled) | Forward-helps | Yes, enabling | Overview surfaces overnight logistics + compliance alerts. Work hosts trade-ops agents. Context shows counterparty + shipment domains. Review for compliance decisions. |

No domain hurt. No verticalization — cockpit is a structural pattern applicable to every domain. Gate passes.

---

## Implementation sequence

Five phases. Phase 1 is doc-only canonization (this commit cycle). Phases 2–5 are surface implementations.

| # | Phase | Scope | Status |
|---|-------|-------|--------|
| 1 | **Cockpit canonization** | This ADR + doc sweep: ESSENCE v12.3 (cockpit in stable elements); NARRATIVE v4.1 (Beat 3 reframe + vocabulary rules); SERVICE-MODEL v1.6 (cockpit preamble + surface rewrite); design/SURFACE-ARCHITECTURE v15 (cockpit nav). | **This commit cycle** |
| 2 | **ADR-199 — Overview surface** | `/overview` route. Since-last-look (Briefing) + snapshot headlines (Dashboard tiles) + pending proposals (Queue) + Reviewer alerts. Absorbs prior `/chat`-as-home behavior. Empty-state matches ADR-161 heartbeat discipline. | Proposed |
| 3 | **ADR-200 — Review surface** | `/review` route. Reviewer identity + principles (Dashboard) + decisions log (Stream) + impersonation chrome when active (ADR-194 Phase 2b). Unblocks Principle 12 for Reviewer layer. | Proposed |
| 4 | **ADR-201 — Team + Work separation + ambient YARNNN rail** | Rename `/agents` → `/team` (agents-as-identity surface). Keep `/work` (tasks-as-activity surface). Cross-link agent↔task detail routes. Implement ambient YARNNN rail on all surfaces. Deprecate `/chat` as primary nav destination (keep route as expanded form). | Proposed |
| 5 | **ADR-202 — External Channel discipline** | Daily-update Briefing template stripped of embedded performance per §1 Refinement 3. Alert notifications (push/SMS) specified as pointer-only per Refinement 2. `produces_deliverable` task external distribution stepped to derivative per §6. | Proposed |

---

## What this ADR does not change

- **Axiom 1 (filesystem substrate).** Every cockpit surface reads files. Surface design does not require new substrate.
- **ADR-141 execution pipeline.** Tasks still execute the same way; compose substrate still produces output folders. What changes is how operators *consume* those outputs — cockpit surface primary, external derivative.
- **The primitive matrix.** No new primitives. Cockpit is a Channel-dimension design, not a Mechanism extension.
- **The agent framework (ADR-176 universal roster + ADR-189 four layers + ADR-194 v2 Reviewer).** Cockpit is what the operator sees; the workforce shape underneath is unchanged.
- **ADR-185 Distribution Derivatives.** Cockpit ratifies ADR-185's framing. Derivatives are legitimate; they were always intended as post-primary. ADR-198 tightens the "what is primary" answer.

---

## Open questions

1. **Mobile app vs responsive web.** Cockpit-on-mobile matters for the day-trader use case. Does this push us toward a native mobile app (push-notification affordance + cockpit rendering) or is responsive web + PWA sufficient? Defer to ADR-199.

2. **Multi-tab operator workflow.** If an operator opens Work in one tab and Review in another, which is "primary"? Likely neither — cockpit destinations are peer, not hierarchical. But the ambient YARNNN rail's state (did I ask YARNNN something in tab 1?) is shared across tabs. Mechanics TBD.

3. **`/chat` as destination vs purely expanded form.** Some users will search for "chat" in the nav. A soft-redirect from `/chat` to the ambient rail (plus keeping `/chat` as the expanded route) is probably right. Needs UX test.

4. **Day-zero cockpit empty states.** Operator who just signed up has no `_performance.md`, zero proposals, zero decisions. What does Overview look like? Probably: "Your workforce is here. Connect a platform or describe your work to activate it." + pointers to Work. Similar to ADR-161's daily-update empty state pattern.

5. **Does the Reviewer ever see cockpit?** Human Reviewer = operator, filling the seat = yes, cockpit. AI Reviewer = invoked headlessly, reads substrate directly, no cockpit. Impersonation Reviewer = admin sees persona's cockpit with impersonation chrome. All three resolved; no new question.

6. **Sixth archetype at scale.** Current five archetypes (Document / Dashboard / Queue / Briefing / Stream) are exhaustive for present scope. If operators with high alert volume emerge and Queue's approve/reject/defer affordance doesn't map (e.g., "acknowledge only" alerts), a sixth archetype may be warranted. Defer until observed.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-20 | v1a (parallel draft) — Five archetype patterns (Document / Dashboard / Queue / Briefing / Stream) canonized as Channel-dimension cells. Nav preserved per ADR-180. |
| 2026-04-20 | v1b (parallel draft) — Cockpit service-model pivot proposed. Nav rewritten to Overview / Workshop / Ledger / Chronicle + ambient YARNNN rail. |
| 2026-04-20 | **v2 (this file) — Unified.** Cockpit service-model pivot is the primary commitment; archetype patterns are absorbed as the Channel-vocabulary-within-destinations. Final nav: **Overview / Team / Work / Context / Review** + ambient YARNNN rail (SaaS-dashboard vocabulary of v1b's "Workshop / Ledger / Chronicle" rejected in favor of operator-native words). Team and Work are peer destinations — agents-as-identity and tasks-as-activity are two distinct operator Purposes, collapsing them would force awkward sub-modes. Merges both v1 drafts; singular-implementation discipline. v1a file (`ADR-198-surface-archetypes-from-first-principles.md`) deleted; this filename (`ADR-198-surface-archetypes.md`) is canonical. |
