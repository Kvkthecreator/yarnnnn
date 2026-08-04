# ADR-507 — The acts are open: Think · Make · Perceive, and the pipeline retires

> **⚠️ Amended by [ADR-518](ADR-518-docs-and-studio-the-writing-app-and-the-layout-app.md) (2026-08-04)**: the Make act's app list is `docs` · `studio` · `images` — the growth rule ran as designed (a new app is a row under an existing act), with an ADR anyway because the split re-cut an existing app's scope, not merely added a row.

- **Status**: **Accepted + Implemented** (2026-07-30, operator-ratified through the
  settle-axiom discourse — *"i think that keep this, settle should not be the axiom. think →
  make have their dedicated surfaces… and thus, apps can increase and the current list is not
  hard-fixed. we have a tendency to be current state assessing when really we need to be
  expansive."*). D3 (delete settle) and D4 (embed deferred, noted) were each ratified
  explicitly.
- **Date**: 2026-07-30
- **Dimension**: Channel (primary — what acts the product names and how surfaces group under
  them) + Purpose (the service model). No new substrate, no schema, no migration.
- **Supersedes**: **ADR-457 D2** (the `think → settle → make` pipeline) and **ADR-457 D3**
  (the settle verb as chat's flagship). ADR-457's derivation, D1 (the verb pair names the
  job), D5 (the floor is posture-invariant; the desk leads), D6 (the MacWrite/MacPaint
  doctrine) and D8 falsifiers 1 + 3 are **preserved**.
- **Amends**:
  - **ESSENCE v16 §The Desk** — two verbs → **three acts over an open set**; the pipeline
    paragraph deleted; settle removed from the four staged moments of the moat.
  - **FOUNDATIONS DP29 fourth amendment (v9.18)** — the "five acts, two felt, pipeline
    think→settle→make" formulation is re-cut.
  - **ADR-454 D1 / ADR-412 D3** — the two acting surfaces become three named acts; the
    surface set beneath them is explicitly open.
- **Preserves**: ADR-310 (two doors, one moat) · ADR-413 (the invocation contract) · ADR-423
  (`revision_kind`) · ADR-448 (the reference edge) · ADR-411 D4 (`member:` attribution) ·
  ADR-321/325 (embedding is an explicit primitive — **not** reversed here, see D4) · ADR-495
  (the conversation's one cast) · every ADR-457 falsifier that tests the desk-vs-hum thesis.

---

## 1. The question

ADR-457 asserted a **pipeline**: `think → settle → make`. Thinking distills into the commons;
making learns from the distillates. `settle` was its middle term and chat's flagship act.

The operator questioned the axiom itself. Two claims came with the question, and both hold:

1. **Think and make have dedicated surfaces, and apps live under them.** The verbs are not
   stages in a flow; they are **media**, each hosting a growing set of apps.
2. **The current list is not hard-fixed.** *"We have a tendency to be current-state assessing
   when really we need to be expansive."*

## 2. What the evidence said

**Settle was built, wired, and used — four times.** (An earlier statement in this session that
settle was "ratified-but-unbuilt" was false, read off ADR-457's status line without checking
the tree; the correction is recorded here because it changed the discourse.) Production at the
cut: `settle.py` 380 LOC, `POST /lanes/{id}/settle`, a "Keep this" button portalled into the
conversation header, a 41/41 gate, **4 settles between 2026-07-15 and 2026-07-24**, all
`success`, ~$0.003–0.009 each.

**The arrow ran backwards.** Of the four real settles, three were *deck build* notes
(`…deck-build-best-time-to-build…`, `…6-slide-sample-deck-drafted`, and a second draft) and
one was `…clarification-needed-on-the-deal`. Three of four were **records of a make that had
already happened** — the observed flow was `make → settle`, settle as *receipt*, not as
feedstock for making. A pipeline whose middle term is used as a terminal step is not that
pipeline.

**Settle was double-classified in canon.** ESSENCE v16 lists it among the four *staged moments
where the ledger becomes felt* (trace · correct-once-everything-inherits ·
leave-with-everything · settle) **and** as a pipeline stage. The other three are
*demonstrations of the record*, not acts in a workflow. That double booking is the confusion:
settle was filed as a moment and promoted as a stage.

## 3. Decisions

### D1 — Three named acts, over an OPEN set of apps

The kernel names **acts**; apps live under them. **Neither list is closed**, and this is the
load-bearing half of the decision — the failure mode being corrected is describing the
current inventory as if it were the model.

| Act | The medium | Apps today |
|---|---|---|
| **Think** | dialogue (divergent work has no stable visual state) | `chat` |
| **Make** | the artifact (convergent work does) | `studio` (document · deck · web) · `images` |
| **Perceive** | the world, arriving | `radar` |

**Perceive is promoted to a named act.** ADR-457 called perception "increasingly ambient" and
excluded it from the felt verbs; radar's unveil (ADR-486) made that false — a member opens
radar and reads briefs, which is a *felt* act with its own app. Naming it resolves the
launcher honestly instead of by force-fit.

**Two surfaces are deliberately NOT acts.** `files` is the **record's mirror** — the moat made
legible (DP29's mirror class), not a verb. Settings/system is the management plane (DP28).
Both sit at a different altitude; a model that called them verbs would be flattening two
genuinely different things.

**The growth rule** (the expansive discipline, stated so a future session inherits it): a new
**app** is a row under an existing act and needs no ADR. A new **act** needs an ADR, and the
bar is *a medium the three do not cover* — not a feature, not an output shape, not an engine.
The three acts are the current answer, not a closed axiom.

### D2 — There is no pipeline; the acts compose freely

`think → settle → make` is retired. The honest shape is **`think ⇄ make`** with perceive
feeding both: work oscillates — you think, you make, you look at what you made and think
again. ADR-457's durable observation survives intact and is what this preserves: *divergent
work's medium is dialogue; convergent work's medium is the artifact.* That is a claim about
**which surface fits which kind of work**. It never implied sequence, and reading a sequence
into it is what produced a mandatory middle term.

The corollary: **nothing has to pass through a distillation step to move between acts.** A
conversation can inform an artifact by being read, cited, searched, or simply remembered by
the member. The commons is the shared medium; a verb in the middle was never required for it
to work.

### D3 — Settle is DELETED, not demoted (Singular Implementation)

Deleted, with no dormant parallel path: `services/settle.py` · `POST /lanes/{id}/settle` ·
`api/test_settle_verb.py` · the FE "Keep this" button, its `settling`/`settled` state, the
landed-note card, and the **entire `actionsContainer` → `actionsRef` portal chain** across
`LanePanel` / `ChatSurface` / `ConversationHeader` (which existed for this one button) ·
`api.lanes.settle` · the now-dead `createPortal` + `NotebookPen` imports.

**Why deleted rather than kept as an app-level act**: it was a *metered verb with its own
route* for something the lane can already do with the tools it holds (D5). Keeping it would be
two implementations of one act — the exact ambiguity Singular Implementation exists to
prevent.

**What the deletion is NOT justified by.** Falsifier 2 (`falsifier_2_settle_adoption`) was
built to detect "the settle verb goes unused after honest staging," and it was **read before
removal** — the discipline the instrument exists for. Its reading at deletion:
`staged=True, settles=4, most recent 6 days prior`. That is **low adoption, not abandonment**,
and 4 events by one dogfooding operator does not clear its own "stay ~0 across the window"
bar. **The falsifier did not fire, and this ADR does not claim it did.** Settle is retired
*structurally* — the pipeline it was the middle of is gone — and the usage data supports that
reading (the `make → settle` arrow) rather than the adoption one. The instrument dies with the
bet it measured; **falsifiers 1 and 3 stand**, because they test the desk-vs-hum investment
thesis (ADR-457 D5), which this ADR preserves. A tombstone in `falsifiers.py` carries the
reading and the honest verdict, and the W0 gate now asserts the tombstone rather than the
retired function.

### D4 — The embed gap is NOTED, not closed here

Verified empirically, not assumed: a member asking *"save this as a note on the deal"* is
served today. The lane declares `WriteFile` with `derived_from` **in its schema** (checked
against `lane_tools_openai()`), and `PARTICIPANT_FILESYSTEM_MODEL` teaches placement
("Documents", meaning-folders, *"you don't ask permission to name a new folder"*), while
`build_lane_conventions` teaches read-before-write, `derived_from` citation, attribution and
`.md` format. `revision_kind` is not model-settable and does not need to be — the write door
defaults it to `derivation` when `derived_from` is present (ADR-448).

**One mechanic does not survive: embedding.** Per ADR-321, embedding is no longer a write
side-effect; it is the explicit `Embed` primitive (ADR-325), and `Embed` is **not in the lane's
tool surface** — nor can it be added there, since `LANE_SURFACE_EXTRA` additions must be in
`READ_ONLY_PRIMITIVES` and Embed is consequential. So a note a member asks for is attributed,
versioned and well-placed, but **not retrievable by `recall`/`QueryKnowledge` until something
embeds it.** Settle embedded explicitly; that was its "bird 3", the retrieval fix.

**This gap is pre-existing and general, not a regression introduced here**: it affects *every*
lane write, and has since ADR-321. Settle was the only lane-adjacent writer that opted in —
so deleting it removes the one place papering over a hole in the floor, rather than digging
one.

**Deliberately deferred** (operator-ratified: *"lean noted on embed"*). The options are (a)
leave it — recall reads what `Embed` touched, and lane notes are not in it; (b) auto-embed
member-lane prose, which partially reverses ADR-321; (c) an explicit "make this searchable"
act. **(b) is an ADR-321 reversal and must not ride a framing commit.** Whoever takes it
should note the shape: this is the same *derive organ* question the ADR-401 audit opened —
autonomous derive has still never fired, and settle was its human-staged stand-in. Removing
settle leaves that organ empty again, honestly rather than nominally.

### D5 — Distillation is something a member ASKS FOR, not a verb the product ships

The act survives; the affordance does not. "Keep this as a note" is a request inside a
conversation, served by the lane's own tools under the member's grant — no button, no route,
no metered verb, no seat. This is the same category as the ADR-450 derive recipes (ask for a
brief *from a file*), which is why ADR-460 already ruled settle a **sibling** of that path
rather than a row in it: a transcript has no path to cite, a difference in kind.

Dividend for the agent roster: `agents_registry.py` justified the three base agents by DERIVE
being "REAL but UN-ADDRESSED — the `settle` GESTURE, not a colleague you talk to." That
argument gets **stronger**, not weaker: DERIVE is now un-addressed in the fuller sense — no
verb at all, just an ask. It was never a seat.

## 4. Consequences

**Positive.** The service model stops asserting a flow the product does not have. The launcher
resolves honestly (three acts + the record's mirror + the management plane) instead of
force-fitting five `primary` surfaces into two verbs. The growth rule makes a fourth act cheap
to reason about and a new app free. One metered route, one button, one portal chain and one
dead instrument leave the codebase. The "settle" concept survives where it was always true —
as ESSENCE's *moat statement* ("the system of record where human and AI work **settles**",
ADR-414 D1, unchanged), which is a property of the record, not a verb in a workflow.

**Costs, stated.** The retrieval gap in D4 is now uncovered — a member's asked-for note is not
searchable until embedding is decided. The felt "episodic becomes cumulative" moment loses its
on-screen instant; the remaining staged moments (trace · correct-once · leave-with-everything)
carry that job, and they are demonstrations rather than acts. If distillation-by-asking proves
unreliable in practice (the model declining, misplacing, or not citing), the answer is
envelope work — not a restored button.

**Reversibility.** The service is deleted, but the shape is recoverable from this ADR + git
history if `think ⇄ make` proves wrong. The falsifiers that would tell us (1 and 3) are live.

## 5. Key files

`api/services/settle.py` (**deleted**) · `api/test_settle_verb.py` (**deleted**) ·
`api/routes/lanes.py` (the route deleted; two comments re-pointed) ·
`api/services/falsifiers.py` (falsifier 2 retired with its reading recorded) ·
`api/services/agents_registry.py` (the DERIVE derivation re-cut) ·
`web/components/chat-surface/{LanePanel,ChatSurface,ConversationHeader}.tsx` (button + portal
chain) · `web/lib/api/client.ts` · gates: `test_w0_falsifiers` (asserts the tombstone),
`test_adr495_conversation` (reader enumeration), `test_adr445_cap_choke_point` (one choke
point, not two) · `docs/ESSENCE.md` (v17) · `docs/architecture/FOUNDATIONS.md` (DP29 fifth
amendment) · `api/prompts/CHANGELOG.md`.
