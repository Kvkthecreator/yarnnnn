# Studio validation pass — operator click-pass checklist (2026-07-22)

**Hat B.** You drive Chrome (a sandboxed iframe is un-automatable from the agent
side); I consume findings and fix in Hat A. Run against the live workspace
(`kvkthecreator@gmail.com`, ws `d5b9029b`) once the `ad32e75` deploy is green.

For each item: **PASS** / **FAIL** + one line of what you saw. A screenshot on
any FAIL. Don't fix anything — just observe; ambiguity is data.

---

## 0. Deploy freshness (do this first)
Open any deck artifact → DevTools → in the canvas iframe's console:
`document.querySelector('style')?.textContent.includes('yarnnn-selbox-editing')`
→ **true** means the P11+ bundle is live. If false, the deploy hasn't
propagated; wait and hard-refresh before continuing (stale bundle fabricates
"defects").

---

## 1. ⭐ A.2 — the second-click-to-edit deviation (HIGHEST VALUE)
The core select→edit gesture on a staged frame. **This is the one I most need
disambiguated** — I've read the code and both suspects produce identical paths
until you see where click 2 lands.

Open a **deck** (`ir-deck` or `prd`) OR the **canvas** (`test-page` is flow, not
staged — use a deck/canvas). Pick a **text** block (a heading or paragraph).

1. **Click once** on the text block.
   - Expected: a bounding box + 8 handles + move band appear; **no caret**, no
     text cursor blinking.
   - → PASS / FAIL: _______
2. **Click a second time** on the *same* text block (same spot, ~1s later).
   - Expected: caret enters text at the click point; border goes dashed.
   - → PASS / FAIL: _______
3. If step 2 FAILED (no caret): **where did the second click land?** Move the
   mouse slowly — is there a ~9px-wide invisible strip near the block's border
   (top/bottom/left/right) where the cursor becomes a **move** cursor (✛)? Click
   the *dead center* of the text instead and report if THAT enters edit.
   - → center-click enters edit? YES / NO: _______
   - → cursor near border is "move"? YES / NO: _______
4. **Double-click** the text block directly (from unselected).
   - Expected: enters edit immediately.
   - → PASS / FAIL: _______

**Why these sub-questions**: if center-click works but near-border doesn't →
the `.yarnnn-selmove` strips (proj.ts :834-838, 9px bands) are eating click 2 →
fix = shrink/inset the strips or let a click *through* them re-hit the block. If
center-click ALSO fails → `cur` is being reset between clicks (re-projection or
a selection race) → fix is in the click ladder's `cur === blk` state, proj.ts
:457-460.

---

## 2. The new PNG export (JUST SHIPPED — never live-smoked)
Open an **IMAGES stage** (compose a real ad first if none exists, or open an
existing composed stage). Design tab → Export group.

1. A **"Download PNG"** button is present (Studio decks must NOT show it —
   check a deck's Export group has only Print/PDF + AI reference).
   - → PASS / FAIL: _______
2. Click **Download PNG**. Button shows "Rendering…" then a PNG downloads.
   - → PASS / FAIL: _______
3. **Open the downloaded PNG. Fidelity check** (the named §13 risk):
   - Generated hero image present + not blank/black? _______
   - Gradients render (not banded/missing)? _______
   - Webfonts correct (not fallback serif/sans)? _______
   - `object-fit` images not stretched/cropped wrong? _______
   - Text legible on its ground (the dark-on-dark fix held)? _______
   - Dimensions ≈ 2× the stage (e.g. 2400×1256 for a 1200×628 ad)? _______
4. If the hero is **blank/black**: the cross-origin re-inline failed. Console
   errors mentioning `tainted`, `SecurityError`, or a failed `fetch` to a
   supabase URL? Paste them. _______

---

## 3. The five template representatives load + select (P8–P12 debt)
For EACH — `ir-deck` (deck) · `prd` (deck) · `test-article` (article) ·
`test-page` (page) · a canvas/IMAGES stage:

- Opens to a **rendered** canvas (not a blank white frame)? _______
- Clicking a block shows selection chrome appropriate to its mode
  (staged → box+handles; flow → outline)? _______
- Typing in a text block works + persists after clicking away? _______

(Blank-white-on-open was a RESOLVED P12 investigation, but the export ship
touched the same StudioSurface — re-confirm none regressed.)

---

## 4. Undo/redo (shipped de85711, also un-smoked)
On a deck: make a text edit → **⌘Z** reverts it → **⌘⇧Z** re-applies.
- Text edit undo/redo: PASS / FAIL: _______
- A geometry move (drag a block) → ⌘Z reverts the move: PASS / FAIL: _______
- ⌘Z while caret is IN text does native caret-undo first (not our stack): PASS / FAIL: _______

---

## Findings summary (fill after the pass)
- A.2: _______
- Export: _______
- Templates: _______
- Undo: _______
- Anything unexpected: _______
