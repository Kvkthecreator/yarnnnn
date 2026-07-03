"""ADR-402 — Model Routing as Kernel Data: regression gate.

Locks the three claims of Part A (the pure refactor):

1. The routing table is the SINGLE model-selection site on the Freddie
   occupant path — no raw model ids in `agents/freddie_agent.py` or
   `agents/occupant_contract.py`; the occupant consumes `resolve_route`.
2. Shape classification is byte-identical to the pre-table branch
   (`use_sonnet = trigger == "reactive" and not is_recurrence_fire`),
   including the legacy else-branch for unknown triggers.
3. Env overrides work per shape, are read at resolve time, and malformed
   values fall back to the table.

The DEFAULT VALUES themselves (which model serves which shape) are pinned to
whatever the table declares at the time — Part B revises them as a data
change; this gate asserts structure, not the tier decision, EXCEPT the
Part-A anchor test which pins byte-identity to the pre-refactor routing and
is updated in the same commit as any ratified routing change.

Pure offline: no LLM, no DB, no network.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from services.model_routing import (
    DEFAULT_ROUTES,
    SHAPE_ADDRESSED,
    SHAPE_PROPOSAL,
    SHAPE_RECURRENCE,
    classify_shape,
    resolve_route,
)

_MODEL_ID_RE = re.compile(r"claude-[a-z0-9][a-z0-9.-]*")


def _clear_env():
    for shape in (SHAPE_ADDRESSED, SHAPE_PROPOSAL, SHAPE_RECURRENCE):
        os.environ.pop(f"YARNNN_MODEL_{shape.upper()}", None)
        os.environ.pop(f"YARNNN_ROUNDS_{shape.upper()}", None)


# ---------------------------------------------------------------------------
# 1. Single model-selection site
# ---------------------------------------------------------------------------

def test_no_model_ids_in_occupant_module():
    """freddie_agent.py must not carry raw model ids — the table is the site."""
    src = (_API_ROOT / "agents" / "freddie_agent.py").read_text()
    hits = _MODEL_ID_RE.findall(src)
    assert not hits, f"raw model ids in freddie_agent.py: {hits}"


def test_no_model_ids_in_occupant_contract():
    """The published ABI stays pure data — no model ids, no routing import."""
    src = (_API_ROOT / "agents" / "occupant_contract.py").read_text()
    # FREDDIE_MODEL_IDENTITY ("ai:freddie-sonnet-v8") is an occupant VERSION
    # name, not a model id — the regex targets real API model ids.
    hits = _MODEL_ID_RE.findall(src)
    assert not hits, f"raw model ids in occupant_contract.py: {hits}"
    assert "model_routing" not in src, (
        "occupant_contract.py must not import the routing module (pure data, "
        "typing-only — ADR-315)"
    )


def test_occupant_consumes_the_table():
    src = (_API_ROOT / "agents" / "freddie_agent.py").read_text()
    assert "from services.model_routing import resolve_route" in src
    assert "route = resolve_route(trigger, is_recurrence_fire)" in src
    assert "model = route.model" in src
    assert "max_rounds = route.max_rounds" in src
    # The dead pre-ADR-402 constants stay deleted.
    for banned in ("_SONNET =", "_HAIKU =", "_CALLER_SONNET", "_CALLER_HAIKU",
                   "use_sonnet"):
        assert banned not in src, f"pre-table residue in freddie_agent.py: {banned}"


def test_table_covers_exactly_the_three_shapes():
    assert set(DEFAULT_ROUTES) == {SHAPE_ADDRESSED, SHAPE_PROPOSAL, SHAPE_RECURRENCE}
    for shape, route in DEFAULT_ROUTES.items():
        assert route.model.startswith("claude-"), (shape, route.model)
        assert route.max_rounds >= 1, (shape, route.max_rounds)


# ---------------------------------------------------------------------------
# 2. Byte-identical shape classification (the Part-A anchor)
# ---------------------------------------------------------------------------

def test_classification_mirrors_the_legacy_branch():
    assert classify_shape("reactive", False) == SHAPE_PROPOSAL
    assert classify_shape("reactive", True) == SHAPE_RECURRENCE
    assert classify_shape("addressed", False) == SHAPE_ADDRESSED
    assert classify_shape("addressed", True) == SHAPE_ADDRESSED
    # Legacy else-branch: any non-reactive trigger routed to the Haiku arm.
    assert classify_shape("anything-else", False) == SHAPE_ADDRESSED


def test_part_b_routing_is_one_model_all_shapes():
    """Pin the ADR-402 Part-B decision (stabilization prior, 2026-07-03):
    ONE model for all three shapes, uniform 20-round COST ceiling (the
    3-round proposal behavioral cap retired — trust-the-model; the
    verdict-early ask rule is the proposal behavior control). Evidence in
    docs/evaluations/2026-07-03-rung4-part{A,B}-*. UPDATE THIS TEST in the
    same commit as any future ratified routing change."""
    _clear_env()
    addressed = resolve_route("addressed", False)
    proposal = resolve_route("reactive", False)
    recurrence = resolve_route("reactive", True)
    assert addressed == proposal == recurrence
    assert addressed.max_rounds == 20
    assert "sonnet" in addressed.model


# ---------------------------------------------------------------------------
# 3. Env overrides
# ---------------------------------------------------------------------------

def test_env_override_model_per_shape():
    _clear_env()
    try:
        os.environ["YARNNN_MODEL_ADDRESSED"] = "claude-sonnet-4-6"
        assert resolve_route("addressed", False).model == "claude-sonnet-4-6"
        # Other shapes untouched.
        assert resolve_route("reactive", True).model == DEFAULT_ROUTES[SHAPE_RECURRENCE].model
    finally:
        _clear_env()


def test_env_override_rounds_and_malformed_fallback():
    _clear_env()
    try:
        os.environ["YARNNN_ROUNDS_PROPOSAL"] = "12"
        assert resolve_route("reactive", False).max_rounds == 12
        os.environ["YARNNN_ROUNDS_PROPOSAL"] = "zero"
        assert resolve_route("reactive", False).max_rounds == DEFAULT_ROUTES[SHAPE_PROPOSAL].max_rounds
        os.environ["YARNNN_ROUNDS_PROPOSAL"] = "0"
        assert resolve_route("reactive", False).max_rounds == DEFAULT_ROUTES[SHAPE_PROPOSAL].max_rounds
    finally:
        _clear_env()


def test_env_is_read_at_resolve_time_not_import_time():
    _clear_env()
    before = resolve_route("addressed", False)
    try:
        os.environ["YARNNN_MODEL_ADDRESSED"] = "claude-test-override"
        after = resolve_route("addressed", False)
        assert after.model == "claude-test-override"
        assert before.model == DEFAULT_ROUTES[SHAPE_ADDRESSED].model
    finally:
        _clear_env()
    assert resolve_route("addressed", False) == before


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ✓ {name}")
            except AssertionError as exc:
                print(f"  ✗ {name}: {exc}")
                fails += 1
    sys.exit(1 if fails else 0)
