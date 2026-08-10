# Session handoff — 2026-08-10 (ADR-546 the rung law, phases 1–5 landed)

`origin/main` @ `14da77c`+. The ADR-544 handoff is absorbed below where items
remain open.

> **Correction (2026-08-10, ADR-544 lane).** An earlier revision of this file said
> the heal `--execute` and the rotated-key item were "explicitly descoped by the
> operator". That was wrong, and the receipts are below: the operator updated the
> key, and **the heal RAN to completion** — 4 decks, 48 Areas named, 73 blocks
> re-homed, 1 position cleared, verified 0 block-ids and 0 words lost. Both items
> are CLOSED, not descoped. See §1b.

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

## 1b. The ADR-544 lane — CLOSED except its click-pass

Ran in parallel with ADR-546 (they are complements: 544 is the PAGED containment
law, 546 the flow rung law). Commits, in order — every one is on `main`:

| Commit | What |
|---|---|
| `d016286` | **ADR-544** — the containment law: Slide → Layout → Area → Block |
| `d8c528b` | D7 — an un-healed region reads "Area", not "Group" (the operator's click-pass caught this) |
| `fb891be` | D6.1 — the AI re-arrange speaks Areas, and its apply path finds them |
| `1a220b1` | D2 — bump the kernel CSS version so the Area selectors actually retrofit |
| `cedfc2f` | D5.1 — the sibling rule locks; the refusal is said |

**The heal RAN** (`api/scripts/oneshot/adr544_heal_containment.py --execute`,
2026-08-10): 4 decks — `ir-deck-v3`, `ir-deck-yarnnn-march-2026-v5`,
`test-deck-2`, `yarrnnnn-decl` — 48 Areas named, 73 blocks re-homed, 1 position
cleared. Verified before and after: **0 block-ids lost, 0 words lost**; post-heal
the substrate carries zero bare blocks, zero `data-slot` markup, zero `data-x`.
Each artifact got an attributed, revertible revision (ids in the run output).
The script is idempotent — re-running it now is a no-op.

**Two operator decisions were ratified into the ADR** (read them there, §D5.1 and
§5):
- **D5.1 — the sibling rule LOCKS, no align/distribute carve-out.** *"The cross
  container drag illegal IS correct."* Enforced at set FORMATION (the ⇧-click
  gates on a shared Area and posts `yarnnn-refused`), not withdrawn afterwards.
- **Re-arrange: content invariant, structure subject.** *"Enforce content is
  sustained, all else is subject (blocks themselves)."* This makes ADR-519 D2.1's
  group-dissolve question moot on decks rather than open.

**Defects this lane found in its own work, all now gated** — the pattern is worth
carrying: each shipped GREEN and never mounted.
1. the label ladder had no legacy `data-slot` rung while every other region
   consumer did (`d8c528b`);
2. `applyArrangementPlan` read `[data-slot]` alone while its sibling read both,
   so the AI plan refused silently and looked like "the router is off" (`fb891be`);
3. the kernel CSS was rewritten without bumping `STUDIO_KERNEL_CSS_VERSION`, so
   the new selectors reached zero existing artifacts (`1a220b1`);
4. `withdrawalNotice` (ADR-541 D4) was exported with ZERO importers — the one
   notice was computed and never mounted (`cedfc2f`).

**OWED (this lane): the click-pass only.** On a HEALED deck the crumb should read
`Slide 2 › Body (left)` — `Area` means un-healed, `Group` means a label rung
regressed, `main`/`side` is a D4 leak. Also: ⇧-click across two Areas must refuse
WITH a visible notice; a drag must re-order within its Area and never float; and
the AI re-arrange must actually land (a silent fall-through to the mechanical
ladder is visually identical to success — watch the "Refining…" state).

**Theme 5's surface half is the one open DESIGN question** (§4).

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

**THE ONE OPEN DESIGN QUESTION — Theme 5's surface half (ADR-544).** The *rule* is
settled (content invariant, structure subject — §1b); what is NOT is what the
member is TOLD before a re-lay restructures their slide. Today a re-arrange can
move every block into different Areas, dissolve authored groups, and clear
block-level geometry, and the only thing said beforehand is the arrangement's own
thumbnail. There IS in-canon precedent to follow rather than invent: ADR-519 D2.1
made the gallery thumb say *"ungroups 2 groups"*, on the principle **say it where
the choice is made**, naming the least recoverable consequence FIRST. The
question is whether that one note now covers enough — group dissolution, carried
content that lands in a different Area, cleared geometry — or whether a re-lay
that will restructure N blocks deserves a fuller pre-commitment statement. It is
a genuine design call, cheap to implement either way, and it is the last thing
ADR-544 left open. Related: ADR-468 D4 (a composition must never dead-end) and
the ADR-466 D5 carried-content note.

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
