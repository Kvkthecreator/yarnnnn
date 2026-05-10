"""
ADR-261 Phase B regression gate.

Asserts the unified recurrence model is in place and the legacy substrate
is gone:

  - RecurrenceShape enum is not importable
  - recurrence_paths module is not importable
  - dispatch_helpers module is not importable
  - reflection_writer module is not importable
  - back_office package is not importable
  - find_declaration_for_agent is not importable from dispatcher
  - _maybe_fire_reviewer_heartbeat is not importable from dispatcher

  - services.recurrence exports Recurrence (not RecurrenceDeclaration)
  - parse_recurrences_yaml accepts the unified {slug, schedule, prompt}
    schema and rejects entries missing required fields
  - walk_workspace_recurrences reads /workspace/_recurrences.yaml only
    (RECURRENCES_PATH constant)
  - dispatch(client, user_id, recurrence) reads recurrence.prompt and
    invokes Reviewer with trigger='scheduled' by default

  - services.conventions provides slug-templated paths (report_root,
    report_output_path, domain_root, etc.) replacing per-shape resolution
  - services.primitives.schedule SCHEDULE_TOOL accepts {action, slug,
    schedule, prompt} — no shape parameter
  - services.primitives.fire_invocation FIRE_INVOCATION_TOOL accepts
    {slug, context} — no shape/domain parameters

Strategy: import-shape + structural assertions. No live LLM calls. No
database writes. Safe to run in CI.

Usage:
    cd api && python test_adr261_phaseB.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"PASS: {msg}")


def assert_import_fails(module_path: str) -> None:
    """The named module should not be importable."""
    try:
        importlib.import_module(module_path)
    except (ModuleNotFoundError, ImportError):
        _ok(f"{module_path} not importable (deleted)")
        return
    _fail(f"{module_path} STILL IMPORTABLE — should have been deleted")


def assert_attr_missing(module_path: str, attr: str) -> None:
    """The named attribute should not exist on the named module."""
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        _fail(f"{module_path} should be importable (it carries surviving symbols): {e}")
        return
    if hasattr(mod, attr):
        _fail(f"{module_path}.{attr} STILL EXISTS — should have been deleted")
    _ok(f"{module_path}.{attr} not present (deleted)")


def assert_attr_present(module_path: str, attr: str) -> None:
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        _fail(f"{module_path} not importable: {e}")
        return
    if not hasattr(mod, attr):
        _fail(f"{module_path}.{attr} missing")
    _ok(f"{module_path}.{attr} present")


def main() -> None:
    print()
    print("=" * 70)
    print("ADR-261 Phase B regression gate")
    print("=" * 70)
    print()

    # --- Section 1: deleted modules ---
    print("Section 1 — deleted modules")
    assert_import_fails("services.recurrence_paths")
    assert_import_fails("services.dispatch_helpers")
    assert_import_fails("services.reflection_writer")
    assert_import_fails("services.back_office")
    assert_import_fails("services.back_office.narrative_digest")
    assert_import_fails("services.back_office.outcome_reconciliation")
    assert_import_fails("services.back_office.reviewer_calibration")
    assert_import_fails("services.back_office.reviewer_reflection")
    assert_import_fails("services.back_office.proposal_cleanup")
    assert_import_fails("services.back_office.trading_universe_tracker")
    assert_import_fails("services.back_office.trading_signal_evaluator")
    print()

    # --- Section 2: deleted symbols ---
    print("Section 2 — deleted symbols on surviving modules")
    assert_attr_missing("services.recurrence", "RecurrenceShape")
    assert_attr_missing("services.recurrence", "RecurrenceDeclaration")
    assert_attr_missing("services.recurrence", "shape_for_path")
    assert_attr_missing("services.recurrence", "derive_declaration_path")
    assert_attr_missing("services.invocation_dispatcher", "find_declaration_for_agent")
    assert_attr_missing("services.invocation_dispatcher", "_maybe_fire_reviewer_heartbeat")
    print()

    # --- Section 3: new surface present ---
    print("Section 3 — unified surface present")
    assert_attr_present("services.recurrence", "Recurrence")
    assert_attr_present("services.recurrence", "parse_recurrences_yaml")
    assert_attr_present("services.recurrence", "walk_workspace_recurrences")
    assert_attr_present("services.recurrence", "compute_next_run_at")
    assert_attr_present("services.recurrence", "serialize_recurrences_yaml")
    assert_attr_present("services.conventions", "RECURRENCES_PATH")
    assert_attr_present("services.conventions", "report_root")
    assert_attr_present("services.conventions", "report_output_path")
    assert_attr_present("services.conventions", "report_dated_folder")
    assert_attr_present("services.conventions", "report_feedback_path")
    assert_attr_present("services.conventions", "domain_root")
    assert_attr_present("services.conventions", "domain_entity_path")
    assert_attr_present("services.invocation_dispatcher", "dispatch")
    assert_attr_present("services.scheduling", "get_due_recurrences")
    assert_attr_present("services.scheduling", "compute_next_run_at")
    assert_attr_present("services.primitives.schedule", "handle_schedule")
    assert_attr_present("services.primitives.schedule", "SCHEDULE_TOOL")
    assert_attr_present("services.primitives.fire_invocation", "handle_fire_invocation")
    assert_attr_present("services.primitives.fire_invocation", "FIRE_INVOCATION_TOOL")
    print()

    # --- Section 4: schema shape ---
    print("Section 4 — Recurrence dataclass shape")
    from services.recurrence import Recurrence, parse_recurrences_yaml
    rec = Recurrence(slug="test", schedule="0 7 * * *", prompt="hello")
    if not (rec.slug == "test" and rec.schedule == "0 7 * * *" and rec.prompt == "hello"):
        _fail("Recurrence dataclass field assignment broken")
    _ok("Recurrence dataclass accepts {slug, schedule, prompt}")

    # ADR-261 D1: prompt is required
    parsed = parse_recurrences_yaml(
        "- slug: ok\n  schedule: '0 7 * * *'\n  prompt: do the thing\n"
    )
    if len(parsed) != 1 or parsed[0].slug != "ok":
        _fail(f"parse_recurrences_yaml failed on valid input: {parsed}")
    _ok("parse_recurrences_yaml accepts top-level list")

    # Reactive (no schedule) is allowed
    parsed = parse_recurrences_yaml(
        "- slug: reactive-1\n  schedule: null\n  prompt: fires on event\n"
    )
    if len(parsed) != 1 or parsed[0].schedule is not None:
        _fail("reactive (null schedule) not accepted")
    _ok("parse_recurrences_yaml accepts reactive (null schedule)")

    # Missing prompt is rejected
    parsed = parse_recurrences_yaml(
        "- slug: bad\n  schedule: '0 7 * * *'\n"
    )
    if parsed:
        _fail(f"missing prompt should reject entry, got: {parsed}")
    _ok("parse_recurrences_yaml rejects entries without prompt")

    # Wrapper-dict shape
    parsed = parse_recurrences_yaml(
        "recurrences:\n  - slug: ok\n    schedule: '0 7 * * *'\n    prompt: hi\n"
    )
    if len(parsed) != 1 or parsed[0].slug != "ok":
        _fail(f"wrapper-dict shape rejected: {parsed}")
    _ok("parse_recurrences_yaml accepts wrapper dict {recurrences: [...]}")
    print()

    # --- Section 5: SCHEDULE_TOOL surface ---
    print("Section 5 — Schedule + FireInvocation tool surfaces")
    from services.primitives.schedule import SCHEDULE_TOOL
    schema = SCHEDULE_TOOL.get("input_schema", {})
    props = set((schema.get("properties") or {}).keys())
    required = set(schema.get("required", []))
    if "shape" in props:
        _fail("SCHEDULE_TOOL should not have a 'shape' property (ADR-261 D1)")
    if "domain" in props:
        _fail("SCHEDULE_TOOL should not have a 'domain' property (ADR-261 D1)")
    if not {"action", "slug"}.issubset(required):
        _fail(f"SCHEDULE_TOOL required fields wrong: {required}")
    _ok("SCHEDULE_TOOL surface = {action, slug, schedule?, prompt?, changes?, paused_until?}")

    from services.primitives.fire_invocation import FIRE_INVOCATION_TOOL
    schema = FIRE_INVOCATION_TOOL.get("input_schema", {})
    props = set((schema.get("properties") or {}).keys())
    required = set(schema.get("required", []))
    if "shape" in props:
        _fail("FIRE_INVOCATION_TOOL should not have a 'shape' property")
    if "domain" in props:
        _fail("FIRE_INVOCATION_TOOL should not have a 'domain' property")
    if required != {"slug"}:
        _fail(f"FIRE_INVOCATION_TOOL required must be {{slug}}, got {required}")
    _ok("FIRE_INVOCATION_TOOL surface = {slug, context?}")
    print()

    # --- Section 6: dispatcher signature + trigger taxonomy ---
    print("Section 6 — dispatcher signature")
    import inspect
    from services.invocation_dispatcher import dispatch
    sig = inspect.signature(dispatch)
    params = list(sig.parameters.keys())
    if params[:3] != ["client", "user_id", "recurrence"]:
        _fail(f"dispatch signature wrong: {params}")
    if "trigger" not in sig.parameters:
        _fail("dispatch should accept 'trigger' kwarg per ADR-260 D2")
    if sig.parameters["trigger"].default != "scheduled":
        _fail(
            f"dispatch trigger default should be 'scheduled', got "
            f"{sig.parameters['trigger'].default!r}"
        )
    _ok("dispatch(client, user_id, recurrence, *, trigger='scheduled', context=None)")
    print()

    # --- Section 7: legacy bundle artifacts gone ---
    print("Section 7 — bundle reference workspace cleaned")
    bundle_root = Path(__file__).parent.parent / "docs/programs/alpha-trader/reference-workspace"
    legacy_paths = [
        bundle_root / "_shared/back-office.yaml",
        bundle_root / "context/trading/_recurring.yaml",
        bundle_root / "operations/trade-proposal/_action.yaml",
        bundle_root / "reports/pre-market-brief/_spec.yaml",
        bundle_root / "reports/quarterly-signal-audit/_spec.yaml",
        bundle_root / "reports/weekly-performance-review/_spec.yaml",
    ]
    for p in legacy_paths:
        if p.exists():
            _fail(f"legacy bundle file still present: {p.relative_to(bundle_root.parent.parent.parent)}")
    _ok("all legacy per-shape declaration files removed from bundle")

    canonical = bundle_root / "_recurrences.yaml"
    if not canonical.exists():
        _fail(f"canonical bundle file missing: {canonical}")
    _ok("bundle ships /workspace/_recurrences.yaml at root of reference-workspace")
    print()

    # --- Section 8: Phase C wiring (Compose auto-trigger + DispatchSpecialist) ---
    print()
    print("Section 8 — Phase C wiring")
    assert_attr_present("services.invocation_dispatcher", "_maybe_auto_compose")
    assert_attr_present("services.primitives.dispatch_specialist", "handle_dispatch_specialist")
    assert_attr_present("services.primitives.dispatch_specialist", "DISPATCH_SPECIALIST_TOOL")
    assert_attr_present("services.primitives.dispatch_specialist", "VALID_SPECIALIST_ROLES")

    # DispatchSpecialist registered in CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, REVIEWER_PRIMITIVES, HANDLERS
    from services.primitives.registry import (
        CHAT_PRIMITIVES,
        HEADLESS_PRIMITIVES,
        REVIEWER_PRIMITIVES,
        HANDLERS,
    )
    chat_names = {t["name"] for t in CHAT_PRIMITIVES}
    headless_names = {t["name"] for t in HEADLESS_PRIMITIVES}
    reviewer_names = {t["name"] for t in REVIEWER_PRIMITIVES}

    if "DispatchSpecialist" not in chat_names:
        _fail("DispatchSpecialist missing from CHAT_PRIMITIVES")
    _ok("DispatchSpecialist registered in CHAT_PRIMITIVES")
    if "DispatchSpecialist" not in headless_names:
        _fail("DispatchSpecialist missing from HEADLESS_PRIMITIVES")
    _ok("DispatchSpecialist registered in HEADLESS_PRIMITIVES")
    if "DispatchSpecialist" not in reviewer_names:
        _fail("DispatchSpecialist missing from REVIEWER_PRIMITIVES (ADR-261 D7)")
    _ok("DispatchSpecialist registered in REVIEWER_PRIMITIVES")
    if "DispatchSpecialist" not in HANDLERS:
        _fail("DispatchSpecialist handler not registered")
    _ok("DispatchSpecialist handler registered in HANDLERS")

    # Reviewer roster has Schedule + Compose + DispatchSpecialist + FireInvocation
    expected_reviewer_authority = {"Schedule", "Compose", "DispatchSpecialist", "FireInvocation", "ProposeAction"}
    missing = expected_reviewer_authority - reviewer_names
    if missing:
        _fail(f"REVIEWER_PRIMITIVES missing authority tools: {missing}")
    _ok(f"REVIEWER_PRIMITIVES has full direction authority: {sorted(expected_reviewer_authority)}")

    # All three primitive handlers conform to the (auth, input) contract
    import inspect
    for handler_name in ["handle_schedule", "handle_fire_invocation", "handle_dispatch_specialist", "handle_compose"]:
        for module_name in [
            "services.primitives.schedule",
            "services.primitives.fire_invocation",
            "services.primitives.dispatch_specialist",
            "services.primitives.compose",
        ]:
            try:
                mod = importlib.import_module(module_name)
                if hasattr(mod, handler_name):
                    handler = getattr(mod, handler_name)
                    sig = inspect.signature(handler)
                    params = list(sig.parameters.keys())
                    if params[:2] != ["auth", "input"]:
                        _fail(
                            f"{module_name}.{handler_name} signature must be "
                            f"(auth, input), got {params}"
                        )
                    break
            except ImportError:
                continue
    _ok("Schedule + FireInvocation + DispatchSpecialist + Compose handlers conform to (auth, input)")
    print()

    print("=" * 70)
    print("ADR-261 Phase B + Phase C regression gate: ALL PASS")
    print("=" * 70)


if __name__ == "__main__":
    # Ensure we can import from api/
    sys.path.insert(0, str(Path(__file__).parent))
    main()
