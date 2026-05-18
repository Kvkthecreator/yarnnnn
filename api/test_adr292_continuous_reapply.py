"""Regression gate for ADR-292 — Continuous Substrate Re-Apply.

ADR-292 closes the kernel/bundle → live-workspace propagation gap. Single
mechanical primitive `ReapplyPlatformSubstrate` walks kernel-universal seed
paths + the activated bundle's reference-workspace, re-writes platform-managed
files where the operator hasn't taken authorship.

This gate enforces the structural shape:

  1. Substrate-reapply service module is importable and has the expected entry point.
  2. Audit log path constant + system actor name match the ADR.
  3. ReapplyPlatformSubstrate primitive is registered in HANDLERS.
  4. The mechanical-mode `back-office-substrate-reapply` recurrence is shipped
     in both active alpha bundles (alpha-trader, alpha-author).
  5. The recurrence prompt names @primitive: ReapplyPlatformSubstrate() correctly.
  6. The primitive is NOT exposed on any LLM tool surface (CHAT/HEADLESS/REVIEWER) —
     mechanical-only per ADR-264 D3 + ADR-263.
  7. ADR-292 doc file exists.

Run:
    python -m api.test_adr292_continuous_reapply
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name: str) -> None:
    _PASS.append(name)
    print(f"  ✓ {name}")


def _bad(name: str, reason: str) -> None:
    _FAIL.append((name, reason))
    print(f"  ✗ {name}\n      {reason}")


# ---------------------------------------------------------------------------
# 1. Service module importable + entry point shape
# ---------------------------------------------------------------------------

def test_service_module_importable() -> None:
    try:
        from services import substrate_reapply
    except Exception as e:
        _bad("substrate_reapply module imports", f"import failed: {e}")
        return

    needed_symbols = [
        "reapply_platform_substrate",
        "handle_reapply_platform_substrate",
        "REAPPLY_PLATFORM_SUBSTRATE_TOOL",
        "REAPPLY_AUDIT_LOG_PATH",
        "REAPPLY_AUTHORED_BY",
        "ReapplyReport",
        "ReapplyAction",
    ]
    missing = [s for s in needed_symbols if not hasattr(substrate_reapply, s)]
    if not missing:
        _ok("substrate_reapply exports 7 expected symbols")
    else:
        _bad("substrate_reapply exports", f"missing: {missing}")


def test_audit_log_path_constant() -> None:
    from services.substrate_reapply import REAPPLY_AUDIT_LOG_PATH

    expected = "_shared/substrate-reapply-log.md"
    if REAPPLY_AUDIT_LOG_PATH == expected:
        _ok(f"REAPPLY_AUDIT_LOG_PATH == {expected!r}")
    else:
        _bad(
            "REAPPLY_AUDIT_LOG_PATH value",
            f"expected {expected!r}, got {REAPPLY_AUDIT_LOG_PATH!r}",
        )


def test_attribution_actor() -> None:
    from services.substrate_reapply import REAPPLY_AUTHORED_BY

    expected = "system:substrate-reapply"
    if REAPPLY_AUTHORED_BY == expected:
        _ok(f"REAPPLY_AUTHORED_BY == {expected!r}")
    else:
        _bad(
            "REAPPLY_AUTHORED_BY value",
            f"expected {expected!r}, got {REAPPLY_AUTHORED_BY!r}",
        )

    # Sanity: this actor name should pass the ADR-209 authored-by taxonomy gate.
    from services.authored_substrate import is_valid_author

    if is_valid_author(REAPPLY_AUTHORED_BY):
        _ok("REAPPLY_AUTHORED_BY passes is_valid_author (ADR-209 taxonomy)")
    else:
        _bad(
            "REAPPLY_AUTHORED_BY taxonomy",
            f"{REAPPLY_AUTHORED_BY!r} rejected by is_valid_author — "
            "would block write_revision() at runtime",
        )


# ---------------------------------------------------------------------------
# 2. Primitive registry contract
# ---------------------------------------------------------------------------

def test_primitive_registered_in_handlers() -> None:
    from services.primitives.registry import HANDLERS

    if "ReapplyPlatformSubstrate" not in HANDLERS:
        _bad(
            "ReapplyPlatformSubstrate in HANDLERS",
            f"primitive not registered — mechanical dispatcher cannot find it. "
            f"HANDLERS keys: {sorted(HANDLERS.keys())}",
        )
        return

    handler = HANDLERS["ReapplyPlatformSubstrate"]
    from services.substrate_reapply import handle_reapply_platform_substrate

    if handler is handle_reapply_platform_substrate:
        _ok("HANDLERS['ReapplyPlatformSubstrate'] resolves to substrate_reapply handler")
    else:
        _bad(
            "HANDLERS handler identity",
            f"HANDLERS['ReapplyPlatformSubstrate'] is {handler!r}, "
            f"expected substrate_reapply.handle_reapply_platform_substrate",
        )


def test_primitive_not_on_llm_tool_surfaces() -> None:
    """ADR-264 D3 + ADR-263: mechanical primitives are NOT in CHAT/HEADLESS/
    REVIEWER tool surfaces. Operators don't directly invoke them — they
    author recurrences that name them via @primitive: directives.
    """
    from services.primitives import registry

    surfaces_to_check = [
        ("CHAT_PRIMITIVES", getattr(registry, "CHAT_PRIMITIVES", None)),
        ("HEADLESS_PRIMITIVES", getattr(registry, "HEADLESS_PRIMITIVES", None)),
        ("REVIEWER_PRIMITIVES", getattr(registry, "REVIEWER_PRIMITIVES", None)),
    ]

    leaked = []
    for surface_name, surface in surfaces_to_check:
        if surface is None:
            continue
        # Surfaces are lists of tool definitions (dicts with "name" key).
        for tool in surface:
            if isinstance(tool, dict) and tool.get("name") == "ReapplyPlatformSubstrate":
                leaked.append(surface_name)

    if not leaked:
        _ok("ReapplyPlatformSubstrate absent from CHAT/HEADLESS/REVIEWER surfaces")
    else:
        _bad(
            "primitive surface exposure",
            f"ReapplyPlatformSubstrate leaked into LLM surfaces: {leaked}. "
            f"Mechanical-only per ADR-264 D3.",
        )


# ---------------------------------------------------------------------------
# 3. Bundle recurrence registration
# ---------------------------------------------------------------------------

def _load_bundle_recurrences(program_slug: str) -> list[dict]:
    path = (
        REPO_ROOT / "docs" / "programs" / program_slug
        / "reference-workspace" / "_recurrences.yaml"
    )
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("recurrences", []) or []


def test_alpha_trader_bundle_has_recurrence() -> None:
    recs = _load_bundle_recurrences("alpha-trader")
    matches = [r for r in recs if r.get("slug") == "back-office-substrate-reapply"]
    if len(matches) != 1:
        _bad(
            "alpha-trader bundle declares back-office-substrate-reapply",
            f"expected exactly 1 entry, got {len(matches)}",
        )
        return

    rec = matches[0]
    if rec.get("mode") != "mechanical":
        _bad(
            "alpha-trader back-office-substrate-reapply mode",
            f"expected mode='mechanical', got {rec.get('mode')!r}",
        )
        return

    prompt = rec.get("prompt", "")
    if "@primitive: ReapplyPlatformSubstrate()" not in prompt:
        _bad(
            "alpha-trader back-office-substrate-reapply prompt",
            f"prompt does not contain '@primitive: ReapplyPlatformSubstrate()': {prompt!r}",
        )
        return

    schedule = rec.get("schedule", "")
    # Daily cadence — should be a cron expression, not @-prefixed semantic
    # (this recurrence is market-agnostic). Loose check: contains a space-
    # delimited 5-field cron.
    if not isinstance(schedule, str) or not re.match(r"^\S+\s+\S+\s+\S+\s+\S+\s+\S+$", schedule):
        _bad(
            "alpha-trader back-office-substrate-reapply schedule",
            f"expected daily UTC cron, got {schedule!r}",
        )
        return

    _ok("alpha-trader bundle declares back-office-substrate-reapply (mechanical, daily cron)")


def test_alpha_author_bundle_has_recurrence() -> None:
    recs = _load_bundle_recurrences("alpha-author")
    matches = [r for r in recs if r.get("slug") == "back-office-substrate-reapply"]
    if len(matches) != 1:
        _bad(
            "alpha-author bundle declares back-office-substrate-reapply",
            f"expected exactly 1 entry, got {len(matches)}",
        )
        return

    rec = matches[0]
    if rec.get("mode") != "mechanical":
        _bad(
            "alpha-author back-office-substrate-reapply mode",
            f"expected mode='mechanical', got {rec.get('mode')!r}",
        )
        return

    prompt = rec.get("prompt", "")
    if "@primitive: ReapplyPlatformSubstrate()" not in prompt:
        _bad(
            "alpha-author back-office-substrate-reapply prompt",
            f"prompt does not contain '@primitive: ReapplyPlatformSubstrate()': {prompt!r}",
        )
        return

    _ok("alpha-author bundle declares back-office-substrate-reapply (mechanical)")


# ---------------------------------------------------------------------------
# 4. ReapplyReport shape
# ---------------------------------------------------------------------------

def test_reapply_report_shape() -> None:
    """The report dataclass must have the fields the audit log + caller expect."""
    import dataclasses
    from services.substrate_reapply import ReapplyReport, ReapplyAction

    required_report_fields = {
        "user_id", "source", "ran_at", "program_slug",
        "actions", "skipped_operator_authored", "skipped_aligned", "error",
    }
    actual = {f.name for f in dataclasses.fields(ReapplyReport)}
    missing = required_report_fields - actual
    if missing:
        _bad(
            "ReapplyReport fields",
            f"missing required fields: {missing}",
        )
        return

    required_action_fields = {"path", "layer", "change_summary"}
    actual_action = {f.name for f in dataclasses.fields(ReapplyAction)}
    missing_action = required_action_fields - actual_action
    if missing_action:
        _bad(
            "ReapplyAction fields",
            f"missing required fields: {missing_action}",
        )
        return

    # Smoke: construct one, render to markdown, confirm structure.
    report = ReapplyReport(
        user_id="test-user-id",
        source="manual",
        ran_at="2026-05-18T00:00:00+00:00",
        program_slug="alpha-trader",
        actions=[
            ReapplyAction(path="memory/_playbook.md", layer="kernel", change_summary="canon updated"),
        ],
        skipped_operator_authored=3,
        skipped_aligned=12,
    )
    md = report.to_log_markdown()
    if "Re-apply run" in md and "alpha-trader" in md and "memory/_playbook.md" in md:
        _ok("ReapplyReport.to_log_markdown produces structured audit-log block")
    else:
        _bad(
            "to_log_markdown output",
            f"markdown rendering missing expected markers: {md[:200]}...",
        )


# ---------------------------------------------------------------------------
# 5. ADR doc exists
# ---------------------------------------------------------------------------

def test_adr292_doc_exists() -> None:
    adr_path = REPO_ROOT / "docs" / "adr" / "ADR-292-continuous-substrate-reapply.md"
    if adr_path.is_file():
        _ok(f"ADR-292 doc exists at {adr_path.relative_to(REPO_ROOT)}")
    else:
        _bad("ADR-292 doc", f"missing: {adr_path}")


def test_planning_doc_status_flipped() -> None:
    """propagation-discipline.md should reference ADR-292 as the ratifying ADR."""
    planning = REPO_ROOT / "docs" / "architecture" / "propagation-discipline.md"
    if not planning.is_file():
        _bad("planning doc exists", f"missing: {planning}")
        return

    content = planning.read_text(encoding="utf-8")
    if "ADR-292" in content:
        _ok("propagation-discipline.md references ADR-292")
    else:
        _bad(
            "planning doc status",
            "propagation-discipline.md does not reference ADR-292 — "
            "status flip missed",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("ADR-292 — Continuous Substrate Re-Apply regression gate\n")

    test_service_module_importable()
    test_audit_log_path_constant()
    test_attribution_actor()
    test_primitive_registered_in_handlers()
    test_primitive_not_on_llm_tool_surfaces()
    test_alpha_trader_bundle_has_recurrence()
    test_alpha_author_bundle_has_recurrence()
    test_reapply_report_shape()
    test_adr292_doc_exists()
    test_planning_doc_status_flipped()

    total = len(_PASS) + len(_FAIL)
    print(f"\n{len(_PASS)}/{total} pass")
    if _FAIL:
        print("\nFAILURES:")
        for name, reason in _FAIL:
            print(f"  • {name}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
