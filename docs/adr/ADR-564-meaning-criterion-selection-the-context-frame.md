# ADR-564: Meaning · Criterion · Selection — the context frame for unattended intake

> **Status**: **Accepted** (2026-08-13, operator-ratified — *"aligned. let's proceed with this
> approach and discipline"*, closing the two-session context-management discourse of
> 2026-08-12/13). Doc-first. The first manifestation is [ADR-565](ADR-565-the-living-report-radar-recut.md)
> (the radar re-cut); this ADR is the frame above the app.
> **Date**: 2026-08-13
> **Dimension**: **Purpose** (primary, Axiom 3 — who declares what matters, and what governs the
> machine's per-sweep judgment) + **Substrate** (Axiom 1 — where each layer lives).
> **Relates to**: ADR-384 (meaning-folders — layer 1 verbatim), FOUNDATIONS Axiom 3 (folder-scoped
> purpose — the `_domain.md` lineage layer 2 recovers), ADR-423/448 (`revision_kind` +
> `derived_from` — layer 3's ledger form), ADR-335 (watches declared / attention calibrated — D4
> and D5's grounding), ADR-404 (capture dormancy — the failure this frame names, §4), ADR-486
> (the standing app this frame re-centers), ADR-254 (format follows consumer — D2's enforcement).
> **Amends**: nothing in FOUNDATIONS — deliberately (§3). ADR-486's app-layer vocabulary is
> amended by ADR-565, not here.

---

## 1. Context — the question above the app

The 2026-08-12/13 discourse began as "what should Radar become" and resolved one level up:
yarnnn needs a frame for **context management under unattended intake** — what happens between
"the world arrives" and "the workspace's understanding updates" when no member is present.
Radar is one manifestation; the connector capture lane (dormant, ADR-404) is another waiting to
happen; any future standing intake is a third.

Two empirical receipts anchored the derivation:

- **Selection pressure bites even on curated input.** The radar derive posture says
  *"Selectivity IS the job"* — and 14 of the app's 20 successful briefs sit at exactly 2044
  output tokens against a 2048 ceiling: truncated, not selective, **on RSS**, the most
  subject-aligned source class there is. If selection collapses on the easiest input, admitting
  scattered sources (Slack, GitHub) makes the collapse categorical.
- **The capture lane's failure was a frame failure.** ADR-404's diagnosis — *"raw platform dumps
  with a low true-signal ratio"* — is, verbatim, intake with no declared criterion and no
  selection stage. The lane didn't fail mechanically (F3 closed positive the same day); it
  failed for lack of the thing this ADR names.

A candidate binary from the first session — "intent-driven vs source-driven sources" (RSS
intent-bearing, Slack scattered) — was examined and rejected as a **type taxonomy** (GitHub
defeats it in both directions; so does any counterexample: a `#competitor-x` channel is tightly
aligned, the HN front page is not). But the replacement claim over-corrected to "no source
carries intent; intent lives in the derivation step" — falsified by canon directly: the
derivation is stateless computation (Axiom 1) and *cannot* hold intent; ADR-335 already rules
that the watch declaration *is* Layer-1 judgment, *"a portfolio of attention."* The corrected
statement is D4.

## 2. Decisions

### D1 — Three layers, keyed on who decides and what governs — a composition, not an invention

| Question | Decided by | Lives in |
|---|---|---|
| Where does this belong? | the operator | the folder path (meaning) |
| What do we care about here? | the operator, revisable by correction | a criterion declaration in the folder |
| What of what arrived matters? | the machine, per sweep | the derivation on the ledger |

Each layer is **existing canon**, not new kernel concept: layer 1 is ADR-384 (the meaning-folder
as the operator's unscriptable judgment act); layer 2 is Axiom 3's folder-scoped purpose — the
`_domain.md` lineage (*"what this domain tracks, what entities belong in it"*) recovered at the
meaning-folder grain; layer 3 is stateless derivation writing `revision_kind='derivation'` +
`derived_from` through the one door (Axiom 1, ADR-423/448). The frame passes Axiom 0's
conflation test: the layers answer different interrogatives (Substrate×Identity / Purpose /
Mechanism×Trigger), decided by different identities.

**The cadence column is commentary, never the key.** Meaning changes rarely and criteria change
slowly *in the typical case*, but a criterion changes fast during early tuning and meaning moves
in a re-org. The defining property is *who decides and what governs* — a mechanic must never be
classified into a layer by how often it changes.

### D2 — The criterion is a folder-scoped prose declaration; criterion prose may not ride machine config

The criterion lives as **`CRITERION.md`** in the folder it governs — UPPERCASE prose class per
ADR-254 (the MANDATE/IDENTITY/AUTONOMY class: a revisable declaration, operator-authored,
lane-revisable, never machine-parsed). Not lowercase (that class is append-only narrative; a
criterion is a declaration, not a log), not underscore-prefixed (that class is machine-parsed;
nothing may ever parse a criterion). The legacy `_domain.md` name predates ADR-254 and is not
carried forward.

**The bright line this D draws: layer-2 prose may not ride a layer-3 carrier.** Judgment prose
inside machine config (the radar `prompt:` steer key inside `_radar.yaml` is the live instance)
is an ADR-254 conflation with a concrete failure mode: the machine writer re-serializes the
whole file (`safe_dump` on every PATCH), churning operator prose — a dual-writer shape ADR-286
exists to prevent — and a YAML value gets none of the correction apparatus (attributed lane
revision, walkable history, diff) that a prose file gets for free. Splitting the carriers splits
the writers: machine config machine-composed; the criterion authored and revised as an ordinary
attributed revision.

### D3 — Selection is a named, governed stage; its machinery is built under pressure, not ahead of it

Between arrival and derivation there is a **selection** act: of what arrived, what matters
*under this folder's criterion*. Today it is collapsed into the derive prompt, which holds only
while the signal ratio is high (§1, first receipt). This D names the stage and fixes its
governance: **any unattended derive over arrivals is governed by a declared, revisable criterion
— never by prompt-buried steer.**

It deliberately does **not** mandate a separate mechanical selection pass. The v1 shape is the
criterion injected into a single governed derive; a distinct pre-selection pass (per-entry
classification against the criterion before synthesis) ships **when scattered sources are
admitted and force it** — machinery under pressure, not ahead of it. The stage has a name in
canon from today so that build has a home when it comes.

### D4 — Intent lives in the declaration, never in the derive; alignment is an edge property

The corrected form of the withdrawn binary (§1): **no source *type* carries intent, and the
derive step cannot** — intent lives in the **declaration**: the criterion plus the source
portfolio, which is the criterion's operational half (ADR-335: the declaration is Layer-1
judgment). What varies across sources is **selection pressure**, and it varies **per edge** —
a property of the *(source, criterion)* pairing, never of the source's type. Consequence for
every surface built on this frame: source admission, tuning, and pruning are ongoing
**layer-2 operator work**, not config.

### D5 — Calibration: the citation rate per source is the earn-their-keep instrument

ADR-335 demands attention be calibrated (*"the loop judges which watches earn their keep"*);
ADR-448's edges supply the instrument for free: of the entries a source fed over the trailing
window, how many were cited by a derivation (`derived_from` + inline citations). Surfaces built
on this frame expose the rate **per source, within the folder's own view** ("fed 40 items,
0 cited in 12 sweeps" is a pruning affordance). Layer 3's output is thereby the evidence layer 2
is revised against — the frame's feedback loop, closed with substrate receipts rather than vibes.

### D6 — Unattended actors are write-confined to the governed folder — a capability constraint, never a read boundary

An unattended sweep may mutate **only the subtree of the folder its criterion governs**,
asserted in code at the write site (no `grant` schema is required or implied — ADR-384's
per-file grant remains doc-direction). Two guards, stated so they cannot drift into each other:

- **Write-scope is capability**: the confinement bounds what a standing actor can touch, so a
  runaway sweep's blast radius is its own folder, reversible by revision (update-before-delete;
  ADR-478 permanent-delete never rides an unattended path).
- **Read-openness is the commons working as designed.** The governed folder answers *what is
  this about* and *what may the sweep write* — **never "who may see this."** The moment a folder
  answers visibility, the workspace ceiling (ADR-378) has been breached and the org-tree
  anti-ICP (CANON-LOCK v19) has entered the room. Separation is a workspace question; meaning is
  a folder question.

## 3. What this ADR does NOT do

- **No new axiom, no FOUNDATIONS amendment.** The frame is a composition of ratified canon
  (D1); naming it an axiom would double-book three existing homes.
- **No permission mechanism.** D6 is a code-level capability assertion; ADR-384 §7's grant
  machinery is untouched and un-advanced.
- **Does not flip `CONNECTOR_CAPTURE_ENABLED`.** ADR-404 stands. §4 names the relationship.
- **No workspace-global surface.** Everything this frame governs is folder-scoped and plural;
  ADR-486 D2's inbox guard (no source-keyed organizing surface) and cockpit guard inherit
  unchanged into every manifestation.
- **Does not decide any app's shape.** ADR-565 is the first manifestation and carries every
  app-layer decision (artifact form, naming, staging, FE).

## 4. Why now — the frame is what the capture re-light was missing

When the connector discourse reopens (on ADR-404's own terms), connections re-enter as
**sources feeding governed folders** — one more row in a portfolio, under a criterion, through
a named selection stage — which is ADR-486 D2's reconciliation *plus the governance it lacked
the first time*. The two-modes deliberation of 2026-08-13 (outward web researcher vs platform
maintainer) resolved on exactly this: the modes are one machine differing by source class, and
the maintainer — the demand center for the copy-paste-seam ICP — becomes buildable the moment
this frame plus its first manifestation are real. What is commoditized is the per-platform
recency digest, silo-bound by construction; what no platform can structurally offer is
cross-source, subject-keyed, maintained understanding landing in a record the team owns. That
product claim rests on this frame.

One naming note: "context management" brushes against Freddie's ESSENCE framing as the
context-management OS (v14.2). That is reinforcement, not collision — this frame is doctrine the
steward's intake-side work follows; it names no new actor and no new seat.
