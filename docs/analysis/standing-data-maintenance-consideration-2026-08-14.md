# Standing data maintenance — a consideration, not a decision (2026-08-14)

> **Correction (same day, operator)**: this record's §2–§3 framing narrowed the
> concept to tables/CSV — the KPI table was an *example*, not the category. The
> general concept is the **maintained file**: any file the member designates as
> kept current under declared rules, any format; designation (not file-type) is
> the boundary. Carried into [ADR-569](../adr/ADR-569-strings-the-maintained-file-kept-by-keeper.md)
> (**ratified 2026-08-14** — app Strings, colleague Keeper), which supersedes
> this record's table-specific wording. The axiom cut (§7) and the
> gesture/management split survive unchanged.

> **Status: deliberation record.** Nothing here is ratified. This captures the
> conceptual boundary that fell out of the 2026-08-14 desk-e2e discourse, so a
> future ADR starts from the decomposition instead of re-deriving it. The
> operator's framing prompt: *"what IF the user does want something that needs
> updating, continuously, under a set of rules — say a table or csv file, or a
> specific slide in the deck that references it. Think of a weekly KPI deck,
> linked to csv tables per slide, where an outside source provides the update."*

## 1. The originating misread, and what it exposed

During the first desk click-pass the operator attached a radar folder and asked
Researcher to work on an existing deck — on the assumption that the standing
loop could update an authored artifact in the watched folder. It cannot, by
ratified design: the sweep writes exactly one judgment output (`report.md`, at
a kernel-fixed leaf, write-confined by `_assert_hub_write` — ADR-564 D6 /
ADR-565 D1+D4), plus its machine signal and the inbound raw observations.
Authored artifacts change only by attended acts.

Two learnings, one per direction:

- **Surface**: the confinement contract is invisible on the desk — the member
  had to ask. (Owed: one sentence on the glass.)
- **Concept**: the *want* behind the misread is real and deserves its own
  frame instead of leaking into radar through lane usage.

## 2. The decomposition: the KPI deck is two mechanisms, one already shipped

A "continuously updated KPI deck" = a **data layer** + a **presentation
layer**, and the deck must never be the write target:

1. **Presentation — already shipped.** Studio artifacts cite data files by
   reference (`data-ref` / chart blocks; the composed authoring posture
   teaches "write the numbers as a `.csv`, then cite it from a chart block —
   a projection stays true when the data changes"). A slide that PROJECTS
   from `kpis/weekly.csv` re-renders when the CSV head moves, with zero
   writes to the deck. The authorship boundary survives untouched.
2. **Data — the genuinely new half.** A standing loop that revises a *data
   file* from an outside source under declared rules. This exists nowhere
   today, and it is **not radar**.

## 3. Why it is not radar: same frame, different species

ADR-564 is deliberately the frame ABOVE the app ("any future standing intake
is a third manifestation"). The data feed is a second manifestation, differing
on exactly the axes the frame parameterizes:

| | Radar (shipped) | Standing data feed (unratified) |
|---|---|---|
| Artifact | prose *understanding* (`report.md`) | structured *state* (CSV/table at a fixed leaf) |
| Governance | criterion — prose judgment ("what matters here") | contract — schema/mapping, machine-checkable |
| Derive | one bounded judgment turn | mostly mechanical transformation |
| Correction | edit the prose head; compounds (ADR-565 D1) | correct a row / revise the mapping contract |

Stretching radar's criterion grammar over schema'd data would blur both apps.
Radar maintains **understanding**; a feed would maintain **state**; the deck
maintains nothing — it references.

## 4. The boundary law (the sentence worth keeping)

> **Unattended writers revise machine-tended files at fixed, declared leaves;
> authored artifacts change only by attended acts — and stay current anyway,
> through reference, because projection is how an artifact reads moving data
> without anyone writing the artifact.**

Corollaries:

- A slide/deck/doc is NEVER a standing loop's write target — in any future
  manifestation. "Keep this slide current" resolves to "keep the file it
  cites current."
- The desk-lane's ability to edit arbitrary files under the member's grant is
  attended conversation, not the loop — and for authored artifacts it is the
  wrong door anyway (the desk posture lacks the medium's conventions; a deck
  wants Studio's lane).

## 5. Why this is the differentiation thesis, not scope creep

The case is only *expressible* on a persistent, attributed, shared filesystem:
a scheduled writer, a human author, and a projecting artifact meet in files,
with attribution deciding who did what and the revision chain making every
layer correctable. A chat-oriented framework can generate the CSV on request;
it has nowhere for the CSV to live, accumulate corrections, and be cited
from. The standing work product is a file whose head is always current — not
a conversation you re-run. (ESSENCE: record = moat.)

## 6. What a future ADR would need to decide (named, not taken)

- The declaration grammar (a `_feed.yaml`-class machine file: source, cadence,
  target leaf, mapping/schema contract) and its fixed-leaf output class.
- The contract's validation posture (a schema violation is a loud repair
  state, not a silent bad write — the ADR-567 D6 shape).
- Source classes: real KPI sources are mostly platforms → gated on the
  connector re-light (ADR-404, entered per ADR-565 D7 phase-next with the
  ADR-564 frame as its answer). Web/API-pull variants may precede it.
- Whether the mechanical transform ever needs a judgment turn (probably the
  ADR-564 D3 "machinery under pressure" rule again).
- App/surface: its own desk? a Files affordance? NOT decided here.

## 7. The axiomatic cut (2026-08-14, same-day follow-up discourse)

**The differentiation claim, made precise.** Scheduled file updates are
commodity (Zapier writes a sheet on cron; Coda packs pull on schedule;
ChatGPT has scheduled tasks). The moat is the COMPOSITION, every leg already
ratified: one attributed commons for the feed's output + the human's
corrections + the artifacts that consume it (Axiom 1, ADR-209); correction
compounds (ADR-384 D4); artifacts reference rather than copy (ADR-448 +
projection); the loop itself is declared in files and managed in conversation
(ADR-564 + the ADR-567 pattern). The doctrine sentence:

> **Currency is a property of the record, not of a conversation** — a file's
> head can carry a standing promise of being kept true, and the promise
> itself is declared, attributed, and correctable like everything else.

Deliberately NOT a new FOUNDATIONS axiom — a composition, the ADR-564 §3
posture again. Grounding: the kernel already half-runs this (alpha-ops
recurrences maintain declared leaves on schedule); what does not exist is the
member-facing, contract-governed, desk-managed cut.

**The flow generalizes the shipped desk verbatim**: pick the subject (one
direct gesture — file or folder) → declare in conversation (source, schema/
mapping, cadence) → standing writer maintains the fixed leaf → correct the
data or the contract → artifacts project. Scenario pairing worth keeping: one
meaning-folder can hold BOTH a criterion-governed report.md (radar,
understanding) and a contract-governed table (feed, state).

**Gesture vs management (the surface question).** The GESTURE belongs
everywhere the file is — right-click "Keep this current…" in Files (and the
document apps) is layer 1, the ADR-514 doors-in-context precedent, cheap and
non-exclusive. The MANAGEMENT belongs at a DESK, because every imagined
component is existing kernel machinery: instructions = the contract file
(CRITERION.md pattern, schema-class); change log = the revision chain
(DeskActivityRail generalizes); schedule = `_*.yaml` + tasks index +
preserve_due_commitment; dedicated agent = the app resident (ADR-562
register_app). Files itself must not become the home — the record's mirror is
"not an act" (ESSENCE v18). ⚠️ "Dashboard" caution: a workspace-global
overview of standing loops is the ADR-486 D2 banned shape; the compliant form
is the rail-of-subjects desk, each subject's page its own dashboard.

**Held, with its decision signal named**: one-app-vs-two (a sibling desk vs
radar widened into "the standing-attention app") is the ADR-565 D8
unified-name question, deferred to the maintainer-phase discourse. Signal: if
members hold one mental model ("what's being kept current while I'm away"),
one desk with two artifact classes; if the governance grammars pull the
surfaces apart (prose criterion vs schema contract), two apps under one
frame.

## 8. Explicit non-decisions

This document ratifies nothing, changes no radar behavior, and does not open
the connector re-light. Radar's contract stands exactly as ADR-564/565/567
shipped it. The app-count question is held per §7.
