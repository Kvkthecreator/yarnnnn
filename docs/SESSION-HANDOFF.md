# Session handoff — 2026-08-09 (streamlining lane)

**ADR-539 committed+pushed this session.** Phases 2–5 of the operator-ratified
streamlining arc remain (see §2).

## 1. ⚠️ A concurrent ADR-540 lane's UNCOMMITTED work was surgically preserved

A concurrent session holds uncommitted "ADR-540 flow-retire" work
(`flowDead` flag + `yarnnn-flow-retire` handler in projection.ts, a sender in
StudioCanvas.tsx). To commit ADR-539 without sweeping that lane's lines, its
hunks were separated at the operator's direction ("surgically separate") and
**restored to the working tree after the push** — the tree should show them as
the only uncommitted changes. Backups if anything is missing:
`/private/tmp/claude-501/-Users-macbook-yarnnn/c6faf054-67aa-4660-b6c6-c5c798bd3a71/scratchpad/`
(`theirs-adr540-canvas.patch` · `projection-both-lanes.patch` · plus a
`git stash` entry `theirs-adr540-canvas`). That lane still owes its own ADR
doc + gates + commit. **The selection-algebra ADR must take the next FREE
number — 540 is claimed by that lane's code comments.**

## 2. The remaining arc (operator-ratified, delegated in full)

1. ⬜ **Selection algebra** (the big one): one selection payload
   {tier, subject, set, setKind, chain}, exported `scopeOf`/`arityOf` as the
   ONLY derivation sites, unify rangeBlockIds+groupIds, set-aware right-click
   menu + runtime keyboard (⌫ over an object set currently deletes ONE —
   data-loss-shaped), span-aware structure ops (both benchmarks demand them:
   Google Docs applies heading across a multi-paragraph range; Notion turns-
   into across a set). Amends ADR-528 D7 corollaries + the d878242 rule.
2. ⬜ Token `(scope, grain)` split (AUTHORING.md's owed refactor) + repair the
   pre-existing `test_adr453` `valid_applies` failure there + dead-chrome
   hygiene (mobile "Outline" tab dead on Docs; always-empty pathRow/contents
   computed on flow).
3. ⬜ ADR-518 §6 housing rename (app-neutral kernel names) — trigger fired per
   the audit; pure-hygiene commit, last.
4. ⬜ Canon: AUTHORING.md block-descriptor table + the one outline rule;
   ADR-LEDGER entries; gitbook sweep (member docs drift silently — the
   ADR-526 lesson).

## 3. OWED

1. **ADR-539 click-pass** (browser lane, human or E2E): paste an h4/h5
   heading into Docs → lands as h3 AND appears in OUTLINE; the Typography
   select reports its rung (not "Text"); the crumb shows h3 ancestors; `/` →
   Chart opens the CSV picker; Turn into offers the same set from pane and
   right-click; a kind the registry marks non-convertible (component) is
   offered nowhere.
2. Inherited: ADR-538 click-pass (needs a CSV in the workspace first) ·
   ADR-536 (single-caret align/indent) · ADR-537 share-sheet tabs · the prod
   OAuth-state error (ADR-531 territory, uninvestigated).
3. `extract_outline` now emits h3 (and indents by rung) into the lane
   posture — no freddie_agent.py change, so no prompt CHANGELOG entry; if a
   posture-size ratchet moves, this is why.

## 4. Verification state at commit

test_adr539 36/36 (falsifiers executed) · adr539.mjs 16/16 · test_adr443
182/182 · test_adr538 59/59 · test_adr536 31/31 · test_adr528 25/25 ·
adr526.mjs 37/37 (mock DOM now honours the selector — the audit's gate-blind-
spot paid) · adr525.mjs 36/36 · adr482_flow_promote 19/19 (harness carries the
clamp constants) · full FE battery green except adr527 (1 fail, pre-existing
at baseline, verified by stash) · `tsc` exit 0 · `next build` clean on the
exact tree committed. The 15 stale-red studio gates at `main` predate this
lane; `test_studio_layout_mode` left that set (now 36/36 green).
