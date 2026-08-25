"""ADR-606 — the pane sees what the member sees.

Defends the OBLIGATION half (D4/D5): every pane-bearing surface answers the
focus question — a declaration, or a written silence — so the next surface
transition cannot silently drop the member's place the way Docs→Text did.
(The rendering half — one kernel site, the D2 binding guard, the selection
sentence — lives in test_adr522_focus_declaration.py, re-anchored by the same
commit; the registry half — every app declares a posture — lives in
test_adr562_app_owned_config.py.)

Run: python3 test_adr606_pane_sees_the_member.py   (from api/)
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


# ── D5: the pane roster is DERIVED, and every mount has a focus story ──────
#
# A mount's story is either DECLARES (the file — possibly a surface parent in
# the same tree — calls useDeclareFocus) or SILENCE (a written reason). A new
# `<LanePanel` mount with no row here fails the roster check: the question
# must be answered, not defaulted.
FOCUS_STORIES: dict[str, dict] = {
    "components/authoring/StudioSurface.tsx": {
        "declares": "components/authoring/StudioSurface.tsx",
    },
    "components/text/TextEditor.tsx": {
        "declares": "components/text/TextEditor.tsx",
    },
    "components/desk/DeskHousing.tsx": {
        # The desk housing is a frame; the strings SURFACE above it owns the
        # object in view and declares document-grain focus (ADR-522).
        "declares": "components/strings/StringsSurface.tsx",
    },
    "components/chat-surface/ChatSurface.tsx": {
        # FOCUS-SILENCE: /chat is the workbench BESIDE the desks, not a desk —
        # it has no object of its own to declare. It READS every declaration
        # instead (LanePanel's useCurrentFocus, with the shell's recency
        # fallback), which is the design, not an omission.
        "silence": "the workbench reads others' declarations; it has no object",
    },
}

mounts = sorted(
    str(p.relative_to(WEB))
    for p in WEB.rglob("*.tsx")
    if "node_modules" not in p.parts and "<LanePanel" in p.read_text()
)
check(
    "D5 every LanePanel mount is rostered (a new pane must answer the focus "
    "question)",
    set(mounts) == set(FOCUS_STORIES),
    f"mounts={mounts} rostered={sorted(FOCUS_STORIES)}",
)

for mount, story in FOCUS_STORIES.items():
    if "declares" in story:
        declarer = WEB / story["declares"]
        src = declarer.read_text() if declarer.exists() else ""
        # The WIRED call, not a mention: `useDeclareFocus(` invoked with the
        # app slug as its first argument somewhere in the declarer.
        check(
            f"D5 {mount} → {story['declares']} actually declares",
            re.search(r"useDeclareFocus\(\s*['\"a-zA-Z]", src) is not None,
            "no wired useDeclareFocus call",
        )
    else:
        check(f"D5 {mount} silence is WRITTEN", bool(story.get("silence")))

# ── The consumer half stays wired: LanePanel reads the declaration and puts
#    it on the wire (deleting either side would pass the roster above) ──────
lane_panel = (WEB / "components/chat-surface/LanePanel.tsx").read_text()
check(
    "the pane reads the member's focus (useCurrentFocus wired)",
    "useCurrentFocus(" in lane_panel,
)
check(
    "…and sends it on the turn (focusToWire wired into send)",
    "focusToWire(" in lane_panel,
)

# ── D4: Text's place reaches the canvas callback, wired end to end ─────────
prose = (WEB / "components/text/ProseCanvas.tsx").read_text()
check(
    "D4 ProseCanvas reports the selection from the update listener",
    re.search(r"onSelectionRef\.current\?\.\(\s*sel\.from,\s*sel\.to\s*\)", prose)
    is not None,
)
text_editor = (WEB / "components/text/TextEditor.tsx").read_text()
check(
    "D4 TextEditor wires the callback into the mounted canvas",
    re.search(r"onSelectionChange=\{onCanvasSelection\}", text_editor) is not None,
)
check(
    "D4 Text declares the 'text' app's focus",
    re.search(r"useDeclareFocus\(\s*'text'", text_editor) is not None,
)
# The commitment ladder: selection first, then the nearest h1/h2, and the
# heading walk filters to D4's levels (h1/h2 — "nearest heading" in ADR-522's
# own spelling), addressed by SOURCE LINE.
check(
    "D4 the heading walk is level-capped (h1/h2) and line-addressed",
    re.search(r"h\.level\s*<=\s*2\s*&&\s*h\.line\s*<=\s*line", text_editor)
    is not None,
)

if failures:
    print(f"ADR-606 FAILED ({len(failures)}):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
print("ADR-606 pane-sees-the-member: all checks passed")
sys.exit(0)
