"""
Test gate for ADR-231 Phase 2 — Recurrence declaration infrastructure.

Validates the YAML parser + path conventions + walker without needing a live
Supabase client. Run as a regular pytest file:

    cd api && python -m pytest test_adr231_recurrence.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone

from services.recurrence import (
    RecurrenceShape,
    RecurrenceDeclaration,
    shape_for_path,
    parse_recurrence_yaml,
    derive_declaration_path,
    serialize_declaration_yaml,
)


# ---------------------------------------------------------------------------
# shape_for_path
# ---------------------------------------------------------------------------


def test_shape_for_path_domain_recurring():
    assert (
        shape_for_path("/workspace/context/competitors/_recurring.yaml")
        == RecurrenceShape.ACCUMULATION
    )
    assert (
        shape_for_path("/workspace/context/market/_recurring.yaml")
        == RecurrenceShape.ACCUMULATION
    )


def test_shape_for_path_report_spec():
    assert (
        shape_for_path("/workspace/reports/market-weekly/_spec.yaml")
        == RecurrenceShape.DELIVERABLE
    )


def test_shape_for_path_operation_action():
    assert (
        shape_for_path("/workspace/operations/slack-standup/_action.yaml")
        == RecurrenceShape.ACTION
    )


def test_shape_for_path_back_office():
    assert (
        shape_for_path("/workspace/_shared/back-office.yaml")
        == RecurrenceShape.MAINTENANCE
    )


def test_shape_for_path_unrecognized_returns_none():
    assert shape_for_path("/workspace/context/competitors/_domain.md") is None
    assert shape_for_path("/workspace/random/file.yaml") is None
    assert shape_for_path("/tasks/legacy/TASK.md") is None


# ---------------------------------------------------------------------------
# parse_recurrence_yaml — single-declaration files
# ---------------------------------------------------------------------------


def test_parse_deliverable_with_wrapper():
    yaml_content = """
report:
  slug: market-weekly
  display_name: "Weekly Market Report"
  output_path: "/workspace/reports/market-weekly/{date}/output.md"
  recurring:
    schedule: "0 9 * * 1"
    paused: false
  agents: [analyst, writer]
  context_reads: [competitors, market]
"""
    path = "/workspace/reports/market-weekly/_spec.yaml"
    decls = parse_recurrence_yaml(yaml_content, path)
    assert len(decls) == 1
    d = decls[0]
    assert d.shape == RecurrenceShape.DELIVERABLE
    assert d.slug == "market-weekly"
    assert d.declaration_path == path
    assert d.schedule == "0 9 * * 1"
    assert d.paused is False
    assert d.display_name == "Weekly Market Report"
    assert d.output_path == "/workspace/reports/market-weekly/{date}/output.md"
    assert d.agents == ["analyst", "writer"]
    assert d.context_reads == ["competitors", "market"]


def test_parse_deliverable_flat():
    """Slug derived from path when not in body, no `report:` wrapper."""
    yaml_content = """
display_name: "Daily Update"
schedule: "0 7 * * *"
agents: [reporting]
"""
    path = "/workspace/reports/daily-update/_spec.yaml"
    decls = parse_recurrence_yaml(yaml_content, path)
    assert len(decls) == 1
    d = decls[0]
    assert d.shape == RecurrenceShape.DELIVERABLE
    assert d.slug == "daily-update"
    assert d.schedule == "0 7 * * *"


def test_parse_action_with_wrapper():
    yaml_content = """
action:
  slug: slack-standup
  display_name: "Daily Slack Standup"
  recurring:
    schedule: "0 9 * * 1-5"
    paused: false
  target_capability: write_slack
  target_channel: "#standup"
"""
    path = "/workspace/operations/slack-standup/_action.yaml"
    decls = parse_recurrence_yaml(yaml_content, path)
    assert len(decls) == 1
    d = decls[0]
    assert d.shape == RecurrenceShape.ACTION
    assert d.slug == "slack-standup"
    assert d.schedule == "0 9 * * 1-5"
    assert d.data.get("target_capability") == "write_slack"


# ---------------------------------------------------------------------------
# parse_recurrence_yaml — domain accumulation (multi-declaration)
# ---------------------------------------------------------------------------


def test_parse_domain_recurring_multi():
    yaml_content = """
recurrences:
  - slug: competitors-weekly-scan
    schedule: "0 9 * * 1"
    agent: researcher
    objective: "Weekly competitive moves"
    paused: false
    context_writes: [competitors]
  - slug: competitors-funding-check
    schedule: "0 6 * * 1"
    agent: tracker
    paused: true
"""
    path = "/workspace/context/competitors/_recurring.yaml"
    decls = parse_recurrence_yaml(yaml_content, path)
    assert len(decls) == 2
    assert all(d.shape == RecurrenceShape.ACCUMULATION for d in decls)
    assert decls[0].slug == "competitors-weekly-scan"
    assert decls[0].agents == ["researcher"]
    assert decls[0].objective == "Weekly competitive moves"
    assert decls[0].paused is False
    assert decls[0].domain == "competitors"
    assert decls[1].slug == "competitors-funding-check"
    assert decls[1].paused is True


# ---------------------------------------------------------------------------
# parse_recurrence_yaml — back-office (multi-declaration with executor)
# ---------------------------------------------------------------------------


def test_parse_back_office_index():
    yaml_content = """
back_office_jobs:
  - executor: services.back_office.workspace_cleanup
    schedule: "0 0 * * *"
    paused: false
  - executor: services.back_office.outcome_reconciliation
    schedule: "0 4 * * *"
    paused: false
  - executor: services.back_office.narrative_digest
    schedule: "0 6 * * *"
    paused: false
"""
    path = "/workspace/_shared/back-office.yaml"
    decls = parse_recurrence_yaml(yaml_content, path)
    assert len(decls) == 3
    assert all(d.shape == RecurrenceShape.MAINTENANCE for d in decls)
    # slug auto-derived from executor dotted path
    assert decls[0].slug == "back-office-workspace-cleanup"
    assert decls[0].executor == "services.back_office.workspace_cleanup"
    assert decls[1].slug == "back-office-outcome-reconciliation"
    assert decls[2].slug == "back-office-narrative-digest"


def test_parse_back_office_explicit_slug():
    yaml_content = """
back_office_jobs:
  - slug: my-custom-cleanup
    executor: services.back_office.workspace_cleanup
    schedule: "0 0 * * *"
"""
    path = "/workspace/_shared/back-office.yaml"
    decls = parse_recurrence_yaml(yaml_content, path)
    assert len(decls) == 1
    assert decls[0].slug == "my-custom-cleanup"


# ---------------------------------------------------------------------------
# Pause semantics
# ---------------------------------------------------------------------------


def test_paused_true_blocks_due():
    decl = RecurrenceDeclaration.from_yaml_block(
        shape=RecurrenceShape.DELIVERABLE,
        slug="x",
        declaration_path="/workspace/reports/x/_spec.yaml",
        data={"schedule": "0 9 * * 1", "paused": True},
    )
    assert decl.is_due(datetime(2026, 5, 11, 9, 0, tzinfo=timezone.utc)) is False


def test_paused_until_future_blocks_due():
    decl = RecurrenceDeclaration.from_yaml_block(
        shape=RecurrenceShape.DELIVERABLE,
        slug="x",
        declaration_path="/workspace/reports/x/_spec.yaml",
        data={
            "schedule": "0 9 * * 1",
            "paused_until": "2026-06-01T00:00:00Z",
        },
    )
    now_before = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
    now_after = datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc)
    assert decl.is_due(now_before) is False
    assert decl.is_due(now_after) is True


def test_no_schedule_never_due():
    """Without a cron expression, never auto-fires (one-shot graduation case)."""
    decl = RecurrenceDeclaration.from_yaml_block(
        shape=RecurrenceShape.DELIVERABLE,
        slug="x",
        declaration_path="/workspace/reports/x/_spec.yaml",
        data={"display_name": "x"},
    )
    assert decl.is_due(datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)) is False


# ---------------------------------------------------------------------------
# Malformed / edge-case handling
# ---------------------------------------------------------------------------


def test_empty_content_returns_empty_list():
    assert (
        parse_recurrence_yaml("", "/workspace/reports/x/_spec.yaml") == []
    )


def test_invalid_yaml_returns_empty_list():
    decls = parse_recurrence_yaml(
        "{ this is not [ valid yaml",
        "/workspace/reports/x/_spec.yaml",
    )
    assert decls == []


def test_unrecognized_path_returns_empty_list():
    decls = parse_recurrence_yaml(
        "schedule: daily",
        "/workspace/random/file.yaml",
    )
    assert decls == []


def test_back_office_entry_missing_executor_skipped():
    yaml_content = """
back_office_jobs:
  - schedule: "0 0 * * *"
    paused: false
  - executor: services.back_office.workspace_cleanup
    schedule: "0 0 * * *"
"""
    decls = parse_recurrence_yaml(yaml_content, "/workspace/_shared/back-office.yaml")
    # Bad entry skipped; valid entry preserved
    assert len(decls) == 1
    assert decls[0].executor == "services.back_office.workspace_cleanup"


def test_domain_entry_missing_slug_skipped():
    yaml_content = """
recurrences:
  - schedule: "0 0 * * *"
    agent: researcher
  - slug: valid-entry
    schedule: "0 0 * * *"
"""
    decls = parse_recurrence_yaml(
        yaml_content, "/workspace/context/competitors/_recurring.yaml"
    )
    assert len(decls) == 1
    assert decls[0].slug == "valid-entry"


# ---------------------------------------------------------------------------
# derive_declaration_path
# ---------------------------------------------------------------------------


def test_derive_declaration_path_deliverable():
    assert (
        derive_declaration_path(RecurrenceShape.DELIVERABLE, "market-weekly")
        == "/workspace/reports/market-weekly/_spec.yaml"
    )


def test_derive_declaration_path_action():
    assert (
        derive_declaration_path(RecurrenceShape.ACTION, "slack-standup")
        == "/workspace/operations/slack-standup/_action.yaml"
    )


def test_derive_declaration_path_accumulation_requires_domain():
    assert (
        derive_declaration_path(
            RecurrenceShape.ACCUMULATION, "anything", domain="competitors"
        )
        == "/workspace/context/competitors/_recurring.yaml"
    )


def test_derive_declaration_path_accumulation_without_domain_raises():
    import pytest

    with pytest.raises(ValueError):
        derive_declaration_path(RecurrenceShape.ACCUMULATION, "anything")


def test_derive_declaration_path_maintenance_is_index():
    assert (
        derive_declaration_path(RecurrenceShape.MAINTENANCE, "anything")
        == "/workspace/_shared/back-office.yaml"
    )


# ---------------------------------------------------------------------------
# serialize_declaration_yaml
# ---------------------------------------------------------------------------


def test_serialize_round_trip_deliverable():
    yaml_in = """
report:
  slug: x
  schedule: "0 9 * * 1"
  agents: [analyst]
"""
    decls = parse_recurrence_yaml(yaml_in, "/workspace/reports/x/_spec.yaml")
    assert len(decls) == 1
    serialized = serialize_declaration_yaml(decls[0])
    re_parsed = parse_recurrence_yaml(serialized, "/workspace/reports/x/_spec.yaml")
    assert len(re_parsed) == 1
    assert re_parsed[0].slug == "x"
    assert re_parsed[0].schedule == "0 9 * * 1"
    assert re_parsed[0].agents == ["analyst"]


def test_serialize_round_trip_action():
    yaml_in = """
action:
  slug: slack-standup
  schedule: "0 9 * * *"
  target_capability: write_slack
"""
    decls = parse_recurrence_yaml(
        yaml_in, "/workspace/operations/slack-standup/_action.yaml"
    )
    assert len(decls) == 1
    serialized = serialize_declaration_yaml(decls[0])
    re_parsed = parse_recurrence_yaml(
        serialized, "/workspace/operations/slack-standup/_action.yaml"
    )
    assert len(re_parsed) == 1
    assert re_parsed[0].data.get("target_capability") == "write_slack"


# ---------------------------------------------------------------------------
# Test summary
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Tally for ad-hoc run via `python test_adr231_recurrence.py`
    test_fns = [
        v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
    ]
    failed = []
    for fn in test_fns:
        try:
            fn()
            print(f"OK  {fn.__name__}")
        except AssertionError as e:
            failed.append((fn.__name__, "AssertionError", str(e)))
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            failed.append((fn.__name__, type(e).__name__, str(e)))
            print(f"ERR  {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(test_fns) - len(failed)}/{len(test_fns)} passed")
    sys.exit(0 if not failed else 1)
