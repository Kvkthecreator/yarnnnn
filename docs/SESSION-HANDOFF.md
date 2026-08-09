# Session handoff — 2026-08-09 (streamlining lane)

`origin/main` @ `9d590a8` (+ the canon commit that absorbs this file). Shipped
this arc: **ADR-539** (`bd9fa10`+`8212add`) and **ADR-541** (`b8936b2`+`9d590a8`)
— phases 1–2 of the operator-ratified hierarchy/docs-app streamlining.

## 1. ⚠️ The concurrent ADR-540 lane (flow-retire) is STILL UNCOMMITTED

Its work sits in the tree across `projection.ts` (flowDead + yarnnn-flow-retire
handler), `StudioCanvas.tsx` (+25), and `StudioSurface.tsx` (4 hunks:
retireFlowCommits state block · the applyOp call · a dep entry · the
flowRetire prop). It was **surgically separated and restored twice** so the
ADR-539/541 commits carry none of its lines; restoration references live in
the scratchpad (`theirs-adr540-surface-hunks.md`, `theirs-adr540-canvas.patch`,
`projection-both-lanes.patch` at
`/private/tmp/claude-501/-Users-macbook-yarnnn/c6faf054-67aa-4660-b6c6-c5c798bd3a71/scratchpad/`).
That lane owes its own ADR doc, gates, and commit. **ADR-540 stays reserved
for it**; note `test_adr521_flow_format_tier`'s interpolation set will need
`+0` entries from it (its hunks add no `${`), and the adr484 harness may need
its new message type registered if it grows chrome.

## 2. Remaining phases (operator-ratified, delegated)

1. ⬜ **ADR-542 — token `(scope, grain)` split**: pay AUTHORING.md's carried
   follow-on (`applies` conflates the two axes); repair the PRE-EXISTING
   `test_adr453` `valid_applies` failure there (stale since ADR-525 —
   deliberately left visible by the 538 lane); dead-chrome hygiene: the
   mobile "Outline" tab renders on Docs while its pane content is
   `isPaged`-unmounted (dead tab), `pathRow`/`contents` are structurally
   always-empty on flow but computed every render, and the served `group`
   field has no FE consumer (keep serving, note it is display-only).
2. ⬜ **ADR-518 §6 housing rename** (app-neutral kernel names — studio.py,
   /studio/vocabulary, StudioSurface/StudioDesignTab etc.). Trigger fired per
   the audit; pure hygiene, LAST, and only when no concurrent lane is mid-
   flight in those files.
3. ⬜ **Gitbook/member-docs sweep** (the ADR-526 lesson: member docs drift
   silently) + ESSENCE touchpoints if the copy names selection behavior.
4. ⬜ The 14 remaining stale-red studio gates at `main` (pre-existing lane;
   `test_studio_name_is_one_fact` 31/32 confirmed among them at `7d81029`).

## 3. OWED — click-passes (browser lane; gates prove the room, not the doorway)

1. **ADR-541**: drag a range across 3 paragraphs → Typography ramp + Turn
   into + align/indent all MOUNT; pick "Heading 2" → all 3 convert, ONE
   revision (one ⌘Z restores); ⇧-click 3 objects on a deck → ⌫ deletes all 3
   (menu says "Delete 3 blocks"); right-click during the set → Move/stacking
   rows withdrawn with the count notice. Verify the range survives a
   right-click (the ADR names this ordering constraint as the click-pass's
   focus — if the menu-open collapses the range, the span rows won't mount).
2. **ADR-539**: paste an h4 into Docs → lands as h3, appears in OUTLINE,
   Typography select reports its rung (not "Text"); `/` → Chart opens the CSV
   picker; component offered in Studio, absent in Docs, absent from Turn into.
3. Inherited: ADR-538 (CSV chart — upload a CSV first) · ADR-537 share sheet ·
   ADR-536 (subsumed by the 541 pass: align/indent now spans BY DESIGN — the
   old "withdraws over a multi-block range" instruction is obsolete) · the
   prod OAuth-state error (ADR-531 territory, still uninvestigated).

## 4. Verification state

ADR-541: adr541.mjs 21/21 (unify/arityOf executed, precedence falsifier) ·
adr528 re-cut to execute the ONE home 27/27 · adr527 59/59 (its baseline red
row went green under the new invariant) · adr519_d41 41/41 · test_adr536
31/31 · test_adr462 52/54 = baseline. ADR-539: test_adr539 36/36 · adr539.mjs
16/16 · test_adr443 182/182 · test_adr538 59/59. `tsc` exit 0 · `next build`
clean at both pushes. **One shipped regression caught and repaired in the
canon commit**: ADR-539's paste clamp added two declared interpolations to
EDIT_SCRIPT and `test_adr521`'s `count("${") == 1` pin went red at `8212add`;
re-cut to the enumerated-constants invariant (35/35). Lesson: the radar's
"targeted pytest gates" must include `test_adr521` whenever projection.ts's
templates change.
