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
# Phase 3.2.a — Path Resolution (services/recurrence_paths.py)
#
# Maps RecurrenceDeclaration → natural-home substrate paths per ADR-231 D2/D9/D10.
# Every shape × every path-kind combination has an explicit assertion here so
# the contract is enforced at CI time before the dispatcher (3.2.b) consumes it.
# ---------------------------------------------------------------------------


def _make_decl(
    shape: RecurrenceShape,
    slug: str,
    declaration_path: str,
    data: dict | None = None,
) -> RecurrenceDeclaration:
    return RecurrenceDeclaration(
        shape=shape,
        slug=slug,
        declaration_path=declaration_path,
        data=data or {},
    )


# ---- resolve_substrate_root ----


def test_substrate_root_deliverable():
    from services.recurrence_paths import resolve_substrate_root

    decl = _make_decl(
        RecurrenceShape.DELIVERABLE,
        "market-weekly",
        "/workspace/reports/market-weekly/_spec.yaml",
    )
    assert resolve_substrate_root(decl) == "/workspace/reports/market-weekly"


def test_substrate_root_accumulation():
    from services.recurrence_paths import resolve_substrate_root

    decl = _make_decl(
        RecurrenceShape.ACCUMULATION,
        "competitors-weekly-scan",
        "/workspace/context/competitors/_recurring.yaml",
    )
    # ACCUMULATION root is the *domain*, not the slug — multiple recurrences share it
    assert resolve_substrate_root(decl) == "/workspace/context/competitors"


def test_substrate_root_accumulation_missing_domain_raises():
    from services.recurrence_paths import resolve_substrate_root

    # Path doesn't match the domain pattern → decl.domain returns None
    decl = _make_decl(
        RecurrenceShape.ACCUMULATION,
        "orphan",
        "/workspace/not-a-domain-path/_recurring.yaml",
    )
    try:
        resolve_substrate_root(decl)
        assert False, "expected ValueError for missing domain"
    except ValueError as e:
        assert "missing domain" in str(e)


def test_substrate_root_action():
    from services.recurrence_paths import resolve_substrate_root

    decl = _make_decl(
        RecurrenceShape.ACTION,
        "slack-standup",
        "/workspace/operations/slack-standup/_action.yaml",
    )
    assert resolve_substrate_root(decl) == "/workspace/operations/slack-standup"


def test_substrate_root_maintenance():
    from services.recurrence_paths import resolve_substrate_root

    decl = _make_decl(
        RecurrenceShape.MAINTENANCE,
        "back-office-workspace-cleanup",
        "/workspace/_shared/back-office.yaml",
    )
    # MAINTENANCE root is the shared back-office area — all back-office tasks share it
    assert resolve_substrate_root(decl) == "/workspace/_shared"


# ---- resolve_output_path ----


def test_output_path_deliverable_default_with_date():
    from services.recurrence_paths import resolve_output_path, DATE_FOLDER_FORMAT

    decl = _make_decl(
        RecurrenceShape.DELIVERABLE,
        "market-weekly",
        "/workspace/reports/market-weekly/_spec.yaml",
    )
    started = datetime(2026, 4, 29, 14, 30, tzinfo=timezone.utc)
    expected_date = started.strftime(DATE_FOLDER_FORMAT)
    assert (
        resolve_output_path(decl, started_at=started)
        == f"/workspace/reports/market-weekly/{expected_date}/output.md"
    )


def test_output_path_deliverable_no_started_at_preserves_placeholder():
    from services.recurrence_paths import resolve_output_path

    decl = _make_decl(
        RecurrenceShape.DELIVERABLE,
        "market-weekly",
        "/workspace/reports/market-weekly/_spec.yaml",
    )
    # No started_at → literal {date} placeholder — useful for declaration-time references
    assert (
        resolve_output_path(decl)
        == "/workspace/reports/market-weekly/{date}/output.md"
    )


def test_output_path_deliverable_bundle_override_with_placeholder():
    from services.recurrence_paths import resolve_output_path

    # Bundle declares a custom output_path with {date} placeholder
    decl = _make_decl(
        RecurrenceShape.DELIVERABLE,
        "pre-market-brief",
        "/workspace/reports/pre-market-brief/_spec.yaml",
        data={"output_path": "/workspace/reports/pre-market-brief/{date}/brief.md"},
    )
    started = datetime(2026, 4, 29, 7, 0, tzinfo=timezone.utc)
    result = resolve_output_path(decl, started_at=started)
    assert result == "/workspace/reports/pre-market-brief/2026-04-29T0700/brief.md"


def test_output_path_deliverable_bundle_override_literal():
    from services.recurrence_paths import resolve_output_path

    # Bundle author opts out of dating with a literal path
    decl = _make_decl(
        RecurrenceShape.DELIVERABLE,
        "single-shot",
        "/workspace/reports/single-shot/_spec.yaml",
        data={"output_path": "/workspace/reports/single-shot/output.md"},
    )
    started = datetime(2026, 4, 29, tzinfo=timezone.utc)
    # Literal path returned as-is
    assert (
        resolve_output_path(decl, started_at=started)
        == "/workspace/reports/single-shot/output.md"
    )


def test_output_path_accumulation_raises():
    from services.recurrence_paths import resolve_output_path

    decl = _make_decl(
        RecurrenceShape.ACCUMULATION,
        "competitors-weekly-scan",
        "/workspace/context/competitors/_recurring.yaml",
    )
    try:
        resolve_output_path(decl)
        assert False, "expected ValueError — ACCUMULATION has no output path"
    except ValueError as e:
        assert "no canonical output path" in str(e)


def test_output_path_action_raises():
    from services.recurrence_paths import resolve_output_path

    decl = _make_decl(
        RecurrenceShape.ACTION,
        "slack-standup",
        "/workspace/operations/slack-standup/_action.yaml",
    )
    try:
        resolve_output_path(decl)
        assert False, "expected ValueError — ACTION has no filesystem output"
    except ValueError as e:
        assert "no filesystem output" in str(e)


def test_output_path_maintenance_returns_audit_log():
    from services.recurrence_paths import resolve_output_path

    decl = _make_decl(
        RecurrenceShape.MAINTENANCE,
        "back-office-workspace-cleanup",
        "/workspace/_shared/back-office.yaml",
    )
    # ADR-231 D2: back-office collapses to single shared audit log
    assert (
        resolve_output_path(decl) == "/workspace/_shared/back-office-audit.md"
    )


# ---- resolve_output_folder ----


def test_output_folder_deliverable():
    from services.recurrence_paths import resolve_output_folder

    decl = _make_decl(
        RecurrenceShape.DELIVERABLE,
        "market-weekly",
        "/workspace/reports/market-weekly/_spec.yaml",
    )
    started = datetime(2026, 4, 29, 14, 30, tzinfo=timezone.utc)
    assert (
        resolve_output_folder(decl, started_at=started)
        == "/workspace/reports/market-weekly/2026-04-29T1430"
    )


def test_output_folder_non_deliverable_raises():
    from services.recurrence_paths import resolve_output_folder

    for shape, slug, path in [
        (RecurrenceShape.ACCUMULATION, "scan", "/workspace/context/x/_recurring.yaml"),
        (RecurrenceShape.ACTION, "post", "/workspace/operations/post/_action.yaml"),
        (RecurrenceShape.MAINTENANCE, "cleanup", "/workspace/_shared/back-office.yaml"),
    ]:
        decl = _make_decl(shape, slug, path)
        try:
            resolve_output_folder(decl)
            assert False, f"expected ValueError for {shape.value}"
        except ValueError as e:
            assert "DELIVERABLE-only" in str(e)


# ---- resolve_run_log_path ----


def test_run_log_deliverable():
    from services.recurrence_paths import resolve_run_log_path

    decl = _make_decl(
        RecurrenceShape.DELIVERABLE,
        "market-weekly",
        "/workspace/reports/market-weekly/_spec.yaml",
    )
    assert (
        resolve_run_log_path(decl) == "/workspace/reports/market-weekly/_run_log.md"
    )


def test_run_log_accumulation_per_domain():
    from services.recurrence_paths import resolve_run_log_path

    # Two declarations under the same domain share the run log
    decl_a = _make_decl(
        RecurrenceShape.ACCUMULATION,
        "competitors-weekly-scan",
        "/workspace/context/competitors/_recurring.yaml",
    )
    decl_b = _make_decl(
        RecurrenceShape.ACCUMULATION,
        "competitors-pricing-watch",
        "/workspace/context/competitors/_recurring.yaml",
    )
    assert resolve_run_log_path(decl_a) == "/workspace/context/competitors/_run_log.md"
    assert resolve_run_log_path(decl_b) == "/workspace/context/competitors/_run_log.md"


def test_run_log_action():
    from services.recurrence_paths import resolve_run_log_path

    decl = _make_decl(
        RecurrenceShape.ACTION,
        "slack-standup",
        "/workspace/operations/slack-standup/_action.yaml",
    )
    assert (
        resolve_run_log_path(decl) == "/workspace/operations/slack-standup/_run_log.md"
    )


def test_run_log_maintenance_is_audit_log():
    from services.recurrence_paths import resolve_run_log_path, resolve_output_path

    # ADR-231 D10: the audit log IS the run log for MAINTENANCE
    decl = _make_decl(
        RecurrenceShape.MAINTENANCE,
        "back-office-workspace-cleanup",
        "/workspace/_shared/back-office.yaml",
    )
    assert resolve_run_log_path(decl) == resolve_output_path(decl)
    assert resolve_run_log_path(decl) == "/workspace/_shared/back-office-audit.md"


# ---- resolve_feedback_path ----


def test_feedback_deliverable_per_declaration():
    from services.recurrence_paths import resolve_feedback_path

    decl = _make_decl(
        RecurrenceShape.DELIVERABLE,
        "market-weekly",
        "/workspace/reports/market-weekly/_spec.yaml",
    )
    assert (
        resolve_feedback_path(decl)
        == "/workspace/reports/market-weekly/_feedback.md"
    )


def test_feedback_accumulation_per_domain():
    from services.recurrence_paths import resolve_feedback_path

    decl = _make_decl(
        RecurrenceShape.ACCUMULATION,
        "competitors-weekly-scan",
        "/workspace/context/competitors/_recurring.yaml",
    )
    # Per-domain feedback (already canonical per ADR-181)
    assert (
        resolve_feedback_path(decl)
        == "/workspace/context/competitors/_feedback.md"
    )


def test_feedback_action_none():
    from services.recurrence_paths import resolve_feedback_path

    # Outcomes ARE the feedback signal per ADR-195 — no separate file
    decl = _make_decl(
        RecurrenceShape.ACTION,
        "slack-standup",
        "/workspace/operations/slack-standup/_action.yaml",
    )
    assert resolve_feedback_path(decl) is None


def test_feedback_maintenance_none():
    from services.recurrence_paths import resolve_feedback_path

    decl = _make_decl(
        RecurrenceShape.MAINTENANCE,
        "back-office-workspace-cleanup",
        "/workspace/_shared/back-office.yaml",
    )
    assert resolve_feedback_path(decl) is None


# ---- resolve_intent_path / resolve_steering_path ----


def test_intent_and_steering_present_for_judgment_shapes():
    from services.recurrence_paths import resolve_intent_path, resolve_steering_path

    cases = [
        (RecurrenceShape.DELIVERABLE, "market-weekly", "/workspace/reports/market-weekly/_spec.yaml",
         "/workspace/reports/market-weekly"),
        (RecurrenceShape.ACCUMULATION, "competitors-weekly-scan", "/workspace/context/competitors/_recurring.yaml",
         "/workspace/context/competitors"),
        (RecurrenceShape.ACTION, "slack-standup", "/workspace/operations/slack-standup/_action.yaml",
         "/workspace/operations/slack-standup"),
    ]
    for shape, slug, decl_path, expected_root in cases:
        decl = _make_decl(shape, slug, decl_path)
        assert resolve_intent_path(decl) == f"{expected_root}/_intent.md"
        assert resolve_steering_path(decl) == f"{expected_root}/_steering.md"


def test_intent_and_steering_absent_for_maintenance():
    from services.recurrence_paths import resolve_intent_path, resolve_steering_path

    decl = _make_decl(
        RecurrenceShape.MAINTENANCE,
        "back-office-workspace-cleanup",
        "/workspace/_shared/back-office.yaml",
    )
    assert resolve_intent_path(decl) is None
    assert resolve_steering_path(decl) is None


# ---- resolve_working_scratch_path ----


def test_working_scratch_deliverable():
    from services.recurrence_paths import resolve_working_scratch_path

    decl = _make_decl(
        RecurrenceShape.DELIVERABLE,
        "market-weekly",
        "/workspace/reports/market-weekly/_spec.yaml",
    )
    assert (
        resolve_working_scratch_path(decl)
        == "/workspace/reports/market-weekly/working/"
    )


def test_working_scratch_accumulation_sub_keyed_by_slug():
    from services.recurrence_paths import resolve_working_scratch_path

    # ADR-231 D9: domain-shared dirs sub-key working/ by recurrence slug
    decl_a = _make_decl(
        RecurrenceShape.ACCUMULATION,
        "competitors-weekly-scan",
        "/workspace/context/competitors/_recurring.yaml",
    )
    decl_b = _make_decl(
        RecurrenceShape.ACCUMULATION,
        "competitors-pricing-watch",
        "/workspace/context/competitors/_recurring.yaml",
    )
    assert (
        resolve_working_scratch_path(decl_a)
        == "/workspace/context/competitors/working/competitors-weekly-scan/"
    )
    assert (
        resolve_working_scratch_path(decl_b)
        == "/workspace/context/competitors/working/competitors-pricing-watch/"
    )


def test_working_scratch_action():
    from services.recurrence_paths import resolve_working_scratch_path

    decl = _make_decl(
        RecurrenceShape.ACTION,
        "slack-standup",
        "/workspace/operations/slack-standup/_action.yaml",
    )
    assert (
        resolve_working_scratch_path(decl)
        == "/workspace/operations/slack-standup/working/"
    )


def test_working_scratch_maintenance_sub_keyed_by_slug():
    from services.recurrence_paths import resolve_working_scratch_path

    # MAINTENANCE shares /workspace/_shared/ so working scratch is sub-keyed
    decl_a = _make_decl(
        RecurrenceShape.MAINTENANCE,
        "back-office-workspace-cleanup",
        "/workspace/_shared/back-office.yaml",
    )
    decl_b = _make_decl(
        RecurrenceShape.MAINTENANCE,
        "back-office-outcome-reconciliation",
        "/workspace/_shared/back-office.yaml",
    )
    assert (
        resolve_working_scratch_path(decl_a)
        == "/workspace/_shared/working/back-office-workspace-cleanup/"
    )
    assert (
        resolve_working_scratch_path(decl_b)
        == "/workspace/_shared/working/back-office-outcome-reconciliation/"
    )


# ---- resolve_paths (aggregate) ----


def test_resolve_paths_deliverable_full_bundle():
    from services.recurrence_paths import resolve_paths

    decl = _make_decl(
        RecurrenceShape.DELIVERABLE,
        "market-weekly",
        "/workspace/reports/market-weekly/_spec.yaml",
    )
    started = datetime(2026, 4, 29, 14, 30, tzinfo=timezone.utc)
    paths = resolve_paths(decl, started_at=started)
    assert paths.substrate_root == "/workspace/reports/market-weekly"
    assert paths.output_path == "/workspace/reports/market-weekly/2026-04-29T1430/output.md"
    assert paths.output_folder == "/workspace/reports/market-weekly/2026-04-29T1430"
    assert paths.run_log_path == "/workspace/reports/market-weekly/_run_log.md"
    assert paths.feedback_path == "/workspace/reports/market-weekly/_feedback.md"
    assert paths.intent_path == "/workspace/reports/market-weekly/_intent.md"
    assert paths.steering_path == "/workspace/reports/market-weekly/_steering.md"
    assert paths.working_scratch == "/workspace/reports/market-weekly/working/"


def test_resolve_paths_accumulation_no_output():
    from services.recurrence_paths import resolve_paths

    decl = _make_decl(
        RecurrenceShape.ACCUMULATION,
        "competitors-weekly-scan",
        "/workspace/context/competitors/_recurring.yaml",
    )
    paths = resolve_paths(decl)
    assert paths.substrate_root == "/workspace/context/competitors"
    assert paths.output_path is None  # ACCUMULATION has no output file
    assert paths.output_folder is None
    assert paths.run_log_path == "/workspace/context/competitors/_run_log.md"
    assert paths.feedback_path == "/workspace/context/competitors/_feedback.md"
    assert paths.intent_path == "/workspace/context/competitors/_intent.md"
    assert paths.steering_path == "/workspace/context/competitors/_steering.md"
    assert (
        paths.working_scratch
        == "/workspace/context/competitors/working/competitors-weekly-scan/"
    )


def test_resolve_paths_action_no_output_no_feedback():
    from services.recurrence_paths import resolve_paths

    decl = _make_decl(
        RecurrenceShape.ACTION,
        "slack-standup",
        "/workspace/operations/slack-standup/_action.yaml",
    )
    paths = resolve_paths(decl)
    assert paths.substrate_root == "/workspace/operations/slack-standup"
    assert paths.output_path is None
    assert paths.output_folder is None
    assert paths.run_log_path == "/workspace/operations/slack-standup/_run_log.md"
    assert paths.feedback_path is None  # outcomes ARE the feedback per ADR-195
    assert paths.intent_path == "/workspace/operations/slack-standup/_intent.md"
    assert paths.steering_path == "/workspace/operations/slack-standup/_steering.md"
    assert paths.working_scratch == "/workspace/operations/slack-standup/working/"


def test_resolve_paths_maintenance_minimal():
    from services.recurrence_paths import resolve_paths

    decl = _make_decl(
        RecurrenceShape.MAINTENANCE,
        "back-office-workspace-cleanup",
        "/workspace/_shared/back-office.yaml",
    )
    paths = resolve_paths(decl)
    assert paths.substrate_root == "/workspace/_shared"
    assert paths.output_path == "/workspace/_shared/back-office-audit.md"
    assert paths.output_folder is None  # no per-firing folder for MAINTENANCE
    # Run log == output path (the audit log doubles as run log per D10)
    assert paths.run_log_path == paths.output_path
    assert paths.feedback_path is None
    assert paths.intent_path is None
    assert paths.steering_path is None
    assert (
        paths.working_scratch
        == "/workspace/_shared/working/back-office-workspace-cleanup/"
    )


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
