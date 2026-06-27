# Analysis — The Workspace as Outermost Unit, and the Single-Filesystem Model

**Date**: 2026-06-27
**Hat**: B → A (the discourse is developer-surface first-principles re-derivation; the decision it feeds — ADR-378 — is system canon).
**Status**: Discourse record + rationale. The *decision* lives in [ADR-378](../adr/ADR-378-the-workspace-as-the-outermost-unit.md); this doc is the **reasoning chain that produced it**, preserved because the operator (KVK) ratified that *the background and rationale are as load-bearing as the decision itself*.
**Participants**: KVK (operator) + Claude (collaborator).
**Substrate-receipts**: every load-bearing claim below was checked against the live kvk workspace (2026-06-27); receipts inline.

---

## 0. Why this doc exists

This records a four-step discourse (2026-06-27) that started as a recheck of the
ledger-intake model (ADR-376) and escalated, by first-principles pressure, to a
re-derivation of the whole substrate-shape and an explicit **scope ceiling**. The
chain matters because each step constrains the next:

1. **Recheck the capture→derive (two-step) intake model.** Sound as data-handling,
   but it encodes a kernel concern (raw-vs-derived) as a *visible directory*
   (`inbound/`).
2. **Drop to first principles on the filesystem itself.** A single filesystem +
   an attributed ledger is *purer* than the two-lane model — raw-vs-derived is a
   property of **revisions**, not **paths**.
3. **Extend to the agent-expansion direction (Freddie + user persona agents).**
   One filesystem holds N principals; agents are *attribution identities*, not
   subtrees; only *internal standing principals* earn a small identity-home.
4. **Stress-test against scale (platforms, physical AI, nesting, enterprise,
   on-prem, volume).** The model holds in every direction except one — spanning
   *multiple* workspaces — and naming that as the deliberate ceiling makes the
   boundary a **strength**.

The decision (step 4's ceiling) is ADR-378. Steps 1–3 are the rationale that
makes the ceiling *coherent* rather than arbitrary — they establish *what a
workspace IS* (one commons, one filesystem, N attributed principals), which is
*why* "the workspace is the outermost unit" is a positive definition and not a
headcount cap.

---

## 1. Step 1 — the two-step intake model is sound but mis-housed

The ledger-intake axiom (ADR-376/DP32) is `retain + attribute + cite`: a
contribution enters as an attributed raw observation; understanding is a separate
attributed derived act citing the raw; the raw is never rewritten. Verified live
(2026-06-27): two clean derive-and-cite cases on kvk
(`operation/yarnnn-ux-philosophy.md` cites `inbound/mcp/chatgpt/…`; the
perception `_watch_signal.yaml` block-list cites two `inbound/web/…` raws);
single-writer holds (zero `inbound/` paths with two authors).

**The finding that escalated it:** the *entire* `inbound/` two-lane apparatus
serves exactly one consumer — `trace` (the moat headline: *which principal
contributed each version, how the seat reconciled them*). And that consumer does
**not** need a raw *lane*; it needs the **revision chain**, which ADR-209 already
built for every path. The `inbound/` directory solves *in the namespace* (a
second visible tree) a problem already solved *in the history* (the
`workspace_file_versions` table). That is a **category error**: encoding a kernel
concern (raw-vs-derived provenance) as a *path* instead of as *metadata on a
revision*.

Receipt that sharpened it: `inbound/mcp/claude/database-decision.md` had **3
revisions** — three `remember(about="database decision")` calls appending an
evolving decision (DynamoDB → reconsidering → "Postgres, Final"). So even the raw
lane is *append-only ledger grammar*, not a frozen file. "Immutable" already
means "never destructively rewritten," i.e. *it is already a revision chain* —
which is the clue that the second lane is redundant with the history layer.

---

## 2. Step 2 — the first principle: one filesystem, two stores, raw-vs-derived is a property of revisions

YARNNN already has two stores, and only one is "the filesystem":

- `workspace_files` — **current state** (what `ls`/`read` returns; the desktop).
- `workspace_file_versions` — **history** (append-only, attributed,
  parent-pointered; ADR-209; the ledger).

The first principle the discourse landed:

> **There is one filesystem. A file's content is the workspace's current
> understanding of something. Its full attributed history is always available.
> Some revisions are *observations* (a principal contributed raw); some are
> *derivations* (the workspace made sense of what was contributed). Both are just
> revisions, on the same file, in the one history.**

Under it, the database-decision example is **one file** whose chain reads
`[observation]×3 → [derivation]` — not raw-in-`inbound/` + derived-in-`operation/`.
`trace` reads the chain and marks each revision's kind. The moat (*contributed-by
vs reconciled-by*) is preserved **perfectly** — it lives where it belongs:
`authored_by` + a `revision_kind` flag — and the user/agent doing `ls` sees **one
file in its natural home**, not a two-lane tree. This is *more* faithful to the
git framing ADR-376 reached for: **git has no `inbound/` directory** — it has one
working tree and attributed commits; a raw paste and a careful refactor are both
just commits.

**Why the two-lane design drifted in:** the buried assumption that *contributor
and deriver can't write the same file* because single-writer-per-path (ADR-286)
forbids it — so the *path* was split to preserve single-writer. But the revision
chain already serializes writes; two principals appending attributed revisions to
one file, in order, with the seat's derivation as the latest revision, is **not a
merge conflict — it is a file with a history.** The real first-principle move is
to relax *single-writer-per-path* to **single current-state, many-attributed
revisions**. The moment you do, the raw lane is unnecessary, because the
contributor's raw and the seat's derivation are two revisions of one file.

**The same fix generalizes to the kernel roots — the *larger* offender.** A live
`ls /workspace` on kvk returns **12** top-level entries (`operation`, `system`,
`persona`, `governance`, `constitution`, `contract`, `inbound`, + stray files).
The six semantic-class roots exist because ADR-320 made *the directory determine
who may write it* (`access(2)` by prefix). That is the **same mistake at a larger
scale**: encoding *permission* as a visible namespace. Unix does not make you put
files in `/only-root-can-write/`; it puts owner+mode *on the file*. The unifying
principle:

> **The filesystem is organized by what things *mean to the operator*. Everything
> the kernel needs — who may write (permission), what's raw vs. understood
> (provenance), what evidence backs a judgment (citation) — is *metadata carried
> on files and revisions*, never *structure imposed on the namespace*. The user's
> `ls` reflects their work, not our architecture.**

`inbound/` violates it (provenance-as-directory). The six roots violate it
(permission-as-directory). Both collapse under the one principle into a flat,
meaningful tree with rich invisible metadata.

**What the single-filesystem model must still answer for (honest costs):**
- the raw verbatim is *one revision back*, not a separate visible artifact —
  better for humans, requires `read(path, @revision)` for an agent that wants to
  re-derive (ADR-209 `ReadRevision` covers it);
- "un-derived" becomes *a file whose head revision is still an observation*
  (queryable, not an `ls`-able directory) — which actually *resolves* the
  orphaned-raw ambiguity (deliberately-not-derived vs. not-yet-derived can be a
  real distinction on the revision);
- **evidence** (perception's cited bytes) is an **attachment to a derivation**,
  reachable *through* the judgment via `trace`, **not** a sibling directory —
  keeping ADR-376's genuine insight (don't discard cited bytes) without its
  filesystem cost.

**Net of Step 2:** simplicity is the *default surface*; the moat is a *capability
you invoke* (`trace`), not a *structure you navigate*.

---

## 3. Step 3 — agents are attribution identities, not subtrees; only internal principals earn a home

The Phase-2 vision ([analysis](phase-2-internal-agents-freddie-and-user-personas-2026-06-26.md))
names three agent-actors. The single-filesystem model classes them by **two
laws**:

- **Law 1 (Namespace = meaning).** Top-level entries are either *work*
  (meaning-folders, shared, attributed) or *principal homes* (one per internal
  standing entity, identity-only). Kernel concerns are metadata.
- **Law 2 (Identity = attribution).** Every actor is a `class:id` on revisions.
  Internal actors additionally get a home; external actors get only attribution;
  non-actors (drivers, config) get neither.

The decisive cut: **what an agent *produces* (work — metadata, shared
meaning-folders) vs. what an agent *is* (its persona/standing-intent/trail — a
small identity-home).** The blunt "every agent is a directory" recreates the
`inbound/` mistake one level down (namespace organized by *who produced it*). The
disciplined version: agents share the meaning-folders for output; only internal
standing principals get a home for *what they reason from*.

| Actor | Home? | Footprint |
|---|---|---|
| **External agent** (ChatGPT, a customer's coding agent, a local model reaching in) | **No home** — pure attribution. It reasons from *its own* intent, brought in. | Attributed revisions in the meaning-folders. Zero directory. |
| **Freddie** (the one systemic fiduciary; renamed steward) | **One home** (`freddie/` — was `persona/`) — its persona, standing intent, trail. | Its judgment *output* is attributed *work* in the meaning-folders (incl. multi-principal reconciliations), **not** in its home. |
| **User persona agents** (operator-authored labor) | **One home each** (`agents/{slug}/`) — identity + persona. | Output scatters across meaning-folders, attributed. |

The principals survive as directories because a standing entity with its own
state to reason from is the one thing *not* reducible to metadata — Unix's
`/home/alice` exists because Alice is a principal with persistent state, not
because of permissions. **The internal/external line *is* the has-a-home line.**

**The trap to hold against:** a persona agent's home must never become a dumping
ground for its work (`agents/researcher/findings/`). The Acme research goes in
`/the-acme-deal`, signed by the researcher — the home holds *what the agent is*,
never *what it did*. Hold that line and the model stays clean as agents multiply;
break it and you get N agents × N little filesystems — the fragmentation the
whole model avoids.

**Adding a principal is therefore cheap and additive:** `mkdir agents/{slug}` + a
new attribution identity. No restructure. This is the substrate proof of the
Phase-2 doc's "additive at the attribution layer" claim.

---

## 4. Step 4 — the stress test, and the one boundary the model cannot carry

The model reduces to the two laws. A scenario *breaks* it only if it forces a
*third* kind of top-level entry, or an actor Law 2 cannot class. Results
(receipts: `platform_connections` is credentials+config, not a ledger principal;
the ledger's `authored_by` classes in use today are `system`/`reviewer`/
`operator`/`operator-proxy`/`yarnnn`/`agent`/`dispatcher` — **no `platform:`**,
confirming the connector-attribution gap below):

| Scenario | Verdict | What it forces |
|---|---|---|
| **Slack/Notion connection** | **Holds (with a split)** | The *connection* is a driver/config (off-desktop — a `platform_connections` row, ADR-335 peripheral), **not** work and not a principal. Its *inflow* is work (meaning-folder, attributed `platform:slack`). "House the connection under `/work`" is the blunt version that puts plumbing on the desktop. |
| **Content/context inflow** | **Holds** | Meaning-folder + attribution; never `/work/{platform}/`. |
| **Physical AI / local LLM** | **Holds for free** | Substrate is transport-blind. A robot or on-device model reaching in is an *external principal* — no special case. |
| **Nested agent stacks** | **Holds** | Nesting → depth in `authored_by` (a delegation chain, e.g. `agent:a/b/c`) + **delegable grants** (the `principal_grants` authorization layer), **never** depth in the namespace. The filesystem stays flat; the *authorization graph* gets depth — kept correctly separate. |
| **On-prem / local substrate** | **Holds** | A *storage-backend* question, not a model question. `write_revision()` is the single seam; the model is substrate-location-agnostic (same reason ADR-208's git-backend could be weighed + withdrawn without touching the axioms). |
| **Enterprise multi-workspace** | **SILENT — the real ceiling** | The model is the *node*; inter-workspace federation (org hierarchy, cross-workspace grants, shared Freddie across 50 workspaces) is a layer *above* it that canon has not built. ADR-373 deliberately stopped at the workspace boundary. |
| **Hybrid external+briefed agent** | **Holds (sharpens)** | The same physical agent is *internal if it reasons from workspace-resident standing intent, external if it brings its own* — the internal/external line is a **substrate-residency-of-intent** line, not a network line. |
| **Volume (10M revisions, 500 principals)** | **Conceptually holds; perf gap** | The ledger needs archival/partitioning (cold revisions off the hot path) before enterprise volume. Conceptually scale-free; the *ledger* is not, and needs an archival story. |

**The single most important finding:** the model has exactly **one** conceptual
boundary it does not cross, and that boundary *is the workspace*. Everything
*inside* — more principals, nested agents, physical AI, on-prem storage, Freddie,
persona agents, platform inflow — the two laws absorb without a new top-level
kind. The **only** thing that breaks it is asking it to span *multiple*
workspaces. That is not a flaw — it is the model honestly marking its own edge.

---

## 5. The decision the stress test produced (→ ADR-378)

Naming the ceiling **explicitly** makes the boundary a **strength**, not a
limitation — *because the workspace is a positive definition (one multi-principal
commons), not a headcount cap.* The ratified framing (operator, 2026-06-27):

- **The workspace is the outermost unit YARNNN composes.** One workspace = one
  attributed commons = N principals (humans, agents, platforms, foreign/local
  LLMs).
- **An enterprise is served iff it fits one commons.** One enterprise, one
  workspace, N principals → in scope, served well.
- **A second workspace is *allowed but unrelated*.** YARNNN does not forbid a
  second workspace; it offers **no relationship** between them. Cross-workspace
  reads, shared Freddie, and org-of-workspaces hierarchy are **explicitly
  undefined** — federation is the deliberately-unbuilt layer above the ceiling.
- This is framed **"the workspace is the unit; federation is undefined,"** NOT
  "one enterprise max" — the latter borrows an org noun the kernel never models
  and reads as a cap rather than a definition.

**Why steps 1–3 are the load-bearing rationale, not preamble:** the ceiling is
coherent *only because* of what a workspace was shown to be — one filesystem
(Step 2), holding N attributed principals (Step 3), with all kernel concerns as
metadata (Step 2's unifying principle). "The workspace is the outermost unit"
would be an arbitrary cap if a workspace were a thin thing; it is a *strong*
boundary precisely because a workspace is a *complete multi-principal commons*.
The definition of the inside is what makes the edge meaningful.

---

## 6. What this deliberately leaves open (named, not answered)

- **The single-filesystem refactor itself** (collapsing `inbound/` + the six
  kernel roots into meaning-folders + metadata) is **not** decided here. ADR-378
  hardens the *ceiling* and records the *first-principles model as rationale*; the
  refactor that *implements* Step 2/3 is its own downstream ADR (it touches
  ADR-286 single-writer, ADR-320 topology, ADR-376 `inbound/`). This doc + ADR-378
  establish the *direction*; they do not migrate substrate.
- **The axiom above the workspace** (federation / org-of-workspaces / cross-
  workspace grant) is the genuinely unbuilt layer. ADR-378 marks the boundary as
  *intentional for the current product*, not *permanent for all time* — if
  enterprise federation becomes real, the workspace-of-workspaces is the next
  first-principles discourse, and it begins *above* this ceiling, not by eroding
  it.
- **Platform-as-principal** (`platform:slack` ledger revisions) is the one
  *implementation* move that would make the intake model (ADR-376) and the actor
  model fully consistent in code — it closes the connector-attribution gap and the
  connector-intake gap with one mechanism. Flagged as highest-leverage; not
  decided here.
- **Ledger archival at volume** — conceptually permitted (history is separable
  from current-state by design), not yet solved.
