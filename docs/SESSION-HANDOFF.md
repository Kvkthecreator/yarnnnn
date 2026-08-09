# Session handoff — 2026-08-09 (streamlining arc COMPLETE, phases 1–5)

`origin/main` @ the canon commit absorbing this file. The operator-ratified
hierarchy/docs-app streamlining shipped in full this arc:

| Phase | ADR | Commits |
|---|---|---|
| 1 | ADR-539 — the vocabulary declares behavior | `bd9fa10` + `8212add` |
| 2 | ADR-541 — the selection algebra | `b8936b2` + `9d590a8` (+ canon `053ae5f`) |
| — | ADR-540 — flow-retire (concurrent lane, click-passed on prod) | `0a4d4fd` |
| 3 | ADR-542 — token scope × grains + dead-chrome sweep | `f271bc7` + `5ebc300` |
| 4 | ADR-518 §6 housing rename (kernel → `authoring`) | `759eefe` |
| 5 | Gitbook/member-docs sweep + LEDGER + this handoff | the absorbing commit |

## 1. The state of the gates (the receipt that matters)

- **Full FE battery: 22/22 mjs gates green** (run from REPO ROOT — from
  `web/` every gate crashes on its readFileSync paths and prints only the
  node version; do not misread that as results).
- **py battery green except four CONFIRMED-BASELINE reds** (each verified by
  stash or worktree at the pre-arc commit): `test_adr456_studio_wave2`
  ("one door" spelling), `test_adr462` 52/54, `test_adr466` 75/78,
  `test_adr459` (its pinned crumb spelling left the Surface before this arc).
  The stale-red set shrank 15 → 4 this arc: `wave1` (crashed on KeyError:pad
  since ADR-516!), `453` (valid_applies), `521`, `layout_mode`, `wave3` all
  repaired WITH receipts in their re-cuts.
- `tsc` clean; `next build` clean at every push.

## 2. Landmarks for the next session

- **The kernel vocabulary lives at `api/services/authoring.py`** and the
  shared FE surface at `web/components/authoring/` (the `759eefe` rename).
  Identifiers (`STUDIO_BLOCKS`, `StudioSurface`, …) and wire paths
  (`/studio/*`, `studio.file`) are DELIBERATELY not renamed — that boundary
  is stated in the commit and the LEDGER; re-opening it needs an ADR.
- One derivation home per question now exists and is gate-defended:
  `selection.ts` (`unify`/`scopeOf`/`arityOf`) · `tokenGrammar.ts`
  (`admits`) · the registry's behavior fields + `HEADING_RUNGS`. If a new
  hand-list or inline derivation appears in review, it is re-opening a paid
  debt.
- `services/studio_arrangement_plan.py` KEEPS its name (arrangement
  machinery, not the kernel) — a greedy rename swept it once and was caught;
  don't "fix" it.

## 3. OWED — click-passes (browser lane; gates prove the room, not the doorway)

1. **ADR-541** (the big one): drag a range across 3 paragraphs → ramp +
   Turn into + align/indent MOUNT; pick "Heading 2" → all 3 convert, one
   ⌘Z restores; ⇧-click 3 objects → ⌫ deletes 3 ("Delete 3 blocks" in the
   menu); right-click during the set → Move/stacking withdrawn with the
   count. **Verify the range survives a right-click** (gate-unverifiable
   ordering constraint; if menu-open collapses the range, the span rows
   won't mount).
2. **ADR-539**: paste an h4 → lands as h3, appears in OUTLINE, Typography
   reports its rung; component absent in Docs + Turn into.
3. **ADR-542**: on Docs mobile (<md) there are TWO tabs (Canvas · Chat) —
   no dead Outline tab; on a deck slide the pane still offers size/x/y
   (staged grain) and a figure offers height/fit (media grain).
4. Inherited: ADR-538 share-view motion + component render check ·
   ADR-537 share sheet · the prod OAuth-state error (ADR-531 territory,
   STILL uninvestigated).

## 4. Also owed / open

- The four remaining baseline reds (§1) are the stale-red repair lane's.
- `metrics` citing a CELL (the defensible-KPI question) still wants its own
  ADR (needs sub-file addressing — the ADR-528 finding).
- ESSENCE/gitbook were swept for the roster + selection copy; a fuller
  member-docs pass (screenshots etc.) was not attempted.
