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

# Character ceilings — the ratchet. Re-carved sizes are ~1.1k / ~1.5k chars;
# ceilings leave ~30% headroom.
CEILINGS = {
    "reactive": 1_600,
    "addressed": 2_000,
}

MINIMAL_FRAME_CEILING = 9_000  # chars; ~8.1k post-ADR-383 re-carve


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
