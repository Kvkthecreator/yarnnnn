# ADR-378 — The Workspace is the Outermost Unit (the Scope Ceiling), and the Single-Filesystem Model Beneath It

> **Status**: **Accepted** (2026-06-27). Doc-first; **scope-defining, not code-changing** — this ADR ratifies a *boundary* and records the *first-principles model* that makes the boundary coherent. It migrates no substrate and ships no migration. The downstream refactor that *implements* the single-filesystem model (collapsing `inbound/` + the kernel-class roots into meaning-folders + metadata) is named as its own future ADR (§7), not done here.
> **Date**: 2026-06-27
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: [`docs/analysis/the-workspace-as-outermost-unit-and-the-single-filesystem-model-2026-06-27.md`](../analysis/the-workspace-as-outermost-unit-and-the-single-filesystem-model-2026-06-27.md) — the four-step chain (recheck intake → single-filesystem first principle → agents-as-attribution → stress test → the ceiling), with substrate receipts. **The operator ratified that the rationale chain is as load-bearing as the decision** — §3 below is therefore the rationale in full, not a summary.
> **Completes**: [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) — ADR-373 established the workspace as the substrate's *binding unit* (`user_id → workspace_id`) but stopped *at* the boundary without naming that the boundary **is** the ceiling. This ADR names it: the workspace is not just the binding unit, it is the **outermost unit YARNNN composes**. Federation is the deliberately-unbuilt layer above it.
> **Preserves**: ADR-373 (multi-principal commons — the *inside* of the ceiling), [ADR-209](ADR-209-authored-substrate.md) (the ledger that makes single-filesystem provenance work), [ADR-286](ADR-286-single-writer-per-path.md) + [ADR-320](ADR-320-constitution-region-topological-cut.md) (untouched here — the §7 refactor will revisit them, this ADR does not), [ADR-376](ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) (the intake invariant — its *mechanism* — `inbound/` — is what the §7 refactor reconsiders, but `retain + attribute + cite` is preserved regardless), [ADR-194](ADR-194-the-reviewer-judgment-seat.md)/[ADR-315](ADR-315-occupant-carve.md) (the steward seat — one per workspace, which is *why* the ceiling lands at the workspace).
> **Relationship to Phase 2**: the [Freddie + user-persona analysis](../analysis/phase-2-internal-agents-freddie-and-user-personas-2026-06-26.md) is the actor taxonomy this ceiling sits under — Freddie (one home), user persona agents (one home each), external agents (no home, pure attribution). All three are *inside* one workspace; none crosses the ceiling.
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 — what the substrate's outermost composition unit IS) + **Identity** (Axiom 2 — the workspace as the commons an open set of principals share, bounded).

---

## 1. The decision in one sentence

**The workspace is the outermost unit YARNNN composes: one workspace is one attributed, multi-principal commons (one filesystem, N principals — humans, agents, platforms, foreign/local LLMs — each attributed as itself); an enterprise is served if and only if it fits into one such commons; a second workspace is allowed but has *no relationship* to the first — cross-workspace reads, a shared steward, and any org-of-workspaces hierarchy are explicitly *undefined*, the deliberately-unbuilt layer above this ceiling.**

This is a **positive boundary, not a headcount cap.** It is framed as *"the
workspace is the unit; federation is undefined,"* **not** *"one enterprise max"* —
the latter borrows an org noun the kernel never models and reads as a limitation;
the former is a definition, and a definition is a strength.

## 2. Why naming the ceiling makes the boundary *stronger*

A boundary you have not named is a boundary you might accidentally erode. By
stating that the workspace is the outermost unit:

- **Every "what about scale?" question has a settled answer.** More principals,
  nested agents, physical AI, on-prem storage, more platform inflow — all *inside*
  the ceiling, all absorbed by the model (§3.4). Multiple *related* workspaces —
  *above* the ceiling, out of scope, by design. The model never has to
  half-answer a federation question it was not built for.
- **The inside is rich, so the edge is meaningful.** A workspace is not a thin
  per-user bucket; it is a *complete multi-principal commons* (ADR-373). "The
  workspace is the outermost unit" is a strong claim *because* the inside is
  strong — see §3.
- **It scopes enterprise honestly.** YARNNN can house an enterprise that operates
  as one commons (one shared substrate, one steward, many human + agent + platform
  principals). It cannot — and does not pretend to — federate divisions. Saying so
  is more credible than implying federation we have not built.

## 3. The rationale (the load-bearing chain — ratified as canon, not preamble)

The ceiling is coherent *only because of what a workspace was shown to be*. The
four-step discourse that established it:

### 3.1 The intake two-step is sound but mis-housed (the trigger)

The ledger-intake axiom (ADR-376/DP32, `retain + attribute + cite`) is correct as
data-handling. But its *mechanism* — a visible `inbound/` raw lane separate from
the derived `operation/` home — encodes a **kernel concern (raw-vs-derived
provenance) as a visible directory**. Its sole consumer is `trace`, and `trace`
needs the **revision chain** (ADR-209), which already exists for every path — not
a raw *lane*. The two-lane design solves *in the namespace* a problem already
solved *in the history*. (Live receipt: even an `inbound/` raw accretes revisions
— `database-decision.md` had 3 — so it is *already* a revision chain; the second
lane is redundant with the history layer.)

### 3.2 The first principle: one filesystem, one ledger, kernel-concerns-as-metadata

> **The filesystem is organized by what things *mean to the operator*. A file's
> content is the workspace's current understanding; its full attributed history is
> always available. Raw-vs-derived is a property of *revisions* (an `observation`
> revision vs. a `derivation` revision on the same file), not of *paths*.
> Everything the kernel needs — permission, provenance, citation, evidence — is
> *metadata on files and revisions*, never *structure imposed on the namespace*.
> The user's `ls` reflects their work, not our architecture.**

The two-lane model drifted in from one assumption — that contributor and deriver
can't write one file because single-writer-per-path (ADR-286) forbids it. But the
revision chain *already serializes writes*; the right relaxation is **single
current-state, many-attributed-revisions**, under which the raw and its derivation
are two revisions of one file and the raw lane is unnecessary. The *same* fix
dissolves the **larger** offender: the six kernel-class roots (`governance/`,
`constitution/`, `persona/`, `operation/`, `contract/`, `system/`) exist because
ADR-320 made *the directory determine who may write it* — **permission encoded as
namespace**. Unix puts owner+mode *on the file*, not in a `/root-only/` directory.
Both `inbound/` (provenance-as-directory) and the six roots
(permission-as-directory) are the same category error at two scales; both collapse
under the one principle. (This ADR *states* the principle as rationale; the
refactor that *applies* it is §7, downstream.)

### 3.3 Agents are attribution identities, not subtrees

Two laws follow:

- **Law 1 (Namespace = meaning).** Top-level entries are either *work*
  (meaning-folders, shared by all principals, attributed) or *principal homes*
  (one per internal standing entity, **identity-only**). Kernel concerns are
  metadata.
- **Law 2 (Identity = attribution).** Every actor is a `class:id` on revisions.
  *Internal* standing actors additionally get a home; *external* actors get only
  attribution; *non-actors* (platform drivers, config) get neither.

The decisive cut is **what an agent *produces* (work — shared meaning-folders,
attributed) vs. what an agent *is* (its persona/standing-intent/trail — a small
identity-home).** Mapping the Phase-2 actor taxonomy:

| Actor | Home? | Footprint |
|---|---|---|
| **External agent** (ChatGPT, a customer's coding agent, a local/physical model reaching in) | **No home** — pure attribution; reasons from its *own* intent. | Attributed revisions in the meaning-folders. |
| **Freddie** (the one systemic fiduciary; the renamed steward) | **One home** | Its judgment *output* — incl. multi-principal reconciliations — is attributed *work* in the meaning-folders, **not** in its home. |
| **User persona agents** (operator-authored labor) | **One home each** | Output scatters across meaning-folders, attributed. |

The **internal/external line *is* the has-a-home line** — and (the sharpening
from the stress test) it is a *substrate-residency-of-intent* line, not a network
line: the same physical agent is *internal if it reasons from workspace-resident
standing intent, external if it brings its own*. Adding a principal is therefore
additive (`mkdir agents/{slug}` + a new attribution identity); nothing
restructures. The trap to hold against: a persona agent's home must never become a
dumping ground for its *work* (`agents/researcher/findings/` recreates the
`inbound/` mistake one level down).

### 3.4 The stress test: holds in every direction but one

The model breaks only if a scenario forces a *third* top-level kind or an actor
Law 2 can't class. (Receipt: today's ledger `authored_by` classes are
`system`/`reviewer`/`operator`/`operator-proxy`/`yarnnn`/`agent`/`dispatcher` — no
`platform:` yet; platform-as-principal is a real *implementation* gap, §7, not a
model gap.)

- **Slack/Notion**: the *connection* is a driver/config (off-desktop,
  `platform_connections` row, ADR-335 peripheral); its *inflow* is work
  (meaning-folder, attributed `platform:slack`). **Holds (with a split).**
- **Physical AI / local LLM**: an external principal; substrate is transport-blind.
  **Holds for free.**
- **Nested agent stacks**: nesting → depth in `authored_by` (a delegation chain)
  + **delegable grants** (the `principal_grants` authorization layer) — **never**
  depth in the namespace. The filesystem stays flat; the *authorization graph*
  gets depth. **Holds.**
- **On-prem / local substrate**: a storage-backend question, not a model question
  (`write_revision()` is the seam). **Holds.**
- **Enterprise multi-workspace**: **SILENT.** The model is the *node*;
  inter-workspace federation is a layer *above* it that canon has not built. This
  is the ceiling.
- **Hybrid external+briefed agent**: **Holds, sharpens** the internal/external
  line (residency-of-intent, not network).
- **Volume (10M revisions)**: **conceptually holds**; the ledger needs an archival
  story (§7).

**The one boundary the model does not cross is the workspace itself** — and that
is the ceiling this ADR ratifies.

## 4. What is IN scope vs OUT of scope (the operational boundary)

| Case | Verdict |
|---|---|
| 1 workspace, 1 human, 0 agents | ✅ in scope (the N=1 case — today) |
| 1 workspace, N humans + M agents + K platforms (one commons) | ✅ in scope (ADR-373 multi-principal) |
| 1 enterprise operating as one commons (one shared substrate + one steward) | ✅ in scope — *this is how YARNNN serves an enterprise* |
| 1 enterprise wanting 2+ *related* workspaces (cross-division reads, shared Freddie, org hierarchy) | ❌ out of scope — federation **undefined** |
| 1 account that creates a 2nd *unrelated* workspace | ✅ allowed — but the two **do not compose** (no relationship, by design) |

**The honest line:** YARNNN does not *forbid* a second workspace; it offers **no
relationship between workspaces.** "No federation," not "no second workspace."

## 5. Why the ceiling lands exactly at the workspace (not above, not below)

- **Below it would be wrong** (per-user): ADR-373 already proved the user is *not*
  the unit — a workspace is a commons of N principals; keying to the user
  re-introduces the single-principal assumption ADR-373 retired.
- **Above it is unbuilt** (federation): nothing in canon defines cross-workspace
  grants, a workspace-of-workspaces, or a steward spanning workspaces. The steward
  seat is *one per workspace* (ADR-194/315) — which is *itself* a reason the
  ceiling is the workspace: there is exactly one accountable fiduciary per commons,
  and "one Freddie across 50 workspaces" is precisely the undefined federation
  case.
- **At the workspace it is complete**: every intra-workspace scenario (§3.4) is
  absorbed; the steward, the grant model, the single filesystem, and the ledger
  are all workspace-scoped already. The ceiling is where the architecture already
  stops — this ADR makes that *intentional* rather than incidental.

## 6. Permanent, or current?

**Intentional for the current product; not declared permanent for all time.** If
enterprise federation becomes a real requirement, the **workspace-of-workspaces**
(or org-as-principal-over-workspaces) is the next first-principles discourse — and
it begins *above* this ceiling, by defining the relationship *between* commons, not
by eroding the definition of one. Marking the ceiling does not foreclose the
future layer; it *names where that layer would attach.* Until then, the boundary
holds and is a strength.

## 7. Explicitly downstream / not decided here

- **The single-filesystem refactor** (collapse `inbound/` + the six kernel-class
  roots into meaning-folders + metadata; relax single-writer-per-path to
  single-current-state-many-revisions; add a `revision_kind` observation/derivation
  flag; move evidence to derivation-attachment). This ADR records the *model* as
  ratified *direction* and *rationale*; the migration is its own ADR and touches
  ADR-286 / ADR-320 / ADR-376. **No substrate is migrated by this ADR.**
- **Platform-as-principal** (`platform:slack` ledger revisions) — the one
  implementation move that makes the intake model (ADR-376) and the actor model
  consistent in code, closing the connector-intake gap and connector-attribution
  gap at once. Highest-leverage single change; not decided here.
- **Ledger archival at volume** — conceptually permitted (history is separable
  from current-state), not yet solved.
- **The federation layer above the ceiling** — named (§6), not designed.

## 8. What this ADR does NOT do

- Does not migrate substrate, add a table, or ship a migration.
- Does not change the gate, the write path (`write_revision()`), the topology lock
  (ADR-320), single-writer (ADR-286), or the intake invariant (ADR-376) — it
  *records the direction* to revisit the first three in a downstream refactor and
  *preserves* the last.
- Does not rename the steward (that is the Phase-2 Freddie ADR) — it only relies on
  the steward being *one per workspace* as a reason the ceiling lands at the
  workspace.
- Does not forbid a second workspace — it declares the two **do not compose**.
