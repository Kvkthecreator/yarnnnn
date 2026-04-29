"""
Validation Suite — ADR-233 Phase 2 (Natural-home pre-read across all generative shapes)

Tests (12 assertions):
  Helper unit tests — _load_natural_home_brief (6):
   1. DELIVERABLE + prior output.md exists → brief contains "## Prior Output"
      with the date marker and content excerpt.
   2. DELIVERABLE + no prior runs → returns None (first-run case).
   3. ACCUMULATION + domain folder with entities → brief contains "## Domain State"
      with entity inventory.
   4. ACCUMULATION + empty domain folder → returns None (first accumulation pass).
   5. ACTION + operation folder with files → brief contains "## Pending Operations"
      with file inventory.
   6. ACTION + empty operation folder → returns None.

  Helper contract (2):
   7. MAINTENANCE shape → returns None without I/O (early exit before any
      DB query — the dotted-executor branch never reaches LLM).
   8. Helper does not raise on DB error; returns None instead (resilience).

  Wiring tests (2):
   9. build_task_execution_prompt accepts `natural_home_brief` parameter and
      threads it into the user message verbatim (with the brief's own header).
  10. build_task_execution_prompt with empty brief produces a user message
      that does NOT contain the natural-home headers.

  Posture content (2):
  11. Each headless posture (deliverable, accumulation, action) contains the
      conditional framing language ("If a `## ...` block appears below").
  12. Phase 1 regression — `prior_output` parameter is fully gone from
      build_task_execution_prompt; signature carries `natural_home_brief`
      instead. (Singular Implementation rule 1.)

Strategy: pure-Python helper tests with a stub Supabase client (mock
`.table().select().eq().like().order().limit().execute()` chain). No real
DB, no LLM. Pure-Python posture content checks.

Usage:
    cd api && python test_adr233_phase2_natural_home_preread.py
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

REPO_API = Path(__file__).parent
RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    icon = "✓" if ok else "✗"
    logger.info(f"{icon} {name}: {detail}")


# ---------------------------------------------------------------------------
# Test fixtures — stub Supabase client + stub RecurrenceDeclaration
# ---------------------------------------------------------------------------


def _stub_decl(shape_value: str, slug: str = "test-decl", domain: str | None = None):
    """Build a minimal stand-in for a RecurrenceDeclaration. The helper only
    reads `.shape` (with `.value`), `.slug`, and `.domain`; nothing else."""
    from services.recurrence import RecurrenceShape
    shape_map = {
        "DELIVERABLE": RecurrenceShape.DELIVERABLE,
        "ACCUMULATION": RecurrenceShape.ACCUMULATION,
        "ACTION": RecurrenceShape.ACTION,
        "MAINTENANCE": RecurrenceShape.MAINTENANCE,
    }
    decl = SimpleNamespace()
    decl.shape = shape_map[shape_value]
    decl.slug = slug
    decl.domain = domain
    decl.declaration_path = f"/test/{slug}.yaml"
    decl.output_path = None
    return decl


class StubQuery:
    """Stub query builder that records the chained calls and returns a fixed result."""

    def __init__(self, rows: list[dict] | None = None):
        self.rows = rows or []
        self.calls: list[tuple[str, tuple, dict]] = []

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        return self

    def select(self, *args, **kwargs):
        return self._record("select", *args, **kwargs)

    def eq(self, *args, **kwargs):
        return self._record("eq", *args, **kwargs)

    def like(self, *args, **kwargs):
        return self._record("like", *args, **kwargs)

    def order(self, *args, **kwargs):
        return self._record("order", *args, **kwargs)

    def limit(self, *args, **kwargs):
        return self._record("limit", *args, **kwargs)

    def in_(self, *args, **kwargs):
        return self._record("in_", *args, **kwargs)

    def execute(self):
        return SimpleNamespace(data=self.rows)


class StubClient:
    """Stub Supabase client. Maps `path -> rows` for table('workspace_files')
    queries. The helper makes one or two queries per shape; the stub returns
    a fixed list each call (caller can re-set between calls if needed)."""

    def __init__(self, rows: list[dict] | None = None, second_rows: list[dict] | None = None):
        self._rows_queue = [rows or [], second_rows or []]
        self.calls = 0

    def table(self, name):
        rows = self._rows_queue[min(self.calls, len(self._rows_queue) - 1)]
        self.calls += 1
        return StubQuery(rows)


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


def test_deliverable_prior_output_present():
    from services.dispatch_helpers import _load_natural_home_brief
    decl = _stub_decl("DELIVERABLE", slug="weekly-brief")
    rows = [
        {
            "path": "/workspace/reports/weekly-brief/2026-04-22/output.md",
            "content": "# Weekly Brief\n\nSection 1: foo\nSection 2: bar",
            "updated_at": "2026-04-22T10:00:00Z",
        }
    ]
    client = StubClient(rows=rows)
    brief = asyncio.run(_load_natural_home_brief(client, "user-123", decl))
    ok = (
        brief is not None
        and "## Prior Output" in brief
        and "2026-04-22" in brief
        and "Section 1: foo" in brief
    )
    record(
        "test_deliverable_prior_output_present",
        ok,
        f"brief={'yes' if brief else 'None'} len={len(brief) if brief else 0}",
    )


def test_deliverable_no_prior_returns_none():
    from services.dispatch_helpers import _load_natural_home_brief
    decl = _stub_decl("DELIVERABLE", slug="brand-new-brief")
    client = StubClient(rows=[])
    brief = asyncio.run(_load_natural_home_brief(client, "user-123", decl))
    ok = brief is None
    record("test_deliverable_no_prior_returns_none", ok, f"brief={brief!r}")


def test_accumulation_inventory_present():
    from services.dispatch_helpers import _load_natural_home_brief
    decl = _stub_decl("ACCUMULATION", slug="track-competitors", domain="competitors")
    rows = [
        {"path": "/workspace/context/competitors/anthropic/profile.md", "updated_at": "2026-04-20T00:00:00Z"},
        {"path": "/workspace/context/competitors/anthropic/signals.md", "updated_at": "2026-04-22T00:00:00Z"},
        {"path": "/workspace/context/competitors/openai/profile.md", "updated_at": "2026-04-21T00:00:00Z"},
        {"path": "/workspace/context/competitors/landscape.md", "updated_at": "2026-04-22T00:00:00Z"},
    ]
    # Second query (landscape.md content fetch) returns the synthesis content
    landscape_rows = [{"content": "Domain summary: 2 active competitors..."}]
    client = StubClient(rows=rows, second_rows=landscape_rows)
    brief = asyncio.run(_load_natural_home_brief(client, "user-123", decl))
    ok = (
        brief is not None
        and "## Domain State" in brief
        and "competitors" in brief
        and "anthropic" in brief
        and "openai" in brief
        and "Existing entities (2)" in brief
    )
    record(
        "test_accumulation_inventory_present",
        ok,
        f"brief={'yes' if brief else 'None'} len={len(brief) if brief else 0}",
    )


def test_accumulation_empty_returns_none():
    from services.dispatch_helpers import _load_natural_home_brief
    decl = _stub_decl("ACCUMULATION", slug="track-fresh", domain="fresh-domain")
    client = StubClient(rows=[])
    brief = asyncio.run(_load_natural_home_brief(client, "user-123", decl))
    ok = brief is None
    record("test_accumulation_empty_returns_none", ok, f"brief={brief!r}")


def test_action_pending_state_present():
    from services.dispatch_helpers import _load_natural_home_brief
    decl = _stub_decl("ACTION", slug="trade-execute")
    rows = [
        {"path": "/workspace/operations/trade-execute/_run_log.md", "updated_at": "2026-04-22T10:00:00Z"},
        {"path": "/workspace/operations/trade-execute/proposal_2026-04-22.md", "updated_at": "2026-04-22T10:00:00Z"},
    ]
    log_rows = [{"content": "2026-04-21: proposed AAPL buy 10\n2026-04-22: proposed MSFT buy 5"}]
    client = StubClient(rows=rows, second_rows=log_rows)
    brief = asyncio.run(_load_natural_home_brief(client, "user-123", decl))
    ok = (
        brief is not None
        and "## Pending Operations" in brief
        and "trade-execute" in brief
        and "_run_log.md" in brief
    )
    record(
        "test_action_pending_state_present",
        ok,
        f"brief={'yes' if brief else 'None'} len={len(brief) if brief else 0}",
    )


def test_action_empty_returns_none():
    from services.dispatch_helpers import _load_natural_home_brief
    decl = _stub_decl("ACTION", slug="brand-new-action")
    client = StubClient(rows=[])
    brief = asyncio.run(_load_natural_home_brief(client, "user-123", decl))
    ok = brief is None
    record("test_action_empty_returns_none", ok, f"brief={brief!r}")


# ---------------------------------------------------------------------------
# Helper contract
# ---------------------------------------------------------------------------


def test_maintenance_returns_none_without_io():
    """MAINTENANCE shape never reaches LLM dispatch (dotted executor). The
    helper should early-exit before any DB call so it's safe to invoke from
    any caller without conditional gating."""
    from services.dispatch_helpers import _load_natural_home_brief
    decl = _stub_decl("MAINTENANCE", slug="back-office-cleanup")
    client = StubClient(rows=[{"would": "be ignored"}])
    brief = asyncio.run(_load_natural_home_brief(client, "user-123", decl))
    ok = brief is None and client.calls == 0  # no .table() call made
    record(
        "test_maintenance_returns_none_without_io",
        ok,
        f"brief={brief!r} db_calls={client.calls}",
    )


def test_helper_resilient_on_db_error():
    """Helper must not propagate DB errors. Returns None on any exception."""
    from services.dispatch_helpers import _load_natural_home_brief

    class BoomClient:
        def table(self, name):
            raise RuntimeError("simulated DB outage")

    decl = _stub_decl("DELIVERABLE", slug="sturdy-test")
    brief = asyncio.run(_load_natural_home_brief(BoomClient(), "user-123", decl))
    ok = brief is None
    record("test_helper_resilient_on_db_error", ok, f"brief={brief!r}")


# ---------------------------------------------------------------------------
# Wiring tests
# ---------------------------------------------------------------------------


def test_build_task_execution_prompt_threads_brief():
    from services.dispatch_helpers import build_task_execution_prompt
    brief = "## Prior Output (latest run, 2026-04-22)\n\nSection 1: foo"
    sb, um = build_task_execution_prompt(
        task_info={"title": "T", "objective": {}, "success_criteria": []},
        agent={"role": "writer"},
        agent_instructions="X",
        context="(none)",
        shape="DELIVERABLE",
        natural_home_brief=brief,
    )
    ok = brief in um
    record(
        "test_build_task_execution_prompt_threads_brief",
        ok,
        f"brief at offset {um.find('## Prior Output')}",
    )


def test_empty_brief_produces_no_natural_home_headers():
    from services.dispatch_helpers import build_task_execution_prompt
    sb, um = build_task_execution_prompt(
        task_info={"title": "T", "objective": {}, "success_criteria": []},
        agent={"role": "writer"},
        agent_instructions="X",
        context="(none)",
        shape="DELIVERABLE",
        natural_home_brief="",
    )
    # The Phase 1 base block describes a generic "Prior Output" hook in
    # `HEADLESS_BASE_BLOCK`; that's expected. The wiring test asserts that
    # NO Phase-2 brief block (## Prior Output (latest run, ...)) gets
    # injected into the user message when the brief is empty.
    has_phase2_block = "(latest run," in um or "## Domain State (what" in um or "## Pending Operations" in um
    ok = not has_phase2_block
    record(
        "test_empty_brief_produces_no_natural_home_headers",
        ok,
        f"phase2_block_present={has_phase2_block}",
    )


# ---------------------------------------------------------------------------
# Posture content
# ---------------------------------------------------------------------------


def test_postures_contain_conditional_framing():
    from agents.prompts import (
        DELIVERABLE_POSTURE,
        ACCUMULATION_POSTURE,
        ACTION_POSTURE,
    )
    deliverable_ok = (
        "If a `## Prior Output` block appears below" in DELIVERABLE_POSTURE
        and "first run" in DELIVERABLE_POSTURE.lower()
    )
    accumulation_ok = (
        "If a `## Domain State` block appears below" in ACCUMULATION_POSTURE
        and "first accumulation pass" in ACCUMULATION_POSTURE.lower()
    )
    action_ok = (
        "If a `## Pending Operations` block appears below" in ACTION_POSTURE
        and "no pending state" in ACTION_POSTURE.lower()
    )
    ok = deliverable_ok and accumulation_ok and action_ok
    record(
        "test_postures_contain_conditional_framing",
        ok,
        f"deliverable={deliverable_ok} accumulation={accumulation_ok} action={action_ok}",
    )


# ---------------------------------------------------------------------------
# Phase 1 regression
# ---------------------------------------------------------------------------


def test_prior_output_param_fully_removed():
    """Phase 1 reserved `prior_output` for Phase 2; Phase 2 spends it.
    The signature should now carry `natural_home_brief`, never `prior_output`.
    Singular Implementation rule 1: no parallel placeholder param surviving."""
    from services.dispatch_helpers import build_task_execution_prompt
    sig = inspect.signature(build_task_execution_prompt)
    params = list(sig.parameters.keys())
    has_natural = "natural_home_brief" in params
    no_prior = "prior_output" not in params
    no_task_mode = "task_mode" not in params  # reaffirms Phase 1 deletion
    ok = has_natural and no_prior and no_task_mode
    record(
        "test_prior_output_param_fully_removed",
        ok,
        f"natural_home_brief={has_natural} prior_output={'still present!' if not no_prior else 'gone'} task_mode={'still present!' if not no_task_mode else 'gone'}",
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main():
    tests = [
        test_deliverable_prior_output_present,
        test_deliverable_no_prior_returns_none,
        test_accumulation_inventory_present,
        test_accumulation_empty_returns_none,
        test_action_pending_state_present,
        test_action_empty_returns_none,
        test_maintenance_returns_none_without_io,
        test_helper_resilient_on_db_error,
        test_build_task_execution_prompt_threads_brief,
        test_empty_brief_produces_no_natural_home_headers,
        test_postures_contain_conditional_framing,
        test_prior_output_param_fully_removed,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            record(t.__name__, False, f"EXCEPTION: {type(e).__name__}: {e}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    logger.info("")
    logger.info(f"━━ ADR-233 Phase 2 gate: {passed}/{total} passed ━━")
    if passed < total:
        for name, ok, detail in RESULTS:
            if not ok:
                logger.error(f"FAIL {name}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
