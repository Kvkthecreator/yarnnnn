# Session handoff — 2026-08-10 (ADR-546 the rung law, phases 1–5 landed)

`origin/main` @ `14da77c`. The ADR-544 handoff is absorbed below where items remain
open. **Ignore the ADR-544 heal `--execute` and the rotated-key item** — the
operator has explicitly descoped both.

## 1. What landed this session — ADR-546

Audited, drafted, ratified and implemented in one arc. The audit was made against
a **22/22 green battery** — five arcs for five, this layer's defects are found by
driving the doorway.

**Docs' fault is the INVERSE of ADR-544's.** ADR-544 found two substrate concepts
wearing one word. Docs had ONE concept — *depth* — wearing **three spellings**,
all shipped, all depth-3, with readership of six consumers / one / **none**:

| spelling | read by |
|---|---|
| `h1/h2/h3` (`HEADING_RUNGS`) | outline, crumb, ramp, turn-into, AI posture, clamp |
| `data-indent="1..3"` (a served token) | ONE pane row, no keyboard entrance |
| `ul ul ul` (kernel CSS, 3 levels) | **nobody** |

The third having no reader is why **Tab could author a hierarchy nothing could
name**. And Tab meant two unrelated things by accident of tag: nest in an `<li>`,
a literal **tab character** in prose.

| D | Decision |
|---|---|
| D0 | **Document → Rung → Block → Range**; no container, no page grain, by derivation |
| D1 | One rung, two spellings; the token values + nesting CSS **generated** from `FLOW_RUNGS` |
| D2 | The floor stays the BLOCK — an `<li>` never gains identity |
| D3 | A span is a SHAPE — a heading-led range is a subtree, derived in `selection.ts` |
| D4 | Tab steps the rung; **the literal-tab branch is deleted** |
| D5 | No `Slide`/`Group`/raw attribute on flow — ADR-544 F2 made **symmetric** |
| D6 | `pathRow`'s "always null on flow" premise **gated**, not assumed |
| D7 | **No heal** (deliberately unlike ADR-544 D7) — nothing here makes markup illegal |

**The fork was refused, with the measurement** (§2.3). The operator raised a hard
Docs/Studio app fork. Not one of the seven audit findings was "shared machinery
forced Docs into a Studio shape" — every one was machinery that **failed to
branch**, or a Studio fix written **one-directionally**. A fork fixes none and
duplicates all. **The law forks; the machinery stays one implementation.**

## 2. The state of the gates

- **23/23 FE mjs gates green** (run from REPO ROOT — from `web/` every gate
  crashes on its readFileSync paths and prints only the node version).
- **5/5 authoring py gates green** (adr521 · adr528 · adr536 · adr539 · adr544).
  These are **script-style, not pytest** — run `python3 test_x.py` directly;
  pytest INTERNALERRORs on their module-level `sys.exit`.
- **`next build` exit 0.** The one warning is the pre-existing Sentry vendor ESM
  issue, unrelated.
- **New gate `adr546_rung_law.mjs` — 46/0.** It EXECUTES the extracted
  `labelForElement` ladder and the `regionOf`/`arrangeOf` derivations rather than
  grepping. All six decisions were falsified and restored.
- **Three existing gates repaired because they PINNED A SPELLING** — third
  occurrence of the ADR-544 lesson: `adr519`'s `slot: dslot`, `adr527`'s literal
  `[data-indent="1"]` rule and its `formatSegments` window. All re-cut to assert
  behaviour; the indent one **re-falsified** (a custom property in place of the
  static step still reddens it). ⚠️ **If you touch this layer and a gate goes red
  on a spelling, that is the gate's bug.**
- `adr521`'s interpolation ENUMERATION took the two new constants — that gate did
  exactly its job. That is the difference between pinning a spelling and defending
  a rule.
- **Baseline py reds — 6, all confirmed by stash at `e78b705`:**
  `adr459_artifact_identity`, `adr462_context_menu`, `adr466_mode_native`,
  `adr485_measure_frame`, plus **`adr469_name_is_lifted`** (`KeyError: 'document'`)
  and **`adr477_block_keyboard`** (`FileNotFoundError` on a `studio/StudioCanvas.tsx`
  path that moved in the ADR-518 rename). The last two are **stale post-ADR-518
  references** and were not on the previous handoff's list — they are cheap fixes
  for whoever wants them, not regressions.
- ⚠️ **DB-backed pytests cannot run in this shell** (401 regardless of the tree).
  Only static gates are meaningful here.

## 3. OWED

1. **The click-pass — the load-bearing one.** ADR-546 §7 names it as gating D2:
   - **Tab-nest a bullet three deep**, then **select across a heading and its
     body** and read what the pane calls it. It should say *"<heading> and the N
     blocks under it"*, never a bare count.
   - **Tab in prose** must step the paragraph in (and ⇧Tab back out), three steps
     max, and must **never insert a tab character**.
   - Open a document and confirm nothing in the chrome says **Slide**, **Group**,
     **Area** or a raw kind (`PROSE`).
   - D2's "a list is one opaque block" reasoning is **from the code, not the
     gesture** — if a nested item turns out to want selecting, that reopens D2
     (and §5 names the evidence).
2. **The span READBACK.** `currentOf` resolves through one `selectedEl`, so over a
   mixed-alignment span the align/indent control shows the clicked block's value
   while writing to all of them — `d878242` at the *read* grain. Named in code and
   in the AUTHORING matrix; not fixed.

## 4. Also open (inherited, not this session's)

- ADR-544's click-pass; ADR-541 / 539 / 542 click-passes (the ADR-541 one is the
  big one — its "range survives a right-click" ordering constraint is
  gate-unverifiable).
- ADR-538 share-view motion + `component` render check; ADR-537 share sheet;
  ADR-535 click-pass + D4 rung; ADR-534 per-redemption history.
- The prod OAuth-state error (ADR-531 territory) — STILL uninvestigated.
- `metrics` citing a CELL wants its own ADR (needs sub-file addressing).
- **GLOSSARY has no ADR-544 grain entries** — ADR-546 added a per-medium authoring
  section covering both media, which pays that debt as a side effect. If Studio
  wants its own deeper entries they go there.

## 5. Landmarks

- **`Rung` is overloaded.** ADR-380's activation **Rung 0·1·2** (workspace
  activation) and ADR-546's authoring **Rung** (a document's depth grain) are
  unrelated. The GLOSSARY section disambiguates them explicitly — read it before
  using the word in canon.
- One derivation home per question, gate-defended: `selection.ts`
  (`unify`/`scopeOf`/`arityOf`/**`spanShapeOf`**/`spanLabel`) · `tokenGrammar.ts`
  (`admits`) · `structureLabels.ts` (`labelForElement`/`areaLabel` — now
  **mode-aware**) · `projection.ts`'s `regionOf`/`arrangeOf` (the paged-grain
  guard) · the registry's behavior fields. A new hand-list is a paid debt re-opened.
- **The kernel's rung CSS is GENERATED** (`_rung_css`/`_nest_css` in
  `services/authoring.py`). Editing the stylesheet text by hand re-opens §1.1.
  Output was verified byte-identical to what it replaced, so no
  `STUDIO_KERNEL_CSS_VERSION` bump was owed — but **a real CSS change needs one**.
- ⭐ **Backticks are illegal in the runtime templates** (`projection.ts` — they are
  module-level template literals). This bit **three times** in this arc alone; the
  ADR-546 gate now guards **every** runtime template, not ADR-519's one region.
- `services/studio_arrangement_plan.py` KEEPS its name; identifiers
  (`STUDIO_BLOCKS`, `StudioSurface`, …) and wire paths (`/studio/*`) are
  DELIBERATELY not renamed — re-opening that boundary needs an ADR.
