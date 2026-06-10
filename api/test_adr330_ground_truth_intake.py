"""ADR-330 — Ground-Truth Intake: generalizing the consequence pipe.

Regression gate for the five-phase ADR-330 implementation:

  Phase 1 — attestation + retrospective fields on OutcomeCandidate; platform
            providers stamp `platform`; ledger persists fields + segments
            retrospective rows + per-attestation accounting.
  Phase 2 — OperatorOutcomeProvider (CSV import) + reconcile_operator_import
            entrypoint + idempotency; operator NOT in DEFAULT_PROVIDERS.
  Phase 3 — retrospective end-to-end (segmented out of live windows); the
            calibration mirror parses + presents segments.
  Phase 4 — bundle ground-truth declarations (defense-in-depth; ADR-287 owns
            the canonical bundle conformance gate).
  Phase 5 — vocabulary + docstrings (no SQL action_outcomes write target).

Pure-Python assertions. No DB, no network, no LLM. Async providers driven
with a minimal fake Supabase client.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest


# =============================================================================
# Fakes — minimal Supabase-shaped client returning a single file content
# =============================================================================


class _FakeTable:
    def __init__(self, content):
        self._content = content

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        content = self._content
        rows = [{"content": content}] if content is not None else []

        class _R:
            data = rows

        return _R()


class _FakeClient:
    def __init__(self, content):
        self._content = content

    def table(self, name):
        return _FakeTable(self._content)


# =============================================================================
# Phase 1 — fields + platform stamps + ledger segmenting/accounting
# =============================================================================


def test_phase1_outcome_candidate_carries_attestation_and_retrospective():
    """The TypedDict exposes attestation + retrospective (ADR-330 D2 + D3)."""
    from services.outcomes.base import OutcomeCandidate

    keys = OutcomeCandidate.__annotations__
    assert "attestation" in keys, "OutcomeCandidate missing attestation field"
    assert "retrospective" in keys, "OutcomeCandidate missing retrospective field"


def test_phase1_platform_providers_stamp_platform():
    """Both platform providers stamp attestation='platform' on emitted rows.

    Driven against an empty Alpaca/LS (no platform_connection) so reconcile
    returns []; the stamp is asserted via source inspection rather than a
    live API. We assert the literal is present in each emit site."""
    import inspect

    from services.outcomes import commerce, trading

    trading_src = inspect.getsource(trading)
    commerce_src = inspect.getsource(commerce)
    assert '"attestation": "platform"' in trading_src, (
        "trading provider does not stamp attestation='platform'"
    )
    assert '"attestation": "platform"' in commerce_src, (
        "commerce provider does not stamp attestation='platform'"
    )


def test_phase1_ledger_init_seeds_attestation_and_retrospective():
    """A fresh money-truth dict carries by_attestation + retrospective."""
    from services.outcomes.ledger import _init_money_truth

    mt = _init_money_truth("trading")
    assert "by_attestation" in mt
    assert "retrospective" in mt
    assert mt["retrospective"]["totals"]["reconciled_event_count"] == 0


def test_phase1_retrospective_rows_segmented_out_of_live_windows():
    """ADR-330 D3: retrospective rows go to the segmented bucket, NOT the
    live totals / rolling windows / narrative."""
    from services.outcomes.ledger import _apply_entries, _init_money_truth
    from services.outcomes.trading import TradingOutcomeProvider

    prov = TradingOutcomeProvider()
    perf = _init_money_truth("trading")
    now = datetime.now(timezone.utc)
    entries = [
        {  # live platform profit
            "action_type": "t", "executed_at": now, "outcome_label": "closed_profit",
            "outcome_value_cents": 5000, "context_domain": "trading",
            "reconciliation_confidence": "high", "attestation": "platform",
        },
        {  # retrospective operator backfill, 400 days old
            "action_type": "t", "executed_at": now - timedelta(days=400),
            "outcome_label": "closed_profit", "outcome_value_cents": 99999,
            "context_domain": "trading", "reconciliation_confidence": "high",
            "attestation": "operator", "retrospective": True,
        },
    ]
    _apply_entries(perf, entries, prov)

    # Live loop sees only the live row.
    assert perf["totals"]["reconciled_event_count"] == 1
    assert perf["totals"]["aggregate_value_cents"] == 5000
    assert perf["rolling_7d"]["value_cents"] == 5000  # backfill not in window

    # Backfill is segmented.
    assert perf["retrospective"]["totals"]["reconciled_event_count"] == 1
    assert perf["retrospective"]["totals"]["aggregate_value_cents"] == 99999


def test_phase1_attestation_accounting_counts_all_rows():
    """by_attestation counts every row (live + retrospective) by level."""
    from services.outcomes.ledger import _apply_entries, _init_money_truth
    from services.outcomes.trading import TradingOutcomeProvider

    prov = TradingOutcomeProvider()
    perf = _init_money_truth("trading")
    now = datetime.now(timezone.utc)
    entries = [
        {"action_type": "t", "executed_at": now, "outcome_label": "p",
         "outcome_value_cents": 10, "context_domain": "trading",
         "reconciliation_confidence": "high", "attestation": "platform"},
        {"action_type": "t", "executed_at": now, "outcome_label": "p",
         "outcome_value_cents": 20, "context_domain": "trading",
         "reconciliation_confidence": "high", "attestation": "operator"},
        {"action_type": "t", "executed_at": now, "outcome_label": "p",
         "outcome_value_cents": -5, "context_domain": "trading",
         "reconciliation_confidence": "high", "attestation": "agent"},
    ]
    _apply_entries(perf, entries, prov)
    assert perf["by_attestation"] == {"platform": 1, "operator": 1, "agent": 1}


def test_phase1_render_surfaces_attestation_backfill_and_inline_flag():
    """Rendered _money_truth.md shows the attestation line, backfill section,
    and an inline [via X] flag on non-platform narrative bullets."""
    from services.outcomes.ledger import (
        _apply_entries,
        _init_money_truth,
        _render_money_truth_file,
    )
    from services.outcomes.trading import TradingOutcomeProvider

    prov = TradingOutcomeProvider()
    perf = _init_money_truth("trading")
    now = datetime.now(timezone.utc)
    entries = [
        {"action_type": "t", "executed_at": now, "outcome_label": "closed_loss",
         "outcome_value_cents": -1200, "context_domain": "trading",
         "reconciliation_confidence": "high", "attestation": "operator"},
        {"action_type": "t", "executed_at": now - timedelta(days=400),
         "outcome_label": "closed_profit", "outcome_value_cents": 99999,
         "context_domain": "trading", "reconciliation_confidence": "high",
         "attestation": "operator", "retrospective": True},
    ]
    _apply_entries(perf, entries, prov)
    rendered = _render_money_truth_file(perf)
    assert "**Attestation:**" in rendered
    assert "## Backfilled history" in rendered
    assert "[via operator]" in rendered


def test_phase1_backward_compat_existing_rows_read_as_platform():
    """Rows written before ADR-330 (no attestation, no retrospective) flow
    through unchanged — default to live + platform-counted."""
    from services.outcomes.ledger import _apply_entries, _init_money_truth
    from services.outcomes.trading import TradingOutcomeProvider

    prov = TradingOutcomeProvider()
    perf = _init_money_truth("trading")
    now = datetime.now(timezone.utc)
    # No attestation, no retrospective — the pre-ADR-330 shape.
    entries = [{
        "action_type": "t", "executed_at": now, "outcome_label": "closed_profit",
        "outcome_value_cents": 4200, "context_domain": "trading",
        "reconciliation_confidence": "high",
    }]
    _apply_entries(perf, entries, prov)
    assert perf["totals"]["reconciled_event_count"] == 1  # live, not segmented
    assert perf["by_attestation"] == {"platform": 1}  # defaults to platform


# =============================================================================
# Phase 2 — operator CSV provider + entrypoint + idempotency
# =============================================================================


_OPERATOR_CSV = (
    "context_domain,outcome_label,executed_at,outcome_value_cents,external_id,"
    "retrospective,proposal_id,note\n"
    "trading,closed_profit,2026-06-01T15:00:00Z,5000,ext-1,,prop-abc,first\n"
    "trading,closed_loss,2026-05-01T15:00:00Z,-2000,,true,,backfill\n"
    "revenue,revenue_received,2026-06-02T10:00:00Z,1999,ord-9,,,vip\n"
    ",missing_domain_ok,2026-06-03T10:00:00Z,100,ext-x,,,default domain\n"
    "badrow,,,,,,,\n"
)


def test_phase2_operator_provider_parses_csv_with_attestation_operator():
    """OperatorOutcomeProvider parses rows, stamps attestation='operator',
    applies default domain, honors retrospective, elevates confidence on
    proposal_id, skips rows missing outcome_label."""
    from services.outcomes.operator import OperatorOutcomeProvider

    prov = OperatorOutcomeProvider("/workspace/uploads/trades.md")
    client = _FakeClient(_OPERATOR_CSV)
    cands = asyncio.run(
        prov.reconcile("user-1234", client, datetime(2020, 1, 1, tzinfo=timezone.utc))
    )
    assert len(cands) == 4  # badrow skipped
    assert all(c["attestation"] == "operator" for c in cands)
    # default domain applied to the comma-leading row
    assert cands[3]["context_domain"] == "trading"
    # proposal_id elevates confidence
    assert cands[0]["reconciliation_confidence"] == "high"
    assert cands[1]["reconciliation_confidence"] == "medium"
    # retrospective flag honored
    assert cands[1].get("retrospective") is True
    # extra column carried into metadata
    assert cands[0]["outcome_metadata"].get("note") == "first"


def test_phase2_operator_import_idempotency_keys_are_stable():
    """Same CSV → same idempotency keys (external_id wins; derived row-hash
    is stable across runs). Re-import is a ledger no-op, not a double-count."""
    from services.outcomes.operator import OperatorOutcomeProvider

    prov = OperatorOutcomeProvider("/workspace/uploads/trades.md")
    client = _FakeClient(_OPERATOR_CSV)
    run1 = asyncio.run(prov.reconcile("u", client, datetime(2020, 1, 1, tzinfo=timezone.utc)))
    run2 = asyncio.run(prov.reconcile("u", client, datetime(2020, 1, 1, tzinfo=timezone.utc)))
    keys1 = [c["outcome_metadata"]["operator_event_key"] for c in run1]
    keys2 = [c["outcome_metadata"]["operator_event_key"] for c in run2]
    assert keys1 == keys2, "operator import keys not stable across runs"
    # external_id rows use the operator id verbatim
    assert "ext-1" in keys1


def test_phase2_operator_not_in_default_providers():
    """ADR-330 anti-goal: DEFAULT_PROVIDERS stays platform-only; the operator
    provider is on-demand (addressed invocation), never always-on."""
    from services.outcomes import DEFAULT_PROVIDERS

    names = {p.provider_name for p in DEFAULT_PROVIDERS}
    assert names == {"trading-reconciler-v1", "commerce-reconciler-v1"}
    assert "operator-import-v1" not in names


def test_phase2_reconcile_operator_import_entrypoint_exists():
    """The addressed-invocation entrypoint is exported and routes through the
    single reconciler (no parallel pipe)."""
    import inspect

    from services.outcomes import reconcile_operator_import

    assert inspect.iscoroutinefunction(reconcile_operator_import)
    src = inspect.getsource(reconcile_operator_import)
    assert "reconcile_user" in src, (
        "operator import entrypoint must route through reconcile_user — "
        "the single intake pipe, not a parallel path"
    )


def test_phase2_empty_import_returns_no_candidates():
    """No staged file → [] (provider tolerant, never raises)."""
    from services.outcomes.operator import OperatorOutcomeProvider

    prov = OperatorOutcomeProvider("/workspace/uploads/missing.md")
    client = _FakeClient(None)
    cands = asyncio.run(prov.reconcile("u", client, datetime(2020, 1, 1, tzinfo=timezone.utc)))
    assert cands == []


# =============================================================================
# Phase 3 — mirror parses + presents segments
# =============================================================================


def test_phase3_mirror_parses_ground_truth_segments():
    """The calibration mirror extracts by_attestation + retrospective from
    the ground-truth frontmatter, tolerating malformed input."""
    from services.outcomes.ledger import (
        _apply_entries,
        _init_money_truth,
        _render_money_truth_file,
    )
    from services.outcomes.trading import TradingOutcomeProvider
    from services.primitives.mirror_calibration import _parse_ground_truth_segments

    prov = TradingOutcomeProvider()
    perf = _init_money_truth("trading")
    now = datetime.now(timezone.utc)
    _apply_entries(perf, [
        {"action_type": "t", "executed_at": now, "outcome_label": "p",
         "outcome_value_cents": 1, "context_domain": "trading",
         "reconciliation_confidence": "high", "attestation": "platform"},
        {"action_type": "t", "executed_at": now, "outcome_label": "p",
         "outcome_value_cents": 2, "context_domain": "trading",
         "reconciliation_confidence": "high", "attestation": "agent"},
        {"action_type": "t", "executed_at": now - timedelta(days=400),
         "outcome_label": "p", "outcome_value_cents": 3, "context_domain": "trading",
         "reconciliation_confidence": "high", "attestation": "operator",
         "retrospective": True},
    ], prov)
    rendered = _render_money_truth_file(perf)

    att, retro = _parse_ground_truth_segments(rendered)
    assert att == {"platform": 1, "agent": 1, "operator": 1}
    assert (retro.get("totals") or {}).get("reconciled_event_count") == 1


def test_phase3_mirror_segment_parse_is_malformed_tolerant():
    """Bad / missing frontmatter → ({}, {}), never raises."""
    from services.primitives.mirror_calibration import _parse_ground_truth_segments

    assert _parse_ground_truth_segments("") == ({}, {})
    assert _parse_ground_truth_segments("no frontmatter") == ({}, {})
    assert _parse_ground_truth_segments("---\nnot json\n---\nbody") == ({}, {})


# =============================================================================
# Phase 4 — bundle ground-truth declarations (defense-in-depth)
# =============================================================================
#
# ADR-287's test owns the canonical bundle-conformance gate. These assert the
# specific ADR-330 D4 outcome: the second active program (alpha-author) now
# resolves a ground-truth path through bundle_reader, lighting its loop.


def test_phase4_alpha_author_declares_ground_truth():
    """ADR-330 D4: alpha-author declares substrate_abi.ground_truth pointing
    at _signal.md — the one-line gap that was leaving its loop dark."""
    from services.bundle_reader import _load_manifest

    m = _load_manifest("alpha-author")
    assert m is not None
    gt = (m.get("substrate_abi") or {}).get("ground_truth")
    assert gt == "operation/authored/_signal.md", (
        f"alpha-author ground_truth should be operation/authored/_signal.md, got {gt!r}"
    )


def test_phase4_alpha_trader_ground_truth_unchanged():
    """alpha-trader's existing declaration is preserved (no regression)."""
    from services.bundle_reader import _load_manifest

    m = _load_manifest("alpha-trader")
    gt = (m.get("substrate_abi") or {}).get("ground_truth")
    assert gt == "operation/trading/_money_truth.md"


# =============================================================================
# Phase 5 — no SQL action_outcomes write target
# =============================================================================


def test_phase5_no_action_outcomes_sql_write_target():
    """ADR-195 v2 moved persistence to the filesystem; ADR-330 D5 corrects
    the stale prose. No outcomes-module code references action_outcomes as a
    live storage target (only as an explicitly-dropped historical note)."""
    import inspect

    from services.outcomes import base, commerce, ledger, operator, reconciler, trading

    for mod in (base, ledger, reconciler, trading, commerce, operator):
        src = inspect.getsource(mod)
        for line in src.splitlines():
            if "action_outcomes" not in line:
                continue
            lowered = line.lower()
            # Permitted: prose that explicitly names the table as dropped/moved.
            assert any(
                marker in lowered
                for marker in ("dropped", "no longer", "moved persistence")
            ), (
                f"{mod.__name__} references action_outcomes as a live target: "
                f"{line.strip()!r}"
            )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
