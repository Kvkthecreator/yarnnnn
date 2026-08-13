# ADR-565: The Living Report — the radar re-cut, staged by source class

> **Status**: **Accepted** (2026-08-13, operator-ratified with [ADR-564](ADR-564-meaning-criterion-selection-the-context-frame.md)
> — one app, one frame, staged by source class; *"strip its current complexity, re-center it on
> one core flow"*). The first manifestation of the ADR-564 frame.
> **Date**: 2026-08-13
> **Dimension**: **Substrate** (the artifact re-cut — one living meaning-file over a brief
> namespace) primary; **Purpose** (the criterion file) + **Channel** (the re-centered surface)
> secondary. Trigger unchanged (the standing sweep stays ADR-486's).
> **Amends**: **ADR-486** — D4's placement clause (append-only dated briefs, *"never
> overwrites"*) is superseded by D1 below; D1's hub anatomy gains `CRITERION.md` + `report.md`
> and loses the `prompt:` steer key (D2); the single-level hub restriction falls (D3). ADR-486's
> D2 (subject-first, never source-first), D3 (standing intent on the declaration), D5
> (composed view derived-never-stored), D6 guards and D7's unveil rule are **preserved**.
> **Relates to**: ADR-209 (namespace-versioning retired — D1's first ground), ADR-384 D3/D4 +
> ADR-423 §7 (the one-chain direction — D1's second ground), ESSENCE Core Thesis #3
> (correction-compounding — D1's third ground), ADR-381 (relabel-keep-slug — D8's precedent),
> ADR-467 D1 + ADR-522 (the bound-lane pattern — D6), ADR-404 (the staging boundary — D7),
> ADR-486 D8 (the falsifiers this re-cut answers).

---

## 1. Context — the falsifier reading, and what it actually said

ADR-486's D8 falsifiers were pre-registered and two have fired negative: **one hub ever
declared** (the developer's own), **paused at day 19**. The unveil gate (D7) was consciously
taken early. Two sharpenings from the 2026-08-13 re-verification:

- **70% of everything the app produced was truncated.** 14 of 20 successful briefs sit at
  exactly 2044 output tokens against `_BRIEF_MAX_TOKENS = 2048` — cut mid-thought, on RSS. The
  symptom of the wrong artifact shape (an unbounded delta), not the wrong ceiling.
- **The denominator is degenerate.** Effectively one real operator pre-launch. The falsifiers
  read *"not felt yet"*, not *"refuted."* This ADR is the response to that reading; the
  launcher-tier decision is deliberately **not** taken here (§5).

The prior shape: append-only dated briefs in `briefs/`, each a delta against the previous, the
sweep's only memory a max-path read of the latest brief, no synthesis above the stack.

## 2. Decisions

### D1 — The living report supersedes the briefs shelf

Each hub maintains **one report** — `report.md` in the hub folder. A sweep **revises** it:
`write_revision(revision_kind='derivation', derived_from=[signal + raws])`, head as the current
understanding, the model handed the head (member edits included) as "previous understanding."
Three grounds, in descending force:

1. **The brief shelf was namespace-encoded versioning** — each brief a delta-vs-previous, the
   latest-brief read a head pointer, the date-prefixed leaf an implicit parent pointer: a
   hand-rolled revision chain in the namespace, duplicating what `workspace_file_versions` does
   natively. Axiom 1: *versioning lives in a separate metadata plane, never in the namespace.*
2. **One meaning-file whose chain carries the derivations is ADR-384 D3's literal worked
   example** and the direction ADR-423 §7 deferred. The living report is the more canonical
   shape, not a departure.
3. **Correction-compounding becomes structural.** A member who fixes a wrong claim in the report
   head has fixed it for every future sweep (single-head-many-authors, ADR-384 D4). The brief
   stack structurally cannot deliver this — correcting brief N does nothing durable for N+1.

The delta remains legible **through the ledger**: the revision message carries the sweep's
headline; the revision history (`RevisionHistoryPanel`) is the delta rail; the diff is the
delta. The report may keep a short "Recent developments" section, but the chain is the history.
The empty sweep stays honest: the sentinel becomes **`NO_CHANGE`** (same contract as
`NO_BRIEF` — falsifier 4's denominator reads on, the `radar-sweep`/`radar-brief` event slugs
are **unchanged** so every existing ledger reader keeps working). ADR-486 D4's *"never
overwrites"* is amended accordingly: a ledger revision is not a destructive overwrite —
retention, attribution, and citation all hold on the chain. **Existing briefs stay where they
are** — the record is the record; new sweeps simply stop adding to the shelf.

### D2 — `CRITERION.md` enters; the `prompt:` steer key retires (ADR-564 D2 applied)

The hub folder gains **`CRITERION.md`** — the operator's declaration of what matters here,
seeded by the create flow, revisable by the operator and by the bound lane (D6) as ordinary
attributed revisions. The sweep's derive is governed by it (injected into the one bounded derive
turn — ADR-564 D3's v1 shape). `_radar.yaml` shrinks to **pure machine config**: `schedule`,
`paused`, `sources`. The `prompt:` key is deleted from the declaration grammar (the live hub's
steer migrates into its criterion). One file, one writer class: the YAML machine-composed by
the route; the criterion never touched by a machine writer.

### D3 — A hub attaches to any meaning-folder; the single-level restriction falls

`topic_from_declaration_path`'s single-segment rule was an R0 discovery-scan simplification,
never a ratified decision — and it is against the re-founding's grain (operators nest meaning).
A hub declaration is valid at **any depth** under the commons root (`operation/` in the live
topology; the meaning-roots when ADR-384 §7 lands). The topic identifier becomes the
folder path relative to the root (slug `radar:{path}`); route params take path form.

**The framing correction this D records**: the agent was never "boxed into" the folder. The
folder is the *subject's* home — a commons folder the member also works in (a memo dropped
there is legitimate sweep context) — and the Researcher *tends* it under a write-grant scoped to
it (D4). Identity homes (`agents/{slug}/`, ADR-384 residue) are untouched; the resident is a
registry fact, never a folder fact. **Named-deferred**: nested criteria (a criterion inside a
governed subtree). The obvious cascade rule — a criterion governs its subtree minus subtrees
carrying their own — is the CLAUDE.md/`.gitignore` model and can ship when a real case demands
it; v1 refuses nested declarations loudly, as today.

### D4 — The sweep is write-confined to the hub subtree (ADR-564 D6 applied)

Asserted in code at the sweep's write site: every path the sweep mutates must live under the
hub root. A capability constraint, not a read boundary — the report and criterion are ordinary
commons files, readable per workspace grants like everything else.

### D5 — The source portfolio is layer-2 surface, with the citation-rate instrument

Sources are a **portfolio** the operator gardens (add / tune / prune) — dedicated FE, one row
per source, never a textarea. Each row carries its earn-their-keep reading per ADR-564 D5
(entries fed vs entries cited over the trailing window, computed from `derived_from` + inline
citations — derived at read time, never stored, the D5-of-486 discipline). Portfolio panes are
**per-hub only**; a workspace-global source pane is ADR-486 D2 violated.

### D6 — The bound lane is the criterion's revision surface

The hub view gains a lane in the Docs/Studio pattern — pinned to `scout` (`lane_meta["agent"]`,
ADR-467 D1), aware of the open report and declaration (the ADR-522 contract). It is
load-bearing for the frame, not chrome: layer 2 changes *by correction*, and "stop tracking
funding rounds, focus on model releases" landing as an attributed revision of `CRITERION.md` is
the correction loop with a surface. No collision with the un-addressed sweep: two triggers, one
substrate — they meet in the files (Axiom 1 is the bus).

### D7 — Staged by source class: one app, one machine, two phases

The 2026-08-13 two-modes deliberation (outward web researcher vs platform maintainer) resolved:
**not two apps — one machine differing by source class** (ADR-486 D2's own reconciliation).
Demand reads maintainer, by a wide margin, for the copy-paste-seam ICP; technically the
maintainer requires the capture re-light plus its two sleeping defects root-caused, and its
scattered inputs are what will force the mechanical selection pass (ADR-564 D3).

- **Phase now (this ADR's build)**: the chassis on the source class that already runs —
  criterion, living report, portfolio, confinement, bound lane — on web/RSS. Every piece is
  load-bearing for the maintainer unchanged; a derive bug here costs an awkward report, not a
  $60/day burn.
- **Phase next (its own discourse)**: connector sources re-enter through the ADR-404 re-light,
  entered *with the ADR-564 frame as its answer* — portfolio rows under criteria, the
  byte-identical-rewrite burn and derive-wake duplication root-caused there, the mechanical
  selection pass shipping because scattered sources demand it. **This ADR does not flip
  `CONNECTOR_CAPTURE_ENABLED`.**
- **Named-deferred**: web-search as a source kind (a standing query — the criterion reaching
  into intake); nested criteria (D3).

### D8 — The rename is deferred until the unified name settles

"Researcher" fits the outward mode; the maintainer mode reads as a tending identity. The winner
should name the **unified** thing, and the fork's product naming belongs to the Phase-next
discourse. When taken, the mechanism is ADR-381's **relabel-keep-slug** (display changes;
the `radar` surface slug, routes, and `kind='radar'` index stay). Until then the app keeps its
name and the hub keeps its vocabulary.

### D9 — Falsifiers re-cut to the report

ADR-486 D8's instruments survive with the felt unit swapped: (1) hubs declared, unchanged;
(2) **report revisits** (is the report re-opened between sweeps?) replaces briefs-opened;
(3) hubs alive at 30d, unchanged; (4) sweep→change yield (`NO_CHANGE` rate), unchanged in
mechanism. One new instrument, the frame's own: (5) **correction events** — member/lane
revisions of `report.md` or `CRITERION.md` (the compounding loop observed on the ledger, via
`workspace_file_versions` authorship — no new schema). Read before any launch-tier re-decision.

## 3. Cascade / blast radius

- **Backend**: `services/radar.py` (report derive + posture re-cut, `NO_CHANGE` sentinel,
  depth-lifted topic parse, confinement assertion, criterion read, ceiling re-cut for a bounded
  document); `routes/radar.py` (criterion create/update as separate revisions, `prompt` field
  retired, path-form topic params, report in the hub view, D2-of-486 fire_on_activation
  consume-once rider lands separately as a fix).
- **FE**: `RadarSurface` re-cut (three-step create: folder → criterion → portfolio; report-
  centered hub view + revision rail; per-hub portfolio pane; bound lane) — its own commit(s).
- **Canon**: this ADR + ADR-564; ADR-486 status banner; GLOSSARY (Criterion; Hub amended;
  Report). CLAUDE.md untouched this pass.
- **Gate**: `api/test_adr565_living_report.py` (report revise path, sentinel, confinement
  refusal, depth parse, criterion injection, no `prompt:` in composed YAML);
  `api/test_adr486_radar.py` amended where it pins the superseded brief-shelf behavior.

## 4. What this ADR does NOT decide

- **The launcher tier.** The falsifier reading argues for `search-only` during the rebuild
  (D7-of-486's own discipline); the degenerate denominator argues the data is weak. Separable
  call, the operator's, read against D9 after the chassis lands.
- **The capture re-light** (D7 phase-next — ADR-404's own discourse).
- **The final name** (D8).
- **Pricing** (standing metered judgment engages ADR-429 no earlier than the maintainer phase).
