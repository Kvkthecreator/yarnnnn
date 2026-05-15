"""Regression gate for ADR-276 — Reactive-trigger envelope governance pre-load.

The Reviewer's reactive wakes (recurrence fires + proposal arrivals) must
receive the same governance + domain substrate pre-load that addressed
wakes receive. Both trigger paths share `services/reviewer_envelope.py::
load_reviewer_governance_envelope` per Singular Implementation discipline.

Run:
    python -m api.test_adr276_reactive_envelope
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
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
# 1. Helper module exists + exports the canonical function
# ---------------------------------------------------------------------------

def test_helper_module_exists() -> None:
    try:
        from services.reviewer_envelope import load_reviewer_governance_envelope
    except ImportError as e:
        _bad("services.reviewer_envelope importable", str(e))
        return

    sig = inspect.signature(load_reviewer_governance_envelope)
    params = list(sig.parameters.keys())
    if params == ["client", "user_id"]:
        _ok("load_reviewer_governance_envelope(client, user_id) signature")
    else:
        _bad(
            "load_reviewer_governance_envelope signature",
            f"expected (client, user_id), got {params}",
        )

    if asyncio.iscoroutinefunction(load_reviewer_governance_envelope):
        _ok("load_reviewer_governance_envelope is async")
    else:
        _bad(
            "load_reviewer_governance_envelope must be async",
            "expected coroutine function",
        )


# ---------------------------------------------------------------------------
# 2. Helper reads the canonical 9 substrate paths
# ---------------------------------------------------------------------------

def test_helper_reads_canonical_paths() -> None:
    import services.reviewer_envelope as mod
    src = inspect.getsource(mod)

    # All 6 path constants from workspace_paths
    needles = [
        "REVIEW_IDENTITY_PATH",
        "REVIEW_PRINCIPLES_PATH",
        "SHARED_PRECEDENT_PATH",
        "SHARED_MANDATE_PATH",
        "SHARED_AUTONOMY_PATH",
        "SHARED_PREFERENCES_PATH",
    ]
    missing = [n for n in needles if n not in src]
    if not missing:
        _ok("helper imports 6 governance path constants from workspace_paths")
    else:
        _bad("workspace_paths constants", f"missing: {missing}")

    # Three trading-program-specific paths
    trading_paths = [
        '"context/trading/_operator_profile.md"',
        '"context/trading/_risk.md"',
        '"context/trading/_performance.md"',
    ]
    missing_t = [p for p in trading_paths if p not in src]
    if not missing_t:
        _ok("helper reads 3 trading-domain paths")
    else:
        _bad("trading domain paths", f"missing: {missing_t}")

    # Signal-files compact summary
    if "read_signal_files" in src:
        _ok("helper invokes read_signal_files for signal-state summary")
    else:
        _bad(
            "signal_files coverage",
            "expected read_signal_files call in helper",
        )


# ---------------------------------------------------------------------------
# 3. Helper returns dict keyed by ReviewerContext field names
# ---------------------------------------------------------------------------

def test_helper_return_shape() -> None:
    """Helper return dict must use the same field names as ReviewerContext."""
    from agents.reviewer_agent import ReviewerContext
    import services.reviewer_envelope as mod
    src = inspect.getsource(mod)

    rc_fields = set(getattr(ReviewerContext, "__annotations__", {}).keys())
    expected_envelope_keys = {
        "identity_md", "principles_md", "precedent_md", "mandate_md",
        "autonomy_md", "preferences_yaml",
        "operator_profile_md", "risk_md", "performance_md",
        "signal_files",
    }

    # All expected keys are declared on ReviewerContext
    missing_on_ctx = expected_envelope_keys - rc_fields
    if not missing_on_ctx:
        _ok("ReviewerContext declares all 10 envelope keys")
    else:
        _bad(
            "ReviewerContext fields",
            f"missing on TypedDict: {missing_on_ctx}",
        )

    # The helper's source contains each key as a return-dict literal
    missing_in_helper = [k for k in expected_envelope_keys if f'"{k}":' not in src]
    if not missing_in_helper:
        _ok("helper return dict contains all 10 envelope keys")
    else:
        _bad(
            "helper return dict keys",
            f"missing: {missing_in_helper}",
        )


# ---------------------------------------------------------------------------
# 4. routes/feed.py migrated to the shared helper (no inline gather)
# ---------------------------------------------------------------------------

def test_feed_route_uses_shared_helper() -> None:
    src = (ROOT / "routes" / "feed.py").read_text()
    if "from services.reviewer_envelope import load_reviewer_governance_envelope" in src:
        _ok("routes/feed.py imports load_reviewer_governance_envelope")
    else:
        _bad(
            "feed.py helper import",
            "expected 'from services.reviewer_envelope import "
            "load_reviewer_governance_envelope'",
        )

    # ADR-276 hardening (2026-05-15): helper now returns (dict, elapsed_ms)
    # tuple so callers can record envelope load latency. Caller pattern
    # updated to tuple-unpack.
    if "governance_envelope, envelope_load_ms = await load_reviewer_governance_envelope" in src:
        _ok("routes/feed.py calls the helper (tuple-unpack)")
    else:
        _bad(
            "feed.py helper call",
            "expected 'governance_envelope, envelope_load_ms = await "
            "load_reviewer_governance_envelope'",
        )

    # The old inline _asyncio.gather of 9 paths should be gone. We check
    # specifically that the unpack-tuple syntax for the 9 fields is no
    # longer present in feed.py (was Singular Implementation violation).
    inline_tuple = (
        "        (\n            identity_md, principles_md, precedent_md, mandate_md,\n"
        "            autonomy_md, preferences_yaml,\n"
        "            operator_profile_md, risk_md, performance_md,\n        ) = await"
    )
    if inline_tuple not in src:
        _ok("feed.py no longer has the inline 9-file gather tuple")
    else:
        _bad(
            "feed.py inline gather removal",
            "the inline _asyncio.gather of 9 paths is still present "
            "(Singular Implementation violation)",
        )

    # And the dict-spread {**governance_envelope, ...} pattern is in the
    # context bag passed to invoke_reviewer.
    if "**governance_envelope" in src:
        _ok("feed.py context bag dict-spreads governance_envelope")
    else:
        _bad(
            "feed.py context bag",
            "expected '**governance_envelope' in invoke_reviewer call",
        )


# ---------------------------------------------------------------------------
# 5. invocation_dispatcher.py wires the helper into reactive dispatch
# ---------------------------------------------------------------------------

def test_dispatcher_wires_governance_envelope() -> None:
    src = (ROOT / "services" / "invocation_dispatcher.py").read_text()
    if "from services.reviewer_envelope import load_reviewer_governance_envelope" in src:
        _ok("invocation_dispatcher.py imports load_reviewer_governance_envelope")
    else:
        _bad(
            "dispatcher helper import",
            "expected 'from services.reviewer_envelope import "
            "load_reviewer_governance_envelope'",
        )

    # ADR-276 hardening (2026-05-15): tuple-unpack pattern matches feed.py.
    if "governance_envelope, envelope_load_ms = await load_reviewer_governance_envelope" in src:
        _ok("invocation_dispatcher.py calls the helper (tuple-unpack)")
    else:
        _bad(
            "dispatcher helper call",
            "expected 'governance_envelope, envelope_load_ms = await "
            "load_reviewer_governance_envelope'",
        )

    if "**governance_envelope" in src:
        _ok("invocation_dispatcher.py context bag dict-spreads governance_envelope")
    else:
        _bad(
            "dispatcher context bag",
            "expected '**governance_envelope' in invoke_reviewer call",
        )

    # The reactive context bag retains the recurrence-specific keys.
    for key in (
        '"recurrence_prompt": prompt',
        '"recurrence_slug": recurrence.slug',
        '"operating_context_block": operating_context',
    ):
        if key in src:
            continue
        _bad("dispatcher context preservation", f"missing key: {key}")
        return
    _ok("dispatcher preserves recurrence_prompt + recurrence_slug + operating_context_block")


# ---------------------------------------------------------------------------
# 6. ADR-276 doc + cross-refs in place
# ---------------------------------------------------------------------------

def test_adr276_doc_exists() -> None:
    repo_root = ROOT.parent
    path = repo_root / "docs" / "adr" / "ADR-276-reactive-trigger-envelope-governance-preload.md"
    if not path.exists():
        _bad("ADR-276 doc present", f"missing: {path}")
        return
    text = path.read_text()
    needles = ["FOUNDATIONS v8.5", "ADR-274", "ADR-275", "Derived Principle 18", "Singular Implementation"]
    missing = [n for n in needles if n not in text]
    if not missing:
        _ok("ADR-276 doc cites all required ancestors + discipline")
    else:
        _bad("ADR-276 doc cross-refs", f"missing: {missing}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("ADR-276 — Reactive-trigger envelope governance pre-load\n")

    test_helper_module_exists()
    test_helper_reads_canonical_paths()
    test_helper_return_shape()
    test_feed_route_uses_shared_helper()
    test_dispatcher_wires_governance_envelope()
    test_adr276_doc_exists()

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
