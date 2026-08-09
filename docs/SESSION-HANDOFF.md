# Session handoff — 2026-08-09 (streamlining + flow-retire lanes)

`origin/main` @ `0a4d4fd`. Shipped this arc: **ADR-539** (`bd9fa10`+`8212add`),
**ADR-541** (`b8936b2`+`9d590a8`), the canon commit (`053ae5f`), and
**ADR-540** (`0a4d4fd`, the concurrent lane, now landed).

## 1. ✅ ADR-540 (flow-retire) — COMMITTED and pushed

**A retired document does not commit.** Found by driving the ADR-538 doorway on
production: inserting a chart did nothing. The block landed and was silently
reverted ~400ms later, HTTP 200 throughout, nothing in the console.

  05:23:36.797  Docs: insert chart …commitments.csv   block present
  05:23:37.324  Docs: edit document                   block GONE

**Not an ADR-538 defect** — `Table` is erased by the identical pair. Every cited
insert on flow (chart · table · image · gallery) had been reverting since the
flow session and the optimistic override began coexisting. Cause: the
re-projection tears the iframe document down, which fires ADR-480 D1's
`beforeunload` rescue commit, which reports a DOM predating the op. Fix: the
parent RETIRES the live document before the override advances (ordering is the
fix; a `useLayoutEffect` sender so it cannot race the projection). A patchable
op is exempt — ADR-524 D2 untouched.

Gate `web/scripts/gates/adr540_flow_retire.mjs` **25/25** (run from repo root),
3 falsifiers executed. `test_adr521` 35/35 (its hunks add **0** interpolations,
as this handoff predicted). `test_adr480` 26/30 and `test_adr482` 49/54 are
**pre-existing** — identical at baseline with the three files stashed.

⚠️ **The ADR-540 click-pass is OWED** (see §3.1): the fix is unobservable until
prod runs the new bundle, and it was pushed at the end of the session.

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

1. **ADR-540 — do this FIRST; it gates the other two.** Until it is confirmed,
   *every* cited insert on Docs is reverted, so an ADR-538/539 chart pass would
   read as a failure of those ADRs when it is this one. In Docs: `/` → Chart →
   pick a CSV → **wait 5s, then hard-reload**. The chart must still be there.
   Test bed left in place: doc `operation/untitled-document-2/document.html` +
   `inbound/uploads/operator/commitments.csv` (delete both after; the doc's
   prose reads `Start here.///` — those orphan slashes are this defect's own
   fingerprint, left by picks that landed nothing).
   Tell you are on the fixed bundle: the served chunks contain
   `yarnnn-flow-retire`. Falsifier: the pre-fix pair was `insert chart` →
   `edit document` ~400ms later; if `edit document` still follows and the block
   vanishes, the fix did not take.
2. **ADR-541**: drag a range across 3 paragraphs → Typography ramp + Turn
   into + align/indent all MOUNT; pick "Heading 2" → all 3 convert, ONE
   revision (one ⌘Z restores); ⇧-click 3 objects on a deck → ⌫ deletes all 3
   (menu says "Delete 3 blocks"); right-click during the set → Move/stacking
   rows withdrawn with the count notice. Verify the range survives a
   right-click (the ADR names this ordering constraint as the click-pass's
   focus — if the menu-open collapses the range, the span rows won't mount).
3. **ADR-539**: paste an h4 into Docs → lands as h3, appears in OUTLINE,
   Typography select reports its rung (not "Text"); `/` → Chart opens the CSV
   picker; component offered in Studio, absent in Docs, absent from Turn into.
4. Inherited: ADR-538 (CSV chart — upload a CSV first) · ADR-537 share sheet ·
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
