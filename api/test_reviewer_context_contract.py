"""Regression gate — Reviewer context-shape contract enforcement.

Problem B fix (2026-05-13). Two orthogonal regressions guarded:

  (i)  Runtime contract enforcement: `_validate_context_shape` accepts
       the three valid context shapes and rejects every malformed one.
       This is the boundary that turns the silent-stand_down class of
       bugs (commit e55d201) into a loud log + None return.

  (ii) Dispatcher↔Reviewer key alignment: the invocation dispatcher
       writes context bags with the canonical key names
       (`recurrence_prompt`, `recurrence_slug`) that the Reviewer's
       ReviewerContext TypedDict + _validate_context_shape expect. The
       legacy key names (`prompt`, `slug`, `trigger_slug`) must NOT
       appear in dispatcher call sites — singular implementation per
       CLAUDE.md item 1.

Both guards live in one file because they protect the same class of bug:
stringly-typed boundaries that drift silently. (i) catches future
regressions in the Reviewer side; (ii) catches future regressions in the
dispatcher side; together they make the dispatcher↔Reviewer interface
contract enforceable in CI.

Run via:
    python -m pytest api/test_reviewer_context_contract.py -v

Or as a standalone script:
    python api/test_reviewer_context_contract.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "api"))

from agents.reviewer_agent import _validate_context_shape  # noqa: E402

# 2026-06-04 (ADR-315 carry-over): the reactive recurrence-fire context-bag
# construction moved from the deleted services/invocation_dispatcher.py into
# services/wake.py (ADR-296 v2 → ADR-298 wake-architecture migration). The
# canonical-key contract is unchanged; only the file that builds the bag moved.
DISPATCHER_PATH = REPO_ROOT / "api" / "services" / "wake.py"
REVIEWER_PATH = REPO_ROOT / "api" / "agents" / "reviewer_agent.py"
# ADR-315: ReviewerContext is defined in the published occupant contract module.
OCCUPANT_CONTRACT_PATH = REPO_ROOT / "api" / "agents" / "occupant_contract.py"


# ---------------------------------------------------------------------------
# (i) _validate_context_shape — accepts valid, rejects invalid
# ---------------------------------------------------------------------------

def test_proposal_arrival_valid():
    """Shape 1 — trigger=reactive + non-empty proposal_row dict."""
    ctx = {"proposal_row": {"id": "p1", "action_type": "trade-execute"}}
    assert _validate_context_shape("reactive", ctx, "user-xyz") is None


def test_recurrence_fire_valid():
    """Shape 2 — trigger=reactive + recurrence_prompt + recurrence_slug."""
    ctx = {
        "recurrence_prompt": "Re-evaluate signals.",
        "recurrence_slug": "signal-evaluation",
    }
    assert _validate_context_shape("reactive", ctx, "user-xyz") is None


def test_addressed_valid():
    """Shape 3 — trigger=addressed + non-empty user_message."""
    ctx = {"user_message": "What's our current exposure?"}
    assert _validate_context_shape("addressed", ctx, "user-xyz") is None


def test_reactive_empty_context_rejected():
    """Missing all sub-shape keys → fail loudly."""
    err = _validate_context_shape("reactive", {}, "user-xyz")
    assert err is not None and "reactive trigger requires" in err


def test_reactive_legacy_keys_rejected():
    """Legacy `prompt`/`slug` keys (pre-e55d201) MUST NOT satisfy the
    recurrence-fire shape. This is the exact regression the contract
    is designed to catch — the silent-inert-stand_down bug class."""
    ctx = {"prompt": "Re-evaluate signals.", "slug": "signal-evaluation"}
    err = _validate_context_shape("reactive", ctx, "user-xyz")
    assert err is not None
    # Diagnostic should name the missing canonical keys
    assert "recurrence_prompt" in err and "recurrence_slug" in err


def test_reactive_recurrence_fire_partial_rejected():
    """Either canonical key alone is insufficient — both required."""
    ctx_prompt_only = {"recurrence_prompt": "Do something."}
    ctx_slug_only = {"recurrence_slug": "do-something"}
    assert _validate_context_shape("reactive", ctx_prompt_only, "u") is not None
    assert _validate_context_shape("reactive", ctx_slug_only, "u") is not None


def test_reactive_empty_proposal_rejected():
    """proposal_row must be a non-empty dict (empty dict ≠ valid shape)."""
    err = _validate_context_shape("reactive", {"proposal_row": {}}, "user-xyz")
    assert err is not None


def test_reactive_proposal_row_wrong_type_rejected():
    """proposal_row must be a dict — None / string / list don't count."""
    for bad in (None, "p1", ["p1"]):
        err = _validate_context_shape("reactive", {"proposal_row": bad}, "u")
        assert err is not None, f"should reject proposal_row={bad!r}"


def test_reactive_ambiguous_both_sub_shapes_rejected():
    """Both proposal_row AND recurrence_prompt set → ambiguous, rejected.
    Callers must choose exactly one sub-shape (Reviewer cannot reason
    about both a proposal and a recurrence prompt simultaneously)."""
    ctx = {
        "proposal_row": {"id": "p1"},
        "recurrence_prompt": "Refresh universe.",
        "recurrence_slug": "track-universe",
    }
    err = _validate_context_shape("reactive", ctx, "user-xyz")
    assert err is not None and "ambiguous" in err.lower()


def test_addressed_empty_user_message_rejected():
    """user_message must be non-empty string."""
    for bad in ({}, {"user_message": ""}, {"user_message": "   "}, {"user_message": None}):
        err = _validate_context_shape("addressed", bad, "user-xyz")
        assert err is not None, f"should reject {bad!r}"


def test_unknown_trigger_rejected():
    """Trigger value outside the two-trigger taxonomy → reject."""
    ctx = {"user_message": "hi"}
    err = _validate_context_shape("scheduled", ctx, "user-xyz")
    assert err is not None and "unknown trigger" in err.lower()


def test_non_dict_context_rejected():
    """Context must be a dict (defensive — typed call sites won't hit
    this, but ad-hoc callers might)."""
    err = _validate_context_shape("reactive", "not a dict", "user-xyz")
    assert err is not None and "dict" in err.lower()


# ---------------------------------------------------------------------------
# (ii) Dispatcher↔Reviewer key alignment
# ---------------------------------------------------------------------------

def _read(p: Path) -> str:
    if not p.exists():
        raise AssertionError(f"Missing file: {p.relative_to(REPO_ROOT)}")
    return p.read_text(encoding="utf-8")


def test_dispatcher_uses_canonical_keys():
    """The invocation dispatcher must build context bags using the
    canonical key names. This pairs with test_reactive_legacy_keys_rejected
    above: that one fails the Reviewer side if it accepts legacy names;
    this one fails the dispatcher side if it emits them."""
    src = _read(DISPATCHER_PATH)
    assert '"recurrence_prompt"' in src, (
        "wake.py must build context bags with the canonical "
        "key 'recurrence_prompt'. If you see this failing, the dispatcher "
        "regressed back to the pre-e55d201 key drift."
    )
    assert '"recurrence_slug"' in src, (
        "wake.py must build context bags with the canonical "
        "key 'recurrence_slug'."
    )


def test_dispatcher_does_not_emit_legacy_context_keys():
    """The legacy `trigger_slug` key (pre-2026-05-13) must not appear in
    dispatcher context-bag construction. We check for it as a dict-string
    literal so unrelated identifier uses don't trip the gate."""
    src = _read(DISPATCHER_PATH)
    assert '"trigger_slug"' not in src, (
        "wake.py must not use the legacy key 'trigger_slug' "
        "in context-bag construction — singular implementation per "
        "CLAUDE.md item 1. The Reviewer side dropped its trigger_slug "
        "fallback 2026-05-13."
    )


def test_reviewer_context_typeddict_canonical_keys():
    """ReviewerContext TypedDict must declare the canonical recurrence-fire
    field names and must not declare the legacy `trigger_slug` field."""
    src = _read(OCCUPANT_CONTRACT_PATH)  # ADR-315: ReviewerContext moved here
    assert re.search(r"recurrence_prompt:\s*str", src), (
        "ReviewerContext must declare `recurrence_prompt: str`."
    )
    assert re.search(r"recurrence_slug:\s*str", src), (
        "ReviewerContext must declare `recurrence_slug: str`."
    )
    assert not re.search(r"^\s*trigger_slug:\s*str", src, re.MULTILINE), (
        "ReviewerContext must not declare the legacy `trigger_slug` field — "
        "removed 2026-05-13 per singular-implementation discipline."
    )


def test_invoke_reviewer_calls_validate_context_shape():
    """The contract validator must be wired INTO invoke_reviewer — not
    just defined alongside it. The whole point of Problem B is that the
    boundary fails loudly; a validator that nothing calls is dead code."""
    src = _read(REVIEWER_PATH)
    # Locate the invoke_reviewer body
    match = re.search(
        r"async def invoke_reviewer\([^)]*\)[^:]*:\s*\"\"\".*?\"\"\"(?P<body>.*?)(?=\nasync def |\ndef |\Z)",
        src,
        re.DOTALL,
    )
    assert match, "Could not locate invoke_reviewer function body."
    body = match.group("body")
    assert "_validate_context_shape(" in body, (
        "invoke_reviewer must call _validate_context_shape() in its body. "
        "This is the wiring that turns Problem B's silent-stand_down bug "
        "class into a loud log + None return at the boundary."
    )
    assert "shape_error" in body and "return None" in body, (
        "invoke_reviewer must short-circuit (return None) on shape_error "
        "from _validate_context_shape — not continue into _build_user_message "
        "with a malformed context bag."
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_proposal_arrival_valid,
        test_recurrence_fire_valid,
        test_addressed_valid,
        test_reactive_empty_context_rejected,
        test_reactive_legacy_keys_rejected,
        test_reactive_recurrence_fire_partial_rejected,
        test_reactive_empty_proposal_rejected,
        test_reactive_proposal_row_wrong_type_rejected,
        test_reactive_ambiguous_both_sub_shapes_rejected,
        test_addressed_empty_user_message_rejected,
        test_unknown_trigger_rejected,
        test_non_dict_context_rejected,
        test_dispatcher_uses_canonical_keys,
        test_dispatcher_does_not_emit_legacy_context_keys,
        test_reviewer_context_typeddict_canonical_keys,
        test_invoke_reviewer_calls_validate_context_shape,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(
        f"\n{len(tests) - failed}/{len(tests)} Reviewer context-contract "
        f"assertions passed."
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
