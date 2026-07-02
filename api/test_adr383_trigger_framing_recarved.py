"""ADR-383 Rung-1 → ADR-400 gate — the kernel prompt surface is steward-first,
program-neutral, thin, and carries the interface contracts.

History: Rung 1 (2026-07-02) re-carved `_TRIGGER_FRAMING` (program nouns out);
ADR-397 scoped the liturgy to reactive; the Rung-3 Arm-B probe proved the close
CONTRACT belongs in the frame (DP22); ADR-400 landed the collapse — the framing
layer is DELETED, per-trigger INTERFACE rules live in the ask branches of
`_ask_for_trigger`, and the envelope is governance-prefix + volatile-suffix.

This gate keeps that permanent:
  1. NO PROGRAM NOUNS in kernel-authored prompt text (frame + ask branches +
     governance headers).
  2. SIZE RATCHET on the frame and on the kernel's per-ask overhead — prompt
     patches accrete one incident at a time; the ceiling forces folds/removals
     (removal-over-addition, ADR-390).
  3. INTERFACE CONTRACTS in the right layer: ReturnVerdict close in the FRAME
     (Arm-B silent-exit regression); verdict-early on proposal asks;
     one-WriteFile on recurrence asks.
  4. NO WAKE LITURGY anywhere in kernel prompt text (ADR-400 deleted it; its
     residual value is principles.md content per agent-composition.md §3.2.1).

Run: cd api && python -m pytest test_adr383_trigger_framing_recarved.py -q
"""
from __future__ import annotations

from agents.freddie_agent import (
    _ask_for_trigger,
    _compute_minimal_frame,
    _governance_prefix,
)

BANNED_PROGRAM_NOUNS = [
    "_money_truth",
    "money_truth",
    "signal_files",
    "signal-evaluation",
    "signal conditions",
    "sizing",
    "trading",
    "ticker",
    "p&l",
    "mechanical mirror",
]

MINIMAL_FRAME_CEILING = 7_600  # chars

# Kernel-authored ask overhead (synthetic minimal ctx → everything rendered
# is kernel text). Ceilings leave ~30% headroom over landed sizes.
ASK_OVERHEAD_CEILINGS = {
    "proposal": 1_300,
    "recurrence": 900,
    "addressed": 500,
}

_PROPOSAL_CTX = {"proposal_row": {"action_type": "x", "reversibility": "y", "inputs": {}}}
_RECURRENCE_CTX = {"recurrence_prompt": "P", "recurrence_slug": "s"}
_ADDRESSED_CTX = {"user_message": "hi"}


def _kernel_texts() -> dict:
    return {
        "minimal_frame": _compute_minimal_frame(),
        "ask:proposal": _ask_for_trigger("reactive", _PROPOSAL_CTX),
        "ask:recurrence": _ask_for_trigger("reactive", _RECURRENCE_CTX),
        "ask:addressed": _ask_for_trigger("addressed", _ADDRESSED_CTX),
        "governance_headers": _governance_prefix({}),
    }


def test_no_program_nouns_in_kernel_prompt_text():
    failures = []
    for name, text in _kernel_texts().items():
        low = text.lower()
        for noun in BANNED_PROGRAM_NOUNS:
            if noun.lower() in low:
                failures.append(f"{name}: contains program noun {noun!r}")
    assert not failures, "\n".join(failures)


def test_minimal_frame_size_ratchet():
    size = len(_compute_minimal_frame())
    assert size <= MINIMAL_FRAME_CEILING, (
        f"_compute_minimal_frame() is {size} chars > ceiling "
        f"{MINIMAL_FRAME_CEILING} — fold or remove before adding"
    )


def test_ask_overhead_size_ratchet():
    sizes = {
        "proposal": len(_ask_for_trigger("reactive", _PROPOSAL_CTX)),
        "recurrence": len(_ask_for_trigger("reactive", _RECURRENCE_CTX)),
        "addressed": len(_ask_for_trigger("addressed", _ADDRESSED_CTX)),
    }
    failures = [
        f"ask:{k} overhead {v} chars > ceiling {ASK_OVERHEAD_CEILINGS[k]}"
        for k, v in sizes.items() if v > ASK_OVERHEAD_CEILINGS[k]
    ]
    assert not failures, "\n".join(failures) + " — removal-over-addition"


def test_close_contract_lives_in_the_frame():
    """Rung-3 finding: the ReturnVerdict close is the agent↔runtime INTERFACE
    CONTRACT (DP22) — when it lived only in strippable coaching, Haiku
    silently exited (2/6 unanswered on the Arm-B probe)."""
    frame = _compute_minimal_frame().lower()
    assert "returnverdict" in frame


def test_proposal_ask_carries_verdict_early():
    ask = _ask_for_trigger("reactive", _PROPOSAL_CTX).lower()
    assert "early" in ask and "returnverdict" in ask, (
        "proposal asks must carry the verdict-early round-budget rule "
        "(ADR-294 mid-write truncation class)"
    )


def test_recurrence_ask_carries_one_writefile_rule():
    ask = _ask_for_trigger("reactive", _RECURRENCE_CTX).lower()
    assert "one writefile" in ask and "returnverdict" in ask


LITURGY_MARKERS = ["standing_intent", "reflection.md", "judgment_log", "situation, not a task"]


def test_no_wake_liturgy_in_kernel_prompt_text():
    """ADR-400: the liturgy is deleted from kernel prompt text — its residual
    value (standing-intent habit, reflection) is principles.md content."""
    failures = []
    for name, text in _kernel_texts().items():
        low = text.lower()
        hits = [m for m in LITURGY_MARKERS if m in low]
        if hits:
            failures.append(f"{name}: carries liturgy {hits}")
    assert not failures, "\n".join(failures)


def test_frame_points_at_principles():
    assert "principles" in _compute_minimal_frame().lower()
