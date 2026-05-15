#!/usr/bin/env python3
"""Regression gate — envelope load timing observability (post-ADR-276 hardening, 2026-05-15).

Validates:
- `load_reviewer_governance_envelope` returns a `(dict, int)` tuple.
- The elapsed_ms is a non-negative int.
- The dict still carries the canonical ReviewerContext fields.
- `record_execution_event` accepts the new `envelope_load_ms` kwarg.
- Both callers (invocation_dispatcher reactive path, feed.py addressed path)
  unpack the tuple and route envelope_load_ms appropriately.

This test does NOT hit the database — it runs against an in-memory stub client
so the assertions are deterministic and the test is CI-safe.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


_passes = 0
_fails: list[str] = []


def _ok(msg: str) -> None:
    global _passes
    _passes += 1
    print(f"  ✓ {msg}")


def _bad(label: str, detail: str) -> None:
    _fails.append(f"{label}: {detail}")
    print(f"  ✗ {label}: {detail}")


# ---------------------------------------------------------------------------
# 1. Return-type contract: (dict, int) tuple
# ---------------------------------------------------------------------------

def test_envelope_returns_tuple() -> None:
    """The canonical helper returns (envelope_dict, elapsed_ms)."""

    # Stub: client.table().select().eq().eq().limit().execute() returns empty
    # data so each _read() yields "". We just want the call to complete and
    # the return shape to be a tuple.
    class _StubResp:
        data: list[dict] = []

    class _StubQuery:
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self): return _StubResp()

    class _StubClient:
        def table(self, *a, **k): return _StubQuery()

    # read_signal_files is called via dynamic import inside the helper;
    # monkeypatch the import target to a no-op async returning "".
    import importlib
    mod = importlib.import_module("agents.reviewer_agent")
    original_rsf = getattr(mod, "read_signal_files", None)

    async def _stub_rsf(client, user_id):  # noqa: ARG001
        return ""
    mod.read_signal_files = _stub_rsf  # type: ignore[attr-defined]

    try:
        from services.reviewer_envelope import load_reviewer_governance_envelope

        result = asyncio.run(load_reviewer_governance_envelope(_StubClient(), "u" * 36))

        if isinstance(result, tuple) and len(result) == 2:
            _ok("load_reviewer_governance_envelope returns a 2-tuple")
        else:
            _bad(
                "return shape",
                f"expected (dict, int) tuple, got {type(result).__name__}",
            )
            return

        envelope, elapsed_ms = result

        if isinstance(envelope, dict):
            _ok("first tuple element is a dict")
        else:
            _bad("envelope element", f"expected dict, got {type(envelope).__name__}")

        if isinstance(elapsed_ms, int) and elapsed_ms >= 0:
            _ok(f"second tuple element is non-negative int ({elapsed_ms}ms)")
        else:
            _bad(
                "elapsed_ms element",
                f"expected non-negative int, got {elapsed_ms!r}",
            )

        # Sanity: dict carries the canonical ReviewerContext keys.
        expected_keys = {
            "identity_md", "principles_md", "precedent_md", "mandate_md",
            "autonomy_md", "preferences_yaml",
            "operator_profile_md", "risk_md", "performance_md", "signal_files",
        }
        if expected_keys.issubset(envelope.keys()):
            _ok("envelope dict carries all 10 canonical ReviewerContext fields")
        else:
            missing = expected_keys - set(envelope.keys())
            _bad("envelope keys", f"missing: {sorted(missing)}")
    finally:
        if original_rsf is not None:
            mod.read_signal_files = original_rsf  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# 2. record_execution_event accepts envelope_load_ms
# ---------------------------------------------------------------------------

def test_telemetry_accepts_envelope_load_ms() -> None:
    from services import telemetry

    sig = inspect.signature(telemetry.record_execution_event)
    if "envelope_load_ms" in sig.parameters:
        param = sig.parameters["envelope_load_ms"]
        if param.default is None:
            _ok("record_execution_event.envelope_load_ms default=None (optional)")
        else:
            _bad(
                "envelope_load_ms default",
                f"expected None, got {param.default!r}",
            )
    else:
        _bad(
            "envelope_load_ms kwarg",
            "expected `envelope_load_ms` parameter on record_execution_event",
        )


# ---------------------------------------------------------------------------
# 3. invocation_dispatcher routes envelope_load_ms into record_execution_event
# ---------------------------------------------------------------------------

def test_dispatcher_routes_envelope_load_ms() -> None:
    src = (ROOT / "services" / "invocation_dispatcher.py").read_text()

    # Tuple-unpack at the call site.
    if "governance_envelope, envelope_load_ms = await load_reviewer_governance_envelope" in src:
        _ok("dispatcher unpacks (envelope, elapsed_ms)")
    else:
        _bad(
            "dispatcher unpack pattern",
            "expected tuple-unpack at load_reviewer_governance_envelope call",
        )

    # The success-path record_execution_event call carries envelope_load_ms.
    # We don't try to parse the full call expression; we check both the
    # `envelope_load_ms=envelope_load_ms` pattern (success) and the
    # `envelope_load_ms=_env_ms` pattern (failure with guarded local).
    success_threading = "envelope_load_ms=envelope_load_ms" in src
    failure_threading = "envelope_load_ms=_env_ms" in src

    if success_threading:
        _ok("dispatcher threads envelope_load_ms into success-path record_execution_event")
    else:
        _bad(
            "dispatcher success-path threading",
            "expected envelope_load_ms=envelope_load_ms in success record_execution_event",
        )

    if failure_threading:
        _ok("dispatcher threads guarded envelope_load_ms into failure-path record_execution_event")
    else:
        _bad(
            "dispatcher failure-path threading",
            "expected envelope_load_ms=_env_ms (locals().get guard) in failure record_execution_event",
        )


# ---------------------------------------------------------------------------
# 4. feed.py addressed path logs envelope_load_ms via structured logger
# ---------------------------------------------------------------------------

def test_feed_addressed_path_logs_envelope_load_ms() -> None:
    src = (ROOT / "routes" / "feed.py").read_text()

    if "governance_envelope, envelope_load_ms = await load_reviewer_governance_envelope" in src:
        _ok("feed.py addressed path unpacks (envelope, elapsed_ms)")
    else:
        _bad(
            "feed.py unpack pattern",
            "expected tuple-unpack at load_reviewer_governance_envelope call in feed.py",
        )

    # Addressed turns don't write to execution_events — log to structured
    # logger instead. Check for the specific log marker.
    if "[REVIEWER_ENVELOPE]" in src and "envelope_load_ms=%d" in src:
        _ok("feed.py logs envelope_load_ms via structured logger")
    else:
        _bad(
            "feed.py logger emit",
            "expected `[REVIEWER_ENVELOPE]` log line carrying envelope_load_ms",
        )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 72)
    print("envelope observability regression gate (post-ADR-276 hardening, 2026-05-15)")
    print("=" * 72)

    test_envelope_returns_tuple()
    test_telemetry_accepts_envelope_load_ms()
    test_dispatcher_routes_envelope_load_ms()
    test_feed_addressed_path_logs_envelope_load_ms()

    print()
    print("=" * 72)
    if _fails:
        print(f"FAIL: {len(_fails)} assertion(s) failed, {_passes} passed")
        for f in _fails:
            print(f"  - {f}")
        return 1
    print(f"PASS: {_passes}/{_passes} assertions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
