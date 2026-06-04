"""F1 regression: judgment-mode execution_events rows carry token telemetry.

Origin: 2026-05-17 workspace-evolution audit on kvk's alpha-trader-2 surfaced
that judgment-mode (signal-evaluation + outcome-reconciliation) execution_events
rows had NULL input_tokens / output_tokens / cost_usd / tool_rounds. The
Reviewer's loop tracked usage internally and wrote it to token_usage, but
never returned the accumulators to the dispatcher — so the slug-indexed
audit table couldn't show per-fire cost without joining token_usage.

Fix: extend ReviewerOutput with token + model + tool_rounds fields; the
judgment dispatch path reads them off and passes into record_execution_event.
(That path lived in invocation_dispatcher.py until the ADR-296 v2 → ADR-298
wake-architecture migration moved it into services/wake.py.)

These assertions are structural (AST + source contract). They do not
exercise a live Anthropic call.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# Contract 1: ReviewerOutput TypedDict declares the six telemetry fields.
# -----------------------------------------------------------------------------

def test_reviewer_output_declares_telemetry_fields() -> None:
    # ADR-315: ReviewerOutput is DEFINED in occupant_contract.py (the published
    # substrate<->occupant ABI). The dict-literal construction sites stay in
    # reviewer_agent.py and are asserted by Contract 2+ below.
    src = _read("agents/occupant_contract.py")
    tree = ast.parse(src)
    found = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ReviewerOutput":
            found = node
            break
    assert found is not None, "ReviewerOutput class must be defined"

    annotated_names = {
        stmt.target.id
        for stmt in found.body
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
    }
    required = {
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_create_tokens",
        "model",
        "tool_rounds",
    }
    missing = required - annotated_names
    assert not missing, f"ReviewerOutput missing telemetry fields: {missing}"


# -----------------------------------------------------------------------------
# Contract 2: invoke_reviewer accumulates cache token counters.
# -----------------------------------------------------------------------------

def test_invoke_reviewer_accumulates_cache_tokens() -> None:
    src = _read("agents/reviewer_agent.py")
    # Both counters must be declared and accumulated from the Anthropic
    # native usage keys (cache_read_input_tokens, cache_creation_input_tokens).
    assert "total_cache_read = 0" in src, "total_cache_read accumulator missing"
    assert "total_cache_create = 0" in src, "total_cache_create accumulator missing"
    assert "cache_read_input_tokens" in src, (
        "Anthropic native key cache_read_input_tokens must be read from usage"
    )
    assert "cache_creation_input_tokens" in src, (
        "Anthropic native key cache_creation_input_tokens must be read from usage"
    )


# -----------------------------------------------------------------------------
# Contract 3: invoke_reviewer's success-path output dict carries telemetry.
# -----------------------------------------------------------------------------

def test_invoke_reviewer_success_output_carries_telemetry() -> None:
    src = _read("agents/reviewer_agent.py")
    # Find the line where `output: ReviewerOutput = {` is opened.
    idx = src.find("output: ReviewerOutput = {")
    assert idx != -1, "ReviewerOutput dict literal must exist in invoke_reviewer"
    # Capture the block until the next closing brace at the same indent.
    tail = src[idx:]
    # Scan to first occurrence of "\n        }" or similar end marker.
    end = tail.find("        }")
    assert end != -1, "ReviewerOutput dict literal must close"
    block = tail[:end]
    for key in (
        '"input_tokens": total_input',
        '"output_tokens": total_output',
        '"cache_read_tokens": total_cache_read',
        '"cache_create_tokens": total_cache_create',
        '"model": model',
        '"tool_rounds": rounds_used',
    ):
        assert key in block, f"ReviewerOutput dict literal missing: {key}"


# -----------------------------------------------------------------------------
# Contract 4: cancellation-path stand_down also carries telemetry.
# -----------------------------------------------------------------------------

def test_cancellation_standdown_carries_telemetry() -> None:
    src = _read("agents/reviewer_agent.py")
    # Find the early-return ReviewerOutput on operator cancellation.
    marker = 'reasoning="Operator interrupted the in-flight Loop'
    idx = src.find(marker)
    assert idx != -1, "cancellation stand_down ReviewerOutput must exist"
    # Look at the surrounding ~600 chars; must include the telemetry kwargs.
    window = src[max(0, idx - 200):idx + 800]
    for kwarg in (
        "input_tokens=total_input",
        "output_tokens=total_output",
        "cache_read_tokens=total_cache_read",
        "cache_create_tokens=total_cache_create",
        "model=model",
        "tool_rounds=rounds_used",
    ):
        assert kwarg in window, (
            f"cancellation stand_down missing telemetry kwarg: {kwarg}"
        )


# -----------------------------------------------------------------------------
# Contract 5: invocation_dispatcher's judgment-success path forwards telemetry.
# -----------------------------------------------------------------------------

def test_dispatcher_judgment_success_forwards_telemetry() -> None:
    # 2026-06-04 (ADR-315 carry-over): the judgment dispatch path moved from
    # the deleted services/invocation_dispatcher.py into services/wake.py
    # (ADR-296 v2 → ADR-298 wake-architecture migration). The telemetry-
    # forwarding shape (`_ro.get(...)` into record_execution_event) survived
    # verbatim; only the file it lives in changed.
    src = _read("services/wake.py")
    # Find the success-path record_execution_event call right after the
    # invoke_reviewer await returns successfully.
    marker = 'mode="judgment", trigger_type=trigger,\n        status="success"'
    idx = src.find(marker)
    assert idx != -1, (
        "judgment-success record_execution_event call site not found "
        "(F1 fix may be inverted or moved)"
    )
    # Grab a 1500-char window to capture the kwargs.
    window = src[idx:idx + 1500]
    for kwarg in (
        'input_tokens=_ro.get("input_tokens")',
        'output_tokens=_ro.get("output_tokens")',
        'cache_read_tokens=_ro.get("cache_read_tokens")',
        'cache_create_tokens=_ro.get("cache_create_tokens")',
        'model=_ro.get("model")',
        'tool_rounds=_ro.get("tool_rounds")',
    ):
        assert kwarg in window, (
            f"dispatcher judgment-success path missing kwarg: {kwarg}"
        )


# -----------------------------------------------------------------------------
# Contract 6: dispatcher guards against reviewer_output=None.
# -----------------------------------------------------------------------------

def test_dispatcher_guards_reviewer_output_none() -> None:
    # 2026-06-04 (ADR-315 carry-over): retargeted invocation_dispatcher.py →
    # wake.py (wake-architecture migration; guard shape preserved verbatim).
    src = _read("services/wake.py")
    # _ro must be assigned conditional on reviewer_output being a dict
    # so the .get() calls don't crash when invoke_reviewer returned None.
    assert "_ro = reviewer_output if isinstance(reviewer_output, dict) else {}" in src, (
        "dispatcher must guard reviewer_output=None before .get() access"
    )


# -----------------------------------------------------------------------------
# Contract 7: record_execution_event signature already accepts the kwargs.
# (Sanity check — telemetry.py was extended in prior work; this verifies
# the receiver didn't regress.)
# -----------------------------------------------------------------------------

def test_record_execution_event_accepts_telemetry_kwargs() -> None:
    src = _read("services/telemetry.py")
    tree = ast.parse(src)
    fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "record_execution_event":
            fn = node
            break
    assert fn is not None, "record_execution_event must be defined"
    kwonly_names = {arg.arg for arg in fn.args.kwonlyargs}
    required = {
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_create_tokens",
        "model",
        "tool_rounds",
    }
    missing = required - kwonly_names
    assert not missing, f"record_execution_event signature missing: {missing}"


if __name__ == "__main__":
    test_reviewer_output_declares_telemetry_fields()
    test_invoke_reviewer_accumulates_cache_tokens()
    test_invoke_reviewer_success_output_carries_telemetry()
    test_cancellation_standdown_carries_telemetry()
    test_dispatcher_judgment_success_forwards_telemetry()
    test_dispatcher_guards_reviewer_output_none()
    test_record_execution_event_accepts_telemetry_kwargs()
    print("F1 telemetry pass-through: 7/7 PASS")
