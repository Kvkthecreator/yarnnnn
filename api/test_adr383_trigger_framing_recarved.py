"""ADR-383 Rung-1 gate — the kernel trigger framing is steward-first and
program-neutral, and stays that size (the anti-scar-tissue ratchet).

The 2026-07-02 envelope diagnosis (docs/analysis/freddie-envelope-refactor-
plan-2026-07-02.md) found alpha-trader vocabulary hardcoded in
_TRIGGER_FRAMING["addressed"] — an ADR-222 violation ("the kernel never
hardcodes a program noun") and the capital-judgment residue ADR-383 flagged.
This gate makes the re-carve permanent:

  1. NO PROGRAM NOUNS in any kernel frame string (trigger framings + the
     minimal frame). The banned list is the trading/program vocabulary that
     was actually found in the kernel on 2026-07-02.
  2. SIZE RATCHET: each trigger-framing block stays under a character
     ceiling. Prompt patches accrete one incident at a time; the ceiling
     forces folds/removals instead (the removal-over-addition discipline,
     ADR-390 precedent). Raising a ceiling requires an ADR-line
     justification in the same commit.
  3. PARTITION (agent-composition.md §3.2.1): the framing may point at
     principles.md / MANDATE; it may not itself carry an operation's
     decision tree (no propose/stand-down action-menu bullets).

Run: cd api && python -m pytest test_adr383_trigger_framing_recarved.py -q
"""
from __future__ import annotations

import re

from agents.freddie_agent import _TRIGGER_FRAMING, _compute_minimal_frame

# The program vocabulary found verbatim in the kernel on 2026-07-02, plus
# obvious siblings. The operation-specific version of every removed
# instruction lives in the bundles' persona/principles.md (verified for
# alpha-trader + alpha-author, 2026-07-02).
BANNED_PROGRAM_NOUNS = [
    "_money_truth",
    "money_truth",
    "signal_files",
    "signal-evaluation",
    "signal conditions",
    "_risk",
    "sizing",
    "trade",
    "trading",
    "ticker",
    "position",
    "p&l",
    "portfolio",
    "_operator_profile",
    "mechanical mirror",
]

# Character ceilings — the ratchet. ADR-397 (Rung 2) relocated the wake
# liturgy from the cached frame into the reactive framing: reactive ceiling
# raised 1,600 → 2,600 to receive it (same content, different carrier —
# net reactive tokens flat); frame ceiling lowered 9,000 → 7,600 (the frame
# shrank ~1.6k); addressed unchanged.
CEILINGS = {
    "reactive": 2_600,
    "addressed": 2_000,
}

MINIMAL_FRAME_CEILING = 7_600  # chars; ~6.5k post-ADR-397 liturgy move


def _all_kernel_strings() -> dict:
    out = dict(_TRIGGER_FRAMING)
    out["minimal_frame"] = _compute_minimal_frame()
    return out


def test_no_program_nouns_in_kernel_framing():
    failures = []
    for name, text in _all_kernel_strings().items():
        low = text.lower()
        for noun in BANNED_PROGRAM_NOUNS:
            if noun.lower() in low:
                failures.append(f"{name}: contains program noun {noun!r}")
    assert not failures, "\n".join(failures)


def test_trigger_framing_size_ratchet():
    failures = []
    for name, ceiling in CEILINGS.items():
        size = len(_TRIGGER_FRAMING[name])
        if size > ceiling:
            failures.append(
                f"_TRIGGER_FRAMING[{name!r}] is {size} chars > ceiling "
                f"{ceiling} — fold or remove before adding "
                f"(removal-over-addition)"
            )
    assert not failures, "\n".join(failures)


def test_minimal_frame_size_ratchet():
    size = len(_compute_minimal_frame())
    assert size <= MINIMAL_FRAME_CEILING, (
        f"_compute_minimal_frame() is {size} chars > ceiling "
        f"{MINIMAL_FRAME_CEILING}"
    )


def test_no_decision_tree_in_kernel():
    """The kernel may POINT at principles.md; it may not carry an
    operation's action menu (bulleted propose/stand-down items)."""
    menu_pattern = re.compile(
        r"^\s*[-*] .*(propose|stand.down)", re.IGNORECASE | re.MULTILINE
    )
    for name, text in _TRIGGER_FRAMING.items():
        assert not menu_pattern.search(text), (
            f"_TRIGGER_FRAMING[{name!r}] carries an action-menu bullet — "
            f"principles.md content per agent-composition.md §3.2.1"
        )


def test_framing_points_at_principles():
    """Both blocks must route decision content to the agent's own files."""
    for name in ("addressed", "reactive"):
        assert "principles" in _TRIGGER_FRAMING[name].lower(), (
            f"_TRIGGER_FRAMING[{name!r}] must route judgment to "
            f"principles.md"
        )


# --- ADR-397 (Rung 2): the wake liturgy is reactive-scoped ---

LITURGY_MARKERS = [
    "standing_intent",
    "reflection.md",
    "judgment_log",
    "situation, not a task",
]


def test_addressed_carries_no_wake_liturgy():
    """ADR-397 D3: the addressed framing keeps a one-line ReturnVerdict
    close and NO unattended-cycle liturgy — the operator is present."""
    low = _TRIGGER_FRAMING["addressed"].lower()
    hits = [m for m in LITURGY_MARKERS if m.lower() in low]
    assert not hits, (
        f"addressed framing carries wake liturgy {hits} — that is the "
        f"reactive (unattended) trigger's content per ADR-397"
    )
    assert "returnverdict" in low, "addressed must keep the one-line close"


def test_frame_carries_no_wake_liturgy():
    """ADR-397 D2: the cached frame is trigger-universal — the liturgy
    lives on the reactive framing, not in every trigger's prompt."""
    low = _compute_minimal_frame().lower()
    hits = [m for m in LITURGY_MARKERS if m.lower() in low]
    assert not hits, f"minimal frame carries wake liturgy {hits} (ADR-397 D2)"


def test_reactive_carries_the_liturgy():
    """ADR-397 D2: reactive wakes — the unattended cycles — keep the full
    discipline: forward reasoning, standing_intent, reflection, verdict."""
    low = _TRIGGER_FRAMING["reactive"].lower()
    for marker in ("situation, not a task", "standing_intent",
                   "reflection.md", "returnverdict"):
        assert marker in low, (
            f"reactive framing lost liturgy marker {marker!r} (ADR-397 D2)"
        )
