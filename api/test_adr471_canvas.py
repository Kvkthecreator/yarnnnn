"""ADR-471 — the canvas mode: click-pass-earned posture invariants (C6).

The canvas layout/z STRUCTURAL checks live in test_adr466_mode_native.py
(landed with C2/C3). This file pins what the CANVAS CLICK PASS earned
(docs/evaluations/2026-07-20-canvas-click-pass/) — intent assertions on the
studio posture, per the worksheet's step-6 rule ("any posture change encoding
a specific discipline gets an intent assertion"). Its own file because the
sibling gates carried a concurrent lane's WIP at commit time — staging by
name means never sweeping another lane's dirty file.

Run:  python3 api/test_adr471_canvas.py   (NOT pytest — check()-gate.)
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from services.studio import build_skeleton, build_studio_posture

    posture = build_studio_posture(
        "operation/x/visual.html", build_skeleton("canvas", "X")
    )

    # ── The click pass's two observed findings, applied + pinned ──────────
    # Both live canvas runs chose wholesale WriteFile for first composition
    # onto the fresh scaffold (a compose IS a re-draft of placeholder
    # content) — the rule was amended to match observed design reality
    # rather than fight it, with the patch discipline resuming after.
    _check(
        "the posture admits FIRST COMPOSITION via one complete WriteFile",
        "FIRST COMPOSITION" in posture and "send the FULL content" in posture,
    )
    _check(
        "…and the patch discipline resumes after it",
        "After the first composition, PATCH." in posture,
    )
    # Both runs dropped the scaffold's placeholder kicker while composing —
    # sensible design, but the old rule ("never remove ids you didn't
    # create") read as forbidding it. The amended rule draws the honest line:
    # placeholders are replaceable, member/prior-turn blocks are not.
    _check(
        "placeholders are replaceable; member-authored blocks never",
        "Scaffold PLACEHOLDER blocks" in posture
        and "never dropped and keep their data-block-id" in posture,
    )
    # C5's staged-measures teaching (the paragraph the canvas lane composes
    # from): staged frames + the z measure, not deck-only.
    _check(
        "the MEASURES paragraph teaches staged frames + z (not deck-only)",
        "STAGED frame" in posture and "data-z with --yz" in posture,
    )
    # The canvas flow prose reaches the composed posture (layouts are data).
    _check(
        "the canvas flow prose composes in (everything-positioned, aspect slugs)",
        "Position EVERY block" in posture and '"wide" 16:9' in posture,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
