# ADR-569: The maintained file — standing currency under contract, kept by Keeper

> **Status**: **Proposed** (2026-08-14, operator ratification pending — drafted from the
> 2026-08-14 boundary discourse; deliberation trail:
> [standing-data-maintenance-consideration-2026-08-14](../analysis/standing-data-maintenance-consideration-2026-08-14.md)).
> **First draft over-narrowed to tables/CSV and was corrected by the operator same day**
> — the KPI table was an *example*; the concept is the maintained FILE, any format the
> member designates. **Names are provisional** per the ADR-486 precedent: the app name
> ("Keep") and the colleague name ("Keeper") are recommendations for the operator to run
> with or retitle. **Nothing builds before ratification.**
> **Date**: 2026-08-14
> **Dimension**: **Substrate** (a designated machine-tended file class: currency under
> contract) + **Purpose** (the contract declaration) primary; **Channel** (the desk
> surface) + **Identity** (a new colleague) + **Trigger** (rides the existing index)
> secondary.
> **Relates to**: ADR-564 (the frame this is the SECOND member-facing manifestation of —
> its §1 named "any future standing intake" in advance), ADR-565 (radar — re-read by D1
> as an already-shipped *specialization* of this frame; D7 phase-next and D8's
> unified-name question interlock with D6), ADR-567 (the desk pattern, reused wholesale;
> its D4 `lane_meta.app` mechanism), ADR-562 (the resident comes from the app's own
> registration), ADR-518 (the housing precedent D6 copies: one parameterized component,
> N app doors), ADR-514 (doors-in-context — the Files gesture), ADR-448 + ADR-423
> (reference edges + revision kinds), ADR-384 D4 (single-head-many-authors — why
> correction compounds on a maintained head), ADR-486 D2 (subject-first guards,
> inherited), ADR-404 (connector sources — NOT re-lit here), ADR-429 (pricing — named,
> not engaged).
> **Amends**: nothing yet — on ratification, ADR-467 D1 / ADR-558's bound-lane roster
> gains a fifth row, and GLOSSARY gains the Maintain vocabulary.

---

## 1. Context — the want behind a misread, generalized past its first example

The first desk click-pass (2026-08-14) surfaced an operator assumption: that radar's
standing loop could keep an existing artifact current. It cannot, by ratified design —
and the discourse that followed found the *want* is real, general, and decomposes:

- **The presentation half already ships.** Authored artifacts cite files by reference
  (`data-ref` / chart blocks, ADR-448 edges); a slide that PROJECTS from a maintained
  file re-renders when its head moves, with zero writes to the artifact.
- **The general mechanism exists only as radar's special case**: a standing writer
  keeping ONE kind of file (a prose understanding at a fixed leaf) current under ONE
  kind of governance (a criterion about the arriving world). The member cannot yet
  designate *a file of their choosing* — a KPI table, a competitor one-pager, a
  glossary, a roster, a JSON state mirror — and declare the rules under which it is
  kept current. That general mechanism is this ADR.

The differentiation claim, made precise in the deliberation record: scheduled file
updates are commodity (Zapier writes a sheet on cron); the moat is the composition only
an attributed commons can hold — the standing writer's revisions, the member's
corrections (which compound, ADR-384 D4), and the artifacts that consume by reference,
all in one substrate, with the loop itself declared in files and managed in
conversation. **Currency is a property of the record, not of a conversation.**

## 2. Decisions

### D1 — The maintained file: designation, not file-type, is the boundary

A **maintained file** is a file the member DESIGNATES as kept current: a declared
contract (what it must stay true to), declared sources (where currency comes from), a
cadence, and a standing writer that revises its head — while the member corrects it
like any file, and every correction compounds into future cycles
(single-head-many-authors, ADR-384 D4). Format is NOT the boundary; **designation is**:

> **Un-designated files are never a standing writer's target. Designation is the
> member's explicit act, and it converts the file to the machine-tended class — where
> unattended revision is expected, attributed, and correctable. Authored artifacts stay
> current without designation, through reference: projection is how an artifact reads a
> moving file without anyone writing the artifact.**

This corrects the first draft's narrowing (tables only) and re-reads ADR-565: radar's
`report.md` is a maintained file that was never member-designated — the app designates
it, shapes its governance as a criterion, and fixes its leaf. Radar is a
*specialization* of this frame, shipped first. Deliberately NOT a new FOUNDATIONS
axiom (the ADR-564 §3 posture): this composes Axiom 1 + ADR-209/384/448.

**v1 designation scope**: `md`, `csv`, `json`, `txt` — file formats whose unattended
revision does not fight an authoring surface's editing model. Designating an
authoring-app artifact (a Studio deck's HTML, a Docs document) is **named-deferred**,
with the reason recorded: a standing writer revising inside Studio's medium collides
with its document model and authorship experience; if demand proves real, that
collision gets its own discourse rather than an implicit allowance. "Keep this slide
current" resolves today to "keep the file it cites current."

### D2 — The declaration is two files, split on the ADR-564 D2 bright line

Mirroring the radar grammar (CRITERION.md + `_radar.yaml`):

- **`CONTRACT.md`** — UPPERCASE prose class (ADR-254): what this file means and must
  stay true to; for structured formats, what each column/field means; for prose, its
  conventions and voice. Operator- and lane-authored, revisable by correction, **never
  machine-parsed**. Judgment prose never rides machine config.
- **`_keep.yaml`** — machine class: `target` (the designated leaf, folder-relative),
  `sources` (v1: pull — HTTP endpoints; see D4), `schedule`, `paused`, and — for
  structured formats only — `shape` (the machine-checkable half: columns/types for
  CSV, a schema for JSON). Machine-composed, `safe_dump`, comment header.

Both live in the designated file's folder; one folder may hold several maintained
files (several `_keep` declarations is a v1-refused complication — one per folder, the
radar single-declaration posture, loudly, until a real case demands more).

### D3 — The write is confined, attributed, and loud on violation

The standing writer revises ONLY the designated leaf, via `write_revision`
(`revision_kind='derivation'`, `derived_from=[raws]`), asserted at the write site
(the `_assert_hub_write` shape; ADR-564 D6). History is the revision chain, never the
namespace (ADR-209). **Validation is per-format**: structured formats with a declared
`shape` refuse a violating write into a **loud repair state** (the ADR-567 D6 shape —
no silent bad numbers, the desk says so, the lane repairs); prose formats carry their
conventions in `CONTRACT.md` and rely on the correction loop, exactly radar's posture.

### D4 — Execution rides the existing machinery; judgment where the format demands

Discovery and cadence reuse the radar pattern verbatim: the tick discovers `_keep.yaml`
declarations, materializes a `kind='keep'` slice of the tasks index (the
`preserve_due_commitment` rule applies by construction), claims via CAS, meters on the
execution ledger (`keep-sweep:{topic}` / `keep-write:{topic}`). The transform runs at
the depth the format needs: mechanical for structured pulls (fetch → parse → map →
validate → write), a bounded judgment turn where the contract demands interpretation
(a prose file kept current IS a judgment derive — governed by `CONTRACT.md` the way
radar's is by its criterion; ADR-564 D3's machinery-under-pressure rule holds for
anything beyond that). **v1 sources: pull only** — HTTP endpoints (CSV/JSON/RSS/pages).
Connector sources (Stripe, GA, Sheets — the real KPI world) enter through the ADR-404
re-light per ADR-565 D7 phase-next; **this ADR does not flip `CONNECTOR_CAPTURE_ENABLED`.**

### D5 — Consumption is reference-only, and the desk shows the consumers

The maintained file's value is realized by artifacts and readers that cite it (chart
blocks / `data-ref` / `derived_from`). The desk carries a "cite this file" affordance
and the inverted provenance instrument: **which artifacts reference this file**
(derived at read time, never stored — ADR-486 D5 discipline), so the member sees the
blast radius of a contract change before making it.

### D6 — A dedicated app on the shared desk housing; the colleague is Keeper

**A separate app, not radar widened** — the ADR-518 reason (the split is housing): the
governance grammars and canvases differ enough that one surface would branch on
manifestation everywhere. The housing consolidates instead: the desk chrome (rail of
subjects · center lifecycle · bound lane · width ladder · activity rail) extracts into
**one parameterized desk component** with two app doors — the `StudioSurface` move.

- **App**: provisional name **"Keep"** (slug `keep`) — function-named like Radar,
  because the medium is plural by design (any designated format); a medium name would
  repeat the first draft's narrowing. Launcher tier starts `search-only`
  (registration ≠ unveil, ADR-486 D7).
- **Colleague**: **Keeper** (slug `keeper`) — tending and fidelity, not judgment:
  "Researcher watches the world; Keeper keeps your files true." Declared as the app's
  resident in the app's OWN module via `register_app("keep", resident="keeper")`
  (ADR-562; engine follows the resident, server-side, never client-asserted).
- **Bound lane**: `create_lane(app='keep', artifact_path={folder}/{target-leaf})`;
  `lane_meta.app` selects the Keeper desk posture (ADR-567 D4's mechanism, one more
  branch). The ADR-467 D1 / ADR-558 roster gains its fifth row consciously.
- **ADR-486 D2 guards inherit unchanged**: subject-first; the rail of subjects is the
  only roster; each subject's page is its own dashboard; a workspace-global "all my
  maintained files" pane is the banned shape.
- **The ADR-565 D8 unified-name question stays open — and this generalization TILTS
  it**: under "maintained files," radar reads as a shipped specialization, which
  strengthens the eventual single standing-attention desk. Held for the
  maintainer-phase discourse; shared housing keeps the fold a door change.

### D7 — Creation and the desk, derived from the acts

Creation is conversational with **exactly one direct gesture** (ADR-567 D3 inherits):
pick the file — an existing file, or a folder plus a name for the new leaf. Two doors
to the same gesture: the app's own picker, and **Files' right-click "Keep this
current…"** on a file or folder (doors-in-context, ADR-514 — the gesture may live
everywhere the file does; the management may not). Then the member tells Keeper what
the file must stay true to and where currency comes from; Keeper authors `CONTRACT.md`
+ `_keep.yaml`; the tick discovers; the loop begins. The form-free discipline holds.

The center pane, by act frequency (the reading-desk derivation, format-generic):

1. **The file** — the canvas, rendered by format through the existing viewer machinery
   (a real table for CSV, a rendered document for md, structured view for JSON), with
   a freshness line ("as of {last successful write}") and staleness stated plainly
   when fetches fail.
2. **What changed** — the activity rail: the leaf's revisions (row/section grain in
   the diff where the format allows) + contract/config revisions + failed/skipped
   runs, attributed (Keeper vs the member), restore on leaf and contract.
3. **Correct** — edit the file (Files, or in-desk where the format makes it cheap —
   an implementation call, not canon) or tell Keeper; either lands attributed and
   compounds.
4. **The setup** — contract card (prose, rendered), sources + fetch health over the
   window, cadence, and for structured formats the shape restated in words;
   refine-in-chat seeds everywhere.
5. **Consumers** — D5's provenance list: what reads from this file.

Direct switches stay direct: Pause/Resume and **Run now** (manual fire — for a
maintained file it is table stakes, and radar is owed the same switch).

### D8 — Falsifiers, pre-registered

Read before any launcher-tier promotion: (1) files designated (excluding the
developer's), across MORE THAN ONE format (a CSV-only uptake would mean the general
frame wasn't the demand — the first draft's narrowing, tested); (2) **consumer edges
exist** — artifacts or derivations citing a maintained leaf (the composition is the
product; a maintained file nobody reads is a cron job with a nicer ledger);
(3) member corrections of leaf or contract observed on the ledger; (4) designations
alive at 30d; (5) repair states entered AND exited (the loud-contract mechanism
observed working, not just designed).

## 3. What this ADR does NOT do

- **No connector re-light** (D4 — ADR-404's own discourse, unchanged).
- **No standing writes to un-designated files, ever** (D1 — the law).
- **No designation of authoring-app artifacts in v1** (D1 — named-deferred with the
  collision reason; reference remains the answer).
- **No workspace-global overview** (D6 — ADR-486 D2 inherited).
- **No new axiom** (D1 — composition, the ADR-564 §3 posture).
- **No pricing decision** (ADR-429 engages no earlier than connector sources make
  volume real — the ADR-565 §4 posture).
- **No app-merge decision** (D6 holds ADR-565 D8 open, tilt recorded, fold kept cheap).
- **Does not build**: implementation stages post-ratification (housing extraction →
  kernel lane → desk → doors), each stage against the gates named in its commit.
