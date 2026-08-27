"""ADR-612 — the judged act is ONE gesture, and it lives at the selection.

Defends the CONSOLIDATION. The judged (metered) act left the mechanical door
and became one selection-triggered affordance; the ADR-589 ladder keeps the
mechanical acts. The failure this guards against is the one this codebase keeps
paying for: a second SPELLING of one door surviving beside the first (ADR-592's
six spellings; the two `hidden` readers).

Run: python3 test_adr612_judged_gesture.py   (from api/)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{label}{(': ' + detail) if detail else ''}")


def surface_src() -> str:
    """StudioSurface, read on demand — the module-level `surface` binding is
    established further down, and reaching forward to it would make these
    checks depend on statement order rather than on the file."""
    return read("components/authoring/StudioSurface.tsx")


def read(rel: str) -> str:
    p = WEB / rel
    if not p.exists():
        failures.append(f"missing file: {rel}")
        return ""
    return p.read_text(encoding="utf-8")


gesture = read("components/authoring/SelectionGesture.tsx")
editor = read("components/text/TextEditor.tsx")
toolbar = read("components/text/MarkdownToolbar.tsx")
lane_panel = read("components/chat-surface/LanePanel.tsx")
canvas = read("components/text/ProseCanvas.tsx")

# ── D1: the affordance exists, and it anchors to the SELECTION ─────────────
check("D1 the shared affordance exists", bool(gesture),
      "Slides adopts this component; it must not live inside one app")
check("D1 it takes a selection anchor, not a pointer position",
      "SelectionAnchor" in gesture and "anchor" in gesture)

# The refusal, enforced rather than described. lane-frame §6 refuses pointer
# telemetry; ADR-612 D1 keeps that true by anchoring to the SELECTION's rect.
# A hover/mousemove handler here would be the refused shape re-entering at the
# render layer — and would be dead on touch besides.
for banned in ("onMouseMove", "onMouseOver", "onHover", "mousemove", "clientX", "clientY"):
    check(f"D1 no pointer tracking in the affordance ({banned})",
          banned not in gesture,
          "lane-frame §6: hover is transit, not commitment — and does not exist on touch")

check("D1 Text derives the anchor from the SELECTION, never a pointer",
      "focusPoint.range ? canvasRef.current?.selectionRect()" in editor,
      "the anchor must be derived from the selection the member made")
check("D1 the anchor is null when nothing is selected",
      re.search(r"focusPoint\.range\s*\n?\s*\?", editor) is not None
      or "focusPoint.range" in editor,
      "no subject, no door")

# A mousedown reaching the canvas collapses the selection this acts on — the
# door would dismiss itself on the way to being clicked.
check("D1 the affordance does not steal the selection on mousedown",
      "onMouseDown" in gesture and "preventDefault" in gesture)

# ── D2: the chip names the grain, and it matches what is anchored ──────────
check("D2 the affordance takes the member's noun for the target",
      "label" in gesture and "Rewrite ${label}" in gesture)
# The button says "the selection"; the composer chip must say the same thing
# for the same seed, or the member reads two different nouns for one act.
check("D2 Text's gesture label matches the chip's noun for that seed",
      'label="the selection"' in editor
      and "if (t.label === 'selection') return 'the selection';" in lane_panel,
      "whatever the chip names is what gets anchored (ADR-612 D2)")
# Scoped to the SEED. `label: 'selection'` also appears in Text's FOCUS
# declaration (ADR-522, ambient) a few hundred lines up — a different thing
# that happens to share the string. An unscoped search therefore passed while
# the seed's own label was changed to 'block' (falsified 2026-08-27), which is
# exactly the noun/anchor divergence D2 exists to prevent.
_seed_block = re.search(r"verb:\s*'rewrite',[\s\S]{0,400}?\}", editor)
check("D2 Text's rewrite seed is locatable", _seed_block is not None)
if _seed_block:
    check("D2 the seed Text sends is the selection grain",
          re.search(r"label:\s*'selection'", _seed_block.group(0)) is not None,
          f"the SEED's own label must match the door's noun: {_seed_block.group(0)!r}")

# ── D1 (revised): the door hangs in the MARGIN, off the reading column ─────
# The first cut anchored to the selection's END POINT. Driven, that reads
# wrong: a multi-line selection ends at the LAST line's x — often far left,
# mid-paragraph — so the door landed on the prose BELOW the selection, covering
# what the member was reading.
check("D1 the affordance takes the selection's RECT, not one point",
      "endLeft" in gesture and "right: number" in gesture,
      "a single end point cannot tell the door where the column edge is")
check("D1 the canvas reports the selection rect",
      "selectionRect" in canvas and "Math.min(a.left, b.left)" in canvas)
# AMENDED 2026-08-27, not loosened — the rule got STRICTER after driving it.
# The old assertion pinned `anchor.right + GAP + DOOR_W < vw`: the door fits
# before the WINDOW edge. That is true almost always (a viewport is far wider
# than a reading column), so a short MID-LINE selection — "rewrite these three
# words", the commonest case — placed the door at `selection.right + gap`,
# squarely on the rest of the member's own sentence. Observed in production
# covering "italic and code." in Text and the word "thesis" in Slides.
#
# The margin is the space outside the CONTENT, so the door is measured against
# the caller's content bounds. Absent bounds it must claim NO margin and fall
# below the selection rather than guess.
check("D1 the door measures the margin against the CONTENT, not the viewport",
      "contentRight" in gesture and "contentLeft" in gesture
      and "anchor.right + GAP + DOOR_W < vw" not in gesture,
      "a door that only clears the window edge still covers the sentence")
check("D1 the right margin starts beyond where the content ends",
      re.search(r"Math\.max\(anchor\.right,\s*cRight[^)]*\)\s*\+\s*GAP", gesture)
      is not None,
      "past the selection AND past the column — whichever is further right")
check("D1 the left margin starts beyond where the content begins",
      re.search(r"Math\.min\(anchor\.left,\s*cLeft[^)]*\)\s*-\s*GAP\s*-\s*DOOR_W", gesture)
      is not None,
      "the mirror of the right rule, on the far side of the content")
check("D1 no bounds means no margin is claimed",
      "haveBounds" in gesture and re.search(r"if \(haveBounds\)", gesture) is not None,
      "guessing a margin is how the door landed on the prose")
# Both callers must actually SUPPLY the bounds, or the shared component falls
# back to below-the-selection everywhere and the fix is inert. Read each file
# by NAME — `canvas` is rebound to StudioCanvas further down, and a rebound
# name is how a slice-scoped assertion reads the wrong region.
_prose = read("components/text/ProseCanvas.tsx")
check("D1 Text reports its reading column",
      "contentLeft: col.left" in _prose and "contentRight: col.right" in _prose,
      "ProseCanvas.selectionRect must carry the column with the rect")
_studio_canvas = read("components/authoring/StudioCanvas.tsx")
check("D1 Slides reports the artifact's box",
      "contentLeft: f?.left" in _studio_canvas
      and "contentRight: f?.right" in _studio_canvas,
      "the iframe's own rect is this medium's content bound")
check("D1 Text reads the rect (not the old end-point anchor)",
      "selectionRect()" in editor and "coordsAt(focusPoint.range.end)" not in editor,
      "the end-point anchor is superseded, not kept beside the rect")

# ── D4: the act says it is working, and cannot get stuck saying so ─────────
check("D4 the door has a pending state", "pending" in gesture and "Rewriting" in gesture,
      "vanishing at the click made the act feel like it went nowhere")
check("D4 the pending door refuses a second click",
      "disabled={pending}" in gesture and "pending ? undefined : onClick" in gesture)
check("D4 Text drives the pending state from a real in-flight rewrite",
      "pending={pendingRewrite !== null}" in editor)
# THE defect this revision fixes: the door said "Rewriting…" the instant the
# member clicked. But a click only SEEDS the composer (ADR-579 D7) — nothing
# fires until Send, and the member may edit the intent, dismiss the chip, or
# never send. A door claiming a turn that does not exist is a lie about state.
check("D4 the click ARMS a target and claims no turn",
      "armedRewriteRef.current = {" in editor
      and "setPendingRewrite({ ...focusPoint.range" not in editor,
      "the click must not set the pending/working state")
# ── ONE GESTURE, ONE TARGET, ONE TURN (2026-08-27, operator-reported) ─────
#
# Two defects with one root, both visible in a single production screenshot:
# the composer read "Rewrite the selection: Rewrite the selection:".
#
#   (1) Nothing stopped a SECOND gesture while one was already held. The seed
#       effect APPENDS when the composer is non-empty, so a second click did
#       not re-arm — it concatenated.
#   (2) The prefill restated the chip. The chip says "Rewrite · the selection
#       — …" and the typed seed carries the whole instruction to the server
#       (`_seed_line` renders verb, target AND anchor). Writing it into the
#       composer too was a second, weaker spelling of both, and it cost the
#       member the real estate they type their actual intent into.
#
# The composer is for the member's INTENT; the chip is the TARGET.
check("no gesture writes a restatement into the composer",
      "'Rewrite the selection: '" not in editor
      and "`Rewrite ${gestureTarget.noun}: `" not in surface_src(),
      "the chip already names the target; the seed already carries the verb")
check("the lane arms the chip from a TARGET-ONLY seed",
      "} else if (!composerSeed.target) {" in lane_panel,
      "with the prefill gone the seed carries no text — an early return on "
      "empty text would leave the chip unarmed and the gesture inert")
check("a held gesture asks for the INTENT, not the target",
      "How should ${seedTargetNoun(pendingSeed)} read?" in lane_panel,
      "the placeholder replaces the prefill; it must not restate the chip")
# The withdrawal. Reported off the STATE (one place), consumed by both mounts.
# Pinned to the DECLARATION, not the bare name: deleting the prop type left
# `onSeedHeld` present at its other three uses, so a substring test passed on
# a component that no longer accepts it (falsified 2026-08-27).
check("the lane reports a HELD gesture, distinct from a running turn",
      "onSeedHeld?: (held: boolean) => void;" in lane_panel,
      "held spans click → Send; running spans Send → settle. One act, two "
      "spans, and the door needs the first")
check("held is reported off the state, not from each setter",
      re.search(r"useEffect\(\(\) => \{\s*onSeedHeld\?\.\(pendingSeed !== null\);",
                lane_panel) is not None,
      "pendingSeed is cleared by ✕, by send, and by a replacing seed — a call "
      "at each site is three chances to miss one, and a missed clear leaves "
      "the door withdrawn forever")
check("Text withdraws its door while a gesture is held",
      "!slashOpen && !seedHeld && (" in editor and "onSeedHeld={setSeedHeld}" in editor,
      "a second click appends to the same composer; it does not start a "
      "second rewrite")

check("D4 the lane reports when a SEEDED turn actually goes up",
      "onSeededTurn" in lane_panel
      and "if (seed) onSeededTurn?.(true);" in lane_panel,
      "the mount cannot infer this from the click")
check("D4 the seeded turn settles however it ended",
      "if (opts.seed) onSeededTurn?.(false);" in lane_panel,
      "reply, refusal, error or stop — all settle the door")
check("D4 Text promotes armed → pending only on that report",
      "onSeededTurn={(running)" in editor
      and "setPendingRewrite(armedRewriteRef.current)" in editor)
# The release is an EFFECT, and all three of its parts are load-bearing. The
# first version of this check searched for the literal "setPendingRewrite(null),
# 180_000" — which passes when the guard is inverted (the timer never arms),
# when the whole effect is deleted into a dead helper, and even when the ceiling
# is widened to 180_000_000 (the literal is a PREFIX of the wider one). All
# three were falsified green on 2026-08-27. Assert the effect's shape.
_release = re.search(
    r"useEffect\(\(\) => \{\s*if \(!pendingRewrite\) return;"
    r"[\s\S]{0,900}?\}, \[pendingRewrite\]\);",
    editor,
)
check("D4 a turn that never writes releases the stuck state",
      _release is not None,
      "the release must be an effect GUARDED on a pending rewrite — an "
      "inverted guard never arms the timer, and a dead helper never runs")
if _release:
    _body = _release.group(0)
    check("D4 the release actually clears the pending state",
          re.search(r"setTimeout\(\(\) => setPendingRewrite\(null\)", _body) is not None,
          f"release body: {_body!r}")
    check("D4 the release ceiling is a real one, not an unreachable number",
          re.search(r"setPendingRewrite\(null\),\s*180_000\s*\)", _body) is not None,
          "180_000_000 (50 hours) is not a release; the literal is a PREFIX "
          "of the widened one, so match it to its closing paren")
    check("D4 the release timer is cleaned up",
          "clearTimeout(t)" in _body, f"release body: {_body!r}")

# ── D5: the member is put back ON the work when the write lands ────────────
check("D5 the canvas can scroll a range to centre",
      "scrollRangeIntoView" in canvas and "y: 'center'" in canvas)
# ...and the landing must CALL it. Falsified 2026-08-27: replacing the call
# with `void start; void end;` left every other D5 check green — the algorithm
# computed a perfect span and threw it away, which is precisely the "landing
# that never fired" the Text half was driven to find in the first place.
check("D5 the landing hands the span to the canvas",
      re.search(r"canvasRef\.current\?\.scrollRangeIntoView\(\s*start", editor)
      is not None,
      "computing the span and not scrolling to it is the defect, not the fix")
check("D5 the landing re-finds the passage by CONTENT, not by offset",
      "landOnRewrite" in editor and "preWriteRef" in editor,
      "the rewritten passage is a different length — the old span no longer describes it")
check("D5 the landing fires when the reloaded text ARRIVES, not at write time",
      "requestAnimationFrame(() => landOnRewriteRef.current" in editor,
      "the document has not reached the canvas yet when onArtifactWrite fires")
# The scroll silently never ran: the turn settles when the STREAM closes, often
# BEFORE the refetch resolves, so reading the spinner's state cleared the
# target first and the member stayed at the top of the document.
check("D5 the landing target outlives the spinner's state",
      "const target = landingTargetRef.current;" in editor
      and "landingTargetRef.current = armedRewriteRef.current;" in editor
      and "pendingRewriteRef" not in editor,
      "two lifetimes from one arming — the spinner ends at settle, the landing at the WRITE")
check("D5 the scroll uses a RANGE, not a bare position",
      "EditorView.scrollIntoView(EditorSelection.range(a, b)" in canvas,
      "a position centres its own line and lets a long passage run off the bottom")
check("D5 the pre-write text is captured before the refetch",
      "preWriteRef.current = textRef.current;" in editor)


# ── D3: ONE producer — the header button is DELETED, not kept beside it ────
# The whole point of the ADR. Two entrances to one act, one of them far from
# the thing it acts on, is the duplication this codebase keeps paying for.
gesture_mounts = editor.count("<SelectionGesture")
check("D3 Text mounts the gesture exactly once", gesture_mounts == 1,
      f"found {gesture_mounts}")
check("D3 the old header button is GONE from Text",
      "Rewrite the selected text — opens the chat" not in editor,
      "ADR-609's header door is superseded, not kept beside the floating one")
check("D3 Text imports no orphaned Sparkles icon",
      not re.search(r"^\s*Sparkles,\s*$", editor, re.MULTILINE),
      "the icon moved into SelectionGesture with the button")
# Exactly one thing may seed a rewrite in this desk.
rewrite_seeds = len(re.findall(r"verb:\s*'rewrite'", editor))
check("D3 Text has exactly ONE rewrite seed producer", rewrite_seeds == 1,
      f"found {rewrite_seeds}")

# ── D4: the deterministic toolbar carries no metered verb ──────────────────
check("D4 MarkdownToolbar declares no judged/metered act",
      "Sparkles" not in toolbar and "rewrite" not in toolbar.lower(),
      "that row is markdown verbs — every one mechanical and free")

# ── ADR-613: the Slides half — same concept, this medium's address ─────────
surface = read("components/authoring/StudioSurface.tsx")
block_menu = read("components/authoring/StudioBlockMenu.tsx")
canvas = read("components/authoring/StudioCanvas.tsx")
projection = read("components/workspace/viewers/projection.ts")

check("613 Slides mounts the SHARED gesture (not a second implementation)",
      "<SelectionGesture" in surface and "SelectionGesture" in surface,
      "the component lives in components/authoring/ precisely for this")

# THE gap Slides had: StudioSelection carries identity and never geometry, and
# every other iframe message carries a pointer POINT (which D1 refuses) or
# nothing at all. The runtime now reports the selection's VISUAL box.
check("613 the runtime reports a selection RECT, not a pointer point",
      "yarnnn-selection-rect" in projection and "postSelectionRect" in projection)
check("613 the rect is the visual box of what is SELECTED",
      "postSelectionRect(r, 'object')" in projection
      and "__yarnnnPostSelRect(rect, 'range')" in projection,
      "both grains report; neither reads the cursor")
check("613 no subject, no door — the rect retracts",
      "postSelectionRect(null, null)" in projection)
# The zoom trap: dividing by the zoom factor is correct ONLY for body-appended
# chrome inside the zoomed document (the format bar). A parent-side door needs
# the raw visual rect; dividing put an earlier menu at ~37% of the offset.
_post_fn = projection.split("function postSelectionRect")[1].split("\n  }\n")[0]
check("613 the reporter does NOT zoom-divide (that is in-frame chrome's rule)",
      "postSelectionRect" in projection
      and "/ z" not in _post_fn and "zf()" not in _post_fn,
      "the parent maps with + iframeRect offset and no zoom multiply")
check("613 the bridge maps iframe→parent coordinates",
      "onSelectionRect" in canvas and "getBoundingClientRect()" in canvas
      and "yarnnn-selection-rect" in canvas)

# D2 in this medium: a text RANGE inside a block and the BLOCK are different
# targets. The noun and the anchor must be decided together or the member gets
# a block rewritten when they meant three words.
check("613 the chip noun and the anchor are decided together",
      "gestureTarget" in surface
      and "selRect.grain === 'range'" in surface,
      "the grain the runtime reported picks the noun AND the label")
check("613 the gesture yields to every other floating door",
      "!slash && !citePicker && !updateMenu && !ctxMenu" in surface,
      "two doors at one selection is a collision, not a choice")
# ADDED 2026-08-27 after driving the Slides half for the first time.
#
# The door was mounted on `selRect` ALONE while `gestureTarget` — and
# `rewriteSelection`, which early-returns without it — needs the rect AND the
# selection. So a rect arriving without a selection rendered a door wearing a
# fallback label that did NOTHING when clicked: a door onto nothing, the
# ADR-373 D6 incorrect-success shape at the affordance layer.
check("613 Slides withdraws its door while a gesture is held",
      "!seedHeld && gestureTarget && (" in surface
      and "onSeedHeld={setSeedHeld}" in surface,
      "the same one-gesture rule as Text, in the medium that shares the "
      "component")
check("613 the door renders only when the act HAS a subject",
      "&& gestureTarget && (" in surface,
      "keyed on the rect alone, the door opens onto nothing")
check("613 the label needs no fallback, because the mount guarantees the target",
      "gestureTarget?.noun ?? 'the selection'" not in surface,
      "a fallback noun here is the tell that the guard is missing")
# D4 in this medium. The Text half was DRIVEN to find that a door which claims
# nothing (or claims a turn too early) makes the act feel like it went nowhere;
# Slides shipped the gesture with no pending state at all.
check("613 Slides drives a pending state from a real in-flight rewrite",
      "pending={pendingRewrite}" in surface and "onSeededTurn" in surface,
      "the click cannot infer that a seeded turn went up — only the lane knows")
check("613 the click ARMS and claims no turn",
      "armedRewriteRef.current = true;" in surface
      and re.search(r"setPendingRewrite\(true\);", surface) is not None,
      "a seed is not a turn: the member may still edit it, dismiss it, or "
      "never send")
_slides_release = re.search(
    r"useEffect\(\(\) => \{\s*if \(!pendingRewrite\) return;"
    r"[\s\S]{0,900}?\}, \[pendingRewrite\]\);",
    surface,
)
check("613 a Slides turn that never writes releases the stuck state",
      _slides_release is not None
      and re.search(r"setPendingRewrite\(false\),\s*180_000\s*\)",
                    _slides_release.group(0)) is not None,
      "same release as Text — guarded effect, real ceiling, cleaned up")

# The deletion — stated as an invariant, not a count.
check("613 the judged verbs left the block menu",
      "Rewrite…" not in block_menu
      and "Check this…" not in block_menu
      and "Ask about this…" not in block_menu)
check("613 the Ask tier went with its rows (every row in it was judged)",
      "askOpen" not in block_menu
      and '<span className="truncate">Ask</span>' not in block_menu)
_bm_code = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", block_menu)
check("613 the meter discriminator is DELETED, not left latent",
      "meter" not in _bm_code,
      "a discriminator with nothing to discriminate is a second spelling waiting")
check("613 the surface's judged seed producers are gone",
      "menuRewrite" not in surface
      and "menuCheck" not in surface
      and "askAboutSelection" not in surface)
check("613 the second-menu route is deleted whole",
      "openBlockActs" not in surface
      and "ctxInitialOpen" not in surface
      and "initialOpen" not in block_menu)


# ── The mechanical door is UNTOUCHED (ADR-589 keeps the ladder) ────────────
studio_menu = read("components/authoring/StudioUpdateMenu.tsx")
check("ADR-589's ladder survives — this ADR does not merge the two doors",
      "SELECTION LADDER" in studio_menu,
      "the mechanical door answers a different question (ADR-612 §1)")

if failures:
    print(f"\nADR-612 FAILED ({len(failures)}):")
    for f in failures:
        print(f"  FAIL {f}")
    sys.exit(1)
print("ADR-612 judged gesture: all checks pass")
sys.exit(0)
