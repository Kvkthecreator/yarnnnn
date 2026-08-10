# Session handoff — 2026-08-10 (ADR-544 containment law, phases 1–6 landed)

`origin/main` @ `d016286`. The streamlining arc (ADR-539/540/541/542 + the
ADR-518 §6 rename) closed in the prior session; its handoff is absorbed below
where items remain open.

## 1. What landed this session — ADR-544

Found by driving a live deck (`operation/ir-deck-v3/deck.html`) through the
doorway, not by a gate. **Every §1 defect was invisible to a green battery.**

| D | Decision |
|---|---|
| D1 | Containment is total — no block is a direct child of a page (gated) |
| D2 | `.cols`/`.col` + `data-slot` collapse into **Area**, typed by role |
| D3 | Position IS Area + order; deck `x/y/z` re-grained to **`artboard`** |
| D4 | One label derivation — the registry's word, never the attribute's |
| D5 | Selection re-cut onto the new grains (cross-Area range now illegal) |
| D6 | Re-lay maps Area→Area **by role**, not by free-form name |
| D7 | Existing decks healed, not grandfathered |

**Vocabulary: Slide → Layout → Area → Block.** Three of four words are the
operator's. "Section" was REFUSED with receipts (ADR-526/AUTHORING rule 12 make
it the span between headings; there is a standing `<section>`-wrapper refusal;
and `<section>` is the slide's own tag). "Object" refused — already a selection
TIER. Typing Areas by content (title/subtitle/body) was refused in §2.2: it
duplicates what the block declares and breaks on "multiple subtitles".

## 2. The state of the gates

- **22/22 FE mjs gates green** (run from REPO ROOT — from `web/` every gate
  crashes on its readFileSync paths and prints only the node version; do not
  misread that as results).
- **`next build` clean.** The one warning is a pre-existing Sentry vendor ESM
  issue, unrelated.
- **Seven stale gates repaired at their named homes.** Three carried the `slots`
  key. **Three PINNED A SPELLING** and so read a vocabulary change as a
  violation — `adr461`'s literal selector string, `adr520`'s `walkContents`
  signature, `adr485_measure_frame.mjs`'s `MEASURE_GRAINS` literal. All three
  were re-cut to assert BEHAVIOUR (a set, a name, an invariant). If you touch
  this layer and a gate goes red on a spelling, that is the gate's bug.
- **Baseline reds unchanged (7, all confirmed by stash at the pre-544 commit):**
  `adr466_mode_native`, `adr480_flow_editing_grain`, `adr482_flow_completion`,
  `adr485_measure_frame` (py), `adr456_studio_wave2`, `adr459_artifact_identity`,
  `adr462_context_menu`. None are ADR-544's.
- ⚠️ **DB-backed pytests cannot run in this shell** — `SUPABASE_URL`/service key
  are unset, so ~300 tests fail on 401 regardless of the working tree. Only
  static gates are meaningful here. Do not read that mass red as a regression.

## 3. OWED — the two things ADR-544 did not finish

1. **The heal's `--execute` run.** `api/scripts/oneshot/adr544_heal_containment.py`
   is dry-run-by-default and was verified EXECUTED on synthetic pre-544 markup
   (inside the gate, with falsifiers), but never run against real substrate —
   blocked on the missing DB credentials above. Run the dry run FIRST and read
   its per-file counts before `--execute`. It heals deck+web only; an IMAGES
   stage and a flow document come back byte-identical (gated).
2. **The browser click-pass** (the load-bearing one — gates prove the room, not
   the doorway):
   - open a pre-544 deck → confirm the pane header says **Text**, not PROSE, and
     the breadcrumb reads `Slide 2 › Body (left)`, not `slide 2 › columns › main`;
   - drag a heading → it must re-order within its Area and **never float free**;
   - re-arrange a two-column slide → content maps body→body by role;
   - the ADR-541 range case: drag a selection from one column into another — it
     must not produce a set the pane cannot describe.

## 4. Also open (inherited, not this session's)

- ADR-541 / 539 / 542 click-passes (§3 of the prior handoff) — the ADR-541 one
  is the big one; its "range survives a right-click" ordering constraint is
  gate-unverifiable.
- ADR-538 share-view motion + `component` render check; ADR-537 share sheet;
  ADR-535 click-pass + D4 rung; ADR-534 per-redemption history.
- The prod OAuth-state error (ADR-531 territory) — STILL uninvestigated.
- `metrics` citing a CELL wants its own ADR (needs sub-file addressing — the
  ADR-528 finding; ADR-544 D6 does not address it).

## 5. Landmarks

- The kernel vocabulary lives at `api/services/authoring.py`; the shared FE
  surface at `web/components/authoring/`. Identifiers (`STUDIO_BLOCKS`,
  `StudioSurface`, …) and wire paths (`/studio/*`, `studio.file`) are
  DELIBERATELY not renamed — re-opening that boundary needs an ADR.
- One derivation home per question, gate-defended: `selection.ts`
  (`unify`/`scopeOf`/`arityOf`) · `tokenGrammar.ts` (`admits`) ·
  `structureLabels.ts` (`labelForElement`/`areaLabel` — ADR-544 D4) · the
  registry's behavior fields. A new hand-list here is a paid debt re-opened.
- `services/studio_arrangement_plan.py` KEEPS its name (arrangement machinery,
  not the kernel) — a greedy rename swept it once and was caught.
