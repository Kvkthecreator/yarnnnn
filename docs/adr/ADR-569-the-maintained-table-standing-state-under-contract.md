# ADR-569: The maintained table — standing state under contract, kept by Keeper

> **Status**: **Proposed** (2026-08-14, operator ratification pending — drafted from the
> 2026-08-14 boundary discourse; deliberation trail:
> [standing-data-maintenance-consideration-2026-08-14](../analysis/standing-data-maintenance-consideration-2026-08-14.md)).
> **Names are provisional** per the ADR-486 precedent: the app name ("Tables") and the
> colleague name ("Keeper") are recommendations for the operator to run with or retitle —
> a rename before implementation is a title edit, not a re-decision. **Nothing builds
> before ratification.**
> **Date**: 2026-08-14
> **Dimension**: **Substrate** (a new machine-tended file class: state under contract) +
> **Purpose** (the contract declaration) primary; **Channel** (the desk surface) +
> **Identity** (a new colleague) + **Trigger** (rides the existing index) secondary.
> **Relates to**: ADR-564 (the frame this is the SECOND manifestation of — its §1 named
> "any future standing intake" in advance), ADR-565 (the first manifestation; D7's
> phase-next and D8's unified-name question interlock with D6 below), ADR-567 (the desk
> pattern this reuses wholesale; its D4 `lane_meta.app` mechanism), ADR-562 (the resident
> comes from the app's own registration), ADR-518 (the housing precedent D6 copies: one
> parameterized component, N app doors), ADR-514 (doors-in-context — the Files gesture),
> ADR-448 + ADR-423 (reference edges + revision kinds — the consumption law's mechanics),
> ADR-486 D2 (subject-first guards, inherited unchanged), ADR-404 (connector sources —
> explicitly NOT re-lit here), ADR-429 (pricing — named, not engaged).
> **Amends**: nothing yet — on ratification, ADR-467 D1 / ADR-558's bound-lane roster
> gains a fifth row, and GLOSSARY gains the Maintain vocabulary.

---

## 1. Context — the want behind a misread

The first desk click-pass (2026-08-14) surfaced an operator assumption: that radar's
standing loop could keep an existing deck current. It cannot, by ratified design — and
the discourse that followed found the *want* is real and decomposes cleanly:

- **The presentation half already ships.** Studio artifacts cite data files by reference
  (`data-ref` / chart blocks); a slide that PROJECTS from `kpis/weekly.csv` re-renders
  when the CSV head moves, with zero writes to the deck.
- **The data half exists nowhere**: a standing loop that revises a *data file* from an
  outside source under declared rules. That half is this ADR.

The differentiation claim, made precise in the deliberation record: scheduled file
updates are commodity (Zapier writes a sheet on cron); the moat is the composition only
an attributed commons can hold — the feed's output, the member's corrections (which
compound, ADR-384 D4), and the artifacts that consume it (by reference, never copy) in
one substrate, with the loop itself declared in files and managed in conversation.

## 2. Decisions

### D1 — The second manifestation, and the boundary law canonized

A **maintained table** is a machine-tended data file at a fixed, declared leaf, kept
true to an outside source under a member-declared **contract**, on a cadence. It is the
second manifestation of the ADR-564 frame, differing from radar on exactly the axes the
frame parameterizes:

| | Radar (ADR-565) | The maintained table (this ADR) |
|---|---|---|
| Artifact | prose *understanding* (`report.md`) | structured *state* (a data leaf) |
| Governance | criterion — prose judgment | contract — meaning prose + machine-checkable shape |
| Derive | one bounded judgment turn | mechanical transform (judgment only under D4's rule) |
| Correction | edit the prose head; compounds | correct a value / revise the contract; compounds |

The doctrine sentence both manifestations now share, canonized here:

> **Unattended writers revise machine-tended files at fixed, declared leaves; authored
> artifacts change only by attended acts — and stay current anyway, through reference,
> because projection is how an artifact reads moving data without anyone writing the
> artifact.** Corollary: *currency is a property of the record, not of a conversation.*

A deck, doc, or slide is NEVER a standing loop's write target — in this manifestation
or any future one. "Keep this slide current" resolves to "keep the file it cites
current." Deliberately NOT a new FOUNDATIONS axiom (the ADR-564 §3 posture): this is a
composition of Axiom 1 + ADR-209/384/448.

### D2 — The declaration is two files, split on the ADR-564 D2 bright line

Mirroring the radar grammar exactly (CRITERION.md + `_radar.yaml`):

- **`CONTRACT.md`** — UPPERCASE prose class (ADR-254): what this table means, what each
  column means, what counts as a valid row, how to read the source. Operator- and
  lane-authored, revisable by correction, **never machine-parsed**. Judgment prose never
  rides machine config.
- **`_feed.yaml`** — machine class: `source` (url + kind), `schedule`, `paused`,
  `target` (the leaf, folder-relative), and `shape` (columns + types — the
  machine-checkable half of the contract, enforced in code at the write site). Composed
  by the route/lane, `safe_dump`, comment header; the prose contract never enters it.

### D3 — The target is a fixed data leaf, write-confined, loud on violation

The maintained leaf is declared once in `_feed.yaml`, lives **inside the meaning-folder
subtree** (ADR-564 D6 write-confinement, asserted at the write site exactly as
`_assert_hub_write`), and is machine-tended: the standing writer revises it via
`write_revision` (`revision_kind='derivation'`, `derived_from=[raws]`), the member
corrects it like any file, history is the revision chain — never namespace versioning
(ADR-209). **v1 format: CSV** (one table, one leaf; JSON named-deferred). A fetch that
parses but violates `shape` is a **loud repair state** (the ADR-567 D6 shape): no write
lands, the desk says so plainly, the lane is the repair surface. A silent bad write is
the one unforgivable failure mode for a numbers file.

### D4 — Execution rides the existing machinery; judgment only under pressure

Discovery and cadence reuse the radar pattern verbatim: the tick discovers `_feed.yaml`
declarations, materializes a `kind='feed'` slice of the tasks index (the
`preserve_due_commitment` rule of 2026-08-13 applies by construction), claims via CAS,
records runs on the execution ledger (`feed-sweep:{topic}` / `feed-write:{topic}` event
slugs). The transform is **mechanical by default** — fetch → parse → map → validate →
write — with a bounded judgment turn admitted only where the mapping demands it
(ADR-564 D3's machinery-under-pressure rule; a judgment transform must still emit rows
that pass `shape`). **v1 sources: pull only** — HTTP endpoints serving CSV/JSON/RSS.
Connector sources (Stripe, GA, Sheets — the real KPI world) enter through the ADR-404
re-light per ADR-565 D7 phase-next; **this ADR does not flip `CONNECTOR_CAPTURE_ENABLED`.**

### D5 — Consumption is reference-only, and the desk teaches it

The table's value is realized by artifacts that cite it (chart blocks / `data-ref`,
ADR-448 edges). The desk carries a first-class "cite this table" affordance (copyable
reference + the teaching sentence), and the citation instrument runs the other way from
radar's: **per-consumer provenance** — which artifacts reference this leaf (derived at
read time from `data-ref`/`derived_from`, never stored, the ADR-486 D5 discipline), so
the member sees the blast radius of a contract change before making it.

### D6 — A dedicated app on the shared desk housing; the colleague is Keeper

**A separate app, not radar widened** — for the ADR-518 reason (the split is housing):
the two grammars force different empty states, setup teaching, repair states, and a
different center canvas (a table is not a reading document); branching one surface on
manifestation everywhere is the fork ADR-518 refused. The housing consolidates instead:
the desk chrome (rail of subjects · center lifecycle · bound lane · width ladder ·
activity rail) extracts into **one parameterized desk component** with two app doors —
exactly Docs/Studio's `StudioSurface` move.

- **App**: provisional name **"Tables"** — medium-named per the ADR-567 D1 rule (the
  app is named for the medium, the colleague for the persona). Surface slug `tables`;
  launcher tier starts `search-only` (registration ≠ unveil, ADR-486 D7 discipline).
- **Colleague**: **Keeper** (slug `keeper`, display "Keeper" — slugs are data-compat,
  display renames free, ADR-381). Persona: precision and tending, not judgment —
  "Researcher watches the world; Keeper keeps your numbers true." Declared as the app's
  resident in the app's OWN module via `register_app("tables", resident="keeper")`
  (ADR-562; the engine follows the resident, server-side, never client-asserted).
- **Bound lane**: `create_lane(app='tables', artifact_path={folder}/{target-leaf})`;
  `lane_meta.app` selects the Keeper desk posture (ADR-567 D4's mechanism, one more
  branch). The ADR-467 D1 / ADR-558 roster gains its fifth row consciously.
- **ADR-486 D2 guards inherit unchanged**: subject-first, never an inbox, never a
  workspace-global overview — the rail of subjects is the only roster; each subject's
  page is its own dashboard. A workspace-global "all my feeds" pane is the banned shape.
- **The ADR-565 D8 unified-name question stays open**: if the maintainer-phase
  discourse finds members hold one mental model ("what's kept current while I'm away"),
  the two apps can fold into one desk later — housing already shared, so a fold is a
  door change, not a rebuild.

### D7 — Creation and the desk, derived from the acts

Creation is conversational with **exactly one direct gesture** (ADR-567 D3 inherits):
pick where the table lives. Two doors to the same gesture: the app's "Keep a table
current" (picker), and **Files' right-click "Keep this current…"** on a folder or an
existing CSV (doors-in-context, ADR-514 — the gesture may live everywhere the file
does; the management may not). Then the member tells Keeper what the table must stay
true to and where the numbers come from; Keeper authors `CONTRACT.md` + `_feed.yaml`;
the tick discovers; the loop begins. The form-free discipline holds.

The center pane, by act frequency (the reading-desk derivation, table-flavored):

1. **The table** — the canvas: the leaf's head rendered as a real table (sortable
   read view), freshness line ("as of {last successful write}"), staleness stated
   plainly when a fetch has been failing.
2. **What changed** — the activity rail at ROW grain where possible: per-revision
   diffs of the leaf + contract/config revisions + failed/skipped runs, attributed
   (Keeper's writes vs the member's corrections), restore on the leaf and contract.
3. **Correct** — the member edits the leaf (Files or in-desk cell edit is a v1-scope
   call for implementation, not canon) or tells Keeper; either lands as an attributed
   revision and compounds.
4. **The setup** — contract card (prose, rendered), source + fetch health (fed /
   failed over the window), cadence, `shape` restated in words; refine-in-chat seeds.
5. **Consumers** — D5's provenance list: what projects from this table.

Direct switches stay direct: Pause/Resume, and **Run now** (the manual fire radar is
also owed — for a data desk it is table stakes: "the numbers meeting starts in five
minutes").

### D8 — Falsifiers, pre-registered

Read before any launcher-tier promotion: (1) tables declared (excluding the
developer's); (2) **consumer edges exist** — at least one artifact citing a maintained
leaf (the composition is the point; a table nobody projects is a spreadsheet with extra
steps); (3) member corrections of leaf or contract observed on the ledger; (4)
tables alive at 30d; (5) repair states entered AND exited (the loud-contract mechanism
observed working, not just designed).

## 3. What this ADR does NOT do

- **No connector re-light** (D4 — ADR-404's own discourse, unchanged).
- **No writes to authored artifacts, ever** (D1 — the law, not a v1 limit).
- **No workspace-global overview** (D6 — ADR-486 D2 inherited).
- **No new axiom** (D1 — composition, the ADR-564 §3 posture).
- **No pricing decision** (standing metered work engages ADR-429 no earlier than
  connector sources make volume real — the ADR-565 §4 posture).
- **No app-merge decision** (D6 holds the ADR-565 D8 question open, with shared
  housing keeping the fold cheap).
- **Does not build**: implementation is staged post-ratification (housing extraction →
  kernel lane → desk → doors), each stage against the gates named in its commit.
