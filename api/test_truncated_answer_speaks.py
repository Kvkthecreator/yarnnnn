"""A cut-off answer says so — it is never an empty message.

THE MEASURED DEFECT (2026-09-16, probe_data_heavy_lane.py):
    A lane asked three questions about a 5,000-row CSV (287,762 chars). It
    paginated CORRECTLY through three ReadFile windows to the end of the file,
    then spent its whole 4096-token budget computing the answer and returned:

        finish_reason='length'   text=''   success=True   tokens_out=4438

    The member saw an EMPTY MESSAGE. No error, no hedge, nothing separating it
    from a hang — after a wait and a real bill. Reproduced twice, identically.

    `RoutedCompletion.finish_reason` had been captured by the router since it
    was written and read by NOBODY:
        $ grep -rn finish_reason api/services/lane_runner.py api/routes/lanes.py
        (no matches)

    The round-cap fallback could not catch it: that branch fires when the `for`
    loop EXHAUSTS, and this turn broke out of round 4 of 8.

WHAT THIS GATE HOLDS, per site (a counting gate cannot defend a per-site
invariant — VERIFICATION.md):
    §1  the helper turns a length-truncated empty answer into the notice
    §2  an honest empty answer (`stop`) is left BYTE-IDENTICAL
    §3  a normal answer is passed through untouched
    §4  BOTH break sites route through the helper — the sync turn and the
        streamed turn members actually use. A fix on one only would leave the
        live path silent, which is the whole defect.

Run:  cd api && python3 -m pytest test_truncated_answer_speaks.py -q
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from services.lane_runner import _TRUNCATED_ANSWER_NOTICE, _final_text_for

SRC = Path(__file__).parent / "services" / "lane_runner.py"


class _Routed:
    """The two fields the helper reads, and nothing else."""

    def __init__(self, text, finish_reason):
        self.text = text
        self.finish_reason = finish_reason


# ── §1 the defect's exact shape now speaks ──────────────────────────────────

def test_length_truncated_empty_answer_speaks():
    out = _final_text_for(_Routed("", "length"), "")
    assert out == _TRUNCATED_ANSWER_NOTICE
    assert out.strip(), "the notice must be non-empty — that is the entire fix"


def test_length_truncated_whitespace_only_answer_speaks():
    """Whitespace is not an answer. A model that emits ' \\n ' before being cut
    off leaves the member exactly as informed as one that emits nothing."""
    assert _final_text_for(_Routed("  \n  ", "length"), "") == _TRUNCATED_ANSWER_NOTICE


def test_the_notice_says_the_workspace_is_unchanged():
    """The fact that matters most to a member whose turn died mid-answer. The
    sibling round-cap notice names it too; a cut-off answer must not be vaguer
    than the failure beside it."""
    low = _TRUNCATED_ANSWER_NOTICE.lower()
    assert "nothing in your workspace changed" in low
    # ADR-638 / VOICE-AND-TONE: plain speech, no internal vocabulary.
    for word in ("finish_reason", "token", "max_tokens", "truncat", "error"):
        assert word not in low, f"member-facing copy leaked {word!r}"


# ── §2 an honest stop is byte-identical ─────────────────────────────────────

def test_stop_with_empty_text_is_unchanged():
    """A model that finishes with nothing to say is NOT truncated. Widening the
    fix to every empty answer would put the notice on honest turns."""
    assert _final_text_for(_Routed("", "stop"), "") == ""


def test_unknown_finish_reason_with_empty_text_is_unchanged():
    assert _final_text_for(_Routed("", None), "") == ""
    assert _final_text_for(_Routed("", "tool_calls"), "") == ""


def test_empty_text_falls_back_to_current_when_not_truncated():
    """The prior `final_text` survives — the pre-fix behaviour for every
    non-length finish."""
    assert _final_text_for(_Routed("", "stop"), "earlier") == "earlier"


# ── §3 a real answer is never touched ───────────────────────────────────────

def test_normal_answer_passes_through():
    assert _final_text_for(_Routed("There are 5,000 rows.", "stop"), "") == (
        "There are 5,000 rows."
    )


def test_a_long_answer_that_was_truncated_but_HAS_text_is_kept():
    """⭐ The partial answer is the member's to read. Replacing real content
    with the notice would DESTROY work — the fix must only fill a void, never
    overwrite. This is the assertion that keeps the fix from becoming a bug."""
    partial = "1. There are 5,000 rows.\n2. Zorvathic Dynamics is in"
    assert _final_text_for(_Routed(partial, "length"), "") == partial


# ── §4 BOTH loops route through the helper ──────────────────────────────────

def _break_sites(src: str) -> list[str]:
    """Each `if not routed.tool_calls:` block body, brace-free and bounded to
    the construct (never a fixed character window — VERIFICATION.md)."""
    sites = []
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "if not routed.tool_calls:":
            sites.append("\n".join(lines[i : i + 6]))
    return sites


def test_both_break_sites_exist_and_use_the_helper():
    """The sync turn AND the streamed turn. Completeness assert: if a third
    loop appears, it must route through the helper too or this reddens."""
    src = SRC.read_text()
    sites = _break_sites(src)
    assert len(sites) == 2, (
        f"expected exactly 2 `if not routed.tool_calls:` sites "
        f"(sync + stream), found {len(sites)} — a new loop must route "
        f"through _final_text_for()"
    )
    for idx, body in enumerate(sites):
        assert "_final_text_for(routed" in body, (
            f"break site {idx} does not route through _final_text_for — "
            f"an empty answer is silent there:\n{body}"
        )
        assert not re.search(r"final_text\s*=\s*routed\.text\b", body), (
            f"break site {idx} still assigns routed.text directly, which is "
            f"the pre-fix defect"
        )


def test_the_streamed_path_is_covered():
    """The path a member actually uses. A fix that only lands on the sync turn
    leaves the live surface silent — the defect would survive its own gate."""
    src = SRC.read_text()
    stream_start = src.index("async def run_lane_turn_stream")
    stream_body = src[stream_start:]
    assert "_final_text_for(routed" in stream_body, (
        "run_lane_turn_stream does not use the helper — the live path is "
        "still silent"
    )


def test_router_still_supplies_finish_reason():
    """The helper reads a field the router must keep populating. If the router
    stops setting finish_reason, this fix silently stops working and every
    assertion above still passes on its fake."""
    router = (Path(__file__).parent / "services" / "model_router.py").read_text()
    assert "finish_reason: Optional[str] = None" in router, (
        "RoutedCompletion no longer declares finish_reason"
    )
    assert router.count("finish_reason=finish_reason") >= 2, (
        "finish_reason is not threaded on both the sync and streaming returns"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
