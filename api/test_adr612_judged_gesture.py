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
check("D2 the seed Text sends is the selection grain",
      re.search(r"label:\s*'selection'", editor) is not None)

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
check("D1 the door prefers a margin over covering prose",
      "anchor.right + GAP + DOOR_W < vw" in gesture
      and "anchor.left - GAP - DOOR_W > 0" in gesture,
      "right margin, then left, then the clamped fallback")
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
check("D4 a turn that never writes releases the stuck state",
      "setPendingRewrite(null), 180_000" in editor
      or re.search(r"setTimeout\(\(\) => setPendingRewrite\(null\), 180_000\)", editor)
      is not None,
      "a refusal or an error must not leave the door saying Rewriting… forever")

# ── D5: the member is put back ON the work when the write lands ────────────
check("D5 the canvas can scroll a range to centre",
      "scrollRangeIntoView" in canvas and "y: 'center'" in canvas)
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
