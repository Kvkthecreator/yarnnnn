"""
Back-office executor return-shape contract regression gate.

Every `services.back_office.*.run()` function must return a dict matching
the contract enforced by `services.invocation_dispatcher` line 646:

    {
        "summary": str,                  # optional but conventional
        "output_markdown": str,          # REQUIRED (dispatcher key check)
        "actions_taken": list[dict],     # optional but conventional
    }

This test prevents the drift surfaced 2026-04-29 (alpha-trader-2 E2E
observation) where `reviewer_calibration` and `outcome_reconciliation`
were returning `{"content": ..., "structured": ...}` — a dispatcher-
incompatible shape that caused silent daily failures.

Strategy: this is a static contract test. We assert that:
  - Every executor module's `run()` source contains a `return {` block
    with the required `"output_markdown"` key.
  - No executor source contains a `return {"content":` (the legacy
    shape), since that's what the dispatcher rejects.

Static check means we don't have to mock every provider/DB to actually
call the executors — we just ensure the source obeys the contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


BACK_OFFICE_DIR = Path(__file__).resolve().parent / "services" / "back_office"


def _executor_modules() -> list[Path]:
    """All back-office executor modules (files that define `async def run`)."""
    out = []
    for p in BACK_OFFICE_DIR.glob("*.py"):
        if p.name == "__init__.py":
            continue
        text = p.read_text()
        if "async def run(" in text:
            out.append(p)
    return out


def test_at_least_six_back_office_executors_present():
    """Sanity floor — fewer than 6 means someone deleted an executor without
    updating this test. As of 2026-04-30: agent_hygiene, narrative_digest,
    workspace_cleanup, reviewer_reflection, reviewer_calibration,
    outcome_reconciliation."""
    mods = _executor_modules()
    assert len(mods) >= 6, f"expected ≥6 executor modules, got {len(mods)}: {[m.name for m in mods]}"


@pytest.mark.parametrize("path", _executor_modules(), ids=lambda p: p.name)
def test_executor_source_has_output_markdown_return(path: Path):
    """Each executor's `run()` must produce dicts with `output_markdown`.

    We check the source file contains at least one `"output_markdown":`
    key inside a return-dict literal. Static check — covers the contract
    without requiring full executor invocation."""
    text = path.read_text()
    assert '"output_markdown"' in text, (
        f"{path.name} has no `\"output_markdown\"` key in source — "
        f"violates services.invocation_dispatcher line 646 contract."
    )


@pytest.mark.parametrize("path", _executor_modules(), ids=lambda p: p.name)
def test_executor_source_does_not_use_legacy_content_key(path: Path):
    """Legacy shape `{"content": ..., "structured": ...}` is dispatcher-
    incompatible — it caused the 2026-04-29 silent-failure drift on
    reviewer_calibration + outcome_reconciliation. Block any return-
    dict that uses the legacy `"content":` key.

    Note: we look specifically for `return {` followed by `"content":`
    nearby — this avoids false positives on legitimate uses of `content`
    as a local variable or in markdown literals."""
    text = path.read_text()
    # Find every `return {` block; assert none has `"content":` as a
    # top-level key inside the next ~200 chars.
    pattern = re.compile(r"return\s*\{[^{}]{0,200}\"content\"\s*:", re.DOTALL)
    matches = pattern.findall(text)
    assert not matches, (
        f"{path.name} has `return {{ ... \"content\": ... }}` — legacy "
        f"shape rejected by dispatcher. Use \"output_markdown\" per "
        f"services.invocation_dispatcher line 646."
    )


def test_dispatcher_contract_check_unchanged():
    """The dispatcher's own assertion that pins the contract. If this test
    fails because the dispatcher changed key, every executor and this
    test must be updated together (singular implementation rule 1)."""
    dispatcher = Path(__file__).resolve().parent / "services" / "invocation_dispatcher.py"
    text = dispatcher.read_text()
    assert '"output_markdown" not in result' in text, (
        "Dispatcher contract assertion at services.invocation_dispatcher "
        "line ~646 missing or moved. If contract evolved, update every "
        "back-office executor + this test in the same commit."
    )
